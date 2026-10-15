# -*- coding: utf-8 -*-
"""v092 Phase E: fixed-representation comparisons.
  C400_only: v = |C160| (1681-dim)
  three_bin_magnitude: v = concat(|C80|,|C160|,|C320|) (5043-dim)
Endpoint leave-group: 7 subsets x 24 queries x 3 features x 2 repr = 1008.
Intermediate queries: 3 policies x 24 x 3 x 2 repr = 432. Total 1440 + 60 sum.
No weight learning, no per-channel normalisation, no phase alignment."""
import os, sys, csv, json
import numpy as np
from scipy.io import loadmat

GH = os.path.join(r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff')
AN = os.path.join(GH, 'analysis')
NUM = os.path.join(GH, 'numeric')
TAB = os.path.join(GH, 'tables')
BANK = os.path.join(AN, 'bank')
ALL24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
         for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)]
INTER = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
         for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (10, 15)]
CACHED = {'D30_zf450_M400_a5': 'v083_fullROI_double_C400_D30_zf450_M400_a5.mat',
          'D30_zf550_M400_a5': 'v083_fullROI_double_C400_D30_zf550_M400_a5.mat',
          'D60_zf450_M400_a5': 'v083_fullROI_double_C400_D60_zf450_M400_a5.mat',
          'D100_zf450_M200_a20': 'v083_fullROI_double_C400_D100_zf450_M200_a20.mat',
          'D30_zf550_M400_a20': 'v084_double_C400_D30_zf550_M400_a20.mat',
          'D60_zf450_M400_a20': 'v084_double_C400_D60_zf450_M400_a20.mat'}


def g17(x):
    return '%.17g' % x


def parse(k):
    p = k.split('_')
    return {'D': int(p[0][1:]), 'zf': int(p[1][2:]), 'type': p[2], 'a': int(p[3][1:])}


def load_bank(key):
    m = loadmat(os.path.join(BANK, 'v092_bank_%s.mat' % key))
    C = np.asarray(m['C'], dtype=np.complex128)
    mask = np.asarray(m['valid_mask'], dtype=bool)
    C160 = np.abs(C[1][mask])
    C80 = np.abs(C[0][mask])
    C320 = np.abs(C[2][mask])
    return {'C400_only': C160, 'three_bin_magnitude': np.concatenate([C80, C160, C320])}


