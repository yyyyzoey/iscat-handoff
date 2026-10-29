"""V168 differential tests for contract section 5 items 5 and 7.

These two behaviours are the ones V167 got wrong, so they get their own file rather
than a softened edit of an inherited assertion.  Item 7 is the quota semantics: a
start is one bounded solver instance that may spend up to its registered ceiling in
*real billed* forwards, the ceiling is enforced by the trusted service from durable
ledger rows, and cache hits cost nothing.  Item 5 is the execution identity: the
digest that gates a reservation is built from the executed sources, the configuration
and the staged task inputs, and never from the evidence tree it is about to write.

The F2c model stays behind the session tripwire in every test here, so a green run is
evidence about the rules, not about the physics.
"""
from __future__ import annotations

import copy
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

import v168_common as common
import v168_controller as controller
import v168_runner as runner
import v168_service as service_mod
import v168_worker as worker

from conftest import JAIL_ROOT, TEST_PREFIX, fake_forward

GUARD = service_mod.GUARD


def _rugged_remote(every: int):
    """A remote whose answer is deliberately non-smooth, so one pass wants more
    forwards than a ceiling allows.

    V167's defect only shows when a solver actually keeps asking: its smooth test
    response converged inside the first 200 calls, so a split pass looked identical to
    a single pass.  A rugged response is the honest way to reach the boundary.
    ``every`` marks that answer number as a free cache hit instead of a billed call.
    """
    state = {"requests": 0, "charged": 0, "hits": 0}
    grid = np.add.outer(np.arange(13.0), np.arange(13.0))

    def forward(theta, evaluation_index, pass_index):
        t = np.asarray(theta, dtype=float)
        state["requests"] += 1
        value = float(np.sum((t - np.array([120.0, 420.0, 0.0, 0.0])) ** 2))
        c = np.cos(grid * 0.05 + value * 1e-6) * 0.5 + np.sin(t[0] * 7.3) * 0.01
        hit = every > 0 and state["requests"] % every == 0
        state["charged"] += 0 if hit else 1
        state["hits"] += 1 if hit else 0
        return {"C": c, "charged": not hit, "cache_hit": bool(hit),
                "seq": state["requests"], "prediction_path": None,
                "prediction_sha256": common.array_sha(np.ascontiguousarray(c, np.float64)),
                "origin": "test_rugged", "forward_wall_ms": 0.0}

    forward.state = state
    return forward


class CountedRemote:
    """The stub remote a pass loop needs: ``forward`` plus four counters."""

    def __init__(self, forward):
        self.forward = forward

    def __getattr__(self, name):
        return getattr(self.forward, name)

    @property
    def forward_requests(self):
        return self.forward.state["requests"]

    @property
    def charged_forwards(self):
        return self.forward.state["charged"]

    @property
    def cache_hit_forwards(self):
        return self.forward.state["hits"]


