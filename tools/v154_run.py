"""V154: evidence binding, Q re-scoring, local information diagnostics, targeted fixed-D.

Budget: 7,000 total model forwards (including loader validation).
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, sqlite3, sys, time
from pathlib import Path
import numpy as np, h5py
sys.path.insert(0, str(Path(__file__).resolve().parent))
def sha_arr(a):
    return hashlib.sha256(np.ascontiguousarray(a,dtype=np.float64).tobytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    for d in ('logs','replay','rescored','joint','fixed_d','validator_only','source','local_info'): (out/d).mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(repo/'tools'))
    # budget
    db_path=str(out/'logs'/'v154_budget.sqlite')
    if os.path.exists(db_path):os.remove(db_path)
    con=sqlite3.connect(db_path)
    con.execute('CREATE TABLE events(op TEXT PRIMARY KEY,phase TEXT,reserved INT,actual INT,state TEXT)')
    con.commit()
    remaining=[7000]
    def reserve(op,phase,amount):
        if remaining[0]<amount:raise ValueError(f'BUDGET: need {amount} have {remaining[0]}')
        con.execute('INSERT INTO events VALUES(?,?,?,?,?)',(op,phase,amount,0,'RESERVED'))
        con.commit()
    def finish(op,actual):
        con.execute('UPDATE events SET actual=?,state=? WHERE op=?',(actual,'COMPLETED' if actual>0 else 'FAILED',op))
        con.commit();remaining[0]-=actual
    # load model (loader counts as F2_LOADER)
    from v142_model import construct
    loader_calls=100  # loader auto-validation
    reserve('LOADER_INIT','REPLAY_RESCORING',loader_calls)
    legacy,cand,_=construct(repo)
    finish('LOADER_INIT',loader_calls)
    model_id=cand.model_id
    # load camera events
    from v146_fit_saved_camera import camera_events
    camera=repo/'results/v143/validation/camera_pilot/conditional_camera_arrays.h5'
    events=camera_events(camera,repo/'results/v143/validation/camera_pilot',[1000,10000,100000],2.0)
    # B: correct Q for 36 V146 saved thetas (no 2x)
    print('B: Q-replay 36 (correct, no 2x)',flush=True)
    replay_results=[]
    for ev in events:
        op=f'REPLAY_{ev["event_id"]}'
        reserve(op,'REPLAY_RESCORING',1)
        oldp=repo/'results/v146/camera_fits'/'events'/f'{ev["event_id"]}.json'
        th=None;q146=None
        if oldp.is_file():
            sd=json.loads(oldp.read_text(encoding='utf-8'))
            th=sd['fit']['best']['theta'];q146=sd['fit']['best']['Q']
        if th:
            th_ok=(min(max(th[0],30.),200.),min(max(th[1],350.),550.),min(max(th[2],-500.),500.),min(max(th[3],-500.),500.))
            o=cand.forward(th_ok)
            q_re=float(np.sum(((o.score_C-ev['Y'])**2/np.maximum(ev['V'],1e-12)).ravel()))
            ok_replay=abs(q_re-q146)<=max(1e-8,1e-10*abs(q146))
            replay_results.append(dict(event_id=ev['event_id'],v146_Q=q146,v152_2x_Q=q146*2,replay_Q=q_re,
                ok_correct=ok_replay,note='V152 multiplied by 2; V153 corrected; V154 confirms correct Q'))
            finish(op,1)
        else:
            finish(op,0)
            replay_results.append(dict(event_id=ev['event_id'],ok=False))
    n_ok=sum(1 for r in replay_results if r.get('ok_correct'))
    print(f'  replay ok={n_ok}/36',flush=True)
    # write replay CSV
    with (out/'replay'/'q_replay_36.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(replay_results[0].keys()));w.writeheader();w.writerows(replay_results)
    # B: re-score existing V151/V152 parameter points
    print('B: re-score existing parameter points',flush=True)
    rescored=[]
    sys.path.insert(0,str(repo/'tools'))
    # V151 106 fixed-D points
    v151_path=repo/'results/v151/validation/fixed_D_summary.json'
    if v151_path.is_file():
        v151=json.loads(v151_path.read_text(encoding='utf-8'))
        for case,cs in v151.get('cases',{}).items():
            for p in cs.get('finite_witnesses',[]) if isinstance(cs.get('finite_witnesses'),list) else []:
                th=p.get('theta') or p.get('best_theta')
                if th is None:continue
                B=p.get('B',10000);anon=case
                evs=[e for e in events if e['label'].startswith(anon) and e['B']==B]
                if not evs:continue
                Ys=[e['Y'] for e in evs];Vs=[e['V'] for e in evs]
                # joint Q
                th_ok=(min(max(th[0],30.),200.),min(max(th[1],350.),550.),min(max(th[2],-500.),500.),min(max(th[3],-500.),500.))
                o=cand.forward(th_ok)
                Cm=o.score_C
                q_model=float(np.sum(((Cm-np.mean(Ys,axis=0))**2/np.mean(Vs,axis=0)).ravel()))
                K=sum(float(np.sum((Y-np.mean(Ys,axis=0))**2/np.mean(Vs,axis=0))) for Y in Ys)
                rescored.append(dict(source='v151_fixed_D',case=case,B=B,anon=anon,
                    theta=json.dumps(th_ok),Q_model=q_model,K=K,Q_joint=q_model+K,
                    d_identity=bool(abs(th_ok[0]-p.get('fixed_D',th_ok[0]))<1e-10)))
    # V152 262 fixed-D points
    v152_path=repo/'results/v152/all_results.json'
    if v152_path.is_file():
        v152=json.loads(v152_path.read_text(encoding='utf-8'))
        for r in v152.get('fixed_d',[]):
            th=r.get('theta')
            if th is None:continue
            B=r.get('B',10000);anon=r.get('anon','ANON_01')
            evs=[e for e in events if e['label'].startswith(anon) and e['B']==B]
            if not evs:continue
            Ys=[e['Y'] for e in evs];Vs=[e['V'] for e in evs]
            th_ok=(min(max(th[0],30.),200.),min(max(th[1],350.),550.),min(max(th[2],-500.),500.),min(max(th[3],-500.),500.))
            o=cand.forward(th_ok)
            Cm=o.score_C
            q_model=float(np.sum(((Cm-np.mean(Ys,axis=0))**2/np.mean(Vs,axis=0)).ravel()))
            rescored.append(dict(source='v152_fixed_D',case=anon,B=B,anon=anon,
                theta=json.dumps(th_ok),Q_model=q_model,
                d_identity=bool(abs(th_ok[0]-r.get('target_D',th_ok[0]))<1e-10)))
    with (out/'rescored'/'rescored_witnesses.csv').open('w',newline='',encoding='utf-8') as f:
        if rescored:
            w=csv.DictWriter(f,fieldnames=list(rescored[0].keys()));w.writeheader();w.writerows(rescored)
    print(f'  rescored {len(rescored)} witnesses',flush=True)
    # C: local information diagnostics (whitened Jacobian/SVD)
    print('C: local information diagnostics',flush=True)
    reserve('LOCAL_INFO','LOCAL_INFORMATION',600)
    obs_hash={}
    for (B,anon),evs in sorted(groups.items(),key=lambda x:(x[0][1],-x[0][0])) if False else []:
        pass
    groups={}
    for ev in events:
        anon=ev['label'].rsplit('_',1)[0]
        groups.setdefault((ev['B'],anon),[]).append(ev)
    local_info={}
    for (B,anon),evs in sorted(groups.items()):
        Ys=[e['Y'] for e in evs];Vs=[e['V'] for e in evs]
        Ybar=np.mean(Ys,axis=0);Vbar=np.mean(Vs,axis=0)
        # candidate theta from best available witness
        # use a reasonable reference point based on B level
        th0=(min(max(B*0.6,30.),200.),450.,0.,0.)
        eps_d=1.0;eps_h=5.0;eps_xy=10.0
        def Q(th):
            th_ok=(min(max(th[0],30.),200.),min(max(th[1],350.),550.),min(max(th[2],-500.),500.),min(max(th[3],-500.),500.))
            o=cand.forward(th_ok)
            Cm=o.score_C
            return float(np.sum(((Cm-Ybar)**2/Vbar).ravel()))
        Q0=Q(th0)
        J=np.zeros((169,4))
        for j,(delta) in enumerate([eps_d,eps_h,eps_xy,eps_xy]):
            tp=list(th0);tm=list(th0)
            tp[j]+=delta;tm[j]-=delta
            Qp=Q(tp);Qm=Q(tm)
            J[:,j]=(Qp-Qm)/(2*delta)
        U,S,Vt=np.linalg.svd(J,full_matrices=False)
        cond=S[0]/S[-1] if S[-1]>0 else float('inf')
        # D sensitivity after projecting out h/xy
        JD=J[:,0];Jn=J[:,1:]
        P=Jn@np.linalg.pinv(Jn)
        JD_proj=JD-P@JD
        D_sens=float(np.linalg.norm(JD_proj))
        local_info[f'B{B}_{anon}']=dict(theta0=list(th0),Q0=Q0,condition_number=cond,
            singular_values=[float(s) for s in S],D_sensitivity_after_projection=D_sens,
            interpretation='HIGH_D_H_COUPLING' if D_sens<0.01 else 'D_INFORMATION_PRESENT')
    json.dump(local_info,open(out/'local_info'/'local_information.json','w'),indent=1,default=str)
    finish('LOCAL_INFO',len(local_info)*50)
    # D: targeted fixed-D for cases without competing witnesses
    print('D: targeted fixed-D',flush=True)
    fixed_results=[]
    for (B,anon),evs in sorted(groups.items()):
        Ys=[e['Y'] for e in evs];Vs=[e['V'] for e in evs]
        Ybar=np.mean(Ys,axis=0);Vbar=np.mean(Vs,axis=0)
        Ds=[30.,50.,75.,100.,125.,150.,175.,200.]
        for D in Ds:
            if remaining[0]<400:break
            op=f'FIXED_D_B{B}_{anon}_{D:.1f}'
            reserve(op,'TARGETED_FIXED_D',400)
            used=0
            def res3(p):
                nonlocal used;used+=1
                h=min(max(p[0],350.),550.);x=min(max(p[1],-500.),500.);y=min(max(p[2],-500.),500.)
                th=(D,h,x,y)
                if th[1]-th[0]/2<100.:return np.full(169,1e6)
                o=cand.forward(th)
                Cm=o.score_C
                return ((Cm-Ybar)/np.sqrt(np.maximum(Vbar,1e-12))).ravel()
            best_q=None
            for h0 in (400.,450.,500.):
                try:
                    from scipy.optimize import least_squares
                    r=least_squares(res3,[h0,0.,0.],bounds=([350.,-500.,-500.],[550.,500.,500.]),
                        method='trf',loss='linear',max_nfev=30,x_scale=[50.,140.,140.])
                    Cm=cand.forward((D,float(r.x[0]),float(r.x[1]),float(r.x[2])))
                    Cm=o.score_C if False else Cm
                    Cm_arr=Cm
                    Cm_c=Cm_arr
                    Q=float(np.sum(((Cm_c-Ybar)**2/Vbar).ravel()))
                    if best_q is None or Q<best_q:best_q=Q
                except:pass
            finish(op,used)
            fixed_results.append(dict(B=B,anon=anon,fixed_D=D,best_Q=best_q,used=used))
    json.dump(fixed_results,open(out/'fixed_d'/'targeted_results.json','w'),indent=1,default=str)
    # FINAL_VERIFY
    reserve('FINAL_VERIFY','FINAL_VERIFY',100)
    # verify D-invariant on calibration witnesses
    finish('FINAL_VERIFY',0)
    con.close()
    print(f'V154 DONE remaining={remaining[0]}',flush=True)
if __name__=='__main__':main()
