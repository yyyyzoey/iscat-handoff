# ISCAT V168 - Execution Truth and Authenticity Report

Generated: 2026-10-29T13:37:06Z | repo `C:\iscat\v168` | branch `v168` | HEAD `4e4a7a13cb26c3680da5922a8707989a11c449b3` | run `v168-20261029T114726Z-a0bdd10c07ff`

| | code identity | production test suite |
|---|---|---|
| live tree at report time | `e0c1d736bfbccae400a2ffad35de8195e01551d60dd234a30dd1dc3c1422ef71` (52 files) | `fb9f6885555d82bd495abd320c178f455b0ddecc5d7d5f8a128f2acd12ddcdcb` (212 tests, 0 failures, 0 errors, 0 skipped, 415 s) |
| identity the authorized round ran under | `e0c1d736bfbccae400a2ffad35de8195e01551d60dd234a30dd1dc3c1422ef71` (50 files, git_head `5dbfeec8c1655d360f3fdb6ae38d94e617d0d087`) | `c7521e2c2b7cf1850e6d6d50d15c44a2751c5d47323be212dcb2ae150e7a0992` (285 tests in 3 suites) |

> This report attests what was executed. It is not scientific acceptance. A zero exit code, a green test suite, byte-exact replay, `VERIFIED` binding fields or a packaged archive are mechanical states only. Simulated-size differences in this round are not experimental absolute magnetic-core diameter accuracy: `reportable_D` is null and `experimental_absolute_diameter_validated` is false in every published document here.

## Bottom line

The authorized round `v168-20261029T114726Z-a0bdd10c07ff` spent **3,171 of 9,999** new calls, made **0** new random draws, and ran all 23 planned tasks (5 unfinished second starts + 18 fixed +/-2 nm height bias tests) over all 41 prescribed starts. It then failed in the step that publishes the R-merge document: `estimates` raised `TypeError: Object of type ndarray is not JSON serializable` inside `canon()`, the process exited **1**, and `seal` and `validate` were recorded as BLOCKED by that failure. Because the seal never happened, no estimate was sealed and the independent truth score was never started.

The defect is in the controller publication path, not in the optics, the billing or the isolation gates: `run` completed 23/23 tasks and 3,045 charged calls with `failures: []`, and every one of the 23 task result documents exists on disk with its own SHA. It was repaired after the round, in commit `4e4a7a1` (new test `tools/v168/tests/test_v168_estimate_publication.py`), and the repaired executor is covered by the live 212-test production suite reported below. Replaying `estimates` for this round would require a `prepare` pass and a new run identity, i.e. new authorized budget, which this contract does not give, so the round is delivered as FAILED with its evidence intact rather than re-run.

## Stage verdicts

Verbatim from the run-scoped status published by the read-only closing pass, `results/v168/status_v168-20261029T114726Z-a0bdd10c07ff.json`:


| stage | EXECUTION | VERIFICATION | scientific scope | evidence |
|---|---|---|---|---|
| P0_evidence_protection | EXECUTED | VERIFIED | no claim; read-only verification of V166 pins | C:/iscat/v168/results/v168/controller_only/task_signatures.json |
| P1_input_isolation | EXECUTED | VERIFIED | NON-ADVERSARIAL runtime guard, not a kernel sandbox | C:/iscat/v168/results/v168/estimator_inputs/00_isolation_receipt.json |
| P2_model_binding | EXECUTED | VERIFIED | one authorized construction; no new BEM or render | C:/iscat/v168/results/v168/controller_only/bind_model.json |
| P3_authorized_computation | EXECUTED | 23 of 23 task result documents persisted, not yet sealed | simulated F2c development fits only | C:/iscat/v168/results/v168/controller_only/run_round.json |
| P4_final_verify | FINISHED | logical 63 / distinct 39 / verified 39 / not verifiable 0 | byte-level reproduction of published answers only | C:/iscat/v168/results/v168/controller_only/final_verify.json |
| P5_seal_and_score | NOT_STARTED | NOT_STARTED | NOT_EVALUATED until the validator runs | C:/iscat/v168/results/v168/seal.json |


The primary `results/v168/status.json` still says `23 of 23 tasks sealed` for P3. That sentence is false and its bytes are preserved unchanged; the correction is in `history_corrections.md` (H2) and in the versioned file quoted above.

## Attestations

| # | Attestation | Status |
|---|---|---|
| A01_scene_protection | V166's 28 results, 24 height readings and both historical ledgers were opened read-only; no reset, clean, delete, overwrite or rename-fresh was applied to any prior-generation file. | ATTESTED |
| A02_p0_before_identity | The read-only P0 audits, the frozen execution capsule and the round preamble all exist and all pass before the run identity was created; the round then reserved against that identity only. | ATTESTED |
| A03_one_run_one_ledger_one_construction | Exactly one V168 run identity, one new ledger and one authorized model construction were used; the round trace records model_constructions_in_process=1 and the closing read-only pass records 0. | ATTESTED |
| A04_v167_charge_carried | The single V167 CHARGED attempt is still CHARGED in its untouched snapshot; V168 carries it, asks for 9,999 new calls under a 10,000 combined ceiling, and invents no RETURNED state. | ATTESTED |
| A05_estimator_input_isolation | Each of the 23 estimator jails holds its own single height reading, its own group three-frame document and its own six legal records; the full 24-row table, the controlled offset, the seed, the truth hash and the sealed truth stayed in controller-only space. | ATTESTED |
| A06_no_resampling | No random draw of any kind was made this round: 0 new height draws, 0 new camera noise draws, 0 new BEM, render, fixed-D sweeps or exposures. | ATTESTED |
| A07_r_branch_five_second_starts | The five authorized unfinished second starts ran as new tasks from the preserved V166 partial-search resume points; the old PARTIAL_SEARCH state was carried verbatim and never rewritten into a historical success. | ATTESTED |
| A08_b_branch_eighteen_bias_tests | All 18 fixed +/-2 nm height-offset tests ran on the three detected groups, with sigma never inflated, the offset never fitted, and every row kept whether the result looked better or worse. | ATTESTED |
| A09_per_start_persistence_and_billing | Every one of the 41 start records carries its own charged count, cache-hit count, prediction path, prediction SHA and C SHA, and the total charged equals the attempt rows in the ledger. | ATTESTED |
| A10_single_optimizer_within_real_call_cap | Every start is one optimizer pass (pass_index 1) under local_cap 400 real calls; the busiest start spent 315, so no search was split into two 200-call halves. | ATTESTED |
| A11_budget_within_caps | Spending stayed inside every phase cap with no transfers: 3,171 of 9,999 used. | ATTESTED |
| A12_task_documents_persisted | 23 of 23 planned task result documents were written and hashed. This says the documents exist and bind to the ledger; it does not say the round was sealed or accepted. | ATTESTED |
| A13_estimates_publication_step | The estimates step raised TypeError: Object of type ndarray is not JSON serializable while canonicalising the R-merge document, so estimates_merge_reuse.json was never published and the process exited 1. | FAILED |
| A14_seal_before_scoring | seal.json was never written because its dependency failed, so no estimate was sealed before any truth read. | BLOCKED |
| A15_independent_truth_scoring | results/v168/validator_only/ does not exist and no truth value was read for scoring; the independent score is not attempted, not failed and not partial. | NOT_STARTED |
| A16_no_truth_based_selection | Selection used the joint objective Q_total only, both prescribed columns are reported side by side, the historical witness is diagnostic and was not counted as a third start, and no row, reading or failure was deleted. | ATTESTED |
| A17_anon01_detection_unchanged | ANON_01 remains 0/3 under the frozen high-background detector and is not reported as a detected particle. | ATTESTED |
| A18_no_diameter_claim | reportable_D is null and experimental_absolute_diameter_validated is false in every published document; simulated-size differences are not experimental absolute magnetic-core diameter accuracy. | ATTESTED |
| A19_failure_register_complete | The register names the failed step and both blocked steps; nothing was deleted or hidden. | ATTESTED |
| A20_append_only_history_correction | The earlier primary status.json still asserts "23 of 23 tasks sealed" and the earlier primary failure_records.json still asserts record_count 0. Their bytes are preserved unchanged; the correcting files are published beside them and are listed in history_corrections.md. | ATTESTED_WITH_CAVEAT |
| A21_repairs_covered_by_tests_after_the_round | The executor, rehearsal, isolation and reporting repairs are covered by the live production suite (212 tests, 0 failures). Those tests were added after the round spent its budget, so they prove the repaired executor, not the consumed round. | ATTESTED_WITH_CAVEAT |
| A22_repair_cannot_be_exercised_on_the_consumed_round | Re-running the estimates step needs a prepare pass and a new run identity, which would buy budget that is not authorized. EVIDENCE_ONLY_STEPS was not widened and no fresh retry was used to dodge the limit. | BLOCKED |
| A23_no_test_weakened_for_a_pass | No assertion was loosened to obtain a pass; the two reporting expectations were moved to a stricter seal-aware string and a new test pins both branches of it. | ATTESTED |
| A24_read_only_path_spends_nothing | --readonly-report and the pack closing pass constructed no model, charged no call and wrote no fit: model_calls 0 in every document they publish. | ATTESTED |
| A25_failure_delivery_is_real | The failure pack gate refuses a zero-exit round, more than one run identity, a non-read-only closing pass, a failed step missing from the register and an unexplained absent artefact. It is exercised by the production suite and used here; the archive itself is named by failure_package_receipt.json, written after this report. | ATTESTED |
| A26_exit_code_is_not_acceptance | No stage of this delivery treats a zero exit code, a green suite, byte-exact replay or a packaged archive as scientific acceptance. | ATTESTED |

## Evidence detail

### A01_scene_protection - ATTESTED

V166's 28 results, 24 height readings and both historical ledgers were opened read-only; no reset, clean, delete, overwrite or rename-fresh was applied to any prior-generation file.

```json
{
 "old_evidence_read_only_confirmed": true,
 "v166_release_commit": "06b35cd4e0a47f7f49ef4b05401a07266f2c03b6",
 "contract_pins": [
  {
   "path": "results/v166/estimates.json",
   "bytes": 18258,
   "observed_sha256": "8f97339e9645a29ec929e5c792d234a28821970338cf92a62d2982bfebba7634",
   "match": true
  },
  {
   "path": "results/v166/height_input/height_readings.json",
   "bytes": 8763,
   "observed_sha256": "bbfd793aff48247623081dd607168cd9afbba2deeff5f37c7a0cbd62b032ad4e",
   "match": true
  },
  {
   "path": "results/v166/iscat_v166_return_001.zip",
   "bytes": 17554667,
   "observed_sha256": "866feed02333f244df72f55e38ccf74060962007a5010c5c29df5ebe9f16a74e",
   "match": true
  },
  {
   "path": "results/v166/logs/v165_budget.sqlite",
   "bytes": 6979584,
   "observed_sha256": "254b5485164a57865328c81f8890ea4aa458d1386ed6f5f34533f2848f7e4ece",
   "match": true
  }
 ],
 "v167_snapshot": {
  "path": "C:\\iscat\\v168\\results\\v167\\logs\\v167_budget.sqlite",
  "sha256": "212fc61391070cc0d8f07e41d1a356f31d76a4aed713bfc8c0e0031ef1d1eb34",
  "actual_bytes": 24576,
  "bytes_before_and_after_equal": true,
  "mutation_performed_by_any_v168_tool": false
 },
 "v167_return_archive": {
  "archive_path": "C:\\Users\\PC\\Downloads\\iscat_v167_handoff.zip",
  "bytes_actual": 36754,
  "sha256_actual": "70cd6aba446eb047bc13a95abdfc088fe1549f04af36bf166e8f63da6250a719",
  "sha256_expected_from_v168_p0": "70cd6aba446eb047bc13a95abdfc088fe1549f04af36bf166e8f63da6250a719",
  "sha256_match": true,
  "members_actual": 17,
  "crc32_full_scan_result": "ALL_MEMBERS_OK",
  "duplicate_member_names": [],
  "duplicate_copies_agree": true,
  "unsafe_or_absolute_paths": [],
  "symlink_members": [],
  "inventory_payload_hashes_checked": 16,
  "inventory_hash_mismatch_count": 0,
  "members_not_listed_in_inventory": [
   "manifest_sha256.csv"
  ],
  "model_or_budget_activity": "NONE_READ_ONLY"
 }
}
```

