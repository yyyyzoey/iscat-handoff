"""Contract 4.2/11.6: reporting and packing must work without a run context.

A round can be blocked by its own gates - uncommitted code, a missing frozen capsule,
a changed test suite - and the contract still demands an honest status report, failure
register and return package in that situation.  Those steps may not call prepare,
reserve or model construction again, so they rebuild their context by read-only means.
Every test here drives the real controller entry point against a throwaway results
tree with the F2c tripwire in place, and asserts three things at once: nothing was
prepared, nothing was billed, and the evidence that was produced says what is true.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest

import v168_common as common
import v168_controller as controller
import v168_service as service_mod

READ_ONLY_STEPS = controller.EVIDENCE_ONLY_STEPS
EVIDENCE_FILES = ("status.json", "manifest.json", "verification.json",
                  "controller_only/failure_records.json",
                  "controller_only/step_sequence.json")


@pytest.fixture()
def probe_tree():
    """A throwaway results tree inside ROOT, removed again on teardown.

    The controller spells evidence paths relative to ROOT, so a probe outside the
    repository would fail for the wrong reason.  No primary evidence name under
    results/v168 is ever written here.
    """
    parent = controller.ROOT / "results" / "v168" / "workstation_tests"
    parent.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="v168_ro_", dir=str(parent)))
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=False)


@pytest.fixture()
def read_only_tree(probe_tree, monkeypatch):
    """Point every writable controller path at the probe tree.

    The refusal tripwires live here too: prepare, staging, the writable ledger and the
    signature context are exactly what contract 11.6 forbids on this path, so a call
    into any of them fails the test instead of being noticed later.
    """
    monkeypatch.setattr(controller, "OUT", probe_tree)
    monkeypatch.setattr(controller, "CONTROL", probe_tree / "controller_only")
    monkeypatch.setattr(controller, "JAIL_ROOT", probe_tree / "estimator_inputs")
    monkeypatch.setattr(controller, "LEDGER_PATH", probe_tree / "logs" / "v168_budget.sqlite")

    def refuse(name):
        def _boom(*args, **kwargs):
            raise AssertionError("READ_ONLY_PATH_CALLED_" + name)
        return _boom

    monkeypatch.setattr(controller, "prepare", refuse("prepare"))
    monkeypatch.setattr(controller, "stage", refuse("stage"))
    monkeypatch.setattr(service_mod, "make_store", refuse("make_store"))
    monkeypatch.setattr(service_mod, "install_signature_context", refuse("install_signature_context"))
    return probe_tree


def _read(path: Path) -> dict:
    return json.loads(path.read_bytes().decode("utf-8"))


def _trace(probe: Path) -> dict:
    return _read(probe / "controller_only" / "step_sequence.json")


def _step(trace: dict, step: str) -> dict:
    return next(row for row in trace["steps"] if row["step"] == step)


def test_the_closing_step_set_named_by_the_packer_contains_no_prepare():
    """The delivered entry point must not re-prepare when it closes a round.

    ``run_all.py --pack`` spawns the controller for its closing evidence pass.  Before
    contract 11.6 that pass carried ``prepare``, so packing re-reserved budget and, with
    a changed tree, re-ran the identity gates that the pack is supposed to report on.
    """
    import run_all

    steps = tuple(run_all.CLOSE_STEPS.split(","))
    assert "prepare" not in steps, "CLOSING_PASS_STILL_PREPARES"
    assert "bind" not in steps and "run" not in steps and "final" not in steps
    assert steps == READ_ONLY_STEPS, (steps, READ_ONLY_STEPS)
    # The authorized round keeps every spending step, so this is not a weakening.
    assert run_all.RUN_STEPS.split(",")[0] == "prepare"
    assert set(READ_ONLY_STEPS).isdisjoint(
        {"bind", "run", "final", "estimates", "seal", "validate"})


def test_an_evidence_only_step_set_reads_the_plan_but_prepares_and_bills_nothing(
        read_only_tree):
    """``--readonly-report`` produces the report with zero reservation and zero model work."""
    probe = read_only_tree
    exit_code = controller.main(["--readonly-report"])

    assert exit_code == 0
    trace = _trace(probe)
    assert trace["requested_steps"] == list(READ_ONLY_STEPS)
    assert trace["read_only_control_path"] is True
    assert trace["read_context_reason"] == "cli_read_only_step_set"
    assert trace["failed_step"] is None
    assert trace["model_constructions_in_process"] == 0
    assert [row["step"] for row in trace["steps"]] == list(READ_ONLY_STEPS)
    assert all(row["status"] == "OK" for row in trace["steps"]), trace["steps"]
    assert not (probe / "logs" / "v168_budget.sqlite").exists(), (
        "THE_READ_ONLY_PATH_CREATED_A_WRITABLE_LEDGER")
    assert not (probe / "estimator_inputs").exists(), (
        "THE_READ_ONLY_PATH_STAGED_A_WORKER_JAIL")
    for rel in EVIDENCE_FILES:
        assert (probe / rel).is_file(), "MISSING_READONLY_EVIDENCE:" + rel
    status = _read(probe / "status.json")
    assert status["budget_used_total"] == 0
    assert status["reportable_D"] is None
    assert status["experimental_absolute_diameter_validated"] is False
    # Nothing has run in this tree, so no stage may claim otherwise.
    # No task signature was written here either, so P0 may not claim the evidence stage.
    assert status["stages"]["P0_evidence_protection"]["EXECUTION"] == "NOT_STARTED"
    assert status["stages"]["P0_evidence_protection"]["VERIFICATION"] == "NOT_STARTED"
    assert status["stages"]["P3_authorized_computation"]["EXECUTION"] == "NOT_STARTED"
    assert status["stages"]["P2_model_binding"]["EXECUTION"] == "NOT_STARTED"
    assert status["stages"]["P5_seal_and_score"]["EXECUTION"] == "NOT_STARTED"
    assert _read(probe / "controller_only" / "failure_records.json")["record_count"] == 23


def test_the_task_tables_refuse_to_invent_rows_without_a_staged_mapping(read_only_tree):
    """A read-only pass has no prescribed starts, so the tables say NOT_STARTED.

    ``r_merge_table`` and ``b_stress_table`` read the staged mapping for the group,
    sigma and replicate of each task.  Staging is forbidden here, so the honest answer
    is that the rows do not exist yet - never a borrowed or reconstructed row.
    """
    probe = read_only_tree
    assert controller.main(["--readonly-report"]) == 0
    summary = _step(_trace(probe), "tables")["summary"]
    assert summary["status"] == "NOT_STARTED"
    assert summary["reason"] == "READ_ONLY_SOURCE_MAPPING_ABSENT"
    assert summary["model_calls"] == 0
    assert not (probe / "controller_only" / "per_start_table.json").exists()


def test_the_read_only_pass_reuses_the_run_identity_already_recorded(read_only_tree):
    """A closing pass that named a fresh run_id would be evidence for no round at all.

    The packer refuses a closing trace whose run_id differs from the authorized round's,
    so the read-only context must read the recorded identity rather than mint one.
    """
    probe = read_only_tree
    control = probe / "controller_only"
    control.mkdir(parents=True, exist_ok=True)
    (control / "run_identity.json").write_bytes(common.canon(
        {"schema": "iscat168.run_identity.1", "run_id": "v168-PROBE-RECORDED",
         "code_identity_sha256": "not checked on the read-only path"}))
    assert controller.main(["--readonly-report"]) == 0
    trace = _trace(probe)
    assert trace["run_id"] == "v168-PROBE-RECORDED"
    assert _read(probe / "status.json")["run_id"] == "v168-PROBE-RECORDED"
    assert _read(probe / "verification.json")["run_id"] == "v168-PROBE-RECORDED"
    assert trace["read_only_control_path"] is True


def test_a_blocked_prepare_still_reaches_the_report_and_the_failure_register(
        read_only_tree, monkeypatch):
    """The round the contract most needs reported is the one that never got to run.

    ``prepare`` may refuse before staging, before the capsule or before any reservation.
    The spending steps have to be recorded as BLOCKED, and the evidence steps have to
    carry on with a read-only context so the return package can still be built.
    """
    probe = read_only_tree
    steps = "prepare,bind,run,tables,records,status,manifest,verification"

    def blocked(dry_run: bool = False) -> dict:
        raise ValueError("V168_CODE_NOT_COMMITTED_BEFORE_RUN:{'dirty_git_entries': ['M x']}")

    monkeypatch.setattr(controller, "prepare", blocked)
    exit_code = controller.main(["--steps", steps])

    assert exit_code == 1
    trace = _trace(probe)
    assert trace["failed_step"] == "prepare"
    assert trace["read_only_control_path"] is True
    assert trace["read_context_reason"].startswith("PREPARE_BLOCKED:ValueError")
    assert _step(trace, "prepare")["status"] == "FAILED"
    for name in ("bind", "run"):
        row = _step(trace, name)
        assert row["status"] == "BLOCKED" and row["blocked_by"] == "prepare"
    assert trace["blocked_steps"] == ["bind", "run"]
    assert trace["model_constructions_in_process"] == 0
    for rel in EVIDENCE_FILES:
        assert (probe / rel).is_file(), "BLOCKED_ROUND_LEFT_NO:" + rel
    assert not (probe / "logs" / "v168_budget.sqlite").exists()
    assert _read(probe / "status.json")["budget_used_total"] == 0


def test_a_step_set_that_spends_budget_still_has_to_prepare(read_only_tree):
    """The read-only exemption covers reporting steps only, never a spending step."""
    for steps in ("run", "bind,run", "status,run", "seal", "validate", "bind"):
        with pytest.raises(ValueError) as refused:
            controller.main(["--steps", steps])
        assert "STEP_SET_REQUIRES_PREPARE" in str(refused.value), steps
    with pytest.raises(ValueError, match="READONLY_REPORT_IS_NOT_A_DRY_RUN"):
        controller.main(["--readonly-report", "--dry-run"])
    assert not list(read_only_tree.rglob("status.json")), (
        "A_REFUSED_STEP_SET_STILL_WROTE_A_STATUS_REPORT")


def test_the_read_only_ledger_reads_the_same_tally_and_creates_nothing(tmp_path):
    """Parity with the frozen store's own query, plus a soft empty when there is no ledger.

    ``status_document`` charges the number it prints to ``store.counts()``, so the
    read-only stand-in has to be the same SELECT over the same table - not an estimate
    rebuilt from the attempt rows, and never a writer that could touch the real ledger.
    """
    store = service_mod.make_store(tmp_path / "ledger.sqlite")
    store.reserve("V168_PROBE_A", "sig-a", "BIAS_STRESS", 400, common.OWNER)
    store.reserve("V168_PROBE_B", "sig-b", "SEARCH_EXTENSION", 400, common.OWNER)
    assert store.counts() == {"V168_PROBE_A": 0, "V168_PROBE_B": 0}
    reader = controller.ReadOnlyLedger(tmp_path / "ledger.sqlite")
    assert reader.counts() == store.counts()
    store.charge("V168_PROBE_A", common.OWNER, [120.0, 420.0, 0.0, 0.0])
    assert reader.counts() == store.counts(), "READ_ONLY_COUNTS_DIVERGED_FROM_THE_STORE"
    assert int(reader.counts()["V168_PROBE_A"]) == 1

    missing = controller.ReadOnlyLedger(tmp_path / "absent" / "ledger.sqlite")
    assert missing.counts() == {}
    assert not (tmp_path / "absent").exists(), "READ_ONLY_LEDGER_CREATED_A_DIRECTORY"
    for writer in ("charge", "reserve", "execute", "set_task_budget", "commit"):
        assert not hasattr(reader, writer), "READ_ONLY_LEDGER_CAN_" + writer.upper()
