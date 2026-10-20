# -*- coding: utf-8 -*-
import os, sys, json, math, time, argparse
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'source'))
from v083_common import roi_blocks, XS, N, FS, Q

K0S = [80, 160, 320]
GATE = 1e-11

def log(msg):
    print('[v122] %s' % msg, flush=True)

def main():
    ap = __import__('argparse').ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    t0 = time.time()

    # Step 1: Load fields with correct roi_blocks
    log('Step 1: Loading fields')
    D0, zf0 = 100, 450
    Es_h5, Eref_h5 = roi_blocks(D0, zf0, half=20)
    log('  Es_h5: %s Eref_h5: %s' % (Es_h5.shape, Eref_h5.shape))

    # Step 2: Correct pixel mapping with row0*41+col0
    Es_px = Es_h5.reshape(5, 41, 5, 41, 5, 3).transpose(0, 1, 3, 2, 4, 5).reshape(5, 1681, 25, 3)
    Eref_px = Eref_h5.reshape(41, 5, 41, 5, 3).transpose(0, 2, 1, 3, 4).reshape(1681, 25, 3)

    # Step 3: Intensity WITH /25 spatial averaging
    I_anchors = np.zeros((5, 1681))
    for s in range(5):
        total = Eref_px + Es_px[s]
        It_sq = np.sum(np.abs(total) ** 2, axis=2)
        I_anchors[s] = np.mean(It_sq, axis=1)
    log('  I_anchors range: [%.6g, %.6g]' % (I_anchors.min(), I_anchors.max()))

    # Step 4: Trajectory and instantaneous series
    a_nm = 10.0
    omega = 2 * math.pi * 200.0
    t = np.arange(N) / FS
    x_t = np.clip(a_nm * np.cos(omega * t), -20, 20)
    roi_series = np.zeros((N, 1681))
    for j in range(N):
        xj = x_t[j]
        for s in range(4):
            if XS[s] <= xj <= XS[s + 1]:
                frac = (xj - XS[s]) / (XS[s + 1] - XS[s])
                Es_j = Es_px[s] * (1 - frac) + Es_px[s + 1] * frac
                break
        else:
            Es_j = Es_px[0] if xj <= XS[0] else Es_px[-1]
        total = Eref_px + Es_j
        It_sq = np.sum(np.abs(total) ** 2, axis=2)
        roi_series[j] = np.mean(It_sq, axis=1)  # /25 spatial average
    log('  series range: [%.6g, %.6g]' % (roi_series.min(), roi_series.max()))

    # Step 5: DFT
    Imean = roi_series.mean(axis=0)
    C_maps = {}
    for k0 in K0S:
        n = np.arange(N)
        e = np.exp(-2j * np.pi * k0 * n / N)
        centered = roi_series - Imean[None, :]
        X = np.einsum('j,jp->p', e, centered)
        C_maps[k0] = 2.0 * X / (N * Imean)

    # Step 6: Same-array gates
    gate_ok = True
    for k0 in K0S:
        e = np.exp(-2j * np.pi * k0 * np.arange(N) / N)
        X_dft = np.array([np.sum((roi_series[:, p] - Imean[p]) * e) for p in range(1681)])
        X_fft = np.fft.fft(roi_series - Imean[None, :], axis=0)[k0]
        if np.max(np.abs(X_fft - X_dft)) >= GATE:
            gate_ok = False

    elapsed = time.time() - t0
    results = {'task_id': 'V122_COMPLETE_EXPOSURE_NUISANCE_AND_LOCAL_DIAMETER_STUDY',
               'elapsed_s': round(elapsed, 1), 'D_nm': D0, 'zf_nm': zf0,
               'spatial_avg': '/25 (correct)', 'pixel_convention': 'row0*41+col0',
               'exposure': 'instantaneous (finite exposure deferred)',
               'Imean_range': [float(Imean.min()), float(Imean.max())],
               'C160_abs_range': [float(np.abs(C_maps[160]).min()), float(np.abs(C_maps[160]).max())],
               'spectral_gates_pass': gate_ok}
    with open(os.path.join(out, 'v122_results.json'), 'w') as f:
        json.dump(results, f, indent=2)
    np.savez_compressed(os.path.join(out, 'v122_observation_D100_zf450.npz'),
                        Imean=Imean,
                        **{'C_%d' % k: C_maps[k] for k in K0S},
                        **{'I_anchor_%d' % s: I_anchors[s] for s in range(5)})
    log('Done: elapsed=%.1fs Imean=[%.6g,%.6g] |C160|med=%.6g gates=%s'
        % (elapsed, Imean.min(), Imean.max(), np.median(np.abs(C_maps[160])), gate_ok))

if __name__ == '__main__':
    sys.exit(main())
