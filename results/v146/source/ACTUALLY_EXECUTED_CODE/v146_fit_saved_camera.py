#!/usr/bin/env python3
"""Fit the 36 EXISTING camera target pairs. Never generates new exposures.
Uses no clean theta, original D labels, or validator truth to initialize fits.
Keeps detection decisions frozen; fitting a non-detection is diagnostic only.
"""
from __future__ import annotations
import argparse,itertools,sys,time
from pathlib import Path
import numpy as np,h5py
from v146_core import (read_json,save_json,digest,file_sha,array_sha,score_crop,
                      ratio_contrast_and_variance,choose_public_starts,fit_camera,Predictor)
from v146_runtime import construct_bound
from v146_ledger import Ledger


def camera_events(path,threshold_root,levels,read_noise=2.):
    threshold_root=Path(threshold_root);rows=[]
    with h5py.File(path,'r') as h:
        for B in levels:
            frozen=read_json(threshold_root/f'B{B}_dev_frozen_threshold.json')
            threshold=float(frozen['threshold'])
            if frozen['B']!=B:raise ValueError('WRONG_THRESHOLD_B')
            base=f'B{B}/target'
            if base not in h or len(h[base])!=12:raise ValueError('EXPECTED_12_TARGETS_PER_B')
            for label in sorted(h[base].keys()):
                g=h[f'{base}/{label}']
                f=np.asarray(g['foreground_counts'][()],float);r=np.asarray(g['reference_counts'][()],float)
                C,V=ratio_contrast_and_variance(f,r,read_noise)
                stored=np.asarray(g['C'][()],float)
                if C.shape!=(17,17) or not np.allclose(C,stored,rtol=0,atol=1e-12):raise ValueError('CAMERA_C_REPLAY_FAILED')
                T=float(np.max(np.abs(score_crop(C))))
                if abs(float(g.attrs['T'])-T)>1e-12:raise ValueError('CAMERA_T_REPLAY_FAILED')
                rows.append({'event_id':f'B{B}_{label}','B':B,'label':label,'T':T,'threshold':threshold,
                             'detected':T>threshold,'Y':score_crop(C),'V':score_crop(V),
                             'observation_sha256':array_sha(score_crop(C)),
                             'counts_sha256':digest([array_sha(f),array_sha(r)]),
                             'variance_sha256':array_sha(score_crop(V)),
                             'threshold_sha256':file_sha(threshold_root/f'B{B}_dev_frozen_threshold.json')})
    return rows


def bank_create_or_reuse(model,folder,ledger,cfg):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    thetas=[list(map(float,t)) for t in itertools.product(model.base.Ds,model.base.Hs,
                                                       cfg['camera_fit']['public_xy_nm'],cfg['camera_fit']['public_xy_nm'])]
    sig=digest({'model_id':model.model_id,'thetas':thetas,'code_sha256':file_sha(__file__)})
    meta=folder/'public_bank.json';npz=folder/'public_bank.npz';op='PUBLIC_BANK_'+sig[:20]
    event=ledger.get(op)
    if event:
        if not(meta.is_file() and npz.is_file()):raise ValueError('BANK_CHECKPOINT_MISSING_RECONCILE')
        doc=read_json(meta)
        if event['state']!='COMPLETED' or doc['signature']!=sig or file_sha(npz)!=doc['npz_sha256']:
            raise ValueError('BANK_REUSE_IDENTITY_MISMATCH')
        with np.load(npz) as z:return z['theta'].copy(),z['scores'].copy(),sig
    ledger.reserve(op,'FORWARD',len(thetas),sig);pred=Predictor(model,len(thetas))
    try:
        scores=np.stack([pred(t) for t in thetas]);np.savez_compressed(npz,theta=np.array(thetas),scores=scores)
        save_json(meta,{'signature':sig,'model_id':model.model_id,'npz_sha256':file_sha(npz),
                        'public_parameters_only':True,'n_templates':len(thetas)})
        ledger.finish(op,pred.used)
    except Exception as e:ledger.finish(op,pred.used,'FAILED',{'error':repr(e)});raise
    return np.array(thetas),scores,sig


