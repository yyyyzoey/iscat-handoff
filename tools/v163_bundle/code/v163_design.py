"""Complete the frozen 17-design comparison from SAVED pixel arrays only.
No model loader, truth reader, optimizer or optical forward is called here.
"""
from __future__ import annotations
import math
import numpy as np
from v155_pixel_diagnostics import validate_pixel_record
from v157_height_design import design_sweep, height_formula_crosscheck, local_design
from v163_semantics import validate_sweep


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def audit_diagnostic(d: dict) -> dict:
    base = validate_pixel_record(d)
    v = np.asarray(d['frame_V'], float)
    vb = 1.0 / np.sum(1.0 / v, axis=0)
    scale = np.sqrt(vb).ravel()
    co = np.asarray(d['raw_J_coarse'], float) / scale[:, None]
    fi = np.asarray(d['raw_J_fine'], float) / scale[:, None]
    den = np.maximum(np.linalg.norm(co, axis=0), np.linalg.norm(fi, axis=0))
    rel = np.divide(np.linalg.norm(fi-co, axis=0), den,
                    out=np.zeros(4), where=den > 0)
    tiny = den < 1e-12
    stable = bool(np.all(rel[~tiny] <= .02))
    _require(stable == d['derivative_stable'], 'DERIVATIVE_FLAG_MISMATCH')
    records = d['predictions']
    c0 = np.asarray(records[d['base_index']]['C'])
    theta = np.asarray(d['theta'], float)
    errors = []
    for x in d['directional_checks']:
        rec = records[x['index']]
        delta = np.asarray(x['delta_nm'], float)
        _require(np.array_equal(np.asarray(rec['theta']), theta+delta), 'DIRECTION_COORDINATE_MISMATCH')
        change = (np.asarray(rec['C'])-c0).ravel()/scale
        norm = np.linalg.norm(change)
        error = float(np.linalg.norm(change-fi@delta)/norm) if norm > 1e-12 else None
        if error is None:
            _require(x['relative_linearization_error'] is None, 'DIRECTION_FLAG_MISMATCH')
        else:
            _require(np.isclose(error, x['relative_linearization_error'],rtol=1e-9,atol=1e-12), 'DIRECTION_ERROR_MISMATCH')
        errors.append(error)
    linear = bool(errors and all(x is not None and x <= .05 for x in errors))
    _require(linear == d['directional_check_pass'], 'LINEARIZATION_FLAG_MISMATCH')
    low=np.array([30,350,-500,-500.]); high=np.array([200,550,500,500.])
    boundary=bool(np.any(theta-low <= 1e-6) or np.any(high-theta <= 1e-6))
    _require(boundary == d['parameter_boundary'], 'BOUNDARY_FLAG_MISMATCH')
    return dict(**base, coarse_whitened=co, fine_whitened=fi,
                derivative_stable=stable, directional_stable=linear,
                step_errors=rel.tolist(), directional_errors=errors,
                parameter_boundary=boundary, tiny_columns=tiny.tolist())


def complete_design(diagnostic: dict) -> dict:
    a = audit_diagnostic(diagnostic)
    co, fi = a['coarse_whitened'], a['fine_whitened']
    sweeps = {'coarse': design_sweep(co), 'fine': design_sweep(fi)}
    _require(all(len(s)==17 for s in sweeps.values()), 'EXACTLY_17_DESIGNS_REQUIRED')
    independent_checks={scale:validate_sweep(j,sweeps[scale]) for scale,j in [('coarse',co),('fine',fi)]}
    checks={}; any_unstable=False
    for name,rows in sweeps['fine'].items():
        allrows = rows+sweeps['coarse'][name]
        vals=np.array([r['total_coefficient_nm_minus2'] for r in allrows])
        bases=np.array([r['D_squared_norm'] for r in allrows])
        _require(np.all(np.isfinite(vals)) and np.all(vals>=0), 'INVALID_COEFFICIENT')
        _require(np.all(vals <= bases + 1e-9*np.maximum(bases,1e-300)), 'ABOVE_ALL_FIXED_BASELINE')
        resolved=bool(np.all(vals > 1e-20*np.maximum(bases,1e-300)))
        relative_range=float((vals.max()-vals.min())/vals.max()) if vals.max()>0 else None
        rank_stable=len({r['nuisance_rank'] for r in allrows})==1
        stable=resolved and rank_stable and relative_range is not None and relative_range <= .05
        any_unstable |= not stable
        checks[name]=dict(resolved=resolved, rank_stable=rank_stable,
                         coarse_fine_rtol_relative_range=relative_range,numerically_stable=stable)
    crosschecks=[]
    for scale,j in [('coarse',co),('fine',fi)]:
        base=float(j[:,0]@j[:,0]); tol=1e-9*max(base,1e-300)
        for rtol in (1e-8,1e-10,1e-12):
            values=[]
            for sigma in (0.,1.,2.,5.,10.,20.,50.,100.,math.inf):
                direct=local_design(j,sigma_h=sigma,rtol=rtol)['total_coefficient_nm_minus2']
                check=height_formula_crosscheck(j,sigma,rtol)
                error=abs(direct-check['coefficient_by_subtraction'])
                _require(error<=tol, 'HEIGHT_FORMULA_CROSSCHECK_FAILED')
                values.append(direct)
                crosschecks.append(dict(scale=scale,rtol=rtol,sigma_h_nm=None if math.isinf(sigma) else sigma,
                                        absolute_error=error,relative_to_baseline=error/base if base else None))
            _require(all(x+tol>=y for x,y in zip(values,values[1:])), 'HEIGHT_MONOTONICITY_FAILED')
    qualification=('BOUNDARY_ALGEBRA_ONLY_NO_REQUIREMENT_RANKING' if a['parameter_boundary'] else
                   'INDETERMINATE_LOCAL_NUMERICS' if any_unstable or not a['derivative_stable'] or not a['directional_stable'] or any(a['tiny_columns']) else
                   'CHECKED_LOCAL_DESIGN_NOT_EXPERIMENTAL_PRECISION')
    return dict(theta=diagnostic['theta'], score=diagnostic['score'],
                designs=sweeps, checks=checks, formula_crosschecks=crosschecks, independent_checks=independent_checks,
                design_count=17, evaluation_count=102,
                all_nuisance_exact_baseline=float(fi[:,0]@fi[:,0]),
                qualification=qualification, boundary=a['parameter_boundary'],
                reportable_D=None,global_uniqueness_certified=False,
                experimental_absolute_diameter_validated=False)


def probe_eligible(design: dict) -> bool:
    return (design['qualification']=='CHECKED_LOCAL_DESIGN_NOT_EXPERIMENTAL_PRECISION' and
            all(design['checks'][x]['numerically_stable'] for x in ('free','exact_height','height_sigma_10nm')))
