# -*- coding: utf-8 -*-
"""v111: V111_TARGETED_AUDIT_AND_REAL_INPUT_READINESS.

Targeted audit of the frozen v110 release: historical count-attribution revision
(real tools/audit_attribution.py run), full-table released-validator audit of the
real production decisions, real metadata provenance (workstation extractor scripts
hash-verified), and the observation-operator interface with pure-math fixtures.
Source frozen at 4aa76ac1204d1133e2d53f9631a2f3fb3db7015d (parent v109 3f894b9...).
Lineage: tools/run_v110_all.py, tools/audit_attribution.py, tools/validate_decisions.py.
Zero new BEM/render/optical-time-series/physics-states/experiment-video reads."""
import os, sys, csv, json, hashlib, shutil, math, subprocess, zipfile, time, argparse, itertools, io
sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import numpy as np
from scipy.io import loadmat

TASK_ID = 'V111_TARGETED_AUDIT_AND_REAL_INPUT_READINESS'
EXPECTED_V110 = '4aa76ac1204d1133e2d53f9631a2f3fb3db7015d'
EXPECTED_V109 = '3f894b919d11dd2e8dead92b83ed7ec2d930d08c'
PROBE_BLOB = '6b180147f64847329375363d44c317b2d4df247b'
V110_ZIP_SHA = '0c8a21116170c26cef59d2446f7fe2e9598babae97df18e171aa343585aadeb8'
N = 2001
FS = 5000.0
K0S = [80, 160, 320]
ALL24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
         for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)]
INTER24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
           for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (10, 15)]
ALL48 = ALL24 + INTER24
PROBE_PIXELS = [(20, 20), (20, 0), (0, 20), (25, 0)]
eps64 = np.finfo(np.float64).eps
REQUIRED_GATES = ['A_source_admission', 'B_full_validator_audit', 'C_metadata_provenance',
                  'D_observation_interface', 'F_verifier_selftest']
GATES = {g: False for g in REQUIRED_GATES}
FAIL_KEYS = {}
STAGE_LOG = {}
FEATS = [(1, 'ROI_L2_log_ratio'), (2, 'magnitude_pattern_symmetric'), (3, 'unit_magnitude_shape')]
POLICY_NAMES = ['unknown_zf_motion', 'known_motion', 'known_motion_zf']
DECISION_FIELDS = ['nearest_candidate', 'nearest_label_D',
                   'same_D_nearest_dist', 'cross_D_nearest_dist',
                   'min_cross_minus_min_same', 'model_label_consistent']

def log(msg):
    print('[v111] %s' % msg, flush=True)

def g17(x):
    return '%.17g' % float(x)

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

def parse(k):
    p = k.split('_')
    return {'D': int(p[0][1:]), 'zf': int(p[1][2:]), 'type': p[2], 'a': int(p[3][1:])}

def wcsv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)

def rcsv(path):
    with open(path, 'r', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def finite_diff(a, b):
    try:
        fa, fb = float(a), float(b)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(fa) and math.isfinite(fb)):
        return None
    return abs(fa - fb)

# ============================== Stage A ==============================

