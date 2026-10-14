# -*- coding: utf-8 -*-
"""v085 Phase D: numerical-path perturbation of the 24-state spatial features
and all 276 pairs (192 cross-D + 84 same-D), pure algebra on the unified
double-precision map set and the stored single-precision maps.

- Common mask: global intersection of the 24 double-map masks (reported);
  no free translation/gain/phase registration.
- Features: A_center=|C400[20,20]|, A_ROI=||C||_F, L1_ROI=sum|C|, shape
  u_i(p)=|C_i(p)|/|| |C_i| ||_2 on the common mask (amplitude-eliminated
  diagnostic only).
- Path error epsilon_i = ||u_i^d - u_i^s||_2; for every pair the triangle
  bound |d^d - d^s| <= epsilon_i + epsilon_j and its utilisation are reported.
- NO detectability / diameter-error / identifiability claims.
"""
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


def g17(x):
    return '%.17g' % x


def main():
    f2 = h5py.File(DYN, 'r')
    D_map = {}
    singles = {}
    mask_info = {}
    for key in ALL24:
        m = loadmat(os.path.join(NUM, 'v085_double_maps24_status.csv' and _mapfile(key)))
        Cd = m['C400_double']; vd = np.array(m['valid_mask'], dtype=bool)
        cm = f2[key]['C400'][:]
        Cs = cm['real'].astype(np.float64) + 1j * cm['imag'].astype(np.float64)
        D_map[key] = (Cd, vd)
        singles[key] = Cs
        mask_info[key] = int(vd.sum())
    f2.close()
    # global common mask
    common = np.ones((41, 41), dtype=bool)
    for key in ALL24:
        common &= D_map[key][1] & np.isfinite(singles[key].real) & np.isfinite(singles[key].imag)
    n_common = int(common.sum())

    eps = {}
    feats = {}
    near_zero = {}
    for key in ALL24:
        Cd, vd = D_map[key]
        Cs = singles[key]
        nd = float(np.linalg.norm(np.abs(Cd[common])))
        ns = float(np.linalg.norm(np.abs(Cs[common])))
        if nd == 0 or ns == 0:
            raise RuntimeError('zero norm state %s cannot be normalised' % key)
        ud = np.where(common, np.abs(Cd) / nd, 0.0)
        us = np.where(common, np.abs(Cs) / ns, 0.0)
        eps[key] = float(np.linalg.norm(ud - us))
        feats[key] = {
            'A_center_double': abs(Cd[20, 20]), 'A_center_single': abs(Cs[20, 20]),
            'A_ROI_double': float(np.linalg.norm(Cd[common])), 'A_ROI_single': float(np.linalg.norm(Cs[common])),
            'L1_double': float(np.sum(np.abs(Cd[common]))), 'L1_single': float(np.sum(np.abs(Cs[common])))}
        near_zero[key] = feats[key]['A_center_double'] < 1e-7

    rows = []
    for key in ALL24:
        ft = feats[key]
        rows.append({
            'case_id': key, 'epsilon_shape_path': g17(eps[key]),
            'A_center_double': g17(ft['A_center_double']), 'A_center_single': g17(ft['A_center_single']),
            'A_center_absdiff': g17(abs(ft['A_center_double'] - ft['A_center_single'])),
            'A_ROI_double': g17(ft['A_ROI_double']), 'A_ROI_single': g17(ft['A_ROI_single']),
            'A_ROI_absdiff': g17(abs(ft['A_ROI_double'] - ft['A_ROI_single'])),
            'L1_ROI_double': g17(ft['L1_double']), 'L1_ROI_single': g17(ft['L1_single']),
            'near_zero_flag': 'NEAR_ZERO' if near_zero[key] else '',
            'status': 'EVALUATED'})
    with open(os.path.join(TAB, 'v085_shape_numerical_delta24.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator='\n'); w.writeheader(); w.writerows(rows)

    pairs = []
    cross_dists = []
    for ki, kj in itertools.combinations(ALL24, 2):
        Cd_i, _ = D_map[ki]; Cd_j, _ = D_map[kj]
        Cs_i, Cs_j = singles[ki], singles[kj]
        ud_i = np.where(common, np.abs(Cd_i), 0.0); ud_i = ud_i / max(np.linalg.norm(ud_i[common]), 1e-300)
        ud_j = np.where(common, np.abs(Cd_j), 0.0); ud_j = ud_j / max(np.linalg.norm(ud_j[common]), 1e-300)
        us_i = np.where(common, np.abs(Cs_i), 0.0); us_i = us_i / max(np.linalg.norm(us_i[common]), 1e-300)
        us_j = np.where(common, np.abs(Cs_j), 0.0); us_j = us_j / max(np.linalg.norm(us_j[common]), 1e-300)
        d_d = float(np.linalg.norm((ud_i - ud_j)[common]))
        d_s = float(np.linalg.norm((us_i - us_j)[common]))
        bound = eps[ki] + eps[kj]
        delta = abs(d_d - d_s)
        parts_i = ki.split('_'); parts_j = kj.split('_')
        cross = parts_i[0] != parts_j[0]
        pairs.append({
            'pair_id': '%s__vs__%s' % (ki, kj), 'state_i': ki, 'state_j': kj,
            'pair_class': 'cross_D' if cross else 'same_D',
            'd_shape_single': g17(d_s), 'd_shape_double': g17(d_d),
            'abs_delta_d': g17(delta), 'triangle_bound_eps_i_plus_eps_j': g17(bound),
            'bound_utilisation': g17(delta / max(bound, 1e-300)),
            'bound_holds': 'YES' if delta <= bound + 1e-15 else 'NO',
            'status': 'EVALUATED'})
        if cross:
            cross_dists.append((d_d, d_s, ki, kj))
    with open(os.path.join(TAB, 'v085_pairwise_276_stability.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(pairs[0].keys()), lineterminator='\n'); w.writeheader(); w.writerows(pairs)

    # nearest cross-D pair ranking under both precisions
    by_d = sorted(cross_dists)
    nearest_d = by_d[0]
    margin = by_d[1][0] - by_d[0][0]
    same_D_max = max(d for d, _, _, _ in pairs if False) if False else None
    nuis = {
        'n_common_mask_pixels': n_common,
        'per_state_mask_pixels_min': min(mask_info.values()),
        'per_state_mask_pixels_max': max(mask_info.values()),
        'epsilon_min': g17(min(eps.values())), 'epsilon_max': g17(max(eps.values())),
        'nearest_cross_D_pair_double': '%s vs %s' % (nearest_d[2], nearest_d[3]),
        'nearest_cross_D_d_double': g17(nearest_d[0]),
        'nearest_cross_D_d_single': g17(nearest_d[1]),
        'nearest_cross_D_changed_vs_single': 'YES' if (by_d[0][2], by_d[0][3]) != min(
            ((d_s, i, j) for d_s, _, i, j in cross_dists))[1:] else 'NO',
        'margin_to_second_nearest_double': g17(margin),
        'boundary': 'triangle bound = numerical-path conservative bound for THIS algorithm/cache; not physical model error, instrument noise, or diameter CI',
    }
    # same-D vs cross-D separation summary
    d_all = sorted((float(p['d_shape_double']), p['pair_class'], p['pair_id']) for p in pairs)
    nuis['min_same_D_d_double'] = g17(min(d for d, c, _ in d_all if c == 'same_D'))
    nuis['max_cross_D_d_double'] = g17(max(d for d, c, _ in d_all if c == 'cross_D'))
    with open(os.path.join(TAB, 'v085_feature_nuisance_summary.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(['metric', 'value']); 
        for k, v in nuis.items():
            w.writerow([k, v])
    # readback
    for name, nexp in (('v085_shape_numerical_delta24.csv', 24),
                       ('v085_pairwise_276_stability.csv', 276)):
        with open(os.path.join(TAB, name), 'r', newline='', encoding='utf-8') as f:
            rr = list(csv.reader(f))
        assert len(rr) - 1 == nexp and all(len(x) == len(rr[0]) for x in rr), name
        assert len(set(x[0] for x in rr[1:])) == nexp, name
    n_cross = sum(1 for p in pairs if p['pair_class'] == 'cross_D')
    n_same = sum(1 for p in pairs if p['pair_class'] == 'same_D')
    assert (n_cross, n_same) == (192, 84)
    summary = {'phase': 'D', 'pairs': 276, 'cross_D': n_cross, 'same_D': n_same,
               'common_mask_pixels': n_common,
               'eps_range': [min(eps.values()), max(eps.values())],
               'nearest_cross_D_double': nuis['nearest_cross_D_d_double'],
               'nearest_pair': nuis['nearest_cross_D_pair_double'],
               'nearest_changed_vs_single': nuis['nearest_cross_D_changed_vs_single'],
               'margin_to_second': nuis['margin_to_second_nearest_double'],
               'min_same_D': nuis['min_same_D_d_double'], 'max_cross_D': nuis['max_cross_D_d_double']}
    print('[D] summary:', json.dumps(summary))
    with open(os.path.join(GH, 'logs', 'v085_phase_d_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)


def _mapfile(key):
    cached = {'D30_zf450_M400_a5': 'v083_fullROI_double_C400_D30_zf450_M400_a5.mat',
              'D30_zf550_M400_a5': 'v083_fullROI_double_C400_D30_zf550_M400_a5.mat',
              'D60_zf450_M400_a5': 'v083_fullROI_double_C400_D60_zf450_M400_a5.mat',
              'D100_zf450_M200_a20': 'v083_fullROI_double_C400_D100_zf450_M200_a20.mat',
              'D30_zf550_M400_a20': 'v084_double_C400_D30_zf550_M400_a20.mat',
              'D60_zf450_M400_a20': 'v084_double_C400_D60_zf450_M400_a20.mat'}
    return cached.get(key, 'C400_double_%s.mat' % key)


if __name__ == '__main__':
    main()
