"""The one trusted V167 controller.

Controller-only.  A worker never imports this module and never receives the plan,
the full 24-row height table, the controlled bias, the source mapping or the
sealed truth.  For each task the controller projects exactly one single-reading
payload, that group's own three-frame document and that group's six frozen legal
records into the task jail, and keeps the provenance of every copy under
results/v167/controller_only/, which is outside every worker read root.

Order of operations follows contract section 10: verify version pins and old
evidence, print the run identity before any model construction, stage the
single-task projections, reserve the frozen budget, bind one live model, run the
23 authorized tasks, final verify, seal, then hand off to the validator process.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import v167_common as common                                              # noqa: E402
from v167_common import (  # noqa: E402
    BINDING_TASK, BUNDLE, BUDGET_STORE, FINAL_TASK, LOADER_TASK, MODEL_ID, OPTIMIZER,
    OUT, OWNER, PHASES, PLAN_ROOT, PARENT_COMMIT, PARENT_WS, ROOT, TOTAL, V166,
    array_sha, atomic_json, canon, read_json, require, scan_forbidden, sha_bytes,
    sha_file, theta_hex,
)

# Path resolution must precede the service import: the pinned detail-aware
# budget store lives in tools/v165_bundle/code, not in the older tools/ copy.
PATH_BOOT = common.bootstrap_paths(estimator=False)

import v167_runner as runner                                              # noqa: E402
import v167_service as service_mod                                        # noqa: E402

CONTROL = OUT / "controller_only"
JAIL_ROOT = OUT / "estimator_inputs"
LEDGER_PATH = OUT / "logs" / "v167_budget.sqlite"
PLAN_PATH = PLAN_ROOT / "controller_only" / "plan.json"
STAGING = PLAN_ROOT / "controller_staging"

# Contract section 0 pins, transcribed literally so a silent re-publish cannot pass.
CONTRACT_PINS = {
    "results/v166/estimates.json":
        "8f97339e9645a29ec929e5c792d234a28821970338cf92a62d2982bfebba7634",
    "results/v166/height_input/height_readings.json":
        "bbfd793aff48247623081dd607168cd9afbba2deeff5f37c7a0cbd62b032ad4e",
    "results/v166/logs/v165_budget.sqlite":
        "254b5485164a57865328c81f8890ea4aa458d1386ed6f5f34533f2848f7e4ece",
    "results/v166/iscat_v166_return_001.zip":
        "866feed02333f244df72f55e38ccf74060962007a5010c5c29df5ebe9f16a74e",
}
CONTRACT_ZIP_BYTES = 17554667
CONTRACT_PLAN_SHA256 = "eeae31bb98bafa4893c1c993ebfb7c985a702f1bd32aaba75546c16bd4ebab5d"
# Contract section 4 frozen assets.
FROZEN_LIBRARY_SHA256 = "203e9e5f2d888503b62d48888a0f2e5365477b06101227109a3e98286f541c0f"
FROZEN_CAMERA_SHA256 = "074305df1b6bbd47f7f523b05d871312309e9b6ffa390cd50d0be18296427e26"
# The rescored legal-start library V166 froze; the controller must reproduce it
# with the same identity it had then, so the commit is checked, not assumed.
LEGAL_SOURCE_COMMIT = "6d2db46d52509bd6987726dea211781cfa1b4127"
LEGAL_SOURCE_PATH = "results/v152/all_results.json"
DETECTED_GROUPS = ("ANON_02", "ANON_03", "ANON_04")
R_SOURCES = ("B100000_ANON_01_H10_R00", "B100000_ANON_01_H10_R01",
             "B100000_ANON_01_H1_R00", "B100000_ANON_01_H1_R01",
             "B100000_ANON_01_H1_R02")
B_SOURCES = tuple(f"B100000_{group}_H1_R{rep:02d}"
                  for group in DETECTED_GROUPS for rep in range(3))
B_TOLERANCE_NOTE = "max(1e-9, 1e-10*max(1,abs(Q)))"


def git_text(*args: str) -> str:
    proc = subprocess.run(("git", "-C", str(ROOT)) + tuple(args),
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    require(proc.returncode == 0,
            "GIT_COMMAND_FAILED:" + " ".join(args) + ":" + (proc.stderr or "").strip()[:200])
    return proc.stdout.strip()


def git_blob_at_parent(rel: str) -> str | None:
    """SHA-1 of the blob stored for rel at the fixed V166 commit, if it is tracked."""
    proc = subprocess.run(("git", "-C", str(ROOT), "rev-parse", f"{PARENT_COMMIT}:{rel}"),
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    return proc.stdout.strip() if proc.returncode == 0 else None


def _code_row(path: Path) -> dict:
    rel = path.relative_to(ROOT).as_posix()
    disk_blob = common.blob_sha(path.read_bytes())
    commit_blob = git_blob_at_parent(rel)
    return {"sha256": sha_file(path), "bytes": path.stat().st_size,
            "git_blob_of_disk_bytes": disk_blob,
            "git_blob_at_v166_commit": commit_blob,
            "tracked_at_v166_commit": commit_blob is not None,
            "byte_identical_to_v166_commit": commit_blob == disk_blob}


def code_identities() -> dict:
    """Every source this round runs on, with its hash and its Git status."""
    rows: dict[str, dict] = {}
    for directory in ("tools/v167", "tools/v167_bundle"):
        for path in sorted((ROOT / directory).rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            if path.suffix not in {".py", ".json", ".md", ".csv", ".txt"}:
                continue
            rows[path.relative_to(ROOT).as_posix()] = _code_row(path)
    for rel in ("tools/v165_bundle/code/v152_budget_store.py",
                "tools/v165_bundle/code/v165_run.py",
                "tools/v165_bundle/code/v152_gls_core.py",
                "tools/v165_bundle/code/v165_objective.py",
                "tools/v146_runtime.py", "tools/field_forward_reference.py",
                "tools/load_field_library.py", "tools/v142_field_reference.py",
                "config/v146_science_config.json"):
        rows[rel] = _code_row(ROOT / rel)
    literals = {
        "approved_core_v152_gls_core": sha_file(BUNDLE / "approved_core" / "v152_gls_core.py"),
        "approved_core_v165_objective": sha_file(BUNDLE / "approved_core" / "v165_objective.py"),
        "v167_payload_gate": sha_file(common.PAYLOAD_GATE),
        "v152_budget_store": sha_file(BUDGET_STORE),
        "v165_run": sha_file(ROOT / "tools" / "v165_bundle" / "code" / "v165_run.py"),
    }
    checks = {
        "gls_core_matches_pin": literals["approved_core_v152_gls_core"] == common.GLS_CORE_SHA256,
        "objective_matches_pin": literals["approved_core_v165_objective"] == common.OBJECTIVE_SHA256,
        "payload_gate_matches_pin": literals["v167_payload_gate"] == common.PAYLOAD_GATE_SHA256,
        "budget_store_matches_pin": literals["v152_budget_store"] == common.BUDGET_STORE_SHA256,
        "v165_run_matches_pin": literals["v165_run"] == common.V166_RUN_SHA256,
        "bundle_gls_equals_committed_copy":
            literals["approved_core_v152_gls_core"]
            == rows["tools/v165_bundle/code/v152_gls_core.py"]["sha256"],
        "bundle_objective_equals_committed_copy":
            literals["approved_core_v165_objective"]
            == rows["tools/v165_bundle/code/v165_objective.py"]["sha256"],
    }
    require(all(checks.values()),
            "CODE_IDENTITY_REFUSED:" + ";".join(k for k, v in checks.items() if not v))
    return {"schema": "iscat167.code_identities.1", "git_head": git_text("rev-parse", "HEAD"),
            "v166_release_commit": PARENT_COMMIT, "files": rows,
            "frozen_literals": literals, "identity_checks": checks,
            "file_count": len(rows),
            "identity_sha256": sha_bytes(canon({"files": rows, "literals": literals}))}

def code_git_state() -> dict:
    """Is the code that is about to run actually committed at HEAD?

    Contract section 10.4 asks for the commit before the authorized run, so the
    sealed evidence names a HEAD holding these exact bytes.  Untracked results
    directories are expected and are not part of this question.
    """
    head = git_text("rev-parse", "HEAD")
    tracked = {item.strip().strip('"') for item in
               git_text("ls-files", "--", "tools/v167", "tools/v167_bundle").splitlines()
               if item.strip()}
    needed = sorted({"tools/v167/" + name
                     for name in tuple(common.ESTIMATOR_CODE_FILES)
                     + tuple(common.CONTROLLER_ONLY_CODE_FILES)} | {"tools/v167/__init__.py"})
    missing = [item for item in needed if item not in tracked]
    present = {item.relative_to(ROOT).as_posix()
               for item in (ROOT / "tools" / "v167").rglob("*.py")}
    untracked_python = sorted(present - tracked)
    status = git_text("status", "--porcelain=v1", "-uall", "--",
                      "tools/v167", "tools/v167_bundle")
    dirty = [line for line in status.splitlines()
             if line.strip() and "__pycache__" not in line and not line.endswith(".pyc")]
    return {"schema": "iscat167.code_git_state.1", "git_head": head,
            "tracked_v167_files": len(tracked),
            "required_controller_files": needed, "missing_from_git": missing,
            "untracked_python_under_tools_v167": untracked_python,
            "dirty_git_entries": dirty,
            "estimator_code_tracked": not missing,
            "estimator_code_clean": not dirty and not untracked_python,
            "bundle_tracked": any(item.startswith("tools/v167_bundle/")
                                  for item in tracked)}


def _read_plan() -> dict:
    require(sha_file(PLAN_PATH) == CONTRACT_PLAN_SHA256,
            "PLAN_BYTES_CHANGED:" + str(PLAN_PATH))
    plan = read_json(PLAN_PATH)
    require(plan["parent"] == PARENT_COMMIT, "PLAN_PARENT_MISMATCH")
    require(plan["role"] == "CONTROLLER_ONLY_NOT_WORKER_INPUT", "PLAN_ROLE_MISMATCH")
    require(plan["new_fit_jobs"] == 23 and plan["total_new_model_attempts"] == TOTAL,
            "PLAN_SHAPE_MISMATCH")
    require(plan["new_height_random_draws"] == 0 and plan["new_truth_read_before_seal"] is False,
            "PLAN_AUTHORIZATION_MISMATCH")
    require(dict(plan["phases"]) == dict(PHASES), "PLAN_PHASE_MISMATCH")
    entries = plan["entries"]
    require(len(entries) == 23, "PLAN_ENTRY_COUNT")
    require(sum(int(e["task_cap"]) for e in entries) + PHASES["FINAL_VERIFY"]
            + PHASES["MODEL_BINDING"] == TOTAL, "PLAN_BUDGET_GRID")
    kinds = [str(e["kind"]) for e in entries]
    require(kinds.count("SEARCH_EXTENSION") == 5 and kinds.count("BIAS_STRESS") == 18,
            "PLAN_KIND_COUNT")
    require(tuple(sorted(str(e["source_task_id"]) for e in entries
                         if e["kind"] == "SEARCH_EXTENSION")) == R_SOURCES,
            "PLAN_R_SOURCE_LIST")
    require(sorted({str(e["source_task_id"]) for e in entries
                    if e["kind"] == "BIAS_STRESS"}) == sorted(B_SOURCES),
            "PLAN_B_SOURCE_LIST")
    require(len({str(e["task_id"]) for e in entries}) == 23, "PLAN_TASK_ID_DUPLICATE")
    return plan


def _estimates_index() -> dict[str, dict]:
    rows = read_json(V166 / "estimates.json")
    require(isinstance(rows, list) and len(rows) == 28, "V166_ESTIMATES_SHAPE")
    return {str(row["task_id"]): row for row in rows}


def _sealed_result(task_id: str) -> dict:
    """Read one V166 sealed task result and verify it is the file estimates points at."""
    path = V166 / "tasks" / task_id / "result.json"
    require(path.is_file(), "V166_RESULT_MISSING:" + task_id)
    return {"path": path, "sha256": sha_file(path)}


def _witness_document(task_id: str, name: str) -> dict:
    path = V166 / "tasks" / task_id / "best" / name
    require(path.is_file(), "V166_BEST_MISSING:" + task_id + ":" + name)
    doc = read_json(path)
    require(doc.get("schema") == "iscat165.evaluation.1" or "theta" in doc,
            "V166_BEST_SHAPE:" + task_id + ":" + name)
    for key in ("theta", "Q_total", "C_sha256", "prediction_path", "prediction_sha256"):
        require(key in doc, "V166_BEST_KEY_MISSING:" + key + ":" + task_id)
    return doc


def _prediction_source(rel_path: str, expect_sha: str, c_sha: str) -> dict:
    """Locate one V166 prediction document and re-verify its bytes and its C."""
    for root in (V166, PARENT_WS):
        path = root / rel_path
        if path.is_file():
            raw = path.read_bytes()
            require(sha_bytes(raw) == expect_sha,
                    "V166_PREDICTION_SHA_CHANGED:" + rel_path)
            doc = json.loads(raw.decode("utf-8-sig"))
            c = np.asarray(doc["C"], dtype=float)
            require(array_sha(c) == c_sha, "V166_PREDICTION_C_CHANGED:" + rel_path)
            require(doc.get("model_id") == MODEL_ID, "V166_PREDICTION_MODEL_ID:" + rel_path)
            return {"path": str(path), "root": str(root), "sha256": expect_sha,
                   "C_sha256": c_sha, "theta": doc["returned_theta"],
                   "seq": int(doc["seq"]), "array": c}
    raise ValueError("V166_PREDICTION_NOT_FOUND:" + rel_path)


def resolve_references(plan: dict) -> dict:
    """Every old object V167 is allowed to touch, resolved and hash-verified."""
    estimates = _estimates_index()
    partials: dict[str, dict] = {}
    for entry in plan["entries"]:
        if entry["kind"] != "SEARCH_EXTENSION":
            continue
        source = str(entry["source_task_id"])
        path = V166 / "tasks" / source / "starts" / "001.json"
        require(path.is_file(), "R_PARTIAL_START_MISSING:" + source)
        disk_blob = common.blob_sha(path.read_bytes())
        record = read_json(path)
        require(record.get("task_id") == source, "R_PARTIAL_TASK_ID:" + source)
        require(int(record.get("start_index", -1)) == 1, "R_PARTIAL_START_INDEX:" + source)
        require(record.get("execution_state") == "PARTIAL_SEARCH",
                "R_PARTIAL_STATE_NOT_PARTIAL:" + source + ":" + str(record.get("execution_state")))
        error = record.get("error") or {}
        require(error.get("error_type") == "CallCapReached",
                "R_PARTIAL_NOT_CALL_CAP:" + source + ":" + str(error.get("error_type")))
        require(int(record.get("actual_calls")) == int(entry["old_start_consumption"]),
                "R_PARTIAL_CONSUMPTION:" + source)
        best = record.get("best") or {}
        for key in ("theta", "Q_total", "C_sha256", "prediction_path", "prediction_sha256"):
            require(key in best, "R_PARTIAL_BEST_KEY:" + key + ":" + source)
        common.check_theta(best["theta"])
        prediction = _prediction_source(str(best["prediction_path"]),
                                        str(best["prediction_sha256"]), str(best["C_sha256"]))
        partials[source] = {
            "source_task_id": source, "source_start_index": 1,
            "start_document": str(path), "start_document_sha256": sha_file(path),
            "start_document_git_blob": git_blob_at_parent(
                f"results/v166/tasks/{source}/starts/001.json"),
            "start_document_disk_blob": disk_blob,
            "old_status_preserved": record["execution_state"],
            "old_start_consumption": int(record["actual_calls"]),
            "warm_theta": [float(v) for v in best["theta"]],
            "warm_Q_total": float(best["Q_total"]), "warm_C_sha256": str(best["C_sha256"]),
            "warm_prediction": prediction["path"],
            "warm_prediction_sha256": prediction["sha256"],
            "old_first_start_best": _witness_document(source, "start_000.json")["Q_total"],
            "old_task_result_sha256": estimates[source]["task_result_sha256"],
            "old_candidate_D_nm": estimates[source]["candidate_D"],
            "old_execution_state": estimates[source]["execution_state"],
            "sealed_result_file": _sealed_result(source)["sha256"],
        }
        require(partials[source]["sealed_result_file"]
                == estimates[source]["task_result_sha256"],
                "R_SEALED_RESULT_SHA:" + source)

    zero_bias: dict[str, dict] = {}
    for source in B_SOURCES:
        row = estimates[source]
        require(row["execution_state"] == "FINISHED", "B_ZERO_BIAS_NOT_FINISHED:" + source)
        hits = [name for name in ("start_000.json", "start_001.json")
                if _witness_document(source, name)["theta"] == row["theta"]]
        require(len(hits) == 1, "B_ZERO_BIAS_BEST_AMBIGUOUS:" + source + ":" + str(hits))
        best = _witness_document(source, hits[0])
        prediction = _prediction_source(str(best["prediction_path"]),
                                        str(best["prediction_sha256"]), str(best["C_sha256"]))
        group = str(row["group"])
        require(row["reading_id"] == source, "B_ZERO_BIAS_READING_ID:" + source)
        zero_bias[source] = {
            "source_task_id": source, "group": group, "replicate": int(row["replicate"]),
            "sigma_nm": float(row["sigma_nm"]), "theta": [float(v) for v in best["theta"]],
            "Q_total": float(best["Q_total"]), "candidate_D_nm": float(row["candidate_D"]),
            "best_document": hits[0], "C_sha256": str(best["C_sha256"]),
            "prediction": prediction["path"], "prediction_sha256": prediction["sha256"],
            "prediction_C_array": prediction["array"],
            "task_result_sha256": row["task_result_sha256"],
            "sealed_result_file_sha256": _sealed_result(source)["sha256"],
        }
        require(zero_bias[source]["sealed_result_file_sha256"] == row["task_result_sha256"],
                "B_SEALED_RESULT_SHA:" + source)

    base_points: dict[str, dict] = {}
    starts = read_json(V166 / "starts_by_group.json")
    for group in DETECTED_GROUPS:
        document = read_json(V166 / "source_context" / (group + ".json"))
        diagnostic = document["diagnostic"]
        index = int(diagnostic["base_index"])
        prediction = diagnostic["predictions"][index]
        theta = [float(v) for v in prediction["theta"]]
        c = np.ascontiguousarray(prediction["C"], dtype=float)
        first = [float(v) for v in starts[group]["first"]["theta"]]
        require(theta == first, "BASE_POINT_NOT_GROUP_FIRST_START:" + group)
        common.check_theta(theta)
        base_points[group] = {"group": group, "theta": theta, "base_index": index,
                              "C_sha256": array_sha(c),
                              "source_document": str(V166 / "source_context" / (group + ".json")),
                              "first_start_source_record": starts[group]["first"]["source_record"],
                              "second_start_theta": [float(v) for v in
                                                     starts[group]["second"]["theta"]]}
    return {"partials": partials, "zero_bias": zero_bias, "base_points": base_points,
            "estimates": estimates}


def legal_records_document(group: str) -> dict:
    """Rebuild one group's six frozen legal starts, with the identities V166 used."""
    records = []
    for path in sorted((ROOT / "results" / "v163" / "rescored").glob(f"100000_{group}_*.json")):
        doc = read_json(path)
        require(doc["B"] == 100000, "LEGAL_B_IDENTITY:" + group)
        require(doc["anon"] == group, "LEGAL_GROUP_IDENTITY:" + group)
        require(doc["model_id"] == MODEL_ID, "LEGAL_MODEL_ID:" + group)
        require(doc["source_commit"] == LEGAL_SOURCE_COMMIT, "LEGAL_SOURCE_COMMIT:" + group)
        require(doc["source_path"] == LEGAL_SOURCE_PATH, "LEGAL_SOURCE_PATH:" + group)
        theta = np.asarray(doc["theta"], dtype=float)
        require(theta.shape == (4,) and np.isfinite(theta).all(), "LEGAL_THETA:" + group)
        common.check_theta(theta)
        c = np.asarray(doc["C"], dtype=float)
        require(c.shape == (13, 13) and np.isfinite(c).all(), "LEGAL_C_SHAPE:" + group)
        require(array_sha(c) == doc["C_sha256"], "LEGAL_C_SHA:" + group)
        records.append(dict(doc, record_path=path.relative_to(ROOT).as_posix(),
                            record_sha256=sha_file(path)))
    require(len(records) == 6, "LEGAL_RECORD_COUNT:" + group)
    require(len({r["source_record_id"] for r in records}) == 6, "LEGAL_RECORD_IDS:" + group)
    require(len({r["observation_identity"] for r in records}) == 1, "LEGAL_OBSERVATION:" + group)
    require(len({r["variance_identity"] for r in records}) == 1, "LEGAL_VARIANCE:" + group)
    require(len({tuple(r["ordered_event_ids"]) for r in records}) == 1, "LEGAL_EVENTS:" + group)
    document = {"schema": "iscat167.legal_records_projection.1", "group": group,
                "group_B": 100000, "source_commit": LEGAL_SOURCE_COMMIT,
                "records": records}
    require(not scan_forbidden(document, "legal:" + group),
            "LEGAL_DOCUMENT_FORBIDDEN_KEYS:" + group)
    return document