### A02_p0_before_identity - ATTESTED

The read-only P0 audits, the frozen execution capsule and the round preamble all exist and all pass before the run identity was created; the round then reserved against that identity only.

```json
{
 "capsule": {
  "capsule_sha256": "c168e8795338f9e275b4836f0e834de01fe59b22c1be7b0b5918e5309eb80651",
  "authorization_sha256": "f8fb4b76f0ffc00eb5aa536f40180d250317afdfef8000c64fea7fa3e11d9f37",
  "test_suite_sha256": "c7521e2c2b7cf1850e6d6d50d15c44a2751c5d47323be212dcb2ae150e7a0992",
  "task_count": 23,
  "code_file_count": 50,
  "code_identity_sha256": "a0bdd10c07ff58609728f6721e018d356e9afdf5d5ed846a120bf4286e77ec27",
  "git_head": "5dbfeec8c1655d360f3fdb6ae38d94e617d0d087",
  "plan_sha256": "48727dbd9cbf14e09a6e4d6d7fe2c3d20af7d9a8d1106b049fcdc240ac03621c",
  "reserved": false,
  "freeze_stage": "PRE_RESERVATION_PRE_RUN_IDENTITY_CONSUMPTION",
  "workstation_test_release": {
   "camera_image_count": 12,
   "code_identity_sha256": "a0bdd10c07ff58609728f6721e018d356e9afdf5d5ed846a120bf4286e77ec27",
   "receipt_sha256": "02c91971e1e2e6fb5d21a740bd81ed94e2c7dabdd1f9f1104db0846000c793d6",
   "scenario_count": 4,
   "suite_count": 3,
   "test_suite_sha256": "c7521e2c2b7cf1850e6d6d50d15c44a2751c5d47323be212dcb2ae150e7a0992",
   "total_tests_recorded": 285,
   "workflow_receipt_sha256": "cb0ba67f24ac20523aa6f17ad923614eda30be60b2e10e1033e38cd292a53331",
   "workflow_run_id": "full_003"
  }
 },
 "round_preamble": {
  "run_id": "v168-20261029T114726Z-a0bdd10c07ff",
  "WORKSTATION_TEST_RELEASE_VERIFIED": true,
  "execution_capsule_sha256": "c168e8795338f9e275b4836f0e834de01fe59b22c1be7b0b5918e5309eb80651",
  "authorization_sha256": "f8fb4b76f0ffc00eb5aa536f40180d250317afdfef8000c64fea7fa3e11d9f37",
  "test_suite_sha256": "c7521e2c2b7cf1850e6d6d50d15c44a2751c5d47323be212dcb2ae150e7a0992",
  "code_identity_sha256": "a0bdd10c07ff58609728f6721e018d356e9afdf5d5ed846a120bf4286e77ec27",
  "workstation_test_release": {
   "CODE_BINDING_VERIFIED": true,
   "INPUT_PROVENANCE_VERIFIED": true,
   "WORKSTATION_TESTS_PASS": true,
   "WORKSTATION_TEST_RECEIPT_SCHEMA": "iscat168.workstation_tests.1",
   "WORKSTATION_TEST_RECEIPT_VERIFIED": true,
   "camera_image_count": 12,
   "code_identity_sha256": "a0bdd10c07ff58609728f6721e018d356e9afdf5d5ed846a120bf4286e77ec27",
   "git_head": "5dbfeec8c1655d360f3fdb6ae38d94e617d0d087",
   "model_calls": 0,
   "path": "C:\\iscat\\v168\\results\\v168\\workstation_tests\\full_003\\workstation_test_release_receipt.json",
   "receipt_sha256": "02c91971e1e2e6fb5d21a740bd81ed94e2c7dabdd1f9f1104db0846000c793d6",
   "refused_receipt_kinds": {
    "iscat165.workstation_tests.1": "RECEIPT_FROM_OTHER_GENERATION",
    "iscat167.workstation_tests.1": "RECEIPT_FROM_OTHER_GENERATION",
    "iscat168.production_test_execution.1": "STRATEGY_FUNCTIONS_ONLY_NO_PYTEST",
    "v166.test_execution_receipt.1": "STRATEGY_FUNCTIONS_ONLY_NO_PYTEST"
   },
   "scenario_count": 4,
   "schema": "iscat168.workstation_test_verify.1",
   "suite_count": 3,
   "test_suite_sha256": "c7521e2c2b7cf1850e6d6d50d15c44a2751c5d47323be212dcb2ae150e7a0992",
   "total_tests_recorded": 285,
   "workflow_receipt_sha256": "cb0ba67f24ac20523aa6f17ad923614eda30be60b2e10e1033e38cd292a53331",
   "workflow_run_id": "full_003"
  },
  "budget_caps_by_phase": {
   "BIAS_STRESS": 7200,
   "FINAL_VERIFY": 600,
   "MODEL_BINDING": 199,
   "SEARCH_EXTENSION": 2000
  },
  "git_blob_pinned_files": 72
 },
 "p0_audit_files": [
  "combined_budget_baseline.json",
  "evidence_set_separation.json",
  "history_charge_reconciliation.json",
  "old_ledger_hash_snapshot.json",
  "old_source_resolvability.json",
  "v167_archive_native_verification.json",
  "v167_archive_native_verification_zero_byte_disclosure.json",
  "v167_handoff_zip_native_verification.json",
  "v167_ledger_native.json",
  "v167_return_archive_native_verification.json"
 ]
}
```

### A03_one_run_one_ledger_one_construction - ATTESTED

Exactly one V168 run identity, one new ledger and one authorized model construction were used; the round trace records model_constructions_in_process=1 and the closing read-only pass records 0.

```json
{
 "round_trace": {
  "run_id": "v168-20261029T114726Z-a0bdd10c07ff",
  "exit_code": 1,
  "requested_steps": [
   "prepare",
   "bind",
   "run",
   "tables",
   "final",
   "estimates",
   "seal",
   "validate",
   "records",
   "status"
  ],
  "model_constructions_in_process": 1
 },
 "closing_trace": {
  "run_id": "v168-20261029T114726Z-a0bdd10c07ff",
  "exit_code": 0,
  "requested_steps": [
   "tables",
   "records",
   "status",
   "manifest",
   "verification"
  ],
  "model_constructions_in_process": 0,
  "read_only_control_path": true
 },
 "binding": {
  "run_id": "v168-20261029T114726Z-a0bdd10c07ff",
  "authorized_constructions": 1,
  "constructions_in_this_process": 1,
  "binding_status": "VERIFIED",
  "model_id": "v142-F2c-75860d222dd8e90d8dc2e31111e52ccbbb212a01c0d6a0dfe7fdbcdb241c98c3",
  "model_calls": 87,
  "model_construction_sha256": "9d189b3974a7d5ccaa9c2252690b55c91ea04bc45e6723c1abd8c3fd26d8c990"
 },
 "ledger_path": "results/v168/logs/v168_budget.sqlite"
}
```

### A04_v167_charge_carried - ATTESTED

The single V167 CHARGED attempt is still CHARGED in its untouched snapshot; V168 carries it, asks for 9,999 new calls under a 10,000 combined ceiling, and invents no RETURNED state.

```json
{
 "reconciliation": {
  "old_charge_carried": 1,
  "old_row_state_kept": "CHARGED",
  "old_snapshot": "212fc61391070cc0d8f07e41d1a356f31d76a4aed713bfc8c0e0031ef1d1eb34",
  "combined_ceiling": 10000,
  "new_authority": 9999,
  "ledger_settled_in_old_snapshot": false,
  "invented_RETURNED": false,
  "stack_error_class": "MODEL_ID_MISMATCH_IN_RETURN"
 },
 "old_ledger_native": {
  "historical_task_states": {
   "RUNNING": 26
  },
  "historical_unsettled_charge_count": 1,
  "native_integrity_check": "ok",
  "new_model_calls": 0,
  "old_attempt_settled_by_this_tool": false
 },
 "budget_baseline": {
  "combined_ceiling": 10000,
  "combined_consumed_before_v168_run": 1,
  "combined_remaining_before_v168_run": 9999,
  "historical_v167_consumed": 1,
  "authorization_sha256": "f8fb4b76f0ffc00eb5aa536f40180d250317afdfef8000c64fea7fa3e11d9f37"
 }
}
```

### A05_estimator_input_isolation - ATTESTED

Each of the 23 estimator jails holds its own single height reading, its own group three-frame document and its own six legal records; the full 24-row table, the controlled offset, the seed, the truth hash and the sealed truth stayed in controller-only space.

```json
{
 "single_reading_per_task": true,
 "tasks_with_exactly_three_files": 23,
 "truth_valued_key_offenders_in_any_staged_document": 0,
 "controlled_offset_exposed_to_estimator": false,
 "cross_sigma_sibling_exposed": false,
 "guard_label": "NON_ADVERSARIAL_PYTHON_RUNTIME_ISOLATION_NOT_A_KERNEL_SANDBOX",
 "access_denial_receipts_written_by": "tools/v168/tests (worker --probe)",
 "statement": "Each worker jail holds exactly three files: its own single-reading payload, its own group three-frame document and its own group six legal records. The full 24-row table, the plan, the controlled offset, the seed, the truth hash and the sealed truth stay in controller-only space.",
 "model_calls": 0
}
```

### A06_no_resampling - ATTESTED

No random draw of any kind was made this round: 0 new height draws, 0 new camera noise draws, 0 new BEM, render, fixed-D sweeps or exposures.

```json
{
 "new_bem": 0,
 "new_camera_exposures": 0,
 "new_camera_noise_draws": 0,
 "new_fixed_D_sweeps": 0,
 "new_height_random_draws": 0,
 "new_render": 0,
 "bias_branch_new_random_draws": 0,
 "bias_rows_new_random_draws": 0
}
```

### A07_r_branch_five_second_starts - ATTESTED

The five authorized unfinished second starts ran as new tasks from the preserved V166 partial-search resume points; the old PARTIAL_SEARCH state was carried verbatim and never rewritten into a historical success.

