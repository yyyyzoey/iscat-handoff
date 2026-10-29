# ISCAT V168 - Return Package (authorized round FAILED at `estimates`)

Generated: 2026-10-29T13:37:22Z | repo `C:\iscat\v168` | branch `v168` | HEAD `4e4a7a13cb26c3680da5922a8707989a11c449b3` | run `v168-20261029T114726Z-a0bdd10c07ff`

| | code identity | production test suite |
|---|---|---|
| live tree at report time | `e0c1d736bfbccae400a2ffad35de8195e01551d60dd234a30dd1dc3c1422ef71` (52 files) | `fb9f6885555d82bd495abd320c178f455b0ddecc5d7d5f8a128f2acd12ddcdcb` (212 tests, 0 failures, 0 errors, 0 skipped, 415 s) |
| identity the authorized round ran under | `e0c1d736bfbccae400a2ffad35de8195e01551d60dd234a30dd1dc3c1422ef71` (50 files, git_head `5dbfeec8c1655d360f3fdb6ae38d94e617d0d087`) | `c7521e2c2b7cf1850e6d6d50d15c44a2751c5d47323be212dcb2ae150e7a0992` (285 tests in 3 suites) |

## Verdict

The round consumed **3,171 of 9,999** newly authorized model calls, made **0** random draws, executed **23 of 23** planned tasks over **41** starts, and then crashed while serializing the R-merge document in the `estimates` step. Its process exited **1**. `seal` and `validate` were blocked by that failure, so **no estimate was sealed and the independent truth score was never started**. This archive is the evidence of that failed round, packaged without re-running, re-charging or replacing anything. `this_archive_is_a_pass: false`.

Read `00_execution_truth_report.md` first. It is the only document here that states, per attestation, what was executed, what was verified, and what was not done.

## Archive layout

| prefix | members |
|---|---|
| (root) README_V168_RETURN.md | 1 |
| code | 44 |
| contract | 1 |
| deliverables | 1 |
| provenance | 2,924 |
| results | 10,966 |

Every member is listed with its SHA-256 and byte count in `ZIP_CONTENTS_SHA256.csv` at the archive root; that file is the authority on membership, not this table. `work/` (where these three report generators live) is not a shipped member, and neither is this archive itself or the receipts written after it.

## Reading order

1. `README_V168_RETURN.md` (this page)
2. `failure_package_notice.json` - what the archive claims to be, written before the manifest
3. `results/v168/00_execution_truth_report.md` - attestations, round trace, failure register, budget, 23 tasks, 41 starts
4. `results/v168/history_corrections.md` - the append-only corrections, including the false `23 of 23 tasks sealed` sentence in the primary status
5. `results/v168/controller_only/step_sequence.json` and `failure_records_v168-20261029T114726Z-a0bdd10c07ff.json`
6. `results/v168/audit/` - P0 forensics, V167 charge carry-over, old snapshot hashes, V167 archive verification
7. `results/v168/estimates_new.json`, `controller_only/{run_round,per_start_table,b_stress_table,r_merge_table,final_verify,bind_model}.json`
8. `results/v168/estimator_inputs/00_isolation_receipt.json` and the 23 jails
9. `results/v168/logs/v168_budget.sqlite` and `logs/cache_hits.jsonl`
10. `results/v168/workstation_tests/full_003/` - the release the round was authorized under

## What is what

| state | items |
|---|---|
| EXECUTED and VERIFIED | P0 scene protection and read-only forensics; P1 estimator input isolation; P2 single authorized model construction with F2/F2c binding |
| EXECUTED, persisted, not sealed | P3: 23 task results, 5 R second-start supplements, 18 fixed +/-2 nm bias tests, 41 start records, 3,171 charged calls |
| FINISHED (mechanical only) | P4 independent final verify: 63 logical items, 39 distinct theta, 39 verified, 0 not verifiable, 0 fabricated theta, 39 charged calls. Byte replay of published answers, not scientific acceptance |
| FAILED | `estimates` - `TypeError: Object of type ndarray is not JSON serializable` inside `canon()` while publishing `estimates_merge_reuse.json` (`v168_controller.py:2010`) |
| BLOCKED | `seal`, `validate` - both `blocked_by: estimates`, reason `an earlier step failed; no budget was spent here` |
| NOT_STARTED | independent truth scoring, `validator_only/`, post-seal R diagnostics, post-seal B three-scenario scoring, `s_D,z` sensitivity, `c_D` second difference |
| NOT EXECUTED | `run_all.py --workstation-tests --run-id full_004` (needs a new authorization); the V166 28-task suite (out of scope for this round); any resampling of the 24 height readings |

