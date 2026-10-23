#!/usr/bin/env python3
"""Read-only F2c coarse profile qualification inventory, NOT a global-min proof."""
from __future__ import annotations
import argparse
from pathlib import Path
from _shared import load_json,save_json


def summarize(data,expected_model=None):
    rows=data.get('rows',[])
    good=[r for r in rows if r.get('loss_L2') is not None]
    exact=[r for r in rows if r.get('exact_joint_witness') is not None]
    issues=[]
    if not rows:issues.append('NO_D_GRID')
    if expected_model and data.get('model_id')!=expected_model:issues.append('MODEL_ID_MISMATCH')
    if any(not r.get('point_search_complete',False) for r in rows):issues.append('NOT_ALL_D_POINTS_SEARCH_COMPLETE')
    if data.get('adaptive_coverage_complete') is not True:issues.append('ADAPTIVE_COVERAGE_INCOMPLETE')
    if data.get('grid_coverage_complete') is not True:issues.append('GRID_COVERAGE_INCOMPLETE')
    if data.get('profile_scientifically_complete') is not True:issues.append('SCIENTIFIC_PROFILE_INCOMPLETE')
    if not exact:issues.append('MISSING_EXACT_JOINT_WITNESS')
    for r in exact:
        w=r['exact_joint_witness']
        if r.get('loss_L2') is None or float(r['loss_L2'])>float(w['loss_L2'])+1e-12:
            issues.append('PROFILE_WORSE_THAN_VALID_SAME_D_WITNESS')
    return {'model_id':data.get('model_id'),'n_D_points':len(rows),
        'n_incomplete_D_points':sum(not r.get('point_search_complete',False) for r in rows),
        'n_exact_joint_witnesses':len(exact),'first_D':rows[0]['D'] if rows else None,
        'last_D':rows[-1]['D'] if rows else None,
        'score_min_L2':min((float(r['loss_L2']) for r in good),default=None),
        'actual_calls_recorded':data.get('actual_forward_calls_so_far'),
        'charged_allocation':data.get('charged_allocation'),
        'completed_scientifically':not issues,'issues':sorted(set(issues))}


def run(repo,cfg):
    repo=Path(repo);root=repo/cfg['source_files']['M_coarse_profiles'];cid=cfg['frozen_f2c_model_id'];cases={}
    for name in cfg['M_opened_dev_cases']:
        f=root/(name+'.json')
        cases[name]=summarize(load_json(f),cid) if f.is_file() else {'completed_scientifically':False,'issues':['NO_PROFILE_FILE']}
    for name in cfg['N_opened_scored_cases']:
        cases[name]={'completed_scientifically':False,'issues':['NO_N_SAME_MODEL_PROFILE_PUBLISHED']}
    return {'schema':'iscat143.profile_inventory.1','cases':cases,'n_scientifically_complete':sum(v['completed_scientifically'] for v in cases.values()),
        'note':'a finite multistart profile is a candidate LOWER-LOSS UPPER-BOUND envelope, not proof of global nuisance minimization'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--config',default=None);p.add_argument('--out',required=True);a=p.parse_args()
    cfg=load_json(a.config or Path(__file__).resolve().parents[1]/'config/v143_science_config.json')
    try:r=run(a.repo,cfg)
    except Exception as e:r={'audit_status':'BLOCKED','error':type(e).__name__+': '+str(e)}
    d=Path(a.out);save_json(d if d.suffix=='.json' else d/'profile_inventory.json',r)
    return 2 if 'audit_status' in r else 0
if __name__=='__main__':raise SystemExit(main())
