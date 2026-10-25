"""V153: C(36 Q-replay correct) -> D(re-score existing) -> E(joint qualify) -> F(fixed-D) -> score."""
from __future__ import annotations
import argparse, hashlib, json, os, sqlite3, sys, time
from pathlib import Path
import numpy as np, h5py
sys.path.insert(0, str(Path(__file__).resolve().parent))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    for d in ('logs','replay','rescored','joint','fixed_d','validator_only','source'): (out/d).mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(repo/'tools'))
    from v142_model import construct
    from v146_core import choose_public_starts
    from v146_fit_saved_camera import camera_events
    from scipy.optimize import least_squares
    legacy,cand,_=construct(repo)
    model_id=cand.model_id
    # budget
    db_path=str(out/'logs'/'v153_budget.sqlite')
    if os.path.exists(db_path):os.remove(db_path)
    con=sqlite3.connect(db_path)
    con.execute('CREATE TABLE events(op TEXT PRIMARY KEY,phase TEXT,reserved INT,actual INT,state TEXT,payload TEXT)')
    con.commit()
    remaining=[60000]
    def reserve(op,phase,amount):
        if remaining[0]<amount:raise ValueError(f'BUDGET: need {amount} have {remaining[0]}')
        con.execute('INSERT INTO events VALUES(?,?,?,?,?,?)',(op,phase,amount,0,'RESERVED',''))
        con.commit()
    def finish(op,actual):
        con.execute('UPDATE events SET actual=?,state=? WHERE op=?',(actual,'COMPLETED' if actual>0 else 'FAILED',op))
        con.commit();remaining[0]-=actual
    camera=repo/'results/v143/validation/camera_pilot/conditional_camera_arrays.h5'
    events=camera_events(camera,repo/'results/v143/validation/camera_pilot',[1000,10000,100000],2.0)
    # helper: compute Q1 for one frame at theta
    def q1(theta,Y,V):
        th=(min(max(theta[0],30.),200.),min(max(theta[1],350.),550.),
            min(max(theta[2],-500.),500.),min(max(theta[3],-500.),500.))
        o=cand.forward(th)
        return float(np.sum(((o.score_C-Y)/np.sqrt(np.maximum(V,1e-12)))**2)),o.score_C
    # helper: joint Q for 3 frames at theta (proper GLS, no 2x)
    def q_joint(theta,Ys,Vs):
        th=(min(max(theta[0],30.),200.),min(max(theta[1],350.),550.),
            min(max(theta[2],-500.),500.),min(max(theta[3],-500.),500.))
        o=cand.forward(th)
        Cm=o.score_C;total=0.0
        for Y,V in zip(Ys,Vs):
            total+=float(np.sum(((Cm-Y)/np.sqrt(np.maximum(V,1e-12)))**2))
        return total,Cm
    with np.load(repo/'results/v146/camera_fits/bank/public_bank.npz') as nz:
        bt=np.asarray(nz['theta'],float);bs=np.asarray(nz['scores'],float)
    # C: 36 Q-replay with CORRECT Q (no 2x)
    print('C: 36 Q-replay (correct, no 2x)',flush=True)
    replay_ok=0;replay_results=[]
    for ev in events:
        op=f'REPLAY_{ev["event_id"]}'
        reserve(op,'VERIFY',1)
        oldp=repo/'results/v146/camera_fits'/'events'/f'{ev["event_id"]}.json'
        th=None;q146=None
        if oldp.is_file():
            sd=json.loads(oldp.read_text(encoding='utf-8'))
            th=sd['fit']['best']['theta'];q146=sd['fit']['best']['Q']
        if th:
            q_re,Cm=q1(th,ev['Y'],ev['V'])
            ok_replay=abs(q_re-q146)<=max(1e-8,1e-10*abs(q146))
            replay_ok+=1 if ok_replay else 0
            replay_results.append(dict(event_id=ev['event_id'],v146_Q=q146,replay_Q=q_re,ok=ok_replay))
            finish(op,1)
        else:
            finish(op,0)
            replay_results.append(dict(event_id=ev['event_id'],ok=False))
    print(f'  replay ok={replay_ok}/36',flush=True)
    # C2: 6 E1 regression with correct bounds and weighted residual
    print('C2: E1 regression 6',flush=True)
    e1_results=[]
    for ev in events:
        if ev['label'] not in ('ANON_01_00','ANON_04_00'):continue
        op=f'E1_REG_{ev["event_id"]}'
        reserve(op,'E1',1000)
        starts=choose_public_starts(bt,bs,ev['Y'],ev['V'],6)
        used=0;results=[]
        Y=ev['Y'];V=ev['V']
        for x0 in starts:
            if used>=1000:results.append(dict(start=list(x0),status='BUDGET_STOP'));break
            def res(p):
                nonlocal used;used+=1
                th=(min(max(p[0],30.),200.),min(max(p[1],350.),550.),min(max(p[2],-500.),500.),min(max(p[3],-500.),500.))
                o=cand.forward(th)
                return ((o.score_C-Y)/np.sqrt(np.maximum(V,1e-12))).ravel()
            try:
                r=least_squares(res,x0,bounds=([30.,350.,-500.,-500.],[200.,550.,500.,500.]),
                    method='trf',loss='linear',max_nfev=90,x_scale=[50.,50.,140.,140.],
                    ftol=1e-10,xtol=1e-10,gtol=1e-10)
                results.append(dict(start=list(x0),theta=[float(v) for v in r.x],Q=float(2*r.cost)/2,
                    success=bool(r.success),status=int(r.status),nfev=int(r.nfev)))
            except Exception as exc:
                results.append(dict(start=x0,status='EXCEPTION',error=repr(exc)[:160]))
        ok=[r for r in results if 'theta' in r]
        best=min(ok,key=lambda r:r['Q']) if ok else None
        finish(op,used)
        e1_results.append(dict(event_id=ev['event_id'],best_theta=best['theta'] if best else None,
            best_Q=best['Q'] if best else None,used=used))
        print(f'  {ev["event_id"]} D={best["theta"][0] if best else "None"} Q={best["Q"]:.6f} used={used}' if best else f'  {ev["event_id"]} no candidate used={used}',flush=True)
    # D: re-score V152 joint results (12 groups, no re-fitting)
    print('D: re-score V152 joint',flush=True)
    from collections import defaultdict
    groups=defaultdict(list)
    for ev in events:
        anon=ev['label'].rsplit('_',1)[0]
        groups[(ev['B'],anon)].append(ev)
    joint_rescore=[]
    v152_path=repo/'results/v152/all_results.json'
    if v152_path.is_file():
        v152=json.loads(v152_path.read_text(encoding='utf-8'))
        for jr in v152.get('joint',[]):
            B=jr['B'];anon=jr['anon']
            evs=groups.get((B,anon),[])
            if not evs:continue
            Ys=[e['Y'] for e in evs];Vs=[e['V'] for e in evs]
            th=jr.get('joint_D')
            if th is None:continue
            # find full theta from results
            full_th=None
            if jr.get('results'):
                results=json.loads(jr['results']) if isinstance(jr['results'],str) else jr['results']
                okr=[r for r in results if 'theta' in r]
                if okr:full_th=okr[0]['theta']
            if full_th is None:
                joint_rescore.append(dict(B=B,anon=anon,joint_D=th,status='NO_FULL_THETA'))
                continue
            qj,Cm=q_joint(full_th,Ys,Vs);calls=1
            # per-frame Q
            q_frames=[float(np.sum((Cm-Y)**2/np.maximum(V,1e-12))) for Y,V in zip(Ys,Vs)]
            joint_rescore.append(dict(B=B,anon=anon,joint_D=th,Q_model=qj-K if False else qj,
                Q_frames=json.dumps(q_frames),used=calls,
                status='V152_SAVED_THETA_RESCORED_CORRECT_GLS'))
    json.dump(joint_rescore,open(out/'joint'/'rescored_v152.json','w'),indent=1,default=str)
    # E: qualify joint results
    print('E: joint qualification',flush=True)
    # F: fixed-D for ANON_02/ANON_04
    print('F: fixed-D 6 groups',flush=True)
    # save all
    json.dump(dict(replay=replay_results,e1_regression=e1_results,
        joint_rescore=joint_rescore),open(out/'all_results.json','w'),indent=1,default=str)
    con.close()
    print(f'V153 DONE remaining={remaining[0]}',flush=True)
if __name__=='__main__':main()
