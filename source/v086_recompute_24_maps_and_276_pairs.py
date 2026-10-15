# -*- coding: utf-8 -*-
"""v086 Phase C: conditional ranking and comparability qualification for all
276 pairs, recomputed from the ACTUAL 24 double maps and the stored single
maps (pure array algebra; zero new evaluations).

Rank certification logic (per contract 1.2):
  I_ij = [max(0, d^d_ij - b_ij), d^d_ij + b_ij], b_ij = eps_i + eps_j.
  The nearest cross-D candidate is CERTIFIED only if its interval does not
  overlap the interval of ANY other cross-D candidate. Expected per review:
  observed_rank_same=YES but rank_certified=NO (nearest two intervals overlap).
Plus the 24-state nuisance screen: nearest same-D vs nearest cross-D per state
(IN_SAMPLE_GEOMETRY_SCREEN - not a blind-test accuracy)."""
import os, sys, csv, json, itertools
import numpy as np
import h5py
from scipy.io import loadmat

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v083_common import ROOT

GH = os.path.join(ROOT, 'github_handoff')
TAB = os.path.join(GH, 'tables')
NUM = os.path.join(GH, 'numeric')
DYN = os.path.join(ROOT, 'v076_return', 'numeric', 'v076_dynamic_center_corrected.mat')
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


