# v089 Review

## Verdict on v088
- RETAINED: the 6 secondary demodulation maps, the paired statistics, the spectral corrections, mask scopes, ranking decision, and all inherited evidence.
- CORRECTED (reproducibility, zero FFT): R1 - frequency labels now stored at %.17g with an explicit 1e-10 Hz roundtrip check; R2 - a 6-row per-window/per-frequency list supplements the 3 paired rows; the NPZ now stores per-window Imean and raw X numerators (previously missing); the ranking min_other_lo is auto-derived.
- SCOPE HONESTY: the normalized inner product is renamed a spatial complex-map normalized inner product (insensitive to a single global phase); the v088 400 Hz coherence 0.2494 is retained as reported.

## What v089 establishes
1. **Phase A**: full-precision spectral roundtrip 8/8; floor identity 6 rows; lineage 4 objects.
2. **Phase B**: 8/8 fixtures through the real estimator functions - amplitude/phase recovery <1e-11 for a pure tone and a 200/400/420+trend mixture; the clock-reset negative (start 1003) is detected; complex closure holds with an off-model 300 Hz component landing in the residual; inner-product invariance to gain/phase; NaN/degenerate-axis/zero-norm guards. (Sign-convention corrections during the session are honestly logged.)
3. **Phase C**: the 6 v088 maps reproduce at rF<1e-10 in one shared session; window moments show neither window dips below the full-frame floor; the fixed intersection mask equals the v088 full-record mask (1681/1681).
4. **Phase D (the answer)**: over the four pre-registered estimators the 400 Hz two-window complex difference L2 moves only 0.3360 -> 0.3361 -> 0.3120 -> 0.3111. Local-vs-common denominator: negligible. Joint-basis LS: removes measurable cross-frequency coupling (inner product 0.2494 -> 0.0715). Trend: minor. A ~0.31 difference persists in every tested estimator, so it cannot be attributed to these estimator choices alone - and equally cannot be attributed to magnetism, noise type, or particle presence by this analysis.
5. **Phase E**: all 12 complex closures PASS.

## Not claimed
No magnetic causality, diameter, Bias/RMSE, detectability, identifiability, or noise-model determination. All within-record quantities remain secondary diagnostics. Frozen states unchanged.
