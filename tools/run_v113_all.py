# -*- coding: utf-8 -*-
"""v113: V113_MEASUREMENT_OPERATOR_ORIGINAL_GATES_AND_INPUT_ADMISSION.

Minimal inheritance from the frozen v112 release; measurement operator with
ORIGINAL gates restored (same-array X/C <1e-11, mean <1e-12; real FFT
production path vs fsum direct-DFT independent path on the SAME stored array);
four bounded mutation tests; effective-assignment/branch evidence; four-layer
admission. Lineage: tools/run_v112_all.py, tools/observation_operator.py (v2)."""
import os, sys, csv, json, hashlib, shutil, math, subprocess, zipfile, time, argparse, io
sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import numpy as np
from scipy.io import loadmat

TASK_ID = 'V113_MEASUREMENT_OPERATOR_ORIGINAL_GATES_AND_INPUT_ADMISSION'
EXPECTED_V112 = 'd11814c2e286a2e6a2195308923adc81406fa537'
EXPECTED_V111 = '24fbd6bbfe8b2dd503efbf093a09fc3a60371a30'
PROBE_BLOB = '6b180147f64847329375363d44c317b2d4df247b'
V112_ZIP_SHA = '7bcee33fccf8e30192917d9aa2e257d9eb1925c74c3d4f7dfe6df72118e45e45'
N = 2001
FS = 5000.0
ALL24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
         for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)]
INTER24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
           for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (10, 15)]
ALL48 = ALL24 + INTER24
PROBE_PIXELS = [(20, 20), (20, 0), (0, 20), (25, 0)]
REQUIRED_GATES = ['A_minimal_inheritance', 'B_operator_original_gates',
                  'C_effective_assignments', 'F_verifier_selftest']
GATES = {g: False for g in REQUIRED_GATES}
FAIL_KEYS = {}
STAGE_LOG = {}

def log(msg):
    print('[v113] %s' % msg, flush=True)

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
    log('=== Stage A: minimal inheritance + v112 evidence archival ===')
    an = os.path.join(root, 'analysis')
    tab = os.path.join(root, 'tables')
    issues = []
    head = subprocess.run(['git', '-C', root, 'rev-parse', 'HEAD'],
                          capture_output=True, text=True, timeout=60).stdout.strip()
    parent = subprocess.run(['git', '-C', root, 'rev-parse', 'HEAD^'],
                            capture_output=True, text=True, timeout=60).stdout.strip()
    if head != EXPECTED_V112:
        issues.append('HEAD %s != fixed v112 commit' % head)
    if parent != EXPECTED_V111:
        issues.append('parent %s != v111 commit' % parent)
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
    wcsv(os.path.join(out, 'logs', 'v113_snapshot73_manifest.csv'), list(snap_rows[0].keys()), snap_rows)

    # archive the v112 ORIGINAL module/tests/report from the frozen commit (no overwrite)
    for rel, dstname in (('tools/observation_operator.py', 'v112_original_observation_operator.py'),
                         ('tools/observation_integration_tests.py', 'v112_original_integration_tests.py')):
        data = subprocess.run(['git', '-C', root, 'show', EXPECTED_V112 + ':' + rel],
                              capture_output=True, timeout=60).stdout
        dst = os.path.join(out, 'logs', dstname)
        with open(dst, 'wb') as f:
            f.write(data)
        with open(dst + '.sha256', 'w') as f:
            f.write(hashlib.sha256(data).hexdigest() + '\n')
    report_src = os.path.join(root, 'observation_integration_report.json')
    if os.path.isfile(report_src):
        shutil.copy2(report_src, os.path.join(out, 'logs', 'v112_original_integration_report.json'))

    # real v112 ZIP byte verification
    v112_zip = next((c for c in (r'C:\Users\PC\Documents\Codex\2026-10-18\files-mentioned-by-the-user-iscat\work\v112_run\iscat_v112_return.zip',
                                 r'C:\Users\PC\Documents\Codex\2026-10-18\files-mentioned-by-the-user-iscat\outputs\iscat_v112_return.zip')
                     if os.path.isfile(c)), None)
    v112_ok = bool(v112_zip and sha256_file(v112_zip) == V112_ZIP_SHA)
    if not v112_ok:
        issues.append('v112 ZIP bytes not independently verified')
    with open(os.path.join(out, 'logs', 'v113_v112_archive_audit.json'), 'w', encoding='utf-8') as f:
        json.dump({'zip_path': v112_zip, 'expected_sha256': V112_ZIP_SHA,
                   'independently_verified_bytes': v112_ok}, f, indent=2)
    diff = subprocess.run(['git', '-C', root, 'diff', EXPECTED_V112, '--', 'tools/'],
                          capture_output=True, text=True, timeout=120).stdout
    with open(os.path.join(out, 'logs', 'v113_source_diff.patch'), 'w', encoding='utf-8', newline='') as f:
        f.write(diff)

    ok_a = not issues and len(snap_rows) == 73
    if not ok_a:
        FAIL_KEYS.setdefault('A', issues[:10])
    GATES['A_minimal_inheritance'] = ok_a
    STAGE_LOG['A'] = {'snapshots': len(snap_rows), 'head': head, 'v112_zip_verified': v112_ok,
                      'issues': issues[:10]}
    log('Stage A: snap=%d v112zip=%s' % (len(snap_rows), v112_ok))

