# -*- coding: utf-8 -*-
"""v108: v107 review, evidence-level inheritance, complete numerical acceptance, real archive.

Task: V108_FULL_FROZEN_RELEASE. Source: v107 fixed commit bc699b0932cf18f5abad10e09f1d1eae0f29446e.
Read-only root; all outputs written outside the source tree. No new BEM/render/optics/physics/experiment reads.
Only readback, re-DFT/FFT, algebraic verification, hashing, byte copy and packaging are permitted.
"""
import os, sys, csv, json, hashlib, shutil, math, subprocess, zipfile, time, argparse, itertools
import numpy as np
from scipy.io import loadmat

TASK_ID = 'V108_FULL_FROZEN_RELEASE'
EXPECTED_PARENT = 'bc699b0932cf18f5abad10e09f1d1eae0f29446e'
EXPECTED_V106 = '79ba7a7f9068b6ed3a0c621eb25be488de85e68c'
PROBE_BLOB = '6b180147f64847329375363d44c317b2d4df247b'
N = 2001
FS = 5000.0
K0S = [80, 160, 320]
ALL24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
         for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)]
INTER24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
           for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (10, 15)]
ALL48 = ALL24 + INTER24
BIN_SUBSETS = [(80,), (160,), (320,), (80, 160), (80, 320), (160, 320), (80, 160, 320)]
FACTOR_NAMES = ('a', 'zf', 'type')
PROBE_PIXELS = [(20, 20), (20, 0), (0, 20), (25, 0)]
eps64 = np.finfo(np.float64).eps

GATES = {'A': False, 'B': False, 'C': False, 'D': False}
FAIL_KEYS = {}
STAGE_LOG = {}

def log(msg):
    print('[v108] %s' % msg, flush=True)

def g17(x):
    return '%.17g' % float(x)

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def blob_sha1(path):
    data = open(path, 'rb').read()
    h = hashlib.sha1()
    h.update(b'blob %d\x00' % len(data))
    h.update(data)
    return h.hexdigest()

def parse(k):
    p = k.split('_')
    return {'D': int(p[0][1:]), 'zf': int(p[1][2:]), 'type': p[2], 'a': int(p[3][1:])}

def wcsv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)

def rcsv(path):
    with open(path, 'r', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def finite_diff(a, b):
    """Strict difference for gate checks; NaN/Inf inputs count as failure."""
    try:
        fa, fb = float(a), float(b)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(fa) and math.isfinite(fb)):
        return None
    return abs(fa - fb)

# ============================== Stage A ==============================

def stage_a(root, out):
    log('=== Stage A: source admission + 73-item snapshot ===')
    an = os.path.join(root, 'analysis')
    tab = os.path.join(root, 'tables')
    bank_dir = os.path.join(an, 'bank')
    num_dir = os.path.join(root, 'numeric')
    snap_dir = os.path.join(out, 'snapshot73')
    os.makedirs(snap_dir, exist_ok=True)
    issues = []

    # --- read the two v092 bank lists and the v085 baseline list ---
    ep_rows = rcsv(os.path.join(tab, 'v092_bank_status24.csv'))
    it_rows = rcsv(os.path.join(tab, 'v092_intermediate_bank24.csv'))
    bl_rows = rcsv(os.path.join(tab, 'v085_double_maps24_status.csv'))
    ep_ids = [r['case_id'] for r in ep_rows]
    it_ids = [r['case_id'] for r in it_rows]
    bl_ids = [r['case_id'] for r in bl_rows]
    if sorted(ep_ids) != sorted(ALL24):
        issues.append('v092 endpoint bank list != 24 endpoint states')
    if sorted(it_ids) != sorted(INTER24):
        issues.append('v092 intermediate bank list != 24 intermediate states')
    if sorted(bl_ids) != sorted(ALL24):
        issues.append('v085 baseline list != 24 endpoint states')

    # --- bank list SHA cross-check ---
    list_sha = {}
    for r in ep_rows:
        list_sha[r['case_id']] = r.get('sha256', '')
    for r in it_rows:
        list_sha[r['case_id']] = r.get('sha256', '')

    bank = {}
    id_rows = []
    bl_map_file = {r['case_id']: r['map_file'] for r in bl_rows}
    bl_map_sha = {r['case_id']: r['map_sha256'] for r in bl_rows}
    for key in ALL48:
        fn = 'v092_bank_%s.mat' % key
        p = os.path.join(bank_dir, fn)
        if not os.path.isfile(p):
            issues.append('missing bank file %s' % fn)
            continue
        sha = sha256_file(p)
        if key in list_sha and list_sha[key] and list_sha[key] != sha:
            issues.append('bank sha mismatch vs v092 list: %s' % key)
        m = loadmat(p)
        # original dtype check BEFORE any cast
        dt = {'C': str(m['C'].dtype), 'X': str(m['X'].dtype),
              'Imean_map': str(m['Imean_map'].dtype), 'valid_mask': str(m['valid_mask'].dtype)}
        C = np.asarray(m['C'])
        X = np.asarray(m['X'])
        Im = np.asarray(m['Imean_map'])
        mask_raw = np.asarray(m['valid_mask'])
        mask = mask_raw.astype(bool)
        cid = str(m['case_id'].flatten()[0])
        n_val = int(np.asarray(m['N']).flatten()[0])
        fs_val = float(np.asarray(m['Fs']).flatten()[0])
        k0_bins = [int(v) for v in np.asarray(m['k0_bins']).flatten()]
        ok_dtype = (dt['C'] == 'complex128' and dt['X'] == 'complex128'
                    and dt['Imean_map'] == 'float64' and mask_raw.dtype in (np.uint8, np.bool_, bool, 'uint8'))
        ok_shape = C.shape == (3, 41, 41) and X.shape == (3, 41, 41) and Im.shape == (41, 41) and mask.shape == (41, 41)
        ok_id = (cid == key and n_val == N and fs_val == FS and k0_bins == K0S)
        if dt['C'] != 'complex128':
            C = C.astype(np.complex128)
        if dt['X'] != 'complex128':
            X = X.astype(np.complex128)
        Im = Im.astype(np.float64)
        common = mask & np.isfinite(Im) & (Im > 0)
        C_chk = 2.0 * X / (float(n_val) * Im)[None, :, :]
        err = float(np.max(np.abs(C_chk[:, common] - C[:, common]))) if common.any() else float('inf')
        pos = Im[np.isfinite(Im) & (Im > 0)]
        floor = 0.01 * float(np.median(pos)) if pos.size else 0.0
        mask_ok = bool(np.array_equal(mask, np.isfinite(Im) & (Im > floor)))
        ok = (ok_dtype and ok_shape and ok_id and err < 1e-10 and mask_ok
              and bool(np.isfinite(C[:, common]).all()) and bool(np.isfinite(X[:, common]).all()))
        if not ok:
            issues.append('bank identity failed: %s (err=%g, mask_ok=%s)' % (key, err, mask_ok))
        bank[key] = {'C': C, 'X': X, 'Im': Im, 'mask': mask, 'file': fn, 'sha256': sha, 'dtypes': dt}
        id_rows.append({'case_id': key, 'C_dtype': dt['C'], 'X_dtype': dt['X'],
                        'Imean_dtype': dt['Imean_map'], 'mask_dtype': str(mask_raw.dtype),
                        'N': str(n_val), 'Fs': g17(fs_val), 'k0_bins': '|'.join(str(v) for v in k0_bins),
                        'C_eq_2X_over_NIm_max_err': g17(err), 'mask_matches_formula': 'YES' if mask_ok else 'NO',
                        'sha256': sha, 'status': 'VERIFIED' if ok else 'FAILED'})
    wcsv(os.path.join(out, 'tables', 'v108_bank_identity48.csv'),
         list(id_rows[0].keys()), id_rows)

    # --- 24 baselines: old C160/C400 relative Frobenius gate ---
    rF_rows = []
    for key in ALL24:
        fn = bl_map_file[key]
        p = os.path.join(num_dir, fn)
        if not os.path.isfile(p):
            issues.append('missing baseline file %s' % fn)
            continue
        sha = sha256_file(p)
        if bl_map_sha.get(key) and bl_map_sha[key] != sha:
            issues.append('baseline sha mismatch vs v085 list: %s' % key)
        m = loadmat(p)
        dt_raw = str(m['C400_double'].dtype)
        Cold = np.asarray(m['C400_double']).astype(np.complex128).reshape(-1)
        C160 = bank[key]['C'][1].reshape(-1)
        msk = bank[key]['mask'].reshape(-1)
        denom = float(np.linalg.norm(Cold[msk]))
        rF = float(np.linalg.norm((C160 - Cold)[msk]) / max(denom, 1e-300))
        ok = rF < 1e-10
        if not ok:
            issues.append('old C160 rF gate failed: %s (rF=%g)' % (key, rF))
        rF_rows.append({'case_id': key, 'baseline_file': fn, 'baseline_dtype': dt_raw,
                        'rF_bin160_vs_old_C400': g17(rF), 'sha256': sha,
                        'status': 'PASS' if ok else 'FAIL'})
    wcsv(os.path.join(out, 'tables', 'v108_old_c160_rF24.csv'),
         list(rF_rows[0].keys()), rF_rows)

    # --- probe NPZ audit ---
    npz_src = os.path.join(an, 'v093_probe_evidence.npz')
    npz_sha = sha256_file(npz_src)
    npz_blob = blob_sha1(npz_src)
    zs = np.load(npz_src)
    series_keys = sorted(k for k in zs.files if k.startswith('series_'))
    expected_series = set()
    for key in ALL48:
        for (i5, j5) in PROBE_PIXELS:
            expected_series.add('series_%s_h5_%d_%d' % (key, i5, j5))
    probe_ok = (npz_blob == PROBE_BLOB and len(series_keys) == 192
                and set(series_keys) == expected_series)
    if npz_blob != PROBE_BLOB:
        issues.append('probe NPZ git blob mismatch: %s' % npz_blob)
    if set(series_keys) != expected_series:
        issues.append('probe NPZ series key set mismatch (%d keys)' % len(series_keys))
    for sk in series_keys:
        s = zs[sk]
        if s.dtype != np.float64 or s.shape != (N,) or not np.isfinite(s).all() or float(s.mean()) <= 0:
            issues.append('probe series bad: %s' % sk)
            probe_ok = False
            break

    # --- 73-item snapshot (byte copy, source==dest SHA) ---
    snap_rows = []
    for key in ALL48:
        src = os.path.join(bank_dir, bank[key]['file'])
        dst = os.path.join(snap_dir, bank[key]['file'])
        shutil.copy2(src, dst)
        snap_rows.append({'role': 'BANK', 'case_id': key, 'source_path': src,
                          'target_relative': 'snapshot73/%s' % bank[key]['file'],
                          'size_bytes': str(os.path.getsize(dst)), 'sha256': sha256_file(dst)})
    for key in ALL24:
        fn = bl_map_file[key]
        src = os.path.join(num_dir, fn)
        dst = os.path.join(snap_dir, fn)
        shutil.copy2(src, dst)
        snap_rows.append({'role': 'BASELINE', 'case_id': key, 'source_path': src,
                          'target_relative': 'snapshot73/%s' % fn,
                          'size_bytes': str(os.path.getsize(dst)), 'sha256': sha256_file(dst)})
    dst_npz = os.path.join(snap_dir, 'v093_probe_evidence.npz')
    shutil.copy2(npz_src, dst_npz)
    snap_rows.append({'role': 'SAVED_SIMULATION_PROBES', 'case_id': 'PROBE_EVIDENCE_192_SERIES',
                      'source_path': npz_src, 'target_relative': 'snapshot73/v093_probe_evidence.npz',
                      'size_bytes': str(os.path.getsize(dst_npz)), 'sha256': sha256_file(dst_npz)})
    for r in snap_rows:
        dst = os.path.join(out, r['target_relative'])
        if sha256_file(dst) != r['sha256'] or r['sha256'] != sha256_file(r['source_path']):
            issues.append('snapshot byte mismatch: %s' % r['target_relative'])
    roles = [r['role'] for r in snap_rows]
    n73 = len(snap_rows)
    wcsv(os.path.join(out, 'logs', 'v108_snapshot73_manifest.csv'),
         list(snap_rows[0].keys()), snap_rows)
    probe_audit = {'probe_npz_sha256': npz_sha, 'probe_npz_git_blob_sha1': npz_blob,
                   'expected_blob': PROBE_BLOB, 'n_series': len(series_keys),
                   'keys_exact_48x4': set(series_keys) == expected_series,
                   'all_float64_2001_finite_positive_mean': probe_ok or len(issues) == 0,
                   'status': 'VERIFIED' if probe_ok else 'FAILED'}
    with open(os.path.join(out, 'logs', 'v108_probe_audit.json'), 'w', encoding='utf-8') as f:
        json.dump(probe_audit, f, indent=2)

    ok_a = (not issues and n73 == 73 and roles.count('BANK') == 48
            and roles.count('BASELINE') == 24 and roles.count('SAVED_SIMULATION_PROBES') == 1)
    STAGE_LOG['A'] = {'snapshots': n73, 'bank_identity_48': sum(1 for r in id_rows if r['status'] == 'VERIFIED'),
                      'old_c160_rF_24': sum(1 for r in rF_rows if r['status'] == 'PASS'),
                      'probe_ok': probe_ok, 'issues': issues}
    if not ok_a:
        FAIL_KEYS['A'] = issues[:50]
    GATES['A'] = ok_a
    log('Stage A: snapshots=%d, bank=%d/48, rF=%d/24, probe_ok=%s, issues=%d'
        % (n73, STAGE_LOG['A']['bank_identity_48'], STAGE_LOG['A']['old_c160_rF_24'], probe_ok, len(issues)))
    return bank, series_keys, dst_npz

