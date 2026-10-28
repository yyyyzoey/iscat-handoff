# ISCAT V166 - Execution Authenticity Report (P5f)

Generated: 2026-10-28T10:27:07.278220Z | repo: C:\iscat\v166 | HEAD: af2078b2a2d545b8455b48d814faa12017e5e8ac

This report attests what was actually executed. It is not scientific acceptance. A zero exit code, a passing test suite, and `LEDGER_AND_ARTIFACT_BINDING_VERIFIED` are mechanical states only.

| # | Attestation | Status |
|---|---|---|
| A01_scene_protection | The V165 uncommitted worktree was snapshotted before any V166 write; no reset, clean, delete, overwrite or rename-fresh was applied. | ATTESTED |
| A02_no_test_files_edited | All five pre-existing production test modules are byte-identical to the V165 uncommitted originals; the repair touched production modules only. | ATTESTED |
| A03_three_known_failures_repaired | The three named V165 failures now pass in the committed production run. | ATTESTED |
| A04_production_collection_is_real | The delivered pytest receipts are real collections/outcomes of the committed bundle with source SHAs bound into the receipt. | ATTESTED |
| A05_single_charged_model_construction | Exactly one real model construction sequence was charged during execution. | ATTESTED |
| A06_sealed_loader_restart_refuses_reconstruction | A restart against a sealed loader blocks unfinished dependents rather than silently rebuilding the model. | ATTESTED |
| A07_truth_isolated_from_estimator_path | Truth SHAs and validator-only modules are absent from the estimator dependency path. | ATTESTED |
| A08_height_readings_generated_once | The 24 hypothetical height readings and 12 normals were generated exactly once from the frozen seed and never re-sampled. | ATTESTED |
| A09_task_matrix_is_the_original_28 | The executed matrix is exactly 4 anonymous particles x (1 baseline + 3 H1 + 3 H10), all retained. | ATTESTED |
| A10_billing_before_persist | Every charged F2c attempt precedes use of its result and every ledger attempt has a persisted array. | ATTESTED |
| A11_per_start_full_save | Every one of the 28 x 2 common starts persisted its complete parameter vector and loss before selection. | ATTESTED |
| A12_budget_within_cap | Total charged calls stayed inside the 12,000 cap with no re-billing of sealed identities. | ATTESTED |
| A13_estimates_sealed_before_truth | Estimates were sealed before any truth file was read for scoring; the file timeline is monotonic. | ATTESTED |
| A14_all_reportable_D_null | No task, start, best-fit, or report artifact carries a non-null reportable diameter. | ATTESTED |
| A15_ANON_01_not_reported_as_detected | ANON_01 is reported as not detected under the frozen high-background detector; its assisted groups stay null. | ATTESTED |
| A16_failures_record_absence | There is no results/v166/failures directory because no task raised an exception in the executed run; V165 failure records were preserved instead. | ATTESTED |
| A17_console_logging_caveat | The P4 console capture is short because the child process block-buffered stdout; timestamped progress was recorded outside the repo. | ATTESTED_WITH_CAVEAT |
| A18_budget_filename_discrepancy | The executed ledger is named v165_budget.sqlite inside the v166 tree while the contract names v166_budget.sqlite. | ATTESTED_WITH_CAVEAT |
| A19_exit_code_is_not_acceptance | No stage treats a zero exit code, a passing suite, or LEDGER_AND_ARTIFACT_BINDING_VERIFIED as scientific acceptance. | ATTESTED |

## Evidence detail

### A01_scene_protection - ATTESTED

The V165 uncommitted worktree was snapshotted before any V166 write; no reset, clean, delete, overwrite or rename-fresh was applied.

