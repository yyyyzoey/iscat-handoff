# -*- coding: utf-8 -*-
"""v083 Phase E: nuisance-robustness screening of fixed spatial observables,
derived purely by algebra from the 24 EXISTING v076 corrected 41x41 complex
C400 maps (read-only). No new BEM/renders/physical states; no MC; no noise
model; therefore NO detectability, diameter-error or identifiability claims.

Fixed features per state:
  A_center = |Cbin(21,21)|                     (dimensionless)
  A_ROI    = ||Cbin_ROI||_F                    (dimensionless)
  L1_ROI   = sum |Cbin| over ROI               (dimensionless)
  shape    = |Cbin| / || |Cbin| ||_F           (amplitude-eliminated diagnostics)

Pair statistics: 276 pairs = 192 cross-D + 84 same-D. Amplitude features are
confounded by unknown motion amplitude/height; shape is a diagnostic only.
"""
import os, sys, csv, json, itertools
import numpy as np
import h5py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v083_common import ROOT

GH = os.path.join(ROOT, 'github_handoff')
TAB = os.path.join(GH, 'tables')
DYN = os.path.join(ROOT, 'v076_return', 'numeric', 'v076_dynamic_center_corrected.mat')
CASES = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
         for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)]


def g17(x):
    return '%.17g' % x


def main():
    f2 = h5py.File(DYN, 'r')
    feats, shapes = {}, {}
    for key in CASES:
        cm = f2[key]['C400'][:]
        C = cm['real'].astype(np.float64) + 1j * cm['imag'].astype(np.float64)
        mask = np.isfinite(C.real) & np.isfinite(C.imag)
        Cv = C[mask]
        A_center = abs(C[20, 20])
        A_ROI = float(np.linalg.norm(Cv))
        L1 = float(np.sum(np.abs(Cv)))
        nrm = float(np.linalg.norm(np.abs(Cv)))
        if nrm == 0 or not np.isfinite(nrm):
            raise RuntimeError('zero shape norm for %s' % key)
        shape = np.where(mask, np.abs(C) / nrm, 0.0)
        parts = key.split('_')
        feats[key] = {'D': int(parts[0][1:]), 'zf': int(parts[1][2:]), 'type': parts[2],
                      'a': int(parts[3][1:]), 'A_center': A_center, 'A_ROI': A_ROI, 'L1': L1,
                      'mask_fraction': float(mask.sum()) / (41 * 41)}
        shapes[key] = shape
        weak = (feats[key]['type'] == 'M400' and feats[key]['a'] == 5 and feats[key]['D'] <= 60)
        feats[key]['weak_flag'] = 'WEAK_M400_NOT_ROBUST' if weak else ''
    f2.close()
    with open(os.path.join(TAB, 'v083_nuisance_observables24.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['case_id', 'D_nm', 'zf_nm', 'type', 'a_nm', 'A_center', 'A_ROI_Frobenius',
                    'L1_ROI', 'mask_fraction', 'weak_flag', 'units', 'note'])
        for key in CASES:
            ft = feats[key]
            w.writerow([key, ft['D'], ft['zf'], ft['type'], ft['a'], g17(ft['A_center']),
                        g17(ft['A_ROI']), g17(ft['L1']), '%.6f' % ft['mask_fraction'],
                        ft['weak_flag'], 'dimensionless',
                        'area-weighted variants would multiply DEMO pixel area 65^2 nm^2 (simulation units, not experimental)'])

    pairs = []
    min_cross_shape = (1e9, None)
    for ki, kj in itertools.combinations(CASES, 2):
        fi, fj = feats[ki], feats[kj]
        cross_D = fi['D'] != fj['D']
        d_shape = float(np.linalg.norm(shapes[ki] - shapes[kj]))
        row = {
            'pair_id': '%s__vs__%s' % (ki, kj), 'state_i': ki, 'state_j': kj,
            'pair_class': 'cross_D' if cross_D else 'same_D',
            'd_A_center_abs': g17(abs(fi['A_center'] - fj['A_center'])),
            'd_A_ROI_abs': g17(abs(fi['A_ROI'] - fj['A_ROI'])),
            'd_L1_abs': g17(abs(fi['L1'] - fj['L1'])),
            'd_shape_Frobenius': g17(d_shape),
            'ratio_A_ROI': g17(max(fi['A_ROI'], fj['A_ROI']) / max(min(fi['A_ROI'], fj['A_ROI']), 1e-300)),
            'note': 'amplitude features confounded by unknown motion amplitude/height; shape is amplitude-eliminated diagnostic only'}
        pairs.append(row)
        if cross_D and d_shape < min_cross_shape[0]:
            min_cross_shape = (d_shape, row['pair_id'])
    with open(os.path.join(TAB, 'v083_nuisance_feature_pairwise276.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(pairs[0].keys()), lineterminator='\n')
        w.writeheader(); w.writerows(pairs)
    n_cross = sum(1 for p in pairs if p['pair_class'] == 'cross_D')
    n_same = sum(1 for p in pairs if p['pair_class'] == 'same_D')
    # same-D ranges per D for each scalar feature
    sameD_ranges = {}
    for D in (30, 60, 100):
        ks = [k for k in CASES if feats[k]['D'] == D]
        for feat_name in ('A_center', 'A_ROI', 'L1'):
            vals = [feats[k][feat_name] for k in ks]
            sameD_ranges['D%d_%s' % (D, feat_name)] = (min(vals), max(vals))
    summary = {'pairs_total': len(pairs), 'cross_D': n_cross, 'same_D': n_same,
               'min_cross_D_shape_Frobenius': g17(min_cross_shape[0]),
               'min_cross_D_shape_pair': min_cross_shape[1],
               'same_D_feature_ranges': {k: [g17(a), g17(b)] for k, (a, b) in sameD_ranges.items()},
               'boundary': 'discrete-set statistics only; no detectability/diameter-error/identifiability claims'}
    print('[E] summary:', json.dumps(summary)[:600])
    with open(os.path.join(GH, 'logs', 'v083_phase_e_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    # readback
    for name, nexp, key in (('v083_nuisance_observables24.csv', 24, 'case_id'),
                            ('v083_nuisance_feature_pairwise276.csv', 276, 'pair_id')):
        with open(os.path.join(TAB, name), 'r', newline='', encoding='utf-8') as f:
            rr = list(csv.reader(f))
        assert len(rr) - 1 == nexp and all(len(x) == len(rr[0]) for x in rr), name
        assert len(set(x[0] for x in rr[1:])) == nexp, name + ' dup'
    print('[E] readback clean (24 + 276 rows)')


if __name__ == '__main__':
    main()
