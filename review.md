# v078 review summary

## 1. Complex harmonic closure (highest priority): conjugate fix confirmed

The v077 formula used `(A_h/2)*G_N(...)` for both positive and negative frequency terms, missing the complex conjugate on the mirror term. The correct formula is `(A_h/2)*G_N(f_h/Fs-k0/N) + (conj(A_h)/2)*G_N(-f_h/Fs-k0/N)`. This matters when A_h is complex (nonzero phase).

Six fixtures validate the fix: old formula FAILs on nonzero-phase; new formula PASSes all with closure_rel < 1e-14.

24 trajectory centre-series closures: all PASS with closure_rel < 1e-13. The bin-161 content IS the coherent 400Hz harmonic (with ~1% off-bin leakage). The v076 claim "bin161 is not a coherent harmonic" is definitively retracted — the v076 QR was correct after all (the v077 "990×" claim was the v075 offset artefact, not a QR normalisation error).

## 2. Proper odd/even derivatives (270 records, zero render)

270 records from 3 distinct physical states (I(-a), I(0), I(+a)) for each of 3D × 2zf × 3a × 5 rows × 3 cols. Proper definitions: odd_half=(I+−I−)/2, even_increment=(I++I−)/2−I0, I'=(I+−I−)/(2a), I''=(I+−2I0+I−)/a². Reconstruction against original I± (not I0).

## 3. Camera ROI 24 rows + T10 separate

24 holdout camera-ROI rows with correct 41×41 semantics: Itot_camera_relL2, Itot_finegrid_relL2 (separate), contrast_roi_relL2, Ccenter, Sarea_nm2 direct/interp/signed/abs. T10 (39nm offset) in a separate file.

## 4. Exposure: 400Hz sinc reference

All 8 rows use sinc(400×τ) as the pure-sine reference. M200: rel_change −0.09% to −0.86%. M400: near-zero baseline, absolute values reported rather than misleading percentages.

## 5. Identifiability: 276 pairs from corrected maps

All 276 pairs from the v076 corrected C400 maps. Pairwise symmetric normalised distances. Severe aliasing confirmed (changing trajectory type gives relL2≈1.0).

## 6. P0

NOT_RUN_RESOURCE_GATED. Gate OPEN at 2.58848e-7 vs 1e-10.

## Not claimed

No experimental validation, no calibration, no diameter, no magnetic attribution, no BEM (0), no renders (0), no threshold changes.
