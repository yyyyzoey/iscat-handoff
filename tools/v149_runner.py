"""V149: C(replay+E1 regression) -> D(joint 12 groups) -> E(12 E2) -> F(6 fixed-D) -> score."""
from __future__ import annotations
import argparse, csv, hashlib, json, os, sqlite3, sys, time
from pathlib import Path
import numpy as np, h5py
sys.path.insert(0, str(Path(__file__).resolve().parent))
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--config',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    cfg=json.loads(Path(a.config).read_text(encoding='utf-8'))
    sys.path.insert(0,str(repo/'tools'))
    from v142_model import construct
    from v146_core import choose_public_starts, ratio_contrast_and_variance, score_crop
    from v146_fit_saved_camera import camera_events
    from scipy.optimize import least_squares
    legacy,cand,_=construct(repo)
    model_id=cand.model_id
    # atomic budget
    db=out/'logs'/'v149_budget.sqlite'
    con=sqlite3.connect(db)
    con.execute('CREATE TABLE IF NOT EXISTS events(op TEXT PRIMARY KEY,metric TEXT,reserved INT,actual INT,state TEXT,payload TEXT)')
    remaining=[120000]
    def reserve(op,amount):
        cur=con.execute('SELECT 1 FROM events WHERE op=?',(op,)).fetchone()
        if cur:raise ValueError('DUP:'+op)
        if remaining[0]<amount:raise ValueError('BUDGET_EXHAUSTED')
        con.execute('INSERT INTO events VALUES(?,?,?,?,?,?)',(op,'FORWARD',amount,0,'RESERVED',''))
        con.commit()
    def finish(op,actual):
        con.execute('UPDATE events SET actual=?,state=? WHERE op=?',(actual,'COMPLETED' if actual>0 else 'FAILED',op))
        con.commit();remaining[0]-=actual
    camera=repo/'results/v143/validation/camera_pilot/conditional_camera_arrays.h5'
    events=camera_events(camera,repo/'results/v143/validation/camera_pilot',[1000,10000,100000],2.0)
    with np.load(repo/'results/v146/camera_fits/bank/public_bank.npz') as nz:
        bt=np.asarray(nz['theta'],float);bs=np.asarray(nz['scores'],float)
    solver=dict(method='trf',loss='linear',max_nfev=90,x_scale=[50.,50.,140.,140.],ftol=1e-10,xtol=1e-10,gtol=1e-10)
    def do_fit(Y,V,starts,cap):
        op='FIT_'+hashlib.sha256(json.dumps(dict(Y=hashlib.sha256(Y.tobytes()).hexdigest(),V=hashlib.sha256(V.tobytes()).hexdigest(),s=[list(s) for s in starts])).encode()).hexdigest()[:24]
        reserve(op,cap);used=0;results=[]
        for x0 in starts:
            if used>=cap:results.append(dict(start=x0,status='BUDGET_STOP'));break
            def res(p):
                nonlocal used
                used+=1
                return (cand.forward(tuple(float(v) for v in p)).score_C-Y).ravel()
            try:
                r=least_squares(res,x0,method='trf',loss='linear',max_nfev=90,x_scale=[50.,50.,140.,140.],ftol=1e-10,xtol=1e-10,gtol=1e-10)
                results.append(dict(start=list(x0),theta=[float(v) for v in r.x],Q=float(2*r.cost),success=bool(r.success),status=int(r.status),nfev=int(r.nfev)))
            except Exception as exc:
                results.append(dict(start=x0,status='EXCEPTION',error=repr(exc)[:160]))
        ok=[r for r in results if 'theta' in r]
        best=min(ok,key=lambda r:r['Q']) if ok else None
        finish(op,used)
        return best,results,used
    all_results=dict(replay=[],e1_regression=[],joint=[],e2_paired=[],fixed_D=[])
    # C1: 36 Q-replay
    print('C1: Q-replay 36',flush=True)
    for ev in events:
        reserve(f'REPLAY_{ev["event_id"]}',1)
        saved_p=repo/'results/v146/camera_fits'/'events'/f'{ev["event_id"]}.json'
        th=None;q146=None
        if saved_p.is_file():
            sd=json.loads(saved_p.read_text(encoding='utf-8'))
            th=sd['fit']['best']['theta'];q146=sd['fit']['best']['Q']
        if th:
            Cm=cand.forward(tuple(float(v) for v in th)).score_C
            q_re=float(np.sum(((Cm-ev['Y'])**2/np.maximum(ev['V'],1e-12)).ravel()))
            ok_replay=abs(q_re-q146)<=max(1e-8,1e-10*abs(q146))
            all_results['replay'].append(dict(event_id=ev['event_id'],v146_Q=q146,replay_Q=q_re,ok=ok_replay))
            finish(f'REPLAY_{ev["event_id"]}',1)
        else:
            finish(f'REPLAY_{ev["event_id"]}',0)
            all_results['replay'].append(dict(event_id=ev['event_id'],v146_Q=None,replay_Q=None,ok=False))
    n_ok=sum(1 for r in all_results['replay'] if r['ok'])
    print(f'  replay ok={n_ok}/36',flush=True)
    # C2: 6 E1 regression
    print('C2: E1 regression 6 events',flush=True)
    targets_e1=[e for e in events if e['label'] in ('ANON_01_00','ANON_04_00') ]
    for ev in targets_e1:
        starts=choose_public_starts(bt,bs,ev['Y'],ev['V'],6)
        best,res,used=do_fit(ev['Y'],ev['V'],starts,3000)
        old_q=None
        oldp=repo/'results/v146/camera_fits'/'events'/f'{ev["event_id"]}.json'
        if oldp.is_file():
            old_q=json.loads(oldp.read_text(encoding='utf-8'))['fit']['best']['Q']
        all_results['e1_regression'].append(dict(event_id=ev['event_id'],old_Q=old_q,new_Q=best['Q'] if best else None,
            new_theta=best['theta'] if best else None,used=used,results=json.dumps(res)))
        print(f'  {ev["event_id"]} old_Q={old_q} new_Q={best["Q"] if best else "None"} used={used}',flush=True)
    # D: 12 joint 3-frame
    print('D: joint 12 groups',flush=True)
    from collections import defaultdict
    groups=defaultdict(list)
    for ev in events:
        anon=ev['label'].rsplit('_',1)[0]
        groups[(ev['B'],anon)].append(ev)
    for (B,anon),evs in sorted(groups.items(),key=lambda x:(x[0][1],-x[0][0])):
        Ys=[e['Y'] for e in evs];Vs=[e['V'] for e in evs]
        Yi=np.stack(Ys);Vi=np.stack(Vs)
        Vbar=1.0/np.sum(1.0/Vi,axis=0);Ybar=Vbar*np.sum(Yi/Vi,axis=0)
        K=float(np.sum((Yi-Ybar)**2/Vi))
        starts=choose_public_starts(bt,bs,Ybar,Vbar,6)
        best,res,used=do_fit(Ybar,Vbar,starts,3000)
        joint_D=best['theta'][0] if best else None
        Q_total=(best['Q']+K) if best and best['Q'] is not None else None
        single_ds=[r['fit']['candidate_D'] for r in [] ]
        all_results['joint'].append(dict(B=B,anon=anon,joint_D=joint_D,Q_joint=Q_total,K=K,used=used,
            results=json.dumps(res),single_ds='from_v146_published'))
        print(f'  B={B} {anon} joint_D={joint_D} used={used}',flush=True)
    # E: 12 E2 paired (unweighted)
    print('E: E2 paired 12',flush=True)
    e2_targets=[e for e in events if e['label'].endswith('_00')]
    for ev in e2_targets:
        starts=choose_public_starts(bt,bs,ev['Y'],ev['V'],6)
        best,res,used=do_fit(ev['Y'],np.ones_like(ev['Y']),starts,3000)
        all_results['e2_paired'].append(dict(event_id=ev['event_id'],theta=best['theta'] if best else None,
            Q_unweighted=best['Q'] if best else None,used=used))
        print(f'  {ev["event_id"]} D={best["theta"][0] if best else "None"} used={used}',flush=True)
    # F: 6 fixed-D profiles (ANON_02, ANON_04 per B)
    print('F: fixed-D 6 groups',flush=True)
    for (B,anon),evs in sorted(groups.items(),key=lambda x:(x[0][1],-x[0][0])):
        if anon not in ('ANON_02','ANON_04'):continue
        Ys=[e['Y'] for e in evs];Vs=[e['V'] for e in evs]
        Yi=np.stack(Ys);Vi=np.stack(Vs)
        Vbar=1.0/np.sum(1.0/Vi,axis=0);Ybar=Vbar*np.sum(Yi/Vi,axis=0)
        jrow=[r for r in all_results['joint'] if r['anon']==anon and r['B']==B]
        cand_D=jrow[0]['joint_D'] if jrow and jrow[0]['joint_D'] else 100.0
        Ds=sorted(set([30.,50.,75.,100.,125.,150.,175.,200.,round(cand_D,3)]))
        for D in Ds:
            starts=[[D,350.,0.,0.],[D,400.,0.,0.],[D,450.,0.,0.],[D,500.,0.,0.]]
            best,res,used=do_fit(Ybar,Vbar,starts,400)
            th=best['theta'] if best else None
            all_results['fixed_D'].append(dict(B=B,anon=anon,fixed_D=D,
                theta=th,loss=best['Q'] if best else None,used=used,
                d_identity_ok=bool(th and abs(th[0]-D)<1e-10)))
        print(f'  B={B} {anon} fixed-D done',flush=True)
    # write all results
    for key,data in all_results.items():
        p=out/f'{key}.json'
        p.write_text(json.dumps(data,indent=1,default=str),encoding='utf-8')
    con.close()
    print(f'V149 SCIENCE DONE total_remaining={remaining[0]}',flush=True)
if __name__=='__main__':main()
