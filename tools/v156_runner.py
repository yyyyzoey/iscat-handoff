"""V156: B(recover 72 thetas + rescore) -> C(per-pixel Jacobian at real candidates) -> D(compile)."""
from __future__ import annotations
import argparse, hashlib, json, os, sys
from pathlib import Path
import numpy as np, h5py
sys.path.insert(0, str(Path(__file__).resolve().parent))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    for d in ('logs','joint','rescored','local_info','source'): (out/d).mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(repo/'tools'))
    from v142_model import construct
    from v146_core import choose_public_starts
    from v146_fit_saved_camera import camera_events
    from v155_pixel_diagnostics import diagnose, validate_pixel_record
    from v155_stage import run_group
    from v152_budget_store import BudgetStore, CountedPredictor
    from v152_gls_core import GlsData
    legacy,cand,_=construct(repo)
    model_id=cand.model_id
    # load camera events
    camera=repo/'results/v143/validation/camera_pilot/conditional_camera_arrays.h5'
    events=camera_events(camera,repo/'results/v143/validation/camera_pilot',[1000,10000,100000],2.0)
    groups={}
    for ev in events:
        anon=ev['label'].rsplit('_',1)[0]
        groups.setdefault((ev['B'],anon),[]).append(ev)
    # load V152 all_results to get 72 full thetas
    v152=json.loads((repo/'results/v152/all_results.json').read_text(encoding='utf-8'))
    # Build 12 groups of 6 thetas each from V152 joint results
    group_data={}
    for jr in v152.get('joint',[]):
        B=jr['B'];anon=jr['anon']
        key=(B,anon)
        if key not in group_data:group_data[key]=dict(B=B,anon=anon,thetas=[],raw_results=jr)
        if jr.get('results'):
            results=json.loads(jr['results']) if isinstance(jr['results'],str) else jr['results']
            for r in results:
                if 'theta' in r:
                    group_data[key]['thetas'].append(dict(theta=r['theta'],Q=r.get('Q',r.get('Q_model')),start=r.get('start')))
    print(f'Loaded {len(group_data)} groups, {sum(len(v["thetas"]) for v in group_data.values())} thetas total',flush=True)
    # B: re-score all 72 thetas with correct GLS (no 2x)
    rescored=[]
    for key,gd in sorted(group_data.items()):
        B,anon=key[0],key[1]
        evs=groups.get((B,anon),[])
        if not evs:continue
        Ys=[e['Y'] for e in evs];Vs=[e['V'] for e in evs]
        Yi=np.stack(Ys);Vi=np.stack(Vs)
        Vbar=1.0/np.sum(1.0/Vi,axis=0);Ybar=Vbar*np.sum(Yi/Vi,axis=0)
        K=float(np.sum((Yi-Ybar)**2/Vi))
        best_th=None;best_Q=None
        for t in gd['thetas']:
            th=t['theta']
            th_ok=(min(max(th[0],30.),200.),min(max(th[1],350.),550.),min(max(th[2],-500.),500.),min(max(th[3],-500.),500.))
            o=cand.forward(th_ok)
            Cm=o.score_C
            q_model=float(np.sum(((Cm-Ybar)**2/np.maximum(Vbar,1e-12)).ravel()))
            q_joint=q_model+K
            entry=dict(B=B,anon=anon,theta=list(th_ok),Q_model=q_model,K=K,Q_joint=q_joint,
                source_start=t.get('start'),d_identity=bool(abs(th_ok[0]-t['theta'][0])<1e-10))
            rescored.append(entry)
            if best_Q is None or q_joint<best_Q:
                best_Q=q_joint;best_th=th_ok
        if best_th:
            gd['best_theta']=list(best_th);gd['best_Q']=best_Q
        print(f'  B={B} {anon} rescored {len(gd["thetas"])} thetas, best_D={best_th[0] if best_th else "None"}',flush=True)
    json.dump(rescored,open(out/'rescored'/'all_72_thetas.json','w'),indent=1,default=str)
    # Select 12 best candidates (lowest Q_joint per group)
    candidates={}
    for entry in rescored:
        key=(entry['B'],entry['anon'])
        if key not in candidates or entry['Q_joint']<candidates[key]['Q_joint']:
            candidates[key]=entry
    # C: per-pixel Jacobian at real candidate thetas
    print('C: per-pixel Jacobian 12 groups',flush=True)
    db_path=str(out/'logs'/'v156_budget_fresh.sqlite')
    if os.path.exists(db_path):os.remove(db_path)
    store=BudgetStore(db_path,'v156',{'LOCAL_INFORMATION':480},480)
    local_info={}
    for (B,anon),gd in sorted(group_data.items()):
        key=(B,anon)
        centry=candidates.get(key)
        if not centry or not centry.get('theta'):continue
        theta=centry['theta']
        evs=groups.get((B,anon),[])
        Ys=[e['Y'] for e in evs];Vs=[e['V'] for e in evs]
        gd_obj=GlsData.from_frames(Ys,Vs)
        task=f'V156_B{B}_{anon}'
        owner='v156'
        source=dict(B=B,anon=anon,model_id=model_id,
            source_record_id=centry.get('theta',[]),
            n_frames=len(Ys))
        def model_contrast(th):
            o=cand.forward(tuple(float(v) for v in th))
            return o.score_C
        try:
            gdir=out/'joint'/f'{B}_{anon}'
            result=run_group(store=store,task=task,owner=owner,data=gd_obj,theta=theta,
                source=source,model_contrast=model_contrast,out=gdir,cap=40)
            diag=result.get('diagnostic',{})
            projections=diag.get('projections',{})
            free_hxy=projections.get('free_hxy',[{}])[0] if projections.get('free_hxy') else {}
            local_info[f'B{B}_{anon}']=dict(
                candidate_D=theta[0],
                condition_number=free_hxy.get('normalized_nuisance_singular_values',['?']),
                remaining_D_norm_fraction=free_hxy.get('remaining_D_norm_fraction'),
                diagnostic_status=diag.get('status','UNKNOWN'),
                derivative_stable=diag.get('derivative_stable'),
                directional_check_pass=diag.get('directional_check_pass'),
                source='REAL_CANDIDATE_NOT_DEFAULT')
            print(f'  B={B} {anon} D={theta[0]:.2f} OK',flush=True)
        except Exception as exc:
            local_info[f'B{B}_{anon}']=dict(error=repr(exc)[:200])
            print(f'  B={B} {anon} ERROR: {exc}',flush=True)
    json.dump(local_info,open(out/'local_info'/'local_information.json','w'),indent=1,default=str)
    # compile per-particle report
    for case_i in range(1,5):
        anon=f'ANON_{case_i:02d}'
        entries=[r for r in rescored if r['anon']==anon]
        if not entries:continue
        best_e=min(entries,key=lambda e:e['Q_joint'])
        (out/'joint'/f'{anon}_best.json').write_text(json.dumps(best_e,indent=1,default=str),encoding='utf-8')
    print(f'V156 SCIENCE DONE rescored={len(rescored)} local_info={len(local_info)}',flush=True)
if __name__=='__main__':main()
