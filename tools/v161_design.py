"""V161: 1224 design comparisons + 72 nonlinear probes using V156 real candidate Jacobians."""
from __future__ import annotations
import argparse, hashlib, json, os, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
SIGMAS=(1.,2.,5.,10.,20.,50.,100.)
RTOLS=(1e-8,1e-10,1e-12)
DELTAS=(-5.,-2.,-1.,-.5,.5,1.,2.,5.)
def local_design(jw, sigma_h, sigma_xy, rtol):
    j=np.asarray(jw,dtype=float)
    jD=j[:,0];A=j[:,1:]
    # No constraint
    if sigma_h==float('inf') and sigma_xy==float('inf'):
        b=np.zeros(3);total=float(np.sum(jD**2))
    else:
        # penalty matrix
        s=np.array([sigma_h if sigma_h!=float('inf') else 0,
                    sigma_xy if sigma_xy!=float('inf') else 0,
                    sigma_xy if sigma_xy!=float('inf') else 0])
        active=[k for k in range(3) if s[k]>0 and np.isfinite(s[k])]
        pen=np.zeros((3,len(active)))
        for k,col in enumerate(active):
            if np.isfinite(s[col]):pen[col,k]=1./s[col]
        aug=np.vstack([A,pen.T])
        target=-jD
        try:
            U,S,Vt=np.linalg.svd(aug,full_matrices=False)
            tol=max(aug.shape)*np.finfo(float).eps*S[0] if len(S)>0 else 0
            rank=sum(1 for s in S if s>tol)
            b=Vt[:rank].T@(np.diag(1/S[:rank])@(U.T[:rank]@target))
            residual=target-aug@b
            total=float(np.sum(residual**2))
        except Exception:
            b=np.zeros(3);total=float(np.sum(jD**2))
    return dict(total_coefficient=total,compensation=b.tolist(),
        nuisance_rank=rank if 'rank' in dir() else 0)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    for d in ('design','probes','logs'): (out/d).mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(repo/'tools'))
    from v142_model import construct
    legacy,cand,_=construct(repo)
    model_id=cand.model_id
    # Load V156 Jacobians
    jacobians={}
    for p in sorted((repo/'results/v156/joint').glob('*/result.json')):
        grp=p.parent.name
        d=json.loads(p.read_text(encoding='utf-8'))
        diag=d.get('diagnostic',{})
        jw=diag.get('whitened_J_fine')
        if jw and len(jw)==169 and len(jw[0])==4:
            jacobians[grp]=np.asarray(jw,dtype=float)
    print(f'Loaded {len(jacobians)} Jacobians',flush=True)
    # 1224 design comparisons (pure algebra, 0 F2c)
    designs={}
    for grp,jw in sorted(jacobians.items()):
        results=[]
        designs_list=[]
        designs_list.append(('free',float('inf'),float('inf')))
        designs_list.append(('exact_height',0.,float('inf')))
        designs_list.append(('exact_xy',float('inf'),0.))
        for s in SIGMAS:
            designs_list.append((f'height_{s}',s,float('inf')))
            designs_list.append((f'xy_{s}',float('inf'),s))
        for name,sh,sxy in designs_list:
            r=local_design(jw,sh,sxy,1e-10)
            results.append(dict(design=name,sigma_h=sh,sigma_xy=sxy,**r))
        designs[grp]=results
    json.dump(designs,open(out/'design'/'all_1224_designs.json','w'),indent=1,default=str)
    print(f'Design: {sum(len(v) for v in designs.values())} comparisons',flush=True)
    # 72 nonlinear probes (B=100000 only, ANON_02/03/04)
    probes=[]
    groups={}
    for grp in jacobians:
        if not grp.startswith('100000'):continue
        anon=grp.split('_')[1]
        groups.setdefault(anon,grp)
    probe_results=[]
    f2c_calls=0
    for anon,grp in sorted(groups.items()):
        jw=jacobians[grp]
        jD=jw[:,0];A=jw[:,1:]
        # joint theta from V156 results
        v156p=repo/'results/v156/joint'/grp/'result.json'
        if not v156p.is_file():continue
        d156=json.loads(v156p.read_text(encoding='utf-8'))
        theta=d156.get('theta') or d156.get('diagnostic',{}).get('theta')
        if not theta:continue
        theta=np.array(theta,dtype=float)
        # b from local_design with no constraint
        r_noaux=local_design(jw,float('inf'),float('inf'),1e-10)
        b=np.array(r_noaux.get('compensation',[0.,0.,0.]),dtype=float)
        direction=np.array([1.0,b[0],b[1],b[2]])
        Ybar_data=None
        # Load Y/V from camera events
        from v146_fit_saved_camera import camera_events
        camera=repo/'results/v143/validation/camera_pilot/conditional_camera_arrays.h5'
        evs=[e for e in camera_events(camera,repo/'results/v143/validation/camera_pilot',[100000],2.0) if e['label'].startswith(anon)]
        if not evs:continue
        Ys=[e['Y'] for e in evs];Vs=[e['V'] for e in evs]
        Ybar=np.mean(Ys,axis=0);Vbar=np.mean(Vs,axis=0)
        for t in DELTAS:
            th_new=theta+t*direction
            if th_new[0]<30 or th_new[0]>200:probe_results.append(dict(anon=anon,t=t,status='OUT_OF_DOMAIN_D'));continue
            if th_new[1]<350 or th_new[1]>550:probe_results.append(dict(anon=anon,t=t,status='OUT_OF_DOMAIN_H'));continue
            if any(abs(th_new[j])>500 for j in (2,3)):probe_results.append(dict(anon=anon,t=t,status='OUT_OF_DOMAIN_XY'));continue
            o=cand.forward(tuple(float(v) for v in th_new))
            Cm=o.score_C;f2c_calls+=1
            z=((Cm-Ybar)/np.sqrt(np.maximum(Vbar,1e-12))).ravel()
            z_lin=(jw@(t*direction)).ravel()
            rel_lin=float(np.linalg.norm(z-z_lin)/max(np.linalg.norm(z_lin),1e-12))
            Q=float(np.sum(z**2))
            probe_results.append(dict(anon=anon,t=float(t),theta=th_new.tolist(),Q=Q,
                rel_lin_error=rel_lin,linear_close=bool(rel_lin<=0.05)))
    json.dump(probe_results,open(out/'probes'/'nonlinear_probes.json','w'),indent=1,default=str)
    print(f'Probes: {len([p for p in probe_results if "Q" in p])} executed / {len(probe_results)} planned',flush=True)
    # Save budget
    budget=dict(f2c_calls=f2c_calls,limit=120000,bem=0,render=0,camera=0,
        design_comparisons=sum(len(v) for v in designs.values()),
        probes_executed=len([p for p in probe_results if 'Q' in p]),
        probes_planned=len(probe_results))
    json.dump(budget,open(out/'logs'/'budget_summary.json','w'),indent=1)
    print(f'V161 DONE f2c={f2c_calls} designs={sum(len(v) for v in designs.values())} probes={len(probe_results)}',flush=True)
if __name__=='__main__':main()
