"""V167 P1 model-identity tests: the loader return rule and stranded charges.

The V167 bind step failed because the loader self-check runs on the legacy F2 field
library that the F2c composite wraps, while the service demanded the composite id on
every return.  These tests drive the real PredictionService and the real frozen
ledger against that defect from both sides: the estimator rule stays exactly as
strict as it was, the loader rule is checked against the value that is actually
correct for a loader forward, and a refused return can never strand a billed charge.
The model object is the conftest fake, so nothing here is evidence about physics.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

import v167_common as common
import v167_controller as controller
import v167_service as service_mod

from conftest import TEST_PREFIX, fake_forward

THETA = [120.0, 420.0, 0.0, 0.0]
FIELD_ID = "v131-field-" + ("ab" * 32)
OTHER_FIELD_ID = "v131-field-" + ("cd" * 32)


def _is_stop_condition(exc: BaseException) -> bool:
    """The controller's own rule for 'this failure must abort the authorized run'."""
    return any(marker in type(exc).__name__ or marker in str(exc)
               for marker in controller.STOP_MARKERS)


def _reserve(service, task_id, cap):
    return service.store.reserve(task_id, "test-signature-" + task_id, "BIAS_STRESS",
                                 cap, common.OWNER)


def _reserve_loader(service) -> str:
    """The production loader reservation: real signature, MODEL_BINDING, cap 100."""
    signature, state = service.reserve_loader()
    assert state == "RUNNING"
    return signature


def _attempts(service, task_id):
    with service.store.db() as conn:
        return conn.execute("SELECT seq,state,detail FROM attempts WHERE task=? "
                            "ORDER BY seq", (task_id,)).fetchall()


def _charge(service, task_id, theta, kind):
    """A durable charge with no return, i.e. exactly what a refusal can strand."""
    return service.store.charge(
        task_id, common.OWNER, theta,
        detail={"start_index": 0, "kind": kind, "invocation": "charged_model_forward",
                "theta_sha256": common.theta_hex(theta), "frames_sha256": None})


class FakeObservation:
    """The attribute shape tools/field_forward_reference.Observation exposes."""

    def __init__(self, theta, model_id):
        grid = np.add.outer(np.arange(17.0), np.arange(17.0))
        self.Ibg = grid
        self.I = grid
        self.C = grid - 8.0
        self.score_C = np.asarray(fake_forward(theta), dtype=float)
        self.theta = np.asarray(theta, dtype=float)
        self.model_id = model_id


class FakeComposite:
    """The F2c identity the loader receipt has to agree with."""

    def __init__(self, parent_model_id):
        self.model_id = common.MODEL_ID
        self.identity = {"parent_model_id": parent_model_id}


# --------------------------------------------------------------------- the rule

def test_the_estimator_rule_still_demands_the_f2c_id():
    """No loosening: every non-loader kind keeps the original MODEL_ID demand."""
    service_mod.check_returned_model_id("OPTIMIZER", common.MODEL_ID)
    service_mod.check_returned_model_id("SOURCE_BINDING", None)
    for kind in ("OPTIMIZER", "SOURCE_BINDING", "FINAL_VERIFY", "COUNTED_PREDICTOR"):
        with pytest.raises(ValueError) as refused:
            service_mod.check_returned_model_id(kind, FIELD_ID)
        assert str(refused.value) == "MODEL_ID_MISMATCH_IN_RETURN"


def test_the_loader_rule_demands_a_wellformed_field_library_id():
    service_mod.check_returned_model_id(service_mod.LOADER_KIND, FIELD_ID)
    for bad in (common.MODEL_ID, None, "", "v131-field-notahex",
                FIELD_ID + "0", FIELD_ID.upper()):
        with pytest.raises(ValueError) as refused:
            service_mod.check_returned_model_id(service_mod.LOADER_KIND, bad)
        assert str(refused.value).startswith("LOADER_FORWARD_MODEL_ID_NOT_FIELD_LIBRARY")


def test_the_loader_field_id_must_be_the_live_f2c_parent():
    assert service_mod.resolve_loader_field_parent(FakeComposite(FIELD_ID),
                                                   {FIELD_ID}) == (FIELD_ID, FIELD_ID)
    with pytest.raises(ValueError) as counted:
        service_mod.resolve_loader_field_parent(
            FakeComposite(FIELD_ID), {FIELD_ID, OTHER_FIELD_ID})
    assert str(counted.value).startswith("LOADER_FIELD_ID_DISTINCT_COUNT")
    with pytest.raises(ValueError) as mismatched:
        service_mod.resolve_loader_field_parent(
            FakeComposite(OTHER_FIELD_ID), {FIELD_ID})
    assert str(mismatched.value).startswith("LOADER_FIELD_ID_NOT_F2C_PARENT")
    with pytest.raises(ValueError) as anonymous:
        service_mod.resolve_loader_field_parent(object(), {FIELD_ID})
    assert str(anonymous.value) == "F2C_IDENTITY_NOT_A_MAPPING"
    with pytest.raises(ValueError) as empty:
        service_mod.resolve_loader_field_parent(FakeComposite(FIELD_ID), set())
    assert str(empty.value).startswith("LOADER_FIELD_ID_DISTINCT_COUNT")