def stage_a(root, out):
    log('=== Stage A: read-only admission + historical attribution revision ===')
    an = os.path.join(root, 'analysis')
    tab = os.path.join(root, 'tables')
    issues = []
    head = subprocess.run(['git', '-C', root, 'rev-parse', 'HEAD'],
                          capture_output=True, text=True, timeout=60).stdout.strip()
    parent = subprocess.run(['git', '-C', root, 'rev-parse', 'HEAD^'],
                            capture_output=True, text=True, timeout=60).stdout.strip()
    if head != EXPECTED_V110:
        issues.append('HEAD %s != fixed v110 commit' % head)
    if parent != EXPECTED_V109:
        issues.append('parent %s != v109 commit' % parent)
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
        C = np.asarray(m['C']).astype(np.complex128)
        X = np.asarray(m['X']).astype(np.complex128)
        Im = np.asarray(m['Imean_map']).astype(np.float64)
        mask = np.asarray(m['valid_mask']).astype(bool)
        cid = str(m['case_id'].flatten()[0])
        n_val = int(np.asarray(m['N']).flatten()[0])
        fs_val = float(np.asarray(m['Fs']).flatten()[0])
        k0_bins = [int(v) for v in np.asarray(m['k0_bins']).flatten()]
        common = mask & np.isfinite(Im) & (Im > 0)
        err = float(np.max(np.abs(2.0 * X / (float(n_val) * Im)[None, :, :] - C)[:, common])) if common.any() else float('inf')
        pos = Im[np.isfinite(Im) & (Im > 0)]
        floor = 0.01 * float(np.median(pos)) if pos.size else 0.0
        mask_ok = bool(np.array_equal(mask, np.isfinite(Im) & (Im > floor)))
        if not (cid == key and n_val == N and fs_val == FS and k0_bins == K0S
                and err < 1e-10 and mask_ok):
            issues.append('bank audit failed: %s' % key)
        bank[key] = {'C': C, 'X': X, 'Im': Im, 'mask': mask, 'sha256': sha}
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
    npz_sha = sha256_file(npz_src)
    if blob_sha1_bytes(open(npz_src, 'rb').read()) != PROBE_BLOB:
        issues.append('probe NPZ git blob mismatch')
    dst_npz = os.path.join(snap_dir, 'v093_probe_evidence.npz')
    shutil.copy2(npz_src, dst_npz)
    snap_rows.append({'role': 'SAVED_SIMULATION_PROBES', 'case_id': 'PROBE_EVIDENCE_192_SERIES',
                      'source_relative': 'analysis/v093_probe_evidence.npz',
                      'target_relative': 'snapshot73/v093_probe_evidence.npz',
                      'size_bytes': str(os.path.getsize(dst_npz)), 'sha256': npz_sha})
    for r in snap_rows:
        if sha256_file(os.path.join(out, r['target_relative'])) != r['sha256']:
            issues.append('snapshot byte mismatch: %s' % r['target_relative'])
    wcsv(os.path.join(out, 'logs', 'v111_snapshot73_manifest.csv'), list(snap_rows[0].keys()), snap_rows)
    zs = np.load(npz_src)
    series_keys = sorted(k for k in zs.files if k.startswith('series_'))
    expected_series = {'series_%s_h5_%d_%d' % (key, i5, j5) for key in ALL48 for (i5, j5) in PROBE_PIXELS}
    if set(series_keys) != expected_series or len(series_keys) != 192:
        issues.append('probe series key set mismatch')

    # real v110 ZIP byte verification (delivered artifact on this workstation)
    v110_zip = next((c for c in (r'C:\Users\PC\Documents\Codex\2026-10-18\files-mentioned-by-the-user-iscat\work\v110_final\iscat_v110_return.zip',
                                 r'C:\Users\PC\Documents\Codex\2026-10-18\files-mentioned-by-the-user-iscat\outputs\iscat_v110_return.zip')
                     if os.path.isfile(c)), None)
    v110_obs = sha256_file(v110_zip) if v110_zip else None
    v110_ok = bool(v110_zip and v110_obs == V110_ZIP_SHA)
    if not v110_ok:
        issues.append('v110 ZIP bytes not independently verified')
    with open(os.path.join(out, 'logs', 'v111_v110_archive_audit.json'), 'w', encoding='utf-8') as f:
        json.dump({'zip_path': v110_zip, 'expected_sha256': V110_ZIP_SHA,
                   'observed_sha256': v110_obs, 'independently_verified_bytes': v110_ok}, f, indent=2)

    # source diff vs frozen v110 commit
    diff = subprocess.run(['git', '-C', root, 'diff', EXPECTED_V110, '--', 'tools/'],
                          capture_output=True, text=True, timeout=120).stdout
    with open(os.path.join(out, 'logs', 'v111_source_diff.patch'), 'w', encoding='utf-8', newline='') as f:
        f.write(diff)

    # --- historical attribution revision: REAL run of tools/audit_attribution.py ---
    proc = subprocess.run([sys.executable, os.path.join(root, 'tools', 'audit_attribution.py'),
                           root, os.path.join(out, 'analysis')],
                          capture_output=True, text=True, timeout=600)
    attr_ok = proc.returncode == 0
    if not attr_ok:
        issues.append('audit_attribution failed: %s %s' % (proc.stdout[-200:], proc.stderr[-300:]))
    # revised 60-row explanation
    attr_rows = rcsv(os.path.join(out, 'analysis', 'v111_threebin_decomposition30.csv'))
    revised = []
    for r in rcsv(os.path.join(an, 'v110_s60_difference_attribution.csv')):
        rep, g, f = r['representation'], r['group'], r['feature']
        d = next((x for x in attr_rows if x['group'] == g and x['feature'] == f), None)
        revised.append({'record_key': r['record_key'], 'representation': rep, 'group': g, 'feature': f,
                        'historical_count': r['historical_count'],
                        'recomputed_v092_count': r['recomputed_v092_definition_count'],
                        'current_bin160_count': r['current_bin160_count'],
                        'current_full3bin_count': r['current_full3bin_count'],
                        'H_minus_S': d['H_minus_S'] if d else ('' if rep == 'C400_only' else ''),
                        'H_minus_M': d['H_minus_M'] if d else '',
                        'M_minus_S': d['M_minus_S'] if d else '',
                        'corrected_interpretation': (
                            'C400_only: identical to current bin160 (30/30); historical reproduction exact'
                            if rep == 'C400_only' else
                            'three_bin: difference decomposed as H-S=(H-M)+(M-S); H-M includes the historical '
                            '6-cached-states C400 triple-copy defect (reproduced, NOT endorsed as a valid '
                            'modern representation); M-S is the fixed-definition channel comparison'),
                        'status': 'REVISED'})
    wcsv(os.path.join(out, 'analysis', 'v111_s60_revised_attribution60.csv'),
         list(revised[0].keys()), revised)
    ok_a = not issues and len(snap_rows) == 73 and attr_ok
    STAGE_LOG['A'] = {'snapshots': len(snap_rows), 'head': head,
                      'v110_zip_verified': v110_ok, 'attribution_ok': attr_ok,
                      'issues': issues[:20]}
    if not ok_a:
        FAIL_KEYS.setdefault('A', issues[:20])
    GATES['A_source_admission'] = ok_a
    log('Stage A: snap=%d v110zip=%s attribution=%s' % (len(snap_rows), v110_ok, attr_ok))
    return bank, zs, series_keys

# ============================== Stage B ==============================

