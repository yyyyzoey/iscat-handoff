"""The one trusted V167 model service.

Holds the single live F2c model for the whole round, owns the V167 ledger, and
persists a charge before every real forward.  Workers are separate interpreter
processes: they never see the model object, the ledger, the plan or another
task's data.  Billing, prediction durability and exact-theta reuse follow the V166
production implementation (tools/v165_bundle/code/v165_run.py ChargedCaller),
reproduced here with a round-wide cache so a repeated theta costs zero.
"""
from __future__ import annotations

import importlib
import json
import re
import sqlite3
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Callable

import numpy as np

# Module resolution belongs to v167_common.bootstrap_paths(estimator=False), which
# must run before this module is imported.  Inserting ROOT/tools here would put the
# older v152_budget_store.py in that directory ahead of the pinned bundle copy.
_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from v152_budget_store import BudgetStore, CallCapReached  # noqa: E402
from v152_gls_core import check_theta  # noqa: E402
from v167_common import (  # noqa: E402
    BINDING_TASK, FINAL_TASK, LOADER_TASK, MODEL_ID, OUT, OWNER, PHASES, ROOT, TOTAL,
    OPTIMIZER, array_meta, array_sha, atomic_json, canon, read_json, require,
    replay_json, sha_bytes, sha_file, theta_hex, update_json,
)


class FatalPersistenceError(RuntimeError):
    pass


class ReconstructionRefused(RuntimeError):
    pass


# The loader self-check does not run on the F2c composite: it runs on the legacy F2
# field library that the composite wraps (tools/load_field_library.py walks its own
# nodes after building the model, and tools/v142_model.py records that library id as
# identity["parent_model_id"]).  So a loader forward legitimately returns an id
# different from MODEL_ID.  V167 still verifies every return; it verifies the correct
# value, and after construction it requires that value to be exactly the frozen F2c
# parent.  Estimator returns keep the original MODEL_ID rule untouched.
LOADER_KIND = "MODEL_LOADER"
FIELD_MODEL_ID = re.compile(r"^v131-field-[0-9a-f]{64}$")


def check_returned_model_id(kind: str, model_id: Any) -> None:
    """Refuse a return whose model id is not the one this call was billed against."""
    if kind == LOADER_KIND:
        require(isinstance(model_id, str) and FIELD_MODEL_ID.match(model_id) is not None,
                "LOADER_FORWARD_MODEL_ID_NOT_FIELD_LIBRARY:" + repr(model_id))
        return
    require(model_id is None or model_id == MODEL_ID, "MODEL_ID_MISMATCH_IN_RETURN")


def resolve_loader_field_parent(model: Any, observed: Any) -> tuple[str, str]:
    """Bind the loader self-check ids to the parent id of the live F2c model."""
    ids = {str(value) for value in observed}
    require(len(ids) == 1, "LOADER_FIELD_ID_DISTINCT_COUNT:" + json.dumps(sorted(ids)))
    identity = getattr(model, "identity", None)
    require(isinstance(identity, dict), "F2C_IDENTITY_NOT_A_MAPPING")
    parent = identity.get("parent_model_id")
    field_id = ids.pop()
    require(field_id == parent,
            "LOADER_FIELD_ID_NOT_F2C_PARENT:" + str(field_id) + "!=" + str(parent))
    return field_id, str(parent)


def make_store(path: Path) -> BudgetStore:
    return BudgetStore(Path(path), "v167", dict(PHASES), TOTAL)


def task_signature(descriptor: Any, phase: str, cap: int) -> str:
    """Hex signature text the frozen ledger compares against on seal.

    Mirrors V166 task_signature: the ledger keeps a TEXT key and every sealed
    result document must carry exactly this string under "signature".
    """
    return sha_bytes(canon({
        "schema": "iscat167.task_signature.1", "plan_id": "v167",
        "descriptor": descriptor, "phase": phase, "cap": cap, "optimizer": OPTIMIZER,
    }))


def read_only_ledger(path: Path) -> sqlite3.Connection:
    """Open a committed ledger for inspection without risking a write."""
    con = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        con.execute("BEGIN TRANSACTION")
        con.execute("ROLLBACK")
    except sqlite3.Error:
        con.close()
        raise
    return con