## Key SHA-256 values

| item | value |
|---|---|
| authorized round | `v168-20261029T114726Z-a0bdd10c07ff` |
| round code identity (50 files) | `e0c1d736bfbccae400a2ffad35de8195e01551d60dd234a30dd1dc3c1422ef71` |
| round git_head | `5dbfeec8c1655d360f3fdb6ae38d94e617d0d087` |
| plan sha256 | `48727dbd9cbf14e09a6e4d6d7fe2c3d20af7d9a8d1106b049fcdc240ac03621c` |
| authorization sha256 | `f8fb4b76f0ffc00eb5aa536f40180d250317afdfef8000c64fea7fa3e11d9f37` |
| capsule sha256 | `c168e8795338f9e275b4836f0e834de01fe59b22c1be7b0b5918e5309eb80651` |
| release receipt sha256 (full_003, 285 tests, 3 suites) | `02c91971e1e2e6fb5d21a740bd81ed94e2c7dabdd1f9f1104db0846000c793d6` |
| release test suite sha256 | `c7521e2c2b7cf1850e6d6d50d15c44a2751c5d47323be212dcb2ae150e7a0992` |
| live tree at report time (HEAD `4e4a7a1`) | code identity `e0c1d736bfbccae400a2ffad35de8195e01551d60dd234a30dd1dc3c1422ef71` (52 files), suite `fb9f6885555d82bd495abd320c178f455b0ddecc5d7d5f8a128f2acd12ddcdcb` (212 tests, 0 failures, 0 errors, 0 skipped) |
| model construction sha256 | `9d189b3974a7d5ccaa9c2252690b55c91ea04bc45e6723c1abd8c3fd26d8c990` |
| model id | `v142-F2c-75860d222dd8e90d8dc2e31111e52ccbbb212a01c0d6a0dfe7fdbcdb241c98c3` |
| new ledger | `0c49ca2ed7643cea879210b0dc8b42459e0a35f93275f8f688fc0c431584ca45` (3,403,776 bytes, 3,171 attempts, all RETURNED) |
| estimates document (unsealed) | `a776200ab697b0b625233587aa8eece25bea51d8300e556cf68a33ce6169e4d6` |
| R-merge table | `14bf88067871290994ded1090a62a973b04c2521cd395854e920eab14c6b9477` |
| B bias table | `7e9bdbd0ed085d8d4bff2459a62f93078526ed6b207b1af3d7de0cf3b48fcb9f` |
| per-start table (41 rows) | `df7768180a5b6a9765d1dfadf8a46c1dbd5fb9d1aa0129a1d76b0747aa3f5e06` |
| final verify | `e93271796ab6ecb95f5f1207e5a7bd0022c24cd1f15302147e0114805679086e` |
| isolation receipt | `567d68fcacc3609019fd32734e4c03360a5d6ab5c250c4cd3d15b57263afdf33` |
| correcting status | `78309f6162e29030197a1bf02182758631f6aec0465b35954b52c24aa48cb039` |
| correcting failure register | `1d507ecc091a5dccde9922e0851e08e2d83c8138208be182bf8423b2002b1641` |
| correcting manifest (file_count 10,899) | `7fc01ec9eba50c91e0eb062105e807d6245c229e2607a29d627a643127bde096` |
| correcting verification | `d4ef1b24288f31ae26134f71d7134d082757ec37ff4a377d34623c72df38b702` |
| seal.json | **ABSENT** - the seal step was BLOCKED |
| failure archive | written after this page by `run_all.py --pack-failure`; its SHA appears in `results/v168/failure_package_receipt.json`, `results/v168/iscat_v168_failure_return_001.zip.sha256` and `results/v168/audit/v168_failure_return_zip_verification.json` |