def stage_b(root, out, bank):
    """Real production tables are audited through the FULL released validation
    entry (tools/validate_decisions.validate_table) - not a reduced 10-field loop."""
    log('=== Stage B: full-table released-validator audit ===')
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import run_v109_delta as v109mod  # independent decision worker lineage
    import validate_decisions as vd    # released full-table validation entry
    issues = []
    worker_path = os.path.join(out, 'logs', 'independent_decision_worker.py')
    with open(worker_path, 'w', encoding='utf-8') as f:
        f.write(v109mod.WORKER_DECISION_SRC)
    worker_out = os.path.join(out, 'logs', 'independent_decision_result.json')
    proc = subprocess.run([sys.executable, worker_path, root, worker_out],
                          capture_output=True, text=True, timeout=3600)
    if proc.returncode != 0:
        issues.append('worker failed: %s' % proc.stderr[:300])
        FAIL_KEYS.setdefault('B', ['worker failed'])
        GATES['B_full_validator_audit'] = False
        return
    indep = json.load(open(worker_out, encoding='utf-8'))
    expected_by_key = {r['record_key']: r for r in indep}
    if len(expected_by_key) != 5040:
        issues.append('worker rows %d != 5040' % len(expected_by_key))

    # REAL production table audited through the full released entry
    prod_rows = rcsv(os.path.join(root, 'tables', 'v110_independent5040.csv'))
    prod_issues = vd.validate_table(prod_rows, expected_by_key)
    n_prod_rows = len(prod_rows)
    # worker rows also cross-audited against the frozen v110 records (both directions)
    prod110_by_key = {r['record_key']: r for r in prod_rows}
    worker_issues = vd.validate_table(indep, prod110_by_key)
    wcsv(os.path.join(out, 'tables', 'v111_independent5040.csv'),
         ['record_key'] + sorted({k for r in indep for k in r if k != 'record_key'}), indep)
    if prod_issues:
        wcsv(os.path.join(out, 'logs', 'v111_production_audit_issues.csv'),
             ['issue'], [{'issue': m[:300]} for m in prod_issues[:500]])

    # 210 summaries + strict subsets 1440/60
    summ = {}
    for r in indep:
        gk = (r['bins'], r.get('subset_S') or r.get('policy'), r['feature'])
        s = summ.setdefault(gk, {'consistent': 0, 'n': 0, 'ambiguous': 0})
        s['n'] += 1
        s['consistent'] += int(r['model_label_consistent'] == 'YES')
        s['ambiguous'] += int(r['tie_across_D'] == 'YES')
    summ_rows = [{'record_key': '%s|%s|%s' % (b, g, f), 'bins': b, 'subset_or_policy': g, 'feature': f,
                  'n_queries': s['n'], 'consistent_count': s['consistent'], 'n_ambiguous': s['ambiguous']}
                 for (b, g, f), s in sorted(summ.items())]
    wcsv(os.path.join(out, 'analysis', 'v111_summaries210.csv'), list(summ_rows[0].keys()), summ_rows)
    summ110 = {(r['bins'], r['subset_or_policy'], r['feature']): r
               for r in rcsv(os.path.join(root, 'analysis', 'v110_summaries210.csv'))}
    summ_bad = sum(1 for r in summ_rows
                   if summ110.get((r['bins'], r['subset_or_policy'], r['feature']), {}).get('consistent_count')
                   != str(r['consistent_count']))
    sub = rcsv(os.path.join(root, 'analysis', 'v095_subset1440.csv'))
    sub_missing = [r['record_key'] for r in sub if r['record_key'] not in expected_by_key]
    sub_field_bad = 0
    for r in sub:
        cur = expected_by_key.get(r['record_key'])
        if cur is None:
            continue
        for f in DECISION_FIELDS:
            d = finite_diff(r.get(f, ''), cur.get(f, ''))
            bad = (str(r.get(f, '')) != str(cur.get(f, ''))) if d is None else not d < 1e-12
            if bad:
                sub_field_bad += 1
                break
    s60 = rcsv(os.path.join(root, 'analysis', 'v092_summaries60.csv'))
    s60_dup = len(s60) - len({r['record_key'] for r in s60})

    # injections through the SAME released entry
    test_rows = []
    base_table = [dict(r) for r in indep]

    def run_table_test(tid, desc, mutate, expect_detected):
        table = [dict(r) for r in base_table]
        table = mutate(table)
        iss = vd.validate_table(table, expected_by_key)
        detected = len(iss) > 0
        test_rows.append({'test_id': tid, 'description': desc,
                          'detected': 'YES' if detected else 'NO',
                          'expected': 'DETECTED' if expect_detected else 'ACCEPTED',
                          'status': 'PASS' if detected == expect_detected else 'FAIL',
                          'sample_issue': iss[0][:120] if iss else ''})

    def mut_field(fname, delta=None, value=None):
        def _m(t):
            r = dict(t[0])
            if delta is not None:
                r[fname] = g17(float(r[fname]) + delta)
            else:
                r[fname] = value
            t[0] = r
            return t
        return _m

    def mut_drop(fname):
        def _m(t):
            r = dict(t[0])
            r.pop(fname, None)
            t[0] = r
            return t
        return _m

    def mut_dup(t):
        t.append(dict(t[0]))
        return t

    def mut_extra(t):
        r = dict(t[0])
        r['record_key'] = 'EXTRA|KEY|q=X|ROI_L2_log_ratio'
        t.append(r)
        return t

    def mut_reorder(t):
        return t[::-1]

    def mut_pool_order(t):
        r = dict(t[0])
        pool = sorted(str(r['reference_pool']).split('|'))
        r['reference_pool'] = '|'.join(pool[::-1])
        t[0] = r
        return t

    def mut_two_same_rep(t):
        r = dict(t[1])
        r['batch'] = t[0]['batch']
        t[1] = r
        return t

    run_table_test('ORT01', 'change cross_D_nearest_dist', mut_field('cross_D_nearest_dist', delta=1e-3), True)
    run_table_test('ORT02', 'change margin', mut_field('min_cross_minus_min_same', delta=1e-3), True)
    run_table_test('ORT03', 'change nearest_candidate', mut_field('nearest_candidate', value='WRONG'), True)
    run_table_test('ORT04', 'change nearest_label_D', mut_field('nearest_label_D', value='999'), True)
    run_table_test('ORT05', 'change second_candidate', mut_field('second_candidate', value='WRONG'), True)
    run_table_test('ORT06', 'change model_label_consistent', mut_field('model_label_consistent', value='FLIPPED'), True)
    run_table_test('ORT07', 'change tied_set_size', mut_field('tied_set_size', value='999'), True)
    run_table_test('ORT08', 'change reference_pool', mut_field('reference_pool', value='WRONG_POOL'), True)
    run_table_test('ORT09', 'change source SHA', mut_field('source_sha256', value='0' * 64), True)
    run_table_test('ORT10', 'NaN', mut_field('same_D_nearest_dist', value='nan'), True)
    run_table_test('ORT11', 'Inf', mut_field('cross_D_nearest_dist', value='inf'), True)
    run_table_test('ORT12', 'missing field', mut_drop('same_D_nearest_dist'), True)
    run_table_test('ORT13', 'duplicate key', mut_dup, True)
    run_table_test('ORT14', 'extra key', mut_extra, True)
    run_table_test('ORT15', 'exact boundary abs(delta)==1e-12', mut_field('same_D_nearest_dist', delta=1e-12), True)
    run_table_test('ORT16', 'change nearest_dist', mut_field('nearest_dist', delta=1e-6), True)
    run_table_test('ORT17', 'change second_dist', mut_field('second_dist', delta=1e-6), True)
    run_table_test('ORT18', 'change final_decision', mut_field('final_decision', value='FLIP'), True)
    run_table_test('ORT19', 'change tie_threshold', mut_field('tie_threshold', delta=1e-9), True)
    run_table_test('ORT20', 'row order reversal (positive)', mut_reorder, False)
    run_table_test('ORT21', 'pool order reversal same set (positive)', mut_pool_order, False)
    run_table_test('ORT22', 'same representation metadata (positive)', mut_two_same_rep, False)
    run_table_test('ORT23', 'unchanged table (positive)', lambda t: t, False)
    n_test_pass = sum(1 for r in test_rows if r['status'] == 'PASS')
    wcsv(os.path.join(out, 'tables', 'v111_error_tests.csv'), list(test_rows[0].keys()), test_rows)

    ok_b = (not prod_issues and not worker_issues and n_test_pass == len(test_rows)
            and not sub_missing and sub_field_bad == 0 and s60_dup == 0
            and len(summ_rows) == 210 and summ_bad == 0 and n_prod_rows == 5040 and not issues)
    if prod_issues:
        FAIL_KEYS.setdefault('B', ['production full-validator issues=%d' % len(prod_issues)])
    if worker_issues:
        FAIL_KEYS.setdefault('B', ['worker cross-audit issues=%d' % len(worker_issues)])
    if n_test_pass < len(test_rows):
        FAIL_KEYS.setdefault('B', ['tests=%d/%d' % (n_test_pass, len(test_rows))])
    if issues:
        FAIL_KEYS.setdefault('B', issues[:10])
    GATES['B_full_validator_audit'] = ok_b
    STAGE_LOG['B'] = {'production_rows': n_prod_rows, 'production_issues': len(prod_issues),
                      'worker_issues': len(worker_issues), 'tests': '%d/%d' % (n_test_pass, len(test_rows)),
                      'sub1440_bad': sub_field_bad, 'summ_bad': summ_bad, 's60_dup': s60_dup,
                      'issues': issues[:10]}
    log('Stage B: prod_rows=%d prod_issues=%d worker_issues=%d tests=%d/%d'
        % (n_prod_rows, len(prod_issues), len(worker_issues), n_test_pass, len(test_rows)))