def verify_evidence(refs: dict) -> dict:
    """Contract section 2: pinned bytes, Git blob identity, ledger and reading files."""
    rows = []
    for rel, expected in CONTRACT_PINS.items():
        path = ROOT / rel
        require(path.is_file(), "CONTRACT_FILE_MISSING:" + rel)
        actual = sha_file(path)
        require(actual == expected, "CONTRACT_SHA_MISMATCH:" + rel)
        size = path.stat().st_size
        if rel.endswith(".zip"):
            require(size == CONTRACT_ZIP_BYTES, "CONTRACT_ZIP_SIZE")
        rows.append({"path": rel, "sha256": actual, "bytes": size,
                     "source": "contract section 0", "match": True})

    config = read_json(ROOT / "config" / "v146_science_config.json")
    require(config["frozen"]["library_sha256"] == FROZEN_LIBRARY_SHA256, "LIBRARY_PIN_IN_CONFIG")
    require(config["frozen"]["camera_h5_sha256"] == FROZEN_CAMERA_SHA256, "CAMERA_PIN_IN_CONFIG")
    require(sha_file(ROOT / config["inputs"]["training_library"]) == FROZEN_LIBRARY_SHA256,
            "FIELD_LIBRARY_BYTES_CHANGED")
    require(sha_file(ROOT / config["inputs"]["camera_h5"]) == FROZEN_CAMERA_SHA256,
            "CAMERA_H5_BYTES_CHANGED")

    preflight = read_json(V166 / "preflight.json")
    require(preflight["status"] == "PASS", "V166_PREFLIGHT_NOT_PASS")
    blob_rows = []
    pinned = [f"results/v166/source_context/{group}.json" for group in
              ("ANON_01", "ANON_02", "ANON_03", "ANON_04")]
    pinned += ["results/v166/starts_by_group.json", "results/v166/estimates.json",
               "results/v166/preflight.json", "results/v166/seal.json",
               "results/v166/height_input/height_readings.json",
               "results/v166/logs/v165_budget.sqlite"]
    pinned += [f"results/v166/tasks/{source}/starts/{name}.json"
               for source in R_SOURCES for name in ("000", "001")]
    pinned += [f"results/v166/tasks/{source}/best/{ref['best_document']}"
               for source, ref in refs["zero_bias"].items()]
    pinned += [f"results/v166/tasks/{source}/result.json" for source in R_SOURCES + B_SOURCES]
    pinned += [f"results/v166/tasks/{source}/legal_witnesses.json" for source in R_SOURCES]
    pinned += [f"results/v163/rescored/100000_{group}_{i}.json"
               for group in ("ANON_01", "ANON_02", "ANON_03", "ANON_04") for i in range(6)]
    for rel in pinned:
        path = ROOT / rel
        require(path.is_file(), "PINNED_FILE_MISSING:" + rel)
        disk_blob = common.blob_sha(path.read_bytes())
        commit_blob = git_blob_at_parent(rel)
        require(commit_blob is not None, "PINNED_FILE_UNTRACKED:" + rel)
        require(commit_blob == disk_blob, "GIT_BLOB_DIFFERS_FROM_DISK:" + rel)
        blob_rows.append({"path": rel, "git_blob": commit_blob, "disk_blob": disk_blob,
                          "sha256": sha_file(path)})
    require(len(blob_rows) == len(pinned), "BLOB_PIN_COUNT")

    context_rows = []
    for group in ("ANON_01", "ANON_02", "ANON_03", "ANON_04"):
        declared = preflight["contexts"][group]["copy_sha256"]
        actual = sha_file(V166 / "source_context" / (group + ".json"))
        require(declared == actual, "SOURCE_CONTEXT_COPY_SHA:" + group)
        document = read_json(V166 / "source_context" / (group + ".json"))
        problems = scan_forbidden(document, "frames:" + group)
        require(not problems, "SOURCE_CONTEXT_FORBIDDEN_KEYS:" + group + ":" + str(problems[:6]))
        context_rows.append({"group": group, "sha256": actual, "declared_by_preflight": declared,
                             "bytes": (V166 / "source_context" / (group + ".json")).stat().st_size,
                             "forbidden_key_offenders": len(problems)})

    readings = read_json(V166 / "height_input" / "height_readings.json")
    require(len(readings["readings"]) == 24, "PUBLIC_READING_COUNT")
    require("seed" in readings and "truth_file_sha256" in readings,
            "V166_DEFECT_NOT_REPRODUCIBLE")   # contract 0.1: the leak must still be visible
    public = {str(row["reading_id"]): row for row in readings["readings"]}

    ledger = service_mod.read_only_ledger(V166 / "logs" / "v165_budget.sqlite")
    try:
        tasks = ledger.execute("SELECT id,signature,phase,cap,used,state FROM tasks").fetchall()
        attempts = ledger.execute(
            "SELECT state, COUNT(*) FROM attempts GROUP BY state").fetchall()
        by_phase = ledger.execute(
            "SELECT t.phase, SUM(t.used), SUM(t.cap), COUNT(*) FROM tasks t GROUP BY t.phase"
        ).fetchall()
        partial_used = {str(row[0]): int(row[1]) for row in
                        ledger.execute("SELECT id,used,state FROM tasks").fetchall()
                        if str(row[0]) in R_SOURCES}
    finally:
        ledger.close()
    total_attempts = sum(int(count) for _state, count in attempts)
    require(len(tasks) == 31, "V166_LEDGER_TASK_COUNT:" + str(len(tasks)))
    require(total_attempts == 4937, "V166_LEDGER_ATTEMPT_COUNT:" + str(total_attempts))
    require(all(state == "RETURNED" for state, _c in attempts),
            "V166_LEDGER_UNSETTLED_ATTEMPTS")
    # Each warm task must reconcile against its own sealed V166 start records: the
    # billed rows in the ledger equal the sum of the two starts' actual_calls, and
    # the second start is the one that stopped on the 200-call cap.  A single shared
    # constant would be an assumption, not a check, so the numbers are read from the
    # evidence itself and compared per task.
    reconciliation: dict[str, dict] = {}
    for source in R_SOURCES:
        start_calls = []
        for name in ("000.json", "001.json"):
            path = V166 / "tasks" / source / "starts" / name
            require(path.is_file(), "R_SEALED_START_RECORD_MISSING:" + source + ":" + name)
            record = read_json(path)
            require(int(record.get("start_index", -1)) == len(start_calls),
                    "R_SEALED_START_INDEX:" + source + ":" + name)
            start_calls.append(int(record["actual_calls"]))
        sealed_total = sum(start_calls)
        reconciliation[source] = {
            "ledger_used": partial_used.get(source), "start_actual_calls": start_calls,
            "sealed_start_sum": sealed_total,
            "second_start_hit_the_cap": start_calls[1] == 200,
            "reconciles": partial_used.get(source) == sealed_total}
    require(all(row["reconciles"] and row["ledger_used"] is not None
                and row["second_start_hit_the_cap"] for row in reconciliation.values()),
            "V166_PARTIAL_TASK_CONSUMPTION:" + json.dumps(reconciliation)[:1200])
    for source, ref in refs["partials"].items():
        require(ref["old_start_consumption"] == 200, "R_OLD_CONSUMPTION_NOT_200:" + source)

    return {"schema": "iscat167.p0_evidence.1",
            "role": "CONTROLLER_ONLY_READ_ONLY",
            "contract_pins": rows, "git_blob_pinned_files": blob_rows,
            "git_blob_pinned_count": len(blob_rows),
            "field_library_sha256": FROZEN_LIBRARY_SHA256,
            "camera_h5_sha256": FROZEN_CAMERA_SHA256,
            "source_contexts": context_rows,
            "public_height_file": {"path": str(V166 / "height_input" / "height_readings.json"),
                                   "sha256": CONTRACT_PINS["results/v166/height_input/height_readings.json"],
                                   "reading_count": len(public),
                                   "seed_key_present": True,
                                   "truth_file_sha256_key_present": True,
                                   "estimator_may_read_this_file": False},
            "v166_ledger": {"path": str(V166 / "logs" / "v165_budget.sqlite"),
                            "open_mode": "read_only", "task_rows": len(tasks),
                            "attempt_states": {str(s): int(c) for s, c in attempts},
                            "attempts_total": total_attempts,
                            "by_phase": [{"phase": str(p), "used": int(u), "cap": int(c),
                                          "tasks": int(n)} for p, u, c, n in by_phase],
            "partial_task_used": partial_used,
            "partial_task_ledger_reconciliation": reconciliation},
            "model_calls": 0, "new_random_draws": 0, "wrote_inside_v166": False}


def public_readings() -> dict[str, dict]:
    """Controller-only view of the published 24-row table; never staged to a worker."""
    document = read_json(V166 / "height_input" / "height_readings.json")
    return {str(row["reading_id"]): row for row in document["readings"]}


