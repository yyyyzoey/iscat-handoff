# -*- coding: utf-8 -*-
"""v089 Phase C+D+E: ONE restricted cached-video session.

C: window moments, mask qualification, same-operator reproduction of the 6
   v088 maps (rF < 1e-10 gate).
D: four pre-registered estimators x 3 frequencies x 2 windows:
   D0 direct local denominator (baseline, = C stage)
   D1 direct common denominator (full-record Imean_full)
   D2 joint 7-column LS (intercept + 3 cos/sin pairs), C_fit = A_f/Imean_full
   D3 D2 + pre-registered normalized linear trend (8 cols)
E: complex component closure X_obs = X_model + X_res per window/model/freq.
All outputs SECONDARY_WITHIN_RECORD_DIAGNOSTIC; no physics claims."""
import os, sys, csv, json, hashlib
import numpy as np
import h5py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v083_common import ROOT
from v089_estimators import design_matrix, component_decomposition, EstimatorError

GH = os.path.join(ROOT, 'github_handoff')
TAB = os.path.join(GH, 'tables')
NUM = os.path.join(GH, 'numeric')
AN = os.path.join(GH, 'analysis')
P = os.path.join(NUM, 'fft400_corrected_small_roi.mat')
V088 = os.path.join(NUM, 'v088_cached_segment_maps.npz')
WINDOWS = [('W1', 0, 1000), ('W2', 1000, 2001)]
FREQS = [200.0, 400.0, 420.0]
FS = 5000.0
N = 2001


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def g17(x):
    return '%.17g' % x


