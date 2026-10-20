# -*- coding: utf-8 -*-
import os, sys, csv, json, hashlib, shutil, math, subprocess, zipfile, time, argparse, io
sys.dont_write_bytecode = True
import numpy as np
from scipy.io import loadmat
import h5py

TASK_ID = 'V120_EXECUTABLE_CACHE_AND_LOCAL_RESPONSE'
EXPECTED_V119 = '1b449d86e44f8ebe8a3444ada80c27819b9b3fbd'
EXPECTED_V118 = '974c64ec06fdbe7905d0b9320f6edb49999f43c0'
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'v074_return', 'numeric', 'render_cache')
CACHE = os.path.normpath(CACHE)
N = 2001
FS = 5000.0
K0S = [80, 160, 320]
ROI_HALF = 20
GATE_XC = 1e-11
GATE_MEAN = 1e-12

def log(msg):
    print('[v120] %s' % msg, flush=True)

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def blob_sha1_bytes(data):
    import hashlib
    h = hashlib.sha1()
    h.update(b'blob %d\\x00' % len(data))
    h.update(data)
    return h.hexdigest()

def load_cache_field(D, zf, x_offset):
    fn = os.path.join(CACHE, 'D%d_zf%d_x%+.0f.mat' % (D, zf, x_offset))
    if not os.path.isfile(fn):
        raise FileNotFoundError(fn)
    with h5py.File(fn, 'r') as h:
        Es_c = h['a/Es'][:]
        Eref_c = h['a/Eref'][:]
    Es = Es_c['real'] + 1j * Es_c['imag']
    Eref = Eref_c['real'] + 1j * Eref_c['imag']
    return Es, Eref

def interpolate_es(Es_list, x_positions, x_target):
    if len(Es_list) == 1:
        return Es_list[0]
    for i in range(len(x_positions) - 1):
        if x_positions[i] <= x_target <= x_positions[i + 1]:
            w = (x_target - x_positions[i]) / (x_positions[i + 1] - x_positions[i])
            return (1 - w) * Es_list[i] + w * Es_list[i + 1]
    if x_target < x_positions[0]:
        return Es_list[0]
    return Es_list[-1]

def compute_roi_intensity(Es_frame, Eref_frame, roi_half=20):
    total = Eref_frame + Es_frame
    It = np.sum(np.abs(total) ** 2, axis=0)
    cy, cx = 162, 162
    roi = It[cy-roi_half:cy+roi_half+1, cx-roi_half:cx+roi_half+1]
    return roi

def main():
    ap = __import__('argparse').ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    results = {'stages': {}, 'start': time.strftime('%Y-%m-%dT%H:%M:%S')}
    # Stage 1: read cache fields for D=100, zf=450
    log('Stage 1: reading cached fields')
    D0, zf0 = 100, 450
    x_anchors = [-20.0, -10.0, 0.0, 10.0, 20.0]
    Es_list = []
    Eref = None
    for x in x_anchors:
        Es, Eref = load_cache_field(D0, zf0, x)
        Es_list.append(Es)
    results['stages']['cache_read'] = {'status': 'SUCCEEDED', 'n_files': len(Es_list)}
    # Stage 2: compute one full ROI observation with M200 trajectory
    log('Stage 2: full ROI observation')
    a_nm = 10.0
    freq = 200.0
    omega = 2 * math.pi * freq
    T_exp = 100e-6
    N_frames = N
    t_j = np.arange(N) / FS
    x_t = a_nm * np.cos(omega * t_j)
    x_t = np.clip(x_t, -20, 20)
    roi_series = np.zeros((N, 2 * 20 + 1, 2 * 20 + 1))
    cy, cx = 162, 162
    rh = 20
    for j in range(N):
        Es_j = interpolate_es(Es_list, x_anchors, x_t[j])
        total = Eref[:, cy-rh:cy+rh+1, cx-rh:cx+rh+1] + Es_j[:, cy-rh:cy+rh+1, cx-rh:cx+rh+1]
        It = np.sum(np.abs(total) ** 2, axis=0)
        roi_series[j] = It
    results['stages']['roi_observation'] = {'status': 'SUCCEEDED', 'shape': list(roi_series.shape)}
    # Stage 3: pixel-level DFT
    log('Stage 3: complex DFT')
    Imean = roi_series.mean(axis=0)
    C_maps = {}
    n = np.arange(N)
    for k0 in K0S:
        e = np.exp(-2j * np.pi * k0 * n / N)
        centered = roi_series - Imean[None, :, :]
        X = np.einsum('j,jpq->pq', e, centered)
        C_maps[k0] = 2.0 * X / (N * Imean)
    results['stages']['dft'] = {'status': 'SUCCEEDED', 'bins': K0S}
    # Save results
    np.savez_compressed(os.path.join(out, 'cached_observation_D100_zf450.npz'),
                        roi_series=roi_series, Imean=Imean,
                        **{'C_%d' % k: C_maps[k] for k in K0S})
    # Summary
    elapsed = time.time() - t0
    results['elapsed_s'] = round(elapsed, 1)
    results['scope'] = 'CACHED_FIELD_MODEL_CONDITIONAL'
    with open(os.path.join(out, 'v120_results.json'), 'w') as f:
        json.dump(results, f, indent=2)
    log('Done: elapsed=%.1fs' % elapsed)

if __name__ == '__main__':
    sys.exit(main())

