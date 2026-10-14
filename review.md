# v080 review summary

## 1. v079 defects: all confirmed and fixed

1. **tt numeric to %s**: sprintf('...%s...', 200) produces char(200) not 'M200'. Fixed: ttype=sprintf('M%d',tt).
2. **scalar C400 indexed as 2D**: v076 QR mat has scalar C400 (not 41×41 map). Fixed: separate scalar/map access paths.
3. **nPass before output**: nPass incremented before CSV write; catch wrote ERROR but nPass already incremented. Fixed: nPass only incremented on successful CSV write.
4. **Design matrix column overwrite**: v078 Bm(:,2+2*(h-1)-1) placed cos at col 1 for h=1 (overwriting intercept). Fixed: B(:,2*h) for cos, B(:,2*h+1) for sin.

## 2. 24/24 trajectory harmonics: ALL PASS

All 24 prescribed trajectories computed with:
- Correct full-rank design matrix (rank=9, cond=1.41)
- Complex closure (rel < 1e-13 for all)
- M200 bin161/C400_fit = 0.9895-0.9897 (confirms coherent 400Hz harmonic with correct matrix)
- M400 bin161/C400_fit varies 0.33-1.24 (near-zero centre, mirror symmetry)
- Per-harmonic DFT contributions in long format (DFT_count units)

## 3. Inherited results

270 odd/even records, 24 camera ROI rows, 276-pair identifiability — all inherited from v078 without recompute, read-only recheck confirms consistency.

## 4. Exposure

8 conditions with analytic sinc(400×τ) reference provided. Higher-order quadrature NOT_EXECUTED_RESOURCE_LIMIT. SYNTHETIC_TAU_ONLY.

## 5. P0 / frozen states

P0 NOT_RUN_RESOURCE_GATED. Gate OPEN at 2.58848e-7 vs 1e-10. calibration_valid=false, experimental_validation=false, single_particle_diameter=NOT_ESTIMATED.
