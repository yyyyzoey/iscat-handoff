# -*- coding: utf-8 -*-
"""v096 comprehensive batch: complete radius (1680), common perturbation (1680),
period diagnostics completion, and discrete record origin diagnostics."""
import os, sys, csv, json, hashlib, itertools
import numpy as np
from scipy.io import loadmat

GH = os.path.join(r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff')
AN = os.path.join(GH, 'analysis')
TAB = os.path.join(GH, 'tables')
BANK = os.path.join(AN, 'bank')
FS = 5000.0
N = 2001
K0S = [80, 160, 320]
ALL24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
         for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)]
INTER24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
           for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (10, 15)]
ALL48 = ALL24 + INTER24
BIN_SUBSETS = [(80,), (160,), (320,), (80, 160), (80, 320), (160, 320), (80, 160, 320)]
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
    from itertools import combinations
    meta = {k: parse(k) for k in ALL48}
    # Load bank C data
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

    # ==================== Complete 1680 radius rows ====================
    print('=== Complete 1680 radius rows ===')
    radius_rows = []
    radius_summ = []
    # For each of 7 bin subsets:
    for bins in BIN_SUBSETS:
        bins_key = '+'.join(str(b) for b in bins)
        # 7 endpoint factor subsets
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
                radius = m / 2.0 if m > 0 else 0.0
                label = 'POSITIVE' if m > 0 else 'NO_POSITIVE_TRUE_LABEL_RADIUS'
                # check tied set for cross-D
                tied = [r for r in sorted(refs, key=lambda r: ds3[r]) if ds3[r] <= d_same + 64 * eps64 * max(1, d_same)]
                tied_Ds = {meta[r]['D'] for r in tied}
                if len(tied_Ds) > 1:
                    label = 'AMBIGUOUS_CROSS_D'
                rk = '%s|%s|q=%s' % (bins_key, '+'.join(S), qi)
                radius_rows.append({
                    'record_key': rk, 'bins': bins_key, 'subset_S': '+'.join(S),
                    'query': qi, 'd_same': g17(d_same), 'd_cross': g17(d_cross),
                    'margin_m': g17(m), 'sufficient_radius': g17(radius),
                    'radius_label': label,
                    'scope': 'sufficient lower bound; NOT max tolerable radius or noise CI'})
        # 3 intermediate policies
        for pname, pol in POLICIES:
            for qi in INTER24:
                refs = [rj for rj in ALL24 if pol(qi, rj)]
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
                radius = m / 2.0 if m > 0 else 0.0
                label = 'POSITIVE' if m > 0 else 'NO_POSITIVE_TRUE_LABEL_RADIUS'
                rk = '%s|%s|q=%s' % (bins_key, pname, qi)
                radius_rows.append({
                    'record_key': rk, 'bins': bins_key, 'subset_S': pname,
                    'query': qi, 'd_same': g17(d_same), 'd_cross': g17(d_cross),
                    'margin_m': g17(m), 'sufficient_radius': g17(radius),
                    'radius_label': label,
                    'scope': 'sufficient lower bound; NOT max tolerable radius or noise CI'})
    # summaries: 7 bins x 10 policy/subsets = 70
    for bins in BIN_SUBSETS:
        bins_key = '+'.join(str(b) for b in bins)
        for S in FACTOR_SUBSETS:
            S_str = '+'.join(S)
            rs = [r for r in radius_rows if r['bins'] == bins_key and r['subset_S'] == S_str]
            pos = [float(r['sufficient_radius']) for r in rs if r['radius_label'] == 'POSITIVE']
            radius_summ.append({'record_key': '%s|%s' % (bins_key, S_str),
                                'bins': bins_key, 'subset_or_policy': S_str,
                                'n_queries': len(rs), 'n_positive_radius': len(pos),
                                'n_no_positive': len(rs) - len(pos),
                                'min_positive_radius': g17(min(pos)) if pos else 'NONE',
                                'median_positive_radius': g17(float(np.median(pos))) if pos else 'NONE',
                                'max_positive_radius': g17(max(pos)) if pos else 'NONE'})
        for pname, _ in POLICIES:
            rs = [r for r in radius_rows if r['bins'] == bins_key and r['subset_S'] == pname]
            pos = [float(r['sufficient_radius']) for r in rs if r['radius_label'] == 'POSITIVE']
            radius_summ.append({'record_key': '%s|%s' % (bins_key, pname),
                                'bins': bins_key, 'subset_or_policy': pname,
                                'n_queries': len(rs), 'n_positive_radius': len(pos),
                                'n_no_positive': len(rs) - len(pos),
                                'min_positive_radius': g17(min(pos)) if pos else 'NONE',
                                'median_positive_radius': g17(float(np.median(pos))) if pos else 'NONE',
                                'max_positive_radius': g17(max(pos)) if pos else 'NONE'})
    fields = list(radius_rows[0].keys())
    wcsv(os.path.join(TAB, 'v096_radius_complete1680.csv'), fields, radius_rows)
    wcsv(os.path.join(TAB, 'v096_radius_summaries70.csv'),
         list(radius_summ[0].keys()), radius_summ)
    print('  radius: %d rows, %d summaries (v095 had 1248, filled %d)' % (
        len(radius_rows), len(radius_summ), len(radius_rows) - 1248))

    # ==================== Common perturbation budget (1680 rows) ====================
    print('=== Common perturbation budget ===')
    pert_rows = []
    pert_summ = []
    for bins in BIN_SUBSETS:
        bins_key = '+'.join(str(b) for b in bins)
        for S in FACTOR_SUBSETS:
            S_str = '+'.join(S)
            rs = [r for r in radius_rows if r['bins'] == bins_key and r['subset_S'] == S_str]
            for r in rs:
                m = float(r['margin_m'])
                # single-side: eps_q < m/2 (reference perfect)
                eps_q_single = m / 2.0 if m > 0 else 0.0
                # symmetric: eps < m/4 (both sides)
                eps_sym = m / 4.0 if m > 0 else 0.0
                # unnormalized relative: eta < m/8
                eta = m / 8.0 if m > 0 else 0.0
                pert_rows.append({
                    'record_key': r['record_key'], 'bins': bins_key, 'subset_S': S_str,
                    'query': r['query'], 'margin_m': r['margin_m'],
                    'eps_q_single_side': g17(eps_q_single),
                    'eps_symmetric_each_side': g17(eps_sym),
                    'eta_unnormalized_relative': g17(eta),
                    'budget_label': 'POSITIVE' if m > 0 else 'NO_POSITIVE_BUDGET',
                    'scope': 'boundary formula; NOT measured error or probability'})
        for pname, _ in POLICIES:
            rs = [r for r in radius_rows if r['bins'] == bins_key and r['subset_S'] == pname]
            for r in rs:
                m = float(r['margin_m'])
                pert_rows.append({
                    'record_key': r['record_key'], 'bins': bins_key, 'subset_S': pname,
                    'query': r['query'], 'margin_m': r['margin_m'],
                    'eps_q_single_side': g17(m / 2.0 if m > 0 else 0),
                    'eps_symmetric_each_side': g17(m / 4.0 if m > 0 else 0),
                    'eta_unnormalized_relative': g17(m / 8.0 if m > 0 else 0),
                    'budget_label': 'POSITIVE' if m > 0 else 'NO_POSITIVE_BUDGET',
                    'scope': 'boundary formula; NOT measured error or probability'})
    for bins in BIN_SUBSETS:
        bins_key = '+'.join(str(b) for b in bins)
        for S in FACTOR_SUBSETS:
            S_str = '+'.join(S)
            rs = [r for r in pert_rows if r['bins'] == bins_key and r['subset_S'] == S_str]
            pos_eps = [float(r['eps_q_single_side']) for r in rs if r['budget_label'] == 'POSITIVE']
            pert_summ.append({'record_key': '%s|%s' % (bins_key, S_str),
                              'bins': bins_key, 'subset_or_policy': S_str,
                              'n_queries': len(rs), 'n_positive_budget': len(pos_eps),
                              'min_positive_eps_q': g17(min(pos_eps)) if pos_eps else 'NONE',
                              'median_positive_eps_q': g17(float(np.median(pos_eps))) if pos_eps else 'NONE'})
        for pname, _ in POLICIES:
            rs = [r for r in pert_rows if r['bins'] == bins_key and r['subset_S'] == pname]
            pos_eps = [float(r['eps_q_single_side']) for r in rs if r['budget_label'] == 'POSITIVE']
            pert_summ.append({'record_key': '%s|%s' % (bins_key, pname),
                              'bins': bins_key, 'subset_or_policy': pname,
                              'n_queries': len(rs), 'n_positive_budget': len(pos_eps),
                              'min_positive_eps_q': g17(min(pos_eps)) if pos_eps else 'NONE',
                              'median_positive_eps_q': g17(float(np.median(pos_eps))) if pos_eps else 'NONE'})
    wcsv(os.path.join(TAB, 'v096_perturbation_budget1680.csv'),
         list(pert_rows[0].keys()), pert_rows)
    wcsv(os.path.join(TAB, 'v096_perturbation_summaries70.csv'),
         list(pert_summ[0].keys()), pert_summ)
    print('  perturbation: %d rows, %d summaries' % (len(pert_rows), len(pert_summ)))

    # ==================== Period diagnostics completion ====================
    print('=== Period diagnostics completion ===')
    zs = np.load(os.path.join(AN, 'v093_probe_evidence.npz'))
    series_keys = sorted(k for k in zs.files if k.startswith('series_'))
    # endpoint + 24 motion pairs + 14400 components
    per_detail = []
    n_endpoint_ok = 0
    motion_pairs = []
    for skey in series_keys:
        parts = skey.replace('series_', '').split('_h5_')
        case_id = parts[0]; pix = parts[1]
        s = zs[skey].astype(np.float64)
        g = s[:25]
        # endpoint (2001st point)
        endpoint_dev = abs(s[2000] - g[0])
        # full periodicity
        max_dev = float(np.max(np.abs(s[:2000] - np.tile(g, 80))))
        # h_r
        n25 = np.arange(25)
        h = np.array([np.mean(g * np.exp(-2j * np.pi * r * n25 / 25)) for r in range(25)])
        # T_kr and closure for 3 bins
        for k0 in K0S:
            T = np.zeros(25, dtype=np.complex128)
            for r in range(25):
                phase = np.exp(2j * np.pi * r * np.arange(N) / 25)
                T[r] = np.sum(np.exp(-2j * np.pi * k0 * np.arange(N) / N) * (phase - np.mean(phase)))
            X_recon = complex(np.sum(T * h))
            e_k = np.exp(-2j * np.pi * k0 * np.arange(N) / N)
            X_direct = complex(np.sum((s - s.mean()) * e_k))
            d = abs(X_recon - X_direct)
            if k0 == 160:
                n_endpoint_ok += int(d < 1e-11)
            # save all 25 components
            for r in range(25):
                contrib = T[r] * h[r]
                per_detail.append({'case_id': case_id, 'k0': k0, 'pixel': pix,
                                   'r': r, 'T_kr_Re': g17(T[r].real), 'T_kr_Im': g17(T[r].imag),
                                   'h_r_Re': g17(h[r].real), 'h_r_Im': g17(h[r].imag),
                                   'contribution_Re': g17(contrib.real), 'contribution_Im': g17(contrib.imag)})
        motion_pairs.append({'case_id': case_id, 'pixel': pix,
                             'endpoint_dev': g17(endpoint_dev),
                             'max_periodicity_dev_2000': g17(max_dev)})
    # 24 M200/M400 pairs: same D/zf/a, different type
    pair_rows = []
    for D in (30, 60, 100):
        for zf in (450, 550):
            for a in (5, 10, 15, 20):
                for pi, (i5, j5) in enumerate(PROBES):
                    m200_key = 'series_D%d_zf%d_M200_a%d_h5_%d_%d' % (D, zf, a, i5, j5)
                    m400_key = 'series_D%d_zf%d_M400_a%d_h5_%d_%d' % (D, zf, a, i5, j5)
                    if m200_key in zs.files and m400_key in zs.files:
                        g200 = zs[m200_key][:25].astype(np.float64)
                        g400 = zs[m400_key][:25].astype(np.float64)
                        # M400[n] should = M200[(2n) mod 25]
                        expected = np.array([g200[(2 * n) % 25] for n in range(25)])
                        d = float(np.max(np.abs(g400 - expected)))
                        pair_rows.append({'record_key': 'D%d_zf%d_a%d_px%d' % (D, zf, a, pi),
                                          'D': D, 'zf': zf, 'a': a, 'pixel_h5': '(%d,%d)' % (i5, j5),
                                          'max_abs_diff_25pt': g17(d),
                                          'status': 'PASS' if d < 1e-10 else 'INVESTIGATE'})
    per_rows = list(csv.DictReader(open(os.path.join(AN, 'v094_period_diagnostic576.csv'), encoding='utf-8', newline='')))
    wcsv(os.path.join(AN, 'v094_period_diagnostic576.csv'),
         list(per_rows[0].keys()), per_rows)
    wcsv(os.path.join(AN, 'v096_period_components14400.csv'),
         list(per_detail[0].keys()), per_detail)
    wcsv(os.path.join(TAB, 'v096_motion_pairs24.csv'),
         list(pair_rows[0].keys()), pair_rows)
    print('  period: %d detail rows, %d motion pairs, endpoint_ok=%d' % (
        len(per_detail), len(pair_rows), n_endpoint_ok))

    # ==================== Discrete record origin diagnostics ====================
    print('=== Discrete record origin diagnostics ===')
    origin_rows = []
    origin_summ = []
    for skey in series_keys:
        parts = skey.replace('series_', '').split('_h5_')
        case_id = parts[0]; pix = parts[1]
        s_full = zs[skey].astype(np.float64)
        g = s_full[:25]
        D, zf, ttype, a = parse(case_id)['D'], parse(case_id)['zf'], parse(case_id)['type'], parse(case_id)['a']
        freq = 200.0 if ttype == 'M200' else 400.0
        for ell in range(25):
            s_ell = np.array([g[(jj + ell) % 25] for jj in range(N)], dtype=np.float64)
            # interpolate full amplitude: use actual sample value at position (jj+ell) mod 2001
            # but for 25-periodic signal, use the 25-point pattern
            s_ell_full = np.array([s_full[(jj + ell) % N] for jj in range(N)], dtype=np.float64)
            Im = float(s_ell_full.mean())
            for k0 in K0S:
                e = np.exp(-2j * np.pi * k0 * np.arange(N) / N)
                X = complex(np.sum((s_ell_full - Im) * e))
                C = 2.0 * X / (N * Im) if Im != 0 else complex(np.nan)
                origin_rows.append({
                    'record_key': '%s|bin%d|px(%s)|ell%d' % (case_id, k0, pix, ell),
                    'case_id': case_id, 'k0': k0, 'pixel': pix, 'origin_ell': ell,
                    'C_Re': g17(C.real), 'C_Im': g17(C.imag), 'abs_C': g17(abs(C)),
                    'Im_mean': g17(Im)})
        # summary per pixel
        for k0 in K0S:
            c_vals = [float(r['abs_C']) for r in origin_rows
                      if r['case_id'] == case_id and r['k0'] == k0 and r['pixel'] == pix]
            if c_vals and max(c_vals) > 1e-12:
                span = max(c_vals) - min(c_vals)
            else:
                span = 0.0
            origin_summ.append({'record_key': '%s|bin%d|px(%s)' % (case_id, k0, pix),
                                'case_id': case_id, 'k0': k0, 'pixel': pix,
                                'min_absC': g17(min(c_vals)) if c_vals else '0',
                                'median_absC': g17(float(np.median(c_vals))) if c_vals else '0',
                                'max_absC': g17(max(c_vals)) if c_vals else '0',
                                'abs_span': g17(span),
                                'note': 'descriptive 25-origin range; NOT stability proof'})
    wcsv(os.path.join(AN, 'v096_origin_results14400.csv'),
         list(origin_rows[0].keys()), origin_rows)
    wcsv(os.path.join(AN, 'v096_origin_summaries576.csv'),
         list(origin_summ[0].keys()), origin_summ)
    print('  origin: %d results, %d summaries' % (len(origin_rows), len(origin_summ)))

    # ==================== Final ====================
    print('=== v096 summary ===')
    print(json.dumps({
        'radius_complete': len(radius_rows),
        'radius_summaries': len(radius_summ),
        'perturbation': len(pert_rows),
        'period_detail': len(per_detail),
        'motion_pairs': len(pair_rows),
        'origin_results': len(origin_rows),
        'origin_summaries': len(origin_summ),
    }, indent=2))
    with open(os.path.join(GH, 'logs', 'v096_summary.json'), 'w', encoding='utf-8') as f:
        json.dump({'radius': len(radius_rows), 'perturbation': len(pert_rows),
                   'period_detail': len(per_detail), 'origin': len(origin_rows)}, f, indent=2)


if __name__ == '__main__':
    main()
