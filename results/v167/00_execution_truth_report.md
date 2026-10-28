# V167 execution truth report

Round `run_id`: `v167-20261028T190448Z-8cf9a24b19c5` (reserved, never executed).
Delivered code: branch `v167`, HEAD `e4939e19f353f8118d98b97ae2af989f298315ea`,
code identity `9d267addaf905669824b7c226a479d4dc233fed58afed2e8583a553dc8b07185`.
Contract plan SHA-256 `eeae31bb98bafa4893c1c993ebfb7c985a702f1bd32aaba75546c16bd4ebab5d`
(`plan_pinned_ok` true, re-hashed on disk).

**Overall state: BLOCKED.** One authorized model construction was charged and failed inside
the loader; 0 estimator passes, 0 sealed estimates and 0 validator scores exist for V167.
V166's published results are intact.

## P0 - protect the V165/V166 scene

- EXECUTION: `EXECUTED`
- VERIFICATION: `VERIFIED`
- EVIDENCE: `audit/v166_archive_ledger_recheck.json`
  (`630ea79d1f2e706e2d109139b5e49116ea06c5e1509aa60f9be050d4e3b16311`),
  `audit/v166_start_and_ledger_recheck.json` (`e2cb3c959f9e46c0b316aab1cf2b8dbf5d7bf5bac5bd50a532b8fcc6a7d949b0`),
  `audit/v167_p0c_identity_and_pins_recheck.json` (`c34fba196bdf60dcf63c6a69fb372e1ae06552d385c4d73866be1c8c83e7b2c4`),
  `audit/v167_refused_write_litter.json`
- SCIENTIFIC_SCOPE: read-only re-verification of already published V166 evidence; no new claim

Contract section 0 pins re-hashed on disk this session, all four match:

| pinned file | SHA-256 | match |
|---|---|---|
| `results/v166/estimates.json` | `8f97339e9645a29ec929e5c792d234a28821970338cf92a62d2982bfebba7634` | yes |
| `results/v166/height_input/height_readings.json` | `bbfd793aff48247623081dd607168cd9afbba2deeff5f37c7a0cbd62b032ad4e` | yes |
| `results/v166/logs/v165_budget.sqlite` | `254b5485164a57865328c81f8890ea4aa458d1386ed6f5f34533f2848f7e4ece` | yes |
| `results/v166/iscat_v166_return_001.zip` | `866feed02333f244df72f55e38ccf74060962007a5010c5c29df5ebe9f16a74e` | yes |
Re-checked V166 facts: return archive 17,554,667 B, 5,177 members, CRC clean,
`all_checks_pass` true, `wrote_inside_v166` false; V166 ledger opened read-only,
4,937 attempts all `RETURNED`, phase use FINAL_VERIFY 32/600, HEIGHT_FITS 4,811/11,200,
MODEL_BINDING 94/200, distinct theta 4,468; 28 estimates = 23 `FINISHED` + 5
`PARTIAL_SEARCH`; 56 starts = 51 `FINISHED` + 5 `PARTIAL_SEARCH`, `start_problems` empty;
56 starts recomputed with `all_match` true and worst absolute Q delta 0.0; the 24 frozen
readings are intact (seed 16520261027 documented in the public file, pairing residuals at
5.7e-14 nm). Refused-write litter (`.tmp.64480`) is disclosed, byte-identical to its
primary, and leaks no truth, seed or epsilon.

## P1 - estimator input isolation (the mandated repair)

- EXECUTION: `EXECUTED`
- VERIFICATION: `VERIFIED`
- EVIDENCE: `estimator_inputs/00_isolation_receipt.json`
  (`60c22bf048a92085dfbc638429181701ee2099ee241a0cb7d4b7275a8674e8bf`)
- SCIENTIFIC_SCOPE: `NON_ADVERSARIAL_PYTHON_RUNTIME_ISOLATION_NOT_A_KERNEL_SANDBOX`

The full paired height table no longer reaches the estimator. 23 jail roots, each with
exactly three files (`input.json` single reading, `frames.json` own group three frames,
`legal_records.json` own group six records): `single_reading_per_task` true,
`tasks_with_exactly_three_files` 23, `truth_valued_key_offenders_in_any_staged_document` 0,
`controlled_offset_exposed_to_estimator` false, `cross_sigma_sibling_exposed` false,
`model_calls` 0. 11 tests in `tools/v167/tests/test_v167_isolation.py` guard it. No field
was renamed, no string split, no test dropped to reach these numbers.

