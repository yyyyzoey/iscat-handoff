#!/usr/bin/env python3
"""Truth-blind local D/h/xy sensitivity diagnostic from frozen F2c.

No camera model, calibrated confidence, uniqueness claim, or actual
experimental precision is implied. Uses dimensionless chosen column scales.
"""
from __future__ import annotations
import argparse,json,sys,math
from pathlib import Path
import numpy as np
from v145_fixed_d_profiles import load_data_and_candidate,read_json,sha_file
from v145_budget import Ledger,BudgetLimit

def derivative(F,theta,j,step,bounds,count):
    x=np.array(theta,float);a,b=bounds
    if x[j]-step>=a and x[j]+step<=b:
        L=x.copy();L[j]-=step;R=x.copy();R[j]+=step;count[0]+=2
        return ((F.forward(R).score_C-F.forward(L).score_C)/(2*step)).ravel()
    elif x[j]+step<=b:
        R=x.copy();R[j]+=step;count[0]+=2
        return ((F.forward(R).score_C-F.forward(x).score_C)/step).ravel()
    elif x[j]-step>=a:
        L=x.copy();L[j]-=step;count[0]+=2
        return ((F.forward(x).score_C-F.forward(L).score_C)/step).ravel()
    raise ValueError('NO_FINITE_DIFFERENCE_SUPPORT')

def local_diagnostic(F,theta):
    count=[0];step=[.5,1.,5.,5.];scales=[10.,10.,50.,50.]
    bounds=[(30.,200.),(350.,550.),(-500.,500.),(-500.,500.)]
    jac=np.column_stack([derivative(F,theta,j,step[j],bounds[j],count)*scales[j] for j in range(4)])
    if not np.isfinite(jac).all():raise ValueError('JACOBIAN_NOT_FINITE')
    jd=jac[:,0];n=jac[:,1:];coefs=np.linalg.lstsq(n,jd,rcond=None)[0]
    effective=jd-n@coefs;s=np.linalg.svd(jac,compute_uv=False)
    return dict(numerical_forward_calls=count[0],scaled_unit_steps=dict(D_nm=10,h_nm=10,x_nm=50,y_nm=50),
        singular_values=s.tolist(),scaled_condition_number=float(s[0]/s[-1]) if s[-1]>0 else None,
        D_after_linear_nuisance_projection_L2=float(np.linalg.norm(effective)),
        D_before_projection_L2=float(np.linalg.norm(jd)),
        D_information_fraction_after_hxy_projection=float(np.linalg.norm(effective)/np.linalg.norm(jd)) if np.linalg.norm(jd)>0 else None,
        scientific_scope='LOCAL_LINEAR_UNWEIGHTED_FEASIBILITY_ONLY__NOT_GLOBAL_IDENTIFIABILITY_OR_PRECISION')

def main():
    a=argparse.ArgumentParser();a.add_argument('--repo',required=True);a.add_argument('--config',required=True)
    a.add_argument('--out',required=True);a.add_argument('--cases',nargs='+',default=['ANON_01','ANON_02','ANON_03','ANON_04','M04','M06']);ns=a.parse_args()
    repo=Path(ns.repo).resolve();cfg=read_json(ns.config)
    sys.path.insert(0,str(repo/'tools'))
    from v142_model import construct
    old,F2c,_=construct(repo,library_relative=cfg['model_library'],expected_library_sha256=cfg['model_library_sha256'],
       expected_old_model_id='v131-field-db000d86636ed018cf1f9bd5291c7409b7e9d2aaa481328b3c22dfdb1a689427')
    if F2c.model_id!=cfg['inherited_model_id']:raise ValueError('FROZEN_F2C_ID_CHANGED')
    limits=cfg['budgets_new_v145'];db=Ledger(repo/'results/v145/logs/v145_budget.sqlite',{'FORWARD':limits['all_F2_plus_F2c_forward_calls'],'RENDER':limits['render_attempts_existing_solves_only'],'CAMERA':0,'BEM':0})
    out=Path(ns.out);out.parent.mkdir(parents=True,exist_ok=True);results={}
    for case in ns.cases:
        y,theta,obs=load_data_and_candidate(repo,cfg,case)
        op='V145_INFORMATION_'+case+'_'+obs[:12]
        if db.get(op):raise ValueError('INFORMATION_ALREADY_RESERVED_OR_COMPLETE__NO_DOUBLE_CHARGING:'+op)
        db.reserve(op,'FORWARD',12,dict(case=case,obs_sha=obs,model_id=F2c.model_id))
        try:
            r=local_diagnostic(F2c,theta)
            db.finish(op,'COMPLETED',r['numerical_forward_calls'],{'case':case})
            results[case]=dict(candidate_theta_from_estimator=theta,observation_sha256=obs,**r)
        except Exception as exc:
            db.finish(op,'FAILED',12,{'error':repr(exc)});results[case]=dict(error=repr(exc),status='FAILED_CHARGED')
    out.write_text(json.dumps(dict(schema='iscat145.local_information.1',model_id=F2c.model_id,cases=results),indent=2,allow_nan=False)+'\n')
    print('LOCAL_INFORMATION_DIAGNOSTIC_ONLY');return 3
if __name__=='__main__':raise SystemExit(main())
