# -*- coding: utf-8 -*-
"""v085 Phase B: implementation regression of the two double-precision imaging
paths on two existing cases (strong: D100_zf450_M200_a20; weak: D30_zf450_M400_a5).

Both paths use the SAME 5 anchors, reference field, per-pixel 25-subpixel
intensity averaging (intensity mean, NOT mean-field modulus), N/Fs/k0, and the
same valid-mask rule:
  P_field  - interpolate complex scattered field first (bilinear), then full
             interference intensity |Eref+Esca|^2, then 25-subpixel mean
  P_qf     - quadratic-form intensity expansion (algebraically identical for
             bilinear interpolation), then 25-subpixel mean

New software-regression engineering gate (same input, same double-precision
algebraic identity ONLY - replaces no physical acceptance):
  2D complex C400 relative Frobenius < 1e-10 on common valid pixels AND
  centre absolute complex difference < 1e-12.
"""
import os, sys, csv, json, time
import numpy as np
import h5py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v083_common import ROOT, N, FS, K0, roi_blocks, qf_coefficients_grid, lin_weights

GH = os.path.join(ROOT, 'github_handoff')
TAB = os.path.join(GH, 'tables')
BATCH = 32
CASES = [('D100_zf450_M200_a20', 100, 450, 'M200', 20.0),
         ('D30_zf450_M400_a5', 30, 450, 'M400', 5.0)]


def batch_frames(x, Lm, Dm_, Qm, Iref, e_sl):
    ia = x[0]; wa = x[1]; wb = x[2]; ib = ia + 1
    v = (Iref[None, :, :]
         + wa[:, None, None] * Lm[ia] + wb[:, None, None] * Lm[ib]
         + (wa ** 2)[:, None, None] * Dm_[ia] + (wb ** 2)[:, None, None] * Dm_[ib]
         + (wa * wb)[:, None, None] * Qm[ia, ib])
    return v.reshape(v.shape[0], 41, 5, 41, 5).mean(axis=(2, 4))


def run_path(D, zf, ttype, a, path, mem_log):
    Es, Eref = roi_blocks(D, zf)
    Lm, Dm_, Qm, Iref = qf_coefficients_grid(Es, Eref)
    mem_log['qf_MB'] = round((Lm.nbytes + Dm_.nbytes + Qm.nbytes + Iref.nbytes) / 1e6, 1)
    if path == 'field':
        mem_log['field_blocks_MB'] = round(Es.nbytes / 1e6, 1)
    tj = np.arange(N) / FS
    freq = 200.0 if ttype == 'M200' else 400.0
    x = a * np.cos(2 * np.pi * freq * tj)
    ia_all, wa_all, wb_all = lin_weights(x)
    S1 = np.zeros((41, 41))
    SX = np.zeros((41, 41), dtype=np.complex128)
    e = np.exp(-2j * np.pi * K0 * np.arange(N) / N)
    for b0 in range(0, N, BATCH):
        sl = slice(b0, min(b0 + BATCH, N))
        xs = (ia_all[sl], wa_all[sl], wb_all[sl])
        if path == 'qf':
            I = batch_frames(xs, Lm, Dm_, Qm, Iref, e[sl])
        else:
            ia, wa, wb = xs
            ib = ia + 1
            EsI = wa[:, None, None, None] * Es[ia] + wb[:, None, None, None] * Es[ib]
            It = np.sum(np.abs(Eref[None, :, :, :] + EsI) ** 2, axis=3)  # (B,205,205)
            I = It.reshape(It.shape[0], 41, 5, 41, 5).mean(axis=(2, 4))
        S1 += I.sum(axis=0)
        SX += np.tensordot(e[sl], I, axes=(0, 0))
    del Es, Eref
    Im_map = S1 / N
    sum_e = np.sum(e)
    X = SX - Im_map * sum_e
    with np.errstate(invalid='ignore', divide='ignore'):
        C = 2.0 * X / (N * Im_map)
    pos = Im_map[(Im_map > 0) & np.isfinite(Im_map)]
    floor = 0.01 * np.median(pos)
    valid = np.isfinite(Im_map) & (Im_map > floor)
    Cm = np.full((41, 41), np.nan + 1j * np.nan)
    Cm[valid] = C[valid]
    return Cm, Im_map, valid


def g17(x):
    return '%.17g' % x


def main():
    rows = []
    all_pass = True
    for key, D, zf, ttype, a in CASES:
        t0 = time.time()
        mem = {}
        Cf, Imf, vf = run_path(D, zf, ttype, a, 'field', mem)
        Cq, Imq, vq = run_path(D, zf, ttype, a, 'qf', mem)
        dt = time.time() - t0
        common = vf & vq
        dmap = (Cf - Cq)[common]
        rF = float(np.linalg.norm(dmap) / max(np.linalg.norm(Cq[common]), 1e-300))
        d_centre = abs(Cf[20, 20] - Cq[20, 20])
        gate_ok = (rF < 1e-10) and (d_centre < 1e-12)
        all_pass &= gate_ok
        rows.append({
            'case_id': key, 'condition_type': ttype, 'a_nm': int(a), 'zf_nm': zf,
            'path_field': 'complex-field-first, full interference intensity, 25-subpixel mean, double',
            'path_qf': 'quadratic-form expansion, 25-subpixel mean, double',
            'anchors': 'v074 render_cache x={-20,-10,0,+10,+20} nm (read-only)',
            'N': N, 'Fs': FS, 'k0': K0, 'batch_frames': BATCH,
            'peak_qf_coeffs_MB': mem['qf_MB'], 'peak_field_blocks_MB': mem['field_blocks_MB'],
            'wall_time_s': '%.1f' % dt, 'n_common_pixels': int(common.sum()),
            'meanI_max_absdiff': g17(float(np.max(np.abs(Imf - Imq)))),
            'C400_relFrobenius_field_vs_qf': g17(rF),
            'centre_abs_complex_diff': g17(d_centre),
            'gate_rF': '< 1e-10', 'gate_centre_abs': '< 1e-12',
            'status': 'REGRESSION_PASS' if gate_ok else 'REGRESSION_FAIL',
            'note': 'software regression for the SAME-input algebraic identity only; no physical acceptance implied'})
        print('  %s: rF=%.3e centre|d|=%.3e (%.1fs)' % (key, rF, d_centre, dt))
    fields = list(rows[0].keys())
    with open(os.path.join(TAB, 'v085_operator_regression2.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n'); w.writeheader(); w.writerows(rows)
    with open(os.path.join(TAB, 'v085_operator_regression2.csv'), 'r', newline='', encoding='utf-8') as f:
        rr = list(csv.reader(f))
    assert len(rr) - 1 == 2 and all(len(x) == len(rr[0]) for x in rr)
    summary = {'phase': 'B', 'all_pass': bool(all_pass), 'cases': len(rows)}
    print('[B] summary:', json.dumps(summary))
    with open(os.path.join(GH, 'logs', 'v085_phase_b_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    if not all_pass:
        sys.exit(2)  # C blocked


if __name__ == '__main__':
    main()
