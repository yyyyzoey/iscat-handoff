# -*- coding: utf-8 -*-
"""v087 Phase C: INDEPENDENT time-domain FFT of the cached 7.29 experimental
41x41x2001 video (roiFrames from fft400_corrected_small_roi.mat).

This is a re-analysis of EXISTING cached data - no BMP reread, no new imaging.
The stored X400/C400/Imean are MATLAB single-precision results from
run_v073_replay_corrected.m; here every pixel's X_160 and C400 are recomputed
from the 2001 cached samples in double precision and compared.

Orientation discrimination happens FIRST at 2 asymmetric pixels (fixed), then
the full 1681-pixel audit, 12 fixed probe pixels (explicit DFT vs numpy FFT vs
stored X400, historical gate rel<1e-5 OR |dX|<1e-7), full-frame meanFloor mask
recheck, full-vs-small crop identity, and the fixed spectral neighbourhood."""
import os, sys, csv, json, hashlib
import numpy as np
import h5py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v083_common import ROOT

GH = os.path.join(ROOT, 'github_handoff')
TAB = os.path.join(GH, 'tables')
NUM = os.path.join(GH, 'numeric')
P_SMALL_C = os.path.join(NUM, 'fft400_corrected_small_roi.mat')
P_SMALL_W = os.path.join(ROOT, 'v073_return', 'numeric', 'fft400_corrected_small_roi.mat')
P_FULL = os.path.join(ROOT, 'v073_return', 'numeric', 'fft400_corrected_full.mat')
P_V072 = os.path.join(ROOT, 'v072_return', 'numeric', 'replay_729_frames1000_3000.mat')
N = 2001
K0 = 160  # 0-based; MATLAB bin 161
# 12 probe pixels fixed BEFORE any error computation: 4 corners, centre, 7 asymmetric
PROBES = [(0, 0), (0, 40), (40, 0), (40, 40), (20, 20), (20, 0), (0, 20),
          (5, 10), (10, 5), (33, 7), (7, 33), (15, 25)]
NEIGHBOUR_BINS_0BASED = [157, 158, 159, 160, 161, 162, 163, 168]  # MATLAB 158-164 + 420 control


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def g17(x):
    return '%.17g' % x


def series_at(frames, i, j):
    """Extract the 2001-sample series for h5-index (i, j): frames (N,1,41,41)."""
    return np.asarray(frames[:, i, j], dtype=np.float64)


def x160(series):
    s = np.asarray(series, dtype=np.float64)
    Im = float(s.mean())
    e = np.exp(-2j * np.pi * K0 * np.arange(N) / N)
    X = complex(np.sum((s - Im) * e))
    C = 2.0 * X / (N * Im) if Im != 0 else complex(np.nan)
    return Im, X, C


