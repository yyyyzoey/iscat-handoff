# v087 Review

## Verdict on v086
- RETAINED: 24 map array verifications, 276-pair distances, guard structure, interface registration.
- CORRECTED: (P1-a) `observed_same` was a per-pair triangle proxy, not an argmin comparison - replaced with true per-path argmins (real data: both paths select the same pair, so YES stands honestly); (P1-b) certification restated as strict `nearest_hi < min(other_lo)` with endpoint-touching = NOT certified; (P0) full/replay sources were adapter-incompatible UNKNOWNs - now `fft400_corrected_full.mat` read via its actual Xk/C_k keys and v072 marked LEGACY_WRONG_AXIS_NEGATIVE; (P0) the heavy-compute counter was an unconnected stub - honesty fix.

## What v087 establishes
1. **Phase A**: true per-path argmins over 192 cross-D candidates with stable (distance, pair_id) ordering; 3 logic fixtures (argmin swap, endpoint touching, separated intervals) all PASS.
2. **Phase B**: production guard gains `check_mask_rule` (sourced full-frame floor 0.000117616...); 8/8 live tests including a real disk-file positive through `load_double_map`; geometry provenance via versioned source.
3. **Phase C (scientific core)**: the cached experimental video (`roiFrames`, 41x41x2001, float32) is independently re-Fourier-transformed in double precision. The stored MATLAB single-precision X400/C400/Imean are reproduced to float32 accumulation scale (max |dX| 1.06e-7, max |dC| 2.35e-7, max |dImean| 8.5e-7), the orientation is decisively anchored at asymmetric pixels, the 12 fixed probes pass the historical DFT/FFT gate, the mask rule agrees exactly with the full-frame floor, and the small ROI is proven to be the crop of the full-frame C_k. **This closes the v086 gap: the experimental observation is now independently derived from the cached frames, not merely algebraically reconciled.**
4. **Phase D/F**: readiness and P0 unchanged; zero new physics.

## Not claimed
The experimental 400 Hz observation remains a single-frequency association: no magnetic causality, no spatial calibration, no exposure truth, no noise model, no diameter. Frozen states unchanged.
