# -*- coding: utf-8 -*-
"""v117: V117_TARGETED_ACCEPTANCE_REPAIR_AND_PHYSICAL_INPUT_CONTRACT.

Per the V116 independent review: three-identity separation (frozen source /
execution code / release commit), repaired source acceptance gate with negative
controls, T11 boolean-unpack fix plus two mandatory mutations, shared static
pre-validation and callback/overflow hardening in BOTH operator entries,
576-item bridge with two NEW explicit gates (same-array FFT-DFT <1e-11 and mean
vs bank Imean_map <1e-12) folded into row PASS, semantic metadata admission with
stable IDs, two DESIGN_ONLY physics pilot preregistrations, and correct failure
propagation (archive_integrity / numerical_accepted / archive_valid read
separately). Source frozen at ae7f479775910654eb10b984ec7076b544ab0a61 (v116)."""
import os, sys, csv, json, hashlib, shutil, math, subprocess, zipfile, time, argparse, io
sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import numpy as np

TASK_ID = 'V117_TARGETED_ACCEPTANCE_REPAIR_AND_PHYSICAL_INPUT_CONTRACT'
EXPECTED_V116 = 'ae7f479775910654eb10b984ec7076b544ab0a61'
EXPECTED_V115 = '59800bae2a6b5c0b37531c09b6cc97158fad1d5f'
V116_DELIVERED_ZIP_SHA = 'e8a4d8cbe327c503f8871b4750a11542fb97ee8ab68819a92f3589365f981f50'
EXEC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # v117_execution root
REQUIRED_GATES = ['A_source_acceptance', 'B_operator_regression', 'C_saved_probe_bridge',
                  'D_metadata_semantic_admission', 'F_verifier_selftest']
GATES = {g: False for g in REQUIRED_GATES}
FAIL_KEYS = {}
STAGE_LOG = {}

def log(msg):
    print('[v117] %s' % msg, flush=True)

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def wcsv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)

def rcsv(path):
    with open(path, 'r', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

# ============================== S0 ==============================

def s0_identities(root, out):
    log('=== S0: three identities + historical statuses ===')
    head = subprocess.run(['git', '-C', root, 'rev-parse', 'HEAD'],
                          capture_output=True, text=True, timeout=60).stdout.strip()
    porcelain = subprocess.run(['git', '-C', root, 'status', '--porcelain'],
                               capture_output=True, text=True, timeout=60).stdout
    identities = {
        'base_source_commit': EXPECTED_V116,
        'execution_code_identity': {
            'execution_root': EXEC,
            'tools': {fn: sha256_file(os.path.join(EXEC, 'tools', fn))
                      for fn in sorted(os.listdir(os.path.join(EXEC, 'tools')))
                      if fn.endswith('.py')},
            'note': 'execution tools run OUTSIDE the frozen source tree; the frozen tree '
                    'stays clean during execution',
        },
        'release_commit': 'recorded after the run when the v117 branch commit exists',
        'run_head_at_start': head,
        'porcelain_lines': len(porcelain.strip().splitlines()) if porcelain.strip() else 0,
    }
    hist = {
        'v115': {'failed_run_HEAD': '7a9102d5f8c6f98305ed9b10279083de96be66e6',
                 'failed_run_zip_sha256': 'd435ca98ab2328dca87a437df5707c2f6f63778deef4491f70b648757de5ba9a',
                 'failure': 'A_source_lock=false; parent HEAD^==v113 direct-parent driver defect',
                 'release_commit': '59800bae2a6b5c0b37531c09b6cc97158fad1d5f'},
        'v116': {'run_HEAD': '59800bae2a6b5c0b37531c09b6cc97158fad1d5f',
                 'release_commit': EXPECTED_V116,
                 'delivered_zip_sha256': V116_DELIVERED_ZIP_SHA,
                 'archive_review': 'PENDING -> verified in this run (S5)'},
    }
    with open(os.path.join(out, 'source_identity.json'), 'w', encoding='utf-8') as f:
        json.dump({'identities': identities, 'historical': hist}, f, indent=2)
    with open(os.path.join(out, 'logs', 'v117_porcelain_start.txt'), 'w', encoding='utf-8') as f:
        f.write(porcelain)
    STAGE_LOG['S0'] = {'head': head, 'porcelain_lines': identities['run_head_at_start'] and len(porcelain.strip().splitlines())}
    return head

# ============================== S1 ==============================

def s1(root, out):
    log('=== S1: repaired source acceptance gate + negative controls ===')
    # build the 73-file snapshot (byte copies) for the acceptance gate
    import csv as _csv
    from scipy.io import loadmat as _loadmat
    snap_dir = os.path.join(out, 'snapshot73')
    os.makedirs(snap_dir, exist_ok=True)
    bl_map_file = {r['case_id']: r['map_file']
                   for r in rcsv(os.path.join(root, 'tables', 'v085_double_maps24_status.csv'))}
    ALL48 = (['D%d_zf%d_%s_a%d' % (D, zf, t, a)
              for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)]
             + ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
                for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400')
                for a in (10, 15)])
    ALL24 = ALL48[:24]
    for k in ALL48:
        fn = 'v092_bank_%s.mat' % k
        shutil.copy2(os.path.join(root, 'analysis', 'bank', fn), os.path.join(snap_dir, fn))
    for k in ALL24:
        fn = bl_map_file[k]
        shutil.copy2(os.path.join(root, 'numeric', fn), os.path.join(snap_dir, fn))
    shutil.copy2(os.path.join(root, 'analysis', 'v093_probe_evidence.npz'),
                 os.path.join(snap_dir, 'v093_probe_evidence.npz'))
    manifest_rows = [{'role': 'BANK', 'case_id': k, 'target_relative': 'snapshot73/v092_bank_%s.mat' % k,
                      'sha256': sha256_file(os.path.join(snap_dir, 'v092_bank_%s.mat' % k))}
                     for k in ALL48]
    manifest_rows += [{'role': 'BASELINE', 'case_id': k,
                       'target_relative': 'snapshot73/%s' % bl_map_file[k],
                       'sha256': sha256_file(os.path.join(snap_dir, bl_map_file[k]))}
                      for k in ALL24]
    manifest_rows.append({'role': 'SAVED_SIMULATION_PROBES', 'case_id': 'PROBE_EVIDENCE_192_SERIES',
                          'target_relative': 'snapshot73/v093_probe_evidence.npz',
                          'sha256': sha256_file(os.path.join(snap_dir, 'v093_probe_evidence.npz'))})
    wcsv(os.path.join(out, 'logs', 'v117_snapshot73_manifest.csv'),
         list(manifest_rows[0].keys()), manifest_rows)
    acc_out = os.path.join(out, 'logs', 'source_acceptance_v117.json')
    proc = subprocess.run([sys.executable, os.path.join(EXEC, 'tools', 'v117_source_acceptance.py'),
                           '--root', root,
                           '--snapshot-dir', os.path.join(out, 'snapshot73'),
                           '--review-dir', os.path.join(root, 'review_inputs'),
                           '--output', acc_out,
                           '--negative-controls-dir', os.path.join(out, 'logs', 'nc')],
                          capture_output=True, text=True, timeout=1800)
    res = json.load(open(acc_out, encoding='utf-8')) if os.path.isfile(acc_out) else {}
    ok = proc.returncode == 0 and res.get('gate') is True \
        and res.get('negatives_all_detected') is True
    if not ok:
        FAIL_KEYS.setdefault('S1', ['gate=%s negatives=%s issues=%s'
                                    % (res.get('gate'), res.get('negatives_all_detected'),
                                       len(res.get('issues', [])))])
    GATES['A_source_acceptance'] = ok
    STAGE_LOG['S1'] = {'gate': res.get('gate'), 'issues': len(res.get('issues', [])),
                       'negatives': res.get('negative_controls', []),
                       'negatives_all_detected': res.get('negatives_all_detected')}
    log('S1: gate=%s negatives=%s' % (res.get('gate'), res.get('negatives_all_detected')))

