from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

import v165_io
import v165_run
import v165_guard
from v152_budget_store import BudgetStore, atomic_json
from v152_gls_core import CallCapReached, GlsData
from v165_objective import HeightReading
from v165_task_ids import tasks


def observation(theta, c=None, model_id="SYNTHETIC_NOT_F2C"):
    theta = tuple(float(x) for x in theta)
    score = np.zeros((13, 13), dtype=float) if c is None else np.asarray(c, dtype=float)
    bg = np.ones((17, 17), dtype=float)
    intensity = bg.copy()
    contrast = np.zeros((17, 17), dtype=float)
    return SimpleNamespace(
        Ibg=bg,
        I=intensity,
        C=contrast,
        score_C=score,
        theta=theta,
        model_id=model_id,
    )


def data_fixture():
    y = np.zeros((3, 13, 13), dtype=float)
    variance = np.ones_like(y)
    return GlsData.from_frames(y, variance)


def store_fixture(tmp_path, phase="X", cap=20, task_id="task"):
    store = BudgetStore(tmp_path / "budget.sqlite", "test", {phase: 1000}, 1000)
    store.reserve(task_id, "signature", phase, cap, v165_run.OWNER)
    return store


def test_charged_prediction_persists_complete_observation(tmp_path):
    store = store_fixture(tmp_path)
    caller = v165_run.ChargedCaller(store, "task", tmp_path / "out")
    theta = [101.0, 432.0, 1.0, -2.0]
    result = caller.call(theta, lambda _t: observation(theta))
    assert result["seq"] == 1
    doc = json.loads((tmp_path / "out" / result["prediction_path"]).read_text())
    assert set(("Ibg", "I", "C", "score_C")) <= set(doc["observation"])
    assert doc["requested_theta"] == theta
    assert doc["returned_theta"] == theta
    assert doc["model_id"] == "SYNTHETIC_NOT_F2C"
    for name in ("Ibg", "I", "C", "score_C"):
        meta = doc["observation_metadata"][name]
        assert meta["shape"] == list(np.asarray(doc["observation"][name]).shape)
        assert meta["dtype"] == "float64"
        assert len(meta["sha256"]) == 64
    assert v165_run._attempt_rows(store, "task")[0]["state"] == "RETURNED"


def test_duplicate_theta_reuses_exact_prediction_without_second_charge(tmp_path):
    store = store_fixture(tmp_path)
    caller = v165_run.ChargedCaller(store, "task", tmp_path / "out")
    theta = [101.0, 432.0, 0.0, 0.0]
    first = caller.call(theta, lambda _t: observation(theta))
    calls = []
    second = caller.call(theta, lambda t: calls.append(t) or observation(t))
    assert calls == []
    assert second["reused_exact_returned_prediction"] is True
    assert second["seq"] == first["seq"]
    assert store.counts()["task"] == 1


def test_budget_rejects_before_extra_model_call(tmp_path):
    store = store_fixture(tmp_path, cap=1)
    caller = v165_run.ChargedCaller(store, "task", tmp_path / "out")
    calls = []
    caller.call([101.0, 432.0, 0.0, 0.0], lambda t: calls.append(t) or observation(t))
    with pytest.raises(CallCapReached):
        caller.call(
            [102.0, 432.0, 0.0, 0.0],
            lambda t: calls.append(t) or observation(t),
        )
    assert len(calls) == 1
    assert store.counts()["task"] == 1


def test_over_budget_reservation_is_rejected(tmp_path):
    store = BudgetStore(tmp_path / "b.sqlite", "test", {"X": 1}, 1)
    with pytest.raises(CallCapReached):
        store.reserve("task", "signature", "X", 2, v165_run.OWNER)


def test_malformed_prediction_is_charged_and_recorded(tmp_path):
    store = store_fixture(tmp_path)
    caller = v165_run.ChargedCaller(store, "task", tmp_path / "out")
    theta = [101.0, 432.0, 0.0, 0.0]
    with pytest.raises(ValueError, match="MODEL_OUTPUT"):
        caller.call(theta, lambda _t: observation(theta, np.zeros((12, 13))))
    assert store.counts()["task"] == 1
    assert v165_run._attempt_rows(store, "task")[0]["state"] == "MODEL_ERROR"


