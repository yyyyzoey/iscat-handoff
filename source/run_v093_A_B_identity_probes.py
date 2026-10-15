# -*- coding: utf-8 -*-
"""v093 Phase A+B: 48-bank identity audit + 48-state 4-pixel independent
field-first verification (576 complex checks). Zero BEM/render/BMP."""
import os, sys, csv, json, hashlib
import numpy as np
import h5py
from scipy.io import loadmat

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v083_common import ROOT, fine_slice

GH = os.path.join(ROOT, 'github_handoff')
AN = os.path.join(GH, 'analysis')
TAB = os.path.join(GH, 'tables')
BANK = os.path.join(AN, 'bank')
NUM = os.path.join(GH, 'numeric')
CACHE = os.path.join(ROOT, 'v074_return', 'numeric', 'render_cache')
FS = 5000.0
N = 2001
K0S = [80, 160, 320]
PROBES = [(20, 20), (20, 0), (0, 20), (25, 0)]
ALL48 = (['D%d_zf%d_%s_a%d' % (D, zf, t, a)
          for D in (30, 60, 100) for zf in (450, 550)
          for t in ('M200', 'M400') for a in (5, 20)] +
         ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
          for D in (30, 60, 100) for zf in (450, 550)
          for t in ('M200', 'M400') for a in (10, 15)])


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def g17(x):
    return '%.17g' % x


def load_anchor_block(D, zf, x, r0, c0):
    """Load 25-subpixel x 3-pol complex Es block for one anchor."""
    p = os.path.join(CACHE, 'D%d_zf%g_x%+g.mat' % (D, zf, x))
    with h5py.File(p, 'r') as f:
        a = f['a']
        Es_raw = a['Es'][:]
        Eref_raw = a['Eref'][:]
    # h5py: (pol, h5ax1=MATLAB col, h5ax2=MATLAB row)
    def cx(arr):
        if arr.dtype.names:
            return arr['real'].astype(np.float64) + 1j * arr['imag'].astype(np.float64)
        return arr.astype(np.complex128)
    Es_i = cx(Es_raw)
    Eref_c = cx(Eref_raw)
    blk = Es_i[:, c0:c0+5, r0:r0+5]  # (3,5,5) h5 order
    ref_blk = Eref_c[:, c0:c0+5, r0:r0+5]
    # transpose (1,2,0) -> (5,5,3) then reshape (25,3)
    return np.transpose(blk, (1, 2, 0)).reshape(25, 3), \
           np.transpose(ref_blk, (1, 2, 0)).reshape(25, 3)


def field_first_series(D, zf, ttype, a_nm, probe_h5):
    """Independent field-first path: interpolate complex Es -> |Eref+Es|^2 -> 25-subpixel mean."""
    i, j = probe_h5  # h5 axis1, axis2 indices
    freq = 200.0 if ttype == 'M200' else 400.0
    tj = np.arange(N) / FS
    xt = float(a_nm) * np.cos(2 * np.pi * freq * tj)
    XS = np.array([-20.0, -10.0, 0.0, 10.0, 20.0])
    Es_list = []
    Eref = None
    for x in XS:
        Es_blk, Eref_blk = load_anchor_block(D, zf, x, i5, j5)
        Es_list.append(Es_blk)
        if Eref is None:
            Eref = Eref_blk
    Es_arr = np.stack(Es_list)  # (5, 25, 3)
    # lin weights
    xc = np.clip(xt, XS[0], XS[-1])
    ia = np.searchsorted(XS, xc, side='right') - 1
    ia = np.clip(ia, 0, 3)
    wb = (xc - XS[ia]) / (XS[ia + 1] - XS[ia])
    wa = 1.0 - wb
    ib = ia + 1
    N_out = N
    result = np.zeros(N_out)
    for b0 in range(0, N_out, 32):
        sl = slice(b0, min(b0 + 32, N_out))
        w1 = wa[sl][:, None, None]
        w2 = wb[sl][:, None, None]
        EsI = w1 * Es_arr[ia[sl]] + w2 * Es_arr[ib[sl]]  # (B, 25, 3)
        It = np.sum(np.abs(Eref[None, :, :] + EsI) ** 2, axis=2)  # (B, 25)
        result[sl] = It.mean(axis=1)
    return result


