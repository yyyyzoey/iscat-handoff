"""W6: shared continuous-D multi-frame refit with public initialization only.

Per-frame nuisance seeds come from library-node template fits (public model,
observed frames only). Final answer is one joint fit with ONE continuous shared
D and per-frame h/x/y. Generator truth is never read.
"""
from __future__ import annotations
import argparse, csv, json, sys
from pathlib import Path
import numpy as np, h5py
sys.path.insert(0, str(Path(__file__).resolve().parent))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    from load_field_library import load_library
    from v133_recover_M import optical
    from fit_reference import solve_start,Objective
    cfg=json.loads((repo/'config/v133_science_config.json').read_text(encoding='utf-8'))
    v137=json.loads((repo/'config/v137_science_config.json').read_text(encoding='utf-8'))
    m=v137['inherited_model']
    model,_=load_library(repo/m['library'],kind='F2',optical=optical(cfg))
    h5=out/'raw_camera_data.h5'
    calls=[0]
    with h5py.File(h5,'r') as hf:
        traj_keys=sorted(k for k in hf['paths'])
        rows=[]
        for key in traj_keys:
            g=hf['paths/'+key]
            t=np.asarray(g['t']);D0=float(np.median(t))*0+55.0
            D0=float(hf['paths/'+key].attrs.get('D',55.0)) if 'D' in hf['paths/'+key].attrs else 55.0
            # observed frames
            Cfr={}
            for f in range(8):
                fg=np.asarray(hf[f'mot/{key}/frame{f}/fg'][()],float)
                R=np.asarray(hf[f'motref/{key}_100.0/refs'][()],float)
                Cest=fg/R.mean(axis=0)-1.0
                Cfr[f]=Cest[2:15,2:15]
            # per-frame public node initialization (free h,x,y at each library D)
            inits={};obj=None
            for f in range(8):
                obj=Objective(model,Cfr[f],total_limit=6000)
                best=None
                for D in model.Ds:
                    r=solve_start(obj,[D,450.,0.,0.],[1,2,3],per_start_calls=400,max_nfev=80)
                    calls[0]+=r['canonical_calls']
                    if r['success'] and r['loss'] is not None and (best is None or r['loss']<best['loss']):
                        best=r
                if best is None and obj.best is not None:
                    best=dict(theta=obj.best['theta'],loss=obj.best['loss'],success=False)
                inits[f]=best
            best_frame=min(inits,key=lambda f:inits[f]['loss'])
            D_init=float(inits[best_frame]['theta'][0])
            def resid(p):
                outv=[]
                for f in range(8):
                    o=model.forward((p[0],p[1+3*f],p[2+3*f],p[3+3*f]));calls[0]+=1
                    outv.append((o.score_C-Cfr[f]).ravel())
                return np.concatenate(outv)
            p0=[D_init]
            for f in range(8):
                th=inits[f]['theta'];p0+= [th[1],th[2],th[3]]
            lo=[30.]+[350.,-500.,-500.]*8;hi=[200.]+[550.,500.,500.]*8
            from scipy.optimize import least_squares
            rr=least_squares(resid,p0,bounds=(lo,hi),max_nfev=120,x_scale=[20.]+[25.,100.,100.]*8)
            ok=bool(rr.success);loss=float(np.linalg.norm(rr.fun))
            rms=loss/np.sqrt(8*169)
            init_total=float(np.sqrt(sum(inits[f]['loss']**2 for f in range(8))))
            reasons=[]
            if not ok:reasons.append('OPTIMIZER_NOT_CONVERGED')
            if not np.isfinite(loss):reasons.append('NONFINITE_LOSS')
            if abs(rr.x[0]-30.)<=0.05 or abs(rr.x[0]-200.)<=0.05:reasons.append('SHARED_D_AT_DOMAIN_BOUNDARY')
            if loss>0.9*init_total:reasons.append('NO_SIGNIFICANT_IMPROVEMENT_OVER_PUBLIC_INIT')
            reject=bool(reasons)
            rows.append(dict(traj=key,D_init_public=D_init,shared_D_fit=float(rr.x[0]),
                fit_success=ok,joint_loss_L2=loss,joint_rms=rms,fit_rejected=bool(reject),reject_reason_codes=reasons,init_total_loss_reference=init_total,
                per_frame_init_losses=json.dumps({str(f):inits[f]['loss'] for f in range(8)}),
                per_frame_theta=json.dumps({str(f):inits[f]['theta'] for f in range(8)}),
                joint_theta=json.dumps([float(v) for v in rr.x]),
                scope='SHARED_SURROGATE_METHOD_DIAGNOSTIC_NOT_NEW_DIRECT_PHYSICAL_BLIND'))
            print(key,'D_init=%.2f D_fit=%.3f loss=%.4f rms=%.5f ok=%s'%(D_init,rr.x[0],loss,rms,ok),flush=True)
    with (out/'motion_per_track.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)
    with (out/'shared_continuous_D.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['traj','D_init_public','shared_D_fit','fit_success','fit_rejected','joint_rms'])
        w.writeheader()
        for r in rows:w.writerow({k:r[k] for k in ['traj','D_init_public','shared_D_fit','fit_success','fit_rejected','joint_rms']})
    print('multiframe refit done, F2 calls=',calls[0])
if __name__=='__main__':main()