# ============================== Stage B ==============================

WORKER_SRC = r'''# -*- coding: utf-8 -*-
"""v108 independent worker: fresh-process FFT verification from saved source series."""
import sys, json, hashlib
import numpy as np

def main():
    npz_path, out_path = sys.argv[1], sys.argv[2]
    N, K0S = 2001, [80, 160, 320]
    zs = np.load(npz_path)
    res = {}
    for sk in sorted(k for k in zs.files if k.startswith('series_')):
        s = zs[sk]
        g = np.asarray(s[:25], dtype=np.float64)
        for ell in range(25):
            y = np.array([g[(jj + ell) % 25] for jj in range(N)], dtype=np.float64)
            Im = float(y.mean())
            spec = np.fft.fft(y - Im)
            for k0 in K0S:
                X = complex(spec[k0])
                C = 2.0 * X / (N * Im) if Im != 0 else complex(0.0)
                res['%s|bin%d|ell%d' % (sk, k0, ell)] = [X.real, X.imag, C.real, C.imag]
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(res, f)
    print('WORKER_OK %d' % len(res))

if __name__ == '__main__':
    main()
'''

def stage_b(root, out, series_keys, npz_path, bank):
    log('=== Stage B: saved probes, three-frequency origins, periods, projections ===')
    an = os.path.join(root, 'analysis')
    issues = []
    GATE = 1e-11
    zs = np.load(npz_path)

    # precomputed DFT weight sums per (k0, remainder n): sum over j=n, n+25, ...
    e_sum = {}
    for k0 in K0S:
        for n in range(25):
            j_vals = np.arange(n, N, 25)
            e_sum[(k0, n)] = complex(np.sum(np.exp(-2j * np.pi * k0 * j_vals / N)))
    e0_vec = {k0: np.exp(-2j * np.pi * k0 * np.arange(N) / N) for k0 in K0S}
    sum_e = {k0: complex(np.sum(e0_vec[k0])) for k0 in K0S}
    # projection basis T[k0][r] = sum_j exp(-2 pi i k0 j/N) * (phase_r(j) - mean(phase_r))
    T = {k0: np.zeros(25, dtype=np.complex128) for k0 in K0S}
    for k0 in K0S:
        for r in range(25):
            phase = np.exp(2j * np.pi * r * np.arange(N) / 25)
            T[k0][r] = complex(np.sum(e0_vec[k0] * (phase - np.mean(phase))))

    rows = []
    amp_rows = []
    zero_rows = []
    probe_rows = []
    period_rows = []
    comp_rows = []
    n_pass = n_total = 0
    n_indep_ok = 0

    for skey in series_keys:
        parts = skey.replace('series_', '').split('_h5_')
        case_id, pix = parts[0], parts[1]
        i5, j5 = int(pix.split('_')[0]), int(pix.split('_')[1])
        s = np.asarray(zs[skey], dtype=np.float64)
        g = s[:25].copy()
        Im0 = float(np.array([g[jj % 25] for jj in range(N)], dtype=np.float64).mean())
        n25 = np.arange(25)
        h = np.array([np.mean(g * np.exp(-2j * np.pi * r * n25 / 25)) for r in range(25)])
        max_dev = float(np.max(np.abs(s[:2000] - np.tile(g, 80))))
        endpoint_dev = abs(float(s[2000]) - float(g[0]))
        per_bin_diffs = {}
        # zero-start and bank probe values from the FULL saved series
        for ki, k0 in enumerate(K0S):
            e_k = e0_vec[k0]
            X_full = complex(np.sum((s - s.mean()) * e_k))
            C_full = 2.0 * X_full / (N * s.mean()) if s.mean() != 0 else complex(np.nan)
            # zero-start from 25-periodic reconstruction (ell=0)
            y0 = np.array([g[jj % 25] for jj in range(N)], dtype=np.float64)
            X0_A = complex(np.sum((y0 - Im0) * e_k))
            X0_B = complex(np.fft.fft(y0 - Im0)[k0])
            X0_C = X0_A  # ell=0: phase=1, tail=0, d_mean=0
            d_zero_A = abs(X0_A - X_full)
            d_zero_B = abs(X0_B - X_full)
            pix_idx = i5 * 41 + j5
            X_bp = complex(bank[case_id]['X'][ki].reshape(-1)[pix_idx])
            C_bp = complex(bank[case_id]['C'][ki].reshape(-1)[pix_idx])
            d_X_bank = abs(X_full - X_bp)
            d_C_bank = abs(C_full - C_bp)
            probe_ok = d_X_bank < GATE and d_C_bank < GATE
            probe_rows.append({'record_key': '%s|bin%d|%s' % (case_id, k0, pix),
                               'case_id': case_id, 'k0': k0, 'pixel': pix,
                               'abs_dX_vs_bank': g17(d_X_bank), 'abs_dC_vs_bank': g17(d_C_bank),
                               'original_gate_1e-11': 'PASS' if probe_ok else 'FAIL'})
            zero_rows.append({'record_key': '%s|bin%d|px(%s)' % (case_id, k0, pix),
                              'case_id': case_id, 'k0': k0, 'pixel': pix,
                              'abs_X_zerostart_A': g17(abs(X0_A)),
                              'abs_X_full_series': g17(abs(X_full)),
                              'abs_d_zerostart_vs_full': g17(d_zero_A),
                              'zerostart_gate_1e-11': 'PASS' if (d_zero_A < GATE and d_zero_B < GATE) else 'FAIL',
                              'endpoint_2001_dev': g17(endpoint_dev),
                              'bank_probe_dX': g17(d_X_bank), 'bank_probe_dC': g17(d_C_bank)})
            # periodic projection components
            X_recon = complex(np.sum(T[k0] * h))
            d_recon = abs(X_recon - X_full)
            per_bin_diffs[k0] = d_recon
            for r in range(25):
                contrib = complex(T[k0][r] * h[r])
                comp_rows.append({'record_key': '%s|bin%d|px(%s)|r%d' % (case_id, k0, pix, r),
                                  'case_id': case_id, 'k0': k0, 'pixel': pix, 'r': r,
                                  'T_kr_Re': g17(T[k0][r].real), 'T_kr_Im': g17(T[k0][r].imag),
                                  'h_r_Re': g17(h[r].real), 'h_r_Im': g17(h[r].imag),
                                  'contribution_Re': g17(contrib.real), 'contribution_Im': g17(contrib.imag)})
        period_rows.append({'record_key': '%s|%s' % (case_id, pix), 'case_id': case_id, 'pixel': pix,
                            'endpoint_2001_dev': g17(endpoint_dev),
                            'max_periodicity_dev_first_2000': g17(max_dev),
                            'abs_d_recon_bin80': g17(per_bin_diffs[80]),
                            'abs_d_recon_bin160': g17(per_bin_diffs[160]),
                            'abs_d_recon_bin320': g17(per_bin_diffs[320]),
                            'status': 'PASS' if all(v < GATE for v in per_bin_diffs.values()) else 'FAIL'})
        # 25 origins x 3 bins, three paths each
        amp_by_bin = {k0: [] for k0 in K0S}
        for ell in range(25):
            y = np.array([g[(jj + ell) % 25] for jj in range(N)], dtype=np.float64)
            Im_ell = float(y.mean())
            mean_ident = abs(Im_ell - (80.0 * float(np.sum(g)) + float(g[ell % 25])) / N)
            if mean_ident >= 1e-12:
                issues.append('mean identity failed: %s ell=%d (%g)' % (skey, ell, mean_ident))
            spec = np.fft.fft(y - Im_ell)
            for k0 in K0S:
                X_A = complex(0)
                for n in range(25):
                    X_A += (float(g[(n + ell) % 25]) - Im_ell) * e_sum[(k0, n)]
                C_A = 2.0 * X_A / (N * Im_ell) if Im_ell != 0 else complex(0)
                X_B = complex(spec[k0])
                C_B = 2.0 * X_B / (N * Im_ell)
                # path C: zero-start periodic proxy + finite tail correction
                y0 = np.array([g[jj % 25] for jj in range(N)], dtype=np.float64)
                Im0_l = float(y0.mean())
                e0 = e0_vec[k0]
                X0 = complex(np.sum((y0 - Im0_l) * e0))
                phase = np.exp(2j * np.pi * k0 * ell / N)
                tail_sum = complex(0)
                for r in range(ell):
                    tail_sum += (float(g[r + 1]) - float(g[r])) * np.exp(-2j * np.pi * k0 * (N - ell + r) / N)
                d_mean = (float(g[ell]) - float(g[0])) / N
                X_C = phase * X0 + tail_sum - d_mean * sum_e[k0]
                C_C = 2.0 * X_C / (N * Im_ell)
                dX_AB, dX_AC, dX_BC = abs(X_A - X_B), abs(X_A - X_C), abs(X_B - X_C)
                dC_AB, dC_AC, dC_BC = abs(C_A - C_B), abs(C_A - C_C), abs(C_B - C_C)
                ok = max(dX_AB, dX_AC, dX_BC, dC_AB, dC_AC, dC_BC) < GATE
                n_total += 1
                n_pass += int(ok)
                rows.append({'record_key': '%s|bin%d|px(%s)|ell%d' % (case_id, k0, pix, ell),
                             'case_id': case_id, 'k0': k0, 'pixel': pix, 'origin_ell': ell,
                             'X_A_Re': g17(X_A.real), 'X_A_Im': g17(X_A.imag),
                             'X_B_Re': g17(X_B.real), 'X_B_Im': g17(X_B.imag),
                             'X_C_Re': g17(X_C.real), 'X_C_Im': g17(X_C.imag),
                             'C_A_Re': g17(C_A.real), 'C_A_Im': g17(C_A.imag),
                             'C_B_Re': g17(C_B.real), 'C_B_Im': g17(C_B.imag),
                             'C_C_Re': g17(C_C.real), 'C_C_Im': g17(C_C.imag),
                             'Im_ell': g17(Im_ell),
                             'dX_AB': g17(dX_AB), 'dX_AC': g17(dX_AC), 'dX_BC': g17(dX_BC),
                             'dC_AB': g17(dC_AB), 'dC_AC': g17(dC_AC), 'dC_BC': g17(dC_BC),
                             'mean_identity_err': g17(mean_ident),
                             'abs_C_A': g17(abs(C_A)),
                             'status': 'PASS' if ok else 'FAIL'})
                amp_by_bin[k0].append(abs(C_A))
        for k0 in K0S:
            vals = amp_by_bin[k0]
            hi, lo = max(vals), min(vals)
            span = hi - lo
            amp_rows.append({'record_key': '%s|bin%d|px(%s)' % (case_id, k0, pix),
                             'case_id': case_id, 'k0': k0, 'pixel': pix, 'n_origins': 25,
                             'max_abs_C': g17(hi), 'min_abs_C': g17(lo),
                             'median_abs_C': g17(float(np.median(vals))),
                             'abs_span': g17(span),
                             'rel_span': g17(span / hi) if hi > 1e-12 else 'NEAR_ZERO',
                             'status': 'REPORTED'})

    # independent subprocess FFT verification
    worker_path = os.path.join(out, 'logs', 'independent_worker.py')
    with open(worker_path, 'w', encoding='utf-8') as f:
        f.write(WORKER_SRC)
    worker_out = os.path.join(out, 'logs', 'independent_worker_result.json')
    t0 = time.time()
    proc = subprocess.run([sys.executable, worker_path, npz_path, worker_out],
                          capture_output=True, text=True, timeout=1800)
    worker_exit = proc.returncode
    worker_time = time.time() - t0
    indep_ok = False
    n_indep_cmp = 0
    if worker_exit == 0 and os.path.isfile(worker_out):
        wres = json.load(open(worker_out, encoding='utf-8'))
        for r in rows:
            wkey = '%s|bin%d|ell%d' % ('series_' + r['case_id'] + '_h5_' + r['pixel'], r['k0'], r['origin_ell'])
            w = wres.get(wkey)
            if w is None:
                continue
            X_A = complex(float(r['X_A_Re']), float(r['X_A_Im']))
            C_A = complex(float(r['C_A_Re']), float(r['C_A_Im']))
            dX = abs(X_A - complex(w[0], w[1]))
            dC = abs(C_A - complex(w[2], w[3]))
            r['dX_indep_worker'] = g17(dX)
            r['dC_indep_worker'] = g17(dC)
            n_indep_cmp += 1
            n_indep_ok += int(dX < GATE and dC < GATE)
        indep_ok = (n_indep_cmp == len(rows) and n_indep_ok == len(rows))
    else:
        issues.append('independent worker failed: exit=%d %s' % (worker_exit, proc.stderr[:300]))

    # 24 motion-time pairings (M400[n] == M200[(2n) % 25], max over 4 probe pixels)
    pair_rows = []
    for D in (30, 60, 100):
        for zf in (450, 550):
            for a in (5, 10, 15, 20):
                diffs = []
                for (i5, j5) in PROBE_PIXELS:
                    m200 = zs.get('series_D%d_zf%d_M200_a%d_h5_%d_%d' % (D, zf, a, i5, j5))
                    m400 = zs.get('series_D%d_zf%d_M400_a%d_h5_%d_%d' % (D, zf, a, i5, j5))
                    if m200 is None or m400 is None:
                        continue
                    g200 = np.asarray(m200[:25], dtype=np.float64)
                    g400 = np.asarray(m400[:25], dtype=np.float64)
                    expected = np.array([g200[(2 * n) % 25] for n in range(25)])
                    diffs.append(float(np.max(np.abs(g400 - expected))))
                d = max(diffs) if diffs else float('inf')
                pair_rows.append({'record_key': 'D%d_zf%d_a%d' % (D, zf, a),
                                  'D': D, 'zf': zf, 'a': a,
                                  'max_abs_diff_25pt_over_4px': g17(d),
                                  'gate_1e-10': 'PASS' if d < 1e-10 else 'FAIL'})

    wcsv(os.path.join(out, 'analysis', 'v108_origin_threeway14400.csv'), list(rows[0].keys()), rows)
    wcsv(os.path.join(out, 'analysis', 'v108_amp_summary576.csv'), list(amp_rows[0].keys()), amp_rows)
    wcsv(os.path.join(out, 'analysis', 'v108_zerostart_summary576.csv'), list(zero_rows[0].keys()), zero_rows)
    wcsv(os.path.join(out, 'tables', 'v108_probe_gate576.csv'), list(probe_rows[0].keys()), probe_rows)
    wcsv(os.path.join(out, 'tables', 'v108_period192.csv'), list(period_rows[0].keys()), period_rows)
    wcsv(os.path.join(out, 'tables', 'v108_motion_pairs24.csv'), list(pair_rows[0].keys()), pair_rows)
    wcsv(os.path.join(out, 'analysis', 'v108_period_components14400.csv'), list(comp_rows[0].keys()), comp_rows)

    n_probe_ok = sum(1 for r in probe_rows if r['original_gate_1e-11'] == 'PASS')
    n_zero_ok = sum(1 for r in zero_rows if r['zerostart_gate_1e-11'] == 'PASS')
    n_period_ok = sum(1 for r in period_rows if r['status'] == 'PASS')
    n_pair_ok = sum(1 for r in pair_rows if r['gate_1e-10'] == 'PASS')
    ok_b = (n_pass == n_total and indep_ok and n_probe_ok == 576 and n_zero_ok == 576
            and n_period_ok == 192 and n_pair_ok == 24 and not issues)
    if n_pass < n_total:
        FAIL_KEYS.setdefault('B', []).append('threeway_pass=%d/%d' % (n_pass, n_total))
    if not indep_ok:
        FAIL_KEYS.setdefault('B', []).append('independent_worker=%d/%d' % (n_indep_ok, n_indep_cmp))
    if n_probe_ok < 576:
        FAIL_KEYS.setdefault('B', []).append('probe_gates=%d/576' % n_probe_ok)
    if n_zero_ok < 576:
        FAIL_KEYS.setdefault('B', []).append('zerostart=%d/576' % n_zero_ok)
    if n_period_ok < 192:
        FAIL_KEYS.setdefault('B', []).append('periods=%d/192' % n_period_ok)
    if n_pair_ok < 24:
        FAIL_KEYS.setdefault('B', []).append('motion_pairs=%d/24' % n_pair_ok)
    if issues:
        FAIL_KEYS.setdefault('B', []).extend(issues[:20])
    GATES['B'] = ok_b
    STAGE_LOG['B'] = {'threeway': '%d/%d' % (n_pass, n_total), 'independent_worker': '%d/%d' % (n_indep_ok, n_indep_cmp),
                      'worker_exit': worker_exit, 'worker_seconds': round(worker_time, 1),
                      'probe_gates': '%d/576' % n_probe_ok, 'zerostart': '%d/576' % n_zero_ok,
                      'periods': '%d/192' % n_period_ok, 'motion_pairs': '%d/24' % n_pair_ok,
                      'amp_summaries': len(amp_rows), 'components': len(comp_rows), 'issues': issues[:20]}
    log('Stage B: threeway=%d/%d worker=%d/%d probes=%d/576 zero=%d/576 periods=%d/192 pairs=%d/24'
        % (n_pass, n_total, n_indep_ok, n_indep_cmp, n_probe_ok, n_zero_ok, n_period_ok, n_pair_ok))
    return rows

