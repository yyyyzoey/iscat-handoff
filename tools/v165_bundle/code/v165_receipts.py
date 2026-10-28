"""Hash-bound V165 test receipts generated from actual pytest outcomes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

TRIPWIRE_FILE = "real_f2c_tripwire.txt"


def hashes(root):
    root = Path(root).resolve()
    paths = []
    for folder, pattern in (
        ("code", "*.py"),
        ("tests", "test_*.py"),
        # conftest carries the real-F2c tripwire fixture, so it must be hash-bound
        # exactly like the test modules it protects.
        ("tests", "conftest.py"),
        ("config", "*.json"),
        ("generator", "*.py"),
        ("validator", "*.py"),
    ):
        paths.extend(sorted((root / folder).glob(pattern)))
    for name in (
        "manifest_sha256.csv",
        "run_all.py",
        "run_workstation_tests.py",
        "test_inventory.json",
    ):
        paths.append(root / name)
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in paths
    }


def tripwire_evidence(folder):
    """Count real F2c loader reaches from the tripwire file the tests append to.

    Absent file means zero; a present file is counted from its own bytes so the
    receipt can never claim zero by hardcoding.
    """
    path = Path(folder) / TRIPWIRE_FILE
    if not path.is_file():
        return {
            "file": TRIPWIRE_FILE,
            "path": str(path),
            "exists": False,
            "records": 0,
            "bytes": 0,
            "sha256": None,
            "record_types": [],
        }
    raw = path.read_bytes()
    records = [line for line in raw.decode("ascii", errors="replace").splitlines() if line.strip()]
    return {
        "file": TRIPWIRE_FILE,
        "path": str(path),
        "exists": True,
        "records": len(records),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "record_types": sorted(set(records)),
    }


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def verify_receipt(root, folder):
    root = Path(root).resolve()
    folder = Path(folder).resolve()
    receipt = _read(folder / "test_receipt.json")
    outcomes = _read(folder / "pytest_outcomes.json")
    inventory = _read(root / "test_inventory.json")
    if receipt.get("scope") != (
        "COMPONENT_SYNTHETIC_FAULT_AND_ISOLATION_TESTS_NOT_PHYSICAL_VALIDATION"
    ):
        raise ValueError("TEST_SCOPE_CHANGED")
    if receipt.get("returncode") != 0:
        raise ValueError("TEST_RETURN_CODE")
    if Path(receipt.get("cwd", "")).resolve() != root:
        raise ValueError("WRONG_TEST_ROOT")
    expected_command = [
        receipt.get("python"),
        "-m",
        "pytest",
        "-q",
        "-p",
        "v165_receipt_plugin",
        "tests",
    ]
    if receipt.get("command") != expected_command:
        raise ValueError("WRONG_TEST_COMMAND")
    if receipt.get("hashes") != hashes(root) or receipt.get("before") != receipt.get("hashes"):
        raise ValueError("TESTED_FILES_CHANGED")
    expected_nodes = inventory.get("nodeids")
    if not isinstance(expected_nodes, list) or len(expected_nodes) != len(set(expected_nodes)):
        raise ValueError("BAD_TEST_INVENTORY")
    if sorted(outcomes.get("collected", [])) != sorted(expected_nodes):
        raise ValueError("COLLECTED_TEST_SET_CHANGED")
    if outcomes.get("collection_errors") or outcomes.get("exitstatus") != 0:
        raise ValueError("TEST_COLLECTION_OR_EXECUTION_FAILED")
    reports = outcomes.get("reports", [])
    if len(reports) != 3 * len(expected_nodes):
        raise ValueError("TEST_REPORT_COUNT")
    for node in expected_nodes:
        rows = [row for row in reports if row.get("nodeid") == node]
        phases = {(row.get("when"), row.get("outcome")) for row in rows}
        if len(rows) != 3 or phases != {
            ("setup", "passed"),
            ("call", "passed"),
            ("teardown", "passed"),
        }:
            raise ValueError("INCOMPLETE_TEST:" + node)
    for key, name in (
        ("outcomes_sha256", "pytest_outcomes.json"),
        ("output_sha256", "test_output.txt"),
        ("command_receipt_sha256", "command_receipt.json"),
    ):
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != receipt.get(key):
            raise ValueError("TEST_RECEIPT_FILE_CHANGED:" + name)
    # The zero-call claim must come from the tripwire file, never from a literal.
    evidence = tripwire_evidence(folder)
    if receipt.get("real_f2c_tripwire") != evidence:
        raise ValueError("REAL_F2C_TRIPWIRE_EVIDENCE_MISMATCH")
    if receipt.get("real_F2c_calls") != evidence["records"]:
        raise ValueError("REAL_F2C_CALL_COUNT_NOT_BOUND_TO_TRIPWIRE")
    if receipt.get("real_F2c_calls") != 0:
        raise ValueError("SOFTWARE_TESTS_MUST_NOT_CALL_REAL_F2C")
    return receipt

