# V133 review

V133 F2 M recovery: ALL 6/6 within target.
- M01: D_true=53, D_est=48.4, err=-4.6nm
- M02: D_true=81, D_est=81.3, err=+0.3nm
- M03: D_true=119, D_est=122.1, err=+3.1nm
- M04: D_true=149, D_est=151.1, err=+2.1nm
- M05: D_true=171, D_est=167.8, err=-3.2nm
- M06: D_true=187, D_est=190.3, err=+3.3nm
- MAE=2.8nm
- V132 C-map MAE=36.5nm -> F2 fix MAE=2.8nm (improvement)
- Root cause: V129 np.empty_like + V132 C-map substitution
- EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=false
