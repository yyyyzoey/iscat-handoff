# -*- coding: utf-8 -*-
"""v083 Phase C: bounded full-ROI (41x41) double-precision complex C400 maps
for 4 frozen legacy conditions, built by streaming time-domain post-processing
(batches <= 32 frames) of the SAME v074 anchor fields. Zero BEM, zero renders.

Compared against the stored v076 single-precision dynamic maps (read-only):
Frobenius abs/rel complex differences, centre complex C400, norms.
This is a numerical-path sensitivity screen, NOT a camera-scale certification.
"""
import os, sys, csv, json, hashlib
import numpy as np
import h5py
from scipy.io import savemat

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v083_common import ROOT, N, FS, K0, roi_blocks, qf_coefficients_grid, lin_weights

GH = os.path.join(ROOT, 'github_handoff')
TAB = os.path.join(GH, 'tables')
NUM = os.path.join(GH, 'numeric')
DYN = os.path.join(ROOT, 'v076_return', 'numeric', 'v076_dynamic_center_corrected.mat')
BATCH = 32
CONDITIONS = [('D30_zf450_M400_a5', 30, 450, 'M400', 5.0),
              ('D30_zf550_M400_a5', 30, 550, 'M400', 5.0),
              ('D60_zf450_M400_a5', 60, 450, 'M400', 5.0),
              ('D100_zf450_M200_a20', 100, 450, 'M200', 20.0)]


def build_map(D, zf, ttype, a_nm, mem_log):
    Es, Eref = roi_blocks(D, zf)
    Lm, Dm_, Qm, Iref = qf_coefficients_grid(Es, Eref)
    del Es, Eref
    mem_log['qf_coeffs_MB'] = round((Lm.nbytes + Dm_.nbytes + Qm.nbytes + Iref.nbytes) / 1e6, 1)
    tj = np.arange(N) / FS
    freq = 200.0 if ttype == 'M200' else 400.0
    x = a_nm * np.cos(2 * np.pi * freq * tj)
    ia_all, wa_all, wb_all = lin_weights(x)
    S1 = np.zeros((205, 205))          # sum of intensity
    SX = np.zeros((205, 205), dtype=np.complex128)  # sum I_j e^{-2pi i k0 j/N}
    e = np.exp(-2j * np.pi * K0 * np.arange(N) / N)
    for b0 in range(0, N, BATCH):
        sl = slice(b0, min(b0 + BATCH, N))
        ia = ia_all[sl]; wa = wa_all[sl]; wb = wb_all[sl]; ib = ia + 1
        v = (Iref[None, :, :]
             + wa[:, None, None] * Lm[ia] + wb[:, None, None] * Lm[ib]
             + (wa ** 2)[:, None, None] * Dm_[ia] + (wb ** 2)[:, None, None] * Dm_[ib]
             + (wa * wb)[:, None, None] * Qm[ia, ib])
        I = v.reshape(v.shape[0], 41, 5, 41, 5).mean(axis=(2, 4))  # (B,41,41)
        S1 += I.sum(axis=0)
        SX += (I * e[sl][:, None, None].real.astype(np.float64)).astype(np.complex128)
        # complex weighting: e is complex; redo properly below
    return S1, SX


def build_map_correct(D, zf, ttype, a_nm, mem_log):
    """Correct complex accumulation (previous draft dropped Im of e)."""
    Es, Eref = roi_blocks(D, zf)
    Lm, Dm_, Qm, Iref = qf_coefficients_grid(Es, Eref)
    del Es, Eref
    mem_log['qf_coeffs_MB'] = round((Lm.nbytes + Dm_.nbytes + Qm.nbytes + Iref.nbytes) / 1e6, 1)
    tj = np.arange(N) / FS
    freq = 200.0 if ttype == 'M200' else 400.0
    x = a_nm * np.cos(2 * np.pi * freq * tj)
    ia_all, wa_all, wb_all = lin_weights(x)
    S1 = np.zeros((41, 41))
    SX = np.zeros((41, 41), dtype=np.complex128)
    e = np.exp(-2j * np.pi * K0 * np.arange(N) / N)
    for b0 in range(0, N, BATCH):
        sl = slice(b0, min(b0 + BATCH, N))
        ia = ia_all[sl]; wa = wa_all[sl]; wb = wb_all[sl]; ib = ia + 1
        v = (Iref[None, :, :]
             + wa[:, None, None] * Lm[ia] + wb[:, None, None] * Lm[ib]
             + (wa ** 2)[:, None, None] * Dm_[ia] + (wb ** 2)[:, None, None] * Dm_[ib]
             + (wa * wb)[:, None, None] * Qm[ia, ib])
        I = v.reshape(v.shape[0], 41, 5, 41, 5).mean(axis=(2, 4))
        S1 += I.sum(axis=0)
        SX += np.tensordot(e[sl], I, axes=(0, 0))
    Im_map = S1 / N
    sum_e = np.sum(e)  # G_N(-k0/N), a complex scalar
    X = SX - Im_map * sum_e
    with np.errstate(invalid='ignore', divide='ignore'):
        C = 2.0 * X / (N * Im_map)
    pos = Im_map[(Im_map > 0) & np.isfinite(Im_map)]
    floor = 0.01 * np.median(pos)
    valid = np.isfinite(Im_map) & (Im_map > floor)
    Cm = np.full((41, 41), np.nan + 1j * np.nan)
    Cm[valid] = C[valid]
    return Cm, Im_map, valid, mem_log


