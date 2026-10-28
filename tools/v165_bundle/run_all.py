"""Fixed V165 stage order through the real production entrypoint.

Newly authored for V166 (the V165 workstation original was NOT_FOUND in P0).
Each stage runs as its own subprocess, its output is archived, and the first
non-zero or blocked stage stops the run. Nothing is retried automatically and
no stage input is invented: a missing Gate A projection, Gate A receipt or
height-reading file blocks that stage instead of substituting a placeholder.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "code/v165_run.py"
STAGES = ("preflight", "execute", "seal-estimates", "verify")


def _write(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--projection", type=Path)
    parser.add_argument("--gate-receipt", type=Path)
    parser.add_argument("--readings", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)

    repo = args.repo.resolve()
    if ROOT != repo / "tools/v165_bundle":
        raise ValueError("WRONG_INSTALLATION")
    out = (args.out or repo / "results/v166").resolve()
    logs = out / "logs"
    logs.mkdir(parents=True, exist_ok=True)

    stage_inputs = {"preflight": (args.projection, args.gate_receipt), "execute": (args.readings,)}
    commands: list[tuple[str, tuple, list[str]]] = [
        (
            "tests",
            (),
            [
                sys.executable,
                str(ROOT / "run_workstation_tests.py"),
                "--out",
                str(out / "workstation_tests/production_001"),
            ],
        )
    ]
    for mode in STAGES:
        command = [sys.executable, str(RUNNER), mode, "--repo", str(repo), "--out", str(out)]
        if mode == "preflight":
            command += [
                "--projection",
                str(args.projection),
                "--gate-receipt",
                str(args.gate_receipt),
            ]
        elif mode == "execute":
            command += ["--readings", str(args.readings)]
        if args.resume:
            command.append("--resume")
        commands.append((mode, stage_inputs.get(mode, ()), command))

    run_id = uuid.uuid4().hex
    manifest_path = logs / f"{run_id}_stage_commands.json"
    receipts: list[dict] = []
    for stage, required_inputs, command in commands:
        missing = [str(p) for p in required_inputs if p is None or not Path(p).is_file()]
        if missing:
            receipts.append(
                {
                    "stage": stage,
                    "command": command,
                    "status": "BLOCKED_MISSING_INPUT",
                    "missing_inputs": missing,
                    "returncode": None,
                }
            )
            _write(manifest_path, {"run_id": run_id, "stages": receipts})
            print(stage, "BLOCKED_MISSING_INPUT", missing, flush=True)
            return 3
        process = subprocess.run(command, cwd=repo, capture_output=True)
        name = f"{run_id}_{stage}"
        (logs / f"{name}.stdout").write_bytes(process.stdout)
        (logs / f"{name}.stderr").write_bytes(process.stderr)
        receipts.append(
            {
                "stage": stage,
                "command": command,
                "returncode": process.returncode,
                "status": "COMPLETED" if process.returncode == 0 else "FAILED",
                "stdout": f"{name}.stdout",
                "stderr": f"{name}.stderr",
            }
        )
        _write(manifest_path, {"run_id": run_id, "stages": receipts})
        print(stage, process.returncode, flush=True)
        if process.returncode:
            return process.returncode
    print("all stages exited zero; this is not experimental diameter validation", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
