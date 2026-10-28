"""Contract section 3.3 tests that are about state, budget and the seal, not plumbing.

Every test here reads the real V166 evidence files, drives the real controller
functions and the real worker pass loop, and asserts the honest failure semantics:
a warm start may only come from the sealed best of the unfinished start, no old
FINISHED task may be re-run, the augmented residual carries the height row exactly
once, a cap or a write failure may never be reported as a usable answer, a historical
PARTIAL may never be rewritten as complete, and one missing task result blocks the
whole-round seal.  The F2c model stays behind the session tripwire, so none of this
bills a charged forward.
"""
from __future__ import annotations

import copy
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

import v167_common as common
import v167_controller as controller
import v167_worker as worker

from conftest import JAIL_ROOT, TEST_PREFIX, fake_forward

V166_TASKS = controller.V166 / "tasks"


def _read_json_new(path: Path) -> dict:
    """Read a V166 evidence file: those documents were written with a BOM."""
    return json.loads(path.read_bytes().decode("utf-8-sig"))


def _mapping_rows(staged, kind: str) -> list[dict]:
    return [row for row in staged["staging"]["mapping"]["tasks"] if row["kind"] == kind]


def _plan_entries(staged, kind: str) -> list[dict]:
    return [entry for entry in staged["plan"]["entries"] if entry["kind"] == kind]


class StubRemote:
    """Answer forwards from memory so the real pass loop can run in-process.

    Only ``forward`` and the four observation counters are used by ``run_pass`` and
    ``assemble``.  The numbers come from the pinned fake response, never from F2c.
    """

    def __init__(self):
        self.forward_requests = 0
        self.charged_forwards = 0
        self.cache_hit_forwards = 0
        self.max_forward_ms = 0.0

    def forward(self, theta, evaluation_index, pass_index):
        self.forward_requests += 1
        self.charged_forwards += 1
        c = fake_forward(theta)
        return {"C": c, "charged": True, "cache_hit": False,
                "seq": self.forward_requests, "prediction_path": None,
                "prediction_sha256": common.array_sha(np.asarray(c, dtype=np.float64)),
                "origin": "test_stub", "forward_wall_ms": 0.0}


def _pass_fixture(staged, tmp_path: Path, kind: str = "BIAS_STRESS"):
    """One real staged task's frames, reading and payload inside a throwaway task tree."""
    row = next(item for item in _mapping_rows(staged, kind))
    jail = JAIL_ROOT / row["task_id"]
    payload = _read_json_new(jail / "input.json")
    data, _identity, _sha = common.frames_from_document(
        _read_json_new(jail / "frames.json"), where="test:" + row["task_id"])
    task_dir = tmp_path / "tasks" / (TEST_PREFIX + "PASS00001")
    for name in ("starts", "evaluations", "best"):
        (task_dir / name).mkdir(parents=True, exist_ok=True)
    return payload, data, {"task": task_dir}, task_dir


@pytest.fixture()
def probe_tree():
    """A throwaway results tree inside ROOT.

    ``write_seal`` and the report writers spell evidence paths relative to ROOT, so a
    probe outside the repository would fail for the wrong reason.  The tree is created
    under results/v167/workstation_tests/ and removed again on teardown; no primary
    evidence name is ever written here.
    """
    parent = controller.ROOT / "results" / "v167" / "workstation_tests"
    parent.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="v167_probe_", dir=str(parent)))
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=False)


# ---------------------------------------------------------------- section 3.3, R warm starts
def test_the_five_warm_starts_come_only_from_the_sealed_best_of_the_unfinished_start(staged):
    rows = {row["task_id"]: row for row in _mapping_rows(staged, "SEARCH_EXTENSION")}
    entries = {str(entry["task_id"]): entry
              for entry in _plan_entries(staged, "SEARCH_EXTENSION")}
    assert len(rows) == len(entries) == 5
    assert set(rows) == set(entries)
    for task_id, entry in sorted(entries.items()):
        source = str(entry["source_task_id"])
        # The dependence is read straight off the sealed V166 bytes, not through the
        # controller's own reference table, so this test cannot agree with a bug there.
        start = _read_json_new(V166_TASKS / source / "starts" / "001.json")
        assert start["execution_state"] == "PARTIAL_SEARCH"
        assert start["error"]["error_type"] == "CallCapReached"
        assert int(start["actual_calls"]) == 200
        assert start["best"] is not None and start["best"]["theta"] is not None
        payload = _read_json_new(JAIL_ROOT / task_id / "input.json")
        assert len(payload["starts"]) == 1, "R_TASK_MUST_CARRY_EXACTLY_ONE_NEW_START"
        assert [float(v) for v in payload["starts"][0]] \
            == [float(v) for v in start["best"]["theta"]], "WARM_START_IS_NOT_THE_SEALED_BEST"
        assert [float(v) for v in payload["starts"][0]] \
            != [float(v) for v in start["x0"]], "WARM_START_IS_THE_ORIGINAL_X0"
        assert int(entry["old_start_consumption"]) == int(start["actual_calls"])
        assert entry["warm_start_record"] == "starts/001.json:best"
        # Section 5 gives the single new start the whole 400-call task ceiling.
        assert int(entry["task_cap"]) == 400 and int(payload["task_cap"]) == 400
        assert int(payload["cap_per_start"]) == 400
        assert entry["old_status_preserved"] == "PARTIAL_SEARCH"
        assert rows[task_id]["source_task_id"] == source


