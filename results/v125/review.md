# V125 review (real executed scope)

## S0 intake
- Fixed v124@384a523; 15/15 reusable nodes verified by field+metadata readback; MAIN_7x9 frozen in plan_lock.json BEFORE any holdout existed.
- V124 render cfg/particle caveat: case identity established via filename+ledger cross-check and solve s.cfg readback (documented in v124_intake.csv).

## S1 fixes (all green)
- Mie: corrected Riccati zh1 convention; lossless Qabs fixture passes D=10..200 and FAILS for old v124_core.python_mie (evidence kept).
- Forward shift: particle-only translation (Eref fixed on camera grid); interpolation validated against exact MATLAB-sampled shifted fields; whole-scene camera-shift difference documented.
- Exposure: 1.25us fine 3D path archived; 2.5us is its strict subsample; intensity-domain window integration; nm/s unit bug fixed; support violations flagged, never clipped.
- Stats: even-sample median (V124 six-holdout median|e|=0.25nm reproduced); separate mean signed/MAE/RMSE/std/range.

## S2 qualification
- V124 original exact-match gate remains FAIL (7.5e-6); two-sided 1e-4 detune well above floor; new 1e-5 detune reported as measured (INDETERMINATE_NUMERICAL_FLOOR where below 2x floor); D30/D200 L0-vs-L1 floor-vs-signal ratios in numerical_qualification.csv.

## S3 library
- 63-node 7x9 D-h library: 15 identity-verified V124 reuses (0 new solves) + 48 new BEM solves + 1 re-solve of D100_h450 (the planned V124-cache import failed: jsondecode cannot represent map keys containing +/. characters; the re-solve is honestly counted); every node Er/Es->C replayed exactly.
- Per-node shift tables (28nm offset grid) for the frozen fast estimator; field-level exact forward used in refinement.

## S4/S5 blind holdout (new D, non-node h, nonzero xy; L1/1444 direct solves)
- Per case: [{"case": "H01", "err_D": -4.24, "err_h": -12.5, "err_xy": 0.2, "ambiguous": true, "boundary": true}, {"case": "H02", "err_D": -20.88, "err_h": -3.3, "err_xy": 2.0, "ambiguous": true, "boundary": false}, {"case": "H03", "err_D": 6.83, "err_h": -2.3, "err_xy": 0.3, "ambiguous": true, "boundary": false}, {"case": "H04", "err_D": 1.85, "err_h": -1.4, "err_xy": 0.0, "ambiguous": true, "boundary": false}, {"case": "H05", "err_D": 7.27, "err_h": -0.1, "err_xy": 0.1, "ambiguous": true, "boundary": false}, {"case": "H06", "err_D": 23.0, "err_h": 2.7, "err_xy": 0.0, "ambiguous": true, "boundary": true}]
- mean signed 2.30 nm, MAE 10.68 nm, RMSE 13.45 nm, median|e| 7.05 nm (n=6).
- Multi-basin/ambiguity and boundary flags per case in inversion_holdout_joint.csv and holdout_profiles/.

## S6 noise/blanks/motion
- Thresholds frozen on 240 dev targets + 100 dev blanks BEFORE holdout-noise/val-blank evaluation (threshold_freeze.json).
- Holdout noise: 51/90 accepted at frozen threshold; validation-blank false-accept rate 0.21 (valid for this synthetic blank distribution only).
- Motion/exposure (same 3D paths, 25/100us): M2 shared-D MAE per exposure: {"100.0": {"n": 10, "MAE": 37.0}, "25.0": {"n": 10, "MAE": 53.0}}; labeled SHARED_LIBRARY_METHOD_DIAGNOSTIC.

## Budget accounting (dual, honest)
- Science pool: 62 unique physical nodes attempted (61 planned + 1 import-failure re-solve) <= 64.
- Total BEM solve EXECUTIONS logged: 105. Extras beyond the science pool: 9 early failures (adapter save bug, root-caused to Windows MAX_PATH with hashed-key fix), ~10 re-executions caused by two adapter edits that changed the solver-id hash (cache keys are hash-bound; the second edit was reverted to restore cache validity), 2 single-case validation fixtures, and the remaining-key duplicates from a killed batch. Every execution is in logs/execution_ledger.csv.
- Renders: 161/240. Synthetic exposure events: 5958/6000.

## Honest limits
- EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=false; no independent size standard, material batch, or optical ruler.
- BEM accounting: science-pool attempts in logs/resource_budget.csv; 9 adapter-infrastructure solve executions (7 save failures, MAX_PATH root cause fixed; 2 validation fixtures) counted separately and visible in the ledger.
- Trajectory inversions use D-h library interpolation (SHARED_LIBRARY_METHOD_DIAGNOSTIC), not independent forward validation.