def _solver_counter(monkeypatch):
    """Count real ``least_squares`` instantiations inside the production worker."""
    seen = {"instances": 0}
    original = worker.least_squares

    def counting(*args, **kwargs):
        seen["instances"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(worker, "least_squares", counting)
    return seen


def _pass_tree(tmp_path: Path, name: str = "PASSQUOTA01") -> tuple[dict, Path]:
    task_dir = tmp_path / "tasks" / (TEST_PREFIX + name)
    for sub in ("starts", "evaluations", "best"):
        (task_dir / sub).mkdir(parents=True, exist_ok=True)
    return {"task": task_dir}, task_dir


def _staged_payload(staged, kind: str):
    row = next(item for item in staged["staging"]["mapping"]["tasks"] if item["kind"] == kind)
    jail = JAIL_ROOT / row["task_id"]
    payload = common.read_json(jail / "input.json")
    data, _identity, _sha = common.frames_from_document(
        common.read_json(jail / "frames.json"), where="test:" + row["task_id"])
    reading = common.reading_from_document(payload["reading"])
    return row, payload, data, reading


# ------------------------------- item 7: one R start, one instance, 400 real calls
def test_the_four_hundredth_real_call_is_reached_inside_the_one_solver_instance(
        staged, tmp_path, monkeypatch):
    """Section 5.7, first half: 201 and 400 both belong to the same instance.

    V167 relaunched the solver whenever a 400-call slot had not been consumed by its
    200-nfev pass, which is exactly the 'artificial restart' the contract forbids.
    """
    _row, payload, data, reading = _staged_payload(staged, "SEARCH_EXTENSION")
    assert int(payload["cap_per_start"]) == 400
    assert len(payload["starts"]) == 1, "an R task extends exactly one prescribed start"
    counters = _solver_counter(monkeypatch)
    dirs, task_dir = _pass_tree(tmp_path)

    forward = _rugged_remote(every=0)
    record, _checkpoint = worker.run_pass(CountedRemote(forward), common, data, reading,
                                         dirs, payload, 1, 1, payload["starts"][0], 400)

    assert counters["instances"] == 1, "the worker restarted the solver inside one start"
    assert record["evaluations"] >= 201, "the pass never crossed the old 200-call boundary"
    assert record["charged_this_pass"] == 400 == record["local_cap"]
    assert record["cache_hits_this_pass"] == 0
    assert record["forward_requests"] == record["charged_this_pass"]
    # The stop is the registered ceiling, reported as it happened, with the best kept.
    assert record["execution_state"] == "PARTIAL_SEARCH"
    assert record["error"]["error_type"] == "CapReached"
    assert record["budget_blocked"] is False, "a local cap is not a ledger refusal"
    assert record["optimizer"] is None, "an escaped exception may not pose as a solver result"
    assert record["best"] is not None and np.isfinite(record["best"]["Q_total"])
    assert record["reportable_D"] is None

    on_disk = common.read_json(task_dir / "starts" / "001_pass_01.json")
    assert on_disk == record
    assert not list((task_dir / "starts").glob("001_pass_02*.json")), \
        "a second pass document means a second solver instance was launched"
    assert len(list((task_dir / "evaluations").glob("001_01_*.json"))) == 400
    crossed = common.read_json(task_dir / "evaluations" / "001_01_0201.json")
    assert crossed["pass_index"] == 1 and crossed["charged"] is True, \
        "the 201st real call must be a billed call of the first and only pass"


def test_the_ceiling_counts_billed_forwards_and_never_cache_hits(staged, tmp_path,
                                                                 monkeypatch):
    """Section 4.3: requests, billed calls and free reuses are three counters.

    One answer in three is served as a cache hit, so the pass asks far more often than
    it is allowed to bill.  If the stop test read the request count the ceiling would
    fire early; if it read nothing it would overrun 400 billed calls.
    """
    _row, payload, data, reading = _staged_payload(staged, "SEARCH_EXTENSION")
    counters = _solver_counter(monkeypatch)
    dirs, task_dir = _pass_tree(tmp_path, "PASSQUOTA02")

    forward = _rugged_remote(every=3)
    record, _checkpoint = worker.run_pass(CountedRemote(forward), common, data, reading,
                                         dirs, payload, 1, 1, payload["starts"][0], 400)

    assert counters["instances"] == 1
    assert record["charged_this_pass"] == 400
    assert record["forward_requests"] > 400
    assert record["cache_hits_this_pass"] == record["forward_requests"] - 400
    assert record["evaluations"] == record["forward_requests"]
    assert record["execution_state"] == "PARTIAL_SEARCH"

    documents = [common.read_json(path)
                 for path in sorted((task_dir / "evaluations").glob("001_01_*.json"))]
    assert len(documents) == record["evaluations"]
    assert sum(1 for doc in documents if doc["charged"]) == 400
    assert sum(1 for doc in documents if doc["cache_hit"]) == record["cache_hits_this_pass"]
    assert all("cache_hit" in doc and "charged" in doc for doc in documents), \
        "every persisted evaluation must state whether it cost anything"


def test_the_real_worker_round_runs_one_solver_instance_per_start(staged, service):
    """Section 5.7 through the production entry point: subprocess, RPC, ledger.

    The pass loop itself is proved above; this is the same rule asserted on the records
    a genuine ``v168_runner.run_task`` round trip leaves on disk.
    """
    task = TEST_PREFIX + "STARTQ0001"
    rows = [row for row in staged["staging"]["mapping"]["tasks"]
            if row["kind"] == "SEARCH_EXTENSION" and len(row["starts"]) == 1]
    source = JAIL_ROOT / rows[0]["task_id"]
    jail = JAIL_ROOT / task
    jail.mkdir(parents=True, exist_ok=True)
    for name in ("frames.json", "legal_records.json"):
        (jail / name).write_bytes((source / name).read_bytes())
    payload = copy.deepcopy(common.read_json(source / "input.json"))
    payload["task_id"] = task
    payload["reading"]["reading_id"] = task
    (jail / "input.json").write_bytes(common.canon(payload))

    cap_per_start = int(payload["cap_per_start"])
    task_cap = int(payload["task_cap"])
    frames_sha = runner.frames_sha_for(common.read_json(jail / "frames.json"),
                                       payload["group"])
    service.store.reserve(task, "start-quota-" + task, "SEARCH_EXTENSION", task_cap,
                          common.OWNER)
    service.set_task_budget(task, cap_per_start=cap_per_start, task_cap=task_cap,
                            start_count=len(payload["starts"]))
    receipt = runner.run_task(task_id=task,
                              expected_payload_sha256=common.sha_file(jail / "input.json"),
                              frames_sha256=frames_sha, service=service)

    assert receipt["worker_exit_code"] == 0, receipt["stderr_lines"][-8:]
    task_dir = common.OUT / "tasks" / task
    starts = common.read_json(task_dir / "search_result.json")["starts"]
    assert len(starts) == 1
    for slot in starts:
        prefix = "%03d_" % slot["start_index"]
        assert len(slot["passes"]) == 1, "a start may not be split into several passes"
        assert slot["solver_instances_per_start"] == 1
        assert slot["cap_per_start"] == cap_per_start
        assert [passed["pass_index"] for passed in slot["passes"]] == [1]
        assert slot["charged_this_start"] <= cap_per_start
        assert slot["charged_this_start"] == sum(p["charged_this_pass"]
                                                 for p in slot["passes"])
        finished = sorted(p.name for p in (task_dir / "starts").iterdir()
                          if p.name.startswith(prefix) and ".running." not in p.name)
        assert finished == [prefix + "pass_01.json"], \
            "one start, one durable pass document, or the solver was restarted"
    assert receipt["charged_replies"] == service.real_calls
    assert service.store.counts()[task] == receipt["charged_replies"]
    assert not (task_dir / "starts" / "001_pass_02.json").exists()


def _theta(index: int) -> list[float]:
    """Distinct legal theta: D walks inside the frozen box, the gap stays >= 100 nm."""
    return [30.0 + index * 1e-3, 400.0, 0.0, 0.0]


def _billed(service, task: str, start_index: int, index: int) -> dict:
    return service.charged_call(task, _theta(index), service.forward,
                                start_index=start_index, kind="OPTIMIZER")


# ------------------------------- item 7: the trusted service enforces the same grid
def test_the_service_refuses_the_four_hundred_first_real_call_before_billing_it(
        service, tmp_path):
    task = TEST_PREFIX + "STARTQ0002"
    # The ledger reservation is deliberately larger than the grid: if the per-start
    # ceiling were missing, the store would happily bill past 400, and this test would
    # see 401 rows instead of a refusal.
    service.store.reserve(task, "grid-" + task, "SEARCH_EXTENSION", 500, common.OWNER)
    service.set_task_budget(task, cap_per_start=400, task_cap=400, start_count=1)

    for index in range(400):
        assert _billed(service, task, 0, index)["charged"] is True
    assert service.store.counts()[task] == 400

    with pytest.raises(service_mod.CallCapReached) as refused:
        _billed(service, task, 0, 400)
    assert "PER_START_REAL_MODEL_CALL_CAP" in str(refused.value)
    assert service.store.counts()[task] == 400, "the refused call was billed anyway"
    with service.store.db() as conn:
        rows = list(conn.execute("SELECT seq, state FROM attempts WHERE task=? ORDER BY seq",
                                 (task,)))
    assert [row[0] for row in rows] == list(range(1, 401))
    assert service.real_calls == 400
    refusal = service.budget_refusals[-1]
    assert refusal == {"task_id": task, "start_index": 0, "charged_for_start": 400,
                       "charged_for_task": 400, "cap_per_start": 400, "task_cap": 400,
                       "refusal": refusal["refusal"]}
    assert refusal["refusal"].startswith("RecoveryRefused:PER_START_REAL_CALL_CAP")


def test_a_biased_task_gets_two_hundred_billed_calls_per_start_and_no_third_start(
        service, tmp_path):
    task = TEST_PREFIX + "STARTQ0003"
    service.store.reserve(task, "grid-" + task, "BIAS_STRESS", 600, common.OWNER)
    service.set_task_budget(task, cap_per_start=200, task_cap=400, start_count=2)

    for index in range(200):
        assert _billed(service, task, 0, index)["charged"] is True
    with pytest.raises(service_mod.CallCapReached):
        _billed(service, task, 0, 200)
    assert service.charged_for_start(task, 0) == 200

    # The second prescribed start gets its own ceiling; it is not a second pass of the
    # first one, and it may not inherit the first start's refusal.
    for index in range(200, 400):
        assert _billed(service, task, 1, index)["charged"] is True
    assert service.charged_for_start(task, 1) == 200
    assert service.charged_for_task(task) == 400
    with pytest.raises(service_mod.CallCapReached):
        _billed(service, task, 1, 400)

    # A third start is not in the registered grid at all, so it is a refusal rather
    # than an unbounded extra search.
    with pytest.raises(ValueError) as outside:
        _billed(service, task, 2, 401)
    assert "START_INDEX_OUTSIDE_REGISTERED_GRID:" + task + ":2" in str(outside.value)
    assert service.store.counts()[task] == 400
    assert service.real_calls == 400


def test_the_task_ceiling_bites_independently_of_the_per_start_ceiling(service):
    task = TEST_PREFIX + "STARTQ0004"
    service.store.reserve(task, "grid-" + task, "BIAS_STRESS", 600, common.OWNER)
    service.set_task_budget(task, cap_per_start=200, task_cap=250, start_count=2)
    for index in range(200):
        _billed(service, task, 0, index)
    for index in range(200, 250):
        _billed(service, task, 1, index)
    assert service.charged_for_start(task, 1) == 50
    assert service.charged_for_task(task) == 250

    with pytest.raises(service_mod.CallCapReached):
        _billed(service, task, 1, 250)
    refusal = service.budget_refusals[-1]
    assert refusal["charged_for_start"] == 50 < refusal["cap_per_start"], \
        "the refusal was attributed to the wrong ceiling"
    assert refusal["charged_for_task"] == refusal["task_cap"] == 250


def test_a_restarted_service_resumes_the_same_ceiling_from_the_durable_rows(
        service, tmp_path):
    """A new process on the same ledger cannot be handed a fresh ceiling.

    This is the accounting half of the sealed-loader rule: the counters come from
    durable attempt rows, so restarting the trusted service neither refunds nor
    top-ups what the first process already spent.
    """
    task = TEST_PREFIX + "STARTQ0005"
    service.store.reserve(task, "grid-" + task, "SEARCH_EXTENSION", 500, common.OWNER)
    service.set_task_budget(task, cap_per_start=400, task_cap=400, start_count=1)
    for index in range(399):
        _billed(service, task, 0, index)

    ledger = tmp_path / "v168_test_budget.sqlite"
    restarted = service_mod.PredictionService(service_mod.make_store(ledger),
                                             out=tmp_path / "restarted")
    (tmp_path / "restarted").mkdir(parents=True, exist_ok=True)
    restarted.model = object()
    restarted.forward = service.forward
    restarted.set_task_budget(task, cap_per_start=400, task_cap=400, start_count=1)
    assert restarted.charged_for_start(task, 0) == 399
    assert restarted.charged_for_task(task) == 399

    assert restarted.charged_call(task, _theta(399), restarted.forward,
                                  start_index=0, kind="OPTIMIZER")["charged"] is True
    assert restarted.charged_for_start(task, 0) == 400
    assert restarted.real_calls == 1, "a resumed ceiling may not restart the count"
    with pytest.raises(service_mod.CallCapReached):
        restarted.charged_call(task, _theta(400), restarted.forward,
                               start_index=0, kind="OPTIMIZER")
    assert service.store.counts()[task] == 400


# ------------------------------- item 5: the execution identity gates a reservation
@pytest.fixture()
def append_tree():
    """A throwaway tree inside results/v168, the place a run really appends."""
    parent = controller.ROOT / "results" / "v168" / "workstation_tests"
    parent.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="v168_append_", dir=str(parent)))
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=False)


