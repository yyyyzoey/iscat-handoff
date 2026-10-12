# v071 review summary (Codex execution report)

## What this round established

1. **v070 arrays are gone.** `v070_return/` contains only `matlab_run.log`, `compare.log`, `controlled_plan24.csv`, `controlled_results24.csv`. `numeric_inventory.csv` claimed local C arrays exist; that was false. No live MATLAB session holds the `C_*_1..6` base-workspace arrays. The v070 36-value table is plausible but unverifiable from primary data; it is preserved as history, not as validated evidence.

2. **The angle switch never worked.** `cfg.numerics.ntheta/nphi` is consumed only by `build_system` (lens construction); `render_system` ignores it. A K01 probe requesting 200/301 left the lens at 50x51 and far at 2550 directions (`numeric/probe_angle_deadswitch.mat`, INACTIVE_CONTROL). Therefore v070's `F_angle` rows were exact zeros because nothing changed, and v070's `P_common` "common post-processing" only changed the Bessel table (its 3.1e-5 signal matches the fine-side Bessel row).

3. **P_common and F_angle are NOT_EXECUTABLE this round.** Both require recomputing `farfields(sol, dir)` on a new angle grid, but `build_system` sol objects were never saved; only `s` (with far on frozen 50/51 or 100/151 grids) persists in `v065_return/*_s_*.mat`. No new BEM is authorized, so both sides are recorded NOT_EXECUTABLE with reason `SOL_NOT_PERSISTED_AND_CFG_ANGLE_DEAD_SWITCH`. No interpolation was used to fake them.

4. **Approved q7 and Bessel controls were executed correctly** on existing boundary solutions: 24 sides (6 conditions x {P_base, F_base, F_q7, F_bessel}) plus 1 dead-switch probe. Per-side evidence (lens counts, far direction count, ntab, subpixels, sol/far hashes, identity error) is stored in `numeric/side_*.mat` and `controlled_plan24_v071.csv`.

5. **Results (41x41 frozen ROI, full-grid 33 +/- 20):**
   - P_base vs F_base: rF = 0.005409 - 0.006215 (unchanged vs v070, as expected)
   - F_q7 vs F_base: rF = 0.000528 - 0.000711 (nonzero, q7 effective)
   - F_bessel vs F_base: rF = 7.81e-6 - 8.21e-6 (nonzero, ntab effective; ~1/4 of the 2001->4001 increment, consistent with second-order tabulation convergence)
   - Telescope identity |dS|/|S_R| = K2R * rF * eta closes to <= ~2e-16 on every completed row.
   - Attribution limited to: COMMON_POSTPROCESS_RESIDUAL (Bessel side), POSTPROCESS_SENSITIVE (q side), and for the prod-fine gap: INDETERMINATE/MIXED - no "100% mesh" claim is made.

6. **Experimental extractor found.** `C:/Users/PC/Desktop/课题/test.m` implements a per-pixel single-frequency FFT amplitude/phase extractor (Fs=5000, targetFreq=420 Hz, frames 1000-3000, no window, 2|X|/N single-sided normalization, phase=angle(X)). Raw BMP data path in the script points to a single .bmp path and the E: drive folder is absent on this workstation; no prior FFT outputs found; replay blocked. Target frequency 420 Hz conflicts with the historical 399.8001 Hz and needs user confirmation.

7. **Material contract corrected** (active copy `experimental/material_contract_v071.json`): citation year 1985 (CRDC-CR-85034), 520 nm node exactly `2.349+0.083i`. The old v063 contract is preserved unchanged.

## Not done this round (with reasons)

- P0 passive hook: not run (budget preserved; hung -batch MATLAB sessions on workstation). P0 gate remains OPEN at 2.58848e-7 vs 1e-10. rule7 large reference authorization stays 0.
- R6 boundary depth diagnostics, A3 4-seed rebuild: not started (unchanged).
- No new BEM, no new D nodes, no camera/noise batches.

## Verification chain

- Renders executed in a fresh `matlab -batch` session (R2024b), hash-keyed cache in `numeric/`.
- Independent second `matlab -batch` session reloaded only `numeric/*.mat` and recomputed all 36 comparison rows: `controlled_comparisons_recheck_v071.csv` is byte-identical to the original (checkpoint roundtrip PASS).
- Cost ledger: 24 controlled renders + 1 probe = 25 render invocations (<= 24 correction + 12 baseline budget).
