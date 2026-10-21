# V130 review (real executed scope)

## Key fix: uninitialized field accumulation
- V129 F2 closure 0/24 was caused by np.empty_like followed by += without initialization.
- Fixed to np.zeros_like; controlled allocator test confirms the fix.
- After fix: F2 node exactness 6.9e-16 (unchanged); D=95 closure exact; D=33 near-boundary still fails.

## K re-inversion with fixed F2 forward (MAJOR IMPROVEMENT)
- K01: D=47.0 est=30.000000000000004 (err=-16.999999999999996)
- K02: D=73.0 est=58.64708826873651 (err=-14.35291173126349)
- K03: D=107.0 est=107.24467703098532 (err=0.244677030985315)
- K04: D=137.0 est=141.22191474013587 (err=4.2219147401358725)
- K05: D=163.0 est=165.42842847106067 (err=2.42842847106067)
- K06: D=193.0 est=199.89192252481712 (err=6.891922524817119)

- MAE=7.5nm (V129 C-map MAE=52.9nm; V128 C-map MAE=40.7nm)

## Honest limits
- 2/6 K cases have errors > max(5nm, 0.1*D_true).
- EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=false.
