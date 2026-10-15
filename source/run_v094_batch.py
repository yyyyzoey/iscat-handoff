# -*- coding: utf-8 -*-
"""v094 comprehensive batch: Phases A-E in one script.
A: 48-bank identity + 24 old C160
B: 576 probe original-gate re-judgment
C: 5040/210 unified comparisons (fixing v093 channel routing)
D: period diagnostics (192 series, 24 pairs, 14400 components)
E: 852-pair spectral decomposition + 180 channel comparisons"""
import os, sys, csv, json, hashlib, itertools
import numpy as np
from scipy.io import loadmat

GH = os.path.join(r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff')
AN = os.path.join(GH, 'analysis')
TAB = os.path.join(GH, 'tables')
BANK = os.path.join(AN, 'bank')
NUM = os.path.join(GH, 'numeric')
FS = 5000.0
N = 2001
K0S = [80, 160, 320]
ALL24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
         for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)]
INTER24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
           for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (10, 15)]
ALL48 = ALL24 + INTER24
CACHED = {'D30_zf450_M400_a5': 'v083_fullROI_double_C400_D30_zf450_M400_a5.mat',
          'D30_zf550_M400_a5': 'v083_fullROI_double_C400_D30_zf550_M400_a5.mat',
          'D60_zf450_M400_a5': 'v083_fullROI_double_C400_D60_zf450_M400_a5.mat',
          'D100_zf450_M200_a20': 'v083_fullROI_double_C400_D100_zf450_M200_a20.mat',
          'D30_zf550_M400_a20': 'v084_double_C400_D30_zf550_M400_a20.mat',
          'D60_zf450_M400_a20': 'v084_double_C400_D60_zf450_M400_a20.mat'}
