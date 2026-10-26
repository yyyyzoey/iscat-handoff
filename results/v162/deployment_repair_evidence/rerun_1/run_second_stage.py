"""V162 resume: run the launcher's own second stage under the documented deployment repair.

Logging wrapper only. It does not change the approved command line, the bundle bytes,
the science, the budget or any gate. Raw stdout/stderr are written byte-for-byte.

Usage: python run_second_stage.py <attempt-label>
"""
import datetime, hashlib, json, os, pathlib, subprocess, sys

ROOT = pathlib.Path(r"C:\iscat\v162")
OUT = ROOT / "results/v162/deployment_repair_evidence/rerun_1"


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main(attempt):
    OUT.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(ROOT / "tools/v162_bundle/run_all.py"), "--repo", str(ROOT)]
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTEST_ADDOPTS"] = "-p no:nose"
    so = OUT / f"{attempt}_run_all.stdout"
    se = OUT / f"{attempt}_run_all.stderr"
    started = utc()
    with so.open("wb") as fo, se.open("wb") as fe:
        proc = subprocess.Popen(cmd, cwd=str(ROOT), env=env, stdout=fo, stderr=fe)
        while True:
            try:
                rc = proc.wait(timeout=60)
                break
            except subprocess.TimeoutExpired:
                print(f"[heartbeat] {utc()} run_all still running (pid {proc.pid})", flush=True)
    ended = utc()
    rec = dict(
        stage="run_all_resume",
        attempt=attempt,
        command=cmd,
        cwd=str(ROOT),
        environment={k: env.get(k) for k in ("PYTEST_ADDOPTS", "PYTHONDONTWRITEBYTECODE", "PYTHONPATH")},
        returncode=rc,
        started_utc=started,
        ended_utc=ended,
        stdout=str(so.relative_to(ROOT)),
        stderr=str(se.relative_to(ROOT)),
        stdout_bytes=so.stat().st_size,
        stderr_bytes=se.stat().st_size,
        stdout_sha256=hashlib.sha256(so.read_bytes()).hexdigest(),
        stderr_sha256=hashlib.sha256(se.read_bytes()).hexdigest(),
        note=(
            "A returned process is not scientific acceptance. Read results/v162/status.json, "
            "verification.json, execution_integrity.json and the per-stage logs."
        ),
    )
    (OUT / f"{attempt}_run_all.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    print("---- run_all stdout ----")
    sys.stdout.write(so.read_text(encoding="utf-8", errors="replace"))
    print("---- run_all stderr ----")
    sys.stdout.write(se.read_text(encoding="utf-8", errors="replace"))
    print("RESUME_RUN_ALL_RETURNCODE", rc)
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "attempt1"))
