"""V168 differential tests for contract section 4.2: the frozen execution capsule.

The capsule gate has been enforced since the first freeze attempt: ``prepare`` refuses
to reserve unless a digest already sits at the pin path.  What was missing is the writer,
and a writer that stands in front of every billed call has to be tested for refusal as
carefully as for success.  These tests fix four things:

* the pin is written once, at ``CAPSULE_PATH``, and holds the digest the delivered guard
  recomputes for the same tree, so the authorized run accepts it instead of inventing it;
* committed code and a verifying workstation test release are preconditions, and each
  refusal leaves no capsule behind, so a round cannot freeze first and earn its evidence
  afterwards;
* freezing is not a run: no signature context, no reservation, no ledger, no model;
* the flags refuse to be mixed, and the real production entry exposes the step, because
  a freeze reachable only by hand-running the controller is a freeze that gets skipped.

The F2c model stays behind the session tripwire in every test here, and the workflow
release receipt is simulated: this file proves the rules around the pin, not that the
workstation suite actually ran.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

import v168_common as common
import v168_controller as controller
import v168_service as service_mod
import v168_test_binding as test_binding

GUARD = service_mod.GUARD
PIN_NAME = "frozen_execution_capsule.json"
RELEASE_KEYS = ("receipt_sha256", "workflow_run_id", "workflow_receipt_sha256",
                "total_tests_recorded", "suite_count", "code_identity_sha256",
                "test_suite_sha256", "scenario_count", "camera_image_count")


@pytest.fixture()
def probe_control():
    """A throwaway control directory *inside* ROOT, removed on teardown.

    The capsule is a real evidence file, and every controller path is spelled relative to
    ROOT, so the pin under test has to live inside the repository and must never be the
    deliverable name at ``results/v168/controller_only/``.
    """
    parent = controller.ROOT / "results" / "v168" / "workstation_tests"
    parent.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="v168_freeze_", dir=str(parent)))
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=False)


def _committed(head: str) -> dict:
    return {"schema": "iscat168.code_git_state.1", "git_head": head,
            "tracked_v168_files": 40, "required_controller_files": [],
            "missing_from_git": [], "untracked_python_under_tools_v168": [],
            "dirty_git_entries": [], "estimator_code_tracked": True,
            "estimator_code_clean": True, "bundle_tracked": True}


def _release(capsule: dict, codes: dict, head: str) -> dict:
    """A verify() shaped result agreeing with the capsule being frozen."""
    return {"schema": "iscat168.workstation_test_verify.1",
            "receipt_sha256": "a" * 64, "workflow_run_id": "probe_001",
            "workflow_receipt_sha256": "b" * 64, "total_tests_recorded": 177,
            "suite_count": 3, "scenario_count": 4, "camera_image_count": 12,
            "WORKSTATION_TESTS_PASS": True,
            "code_identity_sha256": codes["identity_sha256"],
            "test_suite_sha256": capsule["test_suite_sha256"],
            "git_head": head}


def _prepared(ctx: dict) -> dict:
    """The rehearsal context ``freeze_capsule`` reads its capsule and identity from."""
    return {"run_id": ctx["run_id"], "git_head": ctx["git_head"], "dry_run": True,
            "codes": ctx["codes"], "capsule": ctx["capsule"],
            "capsule_sha256": ctx["capsule_sha256"], "plan": ctx["plan"],
            "staging": ctx["staging"]}


def _wire(monkeypatch, control: Path, ctx: dict, *, release: dict | None = None,
          state: dict | None = None, prepared: dict | None = None,
          verify_error: str | None = None) -> tuple[Path, dict]:
    """Point the freeze at the probe directory and stub its two outside calls.

    ``seen`` records which stubs ran: several refusals below have to prove they stopped
    *before* the rehearsal, not merely that they raised.
    """
    pin = control / PIN_NAME
    seen: dict[str, object] = {}

    def prepare(*, dry_run: bool = False) -> dict:
        seen["dry_run"] = dry_run
        return prepared if prepared is not None else _prepared(ctx)

    def verify(*args, **kwargs) -> dict:
        seen["verified"] = True
        if verify_error is not None:
            raise ValueError(verify_error)
        return release if release is not None else _release(
            ctx["capsule"], ctx["codes"], ctx["git_head"])

    monkeypatch.setattr(controller, "CAPSULE_PATH", pin)
    monkeypatch.setattr(controller, "code_git_state",
                        lambda: state if state is not None
                        else _committed(ctx["git_head"]))
    monkeypatch.setattr(controller, "prepare", prepare)
    monkeypatch.setattr(test_binding, "verify", verify)
    return pin, seen


def test_the_freeze_writes_the_pin_from_the_rehearsal_digest(staged, probe_control,
                                                            monkeypatch):
    """Section 4.2: the capsule is the guard's own digest, recorded before any run_id."""
    pin, seen = _wire(monkeypatch, probe_control, staged)

    document = controller.freeze_capsule()

    assert seen == {"verified": True, "dry_run": True}, \
        "the freeze must verify the release, then rehearse, and do neither twice"
    assert pin.is_file(), "the freeze must write the pin it is named for"
    assert common.canon(controller.read_json(pin)) == common.canon(document), \
        "the written bytes are the returned document"
    assert document["capsule_sha256"] == staged["capsule_sha256"]
    assert document["capsule_sha256"] == controller.execution_capsule(
        staged)["capsule_sha256"], "the capsule is not reproducible from the staged tree"
    assert document["test_suite_sha256"] == controller.test_suite_sha256()
    assert document["schema"] == "iscat168.execution_capsule.1"
    assert document["pin_schema"] == "iscat168.frozen_execution_capsule.1"
    assert document["task_count"] == len(staged["plan"]["entries"]) == 23
    assert document["executed_file_count"] == len(document["executed_files"])
    # A freeze is a precondition of a run, never a run of its own.
    assert document["model_calls"] == 0
    assert document["reserved"] is False
    assert document["freeze_stage"] == "PRE_RESERVATION_PRE_RUN_IDENTITY_CONSUMPTION"
    assert document["workstation_test_release"] == {
        key: _release(staged["capsule"], staged["codes"], staged["git_head"])[key]
        for key in RELEASE_KEYS}
    assert document["git_head"] == staged["git_head"]
    assert document["code_identity_sha256"] == staged["codes"]["identity_sha256"]


