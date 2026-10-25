"""V154 evidence binding and local sensitivity helpers.
No truth, simulator, new camera draw, threshold, or reportable diameter.
All actual model predictions must be provided by CountedPredictor.
These helpers do NOT replace a tested, source-locked workstation adapter.
"""
from __future__ import annotations
import hashlib, json
from dataclasses import dataclass
from typing import Callable, Any
import numpy as np
from v152_gls_core import GlsData, check_theta, InvariantError, LOW, HIGH


def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',', ':'),allow_nan=False)


def select_saved_best(rows: list[dict], metric: str='Q_model') -> tuple[int, dict]:
    """Choose a complete source record, never combine D from one and Q from another."""
    candidates=[]
    for i,r in enumerate(rows):
        if 'theta' not in r:
            continue   # failed source rows remain in the caller's immutable raw archive
        t=check_theta(r['theta'])
        q=float(r[metric])
        if not np.isfinite(q) or q<0: raise ValueError('invalid saved Q')
        candidates.append((q,i,dict(r,theta=t.tolist())))
    if not candidates: raise ValueError('no complete finite source witness')
    _,idx,row=min(candidates,key=lambda v:(v[0],v[1]))
    return idx,row


def bind_prediction(source: dict, theta, prediction, data: GlsData) -> dict:
    for k in ('commit','path','row_id','model_id','observation_id','variance_sha256'):
        if not isinstance(source.get(k),str) or not source[k]: raise ValueError('missing source '+k)
    t=check_theta(theta);c=data.prediction(prediction);s=data.score(c)
    # Do not take candidate_D, Q or h/x/y from an unrelated summary record.
    d=dict(source=source,theta=t.tolist(),candidate_D=float(t[0]),**s,
           prediction_sha256=hashlib.sha256(np.ascontiguousarray(c).tobytes()).hexdigest(),
           reportable_D=None,interpretation='ATTAINABLE_WITNESS_NOT_GLOBAL_MINIMUM')
    d['witness_id']=hashlib.sha256(canonical(d).encode()).hexdigest()
    return d


def validate_binding(row: dict):
    t=check_theta(row['theta'])
    if float(row['candidate_D']) != float(t[0]): raise InvariantError('D / full theta mismatch')
    q=float(row['Q_joint']);qm=float(row['Q_model']);k=float(row['K'])
    per=np.asarray(row['Q_per_frame'],float)
    if not np.isfinite([q,qm,k]).all() or min(q,qm,k)<0 or per.ndim!=1 or not np.isfinite(per).all() or np.any(per<0):
        raise InvariantError('invalid loss record')
    tol=max(1e-8,1e-10*abs(q))
    if abs(q-qm-k)>tol or abs(q-float(per.sum()))>tol: raise InvariantError('Q metric identity mismatch')
    if row.get('reportable_D') is not None: raise InvariantError('unqualified reportable diameter')
    return True


def verify_returned_cost(fun,cost):
    """SciPy linear loss cost = 0.5 * sum(fun**2). Use residuals as Q authority."""
    r=np.asarray(fun,float)
    if not np.isfinite(r).all(): raise ValueError('nonfinite residual')
    q=float(r.ravel()@r.ravel())
    if not np.isfinite(cost) or abs(q-2*float(cost))>max(1e-8,1e-10*abs(q)):
        raise InvariantError('optimizer cost scaling mismatch')
    return q


def two_far_D_points(anchor: dict, pool: list[dict]) -> list[dict]:
    """At most one lower and one upper attained D, chosen without true labels."""
    validate_binding(anchor);d=float(anchor['candidate_D']);span=max(5.,0.1*d)
    obs=anchor['source']['observation_id'];mid=anchor['source']['model_id']
    valid=[]
    for r in pool:
        validate_binding(r)
        if r['source']['observation_id']!=obs or r['source']['model_id']!=mid:
            raise InvariantError('cross-observation / cross-model profile selection')
        valid.append(r)
    out=[]
    for side in (-1,1):
        v=[r for r in valid if side*(r['candidate_D']-d)>span]
        if v: out.append(min(v,key=lambda r:(r['Q_joint'],r['candidate_D'],r['witness_id'])))
    return out


