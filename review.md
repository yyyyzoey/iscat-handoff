# v084 Review

## Verdict on v083
- RETAINED: 24 true-centre identities (centre gate), X0 closure, phase fixes, 4 full-ROI double maps, 2x 64-node evaluations, 276-pair screening, parameter contract.
- RETRACTED: the summary-level claim `legacy_bug_proven=true` in v083 status.json. The v083 per-case table honestly recorded `legacy_col1_bug_recon_maxdiff` 1.1e-5..4.2e-4 with `bug NOT_PROVEN` evidence - the proof did not exist because the check called `block_at(1,21)` (= MATLAB row1,col21) instead of `(21,1)`.

## What v084 establishes
1. **Phase A0 (pilot)**: with the corrected call, `block_at(21,1)` reproduces the v076 legacy `tseries_center` at **max|dI| = 9.3e-10** (< frozen 1e-8 gate). Crucially the proof is multi-point: `Ipix(26,1)` matches `tseries_off1` and `Ipix(16,1)` matches `tseries_off2`, both at 9.3e-10, while the swapped hypothesis is rejected (7.9e-5 / 9.8e-5) and the centre is a distinct identity (5.3e-4). The h5py axis convention (axis1=MATLAB col, axis2=MATLAB row) is therefore empirically anchored at three independent asymmetric pixels plus the source-declared Ipix indexing.
2. **Phase A1**: all 24 conditions LEGACY_COL1_NUMERIC_VERIFIED (<1e-8). A transient NameError run was honestly logged and resolved before the final table; the true-centre v083 results were not re-run.
3. **Phase B**: all 4 v083 double maps ORIENTATION_CONFIRMED against the stored single maps - direct masked rF 1.09e-5..1.16e-4 vs transposed 0.98..1.414 (M400 maps are near-antisymmetric, anisotropy ~sqrt(2), decisive). Probe pixels recorded; MATLAB FFT cross-check NOT_EXECUTED (licence safety); NO_NEAR_ZERO_RELATIVE_CONCLUSION retained.
4. **Phase C**: the closest cross-D shape pair (D30_zf550_M400_a20 vs D60_zf450_M400_a20) re-checked in double precision: shape-Frobenius distance 0.133264 (double) vs 0.133265 (single, historical) - stable to 3.8e-7. Discrete-set statistic only.
5. **Phase D/F**: full inheritance ledger; parameter readiness (23 rows); P0 NOT_RUN_RESOURCE_GATED.

## Not claimed
No experimental causality, diameter, calibration, noise model, detectability, or inversion-uniqueness. Frozen states unchanged. Zero new BEM/renders/exposure evaluations.