```json
{
 "comparison_report": {
  "bytes": 6458,
  "path": "p5_report/p0_snapshot_vs_current_code.json",
  "sha256": "1110f0dc6a89b910415206ece6f1362b8f0771638849fd5c326ec75939685bdd"
 },
 "p0_evidence_dir_file_counts": {
  "failures": 4,
  "preflight": 18,
  "unclassified": 21,
  "validator_only": 4,
  "workstation_tests": 37
 },
 "snapshot_files_compared": 110,
 "snapshot_root": "C:\\iscat\\v166_p0\\uncommitted",
 "snapshot_top_level_entries": 10,
 "state_counts": {
  "IDENTICAL": 23,
  "MODIFIED": 6,
  "SNAPSHOT_ONLY": 81
 },
 "tests_identical_to_snapshot": [
  "tools/v165_bundle/tests/conftest.py",
  "tools/v165_bundle/tests/test_generator_ids.py",
  "tools/v165_bundle/tests/test_height.py",
  "tools/v165_bundle/tests/test_production_workflow.py",
  "tools/v165_bundle/tests/test_validator.py"
 ],
 "tests_modified_vs_snapshot": [],
 "v165_head_preserved_as_parent_of_p1_commit": "bbe854c3a8c0427debc40f182fab64368de9ae23"
}
```

### A02_no_test_files_edited - ATTESTED

All five pre-existing production test modules are byte-identical to the V165 uncommitted originals; the repair touched production modules only.

```json
{
 "added_module_sha256": "7fd69068641e8a4cdbffd2230b0ffb588fea1ae1c4ee03e2ee4e8931e69cb025",
 "only_added_test_module": "tools/v165_bundle/tests/test_p1_fault_injections.py",
 "repair_diffs": {
  "bytes": 3118,
  "path": "p5_report/repair_diffs/_index.json",
  "sha256": "4dda196ec140f9acb3fed9939713a09c20df2b8a2dddbc2e746dab7a572f960d"
 },
 "repaired_production_modules": [
  "tools/gate_a.py",
  "tools/v165_bundle/code/v165_guard.py",
  "tools/v165_bundle/code/v165_io.py",
  "tools/v165_bundle/code/v165_receipts.py",
  "tools/v165_bundle/code/v165_run.py"
 ],
 "test_files_vs_snapshot": [
  {
   "path": "tools/v165_bundle/tests/conftest.py",
   "sha256": "fad16f46cb494d72ea962f33cc04587e8559a13648a9812b13a4985bb37cd6cf",
   "state": "IDENTICAL"
  },
  {
   "path": "tools/v165_bundle/tests/test_generator_ids.py",
   "sha256": "42b2f120ad7ce51d63dad3116f148480bbf3be9de98621e38c14c4bf2008c51d",
   "state": "IDENTICAL"
  },
  {
   "path": "tools/v165_bundle/tests/test_height.py",
   "sha256": "9acf55e820704983f1b34a6dfd68e76ab56cc6313c132f1231d6c284f57b76b7",
   "state": "IDENTICAL"
  },
  {
   "path": "tools/v165_bundle/tests/test_production_workflow.py",
   "sha256": "45f2be957958a2a60db6859bdaa7edfc96087d57d979bff280109c47ad3c2068",
   "state": "IDENTICAL"
  },
  {
   "path": "tools/v165_bundle/tests/test_validator.py",
   "sha256": "8d985b218e467f053d087657c67954f21e8543258434c160093e1c502c71103c",
   "state": "IDENTICAL"
  }
 ]
}
```

### A03_three_known_failures_repaired - ATTESTED

The three named V165 failures now pass in the committed production run.

```json
{
 "after_repair_29_passed": {
  "bytes": 101,
  "path": "workstation_tests/p1_after_repair_001/pytest_output.txt",
  "sha256": "0e7476bbc07c6a8faefb7508563c1a183ac002f75d3850d7ca0e3da6324ae1fc"
 },
 "after_repair_41_passed": {
  "bytes": 101,
  "path": "workstation_tests/p1_after_repair_002/pytest_output.txt",
  "sha256": "741c3bf7f09bc9a5b368bb2a6d5a2f7e0a9ae27f33a556d433e1eceaeca53fcc"
 },
 "named_test_outcomes_in_production_run": [
  "tests/test_production_workflow.py::test_execute_constructs_model_once_and_preserves_all_task_states -> passed",
  "tests/test_production_workflow.py::test_restart_with_sealed_loader_blocks_unfinished_dependents -> passed",
  "tests/test_production_workflow.py::test_test_suite_does_not_import_real_model_or_have_truth_literals -> passed"
 ],
 "named_tests": [
  "test_execute_constructs_model_once_and_preserves_all_task_states",
  "test_restart_with_sealed_loader_blocks_unfinished_dependents",
  "test_test_suite_does_not_import_real_model_or_have_truth_literals"
 ],
 "pre_repair_output": {
  "bytes": 929,
  "path": "workstation_tests/p1_baseline_pre_repair_001/pytest_output.txt",
  "sha256": "5cae2914113f9d021e92f94645c8577052e6b283b041d548cd096d4b17b95f28"
 },
 "pre_repair_summary": "3 failed, 26 passed in 1.93s"
}
```

