# V167 history corrections

Append-only. Nothing listed here is deleted, renamed or rewritten in place; each earlier
file keeps its bytes so the record shows what was claimed and when it was corrected.

## 1. The status document claimed a round that never ran

`status.json` (SHA-256 `92259db0376b7678fe350008054a771b2dff9ada4b2c26389e576e404ef4dd76`,
published under identity `8cf9a24b19c5...` at HEAD `d0db5b741680cf072b9a4088a67b42930b309c93`)
reports:

- `P3_authorized_computation` -> `EXECUTION` `EXECUTED`, `VERIFICATION`
  `0 of 23 tasks sealed`
- `P4_final_verify` -> `VERIFICATION` `logical None / distinct None / verified None / not
  verifiable None`

Both are wrong. `controller_only/run_round.json` and `controller_only/final_verify.json` do
not exist on this tree, and no task of the round executed.

Root cause, in `status_document()` (`tools/v167/v167_controller.py:1869-1879`): each
document was merged with `published_versions` before the stage label tested it. A merged
dict is truthy even when the evidence file is absent, so `if round_doc` was always true, and
`round_doc.get("tasks_planned", 0)` printed `0 of 23 tasks sealed` - a number that reads as
an honest zero-completion line while still claiming the round was EXECUTED.

Fix at HEAD `e4939e19f353f8118d98b97ae2af989f298315ea`: `round_ran` and `final_ran` are
captured from `path.is_file()` before any merge, and every P3/P4 label gates on that
existence. Three regression tests were added to
`tools/v167/tests/test_v167_reporting.py` - absent receipt, receipt that records BLOCKED,
receipt from a real round. The stale `status.json` is deliberately left untouched; the
current bytes are described in `audit/v167_current_bytes_readonly_status.json`.

## 2. A derived byte-identity flag was compared against mismatched keys

`audit/v167_status_fix_scope_and_identity.json` (SHA-256
`be7574ed88f64341a71673065da93f5a5027935800ddcb995f74ba17cbd08198`) reports
`estimator_bytes_identical_to_round1` = `False`. The four estimator digests stored in it are
correct and do equal the round-1 values; the comparison was made between dicts whose keys
differ in prefix (`tools/v167/v167_common.py` versus `v167_common.py`), so it compared key
names as well as digests. Corrected in the companion
`audit/v167_status_fix_scope_and_identity_corrected.json` (SHA-256
`7cad89e82dc90ee97cc2e58f4289611f73053950e248f151c239ef6c4f6d51aa`), which carries a
per-module comparison and the digest of the file it supplements. Direction of the error: the
bug made the report too pessimistic, not too generous; it is corrected anyway so the number
is right.

## 3. Test counts must not be read as fit counts

Contract section 12 records that the bundle's 38 local planning and guard tests passed, and
that they must never be described as 23 real simulations. The delivered suite is 177 tests
(41 inherited + 38 bundle + 98 production, run `full_008`), and it is still software
evidence only: V167 has executed 0 estimator passes. The `bundle_plan_and_core` suite in
full_008 is the same 38 tests, re-run on the integrated tree, not new fits.

## 4. Task-count vocabulary

Four denominators appear in this round and are not interchangeable:

| number | meaning |
|---:|---|
| 28 | V166 published tasks (23 `FINISHED`, 5 `PARTIAL_SEARCH`) |
| 23 | V167 estimator tasks (5 R + 18 B) |
| 24 | frozen hypothetical height readings (V166 draw, never resampled) |
| 26 | V167 ledger reservations (23 estimator + loader + binding + final verify) |

## 5. Code identity chain and what each step cost

- `8cf9a24b19c5e261478440d0de4376069a49a781a6eae179d809f11b99d536b8` - HEAD
  `d0db5b741680cf072b9a4088a67b42930b309c93`: round 1 reserved 26 tasks, `bind` failed on the
  loader defect.
- `c5e27bfb90db1f5750376fd9aef43104cfc0eafa1c6d0cbf9260171278a9e0eb` - HEAD `0526452`: the
  loader return is verified against the frozen F2c field parent.
- `9d267addaf905669824b7c226a479d4dc233fed58afed2e8583a553dc8b07185` - HEAD
  `e4939e19f353f8118d98b97ae2af989f298315ea`: the reporting-honesty repair.

24 of 26 signatures move with any committed edit; only `V167_LOADER_1` and `V167_BINDING`
are stable because their descriptors carry no code identity. The estimator surface is
byte-identical across all three identities - `v167_common.py` `fe261c072fbe73935e0a73eb465c14df596618f5e89a524fb0935bc177898d95`,
`v167_jail.py` `9fc9b46a2353d4626240a47271dd890a3119aa613f9e764df955cc57c7dfb721`,
`v167_rpc.py` `6281d75c4ae2ca7124ceae79def163b8bdeee5584affff0d1c037533977731bd`,
`v167_worker.py` `c237779ef1a9c4eff14594495c3e0929970357cf091edc4b3c6128439979b964` - so no
scientific definition moved. The seven frozen-literal identity checks are true on the
current bytes.

## 6. Stale rehearsal archives

`results/v167_prepared/pack_rehearsal/` contains rehearsal ZIPs written
2026-10-28T18:39:21Z through 18:40:38Z, before HEAD `e4939e19`. They do not contain the
corrections above and must not be read as the current return package.

## 7. What was never claimed

No V167 result improved or worsened anything: there are no V167 results. The claim in this
round is limited to scene protection, one isolation repair, one production defect fixed,
177 green local tests, and an honest blocked table.
