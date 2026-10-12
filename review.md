# v073 review summary (Codex execution report)

## 1. v072 replay bug: confirmed, corrected, re-verified

The v072 replay built a 3-D `H x W x N` stack but called `fft(signal,[],4)`. MATLAB returns
the input unchanged when dim > ndims, so v072's "frequency" arrays were time-domain frames
161/169. v073 response:

- `extract_fft_v073.m` implements the full contract with a hard axis guard (timeDim>ndims
  -> error), N=2001 assertion, bin/actualFreq assertions, source-script mask semantics,
  and complex-NaN (never zero) for invalid pixels.
- Negative tests: guarded wrong dim caught; unguarded `fft(...,4)` on 3-D shown to return
  the input unchanged (documents the v072 failure mode); correct dim-3 chain recovers the
  analytic coefficient (rel 2.9e-6, phase 2.8e-6 rad).
- 3-D vs 4-D layout equivalence on identical data: maxdiff = 0.

## 2. Coverage gaps from v072 fixtures closed (8 targeted fixtures, <=8 budget)

TIME_ORIGIN (real 500-sample shift: amplitude invariant 9.3e-8, phase rotation matches
-2*pi*k0*n0/N), MASK_VALUE (complex NaN + mask=0), RGB_INDEPENDENT (unequal channels +
independent analytic gray amplitude), EXPOSURE_ANALYTIC_ONLY (start/center conventions,
SYNTHETIC tau), IO_CSV (no control characters; v072 U+0000 closed), OFF_BIN leakage
diagnostic (ratio 0.8758, no correction applied). Original v072 fixture CSV preserved.

## 3. Corrected replay of the SAME 2001 frames (one group, primary = 400 Hz)

- 4-D `H x W x 1 x N` single stack (source-script layout), `fft(...,4)`; actualFreq
  399.800100 Hz (primary) / 419.790105 Hz (control) asserted.
- PRIMARY `normalizedComplexContrast400`: 93179/104192 valid pixels (89.43%, identical to
  v072's independently-valid mask fraction), 11013 invalid pixels stored complex NaN;
  meanFloor 1.1761607311200351e-4 (matches v072 - mean/mask were reproducible); valid-only
  |C400|: median 6.60e-3, mean 2.40e-2, max 0.9019.
- CONTROL 420 Hz amplitude from the same FFT pass; no rescaling to 400.
- 12 predeclared pixels (corners, center, ROI corners, high/low Imean, brightest |C400|):
  direct double-precision DFT vs FFT all PASS (rel <= 3.68e-7; phase <= 3.45e-7 rad).
- Independent second MATLAB session recheck on the saved 41x41 ROI (frames included):
  3D/4D maxdiff 0, stored-vs-recomputed maxdiff 0, 4 corner direct DFTs PASS,
  C_k formula vs stored PASS -> RECHECK PASS.
- Spectral neighborhood (fixed bins k=158:164 + 169): bin 161 ROI-mean|X| = 0.1626 vs
  neighbor baseline 0.125-0.131 (~25% above local baseline). Labeled
  ASSOCIATION_ONLY_NOT_CAUSAL_MAGNETIC_SIGNAL; no detection threshold claimed.
- v072 wrong artifact isolated (sha256 d7ffe435...), never overwritten; full corrected
  arrays workstation-only; small ROI + control small mat packaged.

## 4. Ledger / P0 / gaps

- `controlled_ledger_v073_verified.csv`: 24 sides with REAL cfg D/zf (v072's
  sprintf-in-find bug fixed) and corrected SHA column semantics (render_system vs wrapper);
  12 NOT_EXECUTABLE; v070 rows remain HISTORY_UNVERIFIABLE in the untouched v072-era table.
- P0: passive process/memory inventory only; own-session hung MATLAB leftovers cleaned with
  per-PID command-line verification and on-disk output verification (historical processes
  untouched). Gate stays OPEN at 2.58848e-7 vs 1e-10; rule7 authorization 0.
- Physical input gap: lambda=520 nm USER_CONFIRMED recorded; exposure, NA, magnification,
  object pixel, drive waveform/reference phase, batch constants, trajectories still missing
  -> single-particle diameter NOT_ESTIMATED; calibration_valid=false;
  experimental_validation=false.

## Not claimed

No experimental validation, no diameter estimate, no causal magnetic attribution, no
static-to-400Hz calibration multiplier, no new BEM (0), no renders (0).
