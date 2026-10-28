# V167 return package - blocked round

This archive is the delivery of a **blocked** V167 round. It is not a gate pass, not a set
of fitted diameters, and not scientific acceptance. Git publication is delivery only
(contract section 10.6).

## What is in here

- Code: branch `v167`, HEAD `e4939e19f353f8118d98b97ae2af989f298315ea`, code identity
  `9d267addaf905669824b7c226a479d4dc233fed58afed2e8583a553dc8b07185`, clean tracked tree,
  46 hashed source files.
- P0: V166 evidence re-verified read-only; contract pins 4/4 match; `results/v166` never
  written to.
- P1: the mandated isolation repair - 23 estimator jail roots, each holding exactly one
  anonymous height reading plus its own group's three frames and six legal records;
  `estimator_inputs/00_isolation_receipt.json`.
- P2: a real production loader defect, the commit that fixes it, and one stranded charged
  call that is disclosed rather than reset.
- P3/P4: 23 estimator tasks and FINAL_VERIFY `BLOCKED`, 0 calls,
  `audit/v167_round1_blocked_task_table.json`.
- P5: `NOT_STARTED`; nothing was sealed, so nothing was scored.
- Verification: `workstation_tests/full_008/` - 177 tests green on these bytes with zero
  charged calls and unchanged source hashes.
- Budget: 1 of 10,000 authorized calls consumed
  (`logs/v167_budget.sqlite`, SHA-256
  `212fc61391070cc0d8f07e41d1a356f31d76a4aed713bfc8c0e0031ef1d1eb34`).

## Read in this order

1. `00_execution_truth_report.md` - stage states, budget, artifact gaps, scope limits.
2. `history_corrections.md` - two claims that were wrong and are now corrected, plus the
   identity chain and the stale rehearsal note.
3. `audit/v167_decision_required_pi.json` - the one decision only the PI can make.
4. `audit/v167_round1_resumability_audit.json` - the identity deadlock, measured: 26
   reservations, 24 signatures move, 2 stable.
5. `audit/v167_current_bytes_readonly_status.json` - the honest status of the delivered
   bytes. `status.json` beside it is stale evidence kept for the record, not current truth.

## What is not here, and why

- No `tasks/` per-start results, no estimate tables, no `seal.json`, no `validator_only/`
  scores, no `verification.json`: the round never reached a fit, and a seal may not precede
  estimates.
- No resampling: V166's 24 height readings and its ledger are referenced by pinned SHA,
  never regenerated.
- No `reportable_D` (null) and `experimental_absolute_diameter_validated` false; ANON_01
  remains 0/3 detected; the 5 V166 `PARTIAL_SEARCH` tasks were not promoted.

## Independent verification

```
python -X utf8 tools/v167/run_all.py --status
python -X utf8 tools/v167/run_all.py --workstation-tests --run-id full_008
python -X utf8 -m pytest tools/v167/tests -q
```

`--status` is read-only. `--pack` (the closing path) legitimately refuses on this tree with
`RUN_IDENTITY_CODE_CHANGED` and exit 2, which is itself part of the finding. External
SHA-256 of this ZIP is published beside the archive as a `.sha256` sidecar and in the branch
commit; the ZIP cannot contain its own digest.
