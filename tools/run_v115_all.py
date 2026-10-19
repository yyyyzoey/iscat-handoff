# -*- coding: utf-8 -*-
"""v115: V115_ROI_MODE_AND_REGISTERED_SIMULATION_BRIDGE.

v114 review implemented: 27-item operator regression red->green (ROI electron/DN
unit conversion, one synchronized (P,Q) frame per quadrature node with exact
callback counts, zero-callback static pre-validation everywhere, k0s=[] rejected
uniformly incl. partial pipelines, boundary error hygiene); 576 saved-probe
bridge re-run THROUGH the fixed production module; 12+4 legacy suite re-run;
four-layer admission. Lineage: tools/run_v114_all.py. No new BEM/render/optical
time series/physics states/experiment video reads."""
import os, sys, csv, json, hashlib, shutil, math, subprocess, zipfile, time, argparse, io
sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import numpy as np
from scipy.io import loadmat

TASK_ID = 'V115_ROI_MODE_AND_REGISTERED_SIMULATION_BRIDGE'
EXPECTED_V114 = '7a9102d5f8c6f98305ed9b10279083de96be66e6'
EXPECTED_V113 = '89a5b353ba104a3dbf0764816933739f8edda33b'
PROBE_BLOB = '6b180147f64847329375363d44c317b2d4df247b'
V114_ZIP_SHA = 'a1e27cce70d44004393c83fa0efbaf42378c99caeea54e915468952a71b54aa4'
N = 2001
FS = 5000.0
ALL24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
         for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)]
INTER24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
           for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (10, 15)]
ALL48 = ALL24 + INTER24
REQUIRED_GATES = ['A_source_lock', 'B_operator_regression', 'C_saved_probe_bridge',
                  'D_metadata_readiness', 'F_verifier_selftest']
GATES = {g: False for g in REQUIRED_GATES}
FAIL_KEYS = {}
STAGE_LOG = {}

def log(msg):
    print('[v115] %s' % msg, flush=True)

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def blob_sha1_bytes(data):
    h = hashlib.sha1()
    h.update(b'blob %d\x00' % len(data))
    h.update(data)
    return h.hexdigest()

def wcsv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)

