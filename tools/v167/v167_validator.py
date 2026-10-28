"""V167 validator: score the sealed estimates against the opened-scene truth.

Contract section 8 is the whole design of this module.  Every new estimate, its
selection rule, its inputs and the code SHAs are sealed first, in
results/v167/seal.json with status SEALED_BEFORE_VALIDATOR; only after that does
this process read the synthetic truth and compute errors.  Nothing here can build
a model, nothing here writes into an estimator-readable root, and every truth
value read here is written only under results/v167/validator_only/.

The module deliberately refuses rather than repairs: a missing seal, a changed
sealed byte, or code that moved after the seal all stop the scoring, because a
score computed on a mutated evidence set is not the score that was sealed.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sqlite3
import statistics
import sys
from pathlib import Path
from typing import Any

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import v167_common as common                                                   # noqa: E402
from v167_common import (  # noqa: E402
    OUT, PARENT_WS, ROOT, TOTAL, V166, canon, read_json, require,
    sha_bytes, sha_file,
)
import v167_controller as ctrl                                                 # noqa: E402

VAL = OUT / "validator_only"
ARCHIVE = VAL / "history"
CONTROL = ctrl.CONTROL
LEDGER_PATH = ctrl.LEDGER_PATH

# The sealed height truth and the file whose hash the public table publishes.
# Both live outside every estimator root; the pins are transcribed from the
# parent workstation tree, and a changed byte stops the validator.
SEALED_TRUTH = (PARENT_WS.parent / "v165" / "validator_only"
                / "v166_height_truth_sealed.json")
SEALED_TRUTH_OWN_SHA256 = ("acb3d44cb944d094a19575aaf6ce98da5d619e8318bf0fd0"
                           "0400a9d9c8ebbb06")
V142_TRUTH = PARENT_WS.parent / "v142" / "validation" / "new_N_validator_only_truth.json"
FROZEN_DETECTIONS = V166 / "frozen_detections.json"
READINGS = V166 / "height_input" / "height_readings.json"

D_SCENE_BY_GROUP = {"ANON_01": 59.0, "ANON_02": 101.0, "ANON_03": 143.0, "ANON_04": 181.0}
SCENARIOS = (-2.0, 2.0)
ZERO_BIAS_DESIGN = "H1"
# Section 8 names the R supplement table 原结果＋补充搜索; built from escapes so
# the source file itself stays ASCII.
LABEL_R_SUPPLEMENT = ("\u539f\u7ed3\u679c\uff0b\u8865\u5145\u641c\u7d22"
                      " (original results plus supplementary search)")


def _rel(path: Path) -> str:
    return Path(path).relative_to(ROOT).as_posix()


def _write_bytes(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        require(path.read_bytes() == raw, "VALIDATOR_BYTE_CONFLICT:" + _rel(path))
        return
    handle = path.open("xb")
    try:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    finally:
        handle.close()
    require(path.read_bytes() == raw, "VALIDATOR_READBACK_MISMATCH:" + _rel(path))


def _replace_bytes(path: Path, raw: bytes) -> None:
    """Overwrite a document only after its previous bytes were archived.

    ``_write_bytes`` refuses a byte conflict on purpose, so the replacement half of
    the archive-then-write path needs its own atomic writer: temp file, fsync,
    rename, read back.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    handle = tmp.open("wb")
    try:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    finally:
        handle.close()
    os.replace(tmp, path)
    require(path.read_bytes() == raw, "VALIDATOR_READBACK_MISMATCH:" + _rel(path))


def _write(path: Path, document: Any) -> dict:
    """Deterministic writer: same bytes replay, different bytes archive the old copy.

    The validator carries no timestamps, so a replay of the same sealed evidence
    is byte identical.  If a real re-run ever produces different content (because
    the sealed set itself moved), the previous bytes are preserved under
    validator_only/history before the current document replaces them, so nothing
    that was ever published as a score is silently destroyed.
    """
    raw = canon(document) if not isinstance(document, bytes) else document
    archived = None
    if Path(path).exists():
        existing = Path(path).read_bytes()
        if existing != raw:
            handle = ARCHIVE / (Path(path).stem + "." + sha_bytes(existing)[:16]
                                + Path(path).suffix)
            _write_bytes(handle, existing)
            archived = _rel(handle)
        elif sha_bytes(existing) == sha_bytes(raw):
            return {"path": _rel(Path(path)), "sha256": sha_bytes(raw),
                    "archived_previous": archived, "replayed_identical": True}
    if archived is None:
        _write_bytes(Path(path), raw)
    else:
        _replace_bytes(Path(path), raw)
    return {"path": _rel(Path(path)), "sha256": sha_bytes(raw),
            "archived_previous": archived, "replayed_identical": False}


# ---------------------------------------------------------------------- evidence gate

