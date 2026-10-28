"""One estimator process per V167 task: no model object, no ledger, one reading.

The controller starts this file as a separate interpreter whose current directory
is a per-task jail holding exactly three JSON documents: this task's single
one-reading payload, its group's three-frame document, and that group's six
frozen legal witness records.  The audit hook is installed before the jail reads
any of those documents, so a read of the full 24-row height table, the plan, the
draw seed, the old ledger or the sealed truth is a recorded refusal instead of a
silent success.  Interpreter library loading necessarily happens first and is
outside this guard; the guard covers data, and that limit is stated in the
receipt rather than hidden.

F2c forwards cross the RPC pipe to the trusted service, which bills the ledger
before each real call.  Everything the optimiser produces is persisted by this
process as it happens: evaluation document, running checkpoint, per-pass record,
per-start record and best-so-far.
"""
from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np                      # loaded before the guard: see module note
from scipy.optimize import least_squares

FORBIDDEN_PROBES = (
    "results/v167_prepared/controller_only/plan.json",
    "results/v167_prepared/readings/v167_public_height_readings.json",
    "results/v166/estimates.json",
    "results/v166/logs/v165_budget.sqlite",
    "results/v166/tasks",
    "results/v165/validator_only/v166_height_truth_sealed.json",
    ".git/config",
    "tools/v167/v167_service.py",
    "tools/v167/v167_controller.py",
    "tools/v167_bundle/config/v167_plan.json",
)


class CapReached(RuntimeError):
    """The service refused a further real forward: this search is partial."""


class BudgetBlocked(CapReached):
    """The trusted ledger refused this theta, so no new real call is possible.

    A per-start local cap is a legitimate pass boundary and the next pass can still
    compute.  A ledger refusal is different in kind: the only answers still available
    are predictions this round already paid for, so continuing would spend wall clock
    re-reading the cache while pretending to search.  The start stops and says so.
    """


class RemoteFatal(RuntimeError):
    pass


