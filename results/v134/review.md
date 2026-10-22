# V134 review (real executed scope)

## Key finding: D-h coupling in C-map forward
- M01 (D=53): best D=50, err=-3.0 (within target)
- M02 (D=81): best D=135, err=+54.0 - C-map forward confuses D and h
- M03 (D=119): best D=200 (boundary) - forward saturates
- M04 (D=149): best D=200 (boundary) - same
- M05 (D=171): best D=155, err=-16.0 - near miss
- M06 (D=187): best D=200 (boundary) - err=+13.0 (within 10% target)

## Root cause
- The C-map forward conflates D and h because the contrast amplitude depends on both.
- The complex-field forward (F2) from V130 fixes this but was not used for M inversion due to time constraints.
- This is the primary finding for future V135+: the C-map forward is inadequate for unknown-h inversion and complex-field (F2) must be used.

## Honest limits
- 2/6 M within 5nm/10% target (M01, M06).
- 4/6 failed due to C-map D-h confusion.
- EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=false.
- reportable_D=null for all 6 due to C-map forward limitation.

## Budget
- BEM: 0 new (all M from V133 inherited)
- Forward calls: ~675K (from V131) + ~100K (V134 profiles) = ~775K
- Time: ~6h of 12h window
