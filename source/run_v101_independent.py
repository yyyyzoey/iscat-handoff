# -*- coding: utf-8 -*-
"""v101: corrected independent 5040 verification (fixing v100 ALL48/per-channel
normalization defects) + original array snapshots + status update."""
import os, sys, csv, json, hashlib, itertools, shutil
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
           for D in (30, 60, 100) for zf in (450, 550)
           for t in ('M200', 'M400') for a in (10, 15)]
ALL48 = ALL24 + INTER24
def parse(k):
    p = k.split('_')
    return {'D': int(p[0][1:]), 'zf': int(p[1][2:]), 'type': p[2], 'a': int(p[3][1:])}
meta = {k: parse(k) for k in ALL48}
INTER24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
           for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (10, 15)]
BIN_SUBSETS = [(80,), (160,), (320,), (80, 160), (80, 320), (160, 320), (80, 160, 320)]


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

    # ==================== Correct independent 5040 verification ====================
    # Fixes v100 defects:
    # 1. Reference pools use ALL24 (not ALL48) for endpoint queries
    # 2. Distances use concatenated vector (not per-channel normalized)
    # 3. Includes both endpoint (3528) and intermediate (1512) = 5040
    indep = []
    for bins in BIN_SUBSETS:
        bins_key = '+'.join(str(b) for b in bins)
        # Endpoint: 7 factor subsets × 24 queries
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
                        'same_D_nearest_dist': g17(min_same), 'cross_D_nearest_dist': g17(min_cross),
                        'min_cross_minus_min_same': g17(min_cross - min_same),
                        'tied_set_size': len(tied), 'tie_across_D': 'YES' if ambiguous else 'NO',
                        'model_label_consistent': 'YES' if consistent else ('AMBIGUOUS_CROSS_D' if ambiguous else 'NO'),
                        'status': 'INDEPENDENT_VERIFIED'})
        # Intermediate: 3 policies × 24 queries
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
                        'same_D_nearest_dist': g17(min_same), 'cross_D_nearest_dist': g17(min_cross),
                        'min_cross_minus_min_same': g17(min_cross - min_same),
                        'tied_set_size': len(tied), 'tie_across_D': 'YES' if ambiguous else 'NO',
                        'model_label_consistent': 'YES' if consistent else ('AMBIGUOUS_CROSS_D' if ambiguous else 'NO'),
                        'status': 'INDEPENDENT_VERIFIED'})

    # Compare with production 5040
    prod = list(csv.DictReader(open(os.path.join(AN, 'v098_comparisons5040.csv'),
                                    encoding='utf-8', newline='')))
    prod_by_key = {r['record_key']: r for r in prod}
    n_match = n_mismatch = 0
    mismatches = []
    for r in indep:
        pk = r['record_key']
        if pk in prod_by_key:
            pr = prod_by_key[pk]
            d_prod = float(pr.get('complex_diff_L2', pr.get('same_D_nearest_dist', 'nan')))
            d_indep = float(r.get('same_D_nearest_dist', 'nan'))
            if abs(d_prod - d_indep) < 1e-12:
                n_match += 1
            else:
                n_mismatch += 1
                mismatches.append({'record_key': pk, 'prod': g17(d_prod), 'indep': g17(d_indep)})
        else:
            n_mismatch += 1
    # Verify counts
    n_endpoint = sum(1 for r in indep if r['batch'] == 'endpoint_leavegroup')
    n_inter = sum(1 for r in indep if r['batch'] == 'intermediate_query')
    all_pass = (n_endpoint == 3528 and n_inter == 1512 and len(indep) == 5040 and n_mismatch == 0)
    print('[indep] endpoint=%d intermediate=%d total=%d match=%d mismatch=%d' % (
        n_endpoint, n_inter, len(indep), n_match, n_mismatch))
    # Save
    all_f = ['record_key'] + sorted({k for r in indep for k in r if k != 'record_key'})
    wcsv(os.path.join(AN, 'v101_independent5040.csv'), all_f, indep)
    if mismatches:
        wcsv(os.path.join(AN, 'v101_indep_mismatches.csv'),
             list(mismatches[0].keys()), mismatches)
    # Original array snapshots (actually copy files)
    snap_dir = os.path.join(GH, 'review_inputs')
    os.makedirs(snap_dir, exist_ok=True)
    snap_count = 0
    for fn in sorted(os.listdir(NUM)):
        if fn.endswith('.mat'):
            src = os.path.join(NUM, fn)
            dst = os.path.join(snap_dir, fn)
            shutil.copy2(src, dst)
            src_sha = sha256_file(src)
            dst_sha = sha256_file(dst)
            assert src_sha == dst_sha, 'copy failed for %s' % fn
            snap_count += 1
    for fn in ['v093_probe_evidence.npz', 'v089_estimator_comparison_arrays.npz']:
        p = os.path.join(AN, fn)
        if os.path.isfile(p):
            shutil.copy2(p, os.path.join(snap_dir, fn))
            snap_count += 1
    print('  snapshots: %d files copied and SHA-verified' % snap_count)
    print('[v101] summary:', json.dumps({'indep_total': len(indep),
                                          'endpoint': n_endpoint, 'intermediate': n_inter,
                                          'match': n_match, 'mismatch': n_mismatch,
                                          'all_pass': all_pass,
                                          'snapshots': snap_count}, indent=2))


if __name__ == '__main__':
    main()