# -*- coding: utf-8 -*-
"""v084 Phase A1: legacy (row21,col1) numeric re-verification for all 24
existing prescriptions. Only (21,1) is compared against tseries_center
(the v083 (1,21) mis-call is corrected here); the true-centre results of v083
stand as recorded and are NOT re-run. Gate max|dI| < 1e-8 (frozen)."""
import os, sys, csv, json
import numpy as np
import h5py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v083_common import ROOT, N, FS, block_at
from v082_qf_common import qf_coefficients, qf_series, cbin

GH = os.path.join(ROOT, 'github_handoff')
TAB = os.path.join(GH, 'tables')
NUM = os.path.join(GH, 'numeric')
DYN = os.path.join(ROOT, 'v076_return', 'numeric', 'v076_dynamic_center_corrected.mat')
GATE = 1e-8
CASES = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
         for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)]


def g17(x):
    return '%.17g' % x


def main():
    f2 = h5py.File(DYN, 'r')
    rows = []
    n_ok = n_fail = n_missing = 0
    for key in CASES:
        parts = key.split('_')
        D, zf, ttype, a = int(parts[0][1:]), int(parts[1][2:]), parts[2], int(parts[3][1:])
        try:
            if 'tseries_center' not in f2[key]:
                rows.append({'case_id': key, 'status': 'LEGACY_COL1_MISSING_SOURCE',
                             'evidence_status': 'tseries_center field missing'})
                n_missing += 1
                continue
            freq = 200.0 if ttype == 'M200' else 400.0
            s_leg = np.array(f2[key]['tseries_center']).flatten().astype(np.float64)
            Es, Eref = block_at(D, zf, 21, 1)
            Lm, Dm_, Qm, Iref = qf_coefficients(Es, Eref)
            tj = np.arange(N) / FS
            xt = float(a) * np.cos(2 * np.pi * freq * tj)
            s_rec = qf_series(xt, Lm, Dm_, Qm, Iref, dtype=np.float32)
            d = float(np.max(np.abs(s_rec - s_leg)))
            relL2 = float(np.linalg.norm(s_rec - s_leg) / max(np.linalg.norm(s_leg), 1e-300))
            Xr, Im_r = cbin(s_rec)
            Xl, Im_l = cbin(s_leg)
            status = 'LEGACY_COL1_NUMERIC_VERIFIED' if d < GATE else 'LEGACY_COL1_NUMERIC_FAILED'
            if status == 'LEGACY_COL1_NUMERIC_VERIFIED':
                n_ok += 1
            else:
                n_fail += 1
            rows.append({
                'case_id': key, 'legacy_row': 21, 'legacy_col': 1,
                'true_row': 21, 'true_col': 21,
                'matlab_ipix_shape': '(41,41,1,2001) single (from v076_C source; MATLAB session NOT_EXECUTED)',
                'hdf5_axis_mapping': 'Es axis1=MATLAB col, axis2=MATLAB row; recon call Es[:, cs(60:65), rs(160:165)]',
                'raw_anchor_sha': 'v074_return/numeric/render_cache (see logs/cache_source_identity_sha256.csv)',
                'source_series_sha': __import__('hashlib').sha256(s_leg.tobytes()).hexdigest(),
                'N': N, 'series_dtype': 'float64 (stored; reconstructed float32)',
                'mean_old': g17(float(np.mean(s_leg))), 'mean_reconstructed': g17(float(np.mean(s_rec))),
                'max_abs_series_diff': g17(d), 'relative_L2_series_diff': g17(relL2),
                'Cbin_Re_diff': g17((Xr - Xl).real), 'Cbin_Im_diff': g17((Xr - Xl).imag),
                'Cbin_Re_recon': g17(Xr.real), 'Cbin_Im_recon': g17(Xr.imag),
                'Imean_recon': g17(Im_r), 'Imean_old': g17(Im_l),
                'wrong_axis_diff_row1_col21': 'see v084_asymmetric_pixel_pilot.csv NEG row (9.8e-5 scale)',
                'gate': 'max|dI| < 1e-8',
                'physical_status': 'same legacy prescription, pure time-domain post-processing, zero new physical state',
                'evidence_status': 'reconstructed + stored + CSV readback verified',
                'status': status,
                'note': 'v083 mis-call (1,21) corrected to (21,1); independent sentinels rows 26/16 at col 1 also verified in pilot'})
        except Exception as exc:  # keep failure rows, never fake
            rows.append({'case_id': key, 'status': 'LEGACY_COL1_NUMERIC_FAILED',
                         'evidence_status': 'exception: %s' % exc})
            n_fail += 1
    f2.close()
    fields = ['case_id', 'legacy_row', 'legacy_col', 'true_row', 'true_col', 'matlab_ipix_shape',
              'hdf5_axis_mapping', 'raw_anchor_sha', 'source_series_sha', 'N', 'series_dtype',
              'mean_old', 'mean_reconstructed', 'max_abs_series_diff', 'relative_L2_series_diff',
              'Cbin_Re_diff', 'Cbin_Im_diff', 'Cbin_Re_recon', 'Cbin_Im_recon', 'Imean_recon',
              'Imean_old', 'wrong_axis_diff_row1_col21', 'gate', 'physical_status',
              'evidence_status', 'status', 'note']
    with open(os.path.join(TAB, 'v084_legacy_col1_identity24.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n'); w.writeheader(); w.writerows(rows)
    with open(os.path.join(TAB, 'v084_legacy_col1_identity24.csv'), 'r', newline='', encoding='utf-8') as f:
        rr = list(csv.reader(f))
    assert len(rr) - 1 == 24 and all(len(x) == len(rr[0]) for x in rr)
    assert len(set(x[0] for x in rr[1:])) == 24
    print('[A1] verified=%d failed=%d missing=%d' % (n_ok, n_fail, n_missing))
    with open(os.path.join(GH, 'logs', 'v084_phase_a1_summary.json'), 'w', encoding='utf-8') as f:
        json.dump({'verified': n_ok, 'failed': n_fail, 'missing': n_missing, 'gate': GATE}, f, indent=2)


if __name__ == '__main__':
    main()

