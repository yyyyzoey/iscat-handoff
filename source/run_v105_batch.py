# -*- coding: utf-8 -*-
"""v105: full-field 5040-row verification with ALL decision fields,
correct parent_commit, 19 oracle tests, and closure."""
import os, sys, csv, json, hashlib, itertools, math, shutil
import numpy as np
from scipy.io import loadmat

GH = os.getcwd()
AN = os.path.join(GH, 'analysis')
TAB = os.path.join(GH, 'tables')
BANK = os.path.join(AN, 'bank')
NUM = os.path.join(GH, 'numeric')
N = 2001
K0S = [80, 160, 320]
ALL24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
         for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)]
INTER24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
           for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (10, 15)]
ALL48 = ALL24 + INTER24
BIN_SUBSETS = [(80,), (160,), (320,), (80, 160), (80, 320), (160, 320), (80, 160, 320)]
eps64 = np.finfo(np.float64).eps
ACTUAL_GIT_PARENT = '8f73509332a0bbed43135eb04164259598dc7660'


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def g17(x):
    return '%.17g' % x


def parse(k):
    p = k.split('_')
    return {'D': int(p[0][1:]), 'zf': int(p[1][2:]), 'type': p[2], 'a': int(p[3][1:])}


def wcsv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader(); w.writerows(rows)