def test_the_pin_is_the_digest_the_reserve_gate_accepts(staged, probe_control, monkeypatch):
    """The point of the file: the run compares against it through the delivered guard."""
    pin, _seen = _wire(monkeypatch, probe_control, staged)
    document = controller.freeze_capsule()

    pinned = controller.read_json(pin)
    current = controller.execution_capsule(staged)["capsule_sha256"]
    GUARD.require_frozen_capsule(str(pinned["capsule_sha256"]), current)
    assert pinned["capsule_sha256"] == document["capsule_sha256"] == current
    assert pinned["test_suite_sha256"] == controller.test_suite_sha256()

    # The same guard refuses a digest moved by a source edit, so the pin is a real gate.
    with pytest.raises(ValueError) as refused:
        GUARD.require_frozen_capsule(str(pinned["capsule_sha256"]), "0" * 64)
    assert "CODE_OR_INPUT_CHANGED_BEFORE_RESERVE_NO_MODEL_AUTHORITY" in str(refused.value)


def test_a_second_freeze_is_refused_and_the_first_pin_survives(staged, probe_control,
                                                              monkeypatch):
    """Re-freezing would silently re-point a reservation, so the pin is write-once."""
    pin, _seen = _wire(monkeypatch, probe_control, staged)
    controller.freeze_capsule()
    frozen = pin.read_bytes()

    with pytest.raises(ValueError) as refused:
        controller.freeze_capsule()
    assert "FROZEN_EXECUTION_CAPSULE_ALREADY_FROZEN" in str(refused.value)
    assert str(pin) in str(refused.value), "the refusal has to name the pin it protects"
    assert pin.read_bytes() == frozen, "a refused freeze rewrote the frozen bytes"


