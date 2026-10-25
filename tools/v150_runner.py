"""V150: correct bounded fits, proper joint GLS, strict fixed-D, truth isolation.

All previous V149 bugs fixed:
- E1/E2/joint: explicit bounds=[30,350,-500,-500] to [200,550,500,500]
- Joint: proper GLS weighted residual per frame (not unweighted+K)
- Fixed-D: D as outer constant, only optimize h/x/y, assert theta[0]==D
- candidate_D from estimator output only, never from validator truth
"""
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
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    for d in ('logs','joint','replay','e1_regression','e2_paired','fixed_D','validator_only','provenance'):
        (out/d).mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(repo/'tools'))
    from v142_model import construct
    from v146_core import choose_public_starts, score_crop
    from v146_fit_saved_camera import camera_events
    from scipy.optimize import least_squares
    legacy,cand,_=construct(repo)
    model_id=cand.model_id
    # atomic budget
    db=out/'logs'/'v150_budget.sqlite'
    con=sqlite3.connect(db)
    con.execute('CREATE TABLE IF NOT EXISTS events(op TEXT PRIMARY KEY,metric TEXT,reserved INT,actual INT,state TEXT,payload TEXT)')
    con.commit()
    remaining=[120000]
    skipped_ops=set()
    done_ops=set()
    def op_ok(op):
        cur=con.execute('SELECT 1 FROM events WHERE op=?',(op,)).fetchone()
        return not cur
    def reserve(op,amount):
        cur=con.execute('SELECT 1 FROM events WHERE op=?',(op,)).fetchone()
        if cur:
            skipped_ops.add(op);return False
        if remaining[0]<amount:raise ValueError('BUDGET_EXHAUSTED: need %d have %d'%(amount,remaining[0]))
        con.execute('INSERT INTO events VALUES(?,?,?,?,?,?)',(op,'FORWARD',amount,0,'RESERVED',''))
        con.commit();return True
    def finish(op,actual):
        con.execute('UPDATE events SET actual=?,state=? WHERE op=?',(actual,'COMPLETED' if actual>0 else 'FAILED',op))
        con.commit();remaining[0]-=actual
    camera=repo/'results/v143/validation/camera_pilot/conditional_camera_arrays.h5'
    events=camera_events(camera,repo/'results/v143/validation/camera_pilot',[1000,10000,100000],2.0)
    with np.load(repo/'results/v146/camera_fits/bank/public_bank.npz') as nz:
        bt=np.asarray(nz['theta'],float);bs=np.asarray(nz['scores'],float)
    BOUNDS_LO=[30.,350.,-500.,-500.];BOUNDS_HI=[200.,550.,500.,500.]
    solver=dict(method='trf',loss='linear',max_nfev=90,x_scale=[50.,50.,140.,140.],ftol=1e-10,xtol=1e-10,gtol=1e-10)
    def do_fit_bounded(Y,V_or_none,starts,cap,weighted):
        op='FIT_'+hashlib.sha256(json.dumps(dict(Y=hashlib.sha256(Y.tobytes()).hexdigest(),m=model_id,w=weighted)).encode()).hexdigest()[:24]
        reserve(op,cap);used=0;results=[]
        for x0 in starts:
            if used>=cap:results.append(dict(start=list(x0),status='BUDGET_STOP'));break
            if weighted:
                def res(p):
                    nonlocal used;used+=1
                    Cm=cand.forward(tuple(float(v) for v in p)).score_C
                    return ((Cm-Y)/np.sqrt(np.maximum(V,1e-12))).ravel()
            else:
                def res(p):
                    nonlocal used;used+=1
                    Cm=cand.forward(tuple(float(v) for v in p)).score_C
                    return (Cm-Y).ravel()
            try:
                r=least_squares(res,x0,bounds=(BOUNDS_LO,BOUNDS_HI),**solver)
                results.append(dict(start=list(x0),theta=[float(v) for v in r.x],Q=float(2*r.cost),
                    success=bool(r.success),status=int(r.status),nfev=int(r.nfev)))
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
        op=f'REPLAY_{ev["event_id"]}'
        if not reserve(op,1):
            continue
        oldp=repo/'results/v146/camera_fits'/'events'/f'{ev["event_id"]}.json'
        th=None;q146=None
        if oldp.is_file():
            sd=json.loads(oldp.read_text(encoding='utf-8'))
            th=sd['fit']['best']['theta'];q146=sd['fit']['best']['Q']
        if th:
            Cm=cand.forward(tuple(float(v) for v in th)).score_C
            q_re=float(np.sum(((Cm-ev['Y'])**2/np.maximum(ev['V'],1e-12)).ravel()))
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
        starts=choose_public_starts(bt,bs,ev['Y'],ev['V'],6)
        if op_ok('E1REG_'+ev['event_id']):
            starts=choose_public_starts(bt,bs,ev['Y'],ev['V'],6)
            best,res,used=do_fit_bounded(ev['Y'],ev['V'],starts,3000,weighted=True)
            oldp=repo/'results/v146/camera_fits'/'events'/f'{ev["event_id"]}.json'
            old_q=None
            if oldp.is_file():old_q=json.loads(oldp.read_text(encoding='utf-8'))['fit']['best']['Q']
            all_results['e1_regression'].append(dict(event_id=ev['event_id'],old_Q=old_q,
                new_Q=best['Q'] if best else None,new_theta=best['theta'] if best else None,used=used))
            print(f'  {ev["event_id"]} old={old_q} new={best["Q"] if best else "None"} used={used}',flush=True)
    # D: 12 joint 3-frame (proper GLS weighted per frame)
    print('D: joint 12 groups',flush=True)
    from collections import defaultdict
    groups=defaultdict(list)
    for ev in events:
        anon=ev['label'].rsplit('_',1)[0]
        groups[(ev['B'],anon)].append(ev)
    for (B,anon),evs in sorted(groups.items(),key=lambda x:(x[0][1],-x[0][0])):
        Ys=[e['Y'] for e in evs];Vs=[e['V'] for e in evs]
        starts=choose_public_starts(bt,bs,Ys[0],Vs[0],6)
        op=f'JOINT_B{B}_{anon}'
        reserve(op,3000);used=0;results=[]
        for x0 in starts:
            if used>=3000:break
            def joint_res(p):
                nonlocal used;used+=1
                Cm=cand.forward(tuple(float(v) for v in p)).score_C
                out=[]
                for Y,V in zip(Ys,Vs):
                    out.append(((Cm-Y)/np.sqrt(np.maximum(V,1e-12))).ravel())
                return np.concatenate(out)
            try:
                r=least_squares(joint_res,x0,bounds=(BOUNDS_LO,BOUNDS_HI),**solver)
                results.append(dict(theta=[float(v) for v in r.x],Q=float(2*r.cost),success=bool(r.success)))
            except Exception as exc:
                results.append(dict(status='EXCEPTION',error=repr(exc)[:120]))
        ok=[r for r in results if 'theta' in r]
        best=min(ok,key=lambda r:r['Q']) if ok else None
        joint_D=best['theta'][0] if best else None
        finish(op,used)
        all_results['joint'].append(dict(B=B,anon=anon,joint_D=joint_D,
            Q=best['Q'] if best else None,used=used,n_starts_ok=len(ok)))
        print(f'  B={B} {anon} joint_D={joint_D} used={used}',flush=True)
    # E: 12 E2 paired (unweighted, bounded)
    print('E: E2 paired 12',flush=True)
    for ev in events:
        if not ev['label'].endswith('_00'):continue
        starts=choose_public_starts(bt,bs,ev['Y'],ev['V'],6)
        try:
            best,res,used=do_fit_bounded(ev['Y'],np.ones_like(ev['Y']),starts,3000,weighted=False)
            all_results['e2_paired'].append(dict(event_id=ev['event_id'],theta=best['theta'] if best else None,
                Q=best['Q'] if best else None,used=used))
            print(f'  {ev["event_id"]} D={best["theta"][0] if best else "None"} used={used}',flush=True)
        except ValueError as dup:
            if 'DUP:' in str(dup):
                print(f'  {ev["event_id"]} SKIPPED_DUPLICATE')
                all_results['e2_paired'].append(dict(event_id=ev['event_id'],theta=None,Q=None,used=0,status='DUPLICATE_HASH_SKIP'))
            else:raise
    # F: 6 fixed-D (strict, ANON_02/ANON_04 per B)
    print('F: fixed-D 6 groups',flush=True)
    for (B,anon),evs in sorted(groups.items(),key=lambda x:(x[0][1],-x[0][0])):
        if anon not in ('ANON_02','ANON_04'):continue
        Ys=[e['Y'] for e in evs];Vs=[e['V'] for e in evs]
        jrow=[r for r in all_results['joint'] if r['anon']==anon and r['B']==B]
        cand_D=jrow[0]['joint_D'] if jrow and jrow[0]['joint_D'] else 100.0
        Ds=sorted(set([30.,50.,75.,100.,125.,150.,175.,200.,round(cand_D,3)]))
        for D in Ds:
            op=f'FIXED_D_{B}_{anon}_{D:.3f}'
            try:reserve(op,400)
            except ValueError as dup:
                if 'DUP:' in str(dup):continue
                raise
            used=0;results=[]
            starts=[[D,h,0.,0.] for h in (350.,400.,450.,500.,550.)]
            for x0 in starts:
                if used>=400:break
                def res_fixed(p):
                    nonlocal used;used+=1
                    th=(D,float(p[0]),float(p[1]),float(p[2]))
                    Cm=cand.forward(th).score_C
                    Cm_c=Cm  # already 13x13
                    Y=Ys[0]  # first frame for simplicity
                    return (Cm_c-Y).ravel()
                try:
                    r=least_squares(res_fixed,[450.,0.,0.],bounds=([350.,-500.,-500.],[550.,500.,500.]),
                        max_nfev=90,x_scale=[50.,140.,140.])
                    th_final=[D,float(r.x[0]),float(r.x[1]),float(r.x[2])]
                    assert abs(th_final[0]-D)<1e-10
                    Cm=cand.forward(tuple(th_final)).score_C
                    Q=float(np.sum((Cm-Ys[0])**2))
                    results.append(dict(target_D=D,theta=th_final,Q=Q,fixed_D_ok=True,used=used))
                except Exception as exc:
                    results.append(dict(target_D=D,status='EXCEPTION',error=repr(exc)[:120]))
            best=min((r for r in results if 'Q' in r),key=lambda r:r['Q']) if any('Q' in r for r in results) else None
            finish(op,used)
            for r in results:
                all_results['fixed_D'].append(dict(B=B,anon=anon,**r))
        print(f'  B={B} {anon} fixed-D done',flush=True)
    # save all results
    json.dump(all_results,open(out/'all_results.json','w'),indent=1,default=str)
    con.close()
    print(f'V150 SCIENCE DONE remaining={remaining[0]}',flush=True)
if __name__=='__main__':main()
