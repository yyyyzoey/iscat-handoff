#!/usr/bin/env python3
"""Actually runnable profile coarsening on real F2c, with source-bound checkpoints.

A multi-start local nuisance profile is an UPPER BOUND on Qp(D), not a proven
global minimizer. Never reads N true diameters. Each fixed-D operation prepays
its worst-case callback budget and saves individual attempts/exit reasons.
"""
from __future__ import annotations
import argparse,hashlib,json,sys,time
from pathlib import Path
import h5py,numpy as np
from _shared import load_json,save_json,sha
from event_budget import Ledger,BudgetExceeded,DuplicateOperation


def signal_identity(a):
    x=np.ascontiguousarray(a)
    return hashlib.sha256((str(x.shape)+'|'+str(x.dtype)+'|').encode()+x.tobytes()).hexdigest()


def coarse_grid(cfg,D0,Ds):
    d=cfg['profiles']['coarse_D_nodes_nm'];return sorted(set([float(x) for x in d]+list(map(float,Ds))+[float(D0)]))


def choose_refine_grid(Dloss,epsilon,steps,source_knots=None):
    """Returns candidate midpoint D list (not a validated CI) in low-loss zones."""
    vals=sorted([(float(d),float(v)) for d,v in Dloss if v is not None])
    if len(vals)<2:return []
    lo=min(v for _,v in vals);threshold=lo+float(epsilon)
    good={d for d,v in vals if v<=threshold}
    keep=[]
    for i,((d,v),(e,w)) in enumerate(zip(vals,vals[1:])):
        if d in good or e in good or (v-threshold)*(w-threshold)<=0:
            mid=(d+e)/2
            if not any(abs(mid-p)<1e-8 for p,_ in vals):keep.append(mid)
    return sorted(set(keep))


def data_case(repo,cfg,case):
    if case in cfg['N_opened_scored_cases']:
        with h5py.File(repo/cfg['source_files']['N_anonymous_obs'],'r') as hf:
            Y=np.asarray(hf[case]['score_C'][()],dtype=float)
        import csv
        with (repo/cfg['source_files']['N_estimates']).open(encoding='utf-8',newline='') as src:
            candidates={r['anon_case']:r for r in csv.DictReader(src)}
        if case not in candidates:raise ValueError('ANONYMOUS_CASE_MISSING_FROM_ESTIMATOR_TABLE')
        cand=candidates[case]
        theta=[float(cand['candidate_D']),float(cand['fit_h']),float(cand['fit_x']),float(cand['fit_y'])]
        model_id=cand['source_model_id']
    elif case in cfg['M_opened_dev_cases']:
        with h5py.File(repo/cfg['source_files']['M_observation'],'r') as hf:
            Y=np.asarray(hf[case]['at_offset/C'][()],dtype=float)[2:15,2:15]
        fit=load_json(repo/cfg['source_files']['M_new_fits']/(case+'.json'))
        theta=list(map(float,fit['best']['theta']));model_id=fit['new_F2c_model_id']
    else:raise ValueError('UNKNOWN_ANONYMOUS_OR_DEVELOPMENT_CASE')
    if Y.shape!=(13,13) or not np.isfinite(Y).all() or model_id!=cfg['frozen_f2c_model_id']:
        raise ValueError('OBS_OR_F2C_MODEL_IDENTITY_NOT_QUALIFIED')
    return Y,theta,signal_identity(Y)


def local_D_fit(F,D,Y,joint,maxcalls,max_nfev,hseed):
    from scipy.optimize import least_squares
    used=[0]
    def predict(z):
        if used[0]>=maxcalls:raise RuntimeError('PRECHARGED_D_CALLBACKS_EXHAUSTED')
        used[0]+=1
        return F.forward([float(D),*map(float,z)]).score_C
    w=None
    if D==joint[0]:
        try:
            residual=predict(joint[1:])-Y
            w={'theta':joint,'loss_L2':float(np.linalg.norm(residual)),'source':'KNOWN_VALID_JOINT_THETA'}
        except Exception as e:w={'error':repr(e),'source':'EXACT_JOINT_WITNESS_FAILED'}
    xyc=joint[2:4]
    starts=[('JOINT_NUISANCE',joint[1:])]
    starts += [(f'PUBLIC_H_{int(h)}',[float(h),*xyc]) for h in hseed]
    # Avoid excessive re-runs at identical nuisance. Deterministic order.
    unique=[]
    for name,v in starts:
        if not any(np.allclose(v,w[1],rtol=0,atol=1e-11) for w in unique):unique.append((name,v))
    fits=[]
    for name,x0 in unique:
        try:
            def residual(z):return (predict(z)-Y).ravel()
            res=least_squares(residual,np.asarray(x0,dtype=float),bounds=([350.,-500.,-500.],[550.,500.,500.]),
                x_scale=[50.,140.,140.],method='trf',max_nfev=max_nfev,loss='linear')
            fits.append({'start':name,'theta':[D,*map(float,res.x)],'loss_L2':float(np.linalg.norm(res.fun)),
                'success':bool(res.success),'status':int(res.status),'nfev':int(res.nfev),'message':str(res.message)})
        except Exception as e:
            fits.append({'start':name,'success':False,'error':type(e).__name__+': '+str(e)})
            if used[0]>=maxcalls:break
    bests=[{'theta':f['theta'],'loss_L2':f['loss_L2'],'source':f['start']} for f in fits
           if f.get('success') and np.isfinite(f.get('loss_L2',float('inf')))]
    if w is not None and 'loss_L2' in w:bests.append(w)
    best=min(bests,key=lambda z:z['loss_L2']) if bests else None
    complete=bool(best and len(fits)==len(unique) and all(f.get('success') is True for f in fits))
    return {'D':D,'best':best,'attempts':fits,'exact_joint_witness':w,
         'point_search_complete':complete,'not_globally_certified':True,'forward_calls':used[0]}


