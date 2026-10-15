# -*- coding: utf-8 -*-
"""v093 clean probe verification: 48 states x 4 pixels x 3 bins = 576 checks.
Independent field-first path (NOT the QF path used by the bank).
h5 convention: Es[pol, h5ax1=MATLAB_col, h5ax2=MATLAB_row].
Probe (i,j) = (h5ax1_idx, h5ax2_idx). Fine offset: 60+5*idx for each axis."""
import os, sys, csv, json, hashlib
import numpy as np
import h5py
from scipy.io import loadmat

GH = os.path.join(r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff')
ROOT = os.path.dirname(GH)
AN = os.path.join(GH, 'analysis')
TAB = os.path.join(GH, 'tables')
NUM = os.path.join(GH, 'numeric')
CACHE = os.path.join(ROOT, 'v074_return', 'numeric', 'render_cache')
N = 2001
FS = 5000.0
K0S = [80, 160, 320]
PROBES = [(20, 20), (20, 0), (0, 20), (25, 0)]
ALL48 = (['D%d_zf%d_%s_a%d' % (D, zf, t, a)
          for D in (30, 60, 100) for zf in (450, 550)
          for t in ('M200', 'M400') for a in (5, 20)] +
         ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
          for D in (30, 60, 100) for zf in (450, 550)
          for t in ('M200', 'M400') for a in (10, 15)])
XS = np.array([-20.0, -10.0, 0.0, 10.0, 20.0])
CACHED = {'D30_zf450_M400_a5': 'v083_fullROI_double_C400_D30_zf450_M400_a5.mat',
          'D30_zf550_M400_a5': 'v083_fullROI_double_C400_D30_zf550_M400_a5.mat',
          'D60_zf450_M400_a5': 'v083_fullROI_double_C400_D60_zf450_M400_a5.mat',
          'D100_zf450_M200_a20': 'v083_fullROI_double_C400_D100_zf450_M200_a20.mat',
          'D30_zf550_M400_a20': 'v084_double_C400_D30_zf550_M400_a20.mat',
          'D60_zf450_M400_a20': 'v084_double_C400_D60_zf450_M400_a20.mat'}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def g17(x):
    return '%.17g' % x


def get_probe_series(D, zf, a_nm, ttype, h5_i, h5_j):
    """Field-first: interpolate complex Es at 25 subpixels -> |Eref+Es|^2 -> mean."""
    freq = 200.0 if ttype == 'M200' else 400.0
    tj = np.arange(N) / FS
    xt = a_nm * np.cos(2 * np.pi * freq * tj)
    xc = np.clip(xt, -20.0, 20.0)
    ia = np.clip(np.searchsorted(XS, xc, side='right') - 1, 0, 3)
    wb = (xc - XS[ia]) / (XS[ia + 1] - XS[ia])
    wa = 1.0 - wb
    ib = ia + 1
    # fine grid offsets for this probe pixel
    col0 = 60 + 5 * h5_i  # h5ax1 = MATLAB col
    row0 = 60 + 5 * h5_j  # h5ax2 = MATLAB row
    Es_list = []
    Eref = None
    for x in XS:
        p = os.path.join(CACHE, 'D%d_zf%g_x%+g.mat' % (D, zf, x))
        with h5py.File(p, 'r') as f:
            Es_raw = f['a']['Es'][:]
            Eref_raw = f['a']['Eref'][:]
        def cx(arr):
            if arr.dtype.names:
                return arr['real'].astype(np.float64) + 1j * arr['imag'].astype(np.float64)
            return arr.astype(np.complex128)
        Es_i = cx(Es_raw)
        Eref_c = cx(Eref_raw)
        blk = Es_i[:, col0:col0+5, row0:row0+5]  # (pol, 5col, 5row)
        ref_blk = Eref_c[:, col0:col0+5, row0:row0+5]
        # transpose to (5row, 5col, pol) then flatten (25, 3)
        Es_list.append(np.transpose(blk, (1, 2, 0)).reshape(25, 3))
        if Eref is None:
            Eref = np.transpose(ref_blk, (1, 2, 0)).reshape(25, 3)
    Es_arr = np.stack(Es_list)  # (5, 25, 3)
    s = np.zeros(N)
    for b0 in range(0, N, 32):
        sl = slice(b0, min(b0 + 32, N))
        w1 = wa[sl][:, None, None]
        w2 = wb[sl][:, None, None]
        EsI = w1 * Es_arr[ia[sl]] + w2 * Es_arr[ib[sl]]
        It = np.sum(np.abs(Eref[None, :, :] + EsI) ** 2, axis=2)
        s[sl] = It.mean(axis=1)
    return s