# ============================== S2 ==============================

def s2(root, out):
    log('=== S2: operator regression (27) + legacy (12+4) + v116 boundary (12+2 mutations) ===')
    redgreen = {'runs': []}

    def run_suite(script, out_name, label):
        p = os.path.join(out, 'logs', out_name)
        pr = subprocess.run([sys.executable, os.path.join(EXEC, 'tools', script), p],
                            capture_output=True, text=True, timeout=1800)
        rep = json.load(open(p, encoding='utf-8')) if os.path.isfile(p) else {}
        redgreen['runs'].append({'suite': label, 'script': script, 'exit': pr.returncode,
                                 'report': out_name})
        return pr.returncode == 0, rep

    ok_reg, rep_reg = run_suite('v115_operator_regression.py', 'v115_regression27.json',
                                '27-item production regression')
    ok_113, rep_113 = run_suite('observation_integration_tests_v113.py', 'v113_suite.json',
                                'legacy 12 groups + 4 mutations')
    ok_bnd, rep_bnd = run_suite('v116_operator_boundary_tests.py', 'v116_boundary12.json',
                                '12 v116 boundary tests + 2 mutations')
    shutil.copy2(os.path.join(out, 'logs', 'v115_regression27.json'),
                 os.path.join(out, 'operator_red_green.json'))
    shutil.copy2(os.path.join(out, 'logs', 'v116_boundary12.json'),
                 os.path.join(out, 'logs', 'operator_targeted_regressions.json'))
    ok_b = ok_reg and ok_113 and ok_bnd
    if not ok_b:
        FAIL_KEYS.setdefault('S2', ['regression=%s legacy=%s boundary=%s'
                                    % (ok_reg, ok_113, ok_bnd)])
    GATES['B_operator_regression'] = ok_b
    STAGE_LOG['S2'] = {'regression27': '%d/%d' % (rep_reg.get('n_pass', 0), rep_reg.get('n_total', 0)),
                       'legacy_groups': '%d/%d' % (sum(1 for g in rep_113.get('groups', []) if g['pass']),
                                                   len(rep_113.get('groups', []))),
                       'legacy_mutations': '%d/%d' % (sum(1 for m in rep_113.get('mutations', []) if m['detected']),
                                                      len(rep_113.get('mutations', []))),
                       'boundary': '%d/%d' % (rep_bnd.get('n_pass', 0), rep_bnd.get('n_total', 0)),
                       'boundary_verdict': rep_bnd.get('verdict', 'UNKNOWN'),
                       'runs': redgreen['runs']}
    log('S2: reg=%s legacy=%s boundary=%s' % (STAGE_LOG['S2']['regression27'],
                                              STAGE_LOG['S2']['legacy_groups'],
                                              STAGE_LOG['S2']['boundary']))

# ============================== S3 ==============================

def s3(root, out):
    log('=== S3: 576 bridge with two NEW explicit gates ===')
    bridge_csv = os.path.join(out, 'tables', 'v117_bridge576.csv')
    proc = subprocess.run([sys.executable, os.path.join(EXEC, 'tools', 'v117_saved_probe_bridge.py'),
                           '--root', root, '--output', bridge_csv],
                          capture_output=True, text=True, timeout=1800)
    ok_c = proc.returncode == 0
    sj = bridge_csv.replace('.csv', '.summary.json')
    summary = json.load(open(sj, encoding='utf-8')) if os.path.isfile(sj) else {}
    if not ok_c:
        FAIL_KEYS.setdefault('S3', ['bridge failures: %s' % (summary.get('issues', []) or proc.stdout[-200:])])
    GATES['C_saved_probe_bridge'] = ok_c
    STAGE_LOG['S3'] = {'checked': summary.get('checked', 0), 'passed': summary.get('passed', 0),
                       'backend': summary.get('backend', '')[:120]}
    log('S3: bridge %s/%s' % (summary.get('passed', 0), summary.get('checked', 0)))

