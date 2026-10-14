# -*- coding: utf-8 -*-
"""v085 Phase C: complete the unified 24-state double-precision C400 map set.

Reuse the 6 verified caches (4x v083 + 2x v084); build the remaining 18 states
with the same streamed (batch<=32) QF double path validated by Phase B.
Each new map is compared against the stored v076 single-precision map
(rF = numerical-path diagnostic, NOT the old 2% physical gate).
Arrays are persisted and read back before DOUBLE_MAP_VERIFIED is written."""
import os, sys, csv, json, time, hashlib
import numpy as np
import h5py
from scipy.io import savemat, loadmat

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v083_common import ROOT, N, FS, K0, roi_blocks, qf_coefficients_grid, lin_weights

GH = os.path.join(ROOT, 'github_handoff')
TAB = os.path.join(GH, 'tables')
NUM = os.path.join(GH, 'numeric')
DYN = os.path.join(ROOT, 'v076_return', 'numeric', 'v076_dynamic_center_corrected.mat')
BATCH = 32
ALL24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
         for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)]
CACHED = {'D30_zf450_M400_a5': 'v083_fullROI_double_C400_D30_zf450_M400_a5.mat',
          'D30_zf550_M400_a5': 'v083_fullROI_double_C400_D30_zf550_M400_a5.mat',
          'D60_zf450_M400_a5': 'v083_fullROI_double_C400_D60_zf450_M400_a5.mat',
          'D100_zf450_M200_a20': 'v083_fullROI_double_C400_D100_zf450_M200_a20.mat',
          'D30_zf550_M400_a20': 'v084_double_C400_D30_zf550_M400_a20.mat',
          'D60_zf450_M400_a20': 'v084_double_C400_D60_zf450_M400_a20.mat'}


def build_map(D, zf, ttype, a, mem_log):
    Es, Eref = roi_blocks(D, zf)
    Lm, Dm_, Qm, Iref = qf_coefficients_grid(Es, Eref)
    del Es, Eref
    mem_log['qf_MB'] = round((Lm.nbytes + Dm_.nbytes + Qm.nbytes + Iref.nbytes) / 1e6, 1)
    tj = np.arange(N) / FS
    freq = 200.0 if ttype == 'M200' else 400.0
    x = a * np.cos(2 * np.pi * freq * tj)
    ia_all, wa_all, wb_all = lin_weights(x)
    S1 = np.zeros((41, 41)); SX = np.zeros((41, 41), dtype=np.complex128)
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
    X = SX - Im_map * np.sum(e)
    with np.errstate(invalid='ignore', divide='ignore'):
        C = 2.0 * X / (N * Im_map)
    pos = Im_map[(Im_map > 0) & np.isfinite(Im_map)]
    floor = 0.01 * np.median(pos)
    valid = np.isfinite(Im_map) & (Im_map > floor)
    Cm = np.full((41, 41), np.nan + 1j * np.nan)
    Cm[valid] = C[valid]
    return Cm, Im_map, valid, mem_log


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def g17(x):
    return '%.17g' % x