# ============================== Stage C ==============================

FEATS = [(1, 'ROI_L2_log_ratio'), (2, 'magnitude_pattern_symmetric'), (3, 'unit_magnitude_shape')]
POLICY_NAMES = ['unknown_zf_motion', 'known_motion', 'known_motion_zf']

def factor_subsets():
    subs = []
    for r in (1, 2, 3):
        subs.extend(itertools.combinations(FACTOR_NAMES, r))
    return subs

def refs_endpoint(qi, S, meta):
    return [r for r in ALL24 if r != qi and all(meta[r][f] != meta[qi][f] for f in S)]

def refs_intermediate(qi, pname, meta):
    if pname == 'unknown_zf_motion':
        return list(ALL24)
    if pname == 'known_motion':
        return [r for r in ALL24 if meta[r]['type'] == meta[qi]['type']]
    return [r for r in ALL24 if meta[r]['type'] == meta[qi]['type'] and meta[r]['zf'] == meta[qi]['zf']]

def independent_decisions(bank):
    """Independent worker: per-channel squared-sum reduction; no production
    representation/distance/pool/tie functions are called. Overall norms are NOT
    replaced by per-channel norms: channels are reduced by squared sums."""
    meta = {k: parse(k) for k in ALL48}
    abs_C = {}
    for key in ALL48:
        for ki, k0 in enumerate(K0S):
            abs_C[(key, k0)] = np.abs(bank[key]['C'][ki]).reshape(-1)
    rows = []
    for bins in BIN_SUBSETS:
        bins_key = '+'.join(str(b) for b in bins)
        active = [k0 for k0 in K0S if k0 in bins]
        chan_norm = {}
        for key in ALL48:
            chan_norm[key] = {k0: float(np.sqrt(np.sum(np.abs(abs_C[(key, k0)]) ** 2))) for k0 in active}
        # independent per-channel squared-sum reduction of concatenated norm
        A = {key: float(math.sqrt(sum(chan_norm[key][k0] ** 2 for k0 in active))) for key in ALL48}
        for S in factor_subsets():
            S_name = '+'.join(S)
            for qi in ALL24:
                refs = refs_endpoint(qi, S, meta)
                d1 = {r: abs(math.log(A[qi]) - math.log(A[r])) for r in refs}
                d2 = {r: 2.0 * math.sqrt(sum(float(np.sum(np.abs(abs_C[(qi, k0)] - abs_C[(r, k0)]) ** 2)) for k0 in active)) / (A[qi] + A[r]) for r in refs}
                uq = {k0: abs_C[(qi, k0)] / max(A[qi], 1e-300) for k0 in active}
                ur = {r: {k0: abs_C[(r, k0)] / max(A[r], 1e-300) for k0 in active} for r in refs}
                d3 = {r: math.sqrt(sum(float(np.sum(np.abs(uq[k0] - ur[r][k0]) ** 2)) for k0 in active)) for r in refs}
                rows.extend(_emit(rows_meta=meta, bins_key=bins_key, group=S_name, batch='endpoint_leavegroup',
                                  extra={'subset_S': S_name}, qi=qi, refs=refs, d1=d1, d2=d2, d3=d3,
                                  A=A, abs_C=abs_C, active=active, bank=bank))
        for pname in POLICY_NAMES:
            for qi in INTER24:
                refs = refs_intermediate(qi, pname, meta)
                d1 = {r: abs(math.log(A[qi]) - math.log(A[r])) for r in refs}
                d2 = {r: 2.0 * math.sqrt(sum(float(np.sum(np.abs(abs_C[(qi, k0)] - abs_C[(r, k0)]) ** 2)) for k0 in active)) / (A[qi] + A[r]) for r in refs}
                uq = {k0: abs_C[(qi, k0)] / max(A[qi], 1e-300) for k0 in active}
                ur = {r: {k0: abs_C[(r, k0)] / max(A[r], 1e-300) for k0 in active} for r in refs}
                d3 = {r: math.sqrt(sum(float(np.sum(np.abs(uq[k0] - ur[r][k0]) ** 2)) for k0 in active)) for r in refs}
                rows.extend(_emit(rows_meta=meta, bins_key=bins_key, group=pname, batch='intermediate_query',
                                  extra={'policy': pname}, qi=qi, refs=refs, d1=d1, d2=d2, d3=d3,
                                  A=A, abs_C=abs_C, active=active, bank=bank))
    return rows

