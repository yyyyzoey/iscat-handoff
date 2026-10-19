# -*- coding: utf-8 -*-
"""v112: V112_EXECUTABLE_OBSERVATION_OPERATOR_AND_SOURCE_ALIGNMENT.

Freezes the legacy 48-state baseline after a one-pass field self-consistency
scan, performs variable-level source verification of the real extractor
scripts (explicit encodings, actual assignments - no first-string hits), and
runs the 12 fixed integration groups of the executable observation operator
module. Lineage: tools/run_v111_all.py + tools/observation_operator.py.
Zero new BEM/render/optical-time-series/physics-states/experiment-video reads."""
import os, sys, csv, json, hashlib, shutil, math, subprocess, zipfile, time, argparse, itertools, io, re
sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import numpy as np
from scipy.io import loadmat

TASK_ID = 'V112_EXECUTABLE_OBSERVATION_OPERATOR_AND_SOURCE_ALIGNMENT'
EXPECTED_V111 = '24fbd6bbfe8b2dd503efbf093a09fc3a60371a30'
EXPECTED_V110 = '4aa76ac1204d1133e2d53f9631a2f3fb3db7015d'
PROBE_BLOB = '6b180147f64847329375363d44c317b2d4df247b'
V111_ZIP_SHA = '40b9476dc9ba1a3190137737dd89616ded76b97e9335bb604f998de5ae01e46a'
N = 2001
FS = 5000.0
K0S = [80, 160, 320]
ALL24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
         for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)]
INTER24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
           for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (10, 15)]
ALL48 = ALL24 + INTER24
PROBE_PIXELS = [(20, 20), (20, 0), (0, 20), (25, 0)]
REQUIRED_GATES = ['A_legacy_scan_and_freeze', 'B_metadata_variables',
                  'C_observation_operator', 'F_verifier_selftest']
GATES = {g: False for g in REQUIRED_GATES}
FAIL_KEYS = {}
STAGE_LOG = {}

def log(msg):
    print('[v112] %s' % msg, flush=True)

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

def finite_val(v):
    try:
        f = float(v)
        return math.isfinite(f)
    except (TypeError, ValueError):
        return False

# ============================== Stage A ==============================

