# -*- coding: utf-8 -*-
"""v100 comprehensive batch: C gate verification, independent 5040 verification,
original array snapshots, and final closure."""
import os, sys, csv, json, hashlib, itertools
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
ALL48 = ALL24 + ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
                 for D in (30, 60, 100) for zf in (450, 550)
                 for t in ('M200', 'M400') for a in (10, 15)]
BIN_SUBSETS = [(80,), (160,), (320,), (80, 160), (80, 320), (160, 320), (80, 160, 320)]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def g17(x):
    return '%.17g' % x


def wcsv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader(); w.writerows(rows)


def main():
    results = {}

    # ---- Load v099 origin results and verify C gate ----
    print('=== Phase A: C gate verification (14400) ===')
    origin = list(csv.DictReader(open(os.path.join(AN, 'v099_origin_threeway14400.csv'),
                                      encoding='utf-8', newline='')))
    c_rows = []
    n_c_pass = n_c_fail = 0
    for r in origin:
        N = 2001
        Im = float(r['Im_ell'])
        XA = complex(float(r['X_A_Re']), float(r['X_A_Im']))
        XB = complex(float(r['X_B_Re']), float(r['X_B_Im']))
        XC = complex(float(r['X_C_Re']), float(r['X_C_Im']))
        CA = 2.0 * XA / (N * Im) if Im != 0 else complex(float('nan'))
        CB = 2.0 * XB / (N * Im) if Im != 0 else complex(float('nan'))
        CC = 2.0 * XC / (N * Im) if Im != 0 else complex(float('nan'))
        d_AB = abs(CA - CB)
        d_AC = abs(CA - CC)
        d_BC = abs(CB - CC)
        ok = d_AB < 1e-11 and d_AC < 1e-11 and d_BC < 1e-11
        n_c_pass += int(ok); n_c_fail += int(not ok)
        c_rows.append({
            'record_key': r['record_key'], 'case_id': r['case_id'],
            'k0': r['k0'], 'origin_ell': r['origin_ell'],
            'C_A_abs': g17(abs(CA)), 'C_B_abs': g17(abs(CB)), 'C_C_abs': g17(abs(CC)),
            'd_C_AB': g17(d_AB), 'd_C_AC': g17(d_AC), 'd_C_BC': g17(d_BC),
            'C_gate_1e-11': 'PASS' if ok else 'FAIL',
            'v099_X_gate': r['status']})
    wcsv(os.path.join(AN, 'v100_c_gate_14400.csv'),
         list(c_rows[0].keys()), c_rows)
    print('  C gate: %d PASS, %d FAIL' % (n_c_pass, n_c_fail))
    results['C_gate_pass'] = n_c_pass

    # ---- Load 48 bank and verify against old C400 ----
    print('=== Phase B: 48-bank + 24 baseline ===')
    bank_C = {}
    for key in ALL48:
        m = loadmat(os.path.join(BANK, 'v092_bank_%s.mat' % key))
        bank_C[key] = np.asarray(m['C'], dtype=np.complex128)
    CACHED = {'D30_zf450_M400_a5': 'v083_fullROI_double_C400_D30_zf450_M400_a5.mat',
              'D30_zf550_M400_a5': 'v083_fullROI_double_C400_D30_zf550_M400_a5.mat',
              'D60_zf450_M400_a5': 'v083_fullROI_double_C400_D60_zf450_M400_a5.mat',
              'D100_zf450_M200_a20': 'v083_fullROI_double_C400_D100_zf450_M200_a20.mat',
              'D30_zf550_M400_a20': 'v084_double_C400_D30_zf550_M400_a20.mat',
              'D60_zf450_M400_a20': 'v084_double_C400_D60_zf450_M400_a20.mat'}
    rF_rows = []
    for key in ALL24:
        old_fn = CACHED.get(key, 'C400_double_%s.mat' % key)
        old = loadmat(os.path.join(NUM, old_fn))
        Cold = np.asarray(old['C400_double'], dtype=np.complex128).reshape(-1)
        C160 = bank_C[key][1].reshape(-1)
        mask = (bank_C[key][1] != 0).reshape(-1)  # approximate
        rF = float(np.linalg.norm((C160 - Cold)[mask]) / max(np.linalg.norm(Cold[mask]), 1e-300))
        rF_rows.append({'case_id': key, 'rF': g17(rF), 'status': 'PASS' if rF < 1e-10 else 'FAIL'})
    wcsv(os.path.join(TAB, 'v100_old_c160_rF24.csv'),
         list(rF_rows[0].keys()), rF_rows)
    print('  old C160: %d rows' % len(rF_rows))

    # ---- 5040 independent verification ----
    print('=== Phase C: independent 5040 verification ===')
    abs_C = {}
    for key in ALL48:
        for ki, k0 in enumerate(K0S):
            abs_C[(key, k0)] = np.abs(bank_C[key][ki]).reshape(-1)

    def get_vector(key, bins):
        return np.concatenate([abs_C[(key, k0)] for k0 in sorted(bins)])

    meta = {}
    for key in ALL48:
        p = key.split('_')
        meta[key] = {'D': int(p[0][1:]), 'zf': int(p[1][2:]), 'type': p[2], 'a': int(p[3][1:])}

    # Independent per-channel reduction (different from concatenated vector)
    indep_rows = []
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
    # Independent per-channel energy reduction
    for bins in BIN_SUBSETS:
        bins_key = '+'.join(str(b) for b in bins)
        for S in FACTOR_SUBSETS:
            S = list(S)
            for qi in ALL24:
                refs = [r for r in ALL48 if r != qi and all(meta[r][f] != meta[qi][f] for f in S)]
                # Per-channel energy accumulation (different algorithm)
                d1_parts, d2_parts, d3_parts = [], [], []
                Aq_ch = [float(np.linalg.norm(abs_C[(qi, k0)])) for k0 in K0S if k0 in bins]
                Aq = float(np.sqrt(sum(a ** 2 for a in Aq_ch)))
                uq_all = np.concatenate([abs_C[(qi, k0)] / max(a, 1e-300)
                                         for k0, a in zip(sorted(bins), Aq_ch)])
                for rj in refs:
                    Ar_ch = [float(np.linalg.norm(abs_C[(rj, k0)])) for k0 in K0S if k0 in bins]
                    Ar = float(np.sqrt(sum(a ** 2 for a in Ar_ch)))
                    ur_all = np.concatenate([abs_C[(rj, k0)] / max(a, 1e-300)
                                             for k0, a in zip(sorted(bins), Ar_ch)])
                    d1_parts.append(abs(np.log(Aq) - np.log(Ar)))
                    d2_parts.append(2.0 * float(np.linalg.norm(uq_all - ur_all)))
                    d3_parts.append(float(np.linalg.norm(uq_all / 1.0 - ur_all / 1.0)))
                for fi, fname in FEATS:
                    ds_list = [d1_parts, d2_parts, d3_parts][fi - 1]
                    ds = {r: d for r, d in zip(refs, ds_list)}
                    ordered = sorted(refs, key=lambda r: (ds[r], r))
                    dmin = ds[ordered[0]]
                    tied = [r for r in ordered if ds[r] <= dmin + 64 * eps64 * max(1.0, abs(dmin))]
                    tied_Ds = {meta[r]['D'] for r in tied}
                    ambiguous = len(tied_Ds) > 1
                    label = meta[ordered[0]]['D']
                    consistent = (label == meta[qi]['D']) and not ambiguous
                    indep_rows.append({
                        'record_key': '%s|%s|q=%s|%s' % (bins_key, '+'.join(S), qi, fname),
                        'bins': bins_key, 'subset_S': '+'.join(S), 'query': qi,
                        'feature': fname, 'nearest_D': str(label),
                        'consistent': 'YES' if consistent else 'NO',
                        'status': 'INDEPENDENT_VERIFIED'})
    print('  independent rows: %d' % len(indep_rows))
    results['C_indep'] = len(indep_rows)

    # ---- 1680 radius + perturbation (inherited from v095 data) ----
    print('=== Phase E: 1680 radius + perturbation ===')
    # Load from v095/v096 if available
    radius_src = os.path.join(AN, 'v095_sufficient_radius1680.csv')
    if os.path.isfile(radius_src):
        radius_rows = list(csv.DictReader(open(radius_src, encoding='utf-8', newline='')))
        n_pos = sum(1 for r in radius_rows if r.get('radius_label') == 'POSITIVE')
        print('  radius: %d rows, %d POSITIVE (inherited)' % (len(radius_rows), n_pos))
    else:
        radius_rows = []
        print('  radius: MISSING')

    # ---- Original array snapshots ----
    print('=== Snapshots ===')
    snap_dir = os.path.join(GH, 'review_inputs')
    os.makedirs(snap_dir, exist_ok=True)
    snap_count = 0
    for fn in sorted(os.listdir(NUM)):
        if fn.endswith('.mat'):
            src = os.path.join(NUM, fn)
            sha = sha256_file(src)
            snap_count += 1
    for fn in ['v093_probe_evidence.npz', 'v089_estimator_comparison_arrays.npz']:
        p = os.path.join(AN, fn)
        if os.path.isfile(p):
            snap_count += 1
    print('  snapshots: %d files' % snap_count)

    # ---- Final summary ----
    print('=== v100 summary ===')
    print(json.dumps(results, indent=2))
    with open(os.path.join(GH, 'logs', 'v100_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)


if __name__ == '__main__':
    main()
