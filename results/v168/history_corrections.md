# ISCAT V168 - Append-Only History Corrections

Generated: 2026-10-29T13:37:13Z | run `v168-20261029T114726Z-a0bdd10c07ff` | repo `C:\iscat\v168` | branch `v168` | HEAD `4e4a7a13cb26c3680da5922a8707989a11c449b3` | run `v168-20261029T114726Z-a0bdd10c07ff`

| | code identity | production test suite |
|---|---|---|
| live tree at report time | `e0c1d736bfbccae400a2ffad35de8195e01551d60dd234a30dd1dc3c1422ef71` (52 files) | `fb9f6885555d82bd495abd320c178f455b0ddecc5d7d5f8a128f2acd12ddcdcb` (212 tests, 0 failures, 0 errors, 0 skipped, 415 s) |
| identity the authorized round ran under | `e0c1d736bfbccae400a2ffad35de8195e01551d60dd234a30dd1dc3c1422ef71` (50 files, git_head `5dbfeec8c1655d360f3fdb6ae38d94e617d0d087`) | `c7521e2c2b7cf1850e6d6d50d15c44a2751c5d47323be212dcb2ae150e7a0992` (285 tests in 3 suites) |

Contract section 12 allows only appending: no earlier published byte is rewritten, renamed or deleted here. Where a statement turned out to be wrong, the wrong file keeps its bytes, this page quotes the wrong text verbatim, says what is true, and names the correcting file beside it with its SHA-256. My own in-session notes are corrected too (H5, H6, H7), so the record of how this round was understood is part of the evidence.

| id | what is being corrected | correcting artefact published |
|---|---|---|
| H1 | the V167 release confirmation queried the wrong table | yes |
| H2 | `23 of 23 tasks sealed` was asserted while no seal existed | yes |
| H3 | the failure register of the crashing process said it saw no failure | yes |
| H4 | a verification file was left empty | yes |
| H5 | my own working note about the code identity was wrong | note only |
| H6 | my own working note about leftover task directories was wrong | note only |
| H7 | artefact names used in earlier notes | note only |
| H8 | a cosmetic aggregation field in the R-merge table | yes |
| H9 | what the closing pass files supersede, and what they do not | yes |

## H1 - the V167 release confirmation queried the wrong table

Wrong statement, verbatim:

> The V167 workstation release receipt reported the old ledger as carrying no charged model attempt, because the confirmation helper read a `charges` table that this ledger does not use instead of `attempts`.

Where it lives: V167 return package `results/v167_prepared/pack_rehearsal/iscat_v167_rehearsal_20261028T204438Z.zip` (27,280,244 bytes, sha256 `273b20b94b1053f4f25de725ab29f4ee534e4997931c7284f27361927755fcae`), as recorded in section 1 of the V168 contract

True statement: The V167 ledger holds exactly one attempt row, `V167_LOADER_1` ledger_seq 1, theta `[30.0, 350.0, 0.0, 0.0]`, state `CHARGED`, timestamp 1793214295.0581424. It is still `CHARGED`: V168 carries it as historical consumption 1, asks for at most 9,999 new calls under the combined 10,000 ceiling, and invents neither a `RETURNED` state nor a qualifying prediction.

| correcting file | bytes | sha256 |
|---|---|---|
| `results/v168/audit/history_charge_reconciliation.json` | 1,600 | `8d641ecc3495d44ea30e56a1711fd0683685404af60004292e53491ce31561ee` |
| `results/v168/audit/old_ledger_hash_snapshot.json` | 604 | `69df805cca26293c814d2e3bddf7977d88b644379ba96e00662ba8cc06e99a75` |

Primary bytes: preserved unchanged, V167 is not modified by this page.

## H2 - `23 of 23 tasks sealed` was asserted while no seal existed

Wrong statement, verbatim:

> P3_authorized_computation.VERIFICATION = "23 of 23 tasks sealed"

Where it lives: `results/v168/status.json` (primary, 2,297 bytes, written by the crashing process at 19:49:21Z under git_head `5dbfeec...`, code identity `a0bdd10c07ff...`)

True statement: No seal was ever written. `seal.json` does not exist, the closing status reports P5 `NOT_STARTED`, and `verification.json` carries `seal_status: null` and `seal_sha256: null`. What is true about P3 is that 23 of 23 task result documents were persisted and hashed, which is a mechanical persistence state, not a seal and not an acceptance.

| correcting file | bytes | sha256 |
|---|---|---|
| `results/v168/status_v168-20261029T114726Z-a0bdd10c07ff.json = "23 of 23 task result documents persisted, not yet sealed"` | 2,332 | `78309f6162e29030197a1bf02182758631f6aec0465b35954b52c24aa48cb039` |

Primary bytes: preserved unchanged, `results/v168/status.json` is not modified by this page.

## H3 - the failure register of the crashing process said it saw no failure

Wrong statement, verbatim:

> record_count: 0 (191-byte register, deleted_records 0, hidden_records 0)

Where it lives: `results/v168/controller_only/failure_records.json`

