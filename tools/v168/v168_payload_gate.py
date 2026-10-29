"""Estimator-side single-payload gate for V168. No plan, seed or truth knowledge.

V168 authored this file: the delivered bundle carries no payload gate, and its
manifest byte-pins every file that is in it, so a round-authored gate cannot be
injected there.  It is the one file in ``tools/v168`` an estimator is allowed to
read, it is loaded by pinned bytes (see ``v168_common.load_payload_gate``), and
the shape it enforces is the shape the trusted controller is required to emit.

This is a schema gate, NOT an OS sandbox; production isolation is the worker
jail's read-path denial (contract section 4.4).

Cap semantics come from contract sections 7 and 8 and are the point of the V168
rewrite: a task budget is 400 real new calls, and one start may never carry more
than its own 400 (single start) or 200 (two fixed starts).  ``max_nfev`` is not a
billing quota.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

SCHEMA = "iscat168.one_task.1"
SCOPE = "OPENED_DEV_NOT_BLIND_NOT_EXPERIMENT"
TOP = {"schema", "task_id", "group", "B", "reading", "starts",
       "cap_per_start", "task_cap", "scope"}
READING = {"reading_id", "group", "B", "replicate", "sigma_nm", "z_nm",
           "hypothetical"}
GROUPS = ("ANON_01", "ANON_02", "ANON_03", "ANON_04")
LOW = (30.0, 350.0, -500.0, -500.0)
HIGH = (200.0, 550.0, 500.0, 500.0)
MIN_SURFACE_GAP_NM = 100.0
TASK_CAP = 400
SIGMA_NM = (1.0, 10.0)


def _number(value) -> bool:
    return type(value) in (int, float) and math.isfinite(float(value))


def validate(payload) -> dict:
    if not isinstance(payload, dict) or set(payload) != TOP:
        raise ValueError("WORKER_PAYLOAD_KEYS")
    if payload["schema"] != SCHEMA or payload["scope"] != SCOPE:
        raise ValueError("SCOPE_OR_SCHEMA")
    # V168 payloads must not be accepted as V167 ones, or the reverse.
    if not isinstance(payload["task_id"], str) or not payload["task_id"].startswith("V168_"):
        raise ValueError("TASK_ID")
    if payload["group"] not in GROUPS or payload["B"] != 100000:
        raise ValueError("GROUP_OR_B")
    reading = payload.get("reading")
    if not isinstance(reading, dict) or set(reading) != READING:
        raise ValueError("ONE_READING_ONLY")
    if (reading["reading_id"] != payload["task_id"]
            or reading["group"] != payload["group"]
            or reading["B"] != payload["B"]):
        raise ValueError("READING_BINDING")
    if type(reading["replicate"]) is not int or reading["replicate"] not in (0, 1, 2):
        raise ValueError("REPLICATE")
    if reading["hypothetical"] is not True:
        raise ValueError("HYPOTHETICAL_REQUIRED")
    if not _number(reading["sigma_nm"]) or float(reading["sigma_nm"]) not in SIGMA_NM:
        raise ValueError("SIGMA")
    if not _number(reading["z_nm"]):
        raise ValueError("Z_FINITE")

    starts = payload["starts"]
    if not isinstance(starts, list) or len(starts) not in (1, 2):
        raise ValueError("START_COUNT")
    for theta in starts:
        if (not isinstance(theta, list) or len(theta) != 4
                or not all(_number(x) for x in theta)):
            raise ValueError("THETA")
        values = [float(x) for x in theta]
        if not all(lo <= x <= hi for x, lo, hi in zip(values, LOW, HIGH)):
            raise ValueError("DOMAIN_NO_CLIP")
        if values[1] - values[0] / 2.0 < MIN_SURFACE_GAP_NM:
            raise ValueError("DOMAIN_NO_CLIP")

    if type(payload["task_cap"]) is not int or type(payload["cap_per_start"]) is not int:
        raise ValueError("CAP")
    if payload["task_cap"] != TASK_CAP:
        raise ValueError("CAP")
    if payload["cap_per_start"] != TASK_CAP // len(starts):
        raise ValueError("CAP")
    # A one-start payload is the R branch and may hold the whole 400; a two-start
    # payload is the B branch and is 200 each.  Anything else is a grid change.
    if len(starts) == 1 and payload["cap_per_start"] != 400:
        raise ValueError("CAP")
    if len(starts) == 2 and payload["cap_per_start"] != 200:
        raise ValueError("CAP")
    return payload


def load_single(path):
    return validate(json.loads(Path(path).read_text(encoding="utf-8")))