def test_appending_run_evidence_never_moves_the_execution_identity(staged, append_tree):
    """Section 5.5, first half: writing results is not an execution change.

    The identity is deliberately a named file list, not a HEAD or an output-tree hash,
    so the authorized run can write predictions and reports without invalidating its
    own reservations between tasks.
    """
    before = controller.code_identities()
    capsule_before = controller.execution_capsule(staged)
    assert capsule_before["capsule_sha256"] == staged["capsule_sha256"], \
        "the capsule is not reproducible from the staged context"

    written = []
    for rel in ("tasks/V168_append/predictions/0001.json",
                "starts/001.json", "logs/model_construction.json",
                "controller_only/per_start_table.json"):
        path = append_tree / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(common.canon({"schema": "iscat168.append_probe.1", "path": rel}))
        written.append(path)
    (append_tree / "logs" / "controller_run.log").write_text("appended\n", encoding="utf-8")

    after = controller.code_identities()
    assert after["identity_sha256"] == before["identity_sha256"]
    assert after["files"] == before["files"]
    assert controller.execution_capsule(staged)["capsule_sha256"] == \
        capsule_before["capsule_sha256"]
    assert not [rel for rel in after["files"] if Path(rel).parts[0] == "results"], \
        "the identity walks the evidence tree, so appends would break the run"
    GUARD.require_frozen_capsule(capsule_before["capsule_sha256"],
                                 after_identity_digest(staged))


