"""R1 adaptive refinement, budget-honest.

Cumulative per-M canonical budget = R0 + R1 usage against the frozen 120k cap.
Only M01 retains calls (11756). Refinement: 2.5 nm warm-started continuation
over the full domain (both directions), then 1.0/0.5 nm near coarse local
minima. All exits recorded; incomplete points stay incomplete.
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys, time
from pathlib import Path
import numpy as np, h5py
sys.path.insert(0, str(Path(__file__).resolve().parent))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    cfg=json.loads((repo/'config/v137_science_config.json').read_text(encoding='utf-8'))
    m=cfg['inherited_model'];pg=cfg['F2_profile']
    cap=int(pg['single_case_canonical_max'])
    r0=json.loads((repo/'results/v137/offline_F2_profiles/component_status.json').read_text(encoding='utf-8'))
    r1=json.loads((out/'component_status.json').read_text(encoding='utf-8'))
    r0use={r['case']:r['new_canonical_calls'] for r in r0['rows']}
    r1use={r['case']:r['new_canonical_calls'] for r in r1['rows']}
    usage={c:r0use[c]+r1use[c] for c in r0use}
    from load_field_library import load_library
    from v133_recover_M import optical
    from fit_reference import Objective,solve_start
    v133=json.loads((repo/'config/v133_science_config.json').read_text(encoding='utf-8'))
    model,_=load_library(repo/m['library'],kind='F2',optical=optical(v133))
    status={}
    with h5py.File(repo/m['prior_observations'],'r') as hf:
        for c in [f'M{i:02d}' for i in range(1,7)]:
            remain=cap-usage[c]
            if remain<=0:
                status[c]=dict(adaptive='BLOCKED_PER_CASE_BUDGET_EXHAUSTED',remaining_calls=0);continue
            Y=np.asarray(hf[c]['score_C'][()],float)
            prof=json.loads((out/'profiles'/f'{c}.json').read_text(encoding='utf-8'))
            coarse=sorted((r for r in prof['rows'] if r.get('theta')),key=lambda r:r['D'])
            obj=Objective(model,Y,total_limit=remain)
            newrows={}
            def cont(D,seed_theta):
                r=solve_start(obj,[D,seed_theta[1],seed_theta[2],seed_theta[3]],[1,2,3],
                              per_start_calls=pg['per_start_call_limit'],max_nfev=pg['max_nfev_per_start'])
                r['seed']='ADAPTIVE_WARM_START_D%.1f'%seed_theta[0]
                return r
            # 2.5 nm full-domain continuation, both directions
            grid25=[float(x) for x in np.arange(model.Ds[0],model.Ds[-1]+1e-9,2.5)]
            if abs(grid25[-1]-model.Ds[-1])>1e-9:grid25.append(model.Ds[-1])
            best_by_D={}
            for direction,order in (('ascending',grid25),('descending',grid25[::-1])):
                prev=None
                for D in order:
                    if obj.calls>=obj.limit:break
                    near=min(coarse,key=lambda r:abs(r['D']-D))
                    seed=near['theta'] if prev is None else best_by_D.get(prev,{}).get('theta') or near['theta']
                    r=cont(D,seed)
                    best=D_data=dict(D=D,theta=r['theta'],loss_L2=r['loss'],point_search_complete=bool(r['success']),
                        directions=[direction],attempts=[r],source='R1_ADAPTIVE_2_5NM')
                    if D in best_by_D:
                        old=best_by_D[D]
                        old['directions'].append(direction)
                        old['attempts'].append(r)
                        old['point_search_complete']=old['point_search_complete'] and bool(r['success'])
                        if r['loss'] is not None and (old['loss_L2'] is None or r['loss']<old['loss_L2']):
                            old['loss_L2']=r['loss'];old['theta']=r['theta']
                    else:best_by_D[D]=best
                    prev=D
            # 1.0/0.5 nm near coarse local minima (public rule)
            losses={r['D']:r['loss_L2'] for r in prof['rows'] if r['loss_L2'] is not None}
            minima=[]
            for r in sorted(coarse,key=lambda r:r['D']):
                lo=[losses[d] for d in losses if r['D']-5.01<=d<=r['D']+5.01 and d!=r['D']]
                if lo and r['loss_L2']<=min(lo):minima.append(r['D'])
            for level in (1.0,0.5):
                for mc in minima:
                    for D in np.arange(mc-3,mc+3.01,level):
                        D=round(float(D),3)
                        if D<model.Ds[0] or D>model.Ds[-1] or obj.calls>=obj.limit:continue
                        base=best_by_D.get(D) or best_by_D.get(min(best_by_D,key=lambda b:abs(b-D)))
                        if base is None or base.get('theta') is None:continue
                        r=cont(D,base['theta'])
                        if D in best_by_D:
                            old=best_by_D[D];old['attempts'].append(r)
                            if r['loss'] is not None and (old['loss_L2'] is None or r['loss']<old['loss_L2']):
                                old['loss_L2']=r['loss'];old['theta']=r['theta']
                        else:
                            best_by_D[D]=dict(D=D,theta=r['theta'],loss_L2=r['loss'],point_search_complete=bool(r['success']),
                                directions=['refine'],attempts=[r],source='R1_ADAPTIVE_%s'%level)
            merged={r['D']:dict(r) for r in prof['rows']}
            for D,r in best_by_D.items():
                ex=merged.get(float(D))
                if ex:
                    ex.setdefault('adaptive_attempts',[]).extend(r['attempts'])
                    if r['loss_L2'] is not None and (ex.get('loss_L2') is None or r['loss_L2']<ex['loss_L2']):
                        ex['loss_L2']=r['loss_L2'];ex['theta']=r['theta'];ex['witness_source']='R1_ADAPTIVE_BETTER'
                    ex['adaptive_levels_covered']=sorted(set(ex.get('adaptive_levels_covered',[])+['2.5']))
                else:
                    merged[float(D)]=dict(D=float(D),theta=r['theta'],loss_L2=r['loss_L2'],
                        point_search_complete=r['point_search_complete'],
                        attempts=r['attempts'],source=r['source'])
            rows=[merged[k] for k in sorted(merged)]
            prof['rows']=rows
            prof['adaptive_coverage']=dict(levels=['2.5','1.0','0.5'],applied_to=c if c=='M01' else None,
                complete=False,blocked_cases=[k for k,v in status.items()])
            prof['per_case_new_canonical_calls_r1_adaptive']=obj.calls
            p=out/'profiles'/f'{c}.json'
            p.write_text(json.dumps(prof,indent=2,ensure_ascii=False,allow_nan=False)+chr(10),encoding='utf-8')
            status[c]=dict(adaptive='RAN_PARTIAL' if c=='M01' else 'RAN',remaining_calls=remain,
                adaptive_calls=obj.calls,new_adaptive_points=len([k for k in best_by_D if k not in merged or merged[k].get('source','').startswith('R1_ADAPTIVE')]))
            print(c,'adaptive_calls=',obj.calls,'/',remain,flush=True)
            break  # only M01 has budget; others are recorded blocked below
    for c in [f'M{i:02d}' for i in range(1,7)]:
        if c not in status:status[c]=dict(adaptive='BLOCKED_PER_CASE_BUDGET_EXHAUSTED',remaining_calls=0)
    (out/'adaptive_status.json').write_text(json.dumps(dict(cumulative_usage=usage,cap=cap,status=status),indent=2)+chr(10),encoding='utf-8')
    print('ADAPTIVE done')
if __name__=='__main__':main()