def rcsv(path):
    with open(path, 'r', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

# ============================== Stage A ==============================

def stage_a(root, out):
    log('=== Stage A: source lock + minimal inheritance ===')
    an = os.path.join(root, 'analysis')
    tab = os.path.join(root, 'tables')
    issues = []
    head = subprocess.run(['git', '-C', root, 'rev-parse', 'HEAD'],
                          capture_output=True, text=True, timeout=60).stdout.strip()
    parent = subprocess.run(['git', '-C', root, 'rev-parse', 'HEAD^'],
                            capture_output=True, text=True, timeout=60).stdout.strip()
    if head != EXPECTED_V114:
        issues.append('HEAD %s != fixed v114 commit' % head)
    # the delivered v114 tip 7a9102d carries an extra red-evidence commit, so the
    # v113 commit is verified as an ANCESTOR rather than the direct parent
    anc = subprocess.run(['git', '-C', root, 'merge-base', '--is-ancestor',
                          EXPECTED_V113, head], capture_output=True, timeout=60).returncode
    if anc != 0:
        issues.append('v113 commit %s is not an ancestor of HEAD' % EXPECTED_V113)
    manifest = {r['path']: r['sha256'] for r in rcsv(os.path.join(root, 'manifest_sha256.csv'))}
    snap_dir = os.path.join(out, 'snapshot73')
    os.makedirs(snap_dir, exist_ok=True)
    bl_rows = rcsv(os.path.join(tab, 'v085_double_maps24_status.csv'))
    bl_map_file = {r['case_id']: r['map_file'] for r in bl_rows}
    snap_rows = []
    for key in ALL48:
        fn = 'v092_bank_%s.mat' % key
        p = os.path.join(an, 'bank', fn)
        sha = sha256_file(p)
        if fn in manifest and manifest[fn] != sha:
            issues.append('bank sha mismatch vs git manifest: %s' % fn)
        m = loadmat(p)
        if not (str(m['case_id'].flatten()[0]) == key
                and int(np.asarray(m['N']).flatten()[0]) == N
                and float(np.asarray(m['Fs']).flatten()[0]) == FS):
            issues.append('bank metadata mismatch: %s' % key)
        dst = os.path.join(snap_dir, fn)
        shutil.copy2(p, dst)
        snap_rows.append({'role': 'BANK', 'case_id': key, 'source_relative': 'analysis/bank/%s' % fn,
                          'target_relative': 'snapshot73/%s' % fn,
                          'size_bytes': str(os.path.getsize(dst)), 'sha256': sha})
    for key in ALL24:
        fn = bl_map_file[key]
        p = os.path.join(root, 'numeric', fn)
        sha = sha256_file(p)
        if fn in manifest and manifest[fn] != sha:
            issues.append('baseline sha mismatch vs git manifest: %s' % fn)
        dst = os.path.join(snap_dir, fn)
        shutil.copy2(p, dst)
        snap_rows.append({'role': 'BASELINE', 'case_id': key, 'source_relative': 'numeric/%s' % fn,
                          'target_relative': 'snapshot73/%s' % fn,
                          'size_bytes': str(os.path.getsize(dst)), 'sha256': sha})
    npz_src = os.path.join(an, 'v093_probe_evidence.npz')
    if blob_sha1_bytes(open(npz_src, 'rb').read()) != PROBE_BLOB:
        issues.append('probe NPZ git blob mismatch')
    dst_npz = os.path.join(snap_dir, 'v093_probe_evidence.npz')
    shutil.copy2(npz_src, dst_npz)
    snap_rows.append({'role': 'SAVED_SIMULATION_PROBES', 'case_id': 'PROBE_EVIDENCE_192_SERIES',
                      'source_relative': 'analysis/v093_probe_evidence.npz',
                      'target_relative': 'snapshot73/v093_probe_evidence.npz',
                      'size_bytes': str(os.path.getsize(dst_npz)), 'sha256': sha256_file(dst_npz)})
    wcsv(os.path.join(out, 'logs', 'v115_snapshot73_manifest.csv'), list(snap_rows[0].keys()), snap_rows)
    v114_zip = next((c for c in (r'C:\Users\PC\Documents\Codex\2026-10-18\files-mentioned-by-the-user-iscat\work\v114_final\iscat_v114_return.zip',
                                 r'C:\Users\PC\Documents\Codex\2026-10-18\files-mentioned-by-the-user-iscat\outputs\iscat_v114_return.zip')
                     if os.path.isfile(c)), None)
    v114_ok = bool(v114_zip and sha256_file(v114_zip) == 'a1e27cce70d44004393c83fa0efbaf42378c99caeea54e915468952a71b54aa4')
    if not v114_ok:
        issues.append('v114 ZIP bytes not independently verified')
    with open(os.path.join(out, 'logs', 'v115_v114_archive_audit.json'), 'w', encoding='utf-8') as f:
        json.dump({'zip_path': v114_zip,
                   'expected_sha256': 'a1e27cce70d44004393c83fa0efbaf42378c99caeea54e915468952a71b54aa4',
                   'independently_verified_bytes': v114_ok}, f, indent=2)
    diff = subprocess.run(['git', '-C', root, 'diff', EXPECTED_V114, '--', 'tools/'],
                          capture_output=True, text=True, timeout=120).stdout
    with open(os.path.join(out, 'logs', 'v115_source_diff.patch'), 'w', encoding='utf-8', newline='') as f:
        f.write(diff)
    ok_a = not issues and len(snap_rows) == 73
    if not ok_a:
        FAIL_KEYS.setdefault('A', issues[:10])
    GATES['A_source_lock'] = ok_a
    STAGE_LOG['A'] = {'snapshots': len(snap_rows), 'head': head, 'v114_zip_verified': v114_ok,
                      'issues': issues[:10]}
    log('Stage A: snap=%d v114zip=%s' % (len(snap_rows), v114_ok))

# ============================== Stage B ==============================

def stage_b(root, out):
    log('=== Stage B: 27-item regression red->green + legacy 12+4 ===')
    red_src = os.path.join(r'C:\Users\PC\Documents\Codex\2026-10-18\files-mentioned-by-the-user-iscat\work',
                           'v115_run', 'prepatch_red.json')
    if os.path.isfile(red_src):
        shutil.copy2(red_src, os.path.join(out, 'logs', 'prepatch_red.json'))
    green_path = os.path.join(out, 'logs', 'postpatch_green.json')
    proc = subprocess.run([sys.executable, os.path.join(root, 'tools', 'v115_operator_regression.py'),
                           green_path], capture_output=True, text=True, timeout=1800)
    ok_reg = proc.returncode == 0
    rep = json.load(open(green_path, encoding='utf-8')) if os.path.isfile(green_path) else {}
    shutil.copy2(green_path, os.path.join(out, 'observation_regression_v115.json'))
    legacy_path = os.path.join(out, 'logs', 'v113_suite_on_v115_module.json')
    proc2 = subprocess.run([sys.executable, os.path.join(root, 'tools',
                            'observation_integration_tests_v113.py'), legacy_path],
                           capture_output=True, text=True, timeout=1800)
    ok_113 = proc2.returncode == 0
    rep113 = json.load(open(legacy_path, encoding='utf-8')) if os.path.isfile(legacy_path) else {}
    shutil.copy2(legacy_path, os.path.join(out, 'observation_integration_v113_suite.json'))
    ok_b = ok_reg and ok_113
    if not ok_reg:
        FAIL_KEYS.setdefault('B', ['regression failures'])
    if not ok_113:
        FAIL_KEYS.setdefault('B', ['v113 suite failures on v115 module'])
    GATES['B_operator_regression'] = ok_b
    STAGE_LOG['B'] = {'regression': '%d/%d' % (rep.get('n_pass', 0), rep.get('n_total', 0)),
                      'legacy_groups': '%d/%d' % (sum(1 for g in rep113.get('groups', []) if g['pass']),
                                                  len(rep113.get('groups', []))),
                      'legacy_mutations': '%d/%d' % (sum(1 for m in rep113.get('mutations', []) if m['detected']),
                                                     len(rep113.get('mutations', []))),
                      'prepatch_red_archived': os.path.isfile(os.path.join(out, 'logs', 'prepatch_red.json'))}
    log('Stage B: regression=%s legacy=%s mutations=%s'
        % (STAGE_LOG['B']['regression'], STAGE_LOG['B']['legacy_groups'],
           STAGE_LOG['B']['legacy_mutations']))

# ============================== Stage C ==============================

def stage_c(root, out):
    log('=== Stage C: 576 saved-probe bridge through the production module ===')
    bridge_csv = os.path.join(out, 'tables', 'v115_bridge576.csv')
    proc = subprocess.run([sys.executable, os.path.join(root, 'tools', 'v115_saved_probe_bridge.py'),
                           '--root', root, '--output', bridge_csv],
                          capture_output=True, text=True, timeout=1800)
    ok_c = proc.returncode == 0
    summary = {}
    sj = bridge_csv.replace('.csv', '.summary.json')
    if os.path.isfile(sj):
        summary = json.load(open(sj, encoding='utf-8'))
        shutil.copy2(sj, os.path.join(out, 'logs', 'v115_bridge_summary.json'))
    if not ok_c:
        FAIL_KEYS.setdefault('C', ['bridge failures: %s' % (summary.get('issues', []) or proc.stdout[-200:])])
    GATES['C_saved_probe_bridge'] = ok_c
    STAGE_LOG['C'] = {'checked': summary.get('checked', 0), 'passed': summary.get('passed', 0),
                      'complete_set': summary.get('complete_set_576_unique_and_expected'),
                      'backend': summary.get('backend', ''), 'issues': summary.get('issues', [])[:5]}
    log('Stage C: bridge %s/%s (production module paths)'
        % (summary.get('passed', 0), summary.get('checked', 0)))

# ============================== Stage D ==============================

def stage_d(root, out):
    log('=== Stage D: metadata readiness + four-layer admission ===')
    eff_src = os.path.join(root, 'logs', 'v113_effective_assignments.csv')
    inherited = rcsv(eff_src) if os.path.isfile(eff_src) else []
    items = [
        {'group': 'optics_scale', 'parameter': 'laser_vacuum_wavelength', 'value': 520.0, 'unit': 'nm',
         'evidence_class': 'USER_CONFIRMED', 'direct_source': 'user statement (no certificate recorded)',
         'source_sha256': '', 'valid_dataset': 'all', 'bounds': None,
         'missing_acquisition': 'instrument calibration certificate (does not invalidate the value)'},
        {'group': 'camera_time', 'parameter': 'frame_rate_Fs', 'value': 5000.0, 'unit': 'fps',
         'evidence_class': 'EXPERIMENT_SCRIPT_RECORDED',
         'direct_source': 'test_with_contrast.m L39 (hash-verified workstation script)',
         'source_sha256': 'd08575b1e860e09f29c74652442a77b721039c6e32368fe76d2c5c63143ea3aa',
         'valid_dataset': '7.29 batch', 'bounds': 'script constant; NOT a calibrated clock',
         'missing_acquisition': 'external clock calibration'},
        {'group': 'camera_time', 'parameter': 'nominal_bins_k0', 'value': '[80, 160, 320]', 'unit': 'bin',
         'evidence_class': 'ANALYSIS_CONTRACT', 'direct_source': 'bank k0_bins field',
         'source_sha256': '', 'valid_dataset': 'demo analysis',
         'bounds': 'analysis indices, never instrument data', 'missing_acquisition': None},
        {'group': 'optics_scale', 'parameter': 'nominal_D', 'value': 100.0, 'unit': 'nm',
         'evidence_class': 'NOMINAL_LABEL', 'direct_source': 'v092 bank case naming',
         'source_sha256': '', 'valid_dataset': 'demo bank',
         'bounds': 'unverified nominal label, NOT an absolute calibration certificate',
         'missing_acquisition': 'independent diameter standard'},
        {'group': 'optics_scale', 'parameter': 'demo_pixel_size', 'value': 65.0, 'unit': 'nm',
         'evidence_class': 'SIMULATION_ASSUMPTION', 'direct_source': 'prior instruction documents',
         'source_sha256': '', 'valid_dataset': 'demo only', 'bounds': 'assumption',
         'missing_acquisition': 'real object-plane scale with error'},
        {'group': 'camera_time', 'parameter': 'exposure_time_per_frame', 'value': None, 'unit': 's',
         'evidence_class': 'MISSING', 'direct_source': None, 'source_sha256': None,
         'valid_dataset': None, 'bounds': None,
         'missing_acquisition': 'camera acquisition log / property readout per frame'},
        {'group': 'camera_time', 'parameter': 'trigger_time_origin_convention', 'value': None,
         'unit': None, 'evidence_class': 'MISSING', 'direct_source': None, 'source_sha256': None,
         'valid_dataset': None, 'bounds': None,
         'missing_acquisition': 'trigger log: exposure-start vs exposure-center'},
        {'group': 'camera_time', 'parameter': 'per_frame_timestamps', 'value': None, 'unit': 's',
         'evidence_class': 'MISSING', 'direct_source': None, 'source_sha256': None,
         'valid_dataset': None, 'bounds': None,
         'missing_acquisition': 'frame timestamp log (host or camera FIFO)'},
        {'group': 'camera_time', 'parameter': 'kappa_e_per_U_per_s', 'value': None, 'unit': 'e-/(U*s)',
         'evidence_class': 'MISSING', 'direct_source': None, 'source_sha256': None,
         'valid_dataset': None, 'bounds': None,
         'missing_acquisition': 'responsivity calibration at 520nm'},
        {'group': 'camera_time', 'parameter': 'g_DN_per_e', 'value': None, 'unit': 'DN/e-',
         'evidence_class': 'MISSING', 'direct_source': None, 'source_sha256': None,
         'valid_dataset': None, 'bounds': None,
         'missing_acquisition': 'photon-transfer curve or datasheet'},
        {'group': 'camera_time', 'parameter': 'offset_DN', 'value': None, 'unit': 'DN',
         'evidence_class': 'MISSING', 'direct_source': None, 'source_sha256': None,
         'valid_dataset': None, 'bounds': None, 'missing_acquisition': 'dark-frame measurement'},
        {'group': 'optics_scale', 'parameter': 'objective_NA_immersion_illumination_polarization',
         'value': None, 'unit': None, 'evidence_class': 'MISSING', 'direct_source': None,
         'source_sha256': None, 'valid_dataset': None, 'bounds': None,
         'missing_acquisition': 'objective datasheet + illumination record'},
        {'group': 'sample_motion', 'parameter': 'sample_medium_substrate_height_fixation',
         'value': None, 'unit': None, 'evidence_class': 'MISSING', 'direct_source': None,
         'source_sha256': None, 'valid_dataset': None, 'bounds': None,
         'missing_acquisition': 'sample preparation record + spacer metrology'},
        {'group': 'sample_motion', 'parameter': 'independent_trajectory_with_scale_and_timebase',
         'value': None, 'unit': None, 'evidence_class': 'MISSING', 'direct_source': None,
         'source_sha256': None, 'valid_dataset': None, 'bounds': None,
         'missing_acquisition': 'independent tracking with certified scale and common timebase (route A)'},
        {'group': 'sample_motion', 'parameter': 'magnetic_field_B_vector_gradient_waveform_sync',
         'value': None, 'unit': None, 'evidence_class': 'MISSING', 'direct_source': None,
         'source_sha256': None, 'valid_dataset': None, 'bounds': None,
         'missing_acquisition': 'calibrated probe B(t) with camera sync (route B); 200Hz drive does '
         'not imply 400Hz translation'},
        {'group': 'optics_scale', 'parameter': 'reference_field_path', 'value': None, 'unit': None,
         'evidence_class': 'MISSING', 'direct_source': None, 'source_sha256': None,
         'valid_dataset': None, 'bounds': None,
         'missing_acquisition': 'optical layout record or interferometric characterization'},
    ]
    wcsv(os.path.join(out, 'metadata_readiness_v115.csv'), list(items[0].keys()), items)
    admission = {
        'LEGACY_SIMULATION_FROZEN': True,
        'SOFTWARE_OPERATOR_CERTIFIED_FOR_FIXED_FIXTURES': bool(GATES.get('B_operator_regression')),
        'REAL_DEVICE_RELATIVE_FORWARD_GO': False,
        'ABSOLUTE_COUNT_AND_DIAMETER_VALIDATION_GO': False,
        'layer3_blockers': [i['parameter'] for i in items if i['evidence_class'] == 'MISSING'],
        'layer4_blockers': ['kappa_e_per_U_per_s', 'g_DN_per_e', 'offset_DN',
                            'independent diameter reference', 'blank/control',
                            'uncertainty chain and independent verification design'],
        'priority_acquisition': [
            '1. camera+optics: object-plane nm/px with uncertainty, NA/immersion/polarization, '
            'Eref path/phase/illumination, batch exposure duration, trigger convention, frame timestamps',
            '2. sample+motion: particle batch/coating, substrate/height/medium, fixed vs suspended; '
            'independent trajectory OR calibrated B(t)/gradient/sync with mechanical boundaries',
            '3. absolute counting/diameter: kappa, DN/e, offset with uncertainties, independent '
            'diameter standard, particle blank/B-off, held-out cross-particle/window validation'],
        'next_physics_design_only': {
            'route_A': 'measured 3D position/orientation trajectory -> Eref+Escat -> per-frame real '
                       'exposure and pixel intensity averaging -> this operator; known-diameter '
                       'standard first, B-off/blank control, object-plane ruler, held-out windows',
            'route_B': 'measured B(t)/gradient/sync + medium/fixation mechanics -> constrained '
                       'trajectory -> route A; 200Hz drive does not imply 400Hz translation',
            'authorization': 'pre-registration only; v115 auto-start count = 0'},
    }
    with open(os.path.join(out, 'admission_v115.json'), 'w', encoding='utf-8') as f:
        json.dump(admission, f, indent=2, ensure_ascii=False)
    ok_d = len(items) == 16 and len(inherited) == 14
    if not ok_d:
        FAIL_KEYS.setdefault('D', ['items=%d inherited=%d' % (len(items), len(inherited))])
    GATES['D_metadata_readiness'] = ok_d
    STAGE_LOG['D'] = {'items': len(items), 'inherited_effective_rows': len(inherited),
                      'missing': sum(1 for i in items if i['evidence_class'] == 'MISSING'),
                      'layer3_go': False, 'layer4_go': False}
    log('Stage D: items=%d missing=%d' % (len(items), STAGE_LOG['D']['missing']))

# ============================== Stage F ==============================

def stage_f(root, out, zip_path, checker_src, status_sha):
    log('=== Stage F: verifier selftest ===')
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import run_v114_all as v114mod  # reuse the proven selftest harness
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
        man = zin.read('iscat_v115_return/manifest_sha256.csv').decode('utf-8').splitlines()
        zo.writestr('iscat_v115_return/manifest_sha256.csv',
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
        man = zin.read('iscat_v115_return/manifest_sha256.csv').decode('utf-8')
        zo.writestr('iscat_v115_return/manifest_sha256.csv', man + '../escape.txt,%s\n' % ('0' * 64))
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
    st = json.loads(zin.read('iscat_v115_return/status.json'))
    for name, mutate in (('gates_string_bool', lambda s: s['gates'].update({'A_source_lock': 'true'})),
                         ('gates_missing', lambda s: s['gates'].pop('A_source_lock')),
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
    wcsv(os.path.join(out, 'logs', 'v115_verifier_selftest.csv'), st_fields, results)
    for fn in os.listdir(work):
        if fn.startswith('case_') and fn.endswith('.zip'):
            os.remove(os.path.join(work, fn))
    n_pass = sum(1 for r in results if r['verdict'] == 'PASS')
    ok_f = all_ok and positive_ok and n_pass == len(results)
    if not ok_f:
        FAIL_KEYS.setdefault('F', ['selftest %d/%d' % (n_pass, len(results))])
    GATES['F_verifier_selftest'] = ok_f
    STAGE_LOG['F'] = {'cases': len(results), 'passed': n_pass, 'positive_control': positive_ok}
    log('Stage F: selftest %d/%d PASS' % (n_pass, len(results)))

# ============================== archive / main ==============================

def build_status(out, tool_sha):
    numerical = all(GATES[g] for g in REQUIRED_GATES)
    statuses = {'execution': 'COMPLETE',
                'numerical': 'ROI_MODE_AND_BRIDGE_SEALED' if numerical else 'UNSEALED_PARTIAL',
                'archive': 'PRE_ARCHIVE_VERIFICATION',
                'physics': 'ALL_FORWARD_GO_FALSE_PENDING_INPUTS'}
    status = {'schema': 'iscat115.status.1', 'task_id': TASK_ID,
              'created_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
              'source_commit': EXPECTED_V114, 'parent_commit': EXPECTED_V113,
              'tool_sha256': tool_sha,
              'required_gates': list(REQUIRED_GATES),
              'gates': {g: bool(GATES[g]) for g in REQUIRED_GATES},
              'states': statuses,
              'four_layer_admission': {
                  'LEGACY_SIMULATION_FROZEN': True,
                  'SOFTWARE_OPERATOR_CERTIFIED_FOR_FIXED_FIXTURES': bool(GATES.get('B_operator_regression')),
                  'REAL_DEVICE_RELATIVE_FORWARD_GO': False,
                  'ABSOLUTE_COUNT_AND_DIAMETER_VALIDATION_GO': False},
              'stage_logs': STAGE_LOG,
              'environment': {'python': sys.version.split()[0],
                              'numpy': np.__version__, 'scipy': __import__('scipy').__version__,
                              'pythondontwritebytecode': '1'},
              'frozen_states': {'calibration_valid': False, 'experimental_validation': False,
                                'detection_validated': False, 'single_particle_diameter': 'NOT_ESTIMATED'},
              'p0_status': 'OPEN (not upgraded)',
              'rule7_new_authorizations': 0,
              'overall': 'ROI_MODE_AND_BRIDGE_SEALED' if numerical else 'UNSEALED_PARTIAL'}
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
                z.write(full, 'iscat_v115_return/%s' % rel)
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
        print('[v115] FATAL: out dir exists and is not empty')
        return 3
    try:
        if os.path.commonpath([root]) == os.path.commonpath([root, out]):
            print('[v115] FATAL: out must be outside the source root')
            return 3
    except ValueError:
        pass
    os.makedirs(out, exist_ok=True)
    for sub in ('analysis', 'tables', 'logs'):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    tool_sha = sha256_file(os.path.abspath(__file__))
    launch = {'task_id': TASK_ID, 'root': root, 'out': out, 'zip': zip_path,
              'expected_v114_commit': EXPECTED_V114, 'tool_sha256': tool_sha,
              'command': 'python tools/run_v115_all.py --root "%s" --out "%s" --zip "%s"' % (root, out, zip_path),
              'python': sys.version.split()[0], 'numpy': np.__version__,
              'scipy': __import__('scipy').__version__,
              'pid': os.getpid(), 'started_at': time.strftime('%Y-%m-%dT%H:%M:%S')}
    launch_ext = os.path.splitext(zip_path)[0] + '.launch.json'
    with open(launch_ext, 'w', encoding='utf-8') as f:
        json.dump(launch, f, indent=2)
    with open(os.path.join(out, 'logs', 'v115_launch_record.json'), 'w', encoding='utf-8') as f:
        json.dump(launch, f, indent=2)
    shutil.copy2(os.path.abspath(__file__), os.path.join(out, 'logs', 'run_v115_all_snapshot.py'))
    log('launch recorded: %s' % launch_ext)

    stage_a(root, out)
    stage_b(root, out)
    stage_c(root, out)
    stage_d(root, out)

    numerical = all(GATES[g] for g in REQUIRED_GATES if g != 'F_verifier_selftest')
    final_summary = {'gates': GATES, 'stage_logs': STAGE_LOG, 'fail_keys': FAIL_KEYS,
                     'elapsed_seconds': None,
                     'pre_archive_note': 'in-ZIP snapshot; external post_archive_summary.json carries '
                                         'final values', 'zip_sha256': None}
    with open(os.path.join(out, 'logs', 'v115_final_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(final_summary, f, indent=2)
    status_path, status_sha, statuses, _ = build_status(out, tool_sha)
    tool_shas = {'run_v115_all.py': tool_sha,
                 'v115_archive_check.py': sha256_file(os.path.join(root, 'tools', 'v115_archive_check.py')),
                 'v115_operator_regression.py': sha256_file(os.path.join(root, 'tools', 'v115_operator_regression.py')),
                 'v115_saved_probe_bridge.py': sha256_file(os.path.join(root, 'tools', 'v115_saved_probe_bridge.py')),
                 'observation_operator.py': sha256_file(os.path.join(root, 'tools', 'observation_operator.py')),
                 'run_v114_all.py': sha256_file(os.path.join(root, 'tools', 'run_v114_all.py'))}
    with open(os.path.join(out, 'logs', 'v115_tool_shas.json'), 'w', encoding='utf-8') as f:
        json.dump(tool_shas, f, indent=2)
    zip_sha = build_zip(out, zip_path)  # provisional selftest fixture
    checker_src = os.path.join(root, 'tools', 'v115_archive_check.py')
    tool_shas['v115_archive_check.py'] = sha256_file(checker_src)
    with open(os.path.join(out, 'logs', 'v115_tool_shas.json'), 'w', encoding='utf-8') as f:
        json.dump(tool_shas, f, indent=2)
    stage_f(root, out, zip_path, checker_src, status_sha)
    provisional_sha = sha256_file(zip_path)
    if GATES['F_verifier_selftest']:
        final_summary['gates'] = GATES
        with open(os.path.join(out, 'logs', 'v115_final_summary.json'), 'w', encoding='utf-8') as f:
            json.dump(final_summary, f, indent=2)
        os.remove(status_path)
        status_path, status_sha, statuses, _ = build_status(out, tool_sha)
        zip_sha = build_zip(out, zip_path)
        with open(os.path.join(out, 'logs', 'v115_provisional_zip_sha.json'), 'w', encoding='utf-8') as f:
            json.dump({'provisional_zip_sha256': provisional_sha, 'final_zip_sha256': zip_sha,
                       'protocol': 'provisional selftest fixture replaced by single final zip after '
                                   'verifier qualification; both hashes disclosed'}, f, indent=2)
    check_json = os.path.splitext(zip_path)[0] + '.archive_check.json'
    proc = subprocess.run([sys.executable, checker_src, '--zip', zip_path,
                           '--expect-status-sha', status_sha, '--out', check_json],
                          capture_output=True, text=True, timeout=900)
    archive_ok = proc.returncode == 0
    exit_code = 0 if (numerical and archive_ok and GATES['F_verifier_selftest']) else 2
    final_summary['elapsed_seconds'] = round(time.time() - t0, 1)
    final_summary['zip_sha256'] = zip_sha
    final_summary['status_json_sha256'] = status_sha
    final_summary['exit_code'] = exit_code
    final_summary['archive_integrity'] = archive_ok
    post_path = os.path.splitext(zip_path)[0] + '.post_archive_summary.json'
    with open(post_path, 'w', encoding='utf-8') as f:
        json.dump(final_summary, f, indent=2)
    post_sha = sha256_file(post_path)
    receipt = {'task_id': TASK_ID, 'source_commit': EXPECTED_V114, 'parent_commit': EXPECTED_V113,
               'tool_sha256': tool_sha, 'tool_shas': tool_shas,
               'zip_path': zip_path, 'zip_sha256': zip_sha,
               'zip_size_bytes': os.path.getsize(zip_path),
               'status_json_sha256_in_zip': status_sha,
               'post_archive_summary_path': post_path, 'post_archive_summary_sha256': post_sha,
               'exit_code': exit_code,
               'execution_status': statuses['execution'], 'numerical_status': statuses['numerical'],
               'archive_status': 'ARCHIVE_VERIFIED' if archive_ok else 'ARCHIVE_CHECK_FAILED',
               'physics_status': statuses['physics'],
               'created_at': time.strftime('%Y-%m-%dT%H:%M:%S')}
    with open(os.path.splitext(zip_path)[0] + '.receipt.json', 'w', encoding='utf-8') as f:
        json.dump(receipt, f, indent=2, ensure_ascii=False)
    log('final: gates=%s numerical=%s archive=%s exit=%d zip=%s'
        % (GATES, statuses['numerical'], receipt['archive_status'], exit_code, zip_sha))
    if exit_code != 0:
        log('FAIL_KEYS: %s' % json.dumps(FAIL_KEYS))
    return exit_code

if __name__ == '__main__':
    sys.exit(main())