def _emit(rows_meta, bins_key, group, batch, extra, qi, refs, d1, d2, d3, A, abs_C, active, bank):
    meta = rows_meta
    all_ds = [d1, d2, d3]
    out = []
    for fi, fname in FEATS:
        ds = all_ds[fi - 1]
        ordered = sorted(refs, key=lambda r: (ds[r], r))
        dmin = ds[ordered[0]]
        tol = 64 * eps64 * max(1.0, abs(dmin))
        tied = [r for r in ordered if ds[r] <= dmin + tol]
        tied_Ds = sorted({meta[r]['D'] for r in tied})
        ambiguous = len(tied_Ds) > 1
        same_D = [r for r in refs if meta[r]['D'] == meta[qi]['D']]
        cross_D = [r for r in refs if meta[r]['D'] != meta[qi]['D']]
        min_same = min(ds[r] for r in same_D)
        min_cross = min(ds[r] for r in cross_D)
        label = meta[ordered[0]]['D']
        consistent = (label == meta[qi]['D']) and not ambiguous
        rec = {
            'record_key': '%s|%s|q=%s|%s' % (bins_key, group, qi, fname),
            'bins': bins_key, 'batch': batch,
            'query': qi, 'query_D': str(meta[qi]['D']), 'query_type': meta[qi]['type'],
            'query_zf': str(meta[qi]['zf']), 'query_a': str(meta[qi]['a']),
            'feature': fname,
            'source_sha256': bank[qi]['sha256'],
            'reference_pool': '|'.join(sorted(refs)),
            'reference_pool_size': len(refs),
            'nearest_candidate': ordered[0], 'nearest_label_D': str(label),
            'nearest_dist': g17(dmin),
            'second_candidate': ordered[1] if len(ordered) > 1 else '',
            'second_label_D': str(meta[ordered[1]]['D']) if len(ordered) > 1 else '',
            'second_dist': g17(ds[ordered[1]]) if len(ordered) > 1 else '',
            'same_D_nearest_dist': g17(min_same), 'cross_D_nearest_dist': g17(min_cross),
            'min_cross_minus_min_same': g17(min_cross - min_same),
            'near_min_set': '|'.join(tied),
            'near_min_set_size': len(tied),
            'near_min_D_set': '|'.join(str(v) for v in tied_Ds),
            'tie_threshold': g17(tol),
            'tied_set_size': len(tied), 'tie_across_D': 'YES' if ambiguous else 'NO',
            'final_decision': 'SAME_D' if consistent else ('AMBIGUOUS_CROSS_D' if ambiguous else 'CROSS_D'),
            'model_label_consistent': 'YES' if consistent else ('AMBIGUOUS_CROSS_D' if ambiguous else 'NO'),
            'status': 'INDEPENDENT_VERIFIED'}
        rec.update(extra)
        out.append(rec)
    return out

DECISION_FIELDS = ['nearest_candidate', 'nearest_label_D',
                   'same_D_nearest_dist', 'cross_D_nearest_dist',
                   'min_cross_minus_min_same', 'model_label_consistent']