def test_freeze_refuses_uncommitted_code_and_writes_no_pin(staged, probe_control,
                                                          monkeypatch):
    """Section 4.2 puts the commit before the freeze; dirty bytes cannot be frozen."""
    dirty = _committed(staged["git_head"])
    dirty["estimator_code_tracked"] = False
    dirty["missing_from_git"] = ["tools/v168/v168_controller.py"]
    pin, seen = _wire(monkeypatch, probe_control, staged, state=dirty)

    with pytest.raises(ValueError) as refused:
        controller.freeze_capsule()
    assert "V168_CODE_NOT_COMMITTED_BEFORE_FREEZE" in str(refused.value)
    assert "v168_controller.py" in str(refused.value), \
        "the refusal has to say what is missing from Git"
    assert not pin.exists(), "uncommitted code was frozen anyway"
    assert seen == {}, "the freeze went on to verify the release and rehearse anyway"


@pytest.mark.parametrize("failure", [
    "WORKSTATION_RELEASE_RECEIPT_COUNT:",
    "WORKSTATION_TEST_RELEASE_RECEIPT_MISSING:C:/x/release.json",
    "RELEASE_RECEIPT_SELF_DIGEST",
    "CODE_CHANGED_AFTER_TESTS:aaa!=bbb",
    "FROZEN_TEST_SUITE_CHANGED_BEFORE_RESERVE",
    "WORKFLOW_RECEIPT_SHA_CHANGED",
    "PRODUCTION_RECOLLECTION_NOT_RECORDED",
])
def test_a_round_without_a_verifying_workstation_release_cannot_freeze(
        staged, probe_control, monkeypatch, failure):
    """The receipt is frozen with the capsule, so it has to verify first or not at all."""
    pin, seen = _wire(monkeypatch, probe_control, staged, verify_error=failure)

    with pytest.raises(ValueError) as refused:
        controller.freeze_capsule()
    assert failure.split(":")[0] in str(refused.value)
    assert not pin.exists(), "a capsule was frozen on a receipt that does not verify"
    assert seen == {"verified": True}, \
        "the rehearsal ran before the receipt stopped the freeze"


@pytest.mark.parametrize("key,bad,expected", [
    ("test_suite_sha256", "f" * 64, "FREEZE_TEST_SUITE_SHA_MISMATCH"),
    ("code_identity_sha256", "e" * 64, "FREEZE_CODE_IDENTITY_SHA_MISMATCH"),
    ("git_head", "0" * 40, "FREEZE_GIT_HEAD_MISMATCH"),
])
def test_a_receipt_from_another_build_or_another_suite_blocks_the_freeze(
        staged, probe_control, monkeypatch, key, bad, expected):
    """Every identity the receipt carries is re-checked against the tree, not trusted."""
    release = _release(staged["capsule"], staged["codes"], staged["git_head"])
    release[key] = bad
    pin, _seen = _wire(monkeypatch, probe_control, staged, release=release)

    with pytest.raises(ValueError) as refused:
        controller.freeze_capsule()
    assert expected in str(refused.value)
    assert not pin.exists()


def test_a_staged_task_set_that_is_not_the_authorized_23_blocks_the_freeze(
        staged, probe_control, monkeypatch):
    """The capsule binds one payload digest per task, so a short set is not this round."""
    prepared = _prepared(staged)
    prepared["plan"] = {"entries": prepared["plan"]["entries"][:22]}
    pin, _seen = _wire(monkeypatch, probe_control, staged, prepared=prepared)

    with pytest.raises(ValueError) as refused:
        controller.freeze_capsule()
    assert "FREEZE_TASK_COUNT_NOT_23" in str(refused.value)
    assert not pin.exists()


def test_the_freeze_spends_nothing_and_builds_no_model(staged, probe_control, monkeypatch):
    """No signature context, no reservation, and no new bytes outside the pin.

    The deliverable paths are compared as they are, present or absent: a freeze may not
    change them either way, which stays true after the authorized round has run.
    """
    pin, _seen = _wire(monkeypatch, probe_control, staged)
    watched = [Path(controller.LEDGER_PATH), controller.CONTROL / "run_identity.json",
               controller.CONTROL / "task_signatures.json"]
    before = {(str(path), path.is_file(),
               common.sha_file(path) if path.is_file() else None) for path in watched}
    signed_before = service_mod.signature_context()

    document = controller.freeze_capsule()

    after = {(str(path), path.is_file(),
              common.sha_file(path) if path.is_file() else None) for path in watched}
    assert document["model_calls"] == 0
    assert after == before, "the freeze touched a deliverable evidence path"
    assert service_mod.signature_context() == signed_before, \
        "a freeze installed a signature context, which only a prepared run may do"
    assert sorted(item.name for item in probe_control.iterdir()) == [PIN_NAME], \
        "the freeze wrote evidence beyond the capsule pin"


