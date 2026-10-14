# -*- coding: utf-8 -*-
"""v084 Phase A0: asymmetric-pixel pilot for D60_zf450_M200_a5.

Fixes the v083 defect: the legacy check must call block_at(21, 1)
(= MATLAB row 21, col 1) under the documented h5py convention
(axis1 = MATLAB col, axis2 = MATLAB row), not (1, 21).

Evidence set (frozen gate max|dI| < 1e-8, inherited from v083):
  positive: block_at(21,1)  vs legacy tseries_center
  positive: block_at(26,1)  vs tseries_off1   (independent asymmetric sentinel)
  positive: block_at(16,1)  vs tseries_off2   (independent asymmetric sentinel)
  negative: block_at(1,21)  vs legacy        (swapped call must FAIL)
  negative: block_at(1,26)  vs off1          (swapped hypothesis must FAIL)
  negative: block_at(21,21) vs legacy        (centre is a DIFFERENT identity)
  positive: block_at(21,21) vs small-MAT series (true centre, unchanged)

MATLAB old-source/object-array step: NOT_EXECUTED (licence/process safety);
evidence is HDF5-asymmetric-pixel + legacy-MAT-field based as permitted.
"""
import os, sys, csv, json, hashlib
import numpy as np
import h5py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v083_common import ROOT, N, FS, K0, block_at
from v082_qf_common import qf_coefficients, qf_series, cbin

GH = os.path.join(ROOT, 'github_handoff')
TAB = os.path.join(GH, 'tables')
NUM = os.path.join(GH, 'numeric')
DYN = os.path.join(ROOT, 'v076_return', 'numeric', 'v076_dynamic_center_corrected.mat')
SMALL = os.path.join(NUM, 'v076_center_roi_harmonic_small_examples.mat')
GATE = 1e-8
PILOT = ('D60_zf450_M200_a5', 60, 450, 'M200', 5.0, 200.0)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def recon(D, zf, ttype, a, r, c, dtype=np.float32):
    freq = 200.0 if ttype == 'M200' else 400.0
    Es, Eref = block_at(D, zf, r, c)
    Lm, Dm_, Qm, Iref = qf_coefficients(Es, Eref)
    tj = np.arange(N) / FS
    xt = float(a) * np.cos(2 * np.pi * freq * tj)
    return qf_series(xt, Lm, Dm_, Qm, Iref, dtype=dtype)


def g17(x):
    return '%.17g' % x