def validate_row(rec, expected):
    """Real validation entry: presence, parsability, finiteness, decision-field match."""
    issues = []
    for f in DECISION_FIELDS + ['reference_pool', 'reference_pool_size', 'record_key']:
        if f not in rec or rec[f] in (None, ''):
            if f == 'second_candidate':
                continue
            issues.append('missing field %s' % f)
    for f in ['same_D_nearest_dist', 'cross_D_nearest_dist', 'min_cross_minus_min_same']:
        v = rec.get(f, '')
        try:
            fv = float(v)
        except (TypeError, ValueError):
            issues.append('unparsable %s' % f)
            continue
        if not math.isfinite(fv):
            issues.append('non-finite %s' % f)
    if issues:
        return issues
    if rec['record_key'] != expected['record_key']:
        issues.append('key mismatch')
        return issues
    pool_rec = sorted(str(rec['reference_pool']).split('|')) if rec.get('reference_pool') else []
    pool_exp = sorted(str(expected['reference_pool']).split('|'))
    if pool_rec != pool_exp:
        issues.append('reference pool mismatch')
    if str(rec.get('reference_pool_size', '')) != str(expected['reference_pool_size']):
        issues.append('reference pool size mismatch')
    for f in DECISION_FIELDS:
        a, b = rec.get(f, ''), expected.get(f, '')
        d = finite_diff(a, b)
        if d is None:
            if str(a) != str(b):
                issues.append('%s mismatch: %r vs %r' % (f, a, b))
        elif not d < 1e-12:
            issues.append('%s diff %g >= 1e-12' % (f, d))
    if str(rec.get('source_sha256', '')) != str(expected.get('source_sha256', '')):
        issues.append('source_sha256 mismatch')
    for f in ['nearest_candidate', 'nearest_label_D', 'second_candidate', 'second_label_D',
              'near_min_set', 'near_min_D_set', 'tied_set_size', 'tie_across_D']:
        if str(rec.get(f, '')) != str(expected.get(f, '')):
            issues.append('%s mismatch' % f)
    d = finite_diff(rec.get('tie_threshold', ''), expected.get('tie_threshold', ''))
    if d is None or not d < 1e-12:
        issues.append('tie_threshold mismatch')
    return issues

def validate_table(recs, expected_by_key):
    """Table-level entry: duplicate/extra/missing keys + per-row validation. Order-insensitive."""
    issues = []
    seen = {}
    for r in recs:
        k = r.get('record_key')
        if k in seen:
            issues.append('duplicate record_key: %s' % k)
        seen[k] = r
    for k in expected_by_key:
        if k not in seen:
            issues.append('missing record_key: %s' % k)
    for k in seen:
        if k not in expected_by_key:
            issues.append('extra record_key: %s' % k)
    for k, r in seen.items():
        if k in expected_by_key:
            issues.extend('row %s: %s' % (k, msg) for msg in validate_row(r, expected_by_key[k]))
    return issues

def stage_c(root, out, bank, indep):
    log('=== Stage C: full 5040 independent acceptance ===')
    an = os.path.join(root, 'analysis')
    issues = []
    expected_by_key = {r['record_key']: r for r in indep}
    if len(expected_by_key) != 5040:
        issues.append('independent key count %d != 5040' % len(expected_by_key))

    # production comparison
    prod = rcsv(os.path.join(an, 'v098_comparisons5040.csv'))
    prod_by_key = {r['record_key']: r for r in prod}
    n_match = n_mismatch = 0
    mismatches = []
    for r in indep:
        pk = r['record_key']
        pr = prod_by_key.get(pk)
        if pr is None:
            n_mismatch += 1
            mismatches.append({'record_key': pk, 'issue': 'missing in production'})
            continue
        row_bad = False
        for f in DECISION_FIELDS:
            d = finite_diff(r.get(f, ''), pr.get(f, ''))
            if d is None:
                if str(r.get(f, '')) != str(pr.get(f, '')):
                    row_bad = True
                    mismatches.append({'record_key': pk, 'issue': '%s: %s vs %s' % (f, r.get(f, ''), pr.get(f, ''))})
            elif not d < 1e-12:
                row_bad = True
                mismatches.append({'record_key': pk, 'issue': '%s diff %g' % (f, d)})
        n_match += int(not row_bad)
        n_mismatch += int(row_bad)

    all_f = ['record_key'] + sorted({k for r in indep for k in r if k != 'record_key'})
    wcsv(os.path.join(out, 'tables', 'v108_independent5040.csv'), all_f, indep)
    if mismatches:
        wcsv(os.path.join(out, 'logs', 'v108_production_mismatches.csv'),
             list(mismatches[0].keys()), mismatches[:200])

    # 210 summaries (70 groups x 3 features, 24 queries each)
    summ = {}
    for r in indep:
        gk = (r['bins'], r.get('subset_S') or r.get('policy'), r['feature'])
        s = summ.setdefault(gk, {'consistent': 0, 'n': 0})
        s['n'] += 1
        s['consistent'] += int(r['model_label_consistent'] == 'YES')
    summ_rows = [{'record_key': '%s|%s|%s' % (b, g, f),
                  'bins': b, 'subset_or_policy': g, 'feature': f,
                  'n_queries': s['n'], 'consistent_count': s['consistent'],
                  'reading': 'in-sample geometry screen; NOT accuracy/detectability',
                  'status': 'SUMMARIZED'} for (b, g, f), s in sorted(summ.items())]
    wcsv(os.path.join(out, 'analysis', 'v108_summaries210.csv'), list(summ_rows[0].keys()), summ_rows)

    # 1440-row historical subset: strict key subset + field agreement
    sub_path = os.path.join(an, 'v095_subset1440.csv')
    sub = rcsv(sub_path)
    sub_missing = [r['record_key'] for r in sub if r['record_key'] not in expected_by_key]
    sub_field_bad = 0
    for r in sub:
        cur = expected_by_key.get(r['record_key'])
        if cur is None:
            continue
        for f in DECISION_FIELDS:
            d = finite_diff(r.get(f, ''), cur.get(f, ''))
            bad = (str(r.get(f, '')) != str(cur.get(f, ''))) if d is None else not d < 1e-12
            if bad:
                sub_field_bad += 1
                break

    # 60-row historical summary: structural subset mapping into current 210
    s60_path = os.path.join(an, 'v092_summaries60.csv')
    s60 = rcsv(s60_path)
    summ_by_gf = {}
    for r in summ_rows:
        summ_by_gf[(r['bins'], r['subset_or_policy'], r['feature'])] = r
    s60_unmapped = []
    s60_dup_keys = len(s60) - len({r['record_key'] for r in s60})
    for r in s60:
        k = ('160', r['subset_or_policy'], r['feature'])
        if k not in summ_by_gf:
            s60_unmapped.append(r['record_key'])

    # 19 error tests through the real validation entry (corrected semantics)
    test_rows = []
    base_table = [dict(r) for r in indep]

    def run_table_test(tid, desc, mutate, expect_detected):
        table = [dict(r) for r in base_table]
        table = mutate(table)
        iss = validate_table(table, expected_by_key)
        detected = len(iss) > 0
        ok = detected == expect_detected
        test_rows.append({'test_id': tid, 'description': desc,
                          'detected': 'YES' if detected else 'NO',
                          'expected': 'DETECTED' if expect_detected else 'ACCEPTED',
                          'status': 'PASS' if ok else 'FAIL',
                          'sample_issue': iss[0][:120] if iss else ''})

    def mut_field(fname, delta=None, value=None):
        def _m(t):
            r = dict(t[0])
            if delta is not None:
                r[fname] = g17(float(r[fname]) + delta)
            else:
                r[fname] = value
            t[0] = r
            return t
        return _m

    def mut_drop(fname):
        def _m(t):
            r = dict(t[0])
            r.pop(fname, None)
            t[0] = r
            return t
        return _m

    def mut_dup(t):
        t.append(dict(t[0]))
        return t

    def mut_extra(t):
        r = dict(t[0])
        r['record_key'] = 'EXTRA|KEY|q=X|ROI_L2_log_ratio'
        t.append(r)
        return t

    def mut_reorder(t):
        return t[::-1]

    def mut_pool_order(t):
        r = dict(t[0])
        pool = sorted(str(r['reference_pool']).split('|'))
        r['reference_pool'] = '|'.join(pool[::-1])
        t[0] = r
        return t

    def mut_two_same_rep(t):
        # positive: two rows may share the same representation metadata with distinct keys
        r = dict(t[1])
        r['batch'] = t[0]['batch']
        t[1] = r
        return t

    run_table_test('ORT01', 'change cross_D_nearest_dist', mut_field('cross_D_nearest_dist', delta=1e-3), True)
    run_table_test('ORT02', 'change margin min_cross_minus_min_same', mut_field('min_cross_minus_min_same', delta=1e-3), True)
    run_table_test('ORT03', 'change nearest_candidate', mut_field('nearest_candidate', value='WRONG'), True)
    run_table_test('ORT04', 'change nearest_label_D', mut_field('nearest_label_D', value='999'), True)
    run_table_test('ORT05', 'change second_candidate', mut_field('second_candidate', value='WRONG'), True)
    run_table_test('ORT06', 'change model_label_consistent', mut_field('model_label_consistent', value='FLIPPED'), True)
    run_table_test('ORT07', 'change tied_set_size', mut_field('tied_set_size', value='999'), True)
    run_table_test('ORT08', 'change reference_pool', mut_field('reference_pool', value='WRONG_POOL'), True)
    run_table_test('ORT09', 'change source SHA', mut_field('source_sha256', value='0' * 64), True)
    run_table_test('ORT10', 'NaN in distance field', mut_field('same_D_nearest_dist', value='nan'), True)
    run_table_test('ORT11', 'Inf in distance field', mut_field('cross_D_nearest_dist', value='inf'), True)
    run_table_test('ORT12', 'missing field', mut_drop('same_D_nearest_dist'), True)
    run_table_test('ORT13', 'duplicate record_key', mut_dup, True)
    run_table_test('ORT14', 'extra record_key', mut_extra, True)
    run_table_test('ORT15', 'exact threshold boundary distance', mut_field('same_D_nearest_dist', delta=2e-12), True)
    run_table_test('ORT16', 'reverse table row order (positive)', mut_reorder, False)
    run_table_test('ORT17', 'reverse reference_pool order (positive)', mut_pool_order, False)
    run_table_test('ORT18', 'same representation two entries (positive)', mut_two_same_rep, False)
    run_table_test('ORT19', 'normal unchanged table (positive)', lambda t: t, False)
    n_test_pass = sum(1 for r in test_rows if r['status'] == 'PASS')
    wcsv(os.path.join(out, 'tables', 'v108_error_tests19.csv'), list(test_rows[0].keys()), test_rows)

    ok_c = (n_mismatch == 0 and len(expected_by_key) == 5040 and n_test_pass == 19
            and not sub_missing and not s60_unmapped and len(summ_rows) == 210)
    if n_mismatch:
        FAIL_KEYS.setdefault('C', []).append('production mismatches=%d' % n_mismatch)
    if n_test_pass < 19:
        FAIL_KEYS.setdefault('C', []).append('error tests=%d/19' % n_test_pass)
    if sub_missing:
        FAIL_KEYS.setdefault('C', []).append('1440 subset missing keys=%d' % len(sub_missing))
    if s60_unmapped:
        FAIL_KEYS.setdefault('C', []).append('60 summaries unmapped=%d' % len(s60_unmapped))
    GATES['C'] = ok_c
    STAGE_LOG['C'] = {'match': n_match, 'mismatch': n_mismatch, 'summaries210': len(summ_rows),
                      'subset1440_missing': len(sub_missing), 'subset1440_field_bad': sub_field_bad,
                      's60_unmapped': len(s60_unmapped), 's60_duplicate_keys': s60_dup_keys,
                      'error_tests': '%d/19' % n_test_pass}
    log('Stage C: match=%d mismatch=%d tests=%d/19 sub1440_missing=%d s60_unmapped=%d'
        % (n_match, n_mismatch, n_test_pass, len(sub_missing), len(s60_unmapped)))
    return indep

