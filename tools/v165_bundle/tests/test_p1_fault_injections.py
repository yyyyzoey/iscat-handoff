"""Fault injections required by the V166 contract (P1 test gate).

Each test breaks one production invariant on purpose and proves the real
production guard refuses it.  Nothing here relaxes a check: the passing
"positive control" calls exist so that a refusal can be shown to come from the
injection and not from a fixture that was already broken.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "generator"))
sys.path.insert(0, str(ROOT / "validator"))

import v165_io
import v165_run
import v165_validator
from v152_budget_store import BudgetStore, StoreError, atomic_json
from v152_gls_core import GlsData
from v165_generate_height import generate
from v165_task_ids import tasks
from v165_validator import validate

GROUPS = ("ANON_01", "ANON_02", "ANON_03", "ANON_04")


def three_frame_data():
    return GlsData.from_frames(
        np.zeros((3, 13, 13), dtype=float), np.ones((3, 13, 13), dtype=float)
    )


def truth_doc():
    return {
        "cases": [
            {"case": "N01", "D_nm": 59.0, "h_nm": 391.25},
            {"case": "N02", "D_nm": 101.0, "h_nm": 432.5},
            {"case": "N03", "D_nm": 143.0, "h_nm": 478.75},
            {"case": "N04", "D_nm": 181.0, "h_nm": 526.25},
        ]
    }


def public_readings():
    readings, _validator_only = generate(truth_doc())
    return {"readings": readings}


def estimate_rows(state="FINISHED", theta=(101.0, 432.5, 0.0, 0.0)):
    return [
        {
            "task_id": row["task_id"],
            "execution_state": state,
            "theta": list(theta) if theta is not None else None,
        }
        for row in tasks()
    ]


def frozen_detections():
    return {group: [True, False, True] for group in GROUPS}


def ledger_folder(tmp_path):
    out = tmp_path / "out"
    (out / "logs").mkdir(parents=True)
    return out


def sealed_fit_store(out, task_id, cap):
    store = BudgetStore(
        out / "logs" / (v165_run.PLAN_ID + "_budget.sqlite"),
        v165_run.PLAN_ID,
        {"HEIGHT_FITS": cap},
        cap,
    )
    store.reserve(task_id, "fixture-signature", "HEIGHT_FITS", cap, v165_run.OWNER)
    return store


def test_duplicate_task_id_is_refused_before_any_reservation(tmp_path, monkeypatch):
    rows = tasks()
    doubled = [dict(rows[0]), dict(rows[0])] + [dict(row) for row in rows[2:]]
    assert len(doubled) == 28 and len({row["task_id"] for row in doubled}) == 27
    monkeypatch.setattr(v165_run, "tasks", lambda: doubled)
    with pytest.raises(ValueError, match="DUPLICATE_TASK_ID"):
        v165_run.plan_descriptors()
    # Positive control: the untouched frozen plan reserves cleanly.
    monkeypatch.undo()
    assert len(v165_run.plan_descriptors()) == 31
    # A repeated id also cannot quietly buy a second quota under a new signature.
    store = BudgetStore(tmp_path / "l.sqlite", "test", {"X": 1000}, 1000)
    store.reserve("B100000_ANON_01_NO_HEIGHT", "sig-a", "X", 10, v165_run.OWNER)
    with pytest.raises(StoreError, match="task signature changed"):
        store.reserve("B100000_ANON_01_NO_HEIGHT", "sig-b", "X", 10, v165_run.OWNER)


def test_forged_model_prediction_fails_the_ledger_audit(tmp_path):
    out = ledger_folder(tmp_path)
    task_id = "task"
    signature = "fixture-signature"
    store = sealed_fit_store(out, task_id, 20)
    caller = v165_run.ChargedCaller(store, task_id, out)
    honest = np.zeros((13, 13), dtype=float)
    honest[3, 4] = 0.25
    caller.call([101.0, 432.0, 1.0, -2.0], lambda _t: honest.copy())
    result_path = out / "tasks" / task_id / "result.json"
    atomic_json(
        result_path,
        {
            "schema": "iscat165.task_result.1",
            "signature": signature,
            "actual_calls": 1,
            "payload": {"execution_state": "FINISHED"},
        },
    )
    store.seal(task_id, v165_run.OWNER, "FINISHED", result_path)
    audit = v165_io.ledger_check(
        out, plan_id=v165_run.PLAN_ID, phases={"HEIGHT_FITS": 20}
    )
    assert audit["total_used"] == 1

    # Injection: rewrite the persisted contrast array, leaving the recorded
    # C_sha256 in the ledger untouched.
    path = out / "tasks" / task_id / "predictions" / "0001.json"
    forged = json.loads(path.read_text(encoding="utf-8"))
    forged["C"][3][4] = -0.75
    atomic_json(path, forged)
    with pytest.raises(ValueError, match="PREDICTION_HASH"):
        v165_io.ledger_check(out, plan_id=v165_run.PLAN_ID, phases={"HEIGHT_FITS": 20})


def test_changed_camera_h5_is_refused_before_any_replay(tmp_path):
    repo = tmp_path / "repo"
    (repo / "data").mkdir(parents=True)
    (repo / "tools").mkdir()
    (repo / "tools" / "v145_camera_replay.py").write_text("# fixture replay module\n", encoding="utf-8")
    camera = repo / "data" / "camera_pilot.h5"
    camera.write_bytes(b"REPLACED ARRAY FILE NOT THE FROZEN CAMERA H5")
    cfg = {
        "inputs": {"camera_h5": "data/camera_pilot.h5"},
        "frozen": {
            "camera_h5_sha256": v165_io.sha(camera),
            "camera_replay_code_sha256": "not-the-replay-code-sha",
        },
    }
    # Positive control: while the array pin matches, the audit advances to the
    # replay-code pin and refuses there, proving the array check is not vacuous.
    with pytest.raises(ValueError, match="CAMERA_REPLAY_CODE_CHANGED"):
        v165_io.camera_binding(repo, cfg)
    # Injection: one added byte in the array file is caught by the array pin.
    camera.write_bytes(camera.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="CAMERA_ARRAY_FILE_CHANGED"):
        v165_io.camera_binding(repo, cfg)


def test_swapped_variance_context_is_refused_after_preflight(tmp_path):
    out = tmp_path / "out"
    contexts = {}
    for group in GROUPS:
        diagnostic = {
            "theta": [101.0, 432.0, 0.0, 0.0],
            "frame_Y": np.zeros((3, 13, 13)).tolist(),
            "frame_V": np.ones((3, 13, 13)).tolist(),
            "base_index": 0,
            "predictions": [{"C": np.zeros((13, 13)).tolist()}],
        }
        path = out / "source_context" / (group + ".json")
        atomic_json(path, {"schema": "fixture.context.1", "diagnostic": diagnostic})
        contexts[group] = {"copy_sha256": v165_run.sha_file(path)}
    atomic_json(
        out / "preflight.json",
        {"schema": "iscat165.preflight.1", "status": "PASS", "contexts": contexts},
    )
    assert tuple(v165_run._load_contexts(out)) == GROUPS

    # Injection: rescale the saved variance of one scene after the gate pinned it.
    path = out / "source_context" / "ANON_03.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["diagnostic"]["frame_V"] = (np.ones((3, 13, 13), dtype=float) * 7.0).tolist()
    atomic_json(path, doc)
    with pytest.raises(
        ValueError, match="CONTEXT_BYTES_CHANGED_SINCE_PREFLIGHT:ANON_03"
    ):
        v165_run._load_contexts(out)


def test_second_start_cannot_exceed_its_share_of_the_task_budget(tmp_path):
    out = ledger_folder(tmp_path)
    task_id = "B100000_ANON_02_H1_R00"
    store = sealed_fit_store(out, task_id, 400)
    # The first start already consumed 398 of the 400 charged calls of this task.
    for _ in range(398):
        store.charge(
            task_id,
            v165_run.OWNER,
            [101.0, 432.0, 0.0, 0.0],
            detail={"start_index": 0, "kind": "OPTIMIZER", "invocation": "fixture"},
        )
    invoked = []
    model = SimpleNamespace(
        forward=lambda t: invoked.append(tuple(t)) or np.zeros((13, 13))
    )
    doc = v165_run.optimize_start(
        task_id=task_id,
        start_index=1,
        x0=[101.0, 432.0, 0.0, 0.0],
        data=three_frame_data(),
        reading=None,
        model=model,
        store=store,
        out=out,
    )
    assert doc["local_cap"] == 2
    assert doc["actual_calls"] <= 2
    assert store.counts()[task_id] == 400
    assert len(invoked) <= 2
    assert doc["execution_state"] == "PARTIAL_SEARCH"
    assert doc["reportable_D"] is None


def test_truth_input_with_unknown_or_missing_scene_is_refused():
    readings = public_readings()
    rows = estimate_rows()
    good = validate(rows, truth_doc(), readings, frozen_detections())
    assert len(good["task_rows"]) == 28

    unknown = truth_doc()
    unknown["cases"][0]["case"] = "N09"
    with pytest.raises(ValueError, match="UNKNOWN_SCENE_MAPPING"):
        validate(rows, unknown, readings, frozen_detections())

    short = truth_doc()
    del short["cases"][3]
    with pytest.raises(ValueError, match="UNKNOWN_SCENE_MAPPING"):
        validate(rows, short, readings, frozen_detections())


def test_scoring_refuses_missing_or_duplicated_inputs():
    readings = public_readings()
    rows = estimate_rows()
    with pytest.raises(ValueError, match="BAD_READINGS"):
        validate(rows, truth_doc(), {"readings": readings["readings"][:-1]}, frozen_detections())
    with pytest.raises(ValueError, match="MISSING_OR_DUPLICATE_OR_UNKNOWN_ESTIMATE_TASKS"):
        validate(rows + [dict(rows[0])], truth_doc(), readings, frozen_detections())
    dropped = frozen_detections()
    del dropped["ANON_04"]
    with pytest.raises(
        ValueError, match="FROZEN_DETECTION_STATUS_REQUIRED_FOR_EACH_OF_THREE_FRAMES"
    ):
        validate(rows, truth_doc(), readings, dropped)
    frame_count = frozen_detections()
    frame_count["ANON_02"] = [True, False]
    with pytest.raises(
        ValueError, match="FROZEN_DETECTION_STATUS_REQUIRED_FOR_EACH_OF_THREE_FRAMES"
    ):
        validate(rows, truth_doc(), readings, frame_count)


def test_scoring_refuses_states_that_hide_a_missing_estimate():
    readings = public_readings()
    rows = estimate_rows()
    rows[5]["execution_state"] = "PASSED"
    with pytest.raises(ValueError, match="INVALID_EXECUTION_STATE"):
        validate(rows, truth_doc(), readings, frozen_detections())
    rows = estimate_rows(state="FINISHED")
    rows[6]["theta"] = None
    with pytest.raises(ValueError, match="FINISHED_WITHOUT_THETA"):
        validate(rows, truth_doc(), readings, frozen_detections())
    rows = estimate_rows(state="FINISHED")
    rows[7]["theta"] = [float("nan"), 432.5, 0.0, 0.0]
    with pytest.raises(ValueError, match="INVALID_THETA_IN_REPORT"):
        validate(rows, truth_doc(), readings, frozen_detections())


def _full_plan_folder(tmp_path, state_cycle):
    """Write a complete 31-task sealed ledger with mixed per-task outcomes."""
    out = ledger_folder(tmp_path)
    (out / "height_input").mkdir(parents=True)
    atomic_json(
        out / "preflight.json",
        {
            "schema": "iscat165.preflight.1",
            "status": "PASS",
            "plan_sha256": "fixture-plan-sha",
            "contexts": {},
        },
    )
    atomic_json(
        out / "height_input" / "height_readings.json",
        public_readings(),
    )
    sigs = v165_run.signatures(
        "fixture-plan-sha", v165_run.sha_file(out / "preflight.json")
    )
    store = BudgetStore(
        out / "logs" / (v165_run.PLAN_ID + "_budget.sqlite"),
        v165_run.PLAN_ID,
        dict(v165_run.PHASES),
        v165_run.TOTAL,
    )
    v165_run.reserve_plan(store, sigs)
    fit_ids = {row["task_id"] for row in tasks()}
    for index, descriptor in enumerate(v165_run.plan_descriptors()):
        task_id = descriptor["task_id"]
        if task_id in fit_ids:
            payload = state_cycle[index % len(state_cycle)]()
            db_state = {
                "FINISHED": "FINISHED",
                "PARTIAL_SEARCH": "PARTIAL_BUDGET",
                "FAILED": "FAILED",
                "BLOCKED": "FAILED",
            }[payload["execution_state"]]
        else:
            payload = {"execution_state": "FINISHED"}
            db_state = "FINISHED"
        result_path = out / "tasks" / task_id / "result.json"
        atomic_json(
            result_path,
            {
                "schema": "iscat165.task_result.1",
                "signature": sigs[task_id]["signature"],
                "actual_calls": 0,
                "payload": payload,
            },
        )
        store.seal(task_id, v165_run.OWNER, db_state, result_path)
    return out, sigs


CYCLE = (
    lambda: {
        "execution_state": "FINISHED",
        "theta": [101.0, 432.5, 0.0, 0.0],
        "physical_qualification": "CONDITIONAL_SIMULATED_F2C_DEVELOPMENT",
    },
    lambda: {
        "execution_state": "PARTIAL_SEARCH",
        "theta": [104.0, 430.0, 1.0, -1.0],
        "reason_codes": ["PER_START_REAL_MODEL_CALL_CAP"],
    },
    lambda: {"execution_state": "FAILED", "theta": None},
    lambda: {
        "execution_state": "BLOCKED",
        "theta": None,
        "reason_codes": ["BLOCKED_MODEL_RESTART_REQUIRES_AUTHORIZATION"],
    },
)


def test_seal_keeps_failed_and_blocked_tasks_without_whitewash(tmp_path, monkeypatch):
    monkeypatch.setattr(v165_run, "git", lambda *_a, **_k: b"SYNTHETIC_HEAD\n")
    out, _sigs = _full_plan_folder(tmp_path, CYCLE)
    seal = v165_run.seal_estimates(tmp_path, out)
    rows = json.loads((out / "estimates.json").read_text(encoding="utf-8"))
    assert len(rows) == 28
    assert [row["task_id"] for row in rows] == [row["task_id"] for row in tasks()]
    assert all(row["reportable_D"] is None for row in rows)
    # Nothing was dropped: every planned fit survives, failures included.
    assert {row["execution_state"] for row in rows} == {
        "FINISHED",
        "PARTIAL_SEARCH",
        "FAILED",
        "BLOCKED",
    }
    # An absent compatible-diameter interval stays null instead of becoming the bounds.
    assert all(row["known_compatible_D_interval_nm"] is None for row in rows)
    states = {row["execution_state"]: row for row in rows}
    assert states["FAILED"]["physical_qualification"] == "NOT_QUALIFIED_FAILED"
    assert states["BLOCKED"]["physical_qualification"] == "NOT_QUALIFIED_BLOCKED"
    assert (
        states["PARTIAL_SEARCH"]["physical_qualification"]
        == "CONDITIONAL_SIMULATED_F2C_DEVELOPMENT"
    )
    assert seal["status"] == "SEALED_BEFORE_VALIDATOR"
    assert seal["all_reportable_D_null"] is True
    assert seal["experimental_absolute_diameter_validated"] is False
    assert seal["validator_may_read_truth_after_this_point_only"] is True
    assert seal["execution_code_head"] == "SYNTHETIC_HEAD"
    assert len(seal["task_result_sha256"]) == 28
    recorded = (out / "estimates.sha256").read_text(encoding="ascii").strip()
    assert recorded == seal["estimates_sha256"]


def test_seal_blocks_when_an_estimate_result_is_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(v165_run, "git", lambda *_a, **_k: b"SYNTHETIC_HEAD\n")
    out, _sigs = _full_plan_folder(tmp_path, CYCLE)
    missing = tasks()[10]["task_id"]
    (out / "tasks" / missing / "result.json").unlink()
    with pytest.raises(ValueError) as caught:
        v165_run.seal_estimates(tmp_path, out)
    message = str(caught.value)
    assert missing in message
    # The seal-layer guard and the ledger seal audit both refuse a dropped task;
    # whichever fires, the run must stop rather than quietly seal 27 estimates.
    assert (
        "ESTIMATE_RESULT_MISSING:" + missing in message
        or "TASK_SEAL_CHANGED:" + missing in message
    )
    assert not (out / "estimates.json").exists()
    assert not (out / "seal.json").exists()


def test_post_seal_scoring_cannot_rewrite_or_use_an_unsealed_estimate_file(
    tmp_path, monkeypatch
):
    rows = estimate_rows()
    estimates = tmp_path / "estimates.json"
    raw = (json.dumps(rows) + "\n").encode("utf-8")
    estimates.write_bytes(raw)
    (tmp_path / "estimates.sha256").write_text(
        v165_run.sha_bytes(raw) + "\n", encoding="ascii"
    )
    atomic_json(tmp_path / "truth.json", truth_doc())
    atomic_json(tmp_path / "readings.json", public_readings())
    atomic_json(tmp_path / "frozen_detections.json", frozen_detections())
    score = tmp_path / "validator_only" / "score.json"
    argv = [
        "v165_validator",
        "--estimates", str(estimates),
        "--estimates-sha256", str(tmp_path / "estimates.sha256"),
        "--truth", str(tmp_path / "truth.json"),
        "--readings", str(tmp_path / "readings.json"),
        "--frozen-detections", str(tmp_path / "frozen_detections.json"),
        "--out", str(score),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    v165_validator.main()
    assert score.is_file()
    with pytest.raises(FileExistsError, match="DO_NOT_OVERWRITE_VALIDATOR_SCORE"):
        v165_validator.main()
    # Injection: change one sealed estimate byte after the SHA was recorded.
    estimates.write_bytes(raw + b" ")
    with pytest.raises(ValueError, match="ESTIMATE_SHA_UNSEALED_OR_CHANGED"):
        v165_validator.main()


def test_anon_group_label_is_never_truncated_to_anon():
    group = v165_run._profile_group
    profile_ids = [
        "PROFILE_100000_ANON_01_m5_free_hxy",
        "PROFILE_100000_ANON_02_m5_free_hxy",
        "PROFILE_100000_ANON_03_m5_free_hxy",
        "PROFILE_100000_ANON_04_p5_height_sigma10",
    ]
    assert [group(item) for item in profile_ids] == list(GROUPS)
    assert len({group(item) for item in profile_ids}) == 4
    for malformed in ("PROFILE_100000_ANON", "PROFILE_100000_B01_m5", "ANON_01"):
        with pytest.raises(ValueError, match="PROFILE_TASK_ID_SHAPE"):
            group(malformed)