def seal_gate() -> dict:
    """Refuse to read any truth until the seal exists and still matches its bytes."""
    path = OUT / "seal.json"
    require(path.is_file(), "VALIDATOR_REQUIRES_SEAL_BEFORE_TRUTH:" + str(path))
    seal = read_json(path)
    require(seal.get("status") == "SEALED_BEFORE_VALIDATOR",
            "SEAL_STATUS_NOT_SEALED:" + str(seal.get("status")))
    require(seal.get("validator_may_read_truth_after_this_point_only") is True,
            "SEAL_DOES_AUTHORISE_TRUTH_READ")
    problems: list[str] = []
    for name, key in (("estimates_new.json", "estimates_sha256"),
                      ("estimates_merge_reuse.json", "merge_reuse_sha256")):
        current = sha_file(OUT / name)
        if current != seal.get(key):
            problems.append(name + ":" + str(seal.get(key)) + "!=" + current)
    for rel, expected in (seal.get("evidence_sha256") or {}).items():
        disk = ROOT / rel
        if not disk.is_file():
            problems.append("missing:" + rel)
        elif sha_file(disk) != expected:
            problems.append("changed:" + rel)
    for task_id, expected in (seal.get("task_result_sha256") or {}).items():
        disk = OUT / "tasks" / task_id / "result.json"
        if not disk.is_file():
            problems.append("missing_task:" + task_id)
        elif sha_file(disk) != expected:
            problems.append("changed_task:" + task_id)
    if seal.get("plan_sha256") != ctrl.CONTRACT_PLAN_SHA256:
        problems.append("plan_sha256")
    if seal.get("v166_estimates_sha256") != ctrl.CONTRACT_PINS["results/v166/estimates.json"]:
        problems.append("v166_estimates_pin")
    if sha_file(READINGS) != ctrl.CONTRACT_PINS[
            "results/v166/height_input/height_readings.json"]:
        problems.append("v166_readings_pin")
    codes = ctrl.code_identities()
    if codes["identity_sha256"] != seal.get("code_identity_sha256"):
        problems.append("code_identity_changed_after_seal:"
                        + str(seal.get("code_identity_sha256")) + "!="
                        + codes["identity_sha256"])
    require(not problems, "SEALED_EVIDENCE_CHANGED:" + ";".join(problems))
    # A sealed ledger row can never change, but the sqlite file keeps a mutable
    # shape while a RUNNING row still exists, so drift here is reported as its own
    # boolean rather than quietly folded into the byte gate above.
    ledger_now = sha_file(LEDGER_PATH) if LEDGER_PATH.is_file() else None
    ledger_matches = ledger_now == seal.get("ledger_sha256")
    return {"seal_path": _rel(path), "seal_sha256": sha_file(path),
            "seal_utc": seal.get("seal_utc"), "run_id": seal.get("run_id"),
            "sealed_task_results": seal.get("task_result_count"),
            "seal_document": seal, "sealed_bytes_verified": True,
            "ledger_sha256_at_seal": seal.get("ledger_sha256"),
            "ledger_sha256_at_validation": ledger_now,
            "ledger_sha_matches_seal": ledger_matches}


def ledger_recount() -> dict:
    """Read-only recount of the billing rows, independent of the controller."""
    require(LEDGER_PATH.is_file(), "VALIDATOR_REQUIRES_LEDGER")
    connection = sqlite3.connect("file:" + str(LEDGER_PATH).replace("\\", "/")
                                 + "?mode=ro", uri=True)
    try:
        tasks = connection.execute(
            "SELECT id, phase, cap, used, state FROM tasks ORDER BY id").fetchall()
        attempts = connection.execute(
            "SELECT task, state, COUNT(*) FROM attempts GROUP BY task, state "
            "ORDER BY task, state").fetchall()
    finally:
        connection.close()
    by_phase: dict[str, dict] = {}
    for task_id, phase, cap, used, state in tasks:
        bucket = by_phase.setdefault(str(phase), {"tasks": 0, "cap": 0, "used": 0})
        bucket["tasks"] += 1
        bucket["cap"] += int(cap)
        bucket["used"] += int(used)
    states: dict[str, int] = {}
    for task_id, state, count in attempts:
        states[str(state)] = states.get(str(state), 0) + int(count)
    used_total = sum(bucket["used"] for bucket in by_phase.values())
    return {"schema": "iscat167.ledger_recount.1", "ledger_path": _rel(LEDGER_PATH),
            "ledger_sha256": sha_file(LEDGER_PATH), "task_rows": len(tasks),
            "by_phase": by_phase, "attempt_states": states,
            "attempt_rows": sum(states.values()), "used_total": used_total,
            "budget_total": TOTAL, "budget_remaining": TOTAL - used_total,
            "cap_exceeded_phase": [phase for phase, bucket in by_phase.items()
                                   if bucket["used"] > ctrl.PHASES[phase]],
            "cap_exceeded_total": used_total > TOTAL, "model_calls": 0}


# ------------------------------------------------------------------------ truth read

def truth_access_receipt() -> dict:
    """One receipt naming exactly which truth objects this process opened."""
    raw = SEALED_TRUTH.read_bytes()
    own = sha_bytes(raw)
    require(own == SEALED_TRUTH_OWN_SHA256, "SEALED_TRUTH_OWN_SHA_CHANGED:" + own)
    truth = json.loads(raw.decode("utf-8-sig"))
    require(set(truth) == {"schema", "seed", "source_truth_sha256", "rows"},
            "SEALED_TRUTH_SHAPE:" + str(sorted(truth)))
    require(len(truth["rows"]) == 24, "SEALED_TRUTH_ROW_COUNT")
    readings_doc = read_json(READINGS)
    require(sha_file(READINGS) == ctrl.CONTRACT_PINS[
        "results/v166/height_input/height_readings.json"], "PUBLIC_READINGS_PIN_CHANGED")
    v142_sha = sha_file(V142_TRUTH)
    require(truth["source_truth_sha256"] == readings_doc["truth_file_sha256"] == v142_sha,
            "TRUTH_IDENTITY_CHAIN_BROKEN:" + str(truth["source_truth_sha256"]) + ":"
            + str(readings_doc["truth_file_sha256"]) + ":" + v142_sha)
    require(truth["seed"] == readings_doc["seed"], "TRUTH_SEED_NOT_THE_PUBLISHED_SEED")
    return {"schema": "iscat167.truth_access_receipt.1",
            "opened_only_after_seal": True,
            "sealed_truth_file": _rel(SEALED_TRUTH),
            "sealed_truth_own_sha256": own,
            "sealed_truth_rows": 24,
            "truth_field_that_the_public_table_publishes": "source_truth_sha256",
            "source_truth_sha256": truth["source_truth_sha256"],
            "public_readings_file": _rel(READINGS),
            "public_readings_sha256": sha_file(READINGS),
            "public_readings_declares_truth_file_sha256": readings_doc["truth_file_sha256"],
            "v142_truth_file": _rel(V142_TRUTH),
            "v142_truth_file_sha256": v142_sha,
            "identity_chain_verified": True,
            "seed": truth["seed"],
            "reading_hash_is_not_a_diameter_value": True,
            "v166_defect_carried_forward": {
                "public_readings_file_still_publishes_seed": True,
                "public_readings_file_still_publishes_truth_file_sha256": True,
                "paired_sigma_rows_were_visible_to_one_V166_process": True,
                "V167_estimator_projection": "one reading row only, single sigma, "
                                             "no h_scene, no D_scene, no epsilon",
                "not_claimed": "this round does not claim truth values were used by "
                               "the V166 estimators"},
            "model_calls": 0}