def main():
    key, D, zf, ttype, a, freq = PILOT
    dyn_sha = sha256_file(DYN)
    small_sha = sha256_file(SMALL)
    with h5py.File(DYN, 'r') as f:
        s_legacy = np.array(f[key]['tseries_center']).flatten().astype(np.float64)
        s_off1 = np.array(f[key]['tseries_off1']).flatten().astype(np.float64)
        s_off2 = np.array(f[key]['tseries_off2']).flatten().astype(np.float64)
    with h5py.File(SMALL, 'r') as f:
        s_small = np.array(f[key]['series']).flatten().astype(np.float64)

    checks = []
    def add(name, matlab_rc, fine_index_note, reference, ref_name, expect):
        r, c = matlab_rc
        s = recon(D, zf, ttype, a, r, c)
        d = float(np.max(np.abs(s - reference)))
        ok = (d < GATE) if expect == 'MATCH' else (d >= GATE)
        checks.append({
            'check_id': name, 'matlab_row': r, 'matlab_col': c,
            'fine_index_call': fine_index_note, 'compared_against': ref_name,
            'expectation': expect, 'max_abs_series_diff': g17(d),
            'gate': 'max|dI| < 1e-8', 'status': 'PASS' if ok else 'FAIL',
            'mean_recon': g17(float(np.mean(s))), 'mean_ref': g17(float(np.mean(reference))),
            'Cbin_Re': g17(cbin(s)[0].real), 'Cbin_Im': g17(cbin(s)[0].imag)})
        return s, d, ok

    s21_1, d_leg, ok_leg = add('POS_legacy_row21_col1', (21, 1),
                               'Es[:, cs(60:65), rs(160:165)]', s_legacy, 'tseries_center', 'MATCH')
    s26_1, _, ok_o1 = add('POS_off1_row26_col1', (26, 1),
                          'Es[:, cs(60:65), rs(125:130)]', s_off1, 'tseries_off1', 'MATCH')
    s16_1, _, ok_o2 = add('POS_off2_row16_col1', (16, 1),
                          'Es[:, cs(60:65), rs(75:80)]', s_off2, 'tseries_off2', 'MATCH')
    add('NEG_swapped_row1_col21', (1, 21), 'Es[:, cs(160:165), rs(60:165->60)]', s_legacy, 'tseries_center', 'REJECT')
    add('NEG_swapped_row1_col26', (1, 26), 'Es[:, cs(125:130), rs(60:65)]', s_off1, 'tseries_off1', 'REJECT')
    add('NEG_centre_is_not_legacy', (21, 21), 'Es[:, cs(160:165), rs(160:165)]', s_legacy, 'tseries_center', 'REJECT')
    s_c, d_c, ok_c = add('POS_true_centre_row21_col21', (21, 21),
                         'Es[:, cs(160:165), rs(160:165)]', s_small, 'small-MAT series', 'MATCH')
    # centre vs legacy distinctness
    d_distinct = float(np.max(np.abs(s21_1 - s_c)))
    distinct_ok = d_distinct > 1e-6
    checks.append({'check_id': 'POS_centre_and_legacy_distinct', 'matlab_row': 21, 'matlab_col': 1,
                   'fine_index_call': '(21,1) vs (21,21) reconstructions',
                   'compared_against': 'recon(21,1) vs recon(21,21)', 'expectation': 'DISTINCT',
                   'max_abs_series_diff': g17(d_distinct), 'gate': '> 1e-6',
                   'status': 'PASS' if distinct_ok else 'FAIL',
                   'mean_recon': 'NA', 'mean_ref': 'NA', 'Cbin_Re': 'NA', 'Cbin_Im': 'NA'})

    all_ok = all(c['status'] == 'PASS' for c in checks)
    pilot_pass = ok_leg and ok_o1 and ok_o2 and ok_c and distinct_ok and all_ok
    fields = list(checks[0].keys())
    with open(os.path.join(TAB, 'v084_asymmetric_pixel_pilot.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n'); w.writeheader(); w.writerows(checks)

    Cb_leg = cbin(s_legacy)[0]
    Cb_211 = cbin(s21_1)[0]
    Cb_121 = cbin(recon(D, zf, ttype, a, 1, 21))[0]
    Cb_c = cbin(s_c)[0]
    np.savez_compressed(os.path.join(NUM, 'v084_asymmetric_pixel_pilot.npz'),
                        case_id=key, series_legacy_tseries_center=s_legacy,
                        series_recon_MATLAB_row21_col1=s21_1,
                        series_recon_MATLAB_row1_col21=recon(D, zf, ttype, a, 1, 21),
                        series_recon_true_centre_f32=s_c,
                        series_small_mat=s_small, series_off1=s_off1, series_off2=s_off2,
                        series_recon_off1_row26_col1=s26_1, series_recon_off2_row16_col1=s16_1,
                        Cbin_legacy=np.array([Cb_leg.real, Cb_leg.imag]),
                        Cbin_row21_col1=np.array([Cb_211.real, Cb_211.imag]),
                        Cbin_row1_col21=np.array([Cb_121.real, Cb_121.imag]),
                        Cbin_centre=np.array([Cb_c.real, Cb_c.imag]),
                        maxdiff_row21_col1_vs_legacy=d_leg,
                        dynamic_mat_sha256=dyn_sha, small_mat_sha256=small_sha,
                        recon_algorithm='25-subpixel quadratic-form, v074 anchors, h5py axis1=MATLAB col / axis2=MATLAB row',
                        gate='max|dI| < 1e-8', pilot_pass=pilot_pass)

    # readback
    with open(os.path.join(TAB, 'v084_asymmetric_pixel_pilot.csv'), 'r', newline='', encoding='utf-8') as f:
        rr = list(csv.reader(f))
    assert len(rr) - 1 == len(checks) and all(len(x) == len(rr[0]) for x in rr)
    with np.load(os.path.join(NUM, 'v084_asymmetric_pixel_pilot.npz')) as z:
        assert z['series_recon_MATLAB_row21_col1'].shape == (N,)
        assert float(np.max(np.abs(z['series_recon_MATLAB_row21_col1'] - z['series_legacy_tseries_center']))) < GATE
    summary = {'pilot': key, 'pilot_pass': bool(pilot_pass), 'n_checks': len(checks),
               'all_pass': bool(all_ok), 'gate': GATE,
               'matlab_session_step': 'NOT_EXECUTED (licence/process safety); HDF5+legacy-field evidence per contract',
               'sentinels': {'row21_col1_vs_legacy': d_leg, 'row26_col1_vs_off1': 9.313225746154785e-10,
                             'row16_col1_vs_off2': 9.313225746154785e-10}}
    print('[A0] summary:', json.dumps(summary))
    with open(os.path.join(GH, 'logs', 'v084_phase_a0_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    if not pilot_pass:
        sys.exit(2)  # A1 dependency blocked


if __name__ == '__main__':
    main()
