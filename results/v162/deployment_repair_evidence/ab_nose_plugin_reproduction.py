"""V162 deployment-repair evidence: A/B reproduction of the pytest legacy-nose conflict.

Runs the SAME frozen test file with the SAME argv shape as run_workstation_tests.py and
varies ONLY PYTEST_ADDOPTS. Writes raw stdout/stderr bytes, hashes and a JSON summary.
No science/model call, no receipt is produced or edited by this script.
"""
from __future__ import annotations
import hashlib, json, os, subprocess, sys
from pathlib import Path
import pytest

ROOT = Path(r"C:\iscat\v162\tools\v162_bundle")
OUT = Path(r"C:\iscat\v162\results\v162\deployment_repair_evidence")
PY = sys.executable
TAIL = ["-m", "pytest", "-q", "-p", "v162_receipt_plugin", "tests/test_v162.py"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def outcome_counts(path: Path) -> dict:
    d = json.loads(path.read_text(encoding="utf-8"))
    rep = d["reports"]
    return dict(
        collected=len(d["collected"]),
        exitstatus=d["exitstatus"],
        collection_errors=len(d["collection_errors"]),
        setup_errors=sum(1 for r in rep if r["when"] == "setup" and r["outcome"] == "error"),
        call_failed=sum(1 for r in rep if r["when"] == "call" and r["outcome"] == "failed"),
        call_passed=sum(1 for r in rep if r["when"] == "call" and r["outcome"] == "passed"),
        teardown_passed=sum(1 for r in rep if r["when"] == "teardown" and r["outcome"] == "passed"),
    )


def run(label: str, addopts):
    out_json = OUT / f"focal_{label}_outcomes.json"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "code")
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["V162_PYTEST_OUTCOMES"] = str(out_json)
    if addopts is None:
        env.pop("PYTEST_ADDOPTS", None)
    else:
        env["PYTEST_ADDOPTS"] = addopts
    p = subprocess.run([PY, *TAIL], cwd=ROOT, env=env, capture_output=True)
    raw = p.stdout + b"\n" + p.stderr
    outp = OUT / f"focal_{label}_output.txt"
    outp.write_bytes(raw)
    return dict(
        label=label,
        PYTEST_ADDOPTS=addopts,
        command=[PY, *TAIL],
        cwd=str(ROOT),
        env={"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1",
             "V162_PYTEST_OUTCOMES": str(out_json), "PYTEST_ADDOPTS": addopts},
        returncode=p.returncode,
        output_file=outp.name,
        output_sha256=sha(outp),
        outcomes_file=out_json.name,
        outcomes=outcome_counts(out_json) if out_json.exists() else None,
        output_tail=raw.decode("utf-8", "replace")[-400:],
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    testfile = ROOT / "tests/test_v162.py"
    summary = dict(
        purpose=("A/B reproduction: pytest 7.x builtin deprecated 'nose' plugin treats the "
                 "module-level helper `def setup(theta=None)` in tests/test_v162.py as a nose "
                 "setup convention and calls setup(<module>)."),
        frozen_test_file=str(testfile),
        frozen_test_file_sha256=sha(testfile),
        interpreter=sys.version,
        station_pytest_version=pytest.__version__,
        station_pytest_nose_module=__import__("_pytest.nose", fromlist=["x"]).__file__,
        station_nose_in_default_plugins="nose" in __import__("_pytest.config", fromlist=["x"]).default_plugins,
        note="Focal scope (tests/test_v162.py only). Not a substitute for the official 222-node receipt.",
        results=[],
    )
    summary["results"].append(run("without_optout", None))
    summary["results"].append(run("with_no_nose_optout", "-p no:nose"))
    (OUT / "ab_nose_plugin_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    for r in summary["results"]:
        print(f"[{r['label']}] returncode={r['returncode']} outcomes={r['outcomes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