def truth_by_reading() -> tuple[dict[str, dict], dict]:
    receipt = truth_access_receipt()
    truth = json.loads(SEALED_TRUTH.read_bytes().decode("utf-8-sig"))
    return {str(row["reading_id"]): row for row in truth["rows"]}, receipt


def reverify_readings(truth_rows: dict[str, dict]) -> dict:
    """Re-derive the 24 published readings from the sealed truth, zero new draws."""
    public = {str(row["reading_id"]): row
              for row in read_json(READINGS)["readings"]}
    require(set(public) == set(truth_rows), "TRUTH_READING_ID_SET_DIFFERS")
    problems: list[str] = []
    worst_residual = 0.0
    worst_pairing = 0.0
    for reading_id, row in sorted(truth_rows.items()):
        spot = public[reading_id]
        for key in ("group", "B", "replicate", "sigma_nm"):
            if row[key] != spot[key]:
                problems.append(reading_id + ":key:" + key)
        if float(spot["z_nm"]) != float(row["z_nm"]):
            problems.append(reading_id + ":public_z_differs_from_sealed_truth")
        residual = abs(float(row["z_nm"])
                       - (float(row["h_scene_nm"]) + float(row["sigma_nm"])
                          * float(row["epsilon"])))
        worst_residual = max(worst_residual, residual)
        if residual > 1e-9:
            problems.append(reading_id + ":z_definition_residual:" + repr(residual))
    by_cell: dict[tuple[str, int], dict[float, dict]] = {}
    for row in truth_rows.values():
        by_cell.setdefault((str(row["group"]), int(row["replicate"])), {})[
            float(row["sigma_nm"])] = row
    for (group, replicate), pair in sorted(by_cell.items()):
        require(set(pair) == {1.0, 10.0}, "PAIR_SIGMAS:" + group + ":" + str(replicate))
        one, ten = pair[1.0], pair[10.0]
        if float(one["epsilon"]) != float(ten["epsilon"]):
            problems.append("paired_epsilon_shared:" + group + ":" + str(replicate))
        if float(one["h_scene_nm"]) != float(ten["h_scene_nm"]):
            problems.append("paired_h_scene_shared:" + group + ":" + str(replicate))
        if float(one["D_scene_nm"]) != float(ten["D_scene_nm"]):
            problems.append("paired_D_scene_shared:" + group + ":" + str(replicate))
        reconstructed = (10.0 * float(one["z_nm"]) - float(ten["z_nm"])) / 9.0
        deviation = abs(reconstructed - float(one["h_scene_nm"]))
        worst_pairing = max(worst_pairing, deviation)
        if deviation > 1e-9:
            problems.append("h_reconstruction:" + group + ":" + str(replicate)
                            + ":" + repr(deviation))
    scene_heights = {float(row["h_scene_nm"]) for row in truth_rows.values()}
    scene_diameters = {float(row["D_scene_nm"]): row["group"] for row in truth_rows.values()}
    epsilons = {float(row["epsilon"]) for row in truth_rows.values()}
    for group, expected in D_SCENE_BY_GROUP.items():
        got = {float(row["D_scene_nm"]) for row in truth_rows.values()
               if row["group"] == group}
        if got != {expected}:
            problems.append("group_D_scene_set:" + group + ":" + str(sorted(got)))
    return {"schema": "iscat167.reverification_24_rows.1",
            "rows_checked": len(truth_rows), "public_rows_checked": len(public),
            "z_definition": "z = h_scene + sigma * epsilon",
            "worst_z_definition_residual_nm": worst_residual,
            "pairing_identity": "h_scene = (10*z_sigma1 - z_sigma10) / 9",
            "worst_h_reconstruction_deviation_nm": worst_pairing,
            "independent_standard_normal_draws": len(epsilons),
            "distinct_scene_heights": len(scene_heights),
            "distinct_scene_diameters": sorted(scene_diameters),
            "scene_diameter_by_group": {value: key for key, value in
                                         scene_diameters.items()},
            "re_sampled_anything": 0, "new_random_draws": 0,
            "problems": problems, "all_rows_verified": not problems,
            "model_calls": 0}


def detection_status() -> dict:
    """Reuse the frozen V166 high-background detection; this round redrew nothing."""
    document = read_json(FROZEN_DETECTIONS)
    rows = {str(group): [bool(item) for item in values]
            for group, values in document.items()}
    require(set(rows) == set(common.GROUPS), "DETECTION_GROUP_SET")
    per_group = {group: {"frames_detected": sum(values), "per_frame": values,
                         "any_frame_detected": any(values)}
                 for group, values in sorted(rows.items())}
    return {"schema": "iscat167.frozen_detection_reuse.1",
            "source_file": _rel(FROZEN_DETECTIONS),
            "source_sha256": sha_file(FROZEN_DETECTIONS),
            "recomputed": False, "groups": per_group,
            "ANON_01_detection": "0/3 -- not detected; must not be reported as "
                                 "successful sizing",
            "model_calls": 0}


def _abs_error(candidate: Any, scene: Any) -> float | None:
    if candidate is None or scene is None or not common.finite_number(candidate):
        return None
    return abs(float(candidate) - float(scene))


def _mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


# ----------------------------------------------------------------------- new estimates

