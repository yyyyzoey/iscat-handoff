#!/usr/bin/env python3
"""Read-only evidence audit of fixed V137 publication. NOT a science PASS.

All conclusions are about published text files unless the actual raw data have
separately passed a byte-level original-solve and observation-operator audit.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, subprocess
from pathlib import Path

FIXED = '0b64405596a7b77ad48aec26db85ca0eee495654'
M_CASES = [f'M{i:02d}' for i in range(1, 7)]


def read_csv(path):
    with Path(path).open('r', encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def assess(rows, config=None):
    config = config or {}
    counts = {}
    for condition in ('default_zero_shift', 'at_offset_nonzero_shift'):
        selected = [r for r in rows if r['condition'] == condition]
        x = [float(r['relative_L2']) for r in selected]
        counts[condition] = {
            'cases': [r['case'] for r in selected], 'n': len(x),
            'qualified': sum(r['verdict'] == 'RENDER_F2_QUALIFIED_1PCT' for r in selected),
            'relative_L2_min': min(x) if x else None,
            'relative_L2_max': max(x) if x else None,
            'relative_L2_mean': sum(x) / len(x) if x else None,
        }
    return counts


def audit(repo: Path):
    repo = Path(repo).resolve()
    p = lambda rel: repo / rel
    needed = [
        'results/v137/status.json', 'results/v137_r1/status.json',
        'results/v137/validation/same_solve_shift_F2.csv',
        'results/v137/validation/physical_forward_qualification.json',
        'results/v137/validation/reportability_per_particle.json',
        'results/v137/validation/development_error_envelope.json',
        'results/v137/validation/threshold_validation.json',
        'results/v137/logs/resource_budget.csv',
        'results/v137_r1/logs/resource_budget.csv',
        'tools/v137_w2_same_solve.py', 'tools/v137_w4_dev_envelope.py',
        'tools/v137_w5_w6_camera_motion.py', 'tools/v137_w6_multiframe_refit.py',
        'tools/v137r1_check_return.py', 'config/v131_science_config.json'
    ]
    for x in needed:
        if not p(x).is_file():
            raise FileNotFoundError(f'published evidence missing: {x}')
    s0, s1 = read_json(p(needed[0])), read_json(p(needed[1]))
    rows = read_csv(p('results/v137/validation/same_solve_shift_F2.csv'))
    cmp_ = assess(rows)
    if len(rows) != 12 or sorted(set(r['case'] for r in rows)) != M_CASES:
        raise ValueError('Expected six M cases with two raw comparisons each; source table differs')
    gate = read_json(p('results/v137/validation/reportability_per_particle.json'))
    if set(gate) != set(M_CASES):
        raise ValueError('Published M quality cases incomplete')
    env = read_json(p('results/v137/validation/development_error_envelope.json'))
    thresholds = read_json(p('results/v137/validation/threshold_validation.json'))
    budgets = {}
    for name in ('v137', 'v137_r1'):
        q = read_csv(p(f'results/{name}/logs/resource_budget.csv'))
        end = q[-1]
        budgets[name] = {
            'last_row': end['event'],
            'f2_calls_reported': int(end['f2_canonical_calls']),
            'camera_exposure_events_reported': int(end['camera_exposure_events']),
        }
        if int(end['camera_exposure_events']) < 0 or int(end['f2_canonical_calls']) < 0:
            raise ValueError('Negative resource total')
    reg = read_json(p('config/v131_science_config.json'))
    devsrc = p('tools/v137_w4_dev_envelope.py').read_text(encoding='utf-8-sig')
    physrc = p('tools/v137_w2_same_solve.py').read_text(encoding='utf-8-sig')
    mot0 = p('tools/v137_w5_w6_camera_motion.py').read_text(encoding='utf-8-sig')
    multsrc = p('tools/v137_w6_multiframe_refit.py').read_text(encoding='utf-8-sig')
    arcsrc = p('tools/v137r1_check_return.py').read_text(encoding='utf-8-sig')
    fpr = {key: {'n': int(x['n']), 'k': int(x['k']),
                 'cp95_upper_one_sided': float(x['cp95_upper_one_sided']),
                 'published_qualifies': bool(x['qualifies_0_of_60'])}
           for key, x in thresholds['independent_validation'].items()}
    # All profile/reportability evidence must remain fail-closed at this stage.
    issued = [k for k in M_CASES if gate[k].get('reportable_D') is not None]
    mismatches = []
    # A same-file invariant of C=(Itotal-Iref)/Iref cannot use arrays leaked
    # from a later render of the same case. Detect the suspect coding pattern.
    if "Cdef_id=np.max(np.abs(Cdef-(Itot-Iref)/Iref))" in physrc:
        mismatches.append('RAW_RENDER_DEFAULT_C_CHECK_USES_LAST_LOOP_ITOTAL_IREF')
    if "Y=np.asarray(hf[case]['C'][()],float)" in devsrc and reg['inputs']['observation_dataset'] == 'at_offset/C':
        mismatches.append('DEV_ERROR_ENVELOPE_MAY_COMPARE_ROOT_C_TO_OFFSET_THETA')
    if "p0=[tr['D']]" in mot0:
        mismatches.append('ORIGINAL_SUPERSEDED_MOTION_ESTIMATOR_WAS_INITIALIZED_WITH_GENERATOR_TRUE_D')
    if "sin(2*np.pi" in mot0 or "np.sin(2*np.pi" in mot0:
        mismatches.append('SAVED_MOTION_GENERATOR_IS_DETERMINISTIC_SINUSOID_NOT_BROWNIAN')
    if 'whitening=' not in multsrc and 'joint background' not in multsrc:
        mismatches.append('FINAL_SHARED_D_REFIT_HAS_NO_EXPLICIT_SHARED_REFERENCE_COVARIANCE')
    if "<0:pass" in arcsrc:
        mismatches.append('R1_ARCHIVE_PROFILE_REPLAY_CHECK_IS_DEAD_CONDITION')
    if "'work/repo/tools'" in arcsrc:
        mismatches.append('R1_ARCHIVE_REPLAY_CHECK_HARDCODES_LOCAL_PATH')
    v137_budget = budgets['v137_r1']
    if v137_budget['camera_exposure_events_reported'] > 6000:
        mismatches.append('V137_CAMERA_HARD_LIMIT_BREACH_NOT_CURED_BY_R1')
    if env['epsilon_dev_L2'] >= 0.01:
        mismatches.append('OLD_DEV_EPSILON_TOO_LARGE_FOR_SIZING_NEEDS_OBSERVATION_IDENTITY_AUDIT')
    # Fixed Git release can be checked even while checking out a descendant.
    head = subprocess.run(['git','-C',str(repo),'rev-parse','HEAD'],capture_output=True,text=True,check=False)
    r = {
        'schema': 'iscat138.v137_published_audit.1',
        'scope': 'PUBLISHED_TEXT_AND_SOURCE_STATIC_AUDIT_NOT_RAW_MAT_PHYSICS',
        'fixed_v137_commit': FIXED,
        'local_checkout_head': head.stdout.strip() if head.returncode == 0 else None,
        'original_status_execution': s0.get('execution'),
        'r1_status_execution': s1.get('execution'),
        'direct_render_vs_F2': cmp_,
        'reported_qualified_unique_sizes': issued,
        'all_M_reportable_null': not bool(issued),
        'development_error_envelope': env,
        'fpr_as_published': fpr,
        'v137_resource_history': budgets,
        'diagnostic_source_flags': mismatches,
        'source_files_sha256': {x: sha(p(x)) for x in needed},
        'verdict': 'V137_PARTIAL__PHYSICAL_SOURCE_UNRESOLVED__BUDGET_BREACH__NO_SIZE_CERTIFIED',
        'next_gate': 'RAW_RENDER_MAT_VS_MERGED_H5_AND_SAME_SOLVE_FIELD_OPERATOR_FIRST',
    }
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    obj = audit(Path(a.repo))
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'verdict': obj['verdict'],
                      'direct_render_gate': obj['direct_render_vs_F2'],
                      'camera_exposure_events': obj['v137_resource_history']['v137_r1']['camera_exposure_events_reported'],
                      'source_flags': obj['diagnostic_source_flags']}, indent=2, ensure_ascii=False))
    return 0  # Successful audit != scientific PASS

if __name__ == '__main__':
    raise SystemExit(main())