def main():
    ALL24_ENDPOINT = ALL48[:24]
    # ---- Phase A: 48-bank identity audit ----
    id_rows = []
    bank_data = {}
    n_ok = 0
    for key in ALL48:
        fn = 'v092_bank_%s.mat' % key
        p = os.path.join(BANK, fn)
        sha = sha256_file(p)
        m = loadmat(p)
        C = np.asarray(m['C'], dtype=np.complex128)
        X = np.asarray(m['X'], dtype=np.complex128)
        Im = np.asarray(m['Imean_map'], dtype=np.float64)
        mask = np.asarray(m['valid_mask'], dtype=bool)
        cid = str(m['case_id'].flatten()[0])
        N_f = float(np.asarray(m['N']).flatten()[0])
        Fs_f = float(np.asarray(m['Fs']).flatten()[0])
        k0s = np.asarray(m['k0_bins']).flatten().tolist()
        a_f = float(np.asarray(m['a_nm']).flatten()[0])
        # verify C = 2X/(N*Im)
        common = mask & np.isfinite(Im) & (Im > 0)
        C_re = 2.0 * X / (N_f * Im)[None]
        err_c = float(np.max(np.abs(C_re[:, common] - C[:, common]))) if common.any() else 0
        c_ok = err_c < 1e-10
        # mask rule
        pos = Im[(np.isfinite(Im)) & (Im > 0)]
        floor = 0.01 * float(np.median(pos)) if pos.size else 0
        mask_ok = bool((mask == (np.isfinite(Im) & (Im > floor))).all())
        p_ok = (cid == key and C.shape == (3, 41, 41) and N_f == 2001 and
                Fs_f == 5000.0 and k0s == [80, 160, 320] and
                abs(a_f - float(key.split('_')[-1][1:])) < 0.5)
        ok = c_ok and mask_ok and p_ok
        n_ok += int(ok)
        bank_data[key] = {'C': C, 'X': X, 'Im': Im, 'mask': mask, 'sha': sha}
        id_rows.append({'case_id': key, 'sha256': sha,
                        'internal_case_id_match': 'YES' if cid == key else 'NO',
                        'shape_ok': 'YES' if C.shape == (3, 41, 41) else 'NO',
                        'C_eq_2X_over_NIm_max_err': g17(err_c),
                        'C_eq_2X_over_NIm_gate': '< 1e-10',
                        'C_eq_2X_status': 'PASS' if c_ok else 'FAIL',
                        'mask_rule_status': 'PASS' if mask_ok else 'FAIL',
                        'params_ok': 'YES' if p_ok else 'NO',
                        'status': 'BANK_IDENTITY_VERIFIED' if ok else 'BANK_IDENTITY_FAILED'})
    # 24 old C160 rF for endpoints
    CACHED = {'D30_zf450_M400_a5': 'v083_fullROI_double_C400_D30_zf450_M400_a5.mat',
              'D30_zf550_M400_a5': 'v083_fullROI_double_C400_D30_zf550_M400_a5.mat',
              'D60_zf450_M400_a5': 'v083_fullROI_double_C400_D60_zf450_M400_a5.mat',
              'D100_zf450_M200_a20': 'v083_fullROI_double_C400_D100_zf450_M200_a20.mat',
              'D30_zf550_M400_a20': 'v084_double_C400_D30_zf550_M400_a20.mat',
              'D60_zf450_M400_a20': 'v084_double_C400_D60_zf450_M400_a20.mat'}
    rF_rows = []
    for key in ALL48[:24]:
        old_fn = CACHED.get(key, 'C400_double_%s.mat' % key)
        old = loadmat(os.path.join(NUM, old_fn))
        Cold = np.asarray(old['C400_double'], dtype=np.complex128).reshape(-1)
        Cnew = bank_data[key]['C'][1].reshape(-1)
        mask = bank_data[key]['mask'].reshape(-1)
        rF = float(np.linalg.norm((Cnew - Cold)[mask]) / max(np.linalg.norm(Cold[mask]), 1e-300))
        rF_rows.append({'case_id': key, 'rF_bin160_vs_old_C400': g17(rF),
                        'gate': '< 1e-10', 'status': 'PASS' if rF < 1e-10 else 'FAIL'})
    with open(os.path.join(TAB, 'v093_bank_identity48.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(id_rows[0].keys()), lineterminator='\n')
        w.writeheader(); w.writerows(id_rows)
    with open(os.path.join(TAB, 'v093_old_c160_rF24.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rF_rows[0].keys()), lineterminator='\n')
        w.writeheader(); w.writerows(rF_rows)
    print('[A] bank identity: %d/48 verified' % n_ok)

    # ---- Phase B: 48-state 4-pixel independent field-first verification ----
    probe_rows = []
    n_probe_ok = 0
    n_probe_total = 0
    # group by D/zf to share anchor loading
    from collections import defaultdict
    by_dzf = defaultdict(list)
    for key in ALL48:
        p = key.split('_')
        D, zf = int(p[0][1:]), int(p[1][2:])
        by_dzf[(D, zf)].append(key)
    evidence = {'probe_pixels_h5': np.array(PROBES),
                'source_video_sha256': '49c10f1b24c6798f745dd8b7f1409b0472912761ac639b71566f9c1e800582be'}
    for (D, zf), keys in sorted(by_dzf.items()):
        # load 5 anchors once per D/zf
        XS = np.array([-20.0, -10.0, 0.0, 10.0, 20.0])
        anchors_Es = []
        anchors_Eref = None
        for x in XS:
            Es_blk, Eref_blk = load_anchor_block(D, zf, x, 60, 60)  # full ROI start
            anchors_Es.append(Es_blk)
            if anchors_Eref is None:
                anchors_Eref = Eref_blk
        # for each probe pixel, extract from the FULL ROI blocks
        # probe h5 (i,j) -> fine row 60+5i..60+5i+4, col 60+5j..60+5j+4
        probe_series = {}
        for pi, (i5, j5) in enumerate(PROBES):
            # within the 205x205 ROI block: sub-block start
            ri = 5 * i5  # 0-based within ROI block (205x205)
            ci = 5 * j5
            for key in keys:
                p = key.split('_')
                ttype = p[2]; a_nm = float(p[3][1:])
                freq = 200.0 if ttype == 'M200' else 400.0
                tj = np.arange(N) / FS
                xt = a_nm * np.cos(2 * np.pi * freq * tj)
                xc = np.clip(xt, -20, 20)
                ia = np.searchsorted(XS, xc, side='right') - 1
                ia = np.clip(ia, 0, 3)
                wb = (xc - XS[ia]) / (XS[ia + 1] - XS[ia])
                wa = 1.0 - wb
                ib = ia + 1
                s = np.zeros(N)
                for b0 in range(0, N, 32):
                    sl = slice(b0, min(b0 + 32, N))
                    # Extract from per-anchor Es at this probe pixel
                    # anchors_Es[a] is (25,3) for full ROI start (60,60)
                    # For probe (i5,j5) we need rows 5*i5..5*i5+4 within the 205x205 ROI
                    # But we loaded the full ROI block. Let me re-extract.
                    pass
                # Simpler: extract probe pixel from each anchor's 25-subpixel block
                # The probe pixel in the ROI block: fine offset = 5*(i5) within ROI
                # We need to go back to the original anchor arrays
                pass
            # Too complex inline; use the simpler approach: for each probe pixel,
            # load the 25-subpixel block from each anchor directly
            for key in keys:
                p = key.split('_')
                ttype = p[2]; a_nm = float(p[3][1:])
                freq = 200.0 if ttype == 'M200' else 400.0
                tj = np.arange(N) / FS
                xt = a_nm * np.cos(2 * np.pi * freq * tj)
                xc = np.clip(xt, -20, 20)
                ia_arr = np.searchsorted(XS, xc, side='right') - 1
                ia_arr = np.clip(ia_arr, 0, 3)
                wb_arr = (xc - XS[ia_arr]) / (XS[ia_arr + 1] - XS[ia_arr])
                wa_arr = 1.0 - wb_arr
                ib_arr = ia_arr + 1
                # load 25-subpixel block for this probe pixel from each anchor
                Es_list = []
                Eref = None
                for x in XS:
                    Es_blk, Eref_blk = load_anchor_block(D, zf, x, i5, j5)
                    Es_list.append(Es_blk)
                    if Eref is None:
                        Eref = Eref_blk
                Es_arr = np.stack(Es_list)  # (5, 25, 3)
                s = np.zeros(N)
                for b0 in range(0, N, 32):
                    sl = slice(b0, min(b0 + 32, N))
                    w1 = wa_arr[sl][:, None, None]
                    w2 = wb_arr[sl][:, None, None]
                    EsI = w1 * Es_arr[ia_arr[sl]] + w2 * Es_arr[ib_arr[sl]]
                    It = np.sum(np.abs(Eref[None, :, :] + EsI) ** 2, axis=2)
                    s[sl] = It.mean(axis=1)
                sname = 'series_h5_%02d_%02d' % (i5, j5)
                probe_series.setdefault(key, {})[sname] = s
        # Now verify against bank
        for key in keys:
            C_bank = bank_data[key]['C']
            X_bank = bank_data[key]['X']
            Im_bank = bank_data[key]['Im']
            mask_bank = bank_data[key]['mask']
            for pi, (i5, j5) in enumerate(PROBES):
                sname = 'series_h5_%02d_%02d' % (i5, j5)
                s = probe_series[key][sname]
                Im = float(s.mean())
                for ki, k0 in enumerate(K0S):
                    e = np.exp(-2j * np.pi * k0 * np.arange(N) / N)
                    X_indep = complex(np.sum((s - Im) * e))
                    C_indep = 2.0 * X_indep / (N * Im) if Im != 0 else complex(np.nan)
                    X_bank_px = X_bank[ki, i5, j5]
                    C_bank_px = C_bank[ki, i5, j5]
                    d_X = abs(X_indep - X_bank_px)
                    d_C = abs(C_indep - C_bank_px)
                    ok = d_X < 1e-8 and d_C < 1e-8  # cross-path (FF vs QF) tolerance
                    n_probe_total += 1
                    n_probe_ok += int(ok)
                    probe_rows.append({
                        'record_key': '%s|%d|px(%d,%d)' % (key, k0, i5, j5),
                        'case_id': key, 'k0': k0,
                        'pixel_h5': '(%d,%d)' % (i5, j5),
                        'X_indep_Re': g17(X_indep.real), 'X_indep_Im': g17(X_indep.imag),
                        'X_bank_Re': g17(X_bank_px.real), 'X_bank_Im': g17(X_bank_px.imag),
                        'abs_dX': g17(d_X), 'abs_dC': g17(d_C),
                        'gate': '< 1e-8 (cross-path FF vs QF)', 'status': 'PASS' if ok else 'FAIL'})
        # save probe series for this D/zf group
        for key in keys:
            for sname, s in probe_series.get(key, {}).items():
                evidence['%s|%s' % (key, sname)] = s
    # save evidence
    np.savez_compressed(os.path.join(AN, 'v093_probe_evidence.npz'), **evidence)
    with open(os.path.join(AN, 'v093_probe_checks576.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(probe_rows[0].keys()), lineterminator='\n')
        w.writeheader(); w.writerows(probe_rows)
    with open(os.path.join(TAB, 'v093_bank_identity48.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(id_rows[0].keys()), lineterminator='\n')
        w.writeheader(); w.writerows(id_rows)
    with open(os.path.join(TAB, 'v093_old_c160_rF24.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rF_rows[0].keys()), lineterminator='\n')
        w.writeheader(); w.writerows(rF_rows)
    # readback
    for name, nexp in (('v093_bank_identity48.csv', 48),
                       ('v093_old_c160_rF24.csv', 24),
                       ('v093_probe_checks576.csv', 576)):
        with open(os.path.join(TAB if 'identity' in name or 'rF' in name else AN, name),
                  'r', newline='', encoding='utf-8') as f:
            rr = list(csv.reader(f))
        assert len(rr) - 1 == nexp and all(len(x) == len(rr[0]) for x in rr), name
    print('[AB] summary:', json.dumps({
        'bank_identity': '%d/48' % n_ok,
        'old_c160_rF': '24 rows',
        'probe_checks': '%d/%d PASS' % (n_probe_ok, n_probe_total)}))
    with open(os.path.join(GH, 'logs', 'v093_phase_ab_summary.json'), 'w', encoding='utf-8') as f:
        json.dump({'bank_ok': n_ok, 'probe_ok': n_probe_ok, 'probe_total': n_probe_total}, f, indent=2)
    if n_ok < 48 or n_probe_ok < n_probe_total:
        sys.exit(2)


if __name__ == '__main__':
    main()
