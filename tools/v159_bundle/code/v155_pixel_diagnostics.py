"""V155: pixel-vector derivatives, not derivatives of scalar loss.

This is a diagnostic stage, not a model loader or an optimizer. The workstation
must supply a persistently counted prediction function returning signed 13x13 C.
Every predicted array and finite-difference stencil is retained for independent
reconstruction. No inference of global identifiability or experimental accuracy.
"""
from __future__ import annotations
from typing import Callable, Any
import numpy as np
from v152_gls_core import GlsData, check_theta

STEPS = np.array([0.2, 0.2, 0.5, 0.5], dtype=float)
SVD_RTOLS = (1e-8, 1e-10, 1e-12)
LOW = np.array([30., 350., -500., -500.])
HIGH = np.array([200., 550., 500., 500.])


def contrast(value: Any) -> np.ndarray:
    a = np.asarray(value, dtype=np.float64)
    if a.shape != (13, 13) or not np.isfinite(a).all():
        raise ValueError('PREDICTION_MUST_BE_FINITE_13x13_C_NOT_SCALAR_Q')
    return a.copy()


def gls_score_independent(c: Any, data: GlsData) -> dict:
    """Independent per-frame formula; no optimizer cost is accepted."""
    c = contrast(c)
    q_each = [float(np.sum((c-y)**2/v)) for y, v in zip(data.y, data.variance)]
    q_total = sum(q_each)
    q_model = float(np.sum((c-data.ybar)**2/data.vbar))
    if abs(q_total-q_model-data.constant_K) > max(1e-8, 1e-10*abs(q_total)):
        raise ValueError('DIRECT_AGGREGATED_GLS_MISMATCH')
    return dict(Q_joint=q_total, Q_model=q_model, K=float(data.constant_K), Q_per_frame=q_each)


def projected_information(jw: np.ndarray, nuisance: list[int], rtol: float) -> dict:
    if jw.shape != (169, 4) or not np.isfinite(jw).all():
        raise ValueError('BAD_PIXEL_JACOBIAN')
    d = jw[:, 0]
    dn = float(np.linalg.norm(d))
    n = jw[:, nuisance]
    norms = np.linalg.norm(n, axis=0)
    keep = norms > 0
    normalized = n[:, keep] / norms[keep] if keep.any() else np.empty((169, 0))
    if normalized.shape[1]:
        u, s, _ = np.linalg.svd(normalized, full_matrices=False)
        rank = int(np.sum(s > rtol*s[0]))
        residual = d - u[:, :rank] @ (u[:, :rank].T @ d)
    else:
        s, rank, residual = np.empty(0), 0, d.copy()
    rn = float(np.linalg.norm(residual))
    ratio = rn/dn if dn > 0 else None
    return dict(nuisance_columns=nuisance, rtol=rtol, rank=rank,
                normalized_nuisance_singular_values=s.tolist(),
                D_norm=dn, remaining_D_norm=rn, remaining_D_norm_fraction=ratio,
                remaining_D_squared_norm_fraction=None if ratio is None else ratio**2,
                local_precision_nm=None, confidence_interval=None)