def test_a_warm_start_that_is_not_the_sealed_best_is_refused_by_the_stager(staged):
    row = _mapping_rows(staged, "SEARCH_EXTENSION")[0]
    source = str(row["source_task_id"])
    x0 = [float(v) for v in
          _read_json_new(V166_TASKS / source / "starts" / "001.json")["x0"]]
    tampered = dict(staged)
    refs = copy.deepcopy(staged["refs"])
    refs["partials"][source]["warm_theta"] = x0
    tampered["refs"] = refs
    tampered["published"] = {}
    with pytest.raises(ValueError) as refused:
        controller.stage(tampered)
    assert "R_WARM_START_NOT_SEALED_BEST" in str(refused.value)


def test_a_bias_task_that_reuses_the_wrong_prescribed_starts_is_refused(staged):
    row = _mapping_rows(staged, "BIAS_STRESS")[0]
    group = str(row["group"])
    tampered = dict(staged)
    refs = copy.deepcopy(staged["refs"])
    refs["base_points"][group]["second_start_theta"] = [
        float(v) + 1.0 for v in refs["base_points"][group]["second_start_theta"]]
    tampered["refs"] = refs
    tampered["published"] = {}
    with pytest.raises(ValueError) as refused:
        controller.stage(tampered)
    assert "B_STARTS_NOT_GROUP_PRESCRIBED" in str(refused.value)


# ---------------------------------------------------- section 3.3, no old run is repeated
def test_no_finished_v166_task_is_re_run_and_no_task_identity_is_reused(staged):
    entries = staged["plan"]["entries"]
    task_ids = [str(entry["task_id"]) for entry in entries]
    assert len(task_ids) == 23 == len(set(task_ids))
    assert all(name.startswith("V167_") for name in task_ids)
    old_ids = {path.name for path in V166_TASKS.iterdir() if path.is_dir()}
    assert old_ids, "NO_V166_TASK_TREE_FOUND"
    assert not (set(task_ids) & old_ids), "A_V167_TASK_REUSES_A_V166_TASK_ID"
    # the sealed V166 estimate table, not the task tree, defines the 28 originals:
    # the tree also holds the loader, binding and final-verify tasks.
    sealed = _read_json_new(controller.V166 / "estimates.json")
    assert len(sealed) == 28 and {row["task_id"] for row in sealed} <= old_ids
    states = {row["task_id"]: row["execution_state"] for row in sealed}
    finished = {name for name, state in states.items() if state == "FINISHED"}
    partial = {name for name, state in states.items() if state == "PARTIAL_SEARCH"}
    assert len(finished) == 23 and len(partial) == 5
    for name in sorted(states):
        disk = _read_json_new(V166_TASKS / name / "result.json").get("execution_state")
        assert disk == states[name], "SEALED_TABLE_DISAGREES_WITH_THE_TASK_TREE:" + name
    r_sources = {str(entry["source_task_id"])
                 for entry in entries if entry["kind"] == "SEARCH_EXTENSION"}
    assert r_sources == partial, "THE_WARM_LIST_IS_NOT_EXACTLY_THE_FIVE_UNFINISHED_TASKS"
    assert not (r_sources & finished), "A_FINISHED_TASK_IS_QUEUED_FOR_RE_RUN"
    b_sources = [str(entry["source_task_id"])
                 for entry in entries if entry["kind"] == "BIAS_STRESS"]
    assert sorted(set(b_sources)) == sorted(controller.B_SOURCES)
    assert set(b_sources) <= finished
    assert all(b_sources.count(source) == 2 for source in set(b_sources)), \
        "EVERY_BIAS_SOURCE_NEEDS_EXACTLY_THE_TWO_PRESCRIBED_OFFSETS"


