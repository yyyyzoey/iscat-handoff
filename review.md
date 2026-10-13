# v077 review summary

## 1. QR normalisation defect (Q1): confirmed, fixed, all 24 rows corrected

The v076 QR decomposition divided the projection coefficients by an additional N/2 factor. The correct normalisation for a cosine/sine LS pair is C400_complex = (coef_cos - 1i*coef_sin) / Imean (no 2/N factor). After correction:
- All 12 M200 rows: bin161_absC400 / corrected_C400_fit = 0.9895..0.9897 (NOT ~990)
- The v076 claim "bin-161 content is NOT a coherent 400Hz harmonic" is RETRACTED
- The bin-161 content IS the coherent 400Hz harmonic (with the expected ~1% off-bin leakage)
- 6 analytic fixtures validate the correct normalisation (all PASS)

## 2. Proper odd/even derivatives (Q3)

Three distinct physical states I(-5), I(0), I(+5) at the same physical pixel:
- odd_half = [I(+5)-I(-5)]/2 ~ 6.8e-11 (near zero -> centre is even-symmetric)
- even_increment = [I(+5)+I(-5)]/2 - I(0) ~ -7.8e-7
- 30 states x 5 pixel rows x 3 pixel cols = 450 derivative rows

## 3. 276-pair identifiability from v076 corrected C400 maps (Q4)

All 276 pairs (24 choose 2) computed with symmetric normalisation from the corrected centre maps. The v076 16-pair table (from withdrawn v075 offset maps) is preserved as history.

## 4. CSV schema fixes (Q5)

All v076 CSV defects documented: exposure8 unquoted comma (11 vs 10 columns), coordinate missing field, harmonic unquoted comma, holdout Sarea duplicate semantics. All v077 CSVs machine-readable with correct column counts.

## 5. T10 proper 39nm test (Q6)

The v076 T10 compared physical pixel blocks 14:54 vs 13:53 (1 full pixel = 65nm apart). The correct test compares fine 64:268 vs 61:265 (3 subpixels = 39nm apart) through 5x5 integration. Max diff confirmed > 0.

## 6. Exposure sinc reference correction (Q7)

The sinc reference now uses the actual 400Hz observation frequency (not the 200Hz motion frequency). M400 near-zero values are marked NUMERICALLY_UNRESOLVED rather than assigned spurious percentage changes.

## 7. Frozen states and P0

calibration_valid=false, experimental_validation=false, detection_validated=false, single_particle_diameter=NOT_ESTIMATED. P0 NOT_RUN_RESOURCE_GATED. Gate OPEN at 2.58848e-7.