@pytest.mark.parametrize("argv,expected", [
    (["--freeze-capsule", "--dry-run"], "FREEZE_CAPSULE_IS_NOT_A_DRY_RUN"),
    (["--freeze-capsule", "--readonly-report"], "FREEZE_CAPSULE_IS_NOT_A_READONLY_REPORT"),
    (["--freeze-capsule", "--steps", "run"], "FREEZE_CAPSULE_RUNS_NO_STEPS"),
])
def test_the_freeze_flag_refuses_to_be_mixed_with_a_run(monkeypatch, argv, expected):
    """Freezing is one act; combined flags would let a run pretend it had frozen."""

    def never(*args, **kwargs) -> dict:
        raise AssertionError("a refused flag set still reached freeze_capsule")

    monkeypatch.setattr(controller, "freeze_capsule", never)
    with pytest.raises(ValueError) as refused:
        controller.main(argv)
    assert expected in str(refused.value)


def test_the_controller_flag_dispatches_one_freeze_and_spends_no_steps(monkeypatch, capsys):
    """The success path prints the pin and returns without entering the step loop."""
    document = {"capsule_sha256": "c" * 64, "test_suite_sha256": "d" * 64,
                "code_identity_sha256": "e" * 64, "git_head": "0" * 40,
                "task_count": 23, "executed_file_count": 18, "model_calls": 0,
                "workstation_test_release": {"receipt_sha256": "a" * 64}}
    calls: list[int] = []

    def refuse_prepare(**kwargs) -> dict:
        raise AssertionError("the freeze ran a step")

    monkeypatch.setattr(controller, "freeze_capsule", lambda: calls.append(1) or dict(document))
    monkeypatch.setattr(controller, "prepare", refuse_prepare)

    assert controller.main(["--freeze-capsule"]) == 0
    assert len(calls) == 1
    printed = capsys.readouterr().out
    assert "FROZEN_EXECUTION_CAPSULE" in printed
    assert document["capsule_sha256"] in printed
    assert "STEP_OK" not in printed, "a freeze is not a step run"


def test_the_production_entry_exposes_the_freeze_step(monkeypatch):
    """Section 10.4: the real workstation entry performs the freeze, not a hand-run."""
    import run_all

    seen: list[list[str]] = []
    monkeypatch.setattr(run_all.ctrl, "code_git_state", lambda: _committed("0" * 40))
    monkeypatch.setattr(run_all, "_spawn",
                        lambda argv, log_path: seen.append(list(argv)) or 0)

    assert run_all.main(["--freeze-capsule"]) == 0
    assert len(seen) == 1, "the entry must reach the controller exactly once"
    assert "--freeze-capsule" in seen[0]
    assert "--dry-run" not in seen[0]
    assert "--steps" not in seen[0], "a freeze may not also run a step set"
    assert "v168_controller.py" in " ".join(seen[0])
    # The mode is one of the mutually exclusive set, so it cannot ride along with --run.
    with pytest.raises(SystemExit):
        run_all.main(["--freeze-capsule", "--run"])


def test_the_production_entry_refuses_to_freeze_uncommitted_code(monkeypatch):
    """The entry stops before spawning a child, so an operator sees the reason directly."""
    import run_all

    dirty = _committed("0" * 40)
    dirty["estimator_code_clean"] = False
    dirty["dirty_git_entries"] = [" M tools/v168/v168_service.py"]
    monkeypatch.setattr(run_all.ctrl, "code_git_state", lambda: dict(dirty))

    def never(*args, **kwargs) -> int:
        raise AssertionError("the entry spawned a freeze on uncommitted code")

    monkeypatch.setattr(run_all, "_spawn", never)
    with pytest.raises(ValueError) as refused:
        run_all.mode_freeze_capsule()
    assert "V168_CODE_NOT_COMMITTED" in str(refused.value)
