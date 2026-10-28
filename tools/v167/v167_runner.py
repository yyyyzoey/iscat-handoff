"""Controller-side supervisor for one estimator subprocess.

Controller-only: never importable by a worker (v167_jail DENIED_MODULE_PREFIXES
and the denied_read path list both refuse it).  This is the only place that
spawns a worker, and every answer it gives to a forward request is produced by
the single trusted service, which writes the charge before the real call.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np

from v152_gls_core import CallCapReached
from v167_common import (
    MODEL_ID, OUT, ROOT, atomic_json, canon, read_json, require, sha_bytes, update_json,
)
import v167_rpc

WORKER_PY = ROOT / "tools" / "v167" / "v167_worker.py"


class WorkerDeath(RuntimeError):
    pass


class ServiceRefusal(RuntimeError):
    pass


def _drain(stream, sink: list[str]) -> None:
    """Worker stderr must be emptied or a long traceback can block the pipe."""
    try:
        while True:
            line = stream.readline()
            if not line:
                return
            sink.append(line.decode("utf-8", "replace").rstrip("\r\n"))
    except Exception as exc:                                # noqa: BLE001
        sink.append("STDERR_DRAIN_ERROR:" + repr(exc))


def spawn(task_dir: Path) -> Any:
    """Launch the worker in its own jail directory with interpreter isolation."""
    import subprocess
    import sys

    task_dir = Path(task_dir)
    # The jail allows writes only inside OUT/tasks/<task_id>.  pathlib's
    # mkdir(parents=True) always calls os.mkdir on every missing ancestor, so
    # the shared parent must already exist on the trusted side; otherwise the
    # worker is refused while climbing above its own write root.
    (OUT / "tasks").mkdir(parents=True, exist_ok=True)
    task_dir.mkdir(parents=True, exist_ok=True)
    return subprocess.Popen(
        [sys.executable, "-I", "-B",
         "-X", "pycache_prefix=" + str(task_dir / "__pycache_redirect"),
         str(WORKER_PY), str(task_dir)],
        cwd=str(task_dir), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=False,
    )


def _meta_line(kind: str, payload: dict) -> dict:
    row = {"kind": kind, "wall_ns": time.time_ns()}
    for key in ("op", "request_id", "task_id", "start_index", "pass_index",
                "evaluation_index", "seq", "charged", "cache_hit", "C_sha256",
                "theta_sha256", "prediction_path", "prediction_sha256",
                "origin", "charged_task_id", "execution_state", "jail_refusals",
                "error_type", "message", "cap_reached", "evaluations", "payload_sha256"):
        if key in payload and isinstance(payload[key], (int, float, bool, str, list, type(None))):
            row[key] = payload[key]
    return row


def serve(proc: Any, *, task_id: str, expected_payload_sha256: str,
          frames_sha256: str, service: Any, log: list[dict],
          timeout_seconds: float = 3600.0) -> dict:
    """Answer one worker's requests until it reports done.  Returns its result doc."""
    stdin, stdout = proc.stdin, proc.stdout
    hello = v167_rpc.recv(stdout)
    if hello.get("op") != "hello":
        raise WorkerDeath("WORKER_FIRST_MESSAGE_NOT_HELLO:" + str(hello.get("op")))
    require(hello.get("task_id") == task_id, "WORKER_TASK_ID_MISMATCH")
    require(hello.get("protocol") == v167_rpc.PROTOCOL, "WORKER_PROTOCOL_MISMATCH")
    require(hello.get("payload_sha256") == expected_payload_sha256,
            "WORKER_PAYLOAD_SHA_DIFFERS_FROM_PLAN")
    log.append(_meta_line("request", hello))
    v167_rpc.send(stdin, {"op": "hello_ack", "request_id": 0, "ack": True,
                          "task_id": task_id, "model_id": MODEL_ID,
                          "frames_sha256": frames_sha256})
    log.append(_meta_line("reply", {"op": "hello_ack", "task_id": task_id,
                                    "frames_sha256": frames_sha256}))
    deadline = time.monotonic() + timeout_seconds
    result: dict | None = None
    while True:
        if time.monotonic() > deadline:
            proc.kill()
            raise WorkerDeath("WORKER_TIMEOUT:" + task_id)
        try:
            message = v167_rpc.recv(stdout)
        except EOFError:
            if result is not None:
                break
            raise WorkerDeath("WORKER_PIPE_CLOSED_BEFORE_DONE:exit="
                              + str(proc.poll())) from None
        op = message.get("op")
        log.append(_meta_line("request", message))
        if op == "forward":
            reply = _answer_forward(message, task_id=task_id, frames_sha256=frames_sha256,
                                    service=service)
            log.append(_meta_line("reply", reply))
            v167_rpc.send(stdin, reply)
            if reply.get("op") == "fatal":
                proc.kill()
                raise ServiceRefusal(str(reply.get("message")))
        elif op == "start_begin":
            v167_rpc.send(stdin, {"op": "hello_ack", "request_id": 0, "ack": True,
                                  "task_id": task_id,
                                  "start_index": message.get("start_index"),
                                  "pass_index": message.get("pass_index")})
            log.append(_meta_line("reply", {"op": "start_begin_ack",
                                            "start_index": message.get("start_index"),
                                            "pass_index": message.get("pass_index")}))
        elif op in ("log", "start_end"):
            # Fire-and-forget by protocol: replying here would desynchronise the pipe.
            pass
        elif op == "done":
            result = message.get("result") or {}
            require(result.get("task_id") == task_id, "WORKER_DONE_TASK_MISMATCH")
            v167_rpc.send(stdin, {"op": "hello_ack", "request_id": 0, "ack": True,
                                  "task_id": task_id})
            log.append(_meta_line("reply", {"op": "done_ack", "task_id": task_id}))
            break
        else:
            v167_rpc.send(stdin, {"op": "fatal", "request_id": message.get("request_id", 0),
                                  "message": "UNKNOWN_WORKER_OP:" + str(op)})
            proc.kill()
            raise WorkerDeath("UNKNOWN_WORKER_OP:" + str(op))
    if result is None:
        raise WorkerDeath("WORKER_EXITED_WITHOUT_DONE:exit=" + str(proc.poll()))
    return result


