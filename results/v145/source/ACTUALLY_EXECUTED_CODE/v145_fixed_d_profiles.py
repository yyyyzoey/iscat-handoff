#!/usr/bin/env python3
"""Recalculate V144's invalid 4D refinements with D FIXED, optimizing (h,x,y).

Estimator is explicitly truth-blind. Supports SHA-bound checkpoints and a
persistent precharged FORWARD ledger. Finite evaluated witnesses may falsify
uniqueness; finite local searches never prove global uniqueness. No old V144
refinement result is used as fixed-D evidence.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,os,sys,time
from pathlib import Path
import numpy as np,h5py
from v145_budget import Ledger,BudgetLimit,DuplicateOperation

def sha_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()

def signal_hash(y):
    a=np.ascontiguousarray(np.asarray(y,dtype=np.float64))
    return hashlib.sha256((str(a.shape)+'|'+str(a.dtype)+'|').encode()+a.tobytes()).hexdigest()

def read_json(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def load_data_and_candidate(repo,cfg,case):
    if case.startswith('ANON_'):
        path=repo/cfg['N_observation']
        if sha_file(path)!=cfg['N_observation_sha256']:raise ValueError('N_H5_SHA_CHANGED')
        with h5py.File(path,'r') as h:y=np.asarray(h[case]['score_C'][()],dtype=np.float64)
        with (repo/cfg['N_candidates']).open(encoding='utf-8',newline='') as f:
            candidates={r['anon_case']:r for r in csv.DictReader(f)}
        if case not in candidates:raise ValueError('N_ESTIMATOR_CANDIDATE_NOT_FOUND')
        r=candidates[case]
        if r['source_model_id']!=cfg['inherited_model_id']:raise ValueError('N_ESTIMATOR_MODEL_NOT_FROZEN')
        theta=[float(r[k]) for k in ('candidate_D','fit_h','fit_x','fit_y')]
        if hashlib.sha256(np.ascontiguousarray(y).tobytes()).hexdigest()!=r['observation_sha256']:
            raise ValueError('N_ESTIMATOR_ANONYMOUS_OBSERVATION_CHANGED')
    elif case.startswith('M'):
        path=repo/cfg['M_observation']
        if sha_file(path)!=cfg['M_observation_sha256']:raise ValueError('M_H5_SHA_CHANGED')
        with h5py.File(path,'r') as h:y=np.asarray(h[case]['at_offset/C'][()],dtype=np.float64)[2:15,2:15].copy()
        fit=read_json(repo/cfg['M_candidates_dir']/(case+'.json'))
        if fit['new_F2c_model_id']!=cfg['inherited_model_id']:raise ValueError('M_CANDIDATE_MODEL_NOT_FROZEN')
        theta=list(map(float,fit['best']['theta']))
    else:raise ValueError('UNKNOWN_CASE')
    if y.shape!=(13,13) or not np.isfinite(y).all() or len(theta)!=4 or not all(math.isfinite(x) for x in theta):
        raise ValueError('NONFINITE_OR_WRONG_SHAPE')
    return y,theta,signal_hash(y)

def old_witnesses(repo,cfg,case,D,model_sha,observation_sha):
    """Only same-model, same-observation, truly fixed-D old V143 checkpoints."""
    base=repo/cfg['v143_profile_root'];out=[]
    for phase in ('coarse','refine'):
        d=base/phase/case
        if not d.is_dir():continue
        bind=d/'input_identity.json'
        if not bind.is_file():raise ValueError('MISSING_V143_INPUT_BINDING:'+case)
        ident=read_json(bind)
        if ident.get('model_id')!=cfg['inherited_model_id'] or ident.get('observation_sha')!=observation_sha or ident.get('estimator_source_sha256')!=model_sha:
            raise ValueError('V143_WITNESS_IDENTITY_MISMATCH:'+case)
        for p in d.glob('*.json'):
            if p.name in ('input_identity.json','summary.json'):continue
            doc=read_json(p);r=doc.get('result') or {};best=r.get('best')
            if not best:continue
            if abs(float(r['D'])-D)>1e-9:continue
            theta=best.get('theta')
            if not isinstance(theta,list) or len(theta)!=4 or abs(float(theta[0])-D)>1e-9:continue
            out.append(dict(theta=[float(x) for x in theta],source=p.relative_to(repo).as_posix(),
                original_recorded_loss=float(best['loss_L2'])))
    return out

def numerically_fit_D(F,D,y,theta,precharge,max_nfev,hseeds,previous=()):
    """Only 3D nuisance; D is an immutable closure constant throughout."""
    from scipy.optimize import least_squares
    calls=[0];attempts=[];candidates=[]
    def predict_nuisance(z):
        if calls[0]>=precharge:raise RuntimeError('PRECHARGED_CALLBACK_EXHAUSTED')
        calls[0]+=1
        z=np.asarray(z,dtype=float)
        if z.shape!=(3,) or not np.all(np.isfinite(z)):raise ValueError('NUISANCE_INVALID')
        return F.forward((D,float(z[0]),float(z[1]),float(z[2]))).score_C
    initial=[('PUBLIC_JOINT_NUISANCE',theta[1:])]
    initial +=[(f'PUBLIC_H_{h:g}',[h,theta[2],theta[3]]) for h in hseeds]
    initial +=[(f'CENTER_XY_H_{h:g}',[h,0.,0.]) for h in hseeds[1::2]]
    for w in previous:initial.append(('SAME_D_PRIOR_WITNESS',w['theta'][1:]))
    # Known union point: retain *only* when D exactly matches the estimated D.
    for w in previous:
        z=np.asarray(w['theta'][1:],float)
        try:
            loss=float(np.linalg.norm(predict_nuisance(z)-y))
            candidates.append(dict(theta=[D,*z.tolist()],loss_L2=loss,source='REPLAYED_V143_SAME_D_WITNESS'))
        except RuntimeError:break
    if D==theta[0]:
        try:
            v=float(np.linalg.norm(predict_nuisance(np.asarray(theta[1:],float))-y))
            candidates.append(dict(theta=[D,*theta[1:]],loss_L2=v,source='EXACT_INHERITED_JOINT_WITNESS'))
        except RuntimeError:pass
    full=True
    for source,x0 in initial:
        if calls[0]>=precharge:
            attempts.append(dict(start=source,success=False,status='BUDGET_STOP'));full=False;break
        z=np.asarray(x0,float)
        try:
            res=least_squares(lambda p:(predict_nuisance(p)-y).ravel(),z,method='trf',
                bounds=([350.,-500.,-500.],[550.,500.,500.]),x_scale=[50.,140.,140.],
                max_nfev=max_nfev,loss='linear',ftol=1e-10,xtol=1e-10,gtol=1e-10)
            theta_final=[D,*map(float,res.x)]
            # Even status=0 returns an attainable numerical witness, not an exclusion proof.
            loss=float(np.linalg.norm(res.fun))
            attempts.append(dict(start=source,theta=theta_final,loss_L2=loss,
                success=bool(res.success),status=int(res.status),nfev=int(res.nfev),message=str(res.message)))
            candidates.append(dict(theta=theta_final,loss_L2=loss,source=source,search_complete=bool(res.success)))
            if not res.success:full=False
        except Exception as exc:
            attempts.append(dict(start=source,success=False,error=repr(exc)));full=False
            if calls[0]>=precharge:break
    valid=[v for v in candidates if all(np.isfinite(v['theta'])) and math.isfinite(v['loss_L2']) and v['theta'][0]==D]
    best=min(valid,key=lambda v:v['loss_L2']) if valid else None
    return dict(fixed_D=D,best=best,valid_witnesses=valid,attempts=attempts,
                point_search_complete=bool(full and len(attempts)==len(initial) and best is not None),
                actual_f2c_callbacks=calls[0],profile_is_upper_bound_not_global_proof=True,
                every_saved_witness_obeys_fixed_D=all(v['theta'][0]==D for v in valid))

def run(repo,cfg,out,cases,max_wall_minutes,attempt_revision=0):
    repo=Path(repo).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    code=repo/cfg['model_source'];model_sha=sha_file(code)
    if model_sha!=cfg['model_expected_git_sha256']:raise ValueError('MODEL_SOURCE_SHA_CHANGED')
    sys.path.insert(0,str(repo/'tools'))
    from v142_model import construct
    _,model,_=construct(repo,library_relative=cfg['model_library'],
        expected_library_sha256=cfg['model_library_sha256'],expected_old_model_id='v131-field-db000d86636ed018cf1f9bd5291c7409b7e9d2aaa481328b3c22dfdb1a689427')
    if model.model_id!=cfg['inherited_model_id']:raise ValueError('FROZEN_F2C_MODEL_ID_MISMATCH')
    limits=cfg['budgets_new_v145']; ledger=Ledger(repo/'results/v145/logs/v145_budget.sqlite',{'FORWARD':limits['all_F2_plus_F2c_forward_calls'],'RENDER':limits['render_attempts_existing_solves_only'],'CAMERA':0,'BEM':0})
    begin=time.monotonic();res=[];per=cfg['fit']['per_D_precharge_calls'];max_nfev=cfg['fit']['max_nfev_per_start'];seeds=cfg['fit']['public_height_seeds_nm']
    for case in cases:
        if case not in cfg['priority_fixed_D_targets']:raise ValueError('CASE_NOT_PLANNED:'+case)
        y,theta,obs_sha=load_data_and_candidate(repo,cfg,case)
        for D in cfg['priority_fixed_D_targets'][case]:
            if time.monotonic()-begin>60*max_wall_minutes:
                res.append(dict(case=case,D=D,status='WALL_TIME_LIMIT_PARTIAL'));return res
            if not cfg['fit']['D_bounds_nm'][0]<=D<=cfg['fit']['D_bounds_nm'][1]:raise ValueError('D_OUTSIDE_FROZEN_SUPPORT')
            sig=hashlib.sha256(json.dumps(dict(case=case,D=float(D).hex(),model_id=model.model_id,obs_sha=obs_sha,source_sha=model_sha,
                max_nfev=max_nfev,per_D_budget=per,seeds=seeds),sort_keys=True).encode()).hexdigest()
            op=f'V145_FIXED_D_{case}_{sig[:20]}_r{attempt_revision}'
            cp=out/case/(f'D{float(D):.12f}'.replace('.','p')+f'_{sig[:10]}_r{attempt_revision}.json')
            cp.parent.mkdir(parents=True,exist_ok=True)
            ev=ledger.get(op)
            if ev and cp.exists():
                doc=read_json(cp)
                if doc.get('signature')!=sig or doc.get('event_key')!=op or not doc.get('result',{}).get('every_saved_witness_obeys_fixed_D'):
                    raise ValueError('CHECKPOINT_IDENTITY_OR_FIXED_D_INVALID:'+op)
                if ev['state']=='RESERVED':
                    ledger.finish(op,'COMPLETED',int(doc['result']['actual_f2c_callbacks']),{'recovered_checkpoint_after_crash':True})
                elif ev['state']!='COMPLETED':raise ValueError('FAILED_OP_CANNOT_AUTOMATICALLY_REUSE')
                res.append(dict(case=case,D=D,status='IDENTICAL_COMPLETED_CHECKPOINT_REUSED'))
                continue
            if ev and not cp.exists():
                res.append(dict(case=case,D=D,status='PRIOR_RESERVATION_HAS_NO_CHECKPOINT__RECONCILE_BEFORE_NEW_REVISION'))
                continue
            if cp.exists() and not ev:raise ValueError('UNBILLED_CHECKPOINT:'+str(cp))
            try:ledger.reserve(op,'FORWARD',per,dict(case=case,D=D,signature=sig))
            except BudgetLimit:
                res.append(dict(case=case,D=D,status='BUDGET_EXHAUSTED__PARTIAL'));return res
            try:
                prev=old_witnesses(repo,cfg,case,D,model_sha,obs_sha)
                r=numerically_fit_D(model,D,y,theta,per,max_nfev,seeds,prev)
                doc=dict(schema='iscat145.fixed_D.1',case=case,target_D=D,signature=sig,event_key=op,
                    model_id=model.model_id,model_source_sha256=model_sha,observation_sha256=obs_sha,
                    result=r,source_scope='ANON_OR_OPENED_DEV__TRUTH_NOT_LOADED',reportable_D=None)
                temp=cp.with_suffix('.tmp')
                temp.write_text(json.dumps(doc,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
                os.replace(temp,cp)
                ledger.finish(op,'COMPLETED',r['actual_f2c_callbacks'],{'point_search_complete':r['point_search_complete']})
                res.append(dict(case=case,D=D,status='FIXED_D_COMPLETED_OR_PARTIAL',best_loss=(r['best'] or {}).get('loss_L2'),
                    forward_calls=r['actual_f2c_callbacks'],point_search_complete=r['point_search_complete']))
            except Exception as e:
                # In case of a fatal runtime crash, reservation remains conservatively charged.
                if ledger.get(op)['state']=='RESERVED':
                    ledger.finish(op,'FAILED',per,{'reason':repr(e),'actual_unknown_charged_full':True})
                res.append(dict(case=case,D=D,status='FAILED_CHARGED',error=repr(e)))
    return res

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--config',required=True);p.add_argument('--out',required=True)
    p.add_argument('--cases',nargs='+',default=['ANON_03','ANON_04','M04','M06'])
    p.add_argument('--max-wall-minutes',type=float,default=240.);p.add_argument('--attempt-revision',type=int,default=0)
    a=p.parse_args();dest=Path(a.out);dest.mkdir(parents=True,exist_ok=True)
    try:
        if a.attempt_revision<0:raise ValueError('NEGATIVE_REVISION')
        cfg=read_json(a.config);result=run(a.repo,cfg,dest,a.cases,a.max_wall_minutes,a.attempt_revision)
    except Exception as e:
        (dest/'v145_fixedD_error.json').write_text(json.dumps(dict(status='BLOCKED',error=repr(e)),indent=2)+'\n')
        print('BLOCKED',repr(e));return 2
    (dest/'v145_fixedD_batch.json').write_text(json.dumps(dict(status='COMPONENT_ONLY_SCIENCE_NOT_CERTIFIED',rows=result),indent=2,ensure_ascii=False)+'\n')
    print('FIXED_D_COMPONENT_COMPLETED; FULL_CONTRACT_CONTINUES',len(result));return 3
if __name__=='__main__':raise SystemExit(main())