def after_identity_digest(staged) -> str:
    """Recompute the capsule after the appends, through the delivered guard."""
    return controller.execution_capsule(staged)["capsule_sha256"]


def edited_capsule(staged, *, file_rel: str | None = None,
                   payload_task: str | None = None) -> str:
    """The capsule digest the guard would recompute after a real science change.

    ``file_rel`` rewrites one executed source's hash; ``payload_task`` rewrites one
    staged task input's hash.  Either is what section 4.2 says must invalidate every
    reservation, so this helper returns the digest a stale pin would no longer match.
    """
    capsule = controller.execution_capsule(staged)
    if payload_task is None:
        require_rel = file_rel or "tools/v168/v168_worker.py"
        executed = dict(capsule["executed_files"])
        assert require_rel in executed, "the edited file is not part of the executed set"
        executed[require_rel] = "e" * 64
        payloads = dict(capsule["payload_sha256_by_task"])
    else:
        executed = dict(capsule["executed_files"])
        payloads = dict(capsule["payload_sha256_by_task"])
        assert payload_task in payloads
        payloads[payload_task] = "a" * 64
    return GUARD.capsule_digest(executed, {"schema": str(staged["plan"].get("schema")),
                                           "plan_sha256": controller.CONTRACT_PLAN_SHA256,
                                           "task_count": len(payloads)},
                                payloads, capsule["test_suite_sha256"])