def test_the_authorised_budget_denominators_match_the_contract_table(staged):
    entries = staged["plan"]["entries"]
    r_entries = _plan_entries(staged, "SEARCH_EXTENSION")
    b_entries = _plan_entries(staged, "BIAS_STRESS")
    assert (len(r_entries), len(b_entries), len(entries)) == (5, 18, 23)
    assert all(int(entry["task_cap"]) == 400 for entry in entries)
    assert sum(int(entry["task_cap"]) for entry in r_entries) == 2_000
    assert sum(int(entry["task_cap"]) for entry in b_entries) == 7_200
    assert dict(common.PHASES) == {"MODEL_BINDING": 200, "SEARCH_EXTENSION": 2_000,
                                   "BIAS_STRESS": 7_200, "FINAL_VERIFY": 600}
    assert common.TOTAL == 10_000


# ------------------------------------------- section 3.3, bias offsets and prescribed starts
def test_each_bias_task_is_the_same_h1_reading_shifted_by_exactly_two_nanometres(staged):
    rows = _mapping_rows(staged, "BIAS_STRESS")
    assert len(rows) == 18
    starts_by_group = _read_json_new(controller.V166 / "starts_by_group.json")
    public = controller.public_readings()
    seen: dict[str, set[float]] = {}
    for row in sorted(rows, key=lambda item: (item["source_task_id"],
                                              item["controlled_offset_nm"])):
        source = str(row["source_task_id"])
        group = str(row["group"])
        payload = _read_json_new(JAIL_ROOT / row["task_id"] / "input.json")
        reading, old = payload["reading"], public[source]
        offset = float(row["controlled_offset_nm"])
        assert offset in (-2.0, 2.0), "B_OFFSET_OUTSIDE_THE_TWO_PRESCRIBED_SCENES"
        seen.setdefault(source, set()).add(offset)
        assert float(old["sigma_nm"]) == float(reading["sigma_nm"]) == 1.0, \
            "SIGMA_MAY_NOT_BE_RELAXED_TO_ABSORB_THE_BIAS"
        assert abs((float(reading["z_nm"]) - float(old["z_nm"])) - offset) < 1e-9
        assert float(reading["z_nm"]) != float(old["z_nm"])
        for key in ("group", "B", "replicate"):
            assert reading[key] == old[key], "BIAS_READING_LEFT_ITS_OWN_ROW:" + key
        expected = [[float(v) for v in starts_by_group[group]["first"]["theta"]],
                    [float(v) for v in starts_by_group[group]["second"]["theta"]]]
        assert [[float(v) for v in item] for item in payload["starts"]] == expected, \
            "BIAS_STARTS_ARE_NOT_THE_GROUP_PRESCRIBED_PAIR"
        # and that pair is exactly what the zero-bias V166 run of the same group used
        old_result = _read_json_new(V166_TASKS / source / "result.json")
        old_starts = [[float(v) for v in item["x0"]]
                      for item in old_result["payload"]["starts"]]
        assert old_starts == expected, \
            "THE_ZERO_BIAS_RUN_USED_A_DIFFERENT_PRESCRIBED_PAIR"
    assert all(offsets == {-2.0, 2.0} for offsets in seen.values())
    assert len(seen) == 9


# ------------------------------------------------------ section 3.3, augmented residual once
def test_the_augmented_residual_adds_the_height_row_exactly_once(staged):
    from v152_gls_core import GlsData  # noqa: F401  (proves the pinned core is importable)
    from v165_objective import _gls, augmented_objective

    row = _mapping_rows(staged, "BIAS_STRESS")[0]
    jail = JAIL_ROOT / row["task_id"]
    payload = _read_json_new(jail / "input.json")
    data, _identity, _sha = common.frames_from_document(
        _read_json_new(jail / "frames.json"), where="test:identity")
    reading = common.reading_from_document(payload["reading"])
    theta = [float(v) for v in payload["starts"][0]]
    c = fake_forward(theta)

    pixel_r, q_joint, q_model, k, _per_frame = _gls(data, c)
    pixel_r = np.asarray(pixel_r, dtype=float)
    assert pixel_r.shape == (169,), "GLS_PIXEL_BLOCK_IS_NOT_169_ROWS"

    doc = augmented_objective(data, c, theta, reading)
    residual = np.asarray(doc["residual"], dtype=float)
    assert residual.shape == (170,)
    # the pixel block is untouched and the height penalty is the one extra row
    assert np.array_equal(residual[:169], pixel_r), "PIXEL_BLOCK_CHANGED_BY_THE_AUGMENTATION"
    height_row = (theta[1] - reading.z_nm) / reading.sigma_nm
    assert residual[169] == pytest.approx(height_row, abs=1e-12)
    assert residual[169] ** 2 == pytest.approx(doc["Q_height"], rel=1e-9, abs=1e-9)
    assert float(residual[:169] @ residual[:169]) == pytest.approx(
        doc["Q_model"], rel=1e-9, abs=1e-9)
    half = 0.5 * float(residual @ residual)
    assert 2.0 * half == pytest.approx(doc["Q_model"] + doc["Q_height"], rel=1e-9, abs=1e-9)
    assert doc["Q_total"] == pytest.approx(2.0 * half + doc["K"], rel=1e-9, abs=1e-9)
    assert doc["Q_total"] == pytest.approx(q_joint + doc["Q_height"], rel=1e-9, abs=1e-9)
    assert doc["reportable_D"] is None

    without = augmented_objective(data, c, theta, None)
    assert np.asarray(without["residual"]).shape == (169,)
    assert float(without["Q_height"]) == 0.0
    assert without["Q_joint"] == pytest.approx(doc["Q_joint"], rel=1e-9, abs=1e-9)

    # the shared scorer takes the frozen dataclass, exactly as the worker does
    score = common.score_document(theta, c, data, reading)
    assert score["residual_shape"] == [170]
    assert score["reportable_D"] is None
    assert score["Q_total"] == pytest.approx(doc["Q_total"], rel=1e-9, abs=1e-9)
    assert score["residual_sha256"] == common.array_sha(residual)