## P2 - model binding

- EXECUTION: `FAILED`
- VERIFICATION: `NOT_VERIFIED`
- EVIDENCE: `controller_only/step_sequence.json`
  (`2cff92b96f438fea7e27c3e870207a9f540f51442aed132c8c170ce93458387a`)
- SCIENTIFIC_SCOPE: no bound live model exists, so nothing downstream of bind was reachable

Under identity `8cf9a24b19c5e261478440d0de4376069a49a781a6eae179d809f11b99d536b8` the loader
charged one F2c forward (`theta [30.0, 350.0, 0.0, 0.0]`,
`theta_sha256 6cf3b6eee80372e1f36d11f746d18a1f8a81842d17e486ac2199fa53e486e588`, charge
digest `2d1dc88673faab8e8d7fe33e700f456ab9337ed8902d0a93f6220656f89294fc`) and then raised
`MODEL_ID_MISMATCH_IN_RETURN` while the frozen library self-check ran inside the
construction. The step sequence records `failed_step` `bind`, `exit_code` 1,
`model_constructions_in_process` 1, and blocked steps `run, final, estimates, seal,
validate`.

This was real production-code behaviour, not a test artefact. It was fixed at commit
`0526452` by verifying the loader return against the frozen F2c field parent, covered by 11
tests in `test_v167_model_identity.py`. Binding has succeeded in no V167 round.

**Stranded charge, disclosed not laundered:** that one charged forward never returned.
`reconcile_loader_orphans()` runs inside `bind()`, which is now unreachable, so the charge
stands as 1 consumed call. A charged attempt that did not return is not counted as zero.

## P3 - authorized computation (5 R + 18 B = 23 estimator tasks)

- EXECUTION: `BLOCKED`
- VERIFICATION: `NOT_EVALUATED`
- EVIDENCE: `audit/v167_round1_blocked_task_table.json`
  (`14f6821e37c158ce4b7f7ef723f0d8461358dc93067abe4e84bc733b92df6df5`),
  `controller_only/per_start_table.json`, `controller_only/b_stress_table.json`,
  `controller_only/r_merge_table.json`, `controller_only/failure_records.json`
- SCIENTIFIC_SCOPE: no fit ran, so V167 states nothing about diameter, error, MAE or bias

23 tasks reserved, all `execution_state` `BLOCKED`, `calls_used` 0 on every row, 0 per-start
rows. Cause: `prepare()` requires the pinned code identity to equal the identity of the
bytes on disk (`v167_controller.py:963`), and the mandated repairs moved that identity
`8cf9a24b19c5...` -> `c5e27bfb90db...` -> `9d267addaf90...`. `task_descriptor()` embeds the
identity in all 23 estimator signatures and in `V167_FINAL_VERIFY`: of 26 reservations, 24
signatures change and only 2 (`V167_LOADER_1`, `V167_BINDING`) are stable, and `reserve()`
refuses the changed ones with `StoreError:task signature changed`
(`audit/v167_round1_resumability_audit.json`,
`05bc8b77c3bb122b50059383f26b7df2c70406b730bc407e2500f61e3bd3fea6`). Two refusal logs are
kept: `logs/controller_run_20261028T193101Z.log`, `logs/controller_close_20261028T194417Z.log`.

## P4 - final verify

- EXECUTION: `BLOCKED`
- VERIFICATION: `NOT_EVALUATED`
- EVIDENCE: `audit/v167_round1_blocked_task_table.json`
- SCIENTIFIC_SCOPE: no sealed estimate exists to reproduce

## P5 - seal, then score

- EXECUTION: `NOT_STARTED`
- VERIFICATION: `NOT_STARTED`
- EVIDENCE: none; `validator_only/` is empty by design until estimates exist
- SCIENTIFIC_SCOPE: `NOT_EVALUATED` until the validator runs

## Budget

| phase | cap | used | tasks reserved |
|---|---:|---:|---:|
| MODEL_BINDING (loader self-check + binding) | 200 | 1 | 2 |
| SEARCH_EXTENSION (R: 5 unfinished second starts) | 2,000 | 0 | 5 |
| BIAS_STRESS (B: 18 fixed +/-2 nm trials) | 7,200 | 0 | 18 |
| FINAL_VERIFY | 600 | 0 | 1 |
| total | 10,000 | 1 | 26 |