def new_task_rows(truth_rows: dict[str, dict], detections: dict,
                  seal: dict) -> tuple[list[dict], dict]:
    """Score every V167 task row, keeping unfinished and undetected rows in place."""
    estimates = read_json(OUT / "estimates_new.json")
    require(estimates["task_count"] == len(estimates["rows"]) == 23,
            "ESTIMATES_ROW_COUNT:" + str(estimates["task_count"]))
    sealed = seal["seal_document"]["task_result_sha256"]
    rows: list[dict] = []
    for item in estimates["rows"]:
        task_id = str(item["task_id"])
        source = str(item["source_task_id"])
        group = str(item["group"])
        truth = truth_rows.get(source)
        require(truth is not None, "TRUTH_ROW_MISSING:" + source)
        state = str(item["execution_state"])
        candidate_D = item.get("candidate_D_nm")
        detection = detections["groups"][group]
        scored = state == "FINISHED" and candidate_D is not None
        rows.append({
            "task_id": task_id, "kind": item["kind"], "phase": item["phase"],
            "source_task_id": source, "group": group, "replicate": item["replicate"],
            "sigma_nm": item["sigma_nm"], "B": item["B"],
            "controlled_offset_nm": item.get(
                "controlled_offset_nm_reported_controller_only"),
            "execution_state": state, "report_label": item.get("report_label"),
            "candidate_D_nm": candidate_D, "candidate_h_nm": item.get("candidate_h_nm"),
            "Q_total": item.get("Q_total"), "Q_model": item.get("Q_model"),
            "Q_height": item.get("Q_height"), "K": item.get("K"),
            "actual_calls": item.get("actual_calls"),
            "charged_replies": item.get("charged_replies"),
            "cache_hit_replies": item.get("cache_hit_replies"),
            "simulated_D_scene_nm": float(truth["D_scene_nm"]),
            "simulated_h_scene_nm": float(truth["h_scene_nm"]),
            "abs_D_error_nm": _abs_error(candidate_D, truth["D_scene_nm"]),
            "abs_h_error_nm": _abs_error(item.get("candidate_h_nm"),
                                         truth["h_scene_nm"]),
            "counts_in_scenario_MAE": scored,
            "detected_frame_count": detection["frames_detected"],
            "any_frame_detected": detection["any_frame_detected"],
            "physical_qualification": item.get("physical_qualification"),
            "global_uniqueness_certified": False,
            "known_compatible_D_interval_nm": None,
            "task_result_sha256": sha_file(OUT / "tasks" / task_id / "result.json"),
            "seal_task_result_sha256": sealed.get(task_id),
            "reportable_D": None,
            "scope": "OPENED_SIMULATED_DEV_NOT_REAL_SIZING",
        })
    states: dict[str, int] = {}
    for row in rows:
        states[row["execution_state"]] = states.get(row["execution_state"], 0) + 1
    errors = [row["abs_D_error_nm"] for row in rows if row["counts_in_scenario_MAE"]]
    summary = {"task_rows": len(rows), "state_counts": states,
               "scored_FINISHED_rows": len(errors),
               "descriptive_mean_abs_D_error_all_FINISHED_nm": _mean(errors),
               "unfinished_rows_kept": len(rows) - len(errors),
               "deleted_rows": 0}
    return rows, summary


# ------------------------------------------------------------------------ R supplement

def r_supplement_table(truth_rows: dict[str, dict], detections: dict) -> dict:
    """Section 8: the five warm completions as 原结果＋补充搜索, never a new baseline."""
    merge = read_json(CONTROL / "r_merge_table.json")
    require(merge["row_count"] == 5, "R_MERGE_ROW_COUNT:" + str(merge["row_count"]))
    rows: list[dict] = []
    for item in merge["rows"]:
        source = str(item["source_task_id"])
        truth = truth_rows[source]
        by_label = {str(row["label"]): row for row in item["candidates"]}
        group = str(item["group"])

        def pick(label: str) -> dict:
            row = by_label.get(label)
            if row is None:
                return {"present": False}
            return {"present": True, "D_nm": row["D_nm"], "h_nm": row["h_nm"],
                    "Q_total": row["Q_total"], "origin": row["origin"],
                    "abs_D_error_nm": _abs_error(row["D_nm"], truth["D_scene_nm"]),
                    "abs_h_error_nm": _abs_error(row["h_nm"], truth["h_scene_nm"]),
                    "physical_clearance_ok": row["physical_clearance_ok"]}

        merged = {"label": item["merged_pick"], "D_nm": item["merged_D_nm"],
                  "h_nm": item["merged_theta"][1], "Q_total": item["merged_Q_total"],
                  "abs_D_error_nm": _abs_error(item["merged_D_nm"],
                                               truth["D_scene_nm"]),
                  "abs_h_error_nm": _abs_error(item["merged_theta"][1],
                                               truth["h_scene_nm"])}
        rows.append({
            "task_id": item["task_id"], "source_task_id": source, "group": group,
            "replicate": item["replicate"], "sigma_nm": item["sigma_nm"],
            "simulated_D_scene_nm": float(truth["D_scene_nm"]),
            "old_execution_state": item["old_execution_state"],
            "old_execution_state_preserved": item["old_execution_state_preserved_verbatim"],
            "old_start_consumption": item["old_start_consumption"],
            "original_result": pick("v166_second_start_partial_best"),
            "v166_first_start_best": pick("v166_first_start_best"),
            "v166_legal_floor": pick("v166_legal_floor"),
            "new_supplementary_result": pick("v167_new_optimizer_best"),
            "new_legal_floor": pick("v167_new_legal_floor"),
            "merged_lowest_Q_total": merged,
            "delta_D_vs_original_nm": item["delta_D_vs_old_partial_nm"],
            "delta_Q_vs_original": item["delta_Q_vs_old_partial"],
            "delta_D_vs_v166_final_nm": item["delta_D_vs_v166_final_nm"],
            "search_state": item["search_state"],
            "actual_extra_budget_calls": item["new_actual_calls"],
            "charged_replies": item["new_charged_replies"],
            "cache_hit_replies": item["new_cache_hit_replies"],
            "detected_frame_count": detections["groups"][group]["frames_detected"],
            "all_old_ANON_01_candidates_kept": True,
            "selection_rule": item["selection_rule"],
            "reportable_D": None, "model_calls": 0,
        })
    finished = [row for row in rows if row["search_state"] == "SEARCH_COMPLETE_LOCAL_RETURN"]
    merged_errors = [row["merged_lowest_Q_total"]["abs_D_error_nm"] for row in rows
                     if row["merged_lowest_Q_total"]["abs_D_error_nm"] is not None]
    groups = sorted({row["group"] for row in rows})
    per_group: dict[str, dict] = {}
    for group in groups:
        subset = [row for row in rows if row["group"] == group]
        values = [row["merged_lowest_Q_total"]["abs_D_error_nm"] for row in subset
                  if row["merged_lowest_Q_total"]["abs_D_error_nm"] is not None]
        per_group[group] = {"planned": len(subset), "scored": len(values),
                            "mean_abs_D_error_nm": _mean(values),
                            "median_abs_D_error_nm": _median(values),
                            "complete": len(values) == len(subset),
                            "detected_frame_count":
                                detections["groups"][group]["frames_detected"]}
    four_group_statistic_available = False
    return {"schema": "iscat167.r_supplement.1",
            "table_label": LABEL_R_SUPPLEMENT,
            "rows": rows, "row_count": len(rows),
            "groups_covered": groups,
            "per_group_descriptive": per_group,
            "search_complete_count": len(finished),
            "search_incomplete_count": len(rows) - len(finished),
            "descriptive_mean_abs_D_error_merged_pick_nm": _mean(merged_errors),
            "descriptive_denominator": len(merged_errors),
            "v166_headline_H1_H10_four_group_MAE": None,
            "v166_headline_stays_null": True,
            "replaces_v166_main_baseline": False,
            "is_a_complete_four_group_statistic": four_group_statistic_available,
            "ANON_01_detection_unchanged": "0/3",
            "budget_authorisation": "SEARCH_EXTENSION cap 2000; five tasks x 400",
            "old_partial_tasks_rewritten": 0,
            "model_calls": 0, "reportable_D": None}