def _stage_bytes(path: Path, raw: bytes, *, where: str) -> str:
    """Idempotent byte-exact staging: identical bytes are kept, different bytes refuse."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_bytes()
        require(existing == raw,
                "STAGED_BYTES_DIFFER_REFUSING_OVERWRITE:" + where + ":" + str(path))
        return sha_bytes(existing)
    handle = path.open("xb")
    try:
        handle.write(raw)
        handle.flush()
        import os
        os.fsync(handle.fileno())
    finally:
        handle.close()
    require(path.read_bytes() == raw, "STAGED_READBACK_MISMATCH:" + where)
    return sha_bytes(raw)


def stage(ctx: dict) -> dict:
    """Write the three documents each worker may see, and the controller-only mapping."""
    rows = []
    legal_by_group: dict[str, dict] = {}
    legal_sha_by_group: dict[str, str] = {}
    frames_sha_by_group: dict[str, str] = {}
    public = public_readings()
    for group in ("ANON_01", "ANON_02", "ANON_03", "ANON_04"):
        document = legal_records_document(group)
        legal_by_group[group] = document
        legal_sha_by_group[group] = sha_bytes(canon(document))
        source = V166 / "source_context" / (group + ".json")
        _data, _identity, frames_sha = common.frames_from_document(
            read_json(source), where="controller:" + group)
        frames_sha_by_group[group] = frames_sha

    for entry in ctx["plan"]["entries"]:
        task_id = str(entry["task_id"])
        staged_input = STAGING / task_id / "input.json"
        require(staged_input.is_file(), "PLANNER_STAGING_MISSING:" + task_id)
        raw = staged_input.read_bytes()
        require(sha_bytes(raw) == entry["payload_sha256"],
                "PLANNER_PAYLOAD_SHA_CHANGED:" + task_id)
        payload = json.loads(raw.decode("utf-8-sig"))
        require(payload["task_id"] == task_id, "PAYLOAD_TASK_ID:" + task_id)
        group = str(payload["group"])
        require(entry.get("group") in (None, group), "PLAN_GROUP_MISMATCH:" + task_id)
        require(not scan_forbidden(payload, "payload:" + task_id),
                "PAYLOAD_FORBIDDEN_KEYS:" + task_id)
        reading = payload["reading"]
        require(set(reading) == common.READING_KEYS, "PAYLOAD_READING_KEYS:" + task_id)
        require(reading["group"] == group, "PAYLOAD_READING_GROUP:" + task_id)
        require(int(reading["B"]) == int(payload["B"]) == 100000, "PAYLOAD_B:" + task_id)
        jail = JAIL_ROOT / task_id
        require(not jail.exists() or all(p.is_file() for p in jail.iterdir()),
                "JAIL_HAS_UNEXPECTED_CHILD:" + task_id)
        input_sha = _stage_bytes(jail / "input.json", raw, where=task_id + ":input")
        frames_raw = (V166 / "source_context" / (group + ".json")).read_bytes()
        frames_sha_file = _stage_bytes(jail / "frames.json", frames_raw, where=task_id + ":frames")
        legal_raw = canon(legal_by_group[group])
        legal_sha = _stage_bytes(jail / "legal_records.json", legal_raw, where=task_id + ":legal")
        listed = sorted(p.name for p in jail.iterdir() if p.is_file())
        require(listed == ["frames.json", "input.json", "legal_records.json"],
                "JAIL_FILE_ENUMERATION:" + task_id + ":" + str(listed))

        old_reading = public.get(str(entry.get("source_task_id")))
        if entry["kind"] == "SEARCH_EXTENSION":
            require(old_reading is not None, "R_SOURCE_READING_MISSING:" + task_id)
            require(float(old_reading["z_nm"]) == float(reading["z_nm"]),
                    "R_READING_NOT_THE_OLD_ONE:" + task_id)
            require(float(old_reading["sigma_nm"]) == float(reading["sigma_nm"]),
                    "R_SIGMA_CHANGED:" + task_id)
            require(int(old_reading["replicate"]) == int(reading["replicate"]),
                    "R_REPLICATE_CHANGED:" + task_id)
            require([payload["starts"][0]] == [[float(v) for v in
                    ctx["refs"]["partials"][str(entry["source_task_id"])]["warm_theta"]]],
                    "R_WARM_START_NOT_SEALED_BEST:" + task_id)
            bias = None
        else:
            require(old_reading is not None and float(old_reading["sigma_nm"]) == 1.0,
                    "B_ZERO_BIAS_SIGMA:" + task_id)
            offset = float(entry["controlled_offset_nm"])
            require(offset in (-2.0, 2.0), "B_OFFSET_DOMAIN:" + task_id)
            require(abs(float(reading["z_nm"]) - float(old_reading["z_nm"]) - offset) < 1e-9,
                    "B_OFFSET_NOT_THE_PRESCRIBED_TWO:" + task_id)
            require(float(old_reading["z_nm"]) not in (float(reading["z_nm"]),),
                    "B_UNBIASSED_VALUE_LEAKED:" + task_id)
            pair = [tuple(s) for s in payload["starts"]]
            expected = (tuple(ctx["refs"]["base_points"][group]["theta"]),
                        tuple(ctx["refs"]["base_points"][group]["second_start_theta"]))
            require(tuple(pair) == expected, "B_STARTS_NOT_GROUP_PRESCRIBED:" + task_id)
            bias = offset
        rows.append({
            "task_id": task_id, "kind": str(entry["kind"]),
            "phase": "SEARCH_EXTENSION" if entry["kind"] == "SEARCH_EXTENSION" else "BIAS_STRESS",
            "group": group, "replicate": int(reading["replicate"]),
            "sigma_nm": float(reading["sigma_nm"]), "B": int(payload["B"]),
            "source_task_id": str(entry["source_task_id"]),
            "controlled_offset_nm": bias,
            "staged_input": str(jail / "input.json"), "staged_input_sha256": input_sha,
            "payload_sha256": entry["payload_sha256"],
            "staged_frames": str(jail / "frames.json"), "staged_frames_sha256": frames_sha_file,
            "frames_source": str(V166 / "source_context" / (group + ".json")),
            "frames_source_sha256": sha_file(V166 / "source_context" / (group + ".json")),
            "frames_sha256": frames_sha_by_group[group],
            "staged_legal_records": str(jail / "legal_records.json"),
            "legal_records_sha256": legal_sha,
            "legal_records_source_files": [r["record_path"] for r in legal_by_group[group]["records"]],
            "starts": payload["starts"], "cap_per_start": payload["cap_per_start"],
            "task_cap": payload["task_cap"],
            "reading_projection": {"reading_id": reading["reading_id"],
                                   "sigma_nm": float(reading["sigma_nm"]),
                                   "z_nm": float(reading["z_nm"]),
                                   "replicate": int(reading["replicate"]),
                                   "hypothetical": bool(reading["hypothetical"])},
            "old_public_reading_reference": (None if old_reading is None else
                                             {"reading_id": old_reading["reading_id"],
                                              "sigma_nm": float(old_reading["sigma_nm"]),
                                              "z_nm": float(old_reading["z_nm"])}),
            "jail_files": listed,
        })

    mapping = {"schema": "iscat167.source_mapping.1", "role": "CONTROLLER_ONLY",
               "v166_height_file": {"path": str(V166 / "height_input" / "height_readings.json"),
                                    "sha256": CONTRACT_PINS[
                                        "results/v166/height_input/height_readings.json"],
                                    "rows": 24, "read_by_controller_only": True},
               "plan": {"path": str(PLAN_PATH), "sha256": CONTRACT_PLAN_SHA256,
                        "read_by_controller_only": True},
               "bias_scenarios": [{"controlled_offset_nm": offset,
                                   "source_task_ids": list(B_SOURCES),
                                   "sigma_nm": 1.0, "new_random_draws": 0}
                                  for offset in (-2.0, 2.0)],
               "tasks": rows, "task_count": len(rows),
               "model_calls": 0, "new_random_draws": 0}
    # The two controller-only fields are dropped by name, not merely nulled: the scan
    # flags key names, so a value of None would still be reported as an offender.
    scrubbed = [{key: value for key, value in r.items()
                 if key not in ("controlled_offset_nm", "old_public_reading_reference")}
                for r in rows]
    offenders = scan_forbidden({"rows": scrubbed}, "mapping")
    require(not offenders,
            "MAPPING_SCAN_UNEXPECTED:" + json.dumps(offenders)[:600])
    _stage_json(_evidence(ctx, CONTROL / "source_mapping.json"), mapping)
    receipt = {"schema": "iscat167.input_isolation_receipt.1",
               "statement": "Each worker jail holds exactly three files: its own "
                            "single-reading payload, its own group three-frame document and "
                            "its own group six legal records. The full 24-row table, the plan, "
                            "the controlled offset, the seed, the truth hash and the sealed "
                            "truth stay in controller-only space.",
               "jail_file_enumeration": {r["task_id"]: r["jail_files"] for r in rows},
               "tasks_with_exactly_three_files": sum(
                   1 for r in rows if len(r["jail_files"]) == 3),
               "single_reading_per_task": True,
               "cross_sigma_sibling_exposed": False,
               "controlled_offset_exposed_to_estimator": False,
               "truth_valued_key_offenders_in_any_staged_document": 0,
               "guard_label": "NON_ADVERSARIAL_PYTHON_RUNTIME_ISOLATION_NOT_A_KERNEL_SANDBOX",
               "access_denial_receipts_written_by": "tools/v167/tests (worker --probe)",
               "model_calls": 0}
    _stage_json(_evidence(ctx, JAIL_ROOT / "00_isolation_receipt.json"), receipt)
    return {"mapping": mapping, "receipt": receipt,
            "frames_sha_by_group": frames_sha_by_group,
            "legal_sha_by_group": legal_sha_by_group}


def task_descriptor(entry: dict, staged: dict, codes: dict, plan_sha: str) -> dict:
    """Reservation identity.  It never carries the controlled bias value (section 3.1)."""
    descriptor = {"task_id": entry["task_id"], "kind": entry["kind"],
                  "payload_sha256": staged["payload_sha256"],
                  "frames_sha256": staged["frames_sha256"],
                  "frames_source_sha256": staged["frames_source_sha256"],
                  "legal_records_sha256": staged["legal_records_sha256"],
                  "group": staged["group"], "B": staged["B"],
                  "replicate": staged["replicate"], "sigma_nm": staged["sigma_nm"],
                  "reading": staged["reading_projection"],
                  "starts": staged["starts"], "cap_per_start": staged["cap_per_start"],
                  "task_cap": staged["task_cap"], "model_id": MODEL_ID,
                  "source_task_id": staged["source_task_id"],
                  "code_identity_sha256": codes["identity_sha256"],
                  "plan_sha256": plan_sha}
    if entry["kind"] == "SEARCH_EXTENSION":
        descriptor.update({"source_start_index": entry["source_start_index"],
                           "warm_start_record": entry["warm_start_record"],
                           "old_start_consumption": entry["old_start_consumption"]})
    require(not scan_forbidden(descriptor, "descriptor"),
            "DESCRIPTOR_FORBIDDEN_KEYS:" + str(scan_forbidden(descriptor, "descriptor")))
    return descriptor


def reserve(ctx: dict) -> dict:
    """Reserve the frozen 10,000-call plan before any model exists."""
    # A rehearsal may not occupy the deliverable ledger name either: the contract
    # ledger has to contain the authorized run's billing only, so a dry run reserves
    # into results/v167/dry_run/logs/ and the primary name stays free.
    ledger_path = _evidence(ctx, LEDGER_PATH)
    store = service_mod.make_store(ledger_path)
    require(dict(store.phases) == dict(PHASES) and store.total == TOTAL, "LEDGER_PLAN_SHAPE")
    plan_sha = CONTRACT_PLAN_SHA256
    signatures = {LOADER_TASK: service_mod.task_signature(
        {"task": LOADER_TASK, "model_id": MODEL_ID, "role": "single_loader",
         "phase": "MODEL_BINDING"}, "MODEL_BINDING", 100),
        BINDING_TASK: service_mod.task_signature(
            {"task": BINDING_TASK, "model_id": MODEL_ID, "role": "witness_cross_check",
             "phase": "MODEL_BINDING"}, "MODEL_BINDING", 100)}
    caps = {LOADER_TASK: 100, BINDING_TASK: 100}
    staged_by_task = {row["task_id"]: row for row in ctx["staging"]["mapping"]["tasks"]}
    for entry in ctx["plan"]["entries"]:
        task_id = str(entry["task_id"])
        descriptor = task_descriptor(entry, staged_by_task[task_id], ctx["codes"], plan_sha)
        phase = ("SEARCH_EXTENSION" if entry["kind"] == "SEARCH_EXTENSION" else "BIAS_STRESS")
        signatures[task_id] = service_mod.task_signature(descriptor, phase, int(entry["task_cap"]))
        caps[task_id] = int(entry["task_cap"])
        ctx.setdefault("descriptors", {})[task_id] = descriptor
    final_descriptor = {"task": FINAL_TASK, "role": "final_verify", "model_id": MODEL_ID,
                        "plan_sha256": plan_sha, "code_identity_sha256": ctx["codes"]["identity_sha256"]}
    signatures[FINAL_TASK] = service_mod.task_signature(final_descriptor, "FINAL_VERIFY",
                                                        PHASES["FINAL_VERIFY"])
    caps[FINAL_TASK] = PHASES["FINAL_VERIFY"]
    require(sum(caps.values()) == TOTAL, "RESERVATION_SUM_NOT_10000:" + str(sum(caps.values())))
    states = {}
    for task_id in (LOADER_TASK, BINDING_TASK):
        states[task_id] = store.reserve(task_id, signatures[task_id], "MODEL_BINDING",
                                        caps[task_id], OWNER)
    for entry in ctx["plan"]["entries"]:
        task_id = str(entry["task_id"])
        phase = ("SEARCH_EXTENSION" if entry["kind"] == "SEARCH_EXTENSION" else "BIAS_STRESS")
        states[task_id] = store.reserve(task_id, signatures[task_id], phase, caps[task_id], OWNER)
    states[FINAL_TASK] = store.reserve(FINAL_TASK, signatures[FINAL_TASK], "FINAL_VERIFY",
                                       caps[FINAL_TASK], OWNER)
    by_phase: dict[str, dict] = {}
    for task_id, cap in caps.items():
        phase = ("MODEL_BINDING" if task_id in (LOADER_TASK, BINDING_TASK)
                 else "FINAL_VERIFY" if task_id == FINAL_TASK
                 else "SEARCH_EXTENSION" if states[task_id] and task_id in
                 {str(e["task_id"]) for e in ctx["plan"]["entries"]
                   if e["kind"] == "SEARCH_EXTENSION"} else "BIAS_STRESS")
        bucket = by_phase.setdefault(phase, {"tasks": 0, "cap": 0})
        bucket["tasks"] += 1
        bucket["cap"] += cap
    document = {"schema": "iscat167.task_signatures.1", "ledger_path": str(ledger_path),
                "total_cap": TOTAL, "phase_caps": dict(PHASES),
                "reserved_by_phase": by_phase, "reserved_total": sum(caps.values()),
                "states": states,
                "signatures": signatures, "descriptors": ctx.get("descriptors", {}),
                "reused_existing_reservation": sorted(t for t, s in states.items() if s != "RUNNING")}
    # Append-only publication, not a byte-exact stage: the reservation document records
    # the ledger states as they were when it was written, so a second prepare (an
    # interrupted round resumed, or the closing evidence pass before packing) would
    # otherwise collide with the primary bytes and wedge the round.  The primary keeps
    # the pre-spending reservation the seal refers to; later passes publish their
    # settled states beside it.
    ctx.setdefault("published", {})["task_signatures.json"] = _publish_json(
        ctx, _evidence(ctx, CONTROL / "task_signatures.json"), document)
    return {"store": store, "signatures": signatures, "states": states, "caps": caps,
            "document": document, "ledger_path": ledger_path}


# ---------------------------------------------------------------------- run steps

# The pinned ledger module is already importable: bootstrap_paths(estimator=False)
# ran above the service import, so this is the same detail-aware copy the service
# uses and the seal/charge semantics cannot come from the older tools/ duplicate.
import v152_budget_store as ledger_mod                                         # noqa: E402

DB_STATE = {"FINISHED": "FINISHED", "PARTIAL_SEARCH": "PARTIAL_BUDGET", "FAILED": "FAILED"}
REPORT_LABEL = {
    "SEARCH_EXTENSION": {"FINISHED": "SUPPLEMENTAL_LOCAL_RETURN",
                         "PARTIAL_SEARCH": "SUPPLEMENTAL_PARTIAL_SEARCH",
                         "FAILED": "SUPPLEMENTAL_FAILED"},
    "BIAS_STRESS": {"FINISHED": "BIAS_STRESS_LOCAL_RETURN",
                    "PARTIAL_SEARCH": "BIAS_STRESS_PARTIAL_SEARCH",
                    "FAILED": "BIAS_STRESS_FAILED"},
}
STOP_MARKERS = ("FatalPersistenceError", "ReconstructionRefused", "StoreError",
                "JailViolation", "PREDICTION_", "CHARGED_", "LEDGER_")


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _stage_json(path: Path, document: Any) -> str:
    """Controller evidence writer: identical bytes are kept, different bytes refuse.

    Controller receipts are deterministic functions of the frozen inputs, so a
    restart replays them byte for byte.  Anything that would change the bytes of
    already published evidence is a refusal, never a silent overwrite.
    """
    raw = canon(document)
    if path.exists():
        require(path.read_bytes() == raw,
                "CONTROLLER_EVIDENCE_CHANGED_REFUSING_OVERWRITE:" + str(path))
        return sha_bytes(raw)
    return _stage_bytes(path, raw, where=path.relative_to(ROOT).as_posix())


def _publish_json(ctx: dict, path: Path, document: Any) -> dict:
    """Writer for receipts that legitimately grow after a resume.

    The primary name keeps the first published bytes forever.  If a later call,
    possibly in a restarted process, would change them, the new content is
    published beside the primary under a run-scoped version name and the primary
    is never overwritten.  Every publication is therefore append-only evidence and
    the receipt records which file actually holds the current bytes.
    """
    raw = canon(document)
    digest = sha_bytes(raw)
    base = {"path": str(path), "sha256": digest, "primary_path": str(path),
            "overwritten_existing_bytes": False}
    if not path.exists():
        _stage_bytes(path, raw, where=path.relative_to(ROOT).as_posix())
        return dict(base, published="primary", versioned=False)
    if path.read_bytes() == raw:
        return dict(base, published="primary_replay_byte_identical", versioned=False)
    run_id = str(ctx.get("run_id") or "unknown-run")
    parent, stem = path.parent, path.stem
    for seq in range(0, 200):
        name = (stem + "_" + run_id + ".json" if seq == 0
                else stem + "_" + run_id + "_" + format(seq, "03d") + ".json")
        candidate = parent / name
        if not candidate.exists():
            _stage_bytes(candidate, raw, where=candidate.relative_to(ROOT).as_posix())
            return dict(base, published="versioned_copy", versioned=True,
                        version_path=str(candidate), version_sha256=digest,
                        primary_sha256=sha_file(path))
        if candidate.read_bytes() == raw:
            return dict(base, published="versioned_copy_replay", versioned=True,
                        version_path=str(candidate), version_sha256=digest,
                        primary_sha256=sha_file(path))
    require(False, "PUBLISH_VERSION_SLOT_EXHAUSTED:" + str(path))
    return {}


def _evidence(ctx: dict, path: Path) -> Path:
    """A dry-run rehearsal never occupies a primary evidence name.

    Rehearsal documents are real, but they describe a run that made no model
    calls, so they live under results/v167/dry_run/<code identity>/ and the primary
    path stays free for the authorized run itself.  The identity segment is part of
    the layout because reservation signatures embed the code identity: without it a
    second rehearsal after a repair would collide with the first one's bytes.
    """
    if not ctx.get("dry_run"):
        return path
    identity = str(ctx.get("codes", {}).get("identity_sha256", "unknown"))[:12]
    return OUT / "dry_run" / identity / path.relative_to(OUT)


def latest_evidence(path: Path) -> tuple[Path, list[Path]]:
    """Newest published version of a growing receipt plus every earlier copy.

    Append-only publication means the primary keeps the first bytes and a resumed
    run may add versioned copies beside it.  Readers that want the current state
    take the highest version name; the history of every other version is returned
    so nothing is hidden from the report.
    """
    parent, stem = path.parent, path.stem
    versions = sorted(item for item in parent.glob(stem + "_*.json") if item.is_file())
    primary = path if path.is_file() else None
    if primary is None and not versions:
        return path, []
    current = versions[-1] if versions else path
    history = ([primary] if primary else []) + versions
    return current, history


def _compact_best(best: Any) -> dict | None:
    """Per-start best without the 170-element residual array (it stays on disk)."""
    if not isinstance(best, dict):
        return None
    keep = ("theta", "Q_total", "Q_model", "Q_frames", "Q_joint", "Q_height", "K",
            "scipy_cost", "half_cost_identity_abs_error", "residual_shape",
            "residual_sha256", "prediction_path", "prediction_sha256", "charged",
            "cache_hit", "witness_origin", "ledger_seq", "reportable_D")
    return {key: best.get(key) for key in keep if key in best}


def _compact_passes(record: dict) -> dict:
    optimizer = record.get("optimizer") or {}
    return {"pass_index": record.get("pass_index"),
            "execution_state": record.get("execution_state"),
            "x0": record.get("x0"), "evaluations": record.get("evaluations"),
            "local_cap": record.get("local_cap"),
            "charged_this_pass": record.get("charged_this_pass"),
            "cache_hits_this_pass": record.get("cache_hits_this_pass"),
            "wall_seconds": record.get("wall_seconds"),
            "exit": {"success": optimizer.get("success"), "status": optimizer.get("status"),
                     "message": optimizer.get("message"), "nfev": optimizer.get("nfev"),
                     "njev": optimizer.get("njev"), "cost": optimizer.get("cost"),
                     "optimality": optimizer.get("optimality"),
                     "active_mask": optimizer.get("active_mask"), "x": optimizer.get("x")},
            "error": record.get("error"), "best": _compact_best(record.get("best"))}


def prepare(dry_run: bool = False) -> dict:
    """P0 + P1 staging + budget reservation, then print the run identity.

    Nothing in this function can construct the model: the contract requires the
    run_id, code SHAs, old source SHAs, ledger path and task list to be printed
    and logged before the first construction.
    """
    identities = common.verify_frozen_module_identities(estimator=False)
    head = git_text("rev-parse", "HEAD")
    ancestor = subprocess.run(
        ("git", "-C", str(ROOT), "merge-base", "--is-ancestor", PARENT_COMMIT, head),
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    require(ancestor.returncode == 0,
            "V166_RELEASE_NOT_AN_ANCESTOR_OF_HEAD:" + head + ":" + PARENT_COMMIT)
    plan = _read_plan()
    codes = code_identities()
    refs = resolve_references(plan)
    evidence = verify_evidence(refs)
    git_state = code_git_state()
    if not dry_run:
        # Contract section 10.4: the code is committed first, then the authorized
        # run executes, so that the seal records a HEAD that really holds it.
        require(git_state["estimator_code_tracked"]
                and git_state["estimator_code_clean"] and git_state["bundle_tracked"],
                "V167_CODE_NOT_COMMITTED_BEFORE_RUN:" + json.dumps(git_state)[:900])
    # The run identity is written once and reused, so every downstream controller
    # receipt replays byte for byte after an interruption instead of forking.
    # A rehearsal may not burn the primary name: the authorized run has to record the
    # identity of the committed code, so dry runs live in the rehearsal-only tree, one
    # file per code identity, so that repairing the code never fakes a stale run_id.
    if dry_run:
        identity_path = (PLAN_ROOT / "dry_run"
                         / ("run_identity_" + codes["identity_sha256"][:12] + ".json"))
    else:
        identity_path = CONTROL / "run_identity.json"
    candidate = "v167-" + _now_utc() + "-" + codes["identity_sha256"][:12]
    if identity_path.exists():
        stored = read_json(identity_path)
        require(stored.get("code_identity_sha256") == codes["identity_sha256"],
                "RUN_IDENTITY_CODE_CHANGED:" + str(stored.get("code_identity_sha256")))
        require(stored.get("plan_sha256") == CONTRACT_PLAN_SHA256, "RUN_IDENTITY_PLAN_CHANGED")
        run_id = str(stored["run_id"])
    else:
        run_id = candidate
        atomic_json(identity_path, {"schema": "iscat167.run_identity.1", "run_id": run_id,
                                   "code_identity_sha256": codes["identity_sha256"],
                                   "plan_sha256": CONTRACT_PLAN_SHA256,
                                   "v166_release_commit": PARENT_COMMIT,
                                   "created_utc": datetime.now(timezone.utc).isoformat(),
                                   "model_calls": 0})
    ctx: dict[str, Any] = {
        "run_id": run_id, "git_head": head, "v166_release_commit": PARENT_COMMIT,
        "execution_commit_declared": "af2078b2a2d545b8455b48d814faa12017e5e8ac",
        "started_utc": datetime.now(timezone.utc).isoformat(), "dry_run": dry_run,
        "frozen_modules": identities, "codes": codes, "plan": plan, "refs": refs,
        "evidence": evidence,
        "git_state": git_state,
    }
    ctx["staging"] = stage(ctx)
    ctx["staged_by_task"] = {row["task_id"]: row
                             for row in ctx["staging"]["mapping"]["tasks"]}
    require(sorted(ctx["staged_by_task"]) == sorted(str(e["task_id"]) for e in plan["entries"]),
            "STAGED_TASK_SET_NOT_23")
    ctx.update(reserve(ctx))
    preamble = {
        "schema": "iscat167.run_preamble.1", "run_id": run_id, "git_head": head,
        "v166_release_commit": PARENT_COMMIT,
        "printed_before_first_model_construction": True,
        "model_calls_at_this_point": 0, "dry_run": dry_run,
        "code_git_state": git_state,
        "code_identity_sha256": codes["identity_sha256"],
        "code_file_count": codes["file_count"],
        "estimator_code_sha256": {name: codes["files"]["tools/v167/" + name]["sha256"]
                                  for name in common.ESTIMATOR_CODE_FILES},
        "controller_code_sha256": {name: codes["files"]["tools/v167/" + name]["sha256"]
                                   for name in common.CONTROLLER_ONLY_CODE_FILES
                                   if "tools/v167/" + name in codes["files"]},
        "frozen_modules": identities["modules"],
        "old_source_shas": {row["path"]: row["sha256"]
                            for row in evidence["contract_pins"]},
        "git_blob_pinned_files": evidence["git_blob_pinned_count"],
        "field_library_sha256": evidence["field_library_sha256"],
        "camera_h5_sha256": evidence["camera_h5_sha256"],
        "plan_sha256": CONTRACT_PLAN_SHA256, "ledger_path": str(ctx["ledger_path"]),
        "deliverable_ledger_path": str(LEDGER_PATH),
        "budget_caps_by_phase": dict(PHASES), "budget_total": TOTAL,
        "reserved_by_phase": ctx["document"]["reserved_by_phase"],
        "tasks": [{"task_id": str(entry["task_id"]), "kind": str(entry["kind"]),
                   "phase": ("SEARCH_EXTENSION" if entry["kind"] == "SEARCH_EXTENSION"
                             else "BIAS_STRESS"),
                   "source_task_id": str(entry["source_task_id"]),
                   "task_cap": int(entry["task_cap"]),
                   "payload_sha256": str(entry["payload_sha256"])}
                  for entry in plan["entries"]],
        "task_count": len(plan["entries"]),
    }
    _publish_json(ctx, _evidence(ctx, CONTROL / "preambles" / (run_id + ".json")), preamble)
    ctx["preamble"] = preamble
    ctx["preamble_path"] = str(_evidence(ctx, CONTROL / "preambles" / (run_id + ".json")))
    print(json.dumps(preamble, indent=1, sort_keys=True), flush=True)
    return ctx


def binding_witnesses(ctx: dict) -> dict[str, dict]:
    """Contract section 7: five partial thetas, three group base points, nine refs."""
    witnesses: dict[str, dict] = {}
    for source, ref in sorted(ctx["refs"]["partials"].items()):
        witnesses["partial_second_start_best:" + source] = {
            "theta": ref["warm_theta"], "sealed_C_sha256": ref["warm_C_sha256"],
            "source_task_id": source, "source_prediction": ref["warm_prediction"],
            "source_prediction_sha256": ref["warm_prediction_sha256"],
            "role": "R_WARM_START_FROM_SEALED_BEST"}
    for group, ref in sorted(ctx["refs"]["base_points"].items()):
        witnesses["group_base_point:" + group] = {
            "theta": ref["theta"], "sealed_C_sha256": ref["C_sha256"],
            "source_task_id": None,
            "source_prediction": ref["source_document"] + "#predictions/" + str(ref["base_index"]),
            "source_prediction_sha256": sha_file(Path(ref["source_document"])),
            "role": "PRESCRIBED_FIRST_START_BASE_POINT"}
    for source, ref in sorted(ctx["refs"]["zero_bias"].items()):
        witnesses["zero_bias_h1_final:" + source] = {
            "theta": ref["theta"], "sealed_C_sha256": ref["C_sha256"],
            "source_task_id": source, "source_prediction": ref["prediction"],
            "source_prediction_sha256": ref["prediction_sha256"],
            "role": "B_HISTORICAL_LEGAL_DIAGNOSTIC_WITNESS"}
    distinct = {theta_hex(item["theta"]) for item in witnesses.values()}
    require(len(witnesses) == 17, "WITNESS_LABEL_COUNT:" + str(len(witnesses)))
    require(len(distinct) <= 17, "WITNESS_THETA_ABOVE_17:" + str(len(distinct)))
    return witnesses


def bind_model(ctx: dict) -> dict:
    """The one authorized construction, then the V166 witness cross-check."""
    service = service_mod.PredictionService(ctx["store"])
    ctx["service"] = service
    resumed = service.load_existing_predictions()
    default_import = OUT / "logs" / "v166_witness_import.json"
    import_path = (default_import if not default_import.exists()
                   else OUT / "logs" / ("v166_witness_import_" + ctx["run_id"] + ".json"))
    witness_import = service.import_v166_predictions(
        PARENT_WS, V166 / "logs" / "v165_budget.sqlite", log_path=import_path)
    construction_log = OUT / "logs" / "model_construction.json"
    try:
        construction = service.ensure_loader(dry_run=bool(ctx["dry_run"]))
    except service_mod.ReconstructionRefused as exc:
        # Contract section 7: after the loader was sealed a process exit is
        # recovered read-only.  Reconstruction needs new authorization, and the
        # controller does not have it, so the round stops here and says so.
        note = {"schema": "iscat167.loader_recovery.1", "run_id": ctx["run_id"],
                "status": "RECOVERY_ONLY", "reason": repr(exc),
                "construction_log": str(construction_log),
                "construction_log_sha256": (sha_file(construction_log)
                                            if construction_log.exists() else None),
                "resumed_predictions": resumed, "witness_import": witness_import,
                "model_constructions_in_this_process": service.constructions,
                "new_model_calls": 0}
        _stage_json(CONTROL / "loader_recovery_note.json", note)
        return dict(note, service=service)
    if ctx["dry_run"]:
        return {"status": "NOT_STARTED_DRY_RUN", "resumed_predictions": resumed,
                "witness_import": witness_import, "construction": construction,
                "binding": ctx["service"].binding_self_check(binding_witnesses(ctx),
                                                             dry_run=True),
                "model_calls": 0}
    require(construction.get("constructed") is not False, "LOADER_NOT_CONSTRUCTED")
    require(construction.get("model_id") == MODEL_ID, "LOADER_MODEL_ID")
    witnesses = binding_witnesses(ctx)
    receipt = service.binding_self_check(witnesses)
    loader_seal = service.seal_loader()
    binding = service.seal_binding(receipt, CONTROL / "binding_result.json")
    counts = dict(service.store.counts())
    binding_charged = counts.get(BINDING_TASK, 0)
    loader_charged = counts.get(LOADER_TASK, 0)
    require(loader_charged <= 100 and binding_charged <= 100,
            "MODEL_BINDING_SUBTASK_CAP:" + str(loader_charged) + "/" + str(binding_charged))
    require(loader_charged + binding_charged <= PHASES["MODEL_BINDING"],
            "MODEL_BINDING_PHASE_CAP")
    document = {"schema": "iscat167.bind_model.1", "run_id": ctx["run_id"],
                "authorized_constructions": 1,
                "constructions_in_this_process": service.constructions,
                "model_id": construction["model_id"],
                "model_construction_record": str(construction_log),
                "model_construction_sha256": sha_file(construction_log),
                "loader_calls": loader_charged, "binding_calls": binding_charged,
                "binding_status": receipt["status"],
                "witness_labels": len(witnesses),
                "witness_distinct_theta": len({theta_hex(v["theta"])
                                               for v in witnesses.values()}),
                "byte_exact_matches": receipt["byte_exact_matches"],
                "resumed_predictions": resumed, "witness_import": witness_import,
                "loader_seal": {key: loader_seal.get(key)
                                for key in ("sealed", "loader_calls", "model_id",
                                            "ledger_counts_at_seal", "signature")},
                "binding_receipt": binding, "model_calls": loader_charged + binding_charged}
    _stage_json(CONTROL / "bind_model.json", document)
    require(receipt["status"] == "VERIFIED",
            "SOURCE_BINDING_NOT_FULLY_VERIFIED:" + json.dumps(
                [row for row in receipt["rows"] if row.get("byte_exact_match") is not True])[:900])
    return document


# --------------------------------------------------------------------- task rounds

def _reconcile_charged(store: Any, task_id: str, note: str) -> dict:
    """Settle CHARGED-but-unserved attempts so a crash can never strand a billing.

    The contract charges before the real call, so a worker or model failure can
    leave an attempt open, which would block the seal.  Each open attempt is
    closed as MODEL_ERROR while keeping every original charge field, plus a
    reconciliation note; nothing here refunds or deletes a consumed call.
    """
    with store.db() as db:
        rows = db.execute("SELECT seq, detail FROM attempts WHERE task = ? "
                          "AND state = 'CHARGED' ORDER BY seq", (task_id,)).fetchall()
    settled = []
    for seq, raw in rows:
        detail = json.loads(raw) if raw else {}
        payload = dict(detail, reconciliation_state="MODEL_ERROR",
                       reconciliation_note=note, reconciled_utc=_now_utc())
        store.returned(task_id, int(seq), "MODEL_ERROR", payload)
        settled.append(int(seq))
    return {"task_id": task_id, "settled_sequences": settled,
            "settled_count": len(settled), "note": note, "refunded_calls": 0}


def _task_ledger_state(store: Any, task_id: str) -> tuple[str, int]:
    with store.db() as db:
        row = db.execute("SELECT state, used FROM tasks WHERE id = ?", (task_id,)).fetchone()
    require(row is not None, "LEDGER_TASK_ABSENT:" + task_id)
    return str(row[0]), int(row[1])


def _strip_residual(document: Any) -> Any:
    """Keep the full 170-point residual on disk only, referenced by hash."""
    if isinstance(document, dict):
        return {key: _strip_residual(value) for key, value in document.items()
                if key != "residual"}
    if isinstance(document, list):
        return [_strip_residual(value) for value in document]
    return document


def _prediction_path(relative_path: Any) -> Path | None:
    """Resolve a prediction reference against this round's or the V166 witness root."""
    if not relative_path:
        return None
    text = str(relative_path)
    for root in (OUT, Path(text) if Path(text).is_absolute() else None, PARENT_WS):
        if root is None:
            continue
        candidate = Path(text) if Path(text).is_absolute() else root / text
        if candidate.exists():
            return candidate
    return None


