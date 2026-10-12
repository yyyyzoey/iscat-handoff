# v072 wrong-axis source and result status (frozen record)

## The bug (confirmed from locked v072 source `source/run_v072_replay.m` @ e1abfed)

```matlab
stack = zeros(H,W,N,'single');   % 3-D: H x W x TIME
timeMean = mean(stack,3);
signal = stack - timeMean;
fftR = fft(signal,[],4);         % BUG: dim 4 has length 1 -> MATLAB returns input UNCHANGED
X420 = fftR(:,:,k420);           % actually time-domain frame 169
X400 = fftR(:,:,k400);           % actually time-domain frame 161
```

MathWorks `fft(X,[],dim)`: if dim > ndims(X), X is returned unchanged. The v072 replay
therefore never transformed along time.

## Consequences

- `chainA_amp420 min/max/mean` and chainB `|C_f| min/max/mean` in v072
  `tables/fft_replay_one_case.csv` are INVALID as frequency observables (INVALID_FFT_AXIS).
- `meanFloor`, `validMask fraction (89.43%)`, frame ordering/reading and BMP metadata
  remain independently reproducible and were re-confirmed by v073.
- Wrong artifact isolated, not overwritten: v072_return/numeric/replay_729_frames1000_3000.mat
  sha256 d7ffe435e44e85744e59a29ea761e26e0229d4c74461f3ef94736f776281bc7f.

## v073 correction

- extract_fft_v073.m hard guard: timeDim > ndims(stack) -> error.
- Corrected replay uses source-script 4-D layout H x W x 1 x N with fft(...,4).
- Verification: 3D/4D equivalence, analytic bin recovery, 12 predeclared pixels direct-DFT
  cross-check (rel <= 3.7e-7), independent-session small-ROI recheck (PASS).
