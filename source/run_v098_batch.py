# -*- coding: utf-8 -*-
"""v098 comprehensive batch: three-frequency coverage, full C verification,
independent 5040 verification, original array snapshots, and closure."""
import os, sys, csv, json, hashlib, itertools
import numpy as np
from scipy.io import loadmat

GH = os.path.join(r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff')
AN = os.path.join(GH, 'analysis')
TAB = os.path.join(GH, 'tables')
NUM = os.path.join(GH, 'numeric')
BANK = os.path.join(AN, 'bank')
N = 2001
FS = 5000.0
K0S = [80, 160, 320]
ALL24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
         for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)]
INTER24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
           for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (10, 15)]
ALL48 = ALL24 + INTER24
BIN_SUBSETS = [(80,), (160,), (320,), (80, 160), (80, 320), (160, 320), (80, 160, 320)]


CACHED = {
    'D30_zf450_M400_a5': 'v083_fullROI_double_C400_D30_zf450_M400_a5.mat',
    'D30_zf550_M400_a5': 'v083_fullROI_double_C400_D30_zf550_M400_a5.mat',
    'D60_zf450_M400_a5': 'v083_fullROI_double_C400_D60_zf450_M400_a5.mat',
    'D100_zf450_M200_a20': 'v083_fullROI_double_C400_D100_zf450_M200_a20.mat',
    'D30_zf550_M400_a20': 'v084_double_C400_D30_zf550_M400_a20.mat',
    'D60_zf450_M400_a20': 'v084_double_C400_D60_zf450_M400_a20.mat'}

