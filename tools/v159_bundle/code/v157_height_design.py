"""V157: fixed-variance local design and deterministic compensation paths.

No optical model loader, optimizer, noise generator or truth reader is present.
Input Jacobians must already have passed source and pixel-identity verification.
The quantities below are local quadratic design coefficients, NOT confidence
intervals, calibrated Fisher information, or experimental diameter precision.
"""
from __future__ import annotations
import math
from typing import Any, Callable
import numpy as np
from v152_gls_core import GlsData, check_theta

SIGMAS_NM = (1., 2., 5., 10., 20., 50., 100.)
RTOLS = (1e-8, 1e-10, 1e-12)
DELTAS_NM = (-5., -2., -1., -.5, .5, 1., 2., 5.)


def _matrix(j: Any) -> np.ndarray:
    a = np.asarray(j, dtype=np.float64)
    if a.shape != (169, 4) or not np.isfinite(a).all():
        raise ValueError('EXPECTED_FINITE_WHITENED_169_BY_4_JACOBIAN')
    return a


def _penalty(sigmas: tuple[float, float, float]) -> tuple[np.ndarray, list[int]]:
    s = np.asarray(sigmas, dtype=float)
    if s.shape != (3,) or np.isnan(s).any() or np.any(s < 0):
        raise ValueError('SIGMAS_MUST_BE_NONNEGATIVE_OR_POSITIVE_INFINITY')
    # sigma=0 means an exactly fixed increment, not a huge penalty approximation.
    active = np.flatnonzero(s > 0).tolist()
    penalty = np.zeros((3, len(active)))
    for k, col in enumerate(active):
        if np.isfinite(s[col]):
            penalty[col, k] = 1. / s[col]
    return penalty, active


def local_design(jw: Any, *, sigma_h: float = math.inf,
                 sigma_xy: float = math.inf, rtol: float = 1e-10) -> dict:
    """min_b ||j_D + J_n b||² + ||L b||², evaluated for a 1-nm D increment.

    b contains nuisance increments per nm of D. Augmented column equilibration
    is used before SVD. The original physical coordinates are restored before
    evaluating the residual; no ridge/damping not specified by sigmas is added.
    """
    j = _matrix(jw)
    if not np.isfinite(rtol) or not 0 < rtol < 1:
        raise ValueError('INVALID_SVD_RTOL')
    penalty, active = _penalty((sigma_h, sigma_xy, sigma_xy))
    b = np.zeros(3)
    d = j[:, 0]
    target = np.r_[-d, np.zeros(3)]
    if active:
        aug = np.vstack((j[:, np.array(active)+1], penalty))
        scales = np.linalg.norm(aug, axis=0)
        keep = scales > 0
        if keep.any():
            normalized = aug[:, keep] / scales[keep]
            u, singular, vt = np.linalg.svd(normalized, full_matrices=False)
            rank = int(np.sum(singular > rtol*singular[0]))
            coeff = vt[:rank].T @ ((u[:, :rank].T @ target)/singular[:rank])
            b[np.asarray(active)[keep]] = coeff/scales[keep]
        else:
            singular, rank = np.empty(0), 0
    else:
        singular, rank = np.empty(0), 0
    residual = d + j[:, 1:] @ b
    aux = penalty @ b[active] if active else np.zeros(3)
    image_i = float(residual @ residual)
    aux_i = float(aux @ aux)
    total_i = image_i + aux_i
    denominator = float(d @ d)
    return dict(
        sigma_h_nm=None if math.isinf(sigma_h) else float(sigma_h),
        sigma_xy_nm=None if math.isinf(sigma_xy) else float(sigma_xy),
        no_height_measurement=math.isinf(sigma_h),
        no_xy_measurement=math.isinf(sigma_xy),
        exact_height=sigma_h == 0, exact_xy=sigma_xy == 0,
        rtol=rtol, nuisance_rank=rank,
        normalized_augmented_singular_values=singular.tolist(),
        compensation_nm_per_nm=b.tolist(), image_coefficient_nm_minus2=image_i,
        auxiliary_coefficient_nm_minus2=aux_i,
        total_coefficient_nm_minus2=total_i,
        D_squared_norm=denominator,
        fraction_of_all_nuisance_fixed=None if denominator == 0 else total_i/denominator,
        scope='LOCAL_QUADRATIC_DESIGN_NOT_CALIBRATED_FISHER_OR_CI',
        reportable_D=None)


def design_sweep(jw: Any) -> dict:
    j = _matrix(jw)
    cases = [('free', math.inf, math.inf), ('exact_height', 0., math.inf),
             ('exact_xy', math.inf, 0.)]
    cases += [(f'height_sigma_{s:g}nm', s, math.inf) for s in SIGMAS_NM]
    cases += [(f'xy_sigma_{s:g}nm', math.inf, s) for s in SIGMAS_NM]
    return {name: [local_design(j, sigma_h=h, sigma_xy=xy, rtol=r) for r in RTOLS]
            for name, h, xy in cases}


