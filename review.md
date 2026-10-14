# v085 Review

## Verdict on v084
- RETAINED: 24/24 legacy (21,1) identities (per-frame intensity gate), 4 map orientations, 2-shape-pair stability, inheritance ledger.
- CORRECTED (metadata only, zero simulation): the hand-written fine_index_call notes in the v084 pilot (row26 "125:130", row16 "75:80") were wrong - auto-derivation via `fine_slice` gives rows 185:190 / 135:140 (0-based); the actual `block_at` calls and all v084 numbers were correct. Sentinel summary constants are now generated from actual computation returns. v084 files preserved read-only.
- SCOPE GUARD (0.2): the per-frame intensity identity does NOT confer weak-C400 relative-precision identity; complex-coefficient errors are managed separately at the centre and full ROI in this round.

## What v085 establishes
1. **Phase A**: 8 sources frozen; the 6 existing double caches verified by actual array reads (case_id/shape/mask/finite); pilot re-verified at 1e-8 with auto-derived slices; 8 negative tests all rejected; orientation spot-check confirmed.
2. **Phase B**: field-first vs quadratic-form double-precision regression on a strong and a weak case - REGRESSION_PASS both (2D complex C400 relative Frobenius 1.6e-14 / 2.8e-13 against the 1e-10 gate; centre |d| ~1e-17 against 1e-12). The two paths are the same algebraic identity at double precision, as required.
3. **Phase C**: the remaining 18 states built with the streamed QF path (budget exactly 18/18); all 24 states DOUBLE_MAP_VERIFIED after persistence + readback. Map-level double-vs-single rF spans 3.9e-6 (strong) to 6.0e-3 (weak-map regime) - numerical-path diagnostics only.
4. **Phase D**: with the unified set, all 276 pairs (192 cross-D + 84 same-D) evaluated on the common 1681-px mask: per-state shape-path epsilon in [2.0e-6, 6.0e-3]; every |d^d - d^s| respects the triangle bound eps_i + eps_j; the nearest cross-D pair is unchanged across precisions (margin 8.9e-5); within-D amplitude confounding honestly retained (min same-D 2.2e-3 < several cross-D distances).

## Not claimed
No absolute Fe3O4 particle diameter, ranging error, noise detectability, experimental 2f causality, or continuous-domain identifiability. Triangle bounds are numerical-path bounds for this algorithm/cache only. Frozen states unchanged.
