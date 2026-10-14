# -*- coding: utf-8 -*-
"""v082 Phase C: weak M400 centre-signal finite-precision diagnostics.

Six fixed old conditions (all M400, a=5 nm, D in {30,60,100} x zf in {450,550}):
pure post-processing of the cached v074 anchor fields, corrected centre ROI.
Paths per condition:
  P1 field_first  - interpolate complex field first, then intensity (float64)
  P2 single_accum - quadratic-form intensity accumulated in float32 (v076 path)
  P3 double_accum - quadratic-form intensity in float64
  P4 fft_vs_dft   - numpy FFT vs explicit DFT consistency on P3 series
Near-zero signals: absolute dC is the meaningful metric; relative error is
flagged meaningful only when |C| exceeds the path-to-path noise scale.
Zero BEM, zero new renders. tau=0 (no exposure integration) on this branch.
"""
import os, sys, csv
import numpy as np
import h5py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v082_qf_common import (ROOT, N, FS, K0,
                            load_center_blocks, qf_coefficients, qf_series,
                            field_first_series, cbin)

GH = os.path.join(ROOT, 'github_handoff')
TAB = os.path.join(GH, 'tables')
DYN = os.path.join(ROOT, 'v076_return', 'numeric', 'v076_dynamic_center_corrected.mat')
CONDITIONS = [('D30', 450), ('D30', 550), ('D60', 450), ('D60', 550), ('D100', 450), ('D100', 550)]


def qr_fit_C400(series):
    """400 Hz complex fit amplitude via intercept-first full-rank basis."""
    tj = np.arange(N) / FS
    B = np.ones((N, 9))
    for h, f in enumerate([400, 800, 1200, 1600]):
        B[:, 1 + 2 * h] = np.cos(2 * np.pi * f * tj)
        B[:, 2 + 2 * h] = np.sin(2 * np.pi * f * tj)
    Ic = series - series.mean()
    coef, _, _, _ = np.linalg.lstsq(B, Ic, rcond=None)
    A400 = complex(coef[1], -coef[2])
    resid = Ic - B @ coef
    return A400 / series.mean(), float(np.sqrt(np.mean(resid ** 2)))


def main():
    rows = []
    f2 = h5py.File(DYN, 'r')
    for D_s, zf in CONDITIONS:
        D = int(D_s[1:])
        key = 'D%d_zf%d_M400_a5' % (D, zf)
        Es, Eref = load_center_blocks(D, zf)
        Lm, Dm_, Qm, Iref = qf_coefficients(Es, Eref)
        tj = np.arange(N) / FS
        xt = 5.0 * np.cos(2 * np.pi * 400.0 * tj)
        s_field = field_first_series(xt, Es, Eref)
        s_single = qf_series(xt, Lm, Dm_, Qm, Iref, dtype=np.float32)
        s_double = qf_series(xt, Lm, Dm_, Qm, Iref, dtype=np.float64)
        paths = [('field_first_double', s_field), ('qf_single_accum', s_single),
                 ('qf_double_accum', s_double)]
        Cs = {name: cbin(s)[0] for name, s in paths}
        Imeans = {name: float(np.mean(s)) for name, s in paths}
        # FFT vs explicit DFT on the double path
        sd = paths[2][1] - np.mean(paths[2][1])
        X_fft = np.fft.fft(sd)[K0]
        e = np.exp(-2j * np.pi * K0 * np.arange(N) / N)
        X_dft = complex(np.sum(sd * e))
        fft_dft_rel = abs(X_fft - X_dft) / max(abs(X_dft), 1e-300)
        # external references
        absCenter = float(np.array(f2[key]['absCenter']).flatten()[0])
        with h5py.File(os.path.join(GH, 'numeric', 'v076_center_roi_harmonic_small_examples.mat'), 'r') as f1:
            s_small = np.array(f1[key]['series']).flatten().astype(np.float64)
        C_small, _ = cbin(s_small)
        # noise scale: max path-to-path absolute dC
        ref = abs(Cs['field_first_double'])
        scale = max(abs(Cs['field_first_double'] - Cs['qf_single_accum']),
                    abs(Cs['field_first_double'] - Cs['qf_double_accum']),
                    abs(Cs['qf_single_accum'] - Cs['qf_double_accum']))
        for name, s in paths:
            C = Cs[name]
            d_abs = abs(C - Cs['field_first_double'])
            rel_meaningful = ref > 10.0 * scale if scale > 0 else True
            Cfit, rmsR = qr_fit_C400(s)
            rows.append({
                'case_id': key, 'path': name, 'absC400_center': '%.17g' % abs(C),
                'C400_Re': '%.17g' % C.real, 'C400_Im': '%.17g' % C.imag,
                'C400fit_abs': '%.17g' % abs(Cfit), 'C400fit_phase_rad': '%.17g' % np.angle(C),
                'Imean': '%.17g' % Imeans[name], 'fit_residual_RMS': '%.17g' % rmsR,
                'delta_vs_field_first_abs': '%.17g' % d_abs,
                'delta_vs_field_first_rel': '%.17g' % (d_abs / max(ref, 1e-300)),
                'relative_error_meaningful': 'YES' if (rel_meaningful and ref > 0) else 'NO_NEAR_ZERO_SIGNAL',
                'path_noise_scale_absC': '%.17g' % scale,
                'fft_vs_direct_dft_rel': '%.17g' % fft_dft_rel if name == 'qf_double_accum' else 'NA',
                'v076_map_absCenter_ref': '%.17g' % absCenter,
                'v076_small_series_Cbin_ref': '%.17g' % abs(C_small),
                'tau_s': '0', 'status': 'DIAGNOSTIC',
                'note': 'prescribed M400 a5 motion; SYNTHETIC trajectory; zero new renders/BEM'})
    f2.close()
    fields = list(rows[0].keys())
    out = os.path.join(TAB, 'v082_weak_center_precision6.csv')
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    # independent readback
    with open(out, 'r', newline='', encoding='utf-8') as f:
        rr = list(csv.reader(f))
    assert len(rr) - 1 == 18, 'expected 18 rows (6 cases x 3 paths)'
    assert all(len(r) == len(rr[0]) for r in rr)
    print('[C] weak centre precision: 18 rows written; sample:')
    for r in rows[::3]:
        print('  %s %s |C|=%s d1st=%s noise=%s' % (r['case_id'], r['path'],
              r['absC400_center'], r['delta_vs_field_first_abs'], r['path_noise_scale_absC']))


if __name__ == '__main__':
    main()