# ------------------------------------------------------------------ B bias directions

def _v166_baseline_design(row: dict) -> str:
    if row.get("reading_id") is None:
        return "NO_HEIGHT"
    return "H10" if float(row["sigma_nm"]) == 10.0 else "H1"


def baselines(truth_rows: dict[str, dict]) -> dict:
    """The b=0 and no-height columns come from V166 bytes; nothing here re-ran them."""
    rows = read_json(V166 / "estimates.json")
    require(len(rows) == 28, "V166_ESTIMATES_NOT_28")
    by_design: dict[str, dict[str, list[float]]] = {}
    per_source_D: dict[str, float] = {}
    for row in rows:
        design = _v166_baseline_design(row)
        source = str(row["task_id"])
        truth = truth_rows.get(source)
        candidate = row.get("candidate_D")
        if design != "NO_HEIGHT":
            require(truth is not None, "BASELINE_TRUTH_MISSING:" + source)
        if row["execution_state"] != "FINISHED" or candidate is None:
            continue
        if truth is None:
            scene = D_SCENE_BY_GROUP[str(row["group"])]
        else:
            scene = float(truth["D_scene_nm"])
        by_design.setdefault(design, {}).setdefault(str(row["group"]), []).append(
            abs(float(candidate) - scene))
        per_source_D[source] = float(candidate)
    blocks: dict[str, dict] = {}
    for design, groups in sorted(by_design.items()):
        per_group = {}
        for group, values in sorted(groups.items()):
            scene = D_SCENE_BY_GROUP[group]
            per_group[group] = {"n": len(values), "mean_abs_D_error_nm": _mean(values),
                                "median_abs_D_error_nm": _median(values),
                                "simulated_D_scene_nm": scene}
        expected_n = 3 if design != "NO_HEIGHT" else 1
        complete = all(item["n"] == expected_n for item in per_group.values())
        means = [item["mean_abs_D_error_nm"] for item in per_group.values()
                 if item["mean_abs_D_error_nm"] is not None]
        # ANON_01 is 0/3 detected and its height rows are not all complete, so the
        # four-group headline stays null; only the three detected groups can be
        # averaged, and only when all three of them really contributed.
        detected_present = [group for group in ctrl.DETECTED_GROUPS if group in per_group]
        three_complete = (len(detected_present) == len(ctrl.DETECTED_GROUPS)
                          and all(per_group[group]["n"] == expected_n
                                  for group in detected_present))
        blocks[design] = {
            "groups": per_group, "contributing_groups": sorted(per_group),
            "group_count": len(per_group),
            "expected_rows_per_group": expected_n,
            "four_group_MAE_nm": (_mean(means) if len(per_group) == 4 and complete
                                  else None),
            "three_detected_group_MAE_nm": (
                _mean([per_group[group]["mean_abs_D_error_nm"]
                       for group in detected_present]) if three_complete else None),
            "all_contributing_tasks_FINISHED": complete,
            "descriptive_equal_weight_MAE_nm": _mean(means),
            "scope": "DESCRIPTIVE_OPENED_DEVELOPMENT"}
    return {"schema": "iscat167.baselines_reused.1",
            "source_file": _rel(V166 / "estimates.json"),
            "source_sha256": sha_file(V166 / "estimates.json"),
            "re_ran_any_task": False, "model_calls": 0,
            "V166_design_blocks": blocks,
            "zero_bias_D_nm_by_source": per_source_D,
            "note": "H1 four-group headline stays null because ANON_01 is incomplete "
                    "and undetected; the three detected groups are reported separately"}


