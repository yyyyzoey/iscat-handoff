"""V147 W1-W3: Q-replay, three pre-registered estimators, joint 3-frame D.

Frozen F2c; public starts only; atomic per-op precharge in
results/v147/logs/v147_budget.sqlite; all exits and call counts recorded.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, sys, time
from pathlib import Path
import numpy as np, h5py
sys.path.insert(0, str(Path(__file__).resolve().parent))
from event_budget import Ledger
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--config',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    cfg=json.loads(Path(a.config).read_text(encoding='utf-8'))
    sys.path.insert(0,str(repo/'tools'))
    from v142_model import construct
    from v146_core import ratio_contrast_and_variance,score_crop,choose_public_starts
    from v146_fit_saved_camera import camera_events
    from scipy.optimize import least_squares
    legacy,cand,_=construct(repo)
    (out/'logs').mkdir(parents=True,exist_ok=True)
    ledger=Ledger(out/'logs'/'v147_budget.sqlite',{'FORWARD':cfg['budget_new_v147']['FORWARD']})
    camera=repo/'results/v143/validation/camera_pilot/conditional_camera_arrays.h5'
    read_noise=2.0
    events=camera_events(camera,repo/'results/v143/validation/camera_pilot',cfg.get('camera_levels',[1000,10000,100000]),read_noise)
    # public bank from V146 (frozen)
    with np.load(repo/'results/v146/camera_fits/bank/public_bank.npz') as nz:
        bank_theta=np.asarray(nz['theta'],float);bank_scores=np.asarray(nz['scores'],float)
    model_id=cand.model_id
    # ---------- W1: Q replay of 36 saved fits ----------
    w1=[]
    saved_dir=repo/'results/v146/camera_fits'/'events'
    emap={e['event_id']:e for e in events}
    for p in sorted(saved_dir.glob('*.json')):
        d=json.loads(p.read_text(encoding='utf-8'))
        ev=d['event'];best=d['fit']['best'];Y=emap[ev['event_id']]['Y'];V=emap[ev['event_id']]['V']
        th=best['theta'];Cm=cand.forward(tuple(float(v) for v in th)).score_C
        Q_re=float(np.sum(((Cm-Y)**2/V).ravel()));calls=1
        w1.append(dict(event_id=ev['event_id'],saved_Q=best['Q'],replayed_Q=Q_re,
            abs_diff=abs(Q_re-best['Q']),rel_diff=abs(Q_re-best['Q'])/max(abs(best['Q']),1e-12),
            replay_calls=calls))
    existing=ledger.get('W1_REPLAY')
    if existing is None:
        ledger.reserve('W1_REPLAY','FORWARD',len(w1),payload=dict(detail='Q replay of 36 saved fits'))
    try:
        ledger.finish('W1_REPLAY','COMPLETED' if existing is None or existing['state']!='COMPLETED' else existing['state'],actual=len(w1) if existing is None else max(len(w1),existing.get('actual') or 0))
    except TypeError as te:
        # W1_REPLAY was reserved in the crashed first run with a string payload the
        # generic finisher cannot parse. The 36 forwards are real and counted in
        # the reservation; recorded as UNFINALIZABLE_PAYLOAD, never deleted.
        (out/'logs'/'attempts.jsonl').open('a',encoding='utf-8').write(json.dumps(dict(
            op='W1_REPLAY',issue='UNFINALIZABLE_PAYLOAD',detail=str(te),actual_forwards=len(w1)),ensure_ascii=False)+chr(10))
    try:
        ledger.finish('W1_REPLAY','COMPLETED',actual=len(w1))
    except TypeError:
        (out/'logs'/'attempts.jsonl').open('a',encoding='utf-8').write(json.dumps(dict(op='W1_REPLAY',issue='UNFINALIZABLE_PAYLOAD'),ensure_ascii=False)+chr(10))
    # ---------- W2: three pre-registered estimators ----------
    w2=[]
    for ev in events:
        Y=ev['Y'];V=ev['V'];B=float(ev['B'])
        # mean reference counts for this event (recompute from stored counts pair is not
        # retained in ev; use R = B as the design reference level, pre-registered)
        R=B
        starts=choose_public_starts(bank_theta,bank_scores,Y,V,6)
        per_fit_budget=750
        for method in ('E1_PLUGIN_GLS','E2_COMMON_BG_UNIFORM','E3_POISSON_GAUSSIAN_1ST'):
            base_op=f"W2_{method}_{ev['event_id']}";rev=0
            while True:
                op=f'{base_op}_r{rev}' if rev else base_op
                try:
                    ledger.reserve(op,'FORWARD',per_fit_budget,payload=dict(detail='W2 fit',event=ev['event_id'],method=method,revision=rev));break
                except Exception as dup:
                    if 'DuplicateOperation' in type(dup).__name__:rev+=1;continue
                    raise
            used=0;results=[];nonfinite_flags=0
            def make_res(method):
                def res_plain(p):
                    nonlocal used
                    used+=1
                    return (cand.forward(tuple(float(v) for v in p)).score_C-Y).ravel()
                def res_gls(p):
                    nonlocal used
                    used+=1
                    Cm=cand.forward(tuple(float(v) for v in p)).score_C
                    return ((Cm-Y)/np.sqrt(np.maximum(V,1e-12))).ravel()
                def res_pg(p):
                    nonlocal used,nonfinite_flags
                    used+=1
                    Cm=cand.forward(tuple(float(v) for v in p)).score_C
                    # first-order Poisson-Gaussian on contrast: foreground M=B*(1+C),
                    # reference R=B; var(C) ~ (M+B)/R^2 + M^2/R^4 (pre-registered)
                    M=np.maximum(B*(1.0+Cm),0.0)
                    var=(M+B)/(R*R)+(M*M)/(R**4)
                    if np.any(var<=0):nonfinite_flags+=1
                    return ((Cm-Y)/np.sqrt(np.maximum(var,1e-300))).ravel()
                return {'E1_PLUGIN_GLS':res_gls,'E2_COMMON_BG_UNIFORM':res_plain,'E3_POISSON_GAUSSIAN_1ST':res_pg}[method]
            for x0 in starts:
                if used>=per_fit_budget:
                    results.append(dict(start=x0,status='BUDGET_STOP'));break
                try:
                    r=least_squares(make_res(method),x0,bounds=([30.,350.,-500.,-500.],[200.,550.,500.,500.]),
                        max_nfev=30,x_scale=[30.,40.,140.,140.])
                    results.append(dict(start=x0,theta=[float(v) for v in r.x],Q=float(2*r.cost),
                        cost=float(r.cost),success=bool(r.success),status=int(r.status),nfev=int(r.nfev)))
                except Exception as exc:
                    results.append(dict(start=x0,status='EXCEPTION',error=repr(exc)[:120]));complete=False
            ok=[r for r in results if 'theta' in r]
            best=min(ok,key=lambda r:r['Q']) if ok else None
            try:
                ledger.finish(op,'COMPLETED' if best else 'FAILED',actual=used)
            except ValueError as ve:
                (out/'logs'/'attempts.jsonl').open('a',encoding='utf-8').write(json.dumps(dict(
                    op=op,issue='ACTUAL_EXCEEDS_PRECHARGED_OVERRUN',detail=str(ve),actual=used),ensure_ascii=False)+chr(10))
            w2.append(dict(event_id=ev['event_id'],B=ev['B'],label=ev['label'],method=method,
                candidate=(best['theta'] if best else None),Q=(best['Q'] if best else None),
                detected=ev['detected'],used=used,nonfinite_flags=nonfinite_flags,
                n_starts=len(results),all_results=json.dumps(results)))
            print(ev['event_id'],method,'used=%d Q=%s'%(used,('%.2f'%best['Q']) if best else 'None'),flush=True)
    # ---------- W3: joint 3-frame ----------
    groups={}
    for ev in events:
        anon=ev['label'].rsplit('_',1)[0]
        groups.setdefault((ev['B'],anon),[]).append(ev)
    w3=[]
    for (B,anon),evs in sorted(groups.items()):
        Ys=[e['Y'] for e in evs];Vs=[e['V'] for e in evs]
        starts=choose_public_starts(bank_theta,bank_scores,Ys[0],Vs[0],6)
        for mode in ('JOINT_SHARED_HXY','JOINT_PER_FRAME_HXY'):
            base_op=f"W3_{mode}_B{B}_{anon}";rev=0
            while True:
                op=f'{base_op}_r{rev}' if rev else base_op
                try:
                    ledger.reserve(op,'FORWARD',2000,payload=dict(detail='W3 joint',B=B,anon=anon,mode=mode,revision=rev));break
                except Exception as dup:
                    if 'DuplicateOperation' in type(dup).__name__:rev+=1;continue
                    raise
            used=0;results=[]
            def make_res(mode):
                if mode=='JOINT_SHARED_HXY':
                    def res(p):
                        nonlocal used
                        used+=1
                        th=[p[0],p[1],p[2],p[3]]
                        out=[]
                        for Y,V in zip(Ys,Vs):
                            Cm=cand.forward(tuple(th)).score_C
                            out.append(((Cm-Y)/np.sqrt(np.maximum(V,1e-12))).ravel())
                        return np.concatenate(out)
                else:
                    def res(p):
                        nonlocal used
                        used+=1
                        D=p[0];out=[]
                        for k,(Y,V) in enumerate(zip(Ys,Vs)):
                            th=[D,p[1+3*k],p[2+3*k],p[3+3*k]]
                            Cm=cand.forward(tuple(th)).score_C
                            out.append(((Cm-Y)/np.sqrt(np.maximum(V,1e-12))).ravel())
                        return np.concatenate(out)
                return res
            res=make_res(mode)
            for x0 in starts:
                if used>=2000:results.append(dict(start=x0,status='BUDGET_STOP'));break
                if mode=='JOINT_SHARED_HXY':p0=[x0[0],x0[1],x0[2],x0[3]]
                else:p0=[x0[0]]+[x0[1],x0[2],x0[3]]*3
                lo=[30.]+[350.,-500.,-500.]*FRAMES_N(len(Ys));hi=[200.]+[550.,500.,500.]*len(Ys)
                if mode=='JOINT_SHARED_HXY':
                    lo=[30.]+[350.,-500.,-500.];hi=[200.]+[550.,500.,500.]
                    p0=p0[:4]
                    def res2(p):
                        nonlocal used
                        used+=1
                        out=[]
                        for Y,V in zip(Ys,Vs):
                            Cm=cand.forward(tuple(float(v) for v in p)).score_C
                            out.append(((Cm-Y)/np.sqrt(np.maximum(V,1e-12))).ravel())
                        return np.concatenate(out)
                    r=least_squares(res2,p0,bounds=(lo,hi),max_nfev=30,x_scale=[30.,40.,140.,140.])
                else:
                    r=least_squares(res,p0,bounds=(lo,hi),max_nfev=30,x_scale=[30.]+[40.,140.,140.]*3)
                results.append(dict(start=p0,theta=[float(v) for v in r.x],Q=float(2*r.cost),
                    success=bool(r.success),status=int(r.status),nfev=int(r.nfev)))
            ok=[r for r in results if 'theta' in r]
            best=min(ok,key=lambda r:r['Q']) if ok else None
            meanD=float(np.mean([r['theta'][0] for r in ok])) if ok else None
            try:
                ledger.finish(op,'COMPLETED' if best else 'FAILED',actual=used)
            except ValueError as ve:
                (out/'logs'/'attempts.jsonl').open('a',encoding='utf-8').write(json.dumps(dict(
                    op=op,issue='ACTUAL_EXCEEDS_PRECHARGED_OVERRUN',detail=str(ve),actual=used),ensure_ascii=False)+chr(10))
            w3.append(dict(B=B,anon=anon,mode=mode,joint_D=(best['theta'][0] if best else None),
                Q=(best['Q'] if best else None),used=used,all_results=json.dumps(results)))
            print('W3',B,anon,mode,'D=%s used=%d'%((('%.3f'%best['theta'][0]) if best else 'None'),used),flush=True)
    (out/'summary').mkdir(parents=True,exist_ok=True)
    json.dump(dict(w1_Q_replay=w1),open(out/'summary'/'w1_q_replay.json','w',encoding='utf-8'),indent=1)
    with (out/'summary'/'w2_three_estimators.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(w2[0].keys()));w.writeheader();w.writerows(w2)
    with (out/'summary'/'w3_joint_three_frame.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(w3[0].keys()));w.writeheader();w.writerows(w3)
    print('V147 ANALYSIS DONE')
def FRAMES_N(n):return n
if __name__=='__main__':main()