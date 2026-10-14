# v079 review summary

## 1. Design matrix rank deficiency (X1): reproduced, fixed, all 24 corrected

v078 harmonic design matrix had a column-index collision: `Bm(:,2+2*(hI-1)-1)` placed cos(200Hz) at column 1 (overwriting the intercept), and column 9 was never assigned. Old matrix: rank=8, cond=Inf. Correct matrix: rank=9, cond=1.41.

All 24 trajectory harmonic decompositions recomputed with the correct full-rank matrix. The key finding: **M200 bin161/C400_fit = 0.9895-0.9897 with the CORRECT matrix** — confirming that the bin-161 content IS the coherent 400Hz harmonic. The v076 claim was correct all along; the v078 "990×" discrepancy was caused by the rank-deficient matrix, not by the harmonic content.

## 2. Closure verification

All 24 trajectories: complex closure |Xbin - (ΣX_h + X_res + X_int)| / (√N·||y||) < 1e-10. Per-harmonic DFT contributions saved in long format (DFT_count units, separate real/imag columns).

## 3. Odd/even, camera ROI, identifiability (inherited)

270 odd/even records, 24 camera ROI rows, 276-pair identifiability — all inherited from v078 without recompute, light re-verification confirms consistency.

## 4. Exposure convergence

8 exposure conditions with 400Hz sinc reference. M200 rel_change: -0.09% to -0.86% (correctly using 400Hz observation frequency). M400 centre near-zero: NUMERICALLY_UNRESOLVED. Higher-order quadrature not executed (resource limit). SYNTHETIC_TAU_ONLY.

## 5. P0 / frozen states

P0 NOT_RUN_RESOURCE_GATED. Gate OPEN at 2.58848e-7 vs 1e-10. calibration_valid=false, experimental_validation=false, single_particle_diameter=NOT_ESTIMATED.
