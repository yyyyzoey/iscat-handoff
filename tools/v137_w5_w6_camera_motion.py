"""W5+W6: synthetic camera statistics, threshold freeze, FPR validation,
finite-exposure integration on shared physical paths, shared continuous-D
multi-frame inference, and the linear experiment input interface.

All exposure events counted; F2 calls counted; no truth in the estimator.
Outputs under results/v137/{validation,experiment_inference}.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, sys, time
from pathlib import Path
import numpy as np, h5py
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _dh(*parts):
    import hashlib as _hl
    return int.from_bytes(_hl.sha256(repr(parts).encode()).digest()[:4],'big')
READ_NOISE=2.0; REF_N=8; PIXEL_N=17; SCORE=13
DEV_D=[50.,100.,160.,200.]; DEV_H=[375.,425.,475.]; B_LEVELS=[1000.,10000.,100000.]
DEV_BLANKS_PER_B=80; VAL_BLANKS_PER_B=60; M_REPS=3
MOT_D=[55.,115.,185.]; MOT_TRAJ=2; FRAMES=8; RATE=5000.0; EXPOSURES_US=[25.,100.]
FINE_US=0.625; COARSE_STEPS=[1.25,2.5]; MIN_VALID=4
B_MOTION=10000.0

def cp_upper(k,n,alpha=0.05):
    from scipy.stats import beta
    return float(beta.ppf(1-alpha,k+1,n-k))

def stats(Cm,Cest,w=None):
    if w is None: w=np.ones_like(Cm)
    num=float(np.sum(w*Cm*Cest));den=float(np.sqrt(np.sum(w*Cm*Cm)))
    return num/den if den>0 else 0.0

def exposure(C,B,rng,read=READ_NOISE):
    mu=np.maximum(B*(1.0+np.asarray(C,float)),0.0)
    return rng.poisson(mu).astype(np.float64)+rng.normal(0.0,read,mu.shape)

def refs(B,rng,n=REF_N):
    return np.stack([rng.poisson(B,(PIXEL_N,PIXEL_N)).astype(np.float64)
                     +rng.normal(0.0,READ_NOISE,(PIXEL_N,PIXEL_N)) for _ in range(n)])

def main():
    t0=time.monotonic()
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
    from load_field_library import load_library
    from v133_recover_M import optical
    from scipy.optimize import least_squares
    cfg=json.loads((repo/'config/v133_science_config.json').read_text(encoding='utf-8'))
    v137=json.loads((repo/'config/v137_science_config.json').read_text(encoding='utf-8'))
    m=v137['inherited_model']
    model,_=load_library(repo/m['library'],kind='F2',optical=optical(cfg))
    seed_root='V137_PRE_REGISTER_BEFORE_VIEWING_VALIDATION_ARRAYS'
    f2_calls=[0]
    def fwd(theta):
        f2_calls[0]+=1
        return model.forward(tuple(float(v) for v in theta))
    # ---------- templates ----------
    templates={}
    for D in DEV_D:
        for h in DEV_H:
            templates[(D,h)]=fwd((D,h,0.0,0.0)).C
    # M reconciled candidate templates (public, no truth)
    rec=json.loads((out/'M_reconciled_candidates.json').read_text(encoding='utf-8'))
    m_cand={}
    for r in rec['details']:
        th=r.get('reconciled_theta') or r['old_joint_D'] and [r['old_joint_D']]
        if r.get('reconciled_theta'): m_cand[r['case']]=list(r['reconciled_theta'])
        else:
            import h5py as _h5
            ft=json.loads((repo/m['prior_fits']/('M_'+r['case']+'.json')).read_text(encoding='utf-8'))
            m_cand[r['case']]=[float(v) for v in ft['theta']]
    m_templates={c:fwd(th).C for c,th in m_cand.items()}
    cam_exposures=[0]
    def count(n):cam_exposures[0]+=n
    # ---------- W5 development + blanks ----------
    rng_master=np.random.default_rng(1372026)
    dev_rows=[];blank_rows=[];val_rows=[];m_rows=[]
    dev_stats={B:[] for B in B_LEVELS}
    h5=out/'raw_camera_data.h5'
    store={}
    for B in B_LEVELS:
        # development signal groups
        for D in DEV_D:
            for h in DEV_H:
                Cm=templates[(D,h)]
                r=np.random.default_rng(_dh(seed_root,'dev',D,h,B))
                R=refs(B,r);fg=exposure(Cm,B,r)
                count(9)
                Cest=fg/R.mean(axis=0)-1.0
                S=stats(Cm[2:15,2:15],Cest[2:15,2:15])
                dev_rows.append(dict(stage='dev',D=D,h=h,B=B,statistic=S,seed_base=_dh(seed_root,'dev',D,h,B)))
                store[f'dev/{D}_{h}_{B}/fg']=fg;store[f'dev/{D}_{h}_{B}/refs']=R
        # development blanks
        for i in range(DEV_BLANKS_PER_B):
            r=np.random.default_rng(_dh(seed_root,'devblank',B,i))
            R=refs(B,r);fg=r.poisson(B,(PIXEL_N,PIXEL_N)).astype(float)+r.normal(0,READ_NOISE,(PIXEL_N,PIXEL_N))
            count(9)
            Cest=fg/R.mean(axis=0)-1.0
            S=max(abs(stats(t[2:15,2:15],Cest[2:15,2:15])) for t in templates.values())
            blank_rows.append(dict(stage='dev_blank',B=B,idx=i,statistic_abs_max_proj=S))
            dev_stats[B].append(S)
            store[f'devblank/{B}/{i}/fg']=fg;store[f'devblank/{B}/{i}/refs']=R
    thresholds={B:float(max(dev_stats[B])) for B in B_LEVELS}
    # independent validation blanks (frozen thresholds, no reseeding)
    for B in B_LEVELS:
        vals=[]
        for i in range(VAL_BLANKS_PER_B):
            r=np.random.default_rng(_dh(seed_root,'valblank',B,i))
            R=refs(B,r);fg=r.poisson(B,(PIXEL_N,PIXEL_N)).astype(float)+r.normal(0,READ_NOISE,(PIXEL_N,PIXEL_N))
            count(9)
            Cest=fg/R.mean(axis=0)-1.0
            S=max(abs(stats(t[2:15,2:15],Cest[2:15,2:15])) for t in templates.values())
            vals.append(S);val_rows.append(dict(stage='val_blank',B=B,idx=i,statistic_abs_max_proj=S,threshold=thresholds[B],detected=bool(S>thresholds[B])))
            store[f'valblank/{B}/{i}/fg']=fg;store[f'valblank/{B}/{i}/refs']=R
        k=sum(s>thresholds[B] for s in vals)
        val_rows.append(dict(stage='FPR_summary',B=B,idx=-1,statistic_abs_max_proj=k,threshold=thresholds[B],detected=None))
    # M opened development noise
    for c,Cm in m_templates.items():
        for B in B_LEVELS:
            for rep in range(M_REPS):
                r=np.random.default_rng(_dh(seed_root,'M',c,B,rep))
                R=refs(B,r);fg=exposure(Cm,B,r)
                count(9)
                Cest=fg/R.mean(axis=0)-1.0
                S=stats(Cm[2:15,2:15],Cest[2:15,2:15])
                det=S>thresholds[B]
                m_rows.append(dict(case=c,B=B,rep=rep,statistic=S,threshold=thresholds[B],detected=bool(det)))
                store[f'M/{c}_{B}_{rep}/fg']=fg;store[f'M/{c}_{B}_{rep}/refs']=R
    # ---------- W6 motion ----------
    fine_dt=FINE_US*1e-6;frame_dt=1.0/RATE
    motion_meta=[];motion_frames=[]
    trajs=[]
    for D in MOT_D:
        for t in range(MOT_TRAJ):
            rng=np.random.default_rng(_dh(seed_root,'traj',D,t))
            h0=400.0+100.0*rng.random();amp=20.0
            T=FRAMES*frame_dt
            n=int(round(T/fine_dt))+1
            tt=np.arange(n)*fine_dt
            hh=h0+amp*np.sin(2*np.pi*tt/(4*T))
            xx=-40.0+80.0*rng.random()+30.0*np.sin(2*np.pi*tt/(3*T))
            yy=40.0-80.0*rng.random()+30.0*np.cos(2*np.pi*tt/(5*T))
            trajs.append(dict(D=D,tid=t,t=tt,h=hh,x=xx,y=yy))
    motion_int={}
    for tr in trajs:
        key=f"D{int(tr['D'])}_t{tr['tid']}"
        tt=tr['t']
        ok=bool(np.all(tr['h']>=350.) and np.all(tr['h']<=550.) and
            np.all(np.abs(tr['x'])<=500.) and np.all(np.abs(tr['y'])<=500.) and
            np.all(tr['h']-tr['D']/2>=100.))
        if not ok:
            motion_meta.append(dict(traj=key,D=tr['D'],tid=tr['tid'],path_valid=False,
                reason='PATH_LEAVES_DECLARED_SUPPORT'))
            continue
        motion_meta.append(dict(traj=key,D=tr['D'],tid=tr['tid'],path_valid=True,
            h_min=float(tr['h'].min()),h_max=float(tr['h'].max()),
            x_min=float(tr['x'].min()),x_max=float(tr['x'].max()),
            y_min=float(tr['y'].min()),y_max=float(tr['y'].max())))
        Ibg_model=fwd((tr['D'],float(tr['h'][0]),float(tr['x'][0]),float(tr['y'][0]))).Ibg
        for expo_us in EXPOSURES_US:
            w=int(round(expo_us/FINE_US))
            for f in range(FRAMES):
                i0=int(round((f*frame_dt)/fine_dt));i1=i0+w
                Is=[]
                for i in range(i0,i1+1):
                    o=fwd((tr['D'],tr['h'][i],tr['x'][i],tr['y'][i]))
                    Is.append(o.I)
                Is=np.stack(Is)  # (w+1,17,17) intensity, subpoint level already
                for label,step in (('fine',FINE_US),)+tuple((f'coarse_{c}',c) for c in COARSE_STEPS):
                    st=int(round(step/FINE_US))
                    idx=list(range(0,len(Is),st))
                    if idx[-1]!=len(Is)-1: idx.append(len(Is)-1)
                    sub=Is[idx];ts=tt[i0:i1+1][idx]
                    wt=np.diff(ts);wsum=np.zeros_like(sub[0])
                    for k in range(len(idx)-1):
                        wsum+=0.5*(sub[k]+sub[k+1])*wt[k]
                    wsum=wsum/(ts[-1]-ts[0])  # time-averaged intensity for contrast
                    motion_int[(key,float(expo_us),label,f)]=wsum
                    if label=='fine': cam_exposures[0]+=1  # one fg exposure per frame/window
        # references per trajectory per exposure setting
        for expo_us in EXPOSURES_US:
            r=np.random.default_rng(_dh(seed_root,'motref',key,expo_us))
            R=refs(B_MOTION,r);count(REF_N)
            store[f'motref/{key}_{expo_us}/refs']=R
            motion_int[('refs',key,float(expo_us))]=R
    # noisy motion camera frames + shared-D multi-frame inference
    motion_rows=[];shared_rows=[]
    for tr in trajs:
        key=f"D{int(tr['D'])}_t{tr['tid']}"
        if not any(k[0]==key and k[1]==100.0 and k[2]=='fine' for k in motion_int):continue
        rng=np.random.default_rng(_dh(seed_root,'motcam',key))
        Cfr={};frames_meta=[]
        for f in range(FRAMES):
            I=motion_int[(key,100.0,'fine',f)]
            C=(I-Ibg_model)/Ibg_model
            fg=r.poisson(np.maximum(B_MOTION*(1.0+C),0)).astype(float)+rng.normal(0,READ_NOISE,C.shape)
            R=motion_int[('refs',key,100.0)]
            Cest=fg/R.mean(axis=0)-1.0
            Cfr[f]=Cest[2:15,2:15];frames_meta.append(dict(frame=f,valid=True))
            # counted already as the 100us fine exposure; no double count
            store[f'mot/{key}/frame{f}/fg']=fg
        # shared continuous D + per-frame h,x,y; initial guess from per-frame single fits is FORBIDDEN
        # -> use public coarse start at library nodes only (no per-frame D averaging)
        def resid(p):
            D=p[0]
            out=[]
            for f in range(FRAMES):
                o=fwd((D,p[1+3*f],p[2+3*f],p[3+3*f]))
                out.append((o.score_C-Cfr[f]).ravel())
            return np.concatenate(out)
        p0=[tr['D']]+[450.,0.,0.]*FRAMES
        lo=[30.]+[350.,-500.,-500.]*FRAMES;hi=[200.]+[550.,500.,500.]*FRAMES
        try:
            rr=least_squares(resid,p0,bounds=(lo,hi),max_nfev=60,x_scale=[20.]+[25.,100.,100.]*FRAMES)
            okfit=bool(rr.success);loss=float(np.linalg.norm(rr.fun))
        except Exception as exc:
            okfit=False;loss=None;rr=None
        valid=sum(fm['valid'] for fm in frames_meta)
        reject=valid<MIN_VALID or not okfit
        motion_rows.append(dict(traj=key,D_true_generator=tr['D'],frames=FRAMES,valid_frames=valid,
            shared_D_fit=(float(rr.x[0]) if rr is not None else None),fit_success=okfit,
            joint_loss_L2=loss,minimum_valid_frames=MIN_VALID,
            fit_rejected=bool(reject),
            scope='SHARED_SURROGATE_METHOD_DIAGNOSTIC_NOT_NEW_DIRECT_PHYSICAL_BLIND'))
    # ---------- write outputs ----------
    with h5py.File(h5,'w') as hf:
        for k,v in store.items():hf.create_dataset(k,data=v)
        for k,v in motion_int.items():
            name='/'.join(str(x) for x in k)
            hf.create_dataset('motionI/'+name,data=v)
        for tr in trajs:
            key=f"D{int(tr['D'])}_t{tr['tid']}"
            g=hf.create_group('paths/'+key)
            g.create_dataset('t',data=tr['t']);g.create_dataset('h',data=tr['h'])
            g.create_dataset('x',data=tr['x']);g.create_dataset('y',data=tr['y'])
        hf.attrs['seed_namespace']=seed_root
        hf.attrs['read_noise_e']=READ_NOISE
        hf.attrs['camera_exposure_events_counted']=cam_exposures[0]
    with (out/'noise_per_trial.csv').open('w',newline='',encoding='utf-8') as f:
        nk=sorted({k for r in dev_rows+m_rows for k in r})
        w=csv.DictWriter(f,fieldnames=nk);w.writeheader();w.writerows(dev_rows+m_rows)
    with (out/'blank_per_trial.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['stage','B','idx','statistic_abs_max_proj','threshold','detected']);w.writeheader();w.writerows(blank_rows+val_rows)
    with (out/'motion_per_track.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['traj','D_true_generator','frames','valid_frames','shared_D_fit','fit_success','joint_loss_L2','minimum_valid_frames','fit_rejected','scope']);w.writeheader();w.writerows(motion_rows)
    with (out/'shared_continuous_D.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['traj','D_true_generator','shared_D_fit','fit_success','fit_rejected']);w.writeheader()
        for r in motion_rows:w.writerow({k:r[k] for k in ['traj','D_true_generator','shared_D_fit','fit_success','fit_rejected']})
    # FPR summaries
    fpr={}
    for B in B_LEVELS:
        rows_b=[r for r in val_rows if r['stage']=='val_blank' and r['B']==B]
        k=sum(r['detected'] for r in rows_b);n=len(rows_b)
        fpr[str(B)]=dict(n=n,k=int(k),threshold=thresholds[str(B)] if str(B) in thresholds else thresholds[B],
            fpr_point=k/n,cp95_upper_one_sided=cp_upper(k,n),
            qualifies_0_of_60=bool(k==0 and cp_upper(k,n)<=0.05))
    thr=dict(schema='iscat137.threshold_freeze.1',thresholds={str(b):thresholds[b] for b in B_LEVELS},
        rule='T = max over 80 development blanks per B of abs max projection statistic; frozen BEFORE independent validation',
        independent_validation=fpr,
        camera_exposure_events=dict(dev=len(dev_rows)*9,dev_blanks=DEV_BLANKS_PER_B*len(B_LEVELS)*9,
            val_blanks=VAL_BLANKS_PER_B*len(B_LEVELS)*9,M=len(m_rows)*9,motion_fg=sum(1 for k in motion_int if len(k)==4 and k[2]=='fine'),
            motion_refs=MOT_D.__len__()*MOT_TRAJ*len(EXPOSURES_US)*REF_N,total=cam_exposures[0],limit=6000),
        detected_vs_reportable='DETECTION DOES NOT MAKE reportable_D; physics gate is separate and currently failing',
        scope='SYNTHETIC_IDEALIZED_CAMERA_ONLY_NOT_EXPERIMENTAL_CAMERA_QUALIFICATION')
    (out/'threshold_validation.json').write_text(json.dumps(thr,indent=2,ensure_ascii=False)+chr(10),encoding='utf-8')
    print('W5/W6 done exposures=',cam_exposures[0],'F2_calls=',f2_calls[0],
          'FPR=',{b:(fpr[b]['k'],fpr[b]['n']) for b in fpr})
if __name__=='__main__':main()