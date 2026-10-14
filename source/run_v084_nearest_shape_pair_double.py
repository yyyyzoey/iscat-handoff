# -*- coding: utf-8 -*-
"""v084 Phase C: exactly 2 newly authorised full-ROI (41x41) double-precision
complex C400 maps - the closest cross-D shape pair from
v083_nuisance_feature_pairwise276.csv (development finding, not a blind test):

  D30_zf550_M400_a20  and  D60_zf450_M400_a20

Same streamed builder as v083 (batch<=32 frames, same v074 anchors, corrected
ROI, h5py orientation confirmed by v084 Phase B). Outputs the double-pair
shape-Frobenius distance alongside the historical single-precision distance.
No new BEM/renders/physical states; no amplitude/phase registration tweaks.
"""
import os, sys, csv, json, time
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
CONDITIONS = [('D30_zf550_M400_a20', 30, 550, 'M400', 20.0),
              ('D60_zf450_M400_a20', 60, 450, 'M400', 20.0)]


def build_map(D, zf, ttype, a_nm, mem_log):
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
    sum_e = np.sum(e)
    X = SX - Im_map * sum_e
    with np.errstate(invalid='ignore', divide='ignore'):
        C = 2.0 * X / (N * Im_map)
    pos = Im_map[(Im_map > 0) & np.isfinite(Im_map)]
    floor = 0.01 * np.median(pos)
    valid = np.isfinite(Im_map) & (Im_map > floor)
    Cm = np.full((41, 41), np.nan + 1j * np.nan)
    Cm[valid] = C[valid]
    return Cm, Im_map, valid, mem_log


def g17(x):
    return '%.17g' % x


def main():
    f2 = h5py.File(DYN, 'r')
    maps, singles, valids = {}, {}, {}
    rows = []
    for key, D, zf, ttype, a in CONDITIONS:
        t0 = time.time()
        mem = {}
        Cm, Im_map, valid, mem = build_map(D, zf, ttype, a, mem)
        dt = time.time() - t0
        cm = f2[key]['C400'][:]
        Cs = cm['real'].astype(np.float64) + 1j * cm['imag'].astype(np.float64)
        maps[key], singles[key], valids[key] = Cm, Cs, valid
        common = valid & np.isfinite(Cs.real) & np.isfinite(Cs.imag)
        rF = float(np.linalg.norm((Cm - Cs)[common]) / max(np.linalg.norm(Cs[common]), 1e-300))
        savemat(os.path.join(NUM, 'v084_double_C400_%s.mat' % key),
                {'C400_double': Cm, 'Imean_map': Im_map, 'valid_mask': valid,
                 'case_id': key,
                 'note': 'v084 streamed double-precision complex C400 map (41x41), orientation h5py axis1=MATLAB col / axis2=MATLAB row (v084 Phase B confirmed)'},
                do_compression=True)
        rows.append({
            'case_id': key, 'condition_type': ttype, 'a_nm': int(a), 'zf_nm': zf,
            'precision': 'double (streamed, batch=%d)' % BATCH,
            'peak_qf_coefficients_MB': mem['qf_coeffs_MB'], 'wall_time_s': '%.1f' % dt,
            'n_common_pixels': int(common.sum()),
            'rF_double_vs_single': g17(rF),
            'centre_C400_double_Re': g17(Cm[20, 20].real), 'centre_C400_double_Im': g17(Cm[20, 20].imag),
            'centre_C400_single_Re': g17(Cs[20, 20].real), 'centre_C400_single_Im': g17(Cs[20, 20].imag),
            'centre_abs_double': g17(abs(Cm[20, 20])), 'centre_abs_single': g17(abs(Cs[20, 20])),
            'L1_double': g17(float(np.sum(np.abs(Cm[common])))),
            'L2_double': g17(float(np.linalg.norm(Cm[common]))),
            'status': 'COMPLETED',
            'note': ' authorised narrow addition (2 of 2); development-condition check only; no全域 robustness or diameter accuracy claims'})
        print('  %s: rF=%.3e centre|d|=%.3e (%.1fs)' % (key, rF, abs(Cm[20, 20] - Cs[20, 20]), dt))
    # pair shape distances
    shapes = {}
    for key in maps:
        Cm, common = maps[key], valids[key]
        nrm = float(np.linalg.norm(np.abs(Cm[common])))
        sh = np.where(common, np.abs(Cm) / max(nrm, 1e-300), 0.0)
        shapes[key] = sh
    sh_single = {}
    for key in maps:
        Cs, common = singles[key], valids[key]
        nrm = float(np.linalg.norm(np.abs(Cs[common])))
        sh_single[key] = np.where(common, np.abs(Cs) / max(nrm, 1e-300), 0.0)
    k1, k2 = maps.keys()
    d_double = float(np.linalg.norm(shapes[k1] - shapes[k2]))
    d_single = float(np.linalg.norm(sh_single[k1] - sh_single[k2]))
    for r in rows:
        r['pair_partner'] = k2 if r['case_id'] == k1 else k1
        r['shape_Frobenius_pair_double'] = g17(d_double) if r['case_id'] == k1 else ''
        r['shape_Frobenius_pair_single_historical'] = g17(d_single) if r['case_id'] == k1 else ''
        r['abs_delta_double_minus_single'] = g17(abs(d_double - d_single)) if r['case_id'] == k1 else ''
    f2.close()
    fields = list(rows[0].keys())
    with open(os.path.join(TAB, 'v084_nearest_shape_pair_double2.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n'); w.writeheader(); w.writerows(rows)
    with open(os.path.join(TAB, 'v084_nearest_shape_pair_double2.csv'), 'r', newline='', encoding='utf-8') as f:
        rr = list(csv.reader(f))
    assert len(rr) - 1 == 2 and all(len(x) == len(rr[0]) for x in rr)
    summary = {'evaluations_used': 2, 'budget': 2,
               'shape_pair_distance_double': g17(d_double),
               'shape_pair_distance_single_historical': g17(d_single),
               'abs_delta': g17(abs(d_double - d_single))}
    print('[C] shape pair distance: double=%.6g single(historical)=%.6g delta=%.3g' % (
        d_double, d_single, abs(d_double - d_single)))
    with open(os.path.join(GH, 'logs', 'v084_phase_c_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)


if __name__ == '__main__':
    main()