def main():
    # ---- ONE read of the cached video ----
    sha = sha256_file(P)
    with h5py.File(P, 'r') as f:
        frames = np.asarray(f['roiFrames'][:, 0, :, :], dtype=np.float64)
        maskst = np.asarray(f['validMask']).astype(bool)
        meanFloor = float(np.asarray(f['meanFloor']).flatten()[0])
    Im_full = frames.mean(axis=0)

    # ---- C: window moments ----
    mom_rows = []
    window_masks = {}
    for wname, lo, hi in WINDOWS:
        Iw = frames[lo:hi, :, :]
        Imw = Iw.mean(axis=0)
        jg = np.arange(lo, hi, dtype=np.float64)
        m = np.isfinite(Imw) & (Imw > meanFloor)
        window_masks[wname] = m
        mom_rows.append({'window': wname, 'j_range': '%d..%d' % (lo, hi - 1), 'N_w': hi - lo,
                         'mean_Imean_w': g17(float(Imw[maskst].mean())),
                         'median_Imean_w': g17(float(np.median(Imw[maskst]))),
                         'pixels_below_fullfloor': int((np.isfinite(Imw) & (Imw <= meanFloor)).sum()),
                         'pixels_nonfinite': int((~np.isfinite(Imw)).sum()),
                         'window_mask_valid': int(m.sum()),
                         'note': 'per-window Imean uses the window samples; floor = sourced full-frame threshold'})
    fixed_intersection = maskst.copy()
    for wname in window_masks:
        fixed_intersection &= window_masks[wname]
    mask_changed = (int(fixed_intersection.sum()) != int(maskst.sum()))
    mom_rows.append({'window': 'FIXED_INTERSECTION', 'j_range': 'both windows', 'N_w': '-',
                     'mean_Imean_w': '-', 'median_Imean_w': '-',
                     'pixels_below_fullfloor': '-', 'pixels_nonfinite': '-',
                     'window_mask_valid': int(fixed_intersection.sum()),
                     'note': 'v088 full-record mask=%d; changed=%s' % (int(maskst.sum()), mask_changed)})
    with open(os.path.join(AN, 'v089_window_moments2.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(mom_rows[0].keys()), lineterminator='\n')
        w.writeheader(); w.writerows(mom_rows)
    M = fixed_intersection

    # ---- C: same-operator reproduction of the 6 v088 maps ----
    recheck = []
    with np.load(V088) as z:
        for wname, lo, hi in WINDOWS:
            Nw = hi - lo
            Iw = frames[lo:hi, :, :]
            Imw = Iw.mean(axis=0)
            jg = np.arange(lo, hi, dtype=np.float64)
            for f in FREQS:
                e = np.exp(-2j * np.pi * f * jg / FS)
                X = np.tensordot(e, Iw - Imw[None, :, :], axes=(0, 0))
                C = 2.0 * X / (Nw * Imw)
                key = 'C_%s_%dHz' % (wname, int(f))
                Cold = z[key]
                mm = M & np.isfinite(Cold)
                rF = float(np.linalg.norm((C - Cold)[mm]) / max(np.linalg.norm(Cold[mm]), 1e-300))
                ok = rF < 1e-10 or (float(np.linalg.norm(Cold[mm])) <= 1e-12 and rF < 1e-12)
                recheck.append({'record_key': '%s|%d' % (wname, int(f)), 'window': wname, 'freq_Hz': '%.1f' % f, 'map_key': key,
                                'relFrobenius_recompute_vs_v088': g17(rF),
                                'gate': 'rF < 1e-10 (abs 1e-12 if norm<=1e-12)',
                                'status': 'SAME_OPERATOR_VERIFIED' if ok else 'REPRODUCTION_FAILED'})
    recheck_ok = all(r['status'] == 'SAME_OPERATOR_VERIFIED' for r in recheck)
    with open(os.path.join(AN, 'v089_v088_same_operator_recheck6.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(recheck[0].keys()), lineterminator='\n')
        w.writeheader(); w.writerows(recheck)
    if not recheck_ok:
        print('[C] REPRODUCTION_FAILED - estimator comparison halted; metadata fixes continue')
        with open(os.path.join(GH, 'logs', 'v089_reference_run.json'), 'w', encoding='utf-8') as f:
            json.dump({'phase_C': 'REPRODUCTION_FAILED', 'rows': recheck}, f, indent=2)
        sys.exit(2)

    # ---- D: four estimators ----
    # D0/D1 from the X numerators (same X for both; denominator differs)
    Xw = {}
    Imw_d = {}
    for wname, lo, hi in WINDOWS:
        Nw = hi - lo
        Iw = frames[lo:hi, :, :]
        Imw = Iw.mean(axis=0)
        jg = np.arange(lo, hi, dtype=np.float64)
        Imw_d[wname] = Imw
        for f in FREQS:
            e = np.exp(-2j * np.pi * f * jg / FS)
            Xw[(wname, f)] = np.tensordot(e, Iw - Imw[None, :, :], axes=(0, 0))
    estimators = {}
    estimators['D0_direct_local'] = {(w, f): 2.0 * Xw[(w, f)] / (Nw_of(w) * Imw_d[w])
                                     for (w, f) in Xw for Nw_of in [lambda w: dict(W1=1000, W2=1001)[w]]}
    estimators['D1_direct_common'] = {(w, f): 2.0 * Xw[(w, f)] / (Nw_of(w) * Im_full)
                                      for (w, f) in Xw for Nw_of in [lambda w: dict(W1=1000, W2=1001)[w]]}
    # D2/D3 joint LS per window (multi-RHS over all pixels)
    coef_maps = {}
    design_meta = []
    for wname, lo, hi in WINDOWS:
        jg = np.arange(lo, hi, dtype=np.float64)
        S = frames[lo:hi, :, :].reshape(hi - lo, 41 * 41)
        for model, trend in (('D2_joint7', False), ('D3_joint8_trend', True)):
            B, labels = design_matrix(jg, FREQS, trend)
            rank = int(np.linalg.matrix_rank(B))
            cond = float(np.linalg.cond(B))
            if rank != B.shape[1] or not (cond < 1e6):
                raise EstimatorError('%s: rank %d/%d cond %.3g' % (model, rank, B.shape[1], cond))
            beta, _, _, _ = np.linalg.lstsq(B, S, rcond=None)
            resid = S - B @ beta
            coef_maps[(wname, model)] = (beta, labels, resid, B)
            design_meta.append({'record_key': '%s|%s' % (wname, model), 'window': wname, 'model': model, 'n_columns': B.shape[1],
                                'rank': rank, 'condition': g17(cond),
                                'columns': '|'.join(labels), 'gate': 'rank=cols, cond<1e6',
                                'status': 'PASS'})
            # C_fit_common = A_f / Imean_full (NO 2/N on fit coefficients)
            for k, f in enumerate(FREQS):
                a = beta[1 + 2 * k, :].reshape(41, 41)
                b = beta[2 + 2 * k, :].reshape(41, 41)
                estimators['%s|%s' % (model, wname)] = (a - 1j * b) / Im_full
    with open(os.path.join(AN, 'v089_design_rank_condition4.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(design_meta[0].keys()), lineterminator='\n')
        w.writeheader(); w.writerows(design_meta)

    # ---- D pairwise comparison: 4 estimators x 3 freqs = 12 rows ----
    comp = []
    def two_window_stats(C1, C2):
        m = M & np.isfinite(C1) & np.isfinite(C2)
        v1, v2 = C1[m], C2[m]
        d = float(np.linalg.norm(v1 - v2))
        rel = d / max(float(np.linalg.norm(v2)), 1e-300)
        n1 = float(np.linalg.norm(v1)); n2 = float(np.linalg.norm(v2))
        if n1 == 0 or n2 == 0:
            rho = None
        else:
            rho = float(abs(np.vdot(v1, v2)) / (n1 * n2))
        return {'n_pixels': int(m.sum()),
                'L2_W1': g17(n1), 'L2_W2': g17(n2),
                'median_absC_W1': g17(float(np.median(np.abs(v1)))),
                'median_absC_W2': g17(float(np.median(np.abs(v2)))),
                'complex_diff_L2': g17(d), 'rel_to_W2': g17(rel),
                'normalized_inner_product': g17(rho) if rho is not None else 'UNDEFINED_ZERO_NORM',
                'window_Imean_mean_change': g17(float(np.mean(Imw_d['W1'][m]) - np.mean(Imw_d['W2'][m])))}
    for f in FREQS:
        for est in ('D0_direct_local', 'D1_direct_common', 'D2_joint7|W1', 'D3_joint8_trend|W1'):
            if est == 'D0_direct_local':
                C1 = estimators[est][('W1', f)]; C2 = estimators[est][('W2', f)]
            elif est == 'D1_direct_common':
                C1 = estimators[est][('W1', f)]; C2 = estimators[est][('W2', f)]
            else:
                model, w = est.split('|')
                C1 = estimators[est]; C2 = estimators['%s|%s' % (model, 'W2')]
            st = two_window_stats(C1, C2)
            comp.append({'record_key': '%s|%d' % (est, int(f)), 'estimator': est, 'freq_Hz': '%.1f' % f, **st,
                         'scope': 'SECONDARY_WITHIN_RECORD_DIAGNOSTIC'})
    with open(os.path.join(AN, 'v089_estimator_comparison12.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(comp[0].keys()), lineterminator='\n')
        w.writeheader(); w.writerows(comp)

    # ---- E: component closure (2 windows x 2 models x 3 freqs = 12 rows) ----
    clo_rows = []
    for wname, lo, hi in WINDOWS:
        jg = np.arange(lo, hi, dtype=np.float64)
        Iw = frames[lo:hi, :, :]
        for model, trend in (('D2_joint7', False), ('D3_joint8_trend', True)):
            beta, labels, resid, B = coef_maps[(wname, model)]
            for p in range(41 * 41):
                pass  # vectorized below instead
            # vectorized closure over all pixels for this window/model
            S = Iw.reshape(hi - lo, 41 * 41)
            e = np.exp(-2j * np.pi * np.asarray(FREQS)[:, None] * jg[None, :] / FS)
            Bc = B - B.mean(axis=0, keepdims=True)
            K = np.tensordot(e, Bc, axes=(1, 0))          # (nf, n_cols)
            X_model = np.tensordot(K, beta, axes=(1, 0))  # (nf, 1681)
            rc = resid - resid.mean(axis=0, keepdims=True)
            X_res = np.tensordot(e, rc, axes=(1, 0))
            X_obs = np.tensordot(e, S - S.mean(axis=0, keepdims=True), axes=(1, 0))
            for k, f in enumerate(FREQS):
                closure = X_obs[k] - X_model[k] - X_res[k]
                normX = np.abs(X_obs[k])
                near = normX <= 1e-12
                ok_px = np.where(near, np.abs(closure) < 1e-12,
                                 np.abs(closure) / np.maximum(normX, 1e-300) < 1e-10)
                clo_rows.append({'record_key': '%s|%s|%d' % (wname, model, int(f)), 'window': wname, 'model': model, 'freq_Hz': '%.1f' % f,
                                 'n_pixels': int(M.reshape(-1).sum()),
                                 'n_closure_ok_on_mask': int(ok_px[M.reshape(-1)].sum()),
                                 'max_abs_closure_on_mask': g17(float(np.max(np.abs(closure)[M.reshape(-1)]))),
                                 'closure_mode': 'RELATIVE (near-zero pixels NEAR_ZERO_ABSOLUTE_ONLY)',
                                 'status': 'PASS' if bool(ok_px[M.reshape(-1)].all()) else 'FAIL'})
    with open(os.path.join(AN, 'v089_component_closure12.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(clo_rows[0].keys()), lineterminator='\n')
        w.writeheader(); w.writerows(clo_rows)

    # ---- estimator comparison arrays ----
    arrs = {}
    for est in ('D0_direct_local', 'D1_direct_common'):
        for (w, f) in Xw:
            arrs['%s|%s|%dHz' % (est, w, int(f))] = estimators[est][(w, f)]
    for key, Cm in estimators.items():
        if '|' in key and key.split('|')[0] in ('D2_joint7', 'D3_joint8_trend'):
            model, w = key.split('|')
            for k, f in enumerate(FREQS):
                pass
    for (w, model) in coef_maps:
        beta, labels, resid, B = coef_maps[(w, model)]
        for k, f in enumerate(FREQS):
            a = beta[1 + 2 * k, :].reshape(41, 41)
            b = beta[2 + 2 * k, :].reshape(41, 41)
            arrs['%s|%s|%dHz' % (model, w, int(f))] = (a - 1j * b) / Im_full
    np.savez_compressed(os.path.join(AN, 'v089_estimator_comparison_arrays.npz'),
                        source_sha256=sha, common_mask=M, Imean_full=Im_full,
                        Imean_W1=Imw_d['W1'], Imean_W2=Imw_d['W2'], **arrs)

    # ---- reference run json ----
    ref = {'source_sha256': sha, 'windows': WINDOWS, 'freqs': FREQS,
           'recheck_ok': recheck_ok, 'mask_changed_vs_v088': bool(mask_changed),
           'n_common_mask_pixels': int(M.sum()),
           'design_matrices': design_meta,
           'closure_rows': len(clo_rows),
           'estimator_rows': len(comp),
           'budget': {'cached_video_sessions': 1, 'design_matrix_entries': 4,
                      'new_simulations': 0, 'new_BEM': 0, 'new_renders': 0}}
    with open(os.path.join(AN, 'v089_reference_run.json'), 'w', encoding='utf-8') as f:
        json.dump(ref, f, indent=2)
    print('[CDE] summary:', json.dumps({'recheck_ok': recheck_ok,
                                        'closure_all_pass': all(r['status'] == 'PASS' for r in clo_rows),
                                        'estimator_rows': len(comp)}))


def Nw_of(w):
    return dict(W1=1000, W2=1001)[w]


if __name__ == '__main__':
    main()
