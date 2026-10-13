# v075 review summary (Codex execution report)

## 1. Anchor-key collision: reproduced, fixed, consequences quantified

- Deterministic reproduction on the workstation: `matlab.lang.makeValidName('D60_zf450_x-10') == matlab.lang.makeValidName('D60_zf450_x+10')` (both `'D60_zf450_x_10'`). The v074 in-memory anchor struct therefore held only 18 of 30 states, with negative-x anchors overwritten by positive-x values.
- Fix: `position_key(D,zf,dx)` with explicit sign letter and pm-integer magnitude (`D60_ZF450_XM10000` / `XP10000`); uniqueness asserted over all 30 states.
- All 30 anchor states were recovered WITHOUT any new render: the on-disk v074 render-cache filenames always carried the sign correctly; only the in-memory keys collided.

## 2. Holdouts re-verified: 24/24 PASS under the original 0.001 gate

24 non-BEM direct holdout renders (the authorised budget), interpolation re-run with fixed keys: relEs = 8.749e-4 .. 8.833e-4, sign-symmetric to <1e-7, all six (D,zf) groups PASS. The v074 negative-side FAILs (0.069-0.207) are thereby attributed entirely to the key collision; the underlying interpolation is well inside the gate on both sides.

## 3. 8-ROI spectra re-exported under the exact 6-neighbour contract (zero render)

Using only the saved v074 A_k maps: BACKGROUND/EDGE ROIs Rlocal median = 1.000 (flat background), CENTER = 1.198, HOTSPOT1 = 1.511 (50.3% of pixels >1.5), HOTSPOT2/3 = 0.96/0.99. The v074 11-neighbour statistic was contaminated by including bins 165:169; the corrected table supersedes it (original preserved in v074).

## 4. Dynamic response recomputed with fixed keys (32 evaluations, zero new renders)

- M400 (prescribed 400 Hz lateral motion): first-order response dominates, absC400_center from 6.4e-5 (D30, a=5nm) to 5.24e-2 (D100/zf450, a=20nm); centre-pixel scaling ratio 3.96 per 4x amplitude (linear, as expected for the first order).
- M200 (prescribed 200 Hz motion): the 400 Hz second harmonic scales superlinearly (ratio 8.86 for 4x amplitude - between a^2 and a^4, higher-order terms present), absC400_center 3.95e-6 to 5.83e-3.
- M400 > M200 at equal amplitude in every state; D100 > D60 > D30.
- Exposure variants (SYNTHETIC tau=0.1/0.2ms): |C400| changes only -0.06%..-0.86% (tau << the 2.5ms modulation period).
- Negative controls: |C400| = 0.049487/0.098971 for depths 0.05/0.10; computed/naive = 0.98974 matches the Dirichlet off-bin leakage band (delta = 0.08 bins, mirror-term interference). A uniform intensity modulation alone produces the 400 Hz peak.
- FFT vs explicit-DFT spot checks: rel <= 2.3e-6.

## 5. Independent session recheck: 0 FAIL (9/9)

Second MATLAB session, saved arrays only: holdout crop relEs < 1e-3 (both signs), map absCenter consistency, M400 > M200 ordering, M200 superlinear / M400 linear scaling, NEG leakage band.

## 6. Preserved v074 verdicts and frozen states

v074 status entries preserved verbatim: ROI_SCHEMA_FAIL, C1_SENTINEL_PARTIAL, HOLDOUT_12_PASS_12_FAIL, DYNAMIC_DEVELOPMENT_INVALID_KEY_COLLISION. Frozen states unchanged: calibration_valid=false, experimental_validation=false, detection_validated=false, single_particle_diameter=NOT_ESTIMATED. P0 NOT_RUN_RESOURCE_GATED; gate OPEN (2.58848e-7 vs 1e-10); rule7 authorisation 0; new BEM 0.