Ledger `logs/v167_budget.sqlite`, SHA-256
`212fc61391070cc0d8f07e41d1a356f31d76a4aed713bfc8c0e0031ef1d1eb34`: 26 tasks all `RUNNING`,
attempts table holds exactly one row, state `CHARGED`, never settled. New real F2c calls
made while producing this report: **0**. No new random draw, height sample, BEM, render,
camera exposure, camera noise, fixed-D sweep or batch Jacobian: all zero (contract section
9). V166's remaining budget was not carried over.

## Workstation tests on the delivered bytes

- EXECUTION: `EXECUTED`
- VERIFICATION: `VERIFIED`
- EVIDENCE: `workstation_tests/full_008/workstation_test_receipt.json`
  (`96c3b7c77f4c2373c56d76d11c4b49b0702c818277f969d4a0c35e65e408c48b`)
- SCIENTIFIC_SCOPE: `LOCAL_TEST_INVENTORY_ONLY: synthetic forwards and plan guards, NOT
  physical validation and NOT the authorized V167 fit`

177 tests green in 3 suites - `v166_inherited_41` 41, `bundle_plan_and_core` 38,
`v167_production` 98 - with `all_suites_green` true, `zero_charged_calls_proved` true,
`source_hashes_unchanged` true, and the ledger never opened mid-run
(`budget_ledger_opened_mid_run` false, proof mode `differential_ledger_digest`: the ledger
digest, charge digest and 29 source hashes are identical before and after the run, and
`primary_task_dirs` stayed 0). A zero-attempt tripwire file
(`real_f2c_tripwire.txt`, `0ec689f1a9defc5a7973db3863e96608546ba228aa2543fc088241b6cbbca5fb`)
records `real_construction_attempts` 0. All 29 recorded source hashes were re-compared
against the files on disk after the run: no mismatch.

Per contract section 12, the bundle's 38 local tests must never be described as 23 real
simulations having passed. Neither may these 177.

## Contract section 11 artifacts: present and absent

| required item | state |
|---|---|
| `00_execution_truth_report.md` | present (this file) |
| `status.json` | present but stale (published under `8cf9a24b`, before the reporting fix); kept as record, see `audit/v167_current_bytes_readonly_status.json` (`8c8fadcb8359cd771a9470e0551451beb1373aab2a03164a66f8ee1fc59c01d1`) |
| `history_corrections.md` | present |
| `audit/` V166 rechecks and diffs | present |
| `workstation_tests/` full output, nodeids, outcomes, source hashes, zero-call tripwire | present (full_008) |
| `controller_only/` source mapping, bias plan SHAs | present, zero-call scaffolding |
| `estimator_inputs/` per-task projection + denial receipts | present |
| `logs/v167_budget.sqlite` | present (1 charge, 26 RUNNING reservations) |
| `tasks/` per-start parameters, C, all Q, best, states | **absent** - no estimator pass executed |
| separate estimate tables and `seal.json` | **absent** - nothing to seal |
| `validator_only/` post-seal scoring, direction/curvature, failure denominators | **absent** - scoring requires a seal first |
| `verification.json`, full manifest, ZIP external SHA | manifest and ZIP produced by the pack rehearsal; `verification.json` **absent** (FINAL_VERIFY blocked) |

## Scientific scope

- `reportable_D` = **null**; no diameter value may be quoted from V167.
- `experimental_absolute_diameter_validated` = **false**; a simulated fitted-diameter error
  is never experimental absolute diameter accuracy of the real device.
- ANON_01 detection remains **0/3** in the existing high-background test; that is not a
  successful diameter measurement and is not reported as one.
- V166 task states preserved verbatim: `v166_historical_states_rewritten` = 0; the 5
  `PARTIAL_SEARCH` stay partial, the 23 `FINISHED` stay finished.
- Bias trials were never run, so no direction or curvature table exists; the asymmetry
  question stays open.
- A clean process exit is not acceptance, and a Git push is delivery, not scientific
  acceptance (contract section 10.6).

## Decision still owed by the PI

`audit/v167_decision_required_pi.json`
(`46e6a9c3ccc36e3d57e25c34de969c5d3514a2f1e426a8b2819ef25b08a06dfc`) states the single
choice: authorize a fresh run identity and fresh ledger that carries the one stranded charge
forward, reducing this round's ceiling to 9,999; or accept the blocked round as the V167
delivery. Creating that state unilaterally would be the budget escape forbidden at contract
line 175, so no compute was started while waiting.
