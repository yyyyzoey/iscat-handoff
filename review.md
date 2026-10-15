# v090 Review

## Verdict on v089
- RETAINED: the fixtures coverage, design-matrix rank/condition, 12 complex closures (as algebra), the 24-map archive (SHA verified), and all inherited evidence.
- RETRACTED: the published D2/D3 rows for 200/400 Hz (420 Hz overwrite via the (model,window)-keyed summary dict); the claim "joint LS reduced the 400 Hz inner product from 0.2494 to 0.0715"; the derived trend-magnitude statement. The per-frequency coefficient MAPS in the NPZ were saved correctly and are the recovery source.

## What v090 establishes
1. **Phase A**: archive identity verified (SHA-256 c75fd800... = review value; 24 full-frequency-key maps; means + mask present).
2. **Phase B**: 8/8 fixtures through the real aggregator - frequency-distinguished positive, overwrite negative reproduced-then-rejected, W1 orthogonality, W2 Gram identity, D3 recovery <1e-11, denominator tamper, duplicate keys, SHA+NaN.
3. **Phase C**: correct 12 rows recovered from the NPZ with ZERO refit. W1 orthogonality identity 3/3 (D2==D1 on W1). W2 sufficient-statistic recovery 3/3 (D2 from D1 via the 6x6 Gram; analytic cos-block confirmed). Corrected 400 Hz diff L2: D0 0.33601 / D1 0.33610 / **D2 0.33607 / D3 0.33505** - inside the review-predicted [0.334370, 0.337834]. Exactly 4 legacy rows changed. Conditional full-ROI recovery NOT used (0/4; NPZ intact).
4. **Phase D**: 12-pixel sparse QR (one authorized sparse HDF5 read session): 12/12 frequency-identity + 12/12 complex closure PASS. A verification-script denominator error was found and fixed during the session (honestly logged).
5. **Closure**: the estimator-diagnostic branch is CLOSED. The within-record 400 Hz difference persists across all four corrected estimators (diff L2 0.335-0.336); its root cause remains UNDETERMINED - not attributable to the tested estimator choices, and no magnetism/noise/particle claim is made.

## Not claimed
No magnetic causality, diameter, Bias/RMSE, detectability, FPR, or identifiability. Frozen states unchanged.
