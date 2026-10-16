# -*- coding: utf-8 -*-
"""v097: corrected 1680 radius with proper tie logic + closure."""
import os, sys, csv, json, hashlib, itertools
import numpy as np
from scipy.io import loadmat

GH = os.path.join(r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff')
AN = os.path.join(GH, 'analysis')
TAB = os.path.join(GH, 'tables')
BANK = os.path.join(AN, 'bank')
FS = 5000.0
K0S = [80, 160, 320]
ALL24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
         for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)]
ALL48 = ALL24 + ['D%d_zf%d_%s_a%d' % (D, zf, t, a) for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (10, 15)]
CACHED = {'D30_zf450_M400_a5': 'v083_fullROI_double_C400_D30_zf450_M400_a5.mat',
          'D30_zf550_M400_a5': 'v083_fullROI_double_C400_D30_zf550_M400_a5.mat',
          'D60_zf450_M400_a5': 'v083_fullROI_double_C400_D60_zf450_M400_a5.mat',
          'D100_zf450_M200_a20': 'v083_fullROI_double_C400_D100_zf450_M200_a20.mat',
          'D30_zf550_M400_a20': 'v084_double_C400_D30_zf550_M400_a20.mat',
          'D60_zf450_M400_a20': 'v084_double_C400_D60_zf450_M400_a20.mat'}


def wcsv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader(); w.writerows(rows)


def g17(x):
    return '%.17g' % x


def parse(k):
    p = k.split('_')
    return {'D': int(p[0][1:]), 'zf': int(p[1][2:]), 'type': p[2], 'a': int(p[3][1:])}


def main():
    from itertools import combinations
    # Load 24 endpoint maps
    abs_C = {}
    meta = {}
    for key in ALL48:
        fn = CACHED.get(key, 'C400_double_%s.mat' % key)
        m = loadmat(os.path.join(BANK, 'v092_bank_%s.mat' % key))
        C = np.asarray(m['C'], dtype=np.complex128)
        for ki, k0 in enumerate([80, 160, 320]):
            abs_C[(key, k0)] = np.abs(C[ki]).reshape(-1)
        meta[key] = parse(key)

    def get_vector(key, bins):
        return np.concatenate([abs_C[(key, k0)] for k0 in sorted(bins)])

    BIN_SUBSETS = [(80,), (160,), (320,), (80, 160), (80, 320), (160, 320), (80, 160, 320)]
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
    # Corrected radius: 7 bins x 10 policy/subsets x 24 queries = 1680
    radius_rows = []
    radius_summ = []
    for bins in BIN_SUBSETS:
        bins_key = '+'.join(str(b) for b in bins)
        all_policies = [(('+'.join(S)), None) for S in FACTOR_SUBSETS] + POLICIES
        for S_name, pol in all_policies:
            if pol is not None:
                queries = [(k, True) for k in ALL48 if k.endswith('_a10') or k.endswith('_a15')]
            else:
                S = tuple(S_name.split('+'))
                queries = [(k, False) for k in ALL24]
            for qi, is_inter in queries:
                if pol is not None:
                    refs = [r for r in ALL24 if pol(qi, r)]
                else:
                    S_list = S_name.split('+')
                    refs = [r for r in ALL24 if r != qi and
                            all(parse(r)[f] != parse(qi)[f] for f in S_list)]
                vq = get_vector(qi, bins)
                Aq = float(np.linalg.norm(vq))
                uq = vq / Aq if Aq > 0 else vq
                qD = meta[qi]['D']
                ds3 = {r: float(np.linalg.norm(uq - get_vector(r, bins) / float(np.linalg.norm(get_vector(r, bins))))) for r in refs}
                # CORRECT tie logic: pool-wide d_min, not d_same
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
                # positive radius only if m>0 AND not ambiguous
                if m > 0 and not ambiguous:
                    radius = m / 2.0
                    label = 'POSITIVE'
                elif ambiguous:
                    radius = 0.0
                    label = 'AMBIGUOUS_CROSS_D'
                else:
                    radius = 0.0
                    label = 'NO_POSITIVE_TRUE_LABEL_RADIUS'
                rk = '%s|%s|q=%s' % (bins_key, S_name, qi)
                radius_rows.append({
                    'record_key': rk, 'bins': bins_key, 'subset_S': S_name,
                    'query': qi, 'd_same': g17(d_same), 'd_cross': g17(d_cross),
                    'margin_m': g17(m), 'sufficient_radius': g17(radius),
                    'radius_label': label,
                    'tied_set_size': len(tied), 'tied_D_labels': '|'.join(str(d) for d in sorted(tied_Ds)),
                    'scope': 'sufficient lower bound; NOT max tolerable radius'})
            # summary
            rs = [r for r in radius_rows if r['bins'] == bins_key and r['subset_S'] == S_name]
            pos = [float(r['sufficient_radius']) for r in rs if r['radius_label'] == 'POSITIVE']
            radius_summ.append({'record_key': '%s|%s' % (bins_key, S_name),
                                'bins': bins_key, 'subset_or_policy': S_name,
                                'n_queries': len(rs), 'n_positive_radius': len(pos),
                                'n_no_positive': len(rs) - len(pos),
                                'n_ambiguous': sum(1 for r in rs if r['radius_label'] == 'AMBIGUOUS_CROSS_D'),
                                'min_positive_radius': g17(min(pos)) if pos else 'NONE',
                                'median_positive_radius': g17(float(np.median(pos))) if pos else 'NONE',
                                'max_positive_radius': g17(max(pos)) if pos else 'NONE'})
    wcsv(os.path.join(TAB, 'v097_radius_complete1680.csv'),
         list(radius_rows[0].keys()), radius_rows)
    wcsv(os.path.join(TAB, 'v097_radius_summaries70.csv'),
         list(radius_summ[0].keys()), radius_summ)
    # readback
    for name, nexp in (('v097_radius_complete1680.csv', 1680),
                       ('v097_radius_summaries70.csv', 70)):
        rr = list(csv.reader(open(os.path.join(TAB, name), encoding='utf-8', newline='')))
        assert len(rr) - 1 == nexp and all(len(x) == len(rr[0]) for x in rr), name
        assert len({x[0] for x in rr[1:]}) == nexp, name
    n_pos = sum(1 for r in radius_rows if r['radius_label'] == 'POSITIVE')
    n_amb = sum(1 for r in radius_rows if r['radius_label'] == 'AMBIGUOUS_CROSS_D')
    n_neg = sum(1 for r in radius_rows if r['radius_label'] == 'NO_POSITIVE_TRUE_LABEL_RADIUS')
    print('[v097 radius] 1680 rows: POSITIVE=%d, AMBIGUOUS=%d, NO_POSITIVE=%d' % (n_pos, n_amb, n_neg))
    # Compare with v096 (which had incorrect tie logic)
    try:
        v096 = list(csv.DictReader(open(os.path.join(TAB, 'v096_radius_complete1680.csv'),
                                        encoding='utf-8', newline='')))
        v096_pos = sum(1 for r in v096 if r['radius_label'] == 'POSITIVE')
        label_changes = sum(1 for a, b in zip(radius_rows, v096)
                            if a['radius_label'] != b.get('radius_label', ''))
        print('  v096 had %d POSITIVE; v097 has %d; label changes: %d' % (v096_pos, n_pos, label_changes))
    except Exception:
        pass


if __name__ == '__main__':
    main()