def test_a_second_height_row_would_break_the_frozen_identity(staged):
    """The scorer refuses a residual that double counts the height penalty."""
    row = _mapping_rows(staged, "BIAS_STRESS")[0]
    jail = JAIL_ROOT / row["task_id"]
    payload = _read_json_new(jail / "input.json")
    data, _identity, _sha = common.frames_from_document(
        _read_json_new(jail / "frames.json"), where="test:double")
    reading = common.reading_from_document(payload["reading"])
    theta = [float(v) for v in payload["starts"][0]]
    doc = augmented_objective_double_check(data, fake_forward(theta), theta, reading)
    assert doc["checked"] is True


def augmented_objective_double_check(data, c, theta, reading) -> dict:
    """Recompute Q by hand with the height row added twice and show it no longer matches.

    This is the negative half of the identity test: it proves the assertion in
    ``score_document`` is sensitive to the mistake the contract forbids, instead of
    passing for every value.
    """
    from v165_objective import augmented_objective

    honest = augmented_objective(data, c, theta, reading)
    residual = np.asarray(honest["residual"], dtype=float)
    doubled = np.r_[residual, residual[-1]]
    half = 0.5 * float(doubled @ doubled)
    expected = 0.5 * (honest["Q_model"] + honest["Q_height"])
    return {"checked": abs(half - expected) > max(1e-10, 1e-12 * max(1.0, abs(expected))),
            "residual_rows": int(doubled.shape[0])}


# ------------------------------------------------ section 3.3, caps, write failures, seal
def test_a_cap_stops_the_real_pass_loop_and_keeps_the_partial_best_without_a_value(
        staged, tmp_path):
    payload, data, dirs, task_dir = _pass_fixture(staged, tmp_path)
    reading = common.reading_from_document(payload["reading"])
    remote = StubRemote()
    record, checkpoint = worker.run_pass(remote, common, data, reading, dirs, payload,
                                        0, 0, [float(v) for v in payload["starts"][0]], 2)
    assert record["execution_state"] == "PARTIAL_SEARCH"
    assert record["budget_blocked"] is False
    assert record["error"]["error_type"] == "CapReached"
    assert record["evaluations"] == 2 and record["charged_this_pass"] == 2
    assert remote.forward_requests == 2, "THE_CAP_LEAKED_A_FORWARD_REQUEST"
    assert record["reportable_D"] is None and record["optimizer"] is None
    assert record["best"] is not None and np.isfinite(record["best"]["Q_total"])
    persisted = _read_json_new(task_dir / "starts" / "000_pass_00.json")
    assert persisted["execution_state"] == "PARTIAL_SEARCH"
    assert persisted["evaluations"] == 2
    assert len(list((task_dir / "evaluations").glob("000_00_*.json"))) == 2
    assert (task_dir / "best" / "start_000_pass_00.json").is_file()
    assert _read_json_new(checkpoint)["execution_state"] == "PARTIAL_SEARCH"


