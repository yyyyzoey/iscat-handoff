# -*- coding: utf-8 -*-
"""v096: complete 1680 radius + common perturbation budget + period diagnostics."""
import os, sys, csv, json, hashlib, itertools, math
import numpy as np
from scipy.io import loadmat

GH = os.path.dirname(os.path.abspath(__file__))
GH = os.path.dirname(GH)  # go up from source/ to repo root
AN = os.path.join(GH, 'analysis')
TAB = os.path.join(GH, 'tables')
BANK = os.path.join(AN, 'bank')
NUM = os.path.join(GH, 'numeric')
eps64 = np.finfo(np.float64).eps
ALL24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
         for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)]
INTER24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
           for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (10, 15)]
ALL48 = ALL24 + INTER24
BIN_SUBSETS = [(80,), (160,), (320,), (80, 160), (80, 320), (160, 320), (80, 160, 320)]
K0S = [80, 160, 320]


def parse_key(k):
    p = k.split('_')
    return {'D': int(p[0][1:]), 'zf': int(p[1][2:]), 'type': p[2], 'a': int(p[3][1:])}


def get_vec(key, bins, abs_c):
    return np.concatenate([abs_c[(key, k0)] for k0 in sorted(bins)])


def g17(x):
    return '%.17g' % x


def wcsv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader(); w.writerows(rows)


def main():
    # Load bank data for ALL48
    bank_C = {}
    for key in ALL48:
        m = loadmat(os.path.join(BANK, 'v092_bank_%s.mat' % key))
        bank_C[key] = np.asarray(m['C'], dtype=np.complex128)
    abs_c = {}
    for key in ALL48:
        for ki, k0 in enumerate(K0S):
            abs_c[(key, k0)] = np.abs(bank_C[key][ki]).reshape(-1)
    meta = {k: parse_key(k) for k in ALL48}

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

    # ==== 1680 radius rows ====
    radius_rows = []
    radius_summ = []
    for bins in BIN_SUBSETS:
        bins_key = '+'.join(str(b) for b in bins)
        all_policies = [(('+'.join(S)), 'endpoint') for S in FACTOR_SUBSETS] + \
                       [(pname, 'intermediate') for pname, _ in POLICIES]
        for S_name, batch_type in all_policies:
            if batch_type == 'endpoint':
                queries = ALL24
                S_list = S_name.split('+')
                get_refs = lambda qi: [r for r in ALL24 if r != qi and all(meta[r][f] != meta[qi][f] for f in S_list)]
            else:
                pol = dict(POLICIES)[S_name]
                queries = INTER24
                get_refs = lambda qi: [r for r in ALL24 if pol(qi, r)]
            for qi in queries:
                refs = get_refs(qi)
                vq = get_vec(qi, bins, abs_c)
                Aq = float(np.linalg.norm(vq))
                uq = vq / Aq if Aq > 0 else vq
                qD = meta[qi]['D']
                ds3 = {r: float(np.linalg.norm(uq - get_vec(r, bins, abs_c) / float(np.linalg.norm(get_vec(r, bins, abs_c))))) for r in refs}
                all_d = sorted(ds3.values())
                dmin = all_d[0]
                tol = 64 * eps64 * max(1.0, abs(dmin))
                tied = [r for r in refs if ds3[r] <= dmin + tol]
                tied_Ds = {meta[r]['D'] for r in tied}
                ambiguous = len(tied_Ds) > 1
                same_D = [r for r in refs if meta[r]['D'] == qD]
                cross_D = [r for r in refs if meta[r]['D'] != qD]
                d_same = min(ds3[r] for r in same_D)
                d_cross = min(ds3[r] for r in cross_D)
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
                    'radius_label': label,
                    'scope': 'sufficient lower bound; NOT noise CI'})
            pos = [float(r['sufficient_radius']) for r in radius_rows
                   if r['bins'] == bins_key and r['subset_S'] == S_name and r['radius_label'] == 'POSITIVE']
            radius_summ.append({'record_key': '%s|%s' % (bins_key, S_name),
                                'bins': bins_key, 'subset_or_policy': S_name,
                                'n_queries': len(queries), 'n_positive_radius': len(pos),
                                'n_no_positive': len(queries) - len(pos),
                                'min_positive_radius': g17(min(pos)) if pos else 'NONE',
                                'median_positive_radius': g17(float(np.median(pos))) if pos else 'NONE',
                                'max_positive_radius': g17(max(pos)) if pos else 'NONE'})

    # ==== 1680 perturbation budget rows ====
    pert_rows = []
    pert_summ = []
    for r in radius_rows:
        m = float(r['margin_m'])
        pert_rows.append({
            'record_key': r['record_key'], 'bins': r['bins'], 'subset_S': r['subset_S'],
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
            pos = [float(r['eps_q_single_side']) for r in rs if r['budget_label'] == 'POSITIVE']
            pert_summ.append({'record_key': '%s|%s' % (bins_key, S_str),
                              'bins': bins_key, 'subset_or_policy': S_str,
                              'n_queries': len(rs), 'n_positive_budget': len(pos),
                              'min_positive_eps_q': g17(min(pos)) if pos else 'NONE',
                              'median_positive_eps_q': g17(float(np.median(pos))) if pos else 'NONE'})
        for pname, _ in POLICIES:
            rs = [r for r in pert_rows if r['bins'] == bins_key and r['subset_S'] == pname]
            pos = [float(r['eps_q_single_side']) for r in rs if r['budget_label'] == 'POSITIVE']
            pert_summ.append({'record_key': '%s|%s' % (bins_key, pname),
                              'bins': bins_key, 'subset_or_policy': pname,
                              'n_queries': len(rs), 'n_positive_budget': len(pos),
                              'min_positive_eps_q': g17(min(pos)) if pos else 'NONE',
                              'median_positive_eps_q': g17(float(np.median(pos))) if pos else 'NONE'})

    # Save
    wcsv(os.path.join(TAB, 'v096_radius_complete1680.csv'),
         list(radius_rows[0].keys()), radius_rows)
    wcsv(os.path.join(TAB, 'v096_radius_summaries70.csv'),
         list(radius_summ[0].keys()), radius_summ)
    wcsv(os.path.join(TAB, 'v096_perturbation_budget1680.csv'),
         list(pert_rows[0].keys()), pert_rows)
    wcsv(os.path.join(TAB, 'v096_perturbation_summaries70.csv'),
         list(pert_summ[0].keys()), pert_summ)
    print('  radius: %d rows, %d summaries' % (len(radius_rows), len(radius_summ)))
    print('  perturbation: %d rows, %d summaries' % (len(pert_rows), len(pert_summ)))


if __name__ == '__main__':
    main()