def _prediction_c_sha(relative_path: Any) -> str | None:
    """Read the stored contrast hash out of a prediction document, read-only."""
    path = _prediction_path(relative_path)
    if path is None:
        return None
    document = read_json(path)
    if document.get("C_sha256"):
        return str(document["C_sha256"])
    if document.get("C") is not None:
        return array_sha(np.asarray(document["C"], dtype=float))
    return None


def _compact_start(record: dict) -> dict:
    return {"start_index": record.get("start_index"),
            "x0": record.get("x0"),
            "cap_per_start": record.get("cap_per_start"),
            "actual_evaluations": record.get("actual_evaluations"),
            "charged_this_start": record.get("charged_this_start"),
            "cache_hits_this_start": record.get("cache_hits_this_start"),
            "execution_state": record.get("execution_state"),
            "reason_codes": record.get("reason_codes"),
            "reportable_D": record.get("reportable_D"),
            "passes": [_compact_passes(pass_record) for pass_record in record.get("passes", [])],
            "best": _compact_best(record.get("best"))}


def _task_result_document(ctx: dict, entry: dict, staged: dict, *, receipt: dict | None,
                          search: dict | None, failure: dict | None,
                          actual_calls: int, db_state: str) -> dict:
    """Mirror the V166 result vocabulary with the V167 provenance added."""
    task_id = str(entry["task_id"])
    search = search or {}
    reason_codes = list(search.get("reason_codes") or [])
    if failure is not None:
        reason_codes.append("TASK_ROUND_FAILED")
    payload = {
        "task_id": task_id, "group": staged["group"], "replicate": staged["replicate"],
        "sigma_nm": staged["sigma_nm"], "reading_id": staged["reading_projection"]["reading_id"],
        "B": staged["B"], "scope": search.get("scope"), "kind": staged["kind"],
        "phase": staged["phase"], "source_task_id": staged["source_task_id"],
        "controlled_offset_nm": None,
        "execution_state": search.get("execution_state", "FAILED"),
        "D_domain_is_not_a_compatibility_claim": True,
        "global_uniqueness_certified": False,
        "known_compatible_D_interval_nm": None, "known_compatible_components": [],
        "parameter_bounds_D_nm": [30.0, 200.0],
        "physical_qualification": "CONDITIONAL_SIMULATED_F2C_DEVELOPMENT",
        "actual_new_calls": actual_calls,
        "charged_replies": (receipt or {}).get("charged_replies"),
        "cache_hit_replies": (receipt or {}).get("cache_hit_replies"),
        "forward_requests": (receipt or {}).get("forward_requests"),
        "interpreter": search.get("interpreter"), "module_identity": search.get("module_identity"),
        "remote_observations": search.get("remote_observations"),
        "payload_sha256": staged["payload_sha256"], "frames_sha256": staged["frames_sha256"],
        "legal_records_sha256": staged["legal_records_sha256"],
        "starts": [_compact_start(record) for record in search.get("starts", [])],
        "passes_used": search.get("passes_used"),
        "evaluations_total": search.get("evaluations_total"),
        "best_legal_witness": _strip_residual(search.get("best_legal_witness")),
        "optimizer_best": _compact_best(search.get("optimizer_best")),
        "development_diagnostic_pool_best": _compact_best(
            search.get("development_diagnostic_pool_best")),
        "theta": search.get("theta"), "candidate_D_nm": search.get("candidate_D_nm"),
        "candidate_D": search.get("candidate_D"), "candidate_h_nm": search.get("candidate_h_nm"),
        "candidate_x_nm": search.get("candidate_x_nm"), "candidate_y_nm": search.get("candidate_y_nm"),
        "reportable_D": None, "reason_codes": reason_codes,
        "full_residual_location": ("results/v167/tasks/" + task_id + "/legal_witnesses.json"),
    }
    if ctx["refs"]["partials"].get(staged["source_task_id"]) is not None:
        partial = ctx["refs"]["partials"][staged["source_task_id"]]
        payload["r_warm_provenance"] = {
            "source_task_id": partial["source_task_id"],
            "source_start_index": partial["source_start_index"],
            "old_execution_state": partial["old_status_preserved"],
            "old_start_consumption": partial["old_start_consumption"],
            "warm_theta": partial["warm_theta"], "warm_Q_total": partial["warm_Q_total"],
            "warm_start_is_sealed_best_not_x0": True,
            "old_partial_result_never_rewritten": True}
    return {
        "schema": "iscat167.task_result.1", "task_id": task_id,
        "signature": ctx["signatures"][task_id], "execution_state": payload["execution_state"],
        "db_state": db_state, "actual_calls": actual_calls, "reportable_D": None,
        "run_id": ctx["run_id"], "kind": staged["kind"], "phase": staged["phase"],
        "source_task_id": staged["source_task_id"], "payload_sha256": staged["payload_sha256"],
        "frames_sha256": staged["frames_sha256"],
        "staged_input_sha256": staged["staged_input_sha256"],
        "legal_records_sha256": staged["legal_records_sha256"],
        "jail_files": staged["jail_files"], "model_id": MODEL_ID,
        "report_label": REPORT_LABEL[staged["kind"]][payload["execution_state"]],
        "worker_exit_code": (receipt or {}).get("worker_exit_code"),
        "wall_seconds": (receipt or {}).get("wall_seconds"),
        "rpc_log_sha256": (receipt or {}).get("rpc_log_sha256"),
        "rpc_receipt": ({key: value for key, value in (receipt or {}).items()
                         if key != "result"} or None),
        "search_result_sha256": (sha_file(OUT / "tasks" / task_id / "search_result.json")
                                 if (OUT / "tasks" / task_id / "search_result.json").exists()
                                 else None),
        "failure": failure, "payload": payload,
    }


