"""V144 C: targeted fixed-D nuisance refinement for planned cases.

Frozen F2c; atomic v144 ledger precharge per fixed-D; checkpoints written to
results/v144/profiles/<phase>/<case>/ in the V143-compatible format.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, sys
from pathlib import Path
import numpy as np
import h5py
sys.path.insert(0, str(Path(__file__).resolve().parent))
from event_budget import Ledger
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--config',required=True)
    ap.add_argument('--plan',required=True)
    ap.add_argument('--per-D-budget',type=int,default=1000)
    ap.add_argument('--max-nfev',type=int,default=35)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    plan=json.loads(Path(a.plan).read_text(encoding='utf-8'))
    sys.path.insert(0,str(repo/'tools'))
    from v142_model import construct
    from scipy.optimize import least_squares
    legacy,cand,_=construct(repo)
    # observation binding per case: use V143 profile identity where available, else N anon H5 sha
    obs_sha={}
    prof143=repo/'results/v143/profiles'
    for case in plan['cases']:
        p=prof143/'coarse'/case/'input_identity.json'
        if p.is_file():obs_sha[case]=json.loads(p.read_text(encoding='utf-8'))['observation_sha']
    anon_h5=repo/'results/v142/validation/new_N_independent_images.h5'
    with h5py.File(anon_h5,'r') as f:
        for i,anon in enumerate(sorted(f.keys()),1):
            case=f'ANON_{i:02d}'
            if case in plan['cases'] and case not in obs_sha:
                obs_sha[case]=hashlib.sha256(np.ascontiguousarray(np.asarray(f[anon]['score_C'][()])).tobytes()).hexdigest()
    msha=hashlib.sha256(open(repo/'tools/v142_model.py','rb').read()).hexdigest()
    estimator_sha=hashlib.sha256(open(__file__,'rb').read()).hexdigest()
    limits={'FORWARD':160000}
    ledger=Ledger(repo/'results/v144/logs/v144_budget.sqlite',limits)
    root=out/'profiles'
    total_fwd=0
    for case,spec in plan['cases'].items():
        targets=spec.get('target_D') or []
        if not targets:continue
        # observation Y
        if case.startswith('ANON'):
            i=int(case.split('_')[1])
            with h5py.File(anon_h5,'r') as f:Y=np.asarray(f[f'ANON_{i:02d}']['score_C'][()],float)
        else:
            with h5py.File(repo/'results/v132/validation/new_M_images.h5','r') as f:
                Y=np.asarray(f[case]['at_offset/C'][()],float)[2:15,2:15]
        identity=dict(case=case,model_id=cand.model_id,observation_sha=obs_sha.get(case,'UNKNOWN'),
            estimator_source_sha256=estimator_sha,optimizer='TRF_BOUNDED_LINEAR_V144_TARGETED',
            max_nfev=a.max_nfev,phase='refine_v144',per_D_budget=a.per_D_budget,truth_used=False)
        cdir=root/'refine_v144'/case;cdir.mkdir(parents=True,exist_ok=True)
        (cdir/'input_identity.json').write_text(json.dumps(identity,indent=1))
        binding=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
        # nearest neighbor witness for warm start (from v143 coarse)
        prev=None
        src=prof143/'coarse'/case
        if src.is_dir():prev=case
        for D in targets:
            op=f'V144_REFINE_{case}_{D:.4f}'
            existing=ledger.get(op)
            if existing is not None:
                # prior run reserved and completed the checkpoint before crashing at finish; finalize honestly
                cpts=list((cdir).glob('*.a1.json'))
                match=[c for c in cpts if abs(float(c.stem.split('.a1')[0])-D)<1e-6]
                if match:
                    doc=json.loads(open(match[0],encoding='utf-8').read())
                    if doc['status'].startswith('COMPLETED'):
                        ledger.finish(op,'COMPLETED',actual=doc['result']['forward_calls'])
                        print(case,'D=%.3f finalized from prior checkpoint (%d calls)'%(D,doc['result']['forward_calls']),flush=True)
                        continue
                ledger.finish(op,'FAILED',actual=0)
                continue
            ledger.reserve(op,'FORWARD',a.per_D_budget,payload=dict(case=case,D=D,binding=binding))
            starts=[]
            for h0 in (350.,400.,450.,500.,550.):
                starts.append([float(D),h0,0.,0.])
            # nearest v143 witness theta as additional start
            wp=prof143/'coarse'/case/(f'{D:.15g}'.rstrip('0').rstrip('.') if False else '')
            import glob
            cands=glob.glob(str(src/f'{D:.6f}*'))
            if cands:
                doc=json.loads(open(cands[0],encoding='utf-8').read())
                th=doc.get('result',{}).get('best',{}).get('theta')
                if th:starts.insert(0,list(th))
            best=None;attempts=[];used=0;complete=True
            for th in starts:
                if used>=a.per_D_budget:
                    attempts.append(dict(start=th,status='BUDGET_STOP'));complete=False;break
                def res(p):
                    nonlocal used
                    used+=1
                    return (cand.forward(tuple(float(v) for v in p)).score_C-Y).ravel()
                r=least_squares(res,th,bounds=([30.,350.,-500.,-500.],[200.,550.,500.,500.]),
                    max_nfev=a.max_nfev,x_scale=[30.,40.,140.,140.])
                rec=dict(start=th,theta=[float(v) for v in r.x],loss_L2=float(np.linalg.norm(r.fun)),
                    success=bool(r.success),status=int(r.status),nfev=int(r.nfev))
                attempts.append(rec)
                if best is None or rec['loss_L2']<best['loss_L2']:best=rec
                if not rec['success']:complete=False
            doc=dict(binding_hash=binding,event_key=op,status='COMPLETED_NUMERICAL_ATTEMPT_NOT_GLOBAL_PROOF',
                result=dict(D=float(D),best=dict(theta=best['theta'],loss_L2=best['loss_L2'],source='V144_TARGETED'),
                attempts=attempts,point_search_complete=bool(complete),not_globally_certified=True,
                forward_calls=used))
            (cdir/(f'{D:.15g}'.rstrip('0').rstrip('.')+'.a1.json')).write_text(json.dumps(doc,indent=1))
            ledger.finish(op,'COMPLETED',actual=used)
            total_fwd+=used
            print(case,'D=%.3f used=%d best=%.6e complete=%s'%(D,used,best['loss_L2'],complete),flush=True)
    print('V144_REFINE_DONE total_forwards=',total_fwd)
    ledger.close() if hasattr(ledger,'close') else None
if __name__=='__main__':main()
