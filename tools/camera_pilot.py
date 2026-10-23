#!/usr/bin/env python3
"""Optional CONDITIONAL camera detector pilot, never an experimental precision claim.

Consumes only already opened N direct MAT intensity, no true N particle labels.
Each foreground AND each matched reference are separately counted as exposures.
Threshold comes from dev nulls, not validation nulls. Never optimizes diameter.
"""
from __future__ import annotations
import argparse, csv,hashlib,json,sys
from pathlib import Path
import h5py,numpy as np
from scipy.stats import beta
from _shared import load_json,save_json,sha
from event_budget import Ledger,BudgetExceeded


def one_sided_cp_upper(k,n,confidence=.95):
    if n<1 or k<0 or k>n:raise ValueError('INVALID_BINOMIAL_COUNTS')
    return 1. if k==n else float(beta.ppf(confidence,k+1,n-k))


def observe_pair(mean_I,mean_bg,read_noise,rng):
    if mean_I.shape!=mean_bg.shape or not np.isfinite(mean_I).all() or not np.isfinite(mean_bg).all():
        raise ValueError('INVALID_EXPECTED_ELECTRON_ARRAYS')
    if (mean_I<0).any() or (mean_bg<=0).any():raise ValueError('NONPOSITIVE_EXPECTED_COUNTS')
    foreground=rng.poisson(mean_I).astype(float)+rng.normal(0.,read_noise,mean_I.shape)
    reference=rng.poisson(mean_bg).astype(float)+rng.normal(0.,read_noise,mean_bg.shape)
    if (reference<=0).any():raise ValueError('NO_VALID_REFERENCE_COUNT__REJECT_NO_CLIP')
    return foreground,reference,(foreground-reference)/reference


def test_statistic(C):
    if C.shape!=(17,17) or not np.isfinite(C).all():raise ValueError('INVALID_CAMERA_C')
    return float(np.max(np.abs(C[2:15,2:15])))