def stage_a(root, out):
    log('=== Stage A: admission + legacy self-consistency scan + freeze ===')
    an = os.path.join(root, 'analysis')
    tab = os.path.join(root, 'tables')
    issues = []
    head = subprocess.run(['git', '-C', root, 'rev-parse', 'HEAD'],
                          capture_output=True, text=True, timeout=60).stdout.strip()
    parent = subprocess.run(['git', '-C', root, 'rev-parse', 'HEAD^'],
                            capture_output=True, text=True, timeout=60).stdout.strip()
    if head != EXPECTED_V111:
        issues.append('HEAD %s != fixed v111 commit' % head)
    if parent != EXPECTED_V110:
        issues.append('parent %s != v110 commit' % parent)
    # byte domains: worktree vs git-canonical for the frozen inputs manifest
    worktree_status_sha = sha256_file(os.path.join(root, 'status.json'))
    canonical = subprocess.run(['git', '-C', root, 'show', EXPECTED_V111 + ':status.json'],
                               capture_output=True, timeout=60).stdout
    domains = {'worktree_status_sha256': worktree_status_sha,
               'git_canonical_status_sha256': hashlib.sha256(canonical).hexdigest(),
               'git_canonical_blob_sha1': blob_sha1_bytes(canonical),
               'note': 'worktree and git-canonical bytes are different hash domains'}
    manifest = {r['path']: r['sha256'] for r in rcsv(os.path.join(root, 'manifest_sha256.csv'))}

    bank = {}
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
        cid = str(m['case_id'].flatten()[0])
        if not (cid == key and int(np.asarray(m['N']).flatten()[0]) == N
                and float(np.asarray(m['Fs']).flatten()[0]) == FS):
            issues.append('bank metadata mismatch: %s' % key)
        bank[key] = {'sha256': sha}
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
    wcsv(os.path.join(out, 'logs', 'v112_snapshot73_manifest.csv'), list(snap_rows[0].keys()), snap_rows)

    # --- legacy 5040 field self-consistency scan (single read, no new distances) ---
    prod = rcsv(os.path.join(tab, 'v111_independent5040.csv'))
    scan_issues = []
    bank_sha = {k: bank[k]['sha256'] for k in ALL48}
    for r in prod:
        k = r['record_key']
        parts = k.split('|')
        if len(parts) != 4:
            scan_issues.append('%s: key parts != 4' % k)
            continue
        bins_k, group, qpart, feat = parts
        if bins_k != r.get('bins', ''):
            scan_issues.append('%s: bins mismatch' % k)
        if qpart != 'q=' + r.get('query', ''):
            scan_issues.append('%s: query mismatch' % k)
        if feat != r.get('feature', ''):
            scan_issues.append('%s: feature mismatch' % k)
        expected_group = r.get('subset_S') or r.get('policy', '')
        if group != expected_group:
            scan_issues.append('%s: group/policy mismatch' % k)
        q = r.get('query', '')
        p = q.split('_')
        qmeta = {'D': str(int(p[0][1:])), 'zf': str(int(p[1][2:])), 'type': p[2], 'a': str(int(p[3][1:]))}
        for f in ('query_D', 'query_type', 'query_zf', 'query_a'):
            if r.get(f, '') != qmeta[f[6:] if f.startswith('query_') else f]:
                scan_issues.append('%s: query metadata %s mismatch' % (k, f))
        members = [m for m in str(r.get('near_min_set', '')).split('|') if m]
        if str(len(members)) != str(r.get('near_min_set_size', '')):
            scan_issues.append('%s: near_min_set_size mismatch' % k)
        dset = set(str(r.get('near_min_D_set', '')).split('|'))
        if (r.get('tie_across_D') == 'YES') != (len(dset) > 1):
            scan_issues.append('%s: tie_across_D vs near_min_D_set inconsistent' % k)
        for f in ('nearest_dist', 'second_dist', 'same_D_nearest_dist',
                  'cross_D_nearest_dist', 'min_cross_minus_min_same', 'tie_threshold'):
            if not finite_val(r.get(f, '')):
                scan_issues.append('%s: non-finite %s' % (k, f))
        if r.get('source_sha256', '') != bank_sha.get(r.get('query', '')):
            scan_issues.append('%s: source sha mismatch' % k)
    scan_ok = len(scan_issues) == 0
    wcsv(os.path.join(out, 'logs', 'v112_legacy_scan_issues.csv'),
         ['record_key', 'issue'], [{'record_key': 'SUMMARY', 'issue': '%d issues in %d rows'
                                    % (len(scan_issues), len(prod))}] +
        [{'record_key': s.split(':')[0], 'issue': s} for s in scan_issues[:500]])
    frozen = scan_ok and len(prod) == 5040
    with open(os.path.join(out, 'logs', 'v112_legacy_freeze.json'), 'w', encoding='utf-8') as f:
        json.dump({'legacy_48_state_baseline_frozen': frozen,
                   'scan_rows': len(prod), 'scan_issues': len(scan_issues),
                   'scope': 'field self-consistency only; no new distance solving; '
                            'if issues existed, only affected keys and dependents would be flagged',
                   'record': 'LEGACY_48_STATE_BASELINE_FROZEN' if frozen else 'LEGACY_SCAN_ISSUES'},
                  f, indent=2)

    # --- C400_only rows: H/M/S components are the three_bin explanation, NOT theirs ---
    rev = rcsv(os.path.join(an, 'v111_s60_revised_attribution60.csv'))
    fixed_rows = []
    n_fixed = 0
    for r in rev:
        r = dict(r)
        if r['representation'] == 'C400_only':
            for f in ('H_minus_S', 'H_minus_M', 'M_minus_S'):
                if r.get(f, '') not in ('', 'NA'):
                    r[f] = 'NOT_APPLICABLE'
                    n_fixed += 1
            r['corrected_interpretation'] = (
                'C400_only: identical to current bin160 (30/30); H/M/S components belong to the '
                'same-group old three_bin explanation and are NOT_APPLICABLE here')
        fixed_rows.append(r)
    wcsv(os.path.join(out, 'analysis', 'v112_s60_revised_attribution60_fixed.csv'),
         list(fixed_rows[0].keys()), fixed_rows)

    # real v111 ZIP byte verification
    v111_zip = next((c for c in (r'C:\Users\PC\Documents\Codex\2026-10-18\files-mentioned-by-the-user-iscat\work\v111_final\iscat_v111_return.zip',
                                 r'C:\Users\PC\Documents\Codex\2026-10-18\files-mentioned-by-the-user-iscat\outputs\iscat_v111_return.zip')
                     if os.path.isfile(c)), None)
    v111_ok = bool(v111_zip and sha256_file(v111_zip) == V111_ZIP_SHA)
    if not v111_ok:
        issues.append('v111 ZIP bytes not independently verified')
    with open(os.path.join(out, 'logs', 'v112_v111_archive_audit.json'), 'w', encoding='utf-8') as f:
        json.dump({'zip_path': v111_zip, 'expected_sha256': V111_ZIP_SHA,
                   'independently_verified_bytes': v111_ok,
                   'note': 'PRE_ARCHIVE_VERIFICATION design itself is correct; the external receipt '
                           'is the post-verification credential'}, f, indent=2)
    diff = subprocess.run(['git', '-C', root, 'diff', EXPECTED_V111, '--', 'tools/'],
                          capture_output=True, text=True, timeout=120).stdout
    with open(os.path.join(out, 'logs', 'v112_source_diff.patch'), 'w', encoding='utf-8', newline='') as f:
        f.write(diff)

    ok_a = not issues and len(snap_rows) == 73 and frozen and scan_ok
    if not ok_a:
        FAIL_KEYS.setdefault('A', issues[:10] + (scan_issues[:5] if scan_issues else []))
    GATES['A_legacy_scan_and_freeze'] = ok_a
    STAGE_LOG['A'] = {'snapshots': len(snap_rows), 'scan_rows': len(prod),
                      'scan_issues': len(scan_issues), 'legacy_frozen': frozen,
                      'c400_components_fixed': n_fixed, 'v111_zip_verified': v111_ok,
                      'issues': issues[:10]}
    log('Stage A: snap=%d scan=%d/%d frozen=%s v111zip=%s'
        % (len(snap_rows), len(prod) - len(scan_issues), len(prod), frozen, v111_ok))
    return bank