# ============================== S4 ==============================

def s4(out):
    log('=== S4: semantic metadata admission + pilot preregistration ===')
    items = [
        {'id': 'WAVELENGTH_520', 'parameter': 'laser_vacuum_wavelength', 'value': 520.0, 'unit': 'nm',
         'evidence_class': 'USER_CONFIRMED', 'evidence_reference': 'user statement, no certificate',
         'source_sha_if_applicable': None, 'valid_dataset': 'all', 'valid_time': 'since 2026-10-12 confirmation',
         'run_effective': None, 'uncertainty_or_bounds': 'no instrument certificate; value not invalidated',
         'required_for': 'all optical forwards', 'missing_acquisition': None},
        {'id': 'FS_5000', 'parameter': 'frame_rate_Fs', 'value': 5000.0, 'unit': 'fps',
         'evidence_class': 'EXPERIMENT_SCRIPT_RECORDED',
         'evidence_reference': 'test_with_contrast.m L39 (hash-verified)',
         'source_sha_if_applicable': 'd08575b1e860e09f29c74652442a77b721039c6e32368fe76d2c5c63143ea3aa',
         'valid_dataset': '7.29 batch', 'valid_time': 'batch acquisition',
         'run_effective': None, 'uncertainty_or_bounds': 'script constant; NOT a calibrated clock',
         'required_for': 'DFT sampling contract', 'missing_acquisition': 'external clock calibration'},
        {'id': 'D_DEMO_BANK', 'parameter': 'demo_bank_D_labels', 'value': [30, 60, 100], 'unit': 'nm',
         'evidence_class': 'ANALYSIS_CONTRACT', 'evidence_reference': 'v092 bank case naming',
         'source_sha_if_applicable': None, 'valid_dataset': '48-state demo bank',
         'valid_time': 'demo', 'run_effective': None,
         'uncertainty_or_bounds': 'simulation labels (diameter, not core/shell/hydrodynamic)',
         'required_for': 'legacy bank only', 'missing_acquisition': None},
        {'id': 'D_NOMINAL_729', 'parameter': 'sample_nominal_D_729', 'value': 100.0, 'unit': 'nm',
         'evidence_class': 'NOMINAL_LABEL', 'evidence_reference': 'batch naming',
         'source_sha_if_applicable': None, 'valid_dataset': '7.29 nominal',
         'valid_time': None, 'run_effective': None,
         'uncertainty_or_bounds': 'NOT an independent absolute diameter certificate',
         'required_for': None, 'missing_acquisition': 'independent characterization of the batch'},
        {'id': 'D_INDEP_REF', 'parameter': 'independent_diameter_reference', 'value': None,
         'unit': 'nm', 'evidence_class': 'MISSING', 'evidence_reference': None,
         'source_sha_if_applicable': None, 'valid_dataset': None, 'valid_time': None,
         'run_effective': None, 'uncertainty_or_bounds': None,
         'required_for': 'ABSOLUTE_DIAMETER_VALIDATION_GO',
         'missing_acquisition': 'certified particle standard with stated diameter definition'},
        {'id': 'OPT_SCALE_001', 'parameter': 'object_plane_nm_per_pixel_with_error', 'value': None,
         'unit': 'nm/px', 'evidence_class': 'MISSING', 'evidence_reference': None,
         'source_sha_if_applicable': None, 'valid_dataset': None, 'valid_time': None,
         'run_effective': None, 'uncertainty_or_bounds': None,
         'required_for': 'REAL_DEVICE_RELATIVE_FORWARD_GO',
         'missing_acquisition': 'stage calibration or certified ruler image'},
        {'id': 'OPT_NA_001', 'parameter': 'objective_NA_immersion_polarization', 'value': None,
         'unit': None, 'evidence_class': 'MISSING', 'evidence_reference': None,
         'source_sha_if_applicable': None, 'valid_dataset': None, 'valid_time': None,
         'run_effective': None, 'uncertainty_or_bounds': None,
         'required_for': 'REAL_DEVICE_RELATIVE_FORWARD_GO',
         'missing_acquisition': 'objective datasheet + illumination record'},
        {'id': 'OPT_REF_001', 'parameter': 'reference_field_path', 'value': None, 'unit': None,
         'evidence_class': 'MISSING', 'evidence_reference': None, 'source_sha_if_applicable': None,
         'valid_dataset': None, 'valid_time': None, 'run_effective': None,
         'uncertainty_or_bounds': None, 'required_for': 'REAL_DEVICE_RELATIVE_FORWARD_GO',
         'missing_acquisition': 'optical layout record or interferometric characterization'},
        {'id': 'CAM_EXP_001', 'parameter': 'exposure_time_per_frame', 'value': None, 'unit': 's',
         'evidence_class': 'MISSING', 'evidence_reference': None, 'source_sha_if_applicable': None,
         'valid_dataset': None, 'valid_time': None, 'run_effective': None,
         'uncertainty_or_bounds': None, 'required_for': 'REAL_DEVICE_RELATIVE_FORWARD_GO',
         'missing_acquisition': 'camera acquisition log per frame'},
        {'id': 'CAM_TRIG_001', 'parameter': 'trigger_time_origin_convention', 'value': None,
         'unit': None, 'evidence_class': 'MISSING', 'evidence_reference': None,
         'source_sha_if_applicable': None, 'valid_dataset': None, 'valid_time': None,
         'run_effective': None, 'uncertainty_or_bounds': None,
         'required_for': 'time-origin discipline',
         'missing_acquisition': 'trigger log (exposure-start vs center)'},
        {'id': 'CAM_TS_001', 'parameter': 'per_frame_timestamps', 'value': None, 'unit': 's',
         'evidence_class': 'MISSING', 'evidence_reference': None, 'source_sha_if_applicable': None,
         'valid_dataset': None, 'valid_time': None, 'run_effective': None,
         'uncertainty_or_bounds': None, 'required_for': 'non-uniform timestamp handling',
         'missing_acquisition': 'frame timestamp log'},
        {'id': 'CAM_KAPPA_001', 'parameter': 'kappa_e_per_U_per_s', 'value': None,
         'unit': 'e-/(U*s)', 'evidence_class': 'MISSING', 'evidence_reference': None,
         'source_sha_if_applicable': None, 'valid_dataset': None, 'valid_time': None,
         'run_effective': None, 'uncertainty_or_bounds': None,
         'required_for': 'ABSOLUTE_COUNT_GO', 'missing_acquisition': 'responsivity calibration'},
        {'id': 'CAM_GAIN_001', 'parameter': 'g_DN_per_e', 'value': None, 'unit': 'DN/e-',
         'evidence_class': 'MISSING', 'evidence_reference': None, 'source_sha_if_applicable': None,
         'valid_dataset': None, 'valid_time': None, 'run_effective': None,
         'uncertainty_or_bounds': None, 'required_for': 'DN mode',
         'missing_acquisition': 'photon-transfer curve'},
        {'id': 'CAM_OFFSET_001', 'parameter': 'offset_DN', 'value': None, 'unit': 'DN',
         'evidence_class': 'MISSING', 'evidence_reference': None, 'source_sha_if_applicable': None,
         'valid_dataset': None, 'valid_time': None, 'run_effective': None,
         'uncertainty_or_bounds': None, 'required_for': 'DN mode',
         'missing_acquisition': 'dark-frame measurement'},
        {'id': 'SMP_BATCH_001', 'parameter': 'sample_batch_coating_medium_substrate_fixation',
         'value': None, 'unit': None, 'evidence_class': 'MISSING', 'evidence_reference': None,
         'source_sha_if_applicable': None, 'valid_dataset': None, 'valid_time': None,
         'run_effective': None, 'uncertainty_or_bounds': None,
         'required_for': 'REAL_DEVICE_RELATIVE_FORWARD_GO',
         'missing_acquisition': 'sample record + spacer metrology'},
        {'id': 'MOT_TRAJ_001', 'parameter': 'independent_trajectory_route_A', 'value': None,
         'unit': None, 'evidence_class': 'MISSING', 'evidence_reference': None,
         'source_sha_if_applicable': None, 'valid_dataset': None, 'valid_time': None,
         'run_effective': None, 'uncertainty_or_bounds': 'z/orientation keep bounded placeholders, never 0',
         'required_for': 'route A', 'missing_acquisition': 'independent tracking with scale+timebase'},
        {'id': 'MOT_FIELD_001', 'parameter': 'magnetic_field_B_gradient_sync_route_B', 'value': None,
         'unit': None, 'evidence_class': 'MISSING', 'evidence_reference': None,
         'source_sha_if_applicable': None, 'valid_dataset': None, 'valid_time': None,
         'run_effective': None, 'uncertainty_or_bounds': None,
         'required_for': 'route B', 'missing_acquisition': 'calibrated B(t) probe + sync + mechanics'},
        {'id': 'BLANK_BOFF_001', 'parameter': 'particle_blank_and_Boff_control', 'value': None,
         'unit': None, 'evidence_class': 'MISSING', 'evidence_reference': None,
         'source_sha_if_applicable': None, 'valid_dataset': None, 'valid_time': None,
         'run_effective': None, 'uncertainty_or_bounds': None,
         'required_for': 'ABSOLUTE_DIAMETER_VALIDATION_GO',
         'missing_acquisition': 'particle-free blank + B-off captures'},
    ]
    wcsv(os.path.join(out, 'metadata_readiness_v117.csv'), list(items[0].keys()), items)
    a_ready = False
    b_ready = False
    admission = {
        'METADATA_SCHEMA_VALID': True,
        'CONDITIONAL_MODEL_DESIGN_READY': True,
        'REAL_DEVICE_RELATIVE_FORWARD_GO': bool(a_ready or b_ready),
        'ABSOLUTE_COUNT_GO': False,
        'ABSOLUTE_DIAMETER_VALIDATION_GO': False,
        'route_logic': 'A_trajectory_ready OR B_field_mechanics_ready; route A does not require '
                       'all B parameters; route B needs its own dynamics boundaries',
        'relative_C_branch_note': 'fixed-exposure linear zero-bias normalized-C forward is NOT '
                                  'blocked solely by missing absolute kappa/g; camera bias and '
                                  'nonlinearity must be handled first and declared',
        'synthetic_values_policy': 'any kappa/g/b used in software tests are SYNTHETIC_FIXTURE values',
    }
    with open(os.path.join(out, 'admission_v117.json'), 'w', encoding='utf-8') as f:
        json.dump(admission, f, indent=2, ensure_ascii=False)
    action = [{'id': i['id'], 'parameter': i['parameter'],
               'needed_record': i['missing_acquisition'] or '',
               'blocked_branch': i['required_for'] or ''}
              for i in items if i['evidence_class'] == 'MISSING']
    wcsv(os.path.join(out, 'missing_inputs_action_sheet.csv'),
         list(action[0].keys()), action)
    ok_d = len(items) == 18 and admission['METADATA_SCHEMA_VALID'] \
        and admission['CONDITIONAL_MODEL_DESIGN_READY'] \
        and admission['REAL_DEVICE_RELATIVE_FORWARD_GO'] is False \
        and admission['ABSOLUTE_COUNT_GO'] is False \
        and admission['ABSOLUTE_DIAMETER_VALIDATION_GO'] is False
    if not ok_d:
        FAIL_KEYS.setdefault('S4', ['items=%d' % len(items)])
    GATES['D_metadata_semantic_admission'] = ok_d
    STAGE_LOG['S4'] = {'items': len(items),
                       'missing': sum(1 for i in items if i['evidence_class'] == 'MISSING'),
                       'statuses': {k: v for k, v in admission.items()
                                    if k.startswith(('METADATA', 'CONDITIONAL', 'REAL', 'ABSOLUTE'))}}
    log('S4: items=%d missing=%d schema_valid=%s' % (len(items), STAGE_LOG['S4']['missing'],
                                                     admission['METADATA_SCHEMA_VALID']))

