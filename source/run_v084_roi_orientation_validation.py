# -*- coding: utf-8 -*-
"""v084 Phase B: orientation / pixel-identity validation of the 4 existing
v083 double-precision complex C400 maps vs the stored v076 single-precision
maps. Zero new time-domain evaluations (pure file/array comparison).

Orientation logic: both maps are read in h5py axis order (axis1 = MATLAB col,
axis2 = MATLAB row) as established by the v084 Phase A asymmetric-pixel
sentinels (rows 21/26/16 at col 1). The decisive numerical test is the
anisotropy ratio: if a map is anisotropic (norm(C - C.T)/norm(C) >> map-level
double-vs-single spread), then direct comparison matching while transposed
comparison fails confirms the shared orientation; the transposed comparison
is retained as the negative result.
MATLAB extract_fft_v073 cross-check: NOT_EXECUTED (licence/process safety)."""
import os, sys, csv, json
import numpy as np
import h5py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v083_common import ROOT

GH = os.path.join(ROOT, 'github_handoff')
TAB = os.path.join(GH, 'tables')
NUM = os.path.join(GH, 'numeric')
DYN = os.path.join(ROOT, 'v076_return', 'numeric', 'v076_dynamic_center_corrected.mat')
CONDITIONS = ['D30_zf450_M400_a5', 'D30_zf550_M400_a5', 'D60_zf450_M400_a5', 'D100_zf450_M200_a20']
PROBE_PIXELS_H5 = [(20, 0), (0, 20), (10, 5), (5, 10)]  # asymmetric, non-centre


def g17(x):
    return '%.17g' % x


def main():
    f2 = h5py.File(DYN, 'r')
    rows = []
    for key in CONDITIONS:
        from scipy.io import loadmat
        fm = loadmat(os.path.join(NUM, 'v083_fullROI_double_C400_%s.mat' % key))
        Cd = fm['C400_double']
        valid_d = np.array(fm['valid_mask'], dtype=bool)
        cm = f2[key]['C400'][:]
        Cs = cm['real'].astype(np.float64) + 1j * cm['imag'].astype(np.float64)
        common = valid_d & np.isfinite(Cs.real) & np.isfinite(Cs.imag)
        d = (Cd - Cs)[common]
        rF_direct = float(np.linalg.norm(d) / max(np.linalg.norm(Cs[common]), 1e-300))
        dt = (Cd - Cs.T)[common]  # negative control: transposed stored map
        rF_transposed = float(np.linalg.norm(dt) / max(np.linalg.norm(Cs.T[common]), 1e-300))
        aniso_d = float(np.linalg.norm((Cd - Cd.T)[common]) / max(np.linalg.norm(Cd[common]), 1e-300))
        aniso_s = float(np.linalg.norm((Cs - Cs.T)[common]) / max(np.linalg.norm(Cs[common]), 1e-300))
        decisive = aniso_s > max(10.0 * rF_direct, 1e-3)
        probes = []
        for (i, j) in PROBE_PIXELS_H5:
            probes.append('h5(%d,%d) double=(%.6g%+.6gj) single=(%.6g%+.6gj) |d|=%.3g' % (
                i, j, Cd[i, j].real, Cd[i, j].imag, Cs[i, j].real, Cs[i, j].imag,
                abs(Cd[i, j] - Cs[i, j])))
        rows.append({
            'case_id': key,
            'orientation_convention': 'both maps h5py (axis1=MATLAB col, axis2=MATLAB row); established by v084 Phase A sentinels rows 21/26/16 at col 1',
            'valid_mask_definition': 'v083 frozen Imean floor (0.01*median positive) AND both maps finite; intersection',
            'n_common_pixels': int(common.sum()),
            'anisotropy_single': g17(aniso_s), 'anisotropy_double': g17(aniso_d),
            'rF_direct_correct_orientation': g17(rF_direct),
            'rF_transposed_negative_control': g17(rF_transposed),
            'orientation_decisive': 'YES' if decisive else 'WEAK_MAP_LOW_DISCRIMINATION',
            'probe_pixels': ' | '.join(probes),
            'rF_v083_historical_frobenius_rel': 'see v083_fullROI_precision4.csv (preserved, not overwritten)',
            'status': 'ORIENTATION_CONFIRMED' if (rF_direct < rF_transposed and decisive) else 'ORIENTATION_WEAK',
            'matlab_fft_crosscheck': 'NOT_EXECUTED (licence/process safety); Python DFT/FFT internal cross-check remains from v082/v083',
            'note': 'map-level agreement does NOT validate the weak centre magnitude: NO_NEAR_ZERO_RELATIVE_CONCLUSION retained'})
    f2.close()
    fields = list(rows[0].keys())
    with open(os.path.join(TAB, 'v084_roi_orientation4.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n'); w.writeheader(); w.writerows(rows)
    with open(os.path.join(TAB, 'v084_roi_orientation4.csv'), 'r', newline='', encoding='utf-8') as f:
        rr = list(csv.reader(f))
    assert len(rr) - 1 == 4 and all(len(x) == len(rr[0]) for x in rr)
    for r in rows:
        print('[B] %s: aniso_single=%s rF_direct=%s rF_transposed=%s -> %s' % (
            r['case_id'], r['anisotropy_single'], r['rF_direct_correct_orientation'],
            r['rF_transposed_negative_control'], r['status']))


if __name__ == '__main__':
    main()