def main():
    # load all 48 states
    vecs = {}
    for key in ALL24 + INTER:
        fn = CACHED.get(key, 'v092_bank_%s.mat' % key)
        p = os.path.join(NUM, fn) if key in CACHED else os.path.join(BANK, 'v092_bank_%s.mat' % key)
        if key in CACHED:
            m = loadmat(p)
            C = np.asarray(m['C400_double'], dtype=np.complex128)
            mask = np.ones(41 * 41, dtype=bool)
            vecs[key] = {'C400_only': np.abs(C).reshape(-1),
                         'three_bin_magnitude': np.concatenate([np.abs(C).reshape(-1)] * 3)}
        else:
            vecs[key] = load_bank(key)
    # normalise representation vectors to unit norm for shape; keep raw for amplitude
    meta = {k: parse(k) for k in list(ALL24) + list(INTER)}
    FSETS = []
    from itertools import combinations
    for r in (1, 2, 3):
        FSETS.extend(combinations(['a', 'zf', 'type'], r))
    FEATS = [(1, 'ROI_L2_log_ratio'), (2, 'magnitude_pattern_symmetric'),
             (3, 'unit_magnitude_shape')]
    POLICIES = [
        ('unknown_zf_motion', lambda q, r: True, 24),
        ('known_motion', lambda q, r: meta[q]['type'] == meta[r]['type'], 12),
        ('known_motion_zf', lambda q, r: meta[q]['type'] == meta[r]['type'] and meta[q]['zf'] == meta[r]['zf'], 6),
    ]
    comp, summ = [], []
    all_states = ALL24 + INTER

    def dist(fi, vq, vr, Aq, Ar):
        if fi == 1:
            return abs(np.log(Aq) - np.log(Ar))
        if fi == 2:
            return 2.0 * float(np.linalg.norm(vq - vr)) / (Aq + Ar)
        return float(np.linalg.norm(vq / Aq - vr / Ar))

    def query_stats(qi, pool, repr_name, scenario_label):
        vq = vecs[qi][repr_name]; Aq = float(np.linalg.norm(vq))
        out = {}
        for fi, fname in FEATS:
            ds = {rj: dist(fi, vq, vecs[rj][repr_name], Aq, float(np.linalg.norm(vecs[rj][repr_name])))
                  for rj in pool}
            ordered = sorted(pool, key=lambda rj: (ds[rj], rj))
            qD = meta[qi]['D']
            same_D = [r for r in pool if meta[r]['D'] == qD]
            cross_D = [r for r in pool if meta[r]['D'] != qD]
            min_same = min(ds[r] for r in same_D)
            min_cross = min(ds[r] for r in cross_D)
            label = meta[ordered[0]]['D']
            consistent = (label == qD)
            out[fi] = (ordered[0], ordered[1], min_same, min_cross, consistent)
        return out

    # endpoint leave-group: 7 subsets x 2 repr
    for S in FSETS:
        S = list(S)
        for repr_name in ('C400_only', 'three_bin_magnitude'):
            for qi in ALL24:
                refs = [rj for rj in ALL24 if rj != qi and
                        all(meta[rj][f] != meta[qi][f] for f in S)]
                qD = meta[qi]['D']
                res = query_stats(qi, refs, repr_name, '+'.join(S))
                for fi, fname in FEATS:
                    first, second, min_same, min_cross, consistent = res[fi]
                    comp.append({
                        'record_key': '%s|%s|q=%s|%s' % ('+'.join(S), repr_name, qi, fname),
                        'batch': 'endpoint_leavegroup', 'subset_S': '+'.join(S),
                        'representation': repr_name, 'query': qi, 'feature': fname,
                        'reference_pool_size': len(refs),
                        'nearest_candidate': first, 'second_candidate': second,
                        'nearest_label_D': str(meta[first]['D']),
                        'same_D_nearest_dist': g17(min_same), 'cross_D_nearest_dist': g17(min_cross),
                        'min_cross_minus_min_same': g17(min_cross - min_same),
                        'model_label_consistent': 'YES' if consistent else 'NO',
                        'status': 'EVALUATED'})
    # intermediate queries: 3 policies x 2 repr
    for pname, pol, pool_size in POLICIES:
        for repr_name in ('C400_only', 'three_bin_magnitude'):
            for qi in INTER:
                refs = [rj for rj in ALL24 if rj != qi and pol(qi, rj)]
                qD = meta[qi]['D']
                res = query_stats(qi, refs, repr_name, pname)
                for fi, fname in FEATS:
                    first, second, min_same, min_cross, consistent = res[fi]
                    comp.append({
                        'record_key': '%s|%s|q=%s|%s' % (pname, repr_name, qi, fname),
                        'batch': 'intermediate_query', 'policy': pname,
                        'representation': repr_name, 'query': qi, 'feature': fname,
                        'reference_pool_size': len(refs),
                        'nearest_candidate': first, 'second_candidate': second,
                        'nearest_label_D': str(meta[first]['D']),
                        'same_D_nearest_dist': g17(min_same), 'cross_D_nearest_dist': g17(min_cross),
                        'min_cross_minus_min_same': g17(min_cross - min_same),
                        'model_label_consistent': 'YES' if consistent else 'NO',
                        'status': 'EVALUATED'})
    # summaries (60)
    for key in sorted({(r['batch'], r.get('subset_S', r.get('policy', '')),
                        r['representation'], r['feature']) for r in comp}):
        batch, S, repr_name, fname = key
        rs = [r for r in comp if r['batch'] == batch and
              r.get('subset_S', r.get('policy', '')) == S and
              r['representation'] == repr_name and r['feature'] == fname]
        summ.append({'record_key': '%s|%s|%s|%s' % (batch, S, repr_name, fname),
                     'batch': batch, 'subset_or_policy': S, 'representation': repr_name,
                     'feature': fname, 'n_queries': len(rs),
                     'consistent_count': sum(1 for r in rs if r['model_label_consistent'] == 'YES'),
                     'inconsistent_count': sum(1 for r in rs if r['model_label_consistent'] == 'NO'),
                     'reading': 'in-sample geometry screen count; NOT accuracy/detectability'})
    with open(os.path.join(AN, 'v092_comparisons1440.csv'), 'w', newline='', encoding='utf-8') as f:
        all_f = ['record_key'] + sorted({k for r in comp for k in r if k != 'record_key'})
        w = csv.DictWriter(f, fieldnames=all_f, lineterminator='\n')
        w.writeheader(); w.writerows(comp)
    with open(os.path.join(AN, 'v092_summaries60.csv'), 'w', newline='', encoding='utf-8') as f:
        all_s = ['record_key'] + sorted({k for r in summ for k in r if k != 'record_key'})
        w = csv.DictWriter(f, fieldnames=all_s, lineterminator='\n')
        w.writeheader(); w.writerows(summ)
    # readback
    for name, nexp in (('v092_comparisons1440.csv', 1440), ('v092_summaries60.csv', 60)):
        with open(os.path.join(AN, name), 'r', newline='', encoding='utf-8') as f:
            rr = list(csv.reader(f))
        assert len(rr) - 1 == nexp and all(len(x) == len(rr[0]) for x in rr), name
        assert len({x[0] for x in rr[1:]}) == nexp, name
    print('[E] summary:', json.dumps({'comparisons': len(comp), 'summaries': len(summ)}))
    # key findings
    for s in summ:
        if s['feature'] == 'magnitude_pattern_symmetric':
            print('  %s %s %s: consistent %d/%d' % (s['batch'], s['subset_or_policy'],
                                                    s['representation'], s['consistent_count'], s['n_queries']))


if __name__ == '__main__':
    main()
