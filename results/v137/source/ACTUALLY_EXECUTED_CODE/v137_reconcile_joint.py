"""W3 step 5: reconcile a legal profile point that beats the inherited joint optimum.

Only a real evaluated lower loss at its own D may trigger a 4D joint re-fit.
Old and new identities are kept side by side; truth is never read.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, sys, time
from pathlib import Path
import numpy as np, h5py
sys.path.insert(0, str(Path(__file__).resolve().parent))

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def write_json(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_name(p.name+'.tmp');t.write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8');os.replace(t,p)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--profile-dir',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
    from load_field_library import load_library
    from v133_recover_M import optical
    from observation_adapter import array_sha
    from fit_reference import Objective,solve_start
    from model_lock import verify_code_lock
    cfg=json.loads((repo/'config/v137_science_config.json').read_text(encoding='utf-8'))
    m=cfg['inherited_model'];v133=json.loads((repo/'config/v133_science_config.json').read_text(encoding='utf-8'))
    passd=json.loads((repo/m['model_passport']).read_text(encoding='utf-8'))
    verify_code_lock(passd['code_sha256'],tools_dir=repo/'tools')
    lib=repo/m['library']
    if sha(lib)!=m['library_sha256']:raise SystemExit('library SHA mismatch')
    model,_=load_library(lib,kind='F2',optical=optical(v133))
    if model.model_id!=m['model_id']:raise SystemExit('model id mismatch')
    limit=int(cfg['budget_new_work_hard_limits']['canonical_F2_calls_all_stages'])
    total_calls=0
    bindings={x['case']:x for x in json.loads((repo/m['prior_observation_binding']).read_text(encoding='utf-8'))}
    rows=[];details=[]
    with h5py.File(repo/m['prior_observations'],'r') as hf:
        for i in range(1,7):
            c=f'M{i:02d}'
            Y=np.asarray(hf[c]['score_C'][()],float)
            if array_sha(Y)!=bindings[c]['score_array_sha256']:raise SystemExit(c+': observation changed')
            prof=json.loads((Path(a.profile_dir)/f'{c}.json').read_text(encoding='utf-8'))
            old=prof['known_joint_loss_L2'];oldth=prof['known_joint_theta']
            best=min(prof['rows'],key=lambda r:r['loss_L2'] if r['loss_L2'] is not None else float('inf'))
            tol=max(1e-12,1e-7*abs(old));triggered=best['loss_L2']<old-tol
            rec=dict(case=c,old_joint_D=oldth[0],old_joint_loss=old,
                best_profile_D=best['D'],best_profile_loss=best['loss_L2'],
                beat_tolerance=tol,triggered=triggered)
            if triggered:
                obj=Objective(model,Y,total_limit=limit)
                starts=[]
                for tag,th in [('BEAT_POINT',best['theta']),('OLD_JOINT',oldth)]:
                    r=solve_start(obj,th,[0,1,2,3],per_start_calls=2000,max_nfev=400)
                    r['seed']=tag;starts.append(r)
                ok=[r for r in starts if r['success'] and r['loss'] is not None]
                if ok:
                    s=min(ok,key=lambda r:r['loss'])
                    newloss=float(np.linalg.norm(model.forward(s['theta']).score_C-Y))
                    rec.update(reconciled_theta=s['theta'],reconciled_loss=newloss,
                        improvement=old-newloss,reconciled=True)
                    if newloss>old+tol:rec['rejected']='RECONCILED_NOT_LOWER_THAN_OLD'
                else:rec['reconciled']=False;rec['blocked']='ALL_STARTS_FAILED'
                rec['starts']=starts;rec['canonical_calls_this_component']=obj.calls;total_calls+=obj.calls
            rows.append(rec);details.append(rec)
    fields=['case','old_joint_D','old_joint_loss','best_profile_D','best_profile_loss','beat_tolerance',
            'triggered','reconciled','reconciled_theta','reconciled_loss','improvement','rejected','blocked',
            'canonical_calls_this_component']
    with (out/'M_reconciled_candidates.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in rows:
            w.writerow({k:(json.dumps(v) if k=='reconciled_theta' and v is not None else v) for k,v in r.items() if k!='starts'})
    write_json(out/'M_reconciled_candidates.json',dict(
        schema='iscat137.v137_joint_reconcile.1',details=details,
        total_canonical_calls=total_calls,
        scope='JOINT_RECONCILIATION_NUMERIC_ONLY_NOT_PHYSICS'))
    print('RECONCILE triggered=',sum(r['triggered'] for r in rows),
          'reconciled=',sum(bool(r.get('reconciled')) for r in rows),
          'calls=',total_calls)
if __name__=='__main__':main()