### A04_production_collection_is_real - ATTESTED

The delivered pytest receipts are real collections/outcomes of the committed bundle with source SHAs bound into the receipt.

```json
{
 "collected_items": 41,
 "collection_errors": 0,
 "collection_report": {
  "bytes": 3802,
  "path": "workstation_tests/p1_collection_001/pytest_outcomes.json",
  "sha256": "9d8725f0d00c18c3a1236c6ef74c3f041cc75639b86c6ce49ad5e30b87291036"
 },
 "command_receipt": {
  "bytes": 790,
  "path": "workstation_tests/production_001/command_receipt.json",
  "sha256": "2ef7b9e3cc675c36bf1487aba29fcb59c598f6c48f7b7e556490389a537657a2"
 },
 "production_exitstatus": 0,
 "production_outcomes": {
  "bytes": 24605,
  "path": "workstation_tests/production_001/pytest_outcomes.json",
  "sha256": "9846f6d28a2937cda4f61a16bdb18651e9f99fbbe4d460e7e1c91c064f3a2f25"
 },
 "production_reports": 123,
 "real_F2c_calls_during_tests": 0,
 "receipt_outcomes_sha256": "9846f6d28a2937cda4f61a16bdb18651e9f99fbbe4d460e7e1c91c064f3a2f25",
 "receipt_output_sha256": "17ecef18670b7d1fc9ef10727d0a583730265282dd01d03115a237312282d31f",
 "receipt_scope": "COMPONENT_SYNTHETIC_FAULT_AND_ISOLATION_TESTS_NOT_PHYSICAL_VALIDATION",
 "source_files_hash_bound": 24,
 "test_receipt": {
  "bytes": 5845,
  "path": "workstation_tests/production_001/test_receipt.json",
  "sha256": "ddbaf835969d65660f742d9be217743103deba5800d001e7903b0abe842cffd0"
 }
}
```

### A05_single_charged_model_construction - ATTESTED

Exactly one real model construction sequence was charged during execution.

```json
{
 "MODEL_BINDING_cap": 200,
 "MODEL_BINDING_phase": {
  "BINDING": 24,
  "LOADER_1": 70
 },
 "MODEL_BINDING_total": 94,
 "guard_installed_once": true,
 "ledger_owner": "v165-single-process",
 "verification_new_model_calls": 0
}
```

Caveat: Reconstruction count is evidenced by ledger charges plus the passing single-construction test; it is not independently re-observable after the run.

### A06_sealed_loader_restart_refuses_reconstruction - ATTESTED

A restart against a sealed loader blocks unfinished dependents rather than silently rebuilding the model.

```json
{
 "covering_tests": [
  "tests/test_production_workflow.py::test_restart_with_sealed_loader_blocks_unfinished_dependents"
 ],
 "fault_injection_module": "tools/v165_bundle/tests/test_p1_fault_injections.py",
 "final_verify_new_model_calls": 0,
 "final_verify_scope": "READONLY_STORED_EVIDENCE_NOT_NEW_MODEL_REPLAY",
 "model_calls_during_test_suite": 0
}
```

### A07_truth_isolated_from_estimator_path - ATTESTED

Truth SHAs and validator-only modules are absent from the estimator dependency path.

```json
{
 "audit_module_relocated_to": "validator/v165_truth_audit.py",
 "covered_by": "test_test_suite_does_not_import_real_model_or_have_truth_literals (passed)",
 "denied_import_attempts": [],
 "denied_open_attempts": [],
 "guard_deny_dir_prefixes": [
  "results/v142/validation/",
  "results/v165/validator_only/"
 ],
 "guard_deny_module_prefixes": [
  "v165_truth_audit",
  "v165_generate_height",
  "v165_validator"
 ],
 "p2_gate_a_isolation": {
  "bytes": 1245,
  "path": "p2_gate_a_isolation_check.json",
  "sha256": "7645764e1dfc47dfec40ab5cc7717bbbdfd7cfb3c220e5005924853193a1da44"
 },
 "truth_literal_scan_offenders": []
}
```

