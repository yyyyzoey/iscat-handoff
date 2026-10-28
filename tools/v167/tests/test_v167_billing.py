"""V167 P2/P4 production tests: billing, reuse and the single-construction rule.

Every test here drives the real PredictionService and the real frozen SQLite ledger
(tools/v165_bundle/code/v152_budget_store.py).  The only substitution is the model
itself: the ``no_real_model_construction`` tripwire makes any F2c import raise, so a
green run of this file is evidence about accounting, never about the physics.
"""
from __future__ import annotations

import copy
import json

import numpy as np
import pytest

from v152_budget_store import StoreError as LedgerStoreError

import v167_common as common
import v167_controller as controller
import v167_service as service_mod

from conftest import TEST_PREFIX, fake_forward

THETA = [120.0, 420.0, 0.0, 0.0]
ALT = [119.5, 421.0, 1.0, -1.0]


def _is_stop_condition(exc: BaseException) -> bool:
    """The controller's own rule for 'this failure must abort the authorized run'."""
    return any(marker in type(exc).__name__ or marker in str(exc)
               for marker in controller.STOP_MARKERS)


def _reserve(service, task_id, cap):
    return service.store.reserve(task_id, "test-signature-" + task_id, "BIAS_STRESS",
                                 cap, common.OWNER)


def _attempts(service, task_id):
    with service.store.db() as conn:
        return conn.execute("SELECT seq,state,detail FROM attempts WHERE task=? ORDER BY seq",
                            (task_id,)).fetchall()


def test_charge_is_durable_before_the_model_is_invoked(service):
    """The exact V166 failure: a call that returned without ever being billed."""
    task = TEST_PREFIX + "CHARGE1"
    _reserve(service, task, 5)
    seen = {}

    def invoke(theta):
        rows = _attempts(service, task)
        seen["rows"] = rows
        seen["live_model_imported"] = [name for name in ("v142_model", "v146_runtime")
                                       if name in __import__("sys").modules]
        if not rows or rows[-1][1] != "CHARGED":
            raise AssertionError("MODEL INVOKED BEFORE A DURABLE CHARGE")
        return fake_forward(theta)

    info = service.charged_call(task, THETA, invoke, start_index=0, kind="OPTIMIZER")
    assert seen["rows"] and seen["rows"][-1][1] == "CHARGED"
    assert info["charged"] is True and info["seq"] == 1
    assert service.store.counts()[task] == 1
    after = _attempts(service, task)
    assert after[-1][1] == "RETURNED"


