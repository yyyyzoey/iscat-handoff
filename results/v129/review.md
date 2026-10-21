# V129 review (real executed scope)

## Key finding: F2 cubic closure FAILED 0/24
- The not-a-knot tensor cubic spline through 7 D nodes creates severe oscillations.
- MAE of D recovery = 52.9nm, max|e| = 153nm. The optimizer consistently converges to wrong D values.
- This is a REAL limitation: 7-node cubic is insufficient. More D nodes or a different approach is needed.
- Per contract: closure gate must pass before new BEM. It did not, so NO new BEM was run.

## What was completed
- V128 library provenance verified: 70 nodes, D100 h-response correct after rebuild.
- F2 closure run: 0/24 - documented as the primary finding.
- F2 uses physical-axis not-a-knot cubic via make_interp_spline (correctly implemented per contract).
- The failure is not an implementation bug but a fundamental limitation of 7-node cubic interpolation.

## What was NOT completed (blocked by closure failure)
- Old K/L re-inversion with F2 (blocked)
- New M holdout BEM (blocked by closure gate)
- Noise/blanks (blocked - no qualified forward)
- Continuous shared-D multi-frame (blocked)

## V128 results retained
- 6 L direct L1 renders and images preserved
- Noise/blanks from V128 preserved as dev diagnostics

## Budget
- BEM 6/8 (from V128 L01-L06, inherited)
- V129 new BEM: 0 (closure gate blocked)
- Render: 18/96 (from V128, inherited)
- Camera: 0/6000 (V129 new)

## Honest limits
- EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=false.
- The 7-node cubic spline oscillation is a genuine limitation that requires either:
  (a) more D nodes in the training grid, or
  (b) a different interpolation approach (e.g. RBF, Gaussian process), or
  (c) direct BEM evaluation at each query point (prohibitively expensive).
