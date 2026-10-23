#!/usr/bin/env python3
"""Executable opened-M (DEVELOPMENT ONLY) old-F2 versus new F2-SpatialCubic fit.
Never imports simulator true diameters. The inherited old thetas are legitimate
DEVELOPMENT seeds, not admissible blinded seeds for new N cases.
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np,h5py
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from v142_model import construct
from v142_budget import Budget

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True);ap.add_argument('--config',required=True)
    ap.add_argument('--out',required=True);ap.add_argument('--max-nfev',type=int,default=75);a=ap.parse_args()
    root=Path(a.repo).resolve();dest=Path(a.out).resolve();dest.mkdir(parents=True,exist_ok=True)
    cfg=json.loads(Path(a.config).read_text(encoding='utf-8'))
    model=cfg['frozen_parent'];obs=root/cfg['inputs']['M_observation_h5'];source_sha=sha(obs)
    if source_sha!=cfg['frozen_inputs']['M_observation_sha256']:raise ValueError('M_OBSERVATION_CHANGED')
    sys.path.insert(0,str(root/'tools'))
    from observation_adapter import array_sha
    legacy,cand,checks=construct(root,library_relative=cfg['inputs']['training_library'],
        expected_library_sha256=cfg['frozen_inputs']['training_library_sha256'],
        expected_old_model_id=model['F2_model_id'])
    bindings={r['case']:r for r in json.loads((root/cfg['inputs']['M_observation_binding']).read_text(encoding='utf-8'))}
    budget=Budget(dest/'../logs/v142_budget.sqlite',cfg['budget_limits'])
    from scipy.optimize import least_squares
    fitrows=[]
    with h5py.File(obs,'r') as f:
        for name in cfg['opened_development_cases']:
            out=dest/f'{name}.json'
            Y=np.asarray(f[name]['at_offset/C'][()],dtype=float)[2:15,2:15]
            if array_sha(Y)!=bindings[name]['score_array_sha256']:raise ValueError('BOUND_OBSERVATION_SHA_MISMATCH:'+name)
            old=json.loads((root/cfg['inputs']['M_prior_fits']/f'M_{name}.json').read_text(encoding='utf-8'))
            if old.get('model_id')!=legacy.model_id:raise ValueError('INHERITED_OLD_FIT_MODEL_ID_MISMATCH')
            oldtheta=list(map(float,old['theta']));sig=hashlib.sha256(json.dumps(dict(case=name,oldtheta=oldtheta,Y_sha=array_sha(Y),new_model=cand.model_id,config_sha=sha(a.config)),sort_keys=True).encode()).hexdigest()
            if out.is_file():
                prior=json.loads(out.read_text(encoding='utf-8'))
                if prior.get('input_signature')!=sig:raise ValueError('NONIDENTICAL_RESUME:'+name)
                fitrows.append(prior);continue
            key=f'M_DEV_F2C_FIT_{name}_{sig[:10]}'
            budget.reserve(key,'FORWARD',2500,'candidate D/h/xy local search; reserve worst-case charged even if stopped')
            calls=[0]
            def forward(theta):
                if calls[0]>=2500:raise RuntimeError('PER_CASE_FORWARD_ALLOCATION_EXHAUSTED')
                calls[0]+=1
                return cand.forward(theta)
            try:
                if calls[0]>=2500:raise RuntimeError('PER_CASE_FORWARD_ALLOCATION_EXHAUSTED')
                calls[0]+=1
                oldloss=float(np.linalg.norm(legacy.forward(oldtheta).score_C-Y))  # old F2 forward counted in shared reservation
                initial_new=float(np.linalg.norm(forward(oldtheta).score_C-Y))
                seeds=[('INHERITED_DEV_THETA',oldtheta),('PUBLIC_CENTER',[100.,450.,0.,0.]),('PUBLIC_LARGE',[160.,500.,0.,0.])]
                trials=[]
                for tag,x0 in seeds:
                    def fun(theta):return (forward(theta).score_C-Y).ravel()
                    try:
                        result=least_squares(fun,np.asarray(x0,float),method='trf',
                            bounds=([30.,350.,-500.,-500.],[200.,550.,500.,500.]),
                            x_scale=[50.,50.,140.,140.],max_nfev=a.max_nfev,loss='linear',ftol=1e-9,xtol=1e-9,gtol=1e-9)
                        trials.append(dict(seed=tag,theta=result.x.tolist(),L2=float(np.linalg.norm(result.fun)),success=bool(result.success),
                            status=int(result.status),message=str(result.message),nfev=int(result.nfev)))
                    except Exception as e:
                        trials.append(dict(seed=tag,success=False,reason=repr(e)))
                        if calls[0]>=2500:break
                finite=[t for t in trials if t.get('success') and np.isfinite(t.get('L2',np.inf))]
                best=min(finite,key=lambda t:t['L2']) if finite else None
                row=dict(case=name,input_signature=sig,old_F2_model_id=legacy.model_id,new_F2c_model_id=cand.model_id,
                    observation_sha256=array_sha(Y),old_theta=oldtheta,old_F2_L2=oldloss,
                    new_F2c_at_old_theta_L2=initial_new,best=best,trials=trials,candidate_D=(best['theta'][0] if best else None),
                    reportable_D=None,profile_complete=False,model_qualified=False,
                    status='DEV_NUMERIC_ONLY_NO_PHYSICAL_MODEL_OR_PROFILE_CERTIFICATION')
                out.write_text(json.dumps(row,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
                budget.mark(key,'COMPLETED',actual_units=calls[0],note='developer opened M; stored all start outcomes')
                fitrows.append(row)
            except Exception as e:
                budget.mark(key,'FAILED',actual_units=calls[0],note=str(e))
                (dest/f'{name}.error.json').write_text(json.dumps(dict(error=repr(e),charged_calls=2500,actual_calls=calls[0]))+'\n')
                raise
    (dest/'summary.json').write_text(json.dumps(dict(new_model_id=cand.model_id,old_model_id=legacy.model_id,
        dev_cases=len(fitrows),candidate_results=[dict(case=r['case'],candidate_D=r['candidate_D'],reportable_D=None) for r in fitrows],
        boundary='DEVELOPMENT_ONLY__NOT_NEW_BLIND__NOT_SCIENTIFIC_PASS'),indent=2)+'\n')
    print('V142_DEV_FIT_COMPLETED_NOT_SCIENCE_PASS',len(fitrows),cand.model_id)
if __name__=='__main__':main()