def height_formula_crosscheck(jw: Any, sigma_h: float, rtol: float = 1e-10) -> dict:
    """Independent closed-form check after removing x/y. Not used as solver."""
    j = _matrix(jw)
    if np.isnan(sigma_h) or sigma_h < 0:
        raise ValueError('BAD_SIGMA')
    xy = j[:, 2:]
    scales = np.linalg.norm(xy, axis=0)
    keep = scales > 0
    if keep.any():
        u, s, _ = np.linalg.svd(xy[:, keep]/scales[keep], full_matrices=False)
        rank = int(np.sum(s > rtol*s[0]))
        u = u[:, :rank]
    else:
        u = np.empty((169, 0))
    a = j[:, 0] - u @ (u.T @ j[:, 0])
    h = j[:, 1] - u @ (u.T @ j[:, 1])
    aa, hh, ah = float(a@a), float(h@h), float(a@h)
    if sigma_h == 0 or hh == 0:
        value = aa
    else:
        precision = 0. if math.isinf(sigma_h) else 1./sigma_h**2
        value = aa - ah**2/(hh+precision)
    return dict(coefficient_by_subtraction=value, xy_projected_D_norm2=aa,
                xy_projected_h_norm2=hh, xy_projected_D_h_dot=ah,
                note='SUBTRACTIVE_FORMULA_CROSSCHECK_ONLY_MAY_LOSE_RELATIVE_ACCURACY_NEAR_ZERO')


def plan_paths(theta: Any, jw: Any) -> list[dict]:
    """Exactly the predeclared 3x8 proposed points; illegal points are skipped.

    These are linear-compensation paths, not optimized fixed-D profiles.
    A 10-nm independent height uncertainty is hypothetical, not measured.
    """
    t = check_theta(theta)
    out = []
    for name, sigma_h in [('free_hxy', math.inf), ('exact_height', 0.), ('height_sigma10', 10.)]:
        design = local_design(jw, sigma_h=sigma_h)
        direction = np.r_[1., design['compensation_nm_per_nm']]
        for delta in DELTAS_NM:
            proposal = t + delta*direction
            row = dict(path=name, delta_D_nm=delta, theta=proposal.tolist(),
                       anchor_theta=t.tolist(), design=design,
                       direction_nm_per_nm=direction.tolist(),
                       method='LINEAR_COMPENSATION_PATH_NOT_PROFILE_MINIMUM')
            try:
                check_theta(proposal)
                row['state'] = 'PLANNED'
            except ValueError as exc:
                row.update(state='SKIPPED_OUT_OF_DOMAIN', reason=str(exc))
            out.append(row)
    return out


def evaluate_path(row: dict, *, c0: Any, data: GlsData, jw: Any,
                  predict: Callable, persist: Callable) -> dict:
    """One prediction at a valid preplanned point; caller must count persistently.

    persist failure propagates. Skipped points call neither model nor predictor.
    Model return must be a finite 13x13 array (not an Observation or scalar).
    """
    if row.get('state') != 'PLANNED':
        return dict(row)
    t = check_theta(row['theta'])
    base = check_theta(row['anchor_theta'])
    c0 = data.prediction(c0)
    j = _matrix(jw)
    c = data.prediction(predict(t))
    delta = t-base
    actual = ((c-c0)/np.sqrt(data.vbar)).ravel()
    linear = j @ delta
    dist2 = float(actual@actual)
    predicted2 = float(linear@linear)
    base_residual = ((c0-data.ybar)/np.sqrt(data.vbar)).ravel()
    cross_term = float(2*base_residual@actual)
    old_score, new_score = data.score(c0), data.score(c)
    dq = new_score['Q_joint']-old_score['Q_joint']
    if abs(dq - cross_term - dist2) > max(1e-8, 1e-10*abs(new_score['Q_joint'])):
        raise ValueError('NOISY_Q_CHANGE_IDENTITY_FAILED')
    cfg = row['design']
    aux2 = 0.
    if not cfg['no_height_measurement'] and not cfg['exact_height']:
        aux2 += float((delta[1]/cfg['sigma_h_nm'])**2)
    # This stage never evaluates an x/y penalty path, but support it explicitly.
    if not cfg['no_xy_measurement'] and not cfg['exact_xy']:
        aux2 += float(np.sum((delta[2:]/cfg['sigma_xy_nm'])**2))
    error = float(np.linalg.norm(actual-linear))
    result = dict(row, state='EVALUATED', C=c.tolist(),
                  image_distance_squared=dist2, predicted_image_distance_squared=predicted2,
                  hypothetical_auxiliary_distance_squared=aux2,
                  total_design_distance_squared=dist2+aux2,
                  relative_linearization_error=None if np.linalg.norm(actual)<=1e-12 else error/np.linalg.norm(actual),
                  observed_Q_change=dq, observed_Q_cross_term=cross_term,
                  score_at_proposal=new_score, reportable_D=None)
    persist(result)
    return result
