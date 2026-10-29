"""V168 production entry point: plan, test, rehearse, run, pack, from one place.

Contract section 10.4 says the real workstation entry point and the single
``run_all.py`` are Codex's integration work, so the bundle deliberately does not carry
them.  This module is controller-only.  It never runs inside a worker jail and it makes
no model call of its own: every authorized computation is delegated to
``v168_controller.py``, which stays the only writer of the ledger, the seal and the step
trace.  The one thing implemented here rather than there is the return package, because
no committed V166 packer exists in the repository.

Modes (mutually exclusive):

  --plan               run the bundle planner into results/v168_prepared (zero calls)
  --workstation-tests  run the three test inventories through run_workstation_tests.py
  --dry-run            controller P0/P1 rehearsal, zero model calls
  --freeze-capsule     contract 4.2 freeze: committed code + verified test release,
                       one frozen capsule written, nothing reserved, nothing constructed
  --run                the authorized run: one construction, at most 10,000 charged calls
  --pack-rehearsal     exercise the packer against today's tree, primary names untouched
  --pack               gate, then build the unique return ZIP plus its external receipts
  --status             read-only summary of the ledger, task states and contract pins
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools" / "v168"
BUNDLE = ROOT / "tools" / "v168_bundle"
V165_STORE = ROOT / "tools" / "v165_bundle" / "code" / "v152_budget_store.py"
OUT = ROOT / "results" / "v168"
PREPARED = ROOT / "results" / "v168_prepared"
V166 = ROOT / "results" / "v166"
LOGS = OUT / "logs"
LEDGER = LOGS / "v168_budget.sqlite"
CONTROL = OUT / "controller_only"
JAIL = OUT / "estimator_inputs"
PLAN = PREPARED / "controller_only" / "plan.json"
TASKS = OUT / "tasks"
PREPARED_LOG = PREPARED / "logs"
ZIP_NAME = "iscat_v168_return_001.zip"
REHEARSAL_DIR = PREPARED / "pack_rehearsal"

# The authorized round: one construction, then the two computation phases, then the
# seal and the independent score.  manifest and verification are deliberately NOT here:
# they have to describe the delivered tree, including the reports written after the
# round, so they are written once by the closing evidence pass at --pack time.
RUN_STEPS = "prepare,bind,run,tables,final,estimates,seal,validate,records,status"
# Contract 4.2 and 11.6: reporting, read-only verification and failure packing may not
# call prepare/reserve/model construction again.  The closing pass is therefore the
# evidence-only set, and the controller rebuilds its context by read-only means, so a
# round that was blocked by its own gates can still be reported and packaged honestly.
CLOSE_STEPS = "tables,records,status,manifest,verification"

if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import v168_common as common                                       # noqa: E402
import v168_controller as ctrl                                     # noqa: E402
import v168_service as service                                     # noqa: E402
import run_workstation_tests as ws_tests                           # noqa: E402
import v168_test_binding as test_binding                            # noqa: E402

CSV_HEADER = "sha256,bytes,arcname"


# --------------------------------------------------------------- small utilities

def _utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require(test: bool, message: str) -> None:
    if not test:
        raise ValueError("RUN_ALL_REFUSED:" + message)


def _child_env() -> dict[str, str]:
    """Single-threaded numerics and no pytest plugin leakage into the children."""
    env = dict(os.environ)
    env.update({
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTHONPATH": str(TOOLS),
    })
    env.pop("PYTEST_ADDOPTS", None)
    return env


def _controller_argv(*, dry_run: bool, steps: str) -> list[str]:
    argv = [sys.executable, "-X", "utf8", str(TOOLS / "v168_controller.py"),
            "--steps", steps]
    if dry_run:
        argv.append("--dry-run")
    return argv


def _spawn(argv: list[str], log_path: Path) -> int:
    """Run a child, streaming to the console and to one append-only log file."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if log_path.exists():
        raise FileExistsError("LOG_NAME_ALREADY_USED:" + str(log_path))
    print("$ " + " ".join(argv), flush=True)
    print("LOG: " + str(log_path), flush=True)
    with log_path.open("w", encoding="utf-8", newline="\n") as handle:
        proc = subprocess.Popen(argv, cwd=str(ROOT), env=_child_env(),
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace", bufsize=1)
        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            handle.write(line)
            handle.flush()
        return proc.wait()


def _write_new(path: Path, text: str) -> str:
    """Evidence writer for run_all: a primary name is never rewritten."""
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = text.encode("utf-8")
    if path.exists():
        _require(path.read_bytes() == raw, "EVIDENCE_CHANGED_REFUSING_OVERWRITE:" + str(path))
        return _sha(path)
    with path.open("xb") as handle:
        handle.write(raw)
    return _sha(path)


def _json_text(document: Any) -> str:
    return json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def _contract_file() -> Path:
    hits = sorted(BUNDLE.glob("00_V168_*.md"))
    _require(len(hits) == 1, "CONTRACT_FILE_AMBIGUOUS:" + str(hits))
    return hits[0]


# ---------------------------------------------------------------------- modes

def mode_plan() -> int:
    """Contract section 10.3: prepare the 23 task payloads, make no model call."""
    if PLAN.is_file():
        observed = _sha(PLAN)
        _require(observed == ctrl.CONTRACT_PLAN_SHA256,
                 "PREPARED_PLAN_SHA_MISMATCH:" + observed)
        print("PLAN_ALREADY_PINNED " + observed + " -- planner not re-run")
        return 0
    _require(not PREPARED.exists(),
             "PREPARED_TREE_EXISTS_WITHOUT_PINNED_PLAN:" + str(PREPARED))
    argv = [sys.executable, "-X", "utf8", str(BUNDLE / "code" / "v168_plan.py"),
            "--v166-results", str(V166), "--out", str(PREPARED)]
    code = _spawn(argv, PREPARED_LOG / ("plan_" + _utc() + ".log"))
    _require(code == 0, "PLAN_STEP_FAILED_EXIT_" + str(code))
    _require(_sha(PLAN) == ctrl.CONTRACT_PLAN_SHA256, "PLAN_SHA_NOT_CONTRACT_VALUE")
    return 0


def mode_workstation_tests(run_id: str) -> int:
    return ws_tests.main(["--out", str(OUT / "workstation_tests"), "--run-id", run_id])


def mode_dry_run() -> int:
    """Full step list against the rehearsal paths; nothing here can spend budget."""
    return _spawn(_controller_argv(dry_run=True, steps="all"),
                  PREPARED_LOG / ("controller_dry_run_" + _utc() + ".log"))


def mode_freeze_capsule() -> int:
    """Contract 4.2 freeze: committed code, verified test release, one capsule, no spend.

    The production entry has to expose this step, otherwise the only way to reach the
    authorized run would be to hand-run the controller and let it invent its own pin.
    The refusal for uncommitted code lives in the controller; it is checked here too so
    an operator gets the answer before a child process starts.
    """
    state = ctrl.code_git_state()
    _require(state["estimator_code_tracked"] and state["estimator_code_clean"]
             and state["bundle_tracked"],
             "V168_CODE_NOT_COMMITTED:" + json.dumps(state["missing_from_git"])
             + "|" + json.dumps(state["untracked_python_under_tools_v168"])
             + "|" + json.dumps(state["dirty_git_entries"]))
    argv = [sys.executable, "-X", "utf8", str(TOOLS / "v168_controller.py"),
            "--freeze-capsule"]
    return _spawn(argv, PREPARED_LOG / ("controller_freeze_capsule_" + _utc() + ".log"))


def mode_run() -> int:
    """The authorized computation.  Refuses unless the code is committed and clean."""
    state = ctrl.code_git_state()
    _require(state["estimator_code_tracked"] and state["estimator_code_clean"]
             and state["bundle_tracked"],
             "V168_CODE_NOT_COMMITTED:" + json.dumps(state["missing_from_git"])
             + "|" + json.dumps(state["untracked_python_under_tools_v168"])
             + "|" + json.dumps(state["dirty_git_entries"]))
    _require_run_entry()
    return _spawn(_controller_argv(dry_run=False, steps=RUN_STEPS),
                  LOGS / ("controller_run_" + _utc() + ".log"))


def mode_status() -> int:
    """Read-only view of what the round has actually done so far."""
    report: dict[str, Any] = {"schema": "iscat168.entry_status.1", "utc": _utc(),
                              "git_head": ctrl.git_text("rev-parse", "HEAD"),
                              "code_git_state": ctrl.code_git_state(),
                              "plan_sha256": _sha(PLAN) if PLAN.is_file() else None,
                              "plan_pinned_ok": (PLAN.is_file()
                                                 and _sha(PLAN) == ctrl.CONTRACT_PLAN_SHA256)}
    # Contract 4.2 puts the freeze between the commit and the run, so an operator asking
    # "what is the state" has to be able to see whether the pin exists yet.  Read-only.
    capsule_path = CONTROL / "frozen_execution_capsule.json"
    if capsule_path.is_file():
        pin = ctrl.read_json(capsule_path)
        report["frozen_execution_capsule"] = {
            "present": True, "path": str(capsule_path.relative_to(ROOT)),
            "sha256": _sha(capsule_path),
            "capsule_sha256": pin.get("capsule_sha256"),
            "test_suite_sha256": pin.get("test_suite_sha256"),
            "task_count": pin.get("task_count"), "frozen_utc": pin.get("frozen_utc"),
            "workstation_test_release_receipt_sha256": (
                pin.get("workstation_test_release") or {}).get("receipt_sha256")}
    else:
        report["frozen_execution_capsule"] = {"present": False,
                                              "path": str(capsule_path.relative_to(ROOT)),
                                              "status": "NOT_STARTED"}
    if LEDGER.is_file():
        db = service.read_only_ledger(LEDGER)
        try:
            report["ledger"] = {
                "sha256": _sha(LEDGER), "bytes": LEDGER.stat().st_size,
                "by_phase": [list(row) for row in db.execute(
                    "SELECT phase, SUM(used), SUM(cap), COUNT(*) FROM tasks"
                    " GROUP BY phase ORDER BY phase")],
                "states": {str(row[0]): int(row[1]) for row in db.execute(
                    "SELECT state, COUNT(*) FROM tasks GROUP BY state")},
                "charged_attempts": int(db.execute(
                    "SELECT COUNT(*) FROM attempts").fetchone()[0]),
                "attempt_states": {str(row[0]): int(row[1]) for row in db.execute(
                    "SELECT state, COUNT(*) FROM attempts GROUP BY state")},
            }
        finally:
            db.close()
    else:
        report["ledger"] = {"status": "NOT_STARTED", "path": str(LEDGER),
                            "charged_attempts": 0}
    for name in ("seal.json", "status.json", "verification.json", "manifest.json",
                 "estimates_new.json", "estimates_merge_reuse.json"):
        path = OUT / name
        report[name] = {"present": path.is_file(),
                        "sha256": _sha(path) if path.is_file() else None}
    report["task_directories"] = sorted(p.name for p in TASKS.glob("V168_*")) \
        if TASKS.is_dir() else []
    report["contract_pins"] = {rel: {"path_present": _pin_path(rel).is_file(),
                                     "match": (_pin_path(rel).is_file()
                                               and _sha(_pin_path(rel)) == pinned)}
                               for rel, pinned in sorted(ctrl.CONTRACT_PINS.items())}
    print(_json_text(report))
    return 0


def _pin_path(rel: str) -> Path:
    """Resolve a contract pin exactly as the controller does: repository path first."""
    path = ROOT / rel
    if path.is_file():
        return path
    stem = Path(rel).name
    for candidate in (V166 / stem, V166 / "deliverables" / stem):
        if candidate.is_file():
            return candidate
    return path


def _sealed_task_count() -> tuple[int, int]:
    entries = ctrl.read_json(PLAN)["entries"]
    total = len(entries)
    sealed = sum(1 for entry in entries
                 if (TASKS / str(entry["task_id"]) / "result.json").is_file())
    return sealed, total


def _traces() -> list[tuple[Path, dict[str, Any]]]:
    """Every published step trace, oldest first: the primary plus its versioned copies."""
    _current, history = ctrl.latest_evidence(CONTROL / "step_sequence.json")
    return [(path, ctrl.read_json(path)) for path in history if path.is_file()]


def _require_run_entry() -> None:
    """Allow one authorized round, plus recovery of that round if it was interrupted.

    The ledger is created by the first authorized call, so its mere existence is not a
    reason to refuse: ``run_round`` skips every task already settled in the ledger and
    spends nothing on it again.  What is refused is a *second* round -- once every
    planned task is sealed, or once a round has finished with exit code zero.  A sealed
    loader can only be recovered read-only (contract section 7), so a resumed process
    cannot spend anything the first process did not already spend; that is stated here
    rather than hidden, and the controller enforces it.
    """
    sealed, total = _sealed_task_count()
    if not LEDGER.exists():
        _require(sealed == 0, "SEALED_TASK_RESULTS_WITHOUT_LEDGER:"
               + str(sealed) + "/" + str(total))
        print("RUN_ENTRY_FIRST_ROUND sealed_tasks=" + str(sealed) + "/" + str(total),
              flush=True)
        return
    traces = _traces()
    _require(bool(traces), "LEDGER_WITHOUT_STEP_TRACE_REFUSING:" + str(LEDGER)
             + "; never delete or rename it")
    rounds = [doc for _path, doc in traces
              if "run" in (doc.get("requested_steps") or [])]
    _require(bool(rounds), "STEP_TRACE_HAS_NO_AUTHORIZED_ROUND:"
           + str([doc.get("requested_steps") for _p, doc in traces]))
    last = rounds[-1]
    _require(last.get("dry_run") is not True, "ONLY_A_DRY_RUN_RECORDED_A_RUN_STEP")
    _require(sealed < total, "AUTHORIZED_ROUND_ALREADY_SEALED_ALL_TASKS:"
             + str(sealed) + "/" + str(total) + "; use --status then --pack")
    _require(last.get("exit_code") != 0, "AUTHORIZED_ROUND_ALREADY_EXITED_ZERO:"
             + str(last.get("run_id")) + "; a second round needs new authorization")
    print("RUN_ENTRY_RESUMING prior_run_id=" + str(last.get("run_id"))
          + " prior_exit_code=" + str(last.get("exit_code"))
          + " failed_step=" + str(last.get("failed_step"))
          + " sealed_tasks=" + str(sealed) + "/" + str(total)
          + " note=a sealed loader is recovered read-only, so no new calls are possible"
            " unless the loader was never constructed", flush=True)


# ----------------------------------------------------------------- the packer

def _publish_stable_run_log() -> dict[str, Any]:
    """Give the authorized round's console transcript one stable, packable name.

    Every entry into the round keeps its own timestamped transcript, and the contract
    asks for the complete error log, so the stable file is those transcripts in time
    order with a header per transcript.  It is append-only: a second pack must never
    rewrite an earlier transcript's bytes, and a mismatch is a refusal.
    """
    sources = sorted(LOGS.glob("controller_run_*.log"))
    _require(bool(sources), "NO_AUTHORIZED_RUN_TRANSCRIPT_TO_PUBLISH")
    text = "".join("\n===== transcript " + path.name + " =====\n"
                   + path.read_text(encoding="utf-8", errors="replace")
                   for path in sources)
    raw = text.encode("utf-8")
    target = LOGS / "controller_run.log"
    mode = "written"
    if target.exists():
        current = target.read_bytes()
        _require(raw.startswith(current),
                 "STABLE_TRANSCRIPT_NOT_APPEND_ONLY:" + str(target))
        if raw != current:
            with target.open("ab") as handle:
                handle.write(raw[len(current):])
            mode = "appended"
    else:
        target.write_bytes(raw)
    return {"schema": "iscat168.stable_run_log.1", "path": str(target),
            "mode": mode, "bytes": target.stat().st_size, "sha256": _sha(target),
            "source_transcripts": [{"path": str(path), "sha256": _sha(path),
                                    "bytes": path.stat().st_size} for path in sources],
            "model_calls": 0}


def _pack_gate() -> dict[str, Any]:
    """Every primary deliverable named by contract section 11 must really exist."""
    checks: dict[str, Any] = {}
    traces = _traces()
    _require(bool(traces), "PACK_GATE_NO_STEP_SEQUENCE_AT_ALL")
    rounds = [doc for _path, doc in traces
              if "run" in (doc.get("requested_steps") or [])]
    _require(bool(rounds), "PACK_GATE_NO_AUTHORIZED_ROUND_TRACE")
    closing = traces[-1][1]
    sequence = rounds[-1]
    checks["step_sequence_paths"] = [str(path) for path, _doc in traces]
    checks["step_sequence_run_ids"] = [str(doc.get("run_id")) for _p, doc in traces]
    checks["authorized_round_run_id"] = sequence.get("run_id")
    checks["authorized_round_dry_run"] = bool(sequence.get("dry_run"))
    checks["authorized_round_exit_code"] = sequence.get("exit_code")
    checks["authorized_round_requested_steps"] = sequence.get("requested_steps")
    checks["authorized_round_model_constructions"] = sequence.get(
        "model_constructions_in_process")
    checks["latest_trace_run_id"] = closing.get("run_id")
    checks["latest_trace_exit_code"] = closing.get("exit_code")
    checks["latest_trace_requested_steps"] = closing.get("requested_steps")
    _require(not checks["authorized_round_dry_run"], "ONLY_A_DRY_RUN_HAS_BEEN_RECORDED")
    _require(checks["authorized_round_exit_code"] == 0,
             "AUTHORIZED_RUN_DID_NOT_EXIT_ZERO:"
             + str(checks["authorized_round_exit_code"]))
    _require(closing.get("exit_code") == 0,
             "CLOSING_EVIDENCE_PASS_DID_NOT_EXIT_ZERO:" + str(closing.get("exit_code")))
    _require(sequence.get("run_id") == closing.get("run_id"),
             "CLOSING_PASS_BELONGS_TO_ANOTHER_ROUND:" + str(sequence.get("run_id"))
             + "!=" + str(closing.get("run_id")))
    _require(checks["authorized_round_model_constructions"] == 1,
             "PACK_GATE_NOT_ONE_CONSTRUCTION:"
             + str(checks["authorized_round_model_constructions"]))
    # Contract section 7 at pack time.  The release receipt is re-verified against the
    # bytes on disk now, the frozen capsule must name the same test suite, and the
    # authorized round's own preamble must show it passed that gate before it reserved.
    # A round delivered on strategy-function evidence, or on a receipt that has gone
    # stale, stops here rather than becoming a ZIP.
    try:
        release = test_binding.verify()
    except ValueError as exc:
        _require(False, "PACK_GATE_NO_WORKSTATION_TEST_RELEASE_RECEIPT:" + str(exc)[:400])
    capsule_path = CONTROL / "frozen_execution_capsule.json"
    _require(capsule_path.is_file(), "PACK_GATE_NO_FROZEN_EXECUTION_CAPSULE:" + str(capsule_path))
    capsule_pin = ctrl.read_json(capsule_path)
    _require(release["test_suite_sha256"] == capsule_pin.get("test_suite_sha256"),
             "PACK_GATE_TEST_SUITE_NOT_CAPSULE_TEST_SUITE:"
             + str(release["test_suite_sha256"]) + "!="
             + str(capsule_pin.get("test_suite_sha256")))
    preamble_path, _history = ctrl.latest_evidence(
        CONTROL / "preambles" / (str(checks["authorized_round_run_id"]) + ".json"))
    _require(preamble_path.is_file(), "PACK_GATE_NO_ROUND_PREAMBLE:" + str(preamble_path))
    round_preamble = ctrl.read_json(preamble_path)
    _require(round_preamble.get("WORKSTATION_TEST_RELEASE_VERIFIED") is True,
             "PACK_GATE_ROUND_DID_NOT_PASS_WORKSTATION_TEST_GATE")
    _require(str(round_preamble.get("execution_capsule_sha256"))
             == str(capsule_pin.get("capsule_sha256")),
             "PACK_GATE_PREAMBLE_CAPSULE_MISMATCH")
    checks["workstation_test_release"] = {
        key: release[key] for key in (
            "receipt_sha256", "workflow_run_id", "workflow_receipt_sha256",
            "total_tests_recorded", "suite_count", "code_identity_sha256",
            "test_suite_sha256", "scenario_count", "camera_image_count")}
    entries = ctrl.read_json(PLAN)["entries"]
    task_results = {}
    for entry in entries:
        task_id = str(entry["task_id"])
        path = TASKS / task_id / "result.json"
        task_results[task_id] = _sha(path) if path.is_file() else None
    checks["task_result_count"] = sum(1 for value in task_results.values() if value)
    _require(checks["task_result_count"] == len(entries),
             "TASK_RESULTS_INCOMPLETE:" + str(checks["task_result_count"])
             + "/" + str(len(entries)))
    required = {
        "seal": OUT / "seal.json",
        "estimates_new": OUT / "estimates_new.json",
        "estimates_merge_reuse": OUT / "estimates_merge_reuse.json",
        "ledger": LEDGER,
        "status": OUT / "status.json",
        "manifest": OUT / "manifest.json",
        "verification": OUT / "verification.json",
        "isolation_receipt": JAIL / "00_isolation_receipt.json",
        "execution_truth_report": OUT / "00_execution_truth_report.md",
        "history_corrections": OUT / "history_corrections.md",
        "return_readme": OUT / "README_V168_RETURN.md",
        "controller_console_log": LOGS / "controller_run.log",
    }
    checks["required"] = {name: (str(path), path.is_file())
                          for name, path in required.items()}
    missing = [name for name, (_p, present) in checks["required"].items() if not present]
    _require(not missing, "PACK_GATE_MISSING:" + ",".join(missing))
    validator = sorted((OUT / "validator_only").glob("*.json"))
    _require(bool(validator), "PACK_GATE_NO_VALIDATOR_OUTPUT")
    checks["validator_outputs"] = [path.name for path in validator]
    seal = ctrl.read_json(OUT / "seal.json")
    checks["seal_status"] = seal.get("status")
    _require(seal.get("status") == "SEALED_BEFORE_VALIDATOR",
             "PACK_GATE_SEAL_NOT_SEALED_BEFORE_VALIDATOR:" + str(seal.get("status")))
    return checks


def _mapping_source_paths(document: Any, *, found: set[str] | None = None) -> list[Path]:
    """Every V166 file the controller itself names as a source it read.

    The provenance set is taken from the published mapping rather than from a list I
    could quietly forget to update, so the package carries what the round really used.
    """
    hits: set[str] = found if found is not None else set()
    if isinstance(document, dict):
        for value in document.values():
            _mapping_source_paths(value, found=hits)
    elif isinstance(document, list):
        for value in document:
            _mapping_source_paths(value, found=hits)
    elif isinstance(document, str):
        text = document.replace("\\", "/")
        # The V166 tree and the frozen V163 legal records are both read into a jail, so
        # both are provenance the package has to carry.
        marker = next((tag for tag in ("results/v166/", "results/v163/") if tag in text),
                      None)
        if marker and Path(text).suffix in {".json", ".sqlite", ".csv", ".h5", ".npy", ".png"}:
            tail = text[text.index(marker):]
            for candidate in (ROOT / tail, Path(tail)):
                if candidate.is_file():
                    hits.add(candidate.resolve().as_posix())
                    break
    return sorted(Path(item) for item in hits)


def _collect_members(*, rehearsal: bool) -> tuple[list[tuple[Path, str]], list[str]]:
    """Build the (host file, arcname) list and report any required file that is absent."""
    members: list[tuple[Path, str]] = []
    missing: list[str] = []
    added: set[str] = set()

    def add(path: Path, arcname: str) -> None:
        """Register one member; an arcname already claimed is not claimed twice."""
        if arcname in added:
            return
        if path.is_file():
            added.add(arcname)
            members.append((path, arcname))
        else:
            missing.append(arcname)

    readme = OUT / "README_V168_RETURN.md"
    if rehearsal:
        # A rehearsal has no report yet; the packer still has to exercise the root file.
        readme = None
    contract = _contract_file()

    for directory, arc_prefix in ((TOOLS, "code/tools/v168/"),
                                  (BUNDLE, "code/tools/v168_bundle/")):
        for path in sorted(directory.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts \
                    or ".pytest_cache" in path.parts:
                continue
            if path.suffix not in {".py", ".json", ".md", ".csv", ".txt"}:
                continue
            add(path, arc_prefix + path.relative_to(directory).as_posix())
    add(V165_STORE, "code/tools/v165_bundle/code/v152_budget_store.py")
    if not rehearsal:
        add(readme, "README_V168_RETURN.md")
    add(contract, "contract/" + contract.name)
    add(LEDGER, "deliverables/budget/v168_budget.sqlite")

    # The V168 result tree, minus the package itself and the receipts written after it.
    for path in sorted(OUT.rglob("*")):
        if not path.is_file():
            continue
        name = path.name
        if name.endswith(".zip") or name.endswith(".zip.sha256"):
            continue
        if name in {"README_V168_RETURN.md", "return_package_receipt.json"}:
            continue
        add(path, "results/v168/" + path.relative_to(OUT).as_posix())
    for path in sorted(PREPARED.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        if path.suffix == ".zip":
            continue
        add(path, "results/v168_prepared/" + path.relative_to(PREPARED).as_posix())

    # V166 provenance: pinned inputs, the tables and reports V168 was scored against,
    # the four group source documents, and the task trees the plan and mapping name.
    for rel in ("estimates.json", "estimates.sha256", "starts_by_group.json",
                "frozen_detections.json", "preflight.json", "seal.json",
                "source_lock.json", "verification.json", "history_forensics.json",
                "execute_status.json", "estimator_guard.json", "p2_gate_a_isolation_check.json",
                "fits_all.json", "height_input/height_readings.json",
                "logs/v165_budget.sqlite", "iscat_v166_return_001.zip.sha256",
                "preflight/gate_a_receipt.json", "preflight/gate_a_projection.json",
                "validator_only/gate_a_003/full_report.json",
                "validator_only/gate_a_003/gate_a_receipt.json",
                "p5_report/execution_authenticity.json",
                "p5_report/unified_task_table.json", "p5_report/unified_task_table.csv",
                "p5_report/per_start_results.json", "p5_report/budget_summary.json",
                "p5_report/provenance_scenarios_and_images.json",
                "p5_report/package_publish_receipt.json"):
        add(V166 / rel, "provenance/v166/" + rel)
    for group in common.GROUPS:
        add(V166 / "source_context" / (group + ".json"),
            "provenance/v166/source_context/" + group + ".json")
    # The six frozen legal starts per group are copied verbatim into every jail of that
    # group, so the files behind them are provenance the package must carry.
    for group in common.GROUPS:
        for path in sorted((ROOT / "results" / "v163" / "rescored")
                           .glob("100000_" + group + "_*.json")):
            add(path, "provenance/v163/rescored/" + path.name)
    named = _mapping_source_paths(ctrl.read_json(CONTROL / "source_mapping.json")) \
        if (CONTROL / "source_mapping.json").is_file() else []
    sources = list(ctrl.R_SOURCES) + list(ctrl.B_SOURCES)
    for task_id in sources:
        tree = V166 / "tasks" / task_id
        if tree.is_dir():
            for item in sorted(tree.rglob("*")):
                if item.is_file():
                    add(item, "provenance/v166/tasks/" + task_id + "/"
                        + item.relative_to(tree).as_posix())
        else:
            missing.append("provenance/v166/tasks/" + task_id)
    for path in named:
        rel = path.relative_to(ROOT).as_posix()
        tail = rel[rel.index("results/") + len("results/"):]
        add(path, "provenance/" + tail)
    return members, sorted(set(missing))


def _build_package(*, rehearsal: bool) -> dict[str, Any]:
    """Write the unique ZIP, its external SHA sidecar and the two closing receipts."""
    destination_dir = REHEARSAL_DIR if rehearsal else OUT
    name = ("iscat_v168_rehearsal_" + _utc() + ".zip") if rehearsal else ZIP_NAME
    zip_path = destination_dir / name
    destination_dir.mkdir(parents=True, exist_ok=True)
    _require(not zip_path.exists(), "PACKAGE_ALREADY_EXISTS:" + str(zip_path))
    gate = _pack_gate() if not rehearsal else {"skipped": "rehearsal"}
    members, missing = _collect_members(rehearsal=rehearsal)
    if rehearsal:
        # A rehearsal exercises the packer against a tree that has not run yet, so the
        # ledger and the task trees the authorized round has not produced are legitimately
        # absent.  They are reported here and in the receipt; only a real pack refuses.
        print("REHEARSAL_MISSING_MEMBERS " + json.dumps(missing), flush=True)
    else:
        _require(not missing, "PACKAGE_MEMBERS_MISSING:" + json.dumps(missing[:20]))
    arcs = [arc for _p, arc in members]
    _require(len(arcs) == len(set(arcs)), "DUPLICATE_ARCNAME")
    for arc in arcs:
        _require(not arc.startswith(("/", "..")) and ".." not in Path(arc).parts,
                 "UNSAFE_ARCNAME:" + arc)
    members.sort(key=lambda item: item[1])
    root_files = [item for item in members if item[1].startswith("results/v168/")]
    rows = [{"arcname": arc, "sha256": _sha(path), "bytes": path.stat().st_size}
            for path, arc in members]
    csv_text = CSV_HEADER + "\n" + "".join(
        row["sha256"] + "," + str(row["bytes"]) + "," + row["arcname"] + "\n"
        for row in rows)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9, allowZip64=True) as archive:
        for path, arc in members:
            archive.write(path, arc)
        archive.writestr("ZIP_CONTENTS_SHA256.csv", csv_text)
    # testzip() reads the central directory, which does not exist while the archive is
    # still open for writing, so the CRC pass runs on the finished bytes.
    with zipfile.ZipFile(zip_path) as archive:
        bad = archive.testzip()
    _require(bad is None, "ZIP_CRC_FAILURE:" + str(bad))

    zip_sha = _sha(zip_path)
    sidecar = zip_path.parent / (zip_path.name + ".sha256")
    _write_new(sidecar, zip_sha + "  " + zip_path.name + "\n")

    tree_now = {("results/v168/" + path.relative_to(OUT).as_posix()): path
                for path in OUT.rglob("*") if path.is_file()}
    controller_manifest = OUT / "manifest.json"
    receipt = {
        "schema": "iscat168.return_package_receipt.1",
        "rehearsal": rehearsal, "utc": _utc(),
        "run_id": gate.get("step_sequence_run_id") if not rehearsal else None,
        "archive": str(zip_path.relative_to(ROOT)).replace("\\", "/"),
        "zip_sha256": zip_sha, "zip_bytes": zip_path.stat().st_size,
        "member_count_including_contents_csv": len(members) + 1,
        "member_count_listed_in_csv": len(rows),
        "uncompressed_bytes_of_listed_members": sum(row["bytes"] for row in rows),
        "contents_csv_header": CSV_HEADER,
        "contents_csv_lists_itself": False,
        "sidecar_path": str(sidecar.relative_to(ROOT)).replace("\\", "/"),
        "sidecar_sha256": _sha(sidecar),
        "why_the_zip_has_no_digest_of_itself": (
            "a ZIP cannot contain the SHA-256 of its own bytes; the digest lives in the "
            "sidecar beside it and in the post-pack audit, both outside the archive"),
        "excluded_from_package": {
            "v166_return_zip": ("results/v166/iscat_v166_return_001.zip is not re-embedded; "
                                 "its SHA-256 and size are pinned in seal.json, "
                                 "verification.json and provenance/v166/"
                                 "iscat_v166_return_001.zip.sha256"),
            "this_receipt_and_audit": "written after the archive, disclosed by path here",
        },
        "results_v168_files_in_package": len(root_files),
        "results_v168_files_not_in_package": sorted(
            arc for arc in tree_now if arc not in {item[1] for item in members}),
        "controller_manifest_snapshot": {"path": "results/v168/manifest.json",
                                         "sha256": (_sha(controller_manifest)
                                                    if controller_manifest.is_file()
                                                    else None),
                                         "note": ("written by the controller manifest step "
                                                  "during the run; the package CSV is the "
                                                  "complete inventory of this archive")},
        "pack_gate": gate,
        "contract_pins": {rel: pinned for rel, pinned in sorted(ctrl.CONTRACT_PINS.items())},
    }
    if not rehearsal:
        _write_new(OUT / "return_package_receipt.json", _json_text(receipt))
    else:
        (destination_dir / "rehearsal_package_receipt.json").write_text(
            _json_text(receipt), encoding="utf-8")
    return receipt


def _audit_package(zip_path: Path, *, expected_sha: str | None) -> dict[str, Any]:
    """Re-open the finished archive and try to break it, from outside the controller."""
    findings: dict[str, Any] = {"schema": "iscat168.return_zip_verification.1",
                               "utc": _utc(), "archive": str(zip_path)}
    _require(zip_path.is_file(), "AUDIT_ARCHIVE_MISSING:" + str(zip_path))
    findings["zip_sha256"] = _sha(zip_path)
    findings["zip_bytes"] = zip_path.stat().st_size
    _require(expected_sha is None or findings["zip_sha256"] == expected_sha,
             "AUDIT_ZIP_SHA_DIFFERS_FROM_SIDECAR")
    with zipfile.ZipFile(zip_path) as archive:
        findings["crc_testzip_first_bad_member"] = archive.testzip()
        names = archive.namelist()
        findings["member_count"] = len(names)
        findings["unsafe_paths"] = [name for name in names
                                    if name.startswith(("/", "\\"))
                                    or ".." in Path(name).parts
                                    or Path(name).is_absolute()]
        csv_rows = {}
        with archive.open("ZIP_CONTENTS_SHA256.csv") as handle:
            for line in handle.read().decode("utf-8").splitlines()[1:]:
                digest, size, arc = line.split(",", 2)
                csv_rows[arc] = (digest, int(size))
        findings["csv_rows"] = len(csv_rows)
        findings["csv_missing_member_rows"] = sorted(set(names) - set(csv_rows)
                                                     - {"ZIP_CONTENTS_SHA256.csv"})
        findings["csv_rows_without_member"] = sorted(set(csv_rows) - set(names))
        mismatched: list[str] = []
        for arc, (digest, size) in sorted(csv_rows.items()):
            if arc not in names:
                continue
            with archive.open(arc) as handle:
                raw = handle.read()
            if hashlib.sha256(raw).hexdigest() != digest or len(raw) != size:
                mismatched.append(arc)
        findings["csv_digest_or_size_mismatches"] = mismatched
        # Input isolation, asserted on the published bytes rather than in memory.
        offenders: dict[str, list[str]] = {}
        jail_members = [name for name in names
                        if "/estimator_inputs/" in name and name.endswith(".json")]
        for name in jail_members:
            with archive.open(name) as handle:
                try:
                    document = json.loads(handle.read().decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
            problems = common.scan_forbidden(document, name)
            if problems:
                offenders[name] = problems
        findings["estimator_input_json_members_scanned"] = len(jail_members)
        findings["estimator_input_forbidden_key_offenders"] = offenders
        findings["sealed_truth_file_packaged"] = any(
            "v166_height_truth_sealed" in name for name in names)
        for arc in ("results/v168/seal.json", "results/v168/manifest.json",
                    "results/v168/verification.json", "results/v168/status.json",
                    "README_V168_RETURN.md", "contract/" + _contract_file().name):
            findings["present_" + Path(arc).name] = arc in names
    sidecar = zip_path.parent / (zip_path.name + ".sha256")
    findings["sidecar_matches"] = (sidecar.is_file()
                                   and findings["zip_sha256"]
                                   in sidecar.read_text(encoding="utf-8"))
    findings["on_disk_manifest_sha256"] = _sha(OUT / "manifest.json") \
        if (OUT / "manifest.json").is_file() else None
    findings["on_disk_verification_sha256"] = _sha(OUT / "verification.json") \
        if (OUT / "verification.json").is_file() else None
    findings["reportable_D"] = None
    findings["experimental_absolute_diameter_validated"] = False
    findings["model_calls"] = 0
    findings["meaning"] = ("mechanical acceptance of the archive only; it is not "
                           "independent scientific acceptance")
    return findings


def mode_pack(*, rehearsal: bool) -> int:
    pack_passes: dict[str, Any] = {"rehearsal": rehearsal}
    if not rehearsal:
        pack_passes["stable_console_log"] = _publish_stable_run_log()
        code = _spawn(_controller_argv(dry_run=False, steps=CLOSE_STEPS),
                      LOGS / ("controller_close_" + _utc() + ".log"))
        _require(code == 0, "CLOSING_EVIDENCE_PASS_FAILED_EXIT_" + str(code))
        pack_passes["closing_pass_steps"] = CLOSE_STEPS
        pack_passes["closing_pass_exit_code"] = code
    receipt = _build_package(rehearsal=rehearsal)
    zip_path = ROOT / receipt["archive"]
    findings = _audit_package(zip_path, expected_sha=receipt["zip_sha256"])
    findings["pack_passes"] = pack_passes
    findings["package_receipt_sha256"] = (_sha(OUT / "return_package_receipt.json")
                                          if not rehearsal else None)
    findings["audit_is_last_byte"] = True
    findings_path = (REHEARSAL_DIR / "rehearsal_zip_verification.json" if rehearsal
                     else OUT / "audit" / "v168_return_zip_verification.json")
    if rehearsal:
        findings_path.write_text(_json_text(findings), encoding="utf-8")
    else:
        _write_new(findings_path, _json_text(findings))
    print(_json_text({"zip_sha256": findings["zip_sha256"],
                      "zip_bytes": findings["zip_bytes"],
                      "member_count": findings["member_count"],
                      "crc_bad_member": findings["crc_testzip_first_bad_member"],
                      "unsafe_paths": findings["unsafe_paths"],
                      "csv_mismatches": findings["csv_digest_or_size_mismatches"],
                      "isolation_offenders":
                          findings["estimator_input_forbidden_key_offenders"],
                      "pack_passes": pack_passes,
                      "audit": str(findings_path)}))
    clean = (not findings["unsafe_paths"]
             and findings["crc_testzip_first_bad_member"] is None
             and not findings["csv_digest_or_size_mismatches"]
             and not findings["csv_missing_member_rows"]
             and not findings["csv_rows_without_member"]
             and not findings["estimator_input_forbidden_key_offenders"])
    print(("PACK_AUDIT_CLEAN " if clean else "PACK_AUDIT_FINDINGS ")
          + receipt["archive"])
    return 0 if clean else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_all", description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--plan", action="store_true")
    group.add_argument("--workstation-tests", action="store_true")
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--freeze-capsule", action="store_true",
                       help=("contract 4.2: freeze the execution capsule after the commit "
                             "and the workstation test release, before any run identity"))
    group.add_argument("--run", action="store_true")
    group.add_argument("--pack", action="store_true")
    group.add_argument("--pack-rehearsal", action="store_true")
    group.add_argument("--status", action="store_true")
    parser.add_argument("--run-id", default="full_004",
                        help="workstation test run id; evidence directories are append-only")
    args = parser.parse_args(argv)
    try:
        if args.plan:
            return mode_plan()
        if args.workstation_tests:
            return mode_workstation_tests(args.run_id)
        if args.dry_run:
            return mode_dry_run()
        if args.freeze_capsule:
            return mode_freeze_capsule()
        if args.run:
            return mode_run()
        if args.pack:
            return mode_pack(rehearsal=False)
        if args.pack_rehearsal:
            return mode_pack(rehearsal=True)
        return mode_status()
    except (ValueError, FileExistsError) as exc:
        print(str(exc), file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
