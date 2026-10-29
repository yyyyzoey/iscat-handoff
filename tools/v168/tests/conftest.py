"""Fixtures for the V168 workstation tests.

These tests drive the real production entry points: the staged estimator jails, the
worker subprocess, the controller-side runner, the frozen budget ledger, the frozen
objective core and the estimator-side payload gate.  The only thing they replace is
the F2c model itself, which is pinned by the ``no_real_model_construction`` tripwire,
so a test run can neither build the scientific model nor bill a charged forward.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

TESTS_DIR = Path(__file__).resolve().parent
TOOLS_DIR = TESTS_DIR.parents[1]
for candidate in (str(TOOLS_DIR / "v168"), str(TOOLS_DIR / "v168_bundle" / "code"),
                  str(TOOLS_DIR / "v165_bundle" / "code")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

import v168_common as common  # noqa: E402

common.bootstrap_paths(estimator=False)

import v168_controller as controller  # noqa: E402
import v168_service as service_mod  # noqa: E402

TEST_PREFIX = "V168_TEST"
JAIL_ROOT = common.OUT / "estimator_inputs"
QUARANTINE = common.OUT / "workstation_tests" / "quarantined_test_tasks"

# The round has two contract documents with authority over different things: the V168
# contract fixes this round's budget and rules, and the V167 contract in the inherited
# bundle still carries the V166 input pins and wording the V168 text refers back to.
# Both are read by the literal tests; neither is treated as a substitute for the other.
CONTRACT_PATH = next(iter(sorted(common.BUNDLE.glob("00_V168_*.md"))))
INHERITED_CONTRACT_PATH = next(iter(sorted(
    (common.ROOT / "tools" / "v167_bundle").glob("00_V167_*.md"))))


def contract_text(path: Path = CONTRACT_PATH) -> str:
    """Read one contract exactly as delivered, with no normalisation."""
    return Path(path).read_text(encoding="utf-8")


def normalised(text: str) -> str:
    """Collapse whitespace and unify the minus sign, so a reformatted clause still
    matches the literal it names.  This widens *formatting* tolerance only; every
    needle below is still a verbatim substring of the contract."""
    return re.sub(r"\s+", "", text).replace("\u2212", "-").replace("\u2012", "-")


def contract_budget_table(text: str) -> dict:
    """Parse the authorised-budget pipe table out of a contract.

    The prose around the table is edited between rounds; the table is the machine-readable
    denominator this round spends against.  Rows are ``phase -> (historical, new,
    combined)``, with the ``合计`` row keyed as ``"TOTAL"``.  A malformed or missing row is
    a hard failure rather than a silent zero, because every downstream cap assertion is
    only as honest as this parse.
    """
    rows: dict[str, tuple[int, int, int]] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != 4:
            continue
        head = cells[0].replace("**", "")
        if head in ("阶段", "---"):
            continue
        try:
            values = tuple(int(cell.replace(",", "")) for cell in cells[1:])
        except ValueError:
            continue
        rows["TOTAL" if head.startswith("合计") else head] = values
    return rows

# Evidence channels used by tools/v168/run_workstation_tests.py.  Both are opt-in:
# with the environment unset the suite behaves as before, and the tripwire file is
# created only when a test actually reaches the real model loader, so an absent file
# is the honest way to record zero real constructions.
OUTCOMES_ENV = "V168_PYTEST_OUTCOMES"
TRIPWIRE_ENV = "V168_REAL_CALL_TRIPWIRE"
TRIPWIRE_FILE = "real_f2c_tripwire.txt"
ZERO_MARKER = "ZERO_REAL_F2C_MODEL_CONSTRUCTION_ATTEMPTS"

_OUTCOMES: dict[str, dict] = {}


def _env_path(name: str) -> Path | None:
    raw = os.environ.get(name, "").strip()
    return Path(raw) if raw else None


def _append_tripwire(text: str) -> None:
    path = _env_path(TRIPWIRE_ENV)
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="ascii") as handle:
        handle.write(text + "\n")
        handle.flush()
        os.fsync(handle.fileno())

# ------------------------------------------------------------------ fake model
_GRID = np.add.outer(np.arange(13.0), np.arange(13.0))
_FAKE_REFERENCE = np.array([120.0, 420.0, 0.0, 0.0])


def fake_forward(theta):
    """Deterministic smooth 13x13 response; no F2c, no BEM, no camera.

    It is deliberately weakly dependent on theta so a bounded trf pass converges on
    its own tolerance criteria instead of burning the whole 200-call slot, which keeps
    a plumbing test fast while still exercising every persisted record.
    """
    t = np.asarray(theta, dtype=float)
    value = float(np.sum((t - _FAKE_REFERENCE) ** 2))
    return np.cos(_GRID * 0.05 + value * 1e-6) * 0.5


class FakeModelReturn:
    """The Observation shape ``tools/field_forward_reference.Observation`` exposes.

    Contract 4.1 refuses a bare array on the estimator side: a real forward answers
    with Ibg, I, C and score_C plus the theta it was asked for and its model id, and
    ``v168_service._read_model_output`` now enforces exactly that.  So a *billed* test
    forward has to return this object rather than the plain array.  ``score_C`` holds
    the numbers ``fake_forward`` produced, which keeps every downstream value, hash and
    witness comparison in this suite identical to the array-only case.
    """

    def __init__(self, theta, c, *, model_id=None):
        array = np.asarray(c, dtype=float)
        self.Ibg = _GRID + 1.0
        self.I = _GRID
        self.C = array
        self.score_C = array
        self.theta = np.asarray(theta, dtype=float)
        self.model_id = common.MODEL_ID if model_id is None else model_id


def fake_model_forward(theta):
    """The same answer as ``fake_forward``, wrapped in the real return contract."""
    return FakeModelReturn(theta, fake_forward(theta))


def _quarantine_test_task_trees() -> list[str]:
    """Move every V168_TEST* artefact out of the trees a real run reads.

    ``PredictionService.load_existing_predictions`` refuses any prediction whose
    charge binding is absent from the live ledger, so a test prediction left in
    results/v168/tasks would abort the authorized run.  Nothing is deleted: the
    trees are renamed into results/v168/workstation_tests/quarantined_test_tasks.
    """
    moved: list[str] = []
    for parent in (common.OUT / "tasks", JAIL_ROOT, controller.CONTROL / "rpc"):
        if not parent.is_dir():
            continue
        for item in sorted(parent.iterdir()):
            if not item.name.startswith(TEST_PREFIX):
                continue
            target = QUARANTINE / parent.name / item.name
            if target.exists():
                # An earlier pass already owns that name.  Keeping both is what the
                # docstring promises, so the older artefact moves to a numbered slot
                # instead of being overwritten.
                base = target
                step = 1
                while target.exists():
                    target = base.with_name(base.name + ".pass" + format(step, "02d"))
                    step += 1
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(item), str(target))
            moved.append(str(target))
    return moved


@pytest.fixture(scope="session", autouse=True)
def no_real_model_construction():
    """Tripwire: any attempt to import or build the F2c runtime fails the suite."""
    def refuse(*args, **kwargs):
        _append_tripwire("REAL_F2C_MODEL_CONSTRUCTION_ATTEMPT")
        raise AssertionError("REAL_MODEL_CONSTRUCTION_ATTEMPTED_IN_TESTS")

    original = service_mod.model_modules
    service_mod.model_modules = refuse
    for name in ("v142_model", "v146_runtime", "field_forward_reference"):
        assert name not in sys.modules, "MODEL_RUNTIME_ALREADY_IMPORTED:" + name
    _quarantine_test_task_trees()
    yield refuse
    service_mod.model_modules = original
    _quarantine_test_task_trees()
    for name in ("v142_model", "v146_runtime", "field_forward_reference"):
        assert name not in sys.modules, "MODEL_RUNTIME_IMPORTED_DURING_TESTS:" + name
    # The tripwire file is written only by an attempt, so a run that never reached the
    # loader leaves it absent.  When a harness asks for evidence explicitly, the zero
    # result is recorded in the same file rather than asserted by the test author.
    if _env_path(TRIPWIRE_ENV) is not None and not _env_path(TRIPWIRE_ENV).exists():
        _append_tripwire(ZERO_MARKER)


def pytest_runtest_logreport(report):
    """Record the real outcome of every phase, for the workstation test receipt."""
    row = _OUTCOMES.setdefault(str(report.nodeid), {"nodeid": str(report.nodeid),
                                                    "phases": {}})
    row["phases"][report.when] = {
        "outcome": report.outcome,
        "longrepr": (str(report.longrepr)[:2000] if report.longrepr else None),
        "duration": round(float(report.duration), 4),
    }


def pytest_sessionfinish(session, exitstatus):
    path = _env_path(OUTCOMES_ENV)
    if path is None:
        return
    rows = []
    for nodeid in sorted(_OUTCOMES):
        row = _OUTCOMES[nodeid]
        phases = row["phases"]
        worst = "passed"
        for when in ("setup", "call", "teardown"):
            outcome = phases.get(when, {}).get("outcome")
            if outcome in ("failed", "error") and worst == "passed":
                worst = "failed"
            elif outcome == "skipped" and worst == "passed":
                worst = "skipped"
        rows.append({"nodeid": nodeid, "final_outcome": worst,
                     "collected": bool(session.items) and any(
                         item.nodeid == nodeid for item in session.items),
                     "phases": phases})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps({"schema": "iscat168.pytest_outcomes.1",
                                 "exitstatus": int(exitstatus), "tests": rows,
                                 "counts": {
                                     outcome: sum(1 for row in rows
                                                  if row["final_outcome"] == outcome)
                                     for outcome in ("passed", "failed", "skipped")}},
                                indent=1, sort_keys=True).encode("utf-8"))


@pytest.fixture(scope="session")
def staged():
    """The real P0/P1 staging a dry-run prepare produces, with zero model calls."""
    ctx = controller.prepare(dry_run=True)
    assert ctx["staging"]["mapping"]["task_count"] == 23
    assert ctx["dry_run"] is True
    return ctx


@pytest.fixture(scope="session", autouse=True)
def signing_run_identity(staged):
    """Contract 4.2: no task may be signed before the frozen run identity is installed.

    ``prepare`` installs the signature context once, from the frozen capsule, and the
    service refuses to sign anything without it.  Making that a session requirement is
    the honest way to keep a test from passing only because of file order, and the
    context is the real one: it is never replaced by a synthetic value, because a second
    install with different content is itself a refusal.
    """
    context = service_mod.signature_context()
    assert context["run_id"] == staged["run_id"], "SIGNATURE_RUN_ID_IS_NOT_THE_STAGED_RUN"
    assert context["capsule_sha256"] == staged["capsule_sha256"], \
        "SIGNATURE_CAPSULE_IS_NOT_THE_FROZEN_CAPSULE"
    assert context["authorization_sha256"] == common.AUTHORIZATION_SHA256, \
        "SIGNATURE_AUTHORIZATION_IS_NOT_THE_PINNED_AUTHORIZATION"
    assert context["plan_sha256"] == controller.CONTRACT_PLAN_SHA256, \
        "SIGNATURE_PLAN_IS_NOT_THE_FROZEN_PLAN"
    return context


@pytest.fixture()
def service(tmp_path, no_real_model_construction):
    """A real PredictionService on a scratch ledger, driven by the fake forward."""
    store = service_mod.make_store(tmp_path / "v168_test_budget.sqlite")
    service_dir = tmp_path / "service_out"
    service_dir.mkdir(parents=True, exist_ok=True)
    live = service_mod.PredictionService(store, out=service_dir)
    live.model = object()
    # The service's own forward stands in for the live model, so it must satisfy the
    # estimator-side return contract, not just hand back a shape-correct array.
    live.forward = fake_model_forward
    return live


@pytest.fixture()
def scratch(tmp_path):
    scratch_dir = tmp_path / "scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    return scratch_dir