Caveat: The guard is a Python-level audit hook, scope: PYTHON_LEVEL_AUDIT_HOOK_NOT_A_KERNEL_SANDBOX

### A08_height_readings_generated_once - ATTESTED

The 24 hypothetical height readings and 12 normals were generated exactly once from the frozen seed and never re-sampled.

```json
{
 "generator_console": {
  "bytes": 285,
  "path": "logs/p3_generate_console.txt",
  "sha256": "6b1252164b24a41d9de9b4f7db3b5851c864e85861351ba316de693fc285beac"
 },
 "groups": 4,
 "independent_normals_count": 12,
 "p3_verification": {
  "bytes": 3143,
  "path": "p3_height_readings/p3_verification.json",
  "sha256": "a0824769b5da1f1dc4753a6198e27723ddf57cedd9f6e0c026124c0ff5ac12a7"
 },
 "public_file": {
  "bytes": 8763,
  "path": "height_input/height_readings.json",
  "sha256": "bbfd793aff48247623081dd607168cd9afbba2deeff5f37c7a0cbd62b032ad4e"
 },
 "readings": 24,
 "sealed_truth_sidecar": {
  "bytes": 7032,
  "path": "results/v165/validator_only/v166_height_truth_sealed.json",
  "sha256": "acb3d44cb944d094a19575aaf6ce98da5d619e8318bf0fd00400a9d9c8ebbb06"
 },
 "seed": 16520261027,
 "sigma_nm": [
  1.0,
  10.0
 ]
}
```

Caveat: sigma=1 nm and sigma=10 nm reuse the same epsilon per (group, replicate): 24 readings from 12 independent draws, not 24 draws.

### A09_task_matrix_is_the_original_28 - ATTESTED

The executed matrix is exactly 4 anonymous particles x (1 baseline + 3 H1 + 3 H10), all retained.

```json
{
 "ledger_fit_tasks": 28,
 "per_condition": {
  "H1": 12,
  "H10": 12,
  "NO_HEIGHT": 4
 },
 "per_group": {
  "ANON_01": 7,
  "ANON_02": 7,
  "ANON_03": 7,
  "ANON_04": 7
 },
 "same_three_frame_gls_and_bounded_optimizer": "single preflight plan bound by SHA in seal.json",
 "states": {
  "BLOCKED": 0,
  "FAILED": 0,
  "FINISHED": 23,
  "PARTIAL_SEARCH": 5
 },
 "tasks_in_unified_table": 28,
 "unified_task_table": {
  "bytes": 47489,
  "path": "p5_report/unified_task_table.json",
  "sha256": "6ec092bf14aff48680d267eec8f67cfca6599fb09d344fe44e094966bb282edd"
 }
}
```

### A10_billing_before_persist - ATTESTED

Every charged F2c attempt precedes use of its result and every ledger attempt has a persisted array.

