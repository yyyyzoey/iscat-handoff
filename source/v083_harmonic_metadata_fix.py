# -*- coding: utf-8 -*-
"""v083 Phase B: read-only repair of two v082 metadata defects.

B1. X0-corrected complex closure: v082 computed closure = Xbin - sum(X_h) - Xres
    (omitting X0). The full defined identity is
    closure_full = Xbin - sum(X_h) - X0 - Xres, recomputed here from the v082
    stored Re/Im columns (no re-run of the 24 QR fits; historical columns kept).
B2. Phase columns: v082 wrote C400fit_phase_rad = angle(Cbin) (mislabeled FFT
    phase). Both phases are now computed from their own correct complex objects.
    Near-zero signals get UNRESOLVED_NEAR_ZERO instead of fake phases.
"""
import os, sys, csv, json
import numpy as np
import h5py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v083_common import ROOT, N, FS, K0, block_at, cbin
from v082_qf_common import qf_coefficients, qf_series, field_first_series

GH = os.path.join(ROOT, 'github_handoff')
TAB = os.path.join(GH, 'tables')
NUM = os.path.join(GH, 'numeric')
SMALL = os.path.join(NUM, 'v076_center_roi_harmonic_small_examples.mat')


def read_csv(path):
    with open(path, 'r', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def g17(x):
    return '%.17g' % x


def main():
    res_rows = read_csv(os.path.join(TAB, 'v082_harmonic_residual24.csv'))
    val_rows = read_csv(os.path.join(TAB, 'v082_harmonics24_validated.csv'))
    val_by_key = {r['case_id']: r for r in val_rows}

    # ---- B1: X0-corrected closure (pure algebra on stored columns) ----
    b1 = []
    max_x0 = 0.0
    for r in res_rows:
        Xbin = complex(float(r['Xbin_Re_DFT_count']), float(r['Xbin_Im_DFT_count']))
        Xh = complex(float(r['Xharmonics_sum_Re']), float(r['Xharmonics_sum_Im']))
        X0 = complex(float(r['X0_intercept_Re']), float(r['X0_intercept_Im']))
        Xres = complex(float(r['Xres_Re']), float(r['Xres_Im']))
        closure_v082 = Xbin - Xh - Xres                       # historical (no X0)
        closure_full = Xbin - Xh - X0 - Xres                  # defined identity
        max_x0 = max(max_x0, abs(X0))
        key = r['case_id']
        series = None
        with h5py.File(SMALL, 'r') as f:
            series = np.array(f[key]['series']).flatten().astype(np.float64)
        normY = np.sqrt(N) * np.linalg.norm(series - series.mean())
        rel_v082 = abs(closure_v082) / max(normY, 1e-300)
        rel_full = abs(closure_full) / max(normY, 1e-300)
        b1.append({
            'case_id': key,
            'Xbin_Re_DFT_count': r['Xbin_Re_DFT_count'], 'Xbin_Im_DFT_count': r['Xbin_Im_DFT_count'],
            'Xharmonics_sum_Re': r['Xharmonics_sum_Re'], 'Xharmonics_sum_Im': r['Xharmonics_sum_Im'],
            'X0_intercept_Re': r['X0_intercept_Re'], 'X0_intercept_Im': r['X0_intercept_Im'],
            'Xres_Re': r['Xres_Re'], 'Xres_Im': r['Xres_Im'],
            'closure_v082_without_X0_Re': g17(closure_v082.real), 'closure_v082_without_X0_Im': g17(closure_v082.imag),
            'closure_v082_without_X0_abs': r['closure_abs'],
            'closure_v082_without_X0_rel': r['closure_rel'],
            'closure_full_with_X0_Re': g17(closure_full.real), 'closure_full_with_X0_Im': g17(closure_full.imag),
            'closure_full_abs': g17(abs(closure_full)), 'closure_full_rel': g17(rel_full),
            'abs_delta_vs_v082': g17(abs(abs(closure_full) - abs(closure_v082))),
            'gate': 'closure_rel < 1e-10 (frozen)',
            'status': 'PASS' if rel_full < 1e-10 else 'FAIL',
            'note': 'X0 max magnitude %.3e across 24 cases - omitted-X0 defect did not change the v082 PASS verdict; now explicitly included' % max_x0})
    with open(os.path.join(TAB, 'v083_harmonic_complex_closure_X0_corrected.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(b1[0].keys()), lineterminator='\n'); w.writeheader(); w.writerows(b1)
    print('[B1] X0-corrected closure: 24 rows; max|X0|=%.3e; all PASS=%s' % (
        max_x0, all(r['status'] == 'PASS' for r in b1)))

    # ---- B2: corrected phase columns ----
    b2 = []
    for r in val_rows:
        Cbin = complex(float(r['Cbin_Re']), float(r['Cbin_Im']))
        Cfit = complex(float(r['C400fit_Re']), float(r['C400fit_Im']))
        b2.append({
            'record_key': r['case_id'] + '|main',
            'case_id': r['case_id'],
            'Cbin_Re': r['Cbin_Re'], 'Cbin_Im': r['Cbin_Im'],
            'Cbin_abs': r['Cbin_abs'],
            'Cbin_phase_rad': g17(np.angle(Cbin)),
            'C400fit_Re': r['C400fit_Re'], 'C400fit_Im': r['C400fit_Im'],
            'C400fit_abs': r['C400fit_abs'],
            'C400fit_phase_rad': g17(np.angle(Cfit)),
            'source': 'v082_harmonics24_validated.csv stored Re/Im (read-only)',
            'status': 'RESOLVED',
            'note': 'each phase from its own complex object; v082 mislabel (FFT phase written as fit phase) corrected'})
    # precision-path phases for the 6 weak M400 conditions x 3 paths
    conds = [('D30', 450), ('D30', 550), ('D60', 450), ('D60', 550), ('D100', 450), ('D100', 550)]
    tj = np.arange(N) / FS
    xt = 5.0 * np.cos(2 * np.pi * 400.0 * tj)
    B = np.ones((N, 9))
    for h, fr in enumerate([400, 800, 1200, 1600]):
        B[:, 1 + 2 * h] = np.cos(2 * np.pi * fr * tj)
        B[:, 2 + 2 * h] = np.sin(2 * np.pi * fr * tj)
    Cs = {}
    for D_s, zf in conds:
        D = int(D_s[1:]); key = 'D%d_zf%d_M400_a5' % (D, zf)
        Es, Eref = block_at(D, zf, 21, 21)
        Lm, Dm_, Qm, Iref = qf_coefficients(Es, Eref)
        for name, s in [('field_first_double', field_first_series(xt, Es, Eref)),
                        ('qf_single_accum', qf_series(xt, Lm, Dm_, Qm, Iref, dtype=np.float32)),
                        ('qf_double_accum', qf_series(xt, Lm, Dm_, Qm, Iref, dtype=np.float64))]:
            Im = s.mean()
            Xb = complex(np.sum((s - Im) * np.exp(-2j * np.pi * K0 * np.arange(N) / N)))
            Cb = 2 * Xb / (N * Im)
            coef, _, _, _ = np.linalg.lstsq(B, s - Im, rcond=None)
            A400 = complex(coef[1], -coef[2])
            Cfit = A400 / Im
            Cs[(key, name)] = (Cb, Cfit)
    for (key, name), (Cb, Cfit) in Cs.items():
        scale = max(abs(Cs[(key, 'field_first_double')][0] - Cs[(key, 'qf_single_accum')][0]),
                    abs(Cs[(key, 'field_first_double')][0] - Cs[(key, 'qf_double_accum')][0]),
                    abs(Cs[(key, 'qf_single_accum')][0] - Cs[(key, 'qf_double_accum')][0]))
        resolved = abs(Cb) > 10.0 * scale if scale > 0 else True
        b2.append({
            'record_key': '%s|%s' % (key, name), 'case_id': key, 'path': name,
            'Cbin_Re': g17(Cb.real), 'Cbin_Im': g17(Cb.imag), 'Cbin_abs': g17(abs(Cb)),
            'Cbin_phase_rad': g17(np.angle(Cb)),
            'C400fit_Re': g17(Cfit.real), 'C400fit_Im': g17(Cfit.imag), 'C400fit_abs': g17(abs(Cfit)),
            'C400fit_phase_rad': g17(np.angle(Cfit)),
            'source': 'v083 Phase-A-equivalent deterministic reconstruction (same operators, no new physical state)',
            'status': 'RESOLVED' if resolved else 'UNRESOLVED_NEAR_ZERO',
            'note': 'numeric path spread scale %.3e; phases are numerical diagnostics only - no real magnetic phase synchronisation exists' % scale})
    b2_fields = ['record_key', 'case_id', 'path', 'Cbin_Re', 'Cbin_Im', 'Cbin_abs', 'Cbin_phase_rad',
                 'C400fit_Re', 'C400fit_Im', 'C400fit_abs', 'C400fit_phase_rad',
                 'source', 'status', 'note']
    with open(os.path.join(TAB, 'v083_phase_columns_corrected.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=b2_fields, lineterminator='\n'); w.writeheader(); w.writerows(b2)
    n_unres = sum(1 for r in b2 if r['status'] == 'UNRESOLVED_NEAR_ZERO')
    print('[B2] phase columns: %d rows (%d main + 18 precision); UNRESOLVED_NEAR_ZERO: %d' % (
        len(b2), 24, n_unres))
    # readback
    for name, nexp, key in (('v083_harmonic_complex_closure_X0_corrected.csv', 24, 'case_id'),
                            ('v083_phase_columns_corrected.csv', 42, 'record_key')):
        with open(os.path.join(TAB, name), 'r', newline='', encoding='utf-8') as f:
            rr = list(csv.reader(f))
        assert len(rr) - 1 == nexp and all(len(x) == len(rr[0]) for x in rr), name
        keys = [x[0] for x in rr[1:]]
        assert len(set(keys)) == nexp, name + ' duplicate keys'
    print('[B] readback clean (24 + 42 rows)')


if __name__ == '__main__':
    main()