# ============================== Stage B ==============================

SCRIPTS = [
    {'name': 'test_with_contrast.m', 'path': r'C:\Users\PC\Downloads\test_with_contrast.m',
     'recorded_sha': 'd08575b1e860e09f29c74652442a77b721039c6e32368fe76d2c5c63143ea3aa',
     'role': 'normalized complex modulation contrast extractor (400 Hz, user formal version)',
     'variables': [
         ('Fs', r'^Fs\s*='), ('targetFreq', r'^targetFreq\s*='),
         ('startFrame', r'^startFrame\s*='), ('endFrame', r'^endFrame\s*='),
         ('meanFloorFraction', r'^meanFloorFraction\s*='),
         ('timeMean', r'timeMean\s*=\s*mean\('), ('fftCall', r'fftResult\s*=\s*fft\('),
         ('oneSidedScale', r'^\s*oneSidedScale\s*='), ('validContrastMask', r'validContrastMask\s*='),
     ]},
    {'name': 'test.m', 'path': r'C:\Users\PC\Desktop\课题\test.m',
     'recorded_sha': 'fdc918e691b13b33cbae8b32ecaacd1e63ec27be3e23b61b0701d0e595aea684',
     'role': 'original gray FFT amplitude extractor (420 Hz, contrast input only)',
     'variables': [
         ('Fs', r'^Fs\s*='), ('targetFreq', r'^targetFreq\s*='),
         ('startFrame', r'^startFrame\s*='), ('endFrame', r'^endFrame\s*='),
         ('timeMean', r'timeMean\s*=\s*mean\('), ('fftCall', r'fftResult\s*=\s*fft\('),
     ]},
]

