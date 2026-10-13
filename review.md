# v076 review summary (Codex execution report)

## 1. Centre-mapping defect: confirmed, corrected, proven

- Verified from a real rendered state: fine_x(163)=0, fine step 13nm; the physical pixel block 13:53 maps to fine 61:265 (centre 163). The v075 dynamic ROI used fine 64:268 (centre 166 = +39nm offset).
- The pixel_mean aggregation path reproduces render_system's contrast exactly: C(33,33) diff = 0, full 41x41 block diff = 0; the (Isca+Iint)/Iref decomposition identity holds to 6.9e-17.
- Negative test: the legacy 64:268 block differs from the correct block by 0.15 contrast units and is rejected as an identity match.

## 2. Holdout camera-ROI postprocessing (zero renders)

All 24 cached holdout states re-postprocessed at the correct centre: Itot ROI relL2 (interp vs direct) 1.6e-4..1.9e-4; C33 direct/interp consistent; S_area_nm2 diffs reported. The v075 holdout FIELD gate (0.001) is unaffected.

## 3. Dynamic response recomputed at the correct centre (32 evaluations, zero renders)

- M400 (prescribed 400Hz lateral motion): centre |C400| collapses to 1.0e-9..5.9e-6 - the v075 values (6.4e-5..5.24e-2) were pure 39nm-offset artefacts. Mirror symmetry at the physical centre is confirmed: a pure 400Hz oscillation of a mirror-symmetric particle produces no first-order 400Hz intensity modulation at the centre pixel.
- M200 (prescribed 200Hz motion): the 400Hz second harmonic PERSISTS at the corrected centre (2.7e-6..6.6e-3) - now sampled at the true curvature.
- ROI norms essentially unchanged (offset-insensitive integral quantity).
- FFT vs explicit-DFT spot checks <= 2.3e-6.

## 4. Harmonic authenticity: bin-161 content is NOT a coherent 400Hz harmonic

- Closed-form two-term complex G_N references (including mirror terms) match explicit DFT to abs err 1e-16..2.3e-18 on three analytic fixtures (200Hz-only, 400Hz-only, mixed).
- FIX1 (200Hz-only): bin-161 leakage = 8.05e-6 even though the true 400Hz harmonic is strictly zero - finite-window leakage quantified.
- QR decomposition of the CORRECT centre-pixel series: the coherent 400Hz harmonic is 2.7e-9..5.7e-8 while the raw bin-161 value is 2.7e-6..6.6e-3 (ratio ~990..115660). The bin-161 energy at the centre is dominated by non-coherent content (200Hz-window/interpolation artefacts), NOT a clean 2f optical harmonic. Label: ODD_EVEN_MODEL_SENSITIVITY / INDETERMINATE.
- Odd/even finite differences at the physical centre (I(-5), I(0), I(+5) from holdout renders): the response is EVEN-dominated (odd component ~0). The I''(0)-driven pathway explains why M200 generates a 400Hz component while M400 does not (at the centre). The v075 "M200 a^2-dominated / M400 first-order" claims are retracted and replaced by these measured decompositions.
- Negative controls: computed/naive = 0.98974 matches the Dirichlet off-bin leakage; the acceptance is now against the exact two-term reference (abs < 1e-7 / rel < 1e-5 achieved via the G_N formula to ~1e-13).

## 5. Identifiability screening (16 pairs)

Pairwise complex relL2 between the 24 corrected C400 maps: changing the trajectory type at D100 a=20 gives relL2 ~1.0 (completely different maps); zf changes give ~0.49-10.7. Severe aliasing across the discrete parameter set; no diameter, no calibration.

## 6. P0 / inputs

P0 NOT_RUN_RESOURCE_GATED (license-seat exhaustion pattern persisted; historical sessions untouched). Gate OPEN at 2.58848e-7 vs 1e-10. 520nm remains the only user-confirmed experimental input; v076_roi_spectrum_recheck covers the 8-ROI 6-neighbour re-export cross-check (unchanged from v075, no BMP re-read).

## Not claimed

No experimental validation, no calibration, no diameter, no magnetic causal attribution, no new BEM (0), no threshold changes, no new ROI selection.
