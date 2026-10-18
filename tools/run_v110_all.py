# -*- coding: utf-8 -*-
"""v110: V110 - v109 commit review, delta numerical evidence sealing, archive
consistency, and real physics admission.

Source frozen at yyyyzoey/iscat-handoff@3f894b919d11dd2e8dead92b83ed7ec2d930d08c
(parent v108 e377f8a11421a04bc3e6c1eaca9f435a46566784). Read-only root; outputs
outside the tree; single final ZIP; external receipt is the only post-verification
credential; in-ZIP status is explicitly PRE_ARCHIVE_VERIFICATION.
Lineage: math modules reused from tools/run_v109_delta.py and tools/run_v108_all.py.
Zero new BEM/render/optical-time-series/physics-states/experiment-video reads.
"""
import os, sys, csv, json, hashlib, shutil, math, subprocess, zipfile, time, argparse, itertools, io
import numpy as np
from scipy.io import loadmat

TASK_ID = 'V110'
EXPECTED_V109 = '3f894b919d11dd2e8dead92b83ed7ec2d930d08c'
EXPECTED_V108 = 'e377f8a11421a04bc3e6c1eaca9f435a46566784'
EXPECTED_V107 = 'bc699b0932cf18f5abad10e09f1d1eae0f29446e'
PROBE_BLOB = '6b180147f64847329375363d44c317b2d4df247b'
V109_ZIP_SHA = '6d4535903f8a2f89c064e35f4c918810e13b9cc5fe0dc6d275a29ab7e10a7a2d'
V108_ZIP_SHA = '47ab8c14028997c56f180d44efeead0f22de2e7b54b3274b44b080b5938fcbab'
V107_STATUS = {
    'LF':   {'blob': 'bf16131fb31f7a82cc920d6544c9585de96c3035',
             'sha256': '0440f92937b60991f39cbcf43f7e3a715c739019a6a50434eb8f8b5a4bb7b2e7'},
    'CRLF': {'blob': '2594b2b7cffae6b9055700f91c86e2fc09eb8cdc',
             'sha256': '8007700d4d46405f255563f25dc34a740ad451ecabc0ca3b2185ba1e55991a39'},
}
N = 2001
FS = 5000.0
K0S = [80, 160, 320]
ALL24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
         for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)]
INTER24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
           for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (10, 15)]
ALL48 = ALL24 + INTER24
BIN_SUBSETS = [(80,), (160,), (320,), (80, 160), (80, 320), (160, 320), (80, 160, 320)]
CONTROL_SUBSETS = [b for b in BIN_SUBSETS if b != (160,)]
PROBE_PIXELS = [(20, 20), (20, 0), (0, 20), (25, 0)]
eps64 = np.finfo(np.float64).eps
REQUIRED_GATES = ['A_source_admission', 'B_independent_decisions', 'C_delta_repair',
                  'D_readback_audit', 'E_physics_admission', 'F_verifier_selftest']
GATES = {g: False for g in REQUIRED_GATES}
FAIL_KEYS = {}
STAGE_LOG = {}
STAGE_TIMES = {}
FEATS = [(1, 'ROI_L2_log_ratio'), (2, 'magnitude_pattern_symmetric'), (3, 'unit_magnitude_shape')]
POLICY_NAMES = ['unknown_zf_motion', 'known_motion', 'known_motion_zf']
DECISION_FIELDS = ['nearest_candidate', 'nearest_label_D',
                   'same_D_nearest_dist', 'cross_D_nearest_dist',
                   'min_cross_minus_min_same', 'model_label_consistent']

def log(msg):
    print('[v110] %s' % msg, flush=True)

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

def factor_subsets():
    subs = []
    for r in (1, 2, 3):
        subs.extend(itertools.combinations(('a', 'zf', 'type'), r))
    return subs

def refs_endpoint(qi, S, meta):
    return [r for r in ALL24 if r != qi and all(meta[r][f] != meta[qi][f] for f in S)]

def refs_intermediate(qi, pname, meta):
    if pname == 'unknown_zf_motion':
        return list(ALL24)
    if pname == 'known_motion':
        return [r for r in ALL24 if meta[r]['type'] == meta[qi]['type']]
    return [r for r in ALL24 if meta[r]['type'] == meta[qi]['type'] and meta[r]['zf'] == meta[qi]['zf']]

# ============================== Stage A ==============================