def ledger_attempt(con: sqlite3.Connection, task_id: str, seq: int) -> dict | None:
    row = con.execute(
        "SELECT seq,theta,state,detail FROM attempts WHERE task=? AND seq=?",
        (task_id, int(seq))).fetchone()
    if row is None:
        return None
    detail = json.loads(row[3]) if row[3] else {}
    return {"seq": int(row[0]), "state": row[2], "detail": detail,
            "theta_column": json.loads(row[1]) if row[1] else None}

def model_modules():
    tools = ROOT / "tools"
    if str(tools) not in sys.path:
        sys.path.insert(0, str(tools))
    runtime = importlib.import_module("v146_runtime")
    fields = importlib.import_module("field_forward_reference")
    require(Path(runtime.__file__).resolve() == tools / "v146_runtime.py", "WRONG_RUNTIME_MODULE")
    require(Path(fields.__file__).resolve() == tools / "field_forward_reference.py", "WRONG_FIELD_MODULE")
    return runtime, fields


def _read_model_output(result: Any, t: np.ndarray) -> tuple[np.ndarray, np.ndarray, str | None, dict]:
    observation: dict[str, np.ndarray] = {}
    if hasattr(result, "score_C"):
        for name in ("Ibg", "I", "C", "score_C"):
            require(hasattr(result, name), "MODEL_OUTPUT_MISSING_" + name)
            array = np.ascontiguousarray(getattr(result, name), dtype=float)
            require(np.isfinite(array).all(), "MODEL_OUTPUT_NONFINITE_" + name)
            observation[name] = array
        c = observation["score_C"]
        returned = np.asarray(getattr(result, "theta", t), dtype=float)
        require(np.array_equal(returned, t), "MODEL_OUTPUT_RETURNED_THETA_CHANGED")
        return c, returned, getattr(result, "model_id", None), observation
    c = np.ascontiguousarray(result, dtype=float)
    return c, t.copy(), None, {"score_C": c}


