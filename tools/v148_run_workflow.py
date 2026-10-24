"""V148 workflow: W1 Q-replay, W2 three estimators x 36, W3 joint, fixed-D subset."""
from __future__ import annotations
import argparse, csv, hashlib, json, os, sys, time
from pathlib import Path
import numpy as np, h5py
sys.path.insert(0, str(Path(__file__).resolve().parent))
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--config',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
    cfg=json.loads(Path(a.config).read_text(encoding='utf-8'))
    sys.path.insert(0,str(repo/'tools'))
    from v142_model import construct
    from v148_ledger import Ledger
    from v148_engine import ForwardCounter,fit_event,joint_shared_sufficient,e1_plugin_gls_variance
    from scipy.optimize import least_squares
    legacy,cand,_=construct(repo)
    ledger=Ledger(out/'logs'/'v148_budget.sqlite',{'FORWARD':cfg['budget']['FORWARD']})
    camera=repo/cfg['inputs']['camera_h5']
    read_noise=cfg['read_noise_e']
    # load events (36)
    from v146_fit_saved_camera import camera_events
    events=camera_events(camera,repo/'results/v143/validation/camera_pilot',cfg['camera_levels'],read_noise)
    # public bank
    with np.load(repo/'results/v146/camera_fits/bank/public_bank.npz') as nz:
        bank_theta=np.asarray(nz['theta'],float);bank_scores=np.asarray(nz['scores'],float)
    results=dict(w1=[],w2=[],w3=[])
    # W1: Q-replay 36 (resume if already done)
    w1_results_path=out/'w1'/'q_replay_36.csv'
    if w1_results_path.is_file():
        import csv as _csv
        results['w1']=list(_csv.DictReader(w1_results_path.open(encoding='utf-8')))
        print('W1 resumed from existing results',flush=True)
    else:
      for ev in events:
        dpath=out/'w1'/'events';dpath.mkdir(parents=True,exist_ok=True)
        op=f'W1_QREPLAY_{ev["event_id"]}'
        try:
            ledger.reserve(op,'FORWARD',1,payload=dict(detail='W1 Q replay'))
        except Exception:
            ledger.finish(op,'COMPLETED',actual=1)
            saved=json.loads((repo/'results/v146/camera_fits'/'events'/f'{ev["event_id"]}.json').read_text(encoding='utf-8')) if (repo/'results/v146/camera_fits'/'events'/f'{ev["event_id"]}.json').is_file() else None
            if saved:
                Cm=cand.forward(tuple(float(v) for v in saved['fit']['best']['theta'])).score_C
                Q_re=float(np.sum(((Cm-ev['Y'])**2/np.maximum(ev['V'],1e-12)).ravel()))
                results['w1'].append(dict(event_id=ev['event_id'],v146_Q=saved['fit']['best']['Q'],replay_Q=Q_re,abs_diff=abs(Q_re-saved['fit']['best']['Q'])))
            continue
        saved=json.loads((repo/'results/v146/camera_fits'/'events'/f'{ev["event_id"]}.json').read_text(encoding='utf-8')) if (repo/'results/v146/camera_fits'/'events'/f'{ev["event_id"]}.json').is_file() else None
        th=saved['fit']['best']['theta'] if saved else None
        if th is None:
            ledger.finish(op,'NOT_EVALUATED',actual=0);continue
        Cm=cand.forward(tuple(float(v) for v in th)).score_C
        Q_re=float(np.sum(((Cm-ev['Y'])**2/np.maximum(ev['V'],1e-12)).ravel()))
        ledger.finish(op,'COMPLETED',actual=1)
        results['w1'].append(dict(event_id=ev['event_id'],v146_Q=saved['fit']['best']['Q'],replay_Q=Q_re,
            abs_diff=abs(Q_re-saved['fit']['best']['Q'])))
    # W1 gate check
    max_rel=max((r['abs_diff']/max(abs(r['v146_Q']),1e-12)) for r in results['w1']) if results['w1'] else 999
    w1_pass=max_rel<=1e-8
    print(f'W1: {len(results["w1"])} replays, max_rel_diff={max_rel:.2e}, gate={"PASS" if w1_pass else "FAIL"}',flush=True)
    if not w1_pass:
        print('W1_GATE_FAIL stops W2/W3',flush=True);json.dump(results,open(out/'partial_results.json','w'),indent=1);return
    # W2: 3 estimators x 36
    for ei,method in enumerate(cfg['estimators']):
        for ev in events:
            op=f'W2_{method}_{ev["event_id"]}'
            ledger.reserve(op,'FORWARD',cfg['per_event_cap'],payload=dict(event=ev['event_id'],method=method))
            fc=ForwardCounter(cand,cfg['budget']['FORWARD']-ledger.spent('FORWARD'),cfg['per_event_cap'],ledger,op)
            starts=ev.get('starts') or []
            if not starts:
                starts=[[float(t) for t in bank_theta[i]] for i in np.argsort([float(np.linalg.norm(bank_scores[k].ravel()-ev['Y'].ravel())) for k in range(len(bank_theta))])[:6]]
            records,best=fit_event(fc,ev['Y'],ev['V'],B_mean(ev['B']),method,starts,cfg['per_event_cap'],cfg['solver']['max_nfev'])
            actual=fc.task_used
            ledger.finish(op,'COMPLETED' if best else 'FAILED',actual=min(actual,cfg['per_event_cap']))
            results['w2'].append(dict(event_id=ev['event_id'],method=method,theta=best['theta'] if best else None,
                Q=best['Q'] if best else None,actual_forwards=actual,records=json.dumps(records)))
            print(f'W2 {method} {ev["event_id"]} D={best["theta"][0]:.2f} used={actual}' if best else f'W2 {method} {ev["event_id"]} FAILED',flush=True)
    # W3: joint 3-frame for 12 groups
    from collections import defaultdict
    groups=defaultdict(list)
    for ev in events:
        anon=ev['label'].rsplit('_',1)[0]
        groups[(ev['B'],anon)].append(ev)
    for (B,anon),evs in sorted(groups.items()):
        Ys=[e['Y'] for e in evs];Vs=[e['V'] for e in evs]
        Ybar,Vbar,K=joint_shared_sufficient(Ys,Vs)
        starts=[[float(t) for t in bank_theta[i]] for i in np.argsort([float(np.linalg.norm(bank_scores[k].ravel()-Ybar.ravel())) for k in range(len(bank_theta))])[:4]]
        for mode in ('JOINT_SHARED_D_H_X_Y','JOINT_PER_FRAME_HXY'):
            op=f'W3_{mode}_B{B}_{anon}'
            ledger.reserve(op,'FORWARD',cfg['joint_per_group_cap'],payload=dict(B=B,anon=anon,mode=mode))
            fc=ForwardCounter(cand,cfg['budget']['FORWARD']-ledger.spent('FORWARD'),cfg['joint_per_group_cap'],ledger,op)
            best=None;all_recs=[]
            for x0 in starts:
                if fc.task_used>=cfg['joint_per_group_cap']:break
                if mode=='JOINT_SHARED_D_H_X_Y':
                    def res(p):
                        o=fc.forward(p);Cm=o.score_C;out=[]
                        for Y,V in zip(Ys,Vs):out.append(((Cm-Y)/np.sqrt(np.maximum(V,1e-12))).ravel())
                        return np.concatenate(out)
                    lo=[30.,350.,-500.,-500.];hi=[200.,550.,500.,500.];p0=list(x0)
                else:
                    def res(p):
                        out=[]
                        for k,(Y,V) in enumerate(zip(Ys,Vs)):
                            th=(p[0],p[1+3*k],p[2+3*k],p[3+3*k])
                            o=fc.forward(th);Cm=o.score_C
                            out.append(((Cm-Y)/np.sqrt(np.maximum(V,1e-12))).ravel())
                        return np.concatenate(out)
                    lo=[30.]+[350.,-500.,-500.]*3;hi=[200.]+[550.,500.,500.]*3
                    p0=[x0[0]]+[x0[1],x0[2],x0[3]]*3
                try:
                    r=least_squares(res,p0,bounds=(lo,hi),max_nfev=90,x_scale=[30.,40.,140.,140.] if mode=='JOINT_SHARED_D_H_X_Y' else [30.]+[40.,140.,140.]*3)
                    rec=dict(theta=[float(v) for v in r.x],Q=float(2*r.cost),success=bool(r.success),nfev=int(r.nfev))
                    all_recs.append(rec)
                    if best is None or rec['Q']<best['Q']:best=rec
                except Exception:pass
            joint_D=best['theta'][0] if best and mode=='JOINT_SHARED_D_H_X_Y' else (best['theta'][0] if best else None)
            ledger.finish(op,'COMPLETED' if best else 'FAILED',actual=fc.task_used)
            results['w3'].append(dict(B=B,anon=anon,mode=mode,joint_D=joint_D,Q=best['Q'] if best else None,used=fc.task_used))
            print(f'W3 {mode} B{B} {anon} D={joint_D} used={fc.task_used}',flush=True)
    json.dump(results,open(out/'workflow_results.json','w'),indent=1,default=str)
    # budget summary
    con=sqlite3.connect(out/'logs'/'v148_budget.sqlite')
    fwd=con.execute("SELECT COUNT(*),COALESCE(SUM(units),0),COALESCE(SUM(actual),0) FROM events WHERE metric='FORWARD'").fetchone()
    con.close()
    print(f'V148 WORKFLOW DONE fwd_events={fwd[0]} reserved={fwd[1]} actual={fwd[2]}',flush=True)
def B_mean(B):return float(B)
if __name__=='__main__':main()