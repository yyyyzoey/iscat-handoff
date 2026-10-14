# v081 review summary

## 1. Design matrix rank deficiency: reproduced and fixed

v078 harmonic design matrix had column-index collision: `Bm(:,2+2*(h-1)-1)` placed cos(200Hz) at column 1 (overwriting intercept) for h=1, leaving column 9 as zeros. Old: rank=8. Correct: rank=9, cond=1.41.

## 2. 24/24 trajectories PASS (computed in Python)

All 24 prescribed trajectories recomputed with correct full-rank QR:
- M200: bin161/C400_fit ratio ~5 (expected N·Im/2 for D60, higher for D100)
- M400: centre near-zero by mirror symmetry confirmed
- Per-harmonic DFT contributions with correct conjugate mirror terms
- Complex closure verified for all 24

## 3. Inherited results

270 odd/even, 24 camera ROI, 276 pairs — all inherited from v078.
