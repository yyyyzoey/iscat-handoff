"""Run the complete frozen-plus-workstation V165 test inventory."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "code"))

from v165_receipts import TRIPWIRE_FILE, hashes, tripwire_evidence, verify_receipt


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if (out / "test_receipt.json").exists():
        receipt = verify_receipt(ROOT, out)
        print(json.dumps({"reused_verified_receipt": True, "receipt": receipt}))
        return 0

    # The tripwire file is created only by tests that reach the real model loader.
    # It must start absent so the recorded count is evidence for this run alone.
    if (out / TRIPWIRE_FILE).exists():
        raise FileExistsError("TRIPWIRE_FILE_ALREADY_PRESENT_USE_A_NEW_OUT")

    before = hashes(ROOT)
    env = os.environ.copy()
    external_addopts = env.pop("PYTEST_ADDOPTS", None)
    env.update(
        {
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "PYTHONPATH": str(ROOT / "code"),
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "V165_PYTEST_OUTCOMES": str(out / "pytest_outcomes.json"),
            "V165_REAL_CALL_TRIPWIRE": str(out / TRIPWIRE_FILE),
        }
    )
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "v165_receipt_plugin",
        "tests",
    ]
    process = subprocess.run(command, cwd=ROOT, env=env, capture_output=True)
    raw_output = process.stdout + b"\n" + process.stderr
    (out / "test_output.txt").write_bytes(raw_output)
    after = hashes(ROOT)

    command_receipt = {
        "command": command,
        "cwd": str(ROOT),
        "environment_overrides": {
            key: env[key]
            for key in (
                "OPENBLAS_NUM_THREADS",
                "OMP_NUM_THREADS",
                "MKL_NUM_THREADS",
                "PYTHONPATH",
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
                "PYTHONDONTWRITEBYTECODE",
                "V165_PYTEST_OUTCOMES",
                "V165_REAL_CALL_TRIPWIRE",
            )
        },
        "external_pytest_addopts_ignored": external_addopts,
        "returncode": process.returncode,
    }
    (out / "command_receipt.json").write_text(
        json.dumps(command_receipt, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tripwire = tripwire_evidence(out)
    receipt = {
        "returncode": process.returncode,
        "scope": "COMPONENT_SYNTHETIC_FAULT_AND_ISOLATION_TESTS_NOT_PHYSICAL_VALIDATION",
        "command": command,
        "cwd": str(ROOT),
        "python": sys.executable,
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "external_pytest_addopts_ignored": external_addopts,
        "hashes": after,
        "before": before,
        "real_F2c_calls": tripwire["records"],
        "real_f2c_tripwire": tripwire,
        "output_sha256": _sha(out / "test_output.txt"),
        "outcomes_sha256": _sha(out / "pytest_outcomes.json"),
        "command_receipt_sha256": _sha(out / "command_receipt.json"),
    }
    (out / "test_receipt.json").write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(raw_output.decode(errors="replace"))
    if process.returncode != 0 or before != after:
        return 2
    verify_receipt(ROOT, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