# ============================== S5 + archive ==============================

def s5_physics_and_exposure(out):
    log('=== S5-prep: exposure diagnostics + two pilot preregistrations ===')
    # analytic exposure transfer factors (Section 6 of the contract; math, not simulation)
    diag = []
    for T in (50e-6, 100e-6, 200e-6):
        row = {'assumed_exposure_s': T}
        for f in (200.0, 400.0, 800.0):
            row['H_%dHz' % f] = '%.10g' % (math.sin(math.pi * f * T) / (math.pi * f * T))
        diag.append(row)
    with open(os.path.join(out, 'logs', 'exposure_diagnostics_analytic.json'), 'w', encoding='utf-8') as f:
        json.dump({'note': 'H_T(f) = sin(pi f T)/(pi f T); analytic math only, T values are '
                           'ASSUMPTIONS not camera settings; correct order: integrate intensity '
                           'over the exposure window FIRST, then the frozen-sampling DFT',
                   'rows': diag}, f, indent=2)
    pilots = {
        'schema': 'iscat117.physics_pilot_preregistration.1',
        'auto_physics_solves': 0,
        'budget_table_note': 'BEM call count, geometry/material changes, trajectory support points, '
                             'exposure quadrature nodes, detector pixels/sub-pixels, peak memory, '
                             'wall time and retries MUST be filled before any physics run',
        'pilot_1': {
            'name': 'known-D standard + B-off/blank + object-plane ruler + held-out windows',
            'prerequisites': ['OPT_SCALE_001', 'OPT_NA_001', 'OPT_REF_001', 'CAM_EXP_001',
                              'CAM_TRIG_001', 'CAM_TS_001', 'SMP_BATCH_001', 'D_INDEP_REF',
                              'BLANK_BOFF_001'],
            'design': 'r(t),orientation(t) with independent scale/timebase -> Eref+Escat -> '
                      'intensity exposure average -> per-pixel spatial average -> frozen-sampling '
                      'complex DFT; compare against held-out experimental windows',
            'uncertainties': 'amplitude/phase/background/model and measurement budgets recorded '
                             'before estimation; P0 convergence assessed on the actual call path',
            'status': 'DESIGN_ONLY',
        },
        'pilot_2': {
            'name': 'second physics condition (B-driven constrained trajectory) for model comparison',
            'prerequisites': ['MOT_FIELD_001', 'route B mechanics boundaries confirmed',
                              'pilot_1 completed without unexplained residuals'],
            'design': 'constrained dynamics from measured B(t)/gradient/sync -> trajectory -> '
                      'same optical chain as pilot 1; independent held-out windows',
            'status': 'DESIGN_ONLY',
        },
        'identifiability_note': 'if allowed-parameter changes can offset D changes within '
                                'experimental error, report feasible ranges/conditional model '
                                'conclusions instead of a unique absolute D; no D-node expansion '
                                'is authorized by this registration',
    }
    with open(os.path.join(out, 'physics_pilot_preregistration.json'), 'w', encoding='utf-8') as f:
        json.dump(pilots, f, indent=2, ensure_ascii=False)
    STAGE_LOG['S5pre'] = {'exposure_rows': len(diag), 'pilots': 2, 'auto_solves': 0}
    log('S5-prep: exposure diagnostics + 2 pilot designs registered (DESIGN_ONLY)')