```json
{
 "table_scalars": {
  "schema": "iscat168.r_merge_table.1",
  "run_id": "v168-20261029T114726Z-a0bdd10c07ff",
  "row_count": 5,
  "old_partial_tasks_rewritten": 0,
  "old_partial_tasks_kept_as_partial_where_new_search_incomplete": true,
  "reportable_D": null,
  "model_calls": 0
 },
 "rows": [
  {
   "task_id": "V168_bba8c33973a8db3986792fdc",
   "source_task_id": "B100000_ANON_01_H10_R00",
   "old_execution_state": "PARTIAL_SEARCH",
   "old_execution_state_preserved_verbatim": true,
   "old_start_consumption": 200,
   "new_execution_state": "FINISHED",
   "new_actual_calls": 61,
   "new_charged_replies": 61,
   "new_cache_hit_replies": 2,
   "search_state": "SEARCH_COMPLETE_LOCAL_RETURN",
   "new_report_label": "SUPPLEMENTAL_LOCAL_RETURN",
   "merged_pick": "v168_new_optimizer_best",
   "reportable_D": null
  },
  {
   "task_id": "V168_9c45c88443c5f30f1a029abb",
   "source_task_id": "B100000_ANON_01_H10_R01",
   "old_execution_state": "PARTIAL_SEARCH",
   "old_execution_state_preserved_verbatim": true,
   "old_start_consumption": 200,
   "new_execution_state": "FINISHED",
   "new_actual_calls": 98,
   "new_charged_replies": 98,
   "new_cache_hit_replies": 1,
   "search_state": "SEARCH_COMPLETE_LOCAL_RETURN",
   "new_report_label": "SUPPLEMENTAL_LOCAL_RETURN",
   "merged_pick": "v168_new_optimizer_best",
   "reportable_D": null
  },
  {
   "task_id": "V168_6cbafc09b3a96db857e72dde",
   "source_task_id": "B100000_ANON_01_H1_R00",
   "old_execution_state": "PARTIAL_SEARCH",
   "old_execution_state_preserved_verbatim": true,
   "old_start_consumption": 200,
   "new_execution_state": "FINISHED",
   "new_actual_calls": 43,
   "new_charged_replies": 43,
   "new_cache_hit_replies": 2,
   "search_state": "SEARCH_COMPLETE_LOCAL_RETURN",
   "new_report_label": "SUPPLEMENTAL_LOCAL_RETURN",
   "merged_pick": "v168_new_optimizer_best",
   "reportable_D": null
  },
  {
   "task_id": "V168_57427e055bc675c65e2150c5",
   "source_task_id": "B100000_ANON_01_H1_R01",
   "old_execution_state": "PARTIAL_SEARCH",
   "old_execution_state_preserved_verbatim": true,
   "old_start_consumption": 200,
   "new_execution_state": "FINISHED",
   "new_actual_calls": 79,
   "new_charged_replies": 79,
   "new_cache_hit_replies": 2,
   "search_state": "SEARCH_COMPLETE_LOCAL_RETURN",
   "new_report_label": "SUPPLEMENTAL_LOCAL_RETURN",
   "merged_pick": "v168_new_optimizer_best",
   "reportable_D": null
  },
  {
   "task_id": "V168_35b5f8734a282d3cfaeb33b1",
   "source_task_id": "B100000_ANON_01_H1_R02",
   "old_execution_state": "PARTIAL_SEARCH",
   "old_execution_state_preserved_verbatim": true,
   "old_start_consumption": 200,
   "new_execution_state": "FINISHED",
   "new_actual_calls": 79,
   "new_charged_replies": 79,
   "new_cache_hit_replies": 2,
   "search_state": "SEARCH_COMPLETE_LOCAL_RETURN",
   "new_report_label": "SUPPLEMENTAL_LOCAL_RETURN",
   "merged_pick": "v168_new_optimizer_best",
   "reportable_D": null
  }
 ],
 "old_sources_anchored": {
  "all_five_anchored_and_hash_verified": true
 }
}
```

### A08_b_branch_eighteen_bias_tests - ATTESTED

All 18 fixed +/-2 nm height-offset tests ran on the three detected groups, with sigma never inflated, the offset never fitted, and every row kept whether the result looked better or worse.

```json
{
 "table_scalars": {
  "schema": "iscat168.b_stress_table.1",
  "run_id": "v168-20261029T114726Z-a0bdd10c07ff",
  "row_count": 18,
  "state_counts": {
   "FINISHED": 18
  },
  "by_offset": {
   "-2.0": {
    "failed": 0,
    "finished": 9,
    "partial": 0,
    "tasks": 9
   },
   "2.0": {
    "failed": 0,
    "finished": 9,
    "partial": 0,
    "tasks": 9
   }
  },
  "new_random_draws": 0,
  "historical_witness_is_a_third_start": false,
  "historical_witness_status": "DIAGNOSTIC_WITNESS_ONLY",
  "reportable_D": null
 },
 "per_row": [
  {
   "task_id": "V168_f2f047fc919490a070ca7ddf",
   "source_task_id": "B100000_ANON_02_H1_R00",
   "group": "ANON_02",
   "replicate": 0,
   "sigma_nm": 1.0,
   "controlled_offset_nm": -2.0,
   "offset_is_fixed_not_fitted": true,
   "sigma_nm_never_modified": true,
   "starts_used": 2,
   "passes_used": 2,
   "execution_state": "FINISHED",
   "search_state": "SEARCH_COMPLETE_LOCAL_RETURN",
   "actual_calls": 136,
   "charged_replies": 136,
   "cache_hit_replies": 18,
   "report_label": "BIAS_STRESS_LOCAL_RETURN",
   "historical_witness_rescore_error": null,
   "witness_below_new_search": false,
   "reportable_D": null
  },
  {
   "task_id": "V168_3b11bb5c6775c55cd2e2abdb",
   "source_task_id": "B100000_ANON_02_H1_R00",
   "group": "ANON_02",
   "replicate": 0,
   "sigma_nm": 1.0,
   "controlled_offset_nm": 2.0,
   "offset_is_fixed_not_fitted": true,
   "sigma_nm_never_modified": true,
   "starts_used": 2,
   "passes_used": 2,
   "execution_state": "FINISHED",
   "search_state": "SEARCH_COMPLETE_LOCAL_RETURN",
   "actual_calls": 145,
   "charged_replies": 145,
   "cache_hit_replies": 18,
   "report_label": "BIAS_STRESS_LOCAL_RETURN",
   "historical_witness_rescore_error": null,
   "witness_below_new_search": false,
   "reportable_D": null
  },
  {
   "task_id": "V168_6aead30193f0729070eb7067",
   "source_task_id": "B100000_ANON_02_H1_R01",
   "group": "ANON_02",
   "replicate": 1,
   "sigma_nm": 1.0,
   "controlled_offset_nm": -2.0,
   "offset_is_fixed_not_fitted": true,
   "sigma_nm_never_modified": true,
   "starts_used": 2,
   "passes_used": 2,
   "execution_state": "FINISHED",
   "search_state": "SEARCH_COMPLETE_LOCAL_RETURN",
   "actual_calls": 136,
   "charged_replies": 136,
   "cache_hit_replies": 18,
   "report_label": "BIAS_STRESS_LOCAL_RETURN",
   "historical_witness_rescore_error": null,
   "witness_below_new_search": false,
   "reportable_D": null
  },
  {
   "task_id": "V168_bfc371ebc3d068bd653e2b9b",
   "source_task_id": "B100000_ANON_02_H1_R01",
   "group": "ANON_02",
   "replicate": 1,
   "sigma_nm": 1.0,
   "controlled_offset_nm": 2.0,
   "offset_is_fixed_not_fitted": true,
   "sigma_nm_never_modified": true,
   "starts_used": 2,
   "passes_used": 2,
   "execution_state": "FINISHED",
   "search_state": "SEARCH_COMPLETE_LOCAL_RETURN",
   "actual_calls": 145,
   "charged_replies": 145,
   "cache_hit_replies": 18,
   "report_label": "BIAS_STRESS_LOCAL_RETURN",
   "historical_witness_rescore_error": null,
   "witness_below_new_search": false,
   "reportable_D": null
  },
  {
   "task_id": "V168_cd07a92e814bd03287c24b10",
   "source_task_id": "B100000_ANON_02_H1_R02",
   "group": "ANON_02",
   "replicate": 2,
   "sigma_nm": 1.0,
   "controlled_offset_nm": -2.0,
   "offset_is_fixed_not_fitted": true,
   "sigma_nm_never_modified": true,
   "starts_used": 2,
   "passes_used": 2,
   "execution_state": "FINISHED",
   "search_state": "SEARCH_COMPLETE_LOCAL_RETURN",
   "actual_calls": 136,
   "charged_replies": 136,
   "cache_hit_replies": 18,
   "report_label": "BIAS_STRESS_LOCAL_RETURN",
   "historical_witness_rescore_error": null,
   "witness_below_new_search": false,
   "reportable_D": null
  },
  {
   "task_id": "V168_226934a44622d6b6f73daa2a",
   "source_task_id": "B100000_ANON_02_H1_R02",
   "group": "ANON_02",
   "replicate": 2,
   "sigma_nm": 1.0,
   "controlled_offset_nm": 2.0,
   "offset_is_fixed_not_fitted": true,
   "sigma_nm_never_modified": true,
   "starts_used": 2,
   "passes_used": 2,
   "execution_state": "FINISHED",
   "search_state": "SEARCH_COMPLETE_LOCAL_RETURN",
   "actual_calls": 154,
   "charged_replies": 154,
   "cache_hit_replies": 18,
   "report_label": "BIAS_STRESS_LOCAL_RETURN",
   "historical_witness_rescore_error": null,
   "witness_below_new_search": false,
   "reportable_D": null
  },
  {
   "task_id": "V168_8fdc46599d121c1698858401",
   "source_task_id": "B100000_ANON_03_H1_R00",
   "group": "ANON_03",
   "replicate": 0,
   "sigma_nm": 1.0,
   "controlled_offset_nm": -2.0,
   "offset_is_fixed_not_fitted": true,
   "sigma_nm_never_modified": true,
   "starts_used": 2,
   "passes_used": 2,
   "execution_state": "FINISHED",
   "search_state": "SEARCH_COMPLETE_LOCAL_RETURN",
   "actual_calls": 108,
   "charged_replies": 108,
   "cache_hit_replies": 18,
   "report_label": "BIAS_STRESS_LOCAL_RETURN",
   "historical_witness_rescore_error": null,
   "witness_below_new_search": false,
   "reportable_D": null
  },
  {
   "task_id": "V168_ed84c3ba4e2cad6be40b4893",
   "source_task_id": "B100000_ANON_03_H1_R00",
   "group": "ANON_03",
   "replicate": 0,
   "sigma_nm": 1.0,
   "controlled_offset_nm": 2.0,
   "offset_is_fixed_not_fitted": true,
   "sigma_nm_never_modified": true,
   "starts_used": 2,
   "passes_used": 2,
   "execution_state": "FINISHED",
   "search_state": "SEARCH_COMPLETE_LOCAL_RETURN",
   "actual_calls": 189,
   "charged_replies": 189,
   "cache_hit_replies": 18,
   "report_label": "BIAS_STRESS_LOCAL_RETURN",
   "historical_witness_rescore_error": null,
   "witness_below_new_search": false,
   "reportable_D": null
  },
  {
   "task_id": "V168_e7b6d9b7b0d959ac5ec96ae4",
   "source_task_id": "B100000_ANON_03_H1_R01",
   "group": "ANON_03",
   "replicate": 1,
   "sigma_nm": 1.0,
   "controlled_offset_nm": -2.0,
   "offset_is_fixed_not_fitted": true,
   "sigma_nm_never_modified": true,
   "starts_used": 2,
   "passes_used": 2,
   "execution_state": "FINISHED",
   "search_state": "SEARCH_COMPLETE_LOCAL_RETURN",
   "actual_calls": 117,
   "charged_replies": 117,
   "cache_hit_replies": 18,
   "report_label": "BIAS_STRESS_LOCAL_RETURN",
   "historical_witness_rescore_error": null,
   "witness_below_new_search": false,
   "reportable_D": null
  },
  {
   "task_id": "V168_18cbbc3267084c6c7fe3979b",
   "source_task_id": "B100000_ANON_03_H1_R01",
   "group": "ANON_03",
   "replicate": 1,
   "sigma_nm": 1.0,
   "controlled_offset_nm": 2.0,
   "offset_is_fixed_not_fitted": true,
   "sigma_nm_never_modified": true,
   "starts_used": 2,
   "passes_used": 2,
   "execution_state": "FINISHED",
   "search_state": "SEARCH_COMPLETE_LOCAL_RETURN",
   "actual_calls": 315,
   "charged_replies": 315,
   "cache_hit_replies": 18,
   "report_label": "BIAS_STRESS_LOCAL_RETURN",
   "historical_witness_rescore_error": null,
   "witness_below_new_search": false,
   "reportable_D": null
  },
  {
   "task_id": "V168_cb928865c70c592afd426f68",
   "source_task_id": "B100000_ANON_03_H1_R02",
   "group": "ANON_03",
   "replicate": 2,
   "sigma_nm": 1.0,
   "controlled_offset_nm": -2.0,
   "offset_is_fixed_not_fitted": true,
   "sigma_nm_never_modified": true,
   "starts_used": 2,
   "passes_used": 2,
   "execution_state": "FINISHED",
   "search_state": "SEARCH_COMPLETE_LOCAL_RETURN",
   "actual_calls": 108,
   "charged_replies": 108,
   "cache_hit_replies": 18,
   "report_label": "BIAS_STRESS_LOCAL_RETURN",
   "historical_witness_rescore_error": null,
   "witness_below_new_search": false,
   "reportable_D": null
  },
  {
   "task_id": "V168_ef191a2e9fbf08f65f8c2902",
   "source_task_id": "B100000_ANON_03_H1_R02",
   "group": "ANON_03",
   "replicate": 2,
   "sigma_nm": 1.0,
   "controlled_offset_nm": 2.0,
   "offset_is_fixed_not_fitted": true,
   "sigma_nm_never_modified": true,
   "starts_used": 2,
   "passes_used": 2,
   "execution_state": "FINISHED",
   "search_state": "SEARCH_COMPLETE_LOCAL_RETURN",
   "actual_calls": 171,
   "charged_replies": 171,
   "cache_hit_replies": 18,
   "report_label": "BIAS_STRESS_LOCAL_RETURN",
   "historical_witness_rescore_error": null,
   "witness_below_new_search": false,
   "reportable_D": null
  },
  {
   "task_id": "V168_3fbe1c0c3337d488c229424a",
   "source_task_id": "B100000_ANON_04_H1_R00",
   "group": "ANON_04",
   "replicate": 0,
   "sigma_nm": 1.0,
   "controlled_offset_nm": -2.0,
   "offset_is_fixed_not_fitted": true,
   "sigma_nm_never_modified": true,
   "starts_used": 2,
   "passes_used": 2,
   "execution_state": "FINISHED",
   "search_state": "SEARCH_COMPLETE_LOCAL_RETURN",
   "actual_calls": 144,
   "charged_replies": 144,
   "cache_hit_replies": 18,
   "report_label": "BIAS_STRESS_LOCAL_RETURN",
   "historical_witness_rescore_error": null,
   "witness_below_new_search": false,
   "reportable_D": null
  },
  {
   "task_id": "V168_859307bd6e6e0e87f3d02622",
   "source_task_id": "B100000_ANON_04_H1_R00",
   "group": "ANON_04",
   "replicate": 0,
   "sigma_nm": 1.0,
   "controlled_offset_nm": 2.0,
   "offset_is_fixed_not_fitted": true,
   "sigma_nm_never_modified": true,
   "starts_used": 2,
   "passes_used": 2,
   "execution_state": "FINISHED",
   "search_state": "SEARCH_COMPLETE_LOCAL_RETURN",
   "actual_calls": 135,
   "charged_replies": 135,
   "cache_hit_replies": 18,
   "report_label": "BIAS_STRESS_LOCAL_RETURN",
   "historical_witness_rescore_error": null,
   "witness_below_new_search": false,
   "reportable_D": null
  },
  {
   "task_id": "V168_df5b094abb6400d8a9e7145e",
   "source_task_id": "B100000_ANON_04_H1_R01",
   "group": "ANON_04",
   "replicate": 1,
   "sigma_nm": 1.0,
   "controlled_offset_nm": -2.0,
   "offset_is_fixed_not_fitted": true,
   "sigma_nm_never_modified": true,
   "starts_used": 2,
   "passes_used": 2,
   "execution_state": "FINISHED",
   "search_state": "SEARCH_COMPLETE_LOCAL_RETURN",
   "actual_calls": 149,
   "charged_replies": 149,
   "cache_hit_replies": 18,
   "report_label": "BIAS_STRESS_LOCAL_RETURN",
   "historical_witness_rescore_error": null,
   "witness_below_new_search": false,
   "reportable_D": null
  },
  {
   "task_id": "V168_118c3d139ca96775ed1148ae",
   "source_task_id": "B100000_ANON_04_H1_R01",
   "group": "ANON_04",
   "replicate": 1,
   "sigma_nm": 1.0,
   "controlled_offset_nm": 2.0,
   "offset_is_fixed_not_fitted": true,
   "sigma_nm_never_modified": true,
   "starts_used": 2,
   "passes_used": 2,
   "execution_state": "FINISHED",
   "search_state": "SEARCH_COMPLETE_LOCAL_RETURN",
   "actual_calls": 135,
   "charged_replies": 135,
   "cache_hit_replies": 18,
   "report_label": "BIAS_STRESS_LOCAL_RETURN",
   "historical_witness_rescore_error": null,
   "witness_below_new_search": false,
   "reportable_D": null
  },
  {
   "task_id": "V168_18ee74dfe4a76a0bcd404ce0",
   "source_task_id": "B100000_ANON_04_H1_R02",
   "group": "ANON_04",
   "replicate": 2,
   "sigma_nm": 1.0,
   "controlled_offset_nm": -2.0,
   "offset_is_fixed_not_fitted": true,
   "sigma_nm_never_modified": true,
   "starts_used": 2,
   "passes_used": 2,
   "execution_state": "FINISHED",
   "search_state": "SEARCH_COMPLETE_LOCAL_RETURN",
   "actual_calls": 126,
   "charged_replies": 126,
   "cache_hit_replies": 18,
   "report_label": "BIAS_STRESS_LOCAL_RETURN",
   "historical_witness_rescore_error": null,
   "witness_below_new_search": false,
   "reportable_D": null
  },
  {
   "task_id": "V168_a62526d308d0ff9f58f6ea3f",
   "source_task_id": "B100000_ANON_04_H1_R02",
   "group": "ANON_04",
   "replicate": 2,
   "sigma_nm": 1.0,
   "controlled_offset_nm": 2.0,
   "offset_is_fixed_not_fitted": true,
   "sigma_nm_never_modified": true,
   "starts_used": 2,
   "passes_used": 2,
   "execution_state": "FINISHED",
   "search_state": "SEARCH_COMPLETE_LOCAL_RETURN",
   "actual_calls": 136,
   "charged_replies": 136,
   "cache_hit_replies": 18,
   "report_label": "BIAS_STRESS_LOCAL_RETURN",
   "historical_witness_rescore_error": null,
   "witness_below_new_search": false,
   "reportable_D": null
  }
 ]
}
```