def main():
    # Phase A: identity audit
    id_rows, rF_rows, probe_rows = [], [], []
    bank = {}
    n_bank_ok = 0
    for key in ALL48:
        fn = 'v092_bank_%s.mat' % key
        p = os.path.join(AN, 'bank', fn)
        sha = sha256_file(p)
        m = loadmat(p)
        C = np.asarray(m['C'], dtype=np.complex128)
        X = np.asarray(m['X'], dtype=np.complex128)
        Im = np.asarray(m['Imean_map'], dtype=np.float64)
        mask = np.asarray(m['valid_mask'], dtype=bool)
        cid = str(m['case_id'].flatten()[0])
        common = mask & (Im > 0)
        C_chk = 2.0 * X / (N * Im)[None]
        err = float(np.max(np.abs(C_chk[:, common] - C[:, common])))
        ok = (cid == key and C.shape == (3, 41, 41) and err < 1e-10)
        n_bank_ok += int(ok)
        bank[key] = (C, X, Im, mask)
        id_rows.append({'case_id': key, 'sha256': sha,
                        'C_eq_2X_max_err': g17(err), 'status': 'VERIFIED' if ok else 'FAILED'})
    for key in ALL48[:24]:
        old_fn = CACHED.get(key, 'C400_double_%s.mat' % key)
        old = loadmat(os.path.join(NUM, old_fn))
        Cold = np.asarray(old['C400_double'], dtype=np.complex128).reshape(-1)
        C160 = bank[key][0][1].reshape(-1)
        mask = bank[key][3].reshape(-1)
        rF = float(np.linalg.norm((C160 - Cold)[mask]) / max(np.linalg.norm(Cold[mask]), 1e-300))
        rF_rows.append({'case_id': key, 'rF_bin160_vs_old_C400': g17(rF),
                        'status': 'PASS' if rF < 1e-10 else 'FAIL'})

    # Phase B: probe verification
    n_ok = n_tot = 0
    evidence = {'probe_pixels_h5': np.array(PROBES)}
    for key in ALL48:
        p = key.split('_')
        D, zf, ttype, a_nm = int(p[0][1:]), int(p[1][2:]), p[2], float(p[3][1:])
        C_bank, X_bank, Im_bank, mask_bank = bank[key]
        for h5_i, h5_j in PROBES:
            s = get_probe_series(D, zf, a_nm, ttype, h5_i, h5_j)
            Im = float(s.mean())
            for ki, k0 in enumerate(K0S):
                e = np.exp(-2j * np.pi * k0 * np.arange(N) / N)
                X_indep = complex(np.sum((s - Im) * e))
                C_indep = 2.0 * X_indep / (N * Im) if Im != 0 else complex(np.nan)
                X_bp = X_bank[ki, h5_i, h5_j]
                C_bp = C_bank[ki, h5_i, h5_j]
                d_X = abs(X_indep - X_bp)
                d_C = abs(C_indep - C_bp)
                ok = d_X < 1e-8 and d_C < 1e-8
                n_tot += 1
                n_ok += int(ok)
                probe_rows.append({
                    'record_key': '%s|bin%d|px(%d,%d)' % (key, k0, h5_i, h5_j),
                    'case_id': key, 'k0': k0, 'pixel_h5': '(%d,%d)' % (h5_i, h5_j),
                    'X_indep_Re': g17(X_indep.real), 'X_indep_Im': g17(X_indep.imag),
                    'X_bank_Re': g17(X_bp.real), 'X_bank_Im': g17(X_bp.imag),
                    'abs_dX': g17(d_X), 'abs_dC': g17(d_C),
                    'gate': '< 1e-8 (cross-path FF vs QF)',
                    'status': 'PASS' if ok else 'FAIL'})
            sname = 'series_%s_h5_%d_%d' % (key, h5_i, h5_j)
            evidence[sname] = s
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
    for name, nexp, d in (('v093_bank_identity48.csv', 48, TAB),
                          ('v093_old_c160_rF24.csv', 24, TAB),
                          ('v093_probe_checks576.csv', 576, AN)):
        rr = list(csv.reader(open(os.path.join(d, name), encoding='utf-8', newline='')))
        assert len(rr) - 1 == nexp and all(len(x) == len(rr[0]) for x in rr), name
    print('[AB] bank %d/48 | probes %d/%d (gate 1e-8 cross-path)' % (n_bank_ok, n_ok, n_tot))
    with open(os.path.join(GH, 'logs', 'v093_phase_ab_summary.json'), 'w', encoding='utf-8') as f:
        json.dump({'bank_ok': n_bank_ok, 'probe_ok': n_ok, 'probe_total': n_tot,
                   'gate': '1e-8 cross-path'}, f, indent=2)


if __name__ == '__main__':
    main()
