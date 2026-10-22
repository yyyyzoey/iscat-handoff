"""Read-only audit of the actual V134->V135 partial publication.

Requires a local checkout with the historical data files. This program proves
only relationships among *published data and code*, not a BEM solution or
independent experimental sizing.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

CASE_IDS = tuple(f'M{i:02d}' for i in range(1, 7))
EXPECTED_V133_MODEL = 'v131-field-db000d86636ed018cf1f9bd5291c7409b7e9d2aaa481328b3c22dfdb1a689427'
OLD_COMMIT = 'd62682b783b6b6666dd4d267221195ff2706cddd'
CURRENT_COMMIT = 'e68a1082e21bf15fa7639bb2af171dcf4829a141'


def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def git_blob(repo: Path, rev: str, relative_path: str):
    cmd = ['git', '-C', str(repo), 'rev-parse', f'{rev}:{relative_path}']
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return r.stdout.strip() if r.returncode == 0 else None


def score(rows, truth):
    error = [float(rows[k]) - float(truth[k]) for k in CASE_IDS]
    return {
        'n': len(error),
        'MAE_nm': sum(abs(x) for x in error) / len(error),
        'RMSE_nm': math.sqrt(sum(x*x for x in error) / len(error)),
        'bias_nm': sum(error) / len(error),
        'max_abs_nm': max(abs(x) for x in error),
        'target_pass_cases': [k for k, e in zip(CASE_IDS, error) if abs(e) <= max(5., .1*truth[k])],
        'errors_nm': dict(zip(CASE_IDS, error)),
    }


def audit(repo: Path):
    repo = repo.resolve()
    task = read_json(repo/'results/v126/v132_M_cases.json')
    truths = {c['tag'].removeprefix('holdout_'):float(c['D_nm']) for c in task['cases']}
    if set(truths) != set(CASE_IDS):
        raise ValueError('Wrong task cases; do not substitute another truth registry')

    f2 = {}
    with (repo/'results/v133/M_F2_baseline/M_F2_candidates.csv').open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            k=r['case']
            if k in f2: raise ValueError('duplicate F2 candidate')
            if r.get('model_id') != EXPECTED_V133_MODEL: raise ValueError('F2 model ID mismatch')
            f2[k]=float(r['candidate_D'])
    if set(f2) != set(CASE_IDS):raise ValueError('Incomplete F2 candidates')

    v134 = read_json(repo/'results/v134/reportability.json')
    props={r['case']:r for r in v134}
    if len(v134)!=6 or set(props)!=set(CASE_IDS):raise ValueError('Incomplete V134 reportability')
    coarse={k:float(props[k]['best_D']) for k in CASE_IDS}

    profiles = {}
    for k in CASE_IDS:
        p=read_json(repo/f'results/v135/profiles/{k}.json')
        xs=p['profile']
        if [float(z['D']) for z in xs] != [float(x) for x in range(30,201,5)]:
            raise ValueError(k+': incomplete or silently changed five-nm grid')
        valid=[z for z in xs if isinstance(z.get('loss'),(int,float)) and math.isfinite(z['loss'])]
        m=min(valid,key=lambda v:v['loss']) if valid else None
        profiles[k]={
            'five_nm_grid_min_D':float(m['D']) if m else None,
            'five_nm_grid_min_L2':float(m['loss']) if m else None,
            'has_locked_model_id':bool(p.get('model_id') == EXPECTED_V133_MODEL),
            'has_observation_sha256':bool(p.get('observation_sha256')),
            'contains_v133_exact_candidate_D':any(abs(float(z['D'])-f2[k])<=1e-9 for z in xs),
            'has_per_D_optimizer_status':all('optimizer_status' in z or 'attempts' in z for z in xs),
            'source_role':'UNQUALIFIED_GRID_DIAGNOSTIC',
        }

    observed_true=[k for k in CASE_IDS if props[k].get('reportable') is True]
    unsafe=[]
    for k in CASE_IDS:
        if props[k].get('reportable') is True:
            comp=props[k].get('compatible',[])
            touches=bool(comp and (comp[0][0]<=30 or comp[-1][-1]>=200))
            width=comp[0][1]-comp[0][0] if len(comp)==1 else None
            unsafe.append({'case':k,'published_accepted':True,'components':comp,
                           'touches_domain_boundary':touches,'width_nm':width,
                           'reason':'PUBLISHED_ACCEPTANCE_WITH_FULL_DOMAIN_COMPATIBILITY'})

    source_script=(repo/'tools/v135_run_profiles.py').read_text(encoding='utf-8')
    source_flags={
        'uses_v129_field_forward_instead_of_locked_v133':bool(re.search(r'import\s+v129_field_forward\s+as',source_script)),
        'reads_true_D_in_estimator_script':bool(re.search(r'M_truth\s*=|D_true\s*=\s*M_truth',source_script)),
        'penalizes_unhandled_exceptions_in_objective':bool(re.search(r'except\s+Exception\s*:\s*\n\s*return\s+np\.full',source_script)),
        'single_forward_warm_D_scan':bool(re.search(r'for\s+D\s+in\s+D_grid',source_script) and 'warm =' in source_script),
        'pre_registered_locked_import_missing':'field_forward_reference' not in source_script,
    }
    missing=[str(p) for p in (
        'evidence/published_values.json', 'results/v135/status.json',
        'results/v135/validation/physical_gate.json', 'results/v135/validation/F2_reportability.json',
        'results/v135/validation/raw_camera_data.h5',
        'results/v135/validation/motion_paths_intensities.h5',
        'results/v135/iscat_v135_return.zip',
    ) if not (repo/p).is_file()]
    old_zip=git_blob(repo,OLD_COMMIT,'results/v134/iscat_v134_return.zip')
    current_zip=git_blob(repo,CURRENT_COMMIT,'results/v134/iscat_v134_return.zip')
    old_status=git_blob(repo,OLD_COMMIT,'results/v134/status.json')
    current_status=git_blob(repo,CURRENT_COMMIT,'results/v134/status.json')
    current_status_json=read_json(repo/'results/v134/status.json')
    return {
        'schema':'iscat136.v134_v135_audit.1',
        'basis':'PUBLISHED_TEXT_AND_REPO_OBJECTS_NOT_ORIGINAL_BINARY_FIELD_REPLAY',
        'old_commit':OLD_COMMIT,'current_commit':CURRENT_COMMIT,
        'v133_locked_F2_candidate_statistics':score(f2,truths),
        'v134_coarse_Cmap_statistics':score(coarse,truths),
        'v134_published_reportable_true':observed_true,
        'v134_unsafe_acceptance':unsafe,
        'v135_new_profiles':profiles,
        'v135_script_risk_flags':source_flags,
        'v134_historical_zip_changed_in_descendant':('NOT_EVALUATED_MISSING_GIT_OBJECT' if old_zip is None or current_zip is None else old_zip!=current_zip),
        'v134_historical_status_changed_in_descendant':('NOT_EVALUATED_MISSING_GIT_OBJECT' if old_status is None or current_status is None else old_status!=current_status),
        'v134_zip_git_blobs':{'old':old_zip,'current':current_zip},
        'v134_status_git_blobs':{'old':old_status,'current':current_status},
        'v134_current_status_fixed_v133_commit':current_status_json.get('fixed_v133_commit'),
        'v134_current_status_fixed_v133_commit_wrong':current_status_json.get('fixed_v133_commit')!='b522894725f159a2a585eafe27c73dd6275894f3',
        'missing_expected_files':missing,
        'science_verdict':'PARTIAL_UNQUALIFIED__NO_REPORTABLE_SIZE_CERTIFIED',
        'notes':[
            'New v135 profiles use a separate function, identity unknown: cross-implementation residuals are not same-objective proofs.',
            'V133 six F2 candidate values remain reusable only after runtime/model/observation replays.',
            'Truth labels are for external scoring only and must not reach formal estimator.',
        ],
    }


def main():
    a=argparse.ArgumentParser()
    a.add_argument('--repo',required=True)
    a.add_argument('--out',required=True)
    x=a.parse_args()
    result=audit(Path(x.repo))
    target=Path(x.out);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'science_verdict':result['science_verdict'],
                      'F2_size_target_pass':len(result['v133_locked_F2_candidate_statistics']['target_pass_cases']),
                      'unsafe_V134_acceptance':result['v134_published_reportable_true'],
                      'unqualified_v135_profiles':len(result['v135_new_profiles'])},ensure_ascii=False))
    return 0 # Audit completed; NOT a scientific PASS.

if __name__=='__main__':raise SystemExit(main())