def _answer_forward(message: dict, *, task_id: str, frames_sha256: str, service: Any) -> dict:
    request_id = int(message.get("request_id", -1))
    theta = np.asarray(message.get("theta"), dtype=float)
    start_index = int(message.get("start_index", 0))
    try:
        # charge-before-real-call happens inside the service, before model.forward.
        info = service.evaluate(task_id, theta, start_index=start_index,
                                kind="OPTIMIZER", frames_sha256=frames_sha256)
    except CallCapReached as exc:
        return {"op": "forward_error", "request_id": request_id, "cap_reached": True,
                "error_type": type(exc).__name__, "message": str(exc), "task_id": task_id}
    except Exception as exc:                                    # noqa: BLE001
        return {"op": "fatal", "request_id": request_id, "error_type": type(exc).__name__,
                "message": str(exc), "task_id": task_id}
    return v167_rpc.forward_result(request_id, np.asarray(info["C"], dtype=float), info)


def run_task(*, task_id: str, expected_payload_sha256: str, frames_sha256: str,
             service: Any) -> dict:
    """One full worker round trip, plus durable controller-side RPC accounting."""
    jail = OUT / "estimator_inputs" / task_id
    log: list[dict] = []
    proc = spawn(jail)
    stderr_lines: list[str] = []
    reader = threading.Thread(target=_drain, args=(proc.stderr, stderr_lines), daemon=True)
    reader.start()
    started = time.perf_counter()
    exit_code = None
    error = None
    try:
        result = serve(proc, task_id=task_id, expected_payload_sha256=expected_payload_sha256,
                       frames_sha256=frames_sha256, service=service, log=log)
    except Exception as exc:                                        # noqa: BLE001
        result = None
        error = {"error_type": type(exc).__name__, "error": str(exc),
                 "traceback": __import__("traceback").format_exc()}
        try:
            proc.kill()
        except OSError:
            pass
    finally:
        try:
            exit_code = proc.wait(timeout=120)
        except Exception:                                           # noqa: BLE001
            exit_code = None
        reader.join(timeout=5)
    forward_requests = sum(1 for row in log if row["kind"] == "request"
                           and row.get("op") == "forward")
    charged = sum(1 for row in log if row["kind"] == "reply"
                  and row.get("op") == "forward_result" and row.get("charged") is True)
    cache_hits = sum(1 for row in log if row["kind"] == "reply"
                     and row.get("op") == "forward_result" and row.get("cache_hit") is True)
    receipt = {
        "schema": "iscat167.controller_task_run.1", "task_id": task_id,
        "worker_exit_code": exit_code, "wall_seconds": time.perf_counter() - started,
        "forward_requests": forward_requests, "charged_replies": charged,
        "cache_hit_replies": cache_hits, "rpc_message_count": len(log),
        "stderr_lines": stderr_lines[-200:], "rpc_log_sha256": sha_bytes(canon(log)),
        "worker_error": error, "ledger_counts_after": dict(service.store.counts()),
        "reportable_D": None,
    }
    path = OUT / "controller_only" / "rpc" / (task_id + ".json")
    document = dict(receipt, rpc_log=log)
    if Path(path).exists():
        update_json(path, document)
    else:
        atomic_json(path, document)
    if error is not None:
        raise WorkerDeath("TASK_ROUND_FAILED:" + task_id + ":" + error["error_type"]
                          + ":" + error["error"][:1500])
    return dict(receipt, result=result)


def probe_task(*, task_id: str, timeout_seconds: float = 300.0) -> dict:
    """Run the worker in --probe mode: boot the jail, try forbidden reads, exit.

    Used by the production test suite.  Probe mode never serves a forward, so it
    cannot bill a model call even if the file guard had failed.
    """
    import subprocess
    import sys

    jail = OUT / "estimator_inputs" / task_id
    proc = subprocess.Popen(
        [sys.executable, "-I", "-B", str(WORKER_PY), str(jail), "--probe"],
        cwd=str(jail), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=False)
    out, err = proc.communicate(timeout=timeout_seconds)
    rows: list[dict] = []
    for line in out.decode("utf-8", "replace").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return {"task_id": task_id, "exit_code": proc.returncode,
            "probe_report": rows[-1] if rows else None,
            "stdout_json_lines": len(rows),
            "stderr": err.decode("utf-8", "replace")[-4000:]}


def frames_sha_for(document: dict, group: str) -> str:
    from v167_common import frames_from_document

    _data, _identity, sha = frames_from_document(document, where="controller:" + group)
    return sha


def require_no_forbidden(doc: Any, where: str) -> None:
    """Controller-side guard so a controller artefact can never carry a truth key."""
    from v167_common import scan_forbidden

    problems = scan_forbidden(doc, where)
    require(not problems, "CONTROLLER_OUTPUT_LEAKS_TRUTH_KEY:" + where + ":" + ";".join(problems))


__all__ = ["WorkerDeath", "ServiceRefusal", "WORKER_PY", "spawn", "serve", "run_task",
           "probe_task", "frames_sha_for", "require_no_forbidden"]