def diagnose(data: GlsData, theta: Any, predict: Callable,
             snapshot: Callable[[dict, np.ndarray], None] | None = None) -> dict:
    """At most 21 unique model predictions: 1 base, 16 stencil, 4 direction checks.

    snapshot is invoked on EACH new successful prediction. A failing persistence
    callback aborts the stage. A persistent counter outside this function enforces
    task/phase/global caps and counts failed model attempts as well.
    """
    theta = check_theta(theta).copy()
    cache: dict[tuple, int] = {}
    records: list[dict] = []

    def get(t: np.ndarray) -> tuple[int, np.ndarray]:
        t = check_theta(t)
        key = tuple(float(v) for v in t)
        if key in cache:
            idx = cache[key]
            return idx, np.asarray(records[idx]['C'], dtype=float)
        c = contrast(predict(t.copy()))
        idx = len(records)
        meta = dict(index=idx, theta=t.tolist())
        if snapshot is not None:
            snapshot(meta, c.copy())
        records.append(dict(**meta, C=c.tolist()))
        cache[key] = idx
        return idx, c

    base_idx, c0 = get(theta)
    stencils = []
    js = []
    for mult in (1.0, 0.5):
        J = np.zeros((169, 4), dtype=float)
        for col, step in enumerate(STEPS*mult):
            e = np.zeros(4); e[col] = step
            if theta[col]-step >= LOW[col] and theta[col]+step <= HIGH[col]:
                points = [theta+e, theta-e]
                coefficients = [1/(2*step), -1/(2*step)]
                mode = 'central_second_order'
            elif theta[col]+2*step <= HIGH[col]:
                points = [theta, theta+e, theta+2*e]
                coefficients = [-3/(2*step), 4/(2*step), -1/(2*step)]
                mode = 'forward_second_order'
            elif theta[col]-2*step >= LOW[col]:
                points = [theta, theta-e, theta-2*e]
                coefficients = [3/(2*step), -4/(2*step), 1/(2*step)]
                mode = 'backward_second_order'
            else:
                raise ValueError('NO_LEGAL_STENCIL_NO_CLIPPING')
            ids, arrays = [], []
            for p in points:
                idx, cp = get(p)
                ids.append(idx); arrays.append(cp)
            derivative = sum(w*cp for w, cp in zip(coefficients, arrays))
            J[:, col] = derivative.ravel()
            stencils.append(dict(multiplier=mult, column=col, step_nm=float(step),
                                 method=mode, indices=ids, coefficients=coefficients))
        js.append(J)
    scale = np.sqrt(data.vbar).ravel()
    ws = [j/scale[:, None] for j in js]
    norms0, norms1 = np.linalg.norm(ws[0], axis=0), np.linalg.norm(ws[1], axis=0)
    diff = np.linalg.norm(ws[1]-ws[0], axis=0)
    denom = np.maximum(norms0, norms1)
    rel = np.divide(diff, denom, out=np.zeros(4), where=denom > 0)
    small = denom < 1e-12  # Numerical flag only; never an optical resolution limit.
    derivative_stable = bool(np.all(rel[~small] <= .02))
    checks = []
    for absolute_direction in (np.array([1., .5, .75, .25]), np.array([.5, 1., .25, .75])):
        # Deterministic feasible one-sided directions; no true parameters involved.
        sign = np.where(theta+STEPS*.5 <= HIGH, 1., -1.)
        delta = sign*STEPS*absolute_direction*.5
        for factor in (1., .5):
            d = delta*factor
            idx, cp = get(theta+d)
            change = (cp-c0).ravel()/scale
            error = change-ws[1]@d
            n = float(np.linalg.norm(change))
            ratio = float(np.linalg.norm(error)/n) if n > 1e-12 else None
            checks.append(dict(delta_nm=d.tolist(), index=idx,
                               relative_linearization_error=ratio,
                               informative=n > 1e-12))
    projections = {}
    for name, nuisance in [('free_hxy', [1, 2, 3]), ('height_fixed', [2, 3]), ('xy_fixed', [1])]:
        projections[name] = [projected_information(ws[1], nuisance, r) for r in SVD_RTOLS]
    rank_stable = all(len({r['rank'] for r in rows}) == 1 for rows in projections.values())
    lin_stable = all(r['relative_linearization_error'] is not None and
                     r['relative_linearization_error'] <= .05 for r in checks)
    boundary = bool(np.any(theta-LOW <= 1e-6) or np.any(HIGH-theta <= 1e-6))
    fine_n = np.linalg.norm(ws[1], axis=0)
    normed = ws[1][:, fine_n > 0]/fine_n[fine_n > 0]
    s_all = np.linalg.svd(normed, compute_uv=False) if normed.shape[1] else np.empty(0)
    status = ('BOUNDARY_LOCAL_DIAGNOSTIC_ONLY' if boundary else
              'NUMERICALLY_CHECKED_LOCAL_ONLY' if derivative_stable and rank_stable and lin_stable and not small.any()
              else 'INDETERMINATE_LOCAL_NUMERICS')
    return dict(theta=theta.tolist(), score=gls_score_independent(c0, data),
                frame_Y=data.y.tolist(), frame_V=data.variance.tolist(),
                raw_J_coarse=js[0].tolist(), raw_J_fine=js[1].tolist(),
                whitened_J_fine=ws[1].tolist(), stencils=stencils,
                predictions=records, base_index=base_idx,
                unique_predictions=len(records), parameter_boundary=boundary,
                derivative_relative_differences=rel.tolist(), tiny_derivative_columns=small.tolist(),
                derivative_stable=derivative_stable, nuisance_rank_stable=rank_stable,
                directional_checks=checks, directional_check_pass=lin_stable,
                all_column_normalized_singular_values=s_all.tolist(), projections=projections,
                status=status, calibrated_uncertainty=False, global_uniqueness_certified=False,
                physical_degeneracy_confirmed=False, reportable_D=None)