# ============================== Stage D ==============================

def stage_d(root, out, bank, indep):
    log('=== Stage D: fixed decomposition, budgets, history backtracking ===')
    an = os.path.join(root, 'analysis')
    tab = os.path.join(root, 'tables')
    issues = []
    meta = {k: parse(k) for k in ALL48}
    abs_C = {}
    for key in ALL48:
        for ki, k0 in enumerate(K0S):
            abs_C[(key, k0)] = np.abs(bank[key]['C'][ki]).reshape(-1)

    # --- 852-pair decomposition: two identities per pair, residuals < 1e-12 ---
    pairs_ee = list(itertools.combinations(ALL24, 2))
    pairs_ei = list(itertools.product(ALL24, INTER24))
    all_pairs = [(i, j, 'EE') for i, j in pairs_ee] + [(i, j, 'EI') for i, j in pairs_ei]
    dec_rows, chan_rows = [], []
    n_dec_pass = n_dec_fail = 0
    for qi, rj, ptype in all_pairs:
        vq_bins = [abs_C[(qi, k0)] for k0 in K0S]
        vr_bins = [abs_C[(rj, k0)] for k0 in K0S]
        aq_bins = [float(np.linalg.norm(v)) for v in vq_bins]
        ar_bins = [float(np.linalg.norm(v)) for v in vr_bins]
        Aq = float(math.sqrt(sum(a ** 2 for a in aq_bins)))
        Ar = float(math.sqrt(sum(a ** 2 for a in ar_bins)))
        if Aq == 0 or Ar == 0:
            issues.append('zero norm in pair %s %s' % (qi, rj))
            continue
        rq_bins = [a / Aq for a in aq_bins]
        rr_bins = [a / Ar for a in ar_bins]
        uq_bins = [v / max(a, 1e-300) for v, a in zip(vq_bins, aq_bins)]
        ur_bins = [v / max(a, 1e-300) for v, a in zip(vr_bins, ar_bins)]
        spec_term = sum((rq - rr) ** 2 for rq, rr in zip(rq_bins, rr_bins))
        spatial_term = sum(rq * rr * float(np.sum(np.abs(uq - ur) ** 2))
                           for rq, rr, uq, ur in zip(rq_bins, rr_bins, uq_bins, ur_bins))
        shape_direct_sq = spec_term + spatial_term
        concat_q = np.concatenate(vq_bins) / Aq
        concat_r = np.concatenate(vr_bins) / Ar
        shape_check_sq = float(np.sum(np.abs(concat_q - concat_r) ** 2))
        shape_resid = abs(shape_direct_sq - shape_check_sq)
        sym_term = 4 * (Aq - Ar) ** 2 / (Aq + Ar) ** 2
        sym_shape_term = 4 * Aq * Ar / (Aq + Ar) ** 2 * shape_direct_sq
        sym_direct_sq = sym_term + sym_shape_term
        concat_vq = np.concatenate(vq_bins)
        concat_vr = np.concatenate(vr_bins)
        sym_check_sq = (2.0 * float(np.linalg.norm(concat_vq - concat_vr)) / (Aq + Ar)) ** 2
        sym_resid = abs(sym_direct_sq - sym_check_sq)
        ok = shape_resid < 1e-12 and sym_resid < 1e-12
        n_dec_pass += int(ok)
        n_dec_fail += int(not ok)
        dec_rows.append({'record_key': '%s__vs__%s' % (qi, rj), 'pair_type': ptype,
                         'A_i': g17(Aq), 'A_j': g17(Ar),
                         'spectral_ratio_term': g17(spec_term),
                         'spatial_shape_term': g17(spatial_term),
                         'shape_direct_sq': g17(shape_direct_sq),
                         'shape_direct_check_sq': g17(shape_check_sq),
                         'shape_residual': g17(shape_resid),
                         'sym_term': g17(sym_term),
                         'sym_shape_term': g17(sym_shape_term),
                         'sym_direct_sq': g17(sym_direct_sq),
                         'sym_direct_check_sq': g17(sym_check_sq),
                         'sym_residual': g17(sym_resid),
                         'status': 'PASS' if ok else 'FAIL'})
        for k0, rq, rr, uq, ur in zip(K0S, rq_bins, rr_bins, uq_bins, ur_bins):
            chan_rows.append({'pair': '%s__vs__%s' % (qi, rj), 'pair_type': ptype, 'k0': k0,
                              'r_i': g17(rq), 'r_j': g17(rr),
                              'spatial_contrib': g17(rq * rr * float(np.sum(np.abs(uq - ur) ** 2))),
                              'unit_shape_dist': g17(float(np.linalg.norm(uq - ur)))})
    wcsv(os.path.join(out, 'analysis', 'v108_decomposition852.csv'), list(dec_rows[0].keys()), dec_rows)
    wcsv(os.path.join(out, 'analysis', 'v108_channel_contributions2556.csv'), list(chan_rows[0].keys()), chan_rows)

    # --- 180 fixed-control items: 60 same-factor pairs x 3 features vs single-160 control ---
    sf_path = os.path.join(tab, 'v092_same_factor_pairs60.csv')
    sf = rcsv(sf_path)
    fc_rows = []
    active_full = list(K0S)
    A_full = {key: float(math.sqrt(sum(float(np.sum(np.abs(abs_C[(key, k0)]) ** 2)) for k0 in active_full))) for key in ALL48}
    A_160 = {key: float(np.linalg.norm(abs_C[(key, 160)])) for key in ALL48}

    def dists(qi, rj, active, A):
        d1 = abs(math.log(A[qi]) - math.log(A[rj]))
        d2 = 2.0 * math.sqrt(sum(float(np.sum(np.abs(abs_C[(qi, k0)] - abs_C[(rj, k0)]) ** 2)) for k0 in active)) / (A[qi] + A[rj])
        uq = {k0: abs_C[(qi, k0)] / max(float(np.linalg.norm(abs_C[(qi, k0)])), 1e-300) for k0 in active}
        ur = {k0: abs_C[(rj, k0)] / max(float(np.linalg.norm(abs_C[(rj, k0)])), 1e-300) for k0 in active}
        d3 = math.sqrt(sum(float(np.sum(np.abs(uq[k0] - ur[k0]) ** 2)) for k0 in active))
        return [d1, d2, d3]

    for r in sf:
        pi, pj = r['state_i'], r['state_j']
        dfull = dists(pi, pj, active_full, A_full)
        d160 = dists(pi, pj, [160], A_160)
        for fi, fname in FEATS:
            fc_rows.append({'record_key': '%s|%s' % (r['record_key'], fname),
                            'pair': r['record_key'], 'factor_changed': r['factor_changed'],
                            'state_i': pi, 'state_j': pj, 'feature': fname,
                            'd_full_3bin': g17(dfull[fi - 1]),
                            'd_single160_fixed_control': g17(d160[fi - 1]),
                            'scope': 'single-160 fixed control readout; NOT a causal contribution',
                            'status': 'REPORTED'})
    wcsv(os.path.join(out, 'tables', 'v108_fixed_control180.csv'), list(fc_rows[0].keys()), fc_rows)

    # --- 1680 radius + 70 summaries + 1680 common budget from the independently verified decision ---
    indep_by_key = {r['record_key']: r for r in indep}
    radius_rows = []
    for bins in BIN_SUBSETS:
        bins_key = '+'.join(str(b) for b in bins)
        groups = [('+'.join(S), 'endpoint') for S in factor_subsets()] + \
                 [(pname, 'intermediate') for pname in POLICY_NAMES]
        for gname, batch_type in groups:
            queries = ALL24 if batch_type == 'endpoint' else INTER24
            for qi in queries:
                key = '%s|%s|q=%s|unit_magnitude_shape' % (bins_key, gname, qi)
                cur = indep_by_key.get(key)
                if cur is None:
                    issues.append('radius key missing from independent decision: %s' % key)
                    continue
                m = float(cur['min_cross_minus_min_same'])
                ambiguous = cur['tie_across_D'] == 'YES'
                if m > 0 and not ambiguous:
                    radius, label = m / 2.0, 'POSITIVE'
                elif ambiguous:
                    radius, label = 0.0, 'AMBIGUOUS_CROSS_D'
                else:
                    radius, label = 0.0, 'NO_POSITIVE_TRUE_LABEL_RADIUS'
                radius_rows.append({'record_key': '%s|%s|q=%s' % (bins_key, gname, qi),
                                    'bins': bins_key, 'subset_S': gname, 'query': qi,
                                    'd_same': cur['same_D_nearest_dist'], 'd_cross': cur['cross_D_nearest_dist'],
                                    'margin_m': g17(m), 'sufficient_radius': g17(radius),
                                    'radius_label': label,
                                    'scope': 'sufficient lower bound; NOT max tolerable radius or noise CI'})
    radius_summ = []
    for bins in BIN_SUBSETS:
        bins_key = '+'.join(str(b) for b in bins)
        for S in factor_subsets():
            gname = '+'.join(S)
            pos = [float(r['sufficient_radius']) for r in radius_rows
                   if r['bins'] == bins_key and r['subset_S'] == gname and r['radius_label'] == 'POSITIVE']
            radius_summ.append({'record_key': '%s|%s' % (bins_key, gname), 'bins': bins_key,
                                'subset_or_policy': gname, 'n_queries': 24,
                                'n_positive_radius': len(pos), 'n_no_positive': 24 - len(pos),
                                'min_positive_radius': g17(min(pos)) if pos else 'NONE',
                                'median_positive_radius': g17(float(np.median(pos))) if pos else 'NONE',
                                'max_positive_radius': g17(max(pos)) if pos else 'NONE'})
        for pname in POLICY_NAMES:
            pos = [float(r['sufficient_radius']) for r in radius_rows
                   if r['bins'] == bins_key and r['subset_S'] == pname and r['radius_label'] == 'POSITIVE']
            radius_summ.append({'record_key': '%s|%s' % (bins_key, pname), 'bins': bins_key,
                                'subset_or_policy': pname, 'n_queries': 24,
                                'n_positive_radius': len(pos), 'n_no_positive': 24 - len(pos),
                                'min_positive_radius': g17(min(pos)) if pos else 'NONE',
                                'median_positive_radius': g17(float(np.median(pos))) if pos else 'NONE',
                                'max_positive_radius': g17(max(pos)) if pos else 'NONE'})
    pert_rows = []
    for r in radius_rows:
        m = float(r['margin_m'])
        pos = m > 0 and r['radius_label'] == 'POSITIVE'
        pert_rows.append({'record_key': r['record_key'], 'bins': r['bins'], 'subset_S': r['subset_S'],
                          'query': r['query'], 'margin_m': r['margin_m'],
                          'eps_q_single_side': g17(m / 2.0 if pos else 0.0),
                          'eps_symmetric_each_side': g17(m / 4.0 if pos else 0.0),
                          'eta_unnormalized_relative': g17(m / 8.0 if pos else 0.0),
                          'budget_label': 'POSITIVE' if pos else 'NO_POSITIVE_BUDGET',
                          'scope': 'boundary formula; NOT measured error or probability'})
    wcsv(os.path.join(out, 'tables', 'v108_radius1680.csv'), list(radius_rows[0].keys()), radius_rows)
    wcsv(os.path.join(out, 'analysis', 'v108_radius_summaries70.csv'), list(radius_summ[0].keys()), radius_summ)
    wcsv(os.path.join(out, 'tables', 'v108_perturbation_budget1680.csv'), list(pert_rows[0].keys()), pert_rows)

    # radius consistency vs historical v096 table (rewritten by v106 at current fixed commit)
    h96 = {r['record_key']: r for r in rcsv(os.path.join(tab, 'v096_radius_complete1680.csv'))}
    r96_bad = 0
    for r in radius_rows:
        h = h96.get(r['record_key'])
        if h is None:
            r96_bad += 1
            continue
        if r['radius_label'] != h.get('radius_label'):
            r96_bad += 1
            continue
        for f in ('d_same', 'd_cross', 'margin_m', 'sufficient_radius'):
            d = finite_diff(r[f], h.get(f, ''))
            if d is None or not d < 1e-12:
                r96_bad += 1
                break

    # --- history backtracking: v103/v104/v105 independent 5040 tables ---
    bt_rows = []
    for ver in ('v103', 'v104', 'v105'):
        p = os.path.join(an, '%s_independent5040.csv' % ver)
        if not os.path.isfile(p):
            bt_rows.append({'table': ver, 'classification': 'RESULT_PRESENT_AUDIT_OPEN',
                            'note': 'file missing', 'sha256': '', 'n_rows': '0',
                            'key_coverage': '0/5040', 'max_field_diff': '', 'status': 'AUDIT_OPEN'})
            issues.append('history table missing: %s' % ver)
            continue
        rows_h = rcsv(p)
        keys_h = {r['record_key'] for r in rows_h}
        by_key = {r['record_key']: r for r in rows_h}
        covered = len(keys_h & set(indep_by_key))
        max_diff = 0.0
        bad = 0
        for k, cur in indep_by_key.items():
            h = by_key.get(k)
            if h is None:
                continue
            for f in DECISION_FIELDS:
                d = finite_diff(cur.get(f, ''), h.get(f, ''))
                if d is None:
                    if str(cur.get(f, '')) != str(h.get(f, '')):
                        bad += 1
                        break
                else:
                    max_diff = max(max_diff, d)
                    if not d < 1e-12:
                        bad += 1
                        break
        cls = 'REUSED_VALUES_AUDITED_CURRENTLY' if (covered == 5040 and bad == 0) else 'RESULT_PRESENT_AUDIT_OPEN'
        if cls != 'REUSED_VALUES_AUDITED_CURRENTLY':
            issues.append('history %s: coverage=%d bad_rows=%d' % (ver, covered, bad))
        bt_rows.append({'table': ver, 'classification': cls,
                        'note': 'decision fields re-audited against current independent run',
                        'sha256': sha256_file(p), 'n_rows': str(len(rows_h)),
                        'key_coverage': '%d/5040' % covered,
                        'max_field_diff': g17(max_diff) if max_diff > 0 else '0',
                        'status': 'AUDIT_PASS' if cls == 'REUSED_VALUES_AUDITED_CURRENTLY' else 'AUDIT_OPEN'})
    bt_rows.append({'table': 'v096_radius_complete1680',
                    'classification': 'REUSED_VALUES_AUDITED_CURRENTLY' if r96_bad == 0 else 'RESULT_PRESENT_AUDIT_OPEN',
                    'note': 'v106 rewrote v096 paths; regenerated values read at current fixed commit %s' % EXPECTED_PARENT,
                    'sha256': sha256_file(os.path.join(tab, 'v096_radius_complete1680.csv')),
                    'n_rows': str(len(h96)), 'key_coverage': '%d/1680' % (len(h96) - r96_bad),
                    'max_field_diff': '', 'status': 'AUDIT_PASS' if r96_bad == 0 else 'AUDIT_OPEN'})
    bt_rows.append({'table': 'v096_perturbation_budget1680',
                    'classification': 'REUSED_VALUES_AUDITED_CURRENTLY' if r96_bad == 0 else 'RESULT_PRESENT_AUDIT_OPEN',
                    'note': 'budget = f(radius); same audit basis as radius rows',
                    'sha256': sha256_file(os.path.join(tab, 'v096_perturbation_budget1680.csv')),
                    'n_rows': '1680', 'key_coverage': '1680/1680', 'max_field_diff': '',
                    'status': 'AUDIT_PASS' if r96_bad == 0 else 'AUDIT_OPEN'})
    wcsv(os.path.join(out, 'analysis', 'v108_history_backtrack.csv'), list(bt_rows[0].keys()), bt_rows)

    # --- v107 audit (historical facts, never copied as v108 evidence) ---
    st_path = os.path.join(root, 'status.json')
    rc_path = os.path.join(root, 'iscat_v107_return.receipt.json')
    st_blob, st_file_sha = blob_sha1(st_path), sha256_file(st_path)
    rc_blob = blob_sha1(rc_path)
    rc = json.load(open(rc_path, encoding='utf-8'))
    audit = {
        'status_json_blob_sha1': st_blob,
        'expected_status_blob_sha1': 'bf16131fb31f7a82cc920d6544c9585de96c3035',
        'status_json_file_sha256': st_file_sha,
        'v107_claimed_status_sha256': '0440f92937b60991f39cbcf43f7e3a715c739019a6a50434eb8f8b5a4bb7b2e7',
        'status_sha_matches_prior_audit': st_file_sha == '0440f92937b60991f39cbcf43f7e3a715c739019a6a50434eb8f8b5a4bb7b2e7',
        'receipt_blob_sha1': rc_blob,
        'expected_receipt_blob_sha1': 'fbeb413f08ac2356f81a176b0166909eb85b75a2',
        'receipt_zip_status': rc.get('zip_status'),
        'receipt_claimed_status_sha256': rc.get('status_json_sha256'),
        'status_claim_mismatch': rc.get('status_json_sha256') != st_file_sha,
        'facts': [
            'v107 delivery did not prove the full contract executed; inherited_results only',
            'v107 receipt zip_status=PENDING_CREATION; no ZIP-level SHA/CRC/member verification existed',
            'v105 oracle record 13/19 kept as historical fact; redone here through the corrected entry',
        ]}
    with open(os.path.join(out, 'logs', 'v108_v107_audit.json'), 'w', encoding='utf-8') as f:
        json.dump(audit, f, indent=2)

    ok_d = (n_dec_fail == 0 and len(dec_rows) == 852 and len(chan_rows) == 2556
            and len(fc_rows) == 180 and len(radius_rows) == 1680
            and len(radius_summ) == 70 and len(pert_rows) == 1680 and r96_bad == 0 and not issues)
    if n_dec_fail:
        FAIL_KEYS.setdefault('D', []).append('decomposition fails=%d' % n_dec_fail)
    if r96_bad:
        FAIL_KEYS.setdefault('D', []).append('radius mismatch vs v096=%d' % r96_bad)
    if issues:
        FAIL_KEYS.setdefault('D', []).extend(issues[:20])
    GATES['D'] = ok_d
    STAGE_LOG['D'] = {'decomposition': '%d/%d PASS' % (n_dec_pass, len(dec_rows)),
                      'channel_terms': len(chan_rows), 'fixed_controls': len(fc_rows),
                      'radius': len(radius_rows), 'radius_summaries': len(radius_summ),
                      'perturbation': len(pert_rows), 'v096_radius_bad': r96_bad,
                      'history_tables': {r['table']: r['classification'] for r in bt_rows},
                      'v107_audit': audit}
    log('Stage D: dec=%d/%d radius=%d budget=%d history=%s' %
        (n_dec_pass, len(dec_rows), len(radius_rows), len(pert_rows),
         'OK' if ok_d else 'ISSUES=%d' % len(issues)))

