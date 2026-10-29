"""Contract 11.6: a failed round must still be reportable and packable as it really is.

The authorized V168 round stopped inside ``estimates``, so the seal and the independent score
never ran.  Two defects made that round undeliverable: the failure register counted only task
results, so a controller crash published ``record_count: 0`` beside a trace that said FAILED,
and the pack gate demanded every primary artefact of a round that was never allowed to write
them.  Both are tested here against the real entry points - ``controller.failure_records``,
``run_all._pack_gate`` and ``run_all._publish_failure_notice`` - in a throwaway results tree
inside ROOT, with zero model calls and zero reservations.  The failure gate is asserted to be
stricter rather than looser: a round that exited zero cannot be packed as a failure at all.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest

import v168_common as common
import v168_controller as controller

import run_all

ROOT = controller.ROOT
PROBE_RUN = "v168-PROBE-PACKROUND"
PROBE_TASK = "V168_PROBE_PACKTASK01"
# A round stopped inside ``estimates`` can only be missing what those two steps owed.
FAILED_ROUND_ABSENCES = ("seal", "estimates_merge_reuse")

ROUND_STEPS = [{"step": name, "status": "OK"} for name in
               ("prepare", "bind", "run", "tables", "final")] + [
    {"step": "estimates", "status": "FAILED", "error_type": "TypeError",
     "error": "Object of type ndarray is not JSON serializable",
     "traceback_tail": "Traceback ... line 2023 in estimates_documents"},
    {"step": "seal", "status": "BLOCKED", "blocked_by": "estimates",
     "reason": "an earlier step failed; no budget was spent here"},
    {"step": "validate", "status": "BLOCKED", "blocked_by": "estimates",
     "reason": "an earlier step failed; no budget was spent here"},
    {"step": "records", "status": "OK"}, {"step": "status", "status": "OK"}]


@pytest.fixture()
def probe_tree():
    """A throwaway results tree inside ROOT, removed again on teardown.

    The packer spells evidence paths relative to ROOT, so a probe outside the repository would
    fail for the wrong reason.  No primary evidence name is written here.
    """
    parent = ROOT / "results" / "v168" / "workstation_tests"
    parent.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="v168_pack_", dir=str(parent)))
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=False)


def _write(path: Path, document) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(common.canon(document))


# ------------------------------------------------------------------ failure register
def _register_ctx(out: Path, monkeypatch, run_id: str, entries: list[dict],
                  trace: list[dict] | None = None) -> dict:
    monkeypatch.setattr(controller, "OUT", out)
    monkeypatch.setattr(controller, "CONTROL", out / "controller_only")
    ctx = {"run_id": run_id, "git_head": "0" * 40,
           "codes": {"identity_sha256": "test" * 20},
           "plan": {"entries": entries}, "dry_run": False, "published": {}, "store": None}
    if trace is not None:
        ctx["step_trace"] = trace
    return ctx


def _step_rows(document: dict) -> list[dict]:
    return [row for row in document["records"]
            if str(row["record_type"]).startswith("CONTROLLER_STEP_")]


def test_a_controller_step_failure_is_registered_by_the_process_that_failed(
        probe_tree, monkeypatch):
    """The register may never read "nothing failed" while the live trace says otherwise.

    On the authorized round the register was written by the process that had just crashed in
    ``estimates``, and it counted only the 23 task rows: no failure record at all, beside a
    trace file naming the failed step.  The live trace is handed to the context before the
    evidence steps run, so this is exactly that path.
    """
    ctx = _register_ctx(probe_tree, monkeypatch, "v168-PROBE-LIVETRACE",
                        [{"task_id": PROBE_TASK, "kind": "BIAS_STRESS"}],
                        [dict(row) for row in ROUND_STEPS[5:9]])
    assert not (probe_tree / "controller_only" / "step_sequence.json").exists()

    document = controller.failure_records(ctx)

    rows = _step_rows(document)
    assert [(row["step"], row["record_type"]) for row in rows] == [
        ("estimates", "CONTROLLER_STEP_FAILED"),
        ("seal", "CONTROLLER_STEP_BLOCKED"),
        ("validate", "CONTROLLER_STEP_BLOCKED")]
    failed = rows[0]
    assert failed["error_type"] == "TypeError" and "ndarray" in failed["error"]
    assert failed["traceback_tail"]
    assert rows[1]["blocked_by"] == "estimates"
    # The task denominator is still in the same register: nothing was traded away.
    assert document["record_count"] == len(document["records"]) == 4
    assert sum(1 for row in document["records"]
               if row["record_type"] == "NOT_STARTED") == 1
    assert document["deleted_records"] == 0 and document["hidden_records"] == 0
    assert document["model_calls"] == 0 and document["reportable_D"] is None


def test_a_published_round_trace_contributes_its_failures_and_is_not_double_counted(
        probe_tree, monkeypatch):
    """The trace on disk and the replaying process describe one failure, recorded once."""
    control = probe_tree / "controller_only"
    _write(control / "step_sequence.json",
           {"schema": "iscat168.step_sequence.1", "run_id": PROBE_RUN, "dry_run": False,
            "exit_code": 1, "failed_step": "estimates",
            "blocked_steps": ["seal", "validate"],
            "requested_steps": list(run_all.RUN_STEPS.split(",")),
            "model_constructions_in_process": 1, "steps": ROUND_STEPS})
    ctx = _register_ctx(probe_tree, monkeypatch, PROBE_RUN, [],
                        [dict(row) for row in ROUND_STEPS])

    document = controller.failure_records(ctx)

    assert [(row["step"], row["record_type"]) for row in _step_rows(document)] == [
        ("estimates", "CONTROLLER_STEP_FAILED"),
        ("seal", "CONTROLLER_STEP_BLOCKED"),
        ("validate", "CONTROLLER_STEP_BLOCKED")]
    assert document["record_count"] == 3


def test_a_trace_from_another_run_does_not_put_its_failures_in_this_rounds_register(
        probe_tree, monkeypatch):
    _write(probe_tree / "controller_only" / "step_sequence.json",
           {"schema": "iscat168.step_sequence.1", "run_id": "v168-SOME-OTHER-ROUND",
            "exit_code": 1, "failed_step": "bind", "requested_steps": ["run"],
            "steps": [{"step": "bind", "status": "FAILED", "error_type": "ValueError",
                       "error": "MODEL_BINDING_REFUSED"}]})
    ctx = _register_ctx(probe_tree, monkeypatch, "v168-PROBE-OWN-RUN",
                        [{"task_id": PROBE_TASK, "kind": "BIAS_STRESS"}], [])

    document = controller.failure_records(ctx)

    assert _step_rows(document) == []
    assert document["record_count"] == 1


def test_the_register_is_published_even_when_it_holds_only_the_task_denominator(
        probe_tree, monkeypatch):
    """An honest empty register is still a deliverable, never an absent file."""
    ctx = _register_ctx(probe_tree, monkeypatch, "v168-PROBE-QUIET",
                        [{"task_id": PROBE_TASK, "kind": "BIAS_STRESS"}], [])

    document = controller.failure_records(ctx)

    published = probe_tree / "controller_only" / "failure_records.json"
    assert published.is_file()
    assert json.loads(published.read_bytes().decode("utf-8")) == document
    assert document["record_count"] == 1 and _step_rows(document) == []


def test_the_records_step_after_a_failed_step_names_that_step_in_the_real_main(
        probe_tree, monkeypatch):
    """The bug that hid the crash: records ran after estimates and still said zero.

    This drives the real ``controller.main`` with a step set in which the failing step comes
    before the register, and refuses the round's spending steps by monkeypatch so that no
    reservation, no construction and no ledger is possible on the way.
    """
    control = probe_tree / "controller_only"
    monkeypatch.setattr(controller, "OUT", probe_tree)
    monkeypatch.setattr(controller, "CONTROL", control)
    monkeypatch.setattr(controller, "JAIL_ROOT", probe_tree / "estimator_inputs")
    monkeypatch.setattr(controller, "LEDGER_PATH", probe_tree / "logs" / "v168_budget.sqlite")

    def read_only_ctx(**kwargs):
        base = {"run_id": "v168-PROBE-MAIN", "git_head": "0" * 40,
                "codes": {"identity_sha256": "probe" * 15 + "p"},
                "plan": {"entries": [{"task_id": PROBE_TASK, "kind": "BIAS_STRESS"}]},
                "document": {"total_cap": 9_999, "run_cap": 9_999},
                "dry_run": False, "published": {}, "store": None, "caps": {},
                "staged_by_task": {}, "refs": {"partials": {}, "zero_bias": {},
                                               "base_points": {}, "estimates": {}}}
        return dict(base, **kwargs)

    monkeypatch.setattr(controller, "read_context", lambda **k: read_only_ctx(**k))
    monkeypatch.setattr(controller, "prepare", lambda **k: read_only_ctx(**k))

    def crash(ctx: dict):
        raise TypeError("Object of type ndarray is not JSON serializable")

    monkeypatch.setattr(controller, "estimates_documents", crash)
    # records and status are the real functions: they must see the crash they follow.
    exit_code = controller.main(["--steps", "prepare,estimates,seal,records"])

    assert exit_code == 1
    trace = json.loads((control / "step_sequence.json")
                       .read_bytes().decode("utf-8-sig"))
    assert trace["failed_step"] == "estimates"
    assert trace["blocked_steps"] == ["seal"]
    register = json.loads((control / "failure_records.json")
                          .read_bytes().decode("utf-8-sig"))
    assert [(row["step"], row["record_type"]) for row in _step_rows(register)] == [
        ("estimates", "CONTROLLER_STEP_FAILED"), ("seal", "CONTROLLER_STEP_BLOCKED")]
    assert register["record_count"] == len(register["records"]) == 3
    assert not (probe_tree / "logs" / "v168_budget.sqlite").exists()
    assert not (probe_tree / "estimator_inputs").exists()


# ---------------------------------------------------------------------- the pack gate
def _pack_probe(probe_tree: Path, monkeypatch, *, exit_code: int = 1,
                failed_step: str | None = "estimates",
                steps: list[dict] | None = None, register_steps: list[str] | None = None,
                omit: tuple[str, ...] = (), close_as_round: bool = False) -> Path:
    """Build a whole failed-round tree, then point every packer path at it.

    The artefacts are real bytes written here, so a gate that accepts this tree has read a
    tree, not a mock.  ``close_as_round`` makes the newest trace a second spending round
    instead of the read-only closing pass, which contract 11.6 does not allow.
    """
    skip = set(omit) | (set(FAILED_ROUND_ABSENCES) if failed_step else set())
    out = probe_tree / "results" / "v168"
    control = out / "controller_only"
    prepared = probe_tree / "results" / "v168_prepared" / "controller_only"
    _write(control / "step_sequence.json",
           {"schema": "iscat168.step_sequence.1", "run_id": PROBE_RUN, "dry_run": False,
            "exit_code": exit_code, "failed_step": failed_step,
            "blocked_steps": ["seal", "validate"] if failed_step else [],
            "requested_steps": list(run_all.RUN_STEPS.split(",")),
            "model_constructions_in_process": 1,
            "steps": steps if steps is not None else ROUND_STEPS})
    _write(control / ("step_sequence_" + PROBE_RUN + ".json"),
           {"schema": "iscat168.step_sequence.1", "run_id": PROBE_RUN, "dry_run": False,
            "exit_code": 0, "failed_step": None, "blocked_steps": [],
            "read_only_control_path": not close_as_round,
            "requested_steps": list(run_all.RUN_STEPS.split(",") if close_as_round
                                    else run_all.CLOSE_STEPS.split(",")),
            "model_constructions_in_process": 0,
            "steps": [{"step": name, "status": "OK"} for name in
                      (run_all.RUN_STEPS.split(",") if close_as_round
                       else run_all.CLOSE_STEPS.split(","))]})
    _write(control / "frozen_execution_capsule.json",
           {"schema": "iscat168.frozen_execution_capsule.1", "capsule_sha256": "c" * 64,
            "test_suite_sha256": "t" * 64, "code_file_count": 50, "task_count": 23,
            "code_identity_sha256": "a" * 64, "git_head": "b" * 40, "reserved": False})
    _write(control / "preambles" / (PROBE_RUN + ".json"),
           {"schema": "iscat168.run_preamble.1", "run_id": PROBE_RUN,
            "WORKSTATION_TEST_RELEASE_VERIFIED": True, "execution_capsule_sha256": "c" * 64,
            "code_identity_sha256": "a" * 64, "git_head": "b" * 40,
            "workstation_test_release": {"receipt_sha256": "r" * 64,
                                         "code_identity_sha256": "a" * 64,
                                         "test_suite_sha256": "t" * 64,
                                         "git_head": "b" * 40}})
    records = [{"record_type": ("CONTROLLER_STEP_FAILED" if name == "estimates"
                                else "CONTROLLER_STEP_BLOCKED"),
                "step": name, "error": "Object of type ndarray is not JSON serializable"}
               for name in (register_steps if register_steps is not None
                            else ["estimates", "seal", "validate"])]
    _write(control / "failure_records.json",
           {"schema": "iscat168.failure_records.1", "run_id": PROBE_RUN, "records": records,
            "record_count": len(records), "deleted_records": 0, "hidden_records": 0})
    _write(prepared / "plan.json",
           {"schema": "iscat168.plan.1", "run_id": PROBE_RUN,
            "entries": [{"task_id": PROBE_TASK, "kind": "BIAS_STRESS"}]})
    artefacts = {"estimates_new": out / "estimates_new.json",
                 "estimates_merge_reuse": out / "estimates_merge_reuse.json",
                 "seal": out / "seal.json",
                 "ledger": out / "logs" / "v168_budget.sqlite",
                 "status": out / "status.json", "manifest": out / "manifest.json",
                 "verification": out / "verification.json",
                 "isolation_receipt": out / "estimator_inputs" / "00_isolation_receipt.json",
                 "execution_truth_report": out / "00_execution_truth_report.md",
                 "history_corrections": out / "history_corrections.md",
                 "return_readme": out / "README_V168_RETURN.md",
                 "controller_console_log": out / "logs" / "controller_run.log",
                 "failure_notice": out / "failure_package_notice.json",
                 "task_result": out / "tasks" / PROBE_TASK / "result.json"}
    for name, path in artefacts.items():
        if name in skip:
            continue
        if name == "task_result":
            _write(path, {"schema": "iscat168.task_result.1", "task_id": PROBE_TASK,
                          "execution_state": "FINISHED", "reportable_D": None})
        elif name == "ledger":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"probe ledger")
        elif path.suffix == ".md":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"# probe\n")
        elif path.suffix == ".log":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"STEP_FAILED estimates TypeError\n")
        else:
            _write(path, {"schema": "iscat168.probe.1", "run_id": PROBE_RUN,
                          "status": ("SEALED_BEFORE_VALIDATOR" if name == "seal" else "PROBE"),
                          "reportable_D": None})
    paths = {"OUT": out, "CONTROL": control, "JAIL": out / "estimator_inputs",
             "LOGS": out / "logs", "LEDGER": out / "logs" / "v168_budget.sqlite",
             "PLAN": prepared / "plan.json", "TASKS": out / "tasks"}
    for name, value in paths.items():
        monkeypatch.setattr(run_all, name, value)

    def fake_verify_history(*, capsule: dict, round_preamble: dict, run_id: str | None = None):
        fake_verify_history.calls.append(str(round_preamble["run_id"]))
        return {"schema": "iscat168.workstation_test_history_verify.1",
                "receipt_sha256": "r" * 64, "workflow_run_id": "full_003",
                "workflow_receipt_sha256": "w" * 64, "total_tests_recorded": 285,
                "suite_count": 3, "git_head": "b" * 40, "code_identity_sha256": "a" * 64,
                "test_suite_sha256": "t" * 64, "scenario_count": 4, "camera_image_count": 12,
                "verification_basis": "STORED_ROUND_EVIDENCE_PLUS_GIT_HISTORY",
                "authorizes_model_construction": False, "model_calls": 0}

    fake_verify_history.calls: list[str] = []
    monkeypatch.setattr(run_all.test_binding, "verify_history", fake_verify_history)
    monkeypatch.setattr(run_all.test_binding, "verify",
                        lambda *a, **k: pytest.fail("THE_PACKER_RE-RAN_THE_LIVE_SUITE"))
    return out


def test_the_failure_gate_accepts_a_round_that_really_failed_and_says_which_step(
        probe_tree, monkeypatch):
    _pack_probe(probe_tree, monkeypatch)

    checks = run_all._pack_gate(failure=True)

    assert checks["authorized_round_run_id"] == PROBE_RUN
    assert checks["authorized_round_exit_code"] == 1
    assert checks["authorized_round_failed_step"] == "estimates"
    assert checks["authorized_round_blocked_steps"] == ["seal", "validate"]
    assert checks["authorized_round_model_constructions"] == 1
    assert checks["latest_trace_exit_code"] == 0
    assert checks["release_verification_basis"] == "STORED_ROUND_EVIDENCE_PLUS_GIT_HISTORY"
    assert checks["seal_status"] == "ABSENT_SEAL_STEP_BLOCKED"
    assert checks["validator_outputs"] == []
    assert checks["accepted_absences"] == {"seal": "seal",
                                           "estimates_merge_reuse": "estimates"}
    assert checks["failure_record_count"] == 3
    assert checks["task_result_count"] == 1
    assert checks["required"]["seal"][1] is False
    assert checks["required"]["estimates_new"][1] is True
    assert checks["required"]["failure_notice"][1] is True
    assert checks["workstation_test_release"]["total_tests_recorded"] == 285
    # The round's own release evidence was authenticated from history; the live suite was
    # never re-collected, because the tree has been repaired since the round spent its budget.
    assert run_all.test_binding.verify_history.calls == [PROBE_RUN]


def test_the_failure_gate_refuses_a_round_that_exited_zero(probe_tree, monkeypatch):
    """A pass cannot be re-labelled a failure, and a failure cannot be packed as a pass."""
    _pack_probe(probe_tree, monkeypatch, exit_code=0, failed_step=None, register_steps=[],
                steps=[{"step": name, "status": "OK"} for name in
                       run_all.RUN_STEPS.split(",")])
    with pytest.raises(ValueError) as refused:
        run_all._pack_gate(failure=True)
    assert "AUTHORIZED_ROUND_EXITED_ZERO_USE_PACK:" + PROBE_RUN in str(refused.value)


def test_the_success_gate_refuses_the_same_failed_round(probe_tree, monkeypatch):
    _pack_probe(probe_tree, monkeypatch)
    with pytest.raises(ValueError) as refused:
        run_all._pack_gate()
    assert "AUTHORIZED_RUN_DID_NOT_EXIT_ZERO:1" in str(refused.value)


def test_the_failure_gate_refuses_a_second_spending_round(probe_tree, monkeypatch):
    """A second spending round cannot be quietly packed in place of the authorized round.

    Here the newest trace is itself a round: the failure gate refuses it because a round that
    exited zero is not a failure, and the gate that would package a pass refuses it because the
    read-only closing pass is missing.  Both refusals are asserted, so the wording of the
    refusal, not just the fact of one, is part of the contract.
    """
    _pack_probe(probe_tree, monkeypatch, close_as_round=True)
    with pytest.raises(ValueError) as refused:
        run_all._pack_gate(failure=True)
    assert "AUTHORIZED_ROUND_EXITED_ZERO_USE_PACK:" + PROBE_RUN in str(refused.value)


def test_the_pack_gate_refuses_a_round_never_closed_by_a_read_only_pass(
        probe_tree, monkeypatch):
    """Without the closing evidence pass the newest trace is the spending round itself.

    A round that really finished is packaged by ``--pack``, but only after the read-only
    evidence pass has run; if the newest trace still carries spending steps and
    ``read_only_control_path`` false, the archive would be published without the closing pass
    that produced its manifest, so the gate refuses rather than trusting the round.
    """
    _pack_probe(probe_tree, monkeypatch, exit_code=0, failed_step=None, register_steps=[],
                steps=[{"step": name, "status": "OK"} for name in
                       run_all.RUN_STEPS.split(",")])
    (run_all.CONTROL / ("step_sequence_" + PROBE_RUN + ".json")).unlink()

    with pytest.raises(ValueError) as refused:
        run_all._pack_gate()

    assert "CLOSING_PASS_IS_NOT_A_READONLY_REPORT:" + PROBE_RUN in str(refused.value)


def test_the_failure_gate_still_refuses_an_absence_no_failed_step_explains(
        probe_tree, monkeypatch):
    """``status`` succeeded, so a missing status report is not excusable evidence."""
    _pack_probe(probe_tree, monkeypatch, omit=("status",))
    with pytest.raises(ValueError) as refused:
        run_all._pack_gate(failure=True)
    assert "PACK_GATE_FAILURE_MISSING:status" in str(refused.value)



def test_the_failure_gate_refuses_a_table_whose_own_step_succeeded(probe_tree, monkeypatch):
    """Only the two artefacts the stopped steps owed are admitted, never a third."""
    _pack_probe(probe_tree, monkeypatch, omit=("estimates_new",))
    with pytest.raises(ValueError) as refused:
        run_all._pack_gate(failure=True)
    assert "PACK_GATE_FAILURE_MISSING:estimates_new" in str(refused.value)


def test_the_failure_gate_refuses_a_register_that_does_not_name_the_failed_step(
        probe_tree, monkeypatch):
    """The archive must carry the failure it describes, not merely a count of something."""
    _pack_probe(probe_tree, monkeypatch, register_steps=["seal", "validate"])
    with pytest.raises(ValueError) as refused:
        run_all._pack_gate(failure=True)
    assert "PACK_GATE_FAILED_STEP_NOT_IN_REGISTER:estimates" in str(refused.value)


def test_the_failure_gate_refuses_a_round_with_no_failed_step_at_all(probe_tree, monkeypatch):
    _pack_probe(probe_tree, monkeypatch, failed_step=None, register_steps=[])
    with pytest.raises(ValueError) as refused:
        run_all._pack_gate(failure=True)
    assert "PACK_GATE_TRACE_HAS_NO_FAILED_STEP" in str(refused.value)


def test_the_failure_gate_refuses_a_missing_failure_register(probe_tree, monkeypatch):
    """The register became a required deliverable on both pack paths."""
    out = _pack_probe(probe_tree, monkeypatch)
    (out / "controller_only" / "failure_records.json").unlink()
    with pytest.raises(ValueError) as refused:
        run_all._pack_gate(failure=True)
    assert "PACK_GATE_FAILURE_MISSING:failure_records" in str(refused.value)


def test_the_failure_gate_tolerates_no_empty_validator_output_unless_validate_stopped(
        probe_tree, monkeypatch):
    """An absent independent score is admissible only because the seal never happened."""
    steps = [dict(row) for row in ROUND_STEPS]
    steps[7] = {"step": "validate", "status": "OK"}
    _pack_probe(probe_tree, monkeypatch, steps=steps)
    with pytest.raises(ValueError) as refused:
        run_all._pack_gate(failure=True)
    assert "PACK_GATE_NO_VALIDATOR_OUTPUT" in str(refused.value)


# --------------------------------------------------------------- the failure notice
def test_the_failure_notice_is_deterministic_and_refuses_a_round_that_passed(
        probe_tree, monkeypatch):
    out = _pack_probe(probe_tree, monkeypatch, omit=("failure_notice",))

    notice = run_all._publish_failure_notice()
    path = out / "failure_package_notice.json"
    first = path.read_bytes()
    again = run_all._publish_failure_notice()

    assert path.read_bytes() == first, "THE_NOTICE_WAS_REWRITTEN_INSTEAD_OF_REPLAYED"
    assert notice["sha256"] == again["sha256"] == common.sha_bytes(first)
    assert notice["schema"] == "iscat168.failure_package_notice.1"
    assert notice["run_id"] == PROBE_RUN
    assert notice["this_archive_is_a_pass"] is False
    assert notice["failed_step"] == "estimates"
    assert notice["blocked_steps"] == ["seal", "validate"]
    assert notice["authorized_round_exit_code"] == 1
    assert notice["reportable_D"] is None
    assert notice["experimental_absolute_diameter_validated"] is False
    assert notice["model_calls"] == 0
    assert "ndarray" in notice["first_failure"]["error"]
    assert notice["first_failure"]["step"] == "estimates"
    absent = notice["deliverables_absent_because_of_that_failure"]
    assert absent["results/v168/seal.json"] == "seal step BLOCKED"
    assert absent["results/v168/estimates_merge_reuse.json"] == "estimates step FAILED"
    assert "NOT_STARTED" in absent["results/v168/validator_only/"]

    _pack_probe(probe_tree, monkeypatch, exit_code=0, failed_step=None, register_steps=[])
    with pytest.raises(ValueError) as refused:
        run_all._publish_failure_notice()
    assert "FAILURE_NOTICE_ROUND_EXITED_ZERO_USE_PACK" in str(refused.value)


def test_the_failure_mode_is_one_more_mode_and_not_a_second_step_set():
    """``--pack-failure`` is exclusive with the other modes and changes no controller step."""
    for conflicting in (["--pack-failure", "--pack"], ["--pack-failure", "--run"],
                        ["--pack-failure", "--pack-rehearsal"]):
        with pytest.raises(SystemExit):
            run_all.main(conflicting)
    assert run_all.CLOSE_STEPS == "tables,records,status,manifest,verification"
    assert run_all.FAILURE_ZIP_NAME != run_all.ZIP_NAME
    assert run_all.FAILURE_ZIP_NAME == "iscat_v168_failure_return_001.zip"
    steps = run_all.RUN_STEPS.split(",")
    for name in ("estimates", "seal", "validate"):
        assert name in steps, name
    for name in ("manifest", "verification"):
        assert name not in steps, name
    assert set(run_all.CLOSE_STEPS.split(",")).isdisjoint(
        {"bind", "run", "final", "estimates", "seal", "validate"})
