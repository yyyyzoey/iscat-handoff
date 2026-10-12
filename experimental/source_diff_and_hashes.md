# Source identity and diff notes (v072)

## Byte identities (SHA-256, computed from actual file bytes on this workstation)

| file | sha256 | bytes | encoding |
|---|---|---|---|
| `C:\Users\PC\Desktop\课题\test.m` | `fdc918e691b13b33cbae8b32ecaacd1e63ec27be3e23b61b0701d0e595aea684` | 12967 | GBK |
| `C:\Users\PC\Downloads\test_with_contrast.m` | `d08575b1e860e09f29c74652442a77b721039c6e32368fe76d2c5c63143ea3aa` | 17580 | GBK |
| repo `Fe3O4_Querry.yml` | `c42e5a5007827fb3548df61daf222b164a7799206790fb2116c8488aefe9e802` | (verified) | ASCII/YAML |

Git blob SHA1 values (e.g. `37cd83a1ad859b18ddb8c6a515c29df78b2d95cb`) are NOT SHA-256 and were not used as byte identities.

## Observable differences (from source reading, both read-only; originals not modified)

1. `test.m` (420 Hz): per-pixel temporal mean removed; FFT along time; nearest bin to 420 Hz (k=169, 419.790104947526 Hz at N=2001/Fs=5000); single-sided amplitude `2|X|/N`; phase `angle(X)`; NO background division; NO low-intensity mask. Output scale = `im2single` gray-level amplitude.
2. `test_with_contrast.m` (400 Hz): same FFT core; keeps `timeMean`; `meanFloor = 0.01 * median(positive finite timeMean)`; `validContrastMask = isfinite(timeMean) & timeMean > meanFloor`; normalized complex contrast `C_f = 2*X_k/(N*timeMean)` inside mask (scale 1 for DC/Nyquist); saves `normalizedComplexContrast/normalizedAmplitudeContrast/normalizedPhaseContrast/validContrastMask/meanFloor/...`; folderPath correctly points at the 7.29 BMP folder.
3. The two outputs are NOT the same observable: chain A is a gray-level FFT amplitude; chain B is a normalized modulation contrast. A calibration multiplier between them is NOT established.
4. Historical FFT outputs used 399.8001 Hz (= bin 160 at N=2001/Fs=5000), proving a 400 Hz processing history; the current `test.m` says 420. `FREQ_VERSION_CONFLICT_PENDING_USER_CONFIRM`.
5. Neither script has been declared by the user as the current formal extractor; replay was executed for both chains on the identical 2001-frame input with independent output labels (`numeric/replay_729_frames1000_3000.mat`, workstation-only).