def main():
    schema_rows, audit_rows, probe_rows = [], [], []
    # schema + hash
    sha_c = sha256_file(P_SMALL_C)
    sha_w = sha256_file(P_SMALL_W)
    same = (sha_c == sha_w)
    with h5py.File(P_SMALL_C, 'r') as f:
        frames = np.asarray(f['roiFrames'][:, 0, :, :], dtype=np.float32)  # (2001,41,41)
        Xst = f['X400'][:]; Xst = Xst['real'].astype(np.float64) + 1j * Xst['imag'].astype(np.float64)
        Cst = f['C400'][:]; Cst = Cst['real'].astype(np.float64) + 1j * Cst['imag'].astype(np.float64)
        Imst = np.asarray(f['Imean']).astype(np.float64)
        maskst = np.asarray(f['validMask']).astype(bool)
        meanFloor = float(np.asarray(f['meanFloor']).flatten()[0])
        kM = float(np.asarray(f['k']).flatten()[0])
        Nf = float(np.asarray(f['N']).flatten()[0]); Fsf = float(np.asarray(f['Fs']).flatten()[0])
    schema_rows.append({'field': 'roiFrames', 'value': 'shape (2001,1,41,41) float32 (h5py); MATLAB (41,41,1,2001) single',
                        'note': 'time on h5py axis 0 (MATLAB last dim); spatial h5 axes: axis1=MATLAB col, axis2=MATLAB row (established below)'})
    schema_rows.append({'field': 'file_sha256_committed', 'value': sha_c, 'note': 'github_handoff/numeric copy'})
    schema_rows.append({'field': 'file_sha256_workstation', 'value': sha_w, 'note': 'v073 original; identical=%s' % same})
    schema_rows.append({'field': 'meanFloor_full_frame', 'value': g17(meanFloor), 'note': 'full-frame operator threshold from the v073 extractor, NOT ROI-local'})
    schema_rows.append({'field': 'k_matlab/N/Fs', 'value': '%g/%g/%g' % (kM, Nf, Fsf), 'note': 'MATLAB bin 161 = 0-based 160'})
    schema_rows.append({'field': 'stored_validMask_sum', 'value': str(int(maskst.sum())), 'note': 'of 1681'})

    # --- orientation discrimination at 2 asymmetric pixels (fixed) ---
    # hypothesis A: h5 spatial axes equal the stored-map axes (col,row) as-is
    # hypothesis B: transposed. Compare recomputed X vs stored X400.
    ori = {}
    for name, px in (('A_direct', (20, 0)), ('A2_direct', (0, 20)), ('B_transposed', (0, 20))):
        i, j = px
        Im, X, C = x160(series_at(frames, i, j))
        if name.startswith('A'):
            ref = Xst[i, j]
        else:
            ref = Xst[j, i]
        d = abs(X - ref)
        ori[name] = {'pixel_h5': (i, j), 'max_err': d, 'rel': d / max(abs(ref), 1e-300)}
    # correct orientation = the one where BOTH asymmetric pixels agree tightly
    errA = max(ori['A_direct']['max_err'], ori['A2_direct']['max_err'])
    errB = ori['B_transposed']['max_err']
    orientation = 'A_direct' if errA < errB else 'B_transposed'
    schema_rows.append({'field': 'orientation_test',
                        'value': '%s wins (errA=%s, errB=%s)' % (orientation, g17(errA), g17(errB)),
                        'note': '2 asymmetric pixels vs stored X400; wrong orientation must disagree'})
    ax_map = ('h5 (i,j) == stored map (i,j) [axis1=MATLAB col, axis2=MATLAB row]'
              if orientation == 'A_direct' else 'transposed')

    # --- full 1681-pixel independent recompute ---
    Xrec = np.zeros((41, 41), dtype=np.complex128)
    Crec = np.zeros((41, 41), dtype=np.complex128)
    Imrec = np.zeros((41, 41))
    for i in range(41):
        for j in range(41):
            Im, X, C = x160(series_at(frames, i, j))
            Xrec[i, j] = X; Crec[i, j] = C; Imrec[i, j] = Im
    dX = Xrec - Xst
    dC = Crec - Cst
    dIm = Imrec - Imst
    absdX = np.abs(dX); absdC = np.abs(dC)
    # quantiles over all pixels (near-zero handled by absolute values)
    q = lambda a, p: float(np.quantile(a, p))
    # mask rule recheck with the FULL-FRAME floor
    mask_rule = np.isfinite(Imrec) & (Imrec > meanFloor)
    n_disagree = int(np.sum(mask_rule != maskst))
    # all-zero-invalid policy: stored mask is 1681/1681; recomputed agrees?
    audit_summary = {
        'max_abs_dX': float(absdX.max()), 'median_abs_dX': q(absdX, 0.5),
        'q90_abs_dX': q(absdX, 0.9), 'q99_abs_dX': q(absdX, 0.99),
        'max_abs_dC': float(absdC.max()), 'median_abs_dC': q(absdC, 0.5),
        'max_abs_dImean': float(np.max(np.abs(dIm))),
        'mask_rule_disagreements': n_disagree,
        'stored_mask_sum': int(maskst.sum()), 'rule_mask_sum': int(mask_rule.sum())}
    # per-pixel audit table (1681 rows)
    for i in range(41):
        for j in range(41):
            audit_rows.append({
                'record_key': 'h5_%02d_%02d' % (i, j), 'pixel_h5_i': i, 'pixel_h5_j': j,
                'X400_stored_Re': g17(Xst[i, j].real), 'X400_stored_Im': g17(Xst[i, j].imag),
                'X160_recomputed_Re': g17(Xrec[i, j].real), 'X160_recomputed_Im': g17(Xrec[i, j].imag),
                'abs_dX': g17(absdX[i, j]), 'rel_dX': g17(absdX[i, j] / max(abs(Xst[i, j]), 1e-300)),
                'abs_dC': g17(absdC[i, j]),
                'C400_stored_abs': g17(abs(Cst[i, j])), 'C400_recomputed_abs': g17(abs(Crec[i, j])),
                'Imean_stored': g17(Imst[i, j]), 'Imean_recomputed': g17(Imrec[i, j]),
                'abs_dImean': g17(abs(dIm[i, j])),
                'near_zero_flag': 'NEAR_ZERO_USE_ABSOLUTE' if abs(Cst[i, j]) < 1e-6 else ''})

    # --- 12 fixed probes: explicit DFT vs numpy FFT vs stored X400 ---
    for (i, j) in PROBES:
        s = series_at(frames, i, j)
        Im, X, C = x160(s)
        Xfft = np.fft.fft(s - s.mean())[K0]
        d_fft_dft = abs(Xfft - X)
        d_stored = abs(X - Xst[i, j])
        rel = d_stored / max(abs(Xst[i, j]), 1e-300)
        gate_ok = (rel < 1e-5) or (d_stored < 1e-7)
        probe_rows.append({
            'record_key': 'probe_%02d_%02d' % (i, j), 'pixel_h5_i': i, 'pixel_h5_j': j,
            'X_explicit_DFT_Re': g17(X.real), 'X_explicit_DFT_Im': g17(X.imag),
            'X_numpy_FFT_Re': g17(Xfft.real), 'X_numpy_FFT_Im': g17(Xfft.imag),
            'abs_dft_vs_fft': g17(d_fft_dft),
            'X400_stored_Re': g17(Xst[i, j].real), 'X400_stored_Im': g17(Xst[i, j].imag),
            'abs_vs_stored': g17(d_stored), 'rel_vs_stored': g17(rel),
            'stored_precision': 'MATLAB single (float32 accumulation)',
            'historical_gate': 'rel<1e-5 OR |dX|<1e-7 (same-definition probe comparison only)',
            'status': 'PASS' if gate_ok else 'FAIL'})

    # --- full-vs-small crop identity ---
    try:
        with h5py.File(P_FULL, 'r') as f:
            Ck = f['C_k'][:]  # h5py (352,296): axis0=MATLAB col(352), axis1=MATLAB row(296)
            sha_full = sha256_file(P_FULL)
        # small ROI = full rows 128:168, cols 156:196 (MATLAB 1-based)
        # h5 full: axis0=col -> slice 155:196; axis1=row -> slice 127:168
        crop = Ck[155:196, 127:168]
        crop = crop['real'].astype(np.float64) + 1j * crop['imag'].astype(np.float64)
        crop_err = float(np.max(np.abs(crop - Cst)))
        crop_status = 'CROP_IDENTITY_CONFIRMED' if crop_err < 1e-6 * max(1.0, float(np.max(np.abs(Cst)))) else 'CROP_MISMATCH'
    except Exception as exc:
        crop_err = float('nan'); crop_status = 'FULL_SOURCE_ERROR: %s' % exc; sha_full = '-'
    schema_rows.append({'field': 'full_vs_small_crop', 'value': '%s (max|dC|=%s)' % (crop_status, g17(crop_err)),
                        'note': 'full C_k rows 128:168, cols 156:196 (MATLAB 1-based), h5py axes (col,row); full sha=%s' % sha_full[:16]})

    # --- fixed spectral neighbourhood ---
    neigh_rows = []
    e_all = {kb: np.exp(-2j * np.pi * kb * np.arange(N) / N) for kb in NEIGHBOUR_BINS_0BASED}
    for kb in NEIGHBOUR_BINS_0BASED:
        Xb = np.tensordot(e_all[kb], frames.astype(np.float64), axes=(0, 0))
        mean_absX = float(np.mean(np.abs(Xb)[maskst]))
        kM = kb + 1
        freq = kM * 5000.0 / 2001.0
        neigh_rows.append({'k_matlab': kM, 'k0_0based': kb,
                           'actualFreq_Hz': '%.6f' % freq,
                           'roi_mean_absX_recomputed': g17(mean_absX),
                           'note': 'fixed neighbourhood of the 400 Hz bin; ASSOCIATION_ONLY_NOT_CAUSAL_MAGNETIC_SIGNAL'})
    # v072 legacy negative control
    schema_rows.append({'field': 'v072_replay_frames', 'value': sha256_file(P_V072),
                        'note': 'LEGACY_WRONG_AXIS_NEGATIVE - v072 applied fft(signal,[],4) with a 3D array (wrong axis); never a valid experimental observation'})

    # --- NPZ samples: 2 asymmetric pixels ---
    np.savez_compressed(os.path.join(NUM, 'v087_cached_experimental_pixels.npz'),
                        source_file='fft400_corrected_small_roi.mat',
                        source_sha256=sha_c,
                        pixel_A_h5=(20, 0), pixel_B_h5=(0, 20),
                        series_A=series_at(frames, 20, 0), series_B=series_at(frames, 0, 20),
                        X160_A=np.array([Xrec[20, 0].real, Xrec[20, 0].imag]),
                        X160_B=np.array([Xrec[0, 20].real, Xrec[0, 20].imag]),
                        X400_stored_A=np.array([Xst[20, 0].real, Xst[20, 0].imag]),
                        X400_stored_B=np.array([Xst[0, 20].real, Xst[0, 20].imag]),
                        orientation=orientation, meanFloor_full_frame=meanFloor)

    # --- outputs ---
    with open(os.path.join(TAB, 'v087_experiment_roi_schema_and_hash.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['field', 'value', 'note'], lineterminator='\n'); w.writeheader(); w.writerows(schema_rows)
    with open(os.path.join(TAB, 'v087_cached_frames_fft_operator_audit.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['record_key'] + [k for k in audit_rows[0].keys() if k != 'record_key'], lineterminator='\n'); w.writeheader(); w.writerows(audit_rows)
    with open(os.path.join(TAB, 'v087_cached_frames_fft_probes12.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['record_key'] + [k for k in probe_rows[0].keys() if k != 'record_key'], lineterminator='\n'); w.writeheader(); w.writerows(probe_rows)
    with open(os.path.join(TAB, 'v087_full_small_crop_identity.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(['item', 'value'])
        w.writerow(['crop_window_matlab_1based', 'rows 128:168, cols 156:196'])
        w.writerow(['max_abs_dC_small_vs_full_crop', g17(crop_err)])
        w.writerow(['status', crop_status])
        w.writerow(['full_file_sha256', sha_full])
    with open(os.path.join(TAB, 'v087_spectral_neighbors_fixed.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(neigh_rows[0].keys()), lineterminator='\n'); w.writeheader(); w.writerows(neigh_rows)
    # readback
    for name, nexp in (('v087_experiment_roi_schema_and_hash.csv', len(schema_rows)),
                       ('v087_cached_frames_fft_operator_audit.csv', 1681),
                       ('v087_cached_frames_fft_probes12.csv', 12),
                       ('v087_spectral_neighbors_fixed.csv', 8)):
        with open(os.path.join(TAB, name), 'r', newline='', encoding='utf-8') as f:
            rr = list(csv.reader(f))
        assert len(rr) - 1 == nexp and all(len(x) == len(rr[0]) for x in rr), name
    probes_ok = all(r['status'] == 'PASS' for r in probe_rows)
    summary = {'phase': 'C', 'orientation': orientation, 'errA_direct': g17(errA),
               'errB_transposed': g17(errB), 'probes_pass': bool(probes_ok),
               'max_abs_dX_vs_stored': audit_summary['max_abs_dX'],
               'max_abs_dC_vs_stored': audit_summary['max_abs_dC'],
               'max_abs_dImean': audit_summary['max_abs_dImean'],
               'mask_rule_disagreements': n_disagree, 'crop_status': crop_status,
               'new_2001frame_SIMULATIONS': 0,
               'note': 'cached-video re-analysis only (authorised single 41x41x2001 FFT pass)'}
    print('[C] summary:', json.dumps(summary))
    with open(os.path.join(GH, 'logs', 'v087_phase_c_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)


if __name__ == '__main__':
    main()