```json
{
 "attempt_states": {
  "RETURNED": 4937
 },
 "attempts_rows": 4937,
 "attempts_without_persisted_array": 0,
 "evaluation_files_persisted": 4811,
 "model_error_calls": 0,
 "per_task": [
  {
   "ledger_used": 245,
   "match": true,
   "prediction_files": 245,
   "task": "B100000_ANON_01_H10_R00"
  },
  {
   "ledger_used": 290,
   "match": true,
   "prediction_files": 290,
   "task": "B100000_ANON_01_H10_R01"
  },
  {
   "ledger_used": 314,
   "match": true,
   "prediction_files": 314,
   "task": "B100000_ANON_01_H10_R02"
  },
  {
   "ledger_used": 272,
   "match": true,
   "prediction_files": 272,
   "task": "B100000_ANON_01_H1_R00"
  },
  {
   "ledger_used": 290,
   "match": true,
   "prediction_files": 290,
   "task": "B100000_ANON_01_H1_R01"
  },
  {
   "ledger_used": 317,
   "match": true,
   "prediction_files": 317,
   "task": "B100000_ANON_01_H1_R02"
  },
  {
   "ledger_used": 47,
   "match": true,
   "prediction_files": 47,
   "task": "B100000_ANON_01_NO_HEIGHT"
  },
  {
   "ledger_used": 235,
   "match": true,
   "prediction_files": 235,
   "task": "B100000_ANON_02_H10_R00"
  },
  {
   "ledger_used": 242,
   "match": true,
   "prediction_files": 242,
   "task": "B100000_ANON_02_H10_R01"
  },
  {
   "ledger_used": 260,
   "match": true,
   "prediction_files": 260,
   "task": "B100000_ANON_02_H10_R02"
  },
  {
   "ledger_used": 163,
   "match": true,
   "prediction_files": 163,
   "task": "B100000_ANON_02_H1_R00"
  },
  {
   "ledger_used": 154,
   "match": true,
   "prediction_files": 154,
   "task": "B100000_ANON_02_H1_R01"
  },
  {
   "ledger_used": 163,
   "match": true,
   "prediction_files": 163,
   "task": "B100000_ANON_02_H1_R02"
  },
  {
   "ledger_used": 37,
   "match": true,
   "prediction_files": 37,
   "task": "B100000_ANON_02_NO_HEIGHT"
  },
  {
   "ledger_used": 72,
   "match": true,
   "prediction_files": 72,
   "task": "B100000_ANON_03_H10_R00"
  },
  {
   "ledger_used": 90,
   "match": true,
   "prediction_files": 90,
   "task": "B100000_ANON_03_H10_R01"
  },
  {
   "ledger_used": 81,
   "match": true,
   "prediction_files": 81,
   "task": "B100000_ANON_03_H10_R02"
  },
  {
   "ledger_used": 153,
   "match": true,
   "prediction_files": 153,
   "task": "B100000_ANON_03_H1_R00"
  },
  {
   "ledger_used": 171,
   "match": true,
   "prediction_files": 171,
   "task": "B100000_ANON_03_H1_R01"
  },
  {
   "ledger_used": 135,
   "match": true,
   "prediction_files": 135,
   "task": "B100000_ANON_03_H1_R02"
  },
  {
   "ledger_used": 36,
   "match": true,
   "prediction_files": 36,
   "task": "B100000_ANON_03_NO_HEIGHT"
  },
  {
   "ledger_used": 156,
   "match": true,
   "prediction_files": 156,
   "task": "B100000_ANON_04_H10_R00"
  },
  {
   "ledger_used": 159,
   "match": true,
   "prediction_files": 159,
   "task": "B100000_ANON_04_H10_R01"
  },
  {
   "ledger_used": 253,
   "match": true,
   "prediction_files": 253,
   "task": "B100000_ANON_04_H10_R02"
  },
  {
   "ledger_used": 144,
   "match": true,
   "prediction_files": 144,
   "task": "B100000_ANON_04_H1_R00"
  },
  {
   "ledger_used": 135,
   "match": true,
   "prediction_files": 135,
   "task": "B100000_ANON_04_H1_R01"
  },
  {
   "ledger_used": 153,
   "match": true,
   "prediction_files": 153,
   "task": "B100000_ANON_04_H1_R02"
  },
  {
   "ledger_used": 44,
   "match": true,
   "prediction_files": 44,
   "task": "B100000_ANON_04_NO_HEIGHT"
  },
  {
   "ledger_used": 24,
   "match": true,
   "prediction_files": 24,
   "task": "BINDING"
  },
  {
   "ledger_used": 32,
   "match": true,
   "prediction_files": 32,
   "task": "FINAL_VERIFY"
  },
  {
   "ledger_used": 70,
   "match": true,
   "prediction_files": 70,
   "task": "LOADER_1"
  }
 ],
 "tasks_checked": 31,
 "tasks_with_prediction_count_equal_to_ledger_used": 31
}
```

### A11_per_start_full_save - ATTESTED

Every one of the 28 x 2 common starts persisted its complete parameter vector and loss before selection.

