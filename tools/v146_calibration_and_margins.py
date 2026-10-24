#!/usr/bin/env python3
"""Replay retained noiseless witnesses; conditional curves; bounded local-D repair.
No simulator true D file is read. No BEM, render, random camera image or new kernel.
"""
from __future__ import annotations
import argparse,csv,time
from pathlib import Path
import numpy as np
from v146_core import (read_json,save_json,digest,file_sha,valid_witness,observed_margin,
                       fixed_d_minimize,Predictor)
from v146_runtime import construct_bound,load_clean
from v146_ledger import Ledger


def run(repo,cfg,out):
    repo=Path(repo).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    if out!=(repo/'results/v146/calibration').resolve():raise ValueError('BAD_OUTPUT_DIRECTORY')
    model=construct_bound(repo,cfg);ledger=Ledger(repo/'results/v146/logs/budget.sqlite',cfg['task_id'],cfg['budget_limits'])
    reports=read_json(repo/cfg['inputs']['v145_report'])['cases']
    candidates={};observations={};oldrows={}
    for case in cfg['N_cases']+cfg['M_cases']:
        y,t,ysha=load_clean(repo,cfg,case);rec=reports[case]
        if rec['model_id']!=model.model_id or rec['observation_sha256']!=ysha or abs(rec['candidate_D']-t[0])>1e-10:
            raise ValueError('ESTIMATOR_REPORT_BINDING_CHANGED:'+case)
        candidates[case]=t;observations[case]=y
        oldrows[case]=[valid_witness(w['theta'],w['loss_L2'],w['D']) for w in rec['all_fixed_D_witness_points']]
    sig=digest({'model_id':model.model_id,'config':cfg['conditional_calibration'],
                'reports_sha':file_sha(repo/cfg['inputs']['v145_report']),'code_sha':file_sha(__file__)})
    op='CALIBRATION_REPLAY_'+sig[:20];path=out/'calibration_replay.json';ev=ledger.get(op)
    if ev:
        if not path.is_file() or ev['state']!='COMPLETED' or read_json(path)['signature']!=sig:raise ValueError('CALIBRATION_RESUME_NOT_VERIFIED')
        initial=read_json(path)
        if file_sha(out/'conditional_calibration_arrays.npz')!=initial['arrays_sha256']:raise ValueError('CALIBRATION_ARRAYS_TAMPERED')
    else:
        slices=cfg['conditional_calibration'];grid=[(d,h,0.,0.) for h in slices['h_slices_nm'] for d in slices['D_grid_nm']]
        cap=sum(len(v) for v in oldrows.values())+len(grid)
        ledger.reserve(op,'FORWARD',cap,sig);pred=Predictor(model,cap);replayed={};curves=[];arrays=[]
        try:
            for case,points in oldrows.items():
                replayed[case]=[]
                for w in points:
                    R=float(np.linalg.norm(pred(w['theta'])-observations[case]))
                    if abs(R-w['loss_L2'])>1e-10+1e-8*abs(w['loss_L2']):raise ValueError('STORED_WITNESS_LOSS_REPLAY_MISMATCH:'+case)
                    replayed[case].append(valid_witness(w['theta'],R,w['D']))
            for t in grid:
                C=pred(t);arrays.append(C)
                curves.append({'D_nm':float(t[0]),'h_nm':float(t[1]),'x_nm':0.,'y_nm':0.,
                               'center_signed_C':float(C[6,6]),'peak_abs_C':float(np.max(np.abs(C))),
                               'score_norm_L2':float(np.linalg.norm(C))})
            np.savez_compressed(out/'conditional_calibration_arrays.npz',theta=np.array(grid),score_C=np.stack(arrays))
            with (out/'conditional_calibration.csv').open('w',encoding='utf-8',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(curves[0]));w.writeheader();w.writerows(curves)
            initial={'signature':sig,'model_id':model.model_id,'verified_witnesses':replayed,
                'curves_n':len(curves),'actual_forward_calls':pred.used,'new_physics':0,
                'scope':'FIXED_HEIGHT_CONDITIONAL_CALIBRATION_NOT_UNIVERSAL_C_TO_D',
                'arrays_sha256':file_sha(out/'conditional_calibration_arrays.npz')}
            save_json(path,initial);ledger.finish(op,pred.used)
        except Exception as e:ledger.finish(op,pred.used,'FAILED',{'error':repr(e)});raise
    allpoints={c:list(v) for c,v in initial['verified_witnesses'].items()}
    attempts=[];started=time.monotonic();jobs=[]
    for case in cfg['N_cases']:
        t=candidates[case]
        for offset in (-5.,-2.5,2.5,5.):
            D=float(t[0]+offset)
            if 30<=D<=200 and not any(abs(w['D']-D)<1e-10 for w in allpoints[case]):jobs.append((case,D))
    jobs=jobs[:cfg['noiseless']['max_new_fixed_D_points']]
    for case,D in jobs:
        t=candidates[case];y=observations[case]
        jsig=digest({'parent':sig,'case':case,'D_hex':D.hex(),'obs':array_hash(y),
                     'core_sha':file_sha(Path(__file__).with_name('v146_core.py'))})
        op='LOCAL_D_'+jsig[:24];p=out/'local_D'/f'{case}_{jsig[:24]}.json';ev=ledger.get(op)
        if ev:
            if not p.is_file() or ev['state'] not in ('COMPLETED','PARTIAL') or read_json(p)['signature']!=jsig:
                raise ValueError('LOCAL_D_RESUME_NOT_VERIFIED')
            doc=read_json(p)
        else:
            if time.monotonic()-started>180*60:
                attempts.append({'case':case,'D':D,'status':'NOT_RUN_WALL_LIMIT'});continue
            cap=cfg['noiseless']['per_fixed_D_forward_cap'];ledger.reserve(op,'FORWARD',cap,jsig)
            try:
                starts=[t[1:]]+[[h,t[2],t[3]] for h in (350.,400.,450.,500.,550.)]
                # Fixed per-image scale changes stopping behavior, not raw loss/order.
                scale=max(float(np.linalg.norm(y)),1e-12)
                r=fixed_d_minimize(model,D,y,starts,max_calls=cap,max_nfev=90,scale=scale)
                doc={'signature':jsig,'case':case,'model_id':model.model_id,'result':r}
                save_json(p,doc);ledger.finish(op,r['actual_forward_calls'],
                    'PARTIAL' if r['actual_forward_calls']>=cap else 'COMPLETED')
            except Exception as exc:
                ledger.finish(op,None,'FAILED',{'error':repr(exc),'unknown_actual_charged_full':True});raise
        r=doc['result'];attempts.append({'case':case,'D':D,'path':p.name,'calls':r['actual_forward_calls']})
        if r['best']:allpoints[case].append(valid_witness(r['best']['theta'],r['best']['loss_L2'],D))
    margin={}
    eps=cfg['noiseless']['legacy_epsilon_L2']
    for case,points in allpoints.items():
        d=observed_margin(points,candidates[case][0]);low=d.get('best_observed_L2')
        d['tolerance_sensitivity']=[{'factor':f,'epsilon_L2':f*eps,
            'observed_compatible_D':[w['D'] for w in points if low is not None and w['loss_L2']<=low+f*eps]}
             for f in (.25,.5,1.,2.)]
        d['parameterization']='FIXED_D__CONTINUOUS_H_X_Y';d['conditional_identifiable']=None
        d['reportable_D']=None;d['candidate_theta']=candidates[case]
        d['epsilon_not_selected_to_get_desired_answer']=True;margin[case]=d
    result={'schema':'iscat146.calibration_margin.1','cases':margin,'local_attempts':attempts,
            'unknown_unsampled_intervals_remain':True,'all_witnesses':allpoints,
            'no_statistical_confidence_claim':True,'budget':ledger.summary()}
    save_json(out/'measurement_margin_summary.json',result)
    return result


def array_hash(a):
    from v146_core import array_sha
    return array_sha(a)


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--config',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    try:run(a.repo,read_json(a.config),a.out)
    except Exception as e:save_json(Path(a.out)/'blocked.json',{'status':'BLOCKED','error':repr(e)});return 2
    return 3
if __name__=='__main__':raise SystemExit(main())