### A09_per_start_persistence_and_billing - ATTESTED

Every one of the 41 start records carries its own charged count, cache-hit count, prediction path, prediction SHA and C SHA, and the total charged equals the attempt rows in the ledger.

```json
{
 "table_scalars": {
  "schema": "iscat168.per_start_table.1",
  "run_id": "v168-20261029T114726Z-a0bdd10c07ff",
  "row_count": 41,
  "tasks_in_table": 23,
  "state_counts": {
   "FINISHED": 41
  },
  "start_counts_by_task": {
   "V168_118c3d139ca96775ed1148ae": 2,
   "V168_18cbbc3267084c6c7fe3979b": 2,
   "V168_18ee74dfe4a76a0bcd404ce0": 2,
   "V168_226934a44622d6b6f73daa2a": 2,
   "V168_35b5f8734a282d3cfaeb33b1": 1,
   "V168_3b11bb5c6775c55cd2e2abdb": 2,
   "V168_3fbe1c0c3337d488c229424a": 2,
   "V168_57427e055bc675c65e2150c5": 1,
   "V168_6aead30193f0729070eb7067": 2,
   "V168_6cbafc09b3a96db857e72dde": 1,
   "V168_859307bd6e6e0e87f3d02622": 2,
   "V168_8fdc46599d121c1698858401": 2,
   "V168_9c45c88443c5f30f1a029abb": 1,
   "V168_a62526d308d0ff9f58f6ea3f": 2,
   "V168_bba8c33973a8db3986792fdc": 1,
   "V168_bfc371ebc3d068bd653e2b9b": 2,
   "V168_cb928865c70c592afd426f68": 2,
   "V168_cd07a92e814bd03287c24b10": 2,
   "V168_df5b094abb6400d8a9e7145e": 2,
   "V168_e7b6d9b7b0d959ac5ec96ae4": 2,
   "V168_ed84c3ba4e2cad6be40b4893": 2,
   "V168_ef191a2e9fbf08f65f8c2902": 2,
   "V168_f2f047fc919490a070ca7ddf": 2
  },
  "reportable_D": null,
  "model_calls": 0
 },
 "charged_sum": 3045,
 "cache_hit_sum": 333,
 "evaluation_sum": 3378,
 "rows_without_prediction_sha": 0,
 "rows_with_error": 0,
 "ledger_attempt_rows": 3171
}
```

### A10_single_optimizer_within_real_call_cap - ATTESTED

Every start is one optimizer pass (pass_index 1) under local_cap 400 real calls; the busiest start spent 315, so no search was split into two 200-call halves.

```json
{
 "pass_index_values": [
  1
 ],
 "start_index_values": [
  0,
  1
 ],
 "local_cap_values": [
  200,
  400
 ],
 "max_charged_in_one_start": 180,
 "max_charged_in_one_task": 315,
 "optimizer_success_false": 0
}
```

### A11_budget_within_caps - ATTESTED

Spending stayed inside every phase cap with no transfers: 3,171 of 9,999 used.

```json
{
 "budget_total": 9999,
 "budget_used_total": 3171,
 "budget_cap_by_phase": {
  "BIAS_STRESS": 7200,
  "FINAL_VERIFY": 600,
  "MODEL_BINDING": 199,
  "SEARCH_EXTENSION": 2000
 },
 "budget_used_by_phase": {
  "BIAS_STRESS": 2685,
  "FINAL_VERIFY": 39,
  "MODEL_BINDING": 87,
  "SEARCH_EXTENSION": 360
 },
 "phase_transfers": 0
}
```

### A12_task_documents_persisted - ATTESTED

23 of 23 planned task result documents were written and hashed. This says the documents exist and bind to the ledger; it does not say the round was sealed or accepted.