# ------------------------------------------------------- charged returns, refused

def test_an_estimator_return_carrying_a_field_id_is_refused_and_billed(service):
    """The refusal must settle its own charge instead of stranding it as CHARGED."""
    task = TEST_PREFIX + "IDENY001"
    _reserve(service, task, 4)
    with pytest.raises(ValueError) as refused:
        service.charged_call(task, THETA, lambda t: FakeObservation(t, FIELD_ID),
                             start_index=0, kind="OPTIMIZER")
    assert str(refused.value) == "MODEL_ID_MISMATCH_IN_RETURN"
    rows = _attempts(service, task)
    assert [row[1] for row in rows] == ["MODEL_ERROR"]
    detail = json.loads(rows[0][2])
    assert detail["refusal_stage"] == "POST_RETURN_VALIDATION"
    assert detail["returned_theta"] is None
    assert detail["kind"] == "OPTIMIZER" and detail["ledger_seq"] == rows[0][0]
    # The charge itself is preserved untouched, and it is not refunded.
    assert detail["requested_theta"] == THETA
    assert detail["theta_sha256"] == common.theta_hex(THETA)
    assert service.store.counts()[task] == 1
    # A refused return never becomes a durable answer or a reusable cache entry.
    assert not (service.out / "tasks" / task).exists()
    assert service.cache == {}
    assert service.real_calls == 0
    # The task is still sealable afterwards, so the round can report it honestly.
    result = service.out / "tasks" / task / "task_result.json"
    common.atomic_json(result, {"signature": "test-signature-" + task, "task_id": task})
    service.store.seal(task, common.OWNER, "FAILED", str(result))
    with service.store.db() as conn:
        assert conn.execute("SELECT state FROM tasks WHERE id=?",
                            (task,)).fetchone()[0] == "FAILED"


def test_a_loader_return_carrying_the_field_id_is_written_and_recalled(service):
    _reserve_loader(service)
    info = service.charged_call(common.LOADER_TASK, THETA,
                                lambda t: FakeObservation(t, FIELD_ID),
                                start_index=0, kind=service_mod.LOADER_KIND,
                                allow_reuse=False)
    assert info["charged"] is True and info["seq"] == 1
    document = common.read_json(service.out / info["prediction_path"])
    assert document["model_id"] == FIELD_ID
    assert document["kind"] == service_mod.LOADER_KIND
    assert document["charged"] is True and document["C_sha256"] == info["C_sha256"]
    assert service.loader_field_model_ids == {FIELD_ID}
    assert [row[1] for row in _attempts(service, common.LOADER_TASK)] == ["RETURNED"]


def test_a_loader_return_cannot_carry_the_f2c_id_or_a_malformed_field_id(service):
    """The loader rule is a real check in both directions, not an any-catch."""
    _reserve_loader(service)
    for bad in ("v131-field-notahex", common.MODEL_ID, "", FIELD_ID + "0"):
        with pytest.raises(ValueError) as refused:
            service.charged_call(common.LOADER_TASK, THETA,
                                 lambda t, value=bad: FakeObservation(t, value),
                                 start_index=0, kind=service_mod.LOADER_KIND,
                                 allow_reuse=False)
        assert str(refused.value).startswith("LOADER_FORWARD_MODEL_ID_NOT_FIELD_LIBRARY")
    # A bare array return has no model id at all, which a loader must not accept.
    with pytest.raises(ValueError) as anonymous:
        service.charged_call(common.LOADER_TASK, THETA, fake_forward, start_index=0,
                             kind=service_mod.LOADER_KIND, allow_reuse=False)
    assert "None" in str(anonymous.value)
    states = [row[1] for row in _attempts(service, common.LOADER_TASK)]
    assert states == ["MODEL_ERROR"] * 5
    assert service.store.counts()[common.LOADER_TASK] == 5
    assert service.loader_field_model_ids == set()
    assert not (service.out / "tasks" / common.LOADER_TASK).exists()


def test_a_loader_answer_never_serves_an_estimator_reuse_request(service):
    """A field-library C is not an F2c C: it must not become a free estimator call."""
    _reserve_loader(service)
    loader = service.charged_call(common.LOADER_TASK, THETA,
                                lambda t: FakeObservation(t, FIELD_ID),
                                start_index=0, kind=service_mod.LOADER_KIND,
                                allow_reuse=False)
    assert loader["charged"] is True
    task = TEST_PREFIX + "IDERE001"
    _reserve(service, task, 3)
    estimator = service.charged_call(task, THETA,
                                     lambda t: FakeObservation(t, common.MODEL_ID),
                                     start_index=0, kind="OPTIMIZER")
    assert estimator["charged"] is True
    assert estimator.get("cache_hit") is not True
    assert service.cache_hits == 0
    assert service.store.counts()[common.LOADER_TASK] == 1
    assert service.store.counts()[task] == 1
    # And the reverse: an F2c answer is cached, but only under the composite id.
    entry = service.cache[common.theta_hex(THETA)]
    assert entry["model_id"] == common.MODEL_ID and entry["task_id"] == task


