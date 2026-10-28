"""Fixtures for the V167 workstation tests.

These tests drive the real production entry points: the staged estimator jails, the
worker subprocess, the controller-side runner, the frozen budget ledger, the frozen
objective core and the estimator-side payload gate.  The only thing they replace is
the F2c model itself, which is pinned by the ``no_real_model_construction`` tripwire,
so a test run can neither build the scientific model nor bill a charged forward.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

TESTS_DIR = Path(__file__).resolve().parent
TOOLS_DIR = TESTS_DIR.parents[1]
for candidate in (str(TOOLS_DIR / "v167"), str(TOOLS_DIR / "v167_bundle" / "code"),
                  str(TOOLS_DIR / "v165_bundle" / "code")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

import v167_common as common  # noqa: E402

common.bootstrap_paths(estimator=False)

import v167_controller as controller  # noqa: E402
import v167_service as service_mod  # noqa: E402

TEST_PREFIX = "V167_TEST"
JAIL_ROOT = common.OUT / "estimator_inputs"
QUARANTINE = common.OUT / "workstation_tests" / "quarantined_test_tasks"

# Evidence channels used by tools/v167/run_workstation_tests.py.  Both are opt-in:
# with the environment unset the suite behaves as before, and the tripwire file is
# created only when a test actually reaches the real model loader, so an absent file
# is the honest way to record zero real constructions.
OUTCOMES_ENV = "V167_PYTEST_OUTCOMES"
TRIPWIRE_ENV = "V167_REAL_CALL_TRIPWIRE"
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


def _quarantine_test_task_trees() -> list[str]:
    """Move every V167_TEST* artefact out of the trees a real run reads.

    ``PredictionService.load_existing_predictions`` refuses any prediction whose
    charge binding is absent from the live ledger, so a test prediction left in
    results/v167/tasks would abort the authorized run.  Nothing is deleted: the
    trees are renamed into results/v167/workstation_tests/quarantined_test_tasks.
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
    path.write_bytes(json.dumps({"schema": "iscat167.pytest_outcomes.1",
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


@pytest.fixture()
def service(tmp_path, no_real_model_construction):
    """A real PredictionService on a scratch ledger, driven by the fake forward."""
    store = service_mod.make_store(tmp_path / "v167_test_budget.sqlite")
    service_dir = tmp_path / "service_out"
    service_dir.mkdir(parents=True, exist_ok=True)
    live = service_mod.PredictionService(store, out=service_dir)
    live.model = object()
    live.forward = lambda theta: fake_forward(theta)
    return live


@pytest.fixture()
def scratch(tmp_path):
    scratch_dir = tmp_path / "scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    return scratch_dir
