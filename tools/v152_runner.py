"""V152: correct E1 bounded weighted fit, proper joint GLS, strict fixed-D."""
from __future__ import annotations
import argparse, hashlib, json, os, sqlite3, sys, time
from pathlib import Path
import numpy as np, h5py
sys.path.insert(0, str(Path(__file__).resolve().parent))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    for d in ('logs','replay','e1','joint','fixed_d','validator_only','source'): (out/d).mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(repo/'tools'))
    from v142_model import construct
    from v146_core import choose_public_starts
    from v146_fit_saved_camera import camera_events
    from scipy.optimize import least_squares
    legacy,cand,_=construct(repo)
    model_id=cand.model_id
    # simple but correct atomic budget
    db_path=str(out/'logs'/'v152_budget.sqlite')
    if os.path.exists(db_path):os.remove(db_path)
    con=sqlite3.connect(db_path)
    con.execute('CREATE TABLE events(op TEXT PRIMARY KEY, phase TEXT, reserved INT, actual INT, state TEXT)')
    con.execute("INSERT INTO events VALUES('GLOBAL','TOTAL',60000,0,'ACTIVE')")
    con.commit()
    def get_remaining():
        return con.execute("SELECT reserved-actual FROM events WHERE op='GLOBAL'").fetchone()[0]
    def reserve_and_track(op,phase,cap):
        rem=get_remaining()
        actual_cap=min(cap,rem)
        if actual_cap<=0:raise ValueError('BUDGET_EXHAUSTED')
        con.execute('INSERT INTO events VALUES(?,?,?,?,?)',(op,phase,actual_cap,0,'RESERVED'))
        con.commit()
        return actual_cap
    def finish(op,actual):
        con.execute('UPDATE events SET actual=?,state=? WHERE op=?',(actual,'COMPLETED' if actual>0 else 'FAILED',op))
        global_row=con.execute("SELECT actual FROM events WHERE op='GLOBAL'").fetchone()[0]
        con.execute("UPDATE events SET actual=? WHERE op='GLOBAL'",(global_row+actual,))
        con.commit()
    camera=repo/'results/v143/validation/camera_pilot/conditional_camera_arrays.h5'
    events=camera_events(camera,repo/'results/v143/validation/camera_pilot',[1000,10000,100000],2.0)
    with np.load(repo/'results/v146/camera_fits/bank/public_bank.npz') as nz:
        bt=np.asarray(nz['theta'],float);bs=np.asarray(nz['scores'],float)
    LO=[30.,350.,-500.,-500.];HI=[200.,550.,500.,500.]
    all_results=dict(replay=[],e1=[],joint=[],fixed_d=[])
    # C1: 36 Q-replay
    print('C1: Q-replay 36',flush=True)
    for ev in events:
        op=f'REPLAY_{ev["event_id"]}'
        cap=reserve_and_track(op,'VERIFY',1)
        oldp=repo/'results/v146/camera_fits'/'events'/f'{ev["event_id"]}.json'
        th=None;q146=None
        if oldp.is_file():
            sd=json.loads(oldp.read_text(encoding='utf-8'))
            th=sd['fit']['best']['theta'];q146=sd['fit']['best']['Q']
        if th:
            th_ok=(min(max(th[0],30.),200.),min(max(th[1],350.),550.),min(max(th[2],-500.),500.),min(max(th[3],-500.),500.))
            o=cand.forward(tuple(float(v) for v in th_ok))
            q_re=float(2*np.sum(((o.score_C-ev['Y'])/np.sqrt(np.maximum(ev['V'],1e-12)))**2))
            ok_replay=abs(q_re-q146)<=max(1e-8,1e-10*abs(q146))
            all_results['replay'].append(dict(event_id=ev['event_id'],v146_Q=q146,replay_Q=q_re,ok=ok_replay))
            finish(op,1)
        else:
            finish(op,0)
            all_results['replay'].append(dict(event_id=ev['event_id'],ok=False))
    n_ok=sum(1 for r in all_results['replay'] if r.get('ok'))
    print(f'  replay ok={n_ok}/36',flush=True)
    # C2: 6 E1 regression
    print('C2: E1 regression 6',flush=True)
    for ev in events:
        if ev['label'] not in ('ANON_01_00','ANON_04_00'):continue
        op=f'E1_REG_{ev["event_id"]}'
        cap=reserve_and_track(op,'E1',3000)
        starts=choose_public_starts(bt,bs,ev['Y'],ev['V'],6)
        used=0;results=[]
        Y=ev['Y'];V=ev['V']
        for x0 in starts:
            if used>=cap:results.append(dict(start=list(x0),status='BUDGET_STOP'));break
            def res(p):
                nonlocal used;used+=1
                th=(min(max(p[0],30.),200.),min(max(p[1],350.),550.),min(max(p[2],-500.),500.),min(max(p[3],-500.),500.))
                o=cand.forward(th)
                return ((o.score_C-Y)/np.sqrt(np.maximum(V,1e-12))).ravel()
            try:
                r=least_squares(res,x0,bounds=(LO,HI),method='trf',loss='linear',
                    max_nfev=90,x_scale=[50.,50.,140.,140.],ftol=1e-10,xtol=1e-10,gtol=1e-10)
                results.append(dict(start=list(x0),theta=[float(v) for v in r.x],Q=float(2*r.cost),
                    success=bool(r.success),status=int(r.status),nfev=int(r.nfev)))
            except Exception as exc:
                results.append(dict(start=x0,status='EXCEPTION',error=repr(exc)[:160]))
        ok=[r for r in results if 'theta' in r]
        best=min(ok,key=lambda r:r['Q']) if ok else None
        finish(op,used)
        all_results['e1'].append(dict(event_id=ev['event_id'],best_theta=best['theta'] if best else None,
            best_Q=best['Q'] if best else None,used=used))
        print(f'  {ev["event_id"]} D={best["theta"][0] if best else "None"} Q={best["Q"] if best else "None"} used={used}',flush=True)
    # D: 12 joint
    print('D: joint 12',flush=True)
    from collections import defaultdict
    groups=defaultdict(list)
    for ev in events:
        anon=ev['label'].rsplit('_',1)[0]
        groups[(ev['B'],anon)].append(ev)
    for (B,anon),evs in sorted(groups.items(),key=lambda x:(x[0][1],-x[0][0])):
        op=f'JOINT_B{B}_{anon}'
        cap=reserve_and_track(op,'JOINT',2000)
        Ys=[e['Y'] for e in evs];Vs=[e['V'] for e in evs]
        Yi=np.stack(Ys);Vi=np.stack(Vs)
        Vbar=1.0/np.sum(1.0/Vi,axis=0);Ybar=Vbar*np.sum(Yi/Vi,axis=0)
        K=float(np.sum((Yi-Ybar)**2/Vi))
        starts=choose_public_starts(bt,bs,Ybar,Vbar,6)
        used=0;results=[]
        for x0 in starts:
            if used>=cap:results.append(dict(start=list(x0),status='BUDGET_STOP'));break
            def res(p):
                nonlocal used;used+=1
                th=(min(max(p[0],30.),200.),min(max(p[1],350.),550.),min(max(p[2],-500.),500.),min(max(p[3],-500.),500.))
                o=cand.forward(th)
                Cm=o.score_C
                return ((Cm-Ybar)/np.sqrt(np.maximum(Vbar,1e-12))).ravel()
            try:
                r=least_squares(res,x0,bounds=(LO,HI),method='trf',loss='linear',
                    max_nfev=90,x_scale=[50.,50.,140.,140.],ftol=1e-10,xtol=1e-10,gtol=1e-10)
                Q_model=float(2*r.cost);Q_total=Q_model+K
                results.append(dict(start=list(x0),theta=[float(v) for v in r.x],Q_model=Q_model,
                    Q_total=Q_total,success=bool(r.success),status=int(r.status),nfev=int(r.nfev)))
            except Exception as exc:
                results.append(dict(start=x0,status='EXCEPTION',error=repr(exc)[:160]))
        ok=[r for r in results if 'theta' in r]
        best=min(ok,key=lambda r:r['Q_model']) if ok else None
        joint_D=best['theta'][0] if best else None
        finish(op,used)
        all_results['joint'].append(dict(B=B,anon=anon,joint_D=joint_D,
            Q_model=best['Q_model'] if best else None,Q_total=best['Q_total'] if best and best.get('Q_total') else None,
            constant_K=K,used=used,results=json.dumps(results)))
        print(f'  B={B} {anon} joint_D={joint_D} used={used}',flush=True)
    # F: fixed-D
    print('F: fixed-D',flush=True)
    for (B,anon),evs in sorted(groups.items(),key=lambda x:(x[0][1],-x[0][0])):
        if anon not in ('ANON_02','ANON_04'):continue
        Ys=[e['Y'] for e in evs];Vs=[e['V'] for e in evs]
        Yi=np.stack(Ys);Vi=np.stack(Vs)
        Vbar=1.0/np.sum(1.0/Vi,axis=0);Ybar=Vbar*np.sum(Yi/Vi,axis=0)
        jrow=[r for r in all_results['joint'] if r['anon']==anon and r['B']==B]
        cand_D=jrow[0]['joint_D'] if jrow and jrow[0]['joint_D'] else 100.0
        Ds=sorted(set([30.,50.,75.,100.,125.,150.,175.,200.,round(cand_D,3)]))
        for D in Ds:
            op=f'FIXED_D_B{B}_{anon}_{D:.3f}'
            cap=reserve_and_track(op,'FIXED_D',600)
            used=0;results=[]
            for h0 in (350.,400.,450.,500.,550.):
                if used>=cap:break
                def res3(p):
                    nonlocal used;used+=1
                    h=min(max(p[0],350.),550.)
                    x=min(max(p[1],-500.),500.);y=min(max(p[2],-500.),500.)
                    th=(D,h,x,y)
                    if th[1]-th[0]/2<100.:return np.full(169,1e6)
                    o=cand.forward(th)
                    Cm=o.score_C
                    return ((Cm-Ybar)/np.sqrt(np.maximum(Vbar,1e-12))).ravel()
                try:
                    r=least_squares(res3,[h0,0.,0.],bounds=([350.,-500.,-500.],[550.,500.,500.]),
                        method='trf',loss='linear',max_nfev=90,x_scale=[50.,140.,140.],ftol=1e-10,xtol=1e-10,gtol=1e-10)
                    th_final=(D,float(r.x[0]),float(r.x[1]),float(r.x[2]))
                    if abs(th_final[0]-D)>1e-10:
                        results.append(dict(target_D=D,status='FIXED_D_DRIFT'));continue
                    Cm=cand.forward(th_final).score_C
                    Q_model=float(np.sum(((Cm-Ybar)/np.sqrt(np.maximum(Vbar,1e-12)))**2))
                    results.append(dict(target_D=D,theta=list(th_final),Q_model=Q_model,fixed_D_ok=True,used=used))
                except Exception as exc:
                    results.append(dict(target_D=D,status='EXCEPTION',error=repr(exc)[:120]))
            ok=[r for r in results if 'Q_model' in r]
            best=min(ok,key=lambda r:r['Q_model']) if ok else None
            finish(op,used)
            for r in results:
                if 'fixed_D_ok' in r:all_results['fixed_d'].append(dict(B=B,anon=anon,**r))
            print(f'  B={B} {anon} D={D:.1f} Q={best["Q_model"] if best else "None"} used={used}',flush=True)
    json.dump(all_results,open(out/'all_results.json','w'),indent=1,default=str)
    con.close()
    final_rem=get_remaining() if False else 0
    print(f'V152 WORKFLOW DONE',flush=True)
if __name__=='__main__':main()
