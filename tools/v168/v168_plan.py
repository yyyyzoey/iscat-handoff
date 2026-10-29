"""Trusted V168 preparation only: deterministic task inputs, no model, no truth.

This module is NOT an estimator.  It is never imported inside an estimator
worker, it opens no optical model, reads no sealed truth file, draws no random
number, and writes nothing into a worker read root.  Workers receive exactly one
validated single-reading payload each.

Contract section 3 fixes the budget grid this file must reproduce: 23 fit tasks
at 400 real new calls each (9,200), plus MODEL_BINDING 199 and FINAL_VERIFY 600,
which is 9,999 new calls because the one stranded V167 loader charge stays spent.

The task-id hash carries an explicit round component.  Without it a V168 task id
would be byte-identical to the V167 id for the same source and bias, and two
rounds of evidence would collide.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import v168_common as common                                              # noqa: E402
from v168_common import GROUPS, PHASES, TOTAL, require                    # noqa: E402

GATE = common.load_payload_gate()

PARENT = common.PARENT_COMMIT
ROUND = "v168"
R_SOURCES = ("B100000_ANON_01_H10_R00", "B100000_ANON_01_H10_R01",
             "B100000_ANON_01_H1_R00", "B100000_ANON_01_H1_R01",
             "B100000_ANON_01_H1_R02")
B_SOURCES = tuple(f"B100000_{group}_H1_R{rep:02d}"
                  for group in GROUPS[1:] for rep in range(3))
DETECTED_GROUPS = GROUPS[1:]

# Git blob ids of the immutable V166 inputs this plan is derived from.  A worktree
# edit to any of them stops preparation rather than silently re-deriving the grid.
PINS = {
    "estimates.json": "242958afa607deee2f84b564c8f4eb8fda01ac24",
    "height_input/height_readings.json": "b087156cf60d2b16fbfe3da3d9e4a20bef902dd0",
    "starts_by_group.json": "3b7b46f0e7cde72e09a50a6cfddc7613f32f6f95",
}

# The delivered bundle ships the 23-task semantic map as a byte-pinned,
# controller-only file.  The planner must reproduce it exactly rather than invent
# a grid that merely passes its own shape checks.
TASK_MATRIX_SHA256 = ("781945033401bfcdc394f156187c27d662c0200a55ae8ed306666c8d42518ab6")
ROLE_TO_KIND = {"SEARCH_EXTENSION": "SEARCH_EXTENSION", "BIAS_STRESS": "BIAS_STRESS"}


def canon(value: Any) -> bytes:
    return common.canon(value)


def finite_number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(float(value))


def identity(kind: str, old_id: str, bias: float | None = None) -> str:
    # The controlled bias is deliberately absent from the readable worker payload;
    # it is present here only because this hash is controller-side provenance.
    h = hashlib.sha256(canon({"parent": PARENT, "round": ROUND, "kind": kind,
                              "source": old_id, "bias": bias}))
    return "V168_" + h.hexdigest()[:24]


def one_reading(row: dict, task_id: str, *, add_nm: float = 0.0) -> dict:
    require(row["group"] in GROUPS and row["B"] == 100000, "READING_GROUP_OR_B")
    require(type(row["replicate"]) is int and row["replicate"] in (0, 1, 2),
            "READING_REPLICATE")
    require(finite_number(row["sigma_nm"]) and float(row["sigma_nm"]) in (1.0, 10.0),
            "READING_SIGMA")
    require(finite_number(row["z_nm"]) and finite_number(add_nm), "READING_FINITE")
    require(row.get("hypothetical") is True, "READING_NOT_HYPOTHETICAL")
    # A strict projection, not a copy of whatever metadata the table happens to hold.
    # add_nm is consumed here and never written into the payload, so an estimator
    # cannot tell a biased reading from an untouched one beyond its own value.
    return {"reading_id": task_id, "group": row["group"], "B": 100000,
            "replicate": row["replicate"], "sigma_nm": float(row["sigma_nm"]),
            "z_nm": float(row["z_nm"]) + float(add_nm), "hypothetical": True}


def make_payload(task_id: str, reading: dict, starts: list, cap: int) -> dict:
    payload = {"schema": "iscat168.one_task.1", "task_id": task_id,
               "group": reading["group"], "B": 100000, "reading": reading,
               "starts": [[float(x) for x in common.check_theta(t)] for t in starts],
               "cap_per_start": cap, "task_cap": common.FIT_TASK_CAP,
               "scope": "OPENED_DEV_NOT_BLIND_NOT_EXPERIMENT"}
    GATE.validate(payload)
    return payload


def load_task_matrix() -> dict:
    raw = common.TASK_MATRIX.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == TASK_MATRIX_SHA256,
            "TASK_MATRIX_BYTES_CHANGED")
    matrix = json.loads(raw.decode("utf-8"))
    require(matrix.get("scope") == "CONTROLLER_ONLY_NOT_ESTIMATOR_INPUT",
            "TASK_MATRIX_SCOPE")
    tasks = matrix.get("tasks")
    require(isinstance(tasks, list) and len(tasks) == 23, "TASK_MATRIX_COUNT")
    require(matrix.get("task_count") == 23 and matrix.get("start_count") == 41
            and matrix.get("fit_call_cap_sum") == 9200, "TASK_MATRIX_TOTALS")
    return matrix


def reconcile_with_matrix(matrix: dict, records: list) -> None:
    """Every authorized task must equal its frozen row: role, source, start, caps.

    The comparison is one-sided on purpose: the matrix is the authority, the plan
    is the derived object.  A plan that quietly adds a start, widens a cap or
    re-points a source fails here before any model exists to spend budget on.
    """
    by_key = {row["logical_key"]: row for row in records}
    expected = {row["logical_key"] for row in matrix["tasks"]}
    require(expected == set(by_key), "TASK_MATRIX_KEY_SET_CHANGED")
    for spec in matrix["tasks"]:
        row = by_key[spec["logical_key"]]
        source = spec.get("source_task_id") or spec.get("source_reading_id")
        require(row["kind"] == ROLE_TO_KIND[spec["role"]],
                "MATRIX_ROLE:" + spec["logical_key"])
        require(row["source_task_id"] == source,
                "MATRIX_SOURCE:" + spec["logical_key"])
        if "source_start_index" in spec:
            require(int(row["source_start_index"]) == int(spec["source_start_index"]),
                    "MATRIX_SOURCE_START:" + spec["logical_key"])
        require(int(row["task_cap"]) == int(spec["task_cap"]),
                "MATRIX_TASK_CAP:" + spec["logical_key"])
        require(int(row["cap_per_start"]) == int(spec["real_cap_per_start"]),
                "MATRIX_REAL_CAP:" + spec["logical_key"])
        require(int(row["optimizer_instances"]) == int(spec["optimizer_instances"]),
                "MATRIX_OPTIMIZER_INSTANCES:" + spec["logical_key"])
        if spec["role"] == "SEARCH_EXTENSION":
            require(row["warm_start_record"] == "starts/001.json:best",
                    "MATRIX_WARM_SOURCE:" + spec["logical_key"])
        else:
            require(float(row["controlled_offset_nm"])
                    == float(spec["controller_only_bias_nm"]),
                    "MATRIX_BIAS:" + spec["logical_key"])
            require(float(row["sigma_nm"]) == float(spec["sigma_nm"]),
                    "MATRIX_SIGMA:" + spec["logical_key"])
            require(int(row["replicate"]) == int(spec["replicate"]),
                    "MATRIX_REPLICATE:" + spec["logical_key"])
            require(row["group"] == spec["group"], "MATRIX_GROUP:" + spec["logical_key"])
            require(row["warm_start_record"] == "starts_by_group.json:first+second",
                    "MATRIX_WARM_SOURCE:" + spec["logical_key"])


def expected_old_ids() -> set[str]:
    return ({f"B100000_{g}_NO_HEIGHT" for g in GROUPS}
            | {f"B100000_{g}_H{s}_R{r:02d}"
               for g in GROUPS for s in (1, 10) for r in range(3)})


def build_plan(estimates: list, readings_doc: dict, starts_doc: dict,
               pending_starts: dict) -> tuple[dict, dict]:
    matrix = load_task_matrix()
    require(isinstance(estimates, list) and len(estimates) == 28, "ESTIMATE_COUNT")
    by_id = {row["task_id"]: row for row in estimates}
    require(len(by_id) == 28 and set(by_id) == expected_old_ids(), "ESTIMATE_ID_SET")
    partial = {row["task_id"] for row in estimates
               if row["execution_state"] == "PARTIAL_SEARCH"}
    require(partial == set(R_SOURCES), "PARENT_PARTIAL_SET_CHANGED")
    require(all(row["execution_state"] in ("FINISHED", "PARTIAL_SEARCH")
                for row in estimates), "OLD_TASK_UNKNOWN_STATE")
    rows = readings_doc.get("readings", [])
    require(len(rows) == 24, "READING_COUNT")
    rmap = {row["reading_id"]: row for row in rows}
    require(len(rmap) == 24 and set(rmap)
            == expected_old_ids() - {f"B100000_{g}_NO_HEIGHT" for g in GROUPS},
            "READING_ID_SET")
    require(set(starts_doc) == set(GROUPS), "GROUP_START_SET")
    for group in DETECTED_GROUPS:
        for key in ("first", "second"):
            require(isinstance(starts_doc[group].get(key), dict),
                    "GROUP_START_MISSING:" + group + "." + key)

    records: list[dict] = []
    payloads: dict[str, dict] = {}

    # Branch R: five exhausted second starts, one start, one solver, 400 real calls.
    for index, old_id in enumerate(R_SOURCES):
        source = pending_starts[old_id]
        require(source.get("execution_state") == "PARTIAL_SEARCH"
                and source.get("start_index") == 1,
                "RECOVERY_SOURCE_NOT_PENDING_START_1:" + old_id)
        require(source.get("error", {}).get("error_type") == "CallCapReached",
                "RECOVERY_NOT_AUTHORIZED_FOR_OTHER_ERRORS:" + old_id)
        require(isinstance(source.get("best"), dict)
                and isinstance(source["best"].get("theta"), list),
                "RECOVERY_BEST_MISSING:" + old_id)
        task_id = identity("SEARCH_EXTENSION", old_id)
        reading = one_reading(rmap[old_id], task_id)
        payload = make_payload(task_id, reading, [source["best"]["theta"]],
                               common.REAL_CAP_PER_START)
        payloads[task_id] = payload
        records.append({"task_id": task_id, "kind": "SEARCH_EXTENSION",
                        "logical_key": "R%02d" % index,
                        "source_task_id": old_id, "group": rmap[old_id]["group"],
                        "source_start_index": 1,
                        "warm_start_record": "starts/001.json:best",
                        "warm_start_reason": "SECOND_SEQUENTIAL_START_FROM_PRIOR_BEST",
                        "old_start_consumption": source.get("actual_calls"),
                        "old_status_preserved": "PARTIAL_SEARCH",
                        "optimizer_instances": 1, "cap_per_start": common.REAL_CAP_PER_START,
                        "merge_rule": "MINIMUM_Q_TOTAL_OVER_OLD_BEST_AND_NEW_LEGAL_POINTS",
                        "task_cap": common.FIT_TASK_CAP,
                        "payload_sha256": hashlib.sha256(canon(payload)).hexdigest()})

    # Branch B: two fixed starts, one solver each, 200 real calls each, no new draws.
    for group in DETECTED_GROUPS:
        starts = [starts_doc[group][key]["theta"] for key in ("first", "second")]
        for rep in range(3):
            old_id = f"B100000_{group}_H1_R{rep:02d}"
            require(by_id[old_id]["execution_state"] == "FINISHED",
                    "ZERO_BIAS_REFERENCE_NOT_FINISHED:" + old_id)
            require(float(rmap[old_id]["sigma_nm"]) == 1.0,
                    "BIAS_STRESS_REQUIRES_SIGMA_ONE:" + old_id)
            for bias in (-2.0, 2.0):
                task_id = identity("BIAS_STRESS", old_id, bias)
                reading = one_reading(rmap[old_id], task_id, add_nm=bias)
                payload = make_payload(task_id, reading, starts,
                                       common.REAL_CAP_PER_START // 2)
                payloads[task_id] = payload
                records.append({"task_id": task_id, "kind": "BIAS_STRESS",
                                "logical_key": "B_%s_%d_%s"
                                % (group, rep, "m2" if bias < 0 else "p2"),
                                "source_task_id": old_id, "group": group,
                                "controlled_offset_nm": bias, "sigma_nm": 1.0,
                                "replicate": rep, "source_start_index": 0,
                                "warm_start_record": "starts_by_group.json:first+second",
                                "old_start_consumption": 0,
                                "old_status_preserved": "FINISHED",
                                "optimizer_instances": 2,
                                "cap_per_start": common.REAL_CAP_PER_START // 2,
                                "task_cap": common.FIT_TASK_CAP,
                                "payload_sha256": hashlib.sha256(canon(payload)).hexdigest()})

    require(len(payloads) == 23 and len(records) == 23, "NEW_TASK_COUNT")
    require(len({row["task_id"] for row in records}) == 23, "TASK_ID_DUPLICATE")
    require(len({row["logical_key"] for row in records}) == 23, "LOGICAL_KEY_DUPLICATE")
    require(sum(PHASES.values()) == TOTAL, "PHASE_SUM_NOT_NEW_ALLOWANCE")
    require(sum(int(row["task_cap"]) for row in records) + PHASES["FINAL_VERIFY"]
            + PHASES["MODEL_BINDING"] == TOTAL, "PLAN_BUDGET_GRID")
    require([row["source_task_id"] for row in records if row["kind"] == "SEARCH_EXTENSION"]
            == list(R_SOURCES), "R_SOURCE_ORDER")
    require(sorted({row["source_task_id"] for row in records
                    if row["kind"] == "BIAS_STRESS"}) == sorted(B_SOURCES),
            "B_SOURCE_SET")
    reconcile_with_matrix(matrix, records)
    for row in records:
        scan = common.scan_forbidden(payloads[row["task_id"]], "worker_payload")
        require(not scan, "WORKER_PAYLOAD_LEAK:" + row["task_id"] + "|" + ",".join(scan))

    manifest = {"schema": "iscat168.controller_plan.1",
                "role": "CONTROLLER_ONLY_NOT_WORKER_INPUT",
                "round": ROUND, "parent": PARENT, "phases": dict(PHASES),
                "total_new_model_attempts": TOTAL,
                "historical_consumed_attempts": common.HISTORICAL_CONSUMED,
                "combined_attempt_ceiling": common.COMBINED_CEILING,
                "new_fit_jobs": 23, "new_height_random_draws": 0,
                "new_truth_read_before_seal": False,
                "entries": records,
                "note": ("Only one payload may be mounted/passed to each worker; never "
                         "mount this plan, the task matrix, the prior ledger or the "
                         "24-row reading table.")}
    return manifest, payloads


def pinned_json(path: Path, blob_sha: str) -> Any:
    raw = path.read_bytes()
    got = common.blob_sha(raw)
    require(got == blob_sha, "SOURCE_BLOB_CHANGED:" + str(path))
    return json.loads(raw.decode("utf-8-sig"))


def write_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Binary on purpose: the recorded payload SHA is the SHA of the canonical
    # bytes, and text mode on Windows would turn the trailing LF into CRLF and
    # make every prepared payload fail its own hash.
    with path.open("xb") as handle:
        handle.write(canon(value))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v166-results", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    source = args.v166_results.resolve()
    out = args.out.resolve()
    require(not out.exists(), "OUTPUT_EXISTS_NO_AUTORETRY")
    require(out != source and source not in out.parents,
            "OUTPUT_MUST_NOT_MODIFY_PARENT_RESULT_TREE")
    require(source.name == "v166" and source.parent.name == "results",
            "EXPECTED_V166_RESULT_ROOT")
    repo = source.parents[1]

    docs = {rel: pinned_json(source / rel, pin) for rel, pin in PINS.items()}

    # Immutable Git blob identity for each warm-start checkpoint: no numerical
    # replay, no checkout, no source mutation, no model construction.
    pending: dict[str, dict] = {}
    blobs: dict[str, str] = {}
    for task_id in R_SOURCES:
        rel = f"results/v166/tasks/{task_id}/starts/001.json"
        blob = subprocess.run(["git", "-C", str(repo), "rev-parse", f"{PARENT}:{rel}"],
                              check=True, capture_output=True).stdout
        blob = blob.decode("ascii").strip()
        require(len(blob) == 40, "INVALID_GIT_BLOB_ID:" + rel)
        blobs[rel] = blob
        pending[task_id] = pinned_json(repo / rel, blob)

    plan, payloads = build_plan(docs["estimates.json"],
                               docs["height_input/height_readings.json"],
                               docs["starts_by_group.json"], pending)
    out.mkdir(parents=True, exist_ok=False)
    write_new(out / "controller_only" / "plan.json", plan)
    for task_id, payload in payloads.items():
        write_new(out / "controller_staging" / task_id / "input.json", payload)
    write_new(out / "preparation_receipt.json",
              {"schema": "iscat168.preparation_receipt.1", "model_calls": 0,
               "random_draws": 0, "new_payloads": 23, "parent_commit": PARENT,
               "source_blobs": dict(PINS), "warm_start_blobs": blobs,
               "requires_workstation_integration": True})
    print("PREPARATION_ONLY__23_TASK_PAYLOADS__NO_MODEL_CALLS__NOT_PRODUCTION_EXECUTION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