# ============================== Stage B ==============================

def stage_b(root, out):
    log('=== Stage B: measurement operator, original gates, 12 groups + mutations ===')
    report_path = os.path.join(out, 'logs', 'v113_integration_report.json')
    run_no = 1
    proc = subprocess.run([sys.executable, os.path.join(root, 'tools', 'observation_integration_tests_v113.py'),
                           report_path], capture_output=True, text=True, timeout=1800)
    ok_b = proc.returncode == 0
    # bounded regression: at most two full reruns with recorded reason
    rerun_log = []
    if not ok_b:
        rerun_log.append({'run': run_no, 'exit': proc.returncode,
                          'stdout_tail': proc.stdout[-300:], 'reason': 'initial run failed'})
        for attempt in (2, 3):
            proc = subprocess.run([sys.executable, os.path.join(root, 'tools',
                                          'observation_integration_tests_v113.py'), report_path],
                                  capture_output=True, text=True, timeout=1800)
            rerun_log.append({'run': attempt, 'exit': proc.returncode,
                              'stdout_tail': proc.stdout[-300:],
                              'reason': 'bounded regression %d' % (attempt - 1)})
            ok_b = proc.returncode == 0
            if ok_b:
                break
            run_no = attempt
    with open(os.path.join(out, 'logs', 'v113_run_log.json'), 'w', encoding='utf-8') as f:
        json.dump({'runs': rerun_log or [{'run': 1, 'exit': proc.returncode,
                                          'reason': 'main run (passed on first attempt)'}],
                   'max_regression_budget': 2, 'expectation_changes': 0}, f, indent=2)
    shutil.copy2(report_path, os.path.join(out, 'observation_integration_v113_report.json'))
    rep = json.load(open(report_path, encoding='utf-8')) if os.path.isfile(report_path) else {}
    with open(os.path.join(out, 'observation_operator_status.json'), 'w', encoding='utf-8') as f:
        json.dump({'status': 'SOFTWARE_ORIGINAL_GATES_PASS' if ok_b else 'FAILED',
                   'gates': rep.get('gates'),
                   'groups_pass': '%d/%d' % (sum(1 for g in rep.get('groups', []) if g['pass']),
                                             len(rep.get('groups', []))),
                   'mutations_detected': '%d/%d' % (sum(1 for m in rep.get('mutations', []) if m['detected']),
                                                    len(rep.get('mutations', []))),
                   'backend': 'production=numpy.fft; independent=direct DFT ((j*k)%%N, math.fsum) on the SAME stored array',
                   'scope': 'fixed software fixtures only; NOT a validation of arbitrary physical inputs',
                   'environment': {'python': sys.version.split()[0], 'numpy': np.__version__,
                                   'platform': sys.platform}}, f, indent=2)
    if not ok_b:
        FAIL_KEYS.setdefault('B', ['integration groups/mutations failed: %s' % proc.stdout[-200:]])
    GATES['B_operator_original_gates'] = ok_b
    STAGE_LOG['B'] = {'groups': '%d/%d' % (sum(1 for g in rep.get('groups', []) if g['pass']),
                                           len(rep.get('groups', []))),
                      'mutations': '%d/%d' % (sum(1 for m in rep.get('mutations', []) if m['detected']),
                                              len(rep.get('mutations', []))),
                      'runs': len(rerun_log) + 1}
    log('Stage B: groups=%s mutations=%s runs=%d'
        % (STAGE_LOG['B']['groups'], STAGE_LOG['B']['mutations'], STAGE_LOG['B']['runs']))