def test_atomic_prediction_write_failure_is_fatal_and_charged(tmp_path):
    store = store_fixture(tmp_path)

    def broken_writer(_path, _obj):
        raise OSError("SYNTHETIC_DISK_FAILURE")

    caller = v165_run.ChargedCaller(
        store, "task", tmp_path / "out", prediction_writer=broken_writer
    )
    theta = [101.0, 432.0, 0.0, 0.0]
    with pytest.raises(v165_run.FatalPersistenceError):
        caller.call(theta, lambda _t: observation(theta))
    assert store.counts()["task"] == 1
    assert v165_run._attempt_rows(store, "task")[0]["state"] == "CHARGED"


def test_evaluate_stored_uses_one_objective_evaluation(tmp_path, monkeypatch):
    calls = []
    original = v165_run.augmented_objective

    def counted(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(v165_run, "augmented_objective", counted)
    score = v165_run.evaluate_stored(
        [101.0, 432.0, 0.0, 0.0],
        np.zeros((13, 13)),
        data_fixture(),
        HeightReading("r", "ANON_02", 0, 1.0, 432.0),
    )
    assert len(calls) == 1
    assert score["reportable_D"] is None


def test_running_start_recovers_as_partial_without_replay(tmp_path):
    store = store_fixture(tmp_path)
    start = tmp_path / "out/tasks/task/starts/000.json"
    checkpoint = {
        "schema": "iscat165.start_checkpoint.1",
        "task_id": "task",
        "start_index": 0,
        "execution_state": "RUNNING",
        "x0": [101.0, 432.0, 0.0, 0.0],
        "local_cap": 200,
        "calls_at_checkpoint": 7,
        "charged_calls_at_checkpoint": 7,
        "best_at_checkpoint": {
            "theta": [101.0, 432.0, 0.0, 0.0],
            "Q_total": 5.0,
            "C_sha256": "0" * 64,
        },
    }
    atomic_json(start, checkpoint)
    invoked = []
    result = v165_run.optimize_start(
        task_id="task",
        start_index=0,
        x0=[101.0, 432.0, 0.0, 0.0],
        data=data_fixture(),
        reading=None,
        model=SimpleNamespace(forward=lambda _t: invoked.append(1)),
        store=store,
        out=tmp_path / "out",
    )
    assert invoked == []
    assert result["execution_state"] == "PARTIAL_SEARCH"
    assert result["best"]["Q_total"] == 5.0
    assert "SCIPY_STATE_UNRECOVERABLE" in result["reason_codes"]


def test_binding_replays_all_twenty_four_legal_records(tmp_path):
    store = BudgetStore(
        tmp_path / "b.sqlite",
        "test",
        {"MODEL_BINDING": 100},
        100,
    )
    store.reserve(v165_run.BIND_TASK, "sig", "MODEL_BINDING", 100, v165_run.OWNER)
    legal = {}
    images = {}
    dispatch = {}
    for gi in range(1, 5):
        group = f"ANON_{gi:02d}"
        rows = []
        for start in range(6):
            theta = [50.0 + gi * 5 + start, 390.0 + start, start, -start]
            c = np.zeros((13, 13))
            c[0, start] = gi + start / 10
            rows.append(
                {
                    "theta": theta,
                    "C": c.tolist(),
                    "record_path": f"{group}/{start}.json",
                }
            )
            images[tuple(theta)] = c
            dispatch[tuple(theta)] = group
        legal[group] = {"six": rows}
    model = SimpleNamespace(
        model_id=v165_run.MODEL_ID,
        forward=lambda theta: observation(theta, images[tuple(float(x) for x in theta)]),
    )
    result = v165_run.binding_task(model, store, tmp_path / "out", legal)
    assert result["bound_legal_records"] == 24
    assert len(result["rows"]) == 24
    assert store.counts()[v165_run.BIND_TASK] == 24


def test_fit_continues_after_start_zero_ordinary_failure(tmp_path, monkeypatch):
    task = {
        "task_id": "B100000_ANON_02_NO_HEIGHT",
        "group": "ANON_02",
        "replicate": None,
        "sigma_nm": None,
    }
    store = store_fixture(
        tmp_path,
        phase="HEIGHT_FITS",
        cap=400,
        task_id=task["task_id"],
    )
    witness = {
        "theta": [101.0, 432.0, 0.0, 0.0],
        "Q_total": 10.0,
        "C_sha256": "0" * 64,
    }
    monkeypatch.setattr(v165_run, "_witness_rows", lambda *args: [witness])

    def fake_optimize(**kwargs):
        if kwargs["start_index"] == 0:
            raise RuntimeError("SYNTHETIC_START_ZERO_FAILURE")
        return {
            "execution_state": "FINISHED",
            "start_index": 1,
            "best": {"theta": [102.0, 432.0, 1.0, 1.0], "Q_total": 1.0},
            "actual_calls": 10,
            "error": None,
        }

    monkeypatch.setattr(v165_run, "optimize_start", fake_optimize)
    result = v165_run.fit_one_task(
        task=task,
        data=data_fixture(),
        context={},
        legal_group={"six": []},
        fixed_starts={
            "first": {"theta": [101.0, 432.0, 0.0, 0.0]},
            "second": {"theta": [102.0, 432.0, 1.0, 1.0]},
        },
        reading=None,
        model=SimpleNamespace(model_id="synthetic"),
        store=store,
        out=tmp_path / "out",
    )
    assert result["execution_state"] == "PARTIAL_SEARCH"
    assert len(result["starts"]) == 2
    assert result["starts"][0]["execution_state"] == "FAILED"
    assert "START_0_FAILED_CONTINUED_TO_START_1" in result["reason_codes"]
    assert result["candidate_D"] == 102.0


def test_final_verify_emits_records_for_all_twenty_eight_tasks(tmp_path, monkeypatch):
    store = BudgetStore(
        tmp_path / "b.sqlite",
        "test",
        {"FINAL_VERIFY": 600},
        600,
    )
    store.reserve(v165_run.FINAL_TASK, "sig", "FINAL_VERIFY", 600, v165_run.OWNER)
    theta = [101.0, 432.0, 0.0, 0.0]
    c = np.zeros((13, 13))
    c[0, 0] = 0.1
    model = SimpleNamespace(
        model_id=v165_run.MODEL_ID,
        forward=lambda t: observation(t, c),
    )
    monkeypatch.setattr(
        v165_run,
        "construct_model",
        lambda *args, **kwargs: (model, {"synthetic_loader": True}),
    )
    fit_payloads = {}
    plans = tasks()
    for index, task in enumerate(plans):
        fit_payloads[task["task_id"]] = (
            {
                "execution_state": "FINISHED",
                "theta": theta,
                "optimizer_best": {
                    "theta": theta,
                    "C_sha256": v165_run.array_sha(c),
                },
            }
            if index % 2 == 0
            else {
                "execution_state": "BLOCKED",
                "theta": None,
                "reason_codes": ["TASK_NOT_VERIFIABLE"],
            }
        )
    contexts = {
        f"ANON_{i:02d}": {
            "theta": theta,
            "base_index": 0,
            "predictions": [{"C": c.tolist()}],
        }
        for i in range(1, 5)
    }
    result = v165_run.final_verify_task(
        tmp_path, store, tmp_path / "out", contexts, fit_payloads
    )
    assert result["execution_state"] == "FINISHED"
    assert len(result["checks"]) == 32
    assert result["not_verifiable_task_count"] == 14
    assert sum(
        row.get("kind") == "TASK_NOT_VERIFIABLE" for row in result["checks"]
    ) == 14


def _minimal_workflow(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    out = repo / "results/v165"
    out.mkdir(parents=True)
    atomic_json(
        out / "preflight.json",
        {
            "schema": "iscat165.preflight.1",
            "status": "PASS",
            "plan_sha256": "a" * 64,
            "source_lock": {},
        },
    )
    atomic_json(out / "frozen_detections.json", {})
    groups = ["ANON_01", "ANON_02", "ANON_03", "ANON_04"]
    start_doc = {}
    starts = {}
    for group in groups:
        first = [101.0, 432.0, 0.0, 0.0]
        second = [101.0, 455.0, 1.0, 1.0]
        starts[group] = {
            "first": {"theta": first, "record_path": group + "/first"},
            "second": {"theta": second, "record_path": group + "/second"},
            "stratum_available": True,
            "stratum_flag": None,
            "all_six": list(range(6)),
            "six": [],
        }
        start_doc[group] = {
            "first": {"theta": first, "source_record": group + "/first"},
            "second": {"theta": second, "source_record": group + "/second"},
            "stratum_available": True,
            "stratum_flag": None,
            "all_six": list(range(6)),
        }
    atomic_json(out / "starts_by_group.json", start_doc)
    contexts = {
        group: {
            "theta": [101.0, 432.0, 0.0, 0.0],
            "frame_Y": np.zeros((3, 13, 13)).tolist(),
            "frame_V": np.ones((3, 13, 13)).tolist(),
            "base_index": 0,
            "predictions": [{"C": np.zeros((13, 13)).tolist()}],
        }
        for group in groups
    }
    monkeypatch.setattr(v165_run, "_load_contexts", lambda _out: contexts)
    monkeypatch.setattr(
        v165_run,
        "_readings",
        lambda _path: (
            {"schema": "synthetic", "readings": []},
            {
                task["task_id"]: HeightReading(
                    task["task_id"],
                    task["group"],
                    task["replicate"],
                    task["sigma_nm"],
                    432.0,
                )
                for task in tasks()
                if task["sigma_nm"] is not None
            },
        ),
    )
    monkeypatch.setattr(v165_io, "lock_sources", lambda _repo: {})
    monkeypatch.setattr(v165_io, "estimator_inputs_check", lambda _docs: {})
    monkeypatch.setattr(v165_io, "frozen_starts", lambda _repo, _groups: starts)
    monkeypatch.setattr(v165_io, "ledger_check", lambda *a, **k: {})
    monkeypatch.setattr(
        v165_guard,
        "install",
        lambda _repo: SimpleNamespace(report=lambda: {"synthetic_guard": True}),
    )
    return repo, out, starts


def test_execute_constructs_model_once_and_preserves_all_task_states(
    tmp_path, monkeypatch
):
    repo, out, _starts = _minimal_workflow(tmp_path, monkeypatch)
    construct_calls = []
    theta = [101.0, 432.0, 0.0, 0.0]

    def fake_construct(*args, **kwargs):
        construct_calls.append(1)
        return (
            SimpleNamespace(
                model_id=v165_run.MODEL_ID,
                forward=lambda t: observation(t),
            ),
            {
                "model_id": v165_run.MODEL_ID,
                "loader_attempts": [],
                "loader_calls": 0,
            },
        )

    def fake_fit(**kwargs):
        state = (
            "PARTIAL_SEARCH"
            if kwargs["task"]["task_id"] == "B100000_ANON_01_NO_HEIGHT"
            else "FINISHED"
        )
        return {
            "execution_state": state,
            "task_id": kwargs["task"]["task_id"],
            "group": kwargs["task"]["group"],
            "replicate": kwargs["task"]["replicate"],
            "sigma_nm": kwargs["task"]["sigma_nm"],
            "reading_id": kwargs["reading"].reading_id if kwargs["reading"] else None,
            "starts": [],
            "theta": theta,
            "candidate_D": theta[0],
            "reportable_D": None,
            "known_compatible_D_interval_nm": None,
            "parameter_bounds_D_nm": [30.0, 200.0],
            "reason_codes": ["SYNTHETIC"],
        }

    monkeypatch.setattr(v165_run, "construct_model", fake_construct)
    monkeypatch.setattr(v165_run, "fit_one_task", fake_fit)
    monkeypatch.setattr(
        v165_run,
        "binding_task",
        lambda *a, **k: {
            "execution_state": "FINISHED",
            "model_id": v165_run.MODEL_ID,
            "bound_legal_records": 24,
            "rows": [],
            "reportable_D": None,
        },
    )
    monkeypatch.setattr(
        v165_run,
        "final_verify_task",
        lambda *a, **k: {
            "execution_state": "FINISHED",
            "checks": [],
            "failures": [],
            "not_verifiable_task_count": 0,
            "reportable_D": None,
            "reason_codes": [],
        },
    )
    status = v165_run.execute(
        repo, out, out / "synthetic_readings.json", resume=False
    )
    assert construct_calls == [1]
    assert status["fit_tasks"] == 28
    assert status["fit_partial_search"] == 1
    assert status["execution_state"] == "FINISHED_WITH_PARTIAL_SEARCH"
    assert len(list((out / "tasks").glob("B100000_*"))) == 28
    assert v165_run.execute(
        repo, out, out / "synthetic_readings.json", resume=True
    )["execution_state"] == "FINISHED_WITH_PARTIAL_SEARCH"
    assert construct_calls == [1]


def test_restart_with_sealed_loader_blocks_unfinished_dependents(
    tmp_path, monkeypatch
):
    repo, out, _starts = _minimal_workflow(tmp_path, monkeypatch)
    construction = []

    def fake_construct(*args, **kwargs):
        construction.append(1)
        return (
            SimpleNamespace(
                model_id=v165_run.MODEL_ID,
                forward=lambda t: observation(t),
            ),
            {"model_id": v165_run.MODEL_ID, "loader_attempts": [], "loader_calls": 0},
        )

    monkeypatch.setattr(v165_run, "construct_model", fake_construct)
    monkeypatch.setattr(
        v165_run,
        "binding_task",
        lambda *a, **k: {
            "execution_state": "FINISHED",
            "model_id": v165_run.MODEL_ID,
            "bound_legal_records": 24,
            "rows": [],
            "reportable_D": None,
        },
    )

    def fatal_first_fit(**_kwargs):
        raise v165_run.FatalPersistenceError("SYNTHETIC_PROCESS_INTERRUPTION")

    monkeypatch.setattr(v165_run, "fit_one_task", fatal_first_fit)
    with pytest.raises(v165_run.FatalPersistenceError):
        v165_run.execute(repo, out, out / "synthetic_readings.json", resume=False)
    assert construction == [1]

    monkeypatch.setattr(
        v165_run,
        "construct_model",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("RESTART_MUST_NOT_RECONSTRUCT_LIVE_MODEL")
        ),
    )
    status = v165_run.execute(
        repo, out, out / "synthetic_readings.json", resume=True
    )
    assert status["execution_state"] == "BLOCKED_OR_PARTIAL"
    assert status["fit_blocked"] == 28
    assert construction == [1]


def test_public_height_readings_reject_missing_group_and_rounded_label():
    doc = {
        "seed": 16520261027,
        "no_camera_noise_draw": True,
        "no_new_camera_exposures": True,
        "no_experimental_height_observation": True,
        "readings": [],
    }
    for group in ("ANON_01", "ANON_02", "ANON_03", "ANON_04"):
        for sigma in (10, 1):
            for replicate in range(3):
                doc["readings"].append(
                    {
                        "reading_id": f"B100000_{group}_H{sigma}_R{replicate:02d}",
                        "group": group,
                        "B": 100000,
                        "replicate": replicate,
                        "sigma_nm": float(sigma),
                        "z_nm": 400.0,
                        "hypothetical": True,
                        "independent_camera_noise_assumption": True,
                        "generation": "GAUSSIAN_HEIGHT_NOISE_ONLY_NO_NEW_CAMERA_FRAMES",
                    }
                )
    v165_io.public_readings_check(doc)
    doc["readings"][0]["reading_id"] = "B100000_ANON_01_H1_R0"
    with pytest.raises(ValueError, match="READING_ID_TASK_GRID"):
        v165_io.public_readings_check(doc)


def test_install_check_rejects_tampered_frozen_member(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    raw = b"{}\n"
    row = {
        "path": "config/frozen.json",
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    (bundle / "config").mkdir()
    (bundle / "config/frozen.json").write_bytes(raw)
    (bundle / "manifest_sha256.csv").write_text(
        "path,bytes,sha256\n"
        f"{row['path']},{row['bytes']},{row['sha256']}\n",
        encoding="utf-8",
    )
    monkey_bundle = v165_io.ZIP_MEMBERS
    v165_io.ZIP_MEMBERS = 2
    try:
        v165_io.install_check(bundle)
        (bundle / "config/frozen.json").write_bytes(b"changed")
        with pytest.raises(ValueError, match="FROZEN_MEMBER_CHANGED"):
            v165_io.install_check(bundle)
    finally:
        v165_io.ZIP_MEMBERS = monkey_bundle


def test_truth_guard_denies_generator_import_in_subprocess(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    script = (
        "import sys\n"
        f"sys.path.insert(0, {str(ROOT / 'code')!r})\n"
        "import v165_guard\n"
        f"v165_guard.install({str(repo)!r})\n"
        "try:\n"
        " import v165_generate_height\n"
        "except RuntimeError as exc:\n"
        " assert 'V165_TRUTH_GUARD_IMPORT_DENIED' in str(exc)\n"
        "else:\n"
        " raise SystemExit('FORBIDDEN_IMPORT_ALLOWED')\n"
    )
    process = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert process.returncode == 0, process.stdout + process.stderr


def test_test_suite_does_not_import_real_model_or_have_truth_literals():
    test_dir = ROOT / "tests"
    forbidden_modules = {"v146_runtime", "v142_model", "field_forward_reference"}
    imports = []
    for path in test_dir.glob("test_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
    assert not [
        name for name in imports if name.split(".", 1)[0] in forbidden_modules
    ]
    hits = v165_io.assert_no_truth_literals(ROOT / "code")
    assert hits["offenders"] == []