def validate_pixel_record(doc: dict) -> dict:
    """Independently reconstruct derivatives from stored pixel arrays and coordinates.

    This validator does not call diagnose or accept a caller-supplied scalar loss
    derivative as a Jacobian. Hash/source validation remains the adapter's duty.
    """
    theta = check_theta(doc['theta'])
    predictions = doc['predictions']
    arrays = [contrast(r['C']) for r in predictions]
    for r in predictions:
        check_theta(r['theta'])
    b = doc['base_index']
    if not np.array_equal(np.asarray(predictions[b]['theta']), theta):
        raise ValueError('BASE_THETA_MISMATCH')
    y, v = np.asarray(doc['frame_Y']), np.asarray(doc['frame_V'])
    if y.shape != v.shape or y.shape not in ((1,13,13), (3,13,13)) or not np.isfinite(y).all() or not np.isfinite(v).all() or np.any(v<=0):
        raise ValueError('BAD_FRAME_DATA')
    precision = 1/v
    vb = 1/precision.sum(axis=0)
    yb = (precision*y).sum(axis=0)*vb
    total = float(np.sum((arrays[b][None, ...]-y)**2/v))
    if not np.isclose(total, doc['score']['Q_joint'], rtol=1e-10, atol=1e-8):
        raise ValueError('Q_IDENTITY_FAILED')
    reconstructed = {1.0: np.zeros((169,4)), .5: np.zeros((169,4))}
    seen = set()
    for s in doc['stencils']:
        mult, col, h = s['multiplier'], s['column'], s['step_nm']
        if (mult, col) in seen or mult not in reconstructed or col not in range(4):
            raise ValueError('DUPLICATE_OR_UNKNOWN_STENCIL')
        seen.add((mult,col))
        if h != STEPS[col]*mult:
            raise ValueError('WRONG_STEP')
        mode = s['method']
        offsets, weights = {'central_second_order':([1,-1],[1,-1]),
                           'forward_second_order':([0,1,2],[-3,4,-1]),
                           'backward_second_order':([0,-1,-2],[3,-4,1])}[mode]
        if len(s['indices']) != len(offsets) or not np.allclose(s['coefficients'], np.array(weights)/(2*h), rtol=0, atol=0):
            raise ValueError('INVALID_STENCIL_WEIGHTS')
        derivative = np.zeros((13,13))
        for idx, offset, w in zip(s['indices'], offsets, weights):
            expected = theta.copy(); expected[col] += offset*h
            if not np.array_equal(np.asarray(predictions[idx]['theta']), expected):
                raise ValueError('STENCIL_COORDINATE_MISMATCH')
            derivative += arrays[idx]*(w/(2*h))
        reconstructed[mult][:,col] = derivative.ravel()
    if len(seen)!=8:
        raise ValueError('MISSING_STENCILS')
    for mult, name in ((1., 'raw_J_coarse'),(.5, 'raw_J_fine')):
        published = np.asarray(doc[name])
        if published.shape != (169,4) or not np.allclose(published, reconstructed[mult], rtol=1e-10, atol=1e-12):
            raise ValueError('PIXEL_DERIVATIVE_IDENTITY_FAILED')
    expected_w = reconstructed[.5]/np.sqrt(vb).ravel()[:,None]
    if np.asarray(doc['whitened_J_fine']).shape != (169,4) or not np.allclose(np.asarray(doc['whitened_J_fine']), expected_w, rtol=1e-10, atol=1e-12):
        raise ValueError('WHITENING_FAILED')
    model_q = float(np.sum((arrays[b]-yb)**2/vb))
    k_value = float(np.sum((y-yb)**2/v))
    per_frame = np.sum((arrays[b][None,...]-y)**2/v,axis=(1,2))
    if not np.isclose(model_q, doc['score']['Q_model'],rtol=1e-10,atol=1e-8) or not np.isclose(k_value,doc['score']['K'],rtol=1e-10,atol=1e-8) or not np.allclose(per_frame,doc['score']['Q_per_frame'],rtol=1e-10,atol=1e-8):
        raise ValueError('Q_COMPONENTS_MISMATCH')
    for name,cols in [('free_hxy',[1,2,3]),('height_fixed',[2,3]),('xy_fixed',[1])]:
        n=expected_w[:,cols]; norms=np.linalg.norm(n,axis=0); keep=norms>0
        if keep.any():
            u,ss,_=np.linalg.svd(n[:,keep]/norms[keep],full_matrices=False)
        else:
            u,ss=np.empty((169,0)),np.empty(0)
        dn=float(np.linalg.norm(expected_w[:,0]))
        rows=doc['projections'][name]
        if len(rows)!=3:raise ValueError('MISSING_RANK_CHECKS')
        for item,rtol in zip(rows,SVD_RTOLS):
            rank=int(np.sum(ss>rtol*ss[0])) if ss.size else 0
            remaining=expected_w[:,0]-u[:,:rank]@(u[:,:rank].T@expected_w[:,0])
            rn=float(np.linalg.norm(remaining)); ratio=rn/dn if dn>0 else None
            if item['rtol']!=rtol or item['rank']!=rank or not np.isclose(item['remaining_D_norm'],rn,rtol=1e-8,atol=1e-12):
                raise ValueError('PROJECTION_MISMATCH')
            if ratio is None:
                if item['remaining_D_norm_fraction'] is not None:raise ValueError('ZERO_D_COLUMN_UNDEFINED_RATIO')
            elif not np.isclose(item['remaining_D_norm_fraction'],ratio,rtol=1e-8,atol=1e-12):
                raise ValueError('PROJECTION_RATIO_MISMATCH')
    if doc.get('reportable_D') is not None or doc.get('physical_degeneracy_confirmed') is not False:
        raise ValueError('UNQUALIFIED_SCIENTIFIC_CLAIM')
    return dict(status='PIXEL_AND_Q_IDENTITIES_PASS_NOT_PHYSICAL_VALIDATION',
                n_predictions=len(predictions), Q_joint=total)


def select_complete_best(records: list[dict]) -> dict:
    """Select one already-rescored complete record. No borrowing D from summaries."""
    if not records:raise ValueError('NO_FINITE_WITNESSES')
    for r in records:
        t=check_theta(r['theta'])
        if r['candidate_D']!=float(t[0]):raise ValueError('D_THETA_MISMATCH')
        if not np.isfinite(r['Q_joint']) or r['Q_joint']<0:raise ValueError('BAD_Q')
        if not r.get('source_record_id'):raise ValueError('MISSING_SOURCE_ID')
    return min(records,key=lambda r:r['Q_joint'])