def test_a_changed_staged_task_input_invalidates_the_capsule_too(staged):
    """Section 5.5 covers inputs as well as sources: a re-drawn reading is a new run."""
    capsule = controller.execution_capsule(staged)
    task = sorted(capsule["payload_sha256_by_task"])[0]
    moved = edited_capsule(staged, payload_task=task)
    assert moved != capsule["capsule_sha256"]
    with pytest.raises(ValueError) as refused:
        GUARD.require_frozen_capsule(capsule["capsule_sha256"], moved)
    assert "CODE_OR_INPUT_CHANGED_BEFORE_RESERVE_NO_MODEL_AUTHORITY" in str(refused.value)


@pytest.fixture()
def probe_control():
    """A throwaway control directory *inside* ROOT, removed on teardown.

    The controller spells every evidence path relative to ROOT, so a control root
    outside the repository would be refused for the wrong reason.
    """
    parent = controller.ROOT / "results" / "v168" / "workstation_tests"
    parent.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="v168_sq_", dir=str(parent)))
    try:
        (root / "logs").mkdir(parents=True, exist_ok=True)
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=False)


def test_a_science_source_edit_blocks_reserve_and_model_at_the_production_entry(
        staged, probe_control, monkeypatch):
    """Section 5.5, second half, through ``controller.prepare`` itself.

    The pin stands for a capsule frozen before an edit; the recomputed digest stands
    for the bytes about to run.  The refusal must happen after the run identity and
    before any signature context, reservation or model authority, so the round stops
    with nothing billed rather than reserving against stale bytes.
    """
    capsule = controller.execution_capsule(staged)
    stale = edited_capsule(staged, file_rel="tools/v168/v168_service.py")
    assert stale != capsule["capsule_sha256"]

    control = probe_control
    pinned = dict(capsule, capsule_sha256=stale)
    (control / "frozen_execution_capsule.json").write_bytes(common.canon(pinned))
    committed = {"schema": "iscat168.code_git_state.1", "git_head": staged["git_head"],
                 "estimator_code_tracked": True, "estimator_code_clean": True,
                 "bundle_tracked": True}
    monkeypatch.setattr(controller, "CONTROL", control)
    monkeypatch.setattr(controller, "CAPSULE_PATH",
                        control / "frozen_execution_capsule.json")
    monkeypatch.setattr(controller, "LEDGER_PATH", control / "logs" / "v168_budget.sqlite")
    monkeypatch.setattr(controller, "code_git_state", lambda: dict(committed))

    signed_before = service_mod.signature_context()
    with pytest.raises(ValueError) as refused:
        controller.prepare(dry_run=False)
    assert "CODE_OR_INPUT_CHANGED_BEFORE_RESERVE_NO_MODEL_AUTHORITY" in str(refused.value)

    # The stop is early: nothing was signed for a new run, nothing was reserved.
    assert service_mod.signature_context() == signed_before
    assert signed_before["capsule_sha256"] == capsule["capsule_sha256"]
    assert not (control / "logs" / "v168_budget.sqlite").exists()
    assert not (control / "task_signatures.json").exists()
    assert (control / "run_identity.json").is_file(), \
        "the identity is recorded before the capsule gate, so the stop is auditable"
    assert service_mod.PredictionService(
        service_mod.make_store(control / "logs" / "fresh.sqlite")).constructions == 0
    assert "REAL_MODEL_CONSTRUCTION" not in str(sys.modules.get("v142_model"))
    assert "v142_model" not in sys.modules, "the refused round imported the model runtime"