class PredictionService:
    """Single live model, single ledger, round-wide exact-theta cache."""

    def __init__(self, store: BudgetStore, out: Path = OUT):
        self.store = store
        self.out = Path(out)
        self.model: Any = None
        self.cache: dict[str, dict] = {}
        self.constructions = 0
        self.real_calls = 0
        self.cache_hits = 0
        self.durations_ms: list[float] = []
        self.log_path = self.out / "logs" / "model_construction.json"
        self.cache_log = self.out / "logs" / "cache_hits.jsonl"
        self.loader_signature: str | None = None
        self.binding_signature: str | None = None
        self.import_summary: dict | None = None
        # Model ids seen on loader returns, and the loader charges this process closed.
        self.loader_field_model_ids: set[str] = set()
        self.orphan_recovery: list[dict] = []

    # --------------------------------------------------------------- cache
    def load_existing_predictions(self) -> dict:
        """Rebuild the exact-theta cache from durable records only; no reconstruction."""
        scanned = 0
        reused_provenance = []
        root = self.out / "tasks"
        for path in sorted(root.glob("*/predictions/*.json")) if root.is_dir() else []:
            doc = read_json(path)
            if doc.get("schema") != "iscat167.prediction.1" or doc.get("model_id") != MODEL_ID:
                continue
            scanned += 1
            c = np.ascontiguousarray(doc["C"], dtype=float)
            require(c.shape == (13, 13) and np.isfinite(c).all(), "CACHED_C_INVALID:" + str(path))
            require(array_sha(c) == doc["C_sha256"], "CACHED_C_SHA_MISMATCH:" + str(path))
            binding = self._verify_charge_binding(path, doc)
            require(binding is not None, "PREDICTION_NOT_CHARGE_BOUND:" + str(path))
            key = theta_hex(doc["returned_theta"])
            entry = {"C": c, "C_sha256": doc["C_sha256"], "task_id": doc["task"],
                     "model_id": doc["model_id"], "seq": int(doc["seq"]),
                     "prediction_path": path.relative_to(self.out).as_posix(),
                     "prediction_sha256": sha_file(path), "charged": True,
                     "frames_sha256": doc.get("frames_sha256")}
            previous = self.cache.get(key)
            if previous is not None and previous["C_sha256"] != entry["C_sha256"]:
                raise FatalPersistenceError("SAME_THETA_DIFFERENT_C:" + key)
            if previous is not None:
                reused_provenance.append({"theta_sha256": key, "duplicate_path": entry["prediction_path"],
                                          "kept_source": previous["prediction_path"]})
            self.cache[key] = previous or entry
        return {"prediction_documents_scanned": scanned, "distinct_theta_cached": len(self.cache),
                "duplicate_documents": reused_provenance}

    def _verify_charge_binding(self, path: Path, doc: dict) -> dict | None:
        seq = int(doc["seq"])
        attempt = self._attempt_for_seq(doc["task"], seq)
        if attempt is None or attempt["state"] != "RETURNED":
            return None
        detail = attempt.get("detail") or {}
        require(detail.get("task_id") == doc["task"] and detail.get("ledger_seq") == seq,
                "PREDICTION_LEDGER_TASK_MISMATCH:" + str(path))
        require(np.array_equal(np.asarray(detail.get("requested_theta"), dtype=float),
                               np.asarray(doc["requested_theta"], dtype=float)),
                "PREDICTION_CHARGE_THETA_MISMATCH:" + str(path))
        require(detail.get("prediction_path") == path.relative_to(self.out).as_posix()
                and detail.get("prediction_sha256") == sha_file(path),
                "PREDICTION_CHARGE_PATH_MISMATCH:" + str(path))
        require(detail.get("C_sha256") == doc["C_sha256"], "PREDICTION_CHARGE_C_MISMATCH:" + str(path))
        require(detail.get("kind") == doc.get("kind")
                and detail.get("start_index") == doc.get("start_index"),
                "PREDICTION_CHARGE_IDENTITY_MISMATCH:" + str(path))
        return detail

    def _attempt_for_seq(self, task_id: str, seq: int) -> dict | None:
        # The frozen ledger stores attempts keyed on column `task`; there is no
        # attempts() accessor, so this is the only read path and it never writes.
        with self.store.db() as conn:
            row = conn.execute(
                "SELECT seq,theta,state,detail FROM attempts WHERE task=? AND seq=?",
                (task_id, int(seq))).fetchone()
        if row is None:
            return None
        seq_stored, theta_text, state, detail_text = row
        detail = json.loads(detail_text) if detail_text else {}
        require(theta_text is None or json.loads(theta_text) == detail.get("requested_theta"),
                "LEDGER_THETA_COLUMN_MISMATCH:" + task_id + ":" + str(seq))
        return {"seq": int(seq_stored), "state": state, "detail": detail,
                "requested_theta": detail.get("requested_theta")}

    def _note_cache_hit(self, task_id: str, key: str, entry: dict) -> None:
        self.cache_hits += 1
        self.cache_log.parent.mkdir(parents=True, exist_ok=True)
        row = {"task_id": task_id, "theta_sha256": key, "new_consumption": 0,
               "source_prediction": entry["prediction_path"],
               "source_prediction_sha256": entry["prediction_sha256"],
               "source_charged_task": entry["task_id"], "C_sha256": entry["C_sha256"],
               "origin": entry.get("origin", "v167_charged"),
               "model_id": MODEL_ID}
        with self.cache_log.open("a", encoding="utf-8") as handle:
            handle.write(canon(row).decode("utf-8"))

    # ------------------------------------------------- imported V166 witnesses
    def import_v166_predictions(self, v166_root: Path, ledger_path: Path,
                                *, log_path: Path | None = None) -> dict:
        """Seed the exact-theta cache with predictions already billed in V166.

        Section 7 of the contract allows a repeated theta to cost nothing when the
        cached value is matched on model id, theta and source hash, and requires
        imported witnesses to be recorded apart from this round's own predictions.
        Every document is re-verified here against the published V166 ledger, which
        is opened read-only: a prediction whose charge record cannot be found, or
        whose bytes disagree with the ledger, is refused rather than trusted.
        """
        v166_root = Path(v166_root)
        require(self.constructions == 0, "IMPORT_AFTER_MODEL_CONSTRUCTION")
        con = read_only_ledger(Path(ledger_path))
        paths = sorted(v166_root.glob("tasks/*/predictions/*.json"))
        accepted, refused, conflicts = 0, [], []
        details: list[dict] = []
        try:
            for path in paths:
                doc = read_json(path)
                problem = None
                try:
                    require(doc.get("schema") == "iscat165.prediction.1", "SCHEMA")
                    require(doc.get("model_id") == MODEL_ID, "MODEL_ID")
                    c = np.ascontiguousarray(doc["C"], dtype=np.float64)
                    require(c.shape == (13, 13) and np.isfinite(c).all(), "C_SHAPE")
                    require(array_sha(c) == doc["C_sha256"], "C_SHA")
                    relative = path.relative_to(v166_root).as_posix()
                    task_id = str(doc["task"])
                    seq = int(doc["seq"])
                    attempt = ledger_attempt(con, task_id, seq)
                    require(attempt is not None, "NO_LEDGER_ATTEMPT")
                    require(attempt["state"] == "RETURNED", "ATTEMPT_NOT_RETURNED")
                    detail = attempt["detail"]
                    require(detail.get("prediction_path") == relative, "PREDICTION_PATH")
                    require(detail.get("prediction_sha256") == sha_file(path), "PREDICTION_SHA")
                    require(detail.get("C_sha256") == doc["C_sha256"], "DETAIL_C_SHA")
                    require(detail.get("requested_theta") == doc["requested_theta"], "REQUESTED_THETA")
                    require(detail.get("returned_theta") == doc["returned_theta"], "RETURNED_THETA")
                    require(np.array_equal(np.asarray(detail.get("requested_theta"), dtype=float),
                                           np.asarray(doc["requested_theta"], dtype=float)),
                            "THETA_COLUMN")
                except (ValueError, KeyError, AssertionError) as exc:
                    problem = type(exc).__name__ + ":" + str(exc)
                if problem is not None:
                    refused.append({"path": str(path), "reason": problem})
                    continue
                key = theta_hex(doc["returned_theta"])
                entry = {"C": c, "C_sha256": doc["C_sha256"], "task_id": task_id,
                         "model_id": doc["model_id"], "seq": seq, "prediction_path": relative,
                         "prediction_sha256": sha_file(path), "charged": False,
                         "origin": "v166_import", "frames_sha256": None}
                previous = self.cache.get(key)
                if previous is not None and previous["C_sha256"] != entry["C_sha256"]:
                    conflicts.append({"theta_sha256": key, "kept": previous["prediction_path"],
                                      "rejected": relative})
                    continue
                if previous is None:
                    self.cache[key] = entry
                    accepted += 1
                    details.append({"theta_sha256": key, "source_task": task_id,
                                    "ledger_seq": seq, "prediction_path": relative,
                                    "prediction_sha256": entry["prediction_sha256"],
                                    "C_sha256": entry["C_sha256"]})
        finally:
            con.close()
        summary = {"schema": "iscat167.v166_witness_import.1",
                   "v166_root": str(v166_root), "ledger_path": str(Path(ledger_path)),
                   "ledger_open_mode": "read_only",
                   "documents_seen": len(paths), "distinct_theta_imported": accepted,
                   "imported_new_charges": 0, "refused": len(refused),
                   "refused_examples": refused[:20],
                   "same_theta_conflicting_C": len(conflicts),
                   "same_theta_conflicts": conflicts[:20],
                   "cache_theta_total": len(self.cache)}
        log = Path(log_path) if log_path is not None else self.out / "logs" / "v166_witness_import.json"
        # The import is a pure function of the published V166 tree and ledger, so a bind
        # step replayed after an interruption must land on the same bytes instead of
        # either forking a second receipt or refusing the whole round.
        digest, replayed = replay_json(log, {"summary": summary, "imported_witnesses": details})
        summary["receipt_path"] = str(log)
        summary["receipt_sha256"] = digest
        summary["receipt_replayed_byte_identical"] = replayed
        self.import_summary = summary
        return summary

    # -------------------------------------------------------------- billing
    def charged_call(self, task_id: str, theta: Any, invoke: Callable[[Any], Any], *,
                     start_index: int | None, kind: str,
                     frames_sha256: str | None = None,
                     allow_reuse: bool = True) -> dict:
        t = check_theta(theta)
        key = theta_hex(t)
        hit = self.cache.get(key) if allow_reuse else None
        if hit is not None:
            # Section 7 matches a reuse on full model id, exact theta and the
            # source prediction, never on an approximate diameter.
            require(hit.get("model_id") == MODEL_ID, "CACHE_ENTRY_MODEL_ID_UNVERIFIED:" + key)
            require(hit.get("prediction_sha256"), "CACHE_ENTRY_SOURCE_MISSING:" + key)
            if frames_sha256 is not None and hit.get("frames_sha256") not in (None, frames_sha256):
                raise FatalPersistenceError("CACHE_FRAMES_SOURCE_CONFLICT:" + key)
            self._note_cache_hit(task_id, key, hit)
            return {"C": hit["C"], "C_sha256": hit["C_sha256"], "seq": hit["seq"],
                    "prediction_path": hit["prediction_path"],
                    "prediction_sha256": hit["prediction_sha256"], "charged": False,
                    "cache_hit": True, "charged_task_id": hit["task_id"],
                    # Section 7: an imported witness and this round's own prediction
                    # must stay distinguishable in every downstream record.
                    "origin": hit.get("origin", "v167_charged"),
                    "returned_theta": t.tolist(), "theta_sha256": key}
        seq = self.store.charge(
            task_id, OWNER, t,
            detail={"start_index": start_index, "kind": kind,
                    "invocation": "charged_model_forward", "theta_sha256": key,
                    "frames_sha256": frames_sha256},
        )
        started = time.perf_counter()
        try:
            result = invoke(t)
        except Exception as exc:
            detail = {"error_type": type(exc).__name__, "error": str(exc),
                      "error_repr": repr(exc), "traceback": traceback.format_exc(),
                      "ledger_seq": seq, "start_index": start_index, "kind": kind,
                      "returned_theta": None, "theta_sha256": key}
            try:
                self.store.returned(task_id, seq, "MODEL_ERROR", detail)
            except Exception as persist_exc:
                raise FatalPersistenceError(
                    "CHARGED_MODEL_ERROR_NOT_DURABLE:" + task_id + ":" + str(seq)) from persist_exc
            raise
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        try:
            c, returned_theta, model_id, observation = _read_model_output(result, t)
            require(c.shape == (13, 13) and np.isfinite(c).all(),
                    "MODEL_OUTPUT_MUST_BE_FINITE_13X13_SIGNED_C")
            check_returned_model_id(kind, model_id)
        except Exception as exc:
            # The model did answer, so the charge stands, but the return is refused.
            # The attempt has to be settled here or the open CHARGED row keeps the task
            # unsealable and the billed call silently disappears from the accounting.
            detail = {"error_type": type(exc).__name__, "error": str(exc),
                      "error_repr": repr(exc), "traceback": traceback.format_exc(),
                      "ledger_seq": seq, "start_index": start_index, "kind": kind,
                      "returned_theta": None, "theta_sha256": key,
                      "refusal_stage": "POST_RETURN_VALIDATION"}
            try:
                self.store.returned(task_id, seq, "MODEL_ERROR", detail)
            except Exception as persist_exc:
                raise FatalPersistenceError(
                    "CHARGED_REFUSED_RETURN_NOT_DURABLE:" + task_id + ":" + str(seq)) from persist_exc
            raise
        if kind == LOADER_KIND:
            self.loader_field_model_ids.add(str(model_id))
        c_hash = array_sha(c)
        path = self.out / "tasks" / task_id / "predictions" / f"{seq:04d}.json"
        require(not path.exists(), "PREDICTION_PATH_ALREADY_EXISTS:" + str(path))
        prediction = {
            "schema": "iscat167.prediction.1", "task": task_id, "seq": seq,
            "ledger_seq": seq, "start_index": start_index, "kind": kind,
            "charged": True, "requested_theta": t.tolist(),
            "returned_theta": returned_theta.tolist(), "theta_sha256": key,
            "model_id": model_id or MODEL_ID, "frames_sha256": frames_sha256,
            "C": c.tolist(), "C_sha256": c_hash,
            "forward_wall_ms": elapsed_ms,
            "observation_metadata": {name: array_meta(values) for name, values in observation.items()},
        }
        digest = atomic_json(path, prediction)
        file_sha = sha_file(path)
        require(file_sha == digest, "PREDICTION_FILE_DIGEST_CHANGED")
        settled = {"ledger_seq": seq, "task_id": task_id, "start_index": start_index,
                   "kind": kind, "requested_theta": t.tolist(),
                   "returned_theta": returned_theta.tolist(), "theta_sha256": key,
                   "prediction_path": path.relative_to(self.out).as_posix(),
                   "prediction_sha256": file_sha, "C_sha256": c_hash,
                   "frames_sha256": frames_sha256}
        self.store.returned(task_id, seq, "RETURNED", settled)
        self.real_calls += 1
        self.durations_ms.append(elapsed_ms)
        relative = path.relative_to(self.out).as_posix()
        if (model_id or MODEL_ID) == MODEL_ID:
            # A loader answer belongs to the legacy field library, so it is never
            # allowed to serve an estimator's reuse request as if it were F2c output.
            self.cache[key] = {"C": c, "C_sha256": c_hash, "task_id": task_id, "seq": seq,
                               "model_id": model_id or MODEL_ID, "origin": "v167_charged",
                               "prediction_path": relative, "prediction_sha256": file_sha,
                               "charged": True, "frames_sha256": frames_sha256}
        return {"C": c, "C_sha256": c_hash, "seq": seq, "prediction_path": relative,
                "prediction_sha256": file_sha, "charged": True, "cache_hit": False,
                "forward_wall_ms": elapsed_ms, "model_output": result,
                "returned_theta": returned_theta.tolist(), "theta_sha256": key}

    # --------------------------------------------------------------- loading
    def reconcile_loader_orphans(self) -> dict:
        """Close a CHARGED loader attempt that a refused return left stranded.

        Section 7 bills before the real forward, so a refusal inside the loader walk
        leaves the attempt open: the loader task can never seal and the billed call
        disappears from the accounting.  Each open loader attempt is settled as
        MODEL_ERROR with every original charge field preserved, which is the same
        semantics the round controller uses for worker tasks.  No call is refunded.
        A CHARGED attempt outside the loader task means a crash this service knows
        nothing about, so it stops the round instead of being absorbed here.
        """
        with self.store.db() as db:
            rows = db.execute(
                "SELECT seq, detail FROM attempts WHERE task = ? AND state = 'CHARGED' "
                "ORDER BY seq", (LOADER_TASK,)).fetchall()
            other = db.execute(
                "SELECT task, seq FROM attempts WHERE state = 'CHARGED' AND task <> ? "
                "ORDER BY task, seq", (LOADER_TASK,)).fetchall()
        require(not other, "CHARGED_ORPHAN_OUTSIDE_LOADER:" + json.dumps(
            [[str(task), int(seq)] for task, seq in other]))
        recovery_log = self.out / "logs" / "loader_orphan_recovery.jsonl"
        settled = []
        for seq, raw in rows:
            detail = json.loads(raw) if raw else {}
            require(detail.get("kind") == LOADER_KIND,
                    "LOADER_ORPHAN_SCOPE_EXCEEDED:" + str(int(seq)) + ":"
                    + str(detail.get("kind")))
            note = "loader_attempt_orphaned_by_a_refused_return"
            self.store.returned(LOADER_TASK, int(seq), "MODEL_ERROR",
                                dict(detail, reconciliation_state="MODEL_ERROR",
                                     reconciliation_note=note,
                                     reconciled_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                                  time.gmtime())))
            # The refusal raised before any return was written, so the ledger holds no
            # reason text for it; the line points at the run that produced the orphan.
            line = {"task_id": LOADER_TASK, "ledger_seq": int(seq),
                    "theta_sha256": detail.get("theta_sha256"),
                    "requested_theta": detail.get("requested_theta"),
                    "charge_detail_sha256": sha_bytes(canon(detail)),
                    "state_before": "CHARGED", "state_after": "MODEL_ERROR",
                    "refunded_calls": 0,
                    "reconciled_by": "v167_service.reconcile_loader_orphans",
                    "note": note, "refusal_reason_in_ledger": False,
                    "refusal_reason_source": "prior authorized run step trace"}
            recovery_log.parent.mkdir(parents=True, exist_ok=True)
            with recovery_log.open("a", encoding="utf-8") as handle:
                handle.write(canon(line).decode("utf-8"))
            settled.append(line)
        self.orphan_recovery.extend(settled)
        return {"settled_count": len(settled), "refunded_calls": 0,
                "settled_sequences": [row["ledger_seq"] for row in settled],
                "recovery_log": (recovery_log.relative_to(self.out).as_posix()
                                 if settled else None)}

    def ensure_loader(self, *, dry_run: bool = False) -> dict:
        if self.model is not None:
            return {"constructed": False, "reason": "ALREADY_LIVE_IN_THIS_PROCESS"}
        existing = self.log_path
        if existing.exists():
            record = read_json(existing)
            if record.get("sealed") is True or record.get("loader_calls"):
                raise ReconstructionRefused(
                    "LOADER_EVIDENCE_PRESENT_REFUSING_SILENT_RECONSTRUCTION:" + str(existing))
        if dry_run:
            return {"constructed": False, "model_calls": 0,
                    "reason": "DRY_RUN_NO_MODEL_CONSTRUCTION_AUTHORIZED"}
        self.reconcile_loader_orphans()
        runtime, fields = model_modules()
        self.loader_signature, state = self.reserve_loader()
        require(state in ("RUNNING",), "LOADER_TASK_STATE:" + str(state))
        loader_rows: list[dict] = []
        original = fields.FieldForward.forward

        def wrapped(instance, theta):
            info = self.charged_call(LOADER_TASK, theta, lambda t: original(instance, t),
                                     start_index=0, kind="MODEL_LOADER", allow_reuse=False)
            require("model_output" in info, "LOADER_FORWARD_RETURNED_A_CACHE_HIT")
            loader_rows.append({"theta": np.asarray(theta, dtype=float).tolist(),
                                "ledger_seq": int(info["seq"]),
                                "prediction_path": info["prediction_path"],
                                "C_sha256": info["C_sha256"]})
            return info["model_output"]

        self.constructions += 1
        started = time.perf_counter()
        fields.FieldForward.forward = wrapped
        try:
            cfg = read_json(ROOT / "config" / "v146_science_config.json")
            model = runtime.construct_bound(ROOT, cfg)
        finally:
            fields.FieldForward.forward = original
        require(model.model_id == MODEL_ID, "F2C_MODEL_ID_CHANGED")
        field_id, parent = resolve_loader_field_parent(model, self.loader_field_model_ids)
        self.model = model
        record = {
            "schema": "iscat167.model_construction.1",
            "signature": self.loader_signature,
            "constructions_in_this_process": self.constructions,
            "model_id": model.model_id,
            "loader_field_model_id": field_id,
            "f2c_parent_model_id": parent,
            "orphan_attempts_reconciled": self.orphan_recovery,
            "model_module": str(Path(sys.modules["v142_model"].__file__).resolve()),
            "loader_task": LOADER_TASK, "loader_calls": len(loader_rows),
            "loader_attempts": loader_rows,
            "construct_wall_seconds": time.perf_counter() - started,
            "ledger_counts": dict(self.store.counts()), "sealed": False,
        }
        atomic_json(self.log_path, record)
        return record

    def reserve_loader(self) -> tuple[str, str]:
        signature = task_signature({"task": LOADER_TASK, "model_id": MODEL_ID,
                                    "role": "single_loader", "phase": "MODEL_BINDING"},
                                   "MODEL_BINDING", 100)
        return signature, self.store.reserve(LOADER_TASK, signature, "MODEL_BINDING", 100, OWNER)

    def seal_loader(self) -> dict:
        record = read_json(self.log_path)
        require(record.get("sealed") is False, "LOADER_ALREADY_SEALED_OR_MISSING")
        signature = record.get("signature")
        require(isinstance(signature, str) and signature, "LOADER_RECORD_UNSIGNED")
        require(signature == task_signature({"task": LOADER_TASK, "model_id": MODEL_ID,
                                             "role": "single_loader", "phase": "MODEL_BINDING"},
                                            "MODEL_BINDING", 100),
                "LOADER_SIGNATURE_CHANGED")
        record["sealed"] = True
        record["ledger_counts_at_seal"] = dict(self.store.counts())
        update_json(self.log_path, record)
        self.store.seal(LOADER_TASK, OWNER, "FINISHED", str(self.log_path))
        return record

    def forward(self, theta: Any) -> Any:
        require(self.model is not None, "NO_LIVE_MODEL_IN_SERVICE")
        return self.model.forward(tuple(float(x) for x in theta))

    def evaluate(self, task_id: str, theta: Any, *, start_index: int | None, kind: str,
                 frames_sha256: str | None = None, allow_reuse: bool = True) -> dict:
        return self.charged_call(task_id, theta, self.forward, start_index=start_index,
                                 kind=kind, frames_sha256=frames_sha256, allow_reuse=allow_reuse)

    # --------------------------------------------------- witness cross-check
    def binding_self_check(self, witnesses: dict[str, dict], *, dry_run: bool = False) -> dict:
        """Re-evaluate each sealed V166 witness theta once in the new process.

        Controller-side evidence only.  Witnesses are never handed to a worker and
        the byte comparison is reported per theta; a mismatch is a finding, not a
        reason to stop reading the rest.
        """
        if dry_run:
            return {"rows": [], "model_calls": 0, "status": "NOT_STARTED_DRY_RUN"}
        require(self.model is not None, "MODEL_REQUIRED_FOR_BINDING_CHECK")
        self.binding_signature, _state = self.reserve_binding()
        rows = []
        for label, item in sorted(witnesses.items()):
            try:
                # allow_reuse=False is the point of this gate: the freshly built live
                # model must itself reproduce the sealed C bytes.  A cache hit against
                # an imported V166 witness would compare the evidence with itself and
                # prove nothing about the new process, so no witness theta is reused
                # here even when the cache already holds it.
                info = self.evaluate(BINDING_TASK, item["theta"], start_index=None,
                                     kind="SOURCE_BINDING", allow_reuse=False)
            except CallCapReached as exc:
                rows.append({"witness": label, "status": "BLOCKED_CAP", "error": repr(exc),
                             "charged": False})
                continue
            sealed = item.get("sealed_C_sha256")
            rows.append({
                "witness": label, "source_task_id": item.get("source_task_id"),
                "source_prediction": item.get("source_prediction"),
                "source_prediction_sha256": item.get("source_prediction_sha256"),
                "sealed_C_sha256": sealed, "v167_C_sha256": info["C_sha256"],
                "byte_exact_match": bool(sealed) and sealed == info["C_sha256"],
                "charged": bool(info["charged"]), "cache_hit": bool(info.get("cache_hit")),
                "theta": np.asarray(item["theta"], dtype=float).tolist(),
                "v167_prediction_path": info["prediction_path"], "status": "VERIFIED_ITEM",
            })
        matched = sum(1 for row in rows if row.get("byte_exact_match"))
        return {"rows": rows, "distinct_theta": len(rows),
                "new_real_calls": sum(1 for row in rows if row.get("charged")),
                "cache_hit_requests": sum(1 for row in rows if row.get("cache_hit")),
                "byte_exact_matches": matched,
                "status": "VERIFIED" if rows and matched == len(rows) else "NOT_FULLY_VERIFIED"}

    def reserve_binding(self) -> tuple[str, str]:
        signature = task_signature({"task": BINDING_TASK, "model_id": MODEL_ID,
                                    "role": "witness_cross_check",
                                    "phase": "MODEL_BINDING"}, "MODEL_BINDING", 100)
        return signature, self.store.reserve(BINDING_TASK, signature, "MODEL_BINDING", 100, OWNER)

    def seal_binding(self, receipt: dict, path: Path) -> dict:
        """Write the binding receipt as the task result document, then seal it."""
        signature = self.binding_signature
        require(signature == task_signature({"task": BINDING_TASK, "model_id": MODEL_ID,
                                            "role": "witness_cross_check",
                                            "phase": "MODEL_BINDING"},
                                           "MODEL_BINDING", 100), "BINDING_SIGNATURE_CHANGED")
        doc = dict(receipt)
        doc.update({"schema": "iscat167.binding_result.1", "signature": signature,
                    "task_id": BINDING_TASK, "db_state": "FINISHED",
                    "actual_calls": int(self.store.counts().get(BINDING_TASK, 0)),
                    "reportable_D": None})
        atomic_json(Path(path), doc)
        require(read_json(Path(path)) == doc, "BINDING_RESULT_READBACK")
        self.store.seal(BINDING_TASK, OWNER, "FINISHED", str(Path(path)))
        return doc

    def close(self) -> None:
        self.model = None


def witness_theta_labels(final_task: str = FINAL_TASK) -> str:
    require(final_task == FINAL_TASK, "FINAL_TASK_IDENTITY")
    return final_task


def sha_of_doc(doc: Any) -> str:
    return sha_bytes(canon(doc))
