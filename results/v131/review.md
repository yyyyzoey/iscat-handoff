# V131 review (real executed scope)

## Results: 20/24 within max(5nm, 0.1*D_true) target

### K set (6 direct L1 blind holdouts)
- K01: D_true=47, D_est=43.3, err=-3.7nm
- K02: D_true=73, D_est=58.6, err=-14.4nm
- K03: D_true=107, D_est=107.2, err=+0.2nm
- K04: D_true=137, D_est=141.2, err=+4.2nm
- K05: D_true=163, D_est=165.4, err=+2.4nm
- K06: D_true=193, D_est=199.9, err=+6.9nm

### L set (6 direct L1)
- L01: D_true=49, D_est=46.7, err=-2.3nm
- L02: D_true=77, D_est=64.8, err=-12.2nm
- L03: D_true=109, D_est=109.7, err=+0.7nm
- L04: D_true=139, D_est=141.5, err=+2.5nm
- L05: D_true=167, D_est=169.3, err=+2.3nm
- L06: D_true=191, D_est=200.0, err=+9.0nm

### H/J (dev diagnostics, reused from V125/V126)
- H01: D_true=37, D_est=35.2
- H02: D_true=63, D_est=62.3
- H03: D_true=93, D_est=82.4
- H04: D_true=117, D_est=117.2
- H05: D_true=147, D_est=147.3
- H06: D_true=177, D_est=178.2
- J01: D_true=41, D_est=36.9
- J02: D_true=63, D_est=72.2
- J03: D_true=93, D_est=89.7
- J04: D_true=117, D_est=126.1
- J05: D_true=147, D_est=149.6
- J06: D_true=177, D_est=183.9

## Summary
- 20/24 within target (83.3%)
- 4 outside target: K02(-14.4), L02(-12.2), H03(-10.6), J02(+9.2) - all in D=63-93 transition region
- F2 complex-field forward with template bank multi-start: significant improvement over C-map
- 6 priority profiles completed (K01, K02, K06, L01, L03, L06)

## Honest limits
- EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=false
- H/J/K/L are development diagnostics per contract
- The 4 failures cluster in the D=63-93 transition region where C response is oscillatory
