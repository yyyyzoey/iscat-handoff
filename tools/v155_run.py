"""V155: proper per-pixel Jacobian diagnostics using the provided reference modules."""
from __future__ import annotations
import argparse, hashlib, json, os, sys, tempfile
from pathlib import Path
import numpy as np, h5py
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v152_budget_store import BudgetStore, CountedPredictor
from v152_gls_core import GlsData
from v155_stage import run_group
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    (out/'logs').mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(repo/'tools'))
    from v142_model import construct
    from v146_core import choose_public_starts
    from v146_fit_saved_camera import camera_events
    legacy,cand,_=construct(repo)
    model_id=cand.model_id
    # Use the provided BudgetStore
    db_path=str(out/'logs'/'v155_budget.sqlite')
    if os.path.exists(db_path):os.remove(db_path)
    store=BudgetStore(db_path,'v155',{'LOCAL_INFORMATION':900},900)
    # Load camera events
    camera=repo/'results/v143/validation/camera_pilot/conditional_camera_arrays.h5'
    events=camera_events(camera,repo/'results/v143/validation/camera_pilot',[1000,10000,100000],2.0)
    # Group by (B, anon)
    from collections import defaultdict
    groups=defaultdict(list)
    for ev in events:
        anon=ev['label'].rsplit('_',1)[0]
        groups[(ev['B'],anon)].append(ev)
    # For each group: prepare GlsData, get candidate theta from V152 joint results
    v150_results=repo/'results/v150'/'all_results.json'
    joint_theta={}
    if v150_results.is_file():
        v150=json.loads(v150_results.read_text(encoding='utf-8'))
        for jr in v150.get('joint',[]):
            key=(jr['B'],jr['anon'])
            # find full theta from results
            if jr.get('results'):
                results=json.loads(jr['results']) if isinstance(jr['results'],str) else jr['results']
                okr=[r for r in results if 'theta' in r]
                if okr:
                    best=min(okr,key=lambda r:r['Q'])
                    joint_theta[key]=best['theta']
    # For groups without V150 results, use a reasonable public start
    all_diags=[]
    for (B,anon),evs in sorted(groups.items()):
        Ys=[e['Y'] for e in evs];Vs=[e['V'] for e in evs]
        # Build GlsData
        gd=GlsData.from_frames(Ys,Vs)
        # candidate theta
        key=(B,anon)
        if key in joint_theta:
            theta=joint_theta[key]
        else:
            theta=[min(max(B*0.5,30.),200.),450.,0.,0.]
        # model contrast callable
        def model_contrast(th):
            o=cand.forward(tuple(float(v) for v in th))
            return o.score_C
        # run group
        task=f'V155_B{B}_{anon}'
        owner='v155_workstation'
        source=dict(B=B,anon=anon,model_id=model_id,n_frames=len(Ys))
        try:
            result=run_group(store=store,task=task,owner=owner,data=gd,theta=theta,
                source=source,model_contrast=model_contrast,out=out/'groups'/f'{B}_{anon}',cap=40)
            all_diags.append(dict(B=B,anon=anon,result=json.dumps(result,default=str)[:200]))
            print(f'B={B} {anon} OK',flush=True)
        except Exception as exc:
            print(f'B={B} {anon} ERROR: {exc}',flush=True)
            all_diags.append(dict(B=B,anon=anon,error=repr(exc)[:200]))
    json.dump(all_diags,open(out/'group_results.json','w'),indent=1,default=str)
    print(f'V155 STAGE DONE groups={len(all_diags)}',flush=True)
if __name__=='__main__':main()
