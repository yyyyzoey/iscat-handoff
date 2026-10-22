"""Fail-closed reference gates for F2 profile structural validity and reportability.

Passing these software checks is a necessary condition, never a physics or
experimental absolute-size certification. All true values belong to an external
validator; never provide true D to the estimator or the quality gate.
"""
from __future__ import annotations
import math

REQUIRED_EVIDENCE=(
 'observable_valid','locked_F2_valid','raw_geometry_provenance_valid',
 'same_solve_shift_qualified','field_numerical_qualified',
 'optimizer_converged','search_complete','profile_complete',
 'adaptive_coverage_complete','joint_profile_consistent',
 'empirical_model_error_frozen','h_xy_boundary_independence_qualified',
 'detection_pass','noise_background_FPR_qualified')

def finite(x):return isinstance(x,(float,int)) and not isinstance(x,bool) and math.isfinite(x)

def check_profile(profile,*,model_id,observation_sha256,joint_D,joint_loss,domain=(30.,200.)):
    reasons=[]
    if profile.get('model_id')!=model_id:reasons.append('MODEL_NOT_BOUND')
    if profile.get('observation_sha256')!=observation_sha256:reasons.append('OBSERVATION_NOT_BOUND')
    if profile.get('loss_type')!='UNSCALED_L2_ON_CENTRAL13_SIGNED_STATIC_C':reasons.append('LOSS_DEFINITION_MISMATCH')
    for key in ('grid_coverage_complete','adaptive_coverage_complete','joint_reconciled'):
        if profile.get(key) is not True:reasons.append('INCOMPLETE:'+key)
    rows=profile.get('rows');ds=[]
    if not isinstance(rows,list) or not rows:rows=[];reasons.append('EMPTY_PROFILE')
    for z in rows:
        if not isinstance(z,dict):reasons.append('BAD_POINT_FORMAT');continue
        d=z.get('D');loss=z.get('loss_L2');theta=z.get('theta')
        if not finite(d) or not finite(loss) or loss<0 or not isinstance(theta,list) or len(theta)!=4 or not all(finite(t) for t in theta):
            reasons.append('INVALID_POINT');continue
        if abs(float(d)-float(theta[0]))>1e-8:reasons.append('POINT_D_THETA_MISMATCH')
        if z.get('point_search_complete') is not True:reasons.append('INCOMPLETE_POINT_SEARCH')
        attempts=z.get('attempts',[])
        if not isinstance(attempts,list) or not attempts:reasons.append('NO_OPTIMIZER_EVIDENCE')
        else:
            if not any(a.get('success') is True and a.get('budget_exhausted') is False for a in attempts):
                reasons.append('NO_CONVERGED_NUISANCE_OPTIMIZATION')
            if any(a.get('budget_exhausted') is True or a.get('success') is not True for a in attempts):
                reasons.append('REQUIRED_START_FAILED_OR_UNQUALIFIED')
        ds.append((float(d),float(loss)))
    if ds:
        if min(x[0] for x in ds)>domain[0]+1e-8 or max(x[0] for x in ds)<domain[1]-1e-8:
            reasons.append('DOMAIN_ENDPOINTS_MISSING')
        if not any(abs(x[0]-joint_D)<=1e-8 for x in ds):reasons.append('EXACT_JOINT_D_MISSING')
        if finite(joint_loss):
            tol=max(1e-12,1e-7*abs(joint_loss))
            same=[x[1] for x in ds if abs(x[0]-joint_D)<=1e-8]
            if same and min(same)>joint_loss+tol:reasons.append('DROPPED_KNOWN_EXACT_JOINT_WITNESS')
            if min(x[1] for x in ds)<joint_loss-tol and profile.get('updated_joint_loss') is None:
                reasons.append('PROFILE_BEATS_UNUPDATED_JOINT')
    else:reasons.append('NO_VALID_POINTS')
    return dict(structurally_complete=not bool(reasons),reason_codes=sorted(set(reasons)),
      scope='NUMERIC_STRUCTURAL_GATE_ONLY_NOT_PHYSICS_OR_GLOBAL_OPTIMUM')

def check_reportability(candidate_D,compatible_components,evidence,*,domain=(30.,200.)):
    """Candidate and compatible components only; NO true size permitted."""
    reasons=[]
    if not finite(candidate_D) or not domain[0]<=candidate_D<=domain[1]:reasons.append('INVALID_CANDIDATE')
    if not isinstance(evidence,dict):evidence={};reasons.append('MISSING_EVIDENCE')
    if any(k in evidence for k in ('D_true','true_D','err_D','ground_truth_D')):reasons.append('TRUTH_LEAKAGE')
    for k in REQUIRED_EVIDENCE:
        if evidence.get(k) is not True:reasons.append('NOT_QUALIFIED:'+k)
    if evidence.get('observable_type')!='SIGNED_STATIC_C_FROM_LINEAR_INTENSITY':
        reasons.append('OBSERVABLE_MISMATCH')
    if evidence.get('measurement_mode') not in ('REAL_LINEAR_CAMERA','NOISY_CAMERA_CONDITIONAL'):
        reasons.append('NO_CAMERA_DETECTION_FOR_CLEAN_SYNTHETIC')
    if not isinstance(compatible_components,list) or len(compatible_components)!=1:
        reasons.append('NO_UNIQUE_COMPATIBLE_COMPONENT')
    else:
        v=compatible_components[0]
        if not isinstance(v,list) or len(v)!=2 or not all(finite(y) for y in v) or not v[0]<v[1]:
            reasons.append('INVALID_COMPATIBLE_INTERVAL')
        else:
            lo,hi=v
            if lo<domain[0] or hi>domain[1]:reasons.append('OUTSIDE_SUPPORT')
            if lo<=domain[0]+1e-9 or hi>=domain[1]-1e-9:reasons.append('INTERVAL_TOUCHES_SUPPORT_BOUNDARY')
            if finite(candidate_D):
                if not lo<=candidate_D<=hi:reasons.append('CANDIDATE_NOT_IN_COMPATIBLE_INTERVAL')
                if hi-lo>2*max(5.,.1*candidate_D):reasons.append('COMPATIBILITY_TOO_WIDE')
    return dict(candidate_D=float(candidate_D) if finite(candidate_D) else None,
      reportable_D=float(candidate_D) if finite(candidate_D) and not reasons else None,
      diameter_reportable=not bool(reasons),reason_codes=sorted(set(reasons)),
      scope='CONDITIONAL_FAIL_CLOSED_GATE_NOT_ABSOLUTE_EXPERIMENTAL_CALIBRATION')