True statement: The round has three register-worthy states: `estimates` FAILED with `TypeError: Object of type ndarray is not JSON serializable`, and `seal` plus `validate` BLOCKED by it. The crashed process could not record them because the round trace that names them is written when the process exits, after the `records` step had already run in dependency order. Commit `4e4a7a1` makes `records` read every published trace for the run plus the live trace, so the 20:55Z read-only closing pass published the three-record register beside the old file.

| correcting file | bytes | sha256 |
|---|---|---|
| `results/v168/controller_only/failure_records_v168-20261029T114726Z-a0bdd10c07ff.json (record_count 3, traceback tails included)` | 2,381 | `1d507ecc091a5dccde9922e0851e08e2d83c8138208be182bf8423b2002b1641` |
| `results/v168/controller_only/step_sequence.json (round trace, exit 1)` | 3,451 | `af881e30a6d91d6e7d8d2d32dcad27eeba4de9113ecfc8e88261269699d1b724` |

Primary bytes: preserved unchanged, `results/v168/controller_only/failure_records.json` is not modified by this page.

## H4 - a verification file was left empty

Wrong statement, verbatim:

> `results/v168/audit/v167_archive_native_verification.json` is 0 bytes (sha256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`, the empty-input digest)

Where it lives: `results/v168/audit/v167_archive_native_verification.json`

True statement: The file was produced by an interrupted audit run and contains no findings. Its bytes are retained untouched rather than deleted or overwritten; the real native verification of the V167 handoff archive is the hand-authored file with 17 members, `testzip()` CRC pass clean, 0 unsafe/symlink/duplicate paths, 16 payload hashes matching the inventory, one duplicate that agrees with the bundle copy, and `model_or_budget_activity: NONE_READ_ONLY`.

| correcting file | bytes | sha256 |
|---|---|---|
| `results/v168/audit/v167_archive_native_verification_zero_byte_disclosure.json` | 1,192 | `4387d4a41a41b0627995ef5ae3eca2e99e2c9cae8bef6b7b70962fb791d9846a` |
| `results/v168/audit/v167_handoff_zip_native_verification.json` | 1,449 | `6ee790cd40fff5e5f9e5a9947fdf111bcf303df6e579ced56185ff6d9efdc3a6` |

Primary bytes: preserved unchanged, `results/v168/audit/v167_archive_native_verification.json` is not modified by this page.

## H5 - my own working note about the code identity was wrong

Wrong statement, verbatim:

> `code_identities()` excludes `tools/v168/tests`

Where it lives: working notes of this session, not in any published artefact

True statement: The live code identity has 52 files, 14 of them under `tools/v168/tests/`; the exclusion that does exist is in `v168_test_binding.py` and applies to production-source binding, not to the identity hash. No shipped document repeated the wrong claim, and nothing was recomputed to make one.

No correcting artefact was needed: nothing shipped repeated the claim, and no published file was touched to make these notes accurate.

Primary bytes: preserved unchanged, working is not modified by this page.

## H6 - my own working note about leftover task directories was wrong

Wrong statement, verbatim:

> `results/v168/tasks/` contains pytest residue such as `V168_TESTPIPE*` / `V168_TESTSTARTQ0001`

Where it lives: working notes of this session

True statement: `results/v168/tasks/` holds exactly 26 directories: the 23 planned fits, each with a `result.json`, and 3 charged service identities (`V168_LOADER_1`, `V168_BINDING`, `V168_FINAL_VERIFY`) that hold predictions only and legitimately have no `result.json`. The pack gate counts the 23 plan entries, not the directory count.

No correcting artefact was needed: nothing shipped repeated the claim, and no published file was touched to make these notes accurate.

Primary bytes: preserved unchanged, working is not modified by this page.

## H7 - artefact names used in earlier notes

Wrong statement, verbatim:

> `bias_table.json`, `loader_seal.json`, `controller_run_20261029T114726Z.log`

Where it lives: working notes of this session

True statement: The published names are `b_stress_table.json` for the 18 fixed-offset rows, the loader seal lives inside `bind_model.json` (there is no separate seal file), and the only round transcript is `controller_run_20261029T114718Z.log`. `logs/controller_run.log` appears later, written by the packer's stable-log step.

No correcting artefact was needed: nothing shipped repeated the claim, and no published file was touched to make these notes accurate.

Primary bytes: preserved unchanged, working is not modified by this page.

## H8 - a cosmetic aggregation field in the R-merge table

Wrong statement, verbatim:

> state_counts: {"None": 5}

Where it lives: `results/v168/controller_only/r_merge_table.json`

True statement: The table builder counts states from `execution_state`, while these five rows publish their new state under `new_execution_state` (all `FINISHED`) so that the preserved old `PARTIAL_SEARCH` value cannot be mistaken for the new one. The per-row data is complete and correct. It is disclosed instead of patched because `tools/v168` is frozen into the identity the authorized round and its capsule are pinned to; editing it now would silently break `verify_history` for this evidence.

| correcting file | bytes | sha256 |
|---|---|---|
| `results/v168/controller_only/r_merge_table.json (per-row new_execution_state, old_execution_state_preserved_verbatim true)` | 15,784 | `14bf88067871290994ded1090a62a973b04c2521cd395854e920eab14c6b9477` |
| `results/v168/controller_only/b_stress_table.json` | 40,913 | `7e9bdbd0ed085d8d4bff2459a62f93078526ed6b207b1af3d7de0cf3b48fcb9f` |

Primary bytes: preserved unchanged, `results/v168/controller_only/r_merge_table.json` is not modified by this page.

## H9 - what the closing pass files supersede, and what they do not

Wrong statement, verbatim:

> the primary `manifest.json` / `verification.json` describe the tree as it stood before the reports existed (file_count 10,402)

Where it lives: `results/v168/manifest.json`, `results/v168/verification.json`

True statement: Those bytes stay. The read-only closing pass republished them versioned (file_count 10,899, 4/4 contract pins matched, `independent_acceptance: NOT_RUN_IN_CONTROLLER`, `zip_sha256: null` filled by the pack step). A manifest describes a file set, not a scientific result, and neither version says the round passed.

| correcting file | bytes | sha256 |
|---|---|---|
| `results/v168/manifest_v168-20261029T114726Z-a0bdd10c07ff.json` | 2,046,975 | `7fc01ec9eba50c91e0eb062105e807d6245c229e2607a29d627a643127bde096` |
| `results/v168/verification_v168-20261029T114726Z-a0bdd10c07ff.json` | 2,401 | `d4ef1b24288f31ae26134f71d7134d082757ec37ff4a377d34623c72df38b702` |

Primary bytes: preserved unchanged, `results/v168/manifest.json`, is not modified by this page.

## Charges and refusals, reported proactively

The contract requires every billing anomaly to be declared by the executor rather than discovered by the next review. For this round:

- the ledger holds 3,171 attempt rows, all `RETURNED`, and none `CHARGED` without an answer; there are 0 refunded calls, 0 phase transfers, and no row outside a declared phase cap;
- 333 forward requests were answered from the byte-exact prediction cache and were logged as cache hits, never as charged calls (3,045 charged + 333 cached = 3,378 evaluations in `per_start_table.json`);
- the model was constructed once, in the `bind` step, and the loader self-check and binding together spent 87 calls (70 + 17) against a cap that was tightened from 100 to 99 for binding;
- the independent final verify spent 39 charged calls for 63 logical items over 39 distinct theta, 0 not-verifiable, with no fabricated theta;
- nothing was charged after the `estimates` failure: the register records for both blocked steps the reason `an earlier step failed; no budget was spent here`;
- the single V167 CHARGED attempt remains unsettled and CHARGED in its untouched snapshot; V168 did not settle, refund or delete it (H1).

```json
{
 "v167_ledger_native": {
  "old_ledger_bytes": 24576,
  "old_ledger_sha256": "212fc61391070cc0d8f07e41d1a356f31d76a4aed713bfc8c0e0031ef1d1eb34",
  "old_attempts": 1,
  "old_used": 1,
  "historical_task_states": {
   "RUNNING": 26
  },
  "historical_unsettled_charge_count": 1,
  "refunded_calls": 0,
  "preserved_unsettled_state": true,
  "native_integrity_check": "ok",
  "new_model_calls": 0,
  "old_attempt_settled_by_this_tool": false
 },
 "old_snapshot": {
  "path": "C:\\iscat\\v168\\results\\v167\\logs\\v167_budget.sqlite",
  "sha256": "212fc61391070cc0d8f07e41d1a356f31d76a4aed713bfc8c0e0031ef1d1eb34",
  "declared_bytes": 24576,
  "actual_bytes": 24576,
  "match": true,
  "bytes_before_and_after_equal": true,
  "mutation_performed_by_any_v168_tool": false
 },
 "budget_baseline": {
  "combined_ceiling": 10000,
  "v168_new_ceiling": 9999,
  "historical_v167_consumed": 1,
  "combined_consumed_before_v168_run": 1,
  "combined_remaining_before_v168_run": 9999,
  "binding_cap_changed_from_v167": {
   "v167": 100,
   "v168": 99
  },
  "earlier_history_listed_separately": {
   "attempts": 4937,
   "ledger_path": "C:\\iscat\\v166\\results\\v166\\logs\\v165_budget.sqlite",
   "ledger_sha256": "254b5485164a57865328c81f8890ea4aa458d1386ed6f5f34533f2848f7e4ece",
   "note": "V166 spend is earlier project history; it is NOT part of this 10000 continuation allowance and is NOT deleted.",
   "read_mode": "sqlite3_uri_mode_ro",
   "round": "v166",
   "tasks_reserved": 31,
   "used_by_phase": {
    "FINAL_VERIFY": 32,
    "HEIGHT_FITS": 4811,
    "MODEL_BINDING": 94
   },
   "used_total": 4937
  },
  "authorization_sha256": "f8fb4b76f0ffc00eb5aa536f40180d250317afdfef8000c64fea7fa3e11d9f37"
 }
}
```
