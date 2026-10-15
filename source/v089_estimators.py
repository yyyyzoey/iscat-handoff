# -*- coding: utf-8 -*-
"""v089 shared within-record estimator functions (single source of truth for
the fixtures and the real cached-video session)."""
import numpy as np


class EstimatorError(Exception):
    pass


def demodulate(series, f, j_global):
    """Exact continuous demodulation at frequency f with GLOBAL time origin.
    Returns (Imean, X_f, C_f) with C_f = 2 X_f / (Nw * Imean)."""
    s = np.asarray(series, dtype=np.float64)
    Nw = s.size
    if Nw == 0:
        raise EstimatorError('empty window')
    if not np.isfinite(s).all():
        raise EstimatorError('non-finite samples in series (NaN/Inf rejected)')
    Im = float(s.mean())
    e = np.exp(-2j * np.pi * f * np.asarray(j_global, dtype=np.float64) / 5000.0)
    X = complex(np.sum((s - Im) * e))
    if Im == 0:
        raise EstimatorError('zero Imean - normalized contrast undefined')
    return Im, X, 2.0 * X / (Nw * Im)


def design_matrix(j_global, freqs, trend=False):
    """Intercept + cos/sin pairs (+ normalized linear trend). Columns in the
    fixed order: [intercept, (cos_f, sin_f) per freq, (trend)]."""
    j = np.asarray(j_global, dtype=np.float64)
    cols = [np.ones_like(j)]
    labels = ['intercept']
    for f in freqs:
        cols.append(np.cos(2 * np.pi * f * j / 5000.0)); labels.append('cos%d' % int(f))
        cols.append(np.sin(2 * np.pi * f * j / 5000.0)); labels.append('sin%d' % int(f))
    if trend:
        g = (j - j.mean()) / max((j.max() - j.min()) / 2.0, 1e-300)
        cols.append(g); labels.append('trend')
    return np.column_stack(cols), labels


def fit_joint(series, j_global, freqs, trend=False):
    """Joint LS fit (QR-stable lstsq). Returns coef, rank, cond, A_f per freq
    (A_f = a_f - i b_f, NO 2/N factor), resid, labels."""
    s = np.asarray(series, dtype=np.float64)
    if not np.isfinite(s).all():
        raise EstimatorError('non-finite samples in series (NaN/Inf rejected)')
    B, labels = design_matrix(j_global, freqs, trend)
    rank = int(np.linalg.matrix_rank(B))
    cond = float(np.linalg.cond(B))
    if rank != B.shape[1]:
        raise EstimatorError('design matrix rank %d != %d columns' % (rank, B.shape[1]))
    if not (cond < 1e6):
        raise EstimatorError('design condition %.3g >= 1e6' % cond)
    coef, _, _, _ = np.linalg.lstsq(B, s, rcond=None)
    resid = s - B @ coef
    A = {}
    for k, f in enumerate(freqs):
        a = coef[1 + 2 * k]; b = coef[2 + 2 * k]
        A[f] = complex(a, -b)
    return {'coef': coef, 'rank': rank, 'cond': cond, 'A_f': A,
            'resid': resid, 'labels': labels, 'B': B}


def component_decomposition(series, j_global, freqs, fit, trend=False):
    """Per-column DFT contributions with the SAME mean-subtraction operator as
    the observation: K_l = sum_j e_f[j] * (B[j,l] - mean_j B[:,l]);
    X_model(f) = sum_l K_{f,l} * beta_l; X_res(f) = sum_j e_f[j]*(r_j - mean r).
    Closure check: X_observed(f) == X_model(f) + X_res(f) per frequency."""
    s = np.asarray(series, dtype=np.float64)
    B = fit['B']; beta = fit['coef']; labels = fit['labels']
    e = np.exp(-2j * np.pi * np.asarray(freqs, dtype=np.float64)[:, None] *
               np.asarray(j_global, dtype=np.float64)[None, :] / 5000.0)
    Bc = B - B.mean(axis=0, keepdims=True)
    K = e @ Bc                                   # (n_freqs, n_cols) complex
    out = {}
    for k, f in enumerate(freqs):
        X_model = complex(np.sum(K[k, :] * beta))
        rc = fit['resid'] - fit['resid'].mean()
        X_res = complex(np.sum(e[k, :] * rc))
        e_f = np.exp(-2j * np.pi * f * np.asarray(j_global, dtype=np.float64) / 5000.0)
        X_obs = complex(np.sum((s - s.mean()) * e_f))
        closure = X_obs - X_model - X_res
        normX = abs(X_obs)
        if normX <= 1e-12:
            ok = abs(closure) < 1e-12
            mode = 'NEAR_ZERO_ABSOLUTE_ONLY'
        else:
            ok = abs(closure) / normX < 1e-10
            mode = 'RELATIVE'
        out[f] = {'X_observed': X_obs, 'X_model': X_model, 'X_res': X_res,
                  'closure': closure, 'closure_ok': ok, 'closure_mode': mode,
                  'K_per_column': {lab: complex(K[k, i]) for i, lab in enumerate(labels)},
                  'beta_per_column': {lab: float(beta[i]) for i, lab in enumerate(labels)}}
    return out


def norm_inner_prod(C1, C2, mask):
    v1 = np.asarray(C1)[mask]; v2 = np.asarray(C2)[mask]
    n1 = np.linalg.norm(v1); n2 = np.linalg.norm(v2)
    if n1 == 0 or n2 == 0:
        return None  # UNDEFINED_ZERO_NORM
    return float(abs(np.vdot(v1, v2)) / (n1 * n2))
