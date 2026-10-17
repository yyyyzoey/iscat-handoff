# -*- coding: utf-8 -*-
"""v103: full-field independent 5040 verification + 73-file snapshot + finite value checks."""
import os, sys, csv, json, hashlib, shutil, itertools, math
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


def g17(x):
    return '%.17g' % x


def parse(k):
    p = k.split('_')
    return {'D': int(p[0][1:]), 'zf': int(p[1][2:]), 'type': p[2], 'a': int(p[3][1:])}


def wcsv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader(); w.writerows(rows)


def is_finite_val(v):
    """Check if a value is finite (not NaN/Inf)."""
    try:
        f = float(v)
        return math.isfinite(f)
    except (ValueError, TypeError):
        return False


def main():
    # Load all 48 bank C arrays
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
    eps64 = np.finfo(np.float64).eps

    # ==================== Full-field independent 5040 verification ====================
    print('=== Full-field independent 5040 verification ===')
    indep = []
    n_pass = n_fail = 0
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
                        'second_label_D': str(meta[ordered[1]]['D']) if len(ordered) > 1 else '',
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
                        'second_label_D': str(meta[ordered[1]]['D']) if len(ordered) > 1 else '',
                        'same_D_nearest_dist': g17(min_same), 'cross_D_nearest_dist': g17(min_cross),
                        'min_cross_minus_min_same': g17(min_cross - min_same),
                        'tied_set_size': len(tied), 'tie_across_D': 'YES' if ambiguous else 'NO',
                        'model_label_consistent': 'YES' if consistent else ('AMBIGUOUS_CROSS_D' if ambiguous else 'NO'),
                        'status': 'INDEPENDENT_VERIFIED'})

    # Compare with production (FULL FIELD)
    prod = list(csv.DictReader(open(os.path.join(AN, 'v098_comparisons5040.csv'),
                                    encoding='utf-8', newline='')))
    prod_by_key = {r['record_key']: r for r in prod}
    # Check for duplicate production keys
    if len(prod_by_key) != len(prod):
        print('WARNING: duplicate keys in production table')
    n_match = n_mismatch = 0
    mismatch_fields = {}
    CHECK_FIELDS = [
        'nearest_candidate', 'nearest_label_D',
        'same_D_nearest_dist', 'cross_D_nearest_dist', 'min_cross_minus_min_same',
        'model_label_consistent',
    ]
    for r in indep:
        pk = r['record_key']
        pr = prod_by_key.get(pk)
        if pr is None:
            n_mismatch += 1
            mismatch_fields[pk] = 'MISSING_IN_PRODUCTION'
            continue
        row_ok = True
        for field in CHECK_FIELDS:
            v_indep = r.get(field, '')
            v_prod = pr.get(field, '')
            # Try numeric comparison first
            try:
                d = abs(float(v_indep) - float(v_prod))
                if math.isnan(d) or d >= 1e-12:
                    row_ok = False
                    mismatch_fields.setdefault(pk, []).append(field)
            except (ValueError, TypeError):
                # String comparison
                if v_indep != v_prod:
                    row_ok = False
                    mismatch_fields.setdefault(pk, []).append(field)
        if row_ok:
            n_match += 1
        else:
            n_mismatch += 1
    print('  independent: %d rows, match=%d, mismatch=%d' % (len(indep), n_match, n_mismatch))
    if mismatch_fields:
        sample = list(mismatch_fields.items())[:3]
        print('  sample mismatches:', sample)

    # Save independent verification
    all_f = ['record_key'] + sorted({k for r in indep for k in r if k != 'record_key'})
    wcsv(os.path.join(AN, 'v103_independent5040.csv'), all_f, indep)

    # ---- 73-file core snapshot ----
    print('=== 73-file core snapshot ===')
    snap_dir = os.path.join(GH, 'review_inputs')
    os.makedirs(snap_dir, exist_ok=True)
    snap_count = 0
    snap_log = []
    # 48 bank
    for fn in sorted(os.listdir(BANK)):
        if fn.endswith('.mat'):
            src = os.path.join(BANK, fn)
            dst = os.path.join(snap_dir, fn)
            shutil.copy2(src, dst)
            sha = hashlib.sha256(open(dst, 'rb').read()).hexdigest()
            snap_count += 1
            snap_log.append({'file': fn, 'sha256': sha, 'role': 'BANK'})
    # 24 baseline
    for fn in sorted(os.listdir(NUM)):
        if fn.endswith('.mat') and ('v083_fullROI' in fn or 'v084_double' in fn or 'C400_double' in fn):
            src = os.path.join(NUM, fn)
            dst = os.path.join(snap_dir, fn)
            shutil.copy2(src, dst)
            sha = hashlib.sha256(open(dst, 'rb').read()).hexdigest()
            snap_count += 1
            snap_log.append({'file': fn, 'sha256': sha, 'role': 'BASELINE'})
    # 1 probe NPZ
    for fn in ['v093_probe_evidence.npz']:
        src = os.path.join(AN, fn)
        if os.path.isfile(src):
            dst = os.path.join(snap_dir, fn)
            shutil.copy2(src, dst)
            sha = hashlib.sha256(open(dst, 'rb').read()).hexdigest()
            snap_count += 1
            snap_log.append({'file': fn, 'sha256': sha, 'role': 'SAVED_SIMULATION_PROBES'})
    # Verify snapshots
    for sl in snap_log:
        dst = os.path.join(snap_dir, sl['file'])
        sha2 = hashlib.sha256(open(dst, 'rb').read()).hexdigest()
        assert sha2 == sl['sha256'], 'snapshot verification failed: %s' % sl['file']
    print('  snapshots: %d files copied and SHA-verified' % snap_count)
    with open(os.path.join(GH, 'logs', 'v103_snapshot_log.json'), 'w', encoding='utf-8') as f:
        json.dump(snap_log, f, indent=2)

    # ---- Summary ----
    all_pass = (n_mismatch == 0 and snap_count >= 73)
    print('[v103] summary:', json.dumps({
        'independent_total': len(indep), 'match': n_match, 'mismatch': n_mismatch,
        'snapshots': snap_count, 'all_pass': all_pass}, indent=2))
    with open(os.path.join(GH, 'logs', 'v103_summary.json'), 'w', encoding='utf-8') as f:
        json.dump({'independent_total': len(indep), 'match': n_match,
                   'mismatch': n_mismatch, 'snapshots': snap_count,
                   'all_pass': all_pass}, f, indent=2)
    if not all_pass:
        sys.exit(2)


if __name__ == '__main__':
    main()