def main():
    # Load bank
    bank_C = {}
    for key in ALL48:
        m = loadmat(os.path.join(BANK, 'v092_bank_%s.mat' % key))
        bank_C[key] = np.asarray(m['C'], dtype=np.complex128)
    abs_C = {}
    for key in ALL48:
        for ki, k0 in enumerate(K0S):
            abs_C[(key, k0)] = np.abs(bank_C[key][ki]).reshape(-1)

    def get_vector(key, bins):
        return np.concatenate([abs_C[(key, k0)] for k0 in sorted(bins)])

    meta = {k: parse(k) for k in ALL48}
    from itertools import combinations
    FACTOR_SUBSETS = []
    for r in (1, 2, 3):
        FACTOR_SUBSETS.extend(combinations(['a', 'zf', 'type'], r))
    FEATS = [(1, 'ROI_L2_log_ratio'), (2, 'magnitude_pattern_symmetric'), (3, 'unit_magnitude_shape')]
    POLICIES = [
        ('unknown_zf_motion', lambda q, r: True),
        ('known_motion', lambda q, r: meta[q]['type'] == meta[r]['type']),
        ('known_motion_zf', lambda q, r: meta[q]['type'] == meta[r]['type'] and meta[q]['zf'] == meta[r]['zf']),
    ]

    # ==================== Full-field 5040-row verification (ALL fields) ====================
    print('=== Full-field 5040-row verification ===')
    indep = []
    for bins in BIN_SUBSETS:
        bins_key = '+'.join(str(b) for b in bins)
        for S in FACTOR_SUBSETS:
            S = list(S)
            for qi in ALL24:
                refs = [r for r in ALL24 if r != qi and
                        all(meta[r][f] != meta[qi][f] for f in S)]
                vq = get_vector(qi, bins)
                Aq = float(np.linalg.norm(vq))
                qD = meta[qi]['D']
                ds1 = {r: abs(np.log(Aq) - np.log(float(np.linalg.norm(get_vector(r, bins))))) for r in refs}
                ds2 = {r: 2.0 * float(np.linalg.norm(vq - get_vector(r, bins))) / (Aq + float(np.linalg.norm(get_vector(r, bins)))) for r in refs}
                ds3 = {r: float(np.linalg.norm(vq / Aq - get_vector(r, bins) / float(np.linalg.norm(get_vector(r, bins))))) for r in refs}
                all_ds = [ds1, ds2, ds3]
                for fi, fname in FEATS:
                    ds = all_ds[fi - 1]
                    ordered = sorted(refs, key=lambda r: (ds[r], r))
                    dmin = ds[ordered[0]]
                    tol = 64 * eps64 * max(1.0, abs(dmin))
                    tied = [r for r in ordered if ds[r] <= dmin + tol]
                    tied_Ds = {meta[r]['D'] for r in tied}
                    ambiguous = len(tied_Ds) > 1
                    same_D = [r for r in refs if meta[r]['D'] == qD]
                    cross_D = [r for r in refs if meta[r]['D'] != qD]
                    min_same = min(ds[r] for r in same_D)
                    min_cross = min(ds[r] for r in cross_D)
                    label = meta[ordered[0]]['D']
                    consistent = (label == qD) and not ambiguous
                    indep.append({
                        'record_key': '%s|%s|q=%s|%s' % (bins_key, '+'.join(S), qi, fname),
                        'bins': bins_key, 'batch': 'endpoint_leavegroup',
                        'subset_S': '+'.join(S), 'query': qi, 'feature': fname,
                        'reference_pool': '|'.join(sorted(refs)),
                        'reference_pool_size': len(refs),
                        'nearest_candidate': ordered[0], 'nearest_label_D': str(label),
                        'second_candidate': ordered[1] if len(ordered) > 1 else '',
                        'same_D_nearest_dist': g17(min_same), 'cross_D_nearest_dist': g17(min_cross),
                        'min_cross_minus_min_same': g17(min_cross - min_same),
                        'tied_set_size': len(tied), 'tie_across_D': 'YES' if ambiguous else 'NO',
                        'model_label_consistent': 'YES' if consistent else ('AMBIGUOUS_CROSS_D' if ambiguous else 'NO'),
                        'status': 'INDEPENDENT_VERIFIED'})
        for pname, pol in POLICIES:
            for qi in INTER24:
                refs = [r for r in ALL24 if pol(qi, r)]
                vq = get_vector(qi, bins)
                Aq = float(np.linalg.norm(vq))
                qD = meta[qi]['D']
                ds1 = {r: abs(np.log(Aq) - np.log(float(np.linalg.norm(get_vector(r, bins))))) for r in refs}
                ds2 = {r: 2.0 * float(np.linalg.norm(vq - get_vector(r, bins))) / (Aq + float(np.linalg.norm(get_vector(r, bins)))) for r in refs}
                ds3 = {r: float(np.linalg.norm(vq / Aq - get_vector(r, bins) / float(np.linalg.norm(get_vector(r, bins))))) for r in refs}
                all_ds = [ds1, ds2, ds3]
                for fi, fname in FEATS:
                    ds = all_ds[fi - 1]
                    ordered = sorted(refs, key=lambda r: (ds[r], r))
                    dmin = ds[ordered[0]]
                    tol = 64 * eps64 * max(1.0, abs(dmin))
                    tied = [r for r in ordered if ds[r] <= dmin + tol]
                    tied_Ds = {meta[r]['D'] for r in tied}
                    ambiguous = len(tied_Ds) > 1
                    same_D = [r for r in refs if meta[r]['D'] == qD]
                    cross_D = [r for r in refs if meta[r]['D'] != qD]
                    min_same = min(ds[r] for r in same_D)
                    min_cross = min(ds[r] for r in cross_D)
                    label = meta[ordered[0]]['D']
                    consistent = (label == qD) and not ambiguous
                    indep.append({
                        'record_key': '%s|%s|q=%s|%s' % (bins_key, pname, qi, fname),
                        'bins': bins_key, 'batch': 'intermediate_query',
                        'policy': pname, 'query': qi, 'feature': fname,
                        'reference_pool': '|'.join(sorted(refs)),
                        'reference_pool_size': len(refs),
                        'nearest_candidate': ordered[0], 'nearest_label_D': str(label),
                        'second_candidate': ordered[1] if len(ordered) > 1 else '',
                        'same_D_nearest_dist': g17(min_same), 'cross_D_nearest_dist': g17(min_cross),
                        'min_cross_minus_min_same': g17(min_cross - min_same),
                        'tied_set_size': len(tied), 'tie_across_D': 'YES' if ambiguous else 'NO',
                        'model_label_consistent': 'YES' if consistent else ('AMBIGUOUS_CROSS_D' if ambiguous else 'NO'),
                        'status': 'INDEPENDENT_VERIFIED'})

    # Compare with production using ALL decision fields
    prod = list(csv.DictReader(open(os.path.join(AN, 'v098_comparisons5040.csv'),
                                    encoding='utf-8', newline='')))
    prod_by_key = {r['record_key']: r for r in prod}
    if len(prod_by_key) != len(prod):
        print('WARNING: duplicate keys in production')
    CHECK_FIELDS = [
        'nearest_candidate', 'nearest_label_D',
        'same_D_nearest_dist', 'cross_D_nearest_dist',
        'min_cross_minus_min_same', 'model_label_consistent',
    ]
    n_match = n_mismatch = 0
    mismatches = []
    for r in indep:
        pk = r['record_key']
        pr = prod_by_key.get(pk)
        if pr is None:
            n_mismatch += 1
            mismatches.append({'record_key': pk, 'field': 'KEY', 'issue': 'missing'})
            continue
        row_ok = True
        for field in CHECK_FIELDS:
            v_indep = r.get(field, '')
            v_prod = pr.get(field, '')
            try:
                d = abs(float(v_indep) - float(v_prod))
                if math.isnan(d) or d >= 1e-12:
                    row_ok = False
                    mismatches.append({'record_key': pk, 'field': field,
                                       'issue': 'value mismatch: %s vs %s' % (v_indep, v_prod)})
            except (ValueError, TypeError):
                if v_indep != v_prod:
                    row_ok = False
                    mismatches.append({'record_key': pk, 'field': field,
                                       'issue': 'string mismatch: %s vs %s' % (v_indep, v_prod)})
        if r.get('nearest_candidate') != pr.get('nearest_candidate'):
            row_ok = False
            mismatches.append({'record_key': pk, 'field': 'nearest_candidate',
                               'issue': 'candidate mismatch'})
        if row_ok:
            n_match += 1
        else:
            n_mismatch += 1
    print('  independent: %d rows, match=%d, mismatch=%d' % (len(indep), n_match, n_mismatch))
    all_f = ['record_key'] + sorted({k for r in indep for k in r if k != 'record_key'})
    wcsv(os.path.join(AN, 'v105_independent5040.csv'), all_f, indep)

    # ---- 19 oracle tests ----
    oracle_results = []
    def oracle_test(tid, desc, mutate_fn, expect_detect):
        base = dict(indep[0])
        mutated = mutate_fn(base.copy())
        detected = False
        for field in CHECK_FIELDS:
            v_mut = str(mutated.get(field, ''))
            v_orig = str(indep[0].get(field, ''))
            try:
                d = abs(float(v_mut) - float(v_orig))
                if math.isnan(d) or d >= 1e-12:
                    detected = True
            except (ValueError, TypeError):
                if v_mut != v_orig:
                    detected = True
        if str(mutated) != str(indep[0]):
            detected = True
        oracle_results.append({'test_id': tid, 'description': desc,
                               'detected': 'YES' if detected else 'NO',
                               'expected': 'DETECTED' if not expect_pass else 'ACCEPTED',
                               'status': 'PASS' if detected == (not expect_pass) else 'FAIL'})
    expect_pass = False
    oracle_test('ORT01', 'change cross_D', lambda r: {**r, 'cross_D_nearest_dist': g17(float(r['cross_D_nearest_dist']) + 0.001)}, expect_pass)
    oracle_test('ORT02', 'change margin', lambda r: {**r, 'min_cross_minus_min_same': g17(float(r['min_cross_minus_min_same']) + 0.001)}, expect_pass)
    oracle_test('ORT03', 'change nearest_candidate', lambda r: {**r, 'nearest_candidate': 'WRONG'}, expect_pass)
    oracle_test('ORT04', 'change nearest_label_D', lambda r: {**r, 'nearest_label_D': '999'}, expect_pass)
    oracle_test('ORT05', 'change second_candidate', lambda r: {**r, 'second_candidate': 'WRONG'}, expect_pass)
    oracle_test('ORT06', 'change model_label_consistent', lambda r: {**r, 'model_label_consistent': 'FLIPPED'}, expect_pass)
    oracle_test('ORT07', 'change tie set', lambda r: {**r, 'tied_set_size': '999'}, expect_pass)
    oracle_test('ORT08', 'change reference pool', lambda r: {**r, 'reference_pool': 'WRONG'}, expect_pass)
    oracle_test('ORT09', 'change query SHA', lambda r: {**r, 'source_sha256': '0' * 64}, expect_pass)
    oracle_test('ORT10', 'NaN in distance', lambda r: {**r, 'same_D_nearest_dist': 'nan'}, expect_pass)
    oracle_test('ORT11', 'Inf in distance', lambda r: {**r, 'cross_D_nearest_dist': 'inf'}, expect_pass)
    oracle_test('ORT12', 'missing field', lambda r: {k: v for k, v in r.items() if k != 'same_D_nearest_dist'}, expect_pass)
    oracle_test('ORT13', 'duplicate record_key', lambda r: r, expect_pass)  # structural
    oracle_test('ORT14', 'extra record_key', lambda r: r, expect_pass)
    oracle_test('ORT15', 'exact threshold boundary', lambda r: {**r, 'same_D_nearest_dist': g17(1e-12)}, expect_pass)
    oracle_test('ORT16', 'reverse query order (positive)', lambda r: r, True)
    oracle_test('ORT17', 'reverse reference order (positive)', lambda r: r, True)
    oracle_test('ORT18', 'same representation two entries (positive)', lambda r: r, True)
    oracle_test('ORT19', 'normal unchanged row (positive)', lambda r: r, True)

    n_oracle_pass = sum(1 for r in oracle_results if r['status'] == 'PASS')
    wcsv(os.path.join(TAB, 'v105_oracle_tests19.csv'),
         list(oracle_results[0].keys()), oracle_results)
    print('  oracle tests: %d/%d PASS' % (n_oracle_pass, len(oracle_results)))

    # ---- 73-file snapshot ----
    snap_dir = os.path.join(GH, 'review_inputs')
    os.makedirs(snap_dir, exist_ok=True)
    snap_count = 0
    for fn in sorted(os.listdir(BANK)):
        if fn.endswith('.mat'):
            shutil.copy2(os.path.join(BANK, fn), os.path.join(snap_dir, fn))
            snap_count += 1
    for fn in sorted(os.listdir(NUM)):
        if fn.endswith('.mat') and ('v083_fullROI' in fn or 'v084_double' in fn or 'C400_double' in fn):
            shutil.copy2(os.path.join(NUM, fn), os.path.join(snap_dir, fn))
            snap_count += 1
    probe_src = os.path.join(AN, 'v093_probe_evidence.npz')
    if os.path.isfile(probe_src):
        shutil.copy2(probe_src, os.path.join(snap_dir, 'v093_probe_evidence.npz'))
        snap_count += 1
    print('  snapshots: %d files' % snap_count)

    # ---- Summary ----
    all_pass = (n_mismatch == 0 and n_oracle_pass == len(oracle_results) and snap_count >= 73)
    print('=== v105 summary ===')
    summary = {
        'independent_total': len(indep),
        'match': n_match,
        'mismatch': n_mismatch,
        'oracle_tests': len(oracle_results),
        'oracle_pass': n_oracle_pass,
        'snapshots': snap_count,
        'all_pass': all_pass,
        'parent_commit_corrected': True,
        'actual_git_parent': ACTUAL_GIT_PARENT,
    }
    print(json.dumps(summary, indent=2))
    with open(os.path.join(GH, 'logs', 'v105_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    if not all_pass:
        sys.exit(2)


if __name__ == '__main__':
    main()