## V166 / V167 sources pinned by the contract, as observed

| pinned path | bytes | observed sha256 | result |
|---|---|---|---|
| results/v166/estimates.json | 18,258 | `8f97339e9645a29ec929e5c792d234a28821970338cf92a62d2982bfebba7634` | MATCH |
| results/v166/height_input/height_readings.json | 8,763 | `bbfd793aff48247623081dd607168cd9afbba2deeff5f37c7a0cbd62b032ad4e` | MATCH |
| results/v166/iscat_v166_return_001.zip | 17,554,667 | `866feed02333f244df72f55e38ccf74060962007a5010c5c29df5ebe9f16a74e` | MATCH |
| results/v166/logs/v165_budget.sqlite | 6,979,584 | `254b5485164a57865328c81f8890ea4aa458d1386ed6f5f34533f2848f7e4ece` | MATCH |

`verification.json` reports `4/4` pins matched and `old_evidence_read_only_confirmed: True`. The V167 ledger snapshot (24,576 bytes, sha256 `212fc61391070cc0d8f07e41d1a356f31d76a4aed713bfc8c0e0031ef1d1eb34`) is byte-equal before and after every V168 tool, and the V167 return archive was verified natively: 17 members, CRC pass clean, `model_or_budget_activity: NONE_READ_ONLY`.

## Reproduce

```text
# production suite against the live tree (212 tests)
python -X utf8 -m pytest tools/v168/tests -p no:cacheprovider -q --junitxml=work/junit_v168final.xml
# the authorized round, exactly as issued (exit 1; DO NOT re-run without new authorization)
python -X utf8 tools/v168/v168_controller.py --steps prepare,bind,run,tables,final,estimates,seal,validate,records,status
# read-only reporting path: 0 model constructions, 0 charged calls, no budget check
python -X utf8 tools/v168/v168_controller.py --readonly-report
# the three report generators, then the failure package
python -X utf8 work/p_report_truth.py
python -X utf8 work/p_report_corrections.py
python -X utf8 work/p_report_readme.py
python -X utf8 tools/v168/run_all.py --pack-failure
```

The pack step is the only writer of the archive; it refuses a second archive with the same name, refuses a round that exited zero, refuses more than one run identity, and refuses any absent deliverable whose step is not recorded as FAILED or BLOCKED in the register.

## Warnings for the reader

- `P4 final_verify FINISHED` means every published answer replays to the same bytes. It does not mean the fit is good, selected, sealed or accepted.
- `execution_state: FINISHED` on a task means its document was persisted and bound to the ledger. It is not a scientific verdict.
- `0 failures` in `run_round.json` is the executor's own record of task-level exceptions. The round still failed at a controller step, which is why `FAILED`, `BLOCKED` and `NOT_STARTED` coexist with it.
- Every diameter-like number in this package is a simulated-size candidate on frozen three-frame GLS data. `reportable_D` is null everywhere and `experimental_absolute_diameter_validated` is false. Nothing here is experimental absolute magnetic-core diameter accuracy, and ANON_01 remains undetected (0/3).
- The bias table's `witness_below_new_search` and per-row `D` values are candidates kept whether they look better or worse; no row, reading or failure was deleted, and no selection used true-parameter error.
- The primary `status.json` and `failure_records.json` in this archive carry the misleading bytes written by the crashing process on purpose. Use the versioned correcting files named in `history_corrections.md`; do not treat the primary names as current.

## What needs a decision from the user, not from Codex

To finish the research question this round was built for, someone must authorize a new run: the `estimates` serialization repair is already committed (`4e4a7a1`) and covered by the live suite, but applying it to the already-consumed round would need a `prepare` pass, a new run identity and new budget, and the combined 10,000-call ceiling leaves 6,828 calls of the authorized V168 continuation unspent. Codex did not spend, reserve or plan any of that here, and did not delete, re-sign or re-run the consumed round.
