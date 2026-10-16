# -*- coding: utf-8 -*-
"""v099: per-frequency three-path origin verification (fixing v098's k0=160-only bug).
Each (case, pixel, bin, origin) gets its own A/B/C computation at that bin's k0."""
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
ALL48 = (['D%d_zf%d_%s_a%d' % (D, zf, t, a)
          for D in (30, 60, 100) for zf in (450, 550)
          for t in ('M200', 'M400') for a in (5, 20)] +
         ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
          for D in (30, 60, 100) for zf in (450, 550)
          for t in ('M200', 'M400') for a in (10, 15)])
PROBES = [(20, 20), (20, 0), (0, 20), (25, 0)]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def wcsv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader(); w.writerows(rows)


def g17(x):
    return '%.17g' % x


def main():
    zs = np.load(os.path.join(AN, 'v093_probe_evidence.npz'))
    series_keys = sorted(k for k in zs.files if k.startswith('series_'))
    print('series count:', len(series_keys))

    all_rows = []
    n_pass = n_total = 0
    GATE = 1e-11
    origin_rows = []

    for skey in series_keys:
        parts = skey.replace('series_', '').split('_h5_')
        case_id = parts[0]; pix = parts[1]
        i5, j5 = int(pix.split('_')[0]), int(pix.split('_')[1])
        p = case_id.split('_')
        D, zf, ttype, a_nm = int(p[0][1:]), int(p[1][2:]), p[2], float(p[3][1:])
        freq_motion = 200.0 if ttype == 'M200' else 400.0
        s_full = zs[skey].astype(np.float64)
        g = s_full[:25].copy()

        # h5 -> fine grid offsets (h5ax1=col, h5ax2=row)
        col0 = 60 + 5 * i5
        row0 = 60 + 5 * j5

        # Load 5 anchors for this D/zf
        XS = np.array([-20.0, -10.0, 0.0, 10.0, 20.0])
        Es_list = []
        Eref = None
        for x in XS:
            pth = os.path.join(CACHE, 'D%d_zf%g_x%+g.mat' % (D, zf, x))
            with h5py.File(pth, 'r') as f:
                a = f['a']
                Es_raw = a['Es'][:]
                Eref_raw = a['Eref'][:]
            def cx(arr):
                if arr.dtype.names:
                    return arr['real'].astype(np.float64) + 1j * arr['imag'].astype(np.float64)
                return arr.astype(np.complex128)
            Es_i = cx(Es_raw); Eref_c = cx(Eref_raw)
            blk = Es_i[:, col0:col0+5, row0:row0+5]
            ref_blk = Eref_c[:, col0:col0+5, row0:row0+5]
            Es_list.append(np.transpose(blk, (1, 2, 0)).reshape(25, 3))
            if Eref is None:
                Eref = np.transpose(ref_blk, (1, 2, 0)).reshape(25, 3)
        Es_arr = np.stack(Es_list)  # (5, 25, 3)

        tj = np.arange(N) / FS
        xt = a_nm * np.cos(2 * np.pi * freq_motion * tj)
        xc = np.clip(xt, -20, 20)
        ia = np.clip(np.searchsorted(XS, xc, side='right') - 1, 0, 3)
        wb = (xc - XS[ia]) / (XS[ia + 1] - XS[ia])
        wa = 1.0 - wb
        ib = ia + 1

        # Build full series (field-first path)
        s_full = np.zeros(N)
        for b0 in range(0, N, 32):
            sl = slice(b0, min(b0 + 32, N))
            w1 = wa[sl][:, None, None]
            w2 = wb[sl][:, None, None]
            EsI = w1 * Es_arr[ia[sl]] + w2 * Es_arr[ib[sl]]
            It = np.sum(np.abs(Eref[None, :, :] + EsI) ** 2, axis=2)
            s_full[sl] = It.mean(axis=1)

        for ell in range(25):
            # Correct 25-point periodic reconstruction
            y = np.array([g[(jj + ell) % 25] for jj in range(N)], dtype=np.float64)
            Im_ell = float(y.mean())

            for k0 in K0S:
                # Path A: remainder sum at THIS bin's k0
                # Group j by j%25, sum DFT weights per group
                X_A = complex(0)
                for n in range(25):
                    j_vals = np.arange(n, N, 25)
                    g_val = g[(n + ell) % 25]
                    e_sum = np.sum(np.exp(-2j * np.pi * k0 * j_vals / N))
                    X_A += (g_val - Im_ell) * e_sum
                C_A = 2.0 * X_A / (N * Im_ell) if Im_ell != 0 else complex(0)

                # Path B: explicit FFT at THIS bin
                X_B = complex(np.fft.fft(y - Im_ell)[k0])
                C_B = 2.0 * X_B / (N * Im_ell)

                # Path C: tail identity at THIS bin
                y0 = np.array([g[jj % 25] for jj in range(N)], dtype=np.float64)
                Im0 = float(y0.mean())
                e0 = np.exp(-2j * np.pi * k0 * np.arange(N) / N)
                X0 = complex(np.sum((y0 - Im0) * e0))
                phase = np.exp(2j * np.pi * k0 * ell / N)
                tail_sum = complex(0)
                for r in range(ell):
                    tail_sum += (g[r + 1] - g[r]) * np.exp(-2j * np.pi * k0 * (N - ell + r) / N)
                d_mean = (g[ell] - g[0]) / N
                sum_e = np.sum(e0)
                X_C = phase * X0 + tail_sum - d_mean * sum_e
                C_C = 2.0 * X_C / (N * Im_ell)

                d_AB = abs(X_A - X_B)
                d_AC = abs(X_A - X_C)
                d_BC = abs(X_B - X_C)
                ok = d_AB < GATE and d_AC < GATE and d_BC < GATE
                n_total += 1
                n_pass += int(ok)

                all_rows.append({
                    'record_key': '%s|bin%d|px(%s)|ell%d' % (case_id, k0, pix, ell),
                    'case_id': case_id, 'k0': k0, 'pixel': pix, 'origin_ell': ell,
                    'X_A_Re': g17(X_A.real), 'X_A_Im': g17(X_A.imag),
                    'X_B_Re': g17(X_B.real), 'X_B_Im': g17(X_B.imag),
                    'X_C_Re': g17(X_C.real), 'X_C_Im': g17(X_C.imag),
                    'C_A_Re': g17(C_A.real), 'C_A_Im': g17(C_A.imag),
                    'C_B_Re': g17(C_B.real), 'C_B_Im': g17(C_B.imag),
                    'C_C_Re': g17(C_C.real), 'C_C_Im': g17(C_C.imag),
                    'Im_ell': g17(Im_ell),
                    'd_AB': g17(d_AB), 'd_AC': g17(d_AC), 'd_BC': g17(d_BC),
                    'abs_C_A': g17(abs(C_A)),
                    'status': 'PASS' if ok else 'FAIL'})

                origin_rows.append({
                    'record_key': '%s|bin%d|px(%s)|ell%d' % (case_id, k0, pix, ell),
                    'case_id': case_id, 'k0': k0, 'pixel': pix, 'origin_ell': ell,
                    'abs_C_A': g17(abs(C_A)), 'abs_C_B': g17(abs(C_B)), 'abs_C_C': g17(abs(C_C))})

    # Write results
    wcsv(os.path.join(AN, 'v099_origin_threeway14400.csv'),
         list(all_rows[0].keys()), all_rows)
    wcsv(os.path.join(AN, 'v099_origin_per_freq.csv'),
         list(origin_rows[0].keys()), origin_rows)
    np.savez_compressed(os.path.join(AN, 'v099_origin_evidence.npz'),
                        source_sha='49c10f1b24c6798f745dd8b7f1409b0472912761ac639b71566f9c1e800582be',
                        **{r['record_key']: np.array([float(r['X_A_Re']), float(r['X_A_Im']),
                                                       float(r['X_B_Re']), float(r['X_B_Im']),
                                                       float(r['X_C_Re']), float(r['X_C_Im'])])
                           for r in all_rows})

    # Summary
    n_14400 = len(all_rows)
    per_bin = {}
    for r in all_rows:
        b = r['k0']
        per_bin.setdefault(b, {'pass': 0, 'total': 0})
        per_bin[b]['total'] += 1
        per_bin[b]['pass'] += int(r['status'] == 'PASS')

    print('[v099 core] three-frequency three-way:')
    for b in sorted(per_bin):
        print('  bin %d: %d/%d PASS' % (b, per_bin[b]['pass'], per_bin[b]['total']))
    print('  TOTAL: %d/%d PASS (gate 1e-11)' % (n_pass, n_total))
    with open(os.path.join(GH, 'logs', 'v099_core_summary.json'), 'w', encoding='utf-8') as f:
        json.dump({'total': n_total, 'pass': n_pass,
                   'per_bin': {str(b): d for b, d in sorted(per_bin.items())},
                   'gate': '1e-11'}, f, indent=2)
    if n_pass < n_total:
        sys.exit(2)


if __name__ == '__main__':
    main()
