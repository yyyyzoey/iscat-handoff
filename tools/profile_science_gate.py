"""Fail-closed structural qualification of a *single-model* empirical D profile.

A structural PASS is a prerequisite, not proof of global optimization,
identifiability, physics, or an experimental confidence interval.
"""
from __future__ import annotations
import math


def check(profile, *, expected_model_id, expected_observation_sha,
          joint_D, joint_loss, domain=(30.,200.),
          loss_tolerance=None):
    reasons=[]
    if profile.get('model_id')!=expected_model_id:
        reasons.append('MODEL_ID_MISSING_OR_DIFFERENT')
    if profile.get('observation_sha256')!=expected_observation_sha:
        reasons.append('OBSERVATION_ID_MISSING_OR_DIFFERENT')
    if profile.get('loss_type')!='UNSCALED_L2_SAME_13x13_SIGNED_C':
        reasons.append('LOSS_IDENTITY_MISSING_OR_DIFFERENT')
    if profile.get('profile_complete') is not True:
        reasons.append('PROFILE_SEARCH_NOT_COMPLETE')
    if profile.get('adaptive_coverage_complete') is not True:
        reasons.append('ADAPTIVE_REFINEMENT_NOT_COMPLETE')
    rows=profile.get('rows')
    if not isinstance(rows,list) or not rows:
        reasons.append('MISSING_PROFILE_POINTS');rows=[]
    ds=[]
    for r in rows:
        if not isinstance(r,dict):
            reasons.append('BAD_POINT');continue
        D=r.get('D');loss=r.get('loss');theta=r.get('theta')
        if not all(isinstance(z,(int,float)) and not isinstance(z,bool) and math.isfinite(z) for z in (D,loss)):
            reasons.append('MISSING_OR_NONFINITE_POINT');continue
        if theta is None or len(theta)!=4 or abs(theta[0]-D)>1e-7:
            reasons.append('POINT_THETA_D_MISMATCH')
        if r.get('point_search_complete') is not True:
            reasons.append('POINT_SEARCH_INCOMPLETE')
        if not isinstance(r.get('attempts'),list) or not r['attempts']:
            reasons.append('NO_START_EXIT_EVIDENCE')
        ds.append(float(D))
    if not ds:
        reasons.append('NO_VALID_POINTS')
    else:
        if min(ds)>domain[0]+1e-10 or max(ds)<domain[1]-1e-10:
            reasons.append('DOMAIN_ENDPOINTS_MISSING')
        if not any(abs(d-joint_D)<=1e-8 for d in ds):
            reasons.append('JOINT_D_WITNESS_NOT_INCLUDED')
        vals=[r['loss'] for r in rows if isinstance(r,dict) and isinstance(r.get('loss'),(int,float)) and math.isfinite(r['loss'])]
        if vals and isinstance(joint_loss,(int,float)) and math.isfinite(joint_loss):
            tol=max(1e-12,1e-7*abs(joint_loss)) if loss_tolerance is None else loss_tolerance
            matching=[r for r in rows if isinstance(r,dict) and isinstance(r.get('D'),(int,float)) and abs(r['D']-joint_D)<=1e-8 and isinstance(r.get('loss'),(int,float))]
            if matching and min(x['loss'] for x in matching)>joint_loss+tol:
                reasons.append('PROFILE_DROPS_KNOWN_SAME_D_JOINT_WITNESS')
            # A refined global minimum may legitimately improve the joint solution;
            # only require explicit recorded reconciliation rather than rejecting.
            if min(vals)<joint_loss-tol and profile.get('joint_update_performed') is not True:
                reasons.append('PROFILE_BETTER_THAN_UNRECONCILED_JOINT')
    return {'structurally_qualified':not bool(reasons),
            'reason_codes':sorted(set(reasons)),
            'scope':'SOFTWARE_PRECONDITION_ONLY_NOT_GLOBAL_OPTIMUM_OR_PHYSICS'}