def main():
    f2 = h5py.File(DYN, 'r')
    rows = []
    n_new = 0
    maps = {}
    for key in ALL24:
        parts = key.split('_')
        D, zf, ttype, a = int(parts[0][1:]), int(parts[1][2:]), parts[2], int(parts[3][1:])
        try:
            if key in CACHED:
                p = os.path.join(NUM, CACHED[key])
                m = loadmat(p)
                Cm = m['C400_double']; mask = np.array(m['valid_mask'], dtype=bool)
                cid = str(m['case_id'].flatten()[0])
                if cid != key or Cm.shape != (41, 41) or mask.sum() != 1681:
                    raise ValueError('cache identity check failed')
                src_file, src_sha, kind = CACHED[key], sha256_file(p), 'INHERITED_CACHE'
                Cm = Cm.astype(np.complex128)
            else:
                t0 = time.time(); mem = {}
                Cm, Im_map, mask, mem = build_map(D, zf, ttype, a, mem)
                dt = time.time() - t0
                src_file = 'C400_double_%s.mat' % key
                p = os.path.join(NUM, src_file)
                savemat(p, {'C400_double': Cm, 'Imean_map': Im_map, 'valid_mask': mask,
                            'case_id': key, 'N': N, 'Fs': FS, 'k0': K0,
                            'note': 'v085 streamed double-precision QF map; orientation h5py axis1=MATLAB col / axis2=MATLAB row'},
                        do_compression=True)
                src_sha, kind = sha256_file(p), 'NEW_V085'
                n_new += 1
            # readback before VERIFIED
            if key in CACHED:
                m2 = loadmat(os.path.join(NUM, CACHED[key]))
                Cb = m2['C400_double']
            else:
                m2 = loadmat(os.path.join(NUM, src_file))
                Cb = m2['C400_double']
            rb_ok = Cb.shape == (41, 41) and np.isfinite(Cb[np.array(mask, dtype=bool)]).all()
            cm = f2[key]['C400'][:]
            Cs = cm['real'].astype(np.float64) + 1j * cm['imag'].astype(np.float64)
            common = (mask > 0) & np.isfinite(Cs.real) & np.isfinite(Cs.imag)
            rF = float(np.linalg.norm((Cb - Cs)[common]) / max(np.linalg.norm(Cs[common]), 1e-300))
            maps[key] = (Cb, Cs, mask, common)
            rows.append({
                'case_id': key, 'condition_type': ttype, 'a_nm': int(a), 'zf_nm': zf,
                'map_file': src_file, 'map_sha256': src_sha, 'map_origin': kind,
                'precision': 'double (streamed QF, batch=%d)' % BATCH if kind == 'NEW_V085' else 'double (inherited cache, identity verified)',
                'batch_frames': BATCH if kind == 'NEW_V085' else '',
                'n_valid_pixels': int((mask > 0).sum()),
                'rF_double_vs_single': g17(rF),
                'centre_C400_double_Re': g17(Cb[20, 20].real), 'centre_C400_double_Im': g17(Cb[20, 20].imag),
                'centre_abs_double': g17(abs(Cb[20, 20])), 'centre_abs_single': g17(abs(Cs[20, 20])),
                'centre_abs_diff': g17(abs(Cb[20, 20] - Cs[20, 20])),
                'L1_ROI_double': g17(float(np.sum(np.abs(Cb[common])))),
                'L2_ROI_double': g17(float(np.linalg.norm(Cb[common]))),
                'readback_ok': 'YES' if rb_ok else 'NO',
                'status': 'DOUBLE_MAP_VERIFIED' if rb_ok else 'FAILED_READBACK',
                'note': 'rF is a numerical-path diagnostic, not the old 2% physical gate'})
            print('  %-24s %-16s rF=%.3e' % (key, kind, rF))
        except Exception as exc:
            rows.append({'case_id': key, 'map_origin': 'FAILED', 'status': 'FAILED',
                         'note': 'exception: %s' % exc})
            print('  %-24s FAILED: %s' % (key, exc))
    f2.close()
    fields = ['case_id', 'condition_type', 'a_nm', 'zf_nm', 'map_file', 'map_sha256', 'map_origin',
              'precision', 'batch_frames', 'n_valid_pixels', 'rF_double_vs_single',
              'centre_C400_double_Re', 'centre_C400_double_Im', 'centre_abs_double',
              'centre_abs_single', 'centre_abs_diff', 'L1_ROI_double', 'L2_ROI_double',
              'readback_ok', 'status', 'note']
    with open(os.path.join(TAB, 'v085_double_maps24_status.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n'); w.writeheader(); w.writerows(rows)
    # double_vs_single table
    dvs = [{k: r.get(k, '') for k in ('case_id', 'map_origin', 'rF_double_vs_single',
            'centre_abs_double', 'centre_abs_single', 'centre_abs_diff',
            'L1_ROI_double', 'L2_ROI_double', 'status')} for r in rows if r['status'] == 'DOUBLE_MAP_VERIFIED']
    with open(os.path.join(TAB, 'v085_double_vs_single_24.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(dvs[0].keys()), lineterminator='\n'); w.writeheader(); w.writerows(dvs)
    # readback
    with open(os.path.join(TAB, 'v085_double_maps24_status.csv'), 'r', newline='', encoding='utf-8') as f:
        rr = list(csv.reader(f))
    assert len(rr) - 1 == 24 and all(len(x) == len(rr[0]) for x in rr)
    n_verified = sum(1 for r in rows if r['status'] == 'DOUBLE_MAP_VERIFIED')
    summary = {'phase': 'C', 'new_maps': n_new, 'verified': n_verified, 'of': 24,
               'full_set_complete': n_verified == 24}
    print('[C] summary:', json.dumps(summary))
    with open(os.path.join(GH, 'logs', 'v085_phase_c_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    with open(os.path.join(TAB, 'v085_double_maps24_status.csv'), 'r', newline='', encoding='utf-8') as f:
        assert len(list(csv.reader(f))) - 1 == 24


if __name__ == '__main__':
    main()
