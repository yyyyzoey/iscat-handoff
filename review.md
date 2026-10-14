# v083 Review

## Verdict on v082 (per instruction contract)
- RETAINED: the 24/96/24 validated tables, full-rank closure, negative guards, exposure 16/16 evaluations, parameter separation. No re-runs to pad records.
- CORRECTED: (X1) the v076 `tseries_center` cross-source comparison was a pixel mismatch (legacy field = MATLAB Ipix(21,1), proven numerically); (X2) `C400fit_phase_rad` held the FFT phase; (X3) closure omitted X0 (max 3.5e-21 - verdict unchanged, now explicit); (X4) "path_noise_scale" renamed semantics: deterministic numerical path-difference bound, NOT instrument noise; (X5) exposure convergence limited to finite 16->32 (now 32->64) increments, no general O(M^-2) claim; (X6) completion evidence separated from scientific conclusions.

## What v083 adds
1. **Phase A**: all 24 true-centre (ROI 21,21) series rebuilt from the same five anchors via three documented operators (field-first double, quadratic-form double, quadratic-form float32). The float32 reconstruction matches the v076 small-MAT series to <=4.7e-10 (accumulation-order rounding) for ALL 24 conditions -> SAME_PIXEL_SAME_OPERATOR_VERIFIED. The legacy field is reproduced by the (row21,col1) reconstruction to 9.3e-10 -> bug PROVEN, documented in `history/v076_tseries_center_col1_bug_source.txt`. 7 negative tests all rejected (pixel injection, axis-convention metadata + asymmetric numeric check, wrong ROI 64:268, SHA mismatch, length, map-centre guard).
2. **Phase B**: X0-explicit complex closure for all 24 (all PASS; v082 historical without-X0 columns preserved); corrected phase columns (42 rows; 12 UNRESOLVED_NEAR_ZERO).
3. **Phase C**: 4 frozen conditions, full 41x41 double complex C400 maps by bounded streaming (batch<=32, peak 12.1 MB); map-level double-vs-single Frobenius spread 1.1e-5..1.2e-4 quantified; centre diffs consistent with the known single-precision path scale.
4. **Phase D**: exactly the 2 authorised 64-node midpoint evaluations; both show 32->64 increments smaller than 16->32 (finite convergence evidence only).
5. **Phase E**: 276-pair screening of fixed observables from the 24 existing maps; within-D amplitude confounding quantified (e.g. D30 A_ROI spans 1.4e-4..0.032); shape is amplitude-eliminated diagnostic only.
6. **Phase F**: 23-row parameter contract with per-item last-verified status and 6 gating gaps; P0 NOT_RUN_RESOURCE_GATED (0 processes detected - explicitly NOT proof of licence safety).

## Not claimed
No experimental causality, diameter, calibration, noise model, detectability, or inversion uniqueness. Frozen states unchanged.
