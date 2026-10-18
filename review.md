# v107 Review
## Scope
Packages the complete accumulated numerical research from v081-v106.
## Inherited verified results
- 48/48 bank identity
- 576/576 probes
- 5040 comparisons with correct channel routing
- 852/852 decomposition
- 1680 radius + 1680 perturbation
- 576 period diagnostics + 14400 components
## v106 findings
- v106 status/review used old schema
- v106 did not include full 5040 independent verification or oracle fixes
- These are delivery scope gaps, not numerical errors
## Not claimed
No diameter, causality, detectability, or identifiability claims.

# v108 Review
## Scope
V108_FULL_FROZEN_RELEASE: v107 audit, evidence-level inheritance, complete numerical acceptance, real archive.
Source: v107 fixed commit bc699b0932cf18f5abad10e09f1d1eae0f29446e (parent v106 79ba7a7f9068b6ed3a0c621eb25be488de85e68c).
Production entry: tools/run_v108_all.py (tool SHA-256 recorded in status.json). All outputs written outside the source tree; the real ZIP carries the 73 core inputs, tool snapshot, stage logs and all numeric results.
## Machine gates (this run, all PASS)
- A: 73/73 snapshots byte-verified; 48/48 bank identity (C=2X/(N*Imean) <1e-10, mask formula); 24/24 old-C160 rF <1e-10; probe NPZ git blob 6b180147f64847329375363d44c317b2d4df247b, 192 keys exact.
- B: 14400/14400 three-frequency three-path origins (6 complex diffs each <1e-11) + independent subprocess FFT 14400/14400; 576/576 probe gates; 576/576 zero-start; 192/192 periods; 24/24 motion-time pairings; 576 amp summaries; 14400 projection components.
- C: 5040/5040 independent decisions match production <1e-12 (per-channel squared-sum reduction; total norms NOT replaced by per-channel norms); 210 summaries; 1440-row and 60-summary historical subsets verified as strict key subsets; 19/19 error tests through the real validation entry (duplicate/extra keys now detected; order-insensitive positives accepted; old v105 13/19 kept as historical fact).
- D: 852/852 decompositions (both identity residuals <1e-12); 2556 channel terms; 180 single-160 fixed-control items; 1680 radii + 70 summaries + 1680 budgets derived from the independently verified decision (m>0 AND no cross-D tie; eps_q<m/2, symmetric<m/4, eta<m/8); v103/v104/v105 tables re-audited REUSED_VALUES_AUDITED_CURRENTLY; v106-rewritten v096 radius values read at the current fixed commit and matched <1e-12; v107 status/receipt audited as historical facts (receipt zip_status=PENDING_CREATION; status hash claim mismatch), never copied as v108 evidence.
## Archive
Real ZIP sha256 47ab8c14028997c56f180d44efeead0f22de2e7b54b3274b44b080b5938fcbab; external receipt, launch record and v108_archive_check.json produced by tools/v108_archive_check.py re-reading ZIP bytes (CRC, member set, per-member SHA, 73 roles/cases, status hash, machine gates). Result: ARCHIVE_VERIFIED, NUMERICAL_SEALED, exit 0.
## Not claimed
No new BEM/render/optics/physics/experiment reads (0/0/0/0/0). calibration_valid, experimental_validation, detection_validated remain false; single_particle_diameter NOT_ESTIMATED; physics admission PENDING_PARAMETERS; rule7 new authorizations 0.

# v109 Review
## Scope
V109_DELTA_REPAIR_AND_PHYSICS_ADMISSION. Delta acceptance of frozen v108 (source commit e377f8a11421a04bc3e6c1eaca9f435a46566784, parent v107 bc699b0932cf18f5abad10e09f1d1eae0f29446e). Production entry tools/run_v109_delta.py; outputs outside the source tree; real ZIP + external receipt/launch/archive_check.
## Machine gates (all PASS -> DELTA_VERIFIED)
- A: fixed HEAD verified; 73/73 byte snapshots (SHA vs git manifest where listed; probe git blob 6b180147...); 14400/14400 origin readback (six diffs <1e-11 recomputed from stored A/B/C) + per-frequency FFT from saved series 14400/14400; mean identity 4800/4800; 576/576 zero-start; 576/576 probe readbacks; periods/pairs/components reused by SHA+gates; v107 status LF/CRLF dual fingerprint verified with explicit hash_domain (git canonical blob bf16131f... == LF; 2594b2b7.../8007700d... == LF->CRLF conversion; content identical, neither is tampering); v108 ZIP bytes independently re-verified (SHA 47ab8c14...).
- B: genuinely independent decision SUBPROCESS: 5040/5040 match vs v108 frozen table <1e-12; 210 summaries; 1440/60 strict subsets (keys + values + counts; sub1440_field_bad=0; s60 dup keys=0); 23/23 error tests through the real validation entry incl. nearest_dist/second_dist/final_decision/tie_threshold injections and EXACT-threshold rejection (diff == 1e-12 rejected under strict <1e-12); row-order reversal accepted.
- C: corrected 180-row count control (6 channel subsets x 10 groups x 3 features, bin-160 baseline; 85 rows with count change; all outcomes kept, no selection); 60-pair factor-distance table repaired: corrected d3 (single total-norm normalization) matches joint unit-shape direct distance from 852 decomposition with max residual 6.7e-16; 60/60 d3 changed, max |delta| 3.146 (formula correction, NOT multi-frequency gain); d1/d2 unchanged; 852/852 decomposition residuals <1e-12; 1680 radii + 70 summaries + 1680 budgets (m>0 AND no cross-D tie).
- D: physics_input_contract.json (15 items: 4 measured with file/line provenance, 3 assumed, 8 missing=null) + two bounded route designs (trajectory-first; field-first); design only, no new solves; 65nm demo pixel and 5-20nm amplitudes remain assumptions.
## Archive
Real ZIP sha256 6d4535903f8a2f89c064e35f4c918810e13b9cc5fe0dc6d275a29ab7e10a7a2d; single final ZIP built after status+final_summary; external checker verifies CRC, unique members, full manifest, 73 roles with EXACT case multiset, per-member SHA, status task/source/gates (exact fixed gate set, strict booleans); archive_integrity and numerical_accepted recorded separately. Result: DELTA_VERIFIED, ARCHIVE_VERIFIED, exit 0.
## Not claimed
0 new BEM/render/optical-time-series/physics-states/experiment-video reads. Frozen states unchanged; physics admission PENDING_PARAMETERS; rule7 new authorizations 0.

