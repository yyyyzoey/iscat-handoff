# v091 Review

## Verdict on v090
- RETAINED: NPZ-based frequency-key recovery (4 rows corrected), W1/W2 identities, sparse QR, all inherited evidence.
- CORRECTED: (2.1) the production aggregator accepted decimal-frequency aliasing (int(400.5)->400) - fixed with an explicit ContractError; (2.2) the v090 sparse closure used an absolute 1e-10 gate where the original contract requires the relative/near-zero rule - re-judged per point from SAVED evidence (144/144 PASS under the original gate, no refit); (2.3) the missing 12-row full-stats table, 6+6 identity relations, and per-window Imean/X numerators are now delivered.

## What v091 establishes
1. **Phase A (seal)**: 8/8 guard tests (including the real alias-gap fix); 12 identity relations 12/12; 144-point original-gate closure 144/144 from the SAVED v090 sparse evidence. The D0-D3 experimental estimator branch is CLOSED - no further window/frequency/model search.
2. **Phase B (leave-group)**: 216 algebraic queries over the frozen 24-state demo library with three pre-registered scenarios and three fixed features. Honest confounding quantification: unit-magnitude shape survives amplitude changes (24/24) but is destroyed by motion-type changes (0/24); the symmetric magnitude pattern is the most focus-robust (22/24) but motion-fragile (8/24); log-ratio is amplitude-dominated (4/24). Count-based in-sample screens only.
3. **Phase C**: parameter readiness with 4 blocking groups; P0 NOT_RUN_RESOURCE_GATED; rule7 0.

## Not claimed
No identification accuracy, detectability, FPR, diameter, Bias/RMSE, magnetic causality, or continuous-domain identifiability. Frozen states unchanged.
