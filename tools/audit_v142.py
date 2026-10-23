#!/usr/bin/env python3
"""Read-only V142 historical audit. Exit 0 = audit produced, NOT a science PASS.

Uses original published artifacts; never silently repairs/deletes a historical log.
N truth is used ONLY here, never in an estimator or profile runner.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, sqlite3, subprocess, sys
from pathlib import Path
from _shared import load_json,rows,sha,save_json,stats

CASES_M=[f'M{i:02d}' for i in range(1,7)]
CASES_N=[f'ANON_{i:02d}' for i in range(1,5)]

def git(repo,*args):
    r=subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True)
    return {'ok':r.returncode==0,'code':r.returncode,'stdout':r.stdout.strip()[:1500],
            'stderr':r.stderr.strip()[:1000]}

def audit(repo,config):
    repo=Path(repo).resolve();c=config;src=c['source_files'];out={
      'schema':'iscat143.published_v142_audit.1','source_commit_required':c['fixed_v142_commit'],
      'audit_success_does_not_imply_science_pass':True,'git':{},'freeze':{},'N':{},'M':{},'profiles':{},'budget':{},'issues':[]}
    g=out['git'];g['branch_v142']=git(repo,'rev-parse','v142');g['HEAD']=git(repo,'rev-parse','HEAD')
    g['review_commit_exists']=git(repo,'cat-file','-e',c['fixed_v142_commit']+'^{commit}')['ok']
    g['preN_is_ancestor_of_N']=git(repo,'merge-base','--is-ancestor',c['actual_v142_preN_git_commit'],c['N_data_git_commit'])['ok']
    g['N_is_ancestor_of_final']=git(repo,'merge-base','--is-ancestor',c['N_data_git_commit'],c['fixed_v142_commit'])['ok']
    frozen=load_json(repo/src['frozen_model']);f=out['freeze'];f['claimed_git_commit']=frozen['freeze_git_commit']
    f['declared_source_sha_check']={k:{'source_path':str(repo/'tools'/k),'exists':(repo/'tools'/k).is_file(),
        'match':(repo/'tools'/k).is_file() and sha(repo/'tools'/k)==h} for k,h in frozen['source_code_sha256'].items()}
    f['claimed_commit_contains_f2c_model']=git(repo,'cat-file','-e',frozen['freeze_git_commit']+':tools/v142_model.py')['ok']
    f['preN_commit_contains_f2c_model']=git(repo,'cat-file','-e',c['actual_v142_preN_git_commit']+':tools/v142_model.py')['ok']
    f['preN_commit_contains_N_estimator']=git(repo,'cat-file','-e',c['actual_v142_preN_git_commit']+':tools/v142_n_estimate.py')['ok']
    f['N_estimator_sha_pinned_in_freeze']='v142_n_estimate.py' in frozen['source_code_sha256']
    f['model_id']=frozen['model_id'];f['N_spec_sha_matches']=sha(repo/src['N_validator_truth'])==frozen['N_validator_spec_sha256']
    f['freeze_sha_of_pinned_inputs_not_committed_at_claimed_sha']=not f['claimed_commit_contains_f2c_model']
    if f['freeze_sha_of_pinned_inputs_not_committed_at_claimed_sha']:
        out['issues'].append('R01_MODEL_CODE_NOT_AT_RECORDED_FREEZE_GIT_COMMIT')
    if not f['N_estimator_sha_pinned_in_freeze']:
        out['issues'].append('R01_ANON_ESTIMATOR_NOT_HASHED_IN_FREEZE')
    if not f['N_spec_sha_matches']:out['issues'].append('R01_N_SPEC_BYTES_DIFFER_FROM_FREEZE')
    nscore=rows(repo/src['N_scores']);cand={r['anon_case']:r for r in rows(repo/src['N_estimates'])}
    ntruth={r['anon_case']:r for r in nscore}
    if set(cand)!=set(CASES_N) or set(ntruth)!=set(CASES_N):raise ValueError('N case mapping incomplete or duplicated')
    ne=[float(cand[k]['candidate_D']) for k in CASES_N];nt=[float(ntruth[k]['D_true']) for k in CASES_N]
    for k,e in zip(CASES_N,ne):
        if abs(e-float(ntruth[k]['D_hat']))>1e-11:raise ValueError(f'{k} score/estimator mismatch')
    out['N']['candidate_stats']=stats(nt,ne)
    out['N']['candidates_model_id_matches']=all(r['source_model_id']==frozen['model_id'] for r in cand.values())
    out['N']['old_published_score_summary']=load_json(repo/'results/v142/validation/new_N_validator_score.json')
    out['N']['anon_names']=sorted(cand)
    out['N']['render_mat_files']=sorted(x.name for x in (repo/src['N_original_mats']).glob('*.mat'))
    out['N']['n_render_mats']=len(out['N']['render_mat_files'])
    out['N']['n_original_solver_mat_under_v142_results']=sum(1 for p in (repo/'results/v142').rglob('*.mat') if p.name.startswith('sol_'))
    if out['N']['n_original_solver_mat_under_v142_results']==0:
        out['issues'].append('R02_N_ORIGINAL_BEM_SOLVE_NOT_PUBLISHED_UNDER_RESULTS_V142')
    mreg=load_json(repo/src['M_truth_registry'])['cases'];mt={r['tag'].removeprefix('holdout_'):float(r['D_nm']) for r in mreg}
    if set(mt)!=set(CASES_M):raise ValueError('M original registry identity mismatch')
    old={k:load_json(repo/src['M_old_fits']/(f'M_{k}.json'))['theta'][0] for k in CASES_M}
    new={k:load_json(repo/src['M_new_fits']/(f'{k}.json'))['candidate_D'] for k in CASES_M}
    out['M']['F2_old_stats']=stats([mt[k] for k in CASES_M],[old[k] for k in CASES_M])
    out['M']['F2c_new_stats']=stats([mt[k] for k in CASES_M],[new[k] for k in CASES_M])
    profile_detail={}
    for k in CASES_M:
        p=load_json(repo/src['M_coarse_profiles']/(f'{k}.json'))
        valid=[r for r in p['rows'] if r.get('loss_L2') is not None]
        errors=sum(not r.get('point_search_complete',False) for r in p['rows'])
        witnesses=[r for r in p['rows'] if r.get('exact_joint_witness')]
        profile_detail[k]={'n_D_points':len(p['rows']),'first_D':p['rows'][0]['D'],'last_D':p['rows'][-1]['D'],
          'grid_coverage_complete':p.get('grid_coverage_complete'),'adaptive_coverage_complete':p.get('adaptive_coverage_complete'),
          'scientifically_complete':p.get('profile_scientifically_complete'),
          'n_points_incomplete':errors,'exact_joint_witnesses':len(witnesses),
          'profile_model_id':p.get('model_id'),'forward_calls_from_checkpoint':p.get('actual_forward_calls_so_far'),
          'charged_allocation':p.get('charged_allocation')}
    out['profiles']['M']=profile_detail
    out['profiles']['N_files_already_published']=[p.name for p in (repo/'results/v142/validation').glob('*N*profile*')]
    out['profiles']['all_M_science_complete']=all(p['scientifically_complete'] is True for p in profile_detail.values())
    if not out['profiles']['all_M_science_complete']:out['issues'].append('R05_ALL_M_PROFILES_STILL_INCOMPLETE')
    bc=rows(repo/src['legacy_v142_summary']);events=[r for r in bc if not r['event'].startswith('TOTAL')]
    out['budget']['published_csv_records']=events
    out['budget']['source_csv_reported_total_actual']=next((r for r in bc if r['event'].startswith('TOTAL')),None)
    out['budget']['rows_bem_total']=sum(int(r['new_bem']) for r in events)
    out['budget']['rows_render_total']=sum(int(r['new_renders']) for r in events)
    db=repo/src['legacy_v142_budget'];out['budget']['sqlite_sha256']=sha(db)
    con=sqlite3.connect(f'file:{db}?mode=ro',uri=True)
    try:
        tables=[r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        out['budget']['sqlite_tables']=tables
        out['budget']['original_events_table_published']='events' in tables
        if 'budget' in tables:
            out['budget']['assembled_budget_rows']=[dict(zip([x[1] for x in con.execute('PRAGMA table_info(budget)')],r)) for r in con.execute('SELECT * FROM budget')]
    finally:con.close()
    if not out['budget']['original_events_table_published']:
        out['issues'].append('R03_ORIGINAL_ATOMIC_EVENT_TABLE_NOT_IN_PUBLISHED_BUDGET_SQLITE')
    if out['budget']['rows_bem_total']==0:
        out['issues'].append('R02_PUBLISHED_BUDGET_CSV_HAS_ZERO_BEM_EVENTS_WHILE_STATUS_CLAIMS_4')
    if out['budget']['rows_render_total']==0:
        out['issues'].append('R02_PUBLISHED_BUDGET_CSV_HAS_ZERO_RENDER_EVENTS_WHILE_STATUS_CLAIMS_12')
    out['source_evidence_level']='PUBLISHED_SOURCE_TEXT_AND_SUMMARIES_RECOMPUTED__NO_ORIGINAL_MAXWELL_SOLVE_REDERIVATION'
    out['scientific_verdict']='PARTIAL_ACCEPTED__CANNOT_CERTIFY_BLIND_PROTOCOL_OR_UNIQUE_DIAMETER'
    return out


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--config',default=None)
    p.add_argument('--out',required=True);a=p.parse_args()
    cfg=load_json(a.config or Path(__file__).resolve().parents[1]/'config/v143_science_config.json')
    try:r=audit(Path(a.repo),cfg)
    except Exception as e:r={'audit_status':'BLOCKED','error':type(e).__name__+': '+str(e)}
    dest=Path(a.out);dest=dest if dest.suffix=='.json' else dest/'v142_audit.json';save_json(dest,r)
    print('AUDIT_COMPLETED_NO_AUTOMATIC_SCIENCE_PASS' if 'audit_status' not in r else 'AUDIT_BLOCKED',dest)
    return 0 if 'audit_status' not in r else 2
if __name__=='__main__':raise SystemExit(main())