def bias_direction_table(truth_rows: dict[str, dict], base: dict,
                         detections: dict) -> dict:
    """Section 8: two report columns, both bias directions, failure denominators kept."""
    stress = read_json(CONTROL / "b_stress_table.json")
    require(stress["row_count"] == 18, "B_STRESS_ROW_COUNT:" + str(stress["row_count"]))
    cells: dict[tuple[str, int], dict[str, Any]] = {}
    witness_losses: list[str] = []
    for item in stress["rows"]:
        source = str(item["source_task_id"])
        truth = truth_rows[source]
        group, replicate = str(item["group"]), int(item["replicate"])
        offset = float(item["controlled_offset_nm"])
        require(offset in SCENARIOS, "B_OFFSET:" + repr(offset))
        require(group in detections["groups"], "B_GROUP_UNKNOWN:" + group)
        require(detections["groups"][group]["any_frame_detected"] is True,
                "B_GROUP_MUST_BE_A_DETECTED_GROUP:" + group)
        cell = cells.setdefault((group, replicate), {"group": group,
                                                     "replicate": replicate,
                                                     "source_task_id": source,
                                                     "simulated_D_scene_nm":
                                                         float(truth["D_scene_nm"]),
                                                     "zero_bias_D_nm":
                                                         float(item["zero_bias_reference_D_nm"]),
                                                     "offsets": {}})
        require(abs(cell["zero_bias_D_nm"]
                    - base["zero_bias_D_nm_by_source"].get(source,
                                                            cell["zero_bias_D_nm"])) < 1e-12,
                "ZERO_BIAS_BASELINE_DISAGREES:" + source)
        column_a = item["column_two_prescribed_starts_only_D_nm"]
        column_b = item["column_including_historical_witness_D_nm"]
        witness = item.get("historical_witness_rescored") or {}
        if item.get("historical_witness_rescore_error"):
            witness_losses.append(source + ":" + str(item["historical_witness_rescore_error"]))
        cell["offsets"][str(offset)] = {
            "task_id": item["task_id"], "execution_state": item["execution_state"],
            "report_label": item.get("report_label"), "search_state": item["search_state"],
            "actual_calls": item.get("actual_calls"),
            "charged_replies": item.get("charged_replies"),
            "cache_hit_replies": item.get("cache_hit_replies"),
            "column_A_D_nm": column_a,
            "column_A_abs_D_error_nm": _abs_error(column_a, truth["D_scene_nm"]),
            "column_A_Q_total": item["column_two_prescribed_starts_only_Q_total"],
            "column_B_D_nm": column_b,
            "column_B_abs_D_error_nm": _abs_error(column_b, truth["D_scene_nm"]),
            "column_B_Q_total": item["column_including_historical_witness_Q_total"],
            "new_legal_floor_D_nm": item.get("new_legal_floor_D_nm"),
            "historical_witness_rescored_D_nm": witness.get("theta", [None])[0],
            "historical_witness_rescored_Q_total": witness.get("Q_total"),
            "historical_witness_present": bool(witness),
            "witness_below_new_search": item.get("witness_below_new_search"),
            "sigma_nm": item["sigma_nm"],
            "reading_id": item["reading_id"],
            "reportable_D": None,
        }
    directions: list[dict] = []
    for (group, replicate), cell in sorted(cells.items()):
        minus = cell["offsets"].get("-2.0") or {}
        plus = cell["offsets"].get("2.0") or {}
        zero = cell["zero_bias_D_nm"]
        entry = {"group": group, "replicate": replicate, "source_task_id":
                 cell["source_task_id"], "D0_zero_bias_nm": zero,
                 "simulated_D_scene_nm": cell["simulated_D_scene_nm"],
                 "abs_D_error_at_zero_bias_nm": _abs_error(zero,
                                                           cell["simulated_D_scene_nm"]),
                 "detected_frame_count": detections["groups"][group]["frames_detected"],
                 "both_offsets_present": bool(minus) and bool(plus),
                 "reportable_D": None}
        for column in ("A", "B"):
            d_plus = plus.get("column_" + column + "_D_nm")
            d_minus = minus.get("column_" + column + "_D_nm")
            entry["column_" + column] = {
                "D_plus_2_nm": d_plus, "D_minus_2_nm": d_minus,
                "abs_error_plus_2_nm": plus.get("column_" + column + "_abs_D_error_nm"),
                "abs_error_minus_2_nm": minus.get("column_" + column + "_abs_D_error_nm"),
                "s_D_z_nm_per_nm": (None if d_plus is None or d_minus is None
                                    else (float(d_plus) - float(d_minus)) / 4.0),
                "c_D_nm": (None if d_plus is None or d_minus is None
                           else float(d_plus) + float(d_minus) - 2.0 * zero),
                "search_state_plus": plus.get("search_state"),
                "search_state_minus": minus.get("search_state"),
            }
        entry["direction_asymmetry_kept"] = True
        entry["s_D_z_and_c_D_are_discrete_differences_only"] = (
            "not a calibrated derivative, not a standard error, not a confidence interval")
        directions.append(entry)
    scenarios: dict[str, dict] = {}
    for offset in SCENARIOS:
        key = "b_%s" % ("minus_2" if offset < 0 else "plus_2")
        block: dict[str, Any] = {"controlled_offset_nm": offset, "columns": {}}
        blockers: list[str] = []
        for column in ("A", "B"):
            per_group: dict[str, dict] = {}
            values_all: list[float] = []
            denominators = 0
            for (group, replicate), cell in sorted(cells.items()):
                spot = cell["offsets"].get(str(offset)) or {}
                error = spot.get("column_" + column + "_abs_D_error_nm")
                state = spot.get("execution_state")
                present = error is not None
                if present:
                    values_all.append(error)
                    denominators += 1
                bucket = per_group.setdefault(group, {"planned": 0, "finished": 0,
                                                      "errors": []})
                bucket["planned"] += 1
                if state == "FINISHED" and present:
                    bucket["finished"] += 1
                    bucket["errors"].append(error)
            for group, bucket in per_group.items():
                bucket["mean_abs_D_error_nm"] = (_mean(bucket["errors"])
                                                 if len(bucket["errors"]) == 3 else None)
                bucket["median_abs_D_error_nm"] = _median(bucket["errors"])
                bucket["n_scored"] = len(bucket["errors"])
                bucket["incomplete"] = len(bucket["errors"]) != 3
                del bucket["errors"]
            group_means = [bucket["mean_abs_D_error_nm"] for bucket in per_group.values()]
            complete = (len(per_group) == len(ctrl.DETECTED_GROUPS)
                        and all(value is not None for value in group_means)
                        and not any(bucket["incomplete"] for bucket in per_group.values()))
            block["columns"][column] = {
                "per_group": per_group,
                "group_count": len(per_group),
                "primary_equal_weight_MAE_nm": (_mean(group_means) if complete else None),
                "primary_complete": complete,
                "descriptive_equal_weight_MAE_nm": _mean(
                    [value for value in group_means if value is not None]),
                "descriptive_task_denominator": denominators,
                "descriptive_mean_over_available_tasks_nm": _mean(values_all),
            }
        for (group, replicate), cell in sorted(cells.items()):
            spot = cell["offsets"].get(str(offset)) or {}
            if spot.get("execution_state") != "FINISHED":
                blockers.append("state:" + str(spot.get("task_id")) + ":"
                                + str(spot.get("execution_state")))
            if not spot.get("historical_witness_present"):
                blockers.append("witness:" + str(spot.get("task_id")))
        if witness_losses:
            blockers.append("witness_rescore_error:" + witness_losses[0])
        block["scenario_primary_null_because"] = blockers
        block["primary_MAE_null_for_both_columns"] = bool(blockers)
        block["readings_in_scenario"] = sum(
            1 for cell in cells.values() if str(offset) in cell["offsets"])
        block["independent_particles_in_scenario"] = len({
            cell["group"] for cell in cells.values() if str(offset) in cell["offsets"]})
        block["nine_readings_are_not_nine_particles"] = True
        block["Q_is_not_comparable_across_bias_scenarios"] = True
        scenarios[key] = block
    zero_bias_cells = [entry["abs_D_error_at_zero_bias_nm"] for entry in directions]
    return {"schema": "iscat167.bias_direction_table.1",
            "source_file": _rel(CONTROL / "b_stress_table.json"),
            "source_sha256": sha_file(CONTROL / "b_stress_table.json"),
            "cells": directions, "cell_count": len(directions),
            "scenarios": scenarios,
            "zero_bias_descriptive_mean_abs_D_error_nm": _mean(
                [value for value in zero_bias_cells if value is not None]),
            "deleted_samples": 0, "selected_by_true_error": 0,
            "sigma_nm_never_modified": True,
            "improvement_or_worsening_kept": "both directions reported verbatim",
            "model_calls": 0, "reportable_D": None}