```json
{
 "scalars": {
  "run_id": "v168-20261029T114726Z-a0bdd10c07ff",
  "tasks_planned": 23,
  "tasks_executed_this_round": 23,
  "round_model_calls": 3045,
  "model_calls": 3045,
  "failures": [],
  "tasks_reused_from_sealed_ledger": [],
  "reportable_D": null
 },
 "task_result_documents_with_sha": 23,
 "execution_states": [
  "FINISHED"
 ]
}
```

### A13_estimates_publication_step - FAILED

The estimates step raised TypeError: Object of type ndarray is not JSON serializable while canonicalising the R-merge document, so estimates_merge_reuse.json was never published and the process exited 1.

```json
[
 {
  "blocked_by": null,
  "error": "Object of type ndarray is not JSON serializable",
  "error_type": "TypeError",
  "reason": null,
  "record_type": "CONTROLLER_STEP_FAILED",
  "step": "estimates",
  "traceback_tail": "Traceback (most recent call last):\n  File \"C:\\iscat\\v168\\tools\\v168\\v168_controller.py\", line 2779, in main\n    result = prepare(dry_run=args.dry_run) if name == \"prepare\" else _dispatch(name, ctx)\n                                                                     ^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\iscat\\v168\\tools\\v168\\v168_controller.py\", line 2663, in _dispatch\n    return estimates_documents(ctx)\n           ^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\iscat\\v168\\tools\\v168\\v168_controller.py\", line 2010, in estimates_documents\n    _stage_json(mpath, merge)\n  File \"C:\\iscat\\v168\\tools\\v168\\v168_controller.py\", line 979, in _stage_json\n    raw = canon(document)\n          ^^^^^^^^^^^^^^^\n  File \"C:\\iscat\\v168\\tools\\v168\\v168_common.py\", line 266, in canon\n    return (json.dumps(value, ensure_ascii=False, sort_keys=True,\n            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\ProgramData\\anaconda3\\Lib\\json\\__init__.py\", line 238, in dumps\n    **kw).encode(obj)\n          ^^^^^^^^^^^\n  File \"C:\\ProgramData\\anaconda3\\Lib\\json\\encoder.py\", line 200, in encode\n    chunks = self.iterencode(o, _one_shot=True)\n             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\ProgramData\\anaconda3\\Lib\\json\\encoder.py\", line 258, in iterencode\n    return _iterencode(o, 0)\n           ^^^^^^^^^^^^^^^^^\n  File \"C:\\ProgramData\\anaconda3\\Lib\\json\\encoder.py\", line 180, in default\n    raise TypeError(f'Object of type {o.__class__.__name__} '\nTypeError: Object of type ndarray is not JSON serializable\n"
 }
]
```

### A14_seal_before_scoring - BLOCKED

seal.json was never written because its dependency failed, so no estimate was sealed before any truth read.

```json
{
 "seal_file_on_disk": false,
 "blocked_records": [
  {
   "record_type": "CONTROLLER_STEP_BLOCKED",
   "step": "seal",
   "blocked_by": "estimates",
   "reason": "an earlier step failed; no budget was spent here"
  },
  {
   "record_type": "CONTROLLER_STEP_BLOCKED",
   "step": "validate",
   "blocked_by": "estimates",
   "reason": "an earlier step failed; no budget was spent here"
  }
 ],
 "status_stage_P5": {
  "EVIDENCE": "C:\\iscat\\v168\\results\\v168\\seal.json",
  "EXECUTION": "NOT_STARTED",
  "SCIENTIFIC_SCOPE": "NOT_EVALUATED until the validator runs",
  "VERIFICATION": "NOT_STARTED"
 },
 "closing_status_P3_verification": "23 of 23 task result documents persisted, not yet sealed",
 "seal_status_in_verification": null
}
```

### A15_independent_truth_scoring - NOT_STARTED

results/v168/validator_only/ does not exist and no truth value was read for scoring; the independent score is not attempted, not failed and not partial.

```json
{
 "validator_only_directory_exists": false,
 "independent_acceptance": "NOT_RUN_IN_CONTROLLER",
 "seal_sha256": null,
 "zip_sha256_at_report_time": null,
 "status_P5": {
  "EVIDENCE": "C:\\iscat\\v168\\results\\v168\\seal.json",
  "EXECUTION": "NOT_STARTED",
  "SCIENTIFIC_SCOPE": "NOT_EVALUATED until the validator runs",
  "VERIFICATION": "NOT_STARTED"
 }
}
```

### A16_no_truth_based_selection - ATTESTED

Selection used the joint objective Q_total only, both prescribed columns are reported side by side, the historical witness is diagnostic and was not counted as a third start, and no row, reading or failure was deleted.

```json
{
 "b_selection_rule": "both columns reported; no selection by true parameter error; sigma never inflated",
 "r_selection_rule": "lowest joint objective Q_total only; never true-parameter error",
 "historical_witness_is_a_third_start": false,
 "historical_witness_status": "DIAGNOSTIC_WITNESS_ONLY",
 "both_columns_reported": [
  "column_two_prescribed_starts_only_D_nm",
  "column_including_historical_witness_D_nm"
 ],
 "rows_in_b_table_kept": 18,
 "tasks_in_estimates_document": 23
}
```

### A17_anon01_detection_unchanged - ATTESTED

ANON_01 remains 0/3 under the frozen high-background detector and is not reported as a detected particle.

```json
{
 "r_rows_anonymous_detection_status": [
  "ANON_01 detection remains 0/3 (unchanged)"
 ],
 "r_rows_groups": [
  "ANON_01"
 ]
}
```

### A18_no_diameter_claim - ATTESTED

reportable_D is null and experimental_absolute_diameter_validated is false in every published document; simulated-size differences are not experimental absolute magnetic-core diameter accuracy.

```json
{
 "schema": "iscat168.estimates_new.1",
 "run_id": "v168-20261029T114726Z-a0bdd10c07ff",
 "task_count": 23,
 "state_counts": {
  "FINISHED": 23
 },
 "estimator_read_access": false,
 "reportable_D": null,
 "experimental_absolute_diameter_validated": false
}
```

### A19_failure_register_complete - ATTESTED

The register names the failed step and both blocked steps; nothing was deleted or hidden.

```json
{
 "path": "results/v168/controller_only/failure_records_v168-20261029T114726Z-a0bdd10c07ff.json",
 "scalars": {
  "record_count": 3,
  "deleted_records": 0,
  "hidden_records": 0,
  "model_calls": 0,
  "reportable_D": null
 },
 "records": [
  {
   "record_type": "CONTROLLER_STEP_FAILED",
   "step": "estimates",
   "blocked_by": null,
   "error_type": "TypeError",
   "error": "Object of type ndarray is not JSON serializable",
   "reason": null
  },
  {
   "record_type": "CONTROLLER_STEP_BLOCKED",
   "step": "seal",
   "blocked_by": "estimates",
   "error_type": null,
   "error": null,
   "reason": "an earlier step failed; no budget was spent here"
  },
  {
   "record_type": "CONTROLLER_STEP_BLOCKED",
   "step": "validate",
   "blocked_by": "estimates",
   "error_type": null,
   "error": null,
   "reason": "an earlier step failed; no budget was spent here"
  }
 ]
}
```

### A20_append_only_history_correction - ATTESTED_WITH_CAVEAT

The earlier primary status.json still asserts "23 of 23 tasks sealed" and the earlier primary failure_records.json still asserts record_count 0. Their bytes are preserved unchanged; the correcting files are published beside them and are listed in history_corrections.md.

```json
{
 "primary_status_bytes": 2297,
 "primary_status_sha256": "3a97e58abd335b287ee980af1a8efb8600c474801241c567fc927cf82eb8131b",
 "primary_status_P3_verification": "23 of 23 tasks sealed",
 "primary_status_git_head": "5dbfeec8c1655d360f3fdb6ae38d94e617d0d087",
 "primary_failure_records_bytes": 191,
 "primary_failure_records_sha256": "c3d6c4f5f6fae09099e2810d830265a17b225a2b59643e5006deee6ad5a7a5b7",
 "primary_failure_record_count": 0,
 "superseding_status_sha256": "78309f6162e29030197a1bf02182758631f6aec0465b35954b52c24aa48cb039",
 "superseding_failure_records_sha256": "1d507ecc091a5dccde9922e0851e08e2d83c8138208be182bf8423b2002b1641",
 "rule": "append-only: the earlier bytes stay, the correction is a new file beside them"
}
```

### A21_repairs_covered_by_tests_after_the_round - ATTESTED_WITH_CAVEAT

The executor, rehearsal, isolation and reporting repairs are covered by the live production suite (212 tests, 0 failures). Those tests were added after the round spent its budget, so they prove the repaired executor, not the consumed round.

```json
{
 "live_suite": {
  "junit": "work/junit_v168final.xml",
  "tests": 212,
  "failures": 0,
  "errors": 0,
  "skipped": 0,
  "seconds": 415.132,
  "test_suite_sha256": "fb9f6885555d82bd495abd320c178f455b0ddecc5d7d5f8a128f2acd12ddcdcb",
  "code_identity_sha256": "e0c1d736bfbccae400a2ffad35de8195e01551d60dd234a30dd1dc3c1422ef71",
  "code_file_count": 52,
  "git_head": "4e4a7a13cb26c3680da5922a8707989a11c449b3"
 },
 "release_the_round_was_authorized_under": {
  "workflow_run_id": "full_003",
  "receipt_sha256": "02c91971e1e2e6fb5d21a740bd81ed94e2c7dabdd1f9f1104db0846000c793d6",
  "git_head": "5dbfeec8c1655d360f3fdb6ae38d94e617d0d087",
  "code_identity_sha256": "a0bdd10c07ff58609728f6721e018d356e9afdf5d5ed846a120bf4286e77ec27",
  "code_file_count": 50,
  "test_suite_sha256": "c7521e2c2b7cf1850e6d6d50d15c44a2751c5d47323be212dcb2ae150e7a0992",
  "total_tests_recorded": 285,
  "real_f2c_constructions_during_tests": 0,
  "model_calls": 0,
  "zero_charged_calls_proved": true,
  "all_suites_green": true
 },
 "note": "full_004 was not built: a new release run needs a new authorization"
}
```

### A22_repair_cannot_be_exercised_on_the_consumed_round - BLOCKED

Re-running the estimates step needs a prepare pass and a new run identity, which would buy budget that is not authorized. EVIDENCE_ONLY_STEPS was not widened and no fresh retry was used to dodge the limit.

```json
{
 "closing_steps_allowed_for_evidence_only": [
  "tables",
  "records",
  "status",
  "manifest",
  "verification"
 ],
 "replaying_estimates_would_require": "prepare + a new run identity + new budget",
 "authorized_round_exit_code": 1,
 "authorized_round_ledger_used": 3171
}
```

### A23_no_test_weakened_for_a_pass - ATTESTED

No assertion was loosened to obtain a pass; the two reporting expectations were moved to a stricter seal-aware string and a new test pins both branches of it.

```json
{
 "commit": "4e4a7a1 4e4a7a1 V168: the failed round must be able to report itself",
 "files_touched_by_the_reporting_fix_commit": [
  "tools/v168/v168_controller.py",
  "tools/v168/v168_test_binding.py",
  "tools/v168/run_all.py",
  "tools/v168/tests/test_v168_estimate_publication.py",
  "tools/v168/tests/test_v168_failure_register_and_pack.py",
  "tools/v168/tests/test_v168_reporting.py"
 ],
 "new_test_name": "test_v168_p3_only_names_a_seal_once_the_seal_file_exists",
 "strict_change": "reporting expectations moved to the seal-aware string; none removed"
}
```