def run(repo,out,cfg):
    repo=Path(repo).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    pc=cfg['camera_optional_pilot'];budget=cfg['hard_budget_new_v143']
    ledger=Ledger(repo/'results/v143/logs/v143_budget.sqlite',{'FORWARD':budget['total_oldF2_and_F2c_forward_queries'],
       'BEM':budget['new_BEM_attempts'],'RENDER':budget['new_render_attempts'],
       'CAMERA':budget['new_camera_exposure_events']})
    ndev=pc['dev_null_per_B'];nval=pc['independent_null_per_B'];repeat=pc['target_repetitions_per_condition_per_B']
    anonymous=cfg['N_opened_scored_cases'];folder=repo/cfg['source_files']['N_original_mats'];images={}
    for anon in anonymous:
        p=folder/(anon+'_at_offset.mat')
        with h5py.File(p,'r') as f:
            I=np.asarray(f['r/Itotal'][()],float).T[::-1,:]
            B=np.asarray(f['r/Iref'][()],float).T[::-1,:]
            C=np.asarray(f['r/contrast'][()],float).T[::-1,:]
        if I.shape!=(17,17) or not np.isfinite(I).all() or (B<=0).any() or np.max(np.abs((I-B)/B-C))>1e-12:
            raise ValueError('CAMERA_PILOT_SOURCE_UNQUALIFIED:'+anon)
        images[anon]=(I,B,sha(p))
    # Each nominal pair is EXACTLY two new simulated exposure events.
    total_expected=2*len(pc['B_electrons_per_pixel_per_100us'])*(ndev+nval+len(anonymous)*repeat)
    if total_expected!=pc['nominal_total_events'] or total_expected>budget['new_camera_exposure_events']:
        raise ValueError('CAMERA_BUDGET_OR_CONFIG_WRONG')
    allsummary=[];detail=[]
    h5path=out/'conditional_camera_arrays.h5'
    with h5py.File(h5path,'a') as h:
        for bi,Blevel in enumerate(pc['B_electrons_per_pixel_per_100us']):
            seed=int(pc['rng_seeds_by_B'][bi])
            base=list(images.values())[0][1];factor=float(Blevel)/float(np.mean(base))
            exp_bg=base*factor
            dev_stats=[]
            # Each B has independent public random seed and strict event list.
            def observation(label,anon,meanI,meanBg,stage):
                key=f'V143_CAMERA_B{Blevel}_{stage}_{label}'
                group=f'B{Blevel}/{stage}/{label}'
                source_file_id=images[anon][2] if anon is not None else list(images.values())[0][2]
                source_sig=hashlib.sha256((str(Blevel)+'|'+str(seed)+'|'+stage+'|'+label+'|'+str(anon)+'|'+source_file_id).encode()).hexdigest()
                existing=ledger.get(key)
                if existing:
                    if group in h and existing['state']=='COMPLETED' and h[group].attrs.get('signature')==source_sig:
                        saved=h[group];return np.asarray(saved['C'][()]),float(saved.attrs['T'])
                    raise ValueError('CAMERA_PARTIAL_OR_MISMATCHED_RESUME:'+key)
                ledger.reserve(key,'CAMERA',2,{'source_signature':source_sig,'anon':anon,'rng_seed':seed,'B':Blevel})
                try:
                    event_seed=int.from_bytes(hashlib.sha256((str(seed)+'|'+stage+'|'+label).encode()).digest()[:8],'little')
                    event_rng=np.random.default_rng(event_seed)
                    fg,ref,C=observe_pair(meanI,meanBg,pc['read_noise_electrons'],event_rng)
                    T=test_statistic(C)
                    g=h.create_group(group);g.create_dataset('foreground_counts',data=fg,compression='gzip')
                    g.create_dataset('reference_counts',data=ref,compression='gzip')
                    g.create_dataset('C',data=C,compression='gzip')
                    g.attrs['T']=T;g.attrs['signature']=source_sig;g.attrs['observation_kind']='IDEAL_CONDITIONAL_POISSON_GAUSSIAN'
                    h.flush();ledger.finish(key,'COMPLETED',2,{'score':T})
                    return C,T
                except Exception as e:
                    ledger.finish(key,'FAILED',2,{'exception':repr(e)});raise
            for j in range(ndev):
                _,score=observation(f'dev_{j:03d}',None,exp_bg,exp_bg,'dev_null');dev_stats.append(score)
            # Freeze the threshold BEFORE independent validation nulls.
            threshold=float(max(dev_stats))
            threshold_file=out/f'B{Blevel}_dev_frozen_threshold.json'
            if threshold_file.exists():
                prev=load_json(threshold_file)
                if abs(prev['threshold']-threshold)>1e-15 or prev['seed']!=seed:raise ValueError('THRESHOLD_REPRODUCIBILITY_OR_RESUME_FAILED')
            else:save_json(threshold_file,{'threshold':threshold,'method':'MAX_80_DEV_NULL',
                'seed':seed,'B':Blevel,'n_dev':ndev,'not_tuned_using_independent_val':True})
            k=0
            for j in range(nval):
                _,T=observation(f'val_{j:03d}',None,exp_bg,exp_bg,'val_null')
                k+=T>threshold;detail.append({'B':Blevel,'stage':'val_null','case':'blank','T':T,'detected':T>threshold})
            up=one_sided_cp_upper(k,nval)
            target_count=0;detected=0
            for anon in anonymous:
                I,B,source_sha=images[anon]
                meanI=I*float(Blevel)/float(np.mean(B))
                meanBg=B*float(Blevel)/float(np.mean(B))
                for j in range(repeat):
                    _,T=observation(f'{anon}_{j:02d}',anon,meanI,meanBg,'target')
                    target_count+=1;detected+=T>threshold
                    detail.append({'B':Blevel,'stage':'target','case':anon,'T':T,'detected':T>threshold})
            allsummary.append({'B_electrons_per_pixel':Blevel,'threshold_from_dev_only':threshold,
                'dev_null_n':ndev,'independent_null_n':nval,'val_false_positives':k,
                'one_sided95_cp_upper':up,'FPR_qualified':up<=pc['false_positive_95pct_one_sided_upper_at_most'],
                'target_n':target_count,'target_detected':detected,'camera_diameter_reportability':'NOT_EVALUATED',
                'scope':'ASSUMED_COUNTS__NOT_REAL_CAMERA_FULL_WELL_OR_ABSOLUTE_DIAMETER'})
    result={'schema':'iscat143.conditional_camera_pilot.1','n_new_exposures_recorded':ledger.spent('CAMERA'),
        'events_are_foreground_and_matched_reference':True,'run_seed_per_B':pc['rng_seeds_by_B'],
        'background_assumption':'COUNT_LEVELS_CONDITIONAL_FULL_WELL_UNMEASURED',
        'results':allsummary,'no_experimental_absolute_validation':True}
    save_json(out/'conditional_camera_pilot.json',result)
    with (out/'camera_trial_summary.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['B','stage','case','T','detected']);w.writeheader();w.writerows(detail)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--out',required=True);p.add_argument('--config',default=None);a=p.parse_args()
    cfg=load_json(a.config or Path(__file__).resolve().parents[1]/'config/v143_science_config.json')
    try:r=run(a.repo,a.out,cfg)
    except Exception as e:
        save_json(Path(a.out)/'camera_pilot_error.json',{'status':'BLOCKED_NO_PILOT_PASS','error':repr(e)})
        print('CAMERA_PILOT_BLOCKED:',repr(e),file=sys.stderr);return 2
    print('CAMERA_PILOT_COMPLETED__CONDITIONAL_ONLY',r['n_new_exposures_recorded']);return 3
if __name__=='__main__':raise SystemExit(main())