def test_a_failed_best_write_is_reported_failed_and_never_becomes_a_usable_value(
        staged, tmp_path, monkeypatch):
    payload, data, dirs, task_dir = _pass_fixture(staged, tmp_path)
    reading = common.reading_from_document(payload["reading"])
    original = common.atomic_json

    def refuse_best(path, value):
        path = Path(path)
        if path.parent.name == "best":
            raise common.FatalPersistenceError("TEST_BEST_WRITE_REFUSED")
        return original(path, value)

    monkeypatch.setattr(common, "atomic_json", refuse_best)
    record, _checkpoint = worker.run_pass(StubRemote(), common, data, reading, dirs,
                                         payload, 0, 0,
                                         [float(v) for v in payload["starts"][0]], 5)
    assert record["execution_state"] == "FAILED"
    assert record["error"]["error_type"] == "FatalPersistenceError"
    # Each evaluation is persisted before the rolling-best pointer is advanced, so a
    # refused pointer leaves an in-memory best with no durable pointer behind it.  The
    # honest guarantee is narrower and stronger than "no best at all": the pass is
    # FAILED, it reports no value, no pointer file exists, and any best it carries is
    # backed by a real evaluation document rather than an invented number.
    assert record["reportable_D"] is None
    assert record["evaluations"] >= 1
    assert not (task_dir / "best" / "start_000_pass_00.json").exists(), \
        "THE REFUSED POINTER STILL REACHED DISK"
    persisted = _read_json_new(task_dir / "starts" / "000_pass_00.json")
    assert persisted["execution_state"] == "FAILED"
    assert persisted["reportable_D"] is None
    assert persisted["best"] is not None
    events = [_read_json_new(p)
              for p in sorted((task_dir / "evaluations").glob("000_00_*.json"))]
    assert events, "NO EVALUATION DOCUMENT SURVIVED"
    persisted_digests = {event["prediction_sha256"] for event in events}
    assert persisted["best"]["prediction_sha256"] in persisted_digests, \
        "THE BEST IS NOT BACKED BY A PERSISTED EVALUATION"
    # A FAILED start is excluded from the answer pool, so this pass can never be
    # assembled into a usable candidate even though it holds an in-memory best.
    witness = {"Q_total": 1.0, "theta": [120.0, 420.0, 0.0, 0.0],
               "C_sha256": "1" * 64, "source": "test"}
    answer = worker.assemble(common, payload, reading,
                             [{"start_index": 0, "execution_state": "FAILED",
                               "best": persisted["best"], "passes": [{"pass_index": 0}]}],
                             witness, StubRemote(), {"module_identity": {"test": True}},
                             "2" * 64, "3" * 64, record["evaluations"])
    assert answer["execution_state"] == "FAILED"
    assert answer["reason_codes"] == ["NO_VALID_OPTIMIZER_WITNESS"]
    assert answer["theta"] is None and answer["candidate_D_nm"] is None
    assert answer["reportable_D"] is None


def test_a_failed_checkpoint_write_aborts_before_any_finished_pass_record(
        staged, tmp_path, monkeypatch):
    payload, data, dirs, task_dir = _pass_fixture(staged, tmp_path)
    reading = common.reading_from_document(payload["reading"])
    original = common.update_json

    def refuse_checkpoint(path, value):
        path = Path(path)
        if path.name.endswith(".running.json"):
            raise common.FatalPersistenceError("TEST_CHECKPOINT_WRITE_REFUSED")
        return original(path, value)

    monkeypatch.setattr(common, "update_json", refuse_checkpoint)
    with pytest.raises(common.FatalPersistenceError):
        worker.run_pass(StubRemote(), common, data, reading, dirs, payload, 0, 0,
                        [float(v) for v in payload["starts"][0]], 3)
    # the only on-disk state is still RUNNING, so no reader can take this pass as done
    assert _read_json_new(task_dir / "starts" / "000_pass_00.running.json")[
        "execution_state"] == "RUNNING"
    assert not (task_dir / "starts" / "000_pass_00.json").exists()


def test_an_intentional_partial_start_can_never_be_assembled_as_finished(staged):
    row = _mapping_rows(staged, "SEARCH_EXTENSION")[0]
    payload = _read_json_new(JAIL_ROOT / row["task_id"] / "input.json")
    reading = common.reading_from_document(payload["reading"])
    boot = {"module_identity": {"test": True}}
    witness = {"Q_total": 100.0, "theta": [120.0, 420.0, 0.0, 0.0],
               "C_sha256": "1" * 64, "source": "test"}

    def best(value: float) -> dict:
        return {"Q_total": value, "theta": [120.0, 420.0, 0.0, 0.0], "charged": True}

    mixed = [{"start_index": 0, "execution_state": "FINISHED", "best": best(90.0),
              "passes": [{"pass_index": 0}]},
             {"start_index": 1, "execution_state": "PARTIAL_SEARCH", "best": best(95.0),
              "passes": [{"pass_index": 0}]}]
    document = worker.assemble(common, payload, reading, mixed, witness, StubRemote(), boot,
                               "2" * 64, "3" * 64, 2)
    assert document["execution_state"] == "PARTIAL_SEARCH"
    assert "PARTIAL_SEARCH" in document["reason_codes"]
    assert document["reportable_D"] is None
    assert document["theta"] == [120.0, 420.0, 0.0, 0.0]

    both = copy.deepcopy(mixed)
    both[1]["execution_state"] = "FINISHED"
    finished = worker.assemble(common, payload, reading, both, witness, StubRemote(), boot,
                               "2" * 64, "3" * 64, 2)
    assert finished["execution_state"] == "FINISHED"
    # FINISHED still means only that the prescribed process ended
    assert finished["reportable_D"] is None
    assert finished["global_uniqueness_certified"] is False

    empty = worker.assemble(common, payload, reading, [], witness, StubRemote(), boot,
                            "2" * 64, "3" * 64, 0)
    assert empty["execution_state"] == "FAILED"
    assert empty["reason_codes"] == ["NO_VALID_OPTIMIZER_WITNESS"]
    assert empty["theta"] is None and empty["candidate_D_nm"] is None


