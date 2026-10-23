"""V140 conservative conditional diameter quality gate; not a calibrated CI."""
from __future__ import annotations
import math
NEEDED=(
    'observable_signed_C_valid','library_and_code_locked','solve_to_render_lineage_qualified',
    'raw_to_canonical_axis_frozen','source_wide_shift_qualified',
    'F2_vs_direct_qualified','same_model_replay_qualified','optimizer_converged',
    'profile_complete','adaptive_coverage_complete','profile_joint_consistent',
    'empirical_error_scale_qualified','height_lateral_boundary_independent',
    'detection_pass','noise_FPR_qualified')

def finite(v):return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)

def decide(D,components,evidence,*,bounds=(30.0,200.0)):
    reasons=[]
    if not finite(D) or not bounds[0]<=D<=bounds[1]:reasons.append('INVALID_CANDIDATE')
    if not isinstance(evidence,dict):evidence={};reasons.append('EVIDENCE_MISSING')
    if any(k in evidence for k in ('true_D','D_true','ground_truth','truth_error','err_D')):
        reasons.append('TRUTH_LEAKAGE')
    for n in NEEDED:
        if evidence.get(n) is not True:reasons.append('NOT_QUALIFIED:'+n)
    if evidence.get('observable_type')!='SIGNED_STATIC_C_FROM_LINEAR_INTENSITY':
        reasons.append('OBSERVABLE_MISMATCH')
    if evidence.get('measurement_mode') not in ('NOISY_CAMERA_CONDITIONAL','REAL_LINEAR_CAMERA'):
        reasons.append('NO_CAMERA_BASED_REPORTABILITY')
    if not isinstance(components,list) or len(components)!=1:
        reasons.append('INCOMPLETE_OR_MULTIPLE_COMPATIBLE_COMPONENTS')
    else:
        v=components[0]
        if (not isinstance(v,list) or len(v)!=2 or not all(finite(q) for q in v)
            or not bounds[0]<=v[0]<v[1]<=bounds[1]):reasons.append('BAD_INTERVAL')
        else:
            lo,hi=v
            if lo<=bounds[0]+1e-9 or hi>=bounds[1]-1e-9:reasons.append('TOUCHES_SIZE_SUPPORT_BOUNDARY')
            if finite(D) and not lo<=D<=hi:reasons.append('POINT_OUTSIDE_COMPATIBILITY')
            if finite(D) and hi-lo>2*max(5,0.1*D):reasons.append('COMPATIBILITY_TOO_WIDE')
    return dict(candidate_D=float(D) if finite(D) else None,
       reportable_D=float(D) if finite(D) and not reasons else None,
       reason_codes=sorted(set(reasons)),diameter_reportable=not bool(reasons),
       scope='FAIL_CLOSED_REFERENCE_NOT_EXPERIMENTAL_ABSOLUTE_DIAMETER')