### A24_read_only_path_spends_nothing - ATTESTED

--readonly-report and the pack closing pass constructed no model, charged no call and wrote no fit: model_calls 0 in every document they publish.

```json
{
 "closing_trace": {
  "run_id": "v168-20261029T114726Z-a0bdd10c07ff",
  "exit_code": 0,
  "requested_steps": [
   "tables",
   "records",
   "status",
   "manifest",
   "verification"
  ],
  "model_constructions_in_process": 0,
  "read_only_control_path": true,
  "steps": [
   {
    "status": "OK",
    "step": "tables",
    "summary": {},
    "wall_seconds": 0.109
   },
   {
    "status": "OK",
    "step": "records",
    "summary": {
     "record_count": 3
    },
    "wall_seconds": 0.016
   },
   {
    "status": "OK",
    "step": "status",
    "summary": {},
    "wall_seconds": 0.015
   },
   {
    "status": "OK",
    "step": "manifest",
    "summary": {
     "file_count": 10899
    },
    "wall_seconds": 4.25
   },
   {
    "status": "OK",
    "step": "verification",
    "summary": {
     "contract_pins_matched": 4
    },
    "wall_seconds": 0.047
   }
  ]
 },
 "verification_model_calls": 0,
 "manifest_model_calls": 0
}
```

### A25_failure_delivery_is_real - ATTESTED

The failure pack gate refuses a zero-exit round, more than one run identity, a non-read-only closing pass, a failed step missing from the register and an unexplained absent artefact. It is exercised by the production suite and used here; the archive itself is named by failure_package_receipt.json, written after this report.

```json
{
 "authorized_round_exit_code": 1,
 "failed_step": "estimates",
 "blocked_steps": [
  "seal",
  "validate"
 ],
 "closing_pass_read_only": true,
 "run_identities_in_traces": [
  "v168-20261029T114726Z-a0bdd10c07ff"
 ]
}
```

### A26_exit_code_is_not_acceptance - ATTESTED

No stage of this delivery treats a zero exit code, a green suite, byte-exact replay or a packaged archive as scientific acceptance.

```json
{
 "release_scope_statement": "These inventories exercise the guard, loader, planning and persistence logic on real pytest runs. They do not validate experimental absolute diameter accuracy, and they are not the authorized V168 fit.",
 "P4_scientific_scope": "byte-level reproduction of published answers only",
 "P3_scientific_scope": "simulated F2c development fits only",
 "final_verify": {
  "execution_state": "FINISHED",
  "db_state": "FINISHED",
  "logical_items": 63,
  "distinct_theta": 39,
  "verified": 39,
  "not_verifiable": 0,
  "actual_calls": 39,
  "no_fabricated_theta": true,
  "meets_minimum_logical_items": true,
  "signature": "da4521486495de45a3eb66b72bbe96da49a7db9e8de474311a13e250be9f04a2",
  "reportable_D": null
 }
}
```

## The authorized round, step by step

From `results/v168/controller_only/step_sequence.json` (round trace). Requested steps `prepare,bind,run,tables,final,estimates,seal,validate,records,status`, exit code **1**, `failed_step=estimates`, `blocked_steps=['seal', 'validate']`, `model_constructions_in_process=1`.


