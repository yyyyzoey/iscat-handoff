# v072 review summary (Codex execution report)

## A. Freeze, reconcile, correct (zero BEM)

- All 24 v071 executable sides re-verified by frozen keys (case/D/zf/suffix/mesh/lens dims/far dirs/ntab/q/SHA-256/shape/finite/identity fields). `tables/controlled_ledger_reconciled.csv` lists v071 events, the 12 NOT_EXECUTABLE sides, the probe, and the 24 v070 history rows (arrays never persisted).
- The v071 `evi.sol_sha256` field is renamed in documentation to what it actually is: the SHA-256 of the saved system file `s` (not a BEM `sol`). No sol exists on the workstation; `P_common`/`F_angle` are formally `NOT_EXECUTABLE_UNDER_ZERO_BEM_BUDGET` and no interpolation was used.
- K01 wrapper lineage: `render_system` SHA-256 (`87ef0db0...`) constant across every render; the wrapper edits between v071 runs changed only evidence fields/CSV writing, never the render switch or cfg overrides. No K01 re-render was needed (0 of 4 authorized used).
- Semantics fixed without touching originals: `controlled_comparisons_semantics_fixed.csv` now carries `deltaS_signed`, `deltaS_abs`, `S_ref_sumC`, `S_area_nm2_A/B` (4225 x sumC), `K2_ref`, `chi1_ref`; the misleading `abs_dS` column is retired (the old column held signed dS).
- Cross-check: v071 K03/K06 P_base/F_base scalars reproduce the v068 frozen-pipeline scalars EXACTLY (rel_diff = 0), a strong bit-level provenance link across versions.
- K05 D100/zf437.5 fine-side signed-area sensitivity confirmed as a finite-numerical fact: scalar |Delta|/|S| ~ 7.35% while whole-image rF ~ 8.2e-6 (near-cancellation regime), not an experimental diameter error.

## B. Two real extractor scripts - both now byte-verified (top priority item)

| | test.m | test_with_contrast.m |
|---|---|---|
| sha256 | fdc918e6...95aea684 | d08575b1...3ea3aa |
| target | 420 Hz (bin 169 -> 419.790105 Hz) | 400 Hz (bin 161 -> 399.800100 Hz) |
| observable | gray-level FFT amplitude `2|X|/N` + phase | normalized complex modulation contrast `2X/(N*Imean)` with 1%-median floor mask |
| folderPath | points at a single .bmp (stale/bug) | correct 7.29 folder |

12 analytic fixtures (constant bg, exact-bin 400/420 with known amp/phase, off-bin leakage, two-tone, time-origin shift, zero bg, low-Imean mask, RGB weights, NaN behavior, exposure sinc) ALL PASS against an independent direct-DFT reference. Declared tolerances: abs 1e-7, rel 1e-5, phase 1e-4 rad (single precision, N=2001). Bin audit table confirms the historical 399.8001 Hz outputs correspond to a 400 Hz target at N=2001/Fs=5000. `FREQ_VERSION_CONFLICT_PENDING_USER_CONFIRM` is recorded; neither script is auto-promoted to "the" formal extractor.

## C. Real data replay (one group, both chains)

The 7.29 batch EXISTS on this workstation: 5000 BMPs, 352x296, 8-bit gray, timestamp delta 200 us (5000 fps). Frames 1000-3000 (N=2001) were replayed through both chains on the identical input:
- chain A (420): amplitude range 0..3.48e-05 gray units; actualFreq 419.790105 Hz
- chain B (400): meanFloor 1.17616e-4, valid mask 89.43%, |C_f| range 0..0.0615; actualFreq 399.800100 Hz
Full arrays remain on the workstation (`numeric/replay_729_frames1000_3000.mat`); only the summary CSV is published. Display-only single-frequency BMP reconstruction was skipped (would write 2001 files; not part of the measurement observable). `calibration_valid=false`, `experimental_validation=false`.

## D. Static identifiability screening (cached tables only)

- D60 C_center zero-crossing between zf 500-525 (v067 refined: 512.5-515). D100 S_area sign change between 425-450 (v071: +143.4 at 435 -> -36.7 at 437.5).
- D-ordering is focus-dependent and NON-monotonic: zf<=475 both scalars order 100>30>60; from zf~475/500 the signed-area ordering flips to 30>100>60; C_center is monotone in D only for zf>=500.
- Consequence (screening only): within this demo optics no single static scalar uniquely identifies D across the focus range; a focus prior or axial-motion model is required. Static focus sweeps are not particle axial motion.

## E. P0 / R6 / A3

P0 hook NOT_RUN (budget preserved; hung -batch MATLAB sessions remain on the workstation). The 1e-10 blocked/unblocked gate stays OPEN at the historical 2.58848e-7. rule7 large reference authorization 0. R6/A3 BLOCKED (no pre-authorized budget).

## Not claimed

- No experimental validation, no calibration, no diameter measurement, no "36/36 physical closure", no Bessel "proven second-order convergence" beyond the two finite-config increments, no mesh-percentage attribution.
