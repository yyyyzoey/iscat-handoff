# V124 review (real executed scope)

## Forward qualification
- Engine: NANOBEM stratified BEM (pinned ce49f77f096337db8be54c46d83696d37b0b23d5) via build_system/render_system; vector imaging chain unchanged.
- Gates: validation/zero_index_and_units.csv. Exact n-match peak|C| = 7.5e-6 (pre-registered 1e-10 ideal NOT met; reported as measured, no relaxation). Two-sided detune 1e-4 gives ~1.0e-4 (13.6x the exact-match residual): scattering converges to zero as np->nwater.
- Python replay of Er/Es -> 5x5 pixel integration -> I -> C: identity error 0.0, C replay exact.
- Mesh 576 vs 1444 relL2(C) = 0.0045 (target <=2%); q5 vs q7 relL2 = 0.0032.
- Independent Mie (Python + MATLAB implementations) vs Rayleigh limit, D=10/15/20nm: agreement documented in gate CSV.
- Lateral-interpolation forward model validated against real shifted-grid renders: max|dC| = 0.004126 at 28nm shift (0.5 fine pixel), 0.01969 at 140nm (worst case, documented limitation).

## Real outputs
- 60 BEM solves / 66 renders: 3 sentinels + D100 sample + mesh reference + 17 train D + 6 holdout D + 32 height points (+5 camera-variant renders, +2 shift-validation renders, 1 exact-identity cache reuse).
- Fixed-h450 18-point D curve, signed 2D iPSFs for all cases, full Er/Es fields in HDF5.
- Clean independent holdout D=[35,55,85,115,145,185]: median |error| = 0.50 nm, all single-minimum, none rejected/boundary.
- D100 height response 200:25:1000 nm from real sphere-interface BEM coupling (oscillatory, period ~ lambda/2n ~ 195nm; NOT a sin(2kh) fit).
- Static noise: raw-residual rejection fires at all backgrounds because the photon-noise floor exceeds the pre-registered clean-observation threshold (0.10); residual_at_truth column quantifies the floor. D estimates remain accurate: mean/max|error| = -1.47/26.50 nm at 1e4 e-/pix.
- Height LOO (D100): median |error| = 200 nm, 12/33 rejected - single-frame height is weakly identified (oscillatory degeneracy), reported honestly.
- Motion (per-frame centroid recentering, 12 trajectories x 8 frames): T=25us mean D_hat = 101.96 nm (spread 13.0 nm); T=100us mean D_hat = 99.42 nm (spread 8.0 nm); photon counts scaled with exposure (1e4 vs 2.5e3 e-/pix).

## Not done / blocked (honest)
- Full 18x33x3 fast D-h library and 2D joint D-h grid: BLOCKED_BUDGET on the BEM path (each (D,h) is an independent solve); the 64-solve pool was allocated per contract W3 fallback. Joint D-h ambiguity diagnostics are provided from the two 1D libraries.
- Fast (Mie+interface) backend: not attempted; bounded BEM satisfied the budget directly (60/64).
- Experimental absolute diameter: NOT validated (EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=false).

## Rejected history
- tools/v123_physics.py preserved unmodified (blob 31aa970435d4a7a8c21c67dd2a29b0f1807b200b); its scalar C(D,h) is NOT used anywhere in V124.
