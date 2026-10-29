"""V168 P3/P4 pipeline tests: the real worker subprocess and the real controller runner.

These answer the V166 criticism directly.  Nothing here goes through a convenience
wrapper: a genuine three-file jail is staged, a genuine ledger task is reserved,
``python -I -B v168_worker.py`` is launched by ``v168_runner.run_task`` and every
persisted record is read back.  The F2c model itself stays behind the
``no_real_model_construction`` tripwire, so a green run is evidence about plumbing,
billing and honest state reporting -- never about the physics.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys

import numpy as np
import pytest

import v168_common as common
import v168_controller as controller
import v168_runner as runner

from conftest import JAIL_ROOT, TEST_PREFIX

THREE_FILES = ["frames.json", "input.json", "legal_records.json"]


def _stage_test_jail(staged, test_id, *, kind="BIAS_STRESS", starts=2):
    """Reuse one real staged task's frames and legal records under a test task id.

    Only the two identity fields the payload gate binds together are rewritten, so
    the round trip exercises the same documents the authorized run will see.
    """
    rows = [row for row in staged["staging"]["mapping"]["tasks"]
            if row["kind"] == kind and len(row["starts"]) == starts]
    assert rows, "NO_STAGED_TASK_WITH_THE_REQUESTED_SHAPE"
    source = JAIL_ROOT / rows[0]["task_id"]
    jail_dir = JAIL_ROOT / test_id
    jail_dir.mkdir(parents=True, exist_ok=True)
    for name in ("frames.json", "legal_records.json"):
        (jail_dir / name).write_bytes((source / name).read_bytes())
    payload = copy.deepcopy(common.read_json(source / "input.json"))
    payload["task_id"] = test_id
    payload["reading"]["reading_id"] = test_id
    (jail_dir / "input.json").write_bytes(common.canon(payload))
    return {
        "jail": jail_dir,
        "payload": payload,
        "group": payload["group"],
        "payload_sha256": common.sha_file(jail_dir / "input.json"),
        "frames_sha256": runner.frames_sha_for(
            common.read_json(jail_dir / "frames.json"), payload["group"]),
        "cap_per_start": int(payload["cap_per_start"]),
        "task_cap": int(payload["task_cap"]),
        "witness_keys": _witness_keys(jail_dir),
    }


def _witness_keys(jail_dir):
    """The (theta, C_sha) pairs the witness floor is allowed to be built from.

    V166's frozen V163 anchor duplicates one of the six legal starts in every
    group, so the de-duplicated floor has six rows, not seven.  The expected set is
    recomputed here from the same two documents the worker reads, never hardcoded.
    """
    legal = common.read_json(jail_dir / "legal_records.json")
    frames = common.read_json(jail_dir / "frames.json")
    anchor = frames["diagnostic"]["predictions"][int(frames["diagnostic"]["base_index"])]
    anchor_sha = common.array_sha(np.ascontiguousarray(anchor["C"], dtype=np.float64))
    keys = {(tuple(record["theta"]), record["C_sha256"]) for record in legal["records"]}
    keys.add((tuple(anchor["theta"]), anchor_sha))
    return {"keys": keys, "anchor": (tuple(anchor["theta"]), anchor_sha),
            "records": len(legal["records"])}


def _round_trip(service, staged, test_id, *, reserve, kind="BIAS_STRESS", starts=2):
    spec = _stage_test_jail(staged, test_id, kind=kind, starts=starts)
    service.store.reserve(test_id, "pipeline-test-" + test_id, "BIAS_STRESS",
                          reserve, common.OWNER)
    # Contract 4.3: the grid the trusted controller registers is the staged payload's
    # own grid, so the round trip enforces exactly what an authorized run enforces.
    # The ledger reservation stays a separate, deliberately smaller ceiling: this test
    # proves the ledger is the refuser when the reservation is smaller than the search,
    # so the service grid must not be tightened to the reservation here.
    service.set_task_budget(test_id, cap_per_start=int(spec["cap_per_start"]),
                            task_cap=int(spec["task_cap"]),
                            start_count=len(spec["payload"]["starts"]))
    receipt = runner.run_task(task_id=test_id,
                              expected_payload_sha256=spec["payload_sha256"],
                              frames_sha256=spec["frames_sha256"], service=service)
    return spec, receipt


def test_a_full_worker_round_trip_bills_every_forward_it_accepts(service, staged):
    task = TEST_PREFIX + "PIPE000001"
    spec, receipt = _round_trip(service, staged, task, reserve=spec_task_cap(staged, task))
    task_dir = common.OUT / "tasks" / task

    assert receipt["worker_exit_code"] == 0, receipt["stderr_lines"][-8:]
    assert receipt["worker_error"] is None
    assert receipt["forward_requests"] > 0
    assert receipt["charged_replies"] + receipt["cache_hit_replies"] \
        == receipt["forward_requests"]
    # Every accepted answer is one durable billed attempt, and nothing was billed
    # that the worker did not receive.
    assert receipt["charged_replies"] == service.real_calls
    assert service.store.counts()[task] == receipt["charged_replies"]
    assert receipt["ledger_counts_after"][task] == receipt["charged_replies"]
    assert receipt["reportable_D"] is None
    assert receipt["result"]["frames_sha256"] == spec["frames_sha256"]
    assert receipt["result"]["payload_sha256"] == spec["payload_sha256"]

    for index in range(len(spec["payload"]["starts"])):
        slot = common.read_json(task_dir / "starts" / f"{index:03d}.json")
        assert slot["start_index"] == index
        assert slot["cap_per_start"] == spec["cap_per_start"]
        assert slot["x0"] == [float(v) for v in spec["payload"]["starts"][index]]
        assert slot["execution_state"] in ("FINISHED", "PARTIAL_SEARCH", "FAILED")
        assert slot["best"] is not None, "START_WITHOUT_A_PERSISTED_BEST"
        common.check_theta(slot["best"]["theta"])
        assert np.isfinite(slot["best"]["Q_total"])
        assert slot["best"]["charged"] in (True, False)
        assert slot["actual_evaluations"] == sum(
            passed["evaluations"] for passed in slot["passes"])
        assert slot["charged_this_start"] <= spec["cap_per_start"]
        for passed in slot["passes"]:
            on_disk = common.read_json(
                task_dir / "starts" / f"{index:03d}_pass_{passed['pass_index']:02d}.json")
            assert on_disk == passed
            assert on_disk["x0"] == passed["x0"]
            # An exception escapes least_squares before the object is bound, so a pass
            # reports either an optimiser outcome or an error, never both.
            assert (on_disk["optimizer"] is None) == (on_disk["error"] is not None)
            # Every evaluation of this pass is its own immutable document, and the
            # rolling per-pass best must be the lowest-Q one of exactly that pass.
            pass_docs = [common.read_json(path) for path in sorted(
                (task_dir / "evaluations").glob(f"{index:03d}_{passed['pass_index']:02d}_*.json"))]
            assert len(pass_docs) == on_disk["evaluations"]
            for position, doc in enumerate(pass_docs, start=1):
                assert doc["evaluation_index"] == position
                assert doc["start_index"] == index and doc["pass_index"] == passed["pass_index"]
            if on_disk["best"] is not None:
                best_doc = common.read_json(
                    task_dir / "best" / f"start_{index:03d}_pass_{passed['pass_index']:02d}.json")
                lowest = min(doc["Q_total"] for doc in pass_docs)
                assert best_doc["Q_total"] == lowest
                assert best_doc == on_disk["best"]
            else:
                assert not (task_dir / "best" /
                            f"start_{index:03d}_pass_{passed['pass_index']:02d}.json").exists()

    evaluations = sorted((task_dir / "evaluations").glob("*.json"))
    assert len(evaluations) == receipt["result"]["evaluations_total"]
    first = common.read_json(evaluations[0])
    assert set(["schema", "task_id", "start_index", "pass_index", "evaluation_index",
                "charged", "ledger_seq", "prediction_path", "prediction_sha256",
                "Q_total", "theta"]) <= set(first)
    assert (service.out / first["prediction_path"]).is_file()

    witnesses = common.read_json(task_dir / "legal_witnesses.json")["rows"]
    assert spec["witness_keys"]["records"] == 6
    assert len(witnesses) == len(spec["witness_keys"]["keys"]) == 6, (
        "the V163 anchor duplicates one legal start, so the floor de-duplicates to six")
    assert {(tuple(row["theta"]), row["C_sha256"]) for row in witnesses} \
        == spec["witness_keys"]["keys"]
    assert [row["Q_total"] for row in witnesses] == sorted(r["Q_total"] for r in witnesses)
    sources = [row["source"] for row in witnesses]
    assert sources.count("V163_CURRENT_ANCHOR") == 1
    assert all(source.endswith(".json") for source in sources if source != "V163_CURRENT_ANCHOR")

    search = common.read_json(task_dir / "search_result.json")
    assert search["schema"] == "iscat168.search_result.1"
    assert search["task_id"] == task
    assert search["reportable_D"] is None
    assert search["candidate_D_nm"] is None or search["execution_state"] == "FINISHED"
    assert search["physical_qualification"] == "CONDITIONAL_SIMULATED_F2C_DEVELOPMENT"
    assert search["execution_state"] in ("FINISHED", "PARTIAL_SEARCH", "FAILED")
    assert search["evaluations_total"] == sum(start["actual_evaluations"]
                                              for start in search["starts"])
    if search["execution_state"] != "FINISHED":
        assert search["reason_codes"], "UNEXPLAINED_INCOMPLETE_SEARCH"
    # A fake forward can never beat the group's real legal-witness floor, so the
    # honest outcome is a refusal to report a diameter, not a fabricated FINISHED.
    assert search["reportable_D"] is None
    assert search["best_legal_witness"] == witnesses[0]
    observed = search["remote_observations"]
    assert observed["forward_requests"] == receipt["forward_requests"]
    assert observed["charged_forwards"] == receipt["charged_replies"]
    assert observed["cache_hit_forwards"] == receipt["cache_hit_replies"]
    assert observed["max_forward_ms"] >= 0.0

    with service.store.db() as conn:
        states = [row[0] for row in conn.execute(
            "SELECT state FROM attempts WHERE task=? ORDER BY seq", (task,))]
    assert set(states) <= {"RETURNED", "MODEL_ERROR"}
    assert len(states) == receipt["charged_replies"]
    assert sorted(path.name for path in spec["jail"].iterdir()) == THREE_FILES


def spec_task_cap(staged, task):
    """The reservation ceiling used by the full round trip."""
    del staged, task
    return 400


def test_a_reservation_smaller_than_the_search_is_trimmed_not_exceeded(service, staged):
    """Section 11: insufficient budget stops at the reservation and reports PARTIAL."""
    task = TEST_PREFIX + "PIPE000002"
    reserve = 3
    spec, receipt = _round_trip(service, staged, task, reserve=reserve)
    assert receipt["worker_exit_code"] == 0, receipt["stderr_lines"][-8:]
    # The reservation, not the worker, is the hard ceiling: the search wanted more
    # forwards and the store refused them without ever billing beyond the cap.
    assert receipt["charged_replies"] == reserve
    assert service.store.counts()[task] == reserve
    assert service.real_calls == reserve
    assert receipt["forward_requests"] > reserve
    result = receipt["result"]
    assert result["reportable_D"] is None
    # Task level the honest label is FAILED: a synthetic forward cannot beat the
    # group's real frozen legal-witness floor, so the worker refuses to name a
    # candidate diameter.  The cap itself is proved by the billing and refusal
    # evidence below, and each start slot still reports PARTIAL_SEARCH.
    assert result["execution_state"] == "FAILED"
    assert result["reason_codes"] == ["SEARCH_INCOMPLETE_OR_IMPLEMENTATION_ERROR"]
    assert result["candidate_D_nm"] is None

    task_dir = common.OUT / "tasks" / task
    slot = common.read_json(task_dir / "starts" / "000.json")
    assert slot["execution_state"] == "PARTIAL_SEARCH"
    assert slot["charged_this_start"] == reserve
    assert slot["best"] is not None and np.isfinite(slot["best"]["Q_total"])
    assert slot["best"]["charged"] is True
    assert slot["actual_evaluations"] > slot["charged_this_start"], (
        "a refused forward counts as an attempt but must never be billed")
    # A ledger refusal ends the start: the search stops rather than living off
    # predictions this round already paid for.  The worker names both facts it knows,
    # in this order: the pass was ended by the durable ledger refusing further charges,
    # and the one bounded solver instance stopped early with its best retained.  The
    # two codes are not alternatives, so the record has to carry both.
    assert slot["reason_codes"] == ["BUDGET_BLOCKED_AT_LEDGER_STOP",
                                    "SINGLE_PASS_STOPPED_EARLY_BEST_RETAINED"]
    assert len(slot["passes"]) == 1
    assert len(result["starts"]) == len(spec["payload"]["starts"])
    assert len(common.read_json(task_dir / "starts" / "001.json")["passes"]) == 1
    # Only accepted forwards (billed or cached) produce an evaluation document, and
    # every document says whether it cost anything.
    docs = [common.read_json(path) for path in sorted((task_dir / "evaluations").glob("*.json"))]
    assert len(docs) == reserve + receipt["cache_hit_replies"]
    assert sum(1 for doc in docs if doc["charged"]) == reserve
    assert all(doc["cache_hit"] is False for doc in docs)
    # Every start keeps its own honest record, so nothing is silently dropped.
    for entry in result["starts"]:
        assert entry["execution_state"] == "PARTIAL_SEARCH"
        assert entry["reason_codes"] == ["BUDGET_BLOCKED_AT_LEDGER_STOP",
                                        "SINGLE_PASS_STOPPED_EARLY_BEST_RETAINED"]

    rpc = common.read_json(controller.CONTROL / "rpc" / (task + ".json"))
    refusals = [row for row in rpc["rpc_log"] if row.get("cap_reached") is True]
    assert refusals, "CAP_REFUSAL_NOT_RECORDED_IN_THE_RPC_RECEIPT"
    assert {row["error_type"] for row in refusals} == {"CallCapReached"}
    assert rpc["charged_replies"] == reserve
    assert rpc["cache_hit_replies"] == 0

    with service.store.db() as conn:
        rows = list(conn.execute(
            "SELECT seq, state FROM attempts WHERE task=? ORDER BY seq", (task,)))
    assert [row[0] for row in rows] == list(range(1, reserve + 1))
    assert {row[1] for row in rows} == {"RETURNED"}


def test_a_task_without_a_reservation_cannot_obtain_a_single_forward(service, staged):
    """The ledger, not the worker, decides what may be computed."""
    task = TEST_PREFIX + "PIPE000003"
    spec = _stage_test_jail(staged, task)
    with pytest.raises(runner.WorkerDeath):
        runner.run_task(task_id=task, expected_payload_sha256=spec["payload_sha256"],
                        frames_sha256=spec["frames_sha256"], service=service)
    assert service.store.counts().get(task, 0) == 0
    assert service.real_calls == 0


def test_a_payload_sha_that_does_not_match_the_plan_is_refused_before_any_forward(
        service, staged):
    task = TEST_PREFIX + "PIPE000004"
    spec = _stage_test_jail(staged, task)
    with pytest.raises(runner.WorkerDeath) as refused:
        runner.run_task(task_id=task, expected_payload_sha256="0" * 64,
                        frames_sha256=spec["frames_sha256"], service=service)
    assert "TASK_ROUND_FAILED" in str(refused.value)
    assert service.store.counts().get(task, 0) == 0
    assert service.real_calls == 0


def test_the_validator_dry_run_opens_no_truth_and_writes_no_primary_evidence():
    primary = common.OUT / "validator_only"
    before = sorted(path.name for path in primary.iterdir()) if primary.is_dir() else []
    script = common.ROOT / "tools" / "v168" / "v168_validator.py"
    proc = subprocess.run([sys.executable, "-X", "utf8", str(script), "--dry-run"],
                          capture_output=True, text=True, cwd=str(common.ROOT))
    assert proc.returncode == 0, proc.stderr[-2000:]
    line = next(item for item in reversed(proc.stdout.splitlines())
                 if item.startswith("VALIDATOR "))
    report = json.loads(line[len("VALIDATOR "):])
    assert report["status"] == "NOT_STARTED_DRY_RUN"
    assert report["model_calls"] == 0
    assert report.get("tasks_total") in (None, 0)
    assert not report.get("task_execution_states")
    after = sorted(path.name for path in primary.iterdir()) if primary.is_dir() else []
    assert after == before, "DRY_RUN_WROTE_PRIMARY_VALIDATOR_EVIDENCE"