```json
{
 "best_directories": 28,
 "max_half_cost_identity_abs_error": 5.684341886080802e-14,
 "per_start_results": {
  "bytes": 102062,
  "path": "p5_report/per_start_results.json",
  "sha256": "dd35a7852fa87dc400edd5a488d9df8a0d50a81296bdb45f5b95e10bdf88bf70"
 },
 "start_files_on_disk": 56,
 "start_states": {
  "FINISHED": 51,
  "PARTIAL_SEARCH": 5
 },
 "starts_in_per_start_table": 56,
 "starts_with_error": 5
}
```

### A12_budget_within_cap - ATTESTED

Total charged calls stayed inside the 12,000 cap with no re-billing of sealed identities.

```json
{
 "attempt_rows": 4937,
 "cap": 12000,
 "distinct_theta": 4468,
 "phases": {
  "FINAL_VERIFY": {
   "phase_authority": 600,
   "task_cap_sum": 600,
   "used": 32
  },
  "HEIGHT_FITS": {
   "phase_authority": 11200,
   "task_cap_sum": 11200,
   "used": 4811
  },
  "MODEL_BINDING": {
   "phase_authority": 200,
   "task_cap_sum": 200,
   "used": 94
  }
 },
 "theta_values_seen_more_than_once": 101,
 "total_used": 4937,
 "utilisation_percent": 41.142,
 "wall_clock_minutes": 38.98
}
```

### A13_estimates_sealed_before_truth - ATTESTED

Estimates were sealed before any truth file was read for scoring; the file timeline is monotonic.

```json
{
 "estimates_sha256": "8f97339e9645a29ec929e5c792d234a28821970338cf92a62d2982bfebba7634",
 "height_readings_sha256": "bbfd793aff48247623081dd607168cd9afbba2deeff5f37c7a0cbd62b032ad4e",
 "ledger_sha256": "254b5485164a57865328c81f8890ea4aa458d1386ed6f5f34533f2848f7e4ece",
 "preflight_sha256": "842f9a625c9704d4e1838c78c72ce522d39f0f946c01b249d22f2449cbc9b11e",
 "seal_flag": true,
 "seal_status": "SEALED_BEFORE_VALIDATOR",
 "utc_mtime_chain": [
  {
   "artifact": "results/v166/estimates.json",
   "mtime_utc": "2026-10-28T10:05:55.946126Z"
  },
  {
   "artifact": "results/v166/seal.json",
   "mtime_utc": "2026-10-28T10:05:56.017160Z"
  },
  {
   "artifact": "results/v166/verification.json",
   "mtime_utc": "2026-10-28T10:06:08.091428Z"
  },
  {
   "artifact": "results/v165/validator_only/v166_validator_score.json",
   "mtime_utc": "2026-10-28T10:06:48.252438Z"
  },
  {
   "artifact": "results/v166/p5_report/per_start_results.json",
   "mtime_utc": "2026-10-28T10:07:05.848631Z"
  },
  {
   "artifact": "results/v165/validator_only/v166_independent_score.json",
   "mtime_utc": "2026-10-28T10:07:23.993227Z"
  }
 ]
}
```

Caveat: mtime is corroborating single-workstation evidence, not a tamper-evident clock.

### A14_all_reportable_D_null - ATTESTED

No task, start, best-fit, or report artifact carries a non-null reportable diameter.

```json
{
 "execute_status_flag": true,
 "json_files_raw_scanned_under_tasks": 9919,
 "non_null_occurrences": 0,
 "offending_paths": [],
 "reportable_D_occurrences": 5741,
 "seal_flag": true,
 "unified_table_flag": true
}
```

### A15_ANON_01_not_reported_as_detected - ATTESTED

ANON_01 is reported as not detected under the frozen high-background detector; its assisted groups stay null.

```json
{
 "frozen_detections": {
  "ANON_01": [
   false,
   false,
   false
  ],
  "ANON_02": [
   true,
   true,
   true
  ],
  "ANON_03": [
   true,
   true,
   true
  ],
  "ANON_04": [
   true,
   true,
   true
  ]
 },
 "h10_scored_of_3": 1,
 "h1_scored_of_3": 0,
 "independent_score": {
  "path": "results/v165/validator_only/v166_independent_score.json",
  "sha256": "bf29b432e17117c942f20616733a212adc59463f25d89f43c0ae8efac6d9a0e5"
 },
 "primary_MAE_H1": null,
 "primary_MAE_H10": null,
 "primary_MAE_NO_HEIGHT": 13.054405824607887,
 "validator_score": {
  "path": "results/v165/validator_only/v166_validator_score.json",
  "sha256": "90e0ce25caa71db18f27db29f28dc8efc6cd13c6e8db8cbae3edb5150fb0d8ae"
 }
}
```

