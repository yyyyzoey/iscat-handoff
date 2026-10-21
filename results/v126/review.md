# V126 review (real executed scope)

## A0/A1
- Fixed v125@36a231e; 63-node library + H01-H06 verified and reused; zero re-solves of existing nodes.
- Corrected pairwise numerics (same-D/same-h/same-material): D30 0.55%, D200 0.067% relL2 (PASS); D100 np-nwater pair reported via absolute floor values (relL2 meaningless at near-zero signal) - fixes the V125 material-mixing bug.
- Axis/nonzero-shift: zero-shift replay 5.4e-7 (wide-vs-standard grid discretization); +/-28nm, +140nm x and +140nm y vs direct MATLAB renders all PASS (2.6e-4..3.7e-4) under the GLOBAL camera-frame normalization (_camx_flip; uniform, no per-case choice).

## A2 error separation (dev H01-H06)
- Forward error at truth (I1): 5e-5..2.4e-2 L2 (worst at grid-edge D=177).
- Closure: optimizer recovers truth in 5/6; H05 full fit failed into a bad basin in BOTH candidates (returned 0.013 > truth 0.0013) - optimizer failure, now guarded by the loss-guard fallback.
- Candidate: I1 frozen (model_freeze.json written BEFORE J inversion; I2 marginal image-deviation advantage offset by its H06 full-fit boundary failure).

## S5 blind J holdouts
- Per case: [{"case": "J01", "err_D": -7.07, "err_h": 167.4, "err_xy": 0.19}, {"case": "J02", "err_D": 0.48, "err_h": 0.1, "err_xy": 0.11}, {"case": "J03", "err_D": 1.83, "err_h": 1.7, "err_xy": 0.17}, {"case": "J04", "err_D": 3.65, "err_h": 0.2, "err_xy": 0.17}, {"case": "J05", "err_D": 8.0, "err_h": 0.1, "err_xy": 0.15}, {"case": "J06", "err_D": 17.0, "err_h": 3.4, "err_xy": 0.3}]
- x/y recovered all 6; D: 4/6 within 8nm; J01 weak-signal h-D degeneracy (AMBIGUOUS), J06 boundary+biased. diameter_profiles.json holds the re-optimized (h,x,y) profiles.

## E detection vs reportable (separated)
- Thresholds: T > max(dev-blank T) per background; validation blanks: B=1e3 0/60 (binom95 4.87% met), B=1e4 3/60 (12.2% NOT met), B=1e5 0/60 (met).
- J noise: detected 46/90, diameter_reportable 28/90, reportable MAE 26.5 nm. candidate_D and reportable_D separate; non-reportable rows have reportable_D=null with reasons.

## F exposure/motion
- Fine/coarse integral: 5/9 pairs within 0.5% (max 0.0526) - honest: coarse path not fully converged everywhere.
- M2 continuous shared-D (noisy surrogate): MAE 31.7nm (100us) / 33.5nm (25us); 192 noiseless frames archived; all rows SHARED_SURROGATE_METHOD_DIAGNOSTIC.

## Honest limits
- EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=false. J01/J06 ambiguous or biased and reported as such. 6 J points validate only their own parameters, not the domain.
- Budget deviation: the 6 J solves predate the reserve() mechanism (recorded in budget_deviation_note.json); BEM 6/16, renders 18/128, exposure 5958(E)+384(F)=6342? authoritative per-event ledger in logs/.