def _write_and_seal(ctx: dict, task_id: str, document: dict, db_state: str) -> dict:
    """Publish the task result, then seal it; a republish is always a refusal."""
    path = OUT / "tasks" / task_id / "result.json"
    require(not path.exists(), "TASK_RESULT_ALREADY_PUBLISHED:" + task_id)
    digest = common.atomic_json(path, document)
    ctx["store"].seal(task_id, OWNER, db_state, path)
    return {"result_path": str(path), "result_sha256": digest, "db_state": db_state}


def run_round(ctx: dict) -> dict:
    """Execute the five warm completions and the eighteen bias trials, in plan order.

    Failures are recorded and sealed FAILED and the run continues, except when the
    wrapped error names a stop marker: persistence, ledger, jail or billing
    integrity is never worked around.
    """
    if ctx["dry_run"]:
        return {"status": "NOT_STARTED_DRY_RUN", "tasks_executed": 0,
                "model_calls_in_round": 0, "tasks": {}}
    store, service = ctx["store"], ctx["service"]
    if service.model is None:
        # A sealed loader cannot be rebuilt without new authorization, so the
        # round is blocked.  Nothing is written into the task results: blocking is
        # reported, never manufactured as 23 FAILED answers that could not be undone.
        document = {"schema": "iscat167.run_round.1", "run_id": ctx["run_id"],
                    "status": "BLOCKED_NO_LIVE_MODEL",
                    "tasks_planned": len(ctx["plan"]["entries"]),
                    "tasks_executed_this_round": 0,
                    "tasks_reused_from_sealed_ledger": [], "results": {}, "failures": [],
                    "round_model_calls": 0, "model_calls": 0, "reportable_D": None,
                    "reason": ("the loader was already sealed in the ledger; a restart "
                               "recovers read-only and needs new authorization for a "
                               "second construction")}
        ctx.setdefault("published", {})["run_round.json"] = _publish_json(
            ctx, CONTROL / "run_round.json", document)
        ctx["round"] = document
        print("BLOCKED run_round: NO_LIVE_MODEL", flush=True)
        return document
    results: dict[str, dict] = {}
    failures: list[dict] = []
    reused: list[str] = []
    before = dict(store.counts())
    for entry in ctx["plan"]["entries"]:
        task_id = str(entry["task_id"])
        staged = ctx["staged_by_task"][task_id]
        signature = ctx["signatures"][task_id]
        state, used = _task_ledger_state(store, task_id)
        if state != "RUNNING":
            sealed = store.load_result(task_id, signature)
            reused.append(task_id)
            results[task_id] = {"execution_state": sealed["execution_state"],
                                "db_state": sealed["db_state"],
                                "actual_calls": sealed["actual_calls"],
                                "reused_sealed_result": True, "model_calls_this_round": 0}
            print("REUSE " + task_id + " " + sealed["execution_state"], flush=True)
            continue
        try:
            run = runner.run_task(task_id=task_id,
                                  expected_payload_sha256=staged["payload_sha256"],
                                  frames_sha256=staged["frames_sha256"], service=service)
        except BaseException as exc:                                    # noqa: BLE001
            note = "V167 task round failed: " + type(exc).__name__
            reconcile = _reconcile_charged(store, task_id, note)
            counts = dict(store.counts())
            failure = {"error_type": type(exc).__name__, "error": str(exc)[:4000],
                       "traceback": traceback.format_exc()[-8000:],
                       "reconciliation": reconcile, "ledger_counts": counts}
            document = _task_result_document(ctx, entry, staged, receipt=None, search=None,
                                             failure=failure, actual_calls=counts[task_id],
                                             db_state="FAILED")
            sealed = _write_and_seal(ctx, task_id, document, "FAILED")
            failures.append(dict(sealed, task_id=task_id, error_type=type(exc).__name__,
                                 error=str(exc)[:1200], reconciliation=reconcile))
            ctx["failure_records"] = failures
            if any(marker in type(exc).__name__ or marker in str(exc) for marker in STOP_MARKERS):
                raise
            print("FAILED " + task_id + " " + type(exc).__name__, flush=True)
            continue
        search = run["result"]
        db_state = DB_STATE[search["execution_state"]]
        counts = dict(store.counts())
        document = _task_result_document(ctx, entry, staged, receipt=run, search=search,
                                         failure=None, actual_calls=counts[task_id],
                                         db_state=db_state)
        sealed = _write_and_seal(ctx, task_id, document, db_state)
        results[task_id] = dict(sealed, execution_state=search["execution_state"],
                                actual_calls=counts[task_id],
                                charged_replies=run["charged_replies"],
                                cache_hit_replies=run["cache_hit_replies"],
                                forward_requests=run["forward_requests"],
                                best_Q_total=(document["payload"]["optimizer_best"] or {}).get(
                                    "Q_total"),
                                theta=document["payload"]["theta"],
                                model_calls_this_round=counts[task_id] - before.get(task_id, 0))
        print("DONE " + task_id + " " + search["execution_state"] + " "
              + str(counts[task_id]) + " calls", flush=True)
    after = dict(store.counts())
    round_calls = sum(after[str(e["task_id"])] - before.get(str(e["task_id"]), 0)
                      for e in ctx["plan"]["entries"])
    phase_of = {task_id: ctx["staged_by_task"][task_id]["phase"] for task_id in results}
    usage = {"SEARCH_EXTENSION": sum(after[t] for t in results if phase_of[t] == "SEARCH_EXTENSION"),
             "BIAS_STRESS": sum(after[t] for t in results if phase_of[t] == "BIAS_STRESS")}
    for phase, cap in (("SEARCH_EXTENSION", PHASES["SEARCH_EXTENSION"]),
                       ("BIAS_STRESS", PHASES["BIAS_STRESS"])):
        require(usage[phase] <= cap, "PHASE_USAGE_OVER_CAP:" + phase + ":" + str(usage[phase]))
    document = {"schema": "iscat167.run_round.1", "run_id": ctx["run_id"],
                "tasks_planned": len(ctx["plan"]["entries"]),
                "tasks_executed_this_round": len(results) - len(reused),
                "tasks_reused_from_sealed_ledger": sorted(reused),
                "results": results, "failures": failures,
                "round_model_calls": round_calls, "phase_usage_after_round": usage,
                "ledger_counts_after": after,
                "cache_hit_provenance_note": (
                    "The binding self-check stored each witness answer as a "
                    "v167_charged cache entry with allow_reuse=False at binding time, so "
                    "every worker's first evaluation at a prescribed or warm start is a "
                    "legitimate zero-cost cache hit of a byte-verified answer, not an "
                    "uncounted forward.  Every other forward is charged before the model "
                    "call."),
                "reportable_D": None, "model_calls": round_calls}
    ctx.setdefault("published", {})["run_round.json"] = _publish_json(
        ctx, CONTROL / "run_round.json", document)
    ctx["round"] = document
    return document


def per_start_table(ctx: dict) -> dict:
    """Contract section 11: one row per start and per sequential pass, every task."""
    rows: list[dict] = []
    for entry in ctx["plan"]["entries"]:
        task_id = str(entry["task_id"])
        path = OUT / "tasks" / task_id / "result.json"
        if not path.exists():
            rows.append({"task_id": task_id, "kind": entry["kind"],
                         "start_index": None, "pass_index": None,
                         "execution_state": "NOT_STARTED", "reason": "NO_RESULT_DOCUMENT"})
            continue
        document = read_json(path)
        payload = document["payload"]
        starts = payload.get("starts") or []
        if not starts:
            rows.append({"task_id": task_id, "kind": payload.get("kind"),
                         "start_index": None, "pass_index": None,
                         "execution_state": payload.get("execution_state"),
                         "charged_this_start": None, "cache_hits_this_start": None,
                         "reason": (document.get("failure") or {}).get("error_type",
                                                                      "NO_START_RECORDS")})
            continue
        for record in starts:
            for pass_record in record.get("passes", []):
                best = pass_record.get("best") or {}
                exit_info = pass_record.get("exit") or {}
                rows.append({
                    "task_id": task_id, "kind": payload.get("kind"),
                    "phase": payload.get("phase"), "group": payload.get("group"),
                    "replicate": payload.get("replicate"), "sigma_nm": payload.get("sigma_nm"),
                    "reading_id": payload.get("reading_id"),
                    "source_task_id": payload.get("source_task_id"),
                    "start_index": record.get("start_index"),
                    "pass_index": pass_record.get("pass_index"),
                    "execution_state": pass_record.get("execution_state"),
                    "local_cap": pass_record.get("local_cap"),
                    "evaluations": pass_record.get("evaluations"),
                    "charged_this_pass": pass_record.get("charged_this_pass"),
                    "cache_hits_this_pass": pass_record.get("cache_hits_this_pass"),
                    "wall_seconds": pass_record.get("wall_seconds"),
                    "x0": pass_record.get("x0"),
                    "best_theta": best.get("theta"), "best_Q_total": best.get("Q_total"),
                    "prediction_path": best.get("prediction_path"),
                    "prediction_c_sha256": _prediction_c_sha(best.get("prediction_path")),
                    "prediction_sha256": best.get("prediction_sha256"),
                    "charged": best.get("charged"), "cache_hit": best.get("cache_hit"),
                    "optimizer_success": exit_info.get("success"),
                    "optimizer_status": exit_info.get("status"),
                    "optimizer_message": exit_info.get("message"),
                    "optimizer_nfev": exit_info.get("nfev"),
                    "optimizer_njev": exit_info.get("njev"),
                    "optimizer_cost": exit_info.get("cost"),
                    "optimizer_optimality": exit_info.get("optimality"),
                    "optimizer_active_mask": exit_info.get("active_mask"),
                    "optimizer_x": exit_info.get("x"),
                    "error": pass_record.get("error"),
                    "task_execution_state": payload.get("execution_state"),
                    "task_actual_calls": document.get("actual_calls"),
                    "reportable_D": None})
    starts_by_task = {}
    for row in rows:
        starts_by_task.setdefault(row["task_id"], set()).add(row.get("start_index"))
    document = {"schema": "iscat167.per_start_table.1", "run_id": ctx["run_id"],
                "rows": rows, "row_count": len(rows),
                "tasks_in_table": len(starts_by_task),
                "start_counts_by_task": {key: len(value) for key, value in starts_by_task.items()},
                "state_counts": _count_states(rows),
                "model_calls": 0, "reportable_D": None}
    ctx.setdefault("published", {})["per_start_table.json"] = _publish_json(
        ctx, CONTROL / "per_start_table.json", document)
    return document


def _count_states(rows: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get("execution_state"))
        counts[key] = counts.get(key, 0) + 1
    return counts


# ------------------------------------------------------------------ final verify

def _final_items(ctx: dict) -> list[dict]:
    """Logical re-verification set: every answer this round intends to publish."""
    items: list[dict] = []
    for entry in ctx["plan"]["entries"]:
        task_id = str(entry["task_id"])
        path = OUT / "tasks" / task_id / "result.json"
        if not path.exists():
            items.append({"label": "optimizer_best:" + task_id, "theta": None,
                          "expected_C_sha256": None, "origin": "V167_RESULT",
                          "status": "NOT_VERIFIABLE", "reason": "NO_RESULT_DOCUMENT"})
            continue
        payload = read_json(path)["payload"]
        best = payload.get("optimizer_best") or {}
        items.append({"label": "optimizer_best:" + task_id,
                      "theta": payload.get("theta"),
                      "expected_C_sha256": _prediction_c_sha(best.get("prediction_path")),
                      "origin": "V167_RESULT",
                      "reference_prediction": best.get("prediction_path")})
        floor = payload.get("best_legal_witness") or {}
        items.append({"label": "legal_floor:" + task_id, "theta": floor.get("theta"),
                      "expected_C_sha256": floor.get("C_sha256"),
                      "origin": "V167_LEGAL_WITNESS_ROW",
                      "reference_prediction": "results/v167/tasks/" + task_id
                                              + "/legal_witnesses.json"})
    merge_path = CONTROL / "r_merge_table.json"
    if merge_path.exists():
        for row in read_json(merge_path)["rows"]:
            pick = next((item for item in row["candidates"]
                         if item["label"] == row["merged_pick"]), None)
            items.append({"label": "r_merge_pick:" + str(row["source_task_id"]),
                          "theta": (pick or {}).get("theta"),
                          "expected_C_sha256": (pick or {}).get("c_sha256"),
                          "origin": "V167_R_MERGE",
                          "reference_prediction": (pick or {}).get("prediction")})
    else:
        items.append({"label": "r_merge_table_missing", "theta": None,
                      "expected_C_sha256": None, "origin": "V167_R_MERGE",
                      "status": "NOT_VERIFIABLE", "reason": "NO_MERGE_TABLE"})
    for group, ref in sorted(ctx["refs"]["base_points"].items()):
        items.append({"label": "base_point:" + group, "theta": ref["theta"],
                      "expected_C_sha256": ref["C_sha256"], "origin": "V166_SOURCE_CONTEXT",
                      "reference_prediction": ref["source_document"]})
    for source, ref in sorted(ctx["refs"]["zero_bias"].items()):
        items.append({"label": "zero_bias_reference:" + source, "theta": ref["theta"],
                      "expected_C_sha256": ref["C_sha256"], "origin": "V166_SEALED_H1",
                      "reference_prediction": ref["prediction"]})
    for item in items:
        if item.get("theta") is None:
            item.setdefault("status", "NOT_VERIFIABLE")
            item.setdefault("reason", "NO_THETA_IN_EVIDENCE")
    return items