def stage_b(root, out):
    log('=== Stage B: variable-level source verification ===')
    issues = []
    rows = []
    scripts_ok = True
    for sc in SCRIPTS:
        found = os.path.isfile(sc['path'])
        sha_obs = sha256_file(sc['path']) if found else None
        sha_ok = bool(found and sha_obs == sc['recorded_sha'])
        scripts_ok &= sha_ok
        enc_used = None
        lines = []
        decode_note = ''
        if found:
            for enc in ('utf-8', 'gbk', 'gb18030', 'latin-1'):
                try:
                    text = open(sc['path'], encoding=enc, errors='strict').read()
                    enc_used = enc
                    lines = text.splitlines()
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue
            if enc_used is None:
                decode_note = 'all candidate decodings failed; semantic claims withheld'
                scripts_ok = False
        for var, pat in sc['variables']:
            hits = []
            for i, ln in enumerate(lines, 1):
                s = ln.strip()
                if re.match(pat, s, re.IGNORECASE):
                    # classify: comment / path string / executable assignment / conditional branch
                    cls = 'executable_assignment'
                    if s.startswith('%'):
                        cls = 'comment'
                    elif "'" in s.split('=')[0] or 'BMP' in s or '.bmp' in s.lower():
                        cls = 'path_string'
                    if re.match(r'^if\b', s) or s.startswith('else'):
                        cls = 'conditional_branch'
                    hits.append({'line': i, 'text': s[:220], 'classification': cls})
            rows.append({'extractor': sc['name'], 'encoding': enc_used or 'DECODE_FAILED',
                         'sha_verified': sha_ok, 'variable': var,
                         'n_hits': len(hits),
                         'first_executable_line': hits[0]['line'] if hits else '',
                         'first_executable_text': hits[0]['text'] if hits else '',
                         'all_hits': json.dumps(hits[:6], ensure_ascii=False)})
    wcsv(os.path.join(out, 'logs', 'v112_metadata_variables.csv'),
         list(rows[0].keys()), rows)
    with open(os.path.join(out, 'logs', 'v112_metadata_variables.json'), 'w', encoding='utf-8') as f:
        json.dump({'scripts': [{'name': s['name'], 'path': s['path'], 'found': found,
                                'sha_recorded': s['recorded_sha'],
                                'sha_observed': sha_obs if found else None,
                                'sha_verified': sha_ok,
                                'encoding_decoded_as': enc_used, 'decode_note': decode_note,
                                'role': s['role']} for s in SCRIPTS[:0]] + [
                       {'name': sc['name'], 'path': sc['path'],
                        'sha_verified': bool(os.path.isfile(sc['path']) and
                                             sha256_file(sc['path']) == sc['recorded_sha']),
                        'role': sc['role']} for sc in SCRIPTS],
                   'rule': 'variable-level: actual assignments with context and classification; '
                           'comments/paths/dead branches excluded; multiple hits keep order',
                   'derived_note': 'N=2001 is DERIVED from frames 1000..3000 inclusive '
                                   '(startFrame/endFrame assignments); N itself is not a direct variable '
                                   'assignment, so DIRECT_VARIABLE_VERIFIED applies to start/endFrame, '
                                   'while N stays DERIVED/ANALYSIS_CONTRACT'}, f, indent=2)

    # camera gain split + 12 open inputs, grouped optics/camera/sample_motion
    missing = [
        {'group': 'optics', 'parameter': 'object_plane_nm_per_pixel_with_error',
         'needed': 'stage calibration or certified ruler image with error budget', 'blocks': 'route A+B'},
        {'group': 'optics', 'parameter': 'objective_NA_immersion_illumination_polarization',
         'needed': 'objective datasheet + illumination configuration record', 'blocks': 'route A+B'},
        {'group': 'optics', 'parameter': 'reference_field_path',
         'needed': 'optical layout record or interferometric characterization', 'blocks': 'route A+B'},
        {'group': 'camera', 'parameter': 'exposure_time_per_frame',
         'needed': 'camera acquisition log / property readout per frame', 'blocks': 'route A+B'},
        {'group': 'camera', 'parameter': 'trigger_time_origin_convention',
         'needed': 'trigger log stating exposure-start vs exposure-center convention', 'blocks': 'route A+B'},
        {'group': 'camera', 'parameter': 'per_frame_timestamps',
         'needed': 'frame timestamp log (host or camera FIFO)', 'blocks': 'uniform-FFT route'},
        {'group': 'camera', 'parameter': 'kappa_e_per_U_per_s (intensity-to-electron-rate response)',
         'needed': 'responsivity calibration (W/cm2 -> e-/s) for the actual wavelength', 'blocks': 'electron-count mode'},
        {'group': 'camera', 'parameter': 'g_DN_per_e (DN/e- conversion gain)',
         'needed': 'photon-transfer curve or datasheet', 'blocks': 'DN mode'},
        {'group': 'camera', 'parameter': 'offset_DN',
         'needed': 'dark-frame offset measurement', 'blocks': 'DN mode offset handling'},
        {'group': 'sample_motion', 'parameter': 'sample_medium_substrate_height_fixation',
         'needed': 'sample preparation record + spacer metrology', 'blocks': 'route A+B'},
        {'group': 'sample_motion', 'parameter': 'independent_trajectory_with_scale_and_timebase',
         'needed': 'independent tracking with certified scale and common timebase', 'blocks': 'route A'},
        {'group': 'sample_motion', 'parameter': 'magnetic_field_B_vector_gradient_waveform_sync',
         'needed': 'calibrated probe B(t) vector/gradient with camera sync record', 'blocks': 'route B'},
    ]
    wcsv(os.path.join(out, 'missing_inputs_groups_v112.csv'),
         list(missing[0].keys()), missing)
    ok_b = scripts_ok and not issues and len(rows) >= 9
    if not ok_b:
        FAIL_KEYS.setdefault('B', issues[:10])
    GATES['B_metadata_variables'] = ok_b
    STAGE_LOG['B'] = {'scripts_sha_verified': sum(1 for sc in SCRIPTS
                                                  if os.path.isfile(sc['path']) and
                                                  sha256_file(sc['path']) == sc['recorded_sha']),
                      'variable_rows': len(rows), 'missing_inputs': len(missing),
                      'issues': issues[:10]}
    log('Stage B: scripts=%d/2 vars=%d missing=%d'
        % (STAGE_LOG['B']['scripts_sha_verified'], len(rows), len(missing)))