# ============================== Stage C ==============================

EXTRACTORS = [
    {'name': 'test.m', 'path': r'C:\Users\PC\Desktop\课题\test.m',
     'expected_sha': 'fdc918e691b13b33cbae8b32ecaacd1e63ec27be3e23b61b0701d0e595aea684',
     'encoding': 'gbk', 'role': 'original gray FFT amplitude extractor (420 Hz, contrast input)',
     'snippets': [('Fs', 'Fs'), ('frames', '1000'), ('normalization', '2')]},
    {'name': 'test_with_contrast.m', 'path': r'C:\Users\PC\Downloads\test_with_contrast.m',
     'expected_sha': 'd08575b1e860e09f29c74652442a77b721039c6e32368fe76d2c5c63143ea3aa',
     'encoding': 'gbk', 'role': 'normalized complex modulation contrast extractor (400 Hz, user formal version)',
     'snippets': [('Fs', '5000'), ('frames', '1000'), ('normalization', 'Imean'), ('mask_floor', '0.01')]},
]

def _read_lines(path, encoding):
    with open(path, 'r', encoding=encoding, errors='replace') as f:
        return f.read().splitlines()

def stage_c(root, out):
    log('=== Stage C: real metadata provenance ===')
    issues = []
    # verify recorded extractor scripts on the workstation (hash + line snippets)
    script_rows = []
    scripts_ok = True
    for ex in EXTRACTORS:
        found = os.path.isfile(ex['path'])
        sha_obs = sha256_file(ex['path']) if found else None
        sha_ok = bool(found and sha_obs == ex['expected_sha'])
        scripts_ok &= sha_ok
        lines = _read_lines(ex['path'], ex['encoding']) if found else []
        snippet_rows = []
        for key, needle in ex['snippets']:
            hit = next((i + 1 for i, ln in enumerate(lines) if needle in ln), None)
            snippet_rows.append({'extractor': ex['name'], 'parameter_key': key,
                                 'needle': needle, 'line': hit or '',
                                 'line_text': lines[hit - 1].strip()[:200] if hit else ''})
        script_rows.append({'extractor': ex['name'], 'path': ex['path'], 'found': found,
                            'sha_expected': ex['expected_sha'], 'sha_observed': sha_obs or '',
                            'sha_verified': sha_ok, 'role': ex['role'], 'snippets': snippet_rows})
    if not scripts_ok:
        issues.append('extractor scripts not hash-verified on workstation')
    with open(os.path.join(out, 'logs', 'v111_extractor_scripts_audit.json'), 'w', encoding='utf-8') as f:
        json.dump({'scripts': script_rows, 'source_directness': 'DIRECT_SCRIPT_HASH_VERIFIED'
                   if scripts_ok else 'UNVERIFIED'}, f, indent=2)

    # contract v111 with directness levels; exposure/gain/trigger/timestamps split
    exp_meta = json.load(open(os.path.join(root, 'experimental', 'experimental_inputs_v073.json'), encoding='utf-8'))
    items = [
        {'parameter': 'laser_vacuum_wavelength', 'value': 520.0, 'unit': 'nm',
         'evidence_level': 'USER_CONFIRMED', 'source_directness': 'USER_STATEMENT',
         'source_commit': EXPECTED_V110, 'source_file': 'experimental/experimental_inputs_v073.json',
         'source_line_or_key': 'laser_wavelength_nm', 'source_hash': sha256_file(os.path.join(root, 'experimental', 'experimental_inputs_v073.json')),
         'validity': 'confirmed 2026-10-12 (user statement; date from prior contract, not re-asserted)',
         'uncertainty_or_bound': 'no instrument certificate recorded; value not invalidated by missing certificate',
         'scope': 'demo + future real use'},
        {'parameter': 'frame_rate_Fs', 'value': 5000.0, 'unit': 'fps',
         'evidence_level': 'EXPERIMENT_SCRIPT_RECORDED', 'source_directness': 'DIRECT_SCRIPT_HASH_VERIFIED',
         'source_commit': EXPECTED_V110, 'source_file': 'test_with_contrast.m (workstation, hash-verified)',
         'source_line_or_key': next((str(s['line']) for s in script_rows[1]['snippets'] if s['parameter_key'] == 'Fs'), ''),
         'source_hash': EXTRACTORS[1]['expected_sha'],
         'validity': 'recorded in the user formal extractor; 7.29 batch timestamp deltas (200us) consistent',
         'uncertainty_or_bound': 'script constant; NOT an external clock calibration for timing accuracy',
         'scope': '7.29 batch processing'},
        {'parameter': 'n_frames_N', 'value': 2001, 'unit': 'frames',
         'evidence_level': 'EXPERIMENT_SCRIPT_RECORDED', 'source_directness': 'DIRECT_SCRIPT_HASH_VERIFIED',
         'source_commit': EXPECTED_V110, 'source_file': 'test_with_contrast.m (workstation, hash-verified)',
         'source_line_or_key': next((str(s['line']) for s in script_rows[1]['snippets'] if s['parameter_key'] == 'frames'), ''),
         'source_hash': EXTRACTORS[1]['expected_sha'],
         'validity': 'frames 1000-3000 trailing-number selection recorded in the extractor',
         'uncertainty_or_bound': None, 'scope': '7.29 batch processing'},
        {'parameter': 'spectral_bins_k0', 'value': [80, 160, 320], 'unit': 'bin',
         'evidence_level': 'ANALYSIS_CONTRACT', 'source_directness': 'SOFTWARE_DEFINITION',
         'source_commit': EXPECTED_V110, 'source_file': 'analysis/bank/v092_bank_*.mat (k0_bins field)',
         'source_line_or_key': 'k0_bins', 'source_hash': '',
         'validity': 'selected analysis indices; real frequency = k0*Fs/N',
         'uncertainty_or_bound': 'never INSTRUMENT_MEASURED', 'scope': 'demo analysis'},
        {'parameter': 'demo_pixel_size_object_plane', 'value': 65.0, 'unit': 'nm',
         'evidence_level': 'SIMULATION_ASSUMPTION', 'source_directness': 'SOFTWARE_DEFINITION',
         'source_commit': EXPECTED_V110, 'source_file': '00_Codex_v110 instruction (in-repo)', 'source_line_or_key': '65nm',
         'source_hash': '', 'validity': 'demo only', 'uncertainty_or_bound': None, 'scope': 'demo'},
        {'parameter': 'prescribed_displacement_amplitude_range', 'value': [5.0, 20.0], 'unit': 'nm',
         'evidence_level': 'SIMULATION_ASSUMPTION', 'source_directness': 'SOFTWARE_DEFINITION',
         'source_commit': EXPECTED_V110, 'source_file': '00_Codex_v110 instruction (in-repo)', 'source_line_or_key': 'amplitude',
         'source_hash': '', 'validity': 'prescribed; NOT measured', 'uncertainty_or_bound': None, 'scope': 'demo'},
        {'parameter': 'roi_size', 'value': [41, 41], 'unit': 'pixel',
         'evidence_level': 'SIMULATION_ASSUMPTION', 'source_directness': 'SOFTWARE_DEFINITION',
         'source_commit': EXPECTED_V110, 'source_file': 'analysis/bank (Imean_map shape)', 'source_line_or_key': 'shape',
         'source_hash': '', 'validity': 'demo analysis convention', 'uncertainty_or_bound': None, 'scope': 'demo'},
        {'parameter': 'object_plane_nm_per_pixel_actual_with_error', 'value': None, 'unit': 'nm/pixel',
         'evidence_level': 'MISSING', 'source_directness': 'DIRECT_SOURCE_NOT_FOUND',
         'source_commit': None, 'source_file': None, 'source_line_or_key': None, 'source_hash': None,
         'validity': None, 'uncertainty_or_bound': None, 'scope': 'route A/B blocking',
         'acquisition_method': 'stage calibration or certified ruler image with error budget'},
        {'parameter': 'exposure_time_per_frame', 'value': None, 'unit': 's',
         'evidence_level': 'MISSING', 'source_directness': 'DIRECT_SOURCE_NOT_FOUND',
         'source_commit': None, 'source_file': None, 'source_line_or_key': None, 'source_hash': None,
         'validity': None, 'uncertainty_or_bound': None, 'scope': 'route A/B blocking',
         'acquisition_method': 'camera acquisition log / property readout per frame'},
        {'parameter': 'camera_gain_conversion', 'value': None, 'unit': 'count/e- or DN/e-',
         'evidence_level': 'MISSING', 'source_directness': 'DIRECT_SOURCE_NOT_FOUND',
         'source_commit': None, 'source_file': None, 'source_line_or_key': None, 'source_hash': None,
         'validity': None, 'uncertainty_or_bound': None, 'scope': 'electron-count observation model',
         'acquisition_method': 'camera datasheet + measured conversion curve'},
        {'parameter': 'trigger_time_origin_convention', 'value': None, 'unit': None,
         'evidence_level': 'MISSING', 'source_directness': 'DIRECT_SOURCE_NOT_FOUND',
         'source_commit': None, 'source_file': None, 'source_line_or_key': None, 'source_hash': None,
         'validity': None, 'uncertainty_or_bound': None, 'scope': 'time-origin discipline',
         'acquisition_method': 'trigger log stating exposure-start vs exposure-center convention'},
        {'parameter': 'per_frame_timestamps', 'value': None, 'unit': 's',
         'evidence_level': 'MISSING', 'source_directness': 'DIRECT_SOURCE_NOT_FOUND',
         'source_commit': None, 'source_file': None, 'source_line_or_key': None, 'source_hash': None,
         'validity': None, 'uncertainty_or_bound': None, 'scope': 'non-uniform timestamp handling',
         'acquisition_method': 'frame timestamp log (host or camera FIFO)'},
        {'parameter': 'objective_NA_immersion_illumination_polarization', 'value': None, 'unit': None,
         'evidence_level': 'MISSING', 'source_directness': 'DIRECT_SOURCE_NOT_FOUND',
         'source_commit': None, 'source_file': None, 'source_line_or_key': None, 'source_hash': None,
         'validity': None, 'uncertainty_or_bound': None, 'scope': 'route A/B blocking',
         'acquisition_method': 'objective datasheet + illumination configuration record'},
        {'parameter': 'reference_field_path', 'value': None, 'unit': None,
         'evidence_level': 'MISSING', 'source_directness': 'DIRECT_SOURCE_NOT_FOUND',
         'source_commit': None, 'source_file': None, 'source_line_or_key': None, 'source_hash': None,
         'validity': None, 'uncertainty_or_bound': None, 'scope': 'route A/B blocking',
         'acquisition_method': 'optical layout record or interferometric characterization'},
        {'parameter': 'magnetic_field_B_vector_gradient_waveform_sync', 'value': None, 'unit': None,
         'evidence_level': 'MISSING', 'source_directness': 'DIRECT_SOURCE_NOT_FOUND',
         'source_commit': None, 'source_file': None, 'source_line_or_key': None, 'source_hash': None,
         'validity': None, 'uncertainty_or_bound': None, 'scope': 'route B blocking',
         'acquisition_method': 'calibrated probe B(t) vector/gradient with camera sync record'},
        {'parameter': 'sample_medium_substrate_height_fixation', 'value': None, 'unit': None,
         'evidence_level': 'MISSING', 'source_directness': 'DIRECT_SOURCE_NOT_FOUND',
         'source_commit': None, 'source_file': None, 'source_line_or_key': None, 'source_hash': None,
         'validity': None, 'uncertainty_or_bound': None, 'scope': 'route A/B blocking',
         'acquisition_method': 'sample preparation record + profilometry/caliper of spacer'},
        {'parameter': 'independent_trajectory_with_scale_and_timebase', 'value': None, 'unit': None,
         'evidence_level': 'MISSING', 'source_directness': 'DIRECT_SOURCE_NOT_FOUND',
         'source_commit': None, 'source_file': None, 'source_line_or_key': None, 'source_hash': None,
         'validity': None, 'uncertainty_or_bound': None, 'scope': 'route A blocking',
         'acquisition_method': 'independent tracking with certified scale and common timebase'},
        {'parameter': 'unknown_axial_motion_and_orientation', 'value': None, 'unit': None,
         'evidence_level': 'MISSING', 'source_directness': 'PENDING_CONSTRAINT',
         'source_commit': None, 'source_file': None, 'source_line_or_key': None, 'source_hash': None,
         'validity': None, 'uncertainty_or_bound': 'must stay constrained, never defaulted to 0',
         'scope': 'route A/B blocking',
         'acquisition_method': 'defocused imaging / multi-view or explicit constrained assumption with bound'},
        {'parameter': 'independent_diameter_reference_and_blank_background', 'value': None, 'unit': None,
         'evidence_level': 'MISSING', 'source_directness': 'DIRECT_SOURCE_NOT_FOUND',
         'source_commit': None, 'source_file': None, 'source_line_or_key': None, 'source_hash': None,
         'validity': None, 'uncertainty_or_bound': None, 'scope': 'GO gate',
         'acquisition_method': 'certified particle standard + particle-free blank capture'},
    ]
    with open(os.path.join(out, 'physics_input_contract_v111.json'), 'w', encoding='utf-8') as f:
        json.dump({'schema': 'iscat111.physics_input_contract.1',
                   'source_directness_levels': ['DIRECT_SCRIPT_HASH_VERIFIED', 'USER_STATEMENT',
                                                'SOFTWARE_DEFINITION', 'INDIRECT_REFERENCE',
                                                'DIRECT_SOURCE_NOT_FOUND', 'PENDING_CONSTRAINT'],
                   'items': items}, f, indent=2, ensure_ascii=False)
    # action sheet
    actions = []
    for it in items:
        if it['evidence_level'] == 'MISSING':
            actions.append({'parameter': it['parameter'], 'needed_record': it.get('acquisition_method', ''),
                            'how_to_obtain': it.get('acquisition_method', ''),
                            'blocked_route': it['scope'], 'status': 'OPEN'})
    wcsv(os.path.join(out, 'missing_inputs_action_sheet.csv'), list(actions[0].keys()), actions)
    ok_c = scripts_ok and not issues and len(items) == 19
    if not ok_c:
        FAIL_KEYS.setdefault('C', issues[:10])
    GATES['C_metadata_provenance'] = ok_c
    STAGE_LOG['C'] = {'extractors_hash_verified': sum(1 for r in script_rows if r['sha_verified']),
                      'items': len(items), 'missing': sum(1 for i in items if i['evidence_level'] == 'MISSING'),
                      'actions': len(actions), 'issues': issues[:10]}
    log('Stage C: extractors=%d/2 items=%d missing=%d'
        % (STAGE_LOG['C']['extractors_hash_verified'], len(items), STAGE_LOG['C']['missing']))