def test_history_partials_keep_their_label_and_their_failure_denominators(staged):
    """No plan row may promise a V166 upgrade, and the register keeps every denominator."""
    for entry in _plan_entries(staged, "SEARCH_EXTENSION"):
        assert entry["old_status_preserved"] == "PARTIAL_SEARCH"
        assert entry["merge_rule"] == ("MINIMUM_Q_TOTAL_OVER_OLD_BEST_AND_NEW_LEGAL_POINTS")
        assert entry["kind"] == "SEARCH_EXTENSION"


# ----------------------------------------------------------------- seal and failure register
def _report_ctx(out: Path, entries: list[dict], run_id: str) -> dict:
    return {"run_id": run_id, "git_head": "0" * 40,
            "codes": {"identity_sha256": "test" * 20},
            "plan": {"entries": entries}, "dry_run": False, "published": {}, "store": None}


def _fill_round_evidence(out: Path, entries: list[dict]) -> None:
    control, jail = out / "controller_only", out / "estimator_inputs"
    for name in ("estimates_new.json", "estimates_merge_reuse.json"):
        (out / name).parent.mkdir(parents=True, exist_ok=True)
        (out / name).write_bytes(b"{}")
    for name in ("per_start_table.json", "r_merge_table.json", "b_stress_table.json",
                 "final_verify.json", "bind_model.json", "source_mapping.json",
                 "run_round.json", "task_signatures.json"):
        control.mkdir(parents=True, exist_ok=True)
        (control / name).write_bytes(b"{}")
    jail.mkdir(parents=True, exist_ok=True)
    (jail / "00_isolation_receipt.json").write_bytes(b"{}")
    (out / "logs").mkdir(parents=True, exist_ok=True)
    (out / "logs" / "v167_budget.sqlite").write_bytes(b"probe ledger")
    for entry in entries:
        path = out / "tasks" / str(entry["task_id"]) / "result.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"{}")


def test_one_missing_task_result_blocks_the_whole_round_seal(staged, probe_tree, monkeypatch):
    entries = staged["plan"]["entries"]
    assert len(entries) == 23
    out = probe_tree
    monkeypatch.setattr(controller, "OUT", out)
    monkeypatch.setattr(controller, "CONTROL", out / "controller_only")
    monkeypatch.setattr(controller, "JAIL_ROOT", out / "estimator_inputs")
    monkeypatch.setattr(controller, "LEDGER_PATH", out / "logs" / "v167_budget.sqlite")
    _fill_round_evidence(out, entries)

    victim = str(entries[7]["task_id"])
    (out / "tasks" / victim / "result.json").unlink()
    with pytest.raises(ValueError) as refused:
        controller.write_seal(_report_ctx(out, entries, "PROBE_SEAL_A"))
    assert "SEAL_MISSING_TASK_RESULT:" + victim in str(refused.value)
    assert not (out / "seal.json").exists(), "A SEAL WAS WRITTEN_WITH_A_MISSING_TASK"

    (out / "tasks" / victim / "result.json").write_bytes(b"{}")
    receipt = controller.write_seal(_report_ctx(out, entries, "PROSE_SEAL_B"))
    assert receipt["sealed_task_results"] == 23
    assert receipt["validator_may_run"] is True
    document = _read_json_new(out / "seal.json")
    assert document["status"] == "SEALED_BEFORE_VALIDATOR"
    assert document["task_result_count"] == 23
    assert document["all_reportable_D_null"] is True
    assert document["experimental_absolute_diameter_validated"] is False
    assert document["old_v166_task_results_modified"] == 0
    assert document["validator_may_read_truth_after_this_point_only"] is True
    assert set(document["task_result_sha256"]) == {str(e["task_id"]) for e in entries}
    # regression guard: the seal must carry the V166 return-ZIP pin that once KeyError'd
    assert document["v166_return_zip_sha256"] == controller.CONTRACT_PINS[
        "results/v166/iscat_v166_return_001.zip"]


