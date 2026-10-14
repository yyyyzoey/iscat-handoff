# v082 Review

## Verdict on v081 (upheld from instruction contract)
- KEEP: `v081_harmonics24_correct.csv` mathematics (24 rows, rank 9, closure <= 3.9e-14) as a Python/NumPy math result.
- REJECT as publish: v081 validated/residual/identity/parts tables (ERROR rows / empty), `bin161_absC` dimensional mislabel (raw DFT count presented where dimensionless C belongs), intercept-column documentation mismatch, status over-claim.
- v081 tables preserved unchanged under `history/`.

## What v082 adds
1. **Phase A**: source identity with SHA-256 for both cached MATs (copies verified byte-identical); 24-case structural verification; corrected-map C400(21,21) cross-check; 10 negative fixtures ALL rejected by the validator (wrong basis label, intercept metadata lie, undefined R, rank-8 acceptance, raw-X-as-C units, closure-gate violation, short CSV row, duplicate keys, control chars, wrong row count).
2. **Phase B**: full-rank intercept-first harmonic decomposition of the 24 stored centre series; complex closure `Xbin = sum(X_h) + X0 + Xres` with every numerator stored as Re/Im in DFT_count; normalized operators kept separate (`Cbin = 2Xbin/(N*Im)`, `C400fit = A400/Im`); 5 tables with 24/96/24/24 unique-key records verified by independent stdlib readback; 3 small readable MAT samples.
3. **Phase C**: weak M400 centre diagnostics on 6 fixed conditions. Key finding: the single-precision historical path has noise 2.1e-8..5.7e-8 in |C400|, which SWAMPS the D30 signal (2.7e-9); the double-precision and complex-field-first paths agree to ~1e-17, and D100-level signals are robust. Relative error is flagged meaningful only above 10x the path noise.
4. **Phase D**: analytic 400 Hz sinc fixture (measured quadrature vs full predicted DFT model match 1e-14; att_M -> |sinc(400 tau)| with O(M^-2) convergence); 16/32-node midpoint exposure integrals for all 8 legacy synthetic conditions = exactly 16 evaluations, deltas vs the inherited v076 5-node results recorded. ALL tau remain SYNTHETIC_TAU; real exposure is MISSING.
5. **Phase E**: parameter contract separated into USER_CONFIRMED / EXPERIMENTAL_SCRIPT_RECORDED / HISTORICAL_RECORDED_UNVERIFIED_FINAL_SETUP / SIMULATION_ASSUMPTION / MISSING. The 200 Hz field frequency, 14 um sensor pixel and 50x nominal objective are historical records, not verified final setup; object-space scale remains undetermined (280 nm/px only if no extra magnification; 65 nm/px is demo).
6. **Phase F**: P0 hook NOT_RUN_RESOURCE_GATED (0 MATLAB processes detected; budget preserved).

## Not claimed
- No experimental magnetic causality, no particle diameter, no calibration, no physical accuracy. All observables are prescribed synthetic trajectories on cached optical fields. The 400 Hz / 200 Hz association stays ASSOCIATION_ONLY.