# v110 Review
## Scope
V110: v109 fixed-commit review, delta numerical evidence sealing, archive consistency, real physics admission. Source frozen at 3f894b919d11dd2e8dead92b83ed7ec2d930d08c (parent v108 e377f8a...). Production entry tools/run_v110_all.py; outputs outside the tree; two-phase archive protocol (provisional selftest fixture -> single final ZIP after verifier qualification; both hashes disclosed in logs/v110_provisional_zip_sha.json).
## Machine gates (all PASS)
- A: fixed HEAD/parent verified; 73/73 snapshots (manifest SHA cross-check; probe blob 6b180147...); v109 ZIP bytes independently re-verified (6d453590...); v108 ZIP re-verified (47ab8c14...); v107 LF/CRLF dual fingerprint confirmed with explicit hash_domain; source diff vs v109 saved (logs/v110_source_diff.patch).
- B: independent decision subprocess 5040/5040 vs frozen v109 table AND v108 table (<1e-12, all fields; v108 absent fields counted NOT_RECORDED, never invented); 210 summaries match; 1440/60 strict subsets; 23/23 error tests through the released validation entry incl. exact-threshold rejection and order-reversal acceptance.
- C: count-control audit 180/180 against the accepted 210 (78 increased / 95 unchanged / 7 decreased; ambiguity preserved, no selection); 60/60 corrected d3 match decomposition <1e-12; 120/120 d1/d2 unchanged; corrected 180-row table carries target_feature_diff NA semantics; 30-group difference attribution: all 60 historical v092 summary rows REPRODUCE EXACTLY under the v092 representation definition with complex128 arrays - the 30 reported differences are three_bin_magnitude rows compared against a single-160 baseline (PROVEN statistical-object difference); C400_only rows equal current bin160 counts exactly; single-precision attribution NOT supported by evidence.
- D: 14400/14400 origin readback (six diffs <1e-11) + per-frequency FFT from saved series; 576/576 zero-start; 576/576 probes; periods/pairs/components reused by SHA+gates; 852/852 decomposition; 1680 radii + 1680 budgets with m>0 AND no-cross-D-tie qualification checked per row; consistent with frozen v109 tables <1e-12.
- E: physics contract reclassified into USER_CONFIRMED / EXPERIMENT_SCRIPT_RECORDED / ANALYSIS_CONTRACT / SIMULATION_ASSUMPTION / MISSING; k0 bins are ANALYSIS_CONTRACT (INSTRUMENT_MEASURED rejected by contract validator); Fs script-recorded only (no clock calibration); 520nm USER_CONFIRMED without instrument certificate; source audit reads each cited file/line (7 VERIFIED, 8 NO_SOURCE_AS_DECLARED); GO=false for both routes -> REAL_PHYSICS_PENDING_INPUTS with formal prerequisites (independent diameter calibration/blank, B-off control, camera time sync).
- F: released v110 verifier self-test 11/11: missing ZIP (v109 finish(ok=True) defect fixed), missing BANK case, duplicate member, corrupt CRC, manifest path traversal, status missing, string-bool gates, missing gate, wrong task id, wrong status SHA all rejected with non-zero exit; positive control mechanically integral. archive_integrity and numerical_accepted recorded separately.
## Archive
Final ZIP sha256 0c8a21116170c26cef59d2446f7fe2e9598babae97df18e171aa343585aadeb8; in-ZIP status explicitly PRE_ARCHIVE_VERIFICATION; external receipt + post_archive_summary.json (sha recorded in receipt) are the only post-verification credentials. Result: DELTA_EVIDENCE_SEALED, ARCHIVE_VERIFIED, exit 0.
## Not claimed
0 new BEM/render/optical-time-series/physics-states/experiment-video reads; P0 remains OPEN; rule7 new authorizations 0; frozen states unchanged; no absolute single-particle diameter claim.