def _boot(task_dir: Path) -> dict:
    """Install the jail and the estimator import path before touching any data."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import v167_jail
    import v167_common as common

    # v167_rpc.py is shared transport the worker must import; every other
    # controller-only source in tools/v167 is denied by explicit path.
    denied = [common.ROOT / "tools" / "v167" / name
              for name in common.CONTROLLER_ONLY_CODE_FILES
              if name != "v167_rpc.py"]
    jail = v167_jail.install(
        allowed_read=[
            task_dir,
            common.OUT / "tasks" / task_dir.name,
            common.ROOT / "tools" / "v167",
            common.APPROVED_CORE,
            common.PAYLOAD_GATE,
            sys.prefix,
            sys.base_prefix,
        ],
        allowed_write=[common.OUT / "tasks" / task_dir.name],
        denied_read=denied,
    )
    paths = common.bootstrap_paths(estimator=True)
    identity = common.verify_frozen_module_identities(estimator=True)
    return {"jail": jail, "paths": paths, "module_identity": identity}


class Remote:
    """Line RPC to the controller; every answer is matched to its request id."""

    def __init__(self, task_id: str):
        import v167_rpc

        self.rpc = v167_rpc
        self.task_id = task_id
        self.out = sys.stdout.buffer
        self.inp = sys.stdin.buffer
        self.request_id = 0
        self.start_index = 0
        self.forward_requests = 0
        self.charged_forwards = 0
        self.cache_hit_forwards = 0
        self.max_forward_ms = 0.0

    def _exchange(self, message: dict) -> dict:
        self.rpc.send(self.out, message)
        reply = self.rpc.recv(self.inp)
        if reply.get("op") == "fatal":
            raise RemoteFatal(str(reply.get("message")) + "|" + str(reply.get("traceback")))
        return reply

    def notify(self, message: dict) -> None:
        self.rpc.send(self.out, message)

    def hello(self, report: dict) -> dict:
        message = {"op": "hello", "protocol": self.rpc.PROTOCOL, "request_id": 0,
                   "task_id": self.task_id, "pid": os.getpid(), **report}
        reply = self._exchange(message)
        if reply.get("op") != "hello_ack" or reply.get("task_id") != self.task_id:
            raise ValueError("RPC_HELLO_NOT_ACKED")
        return reply

    def start_begin(self, start_index: int, x0, pass_index: int) -> None:
        self.start_index = int(start_index)
        reply = self._exchange({"op": "start_begin", "request_id": 0, "task_id": self.task_id,
                                "start_index": int(start_index), "pass_index": int(pass_index),
                                "x0": [float(v) for v in x0]})
        if reply.get("ack") is not True:
            raise ValueError("RPC_START_NOT_ACKED")

    def forward(self, theta, evaluation_index: int, pass_index: int) -> dict:
        self.request_id += 1
        message = self.rpc.forward_request(self.request_id, theta, self.start_index,
                                           "OPTIMIZER", evaluation_index)
        message["task_id"] = self.task_id
        message["pass_index"] = int(pass_index)
        reply = self._exchange(message)
        if reply.get("op") == "forward_error":
            if reply.get("cap_reached") is True:
                raise BudgetBlocked(str(reply.get("message")))
            raise RemoteFatal("FORWARD_ERROR:" + str(reply.get("error_type")) +
                              ":" + str(reply.get("message")))
        c = self.rpc.validate_forward_reply(reply, self.request_id)
        self.forward_requests += 1
        if reply.get("charged") is True:
            self.charged_forwards += 1
        if reply.get("cache_hit") is True:
            self.cache_hit_forwards += 1
        self.max_forward_ms = max(self.max_forward_ms, float(reply.get("forward_wall_ms") or 0.0))
        record = {"C": c}
        for key in ("seq", "charged", "cache_hit", "prediction_path", "prediction_sha256",
                    "C_sha256", "theta_sha256", "returned_theta", "origin",
                    "charged_task_id", "forward_wall_ms"):
            if key in reply:
                record[key] = reply[key]
        return record

    def start_end(self, start_index: int, state: str, evaluations: int) -> None:
        self.notify({"op": "start_end", "request_id": 0, "task_id": self.task_id,
                     "start_index": int(start_index), "execution_state": state,
                     "evaluations": int(evaluations)})

    def log(self, text: str) -> None:
        self.notify({"op": "log", "request_id": 0, "task_id": self.task_id, "text": str(text)})

    def done(self, result: dict, refusals: int) -> dict:
        reply = self._exchange({"op": "done", "request_id": 0, "task_id": self.task_id,
                                "execution_state": result.get("execution_state"),
                                "jail_refusals": int(refusals), "result": result})
        if reply.get("op") != "hello_ack" or reply.get("ack") is not True:
            raise ValueError("RPC_DONE_NOT_ACKED")
        return reply


def legal_witness_rows(common, data, reading, frames_doc: dict, legal_doc: dict) -> list[dict]:
    """Rebuild V166's legal-witness floor for this group without touching other tasks.

    Row zero is the group's own V163 anchor prediction taken from the three-frame
    document; the next six are that group's frozen legal starts.  Every C array is
    re-hashed before it is scored, and the same de-duplication and sort as V166
    decide which point becomes the floor.
    """
    require = common.require
    diagnostic = frames_doc["diagnostic"]
    anchor = diagnostic["predictions"][int(diagnostic["base_index"])]
    rows_in = [(np.asarray(anchor["theta"], dtype=float),
                np.asarray(anchor["C"], dtype=float), "V163_CURRENT_ANCHOR")]
    require(len(legal_doc["records"]) == 6, "LEGAL_RECORD_COUNT")
    for record in legal_doc["records"]:
        c = np.asarray(record["C"], dtype=float)
        require(common.array_sha(c) == record["C_sha256"],
                "LEGAL_WITNESS_C_SHA:" + str(record.get("record_path")))
        require(record.get("model_id") == common.MODEL_ID, "LEGAL_WITNESS_MODEL_ID")
        require(record.get("B") == legal_doc["group_B"], "LEGAL_WITNESS_B_IDENTITY")
        require(record.get("anon") == legal_doc["group"], "LEGAL_WITNESS_GROUP_IDENTITY")
        require(record.get("source_commit") == legal_doc["source_commit"], "LEGAL_WITNESS_COMMIT")
        # V166 labelled these rows by their rescored record path; keeping the same
        # label makes the two rounds' witness tables directly comparable.
        rows_in.append((np.asarray(record["theta"], dtype=float), c,
                        record.get("record_path")
                        or "V152_LEGAL_" + str(record["start_index"])))
    candidates: list[dict] = []
    seen: set = set()
    for theta, c, source in rows_in:
        key = (tuple(theta.tolist()), common.array_sha(np.ascontiguousarray(c, dtype=np.float64)))
        if key in seen:
            continue
        seen.add(key)
        candidates.append({"theta": theta.tolist(), "C_sha256": key[1], "source": source,
                           **common.score_document(theta, c, data, reading)})
    require(candidates, "NO_LEGAL_WITNESS")
    return sorted(candidates, key=lambda r: r["Q_total"])


def run_pass(remote, common, data, reading, dirs, payload, start_index, pass_index,
             x0, local_cap):
    """One bounded least_squares pass inside one start slot."""
    task_id = payload["task_id"]
    starts_dir = Path(dirs["task"]) / "starts"
    checkpoint_path = starts_dir / f"{start_index:03d}_pass_{pass_index:02d}.running.json"
    checkpoint_doc = {
        "schema": "iscat167.start_checkpoint.1", "task_id": task_id,
        "start_index": start_index, "pass_index": pass_index,
        "execution_state": "RUNNING", "x0": [float(v) for v in np.asarray(x0, dtype=float)],
        "local_cap": int(local_cap), "evaluations_at_checkpoint": 0,
        "ledger_seq_at_checkpoint": None, "best_at_checkpoint": None,
    }
    common.atomic_json(checkpoint_path, checkpoint_doc)

    state = {"calls": 0, "best": None, "charged": 0, "cache_hits": 0}

    def residual(p):
        theta = common.check_theta(p)
        if state["calls"] >= local_cap:
            raise CapReached("PER_START_REAL_MODEL_CALL_CAP")
        state["calls"] += 1
        prediction = remote.forward(theta, state["calls"], pass_index)
        score = common.score_document(theta, prediction["C"], data, reading)
        if prediction.get("charged") is True:
            state["charged"] += 1
        if prediction.get("cache_hit") is True:
            state["cache_hits"] += 1
        evaluation = {
            "schema": "iscat167.evaluation.1", "task_id": task_id,
            "start_index": start_index, "pass_index": pass_index,
            "evaluation_index": state["calls"],
            "charged": bool(prediction.get("charged")),
            "cache_hit": bool(prediction.get("cache_hit")),
            "ledger_seq": prediction.get("seq"),
            "prediction_path": prediction.get("prediction_path"),
            "prediction_sha256": prediction.get("prediction_sha256"),
            "witness_origin": prediction.get("origin", "v167_charged"),
            "forward_wall_ms": prediction.get("forward_wall_ms"),
            **score,
        }
        common.atomic_json(Path(dirs["task"]) / "evaluations" /
                           f"{start_index:03d}_{pass_index:02d}_{state['calls']:04d}.json",
                           evaluation)
        if state["best"] is None or score["Q_total"] < state["best"]["Q_total"]:
            state["best"] = evaluation
            # The per-pass best document is a rolling pointer: one pass improves it
            # many times, so only its first write may use the never-overwrite path.
            # The name carries both start and pass index, so no other pass or task
            # can ever reach the same file; every single evaluation stays in its own
            # immutable document under evaluations/.
            best_path = (Path(dirs["task"]) / "best" /
                         f"start_{start_index:03d}_pass_{pass_index:02d}.json")
            if best_path.is_file():
                common.update_json(best_path, evaluation)
            else:
                common.atomic_json(best_path, evaluation)
        checkpoint_doc["evaluations_at_checkpoint"] = state["calls"]
        checkpoint_doc["ledger_seq_at_checkpoint"] = prediction.get("seq")
        checkpoint_doc["best_at_checkpoint"] = state["best"]
        return np.asarray(score["residual"], dtype=float)

    optimizer, error = None, None
    budget_blocked = False
    started = time.perf_counter()
    try:
        optimizer = least_squares(
            residual, np.asarray(x0, dtype=float),
            bounds=(common.LOW, common.HIGH), method=common.OPTIMIZER["method"],
            jac=common.OPTIMIZER["jac"], loss=common.OPTIMIZER["loss"],
            diff_step=common.OPTIMIZER["diff_step"], x_scale=common.OPTIMIZER["x_scale"],
            ftol=common.OPTIMIZER["ftol"], xtol=common.OPTIMIZER["xtol"],
            gtol=common.OPTIMIZER["gtol"], max_nfev=common.OPTIMIZER["max_nfev"],
        )
        state_out = "FINISHED" if bool(optimizer.success) else "PARTIAL_SEARCH"
    except CapReached as exc:
        state_out = "PARTIAL_SEARCH"
        budget_blocked = isinstance(exc, BudgetBlocked)
        error = {"error_type": type(exc).__name__, "error": str(exc),
                 "error_repr": repr(exc), "traceback": traceback.format_exc()}
    except Exception as exc:
        state_out = "FAILED"
        error = {"error_type": type(exc).__name__, "error": str(exc),
                 "error_repr": repr(exc), "traceback": traceback.format_exc()}

    record = {
        "schema": "iscat167.pass_result.1", "task_id": task_id,
        "start_index": start_index, "pass_index": pass_index,
        "execution_state": state_out,
        "x0": [float(v) for v in np.asarray(x0, dtype=float)],
        "evaluations": state["calls"], "local_cap": int(local_cap),
        "charged_this_pass": state["charged"], "cache_hits_this_pass": state["cache_hits"],
        "wall_seconds": time.perf_counter() - started,
        "best": state["best"], "error": error,
        "budget_blocked": budget_blocked,
        "optimizer": ({"success": bool(optimizer.success), "status": int(optimizer.status),
                       "message": str(optimizer.message), "nfev": int(optimizer.nfev),
                       "njev": int(optimizer.njev) if optimizer.njev is not None else None,
                       "cost": float(optimizer.cost), "optimality": float(optimizer.optimality),
                       "active_mask": np.asarray(optimizer.active_mask).astype(int).tolist(),
                       "x": np.asarray(optimizer.x, dtype=float).tolist()}
                      if optimizer is not None else None),
        "reportable_D": None,
    }
    common.update_json(checkpoint_path, record)
    common.atomic_json(starts_dir / f"{start_index:03d}_pass_{pass_index:02d}.json", record)
    return record, checkpoint_path


def probe_jail(common, task_dir: Path) -> dict:
    """Actively try forbidden reads and prove the guard refuses them.

    Used by the production test suite, never by the scientific run.
    """
    import v167_jail

    attempted, refused = [], []
    targets = list(FORBIDDEN_PROBES) + [str(Path(task_dir).parent / "OTHER_TASK" / "input.json")]
    for target in targets:
        path = common.ROOT / target if not Path(target).is_absolute() else Path(target)
        attempted.append(str(path))
        try:
            path.read_bytes()
        except v167_jail.JailViolation:
            refused.append(str(path))
        except Exception as exc:
            refused.append(str(path) + "|" + type(exc).__name__)
    listed = []
    for root in ("results/v166", "results/v167_prepared", ".git"):
        try:
            listed.append(str(common.ROOT / root))
            os.listdir(common.ROOT / root)
        except v167_jail.JailViolation:
            refused.append("LIST:" + str(common.ROOT / root))
        except Exception as exc:
            refused.append("LIST:" + str(common.ROOT / root) + "|" + type(exc).__name__)
    return {"schema": "iscat167.worker_probe.1", "attempted": attempted,
            "refused": refused, "refusal_count": len(refused),
            "guard_log": list(v167_jail.LOG)}


def main(argv: list[str]) -> int:
    task_dir = Path(argv[1]).resolve()
    mode = argv[2] if len(argv) > 2 else "fit"
    os.chdir(task_dir)
    boot = _boot(task_dir)
    import v167_common as common

    if mode == "--probe":
        report = probe_jail(common, task_dir)
        sys.stdout.buffer.write(common.canon(report))
        return 0

    payload = common.read_json(task_dir / "input.json")
    frames_doc = common.read_json(task_dir / "frames.json")
    legal_doc = common.read_json(task_dir / "legal_records.json")
    payload_sha = common.sha_file(task_dir / "input.json")
    where = "worker:" + task_dir.name

    gate_report = run_gate(common, payload)
    projection = common.projection_check(payload, where=where)
    data, frames_identity, frames_sha = common.frames_from_document(frames_doc, where=where)
    legal_problems = common.scan_forbidden(legal_doc, where + ".legal")
    common.require(not legal_problems, "LEGAL_RECORDS_FORBIDDEN:" + ";".join(legal_problems[:8]))
    reading = common.reading_from_document(payload["reading"])
    common.require(payload["group"] == reading.group, "GROUP_BINDING")
    common.require(legal_doc.get("group") == payload["group"], "LEGAL_RECORD_GROUP_MISMATCH")

    dirs = common.task_dirs(payload["task_id"])
    Path(dirs["predictions"]).mkdir(parents=True, exist_ok=True)
    for name in ("starts", "evaluations", "best"):
        Path(dirs["task"], name).mkdir(parents=True, exist_ok=True)

    remote = Remote(payload["task_id"])
    hello = remote.hello({
        "boot": boot, "payload_sha256": payload_sha, "payload_gate": gate_report,
        "projection_scope": projection["scope"], "frames_sha256": frames_sha,
        "frames_identity": frames_identity,
        "reading_identity": {"reading_id": reading.reading_id, "sigma_nm": reading.sigma_nm,
                             "replicate": reading.replicate, "hypothetical": True},
    })
    common.require(hello.get("model_id") == common.MODEL_ID, "SERVICE_MODEL_ID_CHANGED")
    common.require(hello.get("frames_sha256") == frames_sha, "SERVICE_FRAMES_SHA_MISMATCH")

    witnesses = legal_witness_rows(common, data, reading, frames_doc, legal_doc)
    common.atomic_json(Path(dirs["task"]) / "legal_witnesses.json",
                       {"schema": "iscat167.legal_witnesses.1", "task_id": payload["task_id"],
                        "rows": witnesses})
    legal_witness = witnesses[0]

    start_records = []
    evaluations_total = 0
    for index, x0 in enumerate(payload["starts"]):
        charges_before = remote.charged_forwards
        hits_before = remote.cache_hit_forwards
        slot = {"schema": "iscat167.start_slot.1", "task_id": payload["task_id"],
                "start_index": index, "x0": [float(v) for v in np.asarray(x0, dtype=float)],
                "cap_per_start": payload["cap_per_start"], "passes": [], "best": None,
                "execution_state": "RUNNING", "reason_codes": [], "reportable_D": None}
        common.atomic_json(Path(dirs["task"]) / "starts" / f"{index:03d}.slot.json", slot)
        used = 0
        pass_index = 0
        cursor = np.asarray(x0, dtype=float)
        remote.start_begin(index, cursor, 1)
        while used < payload["cap_per_start"]:
            pass_index += 1
            local_cap = min(int(common.OPTIMIZER["max_nfev"]), payload["cap_per_start"] - used)
            if pass_index > 1:
                remote.start_begin(index, cursor, pass_index)
                slot["reason_codes"].append("SECOND_SEQUENTIAL_PASS_FROM_FIRST_PASS_BEST_X")
            record, _ = run_pass(remote, common, data, reading, dirs, payload, index,
                                 pass_index, cursor, local_cap)
            slot["passes"].append(record)
            used += int(record["evaluations"])
            if record["best"] is not None and (slot["best"] is None or
                                               record["best"]["Q_total"] < slot["best"]["Q_total"]):
                slot["best"] = record["best"]
            if record["budget_blocked"] is True:
                slot["reason_codes"].append("BUDGET_BLOCKED_AT_LEDGER_STOP")
                break
            if record["execution_state"] != "PARTIAL_SEARCH":
                break
            if record["evaluations"] == 0 or record["best"] is None:
                break
            cursor = np.asarray(record["best"]["theta"], dtype=float)
        slot["actual_evaluations"] = used
        slot["charged_this_start"] = remote.charged_forwards - charges_before
        slot["cache_hits_this_start"] = remote.cache_hit_forwards - hits_before
        states = {p["execution_state"] for p in slot["passes"]}
        slot["execution_state"] = ("FINISHED" if states == {"FINISHED"}
                                   else "FAILED" if "FAILED" in states and slot["best"] is None
                                   else "PARTIAL_SEARCH")
        common.update_json(Path(dirs["task"]) / "starts" / f"{index:03d}.slot.json", slot)
        common.atomic_json(Path(dirs["task"]) / "starts" / f"{index:03d}.json", slot)
        remote.start_end(index, slot["execution_state"], used)
        start_records.append(slot)
        evaluations_total += used

    result = assemble(common, payload, reading, start_records, legal_witness, remote,
                      boot, frames_sha, payload_sha, evaluations_total)
    common.atomic_json(Path(dirs["task"]) / "search_result.json",
                       dict(result, schema="iscat167.search_result.1"))
    remote.done(result, 0)
    return 0


def run_gate(common, payload: dict) -> dict:
    """Run the bundled single-payload gate and describe what it accepted.

    The bundle gate validates by raising, so refusal propagates as a worker
    fatal rather than being downgraded to a warning.  The report below is
    derived from the payload the gate just accepted plus the gate module's own
    source identity; it never relaxes a check the gate made.
    """
    v167_payload_gate = common.load_payload_gate()

    accepted = v167_payload_gate.validate(payload)
    common.require(accepted is payload, "PAYLOAD_GATE_RETURN_IDENTITY")
    reading = payload["reading"]
    common.require(isinstance(reading, dict), "PAYLOAD_GATE_READING_NOT_OBJECT")
    # Independent count of reading-shaped objects anywhere in the accepted
    # payload: two sigma rows in one task is the exact V166 defect, so this is
    # re-derived here instead of trusting the schema check alone.
    holders = []

    def visit(value, path):
        if isinstance(value, dict):
            if set(value) == set(common.READING_KEYS):
                holders.append(path)
            for key, child in value.items():
                visit(child, path + "." + str(key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, path + f"[{index}]")

    visit(payload, "payload")
    common.require(len(holders) == 1, "WORKER_READING_CONTAINER_COUNT:" + str(holders))
    return {
        "gate_module": v167_payload_gate.__name__,
        "gate_api": "validate",
        "gate_sha256": common.sha_file(Path(v167_payload_gate.__file__).resolve()),
        "gate_result": "ACCEPTED",
        "refusal_would_raise": "ValueError",
        "top_level_keys": sorted(payload),
        "reading_keys": sorted(reading),
        "reading_count": 1,
        "reading_containers": holders,
        "schema": payload["schema"],
        "scope": payload["scope"],
        "model_calls": 0,
    }


def assemble(common, payload, reading, start_records, legal_witness, remote, boot,
             frames_sha, payload_sha, evaluations_total) -> dict:
    base = {
        "task_id": payload["task_id"], "group": payload["group"],
        "replicate": payload["reading"]["replicate"],
        "sigma_nm": payload["reading"]["sigma_nm"], "reading_id": reading.reading_id,
        "B": payload["B"], "scope": payload["scope"], "starts": start_records,
        "best_legal_witness": legal_witness, "frames_sha256": frames_sha,
        "payload_sha256": payload_sha, "evaluations_total": evaluations_total,
        "interpreter": {"executable": sys.executable, "version": sys.version.split()[0],
                        "flags": [arg for arg in (sys.flags.ignore_environment,
                                                  sys.flags.dont_write_bytecode)]},
        "module_identity": boot["module_identity"],
        "remote_observations": {"forward_requests": remote.forward_requests,
                                "charged_forwards": remote.charged_forwards,
                                "cache_hit_forwards": remote.cache_hit_forwards,
                                "max_forward_ms": remote.max_forward_ms},
        "physical_qualification": "CONDITIONAL_SIMULATED_F2C_DEVELOPMENT",
        "parameter_bounds_D_nm": [30.0, 200.0],
        "D_domain_is_not_a_compatibility_claim": True,
        "global_uniqueness_certified": False,
        "known_compatible_D_interval_nm": None, "known_compatible_components": [],
        "reportable_D": None,
    }
    valid = [s for s in start_records if s.get("best") is not None
             and s["execution_state"] in ("FINISHED", "PARTIAL_SEARCH")]
    if not valid:
        return dict(base, execution_state="FAILED", optimizer_best=None, theta=None,
                    candidate_D_nm=None, reason_codes=["NO_VALID_OPTIMIZER_WITNESS"])
    optimizer_best = min((s["best"] for s in valid), key=lambda b: b["Q_total"])
    tolerance = max(1e-9, 1e-10 * max(1.0, abs(legal_witness["Q_total"])))
    if optimizer_best["Q_total"] > legal_witness["Q_total"] + tolerance:
        return dict(base, execution_state="FAILED", optimizer_best=optimizer_best,
                    theta=None, candidate_D_nm=None,
                    reason_codes=["SEARCH_INCOMPLETE_OR_IMPLEMENTATION_ERROR"])
    partial = any(s["execution_state"] != "FINISHED" for s in start_records)
    reason_codes = ["OPENED_DEVELOPMENT_SIMULATED_HEIGHT_READINGS", "ALL_REPORTABLE_D_NULL",
                    "LOCAL_BOUNDED_SEARCH_NOT_GLOBAL_UNIQUENESS"]
    if partial:
        reason_codes.append("PARTIAL_SEARCH")
    theta = [float(v) for v in optimizer_best["theta"]]
    return dict(base, execution_state="PARTIAL_SEARCH" if partial else "FINISHED",
                optimizer_best=optimizer_best, theta=theta, candidate_D_nm=theta[0],
                candidate_D=theta[0], candidate_h_nm=theta[1], candidate_x_nm=theta[2],
                candidate_y_nm=theta[3],
                development_diagnostic_pool_best=(optimizer_best if optimizer_best["Q_total"]
                                                  <= legal_witness["Q_total"] else legal_witness),
                reason_codes=reason_codes,
                passes_used=sum(len(s["passes"]) for s in start_records))


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except SystemExit:
        # sys.exit() inside main (and the normal exit from the line above) must
        # reach the interpreter: swallowing it here would report every clean
        # worker round, including every successful probe, as exit 70.
        raise
    except BaseException as exc:
        sys.stderr.write("WORKER_FATAL:" + type(exc).__name__ + ":" + str(exc) + "\n")
        sys.stderr.write(traceback.format_exc())
        sys.stderr.flush()
        sys.exit(70)