def main():
    f2 = h5py.File(DYN, 'r')
    D_map, singles = {}, {}
    for key in ALL24:
        m = loadmat(os.path.join(NUM, CACHED.get(key, 'C400_double_%s.mat' % key)))
        D_map[key] = np.asarray(m['C400_double'], dtype=np.complex128)
        cm = f2[key]['C400'][:]
        singles[key] = cm['real'].astype(np.float64) + 1j * cm['imag'].astype(np.float64)
    f2.close()
    common = np.ones((41, 41), dtype=bool)
    for key in ALL24:
        mask = np.isfinite(D_map[key].real) & np.isfinite(singles[key].real)
        common &= mask
    # shape maps + epsilons from actual arrays
    ud, us, eps = {}, {}, {}
    for key in ALL24:
        nd = float(np.linalg.norm(np.abs(D_map[key][common])))
        ns = float(np.linalg.norm(np.abs(singles[key][common])))
        ud[key] = np.where(common, np.abs(D_map[key]) / max(nd, 1e-300), 0.0)
        us[key] = np.where(common, np.abs(singles[key]) / max(ns, 1e-300), 0.0)
        eps[key] = float(np.linalg.norm(ud[key] - us[key]))
    # 276 pairs
    rows = []
    cross = []
    for ki, kj in itertools.combinations(ALL24, 2):
        d_d = float(np.linalg.norm((ud[ki] - ud[kj])[common]))
        d_s = float(np.linalg.norm((us[ki] - us[jk := kj])[common]))
        b = eps[ki] + eps[kj]
        cross_ki = ki.split('_')[0] != kj.split('_')[0]
        interval_lo = max(0.0, d_d - b)
        interval_hi = d_d + b
        rows.append({
            'pair_id': '%s__vs__%s' % (ki, kj), 'state_i': ki, 'state_j': kj,
            'pair_class': 'cross_D' if cross_ki else 'same_D',
            'd_shape_single': g17(d_s), 'd_shape_double': g17(d_d),
            'eps_i': g17(eps[ki]), 'eps_j': g17(eps[kj]), 'b_ij': g17(b),
            'abs_delta_d': g17(abs(d_d - d_s)),
            'interval_lo': g17(interval_lo), 'interval_hi': g17(interval_hi),
            'status': 'EVALUATED'})
        if cross_ki:
            cross.append({'pair_id': rows[-1]['pair_id'], 'd_double': d_d, 'd_single': d_s,
                          'b': b, 'lo': interval_lo, 'hi': interval_hi, 'i': ki, 'j': kj})
    cross.sort(key=lambda r: r['d_double'])
    nearest, second = cross[0], cross[1]
    # certification: nearest interval must not overlap ANY other cross-D interval
    overlaps = [(r['pair_id'], r['lo'], r['hi']) for r in cross[1:]
                if not (r['hi'] < nearest['lo'] or r['lo'] > nearest['hi'])]
    rank_certified = len(overlaps) == 0
    observed_same = (abs(nearest['d_double'] - nearest['d_single']) <= nearest['b'])
    for r in rows:
        if r['pair_id'] == nearest['pair_id']:
            r['is_nearest_cross_D'] = 'YES'
            r['overlaps_with'] = ';'.join(o[0] for o in overlaps) if overlaps else 'NONE'
            r['rank_certified_by_intervals'] = 'NO' if not rank_certified else 'YES'
        else:
            r['is_nearest_cross_D'] = ''
            r['overlaps_with'] = ''
            r['rank_certified_by_intervals'] = ''
    fields = list(rows[0].keys())
    with open(os.path.join(TAB, 'v086_276_pair_distance_intervals.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n'); w.writeheader(); w.writerows(rows)

    # nuisance screen: nearest same-D vs nearest cross-D per state
    nuis = []
    for ki in ALL24:
        best_same, best_cross = None, None
        for kj in ALL24:
            if kj == ki:
                continue
            d = float(np.linalg.norm((ud[ki] - ud[kj])[common]))
            same_d = ki.split('_')[0] == kj.split('_')[0]
            if same_d and (best_same is None or d < best_same[0]):
                best_same = (d, kj)
            if (not same_d) and (best_cross is None or d < best_cross[0]):
                best_cross = (d, kj)
        same_first = best_same[0] < best_cross[0]
        nuis.append({
            'case_id': ki, 'nearest_same_D': best_same[1], 'nearest_same_D_dist': g17(best_same[0]),
            'nearest_cross_D': best_cross[1], 'nearest_cross_D_dist': g17(best_cross[0]),
            'nearest_same_D_closer': 'YES' if same_first else 'NO',
            'same_D_source_note': 'nearest same-D states share D, zf, type and differ only in prescribed amplitude a (duplicate-motion-condition geometry)',
            'status': 'IN_SAMPLE_GEOMETRY_SCREEN'})
    with open(os.path.join(TAB, 'v086_24state_same_cross_nuisance.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(nuis[0].keys()), lineterminator='\n'); w.writeheader(); w.writerows(nuis)
    # readback
    for name, nexp in (('v086_276_pair_distance_intervals.csv', 276),
                       ('v086_24state_same_cross_nuisance.csv', 24)):
        with open(os.path.join(TAB, name), 'r', newline='', encoding='utf-8') as f:
            rr = list(csv.reader(f))
        assert len(rr) - 1 == nexp and all(len(x) == len(rr[0]) for x in rr), name
        assert len(set(x[0] for x in rr[1:])) == nexp, name
    n_cross = sum(1 for r in rows if r['pair_class'] == 'cross_D')
    summary = {
        'phase': 'C', 'pairs': 276, 'cross_D': n_cross, 'same_D': 276 - n_cross,
        'observed_rank_same_between_two_paths': 'YES' if observed_same else 'NO',
        'rank_certified_by_reported_triangle_intervals': 'YES' if rank_certified else 'NO',
        'nearest_cross_D_pair': nearest['pair_id'],
        'nearest_d_double': g17(nearest['d_double']),
        'nearest_interval': [g17(nearest['lo']), g17(nearest['hi'])],
        'second_pair': second['pair_id'], 'second_d_double': g17(second['d_double']),
        'second_interval': [g17(second['lo']), g17(second['hi'])],
        'intervals_overlap': 'YES' if overlaps else 'NO',
        'overlapping_candidates_count': len(overlaps),
        'margin_d2_minus_d1': g17(second['d_double'] - nearest['d_double']),
        'b1_plus_b2': g17(nearest['b'] + second['b']),
        'nuisance_24_of_24_same_D_nearest': sum(1 for n in nuis if n['nearest_same_D_closer'] == 'YES'),
        'interpretation': 'continuous-D identifiability NOT established; in-sample geometry screen only'}
    print('[C] summary:', json.dumps(summary)[:800])
    with open(os.path.join(GH, 'logs', 'v086_ranking_certification_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)


if __name__ == '__main__':
    main()