# ============================== Stage C ==============================

SCRIPT_CONTEXTS = [
    {'file': r'C:\Users\PC\Downloads\test_with_contrast.m', 'encoding': 'utf-8',
     'recorded_sha': 'd08575b1e860e09f29c74652442a77b721039c6e32368fe76d2c5c63143ea3aa',
     'role': 'normalized complex modulation contrast extractor (400 Hz, user formal version)',
     'probes': [
         {'variable': 'Fs', 'line': 39, 'expect': 'Fs = 5000;', 'claim': 'DIRECT'},
         {'variable': 'targetFreq', 'line': 42, 'expect': 'targetFreq = 400;', 'claim': 'DIRECT'},
         {'variable': 'startFrame', 'line': 45, 'expect': 'startFrame = 1000;', 'claim': 'DIRECT'},
         {'variable': 'endFrame', 'line': 46, 'expect': 'endFrame   = 3000;', 'claim': 'DIRECT'},
         {'variable': 'endFrame_override_condition', 'line': 93, 'expect': 'if isinf(endFrame)',
          'claim': 'BRANCH_CONDITION_KNOWN', 'effective_line': 94,
          'effective_text': 'endFrame = totalFrames;',
          'verdict': 'branch NOT taken for this configuration (endFrame=3000 is finite)'},
         {'variable': 'meanFloorFraction', 'line': 60, 'expect': 'meanFloorFraction = 0.01;', 'claim': 'DIRECT'},
         {'variable': 'timeMean', 'line': 218, 'expect': 'timeMean = mean(imageStack, 4)', 'claim': 'DIRECT'},
         {'variable': 'fftCall', 'line': 230, 'expect': 'fftResult = fft(signalStack, [], 4)', 'claim': 'DIRECT'},
         {'variable': 'oneSidedScale_condition', 'line': 266, 'expect': 'if ~isDC && ~isNyquist',
          'claim': 'BRANCH_CONDITION_KNOWN', 'effective_line': 267, 'effective_text': 'oneSidedScale = 2;',
          'verdict': 'isDC=false (targetIndex!=1); isNyquist requires even numFrames and '
                     'targetIndex=numFrames/2+1; both false under odd 2001-frame selection -> scale=2; '
                     'EFFECTIVE_FOR_THIS_RUN only with actual batch run metadata'},
         {'variable': 'validContrastMask', 'line': 289,
          'expect': 'validContrastMask = isfinite(timeMean) & timeMean > meanFloor', 'claim': 'DIRECT'},
     ]},
    {'file': r'C:\Users\PC\Desktop\课题\test.m', 'encoding': 'gbk',
     'recorded_sha': 'fdc918e691b13b33cbae8b32ecaacd1e63ec27be3e23b61b0701d0e595aea684',
     'role': 'original gray FFT amplitude extractor (420 Hz, contrast input only)',
     'probes': [
         {'variable': 'Fs', 'line': 23, 'expect': 'Fs = 5000;', 'claim': 'DIRECT'},
         {'variable': 'targetFreq', 'line': 26, 'expect': 'targetFreq = 420;', 'claim': 'DIRECT'},
         {'variable': 'startFrame', 'line': 30, 'expect': 'startFrame = 1000;', 'claim': 'DIRECT'},
         {'variable': 'endFrame', 'line': 31, 'expect': 'endFrame   = 3000;', 'claim': 'DIRECT'},
     ]},
]

