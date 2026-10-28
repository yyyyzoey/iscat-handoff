"""Line-delimited JSON-RPC between the trusted model service and one worker.

The worker owns the optimiser loop and the frozen scorer; the controller owns the
single live F2c model and the ledger.  A forward request therefore crosses the
process boundary as theta out, signed-C in, base64 float64, and the controller --
never the worker -- stamps the ledger identity of the answer (task, seq,
start_index, kind).  Messages are one JSON object per line on stdin/stdout.
"""
from __future__ import annotations

import base64
import json
from typing import Any

import numpy as np

PROTOCOL = "iscat167.rpc.1"
WORKER_OPS = ("hello", "start_begin", "forward", "log", "start_end", "done")
CONTROLLER_OPS = ("hello_ack", "forward_result", "forward_error", "fatal")
ARRAY_KEYS = ("C",)


def encode_array(array: Any) -> str:
    contiguous = np.ascontiguousarray(array, dtype=np.float64)
    return base64.b64encode(contiguous.tobytes()).decode("ascii")


def decode_array(text: str, shape: tuple[int, ...]) -> np.ndarray:
    raw = base64.b64decode(text.encode("ascii"))
    array = np.frombuffer(raw, dtype="<f8")
    expected = int(np.prod(shape)) if len(shape) else 1
    if array.size != expected:
        raise ValueError("RPC_ARRAY_SIZE:%d!=%d" % (array.size, expected))
    return array.reshape(shape).copy()


def _dumps(message: dict) -> bytes:
    return (json.dumps(message, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("utf-8")


def send(stream, message: dict) -> None:
    stream.write(_dumps(message))
    stream.flush()


def recv(stream) -> dict:
    """Read one message; a closed stream means the peer died, which is fatal."""
    line = stream.readline()
    if not line:
        raise EOFError("RPC_PEER_CLOSED")
    message = json.loads(line.decode("utf-8"))
    if not isinstance(message, dict) or "op" not in message:
        raise ValueError("RPC_MALFORMED_MESSAGE")
    return message


def forward_request(request_id: int, theta: Any, start_index: int, kind: str,
                    evaluation_index: int) -> dict:
    t = np.asarray(theta, dtype=float)
    return {"op": "forward", "request_id": int(request_id),
            "theta": [float(x) for x in t], "start_index": int(start_index),
            "kind": str(kind), "evaluation_index": int(evaluation_index)}


def forward_result(request_id: int, c: np.ndarray, record: dict) -> dict:
    message = {"op": "forward_result", "request_id": int(request_id),
               "C": encode_array(c)}
    for key in ("seq", "charged", "cache_hit", "prediction_path", "prediction_sha256",
                "C_sha256", "theta_sha256", "returned_theta", "forward_wall_ms",
                "charged_task_id", "origin"):
        if key in record and isinstance(record[key], (int, float, bool, str, list, type(None))):
            message[key] = record[key]
    return message


def validate_forward_reply(message: dict, request_id: int) -> np.ndarray:
    if message.get("op") != "forward_result":
        raise ValueError("RPC_UNEXPECTED_REPLY:" + str(message.get("op")))
    if int(message.get("request_id", -1)) != int(request_id):
        raise ValueError("RPC_REQUEST_ID_MISMATCH")
    if message.get("C") is None:
        raise ValueError("RPC_MISSING_C")
    return decode_array(message["C"], (13, 13))