def run(repo,output,cfg,cases,phase,per_D_budget,max_nfev,wall_seconds,attempt_revision=0):
    repo=Path(repo).resolve();dest=Path(output).resolve();dest.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(repo/'tools'))
    from v142_model import construct
    old,F2c,_=construct(repo,library_relative=cfg['source_files']['model_library'].as_posix()
        if hasattr(cfg['source_files']['model_library'],'as_posix') else cfg['source_files']['model_library'],
        expected_library_sha256=cfg['sha256_inputs']['library_h5'],
        expected_old_model_id=cfg['parent_f2_model_id'])
    if F2c.model_id!=cfg['frozen_f2c_model_id']:raise ValueError('F2C_MODEL_ID_NOT_FROZEN')
    lim=cfg['hard_budget_new_v143'];ledger=Ledger(repo/'results/v143/logs/v143_budget.sqlite',{
        'FORWARD':lim['total_oldF2_and_F2c_forward_queries'],'CAMERA':lim['new_camera_exposure_events'],
        'RENDER':0,'BEM':0})
    start_t=time.monotonic();processed=[]
    for case in cases:
        Y,theta,yhash=data_case(repo,cfg,case)
        obs_binding={'case':case,'model_id':F2c.model_id,'observation_sha':yhash,
              'estimator_source_sha256':sha(repo/cfg['source_files']['model']),
              'optimizer':'TRF_BOUNDED_LINEAR_V143_4PUBLIC_HEIGHTS','max_nfev':max_nfev,
              'phase':phase,'per_D_budget':per_D_budget}
        joint=list(map(float,theta));idb=hashlib.sha256(json.dumps(obs_binding,sort_keys=True).encode()).hexdigest()
        sub=dest/phase/case;sub.mkdir(parents=True,exist_ok=True)
        prior=None
        if phase=='coarse' and case in cfg['M_opened_dev_cases']:
            pp=repo/cfg['source_files']['M_coarse_profiles']/(case+'.json')
            if pp.is_file():
                prior=load_json(pp)
                if prior['model_id']!=F2c.model_id or prior.get('observation_sha256') is None:
                    raise ValueError('INHERITED_PROFILE_IDENTITY_MISSING')
                # Data-binding: the old observation_adapter.array_sha is used by V142;
                # if missing/unavailable, do NOT auto-reuse.
                from observation_adapter import array_sha
                if prior['observation_sha256']!=array_sha(Y):raise ValueError('INHERITED_PROFILE_OBS_CHANGED')
        if phase=='coarse':nodes=coarse_grid(cfg,joint[0],old.Ds)
        else:
            vv=[]
            # Read identity-verified COARSE checkpoints; refinement has its
            # own phase signature and must not overwrite coarse observations.
            source=dest/'coarse'/case
            srci=source/'input_identity.json'
            if not srci.is_file():raise ValueError('COARSE_PROFILE_IDENTITY_MISSING_FOR_REFINEMENT')
            identity=load_json(srci)
            for key in ('model_id','observation_sha','estimator_source_sha256'):
                if identity.get(key)!=obs_binding.get(key):raise ValueError('COARSE_REFINEMENT_INPUT_CHANGED:'+key)
            for name in sorted(source.glob('*.json')):
                if name.name in ('summary.json','input_identity.json'):continue
                q=load_json(name)
                rr=q.get('result',{});best=rr.get('best')
                if best and rr.get('point_search_complete') is True:
                    vv.append((rr['D'],best['loss_L2']))
            nodes=choose_refine_grid(vv,cfg['validation']['dev_model_error_max_HJKL_L2_unqualified'],
                                     cfg['profiles']['adaptive_step_nm'])
            if not vv:raise ValueError('NO_SCIENTIFICALLY_COMPLETE_COARSE_POINTS_TO_REFINE')
        save_json(sub/'input_identity.json',dict(**obs_binding,binding_hash=idb,truth_used=False))
        for D in nodes:
            if time.monotonic()-start_t>wall_seconds:
                processed.append({'case':case,'status':'WALL_LIMIT_REACHED__PARTIAL'});return processed
            key=f'PROFILE_{phase}_{case}_{D:.13f}_{idb[:16]}_revision{attempt_revision}'
            fname=sub/(f'{D:.13f}'.replace('.','p')+f'.a{attempt_revision}.json')
            # Reuse successful previous attempts; do not charge the same D twice
            # unless the user explicitly requests a revision for unfinished D.
            previous=[]
            for found in sub.glob(f'{D:.13f}'.replace('.','p')+'.a*.json'):
                q=load_json(found)
                if q.get('binding_hash')!=idb:raise ValueError('OLD_PROFILE_ATTEMPT_HAS_DIFFERENT_IDENTITY')
                if q.get('result',{}).get('point_search_complete') is True:
                    previous.append(found)
            if previous:continue
            if fname.is_file():
                oldrow=load_json(fname)
                if oldrow.get('binding_hash')!=idb or abs(oldrow['result']['D']-D)>1e-10:
                    raise ValueError('PROFILE_CHECKPOINT_IDENTITY_NOT_MATCHED')
                if oldrow.get('status')=='INHERITED_V142_VALID_POINT':continue
                if oldrow.get('event_key')==key and ledger.get(key) and ledger.get(key)['state']=='COMPLETED':continue
                raise ValueError('PROFILE_CHECKPOINT_UNRECONCILED_WITH_LEDGER')
            if prior is not None:
                valid=[x for x in prior['rows'] if abs(float(x['D'])-D)<1e-10 and x.get('point_search_complete') is True]
                if valid:
                    save_json(fname,{'binding_hash':idb,'event_key':None,'status':'INHERITED_V142_VALID_POINT',
                        'original_source_sha256':sha(pp),'result':{'D':D,'best':{'theta':valid[0]['theta'],
                        'loss_L2':valid[0]['loss_L2'],'source':'PREVIOUS_VERIFIED_F2C_POINT'},
                        'point_search_complete':True,'not_globally_certified':True}})
                    continue
            if ledger.get(key):raise ValueError('PROFILE_ALREADY_RESERVED_BUT_NO_VERIFIED_CHECKPOINT:'+key)
            try:ledger.reserve(key,'FORWARD',per_D_budget,dict(**obs_binding,D=D))
            except BudgetExceeded:
                processed.append({'case':case,'D':D,'status':'FORWARD_BUDGET_EXHAUSTED__PARTIAL'});return processed
            try:
                res=local_D_fit(F2c,D,Y,joint,per_D_budget,max_nfev,
                    cfg['profiles']['public_height_seeds_nm'])
                save_json(fname,{'binding_hash':idb,'event_key':key,
                      'status':'COMPLETED_NUMERICAL_ATTEMPT_NOT_GLOBAL_PROOF','result':res})
                ledger.finish(key,'COMPLETED',res['forward_calls'],{'complete':res['point_search_complete']})
            except Exception as e:
                # Failed operations remain charged; never re-run without reconciliation.
                ledger.finish(key,'FAILED',per_D_budget,{'exception':repr(e)})
                processed.append({'case':case,'D':D,'status':'FAILED_CHARGED','error':repr(e)})
        processed.append({'case':case,'status':'SCAN_CANDIDATE_SET_COMPLETED_NOT_SCIENTIFIC_CERTIFICATION'})
    return processed


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--config',default=None)
    p.add_argument('--out',required=True);p.add_argument('--phase',choices=['coarse','refine'],default='coarse')
    p.add_argument('--cases',nargs='+',required=True);p.add_argument('--per-D-budget',type=int,default=1000)
    p.add_argument('--max-nfev',type=int,default=35);p.add_argument('--max-wall-minutes',type=float,default=240)
    p.add_argument('--attempt-revision',type=int,default=0)
    a=p.parse_args();cfg=load_json(a.config or Path(__file__).resolve().parents[1]/'config/v143_science_config.json')
    try:
        if a.attempt_revision<0:raise ValueError('REVISION_MUST_BE_NONNEGATIVE')
        r=run(a.repo,a.out,cfg,a.cases,a.phase,a.per_D_budget,a.max_nfev,a.max_wall_minutes*60,a.attempt_revision)
        save_json(Path(a.out)/f'{a.phase}_batch_status.json',{'stage':'COMPLETED_OR_PARTIAL_NOT_FULL_SCIENCE_PASS','rows':r})
        print('PROFILE_STAGE_EXIT_3_MORE_SCIENCE_GATES_REQUIRED');return 3
    except Exception as e:
        save_json(Path(a.out)/f'{a.phase}_blocked.json',{'error':type(e).__name__+': '+str(e)})
        print('PROFILE_BLOCKED',repr(e),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
