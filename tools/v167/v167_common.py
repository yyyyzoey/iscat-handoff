"""Shared V167 identities, durable IO and the frozen scorer.

Estimator-visible surface only: no plan table, no seed, no epsilon, no truth
path, no truth-valued key.  Frozen scientific definitions are copied verbatim
from the byte-verified V166 production runner and cross-checked by
tools/v167/tests/test_v167_frozen_literals.py against the committed source.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "tools" / "v167_bundle"
APPROVED_CORE = BUNDLE / "approved_core"
BUNDLE_CODE = BUNDLE / "code"
PAYLOAD_GATE = BUNDLE_CODE / "v167_payload_gate.py"
PLAN_ROOT = ROOT / "results" / "v167_prepared"
OUT = ROOT / "results" / "v167"
V166 = OUT.parent / "v166"
# V166 charged prediction documents survive only in the parent workstation
# checkout; they are not tracked in Git and were not packed in the return ZIP.
PARENT_WS = ROOT.parent / "v166" / "results" / "v166"

PARENT_COMMIT = "06b35cd4e0a47f7f49ef4b05401a07266f2c03b6"
MODEL_ID = "v142-F2c-75860d222dd8e90d8dc2e31111e52ccbbb212a01c0d6a0dfe7fdbcdb241c98c3"

PHASES = {"MODEL_BINDING": 200, "SEARCH_EXTENSION": 2000, "BIAS_STRESS": 7200, "FINAL_VERIFY": 600}
TOTAL = 10000
OWNER = "v167-model-service"
LOADER_TASK = "V167_LOADER_1"
BINDING_TASK = "V167_BINDING"
FINAL_TASK = "V167_FINAL_VERIFY"

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
LOW = [30.0, 350.0, -500.0, -500.0]
HIGH = [200.0, 550.0, 500.0, 500.0]

GROUPS = ("ANON_01", "ANON_02", "ANON_03", "ANON_04")
PAYLOAD_KEYS = {"schema", "task_id", "group", "B", "reading", "starts", "cap_per_start", "task_cap", "scope"}
READING_KEYS = {"reading_id", "group", "B", "replicate", "sigma_nm", "z_nm", "hypothetical"}
# Keys that must never appear inside anything an estimator process reads.
FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {"D_scene_nm", "h_scene_nm", "epsilon", "D_true", "h_true", "seed",
     "truth_file_sha256", "source_truth_sha256", "controlled_offset_nm",
     "bias_nm", "z_nm_zero_bias", "entries", "plan", "readings"}
)

# Two different v152_budget_store.py files exist in this repository: the tracked
# tools/ copy has charge(task, owner, theta) and cannot carry charge-binding
# detail, while the copy actually used by the published V166 execution carries
# detail=.  V167 must import the latter and refuse anything else.
BUDGET_STORE = ROOT / "tools" / "v165_bundle" / "code" / "v152_budget_store.py"
BUDGET_STORE_SHA256 = "98615b608f57f8ba531fc6a304aa45b371d8b24ca7793c0c252bb827847808b9"
GLS_CORE_SHA256 = "a1746e4feb56136cdba15013cefc1e318f5fda690837564226e32f80db713bb5"
OBJECTIVE_SHA256 = "7d013551d9ae155de023daa1e1a6ad5678c6b038ae217fa79fe22c4e4eed64bd"
PAYLOAD_GATE_SHA256 = "1d39764e91875673bf11d5f1e6e456be9cc214d27994f439145d98f049185b5c"
V166_RUN_SHA256 = "92ed6ca791039b8304050def6d81a8a1cd6648e0dc0bef1bd3d76917b1798deb"
ESTIMATOR_CODE_FILES = ("v167_common.py", "v167_jail.py", "v167_rpc.py", "v167_worker.py")
CONTROLLER_ONLY_CODE_FILES = ("v167_service.py", "v167_controller.py", "v167_runner.py",
                              "v167_validator.py", "v167_rpc.py", "run_all.py")


def bootstrap_paths(*, estimator: bool) -> dict:
    """Deterministic module resolution; the estimator never sees the V166 runner dir.

    approved_core supplies the byte-verified frozen objective/gls modules,
    tools/v167 supplies the V167 estimator modules, and only the trusted service
    additionally gets the directory holding v165_run/v165_io.
    """
    # Priority order, highest first.  ROOT/tools holds older copies of both
    # v152_budget_store.py and v152_gls_core.py, so it always goes last; it is
    # only needed for the model runtime modules the bundle does not carry.
    ordered = [str(APPROVED_CORE), str(ROOT / "tools" / "v167")]
    if not estimator:
        ordered = [str(BUDGET_STORE.parent)] + ordered + [str(ROOT / "tools")]
    for entry in ordered:
        while entry in sys.path:
            sys.path.remove(entry)
    for entry in reversed(ordered):
        sys.path.insert(0, entry)
    recorded = []
    for entry in ordered:
        if entry not in sys.path:
            raise AssertionError("SYS_PATH_NOT_APPLIED:" + entry)
        recorded.append(entry)
    return {"schema": "iscat167.path_bootstrap.1", "estimator": estimator,
            "inserted_in_order": recorded, "sys_path_head": list(sys.path[: len(recorded) + 2])}


def verify_frozen_module_identities(*, estimator: bool) -> dict:
    """Pin the exact module bytes the round runs on, before any model call."""
    import inspect

    v167_payload_gate = load_payload_gate()
    import v152_gls_core
    import v165_objective

    checks = {
        "v152_gls_core": (Path(v152_gls_core.__file__).resolve(), GLS_CORE_SHA256),
        "v165_objective": (Path(v165_objective.__file__).resolve(), OBJECTIVE_SHA256),
        "v167_payload_gate": (Path(v167_payload_gate.__file__).resolve(), PAYLOAD_GATE_SHA256),
    }
    if not estimator:
        import v152_budget_store
        checks["v152_budget_store"] = (Path(v152_budget_store.__file__).resolve(),
                                       BUDGET_STORE_SHA256)
    rows = {}
    for name, (path, expected) in checks.items():
        actual = sha_file(path)
        require(actual == expected, "FROZEN_MODULE_BYTES_CHANGED:" + name + ":" + str(path))
        rows[name] = {"path": str(path), "sha256": actual, "bytes": path.stat().st_size}
    parameters: list[str] = []
    if estimator:
        # An estimator process holds no ledger at all: billing belongs to the service.
        require(str(ROOT / "tools") not in sys.path, "ESTIMATOR_PATH_EXPOSES_V166_RUNNER_DIR")
        require("v152_budget_store" not in sys.modules, "ESTIMATOR_IMPORTED_LEDGER_MODULE")
    else:
        # The ledger must be the detail-aware copy V166 actually used, not the bare tools/ one.
        require(Path(rows["v152_budget_store"]["path"]) == BUDGET_STORE.resolve(),
                "WRONG_BUDGET_STORE_PATH:" + rows["v152_budget_store"]["path"])
        parameters = list(inspect.signature(v152_budget_store.BudgetStore.charge).parameters)
        require("detail" in parameters, "BUDGET_STORE_CHARGE_CANNOT_BIND_DETAIL")
    # Only an estimator process must be free of these: the trusted controller imports
    # its own service and runner by design.
    absent = (["v165_io", "v165_run", "v167_plan", "v167_controller", "v167_service",
               "v167_runner", "v167_validator", "v166_controller", "v166_production"]
              if estimator else ["v165_io", "v165_run", "v167_plan"])
    for name in absent:
        require(name not in sys.modules, "UNEXPECTED_MODULE_ALREADY_IMPORTED:" + name)
    return {"schema": "iscat167.frozen_module_identity.1",
            "role": "estimator" if estimator else "trusted_service", "modules": rows,
            "budget_store_charge_parameters": parameters,
            "absent_from_sys_modules": absent}


class JailViolation(RuntimeError):
    """Raised by the worker file-access guard.  Non-adversarial runtime isolation."""


class ServiceError(RuntimeError):
    pass


class FatalPersistenceError(RuntimeError):
    pass


def require(test: bool, message: str) -> None:
    if not test:
        raise ValueError(message)


def load_payload_gate():
    """Load the bundled single-payload gate from its pinned file bytes.

    The gate lives beside the controller-only planner, so it is deliberately the
    one named file in that directory an estimator may read.  A plain ``import``
    would make the import machinery stat and list the whole directory, which the
    worker jail refuses, and would put ``v167_plan.py`` on the search path too.
    Loading by explicit file identity avoids both and still registers the module
    as ``sys.modules["v167_payload_gate"]``.
    """
    import types

    name = "v167_payload_gate"
    module = sys.modules.get(name)
    if module is not None:
        return module
    raw = PAYLOAD_GATE.read_bytes()
    require(sha_bytes(raw) == PAYLOAD_GATE_SHA256, "PAYLOAD_GATE_BYTES_CHANGED")
    module = types.ModuleType(name)
    module.__file__ = str(PAYLOAD_GATE)
    sys.modules[name] = module
    try:
        exec(compile(raw.decode("utf-8"), str(PAYLOAD_GATE), "exec"), module.__dict__)
    except BaseException:
        del sys.modules[name]
        raise
    return module


def canon(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(Path(path).read_bytes())


def blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def array_sha(array: np.ndarray) -> str:
    return sha_bytes(np.ascontiguousarray(array, dtype=np.float64).tobytes())


def array_meta(array: np.ndarray) -> dict:
    contiguous = np.ascontiguousarray(array, dtype=np.float64)
    return {"shape": list(contiguous.shape), "dtype": "float64",
            "sha256": sha_bytes(contiguous.tobytes())}


def theta_hex(theta: Any) -> str:
    t = np.asarray(theta, dtype=float)
    require(t.shape == (4,) and np.isfinite(t).all(), "NONFINITE_THETA")
    # repr(float) round-trips exactly in CPython 3, so this is a bit-level key.
    return sha_bytes("\n".join(repr(float(x)) for x in t).encode("ascii"))


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_bytes().decode("utf-8-sig"))


def atomic_json(path: Path, value: Any) -> str:
    """Write new only, fsync, then re-read and compare.  Never overwrites."""
    path = Path(path)
    require(str(path) != os.devnull, "DEVNULL_OUTPUT_FORBIDDEN")
    if path.parent.exists():
        require(path.parent.is_dir(), "OUTPUT_PARENT_NOT_A_DIR:" + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canon(value)
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    if tmp.exists():
        tmp.unlink()
    with tmp.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        path.open("xb").close()
    except FileExistsError as exc:
        raise FatalPersistenceError("OUTPUT_PATH_ALREADY_EXISTS:" + str(path)) from exc
    os.replace(tmp, path)
    if read_json(path) != value:
        raise FatalPersistenceError("OUTPUT_READBACK_MISMATCH:" + str(path))
    return sha_bytes(raw)


def write_text_new(path: Path, text: str) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = text.encode("utf-8")
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    return sha_bytes(raw)


def update_json(path: Path, value: Any) -> str:
    """Replace an existing mutable evidence file in place (tmp + fsync + os.replace).

    Exactly two document classes are mutable, and both are rolling pointers rather
    than sealed evidence: the per-pass RUNNING checkpoint, and the per-pass best-so-far
    file, which one pass rewrites on every improvement.  Filenames in both classes
    carry the start *and* pass index, so no other pass or task can reach the same
    path.  Every other artefact keeps the write-new discipline of atomic_json so that
    no charged or sealed evidence can be silently overwritten.
    """
    path = Path(path)
    require(str(path) != os.devnull, "DEVNULL_OUTPUT_FORBIDDEN")
    require(path.is_file(), "UPDATE_REQUIRES_EXISTING_FILE:" + str(path))
    raw = canon(value)
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    if tmp.exists():
        tmp.unlink()
    with tmp.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    if read_json(path) != value:
        raise FatalPersistenceError("OUTPUT_READBACK_MISMATCH:" + str(path))
    return sha_bytes(raw)


def finite_number(value: Any) -> bool:
    return type(value) in (float, int) and math.isfinite(float(value))


def check_theta(theta: Any) -> np.ndarray:
    t = np.asarray(theta, dtype=float)
    if t.shape != (4,) or not np.isfinite(t).all() or np.any(t < np.asarray(LOW)) or np.any(t > np.asarray(HIGH)):
        raise ValueError("INVALID_FROZEN_PARAMETER_DOMAIN_NO_CLIP")
    if t[1] - t[0] / 2 < 100.0:
        raise ValueError("SURFACE_GAP_OUTSIDE_DOMAIN")
    return t


def group_of(task_id: str) -> str | None:
    """A V167 task id must not encode its anonymous group, bias or replicate."""
    require(isinstance(task_id, str) and task_id.startswith("V167_"), "TASK_ID_SHAPE")
    for group in GROUPS:
        if group in task_id or group.lower() in task_id.lower():
            return group
    for token in ("_H1_", "_H10_", "_NO_HEIGHT", "_R0", "ANON"):
        if token in task_id:
            return "?leaked"
    return None


def scan_forbidden(doc: Any, where: str) -> list[str]:
    """Every truth-valued or controller-only key path anywhere inside doc.

    Used by the worker payload projection check and by the three-frame loader, so
    a renamed or split field cannot reach an estimator process through either of
    the two documents a worker is allowed to read.
    """
    problems: list[str] = []

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                name = str(key)
                if name in FORBIDDEN_PAYLOAD_KEYS:
                    problems.append(path + "." + name)
                visit(child, path + "." + name)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, path + f"[{index}]")

    visit(doc, where)
    return problems


def projection_check(payload: Any, *, where: str) -> dict:
    """Independent re-check of the single-reading projection inside the worker.

    Complements the bundled payload gate: this one forbids every truth-valued or
    controller-only key anywhere in the document and refuses group leakage in the
    task id, so a renamed or split field cannot slip past the schema gate.
    """
    require(isinstance(payload, dict), "PAYLOAD_NOT_OBJECT:" + where)
    problems = scan_forbidden(payload, where)
    require(not problems, "TRUTH_OR_CONTROLLER_KEY_IN_WORKER_INPUT:" + ";".join(problems))
    check_task_id_identity(payload)
    # A start that cannot be used is refused before any model call is billed.
    starts = payload["starts"]
    require(isinstance(starts, list) and 1 <= len(starts) <= 2, "WORKER_START_COUNT:" + where)
    for index, start in enumerate(starts):
        require(isinstance(start, list) and len(start) == 4, "WORKER_START_SHAPE:" + str(index))
        check_theta(start)
    require(type(payload["cap_per_start"]) is int and payload["cap_per_start"] > 0,
            "WORKER_CAP_PER_START:" + where)
    require(type(payload["task_cap"]) is int and
            payload["task_cap"] == payload["cap_per_start"] * len(starts),
            "WORKER_TASK_CAP_GRID:" + where)
    return {"scope": "WORKER_INPUT_KEY_SCAN_SINGLE_READING_ONLY",
            "forbidden_keys": sorted(FORBIDDEN_PAYLOAD_KEYS),
            "offenders": problems, "model_calls": 0}


def check_task_id_identity(payload: dict) -> None:
    tid = payload["task_id"]
    require(set(payload) == PAYLOAD_KEYS, "WORKER_PAYLOAD_KEYS")
    require(set(payload["reading"]) == READING_KEYS, "WORKER_READING_KEYS")
    require(group_of(tid) is None, "TASK_ID_LEAKS_GROUP_OR_CONDITION:" + tid)
    require(tid == payload["reading"]["reading_id"], "READING_ID_NOT_TASK_ID")


def score_document(theta: Any, c: Any, data: Any, reading: Any) -> dict:
    """Frozen scorer shared by estimator and validator: asserts both identities."""
    from v165_objective import augmented_objective

    doc = augmented_objective(data, c, theta, reading)
    half = 0.5 * float(doc["residual"] @ doc["residual"])
    expected = 0.5 * (doc["Q_model"] + doc["Q_height"])
    require(abs(half - expected) <= max(1e-10, 1e-12 * max(1.0, abs(expected))),
            "SCIPY_HALF_COST_IDENTITY")
    require(abs(doc["Q_total"] - (2.0 * half + doc["K"])) <= max(1e-8, 1e-10 * abs(doc["Q_total"])),
            "Q_TOTAL_FROM_DOUBLE_COST_PLUS_K")
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
        "q_total_identity_abs_error": doc["Q_total"] - (2.0 * half + doc["K"]),
        "residual": np.asarray(doc["residual"], dtype=float).tolist(),
        "residual_sha256": array_sha(np.asarray(doc["residual"], dtype=float)),
        "residual_shape": list(np.asarray(doc["residual"], dtype=float).shape),
        "reportable_D": None,
    }


def reading_from_document(reading: dict):
    """Rebuild the frozen HeightReading the estimator is allowed to hold.

    Only the seven public reading fields cross into the worker; the frozen
    dataclass has no scene-diameter, scene-height or epsilon field at all, so a
    truth value cannot be carried even if a projection bug let one through the
    key scan.
    """
    from v165_objective import HeightReading

    require(set(reading) == READING_KEYS, "WORKER_READING_KEYS")
    return HeightReading(
        reading_id=str(reading["reading_id"]),
        group=str(reading["group"]),
        replicate=int(reading["replicate"]),
        sigma_nm=float(reading["sigma_nm"]),
        z_nm=float(reading["z_nm"]),
        hypothetical=bool(reading["hypothetical"]),
    )


def frames_from_document(document: dict, *, where: str) -> tuple[Any, dict, str]:
    """Build GlsData for exactly one group from its own three-frame document.

    The staged file is the whole V166 source-context document and is scanned for
    forbidden keys before anything is taken from it, so the frame side channel
    cannot carry a truth-valued field into an estimator process either.
    """
    from v152_gls_core import GlsData

    require(isinstance(document, dict), "FRAMES_DOCUMENT_NOT_OBJECT:" + where)
    problems = scan_forbidden(document, where)
    require(not problems,
            "TRUTH_OR_CONTROLLER_KEY_IN_FRAMES_INPUT:" + ";".join(problems))
    diagnostic = document.get("diagnostic")
    require(isinstance(diagnostic, dict), "FRAMES_DOCUMENT_MISSING_DIAGNOSTIC:" + where)
    frame_y = np.asarray(diagnostic["frame_Y"], dtype=float)
    frame_v = np.asarray(diagnostic["frame_V"], dtype=float)
    require(frame_y.shape == (3, 13, 13) and frame_v.shape == (3, 13, 13),
            "THREE_FRAME_CONTEXT_REQUIRED:" + where)
    require(np.isfinite(frame_y).all() and np.isfinite(frame_v).all(),
            "NONFINITE_FRAMES:" + where)
    require(bool(np.all(frame_v > 0)), "NONPOSITIVE_VARIANCE:" + where)
    data = GlsData.from_frames(frame_y, frame_v)
    identity = {"frame_Y": array_meta(frame_y), "frame_V": array_meta(frame_v),
                "ybar": array_meta(np.asarray(data.ybar, dtype=float)),
                "vbar": array_meta(np.asarray(data.vbar, dtype=float)),
                "constant_K": float(data.constant_K)}
    frames_sha = sha_bytes(canon(identity))
    return data, identity, frames_sha


def task_dirs(task_id: str) -> dict:
    jail = OUT / "estimator_inputs" / task_id
    return {"jail": jail, "task": OUT / "tasks" / task_id,
            "input": jail / "input.json", "frames": jail / "frames.json",
            "predictions": OUT / "tasks" / task_id / "predictions"}