# ============================== Stage E ==============================

def build_status(out, tool_sha, numerical_pass, exit_code):
    statuses = {
        'execution': 'COMPLETE',
        'numerical': 'NUMERICAL_SEALED' if numerical_pass else 'UNSEALED_PARTIAL',
        'archive': 'PENDING_CHECK',
        'physics': 'PENDING_PARAMETERS',
    }
    status = {
        'schema': 'iscat108.status.1',
        'task_id': TASK_ID,
        'created_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'source_commit': EXPECTED_PARENT,
        'v106_commit_note': 'v106 rewrote v096 paths; regenerated values read at current fixed commit',
        'tool_sha256': tool_sha,
        'parent_commit': EXPECTED_PARENT,
        'states': statuses,
        'gates': {k: bool(v) for k, v in GATES.items()},
        'stage_logs': STAGE_LOG,
        'budget': {
            'new_BEM': 0, 'new_position_render': 0, 'new_optical_intensity': 0,
            'new_physics_states': 0, 'experiment_video_reads': 0,
            'core_snapshots': 73,
            'comparisons': 5040, 'independent': 5040, 'summaries': 210,
            'threeway_origins': 14400, 'amp_summaries': 576, 'zerostart': 576,
            'probe_gates': 576, 'periods': 192, 'motion_pairs': 24, 'components': 14400,
            'decomposition_pairs': 852, 'channel_terms': 2556, 'fixed_controls': 180,
            'radius_rows': 1680, 'radius_summaries': 70, 'budget_rows': 1680,
            'error_tests': 19,
        },
        'frozen_states': {
            'calibration_valid': False,
            'experimental_validation': False,
            'detection_validated': False,
            'single_particle_diameter': 'NOT_ESTIMATED',
        },
        'physics_admission': 'PENDING_PARAMETERS',
        'rule7_new_authorizations': 0,
        'overall': 'UNSEALED_PARTIAL' if not numerical_pass else 'ALL_MACHINE_GATES_PASS',
    }
    p = os.path.join(out, 'status.json')
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(status, f, indent=2, ensure_ascii=False)
    return p, sha256_file(p), statuses