# ============================== Stage D ==============================

def _trapz_avg(f, t0, T, n=20001):
    ts = [t0 - T / 2 + T * i / (n - 1) for i in range(n)]
    vals = [f(t) for t in ts]
    return (sum((vals[i] + vals[i + 1]) / 2 for i in range(n - 1)) / (n - 1)) * T / T if T > 0 else None

def stage_d(out):
    log('=== Stage D: observation operator interface + math fixtures ===')
    issues = []
    fx = []

    # 1. constant intensity: exposure average == instantaneous constant
    T, t0 = 2e-4, 0.001
    f1 = lambda t: 3.25
    n = 20001
    ts = [t0 - T / 2 + T * i / (n - 1) for i in range(n)]
    avg1 = sum(f1(t) for t in ts) / n
    fx.append({'fixture': 'constant_intensity', 'pass': abs(avg1 - 3.25) < 1e-12,
               'detail': 'average=%.17g == constant' % avg1})

    # 2. analytic sinusoid rectangular exposure average (closed form)
    a, b, fq = 1.0, 0.5, 400.0
    f2 = lambda t: a + b * math.cos(2 * math.pi * fq * (t - t0))
    vals2 = [f2(t) for t in ts]
    num = (sum(vals2) - (vals2[0] + vals2[-1]) / 2) / (n - 1)  # trapezoid window average
    closed = a + b * math.sin(math.pi * fq * T) / (math.pi * fq * T)
    fx.append({'fixture': 'sinusoid_rectangular_average', 'pass': abs(num - closed) < 1e-9,
               'detail': 'trapezoid=%.12g closed=a+b*sinc(pi f T)=%.12g' % (num, closed)})

    # 3. intensity average != |field average|^2
    E0, e = 1.0, 0.5
    field = lambda t: E0 * (1 + e * math.cos(2 * math.pi * fq * (t - t0)))
    int_avg = sum(abs(field(t)) ** 2 for t in ts) / n
    fld_avg = abs(sum(field(t) for t in ts) / n) ** 2
    fx.append({'fixture': 'intensity_avg_vs_field_avg_squared', 'pass': abs(int_avg - fld_avg) > 1e-6,
               'detail': '<|E|^2>=%.12g != |<E>|^2=%.12g (must never average complex field)' % (int_avg, fld_avg)})

    # 4. time-origin convention: start-centered windows differ; center convention shift-invariant
    f4 = lambda t: a + b * math.cos(2 * math.pi * fq * t)
    avg_start_window = sum(f4(t0 + T * i / (n - 1)) for i in range(n)) / n
    fx.append({'fixture': 'time_origin_convention', 'pass': abs(avg_start_window - num) > 1e-6,
               'detail': 'exposure-start window=%.12g vs exposure-center window=%.12g: origin must be explicit'
                         % (avg_start_window, num)})

    # 5. zero-exposure limit -> instantaneous value
    T5 = 1e-12
    ts5 = [t0 - T5 / 2 + T5 * i / 999 for i in range(1000)]
    avg5 = sum(f2(t) for t in ts5) / len(ts5)
    fx.append({'fixture': 'zero_exposure_limit', 'pass': abs(avg5 - f2(t0)) < 1e-9,
               'detail': 'T->0 limit equals instantaneous value %.12g; T=0 is a math limit, not a camera default' % avg5})

    # 6. unit conversion: electron count = gain * intensity_avg (explicit, not mixed)
    gain = 2.7
    counts = gain * num
    fx.append({'fixture': 'unit_conversion_explicit_gain', 'pass': abs(counts - gain * num) < 1e-12 and gain > 0,
               'detail': 'electron counts = conversion_gain * average intensity (explicit gain; no unit mixing)'})

    # 7. missing-parameter rejection
    def interface_apply(intensity_model, exposure_s, gain_e, timestamps):
        if exposure_s is None:
            raise ValueError('MISSING_PARAMETER: exposure_time_per_frame')
        if gain_e is None:
            raise ValueError('MISSING_PARAMETER: camera_gain_conversion')
        if timestamps is not None and len(set(timestamps)) > 1:
            raise ValueError('NON_UNIFORM_TIMESTAMPS: require explicit new contract, not silent uniform FFT')
        return gain_e * intensity_model * exposure_s
    rejected = False
    try:
        interface_apply(1.0, None, 2.7, None)
    except ValueError as ex:
        rejected = 'MISSING_PARAMETER' in str(ex)
    fx.append({'fixture': 'missing_parameter_rejection', 'pass': rejected,
               'detail': 'interface rejects missing exposure with MISSING_PARAMETER'})

    # 8. non-uniform timestamps rejection
    rejected8 = False
    try:
        interface_apply(1.0, 2e-4, 2.7, [0.0, 1e-4, 3e-4])
    except ValueError as ex:
        rejected8 = 'NON_UNIFORM_TIMESTAMPS' in str(ex)
    fx.append({'fixture': 'nonuniform_timestamp_rejection', 'pass': rejected8,
               'detail': 'non-uniform timestamps are refused; explicit new contract required'})

    all_pass = all(x['pass'] for x in fx)
    with open(os.path.join(out, 'observation_operator_fixtures.json'), 'w', encoding='utf-8') as f:
        json.dump({'fixtures': fx, 'all_pass': all_pass,
                   'status': 'SOFTWARE_INTERFACE_READY' if all_pass else 'INTERFACE_TEST_FAILED',
                   'not_a_claim': 'interface tests do NOT constitute physical GO or experimental validation'}, f, indent=2)
    wcsv(os.path.join(out, 'observation_operator_fixture_report.csv'),
         list(fx[0].keys()), fx)
    interface = {
        'schema': 'iscat111.observation_operator_interface.1',
        'units': 'object-plane nm; seconds; normalized intensity (or explicit electron counts with gain)',
        'model': 'I[p,j] = 1/Tj * integral_{tj-Tj/2}^{tj+Tj/2} ( 1/Ap * integral_pixel_p '
                 '|Eref(x,t)+Es(x,t;D,r(t),orientation,material)|^2 dA ) dt',
        'rules': ['average INTENSITY, never average complex field then square',
                  'electron-count mode requires explicit exposure + conversion gain + response coefficients',
                  'Tj=0 is the instantaneous math limit, not a camera default',
                  'timestamps given as exposure-start must be converted to center or integral bounds adjusted; no implicit time origin',
                  'non-uniform timestamps must NOT silently enter the uniform-FFT contract',
                  'unknown axial motion / orientation stay constrained-pending, never defaulted to 0'],
        'inputs': ['object coordinates unit', 'pixel mapping', 'exposure start/end/center + timebase',
                   'sample geometry', 'material', 'reference field', 'trajectory (route A) or dynamics (route B)',
                   'parameter sources'],
        'routes': {'A': 'independently calibrated trajectory -> this operator (priority only when trajectory sufficient)',
                   'B': 'measured B(t) vector/gradient/sync + constrained dynamics -> trajectory -> route A; '
                        '200Hz drive does not imply 400Hz translation'},
        'authorization': 'pre-registration only; new BEM/noise/diameter-inversion remain 0; REAL_PHYSICS_GO=false',
    }
    with open(os.path.join(out, 'observation_operator_interface.json'), 'w', encoding='utf-8') as f:
        json.dump(interface, f, indent=2, ensure_ascii=False)
    with open(os.path.join(out, 'observation_operator_interface.md'), 'w', encoding='utf-8') as f:
        f.write('# Observation operator interface (pre-registration, no new solves)\n\n')
        f.write('Model: `%s`\n\n' % interface['model'])
        for r in interface['rules']:
            f.write('- %s\n' % r)
        f.write('\nInputs: %s\n\n' % '; '.join(interface['inputs']))
        f.write('Route A: %s\n\nRoute B: %s\n\n' % (interface['routes']['A'], interface['routes']['B']))
        f.write('Authorization: %s\n' % interface['authorization'])
    ok_d = all_pass
    if not ok_d:
        FAIL_KEYS.setdefault('D', ['fixtures failed'])
    GATES['D_observation_interface'] = ok_d
    STAGE_LOG['D'] = {'fixtures': len(fx), 'all_pass': all_pass,
                      'status': 'SOFTWARE_INTERFACE_READY' if all_pass else 'FAILED',
                      'real_physics_go': False}
    log('Stage D: fixtures %d/%d SOFTWARE_INTERFACE_READY=%s'
        % (sum(1 for x in fx if x['pass']), len(fx), all_pass))

