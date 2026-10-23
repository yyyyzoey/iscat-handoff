"""V142 S5: blinded N inversion with the FROZEN F2c model.

The estimator opens ONLY results/v142/validation/new_N_independent_images.h5
(anonymous groups) and the frozen model. It never reads the truth registry,
the validator mapping, or any raw N filename. Multi-start bounded
least_squares over theta=[D,h,x,y] with public starts.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, sys
from pathlib import Path
import numpy as np
import h5py
sys.path.insert(0, str(Path(__file__).resolve().parent))
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--config',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    cfg=json.loads(Path(a.config).read_text(encoding='utf-8'))
    sys.path.insert(0,str(repo/'tools'))
    from v142_model import construct
    from scipy.optimize import least_squares
    legacy,cand,_=construct(repo,library_relative=cfg['inputs']['training_library'],
        expected_library_sha256=cfg['frozen_inputs']['training_library_sha256'],
        expected_old_model_id=cfg['frozen_parent']['F2_model_id'])
    h5=out/'validation'/'new_N_independent_images.h5'
    rows=[]
    with h5py.File(h5,'r') as f:
        for anon in sorted(f.keys()):
            C13=np.asarray(f[anon]['score_C'][()],float)
            # public starts: training-node coarse scan like fit_single, no truth
            obj={'calls':0}
            def res(p):
                obj['calls']+=1
                return (cand.forward(tuple(float(v) for v in p)).score_C-C13).ravel()
            # coarse public scan over library nodes for starts
            starts=[]
            for D in legacy.Ds:
                for h in legacy.Hs[::2]:
                    try:
                        loss=float(np.linalg.norm(cand.forward((float(D),float(h),0.,0.)).score_C-C13));obj['calls']+=1
                        starts.append((loss,[float(D),float(h),0.,0.]))
                    except Exception:pass
            starts.sort(key=lambda t:t[0])
            picks=[s[1] for s in starts[:4]]
            results=[]
            for x0 in picks:
                r=least_squares(res,x0,bounds=([30.,350.,-500.,-500.],[200.,550.,500.,500.]),
                    max_nfev=120,x_scale=[30.,40.,140.,140.])
                results.append(dict(theta=[float(v) for v in r.x],loss=float(np.linalg.norm(r.fun)),
                    success=bool(r.success),status=int(r.status),nfev=int(r.nfev)))
            best=min(results,key=lambda r:r['loss'])
            rows.append(dict(anon_case=anon,candidate_D=best['theta'][0],fit_h=best['theta'][1],
                fit_x=best['theta'][2],fit_y=best['theta'][3],loss_L2=best['loss'],
                nfev=best['nfev'],exit_status=best['status'],starts=len(results),
                all_starts=json.dumps(results),f2c_calls=obj['calls'],
                source_model_id=cand.model_id,
                observation_sha256=hashlib.sha256(C13.tobytes()).hexdigest()))
            print(anon,'D=%.3f h=%.2f loss=%.5f nfev=%d'%(best['theta'][0],best['theta'][1],best['loss'],best['nfev']),flush=True)
    with (out/'validation'/'new_N_candidate_estimates.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    total=sum(r['f2c_calls'] for r in rows)
    print('N_ESTIMATION_DONE calls=',total)
if __name__=='__main__':main()