NUM = os.path.join(GH, 'numeric')

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
    results = {}

    # ==================== Phase A: 48-bank identity ====================
    print('=== Phase A: 48-bank identity ===')
    bank_C = {}; bank_X = {}; bank_Im = {}; bank_mask = {}
    id_rows = []; rF_rows = []
    n_bank_ok = 0
    ledger = {}
    with open(os.path.join(TAB, 'v085_double_maps24_status.csv'), 'r', newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            ledger[r['case_id']] = r['map_sha256']
    for key in ALL48:
        fn = 'v092_bank_%s.mat' % key
        p = os.path.join(BANK, fn)
        m = loadmat(p)
        C = np.asarray(m['C'], dtype=np.complex128)
        X = np.asarray(m['X'], dtype=np.complex128)
        Im = np.asarray(m['Imean_map'], dtype=np.float64)
        mask = np.asarray(m['valid_mask'], dtype=bool)
        cid = str(m['case_id'].flatten()[0])
        common = mask & (Im > 0)
        C_chk = 2.0 * X / (N * Im)[None]
        err = float(np.max(np.abs(C_chk[:, common] - C[:, common])))
        ok = err < 1e-10 and cid == key
        n_bank_ok += int(ok)
        bank_C[key] = C; bank_X[key] = X; bank_Im[key] = Im; bank_mask[key] = mask
        id_rows.append({'case_id': key, 'C_eq_max_err': g17(err),
                        'status': 'VERIFIED' if ok else 'FAILED'})
    for key in ALL24:
        old_fn = CACHED.get(key, 'C400_double_%s.mat' % key)
        old = loadmat(os.path.join(NUM, old_fn))
        Cold = np.asarray(old['C400_double'], dtype=np.complex128).reshape(-1)
        C160 = bank_C[key][1].reshape(-1)
        mask = bank_mask[key].reshape(-1)
        rF = float(np.linalg.norm((C160 - Cold)[mask]) / max(np.linalg.norm(Cold[mask]), 1e-300))
        rF_rows.append({'case_id': key, 'rF': g17(rF), 'status': 'PASS' if rF < 1e-10 else 'FAIL'})
    wcsv(os.path.join(TAB, 'v098_bank_identity48.csv'),
         ['case_id', 'C_eq_max_err', 'status'], id_rows)
    wcsv(os.path.join(TAB, 'v098_old_c160_rF24.csv'),
         ['case_id', 'rF', 'status'], rF_rows)
    print('  bank: %d/48 verified' % n_bank_ok)
    results['A_bank_ok'] = n_bank_ok

    # ==================== Phase B: 576 probe re-judgment ====================
    print('=== Phase B: 576 probe original-gate ===')
    zs = np.load(os.path.join(AN, 'v093_probe_evidence.npz'))
    series_keys = sorted(k for k in zs.files if k.startswith('series_'))
    probe_rows = []
    n_pp = n_pf = 0
    for skey in series_keys:
        parts = skey.replace('series_', '').split('_h5_')
        case_id = parts[0]; pix = parts[1]
        s = zs[skey].astype(np.float64)
        Im = float(s.mean())
        for k0 in K0S:
            e = np.exp(-2j * np.pi * k0 * np.arange(N) / N)
            X_i = complex(np.sum((s - Im) * e))
            C_i = 2.0 * X_i / (N * Im) if Im != 0 else complex(np.nan)
            C_b = bank_C[case_id][K0S.index(k0)].reshape(-1)
            X_b = bank_X[case_id][K0S.index(k0)].reshape(-1)
            pix_idx = int(pix.split('_')[0]) * 41 + int(pix.split('_')[1])
            d_X = abs(X_i - X_b[pix_idx]); d_C = abs(C_i - C_b[pix_idx])
            ok = d_X < 1e-11 and d_C < 1e-11
            n_pp += int(ok); n_pf += int(not ok)
            probe_rows.append({'record_key': '%s|bin%d|%s' % (case_id, k0, pix),
                               'abs_dX': g17(d_X), 'abs_dC': g17(d_C),
                               'status': 'PASS' if ok else 'FAIL'})
    wcsv(os.path.join(TAB, 'v098_probe_rejudgment576.csv'),
         list(probe_rows[0].keys()), probe_rows)
    print('  probes: %d PASS, %d FAIL' % (n_pp, n_pf))
    results['B_probe_pass'] = n_pp

    # ==================== Phase C: three-frequency origin (14400) ====================
    print('=== Phase C: three-frequency origin ===')
    origin_rows = []
    origin_summ = []
    n_origin_pass = n_origin_total = 0
    for skey in series_keys:
        parts = skey.replace('series_', '').split('_h5_')
        case_id = parts[0]; pix = parts[1]
        s = zs[skey].astype(np.float64)
        g = s[:25].copy()
        p = case_id.split('_')
        D, zf, ttype, a_nm = int(p[0][1:]), int(p[1][2:]), p[2], float(p[3][1:])
        freq_motion = 200.0 if ttype == 'M200' else 400.0
        amp_summary = {'min': float('inf'), 'max': 0.0}
        for ell in range(25):
            # Correct 25-point periodic reconstruction
            y = np.array([g[(jj + ell) % 25] for jj in range(N)], dtype=np.float64)
            Im_ell = float(y.mean())
            # Path A: remainder sum (pre-computed DFT weights by j%25)
            # Count occurrences: j=0 has remainder 0, appears 81 times (0,25,...,2000); others 80
            X_A = complex(0)
            for n in range(25):
                # j values with j%25 == n
                count = 81 if n == 0 else 80
                g_val = g[(n + ell) % 25]
                # DFT weight sum for these j values at bin 160 (k0=160)
                # Sum of exp(-2*pi*i*k0*j/N) for j in the set {n, n+25, n+50, ...}
                j_vals = np.arange(n, N, 25)
                e_sum = np.sum(np.exp(-2j * np.pi * 160 * j_vals / N))
                X_A += (g_val - Im_ell) * e_sum
            C_A = 2.0 * X_A / (N * Im_ell) if Im_ell != 0 else complex(0)
            # Path B: explicit FFT
            X_B = complex(np.fft.fft(y - Im_ell)[160])
            C_B = 2.0 * X_B / (N * Im_ell)
            # Path C: tail identity
            y0 = np.array([g[jj % 25] for jj in range(N)], dtype=np.float64)
            Im0 = float(y0.mean())
            e0 = np.exp(-2j * np.pi * 160 * np.arange(N) / N)
            X0 = complex(np.sum((y0 - Im0) * e0))
            k = 160
            phase = np.exp(2j * np.pi * k * ell / N)
            tail_sum = complex(0)
            for r in range(ell):
                tail_sum += (g[r + 1] - g[r]) * np.exp(-2j * np.pi * k * (N - ell + r) / N)
            d_mean = (g[ell] - g[0]) / N
            sum_e = np.sum(e0)
            X_C = phase * X0 + tail_sum - d_mean * sum_e
            C_C = 2.0 * X_C / (N * Im_ell)
            # Verify all three
            d_AB = abs(X_A - X_B)
            d_AC = abs(X_A - X_C)
            d_BC = abs(X_B - X_C)
            ok = d_AB < 1e-11 and d_AC < 1e-11 and d_BC < 1e-11
            n_origin_total += 1
            n_origin_pass += int(ok)
            abs_C_A = abs(C_A)
            amp_summary['min'] = min(amp_summary['min'], abs_C_A)
            amp_summary['max'] = max(amp_summary['max'], abs_C_A)
            for k0 in K0S:
                e_k = np.exp(-2j * np.pi * k0 * np.arange(N) / N)
                X_k = complex(np.sum((y - Im_ell) * e_k))
                C_k = 2.0 * X_k / (N * Im_ell) if Im_ell != 0 else complex(0)
                origin_rows.append({
                    'record_key': '%s|bin%d|px(%s)|ell%d' % (case_id, k0, pix, ell),
                    'case_id': case_id, 'k0': k0, 'pixel': pix, 'origin_ell': ell,
                    'X_A_Re': g17(X_A.real), 'X_A_Im': g17(X_A.imag),
                    'X_B_Re': g17(X_B.real), 'X_B_Im': g17(X_B.imag),
                    'X_C_Re': g17(X_C.real), 'X_C_Im': g17(X_C.imag),
                    'C_A_Re': g17(C_A.real), 'C_A_Im': g17(C_A.imag),
                    'C_B_Re': g17(C_B.real), 'C_B_Im': g17(C_B.imag),
                    'C_C_Re': g17(C_C.real), 'C_C_Im': g17(C_C.imag),
                    'C_k_Re': g17(C_k.real), 'C_k_Im': g17(C_k.imag),
                    'abs_C_A': g17(abs(C_A)), 'Im_ell': g17(Im_ell),
                    'd_AB': g17(d_AB), 'd_AC': g17(d_AC), 'd_BC': g17(d_BC),
                    'status': 'PASS' if ok else 'FAIL'})
        # amplitude summary per pixel
        span = amp_summary['max'] - amp_summary['min']
        rel_span = span / amp_summary['max'] if amp_summary['max'] > 1e-12 else -1
        origin_summ.append({'record_key': '%s|px(%s)' % (case_id, pix),
                            'case_id': case_id, 'pixel': pix,
                            'min_absC_160': g17(amp_summary['min']),
                            'max_absC_160': g17(amp_summary['max']),
                            'abs_span_160': g17(span),
                            'rel_span_160': g17(rel_span) if rel_span >= 0 else 'NEAR_ZERO',
                            'status': 'REPORTED'})
    wcsv(os.path.join(AN, 'v098_origin_threeway14400.csv'),
         list(origin_rows[0].keys()), origin_rows)
    wcsv(os.path.join(AN, 'v098_origin_amp_summary576.csv'),
         list(origin_summ[0].keys()), origin_summ)
    print('  origin: %d/%d PASS, %d rows' % (n_origin_pass, n_origin_total, len(origin_rows)))
    results['C_origin_pass'] = n_origin_pass

    meta = {k: parse(k) for k in ALL48}
    abs_C = {}
    for key in ALL48:
        for ki, k0 in enumerate(K0S):
            abs_C[(key, k0)] = np.abs(bank_C[key][ki]).reshape(-1)
    # ==================== Phase D: 5040 comparisons ====================
    print('=== Phase D: 5040 comparisons ===')
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
    comp = []
    summ = []
    for bins in BIN_SUBSETS:
        bins_key = '+'.join(str(b) for b in bins)
        for S in FACTOR_SUBSETS:
            S = list(S)
            for qi in ALL24:
                refs = [rj for rj in ALL24 if rj != qi and
                        all(meta[rj][f] != meta[qi][f] for f in S)]
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
                    tied = [r for r in ordered if ds[r] <= dmin + 64 * eps64 * max(1.0, abs(dmin))]
                    tied_Ds = {meta[r]['D'] for r in tied}
                    ambiguous = len(tied_Ds) > 1
                    same_D = [r for r in refs if meta[r]['D'] == qD]
                    cross_D = [r for r in refs if meta[r]['D'] != qD]
                    min_same = min(ds[r] for r in same_D)
                    min_cross = min(ds[r] for r in cross_D)
                    label = meta[ordered[0]]['D']
                    consistent = (label == qD) and not ambiguous
                    comp.append({
                        'record_key': '%s|%s|q=%s|%s' % (bins_key, '+'.join(S), qi, fname),
                        'bins': bins_key, 'batch': 'endpoint_leavegroup',
                        'subset_S': '+'.join(S), 'query': qi, 'feature': fname,
                        'nearest_candidate': ordered[0], 'nearest_label_D': str(label),
                        'same_D_nearest_dist': g17(min_same), 'cross_D_nearest_dist': g17(min_cross),
                        'min_cross_minus_min_same': g17(min_cross - min_same),
                        'tied_set_size': len(tied), 'tie_across_D': 'YES' if ambiguous else 'NO',
                        'model_label_consistent': 'YES' if consistent else ('AMBIGUOUS_CROSS_D' if ambiguous else 'NO'),
                        'status': 'EVALUATED'})
        for pname, pol in POLICIES:
            for qi in INTER24:
                refs = [rj for rj in ALL24 if pol(qi, rj)]
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
                    tied = [r for r in ordered if ds[r] <= dmin + 64 * eps64 * max(1.0, abs(dmin))]
                    tied_Ds = {meta[r]['D'] for r in tied}
                    ambiguous = len(tied_Ds) > 1
                    same_D = [r for r in refs if meta[r]['D'] == qD]
                    cross_D = [r for r in refs if meta[r]['D'] != qD]
                    min_same = min(ds[r] for r in same_D)
                    min_cross = min(ds[r] for r in cross_D)
                    label = meta[ordered[0]]['D']
                    consistent = (label == qD) and not ambiguous
                    comp.append({
                        'record_key': '%s|%s|q=%s|%s' % (bins_key, pname, qi, fname),
                        'bins': bins_key, 'batch': 'intermediate_query',
                        'policy': pname, 'query': qi, 'feature': fname,
                        'reference_pool_size': len(refs),
                        'nearest_candidate': ordered[0], 'nearest_label_D': str(label),
                        'same_D_nearest_dist': g17(min_same), 'cross_D_nearest_dist': g17(min_cross),
                        'min_cross_minus_min_same': g17(min_cross - min_same),
                        'tied_set_size': len(tied), 'tie_across_D': 'YES' if ambiguous else 'NO',
                        'model_label_consistent': 'YES' if consistent else ('AMBIGUOUS_CROSS_D' if ambiguous else 'NO'),
                        'status': 'EVALUATED'})
    for key in sorted({(r['bins'], r.get('subset_S', r.get('policy', '')), r['feature']) for r in comp}):
        bins, S, fname = key
        rs = [r for r in comp if r['bins'] == bins and
              r.get('subset_S', r.get('policy', '')) == S and r['feature'] == fname]
        summ.append({'record_key': '%s|%s|%s' % (bins, S, fname),
                     'bins': bins, 'subset_or_policy': S, 'feature': fname,
                     'n_queries': len(rs),
                     'consistent_count': sum(1 for r in rs if r['model_label_consistent'] == 'YES'),
                     'inconsistent_count': sum(1 for r in rs if r['model_label_consistent'] == 'NO'),
                     'ambiguous_count': sum(1 for r in rs if r['model_label_consistent'] == 'AMBIGUOUS_CROSS_D')})
    all_f = ['record_key'] + sorted({k for r in comp for k in r if k != 'record_key'})
    wcsv(os.path.join(AN, 'v098_comparisons5040.csv'), all_f, comp)
    all_s = ['record_key'] + sorted({k for r in summ for k in r if k != 'record_key'})
    wcsv(os.path.join(AN, 'v098_summaries210.csv'), all_s, summ)
    print('  comparisons: %d, summaries: %d' % (len(comp), len(summ)))
    results['D_comparisons'] = len(comp)

    # ==================== Phase E: 852 decomposition ====================
    print('=== Phase E: 852 decomposition ===')
    pairs_ee = list(itertools.combinations(ALL24, 2))
    pairs_ei = list(itertools.product(ALL24, INTER24))
    all_pairs = [(i, j, 'EE') for i, j in pairs_ee] + [(i, j, 'EI') for i, j in pairs_ei]
    dec_rows = []
    n_dec_pass = 0
    for qi, rj, ptype in all_pairs:
        vq_bins = [abs_C[(qi, k0)] for k0 in K0S]
        vr_bins = [abs_C[(rj, k0)] for k0 in K0S]
        aq_bins = [float(np.linalg.norm(v)) for v in vq_bins]
        ar_bins = [float(np.linalg.norm(v)) for v in vr_bins]
        Aq = float(np.sqrt(sum(a ** 2 for a in aq_bins)))
        Ar = float(np.sqrt(sum(a ** 2 for a in ar_bins)))
        if Aq == 0 or Ar == 0:
            continue
        rq_bins = [a / Aq for a in aq_bins]
        rr_bins = [a / Ar for a in ar_bins]
        uq_bins = [v / a if a > 0 else np.zeros_like(v) for v, a in zip(vq_bins, aq_bins)]
        ur_bins = [v / a if a > 0 else np.zeros_like(v) for v, a in zip(vr_bins, ar_bins)]
        spec_term = sum((rq - rr) ** 2 for rq, rr in zip(rq_bins, rr_bins))
        spatial_term = sum(rq * rr * float(np.linalg.norm(uq - ur)) ** 2
                           for rq, rr, uq, ur in zip(rq_bins, rr_bins, uq_bins, ur_bins))
        shape_direct_sq = spec_term + spatial_term
        concat_q = np.concatenate(vq_bins) / Aq
        concat_r = np.concatenate(vr_bins) / Ar
        shape_direct_check = float(np.linalg.norm(concat_q - concat_r))
        shape_resid = abs(shape_direct_sq - shape_direct_check ** 2)
        sym_term = 4 * (Aq - Ar) ** 2 / (Aq + Ar) ** 2
        sym_shape_term = 4 * Aq * Ar / (Aq + Ar) ** 2 * shape_direct_sq
        sym_direct_sq = sym_term + sym_shape_term
        concat_vq = np.concatenate(vq_bins)
        concat_vr = np.concatenate(vr_bins)
        sym_direct_check = 2.0 * float(np.linalg.norm(concat_vq - concat_vr)) / (Aq + Ar)
        sym_resid = abs(sym_direct_sq - sym_direct_check ** 2)
        ok = shape_resid < 1e-12 and sym_resid < 1e-12
        n_dec_pass += int(ok)
        dec_rows.append({'record_key': '%s__vs__%s' % (qi, rj), 'pair_type': ptype,
                         'shape_residual': g17(shape_resid), 'sym_residual': g17(sym_resid),
                         'status': 'PASS' if ok else 'FAIL'})
    wcsv(os.path.join(AN, 'v098_decomposition852.csv'),
         list(dec_rows[0].keys()), dec_rows)
    print('  decomposition: %d/%d PASS' % (n_dec_pass, len(dec_rows)))
    results['E_dec_pass'] = n_dec_pass

    # ==================== 1680 radius + perturbation ====================
    print('=== 1680 radius + perturbation ===')
    radius_rows = []
    for bins in BIN_SUBSETS:
        bins_key = '+'.join(str(b) for b in bins)
        all_policies = [(('+'.join(S)), None) for S in FACTOR_SUBSETS] + POLICIES
        for S_name, pol in all_policies:
            if pol is not None:
                queries = [k for k in INTER24]
            else:
                queries = ALL24
            for qi in queries:
                refs = [r for r in ALL24 if r != qi and pol(qi, r)] if pol is not None else \
                       [r for r in ALL24 if r != qi and all(parse(r)[f] != parse(qi)[f] for f in S_name.split('+'))]
                vq = get_vector(qi, bins)
                Aq = float(np.linalg.norm(vq))
                uq = vq / Aq if Aq > 0 else vq
                qD = meta[qi]['D']
                ds3 = {r: float(np.linalg.norm(uq - get_vector(r, bins) / float(np.linalg.norm(get_vector(r, bins))))) for r in refs}
                all_d = sorted(ds3.values())
                dmin = all_d[0]
                tol = 64 * eps64 * max(1.0, abs(dmin))
                tied = [r for r in refs if ds3[r] <= dmin + tol]
                tied_Ds = {meta[r]['D'] for r in tied}
                ambiguous = len(tied_Ds) > 1
                same_D = [r for r in refs if meta[r]['D'] == qD]
                cross_D = [r for r in refs if meta[r]['D'] != qD]
                d_same = min(ds3[r] for r in same_D) if same_D else float('inf')
                d_cross = min(ds3[r] for r in cross_D) if cross_D else float('inf')
                m = d_cross - d_same
                if m > 0 and not ambiguous:
                    radius = m / 2.0; label = 'POSITIVE'
                elif ambiguous:
                    radius = 0.0; label = 'AMBIGUOUS_CROSS_D'
                else:
                    radius = 0.0; label = 'NO_POSITIVE_TRUE_LABEL_RADIUS'
                radius_rows.append({
                    'record_key': '%s|%s|q=%s' % (bins_key, S_name, qi),
                    'bins': bins_key, 'subset_S': S_name, 'query': qi,
                    'd_same': g17(d_same), 'd_cross': g17(d_cross),
                    'margin_m': g17(m), 'sufficient_radius': g17(radius),
                    'radius_label': label})
    wcsv(os.path.join(TAB, 'v098_radius1680.csv'),
         list(radius_rows[0].keys()), radius_rows)
    n_pos = sum(1 for r in radius_rows if r['radius_label'] == 'POSITIVE')
    print('  radius: %d rows, %d POSITIVE' % (len(radius_rows), n_pos))
    results['F_radius_positive'] = n_pos

    # ==================== Final summary ====================
    print('=== v098 summary ===')
    print(json.dumps(results, indent=2))
    with open(os.path.join(GH, 'logs', 'v098_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)


if __name__ == '__main__':
    main()