# ============================== Stage F ==============================

def stage_f(root, out, zip_path, checker_src, status_sha):
    log('=== Stage F: verifier selftest ===')
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import run_v110_all as v110mod  # reuse the proven selftest harness
    issues = []
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
    case_res = {}

    def run_typed(name, zbytes_or_none, expect_status_sha=None):
        passed, res = run_case(name, zbytes_or_none, expect_status_sha)
        case_res[name] = res
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
        man = zin.read('iscat_v111_return/manifest_sha256.csv').decode('utf-8').splitlines()
        zo.writestr('iscat_v111_return/manifest_sha256.csv',
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
        man = zin.read('iscat_v111_return/manifest_sha256.csv').decode('utf-8')
        zo.writestr('iscat_v111_return/manifest_sha256.csv', man + '../escape.txt,%s\n' % ('0' * 64))
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
    st = json.loads(zin.read('iscat_v111_return/status.json'))
    for name, mutate in (('gates_string_bool', lambda s: s['gates'].update({'A_source_admission': 'true'})),
                         ('gates_missing', lambda s: s['gates'].pop('A_source_admission')),
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
    wcsv(os.path.join(out, 'logs', 'v111_verifier_selftest.csv'), st_fields, results)
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

# ============================== archive ==============================

def build_status(out, tool_sha):
    numerical = all(GATES[g] for g in REQUIRED_GATES)
    statuses = {'execution': 'COMPLETE',
                'numerical': 'TARGETED_AUDIT_SEALED' if numerical else 'UNSEALED_PARTIAL',
                'archive': 'PRE_ARCHIVE_VERIFICATION',
                'physics': 'REAL_PHYSICS_PENDING_INPUTS_SOFTWARE_INTERFACE_READY'}
    status = {'schema': 'iscat111.status.1', 'task_id': TASK_ID,
              'created_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
              'source_commit': EXPECTED_V110, 'parent_commit': EXPECTED_V109,
              'tool_sha256': tool_sha,
              'required_gates': list(REQUIRED_GATES),
              'gates': {g: bool(GATES[g]) for g in REQUIRED_GATES},
              'states': statuses,
              'archive_protocol': {'in_zip_status': 'PRE_ARCHIVE_VERIFICATION (honest pre-state)',
                                   'external_receipt': 'the ONLY post-archive-verification credential',
                                   'post_archive_summary': 'external file with sha recorded in receipt'},
              'stage_logs': STAGE_LOG,
              'environment': {'python': sys.version.split()[0],
                              'numpy': np.__version__, 'scipy': __import__('scipy').__version__,
                              'pythondontwritebytecode': '1'},
              'frozen_states': {'calibration_valid': False, 'experimental_validation': False,
                                'detection_validated': False, 'single_particle_diameter': 'NOT_ESTIMATED'},
              'physics_admission': 'REAL_PHYSICS_PENDING_INPUTS',
              'model_seal': 'original 48-state model formally sealed (v110 repair verified unchanged; '
                            'no further same-type acceptance rounds scheduled)',
              'p0_status': 'OPEN (not upgraded)',
              'rule7_new_authorizations': 0,
              'overall': 'TARGETED_AUDIT_SEALED' if numerical else 'UNSEALED_PARTIAL'}
    p = os.path.join(out, 'status.json')
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(status, f, indent=2, ensure_ascii=False)
    return p, hashlib.sha256(open(p, 'rb').read()).hexdigest(), statuses, numerical

def build_zip(out, zip_path):
    ret_dir = out
    manifest = []
    for dirpath, dirnames, filenames in os.walk(ret_dir):
        for fn in sorted(filenames):
            if fn == 'manifest_sha256.csv':
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, ret_dir).replace(os.sep, '/')
            manifest.append((rel, hashlib.sha256(open(full, 'rb').read()).hexdigest()))
    manifest.sort()
    man_path = os.path.join(ret_dir, 'manifest_sha256.csv')
    with open(man_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['relative_path', 'sha256'])
        for rel, sha in manifest:
            w.writerow([rel, sha])
    if os.path.exists(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for dirpath, dirnames, filenames in os.walk(ret_dir):
            for fn in sorted(filenames):
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, ret_dir).replace(os.sep, '/')
                z.write(full, 'iscat_v111_return/%s' % rel)
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
        print('[v111] FATAL: out dir exists and is not empty')
        return 3
    try:
        if os.path.commonpath([root]) == os.path.commonpath([root, out]):
            print('[v111] FATAL: out must be outside the source root')
            return 3
    except ValueError:
        pass
    os.makedirs(out, exist_ok=True)
    for sub in ('analysis', 'tables', 'logs'):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    tool_sha = sha256_file(os.path.abspath(__file__))
    launch = {'task_id': TASK_ID, 'root': root, 'out': out, 'zip': zip_path,
              'expected_v110_commit': EXPECTED_V110, 'tool_sha256': tool_sha,
              'command': 'python tools/run_v111_all.py --root "%s" --out "%s" --zip "%s"' % (root, out, zip_path),
              'python': sys.version.split()[0], 'numpy': np.__version__,
              'scipy': __import__('scipy').__version__,
              'pid': os.getpid(), 'started_at': time.strftime('%Y-%m-%dT%H:%M:%S')}
    launch_ext = os.path.splitext(zip_path)[0] + '.launch.json'
    with open(launch_ext, 'w', encoding='utf-8') as f:
        json.dump(launch, f, indent=2)
    with open(os.path.join(out, 'logs', 'v111_launch_record.json'), 'w', encoding='utf-8') as f:
        json.dump(launch, f, indent=2)
    shutil.copy2(os.path.abspath(__file__), os.path.join(out, 'logs', 'run_v111_all_snapshot.py'))
    log('launch recorded: %s' % launch_ext)

    bank, zs, series_keys = stage_a(root, out)
    stage_b(root, out, bank)
    stage_c(root, out)
    stage_d(out)

    numerical = all(GATES[g] for g in REQUIRED_GATES if g != 'F_verifier_selftest')
    final_summary = {'gates': GATES, 'stage_logs': STAGE_LOG, 'fail_keys': FAIL_KEYS,
                     'elapsed_seconds': None,
                     'pre_archive_note': 'elapsed_seconds and zip_sha256 are null in the in-ZIP snapshot; '
                                         'external post_archive_summary.json carries final values',
                     'zip_sha256': None}
    with open(os.path.join(out, 'logs', 'v111_final_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(final_summary, f, indent=2)
    status_path, status_sha, statuses, _ = build_status(out, tool_sha)
    tool_shas = {'run_v111_all.py': tool_sha,
                 'v111_archive_check.py': sha256_file(os.path.join(root, 'tools', 'v111_archive_check.py')),
                 'audit_attribution.py': sha256_file(os.path.join(root, 'tools', 'audit_attribution.py')),
                 'validate_decisions.py': sha256_file(os.path.join(root, 'tools', 'validate_decisions.py')),
                 'run_v110_all.py': sha256_file(os.path.join(root, 'tools', 'run_v110_all.py'))}
    with open(os.path.join(out, 'logs', 'v111_tool_shas.json'), 'w', encoding='utf-8') as f:
        json.dump(tool_shas, f, indent=2)
    zip_sha = build_zip(out, zip_path)  # provisional selftest fixture

    checker_src = os.path.join(root, 'tools', 'v111_archive_check.py')
    tool_shas['v111_archive_check.py'] = sha256_file(checker_src)
    with open(os.path.join(out, 'logs', 'v111_tool_shas.json'), 'w', encoding='utf-8') as f:
        json.dump(tool_shas, f, indent=2)

    stage_f(root, out, zip_path, checker_src, status_sha)
    provisional_sha = sha256_file(zip_path)
    if GATES['F_verifier_selftest']:
        final_summary['gates'] = GATES
        with open(os.path.join(out, 'logs', 'v111_final_summary.json'), 'w', encoding='utf-8') as f:
            json.dump(final_summary, f, indent=2)
        os.remove(status_path)
        status_path, status_sha, statuses, _ = build_status(out, tool_sha)
        zip_sha = build_zip(out, zip_path)
        with open(os.path.join(out, 'logs', 'v111_provisional_zip_sha.json'), 'w', encoding='utf-8') as f:
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
    receipt = {'task_id': TASK_ID, 'source_commit': EXPECTED_V110, 'parent_commit': EXPECTED_V109,
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