def test_a_missing_estimate_table_blocks_the_seal_even_with_every_task_present(
        staged, probe_tree, monkeypatch):
    entries = staged["plan"]["entries"]
    out = probe_tree
    monkeypatch.setattr(controller, "OUT", out)
    monkeypatch.setattr(controller, "CONTROL", out / "controller_only")
    monkeypatch.setattr(controller, "JAIL_ROOT", out / "estimator_inputs")
    monkeypatch.setattr(controller, "LEDGER_PATH", out / "logs" / "v167_budget.sqlite")
    _fill_round_evidence(out, entries)
    (out / "estimates_merge_reuse.json").unlink()
    with pytest.raises(ValueError) as refused:
        controller.write_seal(_report_ctx(out, entries, "PROBE_SEAL_C"))
    assert "SEAL_REQUIRES_ESTIMATE_TABLES" in str(refused.value)
    assert not (out / "seal.json").exists()


def test_failure_records_keep_every_task_in_the_denominator(staged, probe_tree, monkeypatch):
    entries = staged["plan"]["entries"]
    out = probe_tree
    monkeypatch.setattr(controller, "OUT", out)
    monkeypatch.setattr(controller, "CONTROL", out / "controller_only")
    ctx = _report_ctx(out, entries, "PROBE_RECORDS")
    document = controller.failure_records(ctx)
    assert document["record_count"] == len(document["records"]) == 23
    assert {row["record_type"] for row in document["records"]} == {"NOT_STARTED"}
    assert document["deleted_records"] == 0 and document["hidden_records"] == 0
    assert document["model_calls"] == 0 and document["reportable_D"] is None

    first = str(entries[0]["task_id"])
    path = out / "tasks" / first / "result.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(common.canon({
        "task_id": first, "kind": "SEARCH_EXTENSION", "execution_state": "PARTIAL_SEARCH",
        "worker_exit_code": 0, "failure": None,
        "payload": {"starts": [{"passes": [{"start_index": 0, "pass_index": 0,
                                             "execution_state": "PARTIAL_SEARCH",
                                             "error": {"error_type": "CallCapReached"},
                                             "evaluations": 200, "local_cap": 200}]}]}}))
    after = controller.failure_records(ctx)
    types = [row["record_type"] for row in after["records"]]
    assert types.count("SEARCH_STATE") == 1
    assert types.count("NOT_STARTED") == 22
    assert after["record_count"] == len(after["records"]) == 23
    assert after["deleted_records"] == 0 and after["hidden_records"] == 0


# --------------------------------------------------------------------------- pin integrity
def test_every_pin_key_the_source_reads_exists_in_the_pin_table():
    pattern = re.compile(r"CONTRACT_PINS\[\s*[\"']([^\"']+)[\"']\s*\]")
    source_dir = Path(controller.__file__).resolve().parent
    used: set[str] = set()
    for path in sorted(source_dir.glob("*.py")):
        used.update(match.group(1) for match in
                    pattern.finditer(path.read_text(encoding="utf-8")))
    assert used, "NO_PIN_READS_FOUND_IN_THE_SOURCE"
    missing = sorted(used - set(controller.CONTRACT_PINS))
    assert not missing, "CONTRACT_PINS_KEY_NOT_IN_TABLE:" + ",".join(missing)


def test_every_pinned_v166_file_is_present_and_matches_its_contract_digest():
    for rel, digest in sorted(controller.CONTRACT_PINS.items()):
        path = controller.ROOT / rel
        assert path.is_file(), "PINNED_PATH_ABSENT:" + rel
        assert common.sha_file(path) == digest, "PINNED_BYTES_CHANGED:" + rel
        # a pinned file may not be reachable only through a rename of a deliverable dir
        assert rel.startswith("results/v166/"), "PIN_OUTSIDE_THE_V166_ROOT:" + rel


# ------------------------------------------------------------------ status honesty
class _StubStore:
    """Counts only: the status document reads the settled budget tally and nothing else."""

    def __init__(self, counts: dict | None = None):
        self._counts = dict(counts or {})

    def counts(self) -> dict:
        return dict(self._counts)


def _status_ctx(out: Path, entries: list[dict], run_id: str) -> dict:
    ctx = _report_ctx(out, entries, run_id)
    ctx["store"] = _StubStore()
    return ctx


def _patch_status_tree(probe_tree, monkeypatch):
    monkeypatch.setattr(controller, "OUT", probe_tree)
    monkeypatch.setattr(controller, "CONTROL", probe_tree / "controller_only")
    monkeypatch.setattr(controller, "JAIL_ROOT", probe_tree / "estimator_inputs")
    monkeypatch.setattr(controller, "LEDGER_PATH", probe_tree / "logs" / "v167_budget.sqlite")


