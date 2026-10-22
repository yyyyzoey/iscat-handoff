"""Strict reference quality gate for a conditional, size-aware F2 measurement.

Not a confidence-interval or experimental calibration method. All inputs must
come from observable-only processing and a pre-frozen error/physics qualification.
NEVER pass true diameter into the formal estimator or this gate.
"""
from __future__ import annotations
import math
from typing import Any, Dict

REQUIRED = (
    "observable_valid", "model_locked_F2", "source_geometry_qualified",
    "same_solve_forward_qualified", "model_numerics_qualified",
    "optimizer_converged", "search_complete", "profile_complete",
    "adaptive_coverage_complete", "joint_profile_consistent",
    "empirical_model_error_frozen", "h_xy_boundary_independence_qualified",
    "detection_pass", "noise_FPR_qualified"
)


def _finite(v):
    try:
        return isinstance(v, (float, int)) and not isinstance(v, bool) and math.isfinite(v)
    except (TypeError, ValueError):
        return False


def evaluate(candidate_D: float, components: Any, gates: Dict[str, Any],
             *, lower_D=30.0, upper_D=200.0):
    """Return reason-codes and reportable_D or None; never inspect ground truth.

    components: a complete pre-frozen empirical compatibility set, expressed
    as a list of closed [D_min,D_max] intervals in nm.
    gates: values MUST be exact booleans. False or missing means no report.
    """
    reasons = []
    if not (_finite(candidate_D) and lower_D <= candidate_D <= upper_D):
        reasons.append("INVALID_CANDIDATE_D")

    if any(k in gates for k in ("true_D", "D_true", "diameter_truth", "err_D")):
        reasons.append("TRUTH_LEAKAGE_IN_GATE")

    for key in REQUIRED:
        if gates.get(key) is not True:
            reasons.append("GATE_NOT_PASSED:" + key)

    if gates.get("observable_type") != "SIGNED_STATIC_C_FROM_LINEAR_INTENSITY":
        reasons.append("OBSERVABLE_TYPE_MISMATCH")
    if gates.get("measurement_mode") not in ("NOISY_CAMERA", "REAL_LINEAR_CAMERA"):
        reasons.append("NO_ACCEPTANCE_FOR_CLEAN_SYNTHETIC_DIAGNOSTIC")

    if not isinstance(components, list) or len(components) != 1:
        reasons.append("NONUNIQUE_OR_MISSING_COMPATIBILITY")
    else:
        one = components[0]
        if not isinstance(one, (tuple, list)) or len(one) != 2 or not all(_finite(v) for v in one):
            reasons.append("INVALID_COMPATIBILITY_INTERVAL")
        else:
            left, right = (float(one[0]), float(one[1]))
            if left >= right or left < lower_D or right > upper_D:
                reasons.append("INVALID_COMPATIBILITY_BOUNDS")
            else:
                if left <= lower_D + 1e-9 or right >= upper_D - 1e-9:
                    reasons.append("COMPATIBILITY_TOUCHES_SIZE_SUPPORT_BOUNDARY")
                if _finite(candidate_D):
                    if not (left - 1e-9 <= candidate_D <= right + 1e-9):
                        reasons.append("CANDIDATE_OUTSIDE_COMPATIBILITY")
                    allowed_width = 2 * max(5.0, 0.1 * float(candidate_D))
                    if right - left > allowed_width + 1e-9:
                        reasons.append("COMPATIBILITY_TOO_WIDE")

    reasons = list(dict.fromkeys(reasons))
    return {
        "candidate_D": float(candidate_D) if _finite(candidate_D) else None,
        "reportable_D": (float(candidate_D) if not reasons else None),
        "diameter_reportable": not bool(reasons),
        "reason_codes": reasons,
        "scope": "FAIL_CLOSED_REFERENCE_GATE_NOT_EXPERIMENTAL_ABSOLUTE_CALIBRATION"
    }