# ---------------------------------------------------------------- orphan recovery

def test_reconcile_closes_a_stranded_loader_charge_without_refunding(service):
    signature = _reserve_loader(service)
    seq = _charge(service, common.LOADER_TASK, THETA, service_mod.LOADER_KIND)
    used_before = dict(service.store.counts())

    report = service.reconcile_loader_orphans()

    assert report["settled_count"] == 1 and report["refunded_calls"] == 0
    assert report["settled_sequences"] == [seq]
    rows = _attempts(service, common.LOADER_TASK)
    assert rows[0][1] == "MODEL_ERROR"
    detail = json.loads(rows[0][2])
    assert detail["requested_theta"] == THETA
    assert detail["kind"] == service_mod.LOADER_KIND
    assert detail["reconciliation_state"] == "MODEL_ERROR"
    assert detail["reconciliation_note"] == "loader_attempt_orphaned_by_a_refused_return"
    assert dict(service.store.counts()) == used_before

    lines = [json.loads(line) for line in
             (service.out / "logs" / "loader_orphan_recovery.jsonl")
             .read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 1 and service.orphan_recovery == lines
    line = lines[0]
    assert line["task_id"] == common.LOADER_TASK and line["ledger_seq"] == seq
    assert line["state_before"] == "CHARGED" and line["state_after"] == "MODEL_ERROR"
    assert line["refunded_calls"] == 0
    assert line["theta_sha256"] == common.theta_hex(THETA)
    assert len(line["charge_detail_sha256"]) == 64
    assert line["refusal_reason_in_ledger"] is False

    # The stranded charge was the only thing keeping the loader task unsealable.
    receipt = {"schema": "iscat167.model_construction.1", "signature": signature,
               "sealed": False, "loader_calls": 1, "model_id": common.MODEL_ID}
    common.atomic_json(service.log_path, receipt)
    assert service.seal_loader()["sealed"] is True
    # A second pass on clean evidence settles nothing and appends nothing.
    again = service.reconcile_loader_orphans()
    assert again["settled_count"] == 0 and again["refunded_calls"] == 0
    assert len((service.out / "logs" / "loader_orphan_recovery.jsonl")
               .read_text(encoding="utf-8").splitlines()) == 1


def test_reconcile_refuses_a_stranded_charge_outside_the_loader(service):
    """An unknown crash is not the loader's to absorb; it stops the round."""
    _reserve_loader(service)
    task = TEST_PREFIX + "IDORF001"
    _reserve(service, task, 3)
    _charge(service, task, THETA, "OPTIMIZER")
    with pytest.raises(ValueError) as refused:
        service.reconcile_loader_orphans()
    assert str(refused.value).startswith("CHARGED_ORPHAN_OUTSIDE_LOADER")
    assert _is_stop_condition(refused.value)
    assert [row[1] for row in _attempts(service, task)] == ["CHARGED"]
    assert service.orphan_recovery == []
    assert not (service.out / "logs" / "loader_orphan_recovery.jsonl").exists()


def test_reconcile_refuses_a_loader_row_that_was_not_a_loader_forward(service):
    _reserve_loader(service)
    seq = _charge(service, common.LOADER_TASK, THETA, "OPTIMIZER")
    with pytest.raises(ValueError) as refused:
        service.reconcile_loader_orphans()
    assert str(refused.value).startswith("LOADER_ORPHAN_SCOPE_EXCEEDED")
    assert str(seq) in str(refused.value)
    assert [row[1] for row in _attempts(service, common.LOADER_TASK)] == ["CHARGED"]


def test_reconcile_does_not_disturb_returned_attempts_or_dry_run(service):
    _reserve_loader(service)
    service.charged_call(common.LOADER_TASK, THETA,
                         lambda t: FakeObservation(t, FIELD_ID),
                         start_index=0, kind=service_mod.LOADER_KIND, allow_reuse=False)
    counts_before = dict(service.store.counts())
    assert service.reconcile_loader_orphans()["settled_count"] == 0
    assert dict(service.store.counts()) == counts_before
    assert [row[1] for row in _attempts(service, common.LOADER_TASK)] == ["RETURNED"]
    # A dry run must not reach the ledger at all, orphaned or not.
    _charge(service, common.LOADER_TASK, [130.0, 430.0, 0.0, 0.0],
            service_mod.LOADER_KIND)
    live = service_mod.PredictionService(service.store, out=service.out)
    report = live.ensure_loader(dry_run=True)
    assert report["constructed"] is False and live.orphan_recovery == []
    assert [row[1] for row in _attempts(service, common.LOADER_TASK)] == ["RETURNED",
                                                                          "CHARGED"]
