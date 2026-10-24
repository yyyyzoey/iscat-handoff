#!/usr/bin/env python3
"""Read-only intake: fixed-D invariants, true candidate sources, budget violations.
Does not certify stored losses without a model replay, or original Maxwell solves.
"""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
from v146_core import read_json,save_json,file_sha,valid_witness,observed_margin


def audit_profile_dir(root):
    root=Path(root);points=[];fail=[]
    for p in sorted(root.glob('*/D*.json')):
        try:
            d=read_json(p);r=d['result'];D=float(d['target_D'])
            if abs(float(r['fixed_D'])-D)>1e-10:raise ValueError('FIXED_D_FIELD_DISAGREES')
            b=r.get('best');witnesses=r.get('valid_witnesses',[])
            if b is not None:valid_witness(b['theta'],b['loss_L2'],D)
            for w in witnesses:valid_witness(w['theta'],w['loss_L2'],D)
            points.append({'path':p.as_posix(),'case':d['case'],'D':D,'theta':None if b is None else b['theta'],
                'R':None if b is None else b['loss_L2'],'source_sha256':file_sha(p),
                'model_id':d.get('model_id'),'observation_sha256':d.get('observation_sha256'),
                'point_search_complete':r.get('point_search_complete') is True,
                'calls':r.get('actual_f2c_callbacks'),'invariants_passed':True})
        except Exception as e:fail.append({'path':p.as_posix(),'error':repr(e)})
    return {'n_point_files':len(points)+len(fail),'n_invariant_pass':len(points),'errors':fail,'points':points,
            'independent_residual_replay':'NOT_DONE_BY_THIS_AUDIT','global_D_coverage':'UNKNOWN_BETWEEN_SAMPLED_POINTS'}


def run(repo,cfg):
    repo=Path(repo);profiles=audit_profile_dir(repo/cfg['inputs']['v145_profiles'])
    with (repo/cfg['inputs']['N_candidates']).open(encoding='utf-8',newline='') as f:
        nr={r['anon_case']:float(r['candidate_D']) for r in csv.DictReader(f)}
    candidates=dict(nr)
    for c in cfg['M_cases']:candidates[c]=float(read_json(repo/cfg['inputs']['M_candidates']/(c+'.json'))['candidate_D'])
    diagnostics={}
    for c,cd in candidates.items():
        ps=[r for r in profiles['points'] if r['case']==c and r['theta'] is not None]
        w=[{'theta':r['theta'],'loss_L2':r['R'],'fixed_D':r['D']} for r in ps]
        diagnostics[c]=observed_margin(w,cd)
    pilot=repo/cfg['inputs']['pilot_ledger']
    with pilot.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    attempted_solves=[r for r in rows if r.get('action')=='solve']
    successful=[r for r in attempted_solves if r.get('ok')=='1']
    renders=[r for r in rows if r.get('action')=='render']
    info=read_json(repo/cfg['inputs']['v145_information'])
    ratios={}
    for c,r in info['cases'].items():
        x=float(r['D_information_fraction_after_hxy_projection'])
        ratios[c]={'published_norm_ratio':x,'squared_ratio_under_iid_equal_variance':x*x,
                   'not_real_camera_Fisher_information':True}
    summary=read_json(repo/cfg['inputs']['v145_summary'])
    inconsistent=[c for c,r in summary.items() if r.get('unknown_D')==[] and not r.get('adaptive_coverage_complete',False)]
    return {'schema':'iscat146.v145_audit.1','fixed_source_commit':cfg['base_commit'],
        'profiles':profiles,'estimator_only_candidates':candidates,'observed_error_margin_diagnostics':diagnostics,
        'pilot_history':{'recorded_BEM_attempts':len(attempted_solves),'recorded_successful_BEM':len(successful),
                         'recorded_render_attempts':len(renders),'no_new_physics_performed':True,
                         'old_budget_violation_preserved':True,'ledger_sha256':file_sha(pilot)},
        'unknown_D_field_misleading_cases':inconsistent,'norm_vs_information_correction':ratios,
        'old_summary_generator_stale_claim_requires_repair':True,
        'input_sources_sha256':{k:file_sha(repo/v) for k,v in cfg['inputs'].items() if (repo/v).is_file()},
        'science_verdict':'PARTIAL; SOFTWARE_INVARIANTS_AND_PUBLISHED_RECORDS_ONLY'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--config',required=True);p.add_argument('--out',required=True)
    a=p.parse_args()
    try:r=run(a.repo,read_json(a.config));save_json(a.out,r)
    except Exception as e:save_json(a.out,{'status':'BLOCKED','error':repr(e)});return 2
    return 2 if r['profiles']['errors'] else 0
if __name__=='__main__':raise SystemExit(main())