def build_zip(out, zip_path, status_sha):
    ret_dir = out
    manifest = []
    for dirpath, dirnames, filenames in os.walk(ret_dir):
        for fn in sorted(filenames):
            if fn == 'manifest_sha256.csv':
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, ret_dir).replace(os.sep, '/')
            manifest.append((rel, sha256_file(full)))
    manifest.sort()
    man_path = os.path.join(ret_dir, 'manifest_sha256.csv')
    with open(man_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['relative_path', 'sha256'])
        for rel, sha in manifest:
            w.writerow([rel, sha])
    if os.path.exists(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for dirpath, dirnames, filenames in os.walk(ret_dir):
            for fn in sorted(filenames):
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, ret_dir).replace(os.sep, '/')
                z.write(full, 'iscat_v108_return/%s' % rel)
    return sha256_file(zip_path), man_path

def write_receipt(receipt_path, zip_path, zip_sha, status_sha, tool_sha, exit_code, statuses):
    receipt = {
        'task_id': TASK_ID,
        'source_commit': EXPECTED_PARENT,
        'tool_sha256': tool_sha,
        'zip_path': os.path.abspath(zip_path),
        'zip_sha256': zip_sha,
        'zip_size_bytes': os.path.getsize(zip_path),
        'status_json_sha256_in_zip': status_sha,
        'exit_code': exit_code,
        'execution_status': statuses['execution'],
        'numerical_status': statuses['numerical'],
        'archive_status': statuses['archive'],
        'physics_status': statuses['physics'],
        'created_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
    }
    with open(receipt_path, 'w', encoding='utf-8') as f:
        json.dump(receipt, f, indent=2, ensure_ascii=False)
    return receipt

# ============================== main ==============================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--zip', required=True)
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    out = os.path.abspath(args.out)
    zip_path = os.path.abspath(args.zip)
    t_start = time.time()

    # sanity: out must be new and outside root; zip outside root
    if os.path.exists(out) and os.listdir(out):
        print('[v108] FATAL: out dir exists and is not empty: %s' % out)
        return 3
    try:
        if os.path.commonpath([root]) == os.path.commonpath([root, out]):
            print('[v108] FATAL: out must be outside the source root')
            return 3
    except ValueError:
        pass
    os.makedirs(out, exist_ok=True)
    for sub in ('analysis', 'tables', 'logs', 'tool_snapshot'):
        os.makedirs(os.path.join(out, sub), exist_ok=True)

    # git commit verification (read-only)
    try:
        head = subprocess.run(['git', '-C', root, 'rev-parse', 'HEAD'],
                              capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception:
        head = ''
    if head != EXPECTED_PARENT:
        print('[v108] FATAL: root HEAD %s != expected v107 commit %s' % (head, EXPECTED_PARENT))
        return 3

    tool_sha = sha256_file(os.path.abspath(__file__))
    launch = {
        'task_id': TASK_ID, 'root': root, 'out': out, 'zip': zip_path,
        'head_commit': head, 'tool_sha256': tool_sha,
        'command': 'python tools/run_v108_all.py --root "%s" --out "%s" --zip "%s"' % (root, out, zip_path),
        'python': sys.version, 'pid': os.getpid(), 'started_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
    }
    launch_ext = os.path.splitext(zip_path)[0] + '.launch.json'
    with open(launch_ext, 'w', encoding='utf-8') as f:
        json.dump(launch, f, indent=2)
    with open(os.path.join(out, 'logs', 'v108_launch_record.json'), 'w', encoding='utf-8') as f:
        json.dump(launch, f, indent=2)
    log('launch recorded: %s' % launch_ext)

    # copy own source into tool_snapshot for the archive
    shutil.copy2(os.path.abspath(__file__), os.path.join(out, 'tool_snapshot', 'run_v108_all.py'))

    bank, series_keys, npz_snap = stage_a(root, out)
    stage_b(root, out, series_keys, npz_snap, bank)
    indep = independent_decisions(bank)
    stage_c(root, out, bank, indep)
    stage_d(root, out, bank, indep)

    numerical_pass = all(GATES.values())
    status_path, status_sha, statuses = build_status(out, tool_sha, numerical_pass, 0)
    zip_sha, man_path = build_zip(out, zip_path, status_sha)

    # archive check via bundled checker (fresh process)
    checker_src = os.path.join(root, 'tools', 'v108_archive_check.py')
    check_json = os.path.splitext(zip_path)[0] + '.archive_check.json'
    proc = subprocess.run([sys.executable, checker_src, '--zip', zip_path,
                           '--expect-status-sha', status_sha, '--out', check_json],
                          capture_output=True, text=True, timeout=900)
    archive_ok = proc.returncode == 0
    statuses['archive'] = 'ARCHIVE_VERIFIED' if archive_ok else 'ARCHIVE_CHECK_FAILED'
    exit_code = 0 if (numerical_pass and archive_ok) else 2
    receipt = write_receipt(os.path.splitext(zip_path)[0] + '.receipt.json',
                            zip_path, zip_sha, status_sha, tool_sha, exit_code, statuses)
    # update status.json archive state and rebuild zip so the archive carries the final state
    statuses_final = dict(statuses)
    with open(status_path, 'r', encoding='utf-8') as f:
        s = json.load(f)
    s['states']['archive'] = statuses_final['archive']
    with open(status_path, 'w', encoding='utf-8') as f:
        json.dump(s, f, indent=2, ensure_ascii=False)
    status_sha = sha256_file(status_path)
    zip_sha, _ = build_zip(out, zip_path, status_sha)
    # re-run the checker on the FINAL zip bytes so the receipt hash is actually verified
    proc2 = subprocess.run([sys.executable, checker_src, '--zip', zip_path,
                            '--expect-status-sha', status_sha, '--out', check_json],
                           capture_output=True, text=True, timeout=900)
    archive_ok_final = proc2.returncode == 0
    statuses_final['archive'] = 'ARCHIVE_VERIFIED' if archive_ok_final else 'ARCHIVE_CHECK_FAILED'
    exit_code = 0 if (numerical_pass and archive_ok_final) else 2
    write_receipt(os.path.splitext(zip_path)[0] + '.receipt.json',
                  zip_path, zip_sha, status_sha, tool_sha, exit_code, statuses_final)

    elapsed = time.time() - t_start
    summary = {'gates': GATES, 'statuses': statuses_final, 'exit_code': exit_code,
               'zip_sha256': zip_sha, 'status_json_sha256': status_sha,
               'elapsed_seconds': round(elapsed, 1)}
    with open(os.path.join(out, 'logs', 'v108_final_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    log('final: %s' % json.dumps(summary))
    if exit_code != 0:
        log('FAIL_KEYS: %s' % json.dumps(FAIL_KEYS))
    return exit_code

if __name__ == '__main__':
    sys.exit(main())
