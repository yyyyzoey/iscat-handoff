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
    wcsv(os.path.join(TAB, 'v095_bank_identity48.csv'),
         ['case_id', 'C_eq_max_err', 'mask_ok', 'status'], id_rows)
    wcsv(os.path.join(TAB, 'v095_old_c160_rF24.csv'),
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
        parts = skey.replace('series_', '').split('_h5_')
        case_id = parts[0]
        pix = parts[1]
        s = zs[skey].astype(np.float64)
        Im = float(s.mean())
        for k0 in K0S:
            e = np.exp(-2j * np.pi * k0 * np.arange(N) / N)
            X_indep = complex(np.sum((s - Im) * e))
            C_indep = 2.0 * X_indep / (N * Im) if Im != 0 else complex(np.nan)
            C_bank = bank_C[case_id][K0S.index(k0)].reshape(-1)
            X_bank = bank_X[case_id][K0S.index(k0)].reshape(-1)
            pix_idx = int(pix.split('_')[0]) * 41 + int(pix.split('_')[1])
            X_bp = X_bank[pix_idx]; C_bp = C_bank[pix_idx]
            d_X = abs(X_indep - X_bp)
            d_C = abs(C_indep - C_bp)
            ok = d_X < 1e-11 and d_C < 1e-11
            n_probe_pass += int(ok); n_probe_fail += int(not ok)
            probe_rows.append({'record_key': '%s|bin%d|%s' % (case_id, k0, pix),
                               'case_id': case_id, 'k0': k0, 'pixel': pix,
                               'abs_dX_vs_bank': g17(d_X), 'abs_dC_vs_bank': g17(d_C),
                               'original_gate_1e-11': 'PASS' if ok else 'FAIL'})
    wcsv(os.path.join(TAB, 'v095_probe_rejudgment576.csv'),
         list(probe_rows[0].keys()), probe_rows)
    print('  probes: %d PASS, %d FAIL (original 1e-11 gate)' % (n_probe_pass, n_probe_fail))
    results['B_probe_pass'] = n_probe_pass; results['B_probe_fail'] = n_probe_fail

    # ==================== Phase C: 5040/210 unified comparisons ====================
    print('=== Phase C: 5040 unified comparisons ===')
    BIN_SUBSETS = [(80,), (160,), (320,), (80, 160), (80, 320), (160, 320), (80, 160, 320)]
    meta = {k: parse(k) for k in ALL48}
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
    wcsv(os.path.join(AN, 'v095_comparisons5040.csv'), all_f, comp)
    all_s = ['record_key'] + sorted({k for r in summ for k in r if k != 'record_key'})
    wcsv(os.path.join(AN, 'v095_summaries210.csv'), all_s, summ)
    sub1440 = [r for r in comp if r['bins'] in ('160', '80+160+320')]
    wcsv(os.path.join(AN, 'v095_subset1440.csv'), all_f, sub1440)
    print('  comparisons: %d, summaries: %d' % (len(comp), len(summ)))
    results['C_comparisons'] = len(comp)

    # ==================== Phase D: CORRECT 852-pair decomposition ====================
    print('=== Phase D: correct 852-pair decomposition ===')
    pairs_ee = list(itertools.combinations(ALL24, 2))
    pairs_ei = list(itertools.product(ALL24, INTER24))
    all_pairs = [(i, j, 'EE') for i, j in pairs_ee] + [(i, j, 'EI') for i, j in pairs_ei]
    dec_rows = []
    chan_rows = []
    n_dec_pass = n_dec_fail = 0
    max_resid_shape = 0.0
    max_resid_sym = 0.0
    for qi, rj, ptype in all_pairs:
        vq_bins = [abs_C[(qi, k0)] for k0 in K0S]
        vr_bins = [abs_C[(rj, k0)] for k0 in K0S]
        aq_bins = [float(np.linalg.norm(v)) for v in vq_bins]
        ar_bins = [float(np.linalg.norm(v)) for v in vr_bins]
        Aq = float(np.sqrt(sum(a ** 2 for a in aq_bins)))
        Ar = float(np.sqrt(sum(a ** 2 for a in ar_bins)))
        if Aq == 0 or Ar == 0:
            continue
        # r_ik = a_ik / A_i (NO extra sqrt!)
        rq_bins = [a / Aq for a in aq_bins]
        rr_bins = [a / Ar for a in ar_bins]
        # u_ik = v_ik / a_ik (unit shape per channel)
        uq_bins = [v / a if a > 0 else np.zeros_like(v) for v, a in zip(vq_bins, aq_bins)]
        ur_bins = [v / a if a > 0 else np.zeros_like(v) for v, a in zip(vr_bins, ar_bins)]
        # CORRECT shape_direct^2 = sum_k (r_ik - r_jk)^2 + sum_k r_ik * r_jk * ||u_ik - u_jk||^2
        spec_term = sum((rq - rr) ** 2 for rq, rr in zip(rq_bins, rr_bins))
        spatial_term = sum(rq * rr * float(np.linalg.norm(uq - ur)) ** 2
                           for rq, rr, uq, ur in zip(rq_bins, rr_bins, uq_bins, ur_bins))
        shape_direct_sq = spec_term + spatial_term
        # verify: shape_direct = ||concat(v_i)/A_i - concat(v_j)/A_j||_2
        concat_q = np.concatenate(vq_bins) / Aq
        concat_r = np.concatenate(vr_bins) / Ar
        shape_direct_check = float(np.linalg.norm(concat_q - concat_r))
        shape_resid = abs(shape_direct_sq - shape_direct_check ** 2)
        # CORRECT sym_direct^2 = 4(Ai-Aj)^2/(Ai+Aj)^2 + 4*Ai*Aj/(Ai+Aj)^2 * shape_direct^2
        sym_term = 4 * (Aq - Ar) ** 2 / (Aq + Ar) ** 2
        sym_shape_term = 4 * Aq * Ar / (Aq + Ar) ** 2 * shape_direct_sq
        sym_direct_sq = sym_term + sym_shape_term
        # verify: sym_direct = 2*||concat(v_i) - concat(v_j)||_2 / (Aq + Ar)
        concat_vq = np.concatenate(vq_bins)
        concat_vr = np.concatenate(vr_bins)
        sym_direct_check = 2.0 * float(np.linalg.norm(concat_vq - concat_vr)) / (Aq + Ar)
        sym_resid = abs(sym_direct_sq - sym_direct_check ** 2)
        ok = shape_resid < 1e-12 and sym_resid < 1e-12
        n_dec_pass += int(ok); n_dec_fail += int(not ok)
        max_resid_shape = max(max_resid_shape, shape_resid)
        max_resid_sym = max(max_resid_sym, sym_resid)
        dec_rows.append({'record_key': '%s__vs__%s' % (qi, rj), 'pair_type': ptype,
                         'A_i': g17(Aq), 'A_j': g17(Ar),
                         'spectral_ratio_term': g17(spec_term),
                         'spatial_shape_term': g17(spatial_term),
                         'shape_direct_sq': g17(shape_direct_sq),
                         'shape_direct_check_sq': g17(shape_direct_check ** 2),
                         'shape_residual': g17(shape_resid),
                         'sym_term': g17(sym_term),
                         'sym_shape_term': g17(sym_shape_term),
                         'sym_direct_sq': g17(sym_direct_sq),
                         'sym_direct_check_sq': g17(sym_direct_check ** 2),
                         'sym_residual': g17(sym_resid),
                         'status': 'PASS' if ok else 'FAIL'})
        for k0, rq, rr, uq, ur in zip(K0S, rq_bins, rr_bins, uq_bins, ur_bins):
            chan_rows.append({'pair': '%s__vs__%s' % (qi, rj), 'pair_type': ptype,
                              'k0': k0, 'r_i': g17(rq), 'r_j': g17(rr),
                              'spatial_contrib': g17(rq * rr * float(np.linalg.norm(uq - ur)) ** 2),
                              'unit_shape_dist': g17(float(np.linalg.norm(uq - ur)))})
    wcsv(os.path.join(AN, 'v095_decomposition852.csv'),
         list(dec_rows[0].keys()), dec_rows)
    wcsv(os.path.join(AN, 'v095_channel_contributions2556.csv'),
         list(chan_rows[0].keys()), chan_rows)
    print('  decomposition: %d pairs, %d PASS, %d FAIL' % (len(dec_rows), n_dec_pass, n_dec_fail))
    print('  max shape resid: %.3g, max sym resid: %.3g' % (max_resid_shape, max_resid_sym))
    results['D_pass'] = n_dec_pass; results['D_fail'] = n_dec_fail

    # ==================== Phase E: 1680 sufficient radius ====================
    print('=== Phase E: 1680 sufficient radius ===')
    radius_rows = []
    radius_summ = []
    for bins in BIN_SUBSETS:
        bins_key = '+'.join(str(b) for b in bins)
        for S in FACTOR_SUBSETS:
            S = list(S)
            for qi in ALL24:
                refs = [rj for rj in ALL24 if rj != qi and
                        all(meta[rj][f] != meta[qi][f] for f in S)]
                vq = get_vector(qi, bins)
                Aq = float(np.linalg.norm(vq))
                uq = vq / Aq if Aq > 0 else vq
                qD = meta[qi]['D']
                ds3 = {r: float(np.linalg.norm(uq - get_vector(r, bins) / float(np.linalg.norm(get_vector(r, bins))))) for r in refs}
                same_D = [r for r in refs if meta[r]['D'] == qD]
                cross_D = [r for r in refs if meta[r]['D'] != qD]
                d_same = min(ds3[r] for r in same_D)
                d_cross = min(ds3[r] for r in cross_D)
                m = d_cross - d_same
                if m > 0:
                    radius = m / 2.0
                    label_radius = 'POSITIVE'
                else:
                    radius = 0.0
                    label_radius = 'NO_POSITIVE_TRUE_LABEL_RADIUS'
                rk = '%s|%s|q=%s' % (bins_key, '+'.join(S), qi)
                radius_rows.append({
                    'record_key': rk, 'bins': bins_key, 'subset_S': '+'.join(S),
                    'query': qi, 'd_same': g17(d_same), 'd_cross': g17(d_cross),
                    'margin_m': g17(m), 'sufficient_radius': g17(radius),
                    'radius_label': label_radius,
                    'scope': 'sufficient lower bound; NOT max tolerable radius or noise CI'})
            # summary for this bins+S
            rs = [r for r in radius_rows if r['bins'] == bins_key and r['subset_S'] == '+'.join(S)]
            pos_radii = [float(r['sufficient_radius']) for r in rs if r['radius_label'] == 'POSITIVE']
            radius_summ.append({
                'record_key': '%s|%s' % (bins_key, '+'.join(S)),
                'bins': bins_key, 'subset_S': '+'.join(S),
                'n_queries': len(rs),
                'n_positive_radius': len(pos_radii),
                'n_no_positive': len(rs) - len(pos_radii),
                'min_positive_radius': g17(min(pos_radii)) if pos_radii else 'NONE',
                'median_positive_radius': g17(float(np.median(pos_radii))) if pos_radii else 'NONE',
                'max_positive_radius': g17(max(pos_radii)) if pos_radii else 'NONE'})
    # also for 3 intermediate policies
    for pname, pol in POLICIES:
        for qi in INTER24:
            refs = [rj for rj in ALL24 if pol(qi, rj)]
            vq = get_vector(qi, (80, 160, 320))
            Aq = float(np.linalg.norm(vq))
            uq = vq / Aq if Aq > 0 else vq
            qD = meta[qi]['D']
            ds3 = {r: float(np.linalg.norm(uq - get_vector(r, (80, 160, 320)) / float(np.linalg.norm(get_vector(r, (80, 160, 320)))))) for r in refs}
            same_D = [r for r in refs if meta[r]['D'] == qD]
            cross_D = [r for r in refs if meta[r]['D'] != qD]
            d_same = min(ds3[r] for r in same_D)
            d_cross = min(ds3[r] for r in cross_D)
            m = d_cross - d_same
            radius = m / 2.0 if m > 0 else 0.0
            label_radius = 'POSITIVE' if m > 0 else 'NO_POSITIVE_TRUE_LABEL_RADIUS'
            rk = '3bin|%s|q=%s' % (pname, qi)
            radius_rows.append({
                'record_key': rk, 'bins': '80+160+320', 'subset_S': pname,
                'query': qi, 'd_same': g17(d_same), 'd_cross': g17(d_cross),
                'margin_m': g17(m), 'sufficient_radius': g17(radius),
                'radius_label': label_radius,
                'scope': 'sufficient lower bound; NOT max tolerable radius or noise CI'})
    for pname in ('unknown_zf_motion', 'known_motion', 'known_motion_zf'):
        rs = [r for r in radius_rows if r.get('subset_S') == pname and r['bins'] == '80+160+320']
        pos_radii = [float(r['sufficient_radius']) for r in rs if r['radius_label'] == 'POSITIVE']
        radius_summ.append({
            'record_key': '3bin|%s' % pname, 'bins': '80+160+320', 'subset_S': pname,
            'n_queries': len(rs), 'n_positive_radius': len(pos_radii),
            'n_no_positive': len(rs) - len(pos_radii),
            'min_positive_radius': g17(min(pos_radii)) if pos_radii else 'NONE',
            'median_positive_radius': g17(float(np.median(pos_radii))) if pos_radii else 'NONE',
            'max_positive_radius': g17(max(pos_radii)) if pos_radii else 'NONE'})
    wcsv(os.path.join(AN, 'v095_sufficient_radius1680.csv'),
         list(radius_rows[0].keys()), radius_rows)
    wcsv(os.path.join(AN, 'v095_radius_summaries70.csv'),
         list(radius_summ[0].keys()), radius_summ)
    print('  radius: %d rows, %d summaries' % (len(radius_rows), len(radius_summ)))
    results['E_radius_rows'] = len(radius_rows)

    # ==================== Final summary ====================
    print('=== v094 summary ===')
    print(json.dumps(results, indent=2))
    with open(os.path.join(GH, 'logs', 'v095_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)


if __name__ == '__main__':
    main()