def test_repeated_theta_is_a_cache_hit_that_consumes_nothing(service):
    task = TEST_PREFIX + "CACHE1"
    _reserve(service, task, 5)
    first = service.charged_call(task, THETA, fake_forward, start_index=0, kind="OPTIMIZER")
    used_after_first = dict(service.store.counts())
    second = service.charged_call(task, THETA, fake_forward, start_index=0, kind="OPTIMIZER")
    assert first["charged"] is True and first["cache_hit"] is not True
    assert second["charged"] is False and second["cache_hit"] is True
    assert second["seq"] == first["seq"]
    assert np.array_equal(second["C"], first["C"])
    assert dict(service.store.counts()) == used_after_first
    assert len(_attempts(service, task)) == 1
    rows = [json.loads(line) for line in
            service.cache_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows[-1]["new_consumption"] == 0
    assert rows[-1]["source_charged_task"] == task
    assert rows[-1]["task_id"] == task
    assert rows[-1]["origin"] == "v167_charged"
    assert rows[-1]["source_prediction"] == first["prediction_path"]
    assert rows[-1]["source_prediction_sha256"] == first["prediction_sha256"]
    assert service.real_calls == 1 and service.cache_hits == 1


def test_a_model_error_keeps_its_charge_visible_as_a_billed_failure(service):
    """No silent refund: the cap is consumed by the call that actually happened."""
    task = TEST_PREFIX + "ERROR1"
    _reserve(service, task, 3)

    def broken(theta):
        raise RuntimeError("synthetic model fault")

    with pytest.raises(RuntimeError):
        service.charged_call(task, THETA, broken, start_index=0, kind="OPTIMIZER")
    assert service.store.counts()[task] == 1
    assert _attempts(service, task)[-1][1] == "MODEL_ERROR"


def test_persistent_cap_blocks_further_model_calls(service):
    task = TEST_PREFIX + "CAP00001"
    _reserve(service, task, 2)
    service.charged_call(task, THETA, fake_forward, start_index=0, kind="OPTIMIZER")
    service.charged_call(task, ALT, fake_forward, start_index=0, kind="OPTIMIZER")
    with pytest.raises(service_mod.CallCapReached):
        service.charged_call(task, [130.0, 430.0, 0.0, 0.0], fake_forward,
                             start_index=0, kind="OPTIMIZER")
    assert service.store.counts()[task] == 2


def test_reservation_cannot_exceed_the_frozen_phase_or_total(service):
    with pytest.raises(service_mod.CallCapReached):
        service.store.reserve(TEST_PREFIX + "OVERCAP", "sig", "BIAS_STRESS", 7201,
                              common.OWNER)
    with pytest.raises(ValueError):
        service.store.reserve(TEST_PREFIX + "BADPHASE", "sig", "NOT_A_PHASE", 10,
                              common.OWNER)
    # A call with no owned reservation is refused by the durable ledger itself, and
    # the refusal must be one of the conditions that stops the whole run.
    with pytest.raises(LedgerStoreError) as refused:
        service.charged_call(TEST_PREFIX + "UNRESERVED", THETA, fake_forward,
                             start_index=0, kind="OPTIMIZER")
    assert _is_stop_condition(refused.value)
    assert dict(service.store.counts()) == {}


def test_replaying_a_reservation_with_a_changed_signature_refuses(service):
    task = TEST_PREFIX + "SIGNAT01"
    assert service.store.reserve(task, "signature-a", "BIAS_STRESS", 10, common.OWNER) \
        == "RUNNING"
    with pytest.raises(LedgerStoreError):
        service.store.reserve(task, "signature-b", "BIAS_STRESS", 10, common.OWNER)
    assert service.store.reserve(task, "signature-a", "BIAS_STRESS", 10, common.OWNER) \
        == "RUNNING"


def test_restarting_on_sealed_loader_evidence_refuses_reconstruction(tmp_path,
                                                                    no_real_model_construction):
    """The V166 defect: a sealed construction receipt plus a silent second build."""
    out = tmp_path / "service_out"
    out.mkdir(parents=True, exist_ok=True)
    store = service_mod.make_store(tmp_path / "ledger.sqlite")
    service = service_mod.PredictionService(store, out=out)
    sealed = {"schema": "iscat167.model_construction.1", "sealed": True,
              "loader_calls": 12, "model_id": common.MODEL_ID}
    common.atomic_json(service.log_path, sealed)
    with pytest.raises(service_mod.ReconstructionRefused):
        service.ensure_loader()
    assert service.model is None and service.constructions == 0
    assert service.real_calls == 0
    # The refusal must not have rewritten the sealed receipt.
    assert common.read_json(service.log_path) == sealed


def test_a_loader_call_count_alone_also_refuses_reconstruction(tmp_path,
                                                              no_real_model_construction):
    out = tmp_path / "service_out"
    out.mkdir(parents=True, exist_ok=True)
    service = service_mod.PredictionService(service_mod.make_store(tmp_path / "l.sqlite"),
                                            out=out)
    common.atomic_json(service.log_path, {"schema": "iscat167.model_construction.1",
                                          "sealed": False, "loader_calls": 3})
    with pytest.raises(service_mod.ReconstructionRefused):
        service.ensure_loader()


def test_dry_run_constructs_nothing_and_writes_no_receipt(tmp_path,
                                                          no_real_model_construction):
    out = tmp_path / "service_out"
    out.mkdir(parents=True, exist_ok=True)
    service = service_mod.PredictionService(service_mod.make_store(tmp_path / "l.sqlite"),
                                            out=out)
    report = service.ensure_loader(dry_run=True)
    assert report["constructed"] is False and report["model_calls"] == 0
    assert not service.log_path.exists()
    assert service.model is None and service.constructions == 0


def test_live_model_in_this_process_is_reused_not_rebuilt(service):
    report = service.ensure_loader()
    assert report == {"constructed": False, "reason": "ALREADY_LIVE_IN_THIS_PROCESS"}
    assert service.constructions == 0


def test_a_prediction_without_its_charge_binding_is_never_reusable(service, tmp_path):
    """A loose prediction file must not become a free model answer."""
    task = TEST_PREFIX + "LOOSE001"
    forged = tmp_path / "out2"
    forged.mkdir(parents=True, exist_ok=True)
    other = service_mod.PredictionService(service_mod.make_store(tmp_path / "l2.sqlite"),
                                          out=forged)
    c = fake_forward(THETA)
    c = np.ascontiguousarray(c, dtype=float)
    prediction = {"schema": "iscat167.prediction.1", "task": task, "seq": 1,
                  "ledger_seq": 1, "start_index": 0, "kind": "OPTIMIZER",
                  "charged": True, "requested_theta": THETA, "returned_theta": THETA,
                  "theta_sha256": common.theta_hex(THETA), "model_id": common.MODEL_ID,
                  "frames_sha256": None, "C": c.tolist(), "C_sha256": common.array_sha(c),
                  "forward_wall_ms": 1.0, "observation_metadata": {}}
    common.atomic_json(forged / "tasks" / task / "predictions" / "0001.json", prediction)
    with pytest.raises(ValueError) as refused:
        other.load_existing_predictions()
    assert _is_stop_condition(refused.value)
    assert other.cache == {}


def test_charged_predictions_reload_with_a_verifiable_binding(service):
    task = TEST_PREFIX + "RELOAD01"
    _reserve(service, task, 4)
    first = service.charged_call(task, THETA, fake_forward, start_index=0, kind="OPTIMIZER")
    second = service.charged_call(task, ALT, fake_forward, start_index=1, kind="OPTIMIZER")
    assert first["charged"] and second["charged"]
    assert service.store.counts()[task] == 2
    rebuild = service_mod.PredictionService(service.store, out=service.out)
    report = rebuild.load_existing_predictions()
    assert rebuild.cache
    assert report["prediction_documents_scanned"] == 2
    assert report["distinct_theta_cached"] == len(rebuild.cache)
    assert report["duplicate_documents"] == []
    assert rebuild.real_calls == 0 and rebuild.constructions == 0
    key = common.theta_hex(THETA)
    entry = rebuild.cache[key]
    assert entry["charged"] is True and entry["task_id"] == task
    assert entry["seq"] == first["seq"]
    assert np.array_equal(entry["C"], first["C"])
    # Reloaded answers still consume nothing.
    used_before = dict(service.store.counts())
    replay = rebuild.charged_call(task, THETA, fake_forward, start_index=0,
                                  kind="OPTIMIZER")
    assert replay["charged"] is False and replay["cache_hit"] is True
    assert dict(service.store.counts()) == used_before


def test_same_theta_with_different_c_is_refused_not_overwritten(service):
    task = TEST_PREFIX + "DUPC0001"
    _reserve(service, task, 3)
    first = service.charged_call(task, THETA, fake_forward, start_index=0, kind="OPTIMIZER")
    other = TEST_PREFIX + "DUPC0002"
    _reserve(service, other, 3)

    def rival(theta):
        return fake_forward(theta) * 1.25

    # allow_reuse=False is what a live-but-nondeterministic model would look like:
    # the same theta billed twice with answers that disagree.
    second = service.charged_call(other, THETA, rival, start_index=0, kind="OPTIMIZER",
                                  allow_reuse=False)
    assert second["charged"] is True
    assert second["C_sha256"] != first["C_sha256"]

    first_path = service.out / "tasks" / task / "predictions" / "0001.json"
    second_path = service.out / "tasks" / other / "predictions" / "0001.json"
    first_sha = common.sha_file(first_path)
    second_sha = common.sha_file(second_path)

    rebuild = service_mod.PredictionService(service.store, out=service.out)
    with pytest.raises(service_mod.FatalPersistenceError) as refused:
        rebuild.load_existing_predictions()
    assert "SAME_THETA_DIFFERENT_C" in str(refused.value)
    # The conflict is surfaced, never silently resolved by rewriting a durable answer.
    assert common.sha_file(first_path) == first_sha
    assert common.sha_file(second_path) == second_sha
    kept = rebuild.cache[common.theta_hex(THETA)]
    assert kept["C_sha256"] == first["C_sha256"]
    assert kept["prediction_sha256"] == first_sha


def test_truth_hash_never_enters_the_estimator_dependency_path():
    """Static: the four estimator modules never name the truth file or validator."""
    banned_modules = {"v167_validator", "v167_controller", "v167_service", "v167_runner",
                      "v167_plan", "run_all", "sqlite3"}
    for name in common.ESTIMATOR_CODE_FILES:
        source = (common.ROOT / "tools" / "v167" / name).read_text(encoding="utf-8")
        tree = __import__("ast").parse(source)
        imported = set()
        for node in __import__("ast").walk(tree):
            if isinstance(node, __import__("ast").Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, __import__("ast").ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        assert not (imported & banned_modules), (name, sorted(imported & banned_modules))
        assert "truth_file_sha256" not in source.split("FORBIDDEN")[0]
    # The single reading is flat: seven keys, no nested reference to any truth file.
    reading = {"reading_id": "V167_X", "group": "ANON_02", "B": 100000, "replicate": 0,
               "sigma_nm": 1.0, "z_nm": 431.0, "hypothetical": True}
    assert set(reading) == set(common.READING_KEYS)
    assert common.scan_forbidden(copy.deepcopy(reading), "unit") == []
    poisoned = dict(reading, truth_file_sha256="a" * 64)
    assert common.scan_forbidden(poisoned, "unit") == ["unit.truth_file_sha256"]
