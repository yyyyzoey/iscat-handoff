"""Run the three V168 test inventories and bind their raw evidence to one receipt.

Contract section 3.3 asks for the complete production nodeid list, the per-phase
outcomes of three separate suites, the original command and output, and the source
hashes the run was bound to.  No pass count is written here: every number in the
receipt is parsed back out of the JUnit XML, the outcomes JSON or the collector
output after the subprocess has finished, so the receipt cannot claim a green suite
that never happened.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools" / "v168"
BUNDLE = ROOT / "tools" / "v168_bundle"
V165 = ROOT / "tools" / "v165_bundle"
OUT = ROOT / "results" / "v168"
LEDGER = OUT / "logs" / "v168_budget.sqlite"
V168_TASKS = OUT / "tasks"
PLUGIN_DIR = str(V165 / "code")

SUITE_ENV = {
    "OPENBLAS_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
}


def _sha(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _source_hashes() -> dict:
    """Hash every code byte the three inventories are allowed to read."""
    paths: list[Path] = []
    for folder, patterns in (
        (TOOLS, ("*.py",)),
        (TOOLS / "tests", ("test_*.py", "conftest.py")),
        (BUNDLE / "code", ("*.py",)),
        (BUNDLE / "approved_core", ("*.py",)),
        (BUNDLE / "tests", ("test_*.py",)),
        (BUNDLE / "config", ("*.json",)),
    ):
        for pattern in patterns:
            paths.extend(sorted(folder.glob(pattern)))
    for extra in (BUNDLE / "manifest_sha256.csv", V165 / "test_inventory.json",
                  V165 / "run_workstation_tests.py", Path(__file__).resolve()):
        paths.append(extra)
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        raise FileNotFoundError("SOURCETREE_INCOMPLETE:" + ";".join(missing))
    return {p.relative_to(ROOT).as_posix(): _sha(p) for p in paths}


def _budget_state() -> dict:
    """Charge evidence for the zero-charge proof, read without touching the ledger.

    Two situations have to be told apart.  Before the authorized round starts there is
    no round ledger at all, so an absent tree is the strongest proof that no test billed
    anything.  Once the round has opened its ledger that proof is no longer available,
    and the only honest statement left is a differential one: every charge, attempt and
    byte of the ledger has to come back identical after the suites.  The digest below is
    taken through a read-only connection so the evidence itself cannot be written by the
    run that is collecting it.
    """
    return {
        "ledger_path": str(LEDGER),
        "ledger_exists": LEDGER.is_file(),
        "ledger_sha256": _sha(LEDGER),
        "primary_task_dirs": len(list(V168_TASKS.iterdir())) if V168_TASKS.is_dir() else 0,
        "estimates_new_exists": (OUT / "estimates_new.json").is_file(),
        "seal_exists": (OUT / "seal.json").is_file(),
        "charge_digest": _charge_digest(),
    }


def _charge_digest() -> dict:
    """Every reserved task and every attempt row in the round ledger, as one digest."""
    if not LEDGER.is_file():
        return {"ledger_absent": True}
    connection = sqlite3.connect(LEDGER.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        tasks = connection.execute(
            "SELECT id, used, state FROM tasks ORDER BY id").fetchall()
        attempts = connection.execute(
            "SELECT task, seq, state FROM attempts ORDER BY task, seq").fetchall()
    finally:
        connection.close()
    encoded = json.dumps([tasks, attempts], sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return {
        "ledger_absent": False,
        "reserved_tasks": len(tasks),
        "calls_charged": sum(int(row[1]) for row in tasks),
        "attempt_rows": len(attempts),
        "attempts_open_charged": sum(1 for row in attempts if row[2] == "CHARGED"),
        "charge_digest_sha256": hashlib.sha256(encoded).hexdigest(),
    }


# The fields a test run must leave exactly as it found them once a ledger exists.
BUDGET_CORE_KEYS = ("ledger_sha256", "primary_task_dirs", "estimates_new_exists",
                    "seal_exists", "charge_digest")


def _budget_unchanged(before: dict, after: dict) -> bool:
    return all(before.get(key) == after.get(key) for key in BUDGET_CORE_KEYS)


def _run(command: list[str], cwd: Path, env: dict, suite_dir: Path, stem: str) -> dict:
    process = subprocess.run(command, cwd=str(cwd), env=env, capture_output=True)
    streams = {"stdout": process.stdout, "stderr": process.stderr}
    for name, raw in streams.items():
        (suite_dir / f"{stem}.{name}.txt").write_bytes(raw)
    return {
        "command": command,
        "cwd": str(cwd),
        "returncode": int(process.returncode),
        "python": sys.executable,
        "python_version": sys.version.split()[0],
        f"{stem}_sha256": {name: hashlib.sha256(raw).hexdigest() for name, raw in streams.items()},
        "captured_utc": _utc(),
    }


def _collect(env: dict, cwd: Path, target: str, suite_dir: Path) -> dict:
    # One -q gives the nodeid list; a second one collapses it to per-file counts, which
    # is not the inventory the contract asks for.
    base = [sys.executable, "-m", "pytest", "--collect-only", "-q"]
    record = _run(base + [target], cwd, env, suite_dir, "collect_only")
    raw = (suite_dir / "collect_only.stdout.txt").read_text(encoding="utf-8", errors="replace")
    nodeids = [line.strip() for line in raw.splitlines() if "::" in line]
    (suite_dir / "nodeids.txt").write_text("\n".join(sorted(nodeids)) + "\n", encoding="utf-8")
    record.update({"collected_nodeids": len(nodeids),
                   "nodeids_sha256": _sha(suite_dir / "nodeids.txt"),
                   "collection_failed": record["returncode"] != 0})
    return record


def _junit_counts(path: Path) -> dict:
    if not path.is_file():
        return {"junit_present": False}
    root = ET.parse(path).getroot()
    suites = list(root.iter("testsuite"))
    return {
        "junit_present": True,
        "junit_sha256": _sha(path),
        "tests": sum(int(item.get("tests", 0)) for item in suites),
        "failures": sum(int(item.get("failures", 0)) for item in suites),
        "errors": sum(int(item.get("errors", 0)) for item in suites),
        "skipped": sum(int(item.get("skipped", 0)) for item in suites),
        "phase_records": len(list(root.iter("testcase"))),
    }


def _outcome_counts(path: Path) -> dict:
    """Read whichever outcomes schema the suite actually produced, without assuming."""
    if not path.is_file():
        return {"outcomes_present": False}
    document = json.loads(path.read_text(encoding="utf-8-sig"))
    if "counts" in document:
        phases = {when: sum(1 for row in document["tests"]
                            if row["phases"].get(when, {}).get("outcome") == "passed")
                  for when in ("setup", "call", "teardown")}
        payload = {"schema": document["schema"], "exitstatus": document["exitstatus"],
                   "tests": len(document["tests"]), "final_outcomes": document["counts"],
                   "phase_pass_records": phases}
    else:
        reports = document["reports"]
        payload = {"schema": "v165_receipt_plugin", "exitstatus": document["exitstatus"],
                   "collected": len(document["collected"]),
                   "collection_errors": len(document["collection_errors"]),
                   "phase_reports": len(reports),
                   "reported_nodeids": len({row["nodeid"] for row in reports}),
                   "phase_pass_records": {when: sum(1 for row in reports if row["when"] == when
                                                    and row["outcome"] == "passed")
                                          for when in ("setup", "call", "teardown")}}
    payload.update({"outcomes_present": True, "outcomes_sha256": _sha(path)})
    return payload


def _tripwire(path: Path) -> dict:
    """Count loader reaches from the file the tripwire fixture appends to.

    An absent file, or a file holding only the zero marker the fixture writes when no
    attempt happened, both mean zero real constructions.  A line naming an attempt is
    reported as a failure instead of being smoothed over.
    """
    if not path.is_file():
        return {"file": path.name, "exists": False, "records": 0, "record_types": [],
                "real_construction_attempts": 0, "zero_marker_written": False}
    lines = [line for line in path.read_text(encoding="ascii", errors="replace").splitlines()
             if line.strip()]
    return {"file": path.name, "exists": True, "path": str(path), "records": len(lines),
            "sha256": _sha(path), "record_types": sorted(set(lines)),
            "real_construction_attempts": sum(
                1 for line in lines if line.startswith("REAL_F2C_MODEL_CONSTRUCTION_ATTEMPT")),
            "zero_marker_written": any(line.startswith("ZERO_REAL_F2C") for line in lines)}


def _suite_env(outer: dict, outcomes: Path | None, tripwire: Path | None,
               *, recorder: str) -> dict:
    """Point exactly one outcome recorder at exactly one evidence file.

    The bundle suite has no conftest of its own, so it uses the shared V165 recorder
    plugin.  The V168 suite already records phases in its own conftest, and loading the
    plugin there too would put two writers on the same path, so each suite gets one
    recorder and one variable.
    """
    env = outer.copy()
    if recorder == "plugin":
        env["PYTHONPATH"] = PLUGIN_DIR + os.pathsep + env.get("PYTHONPATH", "")
    if outcomes is not None:
        name = "V165_PYTEST_OUTCOMES" if recorder == "plugin" else "V168_PYTEST_OUTCOMES"
        env[name] = str(outcomes)
    if tripwire is not None:
        env["V168_REAL_CALL_TRIPWIRE"] = str(tripwire)
    return env


def run_pytest_suite(name: str, cwd: Path, target: str, suite_dir: Path,
                     *, recorder: str, tripwire: bool) -> dict:
    suite_dir.mkdir(parents=True, exist_ok=True)
    outer = os.environ.copy()
    external_addopts = outer.pop("PYTEST_ADDOPTS", None)
    outer.update(SUITE_ENV)
    outcomes = suite_dir / "pytest_outcomes.json"
    wire = suite_dir / "real_f2c_tripwire.txt" if tripwire else None
    env = _suite_env(outer, outcomes, wire, recorder=recorder)
    command = [sys.executable, "-m", "pytest", "-q", "--junitxml",
               str(suite_dir / "junit.xml")]
    if recorder == "plugin":
        command += ["-p", "v165_receipt_plugin"]
    record = _run(command + [target], cwd, env, suite_dir, "run")
    record["suite"] = name
    record["outcome_recorder"] = recorder
    record["environment"] = {key: env.get(key) for key in sorted(SUITE_ENV)}
    record["external_pytest_addopts_ignored"] = external_addopts
    record.update(_junit_counts(suite_dir / "junit.xml"))
    record.update(_outcome_counts(outcomes))
    record["tripwire"] = _tripwire(wire) if wire else {"performed": False}
    record["collection"] = _collect(env, cwd, target, suite_dir)
    collection = record["collection"]
    # Contract 7: the release receipt has to find this suite's own evidence directory and
    # re-collect the same target, so both are recorded instead of being guessed later.
    record["suite_dir"] = suite_dir.relative_to(ROOT).as_posix()
    record["target"] = target
    collected = collection["collected_nodeids"]
    record["counts_reconcile"] = (record.get("tests") == collected
                                  and collection["collection_failed"] is False)
    record["all_green"] = (record["returncode"] == 0 and record.get("failures") == 0
                           and record.get("errors") == 0 and record.get("tests") == collected)
    return record


def run_inherited_v166_suite(suite_dir: Path) -> dict:
    """Hand the V166 inventory to the driver that already owns its receipt rules."""
    suite_dir.mkdir(parents=True, exist_ok=True)
    inner = suite_dir / "v165_driver"
    outer = os.environ.copy()
    outer.pop("PYTEST_ADDOPTS", None)
    outer.update(SUITE_ENV)
    command = [sys.executable, str(V165 / "run_workstation_tests.py"), "--out", str(inner)]
    record = _run(command, ROOT, outer, suite_dir, "v166_inherited")
    record["suite"] = "v166_inherited_41"
    receipt_path = inner / "test_receipt.json"
    outcomes_path = inner / "pytest_outcomes.json"
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
        counts = _outcome_counts(outcomes_path)
        # The inherited driver records one report row per phase, so the honest
        # reconciliation is collected items against distinct nodeids in its own file.
        reported = counts.get("reported_nodeids")
        record.update({"inherited_receipt_sha256": _sha(receipt_path),
                       "inherited_returncode": receipt.get("returncode"),
                       "inherited_real_f2c_calls": receipt.get("real_F2c_calls"),
                       "inherited_scope": receipt.get("scope"),
                       "inherited_outcomes": counts,
                       "tests": counts.get("collected"),
                       "counts_reconcile": (counts.get("collected") == reported
                                            and counts.get("collection_errors") == 0
                                            and receipt.get("returncode") == 0)})
    record["all_green"] = record["returncode"] == 0 and record.get("inherited_returncode") == 0
    record["suite_dir"] = suite_dir.relative_to(ROOT).as_posix()
    record["target"] = str(V165 / "run_workstation_tests.py")
    return record


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUT / "workstation_tests")
    parser.add_argument("--run-id", default="full_001")
    args = parser.parse_args(argv)
    root = args.out.resolve() / args.run_id
    if (root / "workstation_test_receipt.json").exists():
        raise FileExistsError("WORKSTATION_TESTS_ALREADY_RECORDED:" + str(root))
    root.mkdir(parents=True, exist_ok=True)

    before_hashes = _source_hashes()
    before_budget = _budget_state()
    suites = [
        run_inherited_v166_suite(root / "v166_inherited_41"),
        run_pytest_suite("bundle_plan_and_core", BUNDLE, "tests",
                         root / "bundle_local_38", recorder="plugin", tripwire=False),
        run_pytest_suite("v168_production", ROOT, "tools/v168/tests",
                         root / "v168_production_suite", recorder="conftest", tripwire=True),
    ]
    after_hashes = _source_hashes()
    after_budget = _budget_state()
    for index, record in enumerate(suites):
        path = root / f"suite_{index:02d}_receipt.json"
        path.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    wire = _tripwire(root / "v168_production_suite" / "real_f2c_tripwire.txt")
    # An absent ledger proves the suites billed nothing on its own; a live ledger has to
    # be proved by comparison, and a ledger that appears mid-run is a failure either way.
    ledger_present = bool(before_budget["ledger_exists"] or after_budget["ledger_exists"])
    ledger_opened_mid_run = (not before_budget["ledger_exists"]
                             and after_budget["ledger_exists"])
    budget_identical = _budget_unchanged(before_budget, after_budget)
    zero_charged = (not ledger_present) or (budget_identical and not ledger_opened_mid_run)
    receipt = {
        "schema": "iscat168.workstation_tests.1",
        "run_id": args.run_id,
        "utc": _utc(),
        "scope": ("LOCAL_TEST_INVENTORY_ONLY: synthetic forwards and plan guards, "
                  "NOT physical validation and NOT the authorized V168 fit"),
        "contract_reference": "section 3.3",
        "suites": suites,
        "total_tests_recorded": sum(int(record.get("tests") or 0) for record in suites),
        "all_suites_green": all(bool(record["all_green"]) for record in suites),
        "source_hashes_before": before_hashes,
        "source_hashes_after": after_hashes,
        "source_hashes_unchanged": before_hashes == after_hashes,
        "real_f2c_tripwire": wire,
        "budget_proof_mode": ("absent_ledger" if not ledger_present else
                              "differential_ledger_digest"),
        "budget_ledger_present": ledger_present,
        "budget_ledger_opened_mid_run": ledger_opened_mid_run,
        "budget_core_state_unchanged": budget_identical,
        "budget_state_before": before_budget,
        "budget_state_after": after_budget,
        "zero_charged_calls_proved": zero_charged,
        "suite_receipt_sha256": {f"suite_{index:02d}": _sha(root / f"suite_{index:02d}_receipt.json")
                                 for index in range(len(suites))},
    }
    (root / "workstation_test_receipt.json").write_text(
        json.dumps(receipt, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"run_id": args.run_id, "all_suites_green": receipt["all_suites_green"],
                      "per_suite": {record["suite"]: {"tests": record.get("tests"),
                                                      "returncode": record["returncode"],
                                                      "green": record["all_green"]}
                                    for record in suites},
                      "zero_charged_calls": receipt["zero_charged_calls_proved"],
                      "receipt": str(root / "workstation_test_receipt.json")}, indent=1))
    ok = (receipt["all_suites_green"] and receipt["source_hashes_unchanged"]
          and receipt["zero_charged_calls_proved"]
          and wire["real_construction_attempts"] == 0)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
