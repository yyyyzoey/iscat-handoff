"""Formal V165 Gate A runner. Truth-aware process, separate from estimator.

Gate A is deliberately fail-closed.  A fresh attempt directory is claimed before
any provenance work starts, so a failure is still auditable.  Existing attempt
directories are never overwritten; callers must use a new attempt name.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import platform
import sys
import traceback
from pathlib import Path


SCHEMA_ATTEMPT = "iscat165.gate_a_attempt.1"
SCHEMA_FAILURE = "iscat165.gate_a_failure.1"
SCHEMA_RECEIPT = "iscat165.gate_a_receipt.1"


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def canonical_json(obj):
    return (
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_write_new(path, data):
    """Write a new artifact atomically and verify its exact bytes.

    The destination must not exist.  A failed write leaves no successful
    artifact at the final path; the temporary file is removed on failure.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError("REFUSE_TO_OVERWRITE_GATE_A_ARTIFACT:" + str(path))
    tmp = path.with_name(path.name + "." + str(os.getpid()) + ".tmp")
    try:
        with tmp.open("xb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
    if path.read_bytes() != data:
        raise RuntimeError("GATE_A_ATOMIC_READBACK:" + str(path))


def _claim_attempt(out):
    """Claim a new attempt directory, refusing any pre-existing path."""
    out = Path(out).resolve()
    if out.exists():
        raise FileExistsError("REFUSE_TO_OVERWRITE_GATE_A_ATTEMPT:" + str(out))
    out.mkdir(parents=True)
    return out


def _source_hashes(repo, module_path=None):
    candidates = [
        Path(__file__),
        repo / "tools/v165_bundle/validator/v165_truth_audit.py",
        repo / "tools/v165_bundle/code/v165_io.py",
        repo / "tools/v165_bundle/code/v152_gls_core.py",
    ]
    if module_path is not None:
        candidates.append(Path(module_path))
    result = {}
    for p in candidates:
        p = Path(p).resolve()
        if p.is_file():
            result[str(p)] = sha256_file(p)
    return result


def _failure_record(args, repo, out, exc):
    return {
        "schema": SCHEMA_FAILURE,
        "status": "FAILED",
        "utc": utc_now(),
        "attempt": str(out),
        "repo": str(repo),
        "command_argv": [sys.executable, *sys.argv],
        "command": subprocess_command(),
        "shell": {
            "COMSPEC": os.environ.get("COMSPEC"),
            "PSModulePath": os.environ.get("PSModulePath"),
            "cwd": str(Path.cwd()),
        },
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "args": {
            "repo": str(args.repo),
            "out": str(args.out),
            "projection": str(args.projection),
        },
        "source_sha256": _source_hashes(repo),
        "error_type": type(exc).__name__,
        "error": str(exc),
        "error_repr": repr(exc),
        "traceback": traceback.format_exc(),
        "reportable_D": None,
        "physical_result": "NOT_EVALUATED",
        "scope": "GATE_A_PROVENANCE_FAILURE_NOT_A_SIZING_RESULT",
    }


def subprocess_command():
    return " ".join([sys.executable, *sys.argv])


def _write_failure(out, failure):
    raw = canonical_json(failure)
    atomic_write_new(out / "failure.json", raw)
    atomic_write_new(out / "command_output.txt", failure["traceback"].encode("utf-8"))
    atomic_write_new(out / "exit_code.txt", b"2\n")
    digest = sha256_bytes(raw)
    atomic_write_new(out / "failure.sha256", (digest + "\n").encode("ascii"))
    return digest


def run_gate_a(repo, out, projection_path):
    repo = Path(repo).resolve()
    out = Path(out).resolve()
    projection_path = Path(projection_path).resolve()
    if projection_path.exists():
        raise FileExistsError("REFUSE_TO_OVERWRITE_GATE_A_PROJECTION:" + str(projection_path))
    # The truth-aware audit role lives on the validator side of the tree; the
    # estimator ``code`` directory must never be able to import it.
    audit_dir = repo / "tools/v165_bundle/validator"
    if str(audit_dir) not in sys.path:
        sys.path.insert(0, str(audit_dir))

    import v165_truth_audit

    actual_module = Path(v165_truth_audit.__file__).resolve()
    expected_module = (audit_dir / "v165_truth_audit.py").resolve()
    if actual_module != expected_module:
        raise ValueError("WRONG_GATE_A_MODULE")

    cfg = json.loads((repo / "config/v143_science_config.json").read_text(encoding="utf-8-sig"))
    gate = v165_truth_audit.build(repo, cfg)
    if gate.get("status") != "PASS" or gate.get("pass_") is not True:
        raise ValueError("GATE_A_BUILD_DID_NOT_PASS")

    full_raw = canonical_json(gate)
    full_path = out / "full_report.json"
    atomic_write_new(full_path, full_raw)
    full_sha = sha256_bytes(full_raw)
    if sha256_file(full_path) != full_sha:
        raise RuntimeError("FULL_REPORT_READBACK_SHA")

    projection = v165_truth_audit.estimator_projection(
        gate, full_report_sha256=full_sha
    )
    projection_raw = canonical_json(projection)
    atomic_write_new(projection_path, projection_raw)
    projection_sha = sha256_bytes(projection_raw)
    if sha256_file(projection_path) != projection_sha:
        raise RuntimeError("PROJECTION_READBACK_SHA")
    if projection.get("full_report_sha256") != full_sha:
        raise RuntimeError("PROJECTION_NOT_BOUND_TO_FULL_REPORT")
    if projection.get("status") != "PASS":
        raise RuntimeError("PROJECTION_NOT_PASS")

    receipt = {
        "schema": SCHEMA_RECEIPT,
        "status": "PASS",
        "utc": utc_now(),
        "attempt": str(out),
        "repo": str(repo),
        "command_argv": [sys.executable, *sys.argv],
        "command": subprocess_command(),
        "module_path": str(actual_module),
        "source_sha256": _source_hashes(repo, actual_module),
        "full_report_path": str(full_path),
        "full_report_sha256": full_sha,
        "projection_path": str(projection_path),
        "projection_sha256": projection_sha,
        "full_report_status": gate.get("status"),
        "projection_status": projection.get("status"),
        "model_calls": 0,
        "new_BEM": 0,
        "new_render": 0,
        "new_camera_exposures": 0,
        "new_camera_noise_draws": 0,
        "reportable_D": None,
        "physical_result": "NOT_EVALUATED",
        "scope": "READ_ONLY_PROVENANCE_ONLY_NOT_A_PHYSICAL_OR_SIZING_RESULT",
    }
    receipt_raw = canonical_json(receipt)
    atomic_write_new(out / "gate_a_receipt.json", receipt_raw)
    if sha256_file(out / "gate_a_receipt.json") != sha256_bytes(receipt_raw):
        raise RuntimeError("RECEIPT_READBACK_SHA")
    if receipt["full_report_sha256"] != sha256_file(full_path):
        raise RuntimeError("RECEIPT_FULL_REPORT_SHA")
    if receipt["projection_sha256"] != sha256_file(projection_path):
        raise RuntimeError("RECEIPT_PROJECTION_SHA")
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--projection", type=Path, required=True)
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    out = args.out.resolve()
    try:
        _claim_attempt(out)
    except Exception as exc:
        # Never write into a pre-existing attempt.  Emit a refusal record next
        # to it so an automated caller still gets a structured failure.
        refusal = out.with_name(out.name + ".refused-" + datetime.datetime.now().strftime("%Y%m%dT%H%M%S%f"))
        try:
            refusal.mkdir(parents=True)
            failure = _failure_record(args, repo, refusal, exc)
            failure["attempt_claimed"] = False
            _write_failure(refusal, failure)
            print(failure["traceback"], file=sys.stderr)
        except Exception:
            traceback.print_exc()
        return 2

    try:
        receipt = run_gate_a(repo, out, args.projection)
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        failure = _failure_record(args, repo, out, exc)
        try:
            _write_failure(out, failure)
        except Exception:
            traceback.print_exc()
        print(failure["traceback"], file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

