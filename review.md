# v088 Review

## Verdict on v087
- RETAINED: the independent cached-video FFT (1681/1681 OR-gate), probe results, orientation anchoring, crop identity, 24-map and 276-pair inheritance.
- RETRACTED/CORRECTED: (X1) 8 neighbour frequency labels were one bin high - corrected to f=(k_matlab-1)*Fs/N, matching the v073 historical table; (X2) the ranking JSON interpretation text contradicted its own argmin result - now templated from booleans; FIX2 was not truly touching - now Fraction-exact and executed; (X3) the experiment full-frame floor was applied to a DEMO map - mask scopes now separated in the real production loader.

## What v088 establishes
1. **Phase A/B**: published-CSV re-audit (1681/1681 OR-gate with 4/1 boundary counts honestly noted); 8 corrected spectral bins matching v073 history; ranking audit with 4 truly-executed Fraction fixtures (swap / exact touch / separated / overlap) - observed_rank_same=YES, RANK_CERTIFIED=NO.
2. **Phase C**: DEMO_ROI_LOCAL vs EXPERIMENT_FULL_FRAME_SOURCE mask scopes implemented in the real loader; full-frame floor identity confirmed to 2.47e-8 relative; 8/8 live tests with scope-misuse and tamper rejections.
3. **Phase D**: the single authorised segmented diagnostic - 6 secondary within-record demodulation maps (2 pre-registered windows x {200,400,420} Hz, global time origin). Window-to-window coherences 0.044/0.249/0.071 reported as descriptive within-record consistency only - they are neither magnetic causality nor independent repeats, and 420 Hz is an empirical control, not a proven noise distribution.

## Not claimed
No magnetic causality, diameter, Bias/RMSE, detectability, FPR, identifiability, or noise-model claims. Frozen states unchanged.