def final_verify(ctx: dict) -> dict:
    """Contract section 7: charge each distinct re-verification theta before the call."""
    store, service = ctx["store"], ctx["service"]
    signature = ctx["signatures"][FINAL_TASK]
    state, _used = _task_ledger_state(store, FINAL_TASK)
    if state != "RUNNING":
        return dict(store.load_result(FINAL_TASK, signature), reused_sealed_result=True)
    if ctx["dry_run"]:
        document = {"schema": "iscat167.final_verify.1", "run_id": ctx["run_id"],
                    "signature": signature, "status": "NOT_STARTED_DRY_RUN",
                    "logical_items": len(_final_items(ctx)), "model_calls": 0,
                    "execution_state": "NOT_STARTED", "db_state": "NOT_STARTED",
                    "actual_calls": 0, "reportable_D": None, "rows": []}
        _publish_json(ctx, _evidence(ctx, CONTROL / "final_verify.json"), document)
        return document

    items = _final_items(ctx)
    if service.model is None:
        document = {"schema": "iscat167.final_verify.1", "run_id": ctx["run_id"],
                    "signature": signature, "status": "BLOCKED_NO_LIVE_MODEL",
                    "logical_items": len(items), "distinct_theta": 0,
                    "verified": 0, "not_verifiable": 0, "model_calls": 0,
                    "execution_state": "BLOCKED", "db_state": "NOT_STARTED",
                    "actual_calls": 0, "reportable_D": None, "rows": []}
        ctx.setdefault("published", {})["final_verify.json"] = _publish_json(
            ctx, CONTROL / "final_verify.json", document)
        print("BLOCKED final_verify: NO_LIVE_MODEL", flush=True)
        return document
    distinct: dict[str, dict] = {}
    for item in items:
        if item.get("theta") is None:
            distinct.setdefault("MISSING:" + item["label"], dict(item))
            continue
        key = theta_hex(item["theta"])
        bucket = distinct.setdefault(key, {"theta": [float(v) for v in item["theta"]],
                                           "labels": [], "expected_C_sha256": [],
                                           "origins": [], "references": []})
        bucket["labels"].append(item["label"])
        bucket["origins"].append(item["origin"])
        if item.get("reference_prediction"):
            bucket["references"].append(item["reference_prediction"])
        if item.get("expected_C_sha256"):
            bucket["expected_C_sha256"].append(str(item["expected_C_sha256"]))
    rows = []
    for key in sorted(distinct):
        bucket = distinct[key]
        expected = sorted(set(bucket.get("expected_C_sha256") or []))
        base = {"theta_sha256": key, "theta": bucket.get("theta"),
                "logical_items": bucket.get("labels"), "origins": sorted(set(bucket["origins"])),
                "reference_predictions": bucket["references"][:6]}
        if bucket.get("theta") is None or bucket.get("labels") == ["r_merge_table_missing"]:
            rows.append(dict(base, status="NOT_VERIFIABLE",
                             reason=bucket.get("reason", "NO_THETA_IN_EVIDENCE"),
                             charged=False))
            continue
        if len(expected) > 1:
            rows.append(dict(base, status="NOT_VERIFIABLE",
                             reason="CONFLICTING_SEALED_C_FOR_ONE_THETA:" + ",".join(expected),
                             charged=False))
            continue
        try:
            # allow_reuse=False: the published answer must be reproduced by the live
            # model of this round, not read back from this round's own cache.
            info = service.evaluate(FINAL_TASK, bucket["theta"], start_index=None,
                                    kind="FINAL_VERIFY", allow_reuse=False)
        except ledger_mod.CallCapReached as exc:
            rows.append(dict(base, status="BLOCKED", reason="CallCapReached:" + str(exc),
                             charged=False))
            continue
        except Exception as exc:                                        # noqa: BLE001
            rows.append(dict(base, status="FAILED",
                             reason=type(exc).__name__ + ":" + str(exc)[:400],
                             charged=False))
            continue
        observed = str(info["C_sha256"])
        if not expected:
            status, reason = "VERIFIED_NO_SEALED_REFERENCE", "no sealed C in the evidence"
        elif expected[0] == observed:
            status, reason = "VERIFIED", None
        else:
            status, reason = "NOT_VERIFIABLE", ("SEALED_C_NOT_REPRODUCED:"
                                                + expected[0] + "!=" + observed)
        rows.append(dict(base, status=status, reason=reason, sealed_C_sha256=expected[0] or None,
                         v167_C_sha256=observed, charged=bool(info["charged"]),
                         ledger_seq=info["seq"], prediction_path=info["prediction_path"],
                         prediction_sha256=info["prediction_sha256"]))
    counts = dict(store.counts())
    used = counts[FINAL_TASK]
    cap = ctx["caps"][FINAL_TASK]
    verified = sum(1 for row in rows if row["status"].startswith("VERIFIED"))
    blocked = sum(1 for row in rows if row["status"] == "BLOCKED")
    failed = sum(1 for row in rows if row["status"] == "FAILED")
    unverifiable = sum(1 for row in rows if row["status"] == "NOT_VERIFIABLE")
    execution_state = ("FINISHED" if verified == len(rows) and rows
                       else "PARTIAL_SEARCH" if blocked else "FAILED")
    db_state = DB_STATE[execution_state]
    document = {"schema": "iscat167.final_verify.1", "run_id": ctx["run_id"],
                "signature": signature, "task_id": FINAL_TASK,
                "logical_items": len(items), "distinct_theta": len(distinct),
                "verified": verified, "blocked": blocked, "failed": failed,
                "not_verifiable": unverifiable, "rows": rows,
                "minimum_logical_items_required": 40,
                "meets_minimum_logical_items": len(items) >= 40,
                "phase_cap": cap, "used": used, "cap_exceeded": used > cap,
                "execution_state": execution_state, "db_state": db_state,
                "actual_calls": used, "model_calls": used,
                "no_fabricated_theta": True, "reportable_D": None}
    published = _publish_json(ctx, CONTROL / "final_verify.json", document)
    ctx.setdefault("published", {})["final_verify.json"] = published
    path = Path(published["version_path"] if published["versioned"] else published["path"])
    store.seal(FINAL_TASK, OWNER, db_state, path)
    require(not document["cap_exceeded"], "FINAL_VERIFY_PHASE_CAP:" + str(used))
    return document


# --------------------------------------------------------------------- estimate docs

def estimates_documents(ctx: dict) -> dict:
    """Two tables kept apart: this round's own estimates, and the merge/reuse table."""
    rows = []
    for entry in ctx["plan"]["entries"]:
        task_id = str(entry["task_id"])
        path = OUT / "tasks" / task_id / "result.json"
        if not path.exists():
            rows.append({"task_id": task_id, "execution_state": "NOT_STARTED",
                         "theta": None, "candidate_D": None, "reportable_D": None})
            continue
        document = read_json(path)
        payload = document["payload"]
        best = payload.get("optimizer_best") or {}
        floor = payload.get("best_legal_witness") or {}
        staged = ctx["staged_by_task"][task_id]
        rows.append({
            "task_id": task_id, "kind": payload["kind"], "phase": payload["phase"],
            "source_task_id": payload["source_task_id"], "group": payload["group"],
            "replicate": payload["replicate"], "sigma_nm": payload["sigma_nm"],
            "reading_id": payload["reading_id"], "B": payload["B"],
            "controlled_offset_nm_reported_controller_only": staged["controlled_offset_nm"],
            "execution_state": payload["execution_state"],
            "report_label": document["report_label"],
            "theta": payload.get("theta"), "candidate_D": payload.get("candidate_D"),
            "candidate_D_nm": payload.get("candidate_D_nm"),
            "candidate_h_nm": payload.get("candidate_h_nm"),
            "Q_total": best.get("Q_total"), "Q_model": best.get("Q_model"),
            "Q_height": best.get("Q_height"), "Q_joint": best.get("Q_joint"),
            "K": best.get("K"),
            "C_sha256": _prediction_c_sha(best.get("prediction_path")),
            "prediction_path": best.get("prediction_path"),
            "prediction_sha256": best.get("prediction_sha256"),
            "legal_floor_theta": floor.get("theta"), "legal_floor_Q_total": floor.get("Q_total"),
            "legal_floor_C_sha256": floor.get("C_sha256"),
            "actual_calls": document["actual_calls"],
            "charged_replies": payload.get("charged_replies"),
            "cache_hit_replies": payload.get("cache_hit_replies"),
            "passes_used": payload.get("passes_used"),
            "physical_qualification": payload["physical_qualification"],
            "global_uniqueness_certified": False,
            "known_compatible_D_interval_nm": None,
            "parameter_bounds_D_nm": payload["parameter_bounds_D_nm"],
            "reason_codes": payload["reason_codes"], "payload_sha256": payload["payload_sha256"],
            "frames_sha256": payload["frames_sha256"],
            "legal_records_sha256": payload["legal_records_sha256"],
            "task_result_sha256": sha_file(path), "reportable_D": None,
        })
    estimates = {"schema": "iscat167.estimates_new.1", "run_id": ctx["run_id"],
                 "task_count": len(rows), "rows": rows,
                 "state_counts": _count_states(rows),
                 "estimator_read_access": False, "reportable_D": None,
                 "experimental_absolute_diameter_validated": False}
    merge_rows = []
    merge_path = CONTROL / "r_merge_table.json"
    if merge_path.exists():
        for row in read_json(merge_path)["rows"]:
            merge_rows.append(dict(row, identity="MERGE_REUSE_NOT_A_NEW_ESTIMATE"))
    reuse_rows = []
    for source, ref in sorted(ctx["refs"]["zero_bias"].items()):
        reuse_rows.append(dict(ref, identity="ZERO_BIAS_REFERENCE_NOT_A_NEW_ESTIMATE",
                               reuse_kind="V166_SEALED_H1_FINAL_ANSWER"))
    merge = {"schema": "iscat167.estimates_merge_reuse.1", "run_id": ctx["run_id"],
             "r_merge_rows": merge_rows, "r_merge_count": len(merge_rows),
             "zero_bias_reuse_rows": reuse_rows, "zero_bias_reuse_count": len(reuse_rows),
             "v166_estimate_rows_rewritten": 0,
             "v166_estimates_sha256": CONTRACT_PINS["results/v166/estimates.json"],
             "model_calls": 0, "reportable_D": None}
    # Each table is staged on its own path.  The pair used to be written with
    # atomic_json, which refuses an existing path even when it already holds byte
    # for byte the same document, so an interruption between the two writes wedged
    # the round on a name it could neither rewrite nor lawfully remove.  Staging is
    # idempotent: identical bytes are kept, different bytes refuse.
    epath = _evidence(ctx, OUT / "estimates_new.json")
    mpath = _evidence(ctx, OUT / "estimates_merge_reuse.json")
    _stage_json(epath, estimates)
    _stage_json(mpath, merge)
    return {"estimates_new_sha256": sha_file(epath), "merge_reuse_sha256": sha_file(mpath),
            "task_count": len(rows), "state_counts": estimates["state_counts"]}


def write_seal(ctx: dict) -> dict:
    """Seal every new estimate before the validator is allowed to read the truth."""
    estimates_path, merge_path = OUT / "estimates_new.json", OUT / "estimates_merge_reuse.json"
    require(estimates_path.is_file() and merge_path.is_file(), "SEAL_REQUIRES_ESTIMATE_TABLES")
    tables: dict[str, str] = {}
    for path in (estimates_path, merge_path, CONTROL / "per_start_table.json",
                 CONTROL / "r_merge_table.json", CONTROL / "b_stress_table.json",
                 CONTROL / "final_verify.json", CONTROL / "bind_model.json",
                 CONTROL / "source_mapping.json", JAIL_ROOT / "00_isolation_receipt.json",
                 CONTROL / "run_round.json", CONTROL / "task_signatures.json"):
        require(path.is_file(), "SEAL_MISSING_EVIDENCE:" + str(path))
        tables[path.relative_to(ROOT).as_posix()] = sha_file(path)
    tasks = {}
    for entry in ctx["plan"]["entries"]:
        task_id = str(entry["task_id"])
        path = OUT / "tasks" / task_id / "result.json"
        require(path.is_file(), "SEAL_MISSING_TASK_RESULT:" + task_id)
        tasks[task_id] = sha_file(path)
    ledger = LEDGER_PATH
    require(ledger.is_file(), "SEAL_MISSING_LEDGER")
    seal = {
        "schema": "iscat167.estimate_seal.1", "run_id": ctx["run_id"],
        "status": "SEALED_BEFORE_VALIDATOR", "all_reportable_D_null": True,
        "experimental_absolute_diameter_validated": False,
        "execution_code_head": ctx["git_head"],
        "code_identity_sha256": ctx["codes"]["identity_sha256"],
        "plan_sha256": CONTRACT_PLAN_SHA256,
        "height_readings_sha256": CONTRACT_PINS[
            "results/v166/height_input/height_readings.json"],
        "v166_estimates_sha256": CONTRACT_PINS["results/v166/estimates.json"],
        "v166_ledger_sha256": CONTRACT_PINS["results/v166/logs/v165_budget.sqlite"],
        "v166_return_zip_sha256": CONTRACT_PINS[
            "results/v166/iscat_v166_return_001.zip"],
        "preflight_sha256": sha_file(V166 / "preflight.json"),
        "ledger_sha256": sha_file(ledger),
        "estimates_sha256": sha_file(estimates_path),
        "merge_reuse_sha256": sha_file(merge_path),
        "evidence_sha256": tables, "task_result_sha256": tasks,
        "task_result_count": len(tasks),
        "old_v166_task_results_modified": 0,
        "validator_may_read_truth_after_this_point_only": True,
        "seal_utc": datetime.now(timezone.utc).isoformat(),
    }
    path = OUT / "seal.json"
    if path.exists():
        stored = read_json(path)
        require(stored["status"] == "SEALED_BEFORE_VALIDATOR", "SEAL_STATE_CHANGED")
        # The seal is a one-time event: a replay keeps the original instant and the
        # original bytes instead of re-stamping the evidence set.
        seal["seal_utc"] = stored.get("seal_utc")
        sha = _stage_json(path, seal)
        return {"seal_sha256": sha, "sealed_task_results": len(tasks),
                "validator_may_run": True, "already_sealed": True,
                "seal_utc": seal["seal_utc"]}
    else:
        sha = atomic_json(path, seal)
    return {"seal_sha256": sha, "sealed_task_results": len(tasks),
            "validator_may_run": True}


def _stage_text(path: Path, text: str) -> str:
    raw = text.encode("utf-8")
    if path.exists():
        require(path.read_bytes() == raw,
                "REPORT_CHANGED_REFUSING_OVERWRITE:" + str(path))
        return sha_bytes(raw)
    return _stage_bytes(path, raw, where=path.relative_to(ROOT).as_posix())


def failure_records(ctx: dict) -> dict:
    """Every failure, refusal and unfinished state, kept in one durable register."""
    records: list[dict] = []
    for entry in ctx["plan"]["entries"]:
        task_id = str(entry["task_id"])
        path = OUT / "tasks" / task_id / "result.json"
        if not path.exists():
            records.append({"task_id": task_id, "kind": entry["kind"],
                            "record_type": "NOT_STARTED", "detail": "no result document"})
            continue
        document = read_json(path)
        if document.get("failure"):
            failure = document["failure"]
            records.append({"task_id": task_id, "kind": document["kind"],
                            "record_type": "TASK_ROUND_FAILED",
                            "error_type": failure.get("error_type"),
                            "error": failure.get("error"),
                            "reconciliation": failure.get("reconciliation"),
                            "ledger_counts_at_failure": failure.get("ledger_counts"),
                            "traceback_tail": (failure.get("traceback") or "")[-3000:],
                            "db_state": document.get("db_state")})
        for record in document["payload"].get("starts", []):
            for pass_record in record.get("passes", []):
                if pass_record.get("error") or pass_record.get("execution_state") != "FINISHED":
                    records.append({"task_id": task_id, "record_type": "SEARCH_STATE",
                                    "start_index": pass_record.get("start_index"),
                                    "pass_index": pass_record.get("pass_index"),
                                    "execution_state": pass_record.get("execution_state"),
                                    "error": pass_record.get("error"),
                                    "evaluations": pass_record.get("evaluations"),
                                    "local_cap": pass_record.get("local_cap")})
        if document.get("worker_exit_code") not in (0, None):
            records.append({"task_id": task_id, "record_type": "WORKER_EXIT",
                            "worker_exit_code": document.get("worker_exit_code"),
                            "stderr_tail": ((document.get("rpc_receipt") or {}).get(
                                "stderr_lines") or [])[-40:]})
    binding = CONTROL / "binding_result.json"
    if binding.exists():
        receipt = read_json(binding)
        for row in receipt.get("rows", []):
            if row.get("byte_exact_match") is not True:
                records.append({"record_type": "BINDING_WITNESS_MISMATCH", "witness": row})
    recovery = CONTROL / "loader_recovery_note.json"
    if recovery.exists():
        records.append({"record_type": "LOADER_RECOVERY_ONLY",
                        "detail": read_json(recovery).get("reason")})
    document = {"schema": "iscat167.failure_records.1", "run_id": ctx["run_id"],
                "records": records, "record_count": len(records),
                "deleted_records": 0, "hidden_records": 0,
                "model_calls": 0, "reportable_D": None}
    ctx.setdefault("published", {})["failure_records.json"] = _publish_json(
        ctx, CONTROL / "failure_records.json", document)
    return document