# ------------------------------------------------------------------------- csv helpers

def _csv(header: list[str], rows: list[list[Any]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow(["" if item is None else item for item in row])
    return buffer.getvalue().encode("utf-8")


def _bias_csv(bias: dict) -> bytes:
    header = ["group", "replicate", "column", "D0_zero_bias_nm", "D_minus_2_nm",
              "D_plus_2_nm", "abs_err_zero", "abs_err_minus_2", "abs_err_plus_2",
              "s_D_z_nm_per_nm", "c_D_nm", "simulated_D_scene_nm",
              "detected_frame_count", "search_state_minus", "search_state_plus"]
    rows = []
    for cell in bias["cells"]:
        for column in ("A", "B"):
            block = cell["column_" + column]
            rows.append([cell["group"], cell["replicate"], column,
                         cell["D0_zero_bias_nm"], block["D_minus_2_nm"],
                         block["D_plus_2_nm"],
                         cell["abs_D_error_at_zero_bias_nm"],
                         block["abs_error_minus_2_nm"], block["abs_error_plus_2_nm"],
                         block["s_D_z_nm_per_nm"], block["c_D_nm"],
                         cell["simulated_D_scene_nm"], cell["detected_frame_count"],
                         block["search_state_minus"], block["search_state_plus"]])
    return _csv(header, rows)


def _r_csv(table: dict) -> bytes:
    header = ["task_id", "source_task_id", "group", "replicate", "sigma_nm",
              "old_execution_state", "original_D_nm", "original_abs_err_nm",
              "new_D_nm", "new_abs_err_nm", "merged_pick", "merged_D_nm",
              "merged_abs_err_nm", "delta_D_vs_original_nm", "search_state",
              "extra_budget_calls", "simulated_D_scene_nm"]
    rows = []
    for item in table["rows"]:
        original = item["original_result"]
        new = item["new_supplementary_result"]
        merged = item["merged_lowest_Q_total"]
        rows.append([item["task_id"], item["source_task_id"], item["group"],
                    item["replicate"], item["sigma_nm"], item["old_execution_state"],
                    original.get("D_nm"), original.get("abs_D_error_nm"),
                    new.get("D_nm"), new.get("abs_D_error_nm"), merged["label"],
                    merged["D_nm"], merged["abs_D_error_nm"],
                    item["delta_D_vs_original_nm"], item["search_state"],
                    item["actual_extra_budget_calls"], item["simulated_D_scene_nm"]])
    return _csv(header, rows)


# ------------------------------------------------------------------------------ driver

def score(dry_run: bool) -> dict:
    if dry_run:
        document = {"schema": "iscat167.scores.1", "run_id": None,
                    "status": "NOT_STARTED_DRY_RUN",
                    "scientific_scope": "dry rehearsal never opens the truth file",
                    "truth_read": False, "model_calls": 0,
                    "reportable_D": None,
                    "experimental_absolute_diameter_validated": False}
        # The rehearsal writes beside the primary evidence name, never onto it, so
        # the authorized run still owns results/v167/validator_only/v167_scores.json.
        written = _write(OUT / "dry_run" / "validator_only" / "v167_scores.json", document)
        document["artifacts"] = [written]
        return document

    gate = seal_gate()
    seal_doc = gate["seal_document"]
    truth_rows, receipt = truth_by_reading()
    reverification = reverify_readings(truth_rows)
    detections = detection_status()
    base = baselines(truth_rows)
    task_rows, rows_summary = new_task_rows(truth_rows, detections, gate)
    r_table = r_supplement_table(truth_rows, detections)
    bias = bias_direction_table(truth_rows, base, detections)
    ledger = ledger_recount()
    require(reverification["all_rows_verified"], "TRUTH_REVERIFICATION_FAILED")
    require(not reverification["problems"], "REVERIFICATION_PROBLEMS")

    states = rows_summary["state_counts"]
    finished = states.get("FINISHED", 0)
    status = ("SCORED_AFTER_SEAL" if finished == 23 else
              "PARTIALLY_SCORED_AFTER_SEAL" if finished else "NOTHING_SCORED")
    scope = ("opened simulated development scenes only: three detected groups under "
             "identical optical noise and paired hypothetical height readings; "
             "systematic-bias sensitivity, not a new blind test, not a validation of "
             "experimental height unbiasedness, and no claim that a real instrument "
             "reaches 1 nm height accuracy")
    artifacts: list[dict] = []
    written = _write(VAL / "v167_truth_access_receipt.json", receipt)
    artifacts.append(written)
    written = _write(VAL / "v167_reverification_24_rows.json", reverification)
    artifacts.append(written)
    written = _write(VAL / "v167_frozen_detection_reuse.json", detections)
    artifacts.append(written)
    written = _write(VAL / "v167_baselines_reused.json", base)
    artifacts.append(written)
    written = _write(VAL / "v167_ledger_recount.json", ledger)
    artifacts.append(written)
    written = _write(VAL / "v167_task_rows.json",
                     {"schema": "iscat167.task_rows.1", "rows": task_rows,
                      "row_count": len(task_rows), "summary": rows_summary,
                      "all_reportable_D_null": True, "model_calls": 0})
    artifacts.append(written)
    written = _write(VAL / "v167_r_supplement_table.json", r_table)
    artifacts.append(written)
    artifacts.append(_write(VAL / "v167_r_supplement_table.csv", _r_csv(r_table)))
    written = _write(VAL / "v167_bias_direction_table.json", bias)
    artifacts.append(written)
    artifacts.append(_write(VAL / "v167_bias_direction_table.csv", _bias_csv(bias)))

    document = {
        "schema": "iscat167.scores.1", "run_id": gate["run_id"],
        "status": status, "scientific_scope": scope,
        "scored_after_seal": True, "seal_status": seal_doc["status"],
        "seal_utc": gate["seal_utc"], "seal_sha256": gate["seal_sha256"],
        "sealed_bytes_verified": gate["sealed_bytes_verified"],
        "sealed_task_results": gate["sealed_task_results"],
        "truth_read_only_after_seal": True, "truth_access_receipt": receipt,
        "reverification_24_rows": reverification, "detection_status": detections,
        "task_execution_states": states, "tasks_total": len(task_rows),
        "r_tasks": 5, "b_tasks": 18, "row_summary": rows_summary,
        "baselines": base, "r_supplement": r_table, "bias_directions": bias,
        "ledger_recount": ledger,
        "budget_used_total": ledger["used_total"], "budget_total": TOTAL,
        "phase_caps": dict(ctrl.PHASES),
        "primary_scenario_MAE_nm": {
            "V166_NO_HEIGHT_four_group": base["V166_design_blocks"].get(
                "NO_HEIGHT", {}).get("four_group_MAE_nm"),
            "V166_H1_four_group": None,
            "V166_H10_four_group": None,
            "V166_H1_three_detected_groups_zero_bias": base["V166_design_blocks"].get(
                "H1", {}).get("three_detected_group_MAE_nm"),
            "V166_H10_three_detected_groups_zero_bias": base["V166_design_blocks"].get(
                "H10", {}).get("three_detected_group_MAE_nm"),
            "V167_b_minus_2_column_A": bias["scenarios"]["b_minus_2"]["columns"]["A"][
                "primary_equal_weight_MAE_nm"],
            "V167_b_plus_2_column_A": bias["scenarios"]["b_plus_2"]["columns"]["A"][
                "primary_equal_weight_MAE_nm"],
            "V167_b_minus_2_column_B": bias["scenarios"]["b_minus_2"]["columns"]["B"][
                "primary_equal_weight_MAE_nm"],
            "V167_b_plus_2_column_B": bias["scenarios"]["b_plus_2"]["columns"]["B"][
                "primary_equal_weight_MAE_nm"]},
        "four_group_headline_MAE_stays_null": True,
        "strict_blind_validation": False,
        "all_reportable_D_null": all(row["reportable_D"] is None for row in task_rows),
        "global_uniqueness_certified": False,
        "known_compatible_D_interval_nm": None,
        "confidence_intervals_certified": False,
        "experimental_absolute_diameter_validated": False,
        "model_calls": 0, "new_random_draws": 0, "new_bem": 0, "new_render": 0,
        "new_camera_exposures": 0, "v166_results_modified": 0,
        "artifacts": artifacts}
    written = _write(VAL / "v167_scores.json", document)
    document["artifacts"] = artifacts + [written]
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v167_validator",
                                     description="V167 post-seal truth scorer")
    parser.add_argument("--dry-run", action="store_true",
                        help="rehearsal only; the truth file is never opened")
    args = parser.parse_args(argv)
    document = score(dry_run=bool(args.dry_run))
    summary = {"status": document["status"], "run_id": document.get("run_id"),
               "tasks_total": document.get("tasks_total"),
               "task_execution_states": document.get("task_execution_states"),
               "model_calls": document["model_calls"],
               "all_reportable_D_null": document.get("all_reportable_D_null"),
               "primary_scenario_MAE_nm": document.get("primary_scenario_MAE_nm")}
    print("VALIDATOR " + json.dumps(summary, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
