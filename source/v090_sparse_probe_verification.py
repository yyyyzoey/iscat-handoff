# -*- coding: utf-8 -*-
"""v090 Phase D: independent sparse QR verification on 12 pre-registered
pixels - ONE sparse HDF5 read session (12 x 2001 samples; no BMP reread).

For each of the 4 fit entries (2 windows x {D2 joint7, D3 joint8_trend}) the
12-pixel RHS is solved via explicit QR and compared against np.linalg.lstsq
and against the original NPZ per-pixel values. Per model/window/frequency the
column projections and residual closure are recorded in DFT-count units.
Gate: same-input double-precision complex amplitude abs diff < 1e-11."""
import os, sys, csv, json, hashlib
import numpy as np
import h5py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v090_frequency_key_aggregator import full_key, FREQS, WINDOWS, MODELS

GH = os.path.join(r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff')
AN = os.path.join(GH, 'analysis')
NUM = os.path.join(GH, 'numeric')
NPZ = os.path.join(AN, 'v089_estimator_comparison_arrays.npz')
SMALL = os.path.join(NUM, 'fft400_corrected_small_roi.mat')
PROBES = [(0, 0), (0, 40), (40, 0), (40, 40), (20, 20), (20, 0),
          (0, 20), (5, 10), (10, 5), (33, 7), (7, 33), (15, 25)]
FS = 5000.0
WINDOWS = [('W1', 0, 1000), ('W2', 1000, 2001)]
FREQS = [200.0, 400.0, 420.0]


def g17(x):
    return '%.17g' % x


def main():
    # sparse read session (12 pixels x 2001 samples)
    with h5py.File(SMALL, 'r') as f:
        series = {px: np.asarray(f['roiFrames'][:, 0, px[0], px[1]], dtype=np.float64)
                  for px in PROBES}
    z = np.load(NPZ)
    common = z['common_mask'].astype(bool)
    probe_mask = np.zeros(41 * 41, dtype=bool)
    idx = []
    for (i, j) in PROBES:
        flat = i * 41 + j
        probe_mask[flat] = True
        idx.append(flat)

    id_rows, clo_rows, evidence = [], [], {}
    all_ok = True
    for wname, lo, hi in WINDOWS:
        jg = np.arange(lo, hi, dtype=np.float64)
        S = np.column_stack([series[px][lo:hi] for px in PROBES])   # (Nw, 12), window slice
        for model, trend in (('D2_joint7', False), ('D3_joint8_trend', True)):
            cols = [np.ones_like(jg)]
            for f in FREQS:
                cols.append(np.cos(2 * np.pi * f * jg / FS))
                cols.append(np.sin(2 * np.pi * f * jg / FS))
            if trend:
                cols.append((jg - jg.mean()) / ((jg.max() - jg.min()) / 2.0))
            B = np.column_stack(cols)
            # explicit QR vs lstsq
            Q, R = np.linalg.qr(B)
            beta_qr = np.linalg.solve(R, Q.T @ S)
            beta_ls, _, _, _ = np.linalg.lstsq(B, S, rcond=None)
            d_qr_ls = float(np.max(np.abs(beta_qr - beta_ls)))
            resid = S - B @ beta_qr
            e = np.exp(-2j * np.pi * np.asarray(FREQS)[:, None] * jg[None, :] / FS)
            Bc = B - B.mean(axis=0, keepdims=True)
            K = e @ Bc
            X_model = K @ beta_qr
            rc = resid - resid.mean(axis=0, keepdims=True)
            X_res = e @ rc
            X_obs = e @ (S - S.mean(axis=0, keepdims=True))
            for k, f in enumerate(FREQS):
                a = beta_qr[1 + 2 * k, :]; b = beta_qr[2 + 2 * k, :]
                C_qr = (a - 1j * b) / z['Imean_full'].reshape(-1)[idx]  # D2/D3 contract: COMMON full-record denominator
                C_npz = z[full_key(model, wname, f)].reshape(-1)[idx]
                d_npz = float(np.max(np.abs(C_qr - C_npz)))
                ok = d_npz < 1e-11
                all_ok &= ok
                id_rows.append({
                    'record_key': '%s|%s|%d' % (wname, model, int(f)), 'window': wname, 'model': model, 'freq_Hz': '%.1f' % f,
                    'n_probes': 12,
                    'max_abs_diff_qr_vs_lstsq': g17(d_qr_ls),
                    'max_abs_diff_qr_vs_npz': g17(d_npz),
                    'max_abs_C_npz_probe': g17(float(np.max(np.abs(C_npz)))),
                    'gate': 'abs < 1e-11 (same-input double precision)',
                    'status': 'PASS' if ok else 'FAIL'})
                closure = X_obs[k] - X_model[k] - X_res[k]
                ok_c = bool((np.abs(closure) < 1e-10).all())
                all_ok &= ok_c
                clo_rows.append({
                    'record_key': '%s|%s|%d' % (wname, model, int(f)), 'window': wname, 'model': model, 'freq_Hz': '%.1f' % f,
                    'n_probes': 12,
                    'max_abs_closure_DFT_count': g17(float(np.max(np.abs(closure)))),
                    'gate': 'abs < 1e-10 DFT count (sparse 12-pixel check)',
                    'status': 'PASS' if ok_c else 'FAIL'})
            evidence['%s|%s|beta_qr' % (model, wname)] = beta_qr
            evidence['%s|%s|resid' % (model, wname)] = resid
            evidence['%s|%s|B' % (model, wname)] = B
    for (i, j), px in zip(PROBES, PROBES):
        evidence['series_h5_%02d_%02d' % (i, j)] = series[px]
    evidence['probe_pixels_h5'] = np.array(PROBES)
    evidence['source_sha256'] = sha256_file(SMALL)
    np.savez_compressed(os.path.join(AN, 'v090_sparse_probe_evidence.npz'), **evidence)

    with open(os.path.join(AN, 'v090_probes12_frequency_identity.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['record_key'] + [k for k in id_rows[0].keys() if k != 'record_key'], lineterminator='\n')
        w.writeheader(); w.writerows(id_rows)
    with open(os.path.join(AN, 'v090_probes12_complex_closure.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['record_key'] + [k for k in clo_rows[0].keys() if k != 'record_key'], lineterminator='\n')
        w.writeheader(); w.writerows(clo_rows)
    # readback
    for name, nexp in (('v090_probes12_frequency_identity.csv', 12),
                       ('v090_probes12_complex_closure.csv', 12)):
        with open(os.path.join(AN, name), 'r', newline='', encoding='utf-8') as f:
            rr = list(csv.reader(f))
        assert len(rr) - 1 == nexp and all(len(x) == len(rr[0]) for x in rr), name
        assert len({x[0] for x in rr[1:]}) == nexp, name
    print('[D] summary:', json.dumps({'id_rows': len(id_rows), 'closure_rows': len(clo_rows),
                                      'all_pass': bool(all_ok),
                                      'scope': '12 fixed pixels only; NOT a full-ROI time-domain re-verification'}))
    with open(os.path.join(GH, 'logs', 'v089_phase_d_summary.json'), 'w', encoding='utf-8') as f:
        pass
    with open(os.path.join(GH, 'logs', 'v090_phase_d_summary.json'), 'w', encoding='utf-8') as f:
        json.dump({'sparse_session': 1, 'probes': 12, 'fit_entries': 4,
                   'all_pass': bool(all_ok)}, f, indent=2)
    if not all_ok:
        sys.exit(2)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


if __name__ == '__main__':
    main()
