# v086 Review

## Verdict on v085
- RETAINED: the 24 double maps, operator regression, 276-pair distances and epsilon values - all re-verified from actual arrays with matching SHAs and arithmetic.
- RETRACTED as insufficient: the v085 negative-test table (8/8) - several entries were hardcoded throws with test-identity/result text mismatches (NEG-S04/S05/S08) and hand-written sentinel constants. They are preserved read-only as historical-insufficient evidence.
- SCOPE CORRECTION: triangle-bound satisfaction is a mathematical necessity for any four vectors - it does not certify ranking or physical reliability. The correct certification test is interval overlap, performed this round.

## What v086 establishes
1. **Phase A**: a real shared production validator (`v086_identity_guard.py`) with specific GuardError exception types, used by the actual map-loading entry point; 1 positive case + 8 error injections + SQL-escape check + hardcoded-throw detector, all through the real entry, all with `heavy_compute_calls_before_rejection=0`.
2. **Phase B**: 24/24 maps re-verified - actual file SHA-256 matches the frozen v085 ledger; rF and epsilon recomputed from the arrays match the published rows to 1e-12 relative; anchor-cache SHA identity chain recorded; zero new evaluations.
3. **Phase C**: all 276 pairs recomputed from arrays. **Ranking certification result: the observed nearest cross-D pair is unchanged between the two numerical paths, but it is NOT certified by the conservative intervals** - I1=[0.13323436, 0.13329432] overlaps I2=[0.13324434, 0.13346221] (margin 8.9e-5 < b1+b2 1.39e-4). The nuisance screen (24/24 nearest-same-D) is IN_SAMPLE_GEOMETRY_SCREEN with duplicate motion conditions - not an identification rate.
4. **Phase D**: read-only interface check of the cached 7.29 experimental observation (`fft400_corrected_small_roi.mat`): OPERATOR_MATCH on all contract points (N/Fs/k/frequency/frames and Cbin=2X/(N*Imean) reproduces the stored C400), SPATIAL_CALIBRATION=MISSING, SCIENTIFIC_COMPARABILITY=NUMERIC_ONLY. No BMP reread, no registration, no experimental-D comparison.
5. **Phase E/F**: 6 physical blocking classes for the next real-physics stage; P0 NOT_RUN_RESOURCE_GATED; rule7 0.

## Not claimed
No experimental diameter, Bias/RMSE, detectability, FPR, magnetic causality, or continuous identifiability. Frozen states unchanged.