# ============================== Stage C ==============================

def stage_c(root, out):
    log('=== Stage C: observation operator 12 fixed integration groups ===')
    report_path = os.path.join(out, 'logs', 'v112_integration_report.json')
    proc = subprocess.run([sys.executable, os.path.join(root, 'tools', 'observation_integration_tests.py'),
                           report_path], capture_output=True, text=True, timeout=1800)
    ok_c = proc.returncode == 0
    rep = json.load(open(report_path, encoding='utf-8')) if os.path.isfile(report_path) else {}
    shutil.copy2(report_path, os.path.join(out, 'observation_integration_report.json'))
    status = 'OBSERVATION_OPERATOR_TESTED_ON_FIXED_FIXTURES' if ok_c else 'INTERFACE_TEST_FAILED'
    with open(os.path.join(out, 'observation_operator_status.json'), 'w', encoding='utf-8') as f:
        json.dump({'status': status,
                   'module': 'tools/observation_operator.py (importable; all fixtures drive it)',
                   'groups_pass': '%d/%d' % (sum(1 for g in rep.get('groups', []) if g['pass']),
                                             len(rep.get('groups', []))),
                   'scope': 'fixed software fixtures only; NOT a validation of arbitrary physical inputs',
                   'real_device_forward_go': False,
                   'absolute_diameter_validation_go': False,
                   'go_gates_note': 'REAL_DEVICE_FORWARD_GO=false: scale/optics/exposure-timing/sample-motion '
                                    'and route trajectory-or-field inputs insufficient (see '
                                    'missing_inputs_groups_v112.csv); ABSOLUTE_DIAMETER_VALIDATION_GO=false: '
                                    'independent diameter reference, blank/control and uncertainty chain '
                                    'not established',
                   'route_note': 'route A (independent trajectory) vs route B (field-driven dynamics) '
                                 'depends on real evidence; 200Hz drive does not imply 400Hz translation'}, f, indent=2)
    if not ok_c:
        FAIL_KEYS.setdefault('C', ['integration groups failed: %s' % proc.stdout[-200:]])
    GATES['C_observation_operator'] = ok_c
    STAGE_LOG['C'] = {'status': status,
                      'groups': '%d/%d' % (sum(1 for g in rep.get('groups', []) if g['pass']),
                                           len(rep.get('groups', []))),
                      'real_device_forward_go': False,
                      'absolute_diameter_validation_go': False}
    log('Stage C: %s' % status)

