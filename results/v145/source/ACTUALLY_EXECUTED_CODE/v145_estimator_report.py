#!/usr/bin/env python3
"""Truth-blind N/M per-particle report; only actual estimator candidates.

Corrects V144 where validator true D was silently written as candidate_D.
Never asserts global identifiability, calibrated confidence, or real-camera sizing.
"""
from __future__ import annotations
import argparse,json,math,hashlib
from pathlib import Path
from v145_fixed_d_profiles import read_json,load_data_and_candidate,sha_file,signal_hash


def aggregate_witnesses(repo,cfg,case,y_sha):
    model_id=cfg['inherited_model_id'];model_sha=sha_file(Path(repo)/cfg['model_source']);rows=[];invalid=[]
    root=Path(repo)/cfg['v143_profile_root']
    for phase in ('coarse','refine'):
        d=root/phase/case
        if not d.is_dir():continue
        ident=read_json(d/'input_identity.json')
        if (ident.get('model_id'),ident.get('observation_sha'),ident.get('estimator_source_sha256'))!=(model_id,y_sha,model_sha):
            raise ValueError('V143_SOURCE_BINDING_MISMATCH:'+case)
        for p in d.glob('*.json'):
            if p.name in ('input_identity.json','summary.json'):continue
            doc=read_json(p);obj=doc.get('result') or {};best=obj.get('best')
            if not best or not isinstance(best.get('theta'),list) or len(best['theta'])!=4:continue
            D=float(obj['D']);t=list(map(float,best['theta']));loss=float(best['loss_L2'])
            if not all(math.isfinite(v) for v in t+[loss]) or abs(D-t[0])>1e-8:
                invalid.append(dict(source=p.as_posix(),reason='D_NOT_FIXED'));continue
            rows.append(dict(D=D,loss_L2=loss,theta=t,origin='V143_PRIOR_VALID_D_EVALUATION',source=p.relative_to(repo).as_posix(),
              point_search_complete=obj.get('point_search_complete') is True))
    out=Path(repo)/'results/v145/validation/fixed_D_profiles'/case
    if out.is_dir():
        for p in out.glob('D*.json'):
            doc=read_json(p)
            if (doc.get('model_id'),doc.get('observation_sha256'),doc.get('model_source_sha256'))!=(model_id,y_sha,model_sha):
                raise ValueError('V145_SOURCE_BINDING_MISMATCH:'+case)
            D=float(doc['target_D']);result=doc.get('result') or {}
            for j,w in enumerate(result.get('valid_witnesses') or []):
                t=list(map(float,w['theta']));loss=float(w['loss_L2'])
                if len(t)!=4 or not all(math.isfinite(v) for v in t+[loss]) or abs(D-t[0])>1e-8:
                    invalid.append(dict(source=p.as_posix(),reason='D_NOT_FIXED'));continue
                rows.append(dict(D=D,loss_L2=loss,theta=t,origin='V145_STRICT_FIXED_D',source=p.relative_to(repo).as_posix(),
                    point_search_complete=result.get('point_search_complete') is True))
    winners={}
    for r in rows:
        old=winners.get(r['D'])
        if old is None or r['loss_L2']<old['loss_L2']:winners[r['D']]=r
    return sorted(winners.values(),key=lambda r:r['D']),invalid

def report(repo,cfg):
    repo=Path(repo).resolve();cases={}
    epsilon=cfg['existing_dev_epsilon']['value_unscaled_L2']
    for case in cfg['cases']:
        y,theta,yhash=load_data_and_candidate(repo,cfg,case)
        witnesses,invalid=aggregate_witnesses(repo,cfg,case,yhash)
        min_r=min((w['loss_L2'] for w in witnesses),default=None)
        comp=[w for w in witnesses if min_r is not None and w['loss_L2']<=min_r+epsilon]
        width_goal=max(5.,.1*theta[0]);separated=[]
        for i,a in enumerate(comp):
            for b in comp[i+1:]:
                if b['D']-a['D']>2*width_goal:
                    separated.append(dict(D1=a['D'],D2=b['D'],R1=a['loss_L2'],R2=b['loss_L2'],separation_nm=b['D']-a['D']))
        best_sep=max(separated,key=lambda r:r['separation_nm']) if separated else None
        cases[case]=dict(candidate_D=theta[0],candidate_h=theta[1],candidate_x=theta[2],candidate_y=theta[3],
            model_id=cfg['inherited_model_id'],observation_sha256=yhash,
            known_compatible_finite_witness_D=[w['D'] for w in comp],
            observed_far_competing_pair_under_unqualified_dev_eps=best_sep,
            all_fixed_D_witness_points=witnesses,
            invalid_nonfixed_checkpoints=invalid,
            model_error_epsilon_unscaled_L2=epsilon,
            model_error_epsilon_status='UNQUALIFIED_DEVELOPER_MAX__NOT_CI',
            conditional_identifiable=False if best_sep else None,
            conditional_identifiable_scope='NOT_UNIQUE_UNDER_UNQUALIFIED_DEV_EPS' if best_sep else 'UNKNOWN_GLOBAL_SEARCH',
            unknown_D_regions_remain=True,adaptive_profile_complete=False,
            camera_diameter_qualified=False,
            reportable_D=None,
            all_required_science_gates_passed=False,
            reason_codes=(['DISTANT_COMPETING_FINITE_WITNESSES_UNDER_UNQUALIFIED_DEV_EPS'] if best_sep else [])+[
                'GLOBAL_PROFILE_UNCERTIFIED','MODEL_ERROR_NOT_CALIBRATED','REAL_CAMERA_SIZING_NOT_QUALIFIED'],
            estimator_truth_file_used=False)
    return dict(schema='iscat145.estimator_report.1',source_scope='ONLY_ANONYMOUS_ESTIMATES_AND_OPENED_M_FITS__NO_VALIDATOR_TRUTH',
       cases=cases,experimental_absolute_diameter_validated=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--config',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    dst=Path(a.out);dst.parent.mkdir(parents=True,exist_ok=True)
    try:r=report(a.repo,read_json(a.config))
    except Exception as e:
        dst.write_text(json.dumps(dict(status='BLOCKED',error=repr(e)),indent=2)+'\n');print('BLOCKED',repr(e));return 2
    dst.write_text(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print('ESTIMATOR_TRUTH_ISOLATION_COMPLETE__NO_SIZING_PASS',sum(v['reportable_D'] is None for v in r['cases'].values()))
    return 0
if __name__=='__main__':raise SystemExit(main())