PROBES = [(20, 20), (20, 0), (0, 20), (25, 0)]


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
    print('=== Phase A: 48-bank identity audit ===')
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
        N_f = float(np.asarray(m['N']).flatten()[0])
        common = mask & (Im > 0)
        C_chk = 2.0 * X / (N_f * Im)[None]
        err = float(np.max(np.abs(C_chk[:, common] - C[:, common])))
        pos = Im[np.isfinite(Im) & (Im > 0)]
        floor = 0.01 * float(np.median(pos))
        mask_ok = bool((mask == (np.isfinite(Im) & (Im > floor))).all())
        ok = err < 1e-10 and mask_ok and cid == key
        n_bank_ok += int(ok)
        bank_C[key] = C; bank_X[key] = X; bank_Im[key] = Im; bank_mask[key] = mask
        id_rows.append({'case_id': key, 'C_eq_max_err': g17(err), 'mask_ok': 'YES' if mask_ok else 'NO',
                        'status': 'VERIFIED' if ok else 'FAILED'})
    # 24 old C160
    for key in ALL24:
        old_fn = CACHED.get(key, 'C400_double_%s.mat' % key)
        old = loadmat(os.path.join(NUM, old_fn))
        Cold = np.asarray(old['C400_double'], dtype=np.complex128).reshape(-1)
        C160 = bank_C[key][1].reshape(-1)
        mask = bank_mask[key].reshape(-1)
        rF = float(np.linalg.norm((C160 - Cold)[mask]) / max(np.linalg.norm(Cold[mask]), 1e-300))
        rF_rows.append({'case_id': key, 'rF': g17(rF), 'status': 'PASS' if rF < 1e-10 else 'FAIL'})
    wcsv(os.path.join(TAB, 'v094_bank_identity48.csv'),
         ['case_id', 'C_eq_max_err', 'mask_ok', 'status'], id_rows)
    wcsv(os.path.join(TAB, 'v094_old_c160_rF24.csv'),
         ['case_id', 'rF', 'status'], rF_rows)
    print('  bank: %d/48 verified' % n_bank_ok)
    results['A_bank_ok'] = n_bank_ok

    # ==================== Phase B: 576 probe re-judgment ====================
    print('=== Phase B: 576 probe original-gate re-judgment ===')
    zs = np.load(os.path.join(AN, 'v093_probe_evidence.npz'))
    series_keys = sorted(k for k in zs.files if k.startswith('series_'))
    probe_rows = []
    n_probe_pass = n_probe_fail = 0
    for skey in series_keys:
        # parse case and pixel from key like 'series_D30_zf450_M200_a5_h5_20_20'
        parts = skey.replace('series_', '').split('_h5_')
        case_id = parts[0]
        pix = parts[1]  # e.g. '20_20'
        s = zs[skey].astype(np.float64)
        Im = float(s.mean())
        for k0 in K0S:
            e = np.exp(-2j * np.pi * k0 * np.arange(N) / N)
            X_indep = complex(np.sum((s - Im) * e))
            C_indep = 2.0 * X_indep / (N * Im) if Im != 0 else complex(np.nan)
            # bank values
            C_bank = bank_C[case_id][K0S.index(k0)].reshape(-1)
            X_bank = bank_X[case_id][K0S.index(k0)].reshape(-1)
            pix_idx = int(pix.split('_')[0]) * 41 + int(pix.split('_')[1])
            X_bp = X_bank[pix_idx]; C_bp = C_bank[pix_idx]
            d_X = abs(X_indep - X_bp)
            d_C = abs(C_indep - C_bp)
            # ORIGINAL gate: per-item complex diff < 1e-11
            ok = d_X < 1e-11 and d_C < 1e-11
            n_probe_pass += int(ok); n_probe_fail += int(not ok)
            probe_rows.append({'record_key': '%s|bin%d|%s' % (case_id, k0, pix),
                               'case_id': case_id, 'k0': k0, 'pixel': pix,
                               'abs_dX_vs_bank': g17(d_X), 'abs_dC_vs_bank': g17(d_C),
                               'original_gate_1e-11': 'PASS' if ok else 'FAIL',
                               'v093_gate_1e-8': 'PASS' if (d_X < 1e-8 and d_C < 1e-8) else 'FAIL'})
    wcsv(os.path.join(TAB, 'v094_probe_rejudgment576.csv'),
         list(probe_rows[0].keys()), probe_rows)
    print('  probes: %d PASS, %d FAIL (original 1e-11 gate)' % (n_probe_pass, n_probe_fail))
    results['B_probe_pass'] = n_probe_pass; results['B_probe_fail'] = n_probe_fail

    # ==================== Phase C: 5040/210 unified comparisons ====================
    print('=== Phase C: 5040 unified comparisons ===')
    # Build magnitude vectors for all 48 states, all 7 bin subsets
    BIN_SUBSETS = [(80,), (160,), (320,), (80, 160), (80, 320), (160, 320), (80, 160, 320)]
    meta = {k: parse(k) for k in ALL48}
    # Pre-compute |C_k| vectors per state per bin
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
    comp = []
    summ = []
    eps64 = np.finfo(np.float64).eps
    for bins in BIN_SUBSETS:
        bins_key = '+'.join(str(b) for b in bins)
        # endpoint leave-group (7 factor subsets)
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
                        'subset_S': '+'.join(S), 'representation': 'ablation_' + bins_key,
                        'query': qi, 'feature': fname,
                        'reference_pool_size': len(refs),
                        'nearest_candidate': ordered[0], 'nearest_label_D': str(label),
                        'same_D_nearest_dist': g17(min_same), 'cross_D_nearest_dist': g17(min_cross),
                        'min_cross_minus_min_same': g17(min_cross - min_same),
                        'tied_set_size': len(tied), 'tie_across_D': 'YES' if ambiguous else 'NO',
                        'model_label_consistent': 'YES' if consistent else ('AMBIGUOUS_CROSS_D' if ambiguous else 'NO'),
                        'status': 'EVALUATED'})
        # intermediate queries (3 policies)
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
                        'policy': pname, 'representation': 'ablation_' + bins_key,
                        'query': qi, 'feature': fname,
                        'reference_pool_size': len(refs),
                        'nearest_candidate': ordered[0], 'nearest_label_D': str(label),
                        'same_D_nearest_dist': g17(min_same), 'cross_D_nearest_dist': g17(min_cross),
                        'min_cross_minus_min_same': g17(min_cross - min_same),
                        'tied_set_size': len(tied), 'tie_across_D': 'YES' if ambiguous else 'NO',
                        'model_label_consistent': 'YES' if consistent else ('AMBIGUOUS_CROSS_D' if ambiguous else 'NO'),
                        'status': 'EVALUATED'})
    # summaries
    for key in sorted({(r['bins'], r.get('subset_S', r.get('policy', '')), r['feature']) for r in comp}):
        bins, S, fname = key
        rs = [r for r in comp if r['bins'] == bins and
              r.get('subset_S', r.get('policy', '')) == S and r['feature'] == fname]
        summ.append({'record_key': '%s|%s|%s' % (bins, S, fname),
                     'bins': bins, 'subset_or_policy': S, 'feature': fname,
                     'n_queries': len(rs),
                     'consistent_count': sum(1 for r in rs if r['model_label_consistent'] == 'YES'),
                     'inconsistent_count': sum(1 for r in rs if r['model_label_consistent'] == 'NO'),
                     'ambiguous_count': sum(1 for r in rs if r['model_label_consistent'] == 'AMBIGUOUS_CROSS_D'),
                     'reading': 'in-sample geometry screen; NOT accuracy'})
    all_f = ['record_key'] + sorted({k for r in comp for k in r if k != 'record_key'})
    wcsv(os.path.join(AN, 'v094_comparisons5040.csv'), all_f, comp)
    all_s = ['record_key'] + sorted({k for r in summ for k in r if k != 'record_key'})
    wcsv(os.path.join(AN, 'v094_summaries210.csv'), all_s, summ)
    # 1440 subset check ({160} and {80,160,320})
    sub1440 = [r for r in comp if r['bins'] in ('160', '80+160+320')]
    wcsv(os.path.join(AN, 'v094_subset1440.csv'), all_f, sub1440)
    print('  comparisons: %d, summaries: %d' % (len(comp), len(summ)))
    results['C_comparisons'] = len(comp)

    # ==================== Phase D: period diagnostics ====================
    print('=== Phase D: period diagnostics ===')
    per_rows = []
    for skey in series_keys:
        parts = skey.replace('series_', '').split('_h5_')
        case_id = parts[0]; pix = parts[1]
        s = zs[skey].astype(np.float64)
        g = s[:25]
        # periodicity check
        max_dev = float(np.max(np.abs(s[:2000] - np.tile(g, 80))))
        # h_r coefficients
        n25 = np.arange(25)
        h = np.array([np.mean(g * np.exp(-2j * np.pi * r * n25 / 25)) for r in range(25)])
        # T_kr projection and closure for 3 bins
        for k0 in K0S:
            T = np.zeros((25,), dtype=np.complex128)
            for r in range(25):
                phase = np.exp(2j * np.pi * r * np.arange(N) / 25)
                T[r] = np.sum(np.exp(-2j * np.pi * k0 * np.arange(N) / N) * (phase - np.mean(phase)))
            X_recon = complex(np.sum(T * h))
            e_k = np.exp(-2j * np.pi * k0 * np.arange(N) / N)
            X_direct = complex(np.sum((s - s.mean()) * e_k))
            d = abs(X_recon - X_direct)
            per_rows.append({'record_key': '%s|bin%d|%s' % (case_id, k0, pix),
                             'case_id': case_id, 'k0': k0, 'pixel': pix,
                             'periodicity_max_dev_first_2000': g17(max_dev),
                             'abs_X_direct': g17(abs(X_direct)),
                             'abs_X_periodic_recon': g17(abs(X_recon)),
                             'abs_diff': g17(d),
                             'gate_1e-11': 'PASS' if d < 1e-11 else 'FAIL'})
    wcsv(os.path.join(AN, 'v094_period_diagnostic576.csv'),
         list(per_rows[0].keys()), per_rows)
    print('  period rows: %d' % len(per_rows))

    # ==================== Phase E: spectral decomposition (852 pairs) ====================
    print('=== Phase E: spectral decomposition ===')
    # Build 852 pairs: 276 endpoint-endpoint + 576 endpoint-intermediate
    pairs_ee = list(itertools.combinations(ALL24, 2))
    pairs_ei = list(itertools.product(ALL24, INTER24))
    all_pairs = [(i, j, 'EE') for i, j in pairs_ee] + [(i, j, 'EI') for i, j in pairs_ei]
    dec_rows = []
    chan_rows = []
    for qi, rj, ptype in all_pairs:
        vq_bins = [abs_C[(qi, k0)] for k0 in K0S]
        vr_bins = [abs_C[(rj, k0)] for k0 in K0S]
        aq_bins = [float(np.linalg.norm(v)) for v in vq_bins]
        ar_bins = [float(np.linalg.norm(v)) for v in vr_bins]
        Aq = float(np.sqrt(sum(a ** 2 for a in aq_bins)))
        Ar = float(np.sqrt(sum(a ** 2 for a in ar_bins)))
        if Aq == 0 or Ar == 0:
            continue
        # spectral ratio term
        spec_term = sum((np.sqrt(aq / Aq) - np.sqrt(ar / Ar)) ** 2
                        for aq, ar in zip(aq_bins, ar_bins))
        # spatial shape term per channel
        total_shape = 0.0
        for k0, vq_k, vr_k, aq_k, ar_k in zip(K0S, vq_bins, vr_bins, aq_bins, ar_bins):
            if aq_k == 0 or ar_k == 0:
                continue
            uq = vq_k / aq_k; ur = vr_k / ar_k
            p_q = aq_k ** 2 / Aq ** 2; p_r = ar_k ** 2 / Ar ** 2
            contrib = np.sqrt(p_q * p_r) * float(np.linalg.norm(uq - ur))
            total_shape += contrib
            chan_rows.append({'pair': '%s__vs__%s' % (qi, rj), 'pair_type': ptype,
                              'k0': k0, 'p_i': g17(p_q), 'p_j': g17(p_r),
                              'spatial_shape_contrib': g17(contrib),
                              'unit_shape_dist': g17(float(np.linalg.norm(uq - ur)))})
        d_shape_sq = spec_term + total_shape
        d_sym_sq = 4 * (Aq - Ar) ** 2 / (Aq + Ar) ** 2 + (4 * Aq * Ar / (Aq + Ar) ** 2) * d_shape_sq
        d_sym_actual = float(np.linalg.norm(
            np.concatenate(vq_bins) / Aq - np.concatenate(vr_bins) / Ar))
        resid = d_sym_sq - d_sym_actual ** 2
        dec_rows.append({'record_key': '%s__vs__%s' % (qi, rj), 'pair_type': ptype,
                         'A_i': g17(Aq), 'A_j': g17(Ar),
                         'spectral_ratio_term': g17(spec_term),
                         'spatial_shape_term': g17(total_shape),
                         'd_shape_squared': g17(d_shape_sq),
                         'd_sym_squared_decomposed': g17(d_sym_sq),
                         'd_sym_squared_actual': g17(d_sym_actual ** 2),
                         'identity_residual': g17(resid),
                         'status': 'PASS' if abs(resid) < 1e-12 else 'FAIL'})
    wcsv(os.path.join(AN, 'v094_spectral_decomposition852.csv'),
         list(dec_rows[0].keys()), dec_rows)
    wcsv(os.path.join(AN, 'v094_channel_contributions.csv'),
         list(chan_rows[0].keys()), chan_rows)
    print('  decomposition: %d pairs, %d channel rows' % (len(dec_rows), len(chan_rows)))

    # ==================== Assembly ====================
    print('=== Assembly ===')
    n_abl_pass = sum(1 for r in comp if r['model_label_consistent'] == 'YES')
    summary_data = {
        'A_bank_verified': n_bank_ok,
        'B_probe_144': {'pass': n_probe_pass, 'fail': n_probe_fail,
                        'note': 'original 1e-11 gate; v093 used 1e-8'},
        'C_comparisons': len(comp),
        'C_summaries': len(summ),
        'D_period_rows': len(per_rows),
        'E_decomposition_pairs': len(dec_rows),
        'E_channel_rows': len(chan_rows),
        'ablation_consistent': n_abl_pass,
        'ablation_total': len(comp),
    }
    with open(os.path.join(GH, 'logs', 'v094_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2)
    print('[v094] summary:', json.dumps(summary_data))


if __name__ == '__main__':
    main()