def _projection_info(J: np.ndarray, rtol: float, nuisance_columns=(1,2,3)) -> dict:
    if not nuisance_columns or any(c not in (1,2,3) for c in nuisance_columns):
        raise ValueError('invalid nuisance columns')
    jd=J[:,0];jn=J[:,list(nuisance_columns)]
    dn=float(np.linalg.norm(jd));norms=np.linalg.norm(jn,axis=0)
    z=jn/np.where(norms>0,norms,1.)
    u,s,_=np.linalg.svd(z,full_matrices=False)
    rank=int(np.sum(s>rtol*s[0])) if len(s) and s[0]>0 else 0
    e=jd-u[:,:rank]@(u[:,:rank].T@jd)
    information=float(e@e)
    ratio=None if dn==0 else information/(dn*dn)
    if ratio is not None and (ratio < -1e-12 or ratio > 1+1e-10):
        raise InvariantError('projection information outside numerical range')
    return dict(rank=rank,nuisance_singular_values=s.tolist(),
                D_raw_squared_sensitivity=dn*dn,D_residual_squared_sensitivity=information,
                information_fraction=ratio,sensitivity_norm_fraction=None if ratio is None else float(np.sqrt(ratio)),
                nuisance_columns=list(nuisance_columns),svd_rtol=rtol)


def local_sensitivity(data: GlsData, theta, predict: Callable, *,
                      step_nm=(0.2,0.2,0.5,0.5), relative_tolerance=0.02) -> dict:
    """Two-scale finite differences. At most 17 unique predictions per call.

    Near bounds use second-order one-sided differences without clipping. The
    projection ignores inequality tangent cones, so boundary cases receive NO
    precision/identifiability interpretation. This is not an exact Fisher matrix.
    """
    t=check_theta(theta);steps=np.asarray(step_nm,float)
    if steps.shape!=(4,) or not np.isfinite(steps).all() or np.any(steps<=0): raise ValueError('bad steps')
    cache={};attempts=0
    def get(p):
        nonlocal attempts
        p=check_theta(p);key=tuple(map(float,p))
        if key not in cache:
            attempts+=1;cache[key]=data.prediction(predict(p))
        return cache[key]
    base=get(t);jac=[];schemes=[]
    for mult in (1.,.5):
        cols=[];which=[]
        for j,base_step in enumerate(steps):
            h=base_step*mult
            def offset(delta):
                z=t.copy();z[j]+=delta;return get(z)
            if t[j]-h>=LOW[j] and t[j]+h<=HIGH[j]:
                col=(offset(h)-offset(-h))/(2*h);scheme='central2'
            elif t[j]+2*h<=HIGH[j]:
                col=(-3*base+4*offset(h)-offset(2*h))/(2*h);scheme='forward2'
            elif t[j]-2*h>=LOW[j]:
                col=(3*base-4*offset(-h)+offset(-2*h))/(2*h);scheme='backward2'
            else: raise ValueError('difference stencil outside support')
            cols.append(col.ravel());which.append(scheme)
        jac.append(np.stack(cols,axis=1));schemes.append(which)
    relative=[]
    for j in range(4):
        denom=max(float(np.linalg.norm(jac[0][:,j])),float(np.linalg.norm(jac[1][:,j])),1e-15)
        relative.append(float(np.linalg.norm(jac[1][:,j]-jac[0][:,j]))/denom)
    J=jac[1]/np.sqrt(data.vbar).reshape(-1,1)
    ranks=[_projection_info(J,r) for r in (1e-8,1e-10,1e-12)]
    split={
        'remove_hxy':_projection_info(J,1e-10,(1,2,3)),
        'remove_xy_height_fixed_hypothesis':_projection_info(J,1e-10,(2,3)),
        'remove_h_xy_fixed_hypothesis':_projection_info(J,1e-10,(1,)),
    }
    single_frame=[_projection_info(jac[1]/np.sqrt(v).reshape(-1,1),1e-10) for v in data.variance]
    boundary=bool(np.any(np.minimum(t-LOW,HIGH-t)<=1e-6))
    stable=max(relative)<=relative_tolerance and len({r['rank'] for r in ranks})==1
    return dict(theta=t.tolist(),step_nm=steps.tolist(),schemes=schemes,
                derivative_relative_changes=relative,step_stable=stable,
                at_parameter_boundary=boundary,actual_predictor_requests=attempts,
                raw_J=jac[1].tolist(),whitened_J=J.tolist(),projection=ranks,
                nuisance_split=split,single_frame_at_same_theta=single_frame,
                interpretation=('LOCAL_LINEAR_DIAGNOSTIC_ONLY' if stable and not boundary
                                else 'NUMERICAL_OR_BOUNDARY_LIMITED_NO_PRECISION_CLAIM'),
                confidence_interval=None,global_uniqueness_certified=False,reportable_D=None)