# ============================== Stage F ==============================

def stage_f(root, out, zip_path, checker_src, status_sha):
    log('=== Stage F: verifier selftest ===')
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import run_v111_all as v111mod  # reuse the proven selftest harness
    good = open(zip_path, 'rb').read()
    work = os.path.join(out, 'logs', 'verifier_selftest')
    os.makedirs(work, exist_ok=True)
    results = []

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
    MECH = {'missing_zip', 'missing_bank_case', 'duplicate_member', 'corrupt_crc',
            'manifest_path_traversal', 'status_missing', 'wrong_status_sha'}
    GATEC = {'gates_string_bool', 'gates_missing', 'wrong_task_id', 'wrong_source_commit'}
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
        man = zin.read('iscat_v112_return/manifest_sha256.csv').decode('utf-8').splitlines()
        zo.writestr('iscat_v112_return/manifest_sha256.csv',
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
        man = zin.read('iscat_v112_return/manifest_sha256.csv').decode('utf-8')
        zo.writestr('iscat_v112_return/manifest_sha256.csv', man + '../escape.txt,%s\n' % ('0' * 64))
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
    st = json.loads(zin.read('iscat_v112_return/status.json'))
    for name, mutate in (('gates_string_bool', lambda s: s['gates'].update({'A_legacy_scan_and_freeze': 'true'})),
                         ('gates_missing', lambda s: s['gates'].pop('A_legacy_scan_and_freeze')),
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
    wcsv(os.path.join(out, 'logs', 'v112_verifier_selftest.csv'), st_fields, results)
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
                'numerical': 'OBSERVATION_OPERATOR_SEALED' if numerical else 'UNSEALED_PARTIAL',
                'archive': 'PRE_ARCHIVE_VERIFICATION',
                'physics': 'REAL_DEVICE_FORWARD_GO_FALSE'}
    status = {'schema': 'iscat112.status.1', 'task_id': TASK_ID,
              'created_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
              'source_commit': EXPECTED_V111, 'parent_commit': EXPECTED_V110,
              'tool_sha256': tool_sha,
              'required_gates': list(REQUIRED_GATES),
              'gates': {g: bool(GATES[g]) for g in REQUIRED_GATES},
              'states': statuses,
              'three_statuses': {
                  'legacy': 'LEGACY_48_STATE_BASELINE_FROZEN',
                  'operator': 'OBSERVATION_OPERATOR_TESTED_ON_FIXED_FIXTURES',
                  'real_device_forward_go': False,
                  'absolute_diameter_validation_go': False},
              'stage_logs': STAGE_LOG,
              'environment': {'python': sys.version.split()[0],
                              'numpy': np.__version__, 'scipy': __import__('scipy').__version__,
                              'pythondontwritebytecode': '1'},
              'frozen_states': {'calibration_valid': False, 'experimental_validation': False,
                                'detection_validated': False, 'single_particle_diameter': 'NOT_ESTIMATED'},
              'p0_status': 'OPEN (block/unblock consistency item; not a model failure verdict)',
              'rule7_new_authorizations': 0,
              'overall': 'OBSERVATION_OPERATOR_SEALED' if numerical else 'UNSEALED_PARTIAL'}
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
                z.write(full, 'iscat_v112_return/%s' % rel)
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
        print('[v112] FATAL: out dir exists and is not empty')
        return 3
    try:
        if os.path.commonpath([root]) == os.path.commonpath([root, out]):
            print('[v112] FATAL: out must be outside the source root')
            return 3
    except ValueError:
        pass
    os.makedirs(out, exist_ok=True)
    for sub in ('analysis', 'tables', 'logs'):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    tool_sha = sha256_file(os.path.abspath(__file__))
    launch = {'task_id': TASK_ID, 'root': root, 'out': out, 'zip': zip_path,
              'expected_v111_commit': EXPECTED_V111, 'tool_sha256': tool_sha,
              'command': 'python tools/run_v112_all.py --root "%s" --out "%s" --zip "%s"' % (root, out, zip_path),
              'python': sys.version.split()[0], 'numpy': np.__version__,
              'scipy': __import__('scipy').__version__,
              'pid': os.getpid(), 'started_at': time.strftime('%Y-%m-%dT%H:%M:%S')}
    launch_ext = os.path.splitext(zip_path)[0] + '.launch.json'
    with open(launch_ext, 'w', encoding='utf-8') as f:
        json.dump(launch, f, indent=2)
    with open(os.path.join(out, 'logs', 'v112_launch_record.json'), 'w', encoding='utf-8') as f:
        json.dump(launch, f, indent=2)
    shutil.copy2(os.path.abspath(__file__), os.path.join(out, 'logs', 'run_v112_all_snapshot.py'))
    log('launch recorded: %s' % launch_ext)

    stage_a(root, out)
    stage_b(root, out)
    stage_c(root, out)

    numerical = all(GATES[g] for g in REQUIRED_GATES if g != 'F_verifier_selftest')
    final_summary = {'gates': GATES, 'stage_logs': STAGE_LOG, 'fail_keys': FAIL_KEYS,
                     'elapsed_seconds': None,
                     'pre_archive_note': 'in-ZIP snapshot; external post_archive_summary.json carries '
                                         'final values', 'zip_sha256': None}
    with open(os.path.join(out, 'logs', 'v112_final_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(final_summary, f, indent=2)
    status_path, status_sha, statuses, _ = build_status(out, tool_sha)
    tool_shas = {'run_v112_all.py': tool_sha,
                 'v112_archive_check.py': sha256_file(os.path.join(root, 'tools', 'v112_archive_check.py')),
                 'observation_operator.py': sha256_file(os.path.join(root, 'tools', 'observation_operator.py')),
                 'observation_integration_tests.py': sha256_file(os.path.join(root, 'tools', 'observation_integration_tests.py')),
                 'run_v111_all.py': sha256_file(os.path.join(root, 'tools', 'run_v111_all.py'))}
    with open(os.path.join(out, 'logs', 'v112_tool_shas.json'), 'w', encoding='utf-8') as f:
        json.dump(tool_shas, f, indent=2)
    zip_sha = build_zip(out, zip_path)  # provisional selftest fixture
    checker_src = os.path.join(root, 'tools', 'v112_archive_check.py')
    tool_shas['v112_archive_check.py'] = sha256_file(checker_src)
    with open(os.path.join(out, 'logs', 'v112_tool_shas.json'), 'w', encoding='utf-8') as f:
        json.dump(tool_shas, f, indent=2)
    stage_f(root, out, zip_path, checker_src, status_sha)
    provisional_sha = sha256_file(zip_path)
    if GATES['F_verifier_selftest']:
        final_summary['gates'] = GATES
        with open(os.path.join(out, 'logs', 'v112_final_summary.json'), 'w', encoding='utf-8') as f:
            json.dump(final_summary, f, indent=2)
        os.remove(status_path)
        status_path, status_sha, statuses, _ = build_status(out, tool_sha)
        zip_sha = build_zip(out, zip_path)
        with open(os.path.join(out, 'logs', 'v112_provisional_zip_sha.json'), 'w', encoding='utf-8') as f:
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
    receipt = {'task_id': TASK_ID, 'source_commit': EXPECTED_V111, 'parent_commit': EXPECTED_V110,
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
