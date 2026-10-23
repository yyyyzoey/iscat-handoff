#!/usr/bin/env python3
"""Resumable, conservative *starter* F2c D-profile for OPENED M developer set.
Every fixed D optimizes nuisance h/x/y from multiple public height seeds;
valid exact joint witness is explicitly inserted. This is a finite numerical
profile approximation, NOT proof of globally minimized Qp(D), noise CI, or
reportable experimental particle size.
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np,h5py
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from v142_model import construct
from v142_budget import Budget

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True);ap.add_argument('--config',required=True)
    ap.add_argument('--dev-fit-dir',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--per-case-allocation',type=int,default=45000);ap.add_argument('--max-nfev',type=int,default=55)
    a=ap.parse_args();root=Path(a.repo).resolve();cfg=json.loads(Path(a.config).read_text(encoding='utf-8'))
    out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
    fitdir=Path(a.dev_fit_dir).resolve()
    sys.path.insert(0,str(root/'tools'))
    from observation_adapter import array_sha
    from scipy.optimize import least_squares
    legacy,model,_=construct(root,library_relative=cfg['inputs']['training_library'],
        expected_library_sha256=cfg['frozen_inputs']['training_library_sha256'],
        expected_old_model_id=cfg['frozen_parent']['F2_model_id'])
    budget=Budget(out/'../logs/v142_budget.sqlite',cfg['budget_limits'])
    obs=root/cfg['inputs']['M_observation_h5']
    if sha(obs)!=cfg['frozen_inputs']['M_observation_sha256']:raise ValueError('OBS_SHA_CHANGED')
    slevel=sorted(set(float(d) for d in list(np.arange(30.,200.01,10.))+list(model.base.Ds)))
    with h5py.File(obs,'r') as h:
        for case in cfg['opened_development_cases']:
            fit=json.loads((fitdir/f'{case}.json').read_text(encoding='utf-8'))
            if fit['new_F2c_model_id']!=model.model_id or fit['best'] is None:raise ValueError('FIT_MISSING_OR_MODEL_ID_CHANGED:'+case)
            y=np.asarray(h[case]['at_offset/C'][()],float)[2:15,2:15]
            if array_sha(y)!=fit['observation_sha256']:raise ValueError('PROFILE_OBSERVATION_ID_CHANGED')
            joint=np.asarray(fit['best']['theta'],float);joint_d=float(joint[0]);grid=sorted(set(slevel+[joint_d]))
            path=out/f'{case}.json'
            sig=hashlib.sha256(json.dumps(dict(case=case,grid=grid,model_id=model.model_id,obs=fit['observation_sha256'],max_nfev=a.max_nfev),sort_keys=True).encode()).hexdigest()
            op=f'V142_PROFILE_{case}_{sig[:12]}'
            if path.exists():
                old=json.loads(path.read_text(encoding='utf-8'))
                if old['input_signature']!=sig or old['budget_op']!=op:raise ValueError('PROFILE_RESUME_DIFFERENT_ID:'+case)
                rows=old.get('rows',[])
                used=int(old.get('actual_forward_calls_so_far',-1));ev=budget.fetch(op)
                if ev is None or ev['metric']!='FORWARD' or ev['units']!=a.per_case_allocation or ev['actual_units']!=used or ev['state'] not in ('BLOCKED','COMPLETED'):
                    raise ValueError('PROFILE_RESUME_BUDGET_NOT_RECONCILED:'+case)
                if len(rows)==len(grid) and old.get('grid_coverage_complete') is True:continue
                if used>=a.per_case_allocation:continue
                if [r['D'] for r in rows]!=grid[:len(rows)]:raise ValueError('PROFILE_RESUME_NONPREFIX_CHECKPOINT:'+case)
            else:
                budget.reserve(op,'FORWARD',a.per_case_allocation,'full fixed D developer starter grid; all outcomes saved')
                rows=[];used=0
            calls=[used]
            def F(theta):
                if calls[0]>=a.per_case_allocation:raise RuntimeError('PROFILE_RESERVED_CALLS_EXHAUSTED')
                calls[0]+=1;return model.forward(theta).score_C
            try:
                for D in grid[len(rows):]:
                    if calls[0]>=a.per_case_allocation:break
                    seeds=[('JOINT_NUISANCE',list(joint[1:]))]
                    seeds += [(f'PUBLIC_H_{z:g}',[z,0.,0.]) for z in (350.,400.,450.,500.,550.)]
                    fits=[];reference=None
                    if D==joint_d:
                        reference=dict(theta=joint.tolist(),loss_L2=float(np.linalg.norm(F(joint)-y)),source='KNOWN_SAME_D_VALID_POINT')
                    for tag,nuisance in seeds:
                        x=np.asarray(nuisance,float)
                        try:
                            def f(z):return (F([D,z[0],z[1],z[2]])-y).ravel()
                            r=least_squares(f,x,method='trf',bounds=([350.,-500.,-500.],[550.,500.,500.]),
                                x_scale=[50.,140.,140.],max_nfev=a.max_nfev,loss='linear')
                            fits.append(dict(start=tag,theta=[D,*map(float,r.x)],loss_L2=float(np.linalg.norm(r.fun)),
                                success=bool(r.success),status=int(r.status),nfev=int(r.nfev)))
                        except Exception as exc:
                            fits.append(dict(start=tag,success=False,error=repr(exc)))
                            if calls[0]>=a.per_case_allocation:break
                    valid=[dict(theta=r['theta'],loss_L2=r['loss_L2'],source=r['start']) for r in fits if r.get('success')]
                    if reference is not None:valid.append(reference)
                    best=min(valid,key=lambda r:r['loss_L2']) if valid else None
                    row=dict(D=D,theta=best['theta'] if best else None,loss_L2=best['loss_L2'] if best else None,
                        witness_source=best['source'] if best else None,attempts=fits,
                        point_search_complete=bool(best is not None and all(s.get('success') is True for s in fits)),
                        exact_joint_witness=reference)
                    rows.append(row)
                    path.write_text(json.dumps(dict(case=case,input_signature=sig,budget_op=op,
                        model_id=model.model_id,observation_sha256=fit['observation_sha256'],
                        rows=rows,grid_coverage_complete=False,adaptive_coverage_complete=False,
                        profile_scientifically_complete=False,reportable_D=None,
                        charged_allocation=a.per_case_allocation,actual_forward_calls_so_far=calls[0],
                        note='NUMERIC_STARTER_PARTIAL_NOT_GLOBAL_PROFILE_AND_NOT_SIZING_PASS'),
                        indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
                old=json.loads(path.read_text(encoding='utf-8'))
                old['grid_coverage_complete']=len(rows)==len(grid) and all(r['point_search_complete'] for r in rows)
                old['actual_forward_calls_so_far']=calls[0]
                path.write_text(json.dumps(old,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
                budget.mark(op,'COMPLETED' if len(rows)==len(grid) else 'BLOCKED',actual_units=calls[0],
                    note='incomplete searches preserve unknown D, never high-loss substitute')
                print(case,'coarse_points',len(rows),'/',len(grid),'used',calls[0])
            except Exception as e:
                budget.mark(op,'FAILED',actual_units=calls[0],note=repr(e));raise
    print('V142_DEV_PROFILE_STARTER_DONE__NOT_UNIQUENESS_CERTIFICATION')
if __name__=='__main__':main()