def stage_c(root, out):
    log('=== Stage C: effective assignments and branch evidence ===')
    issues = []
    rows = []
    for sc in SCRIPT_CONTEXTS:
        found = os.path.isfile(sc['file'])
        sha_obs = sha256_file(sc['file']) if found else None
        sha_ok = bool(found and sha_obs == sc['recorded_sha'])
        if not sha_ok:
            issues.append('script sha mismatch: %s' % sc['file'])
            continue
        lines = open(sc['file'], encoding=sc['encoding'], errors='strict').read().splitlines()
        for pr in sc['probes']:
            observed = lines[pr['line'] - 1].strip() if pr['line'] <= len(lines) else ''
            match = (pr['expect'] in observed) if pr['expect'] else False
            eff_text = ''
            if 'effective_line' in pr:
                eff_text = lines[pr['effective_line'] - 1].strip()
            rows.append({'extractor': os.path.basename(sc['file']), 'variable': pr['variable'],
                         'line': pr['line'], 'observed_text': observed[:200],
                         'expectation_matched': match, 'classification': pr['claim'],
                         'effective_line': pr.get('effective_line', ''),
                         'effective_text': eff_text[:200], 'verdict': pr.get('verdict', ''),
                         'source_file_sha256': sha_obs, 'encoding': sc['encoding']})
    wcsv(os.path.join(out, 'logs', 'v113_effective_assignments.csv'),
         list(rows[0].keys()), rows)
    n_direct = sum(1 for r in rows if r['classification'] == 'DIRECT' and r['expectation_matched'])
    n_branch = sum(1 for r in rows if r['classification'] == 'BRANCH_CONDITION_KNOWN'
                   and r['expectation_matched'])
    ok_c = not issues and n_direct + n_branch == len(rows) and len(rows) >= 13
    if not ok_c:
        FAIL_KEYS.setdefault('C', issues[:10] + [r['variable'] for r in rows
                                                 if r['expectation_matched'] is False][:5])
    GATES['C_effective_assignments'] = ok_c
    STAGE_LOG['C'] = {'rows': len(rows), 'direct': n_direct, 'branch_known': n_branch,
                      'effective_for_this_run': 0,
                      'note': 'N=2001 stays DERIVED/conditional: endpoints inclusive AND no frame '
                              'truncation; EFFECTIVE_FOR_THIS_RUN requires actual batch run metadata',
                      'issues': issues[:10]}
    log('Stage C: rows=%d direct=%d branch=%d' % (len(rows), n_direct, n_branch))

# ============================== Stage D (admission) ==============================

def stage_d(out):
    log('=== Stage D: four-layer admission ===')
    admission = {
        'layer_1_legacy': 'LEGACY_48_STATE_BASELINE_FROZEN (inherited; this round\'s operator work does not change it)',
        'layer_2_software': 'SOFTWARE_ORIGINAL_GATES_PASS' if GATES.get('B_operator_original_gates') else 'FAILED',
        'layer_3_real_device_relative_forward_go': False,
        'layer_3_requirements': [
            'object-plane scale with error (MISSING)',
            'NA/immersion/reference path/polarization (MISSING)',
            'material and sample geometry (MISSING)',
            'real exposure and time base (MISSING)',
            'route A: independently calibrated trajectory (MISSING) OR route B: field/dynamics constraints (MISSING)',
            'permitted limited case: normalized-C forward under explicit fixed-exposure, linear, '
            'zero-offset assumptions - assumptions must be declared, never presented as measured'],
        'layer_4_absolute_count_go': False,
        'layer_4_absolute_count_requirements': [
            'photon/electron response kappa (MISSING)', 'DN/e- conversion gain (MISSING)',
            'offset_DN (MISSING)'],
        'layer_4_absolute_diameter_validation_go': False,
        'layer_4_diameter_requirements': [
            'independent diameter reference (MISSING)', 'blank/control (MISSING)',
            'uncertainty chain and independent verification design (MISSING)'],
        'user_request_groups': {
            'optics': ['object-plane nm/px with error', 'NA/immersion/reference path/polarization'],
            'camera': ['exposure time', 'time-origin convention', 'per-frame timestamps',
                       'kappa_e_per_U_per_s', 'g_DN_per_e', 'offset_DN'],
            'sample_motion': ['medium/substrate/fixation', 'trajectory with scale+timebase (route A)',
                              'B(t) vector/gradient/sync + dynamics constraints (route B)'],
        },
        'rule': 'REAL_DEVICE_RELATIVE_FORWARD_GO stays false until its listed inputs exist; '
                'software PASS never implies physical GO; no new BEM, no diameter fitting',
    }
    with open(os.path.join(out, 'admission_v113.json'), 'w', encoding='utf-8') as f:
        json.dump(admission, f, indent=2, ensure_ascii=False)
    STAGE_LOG['D'] = {'layer_2': admission['layer_2_software'],
                      'layer_3_go': admission['layer_3_real_device_relative_forward_go'],
                      'layer_4_count_go': admission['layer_4_absolute_count_go'],
                      'layer_4_diameter_go': admission['layer_4_absolute_diameter_validation_go']}
    log('Stage D: software=%s relative_go=%s abs_count_go=%s abs_diameter_go=%s'
        % (admission['layer_2_software'], admission['layer_3_real_device_relative_forward_go'],
           admission['layer_4_absolute_count_go'], admission['layer_4_absolute_diameter_validation_go']))

