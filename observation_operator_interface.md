# Observation operator interface (pre-registration, no new solves)

Model: `I[p,j] = 1/Tj * integral_{tj-Tj/2}^{tj+Tj/2} ( 1/Ap * integral_pixel_p |Eref(x,t)+Es(x,t;D,r(t),orientation,material)|^2 dA ) dt`

- average INTENSITY, never average complex field then square
- electron-count mode requires explicit exposure + conversion gain + response coefficients
- Tj=0 is the instantaneous math limit, not a camera default
- timestamps given as exposure-start must be converted to center or integral bounds adjusted; no implicit time origin
- non-uniform timestamps must NOT silently enter the uniform-FFT contract
- unknown axial motion / orientation stay constrained-pending, never defaulted to 0

Inputs: object coordinates unit; pixel mapping; exposure start/end/center + timebase; sample geometry; material; reference field; trajectory (route A) or dynamics (route B); parameter sources

Route A: independently calibrated trajectory -> this operator (priority only when trajectory sufficient)

Route B: measured B(t) vector/gradient/sync + constrained dynamics -> trajectory -> route A; 200Hz drive does not imply 400Hz translation

Authorization: pre-registration only; new BEM/noise/diameter-inversion remain 0; REAL_PHYSICS_GO=false