def main():
    rows = []
    f2 = h5py.File(DYN, 'r')
    for key, D, zf, ttype, a in CONDITIONS:
        import time
        t0 = time.time()
        mem = {}
        Cm, Im_map, valid, mem = build_map_correct(D, zf, ttype, a, mem)
        dt = time.time() - t0
        stored = f2[key]['C400'][:]
        Cs = stored['real'].astype(np.float64) + 1j * stored['imag'].astype(np.float64)
        common = valid & np.isfinite(Cs)
        dmap = Cm[common] - Cs[common]
        fro_abs = float(np.linalg.norm(dmap))
        fro_rel = fro_abs / max(float(np.linalg.norm(Cs[common])), 1e-300)
        centre = (20, 20)
        d_centre = Cm[centre] - Cs[centre]
        # single-frame spot check vs centre series identity (Phase A cross-check)
        rows.append({
            'case_id': key, 'condition_type': ttype, 'a_nm': int(a), 'zf_nm': zf,
            'precision': 'double (streamed, batch=%d)' % BATCH,
            'n_frames': N, 'batch_frames': BATCH,
            'peak_qf_coefficients_MB': mem['qf_coeffs_MB'],
            'wall_time_s': '%.1f' % dt,
            'valid_fraction': '%.6f' % (common.sum() / (41 * 41)),
            'map_Frobenius_abs_diff': '%.17g' % fro_abs,
            'map_Frobenius_rel_diff': '%.17g' % fro_rel,
            'norm_Frobenius_v083_double': '%.17g' % float(np.linalg.norm(Cm[common])),
            'norm_Frobenius_v076_single': '%.17g' % float(np.linalg.norm(Cs[common])),
            'L1_v083_double': '%.17g' % float(np.sum(np.abs(Cm[common]))),
            'L1_v076_single': '%.17g' % float(np.sum(np.abs(Cs[common]))),
            'centre_C400_v083_Re': '%.17g' % Cm[centre].real, 'centre_C400_v083_Im': '%.17g' % Cm[centre].imag,
            'centre_C400_v076_Re': '%.17g' % Cs[centre].real, 'centre_C400_v076_Im': '%.17g' % Cs[centre].imag,
            'centre_abs_diff': '%.17g' % abs(d_centre),
            'centre_abs_v083': '%.17g' % abs(Cm[centre]), 'centre_abs_v076': '%.17g' % abs(Cs[centre]),
            'status': 'COMPLETED_SCREEN',
            'note': 'numerical path sensitivity screen only; no camera-scale certification; no new physical states'})
        savemat(os.path.join(NUM, 'v083_fullROI_double_C400_%s.mat' % key),
                {'C400_double': Cm, 'Imean_map': Im_map, 'valid_mask': valid,
                 'case_id': key, 'note': 'v083 streamed double-precision complex C400 map (41x41), corrected ROI'},
                do_compression=True)
        print('  %s: fro_rel=%.3e centre|d|=%.3e (%.1fs, %s MB)' % (
            key, fro_rel, abs(d_centre), dt, mem['qf_coeffs_MB']))
    f2.close()
    fields = list(rows[0].keys())
    with open(os.path.join(TAB, 'v083_fullROI_precision4.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n'); w.writeheader(); w.writerows(rows)
    with open(os.path.join(TAB, 'v083_fullROI_precision4.csv'), 'r', newline='', encoding='utf-8') as f:
        rr = list(csv.reader(f))
    assert len(rr) - 1 == 4 and all(len(x) == len(rr[0]) for x in rr)
    print('[C] 4 full-ROI conditions complete; readback clean')


if __name__ == '__main__':
    main()

