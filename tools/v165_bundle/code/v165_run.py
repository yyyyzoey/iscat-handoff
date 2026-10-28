"""V165 production runner for hypothetical-height particle fitting.

This module is the estimator side.  It never opens the validator-only truth or
height-generation records.  Ground truth is consumed only by the separate
preflight Gate A process and the post-seal validator.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sqlite3
import sys
import traceback
from pathlib import Path
from typing import Any, Callable

import numpy as np

from v152_budget_store import (
    BudgetStore,
    StoreError,
    atomic_json,
    canonical,
)
from v152_gls_core import CallCapReached, GlsData
from v165_objective import HeightReading, augmented_objective, check_theta
from v165_task_ids import tasks


PARENT = "2558e24ced48e65d34797a4021cab659aa045566"
MODEL_ID = (
    "v142-F2c-75860d222dd8e90d8dc2e31111e52ccbbb212a01c0d6a0dfe7fdbcdb241c98c3"
)
PHASES = {"MODEL_BINDING": 200, "HEIGHT_FITS": 11200, "FINAL_VERIFY": 600}
TOTAL = 12000
OWNER = "v165-single-process"
PLAN_ID = "v165"
LOADER_TASK = "LOADER_1"
BIND_TASK = "BINDING"
FINAL_TASK = "FINAL_VERIFY"
OPTIMIZER = dict(
    method="trf",
    jac="3-point",
    loss="linear",
    diff_step=1e-5,
    x_scale=[50.0, 50.0, 280.0, 280.0],
    ftol=1e-9,
    xtol=1e-9,
    gtol=1e-8,
    max_nfev=200,
)
LOW = np.array([30.0, 350.0, -500.0, -500.0])
HIGH = np.array([200.0, 550.0, 500.0, 500.0])


class RunError(RuntimeError):
    pass


class FatalPersistenceError(RunError):
    pass


def require(value: Any, message: str):
    if not value:
        raise ValueError(message)


def sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def array_sha(array: np.ndarray) -> str:
    return sha_bytes(np.ascontiguousarray(array, dtype=np.float64).tobytes())


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_once_json(path: Path, obj: Any) -> str:
    path = Path(path)
    raw = (canonical(obj) + "\n").encode("utf-8")
    if path.exists():
        require(path.read_bytes() == raw, "REFUSE_TO_REWRITE_CHANGED_ARTIFACT:" + str(path))
        return sha_bytes(raw)
    digest = atomic_json(path, obj)
    require(path.read_bytes() == raw, "ATOMIC_JSON_READBACK:" + str(path))
    return digest


def write_once_bytes(path: Path, raw: bytes) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        require(path.read_bytes() == raw, "REFUSE_TO_REWRITE_CHANGED_BYTES:" + str(path))
        return sha_bytes(raw)
    tmp = path.with_name(path.name + "." + str(__import__("os").getpid()) + ".tmp")
    try:
        with tmp.open("xb") as f:
            f.write(raw)
            f.flush()
            __import__("os").fsync(f.fileno())
        __import__("os").replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
    require(path.read_bytes() == raw, "BYTE_READBACK:" + str(path))
    return sha_bytes(raw)


def git(repo: Path, *args: str) -> bytes:
    import subprocess

    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True
    ).stdout


def blob(path: Path) -> str:
    p = Path(path)
    h = hashlib.sha1(b"blob " + str(p.stat().st_size).encode("ascii") + b"\0")
    with p.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def task_descriptor(name: str, row: dict | None = None) -> dict:
    if name == LOADER_TASK:
        return {"task_id": name, "phase": "MODEL_BINDING", "cap": 100, "kind": "LOADER"}
    if name == BIND_TASK:
        return {"task_id": name, "phase": "MODEL_BINDING", "cap": 100, "kind": "BINDING"}
    if name == FINAL_TASK:
        return {"task_id": name, "phase": "FINAL_VERIFY", "cap": 600, "kind": "FINAL"}
    require(row is not None, "MISSING_FIT_TASK_DESCRIPTOR")
    return {
        "task_id": name,
        "phase": "HEIGHT_FITS",
        "cap": 400,
        "kind": "HEIGHT_FIT",
        **{k: row[k] for k in ("group", "replicate", "sigma_nm")},
    }


def plan_descriptors() -> list[dict]:
    rows = [task_descriptor(LOADER_TASK), task_descriptor(BIND_TASK)]
    rows.extend(task_descriptor(row["task_id"], row) for row in tasks())
    rows.append(task_descriptor(FINAL_TASK))
    require(len(rows) == 31, "V165_MUST_HAVE_31_TASKS")
    require(len({r["task_id"] for r in rows}) == 31, "DUPLICATE_TASK_ID")
    require(sum(r["cap"] for r in rows) == TOTAL, "V165_RESERVATION_SUM")
    return rows


def task_signature(descriptor: dict, plan_sha: str, preflight_sha: str) -> str:
    payload = canonical(
        {
            "schema": "iscat165.task_signature.1",
            "plan_id": PLAN_ID,
            "descriptor": descriptor,
            "plan_sha256": plan_sha,
            "preflight_sha256": preflight_sha,
            "optimizer": OPTIMIZER,
        }
    ).encode("utf-8")
    return sha_bytes(payload)


def signatures(plan_sha: str, preflight_sha: str) -> dict[str, dict]:
    return {
        row["task_id"]: {
            "descriptor": row,
            "signature": task_signature(row, plan_sha, preflight_sha),
        }
        for row in plan_descriptors()
    }


def reserve_plan(store: BudgetStore, sigs: dict[str, dict]) -> dict[str, str]:
    states = {}
    for task_id, item in sigs.items():
        desc = item["descriptor"]
        states[task_id] = store.reserve(
            task_id, item["signature"], desc["phase"], desc["cap"], OWNER
        )
    require(len(store.counts()) == 31, "UNEXPECTED_TASK_RESERVATIONS")
    return states


def _task_row(store: BudgetStore, task_id: str) -> dict:
    path = store.path.resolve()
    con = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        row = con.execute(
            "SELECT signature,phase,cap,used,owner,state,result_path,result_sha "
            "FROM tasks WHERE id=?",
            (task_id,),
        ).fetchone()
        require(row is not None, "MISSING_TASK_ROW:" + task_id)
        return dict(
            task_id=task_id,
            signature=row[0],
            phase=row[1],
            cap=row[2],
            used=row[3],
            owner=row[4],
            state=row[5],
            result_path=row[6],
            result_sha=row[7],
        )
    finally:
        con.close()


def _attempt_rows(store: BudgetStore, task_id: str) -> list[dict]:
    path = store.path.resolve()
    con = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT seq,theta,state,detail,ts FROM attempts WHERE task=? ORDER BY seq",
            (task_id,),
        ).fetchall()
        return [
            dict(
                seq=row[0],
                theta=json.loads(row[1]),
                state=row[2],
                detail=json.loads(row[3]) if row[3] is not None else None,
                ts=row[4],
            )
            for row in rows
        ]
    finally:
        con.close()


def _attempt_for_seq(store: BudgetStore, task_id: str, seq: int) -> dict | None:
    for row in _attempt_rows(store, task_id):
        if int(row["seq"]) == int(seq):
            return row
    return None


class ChargedCaller:
    """Persist a charge before invoking a model and finalize only after C is durable."""

    def __init__(
        self,
        store: BudgetStore,
        task_id: str,
        out: Path,
        *,
        start_index: int | None = None,
        kind: str = "MODEL",
        prediction_writer: Callable[[Path, Any], str] | None = None,
        allow_exact_reuse: bool = True,
    ):
        self.store = store
        self.task_id = task_id
        self.out = Path(out)
        self.start_index = start_index
        self.kind = kind
        self.prediction_writer = prediction_writer or atomic_json
        self.prediction_dir = self.out / "tasks" / task_id / "predictions"
        self.allow_exact_reuse = allow_exact_reuse

    @staticmethod
    def _array_metadata(array: np.ndarray) -> dict:
        contiguous = np.ascontiguousarray(array, dtype=np.float64)
        return {
            "shape": list(contiguous.shape),
            "dtype": "float64",
            "sha256": sha_bytes(contiguous.tobytes()),
        }

    def _exact_prediction(self, theta: np.ndarray) -> dict | None:
        if not self.allow_exact_reuse or not self.prediction_dir.is_dir():
            return None
        for path in sorted(self.prediction_dir.glob("*.json")):
            doc = read_json(path)
            if (
                doc.get("schema") != "iscat165.prediction.1"
                or doc.get("task") != self.task_id
            ):
                continue
            seq = int(doc.get("seq", -1))
            attempt = _attempt_for_seq(self.store, self.task_id, seq)
            if attempt is None or attempt["state"] != "RETURNED":
                continue
            detail = attempt.get("detail") or {}
            require(
                detail.get("task_id") == self.task_id
                and detail.get("ledger_seq") == seq
                and np.array_equal(
                    np.asarray(detail.get("requested_theta"), dtype=float),
                    np.asarray(attempt["theta"], dtype=float),
                ),
                "REUSED_PREDICTION_CHARGE_BINDING:" + str(path),
            )
            if not np.array_equal(
                np.asarray(doc.get("requested_theta"), dtype=float), theta
            ):
                continue
            relative_path = path.relative_to(self.out).as_posix()
            require(
                doc.get("ledger_seq") == seq
                and doc.get("start_index") == self.start_index
                and doc.get("start_index") == detail.get("start_index")
                and doc.get("kind") == self.kind
                and doc.get("kind") == detail.get("kind")
                and detail.get("prediction_path") == relative_path
                and detail.get("prediction_sha256") == sha_file(path),
                "REUSED_PREDICTION_LEDGER_IDENTITY:" + str(path),
            )
            require(
                np.array_equal(
                    np.asarray(doc.get("returned_theta"), dtype=float), theta
                )
                and np.array_equal(
                    np.asarray(detail.get("returned_theta"), dtype=float), theta
                ),
                "REUSED_PREDICTION_RETURNED_THETA:" + str(path),
            )
            observation = doc.get("observation")
            metadata = doc.get("observation_metadata")
            require(
                isinstance(observation, dict) and isinstance(metadata, dict),
                "REUSED_PREDICTION_OBSERVATION_MISSING:" + str(path),
            )
            require(
                set(observation) == set(metadata),
                "REUSED_PREDICTION_OBSERVATION_KEYS:" + str(path),
            )
            for name, values in observation.items():
                array = np.ascontiguousarray(values, dtype=float)
                require(
                    np.isfinite(array).all(),
                    "REUSED_PREDICTION_NONFINITE:" + name,
                )
                require(
                    self._array_metadata(array) == metadata[name],
                    "REUSED_PREDICTION_ARRAY_METADATA:" + name,
                )
            c = np.ascontiguousarray(doc["C"], dtype=float)
            require(
                c.shape == (13, 13)
                and np.isfinite(c).all()
                and array_sha(c) == doc.get("C_sha256")
                and doc.get("C_sha256") == detail.get("C_sha256"),
                "REUSED_PREDICTION_C",
            )
            return {
                "C": c,
                "seq": seq,
                "C_sha256": doc["C_sha256"],
                "prediction_path": relative_path,
                "prediction_sha256": sha_file(path),
                "reused_exact_returned_prediction": True,
                "observation": {
                    name: np.ascontiguousarray(values, dtype=np.float64)
                    for name, values in observation.items()
                },
            }
        return None

    def call(
        self,
        theta: Any,
        invoke: Callable[[np.ndarray], Any],
    ) -> dict:
        t = check_theta(theta)
        reused = self._exact_prediction(t)
        if reused is not None:
            return reused
        seq = self.store.charge(
            self.task_id,
            OWNER,
            t,
            detail={
                "start_index": self.start_index,
                "kind": self.kind,
                "invocation": "charged_model_forward",
            },
        )
        try:
            result = invoke(t)
            if hasattr(result, "score_C"):
                observation = {}
                for name in ("Ibg", "I", "C", "score_C"):
                    require(
                        hasattr(result, name),
                        "MODEL_OUTPUT_MISSING_" + name,
                    )
                    observation[name] = np.ascontiguousarray(
                        getattr(result, name), dtype=float
                    )
                    require(
                        np.isfinite(observation[name]).all(),
                        "MODEL_OUTPUT_NONFINITE_" + name,
                    )
                c = observation["score_C"]
                returned_theta = np.asarray(
                    getattr(result, "theta", t), dtype=float
                )
                require(
                    np.array_equal(returned_theta, t),
                    "MODEL_OUTPUT_RETURNED_THETA_CHANGED",
                )
                model_id = getattr(result, "model_id", None)
            else:
                c = np.ascontiguousarray(result, dtype=float)
                observation = {"score_C": c}
                returned_theta = t.copy()
                model_id = None
            if c.shape != (13, 13) or not np.isfinite(c).all():
                raise ValueError("MODEL_OUTPUT_MUST_BE_FINITE_13X13_SIGNED_C")
        except Exception as exc:
            detail = {
                "error_type": type(exc).__name__,
                "error": str(exc),
                "error_repr": repr(exc),
                "traceback": traceback.format_exc(),
                "ledger_seq": seq,
                "start_index": self.start_index,
                "kind": self.kind,
                "returned_theta": None,
            }
            try:
                self.store.returned(
                    self.task_id,
                    seq,
                    "MODEL_ERROR",
                    detail,
                )
            except Exception as persist_exc:
                raise FatalPersistenceError(
                    "CHARGED_MODEL_ERROR_NOT_DURABLE:"
                    + self.task_id
                    + ":"
                    + str(seq)
                    + ":"
                    + repr(persist_exc)
                ) from persist_exc
            raise

        c = np.ascontiguousarray(c, dtype=np.float64)
        c_hash = array_sha(c)
        observation_json = {
            name: np.ascontiguousarray(values, dtype=np.float64).tolist()
            for name, values in observation.items()
        }
        observation_metadata = {
            name: self._array_metadata(values)
            for name, values in observation.items()
        }
        path = self.prediction_dir / f"{seq:04d}.json"
        if path.exists():
            raise FatalPersistenceError("PREDICTION_PATH_ALREADY_EXISTS:" + str(path))
        prediction = {
            "schema": "iscat165.prediction.1",
            "task": self.task_id,
            "seq": seq,
            "ledger_seq": seq,
            "start_index": self.start_index,
            "kind": self.kind,
            "requested_theta": t.tolist(),
            "returned_theta": returned_theta.tolist(),
            "model_id": model_id,
            "theta": returned_theta.tolist(),
            "C": c.tolist(),
            "C_sha256": c_hash,
            "observation": observation_json,
            "observation_metadata": observation_metadata,
        }
        relative_path = path.relative_to(self.out).as_posix()
        try:
            digest = self.prediction_writer(path, prediction)
            persisted = read_json(path)
            require(persisted == prediction, "PREDICTION_READBACK_IDENTITY")
            file_sha = sha_file(path)
            require(digest == file_sha, "PREDICTION_WRITER_DIGEST")
            require(
                array_sha(np.asarray(persisted["C"], dtype=float)) == c_hash,
                "PREDICTION_ARRAY_READBACK",
            )
        except Exception as exc:
            raise FatalPersistenceError(
                "CHARGED_ATTEMPT_PREDICTION_NOT_DURABLE:"
                + self.task_id
                + ":"
                + str(seq)
                + ":"
                + repr(exc)
            ) from exc

        try:
            self.store.returned(
                self.task_id,
                seq,
                "RETURNED",
                {
                    "ledger_seq": seq,
                    "C_sha256": c_hash,
                    "prediction_path": relative_path,
                    "prediction_sha256": file_sha,
                    "start_index": self.start_index,
                    "kind": self.kind,
                    "returned_theta": returned_theta.tolist(),
                    "model_id": model_id,
                    "observation_metadata": observation_metadata,
                },
            )
        except Exception as exc:
            raise FatalPersistenceError(
                "CHARGED_RETURN_NOT_DURABLE:"
                + self.task_id
                + ":"
                + str(seq)
                + ":"
                + repr(exc)
            ) from exc
        return {
            "C": c,
            "seq": seq,
            "C_sha256": c_hash,
            "prediction_path": relative_path,
            "prediction_sha256": file_sha,
            "reused_exact_returned_prediction": False,
            "model_output": result,
        }


class ModelPredictor:
    def __init__(
        self,
        model: Any,
        store: BudgetStore,
        task_id: str,
        out: Path,
        *,
        start_index: int | None = None,
        kind: str = "OPTIMIZER",
        prediction_writer: Callable[[Path, Any], str] | None = None,
        allow_exact_reuse: bool = True,
    ):
        self.model = model
        self.caller = ChargedCaller(
            store,
            task_id,
            out,
            start_index=start_index,
            kind=kind,
            prediction_writer=prediction_writer,
            allow_exact_reuse=allow_exact_reuse,
        )

    def __call__(self, theta: Any) -> dict:
        return self.caller.call(
            theta,
            lambda t: self.model.forward(tuple(float(x) for x in t)),
        )


def reconcile_charged(store: BudgetStore, task_id: str, out: Path) -> list[dict]:
    """Finalize only CHARGED attempts whose durable matching prediction exists."""
    recovered = []
    for row in _attempt_rows(store, task_id):
        if row["state"] != "CHARGED":
            continue
        path = out / "tasks" / task_id / "predictions" / f"{row['seq']:04d}.json"
        require(
            path.is_file(),
            "UNRECOVERABLE_CHARGED_ATTEMPT_NO_PREDICTION:"
            + task_id
            + f":{row['seq']}",
        )
        doc = read_json(path)
        detail = row.get("detail") or {}
        require(
            doc.get("task") == task_id
            and doc.get("seq") == row["seq"]
            and doc.get("ledger_seq") == row["seq"],
            "CHARGED_PREDICTION_IDENTITY",
        )
        require(
            detail.get("task_id") == task_id
            and detail.get("ledger_seq") == row["seq"]
            and detail.get("start_index") == doc.get("start_index")
            and detail.get("kind") == doc.get("kind")
            and detail.get("prediction_path")
            == path.relative_to(out).as_posix()
            and np.array_equal(
                np.asarray(detail.get("requested_theta"), dtype=float),
                np.asarray(row["theta"], dtype=float),
            ),
            "CHARGED_PREDICTION_CHARGE_METADATA",
        )
        require(
            np.array_equal(
                np.asarray(doc.get("requested_theta"), dtype=float),
                np.asarray(row["theta"], dtype=float),
            )
            and np.array_equal(
                np.asarray(doc.get("returned_theta"), dtype=float),
                np.asarray(row["theta"], dtype=float),
            )
            and np.array_equal(
                np.asarray(doc.get("theta"), dtype=float),
                np.asarray(row["theta"], dtype=float),
            ),
            "CHARGED_PREDICTION_REQUESTED_AND_RETURNED_THETA",
        )
        require(
            np.array_equal(
                np.asarray(doc.get("theta"), dtype=float),
                np.asarray(row["theta"], dtype=float),
            ),
            "CHARGED_PREDICTION_THETA",
        )
        c = np.ascontiguousarray(doc.get("C"), dtype=float)
        require(
            c.shape == (13, 13) and np.isfinite(c).all(),
            "CHARGED_PREDICTION_ARRAY",
        )
        c_hash = array_sha(c)
        require(c_hash == doc.get("C_sha256"), "CHARGED_PREDICTION_C_HASH")
        try:
            store.returned(
                task_id,
                row["seq"],
                "RETURNED",
                {
                    "ledger_seq": row["seq"],
                    "C_sha256": c_hash,
                    "prediction_path": path.relative_to(out).as_posix(),
                    "prediction_sha256": sha_file(path),
                    "recovered_after_charge": True,
                    "start_index": doc.get("start_index"),
                    "kind": doc.get("kind"),
                    "returned_theta": np.asarray(
                        doc.get("returned_theta"), dtype=float
                    ).tolist(),
                    "model_id": doc.get("model_id"),
                    "observation_metadata": doc.get("observation_metadata"),
                },
            )
        except Exception as exc:
            raise FatalPersistenceError(
                "RECONCILED_RETURN_NOT_DURABLE:"
                + task_id
                + ":"
                + str(row["seq"])
                + ":"
                + repr(exc)
            ) from exc
        recovered.append({"seq": row["seq"], "C_sha256": c_hash})
    return recovered


def task_db_state(execution_state: str) -> str:
    if execution_state == "FINISHED":
        return "FINISHED"
    if execution_state == "PARTIAL_SEARCH":
        return "PARTIAL_BUDGET"
    require(
        execution_state in ("FAILED", "BLOCKED"),
        "INVALID_EXECUTION_STATE:" + execution_state,
    )
    return "FAILED"


def seal_task_result(
    store: BudgetStore,
    task_id: str,
    sig: str,
    payload: dict,
    out: Path,
) -> dict:
    actual_calls = int(store.counts()[task_id])
    execution_state = payload.get("execution_state", "FAILED")
    db_state = task_db_state(execution_state)
    doc = {
        "schema": "iscat165.task_result.1",
        "task_id": task_id,
        "signature": sig,
        "execution_state": execution_state,
        "db_state": db_state,
        "actual_calls": actual_calls,
        "reportable_D": None,
        "payload": payload,
    }
    path = out / "tasks" / task_id / "result.json"
    atomic_json(path, doc)
    require(read_json(path) == doc, "TASK_RESULT_READBACK:" + task_id)
    store.seal(task_id, OWNER, db_state, path)
    return doc


def blocked_task_payload(
    store: BudgetStore,
    task_id: str,
    out: Path,
    reason_code: str,
) -> dict:
    """Preserve durable evidence without replaying an interrupted task."""
    starts = []
    start_dir = out / "tasks" / task_id / "starts"
    if start_dir.is_dir():
        for path in sorted(start_dir.glob("[0-9][0-9][0-9].json")):
            starts.append(read_json(path))
    valid = [
        row
        for row in starts
        if row.get("best") is not None
        and row.get("execution_state") in ("FINISHED", "PARTIAL_SEARCH")
    ]
    best = (
        min(valid, key=lambda row: row["best"]["Q_total"])["best"]
        if valid
        else None
    )
    prior_actual_calls = int(store.counts()[task_id])
    reason_codes = [reason_code]
    if starts or prior_actual_calls:
        # Only a task carrying durable charge or checkpoint evidence was actually
        # interrupted.  A task that never reached its first call is blocked before
        # any work, and must not be described as an unreplayed interruption.
        reason_codes.append("INTERRUPTED_TASK_NOT_REPLAYED")
    return {
        "execution_state": "BLOCKED",
        "task_id": task_id,
        "reason_codes": reason_codes,
        "prior_actual_calls": prior_actual_calls,
        "attempts": _attempt_rows(store, task_id),
        "starts": starts,
        "optimizer_best": best,
        "best_legal_witness": None,
        "theta": best.get("theta") if best else None,
        "candidate_D": (
            float(np.asarray(best["theta"], dtype=float)[0]) if best else None
        ),
        "candidate_D_nm": (
            float(np.asarray(best["theta"], dtype=float)[0]) if best else None
        ),
        "known_compatible_D_interval_nm": None,
        "known_compatible_components": [],
        "parameter_bounds_D_nm": [30.0, 200.0],
        "global_uniqueness_certified": False,
        "physical_qualification": "NOT_QUALIFIED_BLOCKED",
        "reportable_D": None,
    }


def seal_blocked_task(
    store: BudgetStore,
    task_id: str,
    sig: str,
    out: Path,
    reason_code: str,
) -> dict:
    row = _task_row(store, task_id)
    require(row["signature"] == sig, "TASK_SIGNATURE_CHANGED:" + task_id)
    if row["state"] != "RUNNING":
        return store.load_result(task_id, sig)
    reconcile_charged(store, task_id, out)
    payload = blocked_task_payload(store, task_id, out, reason_code)
    return seal_task_result(store, task_id, sig, payload, out)


def _adopt_durable_result(
    store: BudgetStore,
    task_id: str,
    sig: str,
    out: Path,
) -> dict | None:
    """Seal the ledger against a result file that survived an interruption."""
    result_path = out / "tasks" / task_id / "result.json"
    if not result_path.exists():
        return None
    reconcile_charged(store, task_id, out)
    doc = read_json(result_path)
    require(doc.get("signature") == sig, "ORPHAN_RESULT_SIGNATURE:" + task_id)
    store.seal(task_id, OWNER, doc["db_state"], result_path)
    return doc


def replay_or_block(
    store: BudgetStore,
    task_id: str,
    sig: str,
    out: Path,
    reason_code: str,
) -> dict:
    """Replay durable evidence for a task that cannot be run in this process.

    A task already holding a sealed result, or a result file awaiting adoption, is
    returned exactly as recorded.  Anything else is sealed honestly as BLOCKED with
    no charge and no recomputation.  This is the only route available to a dependent
    task when the process has no live model object.
    """
    row = _task_row(store, task_id)
    require(row["signature"] == sig, "TASK_SIGNATURE_CHANGED:" + task_id)
    if row["state"] != "RUNNING":
        return store.load_result(task_id, sig)
    durable = _adopt_durable_result(store, task_id, sig, out)
    if durable is not None:
        return durable
    return seal_blocked_task(store, task_id, sig, out, reason_code)


def execute_task(
    store: BudgetStore,
    task_id: str,
    sig: str,
    out: Path,
    work: Callable[[], dict],
) -> dict:
    row = _task_row(store, task_id)
    require(row["signature"] == sig, "TASK_SIGNATURE_CHANGED:" + task_id)
    if row["state"] != "RUNNING":
        return store.load_result(task_id, sig)

    durable = _adopt_durable_result(store, task_id, sig, out)
    if durable is not None:
        return durable

    if row["used"] > 0 and task_id not in (LOADER_TASK, BIND_TASK, FINAL_TASK):
        start_dir = out / "tasks" / task_id / "starts"
        start_files = (
            list(start_dir.glob("[0-9][0-9][0-9].json"))
            if start_dir.is_dir()
            else []
        )
        if not start_files:
            return seal_blocked_task(
                store,
                task_id,
                sig,
                out,
                "CHARGED_TASK_HAS_NO_DURABLE_START_CHECKPOINT",
            )
    if (
        row["used"] > 0
        and task_id in (LOADER_TASK, BIND_TASK, FINAL_TASK)
        and task_id != LOADER_TASK
    ):
        return seal_blocked_task(
            store,
            task_id,
            sig,
            out,
            "INTERRUPTED_TASK_NOT_REPLAYED",
        )

    try:
        payload = work()
    except FatalPersistenceError:
        raise
    except Exception as exc:
        payload = {
            "execution_state": "FAILED",
            "reason_codes": ["TASK_EXCEPTION"],
            "error_type": type(exc).__name__,
            "error": str(exc),
            "error_repr": repr(exc),
            "traceback": traceback.format_exc(),
            "reportable_D": None,
            "candidate_D": None,
            "candidate_D_nm": None,
            "known_compatible_D_interval_nm": None,
            "known_compatible_components": [],
            "parameter_bounds_D_nm": [30.0, 200.0],
            "global_uniqueness_certified": False,
            "physical_qualification": "NOT_QUALIFIED",
        }
    return seal_task_result(store, task_id, sig, payload, out)


def evaluate_stored(theta: Any, c: Any, data: GlsData, reading: HeightReading | None) -> dict:
    doc = augmented_objective(data, c, theta, reading)
    half = 0.5 * float(doc["residual"] @ doc["residual"])
    expected = 0.5 * (doc["Q_model"] + doc["Q_height"])
    require(
        abs(half - expected) <= max(1e-10, 1e-12 * max(1.0, abs(expected))),
        "SCIPY_HALF_COST_IDENTITY",
    )
    return {
        "theta": doc["theta"],
        "Q_frames": doc["Q_frames"],
        "Q_model": doc["Q_model"],
        "K": doc["K"],
        "Q_joint": doc["Q_joint"],
        "Q_height": doc["Q_height"],
        "Q_total": doc["Q_total"],
        "scipy_cost": half,
        "half_cost_identity_abs_error": half - expected,
        "residual": np.asarray(doc["residual"], dtype=float).tolist(),
        "reportable_D": None,
    }


def latest_best(path: Path) -> dict | None:
    return read_json(path) if path.exists() else None


def optimize_start(
    *,
    task_id: str,
    start_index: int,
    x0: Any,
    data: GlsData,
    reading: HeightReading | None,
    model: Any,
    store: BudgetStore,
    out: Path,
    prediction_writer: Callable[[Path, Any], str] | None = None,
) -> dict:
    from scipy.optimize import least_squares

    start_path = out / "tasks" / task_id / "starts" / f"{start_index:03d}.json"
    if start_path.exists():
        doc = read_json(start_path)
        if doc.get("execution_state") == "RUNNING":
            raw = start_path.read_bytes()
            preserved = start_path.with_name(
                f"{start_index:03d}.running_checkpoint.json"
            )
            write_once_bytes(preserved, raw)
            recovered = {
                "schema": "iscat165.start_result.1",
                "task_id": task_id,
                "start_index": start_index,
                "execution_state": "PARTIAL_SEARCH",
                "x0": doc.get("x0"),
                "actual_calls": int(store.counts()[task_id]),
                "local_cap": int(doc.get("local_cap", 200)),
                "calls_at_checkpoint": int(doc.get("calls_at_checkpoint", 0)),
                "charged_calls_at_checkpoint": int(
                    doc.get("charged_calls_at_checkpoint", 0)
                ),
                "best": doc.get("best_at_checkpoint"),
                "optimizer": None,
                "error": None,
                "reason_codes": [
                    "SCIPY_STATE_UNRECOVERABLE",
                    "RUNNING_CHECKPOINT_RECOVERED_WITHOUT_REPLAY",
                ],
                "preserved_running_checkpoint": preserved.relative_to(out).as_posix(),
                "reportable_D": None,
            }
            atomic_json(start_path, recovered)
            require(read_json(start_path) == recovered, "RECOVERED_START_READBACK")
            return recovered
        return doc

    t0 = check_theta(x0)
    before_calls = int(store.counts()[task_id])
    remaining = 400 - before_calls
    require(remaining > 0, "TASK_BUDGET_ALREADY_EXHAUSTED")
    local_cap = min(200, remaining)
    predictor = ModelPredictor(
        model,
        store,
        task_id,
        out,
        start_index=start_index,
        kind="OPTIMIZER",
        prediction_writer=prediction_writer,
    )
    best_path = out / "tasks" / task_id / "best" / f"start_{start_index:03d}.json"
    evaluations_dir = out / "tasks" / task_id / "evaluations"
    calls = 0
    best = None
    running = {
        "schema": "iscat165.start_checkpoint.1",
        "task_id": task_id,
        "start_index": start_index,
        "execution_state": "RUNNING",
        "x0": t0.tolist(),
        "local_cap": local_cap,
        "calls_at_checkpoint": 0,
        "best_at_checkpoint": None,
    }
    atomic_json(start_path, running)

    def residual(p: Any) -> np.ndarray:
        nonlocal calls, best
        theta = check_theta(p)
        if calls >= local_cap:
            raise CallCapReached("PER_START_REAL_MODEL_CALL_CAP")
        calls += 1
        try:
            prediction = predictor(theta)
        except FatalPersistenceError:
            raise
        score = evaluate_stored(theta, prediction["C"], data, reading)
        seq = prediction["seq"]
        evaluation = {
            "schema": "iscat165.evaluation.1",
            "task_id": task_id,
            "start_index": start_index,
            "seq": seq,
            "prediction_path": prediction["prediction_path"],
            "prediction_sha256": prediction["prediction_sha256"],
            "C_sha256": prediction["C_sha256"],
            **score,
        }
        eval_path = evaluations_dir / f"{seq:04d}.json"
        atomic_json(eval_path, evaluation)
        require(read_json(eval_path) == evaluation, "EVALUATION_READBACK")
        if best is None or score["Q_total"] < best["Q_total"]:
            best = evaluation
            atomic_json(best_path, best)
            require(read_json(best_path) == best, "BEST_EVALUATION_READBACK")
        return np.asarray(score["residual"], dtype=float)

    state = "FAILED"
    optimizer = None
    error = None
    try:
        optimizer = least_squares(
            residual,
            t0,
            bounds=(LOW, HIGH),
            method=OPTIMIZER["method"],
            jac=OPTIMIZER["jac"],
            loss=OPTIMIZER["loss"],
            diff_step=OPTIMIZER["diff_step"],
            x_scale=OPTIMIZER["x_scale"],
            ftol=OPTIMIZER["ftol"],
            xtol=OPTIMIZER["xtol"],
            gtol=OPTIMIZER["gtol"],
            max_nfev=OPTIMIZER["max_nfev"],
        )
        state = "FINISHED" if bool(optimizer.success) else "PARTIAL_SEARCH"
    except CallCapReached as exc:
        state = "PARTIAL_SEARCH"
        error = {
            "error_type": type(exc).__name__,
            "error": str(exc),
            "error_repr": repr(exc),
            "traceback": traceback.format_exc(),
        }
    except Exception as exc:
        state = "FAILED"
        error = {
            "error_type": type(exc).__name__,
            "error": str(exc),
            "error_repr": repr(exc),
            "traceback": traceback.format_exc(),
        }

    after_calls = int(store.counts()[task_id])
    actual_calls = after_calls - before_calls
    require(actual_calls <= local_cap, "PER_START_BUDGET_EXCEEDED")
    doc = {
        "schema": "iscat165.start_result.1",
        "task_id": task_id,
        "start_index": start_index,
        "execution_state": state,
        "x0": t0.tolist(),
        "actual_calls": actual_calls,
        "local_cap": local_cap,
        "best": best,
        "error": error,
        "optimizer": (
            {
                "success": bool(optimizer.success),
                "status": int(optimizer.status),
                "message": str(optimizer.message),
                "nfev": int(optimizer.nfev),
                "njev": int(optimizer.njev) if optimizer.njev is not None else None,
                "cost": float(optimizer.cost),
                "optimality": float(optimizer.optimality),
                "active_mask": np.asarray(optimizer.active_mask).astype(int).tolist(),
                "x": np.asarray(optimizer.x, dtype=float).tolist(),
            }
            if optimizer is not None
            else None
        ),
        "reportable_D": None,
    }
    atomic_json(start_path, doc)
    require(read_json(start_path) == doc, "START_RESULT_READBACK")
    require(actual_calls <= 200, "PER_START_HARD_CAP")
    return doc


def _witness_rows(
    group: str,
    context: dict,
    legal_group: dict,
    data: GlsData,
    reading: HeightReading | None,
) -> list[dict]:
    candidates = []
    seen = set()
    all_rows = [context] + legal_group["six"]
    for index, row in enumerate(all_rows):
        theta = np.asarray(row["theta"], dtype=float)
        if index == 0:
            c = np.asarray(
                context["predictions"][context["base_index"]]["C"], dtype=float
            )
            source = "V163_CURRENT_ANCHOR"
        else:
            c = np.asarray(row["C"], dtype=float)
            source = row.get("record_path", f"V152_LEGAL_{row['start_index']}")
        key = (
            tuple(theta.tolist()),
            array_sha(np.ascontiguousarray(c, dtype=np.float64)),
        )
        if key in seen:
            continue
        seen.add(key)
        score = evaluate_stored(theta, c, data, reading)
        candidates.append(
            {
                "theta": theta.tolist(),
                "C_sha256": array_sha(np.ascontiguousarray(c, dtype=np.float64)),
                "source": source,
                **score,
            }
        )
    require(candidates, "NO_LEGAL_WITNESS:" + group)
    return sorted(candidates, key=lambda r: r["Q_total"])


def fit_one_task(
    *,
    task: dict,
    data: GlsData,
    context: dict,
    legal_group: dict,
    fixed_starts: dict,
    reading: HeightReading | None,
    model: Any,
    store: BudgetStore,
    out: Path,
    prediction_writer: Callable[[Path, Any], str] | None = None,
) -> dict:
    task_id = task["task_id"]
    witnesses = _witness_rows(
        task["group"], context, legal_group, data, reading
    )
    legal_witness = witnesses[0]
    write_once_json(
        out / "tasks" / task_id / "legal_witnesses.json",
        {"schema": "iscat165.legal_witnesses.1", "task_id": task_id, "rows": witnesses},
    )
    starts = [fixed_starts["first"], fixed_starts["second"]]
    start_records = []
    for index, start in enumerate(starts):
        calls_before_start = int(store.counts()[task_id])
        try:
            record = optimize_start(
                task_id=task_id,
                start_index=index,
                x0=start["theta"],
                data=data,
                reading=reading,
                model=model,
                store=store,
                out=out,
                prediction_writer=prediction_writer,
            )
        except FatalPersistenceError:
            raise
        except Exception as exc:
            actual_calls = int(store.counts()[task_id]) - calls_before_start
            start_path = out / "tasks" / task_id / "starts" / f"{index:03d}.json"
            if start_path.exists():
                preserved = start_path.with_name(
                    f"{index:03d}.ordinary_failure_checkpoint.json"
                )
                write_once_bytes(preserved, start_path.read_bytes())
            start_records.append(
                {
                    "schema": "iscat165.start_result.1",
                    "task_id": task_id,
                    "start_index": index,
                    "execution_state": "FAILED",
                    "x0": list(check_theta(start["theta"])),
                    "actual_calls": actual_calls,
                    "error": {
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "error_repr": repr(exc),
                        "traceback": traceback.format_exc(),
                    },
                    "best": None,
                    "optimizer": None,
                    "reportable_D": None,
                }
            )
            atomic_json(start_path, start_records[-1])
            require(
                read_json(start_path) == start_records[-1],
                "FAILED_START_READBACK:" + task_id,
            )
            continue
        start_records.append(record)

    valid = [
        r
        for r in start_records
        if r.get("best") is not None
        and r["execution_state"] in ("FINISHED", "PARTIAL_SEARCH")
    ]
    failed_starts = [
        r for r in start_records if r["execution_state"] in ("FAILED", "BLOCKED")
    ]
    if not valid:
        return {
            "execution_state": "FAILED",
            "task_id": task_id,
            "group": task["group"],
            "replicate": task["replicate"],
            "sigma_nm": task["sigma_nm"],
            "reading_id": reading.reading_id if reading else None,
            "starts": start_records,
            "best_legal_witness": legal_witness,
            "fatal_error": None,
            "candidate_D": None,
            "candidate_D_nm": None,
            "theta": None,
            "known_compatible_D_interval_nm": None,
            "known_compatible_components": [],
            "parameter_bounds_D_nm": [30.0, 200.0],
            "reportable_D": None,
            "reason_codes": ["NO_VALID_OPTIMIZER_WITNESS"],
        }

    optimizer_best = min(valid, key=lambda r: r["best"]["Q_total"])["best"]
    tolerance = max(1e-9, 1e-10 * max(1.0, abs(legal_witness["Q_total"])))
    if optimizer_best["Q_total"] > legal_witness["Q_total"] + tolerance:
        return {
            "execution_state": "FAILED",
            "task_id": task_id,
            "group": task["group"],
            "replicate": task["replicate"],
            "sigma_nm": task["sigma_nm"],
            "reading_id": reading.reading_id if reading else None,
            "starts": start_records,
            "optimizer_best": optimizer_best,
            "best_legal_witness": legal_witness,
            "candidate_D": None,
            "candidate_D_nm": None,
            "theta": None,
            "known_compatible_D_interval_nm": None,
            "known_compatible_components": [],
            "parameter_bounds_D_nm": [30.0, 200.0],
            "reportable_D": None,
            "reason_codes": ["SEARCH_INCOMPLETE_OR_IMPLEMENTATION_ERROR"],
        }

    partial = any(r["execution_state"] == "PARTIAL_SEARCH" for r in start_records)
    resumed_after_failure = bool(failed_starts) and any(
        int(r["start_index"]) > 0 for r in valid
    )
    execution_state = (
        "PARTIAL_SEARCH" if partial or resumed_after_failure else "FINISHED"
    )
    theta = np.asarray(optimizer_best["theta"], dtype=float).tolist()
    reason_codes = [
        "OPENED_DEVELOPMENT_SIMULATED_HEIGHT_READINGS",
        "ALL_REPORTABLE_D_NULL",
        "LOCAL_BOUNDED_SEARCH_NOT_GLOBAL_UNIQUENESS",
    ]
    if partial:
        reason_codes.append("PARTIAL_SEARCH")
    if resumed_after_failure:
        reason_codes.append("START_0_FAILED_CONTINUED_TO_START_1")
    return {
        "execution_state": execution_state,
        "task_id": task_id,
        "group": task["group"],
        "replicate": task["replicate"],
        "sigma_nm": task["sigma_nm"],
        "reading_id": reading.reading_id if reading else None,
        "starts": start_records,
        "optimizer_best": optimizer_best,
        "best_legal_witness": legal_witness,
        "development_diagnostic_pool_best": (
            optimizer_best
            if optimizer_best["Q_total"] <= legal_witness["Q_total"]
            else legal_witness
        ),
        "theta": theta,
        "candidate_D_nm": float(theta[0]),
        "candidate_D": float(theta[0]),
        "candidate_h_nm": float(theta[1]),
        "candidate_x_nm": float(theta[2]),
        "candidate_y_nm": float(theta[3]),
        "known_compatible_D_interval_nm": None,
        "known_compatible_components": [],
        "parameter_bounds_D_nm": [30.0, 200.0],
        "D_domain_is_not_a_compatibility_claim": True,
        "global_uniqueness_certified": False,
        "physical_qualification": "CONDITIONAL_SIMULATED_F2C_DEVELOPMENT",
        "reportable_D": None,
        "reason_codes": reason_codes,
        "actual_new_calls": int(store.counts()[task_id]),
    }


def _load_contexts(out: Path) -> dict[str, dict]:
    # The three-frame Y/V files were copied and hashed by preflight.  Re-checking the
    # recorded copy hash here is what stops a swapped variance or rewritten frame file
    # from reaching the fit after the gate has already passed.
    pinned = read_json(out / "preflight.json")["contexts"]
    contexts = {}
    for group in ("ANON_01", "ANON_02", "ANON_03", "ANON_04"):
        path = out / "source_context" / f"{group}.json"
        require(path.is_file(), "MISSING_CONTEXT:" + group)
        require(
            sha_file(path) == (pinned.get(group) or {}).get("copy_sha256"),
            "CONTEXT_BYTES_CHANGED_SINCE_PREFLIGHT:" + group,
        )
        d = read_json(path)["diagnostic"]
        require(
            np.asarray(d["frame_Y"]).shape == (3, 13, 13)
            and np.asarray(d["frame_V"]).shape == (3, 13, 13),
            "THREE_FRAME_CONTEXT_REQUIRED:" + group,
        )
        GlsData.from_frames(d["frame_Y"], d["frame_V"])
        contexts[group] = d
    return contexts


def _readings(path: Path) -> tuple[dict, dict[str, HeightReading]]:
    from v165_io import estimator_inputs_check, public_readings_check

    doc = read_json(path)
    public_readings_check(doc)
    estimator_inputs_check({"height_readings": doc})
    mapped = {}
    for row in doc["readings"]:
        reading = HeightReading(
            row["reading_id"],
            row["group"],
            row["replicate"],
            float(row["sigma_nm"]),
            float(row["z_nm"]),
            bool(row["hypothetical"]),
        )
        mapped[reading.reading_id] = reading
    return doc, mapped


def _model_modules(repo: Path):
    tools = (repo / "tools").resolve()
    sys.path.insert(0, str(tools))
    runtime = importlib.import_module("v146_runtime")
    fields = importlib.import_module("field_forward_reference")
    require(
        Path(runtime.__file__).resolve() == tools / "v146_runtime.py",
        "WRONG_RUNTIME_MODULE",
    )
    require(
        Path(fields.__file__).resolve() == tools / "field_forward_reference.py",
        "WRONG_FIELD_MODULE",
    )
    return runtime, fields


def construct_model(
    repo: Path,
    store: BudgetStore,
    out: Path,
    task_id: str,
    *,
    prediction_writer: Callable[[Path, Any], str] | None = None,
) -> tuple[Any, dict]:
    runtime, fields = _model_modules(repo)
    caller = ChargedCaller(
        store,
        task_id,
        out,
        kind="MODEL_LOADER",
        prediction_writer=prediction_writer,
        allow_exact_reuse=False,
    )
    loaded = []
    original = fields.FieldForward.forward

    def wrapped(instance, theta):
        call_info = caller.call(theta, lambda t: original(instance, t))
        result = call_info["model_output"]
        loaded.append(
            {
                "theta": np.asarray(theta, dtype=float).tolist(),
                "ledger_seq": int(call_info["seq"]),
            }
        )
        return result

    fields.FieldForward.forward = wrapped
    try:
        cfg = read_json(repo / "config/v146_science_config.json")
        model = runtime.construct_bound(repo, cfg)
    finally:
        fields.FieldForward.forward = original
    require(model.model_id == MODEL_ID, "F2C_MODEL_ID_CHANGED")
    attempts = _attempt_rows(store, task_id)
    loader_rows = []
    for row in attempts:
        if row["state"] != "RETURNED":
            loader_rows.append(
                {
                    "seq": row["seq"],
                    "state": row["state"],
                    "detail": row["detail"],
                }
            )
            continue
        loader_rows.append(
            {
                "seq": row["seq"],
                "state": row["state"],
                "C_sha256": row["detail"].get("C_sha256"),
                "prediction_path": row["detail"].get("prediction_path"),
            }
        )
    return model, {
        "model_id": model.model_id,
        "model_module": str(Path(sys.modules["v142_model"].__file__).resolve()),
        "loader_attempts": loader_rows,
        "loader_calls": len(attempts),
        "wrapped_forward_calls": loaded,
    }


def binding_task(
    model: Any,
    store: BudgetStore,
    out: Path,
    legal: dict,
    *,
    prediction_writer: Callable[[Path, Any], str] | None = None,
) -> dict:
    predictor = ModelPredictor(
        model,
        store,
        BIND_TASK,
        out,
        kind="SOURCE_BINDING",
        prediction_writer=prediction_writer,
    )
    rows = []
    for group in ("ANON_01", "ANON_02", "ANON_03", "ANON_04"):
        for source in legal[group]["six"]:
            prediction = predictor(source["theta"])
            expected = np.asarray(source["C"], dtype=float)
            actual = prediction["C"]
            require(
                np.allclose(actual, expected, rtol=1e-10, atol=1e-12),
                "BINDING_PIXEL_REPLAY_FAILED:" + group,
            )
            rows.append(
                {
                    "group": group,
                    "source_record": source["record_path"],
                    "theta": np.asarray(source["theta"], dtype=float).tolist(),
                    "seq": prediction["seq"],
                    "C_sha256": prediction["C_sha256"],
                    "max_abs_source_difference": float(
                        np.max(np.abs(actual - expected))
                    ),
                }
            )
    return {
        "execution_state": "FINISHED",
        "model_id": model.model_id,
        "bound_legal_records": len(rows),
        "rows": rows,
        "reportable_D": None,
    }


def final_verify_task(
    repo: Path,
    store: BudgetStore,
    out: Path,
    contexts: dict,
    fit_payloads: dict[str, dict],
    *,
    prediction_writer: Callable[[Path, Any], str] | None = None,
    model: Any | None = None,
) -> dict:
    # ``execute`` always routes this task through the single live model of the
    # process, or blocks it outright.  The fallback below therefore only ever runs
    # for a direct in-process caller, and the sealed record says which case applied.
    if model is None:
        model_source = "CONSTRUCTED_WITHIN_FINAL_VERIFY_CALLER"
        model, load_info = construct_model(
            repo,
            store,
            out,
            FINAL_TASK,
            prediction_writer=prediction_writer,
        )
    else:
        model_source = "PROCESS_LIVE_MODEL"
        load_info = None
    predictor = ModelPredictor(
        model,
        store,
        FINAL_TASK,
        out,
        kind="INDEPENDENT_FINAL",
        prediction_writer=prediction_writer,
    )
    checks = []
    failures = []
    for task_id, payload in fit_payloads.items():
        theta = payload.get("theta")
        if theta is None:
            checks.append(
                {
                    "kind": "TASK_NOT_VERIFIABLE",
                    "task_id": task_id,
                    "execution_state": payload.get("execution_state"),
                    "reason_codes": payload.get("reason_codes", []),
                }
            )
            continue
        best = payload.get("optimizer_best")
        require(best is not None, "MISSING_OPTIMIZER_BEST:" + task_id)
        prediction = predictor(theta)
        expected_hash = best.get("C_sha256")
        if prediction["C_sha256"] != expected_hash:
            failures.append(
                {
                    "kind": "TASK_PREDICTION_HASH",
                    "task_id": task_id,
                    "expected": expected_hash,
                    "actual": prediction["C_sha256"],
                }
            )
        checks.append(
            {
                "kind": "TASK_CANDIDATE",
                "task_id": task_id,
                "theta": theta,
                "seq": prediction["seq"],
                "C_sha256": prediction["C_sha256"],
                "expected_C_sha256": expected_hash,
            }
        )
    for group, d in contexts.items():
        theta = d["theta"]
        prediction = predictor(theta)
        expected = np.asarray(
            d["predictions"][d["base_index"]]["C"], dtype=float
        )
        ok = np.allclose(
            prediction["C"], expected, rtol=1e-10, atol=1e-12
        )
        if not ok:
            failures.append(
                {
                    "kind": "ANCHOR_PIXELS",
                    "group": group,
                    "max_abs": float(np.max(np.abs(prediction["C"] - expected))),
                }
            )
        checks.append(
            {
                "kind": "GROUP_ANCHOR",
                "group": group,
                "theta": theta,
                "seq": prediction["seq"],
                "C_sha256": prediction["C_sha256"],
            }
        )
    return {
        "execution_state": "FINISHED" if not failures else "FAILED",
        "model_id": model.model_id,
        "model_source": model_source,
        "fresh_model_loader": load_info,
        "checks": checks,
        "failures": failures,
        "not_verifiable_task_count": sum(
            row.get("kind") == "TASK_NOT_VERIFIABLE" for row in checks
        ),
        "reportable_D": None,
        "reason_codes": [] if not failures else ["INDEPENDENT_FINAL_REPLAY_FAILED"],
    }


def _profile_group(task_id: str) -> str:
    """Full ANON group name out of a profile task id such as
    ``PROFILE_100000_ANON_02_m5_free_hxy``.

    Group names carry an underscore themselves, so a fixed split index would
    truncate ANON_01 to ANON and silently collapse four scenes into one label.
    """
    parts = task_id.split("_")
    require(
        task_id.startswith("PROFILE_") and len(parts) >= 4 and parts[2] == "ANON",
        "PROFILE_TASK_ID_SHAPE:" + task_id,
    )
    return "_".join(parts[2:4])


def _history_audit(repo: Path) -> dict:
    from v165_io import archive_check, ledger_check

    v164 = repo / "results/v164"
    archive = archive_check(v164 / "iscat_v164_return.zip")
    ledger = ledger_check(
        v164,
        plan_id="v164",
        phases={
            "MODEL_BINDING": 160,
            "FIXED_D_DESIGN": 9600,
            "FINAL_VERIFY": 240,
        },
        expected_total=1357,
        hash_only_arrays_tasks=("LOADER_1",),
    )
    groups = {_profile_group(t["task"]) for t in ledger["tasks"] if t["task"].startswith("PROFILE_")}
    require(groups == {"ANON_02", "ANON_03", "ANON_04"}, "V164_GROUP_HISTORY")
    return {
        "schema": "iscat165.v164_history_audit.1",
        "archive": archive,
        "ledger": ledger,
        "v164_profiled_groups": sorted(groups),
        "ANON_01_V164_FREE_HXY_WITNESS_UNAVAILABLE": True,
        "scope": "READ_ONLY_HISTORICAL_EVIDENCE_NOT_REEXECUTED",
    }


def _gate_a_receipt(receipt_path: Path, projection_path: Path) -> dict:
    receipt = read_json(receipt_path)
    require(receipt.get("status") == "PASS", "GATE_A_RECEIPT_NOT_PASS")
    require(receipt.get("projection_status") == "PASS", "GATE_A_PROJECTION_STATUS")
    projection_sha = sha_file(projection_path)
    require(
        receipt.get("projection_sha256") == projection_sha,
        "GATE_A_PROJECTION_SHA_NOT_RECEIPTED",
    )
    require(
        receipt.get("full_report_sha256")
        and len(receipt["full_report_sha256"]) == 64,
        "GATE_A_FULL_REPORT_SHA",
    )
    for raw_path, expected in receipt.get("source_sha256", {}).items():
        p = Path(raw_path)
        if not p.is_absolute():
            continue
        require(p.is_file(), "GATE_A_SOURCE_MISSING:" + str(p))
        require(sha_file(p) == expected, "GATE_A_SOURCE_CHANGED:" + str(p))
    return receipt


def preflight(repo: Path, out: Path, projection: Path, gate_receipt: Path) -> dict:
    from v165_io import (
        assert_no_truth_literals,
        camera_binding,
        frozen_starts,
        install_check,
        lock_sources,
    )
    from v165_receipts import verify_receipt

    repo = Path(repo).resolve()
    out = Path(out).resolve()
    bundle = repo / "tools/v165_bundle"
    require(bundle.is_dir(), "INSTALL_COMPLETE_BUNDLE")
    test_receipt = verify_receipt(bundle, out / "workstation_tests/production_001")
    require(
        git(repo, "merge-base", "--is-ancestor", PARENT, "HEAD") == b"",
        "WRONG_V165_PARENT",
    )
    head = git(repo, "rev-parse", "HEAD").decode().strip()
    from v165_receipts import hashes

    for rel in hashes(bundle):
        path = bundle / rel
        rel_repo = path.relative_to(repo).as_posix()
        require(
            git(repo, "rev-parse", "HEAD:" + rel_repo).decode().strip() == blob(path),
            "UNCOMMITTED_EXECUTION_CODE:" + rel_repo,
        )
    install = install_check(bundle)
    literals = assert_no_truth_literals(bundle / "code")
    cfg = read_json(bundle / "config/v165_plan.json")
    require(cfg["reviewed_v164_head"] == PARENT, "PLAN_PARENT")
    require(cfg["frozen_model_id"] == MODEL_ID, "PLAN_MODEL")
    require(cfg["phases"] == PHASES and cfg["max_new_model_forward_attempts"] == TOTAL, "PLAN_BUDGET")
    require(cfg["total_fits"] == 28 and cfg["starts_per_fit"] == 2, "PLAN_TASKS")
    require(cfg["optimizer"]["jac"] == "3-point", "PLAN_OPTIMIZER_JAC")
    require(cfg["optimizer"]["diff_step"] == 1e-5, "PLAN_OPTIMIZER_DIFF")
    require(cfg["optimizer"]["x_scale"] == OPTIMIZER["x_scale"], "PLAN_OPTIMIZER_SCALE")
    require(cfg["all_reportable_D_null"] is True, "PLAN_REPORTABILITY")
    for key in (
        "new_BEM",
        "new_render",
        "new_camera_exposures",
        "new_camera_noise_draws",
        "new_Jacobian_batch",
        "new_second_focus",
        "new_fixed_D_profiles",
    ):
        require(cfg[key] == 0, "FORBIDDEN_WORK_ENABLED:" + key)

    gate = _gate_a_receipt(Path(gate_receipt), Path(projection))
    projection_doc = read_json(projection)
    require(projection_doc.get("status") == "PASS", "GATE_A_PROJECTION_NOT_PASS")
    require(projection_doc.get("pass_") is True, "GATE_A_PROJECTION_PASS_FLAG")
    require(
        all(projection_doc.get("checks", {}).values()),
        "GATE_A_PROJECTION_CHECK_FAILED",
    )
    require(
        projection_doc.get("full_report_sha256")
        == gate.get("full_report_sha256"),
        "GATE_A_FULL_REPORT_BINDING",
    )

    sources = lock_sources(repo)
    cfg146 = read_json(repo / "config/v146_science_config.json")
    camera = camera_binding(repo, cfg146)
    history = _history_audit(repo)
    starts = frozen_starts(repo, list(cfg["groups"]))
    contexts = {}
    for group in cfg["groups"]:
        source = repo / f"results/v163/source_context/v156/100000_{group}.json"
        raw = source.read_bytes()
        target = out / "source_context" / f"{group}.json"
        write_once_bytes(target, raw)
        d = read_json(target)["diagnostic"]
        GlsData.from_frames(d["frame_Y"], d["frame_V"])
        contexts[group] = {
            "source_path": source.relative_to(repo).as_posix(),
            "copy_path": target.relative_to(out).as_posix(),
            "source_sha256": sha_file(source),
            "copy_sha256": sha_file(target),
        }

    projection_copy = out / "preflight/gate_a_projection.json"
    write_once_bytes(projection_copy, Path(projection).read_bytes())
    receipt_copy = out / "preflight/gate_a_receipt.json"
    write_once_bytes(receipt_copy, Path(gate_receipt).read_bytes())
    detections = out / "frozen_detections.json"
    write_once_json(detections, projection_doc["detections"])
    write_once_json(
        out / "starts_by_group.json",
        {
            g: {
                "first": {
                    "theta": starts[g]["first"]["theta"],
                    "source_record": starts[g]["first"]["record_path"],
                },
                "second": {
                    "theta": starts[g]["second"]["theta"],
                    "source_record": starts[g]["second"]["record_path"],
                },
                "stratum_available": starts[g]["stratum_available"],
                "stratum_flag": starts[g]["stratum_flag"],
                "all_six": starts[g]["all_six"],
            }
            for g in cfg["groups"]
        },
    )
    pre = {
        "schema": "iscat165.preflight.1",
        "status": "PASS",
        "parent": PARENT,
        "head": head,
        "plan_sha256": sha_file(bundle / "config/v165_plan.json"),
        "test_receipt": test_receipt,
        "install_check": install,
        "truth_literal_scan": literals,
        "gate_a_receipt_sha256": sha_file(gate_receipt),
        "gate_a_projection_sha256": sha_file(projection),
        "gate_a_full_report_sha256": gate["full_report_sha256"],
        "camera_binding": camera,
        "history": history,
        "source_lock": sources,
        "contexts": contexts,
        "frozen_starts": {
            g: {
                "first_theta": starts[g]["first"]["theta"],
                "second_theta": starts[g]["second"]["theta"],
                "stratum_available": starts[g]["stratum_available"],
            }
            for g in cfg["groups"]
        },
        "model_calls": 0,
        "new_BEM": 0,
        "new_render": 0,
        "new_camera_exposures": 0,
        "new_camera_noise_draws": 0,
        "new_fixed_D_profiles": 0,
        "scope": "READ_ONLY_PREFLIGHT_NOT_A_SIZING_RESULT",
    }
    write_once_json(out / "preflight.json", pre)
    write_once_json(out / "history_forensics.json", history)
    write_once_json(out / "source_lock.json", sources)
    return pre


def execute(
    repo: Path,
    out: Path,
    readings_path: Path,
    *,
    resume: bool,
    prediction_writer: Callable[[Path, Any], str] | None = None,
) -> dict:
    from v165_guard import install
    from v165_io import estimator_inputs_check, frozen_starts, ledger_check, lock_sources

    repo = Path(repo).resolve()
    out = Path(out).resolve()
    pre = read_json(out / "preflight.json")
    require(pre.get("status") == "PASS", "PREFLIGHT_NOT_PASS")
    require(
        lock_sources(repo) == pre["source_lock"],
        "SOURCE_CHANGED_AFTER_PREFLIGHT",
    )
    guard = install(repo)
    readings_doc, reading_map = _readings(Path(readings_path))
    estimator_inputs_check(
        {
            "height_readings": readings_doc,
            "frozen_detections": read_json(out / "frozen_detections.json"),
        }
    )
    contexts = _load_contexts(out)
    starts = frozen_starts(repo, ["ANON_01", "ANON_02", "ANON_03", "ANON_04"])
    fixed_doc = read_json(out / "starts_by_group.json")
    for group in starts:
        require(
            fixed_doc[group]["first"]["theta"] == starts[group]["first"]["theta"],
            "FIXED_START_FIRST_CHANGED",
        )
        require(
            fixed_doc[group]["second"]["theta"] == starts[group]["second"]["theta"],
            "FIXED_START_SECOND_CHANGED",
        )

    plan_sha = pre["plan_sha256"]
    preflight_sha = sha_file(out / "preflight.json")
    sigs = signatures(plan_sha, preflight_sha)
    ledger_path = out / "logs/v165_budget.sqlite"
    if ledger_path.exists() and not resume:
        raise FileExistsError("EXISTING_V165_LEDGER_REQUIRES_RESUME")
    store = BudgetStore(ledger_path, PLAN_ID, PHASES, TOTAL)
    reserve_plan(store, sigs)
    for task_id in sigs:
        reconcile_charged(store, task_id, out)

    legal = frozen_starts(
        repo, ["ANON_01", "ANON_02", "ANON_03", "ANON_04"]
    )
    live: dict[str, Any] = {}

    def _loader_work() -> dict:
        built, info = construct_model(
            repo,
            store,
            out,
            LOADER_TASK,
            prediction_writer=prediction_writer,
        )
        live["model"] = built
        return {
            **info,
            "execution_state": "FINISHED",
            "reportable_D": None,
        }

    loader = execute_task(
        store, LOADER_TASK, sigs[LOADER_TASK]["signature"], out, _loader_work
    )
    if loader["execution_state"] != "FINISHED":
        raise RunError("LOADER_TASK_NOT_FINISHED")
    # A sealed loader result carries no live model object and the loader task is
    # never charged twice.  A restart therefore must not rebuild one silently: the
    # model exists only if this process constructed it exactly once.  Otherwise every
    # dependent task is replayed from durable evidence or blocked explicitly.
    model = live.get("model")

    def _dependent(task_id: str, work: Callable[[], dict]) -> dict:
        sig = sigs[task_id]["signature"]
        if model is not None:
            return execute_task(store, task_id, sig, out, work)
        return replay_or_block(
            store,
            task_id,
            sig,
            out,
            "BLOCKED_MODEL_RESTART_REQUIRES_AUTHORIZATION",
        )

    binding = _dependent(
        BIND_TASK,
        lambda: binding_task(
            model,
            store,
            out,
            legal,
            prediction_writer=prediction_writer,
        ),
    )
    fit_payloads: dict[str, dict] = {}
    for task in tasks():
        task_id = task["task_id"]
        group = task["group"]
        reading = (
            reading_map[task_id] if task["sigma_nm"] is not None else None
        )
        if reading is not None:
            require(
                reading.group == group
                and reading.replicate == task["replicate"]
                and reading.sigma_nm == task["sigma_nm"],
                "HEIGHT_READING_TASK_BINDING:" + task_id,
            )
        data = GlsData.from_frames(
            contexts[group]["frame_Y"], contexts[group]["frame_V"]
        )
        doc = _dependent(
            task_id,
            lambda task=task, data=data, reading=reading, group=group: fit_one_task(
                task=task,
                data=data,
                context=contexts[group],
                legal_group=legal[group],
                fixed_starts=starts[group],
                reading=reading,
                model=model,
                store=store,
                out=out,
                prediction_writer=prediction_writer,
            ),
        )
        fit_payloads[task_id] = doc["payload"]

    final = _dependent(
        FINAL_TASK,
        lambda: final_verify_task(
            repo,
            store,
            out,
            contexts,
            fit_payloads,
            prediction_writer=prediction_writer,
            model=model,
        ),
    )
    write_once_json(
        out / "fits_all.json",
        [fit_payloads[t["task_id"]] for t in tasks()],
    )
    guard_report = guard.report()
    write_once_json(out / "estimator_guard.json", guard_report)
    fit_states = [payload["execution_state"] for payload in fit_payloads.values()]
    require(len(fit_states) == 28, "FIT_TASK_ACCOUNTING")
    fit_finished = sum(state == "FINISHED" for state in fit_states)
    fit_partial_search = sum(state == "PARTIAL_SEARCH" for state in fit_states)
    fit_failed = sum(state == "FAILED" for state in fit_states)
    fit_blocked = sum(state == "BLOCKED" for state in fit_states)
    require(
        fit_finished + fit_partial_search + fit_failed + fit_blocked == 28,
        "FIT_STATE_ACCOUNTING_INCOMPLETE",
    )
    gate_states = [
        loader["execution_state"],
        binding["execution_state"],
        final["execution_state"],
    ]
    if any(state in ("BLOCKED", "FAILED") for state in fit_states + gate_states):
        execution_state = "BLOCKED_OR_PARTIAL"
    elif "PARTIAL_SEARCH" in fit_states:
        execution_state = "FINISHED_WITH_PARTIAL_SEARCH"
    else:
        execution_state = "FINISHED"
    status = {
        "schema": "iscat165.execute_status.1",
        "execution_state": execution_state,
        "model_calls": int(sum(store.counts().values())),
        "phase_caps": PHASES,
        "tasks_reserved": len(store.counts()),
        "fit_tasks": len(fit_states),
        "fit_finished": fit_finished,
        "fit_partial_search": fit_partial_search,
        "fit_failed": fit_failed,
        "fit_blocked": fit_blocked,
        "final_verify_execution_state": final["execution_state"],
        "binding_execution_state": binding["execution_state"],
        "all_reportable_D_null": all(
            payload.get("reportable_D") is None
            for payload in [loader["payload"], binding["payload"], final["payload"]]
            + list(fit_payloads.values())
        ),
        "experimental_absolute_diameter_validated": False,
        "scope": "OPENED_DEVELOPMENT_SIMULATED_HEIGHT_READINGS_NOT_REAL_SIZING",
    }
    write_once_json(out / "execute_status.json", status)
    return status


def seal_estimates(repo: Path, out: Path) -> dict:
    from v165_io import ledger_check

    repo = Path(repo).resolve()
    out = Path(out).resolve()
    pre = read_json(out / "preflight.json")
    ledger = ledger_check(
        out,
        plan_id=PLAN_ID,
        phases=PHASES,
    )
    require(len(ledger["tasks"]) == 31, "SEAL_REQUIRES_31_SEALED_TASKS")
    sigs = signatures(
        pre["plan_sha256"], sha_file(out / "preflight.json")
    )
    rows = []
    for task in tasks():
        task_id = task["task_id"]
        result_path = out / "tasks" / task_id / "result.json"
        require(result_path.is_file(), "ESTIMATE_RESULT_MISSING:" + task_id)
        result = read_json(result_path)
        require(
            result["signature"] == sigs[task_id]["signature"],
            "ESTIMATE_TASK_SIGNATURE:" + task_id,
        )
        payload = result["payload"]
        execution_state = payload["execution_state"]
        qualification = payload.get("physical_qualification")
        if qualification is None:
            # Two fit failure paths carry no qualification of their own.  A failed
            # or blocked task must never inherit the qualification of a completed
            # one, so the label is derived from this task's own state.
            qualification = (
                "CONDITIONAL_SIMULATED_F2C_DEVELOPMENT"
                if execution_state in ("FINISHED", "PARTIAL_SEARCH")
                else "NOT_QUALIFIED_" + execution_state
            )
        rows.append(
            {
                "task_id": task_id,
                "group": task["group"],
                "replicate": task["replicate"],
                "sigma_nm": task["sigma_nm"],
                "execution_state": payload["execution_state"],
                "reading_id": payload.get("reading_id"),
                "theta": payload.get("theta"),
                "candidate_D": payload.get("candidate_D"),
                "reportable_D": None,
                "known_compatible_D_interval_nm": payload.get("known_compatible_D_interval_nm"),
                "global_uniqueness_certified": False,
                "physical_qualification": qualification,
                "reason_codes": payload.get("reason_codes", []),
                "task_result_sha256": sha_file(result_path),
            }
        )
    require(len(rows) == 28, "ESTIMATE_COUNT")
    estimate_path = out / "estimates.json"
    write_once_json(estimate_path, rows)
    estimate_sha = sha_file(estimate_path)
    sha_path = out / "estimates.sha256"
    write_once_bytes(sha_path, (estimate_sha + "\n").encode("ascii"))
    seal = {
        "schema": "iscat165.estimate_seal.1",
        "status": "SEALED_BEFORE_VALIDATOR",
        "estimates_sha256": estimate_sha,
        "ledger_sha256": sha_file(out / "logs/v165_budget.sqlite"),
        "preflight_sha256": sha_file(out / "preflight.json"),
        "height_readings_sha256": sha_file(
            out / "height_input/height_readings.json"
        ),
        "task_result_sha256": {
            t["task_id"]: sha_file(out / "tasks" / t["task_id"] / "result.json")
            for t in tasks()
        },
        "execution_code_head": git(repo, "rev-parse", "HEAD")
        .decode()
        .strip(),
        "validator_may_read_truth_after_this_point_only": True,
        "all_reportable_D_null": True,
        "experimental_absolute_diameter_validated": False,
    }
    write_once_json(out / "seal.json", seal)
    return seal


def verify_readonly(repo: Path, out: Path) -> dict:
    from v165_io import ledger_check, lock_sources
    from v165_receipts import verify_receipt

    repo = Path(repo).resolve()
    out = Path(out).resolve()
    bundle = repo / "tools/v165_bundle"
    receipt = verify_receipt(bundle, out / "workstation_tests/production_001")
    pre = read_json(out / "preflight.json")
    require(lock_sources(repo) == pre["source_lock"], "SOURCE_CHANGED")
    ledger = ledger_check(out, plan_id=PLAN_ID, phases=PHASES)
    require(len(ledger["tasks"]) == 31, "LEDGER_TASK_COUNT")
    sigs = signatures(
        pre["plan_sha256"], sha_file(out / "preflight.json")
    )
    task_results = {}
    for task_id, item in sigs.items():
        result = read_json(out / "tasks" / task_id / "result.json")
        require(
            result["signature"] == item["signature"]
            and result["actual_calls"] == next(
                r["used"] for r in ledger["tasks"] if r["task"] == task_id
            ),
            "TASK_RESULT_LEDGER_BINDING:" + task_id,
        )
        task_results[task_id] = result
    estimates = read_json(out / "estimates.json")
    require(len(estimates) == 28, "ESTIMATE_COUNT")
    expected_ids = {t["task_id"] for t in tasks()}
    require(
        {r["task_id"] for r in estimates} == expected_ids,
        "ESTIMATE_TASK_SET",
    )
    require(
        sha_file(out / "estimates.json")
        == (out / "estimates.sha256").read_text(encoding="ascii").strip(),
        "ESTIMATE_SHA",
    )
    require(
        read_json(out / "seal.json")["estimates_sha256"]
        == sha_file(out / "estimates.json"),
        "SEAL_ESTIMATE_SHA",
    )
    final = task_results[FINAL_TASK]["payload"]
    report = {
        "schema": "iscat165.readonly_verification.1",
        "status": "LEDGER_AND_ARTIFACT_BINDING_VERIFIED",
        "test_receipt_sha256": receipt["output_sha256"],
        "ledger": ledger,
        "task_count": 31,
        "fit_task_count": 28,
        "estimate_sha256": sha_file(out / "estimates.json"),
        "final_verify_execution_state": final["execution_state"],
        "final_verify_failures": final.get("failures", []),
        "all_reportable_D_null": all(
            r["reportable_D"] is None for r in estimates
        ),
        "experimental_absolute_diameter_validated": False,
        "new_model_calls": 0,
        "scope": "READ_ONLY_MECHANICAL_AND_NUMERICAL_BINDING_CHECK",
    }
    require(report["all_reportable_D_null"], "REPORTABILITY_MUST_BE_NULL")
    write_once_json(out / "verification.json", report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        choices=("preflight", "execute", "seal-estimates", "verify"),
    )
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--projection", type=Path)
    parser.add_argument("--gate-receipt", type=Path)
    parser.add_argument("--readings", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    out = (args.out or (repo / "results/v165")).resolve()
    try:
        if args.mode == "preflight":
            require(args.projection and args.gate_receipt, "PREFLIGHT_ARGUMENTS")
            result = preflight(
                repo, out, args.projection.resolve(), args.gate_receipt.resolve()
            )
        elif args.mode == "execute":
            require(args.readings, "EXECUTE_REQUIRES_READINGS")
            result = execute(
                repo, out, args.readings.resolve(), resume=args.resume
            )
        elif args.mode == "seal-estimates":
            result = seal_estimates(repo, out)
        else:
            result = verify_readonly(repo, out)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        failures = out / "failures"
        failures.mkdir(parents=True, exist_ok=True)
        i = 0
        while (failures / f"{i:03d}.json").exists():
            i += 1
        atomic_json(
            failures / f"{i:03d}.json",
            {
                "schema": "iscat165.run_failure.1",
                "mode": args.mode,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "error_repr": repr(exc),
                "traceback": traceback.format_exc(),
                "reportable_D": None,
            },
        )
        print(traceback.format_exc(), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
