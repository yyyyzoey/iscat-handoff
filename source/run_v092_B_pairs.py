# -*- coding: utf-8 -*-
"""v092 Phase B: 60 same-factor pairs + 7 non-empty factor-subset leave-group
extension (504 rows), pure algebra on the 24 baseline maps."""
import os, sys, csv, json, itertools
import numpy as np
from scipy.io import loadmat

GH = os.path.join(r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff')
TAB = os.path.join(GH, 'tables')
ALL24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
         for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)]
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


def main():
    v = {}
    for key in ALL24:
        fn = CACHED.get(key, 'C400_double_%s.mat' % key)
        m = loadmat(os.path.join(GH, 'numeric', fn))
        v[key] = np.abs(np.asarray(m['C400_double'], dtype=np.complex128)).reshape(-1)
    meta = {k: parse(k) for k in ALL24}

    # ---- 60 same-factor pairs ----
    pair_rows = []
    factors = [('a', lambda m: m['a']), ('zf', lambda m: m['zf']),
               ('type', lambda m: m['type']), ('D', lambda m: m['D'])]
    seen = set()
    for fname, getter in factors:
        for i, j in itertools.combinations(ALL24, 2):
            mi, mj = meta[i], meta[j]
            diff_keys = [k for k in ('D', 'zf', 'type', 'a') if mi[k] != mj[k]]
            if diff_keys != [fname]:
                continue
            pk = tuple(sorted([i, j]))
            if pk in seen:
                continue
            seen.add(pk)
            vi, vj = v[i], v[j]
            Ai, Aj = float(np.linalg.norm(vi)), float(np.linalg.norm(vj))
            d_shape = float(np.linalg.norm(vi / Ai - vj / Aj))
            d_sym = 2.0 * float(np.linalg.norm(vi - vj)) / (Ai + Aj)  # symmetric normalized distance
            # algebraic decomposition: d_sym^2 = 4(Ai-Aj)^2/(Ai+Aj)^2 + [4AiAj/(Ai+Aj)^2] d_shape^2
            amp_term = 4 * (Ai - Aj) ** 2 / (Ai + Aj) ** 2
            shape_coeff = 4 * Ai * Aj / (Ai + Aj) ** 2
            resid = d_sym ** 2 - (amp_term + shape_coeff * d_shape ** 2)
            pair_rows.append({
                'record_key': '%s__vs__%s' % tuple(sorted([i, j])),
                'factor_changed': fname, 'state_i': i, 'state_j': j,
                'A_i': g17(Ai), 'A_j': g17(Aj),
                'd_sym_symmetric': g17(d_sym),
                'd_sym_raw_L2': g17(float(np.linalg.norm(vi - vj))),
                'amp_term': g17(amp_term), 'shape_coeff': g17(shape_coeff),
                'd_shape_term_contrib': g17(shape_coeff * d_shape ** 2),
                'd_shape': g17(d_shape),
                'decomposition_residual': g17(resid),
                'decomposition_ok': 'YES' if abs(resid) < 1e-12 else 'FAIL',
                'note': 'algebraic identity, not a causal contribution percentage'})
    with open(os.path.join(TAB, 'v092_same_factor_pairs60.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(pair_rows[0].keys()), lineterminator='\n')
        w.writeheader(); w.writerows(pair_rows)

    # ---- 7 non-empty factor-subset leave-group (504 rows) ----
    from itertools import combinations as comb
    subsets = []
    for r in (1, 2, 3):
        subsets.extend(comb(['a', 'zf', 'type'], r))
    lg_rows = []
    for S in subsets:
        S = list(S)
        for qi in ALL24:
            refs = [rj for rj in ALL24 if rj != qi and
                    all(meta[rj][f] != meta[qi][f] for f in S)]
            # per-D balance check (informational)
            fq, fr = v[qi], None
            Aq = float(np.linalg.norm(fq))
            dists = {}
            for rj in refs:
                vr = v[rj]
                Ar = float(np.linalg.norm(vr))
                dists[rj] = (abs(np.log(Aq) - np.log(Ar)),
                             2.0 * float(np.linalg.norm(fq - vr)) / (Aq + Ar),
                             float(np.linalg.norm(fq / Aq - vr / Ar)))
            for fi, fname in ((1, 'ROI_L2_log_ratio'), (2, 'magnitude_pattern_symmetric'),
                              (3, 'unit_magnitude_shape')):
                ordered = sorted(refs, key=lambda rj: (dists[rj][fi - 1], rj))
                eps64 = np.finfo(np.float64).eps
                dmin = dists[ordered[0]][fi - 1]
                tied = [rj for rj in ordered if dists[rj][fi - 1] <= dmin + 64 * eps64 * max(1.0, abs(dmin))]
                tied_Ds = {meta[rj]['D'] for rj in tied}
                qD = meta[qi]['D']
                ambiguous = len(tied_Ds) > 1
                label = meta[ordered[0]]['D']
                consistent = (not ambiguous) and (label == qD)
                lg_rows.append({
                    'record_key': '%s|q=%s|%s' % ('+'.join(S), qi, fname),
                    'subset_S': '+'.join(S), 'query': qi, 'feature': fname,
                    'reference_pool': '|'.join(sorted(refs)), 'pool_size': len(refs),
                    'nearest_candidate': ordered[0], 'nearest_dist': g17(dmin),
                    'second_candidate': ordered[1], 'second_dist': g17(dists[ordered[1]][fi - 1]),
                    'tied_set_size': len(tied),
                    'tied_set_D_labels': '|'.join(str(d) for d in sorted(tied_Ds)),
                    'tie_across_D': 'YES' if ambiguous else 'NO',
                    'model_label_consistent': ('YES' if consistent else
                                               'AMBIGUOUS_CROSS_D' if ambiguous else 'NO'),
                    'status': 'EVALUATED'})
    with open(os.path.join(TAB, 'v092_leavegroup7_504.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(lg_rows[0].keys()), lineterminator='\n')
        w.writeheader(); w.writerows(lg_rows)
    # readback
    for name, nexp in (('v092_same_factor_pairs60.csv', 60), ('v092_leavegroup7_504.csv', 504)):
        with open(os.path.join(TAB, name), 'r', newline='', encoding='utf-8') as f:
            rr = list(csv.reader(f))
        assert len(rr) - 1 == nexp and all(len(x) == len(rr[0]) for x in rr), name
        assert len({x[0] for x in rr[1:]}) == nexp, name
    n_decomp_fail = sum(1 for r in pair_rows if r['decomposition_ok'] != 'YES')
    print('[B] summary:', json.dumps({'pairs': len(pair_rows), 'decomposition_fail': n_decomp_fail,
                                      'leavegroup7_rows': len(lg_rows)}))


if __name__ == '__main__':
    main()
