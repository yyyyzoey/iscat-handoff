"""Fail-closed, truth-independent diameter quality gate. No simulated ground truth accepted.
A conditional synthetic noiseless result is NEVER camera-reportable by this gate.
"""
import math
REQUIRED=('source_lineage_qualified','model_identity_locked','direct_render_qualified',
 'optimizer_converged','independent_starts_checked','search_complete','profile_complete',
 'adaptive_coverage_complete','compatible_interval_validated',
 'h_xy_boundary_independence_qualified','development_error_rule_frozen',
 'observable_type_qualified','camera_detection_qualified','camera_false_positive_qualified')

def numeric(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)

def gate(candidate,components,evidence,domain=(30.,200.)):
    reasons=[]
    if not numeric(candidate) or not domain[0]<=candidate<=domain[1]:reasons.append('INVALID_CANDIDATE')
    if not isinstance(evidence,dict):evidence={};reasons.append('EVIDENCE_MISSING')
    if {'true_D','D_true','ground_truth_D','abs_error_nm','label_D'}&set(evidence):reasons.append('TRUTH_LEAKAGE_FORBIDDEN')
    for r in REQUIRED:
        if evidence.get(r) is not True:reasons.append('NOT_QUALIFIED:'+r)
    if evidence.get('measurement_mode') not in ('REAL_LINEAR_CAMERA','NOISY_CAMERA_CONDITIONAL'):
        reasons.append('NOT_A_CAMERA_MEASUREMENT')
    if evidence.get('observable_kind')!='SIGNED_STATIC_C':reasons.append('OBSERVABLE_KIND_MISMATCH')
    if not isinstance(components,list) or len(components)!=1:reasons.append('UNIQUE_COMPONENT_NOT_ESTABLISHED')
    else:
        c=components[0]
        if not isinstance(c,(list,tuple)) or len(c)!=2 or not all(numeric(v) for v in c) or not c[0]<c[1]:
            reasons.append('INVALID_COMPATIBLE_INTERVAL')
        else:
            lo,hi=c
            if lo<=domain[0] or hi>=domain[1]:reasons.append('INTERVAL_TOUCHES_SUPPORT_EDGE')
            if numeric(candidate):
                if not lo<=candidate<=hi:reasons.append('CANDIDATE_OUTSIDE_INTERVAL')
                if hi-lo>2*max(5.,.10*candidate):reasons.append('COMPATIBILITY_TOO_WIDE')
    return dict(candidate_D=float(candidate) if numeric(candidate) else None,
                reportable_D=float(candidate) if numeric(candidate) and not reasons else None,
                reportable=not bool(reasons),reason_codes=sorted(set(reasons)),
                scope='CONDITIONAL_GATE_ONLY_EXPERIMENTAL_ABSOLUTE_NOT_VALIDATED')