### A16_failures_record_absence - ATTESTED

There is no results/v166/failures directory because no task raised an exception in the executed run; V165 failure records were preserved instead.

```json
{
 "execute_status_fit_blocked": 0,
 "execute_status_fit_failed": 0,
 "final_verify_failures": [],
 "p0_retained_failure_record_files": 4,
 "results_v166_failures_exists": false
}
```

### A17_console_logging_caveat - ATTESTED_WITH_CAVEAT

The P4 console capture is short because the child process block-buffered stdout; timestamped progress was recorded outside the repo.

```json
{
 "authoritative_ledger": {
  "bytes": 6979584,
  "path": "results/v166/logs/v165_budget.sqlite",
  "sha256": "254b5485164a57865328c81f8890ea4aa458d1386ed6f5f34533f2848f7e4ece"
 },
 "external_progress_log": "C:\\Users\\PC\\Documents\\Codex\\2026-10-28\\sh\\work\\p4_watch_log.txt",
 "ledger_utc_window": [
  "2026-10-28T09:26:21.787490Z",
  "2026-10-28T10:05:20.447867Z"
 ],
 "p4_console": {
  "bytes": 619,
  "path": "logs/p4_execute_console.txt",
  "sha256": "1d6e380001558f3d9a3b9aaa07405f9ecab7173f561c5fba395c882aa7bf8d52"
 }
}
```

### A18_budget_filename_discrepancy - ATTESTED_WITH_CAVEAT

The executed ledger is named v165_budget.sqlite inside the v166 tree while the contract names v166_budget.sqlite.

```json
{
 "delivered_copy": "deliverables/budget/v166_budget.sqlite (byte-identical copy in the return ZIP)",
 "executed_path": "results/v166/logs/v165_budget.sqlite",
 "executed_sha256": "254b5485164a57865328c81f8890ea4aa458d1386ed6f5f34533f2848f7e4ece",
 "why_not_renamed": "renaming a file in the executed tree would have modified the protected scene; only a ZIP-side copy was made"
}
```

### A19_exit_code_is_not_acceptance - ATTESTED

No stage treats a zero exit code, a passing suite, or LEDGER_AND_ARTIFACT_BINDING_VERIFIED as scientific acceptance.

```json
{
 "contract_clause": "P5.6 - a failed or short stage must be reported as such; packaging is never scientific success",
 "execution_state": "FINISHED_WITH_PARTIAL_SEARCH",
 "experimental_absolute_diameter_validated": false,
 "scope": "OPENED_DEVELOPMENT_SIMULATED_HEIGHT_READINGS_NOT_REAL_SIZING",
 "verification_status": "LEDGER_AND_ARTIFACT_BINDING_VERIFIED"
}
```

## Not established

- any absolute diameter for ANON_01..ANON_04 (all reportable_D null)
- experimental magnetic-core absolute sizing accuracy
- validated improvement of H1 or H10 over the no-height baseline; primary group MAE is null for both
- an independent replication of the construction count beyond ledger charges and tests
- tamper-evident timing; mtime ordering is single-workstation evidence
- physical realism of the hypothetical height readings (camera noise independent assumption)

## Remaining / not started

- P5f result commit and single return ZIP
- no push performed; branch v166 exists only on this workstation
- raw prediction arrays stay on the workstation, excluded from the commit and manifest-listed instead

## Revision history

- SUPERSEDED_BEFORE_DELIVERY sha256=4af5d5bbb39754559afb7c926a34e7eb5a2d3e0c6d9264d965f94fbe827c758c - four attestation fields read wrong keys from the upstream P5 reports (state_counts, start_states, identity-error key, phases key); no evidence file or executed artifact was touched. The draft was not deleted: it was renamed and is retained beside this file as execution_authenticity_r1_superseded.json