def run(repo,cfg,out):
    repo=Path(repo).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    if out!=(repo/'results/v146/camera_fits').resolve():raise ValueError('OUTPUT_MUST_BE_RESULTS_V146_CAMERA_FITS')
    camera=repo/cfg['inputs']['camera_h5'];expected=cfg['frozen']['camera_h5_sha256']
    if file_sha(camera)!=expected:raise ValueError('CAMERA_ARRAY_FILE_CHANGED')
    # Verify the complete existing dev/val/target replay BEFORE consuming images.
    source=repo/'tools/v145_camera_replay.py'
    if file_sha(source)!=cfg['frozen']['camera_replay_code_sha256']:raise ValueError('REPLAY_CODE_CHANGED')
    sys.path.insert(0,str(repo/'tools'))
    from v145_camera_replay import replay
    replay_result=replay(camera,repo/cfg['inputs']['camera_root'])
    save_json(out/'existing_camera_replay.json',replay_result)
    model=construct_bound(repo,cfg)
    ledger=Ledger(repo/'results/v146/logs/budget.sqlite',cfg['task_id'],cfg['budget_limits'])
    bank_theta,bank_scores,bsig=bank_create_or_reuse(model,out/'bank',ledger,cfg)
    events=camera_events(camera,repo/cfg['inputs']['camera_root'],cfg['camera_fit']['levels'],cfg['camera_fit']['read_noise_e'])
    # Earlier low-count detections should not starve high-count data: round-robin
    # by repetition/anonymous label, alternating B. No true D is used.
    events.sort(key=lambda r:(r['label'], -r['B']))
    estimator_id='v146-deltaGLS-'+digest({'model_id':model.model_id,'bank_signature':bsig,
        'method':cfg['camera_fit'],'entry_sha256':file_sha(__file__),
        'core_sha256':file_sha(Path(__file__).with_name('v146_core.py'))})
    rows=[];start=time.monotonic()
    for event in events:
        if time.monotonic()-start>cfg['camera_fit']['wall_minutes']*60:
            rows.append({'event_id':event['event_id'],'status':'NOT_RUN_WALL_LIMIT','reportable_D':None});continue
        y,v=event['Y'],event['V'];details={k:w for k,w in event.items() if k not in ('Y','V')}
        sig=digest({'event':details,'bank_signature':bsig,'config':cfg['camera_fit'],
                    'estimator_code_sha':file_sha(__file__),
                    'core_sha':file_sha(Path(__file__).with_name('v146_core.py'))})
        op='CAMERA_FIT_'+sig[:24];path=out/'events'/(event['event_id']+'.json');old=ledger.get(op)
        if old:
            if not path.is_file():raise ValueError('FIT_RESERVED_WITHOUT_CHECKPOINT_RECONCILE:'+op)
            saved=read_json(path)
            if saved.get('signature')!=sig or old['state'] not in ('COMPLETED','PARTIAL'):raise ValueError('BAD_CAMERA_RESUME')
            rows.append(saved);continue
        cap=cfg['camera_fit']['calls_per_pair'];ledger.reserve(op,'FORWARD',cap,sig)
        try:
            starts=choose_public_starts(bank_theta,bank_scores,y,v,cfg['camera_fit']['starts'])
            fit=fit_camera(model,y,v,starts,cap,cfg['camera_fit']['max_nfev'])
            fit['reason_codes']+=[] if event['detected'] else ['NOT_DETECTED_DIAGNOSTIC_CANDIDATE_ONLY']
            doc={'signature':sig,'model_id':model.model_id,'estimator_id':estimator_id,'observation_run_id':sig,
                 'event':details,'fit':fit,'camera_diameter_qualified':False,
                 'scope':'OPENED_SAVED_SIMULATION_REANALYSIS_NOT_NEW_BLIND_TEST'}
            save_json(path,doc)
            ledger.finish(op,fit['actual_forward_calls'],'PARTIAL' if fit['callback_cap_reached'] else 'COMPLETED')
            rows.append(doc)
        except Exception as exc:
            # Lost callback counter must not be guessed as zero.
            ledger.finish(op,None,'FAILED',{'actual_unknown_reservation_kept':True,'error':repr(exc)})
            save_json(path,{'signature':sig,'status':'FAILED','error':repr(exc),'reportable_D':None});raise
    result={'schema':'iscat146.saved_camera_sizing.1','observed_pair_count':len(events),
            'new_camera_exposures':0,'new_BEM':0,'new_render':0,'event_results':rows,
            'model_id':model.model_id,'estimator_id':estimator_id,'source_h5_sha256':expected,
            'coverage_or_95pct_CI_certified':False,'all_reportable_D_null':True,
            'missing_or_partial_fits':[r.get('event_id',r.get('event',{}).get('event_id')) for r in rows if 'fit' not in r or r.get('fit',{}).get('callback_cap_reached')],
            'budget':ledger.summary()}
    save_json(out/'summary.json',result)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--config',required=True);p.add_argument('--out',required=True)
    a=p.parse_args()
    try:r=run(a.repo,read_json(a.config),a.out)
    except Exception as e:save_json(Path(a.out)/'blocked.json',{'status':'BLOCKED','error':repr(e)});return 2
    print('SAVED_CAMERA_CANDIDATES_COMPLETE__FULL_CONTRACT_REQUIRES_MORE_STAGES')
    return 3
if __name__=='__main__':raise SystemExit(main())