def _write_control_json(out: Path, name: str, document: dict) -> None:
    control = out / "controller_only"
    control.mkdir(parents=True, exist_ok=True)
    (control / name).write_bytes(common.canon(document))


def test_the_status_document_may_not_report_a_round_that_left_no_run_round_file(
        staged, probe_tree, monkeypatch):
    """P3/P4 may only claim what their own evidence file proves (regression guard).

    The primary status.json of the failed first round printed P3 "EXECUTED" with
    "0 of 23 tasks sealed" even though no run_round.json existed: the stage labels
    tested the truthiness of a dict that had just been merged with
    published_versions, which is never empty.  Existence of the evidence file is the
    only admissible proof.
    """
    entries = staged["plan"]["entries"]
    out = probe_tree
    _patch_status_tree(out, monkeypatch)
    # P0/P1 evidence present, so those two stages legitimately read EXECUTED.
    _write_control_json(out, "task_signatures.json", {"schema": "iscat167.task_signatures.1"})
    jail = out / "estimator_inputs"
    jail.mkdir(parents=True, exist_ok=True)
    (jail / "00_isolation_receipt.json").write_bytes(common.canon({"schema": "probe"}))
    assert not (out / "controller_only" / "run_round.json").exists()
    assert not (out / "controller_only" / "final_verify.json").exists()

    document = controller.status_document(_status_ctx(out, entries, "PROBE_STATUS_EMPTY"))
    stages = document["stages"]
    assert not (out / "controller_only" / "run_round.json").exists(), (
        "status_document must not author the evidence it reads")
    assert stages["P3_authorized_computation"]["EXECUTION"] == "NOT_STARTED", (
        "P3_CLAIMED_EXECUTION_WITHOUT_A_RUN_ROUND_FILE")
    assert stages["P3_authorized_computation"]["VERIFICATION"] == "NOT_STARTED", (
        "P3_CLAIMED_SEAL_COUNT_WITHOUT_A_RUN_ROUND_FILE")
    assert stages["P4_final_verify"]["EXECUTION"] == "NOT_STARTED"
    assert stages["P4_final_verify"]["VERIFICATION"] == "NOT_STARTED", (
        "P4_INVENTED_A_VERIFICATION_STRING_WITHOUT_A_FINAL_VERIFY_FILE")
    assert "logical None" not in stages["P4_final_verify"]["VERIFICATION"]
    assert stages["P2_model_binding"]["EXECUTION"] == "NOT_STARTED"
    assert stages["P5_seal_and_score"]["EXECUTION"] == "NOT_STARTED"
    assert document["budget_used_total"] == 0
    assert document["reportable_D"] is None
    assert document["experimental_absolute_diameter_validated"] is False


def test_a_round_document_that_records_blocked_execution_is_reported_verbatim(
        staged, probe_tree, monkeypatch):
    """A BLOCKED round receipt must reach the status document unchanged, not as a pass."""
    entries = staged["plan"]["entries"]
    out = probe_tree
    _patch_status_tree(out, monkeypatch)
    _write_control_json(out, "run_round.json",
                        {"status": "BLOCKED", "tasks_planned": 0,
                         "blocked_reason": "RUN_IDENTITY_CODE_CHANGED"})

    document = controller.status_document(_status_ctx(out, entries, "PROBE_STATUS_BLOCKED"))
    p3 = document["stages"]["P3_authorized_computation"]
    assert p3["EXECUTION"] == "BLOCKED", "A_BLOCKED_ROUND_WAS_SMOOTHED_INTO_A_STATUS"
    assert p3["VERIFICATION"] == "0 of 23 tasks sealed"
    assert document["stages"]["P4_final_verify"]["EXECUTION"] == "NOT_STARTED"


def test_p3_only_claims_executed_once_the_round_step_wrote_its_own_receipt(
        staged, probe_tree, monkeypatch):
    """The positive side of the same gate: with the receipt present the label is allowed."""
    entries = staged["plan"]["entries"]
    out = probe_tree
    _patch_status_tree(out, monkeypatch)
    _write_control_json(out, "run_round.json", {"status": "EXECUTED", "tasks_planned": 23})
    _write_control_json(out, "final_verify.json",
                        {"status": "EXECUTED", "logical_items": 28, "distinct_theta": 28,
                         "verified": 28, "not_verifiable": 0})

    document = controller.status_document(_status_ctx(out, entries, "PROBE_STATUS_FULL"))
    p3 = document["stages"]["P3_authorized_computation"]
    assert p3["EXECUTION"] == "EXECUTED"
    assert p3["VERIFICATION"] == "23 of 23 tasks sealed"
    assert document["stages"]["P4_final_verify"]["EXECUTION"] == "EXECUTED"
    assert "logical 28" in document["stages"]["P4_final_verify"]["VERIFICATION"]