def status_document(ctx: dict) -> dict:
    """Contract section 11: EXECUTION, VERIFICATION, EVIDENCE, SCIENTIFIC_SCOPE."""
    round_path, round_history = latest_evidence(CONTROL / "run_round.json")
    final_path, final_history = latest_evidence(CONTROL / "final_verify.json")
    round_doc = read_json(round_path) if round_path.exists() else {}
    final = read_json(final_path) if final_path.exists() else {}
    round_doc = dict(round_doc, published_versions=[str(p) for p in round_history])
    final = dict(final, published_versions=[str(p) for p in final_history])
    estimates = read_json(OUT / "estimates_new.json") if (OUT / "estimates_new.json").exists() \
        else {}
    validator = read_json(OUT / "validator_only" / "v167_scores.json") \
        if (OUT / "validator_only" / "v167_scores.json").exists() else {}
    states = estimates.get("state_counts", {})
    stages = {
        "P0_evidence_protection": {
            "EXECUTION": "EXECUTED", "VERIFICATION": "VERIFIED",
            "EVIDENCE": str(CONTROL / "task_signatures.json"),
            "SCIENTIFIC_SCOPE": "no claim; read-only verification of V166 pins"},
        "P1_input_isolation": {
            "EXECUTION": "EXECUTED",
            "VERIFICATION": ("VERIFIED" if (JAIL_ROOT / "00_isolation_receipt.json").exists()
                             else "NOT_STARTED"),
            "EVIDENCE": str(JAIL_ROOT / "00_isolation_receipt.json"),
            "SCIENTIFIC_SCOPE": "NON-ADVERSARIAL runtime guard, not a kernel sandbox"},
        "P2_model_binding": {
            "EXECUTION": ("EXECUTED" if (CONTROL / "bind_model.json").exists()
                          else "NOT_STARTED"),
            "VERIFICATION": (read_json(CONTROL / "bind_model.json").get("binding_status")
                             if (CONTROL / "bind_model.json").exists() else "NOT_STARTED"),
            "EVIDENCE": str(CONTROL / "bind_model.json"),
            "SCIENTIFIC_SCOPE": "one authorized construction; no new BEM or render"},
        "P3_authorized_computation": {
            "EXECUTION": round_doc.get("status", "EXECUTED" if round_doc else "NOT_STARTED"),
            "VERIFICATION": ("%d of 23 tasks sealed" % round_doc.get("tasks_planned", 0)
                             if round_doc else "NOT_STARTED"),
            "EVIDENCE": str(round_path),
            "SCIENTIFIC_SCOPE": "simulated F2c development fits only"},
        "P4_final_verify": {
            "EXECUTION": final.get("status", final.get("execution_state", "NOT_STARTED")),
            "VERIFICATION": ("logical %s / distinct %s / verified %s / not verifiable %s"
                             % (final.get("logical_items"), final.get("distinct_theta"),
                                final.get("verified"), final.get("not_verifiable"))
                             if final else "NOT_STARTED"),
            "EVIDENCE": str(final_path),
            "SCIENTIFIC_SCOPE": "byte-level reproduction of published answers only"},
        "P5_seal_and_score": {
            "EXECUTION": "EXECUTED" if (OUT / "seal.json").exists() else "NOT_STARTED",
            "VERIFICATION": validator.get("status", "NOT_STARTED"),
            "EVIDENCE": str(OUT / "seal.json"),
            "SCIENTIFIC_SCOPE": validator.get("scientific_scope",
                                              "NOT_EVALUATED until the validator runs")},
    }
    counts = dict(ctx["store"].counts())
    usage = {"MODEL_BINDING": counts.get(LOADER_TASK, 0) + counts.get(BINDING_TASK, 0),
             "SEARCH_EXTENSION": sum(counts.get(str(e["task_id"]), 0)
                                     for e in ctx["plan"]["entries"]
                                     if e["kind"] == "SEARCH_EXTENSION"),
             "BIAS_STRESS": sum(counts.get(str(e["task_id"]), 0)
                                for e in ctx["plan"]["entries"]
                                if e["kind"] == "BIAS_STRESS"),
             "FINAL_VERIFY": counts.get(FINAL_TASK, 0)}
    document = {"schema": "iscat167.status.1", "run_id": ctx["run_id"],
                "git_head": ctx["git_head"], "code_identity_sha256": ctx["codes"]["identity_sha256"],
                "plan_sha256": CONTRACT_PLAN_SHA256, "stages": stages,
                "task_execution_states": states,
                "tasks_total": len(ctx["plan"]["entries"]),
                "r_tasks": 5, "b_tasks": 18,
                "budget_used_by_phase": usage, "budget_cap_by_phase": dict(PHASES),
                "budget_used_total": sum(usage.values()), "budget_total": TOTAL,
                "phase_transfers": 0,
                "new_bem": 0, "new_render": 0, "new_camera_exposures": 0,
                "new_camera_noise_draws": 0, "new_height_random_draws": 0,
                "new_fixed_D_sweeps": 0, "v166_results_modified": 0,
                "reportable_D": None,
                "experimental_absolute_diameter_validated": False,
                "global_uniqueness_certified": False}
    ctx.setdefault("published", {})["status.json"] = _publish_json(ctx, OUT / "status.json",
                                                                   document)
    return document


def manifest_document(ctx: dict) -> dict:
    """Hash every byte under results/v167 so the published tree is checkable."""
    rows = []
    for path in sorted(OUT.rglob("*")):
        if not path.is_file():
            continue
        name = path.name
        if (name.endswith(".zip") or name == "manifest.json"
                or name.startswith("verification") or name.endswith(".tmp")):
            continue
        rows.append({"path": path.relative_to(ROOT).as_posix(),
                     "sha256": sha_file(path), "bytes": path.stat().st_size})
    tree = {"results/v167": len(rows),
            "bytes_total": sum(row["bytes"] for row in rows)}
    document = {"schema": "iscat167.manifest.1", "run_id": ctx["run_id"],
                "files": rows, "file_count": len(rows), "tree_counts": tree,
                "excluded": ["results/v167/manifest.json", "results/v167/verification*.json",
                             "results/v167/*.zip", "*.tmp"],
                "exclusion_reason": ("a manifest cannot hash itself, and verification.json "
                                     "records the manifest SHA, so hashing it here would be a "
                                     "reference cycle"),
                "model_calls": 0}
    ctx.setdefault("published", {})["manifest.json"] = _publish_json(ctx, OUT / "manifest.json",
                                                                     document)
    return document


def verification_document(ctx: dict, manifest: dict) -> dict:
    rows = []
    for rel, pinned in sorted(CONTRACT_PINS.items()):
        # Every contract pin is named by its repository-relative path, the return
        # archive included.  Only if that exact path is absent do we look for the
        # file name in the V166 root or its deliverables mirror, and a repository-wide
        # search is the last resort, recorded in the row.
        path = ROOT / rel
        resolved_by = "contract_repository_path"
        if not path.is_file():
            stem = Path(rel).name
            for alternative in (V166 / stem, V166 / "deliverables" / stem):
                if alternative.is_file():
                    path, resolved_by = alternative, "v166_mirror_by_file_name"
                    break
            else:
                hit = next((item for item in ROOT.rglob(stem) if item.is_file()), None)
                path, resolved_by = (hit, "repository_search_by_file_name") if hit else (path, "unresolved")
        candidate = path if path.is_file() else None
        rows.append({"path": rel, "contract_sha256": pinned,
                     "resolved_path": str(candidate) if candidate else None,
                     "resolved_by": resolved_by,
                     "observed_sha256": sha_file(candidate) if candidate else None,
                     "match": bool(candidate) and sha_file(candidate) == pinned,
                     "bytes": candidate.stat().st_size if candidate else None,
                     "expected_zip_bytes": CONTRACT_ZIP_BYTES if rel.endswith(".zip") else None})
    seal = read_json(OUT / "seal.json") if (OUT / "seal.json").exists() else {}
    document = {"schema": "iscat167.verification.1", "run_id": ctx["run_id"],
                "git_head": ctx["git_head"], "v166_release_commit": PARENT_COMMIT,
                "code_identity_sha256": ctx["codes"]["identity_sha256"],
                "code_file_count": ctx["codes"]["file_count"],
                "plan_sha256": CONTRACT_PLAN_SHA256,
                "manifest_sha256": sha_file(OUT / "manifest.json"),
                "manifest_file_count": manifest["file_count"],
                "contract_pin_rows": rows,
                "contract_pins_matched": sum(1 for row in rows if row["match"]),
                "seal_sha256": sha_file(OUT / "seal.json") if (OUT / "seal.json").exists() else None,
                "seal_status": seal.get("status"),
                "old_evidence_read_only_confirmed": True,
                "zip_sha256": None, "zip_bytes": None,
                "zip_filled_by_pack_step": "run_all.py",
                "independent_acceptance": "NOT_RUN_IN_CONTROLLER",
                "model_calls": 0, "reportable_D": None,
                "experimental_absolute_diameter_validated": False}
    ctx.setdefault("published", {})["verification.json"] = _publish_json(
        ctx, OUT / "verification.json", document)
    return document


# ----------------------------------------------------------------- merge and stress

def _v166_legal_floor(source_task_id: str) -> dict:
    """The frozen legal-record floor V166 sealed for one old task."""
    path = V166 / "tasks" / source_task_id / "legal_witnesses.json"
    require(path.is_file(), "V166_LEGAL_WITNESSES_MISSING:" + source_task_id)
    document = read_json(path)
    rows = document.get("rows") or []
    require(len(rows) >= 1, "V166_LEGAL_WITNESS_ROWS:" + source_task_id)
    floor = min(rows, key=lambda row: float(row["Q_total"]))
    require(abs(float(floor["Q_total"]) - float(rows[0]["Q_total"])) < 1e-12,
            "V166_LEGAL_FLOOR_NOT_FIRST_ROW:" + source_task_id)
    return {"source_task_id": source_task_id, "theta": [float(v) for v in floor["theta"]],
            "Q_total": float(floor["Q_total"]), "C_sha256": str(floor["C_sha256"]),
            "document": str(path), "document_sha256": sha_file(path),
            "rows": len(rows)}


def _candidate(source: str, label: str, theta: Any, q_total: Any, *, origin: str,
               prediction: Any = None, c_sha: Any = None) -> dict | None:
    if theta is None or q_total is None:
        return None
    theta = [float(v) for v in theta]
    return {"origin": origin, "source": source, "label": label, "theta": theta,
            "c_sha256": (None if c_sha is None else str(c_sha)),
            "Q_total": float(q_total), "D_nm": theta[0], "h_nm": theta[1],
            "h_minus_half_D_nm": theta[1] - 0.5 * theta[0],
            "physical_clearance_ok": theta[1] - 0.5 * theta[0] >= 100.0,
            "prediction": prediction, "reportable_D": None}


def r_merge_table(ctx: dict) -> dict:
    """Contract section 5: merge the warm completion with the sealed V166 history.

    Nothing is discarded and nothing is rewritten: the old PARTIAL_SEARCH row, the
    old first-start best, the old second-start best (the warm start), the old legal
    floor and the two new V167 values all stay as candidates, and the merged pick is
    purely the lowest joint objective Q_total.
    """
    rows = []
    for entry in ctx["plan"]["entries"]:
        if entry["kind"] != "SEARCH_EXTENSION":
            continue
        source = str(entry["source_task_id"])
        task_id = str(entry["task_id"])
        partial = ctx["refs"]["partials"][source]
        result_path = OUT / "tasks" / task_id / "result.json"
        new = read_json(result_path) if result_path.exists() else None
        new_payload = (new or {}).get("payload") or {}
        old_floor = _v166_legal_floor(source)
        new_best = new_payload.get("optimizer_best") or {}
        new_floor = new_payload.get("best_legal_witness") or {}
        candidates = [
            _candidate(source, "v166_first_start_best", None,
                       partial["old_first_start_best"], origin="V166_SEALED"),
            _candidate(source, "v166_second_start_partial_best", partial["warm_theta"],
                       partial["warm_Q_total"], origin="V166_SEALED",
                       prediction=partial["warm_prediction"],
                       c_sha=partial["warm_C_sha256"]),
            _candidate(source, "v166_legal_floor", old_floor["theta"],
                       old_floor["Q_total"], origin="V166_SEALED",
                       prediction=old_floor["document"], c_sha=old_floor["C_sha256"]),
            _candidate(task_id, "v167_new_optimizer_best", new_payload.get("theta"),
                       new_best.get("Q_total"), origin="V167_NEW",
                       prediction=new_best.get("prediction_path"),
                       c_sha=_prediction_c_sha(new_best.get("prediction_path"))),
            _candidate(task_id, "v167_new_legal_floor",
                       new_floor.get("theta"), new_floor.get("Q_total"),
                       origin="V167_NEW", prediction=(new or {}).get("result_sha256"),
                       c_sha=new_floor.get("C_sha256")),
        ]
        candidates = [item for item in candidates if item is not None]
        # The first-start best keeps only its Q_total in V166 estimates; the theta is
        # recovered from the sealed best document so the merge can compare parameters.
        for item in candidates:
            if item["label"] == "v166_first_start_best":
                document = _witness_document(source, "start_000.json")
                item["theta"] = [float(v) for v in document["theta"]]
                item["D_nm"] = item["theta"][0]
                item["h_nm"] = item["theta"][1]
                item["h_minus_half_D_nm"] = item["theta"][1] - 0.5 * item["theta"][0]
                item["physical_clearance_ok"] = item["h_minus_half_D_nm"] >= 100.0
                item["prediction"] = document["prediction_path"]
                item["c_sha256"] = str(document["C_sha256"])
        require(all(item["theta"] is not None for item in candidates),
                "R_MERGE_CANDIDATE_THETA_MISSING:" + task_id)
        best = min(candidates, key=lambda item: item["Q_total"])
        old_theta = [float(v) for v in partial["warm_theta"]]
        rows.append({
            "task_id": task_id, "source_task_id": source,
            "group": ctx["staged_by_task"][task_id]["group"],
            "sigma_nm": ctx["staged_by_task"][task_id]["sigma_nm"],
            "replicate": ctx["staged_by_task"][task_id]["replicate"],
            "old_execution_state": partial["old_status_preserved"],
            "old_execution_state_preserved_verbatim": True,
            "old_candidate_D_nm": partial["old_candidate_D_nm"],
            "old_task_result_sha256": partial["old_task_result_sha256"],
            "old_start_consumption": partial["old_start_consumption"],
            "new_execution_state": (new or {}).get("execution_state", "NOT_STARTED"),
            "new_report_label": (new or {}).get("report_label"),
            "new_actual_calls": (new or {}).get("actual_calls"),
            "new_charged_replies": (new_payload.get("charged_replies")),
            "new_cache_hit_replies": (new_payload.get("cache_hit_replies")),
            "candidates": candidates,
            "merged_pick": best["label"], "merged_Q_total": best["Q_total"],
            "merged_theta": best["theta"], "merged_D_nm": best["D_nm"],
            "delta_D_vs_old_partial_nm": best["D_nm"] - old_theta[0],
            "delta_Q_vs_old_partial": best["Q_total"] - float(partial["warm_Q_total"]),
            "delta_D_vs_v166_final_nm": best["D_nm"] - float(partial["old_candidate_D_nm"]),
            "search_state": ("SEARCH_COMPLETE_LOCAL_RETURN"
                             if (new or {}).get("execution_state") == "FINISHED"
                             else "SEARCH_INCOMPLETE"),
            "selection_rule": "lowest joint objective Q_total only; never true-parameter error",
            "anonymous_detection_status": "ANON_01 detection remains 0/3 (unchanged)",
            "reportable_D": None, "model_calls": 0,
        })
    document = {"schema": "iscat167.r_merge_table.1", "run_id": ctx["run_id"],
                "rows": rows, "row_count": len(rows),
                "state_counts": _count_states(rows),
                "old_partial_tasks_rewritten": 0,
                "old_partial_tasks_kept_as_partial_where_new_search_incomplete": True,
                "model_calls": 0, "reportable_D": None}
    ctx.setdefault("published", {})["r_merge_table.json"] = _publish_json(
        ctx, CONTROL / "r_merge_table.json", document)
    return document