def stage_a(root, out):
    log('=== Stage A: read-only admission, snapshots, provenance fingerprints ===')
    an = os.path.join(root, 'analysis')
    tab = os.path.join(root, 'tables')
    issues = []
    head = subprocess.run(['git', '-C', root, 'rev-parse', 'HEAD'],
                          capture_output=True, text=True, timeout=60).stdout.strip()
    parent = subprocess.run(['git', '-C', root, 'rev-parse', 'HEAD^'],
                            capture_output=True, text=True, timeout=60).stdout.strip()
    if head != EXPECTED_V109:
        issues.append('HEAD %s != fixed v109 commit' % head)
    if parent != EXPECTED_V108:
        issues.append('parent %s != v108 commit' % parent)
    manifest = {r['path']: r['sha256'] for r in rcsv(os.path.join(root, 'manifest_sha256.csv'))}

    # 73 core inputs
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
        dt = {'C': str(m['C'].dtype), 'X': str(m['X'].dtype),
              'Imean_map': str(m['Imean_map'].dtype), 'valid_mask': str(m['valid_mask'].dtype)}
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
        if not (dt['C'] == 'complex128' and dt['X'] == 'complex128' and dt['Imean_map'] == 'float64'
                and cid == key and n_val == N and fs_val == FS and k0_bins == K0S
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
    npz_blob = blob_sha1_bytes(open(npz_src, 'rb').read())
    if npz_blob != PROBE_BLOB:
        issues.append('probe NPZ git blob mismatch: %s' % npz_blob)
    dst_npz = os.path.join(snap_dir, 'v093_probe_evidence.npz')
    shutil.copy2(npz_src, dst_npz)
    snap_rows.append({'role': 'SAVED_SIMULATION_PROBES', 'case_id': 'PROBE_EVIDENCE_192_SERIES',
                      'source_relative': 'analysis/v093_probe_evidence.npz',
                      'target_relative': 'snapshot73/v093_probe_evidence.npz',
                      'size_bytes': str(os.path.getsize(dst_npz)), 'sha256': npz_sha})
    for r in snap_rows:
        if sha256_file(os.path.join(out, r['target_relative'])) != r['sha256']:
            issues.append('snapshot byte mismatch: %s' % r['target_relative'])
    wcsv(os.path.join(out, 'logs', 'v110_snapshot73_manifest.csv'), list(snap_rows[0].keys()), snap_rows)

    zs = np.load(npz_src)
    series_keys = sorted(k for k in zs.files if k.startswith('series_'))
    expected_series = {'series_%s_h5_%d_%d' % (key, i5, j5) for key in ALL48 for (i5, j5) in PROBE_PIXELS}
    if set(series_keys) != expected_series or len(series_keys) != 192:
        issues.append('probe series key set mismatch')

    # source diff vs frozen v109 commit (saved, not applied)
    diff = subprocess.run(['git', '-C', root, 'diff', EXPECTED_V109, '--', 'tools/'],
                          capture_output=True, text=True, timeout=120).stdout
    with open(os.path.join(out, 'logs', 'v110_source_diff.patch'), 'w', encoding='utf-8', newline='') as f:
        f.write(diff)

    # prior archive byte verification
    prior = {}
    for name, cands, expect in (
            ('v109', [r'C:\Users\PC\Documents\Codex\2026-10-18\files-mentioned-by-the-user-iscat\work\v109_final\iscat_v109_return.zip',
                      r'C:\Users\PC\Documents\Codex\2026-10-18\files-mentioned-by-the-user-iscat\outputs\iscat_v109_return.zip'], V109_ZIP_SHA),
            ('v108', [r'C:\Users\PC\Documents\Codex\2026-10-18\files-mentioned-by-the-user-iscat\work\v108_run3\iscat_v108_return.zip',
                      r'C:\Users\PC\Documents\Codex\2026-10-18\files-mentioned-by-the-user-iscat\outputs\iscat_v108_return.zip'], V108_ZIP_SHA)):
        found = next((c for c in cands if os.path.isfile(c)), None)
        obs = sha256_file(found) if found else None
        prior[name] = {'zip_path': found, 'expected_sha256': expect, 'observed_sha256': obs,
                       'independently_verified_bytes': bool(found and obs == expect)}
        if not prior[name]['independently_verified_bytes']:
            prior[name]['note'] = 'actual ZIP bytes not independently verified here; recorded, NOT faked'
    with open(os.path.join(out, 'logs', 'v110_prior_archive_audit.json'), 'w', encoding='utf-8') as f:
        json.dump(prior, f, indent=2)
    if not (prior['v109']['independently_verified_bytes'] and prior['v108']['independently_verified_bytes']):
        issues.append('prior ZIP bytes not independently verified')

    # v107 status LF/CRLF dual fingerprint from the fixed v107 git object
    st_path = os.path.join(root, 'status.json')
    proc_st = subprocess.run(['git', '-C', root, 'show', EXPECTED_V107 + ':status.json'],
                             capture_output=True, timeout=60)
    raw_lf = proc_st.stdout
    raw_crlf = raw_lf.replace(b'\n', b'\r\n')
    variants = {}
    for name, data, domain in (('git_canonical_LF', raw_lf, 'git_canonical_blob_bytes'),
                               ('LF_to_CRLF', raw_crlf, 'derived_lineending_bytes'),
                               ('current_worktree', open(st_path, 'rb').read(), 'worktree_bytes')):
        variants[name] = {'sha256': hashlib.sha256(data).hexdigest(),
                          'git_blob_sha1': blob_sha1_bytes(data),
                          'hash_domain': domain, 'byte_len': len(data)}
    fp = {'lf_sha_match': variants['git_canonical_LF']['sha256'] == V107_STATUS['LF']['sha256'],
          'lf_blob_match': variants['git_canonical_LF']['git_blob_sha1'] == V107_STATUS['LF']['blob'],
          'crlf_sha_match': variants['LF_to_CRLF']['sha256'] == V107_STATUS['CRLF']['sha256'],
          'crlf_blob_match': variants['LF_to_CRLF']['git_blob_sha1'] == V107_STATUS['CRLF']['blob'],
          'hash_domain_note': 'Git canonical (LF) and line-ending-converted (CRLF) bytes are different objects '
                              'with identical parsed JSON; neither is tampering.',
          'variants': variants}
    if not (fp['lf_sha_match'] and fp['lf_blob_match'] and fp['crlf_sha_match'] and fp['crlf_blob_match']):
        issues.append('v107 status dual fingerprint mismatch')
    with open(os.path.join(out, 'logs', 'v110_v107_fingerprint.json'), 'w', encoding='utf-8') as f:
        json.dump(fp, f, indent=2)

    ok_a = not issues and len(snap_rows) == 73
    STAGE_LOG['A'] = {'snapshots': len(snap_rows), 'head': head,
                      'v109_zip_verified': prior['v109']['independently_verified_bytes'],
                      'v108_zip_verified': prior['v108']['independently_verified_bytes'],
                      'v107_fingerprint_ok': fp['lf_sha_match'] and fp['crlf_sha_match'],
                      'source_diff_bytes': len(diff), 'issues': issues[:20]}
    if not ok_a:
        FAIL_KEYS.setdefault('A', issues[:20])
    GATES['A_source_admission'] = ok_a
    log('Stage A: snap=%d v109zip=%s v108zip=%s fingerprint=%s'
        % (len(snap_rows), prior['v109']['independently_verified_bytes'],
           prior['v108']['independently_verified_bytes'],
           fp['lf_sha_match'] and fp['crlf_sha_match']))
    return bank, zs, series_keys

# ============================== Stage B ==============================

def stage_b(root, out):
    """Differential audit of the saved 5040 decisions: a separate Python process
    recomputes per-channel-reduced decisions from the frozen 73 sources; the
    released validation entry judges everything."""
    log('=== Stage B: independent decision subprocess + differential audit ===')
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import run_v109_delta as v109mod  # proven math/validator lineage, not a rename
    issues = []
    worker_path = os.path.join(out, 'logs', 'independent_decision_worker.py')
    with open(worker_path, 'w', encoding='utf-8') as f:
        f.write(v109mod.WORKER_DECISION_SRC)
    worker_out = os.path.join(out, 'logs', 'independent_decision_result.json')
    proc = subprocess.run([sys.executable, worker_path, root, worker_out],
                          capture_output=True, text=True, timeout=3600)
    worker_exit = proc.returncode
    if worker_exit != 0:
        issues.append('independent decision worker failed: exit=%d %s' % (worker_exit, proc.stderr[:300]))
        FAIL_KEYS.setdefault('B', ['worker failed'])
        GATES['B_independent_decisions'] = False
        return None
    indep = json.load(open(worker_out, encoding='utf-8'))
    expected_by_key = {r['record_key']: r for r in indep}
    if len(expected_by_key) != 5040:
        issues.append('independent row count %d != 5040' % len(expected_by_key))

    # production comparison vs frozen v109 table (full fields)
    prod109 = {r['record_key']: r for r in rcsv(os.path.join(root, 'tables', 'v109_independent5040.csv'))}
    full_fields = v109mod.DECISION_FIELDS + ['nearest_dist', 'second_dist', 'final_decision', 'tie_threshold']
    n_match = n_mismatch = 0
    mismatches = []
    for r in indep:
        pk = r['record_key']
        pr = prod109.get(pk)
        if pr is None:
            n_mismatch += 1
            mismatches.append({'record_key': pk, 'issue': 'missing in v109 table'})
            continue
        row_bad = False
        for f in full_fields:
            d = finite_diff(r.get(f, ''), pr.get(f, ''))
            if d is None:
                if str(r.get(f, '')) != str(pr.get(f, '')):
                    row_bad = True
                    mismatches.append({'record_key': pk, 'issue': '%s: %s vs %s' % (f, r.get(f, ''), pr.get(f, ''))})
            elif not d < 1e-12:
                row_bad = True
                mismatches.append({'record_key': pk, 'issue': '%s diff %g' % (f, d)})
        n_match += int(not row_bad)
        n_mismatch += int(row_bad)

    # v108 differential: fields recorded in v108 compared; absent fields NOT_RECORDED
    prod108 = {r['record_key']: r for r in rcsv(os.path.join(root, 'tables', 'v108_independent5040.csv'))}
    n_match108 = n_mismatch108 = n_not_recorded = 0
    for r in indep:
        pr = prod108.get(r['record_key'])
        if pr is None:
            n_mismatch108 += 1
            continue
        row_bad = False
        for f in full_fields:
            if f not in pr or pr[f] in (None, ''):
                n_not_recorded += 1
                continue
            d = finite_diff(r.get(f, ''), pr[f])
            if d is None:
                if str(r.get(f, '')) != str(pr[f]):
                    row_bad = True
            elif not d < 1e-12:
                row_bad = True
        n_match108 += int(not row_bad)
        n_mismatch108 += int(row_bad)

    all_f = ['record_key'] + sorted({k for r in indep for k in r if k != 'record_key'})
    wcsv(os.path.join(out, 'tables', 'v110_independent5040.csv'), all_f, indep)

    # 210 summaries + compare to frozen v109 summaries
    summ = {}
    for r in indep:
        gk = (r['bins'], r.get('subset_S') or r.get('policy'), r['feature'])
        s = summ.setdefault(gk, {'consistent': 0, 'n': 0, 'ambiguous': 0})
        s['n'] += 1
        s['consistent'] += int(r['model_label_consistent'] == 'YES')
        s['ambiguous'] += int(r['tie_across_D'] == 'YES')
    summ_rows = [{'record_key': '%s|%s|%s' % (b, g, f), 'bins': b, 'subset_or_policy': g, 'feature': f,
                  'n_queries': s['n'], 'consistent_count': s['consistent'], 'n_ambiguous': s['ambiguous'],
                  'reading': 'in-sample geometry screen; NOT accuracy/detectability'}
                 for (b, g, f), s in sorted(summ.items())]
    wcsv(os.path.join(out, 'analysis', 'v110_summaries210.csv'), list(summ_rows[0].keys()), summ_rows)
    summ109 = {(r['bins'], r['subset_or_policy'], r['feature']): r
               for r in rcsv(os.path.join(root, 'analysis', 'v109_summaries210.csv'))}
    summ_bad = sum(1 for r in summ_rows
                   if summ109.get((r['bins'], r['subset_or_policy'], r['feature']), {}).get('consistent_count')
                   != str(r['consistent_count']))

    # 1440/60 strict subsets (keys + values + counts)
    sub = rcsv(os.path.join(root, 'analysis', 'v095_subset1440.csv'))
    sub_missing = [r['record_key'] for r in sub if r['record_key'] not in expected_by_key]
    sub_field_bad = 0
    for r in sub:
        cur = expected_by_key.get(r['record_key'])
        if cur is None:
            continue
        for f in v109mod.DECISION_FIELDS:
            d = finite_diff(r.get(f, ''), cur.get(f, ''))
            bad = (str(r.get(f, '')) != str(cur.get(f, ''))) if d is None else not d < 1e-12
            if bad:
                sub_field_bad += 1
                break
    s60 = rcsv(os.path.join(root, 'analysis', 'v092_summaries60.csv'))
    s60_duplicate_keys = len(s60) - len({r['record_key'] for r in s60})
    summ_by_gf = {(r['bins'], r['subset_or_policy'], r['feature']): r for r in summ_rows}
    s60_unmapped = [r['record_key'] for r in s60
                    if ('160', r['subset_or_policy'], r['feature']) not in summ_by_gf]

    # injection tests through the SAME released validation entry
    test_rows = []
    base_table = [dict(r) for r in indep]

    def run_table_test(tid, desc, mutate, expect_detected):
        table = [dict(r) for r in base_table]
        table = mutate(table)
        iss = v109mod.validate_table(table, expected_by_key)
        detected = len(iss) > 0
        ok = detected == expect_detected
        test_rows.append({'test_id': tid, 'description': desc,
                          'detected': 'YES' if detected else 'NO',
                          'expected': 'DETECTED' if expect_detected else 'ACCEPTED',
                          'status': 'PASS' if ok else 'FAIL',
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
    run_table_test('ORT02', 'change margin min_cross_minus_min_same', mut_field('min_cross_minus_min_same', delta=1e-3), True)
    run_table_test('ORT03', 'change nearest_candidate', mut_field('nearest_candidate', value='WRONG'), True)
    run_table_test('ORT04', 'change nearest_label_D', mut_field('nearest_label_D', value='999'), True)
    run_table_test('ORT05', 'change second_candidate', mut_field('second_candidate', value='WRONG'), True)
    run_table_test('ORT06', 'change model_label_consistent', mut_field('model_label_consistent', value='FLIPPED'), True)
    run_table_test('ORT07', 'change tied_set_size', mut_field('tied_set_size', value='999'), True)
    run_table_test('ORT08', 'change reference_pool', mut_field('reference_pool', value='WRONG_POOL'), True)
    run_table_test('ORT09', 'change source SHA', mut_field('source_sha256', value='0' * 64), True)
    run_table_test('ORT10', 'NaN in distance field', mut_field('same_D_nearest_dist', value='nan'), True)
    run_table_test('ORT11', 'Inf in distance field', mut_field('cross_D_nearest_dist', value='inf'), True)
    run_table_test('ORT12', 'missing field', mut_drop('same_D_nearest_dist'), True)
    run_table_test('ORT13', 'duplicate record_key', mut_dup, True)
    run_table_test('ORT14', 'extra record_key', mut_extra, True)
    run_table_test('ORT15', 'EXACT threshold boundary (abs(delta)==1e-12 rejected)', mut_field('same_D_nearest_dist', delta=1e-12), True)
    run_table_test('ORT16', 'change nearest_dist', mut_field('nearest_dist', delta=1e-6), True)
    run_table_test('ORT17', 'change second_dist', mut_field('second_dist', delta=1e-6), True)
    run_table_test('ORT18', 'change final_decision', mut_field('final_decision', value='CROSS_D_FLIPPED'), True)
    run_table_test('ORT19', 'change tie_threshold', mut_field('tie_threshold', delta=1e-9), True)
    run_table_test('ORT20', 'reverse table row order (positive, per-key values unchanged)', mut_reorder, False)
    run_table_test('ORT21', 'reverse reference_pool order (same set, positive)', mut_pool_order, False)
    run_table_test('ORT22', 'same representation metadata two entries (positive)', mut_two_same_rep, False)
    run_table_test('ORT23', 'normal unchanged table (positive)', lambda t: t, False)
    n_test_pass = sum(1 for r in test_rows if r['status'] == 'PASS')
    wcsv(os.path.join(out, 'tables', 'v110_error_tests.csv'), list(test_rows[0].keys()), test_rows)

    ok_b = (n_mismatch == 0 and len(expected_by_key) == 5040 and n_test_pass == len(test_rows)
            and not sub_missing and sub_field_bad == 0 and not s60_unmapped
            and s60_duplicate_keys == 0 and len(summ_rows) == 210 and summ_bad == 0 and not issues)
    if n_mismatch:
        FAIL_KEYS.setdefault('B', ['v109-table mismatches=%d' % n_mismatch])
    if n_mismatch108:
        FAIL_KEYS.setdefault('B', ['v108-table mismatches=%d' % n_mismatch108])
    if n_test_pass < len(test_rows):
        FAIL_KEYS.setdefault('B', ['error tests=%d/%d' % (n_test_pass, len(test_rows))])
    if sub_missing or sub_field_bad:
        FAIL_KEYS.setdefault('B', ['sub1440 missing=%d field_bad=%d' % (len(sub_missing), sub_field_bad)])
    if issues:
        FAIL_KEYS.setdefault('B', issues[:10])
    GATES['B_independent_decisions'] = ok_b
    STAGE_LOG['B'] = {'worker_exit': worker_exit, 'match_v109': n_match, 'mismatch_v109': n_mismatch,
                      'match_v108': n_match108, 'mismatch_v108': n_mismatch108,
                      'v108_fields_not_recorded': n_not_recorded,
                      'summaries210': len(summ_rows), 'summaries_vs_v109_bad': summ_bad,
                      'sub1440_field_bad': sub_field_bad, 's60_duplicate_keys': s60_duplicate_keys,
                      'error_tests': '%d/%d' % (n_test_pass, len(test_rows)), 'issues': issues[:10]}
    log('Stage B: worker=%d match109=%d match108=%d tests=%d/%d sub1440_bad=%d'
        % (worker_exit, n_match, n_match108, n_test_pass, len(test_rows), sub_field_bad))
    return indep, summ_rows

# ============================== Stage C ==============================

CACHED6 = {'D30_zf450_M400_a5': 'v083_fullROI_double_C400_D30_zf450_M400_a5.mat',
           'D30_zf550_M400_a5': 'v083_fullROI_double_C400_D30_zf550_M400_a5.mat',
           'D60_zf450_M400_a5': 'v083_fullROI_double_C400_D60_zf450_M400_a5.mat',
           'D100_zf450_M200_a20': 'v083_fullROI_double_C400_D100_zf450_M200_a20.mat',
           'D30_zf550_M400_a20': 'v084_double_C400_D30_zf550_M400_a20.mat',
           'D60_zf450_M400_a20': 'v084_double_C400_D60_zf450_M400_a20.mat'}

def stage_c(root, out, bank, indep, summ_rows):
    log('=== Stage C: count-control audit, d3 reconciliation, 30-group attribution ===')
    an = os.path.join(root, 'analysis')
    issues = []
    meta = {k: parse(k) for k in ALL48}
    abs_C = {}
    for key in ALL48:
        for ki, k0 in enumerate(K0S):
            abs_C[(key, k0)] = np.abs(bank[key]['C'][ki]).reshape(-1)
    indep_by_key = {r['record_key']: r for r in indep}
    summ_by_key = {(r['bins'], r['subset_or_policy'], r['feature']): r for r in summ_rows}

    # --- 1. count-control audit vs the accepted 210 summaries ---
    cc_rows = rcsv(os.path.join(root, 'tables', 'v109_count_control180.csv'))
    cc_bad = 0
    tally = {'INCREASED': 0, 'UNCHANGED': 0, 'DECREASED': 0}
    n_ambiguous = 0
    for r in cc_rows:
        k_sub = (r['channel_subset'], r['group'], r['feature'])
        k_base = ('160', r['group'], r['feature'])
        cs, cb = summ_by_key.get(k_sub), summ_by_key.get(k_base)
        if cs is None or cb is None:
            cc_bad += 1
            continue
        delta = int(cs['consistent_count']) - int(cb['consistent_count'])
        direction = 'INCREASED' if delta > 0 else ('UNCHANGED' if delta == 0 else 'DECREASED')
        amb = int(cs['n_ambiguous']) + int(cb['n_ambiguous'])
        n_ambiguous += 1 if amb else 0
        if (delta != int(r['delta_vs_bin160']) or direction != r['direction']
                or int(cs['consistent_count']) != int(r['count_subset'])
                or int(cb['consistent_count']) != int(r['count_baseline_bin160'])):
            cc_bad += 1
        tally[direction] += 1
    if cc_bad or len(cc_rows) != 180:
        issues.append('count-control audit: rows=%d bad=%d' % (len(cc_rows), cc_bad))
    audit_rows = [{'total_rows': len(cc_rows), 'verified': len(cc_rows) - cc_bad,
                   'increased': tally['INCREASED'], 'unchanged': tally['UNCHANGED'],
                   'decreased': tally['DECREASED'],
                   'groups_with_any_ambiguity': n_ambiguous,
                   'baseline': 'single-160 counts from the accepted 210 summaries',
                   'status': 'AUDIT_PASS' if cc_bad == 0 and len(cc_rows) == 180 else 'AUDIT_FAIL'}]
    wcsv(os.path.join(out, 'analysis', 'v110_count_control_audit.csv'), list(audit_rows[0].keys()), audit_rows)

    # --- 2. factor-pair reconciliation: 60 corrected d3 + 120 unchanged d1/d2 ---
    dec109 = {r['record_key']: r for r in rcsv(os.path.join(an, 'v109_decomposition852.csv'))}
    fc_old = {r['record_key']: r for r in rcsv(os.path.join(root, 'tables', 'v108_fixed_control180.csv'))}
    fp_rows = rcsv(os.path.join(root, 'analysis', 'v109_factor_pairs_repaired180.csv'))
    n_d3_ok = n_d12_ok = 0
    d3_bad = d12_bad = 0
    corrected_rows = []
    for r in fp_rows:
        pi, pj = r['state_i'], r['state_j']
        dec_key = '%s__vs__%s' % (pi, pj)
        if dec_key not in dec109:
            dec_key = '%s__vs__%s' % (pj, pi)
        dec = dec109.get(dec_key)
        is_shape = r['feature'] == 'unit_magnitude_shape'
        d3_delta_na = 'NA (d3_delta only interpretable for unit_magnitude_shape)'
        row = dict(r)
        if is_shape:
            if dec is None:
                d3_bad += 1
                continue
            resid = abs(float(r['d3_corrected_totalnorm']) ** 2 - float(dec['shape_direct_sq']))
            d3_delta = r.get('d3_delta', '')
            d3_ok = resid < 1e-12 and (d3_delta == '' or math.isfinite(float(d3_delta)))
            n_d3_ok += int(d3_ok)
            d3_bad += int(not d3_ok)
            row['target_feature_diff'] = g17(resid)
        else:
            old = fc_old.get(r['record_key'], {})
            col = 'd1' if r['feature'] == 'ROI_L2_log_ratio' else 'd2'
            try:
                same = abs(float(r[col]) - float(old['d_full_3bin'])) < 1e-12
            except (TypeError, ValueError, KeyError):
                same = False
            n_d12_ok += int(same)
            d12_bad += int(not same)
            row['target_feature_diff'] = 'NA'
            row['d3_delta'] = d3_delta_na
        corrected_rows.append(row)
    wcsv(os.path.join(out, 'analysis', 'v110_factor_pairs_corrected180.csv'),
         list(corrected_rows[0].keys()), corrected_rows)
    if d3_bad or d12_bad or len(corrected_rows) != 180:
        issues.append('factor-pair reconciliation: d3_bad=%d d12_bad=%d rows=%d' % (d3_bad, d12_bad, len(corrected_rows)))

    # --- 3. 30-group difference attribution with recomputation evidence ---
    # Recompute the historical v092 C400_only representation exactly as
    # source/run_v092_E_comparison.py defines it: 6 cached states use v083/v084
    # C400_double with mask=ones (full 1681); all other states use bank C160 with
    # the bank common mask. Double precision throughout (complex128).
    vecs_by_rep = {'C400_only': {}, 'three_bin_magnitude': {}}
    for key in ALL48:
        if key in CACHED6:
            m = loadmat(os.path.join(root, 'numeric', CACHED6[key]))
            C = np.asarray(m['C400_double']).astype(np.complex128)
            c400 = np.abs(C).reshape(-1)
            vecs_by_rep['C400_only'][key] = c400
            vecs_by_rep['three_bin_magnitude'][key] = np.concatenate([c400] * 3)
        else:
            msk = bank[key]['mask'].reshape(-1)
            c80 = abs_C[(key, 80)][msk]
            c160 = abs_C[(key, 160)][msk]
            c320 = abs_C[(key, 320)][msk]
            vecs_by_rep['C400_only'][key] = c160
            vecs_by_rep['three_bin_magnitude'][key] = np.concatenate([c80, c160, c320])
    A_by_rep = {rep: {key: float(np.linalg.norm(v)) for key, v in vecs.items()}
                for rep, vecs in vecs_by_rep.items()}
    groups = [('+'.join(S), 'endpoint') for S in factor_subsets()] + \
             [(pname, 'intermediate') for pname in POLICY_NAMES]

    def decisions_for(rep, qi, refs):
        vecs = vecs_by_rep[rep]
        A = A_by_rep[rep]
        vq = vecs[qi]
        Aq = A[qi]
        d1 = {r: abs(math.log(Aq) - math.log(A[r])) for r in refs}
        d2 = {r: 2.0 * float(np.linalg.norm(vq - vecs[r])) / (Aq + A[r]) for r in refs}
        d3 = {r: float(np.linalg.norm(vq / max(Aq, 1e-300) - vecs[r] / max(A[r], 1e-300))) for r in refs}
        return [d1, d2, d3]

    counts92 = {rep: {} for rep in vecs_by_rep}
    for gname, batch_type in groups:
        queries = ALL24 if batch_type == 'endpoint' else INTER24
        for qi in queries:
            refs = refs_endpoint(qi, gname.split('+'), meta) if batch_type == 'endpoint' \
                else refs_intermediate(qi, gname, meta)
            for rep in vecs_by_rep:
                all_ds = decisions_for(rep, qi, refs)
                for fi, fname in FEATS:
                    ds = all_ds[fi - 1]
                    ordered = sorted(refs, key=lambda r: (ds[r], r))
                    dmin = ds[ordered[0]]
                    tol = 64 * eps64 * max(1.0, abs(dmin))
                    tied = [r for r in ordered if ds[r] <= dmin + tol]
                    tied_Ds = {meta[r]['D'] for r in tied}
                    label = meta[ordered[0]]['D']
                    consistent = (label == meta[qi]['D']) and len(tied_Ds) <= 1
                    k = (gname, fname)
                    counts92[rep][k] = counts92[rep].get(k, 0) + int(consistent)

    s60 = rcsv(os.path.join(root, 'analysis', 'v092_summaries60.csv'))
    attr_rows = []
    n_hist_reproduced = 0
    for r in s60:
        rep = r['representation']
        k = (r['subset_or_policy'], r['feature'])
        cur160 = summ_by_key.get(('160', k[0], k[1]))
        cur_full = summ_by_key.get(('80+160+320', k[0], k[1]))
        cur160_count = int(cur160['consistent_count']) if cur160 else None
        cur_full_count = int(cur_full['consistent_count']) if cur_full else None
        hist_count = int(r['consistent_count'])
        recomp = counts92.get(rep, {}).get(k)
        reproduced = (recomp == hist_count)
        n_hist_reproduced += int(reproduced)
        if rep == 'C400_only':
            diff = (cur160_count - hist_count) if cur160_count is not None else None
            if reproduced and diff == 0:
                attribution = ('NO_DIFFERENCE: C400_only (bin-160 masked) reproduces exactly with the current '
                               'engine and equals the current bin160 counts')
            elif reproduced:
                attribution = 'PROVEN_DIFFERENCE_UNEXPECTED (C400_only should equal current bin160)'
            else:
                attribution = 'IMPLEMENTATION_SEMANTICS_DIFFERENCE (recomputation fails to reproduce)'
        else:
            diff = (cur160_count - hist_count) if cur160_count is not None else None
            full_match = (cur_full_count == hist_count) if cur_full_count is not None else None
            if reproduced and diff not in (0, None) and full_match:
                attribution = ('PROVEN_STATISTICAL_OBJECT_DIFFERENCE: the 30 differing groups are '
                               'three_bin_magnitude rows compared against a single-160 baseline - different '
                               'statistical objects; the same rows EXACTLY match the current full-3bin '
                               'summaries and the v092 definition reproduces them exactly; single-precision '
                               'attribution NOT supported (v092 used complex128 arrays)')
            elif reproduced and full_match:
                attribution = 'NO_DIFFERENCE_VS_FULL3BIN'
            elif reproduced:
                attribution = 'REPRODUCED_HISTORICAL_ONLY'
            else:
                attribution = 'IMPLEMENTATION_SEMANTICS_DIFFERENCE (recomputation fails to reproduce)'
        attr_rows.append({'record_key': r['record_key'], 'representation': rep,
                          'group': r['subset_or_policy'], 'feature': r['feature'],
                          'historical_count': hist_count,
                          'recomputed_v092_definition_count': recomp if recomp is not None else '',
                          'historical_reproduced': 'YES' if reproduced else 'NO',
                          'current_bin160_count': cur160_count if cur160_count is not None else '',
                          'current_full3bin_count': cur_full_count if cur_full_count is not None else '',
                          'difference_vs_bin160': diff if diff is not None else '',
                          'reference_pool_rule': 'same policy/group structure; pool sizes per v092 engine',
                          'mask_rule_v092_C400_only': 'mask=ones full-1681 for 6 cached states; bank mask otherwise',
                          'attribution': attribution})
    wcsv(os.path.join(out, 'analysis', 'v110_s60_difference_attribution.csv'), list(attr_rows[0].keys()), attr_rows)

    ok_c = (cc_bad == 0 and len(cc_rows) == 180 and d3_bad == 0 and d12_bad == 0
            and len(corrected_rows) == 180 and len(attr_rows) == 60
            and n_hist_reproduced == 60 and not issues)
    if n_hist_reproduced < 60:
        issues.append('historical s60 reproduction %d/60' % n_hist_reproduced)
        FAIL_KEYS.setdefault('C', ['attribution reproduction=%d/60' % n_hist_reproduced])
    if issues:
        FAIL_KEYS.setdefault('C', issues[:10])
    GATES['C_delta_repair'] = ok_c
    STAGE_LOG['C'] = {'count_control_verified': '%d/180' % (len(cc_rows) - cc_bad),
                      'count_tally': tally, 'd3_reconciled': '%d/60' % n_d3_ok,
                      'd12_unchanged': '%d/120' % n_d12_ok,
                      's60_attribution_reproduced': '%d/60' % n_hist_reproduced,
                      'issues': issues[:10]}
    log('Stage C: cc=%d/180 d3=%d/60 d12=%d/120 attr=%d/60'
        % (len(cc_rows) - cc_bad, n_d3_ok, n_d12_ok, n_hist_reproduced))

# ============================== Stage D ==============================

def stage_d(root, out, bank, zs, series_keys, indep):
    log('=== Stage D: origin/probe readback, decomposition, radius qualification ===')
    an = os.path.join(root, 'analysis')
    issues = []
    GATE = 1e-11
    origin_rows = rcsv(os.path.join(an, 'v108_origin_threeway14400.csv'))
    origin_by_key = {r['record_key']: r for r in origin_rows}
    n_ok = n_fft_ok = 0
    for sk in series_keys:
        s = np.asarray(zs[sk], dtype=np.float64)
        g = s[:25]
        case_id = sk.replace('series_', '').split('_h5_')[0]
        pix = sk.replace('series_', '').split('_h5_')[1]
        for ell in range(25):
            y = np.array([g[(jj + ell) % 25] for jj in range(N)], dtype=np.float64)
            Im = float(y.mean())
            spec = np.fft.fft(y - Im)
            for k0 in K0S:
                r = origin_by_key.get('%s|bin%d|px(%s)|ell%d' % (case_id, k0, pix, ell))
                if r is None:
                    continue
                X_A = complex(float(r['X_A_Re']), float(r['X_A_Im']))
                X_B = complex(float(r['X_B_Re']), float(r['X_B_Im']))
                X_C = complex(float(r['X_C_Re']), float(r['X_C_Im']))
                C_A = complex(float(r['C_A_Re']), float(r['C_A_Im']))
                C_B = complex(float(r['C_B_Re']), float(r['C_B_Im']))
                C_C = complex(float(r['C_C_Re']), float(r['C_C_Im']))
                diffs = [abs(X_A - X_B), abs(X_A - X_C), abs(X_B - X_C),
                         abs(C_A - C_B), abs(C_A - C_C), abs(C_B - C_C)]
                n_ok += int(max(diffs) < GATE)
                n_fft_ok += int(abs(complex(spec[k0]) - X_A) < GATE)
    n_zero_ok = 0
    zero_by_key = {r['record_key']: r for r in rcsv(os.path.join(an, 'v108_zerostart_summary576.csv'))}
    for sk in series_keys:
        s = np.asarray(zs[sk], dtype=np.float64)
        g = s[:25]
        case_id = sk.replace('series_', '').split('_h5_')[0]
        pix = sk.replace('series_', '').split('_h5_')[1]
        y0 = np.array([g[jj % 25] for jj in range(N)], dtype=np.float64)
        Im0 = float(y0.mean())
        for k0 in K0S:
            e_k = np.exp(-2j * np.pi * k0 * np.arange(N) / N)
            X0 = complex(np.sum((y0 - Im0) * e_k))
            X_full = complex(np.sum((s - s.mean()) * e_k))
            zr = zero_by_key.get('%s|bin%d|px(%s)' % (case_id, k0, pix))
            if zr is None:
                continue
            n_zero_ok += int(abs(abs(X0) - float(zr['abs_X_zerostart_A'])) < GATE and abs(X0 - X_full) < GATE)
    bank_probe = {}
    for key in ALL48:
        m = loadmat(os.path.join(root, 'analysis', 'bank', 'v092_bank_%s.mat' % key))
        bank_probe[key] = (np.asarray(m['X']).astype(np.complex128), np.asarray(m['C']).astype(np.complex128))
    n_probe_ok = 0
    for r in rcsv(os.path.join(root, 'tables', 'v108_probe_gate576.csv')):
        sk = 'series_%s_h5_%s' % (r['case_id'], r['pixel'])
        s = np.asarray(zs[sk], dtype=np.float64)
        i5, j5 = int(r['pixel'].split('_')[0]), int(r['pixel'].split('_')[1])
        k0 = int(r['k0'])
        ki = K0S.index(k0)
        e_k = np.exp(-2j * np.pi * k0 * np.arange(N) / N)
        X_full = complex(np.sum((s - s.mean()) * e_k))
        C_full = 2.0 * X_full / (N * float(s.mean()))
        X_bp = complex(bank_probe[r['case_id']][0][ki].reshape(-1)[i5 * 41 + j5])
        C_bp = complex(bank_probe[r['case_id']][1][ki].reshape(-1)[i5 * 41 + j5])
        n_probe_ok += int(abs(X_full - X_bp) < GATE and abs(C_full - C_bp) < GATE)
    # periods / pairs / components reuse by SHA + gate columns
    reuse = {}
    for rel, expect_rows, gate_field in (
            ('tables/v108_period192.csv', 192, 'status'),
            ('tables/v108_motion_pairs24.csv', 24, 'gate_1e-10'),
            ('analysis/v108_period_components14400.csv', 14400, None)):
        p = os.path.join(root, rel)
        rows = rcsv(p)
        gate_ok = all(r.get(gate_field) == 'PASS' for r in rows) if gate_field else True
        reuse[rel] = {'sha256': sha256_file(p), 'row_count_ok': len(rows) == expect_rows,
                      'gate_columns_ok': gate_ok}
        if len(rows) != expect_rows or not gate_ok:
            issues.append('reuse audit failed: %s' % rel)

    # 852 decomposition recompute (both residuals < 1e-12)
    abs_C = {}
    for key in ALL48:
        for ki, k0 in enumerate(K0S):
            abs_C[(key, k0)] = np.abs(bank[key]['C'][ki]).reshape(-1)
    pairs = [(i, j, 'EE') for i, j in itertools.combinations(ALL24, 2)] + \
            [(i, j, 'EI') for i, j in itertools.product(ALL24, INTER24)]
    n_dec_fail = 0
    dec_rows = []
    for qi, rj, ptype in pairs:
        vq_bins = [abs_C[(qi, k0)] for k0 in K0S]
        vr_bins = [abs_C[(rj, k0)] for k0 in K0S]
        aq_bins = [float(np.linalg.norm(v)) for v in vq_bins]
        ar_bins = [float(np.linalg.norm(v)) for v in vr_bins]
        Aq = float(math.sqrt(sum(a ** 2 for a in aq_bins)))
        Ar = float(math.sqrt(sum(a ** 2 for a in ar_bins)))
        rq = [a / Aq for a in aq_bins]
        rr = [a / Ar for a in ar_bins]
        uq = [v / max(a, 1e-300) for v, a in zip(vq_bins, aq_bins)]
        ur = [v / max(a, 1e-300) for v, a in zip(vr_bins, ar_bins)]
        spec = sum((a - b) ** 2 for a, b in zip(rq, rr))
        spat = sum(a * b * float(np.sum(np.abs(x - y) ** 2)) for a, b, x, y in zip(rq, rr, uq, ur))
        shape_sq = spec + spat
        cq = np.concatenate(vq_bins) / Aq
        cr = np.concatenate(vr_bins) / Ar
        shape_resid = abs(shape_sq - float(np.sum(np.abs(cq - cr) ** 2)))
        sym_sq = 4 * (Aq - Ar) ** 2 / (Aq + Ar) ** 2 + 4 * Aq * Ar / (Aq + Ar) ** 2 * shape_sq
        sym_resid = abs(sym_sq - (2.0 * float(np.linalg.norm(np.concatenate(vq_bins) - np.concatenate(vr_bins))) / (Aq + Ar)) ** 2)
        n_dec_fail += int(not (shape_resid < 1e-12 and sym_resid < 1e-12))
        dec_rows.append({'record_key': '%s__vs__%s' % (qi, rj), 'shape_residual': g17(shape_resid),
                         'sym_residual': g17(sym_resid),
                         'status': 'PASS' if (shape_resid < 1e-12 and sym_resid < 1e-12) else 'FAIL'})
    wcsv(os.path.join(out, 'analysis', 'v110_decomposition852.csv'), list(dec_rows[0].keys()), dec_rows)

    # 1680 radius + 70 + 1680 budgets with qualification m>0 and !tie_crossD
    indep_by_key = {r['record_key']: r for r in indep}
    radius_rows = []
    qual_bad = 0
    for bins in BIN_SUBSETS:
        bins_key = '+'.join(str(b) for b in bins)
        groups = [('+'.join(S), 'endpoint') for S in factor_subsets()] + \
                 [(pname, 'intermediate') for pname in POLICY_NAMES]
        for gname, batch_type in groups:
            queries = ALL24 if batch_type == 'endpoint' else INTER24
            for qi in queries:
                cur = indep_by_key.get('%s|%s|q=%s|unit_magnitude_shape' % (bins_key, gname, qi))
                if cur is None:
                    issues.append('radius key missing: %s|%s|%s' % (bins_key, gname, qi))
                    continue
                m = float(cur['min_cross_minus_min_same'])
                ambiguous = cur['tie_across_D'] == 'YES'
                qualified = m > 0 and not ambiguous
                radius = m / 2.0 if qualified else 0.0
                label = 'POSITIVE' if qualified else ('AMBIGUOUS_CROSS_D' if ambiguous else 'NO_POSITIVE_TRUE_LABEL_RADIUS')
                if qualified != (label == 'POSITIVE'):
                    qual_bad += 1
                radius_rows.append({'record_key': '%s|%s|q=%s' % (bins_key, gname, qi),
                                    'bins': bins_key, 'subset_S': gname, 'query': qi,
                                    'margin_m': g17(m), 'sufficient_radius': g17(radius),
                                    'radius_label': label,
                                    'qualification_m_gt_0_and_no_crossD_tie': 'YES' if qualified else 'NO',
                                    'scope': 'sufficient lower bound; NOT max tolerable radius or noise CI'})
    # budgets derived: eps_q<m/2, symmetric<m/4, eta<m/8
    pert_rows = []
    for r in radius_rows:
        m = float(r['margin_m'])
        pos = r['radius_label'] == 'POSITIVE'
        pert_rows.append({'record_key': r['record_key'], 'bins': r['bins'], 'subset_S': r['subset_S'],
                          'query': r['query'], 'margin_m': r['margin_m'],
                          'eps_q_single_side': g17(m / 2.0 if pos else 0.0),
                          'eps_symmetric_each_side': g17(m / 4.0 if pos else 0.0),
                          'eta_unnormalized_relative': g17(m / 8.0 if pos else 0.0),
                          'budget_label': 'POSITIVE' if pos else 'NO_POSITIVE_BUDGET',
                          'scope': 'boundary formula; NOT measured error or probability'})
    wcsv(os.path.join(out, 'tables', 'v110_radius1680.csv'), list(radius_rows[0].keys()), radius_rows)
    wcsv(os.path.join(out, 'tables', 'v110_perturbation_budget1680.csv'), list(pert_rows[0].keys()), pert_rows)
    # consistency vs frozen v109 tables
    r109 = {r['record_key']: r for r in rcsv(os.path.join(root, 'tables', 'v109_radius1680.csv'))}
    p109 = {r['record_key']: r for r in rcsv(os.path.join(root, 'tables', 'v109_perturbation_budget1680.csv'))}
    r_bad = 0
    for r in radius_rows:
        h = r109.get(r['record_key'])
        if h is None or r['radius_label'] != h.get('radius_label'):
            r_bad += 1
            continue
        for f in ('margin_m', 'sufficient_radius'):
            d = finite_diff(r[f], h.get(f, ''))
            if d is None or not d < 1e-12:
                r_bad += 1
                break
    p_bad = 0
    for r in pert_rows:
        h = p109.get(r['record_key'])
        if h is None:
            p_bad += 1
            continue
        for f in ('eps_q_single_side', 'eps_symmetric_each_side', 'eta_unnormalized_relative'):
            d = finite_diff(r[f], h.get(f, ''))
            if d is None or not d < 1e-12:
                p_bad += 1
                break

    ok_d = (n_ok == 14400 and n_fft_ok == 14400 and n_zero_ok == 576 and n_probe_ok == 576
            and n_dec_fail == 0 and len(dec_rows) == 852 and len(radius_rows) == 1680
            and qual_bad == 0 and r_bad == 0 and p_bad == 0 and not issues)
    if issues:
        FAIL_KEYS.setdefault('D', issues[:10])
    GATES['D_readback_audit'] = ok_d
    STAGE_LOG['D'] = {'origin_readback': '%d/14400' % n_ok, 'fft_audit': '%d/14400' % n_fft_ok,
                      'zerostart': '%d/576' % n_zero_ok, 'probes': '%d/576' % n_probe_ok,
                      'reuse': {k: v for k, v in reuse.items()},
                      'decomposition': '%d/%d' % (len(dec_rows) - n_dec_fail, len(dec_rows)),
                      'radius': len(radius_rows), 'radius_vs_v109_bad': r_bad,
                      'budget_vs_v109_bad': p_bad, 'qualification_bad': qual_bad, 'issues': issues[:10]}
    log('Stage D: origin=%d fft=%d zero=%d probes=%d dec=%d/%d radius_bad=%d'
        % (n_ok, n_fft_ok, n_zero_ok, n_probe_ok, len(dec_rows) - n_dec_fail, len(dec_rows), r_bad))

# ============================== Stage E ==============================

def stage_e(root, out):
    log('=== Stage E: physics evidence levels, source audit, GO/NO-GO ===')
    doc = '00_Codex_v110_v109审查与真实物理准入完整执行指令.md'
    doc2 = '00_Codex_v108_v107审查与实证验收及数据归档指令.md'
    LEVELS = ['USER_CONFIRMED', 'EXPERIMENT_SCRIPT_RECORDED', 'ANALYSIS_CONTRACT',
              'SIMULATION_ASSUMPTION', 'INSTRUMENT_MEASURED', 'MISSING']
    items = [
        {'parameter': 'laser_vacuum_wavelength', 'value': 520.0, 'unit': 'nm',
         'evidence_level': 'USER_CONFIRMED',
         'source_file': doc2, 'source_line': 41,
         'source_snippet_expected': '520 nm',
         'time_validity': 'user confirmation 2026-10-12',
         'uncertainty_or_bound': 'no instrument calibration certificate recorded',
         'note': 'user confirmation is NOT an instrument measurement; certificate still required for metrology use'},
        {'parameter': 'n_frames_N', 'value': 2001, 'unit': 'frames',
         'evidence_level': 'EXPERIMENT_SCRIPT_RECORDED',
         'source_file': doc2, 'source_line': 42, 'source_snippet_expected': 'N=2001',
         'time_validity': 'current',
         'uncertainty_or_bound': 'recorded in extraction scripts and bank metadata',
         'note': None},
        {'parameter': 'frame_rate_Fs', 'value': 5000.0, 'unit': '1/s',
         'evidence_level': 'EXPERIMENT_SCRIPT_RECORDED',
         'source_file': doc2, 'source_line': 42, 'source_snippet_expected': 'Fs=5000',
         'time_validity': 'current',
         'uncertainty_or_bound': 'script-recorded; NO independent clock calibration, accuracy NOT instrument-verified',
         'note': 'must not be upgraded to measured accuracy without external clock calibration'},
        {'parameter': 'spectral_bins_k0', 'value': [80, 160, 320], 'unit': 'bin',
         'evidence_level': 'ANALYSIS_CONTRACT',
         'source_file': doc2, 'source_line': 42, 'source_snippet_expected': 'bin={80,160,320}',
         'time_validity': 'current',
         'uncertainty_or_bound': 'software-selected analysis indices; real frequency = k0*Fs/N',
         'note': 'k0 bins are chosen analysis indices, NOT instrument measurements; INSTRUMENT_MEASURED is invalid here'},
        {'parameter': 'demo_pixel_size_object_plane', 'value': 65.0, 'unit': 'nm',
         'evidence_level': 'SIMULATION_ASSUMPTION',
         'source_file': doc, 'source_line': 22, 'source_snippet_expected': '65nm',
         'time_validity': 'demo only',
         'uncertainty_or_bound': 'demo assumption; NOT measured',
         'note': None},
        {'parameter': 'prescribed_displacement_amplitude_range', 'value': [5.0, 20.0], 'unit': 'nm',
         'evidence_level': 'SIMULATION_ASSUMPTION',
         'source_file': doc2, 'source_line': 106, 'source_snippet_expected': '20nm',
         'time_validity': 'demo only',
         'uncertainty_or_bound': 'prescribed; NOT measured',
         'note': None},
        {'parameter': 'roi_size', 'value': [41, 41], 'unit': 'pixel',
         'evidence_level': 'SIMULATION_ASSUMPTION',
         'source_file': doc2, 'source_line': 42, 'source_snippet_expected': '41',
         'time_validity': 'current demo',
         'uncertainty_or_bound': 'analysis ROI convention',
         'note': None},
        {'parameter': 'object_plane_nm_per_pixel_actual_with_error', 'value': None, 'unit': 'nm/pixel',
         'evidence_level': 'MISSING', 'source_file': None, 'source_line': None,
         'source_snippet_expected': None, 'time_validity': None,
         'uncertainty_or_bound': None,
         'acquisition_method': 'stage calibration or certified ruler image with error budget'},
        {'parameter': 'objective_NA_immersion_illumination_polarization', 'value': None, 'unit': None,
         'evidence_level': 'MISSING', 'source_file': None, 'source_line': None,
         'source_snippet_expected': None, 'time_validity': None,
         'uncertainty_or_bound': None,
         'acquisition_method': 'objective datasheet + illumination configuration record'},
        {'parameter': 'reference_field_path', 'value': None, 'unit': None,
         'evidence_level': 'MISSING', 'source_file': None, 'source_line': None,
         'source_snippet_expected': None, 'time_validity': None,
         'uncertainty_or_bound': None,
         'acquisition_method': 'optical layout record or interferometric characterization'},
        {'parameter': 'exposure_gain_trigger_timestamps', 'value': None, 'unit': None,
         'evidence_level': 'MISSING', 'source_file': None, 'source_line': None,
         'source_snippet_expected': None, 'time_validity': None,
         'uncertainty_or_bound': None,
         'acquisition_method': 'camera acquisition log with exposure and trigger timestamps'},
        {'parameter': 'magnetic_field_B_vector_gradient_waveform_sync', 'value': None, 'unit': None,
         'evidence_level': 'MISSING', 'source_file': None, 'source_line': None,
         'source_snippet_expected': None, 'time_validity': None,
         'uncertainty_or_bound': None,
         'acquisition_method': 'calibrated probe measurement of B(t) vector/gradient with camera sync record'},
        {'parameter': 'particle_batch_coating_medium_substrate_fixation', 'value': None, 'unit': None,
         'evidence_level': 'MISSING', 'source_file': None, 'source_line': None,
         'source_snippet_expected': None, 'time_validity': None,
         'uncertainty_or_bound': None,
         'acquisition_method': 'sample batch record + preparation protocol'},
        {'parameter': 'independent_trajectory_with_scale_and_timebase', 'value': None, 'unit': None,
         'evidence_level': 'MISSING', 'source_file': None, 'source_line': None,
         'source_snippet_expected': None, 'time_validity': None,
         'uncertainty_or_bound': None,
         'acquisition_method': 'independent tracking with certified scale and common timebase'},
        {'parameter': 'independent_diameter_reference_and_blank_background', 'value': None, 'unit': None,
         'evidence_level': 'MISSING', 'source_file': None, 'source_line': None,
         'source_snippet_expected': None, 'time_validity': None,
         'uncertainty_or_bound': None,
         'acquisition_method': 'certified particle standard + particle-free blank capture'},
    ]
    # contract validator: forbidden level assignments must be rejected
    violations = []
    for it in items:
        if it['evidence_level'] not in LEVELS:
            violations.append('%s: unknown level' % it['parameter'])
        if it['evidence_level'] == 'MISSING' and it['value'] is not None:
            violations.append('%s: MISSING must have value null' % it['parameter'])
        if it['parameter'] == 'spectral_bins_k0' and it['evidence_level'] == 'INSTRUMENT_MEASURED':
            violations.append('k0_bins cannot be INSTRUMENT_MEASURED')
        if it['parameter'] == 'frame_rate_Fs' and it['evidence_level'] == 'INSTRUMENT_MEASURED':
            violations.append('Fs cannot be INSTRUMENT_MEASURED without clock calibration')
    # source audit: actually read the cited file/line and confirm the snippet
    audit_rows = []
    for it in items:
        verified = ''
        observed = ''
        if it['source_file'] and it['source_line']:
            p = os.path.join(root, it['source_file'])
            if os.path.isfile(p):
                lines = open(p, encoding='utf-8', errors='replace').read().splitlines()
                if 1 <= it['source_line'] <= len(lines):
                    observed = lines[it['source_line'] - 1].strip()
                    verified = 'VERIFIED' if (it['source_snippet_expected'] or '') in observed else 'SNIPPET_NOT_FOUND'
                else:
                    verified = 'LINE_OUT_OF_RANGE'
            else:
                verified = 'SOURCE_FILE_NOT_FOUND'
        else:
            verified = 'NO_SOURCE_AS_DECLARED' if it['evidence_level'] == 'MISSING' else 'UNVERIFIED'
        audit_rows.append({'parameter': it['parameter'], 'evidence_level': it['evidence_level'],
                           'source_file': it['source_file'] or '', 'source_line': it['source_line'] or '',
                           'observed_snippet': observed[:120], 'source_verification': verified,
                           'classification': 'INDIRECT_UNVERIFIED' if verified not in ('VERIFIED', 'NO_SOURCE_AS_DECLARED') else 'OK'})
    wcsv(os.path.join(out, 'physics_source_audit.csv'), list(audit_rows[0].keys()), audit_rows)
    with open(os.path.join(out, 'physics_input_contract_v110.json'), 'w', encoding='utf-8') as f:
        json.dump({'schema': 'iscat110.physics_input_contract.1',
                   'evidence_levels': LEVELS,
                   'rules': ['MISSING -> value null + acquisition_method',
                             'k0 bins are ANALYSIS_CONTRACT indices, never INSTRUMENT_MEASURED',
                             'script-recorded Fs is NOT instrument-verified accuracy',
                             '520nm is USER_CONFIRMED, no instrument certificate recorded'],
                   'items': items}, f, indent=2, ensure_ascii=False)
    go_nogo = {
        'status': 'REAL_PHYSICS_PENDING_INPUTS',
        'route_A_GO': False,
        'route_B_GO': False,
        'prerequisites': [
            {'item': 'object_plane_nm_per_pixel_with_error', 'evidence': 'MISSING'},
            {'item': 'objective_and_reference_field_or_provable_prior', 'evidence': 'MISSING'},
            {'item': 'exposure_and_clock_with_external_calibration', 'evidence': 'MISSING'},
            {'item': 'independent_particle_free_blank', 'evidence': 'MISSING'},
            {'item': 'diameter_standard_and_sample_batch', 'evidence': 'MISSING'},
            {'item': 'route_A: independently calibrated trajectory', 'evidence': 'MISSING'},
            {'item': 'route_B: measured B(t) vector/gradient/sync + mechanical boundaries', 'evidence': 'MISSING'},
            {'item': 'camera time synchronization record', 'evidence': 'MISSING'},
        ],
        'rule': 'any critical item without evidence -> GO=false; no absolute single-particle diameter claim',
        'design_only': 'bounded real-physics experiment and simulation matrix pre-registered; '
                       'new BEM, noise simulation, and diameter inversion remain 0-authorized',
    }
    with open(os.path.join(out, 'physics_route_go_nogo.json'), 'w', encoding='utf-8') as f:
        json.dump(go_nogo, f, indent=2, ensure_ascii=False)
    with open(os.path.join(out, 'physics_route_plans.json'), 'w', encoding='utf-8') as f:
        json.dump({'route_A': 'calibrated trajectory -> intensity average over exposure -> pixel integration '
                              '-> 2001-point complex DFT; never average complex field then square; '
                              'unknown z/orientation never filled with 0; no self-referential trajectory inversion',
                   'route_B': 'measured B(t) vector/amplitude/gradient/sync + sample magnetics/medium/fixation '
                              '-> constrained dynamics -> trajectory -> route A; 200Hz drive does NOT license '
                              'a 400Hz pure-sine displacement assumption',
                   'authorization': 'pre-registration only; NO solves this round'}, f, indent=2, ensure_ascii=False)
    ok_e = not violations and len(items) == 15 and all(
        r['source_verification'] in ('VERIFIED', 'NO_SOURCE_AS_DECLARED') for r in audit_rows)
    if not ok_e:
        FAIL_KEYS.setdefault('E', violations + [r['parameter'] + ':' + r['source_verification']
                                                for r in audit_rows if r['source_verification'] not in
                                                ('VERIFIED', 'NO_SOURCE_AS_DECLARED')][:10])
    GATES['E_physics_admission'] = ok_e
    STAGE_LOG['E'] = {'items': len(items), 'violations': violations,
                      'source_verified': sum(1 for r in audit_rows if r['source_verification'] == 'VERIFIED'),
                      'no_source_declared': sum(1 for r in audit_rows if r['source_verification'] == 'NO_SOURCE_AS_DECLARED'),
                      'go_status': go_nogo['status']}
    log('Stage E: items=%d verified_src=%d go=%s' % (len(items), STAGE_LOG['E']['source_verified'], go_nogo['status']))

# ============================== Stage F ==============================

def stage_f(root, out, zip_path, checker_src, status_sha):
    """Run the RELEASED checker against real negative cases + the good ZIP."""
    log('=== Stage F: verifier selftest (real checker, negative cases) ===')
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
        args = [sys.executable, checker_src, '--zip', zp, '--out', res_p]
        if expect_status_sha:
            args += ['--expect-status-sha', expect_status_sha]
        proc = subprocess.run(args, capture_output=True, text=True, timeout=600)
        res = json.load(open(res_p, encoding='utf-8')) if os.path.isfile(res_p) else {}
        passed = (proc.returncode != 0) and (res.get('archive_valid') is not True)
        results.append({'case': name, 'exit_code': proc.returncode,
                        'archive_valid': res.get('archive_valid'),
                        'verdict': 'PASS' if passed else 'FAIL'})
        return passed, res

    all_ok = True
    MECH = {'missing_zip', 'missing_bank_case', 'duplicate_member', 'corrupt_crc',
            'manifest_path_traversal', 'status_missing', 'wrong_status_sha'}
    GATE = {'gates_string_bool', 'gates_missing', 'wrong_task_id'}
    case_res = {}

    def run_typed(name, zbytes_or_none, expect_status_sha=None):
        passed, res = run_case(name, zbytes_or_none, expect_status_sha)
        case_res[name] = res
        if name in MECH:
            typed_ok = passed and res.get('archive_integrity') is False
        elif name in GATE:
            typed_ok = passed and res.get('archive_integrity') is True \
                and res.get('numerical_accepted') is False
        else:
            typed_ok = passed
        if not typed_ok:
            results[-1]['verdict'] = 'FAIL'
            results[-1]['typed_expectation'] = name
        return typed_ok

    # 1. missing ZIP
    all_ok &= run_typed('missing_zip', None)
    # 2. missing one BANK case (drop member + manifest entry)
    zin = zipfile.ZipFile(io.BytesIO(good))
    drop = [n for n in zin.namelist() if 'v092_bank_D30_zf450_M200_a5.mat' in n]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zo:
        for n in zin.namelist():
            if n == drop[0] or (n.endswith('manifest_sha256.csv')):
                continue
            zo.writestr(n, zin.read(n))
        # manifest without the dropped file
        man_lines = zin.read('iscat_v110_return/manifest_sha256.csv').decode('utf-8').splitlines()
        keep = [ln for ln in man_lines if 'v092_bank_D30_zf450_M200_a5.mat' not in ln]
        zo.writestr('iscat_v110_return/manifest_sha256.csv', '\n'.join(keep) + '\n')
    all_ok &= run_typed('missing_bank_case', buf.getvalue())
    # 3. duplicate member
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zo:
        for n in zin.namelist():
            zo.writestr(n, zin.read(n))
        zo.writestr(zin.namelist()[3], zin.read(zin.namelist()[3]))
    all_ok &= run_typed('duplicate_member', buf.getvalue())
    # 4. corrupt a byte inside a member payload (CRC failure)
    corrupt = bytearray(good)
    corrupt[len(corrupt) // 2] ^= 0xFF
    all_ok &= run_typed('corrupt_crc', bytes(corrupt))
    # 5. path traversal in manifest
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zo:
        for n in zin.namelist():
            zo.writestr(n, zin.read(n))
        man = zin.read('iscat_v110_return/manifest_sha256.csv').decode('utf-8')
        man += '../escape.txt,%s\n' % ('0' * 64)
        zo.writestr('iscat_v110_return/manifest_sha256.csv', man)
    all_ok &= run_typed('manifest_path_traversal', buf.getvalue())
    # 6. status missing
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zo:
        for n in zin.namelist():
            if n.endswith('/status.json'):
                continue
            if n.endswith('manifest_sha256.csv'):
                man = zin.read(n).decode('utf-8').splitlines()
                keep = [ln for ln in man if 'status.json' not in ln]
                zo.writestr(n, '\n'.join(keep) + '\n')
                continue
            zo.writestr(n, zin.read(n))
    all_ok &= run_typed('status_missing', buf.getvalue())
    # 7-9. fake gates / wrong task / wrong source commit
    st = json.loads(zin.read('iscat_v110_return/status.json'))
    for name, mutate in (('gates_string_bool', lambda s: s['gates'].update({'A_source_admission': 'true'})),
                         ('gates_missing', lambda s: s['gates'].pop('A_source_admission')),
                         ('wrong_task_id', lambda s: s.update({'task_id': 'WRONG_TASK'}))):
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
                    keep = [('status.json,' + new_sha) if ln.split(',')[0].strip() == 'status.json' else ln
                            for ln in man if ln.strip()]
                    zo.writestr(n, '\n'.join(keep) + '\n')
                else:
                    zo.writestr(n, zin.read(n))
        all_ok &= run_typed(name, buf.getvalue())
    # 10. receipt/status sha mismatch (checker run with wrong expected sha)
    all_ok &= run_typed('wrong_status_sha', good, expect_status_sha='0' * 64)
    # positive control
    res_p = os.path.join(work, 'positive.json')
    proc = subprocess.run([sys.executable, checker_src, '--zip', zip_path,
                           '--expect-status-sha', status_sha, '--out', res_p],
                          capture_output=True, text=True, timeout=600)
    pos = json.load(open(res_p, encoding='utf-8')) if os.path.isfile(res_p) else {}
    positive_ok = (pos.get('archive_integrity') is True)
    results.append({'case': 'positive_control', 'exit_code': proc.returncode,
                    'archive_integrity': pos.get('archive_integrity'),
                    'verdict': 'PASS' if positive_ok else 'FAIL'})
    st_fields = list(results[0].keys()) + [k for r in results for k in r if k not in results[0]]
    wcsv(os.path.join(out, 'logs', 'v110_verifier_selftest.csv'),
         st_fields, results)
    # keep JSON verdicts as evidence; drop the large fixture zips from the archive
    for fn in os.listdir(work):
        if fn.startswith('case_') and fn.endswith('.zip'):
            os.remove(os.path.join(work, fn))
    n_pass = sum(1 for r in results if r['verdict'] == 'PASS')
    ok_f = all_ok and positive_ok and n_pass == len(results)
    if not ok_f:
        FAIL_KEYS.setdefault('F', ['selftest %d/%d' % (n_pass, len(results))])
    GATES['F_verifier_selftest'] = ok_f
    STAGE_LOG['F'] = {'cases': len(results), 'passed': n_pass, 'positive_control': positive_ok}
    log('Stage F: selftest %d/%d PASS (incl. positive control)' % (n_pass, len(results)))

# ============================== archive ==============================

def build_status(out, tool_sha):
    numerical = all(GATES[g] for g in REQUIRED_GATES)
    statuses = {'execution': 'COMPLETE',
                'numerical': 'DELTA_EVIDENCE_SEALED' if numerical else 'UNSEALED_PARTIAL',
                'archive': 'PRE_ARCHIVE_VERIFICATION',
                'physics': 'REAL_PHYSICS_PENDING_INPUTS'}
    status = {'schema': 'iscat110.status.1', 'task_id': TASK_ID,
              'created_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
              'source_commit': EXPECTED_V109, 'parent_commit': EXPECTED_V108,
              'tool_sha256': tool_sha,
              'required_gates': list(REQUIRED_GATES),
              'gates': {g: bool(GATES[g]) for g in REQUIRED_GATES},
              'states': statuses,
              'archive_protocol': {'in_zip_status': 'PRE_ARCHIVE_VERIFICATION (honest pre-state; the ZIP cannot '
                                                   'verify itself)',
                                   'external_receipt': 'the ONLY post-archive-verification credential',
                                   'final_summary': 'in-ZIP final_summary holds determined fields; elapsed and '
                                                    'zip sha recorded as null with explicit pre_archive marker; '
                                                    'external post_archive_summary.json carries the final values '
                                                    'and its sha256 is written into the receipt'},
              'stage_logs': STAGE_LOG,
              'environment': {'python': sys.version.split()[0],
                              'numpy': np.__version__, 'scipy': __import__('scipy').__version__},
              'frozen_states': {'calibration_valid': False, 'experimental_validation': False,
                                'detection_validated': False, 'single_particle_diameter': 'NOT_ESTIMATED'},
              'physics_admission': 'REAL_PHYSICS_PENDING_INPUTS',
              'p0_status': 'OPEN (not upgraded)',
              'rule7_new_authorizations': 0,
              'overall': 'DELTA_EVIDENCE_SEALED' if numerical else 'UNSEALED_PARTIAL'}
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
                z.write(full, 'iscat_v110_return/%s' % rel)
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
        print('[v110] FATAL: out dir exists and is not empty')
        return 3
    try:
        if os.path.commonpath([root]) == os.path.commonpath([root, out]):
            print('[v110] FATAL: out must be outside the source root')
            return 3
    except ValueError:
        pass
    os.makedirs(out, exist_ok=True)
    for sub in ('analysis', 'tables', 'logs'):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    tool_sha = sha256_file(os.path.abspath(__file__))
    launch = {'task_id': TASK_ID, 'root': root, 'out': out, 'zip': zip_path,
              'expected_v109_commit': EXPECTED_V109, 'tool_sha256': tool_sha,
              'command': 'python tools/run_v110_all.py --root "%s" --out "%s" --zip "%s"' % (root, out, zip_path),
              'python': sys.version.split()[0], 'numpy': np.__version__,
              'scipy': __import__('scipy').__version__,
              'pid': os.getpid(), 'started_at': time.strftime('%Y-%m-%dT%H:%M:%S')}
    launch_ext = os.path.splitext(zip_path)[0] + '.launch.json'
    with open(launch_ext, 'w', encoding='utf-8') as f:
        json.dump(launch, f, indent=2)
    with open(os.path.join(out, 'logs', 'v110_launch_record.json'), 'w', encoding='utf-8') as f:
        json.dump(launch, f, indent=2)
    shutil.copy2(os.path.abspath(__file__), os.path.join(out, 'logs', 'run_v110_all_snapshot.py'))
    log('launch recorded: %s' % launch_ext)

    bank, zs, series_keys = stage_a(root, out)
    res_b = stage_b(root, out)
    if res_b is not None:
        indep, summ_rows = res_b
        stage_c(root, out, bank, indep, summ_rows)
        stage_d(root, out, bank, zs, series_keys, indep)
    else:
        stage_c(root, out, bank, None, [])
        stage_d(root, out, bank, zs, series_keys, None)
    stage_e(root, out)

    numerical = all(GATES[g] for g in REQUIRED_GATES if g != 'F_verifier_selftest')
    final_summary = {'gates': GATES, 'stage_logs': STAGE_LOG, 'fail_keys': FAIL_KEYS,
                     'elapsed_seconds': None,
                     'pre_archive_note': 'elapsed_seconds and zip_sha256 are null in the in-ZIP snapshot; '
                                         'the external post_archive_summary.json carries final values',
                     'zip_sha256': None}
    with open(os.path.join(out, 'logs', 'v110_final_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(final_summary, f, indent=2)
    status_path, status_sha, statuses, _ = build_status(out, tool_sha)
    # tool SHA changes if the checker/self-test logic lives in a separate committed file; record all tool SHAs
    tool_shas = {'run_v110_all.py': tool_sha,
                 'v110_archive_check.py': sha256_file(os.path.join(root, 'tools', 'v110_archive_check.py')),
                 'run_v109_delta.py': sha256_file(os.path.join(root, 'tools', 'run_v109_delta.py')),
                 'run_v108_all.py': sha256_file(os.path.join(root, 'tools', 'run_v108_all.py'))}
    with open(os.path.join(out, 'logs', 'v110_tool_shas.json'), 'w', encoding='utf-8') as f:
        json.dump(tool_shas, f, indent=2)
    zip_sha = build_zip(out, zip_path)  # provisional build (selftest fixture)

    checker_src = os.path.join(root, 'tools', 'v110_archive_check.py')
    tool_shas['v110_archive_check.py'] = sha256_file(checker_src)
    with open(os.path.join(out, 'logs', 'v110_tool_shas.json'), 'w', encoding='utf-8') as f:
        json.dump(tool_shas, f, indent=2)

    stage_f(root, out, zip_path, checker_src, status_sha)
    provisional_sha = sha256_file(zip_path)
    if GATES['F_verifier_selftest']:
        # two-phase protocol: after tooling qualification, write the FINAL zip once
        # (status gates all-true, final_summary refreshed); old provisional bytes
        # hash is recorded as evidence, never overwritten in place silently.
        final_summary['gates'] = GATES
        with open(os.path.join(out, 'logs', 'v110_final_summary.json'), 'w', encoding='utf-8') as f:
            json.dump(final_summary, f, indent=2)
        os.remove(status_path)
        status_path, status_sha, statuses, _ = build_status(out, tool_sha)
        zip_sha = build_zip(out, zip_path)
        with open(os.path.join(out, 'logs', 'v110_provisional_zip_sha.json'), 'w', encoding='utf-8') as f:
            json.dump({'provisional_zip_sha256': provisional_sha, 'final_zip_sha256': zip_sha,
                       'protocol': 'provisional selftest fixture replaced by single final zip after '
                                   'verifier qualification; both hashes disclosed'}, f, indent=2)
    check_json = os.path.splitext(zip_path)[0] + '.archive_check.json'
    proc = subprocess.run([sys.executable, checker_src, '--zip', zip_path,
                           '--expect-status-sha', status_sha, '--out', check_json],
                          capture_output=True, text=True, timeout=900)
    archive_ok = proc.returncode == 0
    exit_code = 0 if (numerical and archive_ok and GATES['F_verifier_selftest']) else 2

    # external post-archive summary (final values; sha recorded in the receipt)
    final_summary['elapsed_seconds'] = round(time.time() - t0, 1)
    final_summary['zip_sha256'] = zip_sha
    final_summary['status_json_sha256'] = status_sha
    final_summary['exit_code'] = exit_code
    final_summary['archive_integrity'] = archive_ok
    final_summary['pre_archive_note'] = 'external post-archive summary; sha256 recorded in receipt'
    post_path = os.path.splitext(zip_path)[0] + '.post_archive_summary.json'
    with open(post_path, 'w', encoding='utf-8') as f:
        json.dump(final_summary, f, indent=2)
    post_sha = sha256_file(post_path)

    receipt = {'task_id': TASK_ID, 'source_commit': EXPECTED_V109, 'parent_commit': EXPECTED_V108,
               'tool_sha256': tool_sha, 'tool_shas': tool_shas,
               'zip_path': zip_path, 'zip_sha256': zip_sha,
               'zip_size_bytes': os.path.getsize(zip_path),
               'status_json_sha256_in_zip': status_sha,
               'post_archive_summary_path': post_path,
               'post_archive_summary_sha256': post_sha,
               'exit_code': exit_code,
               'execution_status': statuses['execution'],
               'numerical_status': statuses['numerical'],
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