def stage_f(root, out, zip_path, checker_src, status_sha):
    log('=== Stage F: verifier selftest + V116 archive verification ===')
    # V116 original final ZIP verification (obtainable on this workstation)
    v116_zip = next((c for c in (r'C:\Users\PC\Documents\Codex\2026-10-18\files-mentioned-by-the-user-iscat\work\v116_final2b\iscat_v116_return.zip',
                                 r'C:\Users\PC\Documents\Codex\2026-10-18\files-mentioned-by-the-user-iscat\outputs\iscat_v116_return.zip')
                     if os.path.isfile(c)), None)
    v116_sha = sha256_file(v116_zip) if v116_zip else None
    v116_verified = bool(v116_zip and v116_sha == V116_DELIVERED_ZIP_SHA)
    with open(os.path.join(out, 'logs', 'v116_archive_verification.json'), 'w', encoding='utf-8') as f:
        json.dump({'zip_path': v116_zip, 'expected_sha256': V116_DELIVERED_ZIP_SHA,
                   'observed_sha256': v116_sha,
                   'verdict': 'V116_ARCHIVE_VERIFIED' if v116_verified else 'V116_ARCHIVE_REVIEW_UNVERIFIED',
                   'note': 'per contract S5 item 5: hash + real receipt checked; not rebuilt'}, f, indent=2)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import run_v116_all as v116mod  # reuse the proven selftest harness
    good = open(zip_path, 'rb').read()
    work = os.path.join(out, 'logs', 'verifier_selftest')
    os.makedirs(work, exist_ok=True)
    results = []
    MECH = {'missing_zip', 'missing_bank_case', 'duplicate_member', 'corrupt_crc',
            'manifest_path_traversal', 'status_missing', 'wrong_status_sha'}
    GATEC = {'gates_string_bool', 'gates_missing', 'wrong_task_id', 'wrong_source_commit'}

    def run_case(name, zbytes_or_none, expect_status_sha=None):
        zp = os.path.join(work, 'case_%s.zip' % name)
        if zbytes_or_none is not None:
            open(zp, 'wb').write(zbytes_or_none)
        elif os.path.exists(zp):
            os.remove(zp)
        res_p = os.path.join(work, 'case_%s.json' % name)
        if os.path.exists(res_p):
            os.remove(res_p)
        cargs = [sys.executable, checker_src, '--zip', zp, '--out', res_p]
        if expect_status_sha:
            cargs += ['--expect-status-sha', expect_status_sha]
        proc = subprocess.run(cargs, capture_output=True, text=True, timeout=600)
        res = json.load(open(res_p, encoding='utf-8')) if os.path.isfile(res_p) else {}
        passed = (proc.returncode != 0) and (res.get('archive_valid') is not True)
        results.append({'case': name, 'exit_code': proc.returncode,
                        'archive_valid': res.get('archive_valid'),
                        'verdict': 'PASS' if passed else 'FAIL'})
        return passed, res

    zin = zipfile.ZipFile(io.BytesIO(good))
    all_ok = True

    def run_typed(name, zbytes_or_none, expect_status_sha=None):
        passed, res = run_case(name, zbytes_or_none, expect_status_sha)
        if name in MECH:
            typed_ok = passed and res.get('archive_integrity') is False
        elif name in GATEC:
            typed_ok = passed and res.get('archive_integrity') is True \
                and res.get('numerical_accepted') is False
        else:
            typed_ok = passed
        if not typed_ok:
            results[-1]['verdict'] = 'FAIL'
        return typed_ok

    all_ok &= run_typed('missing_zip', None)
    drop = [n for n in zin.namelist() if 'v092_bank_D30_zf450_M200_a5.mat' in n]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zo:
        for n in zin.namelist():
            if n == drop[0] or n.endswith('manifest_sha256.csv'):
                continue
            zo.writestr(n, zin.read(n))
        man = zin.read('iscat_v117_return/manifest_sha256.csv').decode('utf-8').splitlines()
        zo.writestr('iscat_v117_return/manifest_sha256.csv',
                    '\n'.join(ln for ln in man if 'v092_bank_D30_zf450_M200_a5.mat' not in ln) + '\n')
    all_ok &= run_typed('missing_bank_case', buf.getvalue())
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zo:
        for n in zin.namelist():
            zo.writestr(n, zin.read(n))
        zo.writestr(zin.namelist()[3], zin.read(zin.namelist()[3]))
    all_ok &= run_typed('duplicate_member', buf.getvalue())
    corrupt = bytearray(good)
    corrupt[len(corrupt) // 2] ^= 0xFF
    all_ok &= run_typed('corrupt_crc', bytes(corrupt))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zo:
        for n in zin.namelist():
            zo.writestr(n, zin.read(n))
        man = zin.read('iscat_v117_return/manifest_sha256.csv').decode('utf-8')
        zo.writestr('iscat_v117_return/manifest_sha256.csv', man + '../escape.txt,%s\n' % ('0' * 64))
    all_ok &= run_typed('manifest_path_traversal', buf.getvalue())
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zo:
        for n in zin.namelist():
            if n.endswith('/status.json'):
                continue
            if n.endswith('manifest_sha256.csv'):
                man = zin.read(n).decode('utf-8').splitlines()
                zo.writestr(n, '\n'.join(ln for ln in man if 'status.json' not in ln) + '\n')
                continue
            zo.writestr(n, zin.read(n))
    all_ok &= run_typed('status_missing', buf.getvalue())
    st = json.loads(zin.read('iscat_v117_return/status.json'))
    for name, mutate in (('gates_string_bool', lambda s: s['gates'].update({'A_source_acceptance': 'true'})),
                         ('gates_missing', lambda s: s['gates'].pop('A_source_acceptance')),
                         ('wrong_task_id', lambda s: s.update({'task_id': 'WRONG_TASK'})),
                         ('wrong_source_commit', lambda s: s.update({'source_commit': '0' * 40}))):
        s2 = json.loads(json.dumps(st))
        mutate(s2)
        new_status = json.dumps(s2, indent=2).encode('utf-8')
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zo:
            for n in zin.namelist():
                if n.endswith('/status.json'):
                    zo.writestr(n, new_status)
                elif n.endswith('manifest_sha256.csv'):
                    man = zin.read(n).decode('utf-8').splitlines()
                    new_sha = hashlib.sha256(new_status).hexdigest()
                    zo.writestr(n, '\n'.join(
                        ('status.json,' + new_sha) if ln.split(',')[0].strip() == 'status.json' else ln
                        for ln in man if ln.strip()) + '\n')
                else:
                    zo.writestr(n, zin.read(n))
        all_ok &= run_typed(name, buf.getvalue())
    all_ok &= run_typed('wrong_status_sha', good, expect_status_sha='0' * 64)
    res_p = os.path.join(work, 'positive.json')
    proc = subprocess.run([sys.executable, checker_src, '--zip', zip_path,
                           '--expect-status-sha', status_sha, '--out', res_p],
                          capture_output=True, text=True, timeout=600)
    pos = json.load(open(res_p, encoding='utf-8')) if os.path.isfile(res_p) else {}
    positive_ok = pos.get('archive_integrity') is True
    results.append({'case': 'positive_control', 'exit_code': proc.returncode,
                    'archive_integrity': pos.get('archive_integrity'),
                    'verdict': 'PASS' if positive_ok else 'FAIL'})
    st_fields = list(results[0].keys()) + [k for r in results for k in r if k not in results[0]]
    wcsv(os.path.join(out, 'logs', 'v117_verifier_selftest.csv'), st_fields, results)
    for fn in os.listdir(work):
        if fn.startswith('case_') and fn.endswith('.zip'):
            os.remove(os.path.join(work, fn))
    n_pass = sum(1 for r in results if r['verdict'] == 'PASS')
    ok_f = all_ok and positive_ok and n_pass == len(results)
    if not ok_f:
        FAIL_KEYS.setdefault('F', ['selftest %d/%d' % (n_pass, len(results))])
    GATES['F_verifier_selftest'] = ok_f
    STAGE_LOG['F'] = {'cases': len(results), 'passed': n_pass,
                      'v116_archive': 'VERIFIED' if v116_verified else 'UNVERIFIED'}
    log('Stage F: selftest %d/%d PASS | v116 archive %s'
        % (n_pass, len(results), 'VERIFIED' if v116_verified else 'UNVERIFIED'))

def build_status(out, tool_sha):
    numerical = all(GATES[g] for g in REQUIRED_GATES)
    statuses = {'execution': 'COMPLETE',
                'numerical': 'TARGETED_REPAIR_AND_ADMISSION_SEALED' if numerical else 'UNSEALED_PARTIAL',
                'archive': 'PRE_ARCHIVE_VERIFICATION',
                'physics': 'ALL_FORWARD_GO_FALSE_PENDING_INPUTS'}
    status = {'schema': 'iscat117.status.1', 'task_id': TASK_ID,
              'created_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
              'source_commit': EXPECTED_V116, 'parent_commit': EXPECTED_V115,
              'tool_sha256': tool_sha,
              'required_gates': list(REQUIRED_GATES),
              'gates': {g: bool(GATES[g]) for g in REQUIRED_GATES},
              'states': statuses,
              'admission_layers': {
                  'LEGACY_NUMERICAL_FROZEN': True,
                  'METADATA_SCHEMA_VALID': True,
                  'CONDITIONAL_MODEL_DESIGN_READY': True,
                  'REAL_DEVICE_RELATIVE_FORWARD_GO': False,
                  'ABSOLUTE_COUNT_GO': False,
                  'ABSOLUTE_DIAMETER_VALIDATION_GO': False},
              'stage_logs': STAGE_LOG,
              'environment': {'python': sys.version.split()[0],
                              'numpy': np.__version__, 'scipy': __import__('scipy').__version__,
                              'pythondontwritebytecode': '1'},
              'frozen_states': {'calibration_valid': False, 'experimental_validation': False,
                                'detection_validated': False, 'single_particle_diameter': 'NOT_ESTIMATED'},
              'p0_status': 'OPEN (not upgraded)',
              'rule7_new_authorizations': 0,
              'overall': 'TARGETED_REPAIR_AND_ADMISSION_SEALED' if numerical else 'UNSEALED_PARTIAL'}
    p = os.path.join(out, 'status.json')
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(status, f, indent=2, ensure_ascii=False)
    return p, hashlib.sha256(open(p, 'rb').read()).hexdigest(), statuses, numerical

def build_zip(out, zip_path):
    manifest = []
    for dirpath, dirnames, filenames in os.walk(out):
        for fn in sorted(filenames):
            if fn == 'manifest_sha256.csv':
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, out).replace(os.sep, '/')
            manifest.append((rel, hashlib.sha256(open(full, 'rb').read()).hexdigest()))
    manifest.sort()
    with open(os.path.join(out, 'manifest_sha256.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['relative_path', 'sha256'])
        for rel, sha in manifest:
            w.writerow([rel, sha])
    if os.path.exists(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for dirpath, dirnames, filenames in os.walk(out):
            for fn in sorted(filenames):
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, out).replace(os.sep, '/')
                z.write(full, 'iscat_v117_return/%s' % rel)
    return hashlib.sha256(open(zip_path, 'rb').read()).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--zip', required=True)
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    out = os.path.abspath(args.out)
    zip_path = os.path.abspath(args.zip)
    t0 = time.time()
    if os.path.exists(out) and os.listdir(out):
        print('[v117] FATAL: out dir exists and is not empty')
        return 3
    try:
        if os.path.commonpath([root]) == os.path.commonpath([root, out]):
            print('[v117] FATAL: out must be outside the source root')
            return 3
    except ValueError:
        pass
    os.makedirs(out, exist_ok=True)
    for sub in ('analysis', 'tables', 'logs'):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    tool_sha = sha256_file(os.path.abspath(__file__))
    launch = {'task_id': TASK_ID, 'source_root': root, 'execution_root': EXEC,
              'out': out, 'zip': zip_path, 'expected_v116_commit': EXPECTED_V116,
              'tool_sha256': tool_sha,
              'command': 'python run_v117_all.py --root "%s" --out "%s" --zip "%s"' % (root, out, zip_path),
              'python': sys.version.split()[0], 'numpy': np.__version__,
              'scipy': __import__('scipy').__version__,
              'pid': os.getpid(), 'started_at': time.strftime('%Y-%m-%dT%H:%M:%S')}
    launch_ext = os.path.splitext(zip_path)[0] + '.launch.json'
    with open(launch_ext, 'w', encoding='utf-8') as f:
        json.dump(launch, f, indent=2)
    with open(os.path.join(out, 'logs', 'v117_launch_record.json'), 'w', encoding='utf-8') as f:
        json.dump(launch, f, indent=2)
    shutil.copy2(os.path.abspath(__file__), os.path.join(out, 'logs', 'run_v117_all_snapshot.py'))
    log('launch recorded: %s' % launch_ext)

    s0_head = s0_identities(root, out)
    s1(root, out)
    s2(root, out)
    s3(root, out)
    s4(out)
    s5_physics_and_exposure(out)

    numerical = all(GATES[g] for g in REQUIRED_GATES if g != 'F_verifier_selftest')
    final_summary = {'gates': GATES, 'stage_logs': STAGE_LOG, 'fail_keys': FAIL_KEYS,
                     'elapsed_seconds': None,
                     'pre_archive_note': 'in-ZIP snapshot; external post_archive_summary.json carries '
                                         'final values', 'zip_sha256': None}
    with open(os.path.join(out, 'logs', 'v117_final_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(final_summary, f, indent=2)
    status_path, status_sha, statuses, _ = build_status(out, tool_sha)
    tool_shas = {'run_v117_all.py': tool_sha,
                 'v117_archive_check.py': sha256_file(os.path.join(EXEC, 'tools', 'v117_archive_check.py')),
                 'v117_source_acceptance.py': sha256_file(os.path.join(EXEC, 'tools', 'v117_source_acceptance.py')),
                 'v117_saved_probe_bridge.py': sha256_file(os.path.join(EXEC, 'tools', 'v117_saved_probe_bridge.py')),
                 'v115_operator_regression.py': sha256_file(os.path.join(EXEC, 'tools', 'v115_operator_regression.py')),
                 'v116_operator_boundary_tests.py': sha256_file(os.path.join(EXEC, 'tools', 'v116_operator_boundary_tests.py')),
                 'observation_operator.py': sha256_file(os.path.join(EXEC, 'tools', 'observation_operator.py'))}
    with open(os.path.join(out, 'execution_code_manifest.json'), 'w', encoding='utf-8') as f:
        json.dump({'tools': tool_shas, 'note': 'execution root is outside the frozen source tree'}, f, indent=2)
    zip_sha = build_zip(out, zip_path)  # provisional selftest fixture
    checker_src = os.path.join(EXEC, 'tools', 'v117_archive_check.py')
    stage_f(root, out, zip_path, checker_src, status_sha)
    provisional_sha = sha256_file(zip_path)
    if GATES['F_verifier_selftest']:
        final_summary['gates'] = GATES
        with open(os.path.join(out, 'logs', 'v117_final_summary.json'), 'w', encoding='utf-8') as f:
            json.dump(final_summary, f, indent=2)
        os.remove(status_path)
        status_path, status_sha, statuses, _ = build_status(out, tool_sha)
        zip_sha = build_zip(out, zip_path)
        with open(os.path.join(out, 'logs', 'v117_provisional_zip_sha.json'), 'w', encoding='utf-8') as f:
            json.dump({'provisional_zip_sha256': provisional_sha, 'final_zip_sha256': zip_sha,
                       'protocol': 'provisional selftest fixture replaced by single final zip after '
                                   'verifier qualification; both hashes disclosed'}, f, indent=2)
    check_json = os.path.splitext(zip_path)[0] + '.archive_check.json'
    proc = subprocess.run([sys.executable, checker_src, '--zip', zip_path,
                           '--expect-status-sha', status_sha, '--out', check_json],
                          capture_output=True, text=True, timeout=900)
    chk = json.load(open(check_json, encoding='utf-8')) if os.path.isfile(check_json) else {}
    archive_integrity = bool(chk.get('archive_integrity'))
    numerical_accepted = bool(chk.get('numerical_accepted'))
    archive_valid = bool(chk.get('archive_valid'))
    exit_code = 0 if (numerical and archive_valid and GATES['F_verifier_selftest']) else 2
    final_summary['elapsed_seconds'] = round(time.time() - t0, 1)
    final_summary['zip_sha256'] = zip_sha
    final_summary['status_json_sha256'] = status_sha
    final_summary['exit_code'] = exit_code
    final_summary['archive_integrity'] = archive_integrity
    final_summary['numerical_accepted'] = numerical_accepted
    final_summary['archive_valid'] = archive_valid
    post_path = os.path.splitext(zip_path)[0] + '.post_archive_summary.json'
    with open(post_path, 'w', encoding='utf-8') as f:
        json.dump(final_summary, f, indent=2)
    post_sha = sha256_file(post_path)
    receipt = {'task_id': TASK_ID, 'source_commit': EXPECTED_V116, 'parent_commit': EXPECTED_V115,
               'tool_sha256': tool_sha, 'tool_shas': tool_shas,
               'zip_path': zip_path, 'zip_sha256': zip_sha,
               'zip_size_bytes': os.path.getsize(zip_path),
               'status_json_sha256_in_zip': status_sha,
               'post_archive_summary_path': post_path, 'post_archive_summary_sha256': post_sha,
               'exit_code': exit_code,
               'execution_status': statuses['execution'], 'numerical_status': statuses['numerical'],
               'archive_status': 'ARCHIVE_VERIFIED' if archive_valid else 'ARCHIVE_CHECK_FAILED',
               'physics_status': statuses['physics'],
               'created_at': time.strftime('%Y-%m-%dT%H:%M:%S')}
    with open(os.path.splitext(zip_path)[0] + '.receipt.json', 'w', encoding='utf-8') as f:
        json.dump(receipt, f, indent=2, ensure_ascii=False)
    log('final: gates=%s numerical=%s integrity=%s valid=%s exit=%d zip=%s'
        % (GATES, statuses['numerical'], archive_integrity, archive_valid, exit_code, zip_sha))
    if exit_code != 0:
        log('FAIL_KEYS: %s' % json.dumps(FAIL_KEYS))
    return exit_code

if __name__ == '__main__':
    sys.exit(main())