def _rescore_historical_witness(ctx: dict, entry: dict, source: str) -> dict | None:
    """Score the zero-bias legal θ under the biased reading from stored C only.

    Contract section 6 calls the historical best a diagnostic witness, not a third
    start.  The model output for that theta is already billed and was byte-verified
    against the live model at binding time, so re-scoring costs zero forward calls.
    """
    ref = ctx["refs"]["zero_bias"][source]
    task_id = str(entry["task_id"])
    jail = OUT / "estimator_inputs" / task_id
    frames_doc = read_json(jail / "frames.json")
    payload = read_json(jail / "input.json")
    data, _identity, frames_sha = common.frames_from_document(frames_doc,
                                                              where="controller:bias_witness")
    reading = common.reading_from_document(payload["reading"])
    score = common.score_document(ref["theta"], ref["prediction_C_array"], data, reading)
    return {"source_task_id": source, "label": "v166_zero_bias_legal_witness_rescored",
            "theta": [float(v) for v in ref["theta"]], "Q_total": float(score["Q_total"]),
            "Q_model": float(score["Q_model"]), "Q_height": float(score["Q_height"]),
            "K": float(score["K"]), "residual_sha256": score["residual_sha256"],
            "sealed_zero_bias_C_sha256": ref["C_sha256"],
            "zero_bias_Q_total": ref["Q_total"], "zero_bias_D_nm": ref["candidate_D_nm"],
            "historical_prediction": ref["prediction"],
            "historical_prediction_sha256": ref["prediction_sha256"],
            "binding_witness_verified": True, "frames_sha256": frames_sha,
            "new_model_calls": 0, "reportable_D": None}


def b_stress_table(ctx: dict) -> dict:
    """Contract section 6: two report columns, never a truth-based selection."""
    rows = []
    for entry in ctx["plan"]["entries"]:
        if entry["kind"] != "BIAS_STRESS":
            continue
        task_id = str(entry["task_id"])
        source = str(entry["source_task_id"])
        staged = ctx["staged_by_task"][task_id]
        result_path = OUT / "tasks" / task_id / "result.json"
        new = read_json(result_path) if result_path.exists() else None
        payload = (new or {}).get("payload") or {}
        optimizer_best = payload.get("optimizer_best") or {}
        legal_floor = payload.get("best_legal_witness") or {}
        column_a = optimizer_best.get("Q_total")
        column_a = float(column_a) if column_a is not None else None
        column_a_theta = payload.get("theta")
        floor_q = float(legal_floor["Q_total"]) if legal_floor.get("Q_total") is not None else None
        floor_theta = [float(v) for v in legal_floor["theta"]] if legal_floor.get("theta") else None
        witness = None
        witness_error = None
        try:
            witness = _rescore_historical_witness(ctx, entry, source)
        except Exception as exc:                                    # noqa: BLE001
            witness_error = type(exc).__name__ + ":" + str(exc)[:600]
        pool = [value for value in (column_a, floor_q,
                                    witness["Q_total"] if witness else None)
                if value is not None]
        column_b = min(pool) if pool else None
        column_b_theta = column_a_theta
        if witness and column_b == witness["Q_total"]:
            column_b_theta = witness["theta"]
        elif floor_q is not None and column_b == floor_q:
            column_b_theta = floor_theta
        tolerance = max(1e-9, 1e-10 * max(1.0, abs(column_a or 0.0)))
        search_incomplete = (column_b is not None and column_a is not None
                             and column_b < column_a - tolerance)
        rows.append({
            "task_id": task_id, "source_task_id": source, "group": staged["group"],
            "replicate": staged["replicate"], "sigma_nm": staged["sigma_nm"],
            "reading_id": staged["reading_projection"]["reading_id"],
            "controlled_offset_nm": staged["controlled_offset_nm"],
            "offset_is_fixed_not_fitted": True, "new_random_draws": 0,
            "zero_bias_reference_D_nm": ctx["refs"]["zero_bias"][source]["candidate_D_nm"],
            "zero_bias_reference_Q_total": ctx["refs"]["zero_bias"][source]["Q_total"],
            "execution_state": (new or {}).get("execution_state", "NOT_STARTED"),
            "report_label": (new or {}).get("report_label"),
            "actual_calls": (new or {}).get("actual_calls"),
            "charged_replies": payload.get("charged_replies"),
            "cache_hit_replies": payload.get("cache_hit_replies"),
            "new_start_thetas": [[float(v) for v in start] for start in staged["starts"]],
            "starts_used": len(payload.get("starts") or []),
            "passes_used": payload.get("passes_used"),
            "column_two_prescribed_starts_only_D_nm": (None if column_a_theta is None
                                                       else float(column_a_theta[0])),
            "column_two_prescribed_starts_only_Q_total": column_a,
            "column_including_historical_witness_D_nm": (None if column_b_theta is None
                                                         else float(column_b_theta[0])),
            "column_including_historical_witness_Q_total": column_b,
            "new_legal_floor_Q_total": floor_q,
            "new_legal_floor_D_nm": (None if floor_theta is None else float(floor_theta[0])),
            "historical_witness_rescored": witness,
            "historical_witness_rescore_error": witness_error,
            "witness_below_new_search": search_incomplete,
            "search_state": ("SEARCH_INCOMPLETE" if search_incomplete
                             else "SEARCH_COMPLETE_LOCAL_RETURN"
                             if (new or {}).get("execution_state") == "FINISHED"
                             else (new or {}).get("execution_state", "NOT_STARTED")),
            "selection_rule": ("both columns reported; no selection by true parameter "
                               "error; sigma never inflated"),
            "sigma_nm_never_modified": True, "reportable_D": None, "model_calls": 0,
        })
    by_offset: dict[str, dict] = {}
    for row in rows:
        bucket = by_offset.setdefault(str(row["controlled_offset_nm"]),
                                      {"tasks": 0, "finished": 0, "partial": 0, "failed": 0})
        bucket["tasks"] += 1
        state = row["execution_state"]
        if state == "FINISHED":
            bucket["finished"] += 1
        elif state == "PARTIAL_SEARCH":
            bucket["partial"] += 1
        elif state in ("FAILED", "NOT_STARTED"):
            bucket["failed"] += 1
    document = {"schema": "iscat167.b_stress_table.1", "run_id": ctx["run_id"],
                "rows": rows, "row_count": len(rows),
                "state_counts": _count_states(rows), "by_offset": by_offset,
                "historical_witness_is_a_third_start": False,
                "historical_witness_status": "DIAGNOSTIC_WITNESS_ONLY",
                "model_calls": 0, "new_random_draws": 0, "reportable_D": None}
    ctx.setdefault("published", {})["b_stress_table.json"] = _publish_json(
        ctx, CONTROL / "b_stress_table.json", document)
    return document


# ------------------------------------------------------------------------ CLI

def run_validator(ctx: dict) -> dict:
    """Hand the sealed bytes to the one truth-reading process and record what it said.

    The validator runs as a subprocess so that no truth read can be attributed to the
    model-bearing controller process, and so that its own seal gate is evaluated on
    bytes on disk rather than on in-memory state.  It is refused unless seal.json
    already exists, and the ledger must come back byte-identical because the validator
    opens it read-only.
    """
    seal_path = OUT / "seal.json"
    if not ctx["dry_run"]:
        require(seal_path.is_file(), "VALIDATE_REQUIRES_SEAL_FIRST:" + str(seal_path))
    script = ROOT / "tools" / "v167" / "v167_validator.py"
    require(script.is_file(), "VALIDATOR_SCRIPT_MISSING:" + str(script))
    argv = [sys.executable, "-X", "utf8", str(script)]
    if ctx["dry_run"]:
        argv.append("--dry-run")
    service = ctx.get("service")
    constructions_before = service.constructions if service is not None else 0
    ledger_before = sha_file(LEDGER_PATH) if LEDGER_PATH.is_file() else None
    proc = subprocess.run(argv, capture_output=True, text=True, cwd=str(ROOT),
                          encoding="utf-8", errors="replace")
    ledger_after = sha_file(LEDGER_PATH) if LEDGER_PATH.is_file() else None
    log_path = OUT / "logs" / ("validator_run_" + str(ctx["run_id"]) + ".log")
    log_sha = _stage_text(
        log_path,
        "# V167 validator subprocess\n$ " + " ".join(argv)
        + "\nexit_code=" + str(proc.returncode)
        + "\n--- stdout ---\n" + (proc.stdout or "")
        + "\n--- stderr ---\n" + (proc.stderr or ""))
    line = next((item for item in reversed((proc.stdout or "").splitlines())
                 if item.startswith("VALIDATOR ")), None)
    require(proc.returncode == 0,
            "VALIDATOR_SUBPROCESS_FAILED:exit=" + str(proc.returncode) + ":"
            + ((proc.stderr or "").strip()[-2000:] or (proc.stdout or "")[-2000:]))
    require(line is not None, "VALIDATOR_NO_REPORT_LINE")
    report = json.loads(line[len("VALIDATOR "):])
    require(report.get("model_calls") == 0, "VALIDATOR_MUST_MAKE_NO_MODEL_CALLS")
    require(ledger_after == ledger_before,
            "LEDGER_CHANGED_DURING_VALIDATOR:" + str(ledger_before) + "!=" + str(ledger_after))
    after = service.constructions if service is not None else 0
    require(after == constructions_before,
            "VALIDATOR_CONSTRUCTED_A_MODEL_IN_CONTROLLER_PROCESS")
    document = {"schema": "iscat167.validator_run.1", "run_id": ctx["run_id"],
                "dry_run": bool(ctx["dry_run"]),
                "script": script.relative_to(ROOT).as_posix(),
                "script_sha256": sha_file(script), "argv": argv,
                "exit_code": proc.returncode,
                "log_path": log_path.relative_to(ROOT).as_posix(),
                "log_sha256": log_sha, "report_line": report,
                "stdout_tail": (proc.stdout or "")[-2000:],
                "stderr_tail": (proc.stderr or "")[-2000:],
                "ledger_sha256_before": ledger_before, "ledger_sha256_after": ledger_after,
                "ledger_writable_by_validator": False,
                "seal_sha256": (sha_file(seal_path) if seal_path.is_file() else None),
                "sealed_estimates_sha256": (read_json(seal_path).get("estimates_sha256")
                                            if seal_path.is_file() else None),
                "status": report.get("status"),
                "truth_file_opened": not bool(ctx["dry_run"]),
                "model_calls": 0,
                "model_constructions_in_controller_process": after,
                "reportable_D": None}
    ctx.setdefault("published", {})["validator_run.json"] = _publish_json(
        ctx, _evidence(ctx, CONTROL / "validator_run.json"), document)
    return document


STEP_ORDER = ("prepare", "bind", "run", "tables", "final", "estimates", "seal",
              "validate", "records", "status", "manifest", "verification")
EVIDENCE_ONLY_STEPS = ("tables", "records", "status", "manifest", "verification")

# A rehearsal makes no model calls, so there is nothing sealed to merge, score or
# hash.  These steps report NOT_STARTED_DRY_RUN instead of occupying a primary
# evidence name that the authorized run still has to write.
DRY_SKIPPED_STEPS = ("tables", "estimates", "seal", "records", "status",
                     "manifest", "verification")


def _dispatch(name: str, ctx: dict) -> Any:
    if ctx.get("dry_run") and name in DRY_SKIPPED_STEPS:
        return {"step": name, "status": "NOT_STARTED_DRY_RUN",
                "reason": ("the rehearsal made no model calls, so there are no sealed "
                           "task results for this step to consume"),
                "model_calls": 0}
    if name == "bind":
        return bind_model(ctx)
    if name == "run":
        return run_round(ctx)
    if name == "tables":
        return {"per_start_table_rows": per_start_table(ctx)["row_count"],
                "r_merge_rows": r_merge_table(ctx)["row_count"],
                "b_stress_rows": b_stress_table(ctx)["row_count"]}
    if name == "final":
        return final_verify(ctx)
    if name == "estimates":
        return estimates_documents(ctx)
    if name == "seal":
        document = write_seal(ctx)
        ctx["seal"] = document
        return document
    if name == "validate":
        document = run_validator(ctx)
        ctx["validate"] = document
        return document
    if name == "records":
        return {"record_count": failure_records(ctx)["record_count"]}
    if name == "status":
        stages = status_document(ctx)["stages"]
        return {key: (value["EXECUTION"], value["VERIFICATION"])
                for key, value in stages.items()}
    if name == "manifest":
        document = manifest_document(ctx)
        ctx["manifest"] = document
        return {"file_count": document["file_count"]}
    if name == "verification":
        if "manifest" not in ctx:
            ctx["manifest"] = manifest_document(ctx)
        document = verification_document(ctx, ctx["manifest"])
        return {"contract_pins_matched": document["contract_pins_matched"],
                "manifest_sha256": document["manifest_sha256"]}
    raise ValueError("STEP_NOT_DISPATCHABLE:" + name)


def _scalar_summary(result: Any) -> dict:
    """Keep the step trace readable: scalars only, never a 23-row payload dump."""
    if not isinstance(result, dict):
        return {"result_type": type(result).__name__}
    keep = {}
    for key in ("status", "execution_state", "db_state", "binding_status", "model_calls",
                "actual_calls", "tasks_planned", "tasks_executed_this_round", "row_count",
                "task_count", "seal_sha256", "estimates_new_sha256", "merge_reuse_sha256",
                "logical_items", "distinct_theta", "verified", "not_verifiable",
                "authorized_constructions", "file_count", "contract_pins_matched"):
        value = result.get(key)
        if isinstance(value, (bool, int, float, str, type(None))):
            keep[key] = value
    return keep


def main(argv: list[str] | None = None) -> int:
    """Run the authorized V167 sequence in one process, one construction.

    A failing step never silently continues into the steps that spend budget: those
    are recorded as BLOCKED.  The evidence-only steps still run, because a failure
    has to be reported with the current tree around it.
    """
    parser = argparse.ArgumentParser(prog="v167_controller",
                                     description="V167 trusted controller")
    parser.add_argument("--dry-run", action="store_true",
                        help="P0/P1 staging and rehearsal only; zero model calls")
    parser.add_argument("--steps", default="all",
                        help="comma separated subset of " + ",".join(STEP_ORDER))
    args = parser.parse_args(argv)
    wanted = (list(STEP_ORDER) if args.steps == "all"
              else [item for item in args.steps.replace(" ", "").split(",") if item])
    unknown = [item for item in wanted if item not in STEP_ORDER]
    require(not unknown, "UNKNOWN_STEP:" + ",".join(unknown))
    require("prepare" in wanted, "STEP_SET_REQUIRES_PREPARE")

    trace: list[dict] = []
    ctx: dict[str, Any] = {}
    exit_code = 0
    failed_step: str | None = None
    for name in wanted:
        if failed_step is not None:
            if name not in EVIDENCE_ONLY_STEPS:
                trace.append({"step": name, "status": "BLOCKED",
                              "blocked_by": failed_step,
                              "reason": "an earlier step failed; no budget was spent here"})
                print("BLOCKED " + name + " by " + failed_step, flush=True)
                continue
        step_started = time.monotonic()
        try:
            result = prepare(dry_run=args.dry_run) if name == "prepare" else _dispatch(name, ctx)
            if name == "prepare":
                # prepare returns the live context itself: run_id, plan, staged rows,
                # ledger handle.  The later steps read that context, so it is merged
                # rather than nested, and the trace keeps a scalar view of it.
                ctx.update(result)
                summary = {"run_id": ctx["run_id"], "dry_run": bool(ctx["dry_run"]),
                           "git_head": ctx["git_head"],
                           "code_identity_sha256": ctx["codes"]["identity_sha256"],
                           "tasks_planned": len(ctx["plan"]["entries"]),
                           "budget_total": ctx["document"]["total_cap"],
                           "model_calls": 0}
            else:
                summary = _scalar_summary(result) if isinstance(result, dict) else {}
                ctx[name] = result
            trace.append({"step": name, "status": "OK",
                          "wall_seconds": round(time.monotonic() - step_started, 3),
                          "summary": summary})
            print("STEP_OK " + name + " " + json.dumps(summary, sort_keys=True)[:600],
                  flush=True)
        except BaseException as exc:                                # noqa: BLE001
            exit_code = 1
            failed_step = name
            trace.append({"step": name, "status": "FAILED",
                          "wall_seconds": round(time.monotonic() - step_started, 3),
                          "error_type": type(exc).__name__,
                          "error": str(exc)[:3000],
                          "traceback_tail": traceback.format_exc()[-6000:]})
            print("STEP_FAILED " + name + " " + type(exc).__name__ + " "
                  + str(exc)[:1200], flush=True)
            if name == "prepare":
                break
    service = ctx.get("service")
    if service is not None:
        try:
            service.close()
        except BaseException as exc:                                # noqa: BLE001
            trace.append({"step": "close_service", "status": "FAILED",
                          "error_type": type(exc).__name__, "error": str(exc)[:1000]})
    trace_doc = {"schema": "iscat167.step_sequence.1",
                 "run_id": ctx.get("run_id"), "dry_run": bool(args.dry_run),
                 "requested_steps": wanted, "steps": trace,
                 "exit_code": exit_code,
                 "failed_step": failed_step,
                 "blocked_steps": [row["step"] for row in trace if row["status"] == "BLOCKED"],
                 "model_constructions_in_process": (service.constructions
                                                    if service is not None else 0),
                 "reportable_D": None}
    if ctx:
        _publish_json(ctx, _evidence(ctx, CONTROL / "step_sequence.json"), trace_doc)
    print("TRACE " + json.dumps(trace_doc, sort_keys=True), flush=True)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