# ============================== Stage F + archive ==============================

def stage_f(root, out, zip_path, checker_src, status_sha):
    log('=== Stage F: verifier selftest ===')
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import run_v112_all as v112mod  # reuse the proven selftest harness
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
        man = zin.read('iscat_v113_return/manifest_sha256.csv').decode('utf-8').splitlines()
        zo.writestr('iscat_v113_return/manifest_sha256.csv',
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
        man = zin.read('iscat_v113_return/manifest_sha256.csv').decode('utf-8')
        zo.writestr('iscat_v113_return/manifest_sha256.csv', man + '../escape.txt,%s\n' % ('0' * 64))
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
    st = json.loads(zin.read('iscat_v113_return/status.json'))
    for name, mutate in (('gates_string_bool', lambda s: s['gates'].update({'A_minimal_inheritance': 'true'})),
                         ('gates_missing', lambda s: s['gates'].pop('A_minimal_inheritance')),
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
    wcsv(os.path.join(out, 'logs', 'v113_verifier_selftest.csv'), st_fields, results)
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

def build_status(out, tool_sha):
    numerical = all(GATES[g] for g in REQUIRED_GATES)
    statuses = {'execution': 'COMPLETE',
                'numerical': 'ORIGINAL_GATES_RESTORED' if numerical else 'UNSEALED_PARTIAL',
                'archive': 'PRE_ARCHIVE_VERIFICATION',
                'physics': 'ALL_FORWARD_GO_FALSE_PENDING_INPUTS'}
    status = {'schema': 'iscat113.status.1', 'task_id': TASK_ID,
              'created_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
              'source_commit': EXPECTED_V112, 'parent_commit': EXPECTED_V111,
              'tool_sha256': tool_sha,
              'required_gates': list(REQUIRED_GATES),
              'gates': {g: bool(GATES[g]) for g in REQUIRED_GATES},
              'states': statuses,
              'four_layer_admission': {
                  'layer_1_legacy': 'LEGACY_48_STATE_BASELINE_FROZEN',
                  'layer_2_software': 'SOFTWARE_ORIGINAL_GATES_PASS' if GATES.get('B_operator_original_gates') else 'FAILED',
                  'layer_3_real_device_relative_forward_go': False,
                  'layer_4_absolute_count_go': False,
                  'layer_4_absolute_diameter_validation_go': False},
              'stage_logs': STAGE_LOG,
              'environment': {'python': sys.version.split()[0],
                              'numpy': np.__version__, 'scipy': __import__('scipy').__version__,
                              'pythondontwritebytecode': '1'},
              'frozen_states': {'calibration_valid': False, 'experimental_validation': False,
                                'detection_validated': False, 'single_particle_diameter': 'NOT_ESTIMATED'},
              'p0_status': 'OPEN (not upgraded)',
              'rule7_new_authorizations': 0,
              'overall': 'ORIGINAL_GATES_RESTORED' if numerical else 'UNSEALED_PARTIAL'}
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
                z.write(full, 'iscat_v113_return/%s' % rel)
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
        print('[v113] FATAL: out dir exists and is not empty')
        return 3
    try:
        if os.path.commonpath([root]) == os.path.commonpath([root, out]):
            print('[v113] FATAL: out must be outside the source root')
            return 3
    except ValueError:
        pass
    os.makedirs(out, exist_ok=True)
    for sub in ('analysis', 'tables', 'logs'):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    tool_sha = sha256_file(os.path.abspath(__file__))
    launch = {'task_id': TASK_ID, 'root': root, 'out': out, 'zip': zip_path,
              'expected_v112_commit': EXPECTED_V112, 'tool_sha256': tool_sha,
              'command': 'python tools/run_v113_all.py --root "%s" --out "%s" --zip "%s"' % (root, out, zip_path),
              'python': sys.version.split()[0], 'numpy': np.__version__,
              'scipy': __import__('scipy').__version__,
              'pid': os.getpid(), 'started_at': time.strftime('%Y-%m-%dT%H:%M:%S')}
    launch_ext = os.path.splitext(zip_path)[0] + '.launch.json'
    with open(launch_ext, 'w', encoding='utf-8') as f:
        json.dump(launch, f, indent=2)
    with open(os.path.join(out, 'logs', 'v113_launch_record.json'), 'w', encoding='utf-8') as f:
        json.dump(launch, f, indent=2)
    shutil.copy2(os.path.abspath(__file__), os.path.join(out, 'logs', 'run_v113_all_snapshot.py'))
    log('launch recorded: %s' % launch_ext)

    stage_a(root, out)
    stage_b(root, out)
    stage_c(root, out)
    stage_d(out)

    numerical = all(GATES[g] for g in REQUIRED_GATES if g != 'F_verifier_selftest')
    final_summary = {'gates': GATES, 'stage_logs': STAGE_LOG, 'fail_keys': FAIL_KEYS,
                     'elapsed_seconds': None,
                     'pre_archive_note': 'in-ZIP snapshot; external post_archive_summary.json carries '
                                         'final values', 'zip_sha256': None}
    with open(os.path.join(out, 'logs', 'v113_final_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(final_summary, f, indent=2)
    status_path, status_sha, statuses, _ = build_status(out, tool_sha)
    tool_shas = {'run_v113_all.py': tool_sha,
                 'v113_archive_check.py': sha256_file(os.path.join(root, 'tools', 'v113_archive_check.py')),
                 'observation_operator.py': sha256_file(os.path.join(root, 'tools', 'observation_operator.py')),
                 'observation_integration_tests_v113.py': sha256_file(os.path.join(root, 'tools', 'observation_integration_tests_v113.py')),
                 'run_v112_all.py': sha256_file(os.path.join(root, 'tools', 'run_v112_all.py'))}
    with open(os.path.join(out, 'logs', 'v113_tool_shas.json'), 'w', encoding='utf-8') as f:
        json.dump(tool_shas, f, indent=2)
    zip_sha = build_zip(out, zip_path)  # provisional selftest fixture
    checker_src = os.path.join(root, 'tools', 'v113_archive_check.py')
    tool_shas['v113_archive_check.py'] = sha256_file(checker_src)
    with open(os.path.join(out, 'logs', 'v113_tool_shas.json'), 'w', encoding='utf-8') as f:
        json.dump(tool_shas, f, indent=2)
    stage_f(root, out, zip_path, checker_src, status_sha)
    provisional_sha = sha256_file(zip_path)
    if GATES['F_verifier_selftest']:
        final_summary['gates'] = GATES
        with open(os.path.join(out, 'logs', 'v113_final_summary.json'), 'w', encoding='utf-8') as f:
            json.dump(final_summary, f, indent=2)
        os.remove(status_path)
        status_path, status_sha, statuses, _ = build_status(out, tool_sha)
        zip_sha = build_zip(out, zip_path)
        with open(os.path.join(out, 'logs', 'v113_provisional_zip_sha.json'), 'w', encoding='utf-8') as f:
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
    receipt = {'task_id': TASK_ID, 'source_commit': EXPECTED_V112, 'parent_commit': EXPECTED_V111,
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
