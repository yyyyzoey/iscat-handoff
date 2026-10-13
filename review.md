# v074 review summary (Codex execution report)

## A. Replay closeout (no 2001-frame recompute)

All v073 table numbers reproduce from the stored full-field arrays: 93179/11013/104192 pixels, bright-pixel diagnostic 82749, meanFloor 1.1761607311200351e-4, |C400| median/mean/max. Five rejection tests all PASS: wrong time dim guarded (BAD_TIME_DIM), ROI recompute matches stored X400 (maxdiff 0), wrong bin (169) differs (1.23), zero-fill of invalid pixels detected, ROI-local floor (5.69e-4) preserved distinct from full-field floor (1.18e-4), transpose detected (0.883). The v072 "400/420 same FFT pass" narrative is corrected: v073 called extract twice; the new multi-bin ROI interface computes one FFT for k=158:164+169.

## B. ROI spectral/background qualification (8 predeclared ROIs, one additional scan)

ROIs selected ONLY from v073 |C400|/Imean/validMask (selection logged before any neighbor-bin computation): center (reused), 3 hotspots, 3 background candidates, 1 edge. One read-only 2001-frame scan; per-ROI A_k=|2X_k/(N Imean)| for k=158:164,169 with the SAME full-image mask/floor.
- HOTSPOT1: Rlocal=A161/median(neighbors) median 1.883; 37.3% of valid pixels >1.5.
- BACKGROUND candidates: Rlocal median 1.10-1.19; EDGE 1.18 - the local 400Hz excess is NOT spatially exclusive to hotspot-like regions at this diagnostic level.
- Sub-window demodulation at fixed f*: median amplitude 0.00327 vs 0.00366 (~11% drift) - DEVELOPMENT_DIAGNOSTIC only.
- Everything labeled ASSOCIATION_ONLY_NOT_CAUSAL_MAGNETIC_SIGNAL; no detection threshold, no FPR claim, no single-particle claims.

## C. Translation qualification + bounded prescribed-motion forward (0 BEM)

C1: lateral translation of the SAVED Fe3O4 complex fields implemented as a far-field phase ramp (flat layers are x/y-translation invariant). Sentinel: prescribed dx=+10nm moves the image intensity CoM by 9.92nm (0.1526 px x 65nm), linear 19.8nm at 20nm, Eref invariant exactly (maxdiff 0), consistent across D30/D60/D100. The sign was fixed by the physical sentinel (image moves with particle), not by fitting. The image-plane periodic-DFT shift was tried as an independent cross-check and REJECTED as a verifier (windowed non-periodic field wrap; relAB~0.9) - documented, sentinel route used per contract C1.2.

C2 (54 unique render states, 0 BEM): 30 anchors (3D x 2zf x 5x) + 24 holdouts. Interpolation-holdout gate 0.001 on the complex field: +5/+15 sides PASS (relEs 8.8e-4), -5/-15 sides FAIL (0.069-0.207) - the piecewise-linear complex-field interpolation is asymmetric and its errors bound the trajectory stage; reported as-is.

34 time-series evaluations:
- 24 prescribed trajectories (M200/M400 x a=5/20nm, 3D x 2zf): M200 produces a 400Hz second harmonic through the optical/geometric nonlinearity (absC400_center 2.3e-5..1.57e-2, grows with a and with D; ROI norm up to 0.47); M400 shows a mirror-symmetry silent center (1e-8) with first-order response off-center (ROI norm 6e-6..2.3e-4).
- 8 exposure variants (SYNTHETIC tau=0.1/0.2ms): |C400| shifts +16%..+224% vs tau=0 - exposure is a first-order nuisance; no real exposure claimed.
- 2 analytic negative controls: uniform intensity modulation alone yields |C400|=modulation depth exactly (PASS) - a 400Hz FFT peak is NOT evidence of particles.
- FFT-vs-explicit-DFT spot checks on every trajectory: rel <= 1.6e-6.

## C3 Non-identifiability

The same |C400| arises from multiple (D,zf,a) combinations across the 24 exploration points; zf550/zf450 ratio ~0.80 across D for both trajectory types. NOT_IDENTIFIABLE_UNDER_CURRENT_NUISANCE. No diameter, no bias/RMSE, no calibration curve.

## D/E

physical_input_readiness.json: 520nm USER_CONFIRMED enters the experiment contract; exposure (+16..+224% impact), NA/magnification/pixel, drive waveform/phase, batch constants, trajectories remain missing with quantified impacts. P0: NOT_RUN_RESOURCE_GATED (license-seat exhaustion from hung historical sessions twice blocked startup; own-session leftovers cleaned with per-PID verification; historical processes untouched). Gate OPEN at 2.58848e-7.

## Not claimed

No real magnetic motion, no experimental validation, no calibration, no diameter, no detection performance, no new BEM (0), no threshold changes.