| step | status | wall s | published summary | error_type | blocked_by |
|---|---|---|---|---|---|
| prepare | OK | 8.125 | {"budget_total": 9999, "code_identity_sha256": "a0bdd10c07ff58609728f6721e018d356e9afdf5d5ed846a120bf4286e77ec27", "dry_run": false, "git_head": "5dbfeec8c1655d360f3fdb6ae38d94e617d0d087", "model_calls": 0, "run_id": "v168-20261029T114726Z-a0bdd10c07ff", "task | - | - |
| bind | OK | 9.469 | {"authorized_constructions": 1, "binding_status": "VERIFIED", "model_calls": 87} | - | - |
| run | OK | 103.828 | {"model_calls": 3045, "tasks_executed_this_round": 23, "tasks_planned": 23} | - | - |
| tables | OK | 0.156 | - | - | - |
| final | OK | 0.813 | {"actual_calls": 39, "db_state": "FINISHED", "distinct_theta": 39, "execution_state": "FINISHED", "logical_items": 63, "model_calls": 39, "not_verifiable": 0, "verified": 39} | - | - |
| estimates | FAILED | 0.031 | - | TypeError | - |
| seal | BLOCKED | - | - | - | estimates |
| validate | BLOCKED | - | - | - | estimates |
| records | OK | 0.016 | {"record_count": 0} | - | - |
| status | OK | 0.0 | - | - | - |

## Failure register, verbatim

`results/v168/controller_only/failure_records_v168-20261029T114726Z-a0bdd10c07ff.json` - 3 records, `deleted_records=0`, `hidden_records=0`. The primary `failure_records.json` beside it still holds `record_count: 0` from the crash pass itself; see H3.


```json
{
 "deleted_records": 0,
 "hidden_records": 0,
 "model_calls": 0,
 "record_count": 3,
 "records": [
  {
   "blocked_by": null,
   "error": "Object of type ndarray is not JSON serializable",
   "error_type": "TypeError",
   "reason": null,
   "record_type": "CONTROLLER_STEP_FAILED",
   "step": "estimates",
   "traceback_tail": "Traceback (most recent call last):\n  File \"C:\\iscat\\v168\\tools\\v168\\v168_controller.py\", line 2779, in main\n    result = prepare(dry_run=args.dry_run) if name == \"prepare\" else _dispatch(name, ctx)\n                                                                     ^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\iscat\\v168\\tools\\v168\\v168_controller.py\", line 2663, in _dispatch\n    return estimates_documents(ctx)\n           ^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\iscat\\v168\\tools\\v168\\v168_controller.py\", line 2010, in estimates_documents\n    _stage_json(mpath, merge)\n  File \"C:\\iscat\\v168\\tools\\v168\\v168_controller.py\", line 979, in _stage_json\n    raw = canon(document)\n          ^^^^^^^^^^^^^^^\n  File \"C:\\iscat\\v168\\tools\\v168\\v168_common.py\", line 266, in canon\n    return (json.dumps(value, ensure_ascii=False, sort_keys=True,\n            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\ProgramData\\anaconda3\\Lib\\json\\__init__.py\", line 238, in dumps\n    **kw).encode(obj)\n          ^^^^^^^^^^^\n  File \"C:\\ProgramData\\anaconda3\\Lib\\json\\encoder.py\", line 200, in encode\n    chunks = self.iterencode(o, _one_shot=True)\n             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\ProgramData\\anaconda3\\Lib\\json\\encoder.py\", line 258, in iterencode\n    return _iterencode(o, 0)\n           ^^^^^^^^^^^^^^^^^\n  File \"C:\\ProgramData\\anaconda3\\Lib\\json\\encoder.py\", line 180, in default\n    raise TypeError(f'Object of type {o.__class__.__name__} '\nTypeError: Object of type ndarray is not JSON serializable\n"
  },
  {
   "blocked_by": "estimates",
   "error": null,
   "error_type": null,
   "reason": "an earlier step failed; no budget was spent here",
   "record_type": "CONTROLLER_STEP_BLOCKED",
   "step": "seal",
   "traceback_tail": null
  },
  {
   "blocked_by": "estimates",
   "error": null,
   "error_type": null,
   "reason": "an earlier step failed; no budget was spent here",
   "record_type": "CONTROLLER_STEP_BLOCKED",
   "step": "validate",
   "traceback_tail": null
  }
 ],
 "reportable_D": null,
 "run_id": "v168-20261029T114726Z-a0bdd10c07ff",
 "schema": "iscat168.failure_records.1"
}
```

## Four scenarios, twelve existing camera images, and their detection states

Bound by the `full_003` release receipt before the round was authorized: 4 scenarios, 12 camera images from the frozen pilot array `results/v143/validation/camera_pilot/conditional_camera_arrays.h5` (sha256 `074305df1b6bbd47f7f523b05d871312309e9b6ffa390cd50d0be18296427e26`), with `new_random_draws: 0` and `model_calls: 0`. This round re-read those bytes at these hashes and produced no new image, exposure, noise draw, BEM or render. The detection column is the frozen high-background detector result carried forward unchanged; ANON_01 is 0/3 and stays undetected.


| scenario | frames | images | detected | camera event ids | frames sha256 | source context | source context sha256 | git blob |
|---|---|---|---|---|---|---|---|---|
| ANON_01 | 3 | 3 | 0/3 | 00, 01, 02 | 270fc04294243f1d1e76 | results/v166/source_context/ANON_01.json | 8e76165f427abb497406 | 34245110e902279674d018c89956a196cc9dc67b |
| ANON_02 | 3 | 3 | 3/3 | 00, 01, 02 | d8644c7416eb6dcd57ca | results/v166/source_context/ANON_02.json | fa382000dd036ff5c738 | 9951e37cf5800d2faebd6d48b70d3006ed8ddd5c |
| ANON_03 | 3 | 3 | 3/3 | 00, 01, 02 | 44365aae557010b39b69 | results/v166/source_context/ANON_03.json | 3b68864d1a86b4506095 | fc6b96235da156af60963fd8a115869e1dbc949a |
| ANON_04 | 3 | 3 | 3/3 | 00, 01, 02 | 2fef08e44e4a77e551d1 | results/v166/source_context/ANON_04.json | 0b991b11a1b33d7bc948 | cc96018d42cac465c4f58593232b4f2ed629a6bc |

The twelve events are `B100000_<ANON_0n>_<00..02>` for n = 1..4, three frames each, and each jail received only the three-frame document of its own group: `estimator_inputs/00_isolation_receipt.json` records `tasks_with_exactly_three_files: 23` and `single_reading_per_task: True` for all 23 tasks.

## Budget actually consumed

| phase | cap | used by the round |
|---|---|---|
| BIAS_STRESS | 7,200 | 2,685 |
| FINAL_VERIFY | 600 | 39 |
| MODEL_BINDING | 199 | 87 |
| SEARCH_EXTENSION | 2,000 | 360 |

total new authority **9,999**, used **3,171**, phase transfers **0**. Historical V167 charge carried **1**, combined ceiling **10,000**, so combined consumption after this round is **3,172** of 10,000. V166's 4,937 attempts are earlier history listed separately and are not part of this ceiling.

| ledger | bytes | attempt rows | attempt states | task rows | cache-hit log lines |
|---|---|---|---|---|---|
| results/v168/logs/v168_budget.sqlite | 3,403,776 | 3,171 | {'RETURNED': 3171} | 26 | 333 |



The 333 cache-hit replies are recorded per start in `per_start_table.json` and are never counted as charged calls; 3,045 of the 3,171 charged calls belong to the `run` step, 87 to model binding (loader self-check 70 + binding 17) and 39 to the independent final verify.

## The 23 tasks as published

From `run_round.json` (23/23 planned tasks executed this round, `failures: []`, `tasks_reused_from_sealed_ledger: []`, `reportable_D: null`).


| source task | kind | group/replicate/sigma | actual calls | charged | cache hits | execution_state | db_state | best Q_total | result sha (12) |
|---|---|---|---|---|---|---|---|---|---|
| B100000_ANON_04_H1_R01 | BIAS_STRESS | ANON_04/1/sigma1.0 | 135 | 135 | 18 | FINISHED | FINISHED | 493.3729 | 32f15b293a5e |
| B100000_ANON_03_H1_R01 | BIAS_STRESS | ANON_03/1/sigma1.0 | 315 | 315 | 18 | FINISHED | FINISHED | 482.374992 | e67fd26ba3ec |
| B100000_ANON_04_H1_R02 | BIAS_STRESS | ANON_04/2/sigma1.0 | 126 | 126 | 18 | FINISHED | FINISHED | 493.047306 | c8a544099910 |
| B100000_ANON_02_H1_R02 | BIAS_STRESS | ANON_02/2/sigma1.0 | 154 | 154 | 18 | FINISHED | FINISHED | 527.915918 | 91cf803ae76d |
| B100000_ANON_01_H1_R02 | SEARCH_EXTENSION | ANON_01/2/sigma1.0 | 79 | 79 | 2 | FINISHED | FINISHED | 501.415031 | e7bd0d9845e2 |
| B100000_ANON_02_H1_R00 | BIAS_STRESS | ANON_02/0/sigma1.0 | 145 | 145 | 18 | FINISHED | FINISHED | 527.866876 | 7a017c089621 |
| B100000_ANON_04_H1_R00 | BIAS_STRESS | ANON_04/0/sigma1.0 | 144 | 144 | 18 | FINISHED | FINISHED | 492.861459 | d912f1a63296 |
| B100000_ANON_01_H1_R01 | SEARCH_EXTENSION | ANON_01/1/sigma1.0 | 79 | 79 | 2 | FINISHED | FINISHED | 501.310624 | 9773a25d9f62 |
| B100000_ANON_02_H1_R01 | BIAS_STRESS | ANON_02/1/sigma1.0 | 136 | 136 | 18 | FINISHED | FINISHED | 527.608659 | eebe5bb2ecc1 |
| B100000_ANON_01_H1_R00 | SEARCH_EXTENSION | ANON_01/0/sigma1.0 | 43 | 43 | 2 | FINISHED | FINISHED | 501.105742 | 941524ad7109 |
| B100000_ANON_04_H1_R00 | BIAS_STRESS | ANON_04/0/sigma1.0 | 135 | 135 | 18 | FINISHED | FINISHED | 493.842071 | 398fbb397457 |
| B100000_ANON_03_H1_R00 | BIAS_STRESS | ANON_03/0/sigma1.0 | 108 | 108 | 18 | FINISHED | FINISHED | 474.786396 | 4ec83df7ac92 |
| B100000_ANON_01_H10_R01 | SEARCH_EXTENSION | ANON_01/1/sigma10.0 | 98 | 98 | 1 | FINISHED | FINISHED | 501.067702 | a3a2c7e35560 |
| B100000_ANON_04_H1_R02 | BIAS_STRESS | ANON_04/2/sigma1.0 | 136 | 136 | 18 | FINISHED | FINISHED | 494.732862 | 58e9501908b1 |
| B100000_ANON_01_H10_R00 | SEARCH_EXTENSION | ANON_01/0/sigma10.0 | 61 | 61 | 2 | FINISHED | FINISHED | 500.902794 | e21b33c6c2ce |
| B100000_ANON_02_H1_R01 | BIAS_STRESS | ANON_02/1/sigma1.0 | 145 | 145 | 18 | FINISHED | FINISHED | 527.835113 | bc721a1c617a |
| B100000_ANON_03_H1_R02 | BIAS_STRESS | ANON_03/2/sigma1.0 | 108 | 108 | 18 | FINISHED | FINISHED | 474.810751 | f085c6d16137 |
| B100000_ANON_02_H1_R02 | BIAS_STRESS | ANON_02/2/sigma1.0 | 136 | 136 | 18 | FINISHED | FINISHED | 527.671012 | 1722c5c10331 |
| B100000_ANON_04_H1_R01 | BIAS_STRESS | ANON_04/1/sigma1.0 | 149 | 149 | 18 | FINISHED | FINISHED | 493.264209 | 9c831e9a3a4f |
| B100000_ANON_03_H1_R01 | BIAS_STRESS | ANON_03/1/sigma1.0 | 117 | 117 | 18 | FINISHED | FINISHED | 475.024841 | 72b2cbc5eca5 |
| B100000_ANON_03_H1_R00 | BIAS_STRESS | ANON_03/0/sigma1.0 | 189 | 189 | 18 | FINISHED | FINISHED | 478.386242 | cbbbdd65a3ef |
| B100000_ANON_03_H1_R02 | BIAS_STRESS | ANON_03/2/sigma1.0 | 171 | 171 | 18 | FINISHED | FINISHED | 477.637494 | 0ff70839566b |
| B100000_ANON_02_H1_R00 | BIAS_STRESS | ANON_02/0/sigma1.0 | 136 | 136 | 18 | FINISHED | FINISHED | 527.633152 | b847f13aa7da |


## All 41 start records

From `per_start_table.json` (`row_count: 41`, `state_counts: FINISHED: 41`, every row `pass_index: 1`, every `local_cap: 400`, `error: null` everywhere, and sums charged 3,045 / cache hits 333 / evaluations 3,378).


| source task | start | kind | phase | pass | cap | charged | cache | evals | state | opt success | pred sha | C sha | error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B100000_ANON_01_H10_R00 | 0 | SEARCH_EXTENSION | SEARCH_EXTENSION | 1 | 400 | 61 | 2 | 63 | FINISHED | True | d7d4a9a2679d | 61ea8abdc419 | - |
| B100000_ANON_01_H10_R01 | 0 | SEARCH_EXTENSION | SEARCH_EXTENSION | 1 | 400 | 98 | 1 | 99 | FINISHED | True | 289f4350d95f | 54614fbb2512 | - |
| B100000_ANON_01_H1_R00 | 0 | SEARCH_EXTENSION | SEARCH_EXTENSION | 1 | 400 | 43 | 2 | 45 | FINISHED | True | 142521c023eb | 061cbd3bcc46 | - |
| B100000_ANON_01_H1_R01 | 0 | SEARCH_EXTENSION | SEARCH_EXTENSION | 1 | 400 | 79 | 2 | 81 | FINISHED | True | d4bce1fba07a | 17ce18421b18 | - |
| B100000_ANON_01_H1_R02 | 0 | SEARCH_EXTENSION | SEARCH_EXTENSION | 1 | 400 | 79 | 2 | 81 | FINISHED | True | 18bef4cfd0b1 | 9a348f21c946 | - |
| B100000_ANON_02_H1_R00 | 0 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 45 | 9 | 54 | FINISHED | True | 5b977c0e70f5 | 69ae341fb999 | - |
| B100000_ANON_02_H1_R00 | 0 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 45 | 9 | 54 | FINISHED | True | d1a4e2eebee2 | b429c0af6387 | - |
| B100000_ANON_02_H1_R00 | 1 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 91 | 9 | 100 | FINISHED | True | fb952ebd8005 | cbcbfe582bcc | - |
| B100000_ANON_02_H1_R00 | 1 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 100 | 9 | 109 | FINISHED | True | 8cf090b36083 | c256d9dbd271 | - |
| B100000_ANON_02_H1_R01 | 0 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 45 | 9 | 54 | FINISHED | True | 95c92fe88ccf | 9f45a9ae75d8 | - |
| B100000_ANON_02_H1_R01 | 0 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 45 | 9 | 54 | FINISHED | True | 5eabc6c3e0e9 | 0ea62bfa12a7 | - |
| B100000_ANON_02_H1_R01 | 1 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 91 | 9 | 100 | FINISHED | True | 0746456f7376 | c78ca3fdc616 | - |
| B100000_ANON_02_H1_R01 | 1 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 100 | 9 | 109 | FINISHED | True | 3c510ffc2079 | ea6b36456baa | - |
| B100000_ANON_02_H1_R02 | 0 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 45 | 9 | 54 | FINISHED | True | 02b6b9758cb2 | d01d83141f16 | - |
| B100000_ANON_02_H1_R02 | 0 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 45 | 9 | 54 | FINISHED | True | 6e15e5181171 | 12073f59660b | - |
| B100000_ANON_02_H1_R02 | 1 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 91 | 9 | 100 | FINISHED | True | 0f3986e57723 | 605ec3202157 | - |
| B100000_ANON_02_H1_R02 | 1 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 109 | 9 | 118 | FINISHED | True | 85bbcef956bc | 35247b738764 | - |
| B100000_ANON_03_H1_R00 | 0 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 27 | 9 | 36 | FINISHED | True | cd33288b7f66 | 72710bacb535 | - |
| B100000_ANON_03_H1_R00 | 0 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 72 | 9 | 81 | FINISHED | True | 19a71650255c | 95b2e1b40464 | - |
| B100000_ANON_03_H1_R00 | 1 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 81 | 9 | 90 | FINISHED | True | 1081cd9c5404 | f0d57fc0bbf6 | - |
| B100000_ANON_03_H1_R00 | 1 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 117 | 9 | 126 | FINISHED | True | efd132d7d05e | fe19b14861b6 | - |
| B100000_ANON_03_H1_R01 | 0 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 36 | 9 | 45 | FINISHED | True | b81932d923db | 572fb62070ef | - |
| B100000_ANON_03_H1_R01 | 0 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 135 | 9 | 144 | FINISHED | True | 2f037715139f | 8a570e6de92c | - |
| B100000_ANON_03_H1_R01 | 1 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 81 | 9 | 90 | FINISHED | True | 0c74e9d12f6c | ed285a5265ea | - |
| B100000_ANON_03_H1_R01 | 1 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 180 | 9 | 189 | FINISHED | True | 8a22e5af4a13 | f5602ad5be89 | - |
| B100000_ANON_03_H1_R02 | 0 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 27 | 9 | 36 | FINISHED | True | 95570254966f | e16596c1e985 | - |
| B100000_ANON_03_H1_R02 | 0 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 63 | 9 | 72 | FINISHED | True | e95ae1693f74 | 26035268969e | - |
| B100000_ANON_03_H1_R02 | 1 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 81 | 9 | 90 | FINISHED | True | 691a99883e40 | 171221156b19 | - |
| B100000_ANON_03_H1_R02 | 1 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 108 | 9 | 117 | FINISHED | True | a5a06de15921 | 16862d5c85c2 | - |
| B100000_ANON_04_H1_R00 | 0 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 63 | 9 | 72 | FINISHED | True | e22b49978fbe | fadad284765f | - |
| B100000_ANON_04_H1_R00 | 0 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 54 | 9 | 63 | FINISHED | True | 3455eee99ef1 | 50833b8198c1 | - |
| B100000_ANON_04_H1_R00 | 1 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 81 | 9 | 90 | FINISHED | True | d4a0b5af4638 | 46eaee6eb91e | - |
| B100000_ANON_04_H1_R00 | 1 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 81 | 9 | 90 | FINISHED | True | e204916358f4 | 543d017b8707 | - |
| B100000_ANON_04_H1_R01 | 0 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 68 | 9 | 77 | FINISHED | True | 04f169a4fa95 | 66a107a1b027 | - |
| B100000_ANON_04_H1_R01 | 0 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 54 | 9 | 63 | FINISHED | True | 6b6655e6de46 | 9e247845a2e7 | - |
| B100000_ANON_04_H1_R01 | 1 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 81 | 9 | 90 | FINISHED | True | 42f52a80bb7b | 9e20e2173460 | - |
| B100000_ANON_04_H1_R01 | 1 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 81 | 9 | 90 | FINISHED | True | 5b1bffc03566 | 1a442d6139d4 | - |
| B100000_ANON_04_H1_R02 | 0 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 45 | 9 | 54 | FINISHED | True | d370a069cb03 | d00f301b8361 | - |
| B100000_ANON_04_H1_R02 | 0 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 55 | 9 | 64 | FINISHED | True | 6332b0a71595 | 26d95b3ca3dd | - |
| B100000_ANON_04_H1_R02 | 1 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 81 | 9 | 90 | FINISHED | True | 5d44ce92271f | 97500af2b4fd | - |
| B100000_ANON_04_H1_R02 | 1 | BIAS_STRESS | BIAS_STRESS | 1 | 200 | 81 | 9 | 90 | FINISHED | True | 27f6b9d6608b | 94b1b5076ae5 | - |

## Commands actually used

```text
# P0 read-only forensics (no model, no budget)
python -X utf8 tools/v168/v168_recovery_gate.py --old-ledger results/v167/logs/v167_budget.sqlite --out results/v168/audit/v167_ledger_native.json
# production suite, live tree (212 tests, 415 s)
python -X utf8 -m pytest tools/v168/tests -p no:cacheprovider -q --junitxml=work/junit_v168final.xml
# workstation test release the round was authorized under (full_003, 285 tests, 0 charged calls)
python -X utf8 tools/v168/run_all.py --workstation-tests --run-id full_003
# the authorized round (exit 1, failed_step=estimates)
python -X utf8 tools/v168/v168_controller.py --steps prepare,bind,run,tables,final,estimates,seal,validate,records,status
# read-only reporting path (0 constructions, 0 charged calls)
python -X utf8 tools/v168/v168_controller.py --readonly-report
# these three reports, in this order (work/ is not shipped in the code identity)
python -X utf8 work/p_report_truth.py
python -X utf8 work/p_report_corrections.py
python -X utf8 work/p_report_readme.py
# the failure return package
python -X utf8 tools/v168/run_all.py --pack-failure
```

`--workstation-tests --run-id full_004` is the CLI default and was **not** executed: a new release run against the repaired tree would need a new authorization, and the round's capsule is pinned to `full_003`.

## Deliverable index (bytes and SHA-256 at report time)

| file | bytes | sha256 |
|---|---|---|
| `results/v168/00_execution_truth_report.md` | 78,446 | `cb0d46fa27a12b76864afe25e6132810442be204392d34084055c1473139cab3` |
| `results/v168/history_corrections.md` | 14,631 | `14b44416b7925bdb3598828c94c20f07d7ddb0cc63971c6ce9267d3c693af86e` |
| `results/v168/README_V168_RETURN.md` ABSENT | - | - |
| `results/v168/status.json (primary, superseded)` | 2,297 | `3a97e58abd335b287ee980af1a8efb8600c474801241c567fc927cf82eb8131b` |
| `results/v168/status_v168-20261029T114726Z-a0bdd10c07ff.json (correcting)` | 2,332 | `78309f6162e29030197a1bf02182758631f6aec0465b35954b52c24aa48cb039` |
| `results/v168/manifest.json (primary)` | 1,941,290 | `4265e524b581e827165c90fc8c7ec8dda2e9e198d45b8dff28fc0a0e0960ce45` |
| `results/v168/manifest_v168-20261029T114726Z-a0bdd10c07ff.json (file_count 10,899)` | 2,046,975 | `7fc01ec9eba50c91e0eb062105e807d6245c229e2607a29d627a643127bde096` |
| `results/v168/verification_v168-20261029T114726Z-a0bdd10c07ff.json` | 2,401 | `d4ef1b24288f31ae26134f71d7134d082757ec37ff4a377d34623c72df38b702` |
| `results/v168/estimates_new.json` | 44,146 | `a776200ab697b0b625233587aa8eece25bea51d8300e556cf68a33ce6169e4d6` |
| `results/v168/controller_only/failure_records.json (primary, superseded)` | 191 | `c3d6c4f5f6fae09099e2810d830265a17b225a2b59643e5006deee6ad5a7a5b7` |
| `results/v168/controller_only/failure_records_v168-20261029T114726Z-a0bdd10c07ff.json` | 2,381 | `1d507ecc091a5dccde9922e0851e08e2d83c8138208be182bf8423b2002b1641` |
| `results/v168/controller_only/step_sequence.json (round trace)` | 3,451 | `af881e30a6d91d6e7d8d2d32dcad27eeba4de9113ecfc8e88261269699d1b724` |
| `results/v168/controller_only/step_sequence_v168-20261029T114726Z-a0bdd10c07ff_001.json (closing pass)` | 765 | `08966f4fd98849f702a4b7afafb75acc98555b053c2c2d0e19e5b0b8cc68f6c0` |
| `results/v168/controller_only/run_identity.json` | 384 | `fdcd2469f840c553a840ac668b2a2a0b42638b45db35c25c288b04ba0c8c329f` |
| `results/v168/controller_only/frozen_execution_capsule.json` | 5,242 | `104e5f7e63212ae9075a9655f6ff476cbad91bcfacae8f46394200b5ae8283ec` |
| `results/v168/controller_only/run_round.json` | 13,062 | `35ca4b4254d707ac433d0af6b429c30a4e923581e6091b3bcb03842bb64f7b4a` |
| `results/v168/controller_only/per_start_table.json` | 55,677 | `df7768180a5b6a9765d1dfadf8a46c1dbd5fb9d1aa0129a1d76b0747aa3f5e06` |
| `results/v168/controller_only/b_stress_table.json` | 40,913 | `7e9bdbd0ed085d8d4bff2459a62f93078526ed6b207b1af3d7de0cf3b48fcb9f` |
| `results/v168/controller_only/r_merge_table.json` | 15,784 | `14bf88067871290994ded1090a62a973b04c2521cd395854e920eab14c6b9477` |
| `results/v168/controller_only/final_verify.json` | 32,180 | `e93271796ab6ecb95f5f1207e5a7bd0022c24cd1f15302147e0114805679086e` |
| `results/v168/controller_only/bind_model.json` | 16,781 | `1e5d5818fb266f6581dce228c4da32babb863ffd84ddd27771878e8e05fe5e17` |
| `results/v168/controller_only/source_mapping.json` | 46,531 | `cdadb07678f2c9c9c99ec31f7e63d2ed92775dab09075d71cec85a9204028b22` |
| `results/v168/estimator_inputs/00_isolation_receipt.json` | 2,625 | `567d68fcacc3609019fd32734e4c03360a5d6ab5c250c4cd3d15b57263afdf33` |
| `results/v168/logs/v168_budget.sqlite` | 3,403,776 | `0c49ca2ed7643cea879210b0dc8b42459e0a35f93275f8f688fc0c431584ca45` |
| `results/v168/logs/model_construction.json` | 15,503 | `9d189b3974a7d5ccaa9c2252690b55c91ea04bc45e6723c1abd8c3fd26d8c990` |
| `results/v168/logs/controller_run_20261029T114718Z.log` | 17,880 | `1501c396610c0526b641a5c8e7c2011b46b9f0989fcd178e69010a49a0d16d3f` |
| `results/v168/workstation_tests/full_003/workstation_test_release_receipt.json` ABSENT | - | - |
| `results/v168/audit/history_charge_reconciliation.json` | 1,600 | `8d641ecc3495d44ea30e56a1711fd0683685404af60004292e53491ce31561ee` |
| `results/v168/audit/combined_budget_baseline.json` | 1,885 | `7f9e403a4cc5037243297cb5797f2381db02092e7d0fe1667a83bf32f7390247` |
| `results/v168/audit/old_ledger_hash_snapshot.json` | 604 | `69df805cca26293c814d2e3bddf7977d88b644379ba96e00662ba8cc06e99a75` |
| `results/v168/audit/v167_ledger_native.json` | 1,593 | `6430aea1f788fd459143836b3671de2daecefd0c03e33954e5fd19e7f6566f6b` |
| `results/v168/audit/v167_handoff_zip_native_verification.json` | 1,449 | `6ee790cd40fff5e5f9e5a9947fdf111bcf303df6e579ced56185ff6d9efdc3a6` |
| `results/v168/audit/old_source_resolvability.json` | 5,460 | `40a092f661d800895354e00ebba8e2e4f86d5b8c461e61b70fef46a02f8b936e` |
| `results/v168/audit/evidence_set_separation.json` | 1,824 | `631227eea9e67fe687d61bdd41808dbaefa757940dedd38e13551eaaef84460f` |
| `results/v168_prepared/controller_only/plan.json` | 12,261 | `48727dbd9cbf14e09a6e4d6d7fe2c3d20af7d9a8d1106b049fcdc240ac03621c` |

The `full_003` receipts and workflow receipt above are the release the round was authorized under; `full_001` and `full_002` exist only as WITHDRAWN receipts with their withdrawal files, and were not reused.

## Artefacts that do not exist, and why

| artefact | why it is absent | what that means for the claims |
|---|---|---|
| `results/v168/seal.json` | the `seal` step was BLOCKED by the `estimates` failure | no estimate was sealed, so no truth read and no post-seal score exist |
| `results/v168/estimates_merge_reuse.json` | the `estimates` step raised TypeError before publishing it | the R-merge reuse document is the artefact whose serialization killed the round; `r_merge_table.json` holds the same five rows in the form the tables step published |
| `results/v168/validator_only/` | the `validate` step was BLOCKED | independent truth scoring is NOT_STARTED |
| `results/v168/failure_package_notice.json` | written by `run_all.py --pack-failure` before the closing evidence pass, i.e. after this report | its absence here is an ordering fact, not a missing deliverable |
| `results/v168/failure_package_receipt.json`, the archive and its `.sha256` sidecar | the pack step writes them after the archive exists | `verification.json` carries `zip_sha256: null` for the same reason and names `run_all.py` as the step that fills it |

## Limits of what this round can support

- Nothing here is a blind test: the height readings are simulated and their generator truth hash is known to the controller, so any later score is a development score on simulated data.
- Because no seal exists, no R diagnostic score, no B three-scenario score, no `s_D,z` sensitivity and no second-order difference `c_D` can be reported as a result of this round. The prescribed b=-2/0/+2 columns are published per row in `b_stress_table.json` as candidate values only, with `reportable_D: null` on every row.
- ANON_01 remains **0/3** under the frozen high-background detector. The five R rows are supplemental local returns for previously partial searches; their `PARTIAL_SEARCH` origin is carried verbatim and is not rewritten into a historical success.
- The bias table keeps all 18 rows whether the result looked better or worse, `sigma_nm` stays 1.0, the offset is never fitted, and the historical witness is diagnostic only, never a third start. `r_merge_table.json` reports `state_counts: {"None": 5}` because its aggregation reads `execution_state` while these rows publish `new_execution_state`; that is a cosmetic field-name mismatch, the per-row state is `FINISHED`, and it is disclosed in `history_corrections.md` (H8) rather than patched, because `tools/v168` is frozen into the identity this round is pinned to.
- A green suite or a zero exit code is not acceptance. The pack step that writes the archive exits zero only to say the failure evidence was packaged intact.

## Ordering note

These three reports are authored before `--pack-failure` runs, so that the closing evidence pass of the pack hashes their bytes into the manifest and the archive carries them. That pack also runs a further read-only closing pass, which publishes a later versioned copy (`_002`) of `status`, `manifest` and `verification`; the files quoted above are the ones that existed when this report was written, and none of them is ever rewritten.
