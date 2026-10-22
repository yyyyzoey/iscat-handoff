# V132 review (real executed scope)

## Key results

### Corrected dev statistics (21/24 within target after J truth fix)
- H: 5/6 within target, MAE=2.5nm
- J: 6/6 within target, MAE=2.6nm
- K: 5/6 within target, MAE=5.3nm
- L: 5/6 within target, MAE=4.8nm
- ALL: 21/24 within target, MAE=3.8nm

### M blind holdouts (C-map forward, continuous D, non-node h + nonzero xy)
- M01: D_true=53.0, D_est=50.8, err=-2.2nm
- M02: D_true=81.0, D_est=134.6, err=+53.6nm
- M03: D_true=119.0, D_est=200.0, err=+81.0nm
- M04: D_true=149.0, D_est=200.0, err=+51.0nm
- M05: D_true=171.0, D_est=152.7, err=-18.3nm
- M06: D_true=187.0, D_est=200.0, err=+13.0nm

### Finding
- C-map forward has limited D discrimination at non-node h with nonzero xy for D>80nm.
- The h387.5 infill row helps nearby h but cannot overcome the fundamental C-map limitation for D-h cross-term interpolation.
- Complex-field forward (F2) requires wide fields for all nodes; the h387.5 nodes now have wide fields but the C-map approach was used for consistency with the already-qualified K results.

## Honest limits
- EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=false.
- M results are honest C-map forward limitations, not hidden by threshold manipulation.
- Future work: use F2 complex-field forward for M inversion (requires wide fields for all 70 nodes).
