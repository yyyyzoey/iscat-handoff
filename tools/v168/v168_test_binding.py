"""Contract section 7: the workstation test receipt that is allowed to authorize a run.

Section 7 closes three shortcuts V167 fell into.  Its release receipt was built by a module
that only exercises strategy *functions* and never runs pytest; a receipt recorded against
another generation's suite was reused as if it were current; and the pin pointed at a bundle
document nobody had run.  So this module binds the real workflow receipt written by
``run_workstation_tests.py``, re-collects the production node IDs here and now instead of
trusting a recorded count, re-hashes every source file the workflow hashed against the
delivered code identity, and proves the four scenarios and twelve camera images behind the
twelve height readings from the pinned V166 evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

import v168_common as common
import v168_controller as controller

require = common.require
sha_file = common.sha_file
read_json = common.read_json
canon = common.canon

WORKFLOW_SCHEMA = "iscat168.workstation_tests.1"
RELEASE_SCHEMA = "iscat168.workstation_test_release.1"
WORKFLOW_NAME = "workstation_test_receipt.json"
RELEASE_NAME = "workstation_test_release_receipt.json"
WORKSTATION_TESTS_DIR = controller.OUT / "workstation_tests"
PRODUCTION_SUITE = "v168_production"
# The V166 inventory is run by the driver that owns its receipt rules, so its evidence
# shape is different and only this suite may use the collector-list inventory.
INHERITED_SUITE = "v166_inherited_41"

# A receipt of any of these kinds describes a suite that never ran, or ran other bytes.
# V167 billed its one charged model call against the first two; the last two are prior
# generations' workstation receipts, which are real evidence for a different suite.
FORBIDDEN_RECEIPTS = {
    "iscat168.production_test_execution.1": "STRATEGY_FUNCTIONS_ONLY_NO_PYTEST",
    "v166.test_execution_receipt.1": "STRATEGY_FUNCTIONS_ONLY_NO_PYTEST",
    "iscat165.workstation_tests.1": "RECEIPT_FROM_OTHER_GENERATION",
    "iscat167.workstation_tests.1": "RECEIPT_FROM_OTHER_GENERATION",
}

SCENARIO_GROUPS = ("ANON_01", "ANON_02", "ANON_03", "ANON_04")
FRAMES_PER_GROUP = 3
V166_PROVENANCE = "results/v166/p5_report/provenance_scenarios_and_images.json"
V166_DETECTIONS = "results/v166/frozen_detections.json"

# The release fields the capsule freeze reads out of verify().  Naming them here, beside the
# verifier that returns them, is what keeps the freeze and its stubs from drifting: the first
# V168 freeze attempt died on KeyError('git_head') because that key lived in the release
# document but not in verify()'s return, and a list hand-copied into the controller and the
# tests could not see the difference.
FREEZE_RELEASE_KEYS = ("receipt_sha256", "workflow_run_id", "workflow_receipt_sha256",
                       "total_tests_recorded", "suite_count", "code_identity_sha256",
                       "test_suite_sha256", "scenario_count", "camera_image_count")
# Fields compared against the live tree rather than copied into the capsule.
FREEZE_COMPARED_KEYS = ("git_head", "code_identity_sha256", "test_suite_sha256")


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _rel(path: Path) -> str:
    """Repo-relative POSIX path, so an evidence file name is stable across machines."""
    return Path(path).resolve().relative_to(controller.ROOT).as_posix()


def _digest(value) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else canon(value)).hexdigest()


def rows_digest(rows: list[str]) -> str:
    """The one node-ID list digest that both the recorded inventory and a fresh
    re-collection are compared with, whatever shape the evidence file has."""
    return _digest(list(rows))


def _self_digest(document: dict) -> str:
    return _digest({key: value for key, value in document.items() if key != "receipt_sha256"})


def workflow_path(run_id: str) -> Path:
    return WORKSTATION_TESTS_DIR / run_id / WORKFLOW_NAME


def release_path(run_id: str) -> Path:
    return WORKSTATION_TESTS_DIR / run_id / RELEASE_NAME


def read_workflow(path: Path) -> dict:
    """Load the workflow receipt, refusing every kind section 7 forbids.

    The refusal is on the schema the workflow wrote, not on a file name: strategy receipts
    sit in reachable directories with plausible names, and a prior generation's workstation
    receipt is honest evidence about a suite that is not this one.
    """
    require(path.is_file(), "WORKSTATION_TEST_RECEIPT_MISSING:" + str(path))
    require(path.name == WORKFLOW_NAME, "WORKSTATION_TEST_RECEIPT_WRONG_NAME:" + path.name)
    require(path.parent.parent == WORKSTATION_TESTS_DIR,
            "WORKSTATION_TEST_RECEIPT_OUTSIDE_EVIDENCE_DIR:" + str(path.parent))
    document = read_json(path)
    schema = str(document.get("schema", ""))
    if schema in FORBIDDEN_RECEIPTS:
        raise ValueError("WORKSTATION_TEST_RECEIPT_REFUSED:" + FORBIDDEN_RECEIPTS[schema]
                         + ":" + schema)
    require(schema == WORKFLOW_SCHEMA, "TEST_RECEIPT_NOT_VERIFIED:" + schema)
    require(str(document.get("contract_reference", "")).startswith("section 3"),
            "TEST_RECEIPT_CONTRACT_REFERENCE:" + str(document.get("contract_reference")))
    require("LOCAL_TEST_INVENTORY_ONLY" in str(document.get("scope", "")),
            "TEST_RECEIPT_SCOPE:" + str(document.get("scope"))[:200])
    require(int(document.get("total_tests_recorded", 0)) > 0, "TEST_RECEIPT_NO_TESTS")
    require(bool(document.get("all_suites_green")), "WORKSTATION_TESTS_NOT_PASS")
    require(bool(document.get("zero_charged_calls_proved")), "TEST_SUITES_BILLED_MODEL_CALLS")
    require(bool(document.get("source_hashes_unchanged")), "SOURCE_HASHES_MOVED_DURING_TESTS")
    tripwire = document.get("real_f2c_tripwire") or {}
    require(int(tripwire.get("real_construction_attempts", -1)) == 0,
            "TEST_SUITES_REACHED_REAL_MODEL:" + json.dumps(tripwire)[:300])
    suites = document.get("suites")
    require(isinstance(suites, list) and len(suites) == 3,
            "TEST_RECEIPT_SUITE_COUNT:" + str(len(suites or [])))
    recorded = document.get("suite_receipt_sha256") or {}
    for index in range(len(suites)):
        name = f"suite_{index:02d}_receipt.json"
        bound = path.parent / name
        require(bound.is_file(), "SUITE_RECEIPT_MISSING:" + name)
        require(recorded.get(f"suite_{index:02d}") == sha_file(bound),
                "SUITE_RECEIPT_SHA_UNBOUND:" + name)
        suite = read_json(bound)
        require(bool(suite.get("all_green")), "SUITE_NOT_GREEN:" + name)
        require(int(suite.get("returncode", -1)) == 0, "SUITE_RETURN_CODE:" + name)
    return document


def _suite_dir(path: Path, suite: dict) -> Path:
    rel = str(suite.get("suite_dir") or "")
    require(rel, "SUITE_DIR_NOT_RECORDED:" + str(suite.get("suite")))
    resolved = (controller.ROOT / rel).resolve()
    require(str(path.parent.resolve()) in str(resolved), "SUITE_DIR_OUTSIDE_EVIDENCE:" + rel)
    require(resolved.is_dir(), "SUITE_DIR_MISSING:" + rel)
    return resolved


def _check_rows(rows: list[str], where: str) -> None:
    require(bool(rows), "NODEID_INVENTORY_EMPTY:" + where)
    require(rows == sorted(rows), "NODEID_INVENTORY_UNSORTED:" + where)
    require(len(set(rows)) == len(rows), "NODEID_INVENTORY_DUPLICATES:" + where)
    require(all("::" in row for row in rows), "NODEIDS_NOT_ITEM_INVENTORY:" + where)


def _collected_rows(path: Path) -> tuple[list[str], dict]:
    """The collector list and per-phase reports inside the inherited driver's outcomes file.

    Suite 0 is run by the V165 driver, which predates this module and writes no
    ``nodeids.txt`` and no JUnit XML.  Its own outcomes document is still a real pytest
    artifact: the recorder plugin puts the collector list in ``collected`` and one row per
    phase in ``reports``, so the inventory is read from there rather than invented.
    """
    found = sorted(path.rglob("pytest_outcomes.json"))
    require(len(found) == 1, "INHERITED_OUTCOMES_COUNT:"
                            + ",".join(str(row) for row in found))
    document = read_json(found[0])
    require(isinstance(document.get("collected"), list),
            "INHERITED_NO_COLLECTOR_LIST:" + str(found[0]))
    rows = sorted({str(row["nodeid"]) for row in document["reports"]})
    collected = sorted(str(row) for row in document["collected"])
    require(len(document.get("collection_errors") or []) == 0, "INHERITED_COLLECTION_ERRORS")
    return collected, {"outcome_file": found[0], "reported": rows}


def _inventory(path: Path, suite: dict | None = None) -> dict:
    """The real node ID list: sorted, distinct, and re-read from the recorded evidence.

    Two evidence shapes have to be honoured.  A suite this driver ran itself leaves a
    re-collected ``nodeids.txt``; the inherited V166 suite leaves only its recorder's
    outcomes file, and its node IDs are then taken from the collector list that file
    already pins by SHA.
    """
    found = sorted(p for p in path.rglob("nodeids.txt"))
    if found:
        require(len(found) == 1, "NODEID_INVENTORY_COUNT:" + ",".join(str(p) for p in found))
        rows = [line.strip() for line in found[0].read_text(encoding="utf-8").splitlines()
                if line.strip()]
        _check_rows(rows, found[0].name)
        return {"nodeids": rows, "count": len(rows), "source": "nodeids.txt",
                "inventory_sha256": sha_file(found[0]), "inventory_path": _rel(found[0]),
                "nodeids_digest": rows_digest(rows)}
    # No node ID file: only the inherited suite is allowed to reach this branch.
    require(str((suite or {}).get("suite")) == INHERITED_SUITE,
            "NODEID_INVENTORY_MISSING:" + str(path))
    collected, extra = _collected_rows(path)
    _check_rows(collected, "pytest_outcomes.json")
    outcomes = extra["outcome_file"]
    require(sha_file(outcomes) == ((suite or {}).get("inherited_outcomes") or {})
            .get("outcomes_sha256"), "INHERITED_OUTCOMES_SHA_UNBOUND")
    require(extra["reported"] == collected, "INHERITED_REPORTED_NOT_COLLECTED")
    return {"nodeids": collected, "count": len(collected), "source": "pytest_outcomes.json",
            "inventory_sha256": sha_file(outcomes), "inventory_path": _rel(outcomes),
            "nodeids_digest": rows_digest(collected)}


def _outcomes(path: Path) -> dict:
    """Per-test results from whichever channel the suite really wrote, plus error text."""
    junits = sorted(p for p in path.rglob("junit.xml"))
    if junits:
        require(len(junits) == 1, "JUNIT_COUNT")
        # Damaged XML has to be a named refusal: this channel is read in front of model
        # authority, and a bare parser traceback is not evidence that can be reported.
        try:
            root = ET.parse(junits[0]).getroot()
        except ET.ParseError as exc:
            raise ValueError("JUNIT_UNPARSEABLE:" + _rel(junits[0]) + ":" + str(exc)[:200])
        cases = list(root.iter("testcase"))
        states = []
        problems = []
        for case in cases:
            for tag in ("failure", "error", "skipped"):
                child = case.find(tag)
                if child is not None:
                    states.append(tag if tag != "skipped" else "skipped")
                    problems.append({"nodeid": f"{case.get('classname')}.{case.get('name')}",
                                     "kind": tag,
                                     "text": ((child.text or child.get("message") or "")
                                              .strip())[:600]})
                    break
            else:
                states.append("passed")
        counts = {state: states.count(state) for state in sorted(set(states))}
        return {"channel": "junit", "channel_sha256": sha_file(junits[0]),
                "items": len(cases), "counts": counts,
                "passed": counts.get("passed", 0), "problems": problems}
    recorded = sorted(p for p in path.rglob("pytest_outcomes.json"))
    require(recorded, "NO_PER_TEST_OUTCOME_CHANNEL:" + str(path))
    require(len(recorded) == 1, "OUTCOMES_CHANNEL_COUNT:"
                                + ",".join(str(row) for row in recorded))
    document = read_json(recorded[0])
    rows = document.get("reports")
    if rows is None:
        rows = [{"nodeid": row.get("nodeid"), "outcome": row["phases"]["call"].get("outcome")}
                for row in document["tests"]]
    counts: dict[str, int] = {}
    problems = []
    for row in rows:
        outcome = str(row.get("outcome", "unknown"))
        counts[outcome] = counts.get(outcome, 0) + 1
        if outcome not in ("passed",):
            problems.append({"nodeid": str(row.get("nodeid")), "kind": outcome,
                             "text": str(row.get("longrepr", ""))[:600]})
    return {"channel": "outcomes", "channel_sha256": sha_file(recorded[0]),
            "items": len({str(row.get("nodeid")) for row in rows}), "counts": counts,
            "passed": counts.get("passed", 0), "problems": problems}


def _streams(path: Path) -> dict:
    """Every captured console stream, so a complete error log is packable."""
    rows = {}
    for stream in ("stdout", "stderr"):
        for file in sorted(path.rglob(f"*.{stream}.txt")):
            rows[_rel(file)] = {"sha256": sha_file(file),
                                      "bytes": file.stat().st_size}
    require(rows, "NO_CAPTURED_STREAMS:" + str(path))
    return rows


def _recollect(target: str) -> dict:
    """Contract 7: the node IDs are collected again now, never copied from the receipt."""
    # The nested collection must never write: if a recorder or tripwire path is inherited
    # from the calling shell, the child session would overwrite primary test evidence with
    # an empty collection-only document.  Those variables are stripped here, not in pytest.
    env = {key: value for key, value in os.environ.items()
           if key not in ("V168_PYTEST_OUTCOMES", "V168_REAL_CALL_TRIPWIRE",
                          "V165_PYTEST_OUTCOMES", "V165_REAL_CALL_TRIPWIRE",
                          "PYTEST_ADDOPTS")}
    env.update({"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
                "MKL_NUM_THREADS": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                "PYTHONDONTWRITEBYTECODE": "1"})
    result = subprocess.run([sys.executable, "-X", "utf8", "-m", "pytest", target,
                             "--collect-only", "-q", "-p", "no:cacheprovider"],
                            cwd=str(controller.ROOT), capture_output=True, env=env)
    require(result.returncode == 0,
            "NODEID_RECOLLECTION_FAILED:" + target + ":"
            + result.stderr.decode("utf-8", "replace")[-500:])
    rows = sorted(line.strip() for line in
                  result.stdout.decode("utf-8", "replace").splitlines() if "::" in line)
    require(rows, "NODEID_RECOLLECTION_EMPTY:" + target)
    return {"target": target, "count": len(rows), "nodeids_sha256": rows_digest(rows)}


def source_binding(document: dict, codes: dict) -> dict:
    """Bind the receipt to the bytes under test, file by file.

    ``source_hashes_after`` is the workflow's own list of code the three inventories could
    read. Each file is re-hashed here and compared both with that record and, where the file
    is part of the delivered identity, with the identity, so neither a shortened file list
    nor an edit made after the run can pass.
    """
    rows = {}
    for rel, recorded in sorted((document.get("source_hashes_after") or {}).items()):
        path = controller.ROOT / rel
        require(path.is_file(), "BOUNDED_SOURCE_MISSING:" + rel)
        actual = sha_file(path)
        require(actual == recorded, "BOUNDED_SOURCE_SHA:" + rel)
        in_identity = rel in codes["files"]
        if in_identity:
            require(codes["files"][rel]["sha256"] == actual, "BOUNDED_SOURCE_CODE_IDENTITY:" + rel)
        rows[rel] = {"sha256": actual, "in_code_identity": in_identity}
    require(rows, "SOURCE_BINDING_EMPTY")
    production = sorted(rel for rel in rows if rel.startswith("tools/v168/")
                        and not rel.startswith("tools/v168/tests/"))
    require(production, "SOURCE_BINDING_HAS_NO_PRODUCTION_MODULE")
    return {"bound_file_count": len(rows), "production_files": production,
            "files": rows, "code_identity_sha256": codes["identity_sha256"]}


def input_provenance() -> dict:
    """The four scenarios and the twelve existing camera images behind the twelve readings.

    Read-only on pinned V166 evidence.  The camera file is re-hashed and its SHA must equal
    this round's contract pin and the SHA recorded inside the provenance document; the frame
    table must hold twelve rows, three per group; each group's legal records must name the
    same three camera events; and the detection table must still say ANON_01 0/3.
    """
    config = read_json(controller.ROOT / "config" / "v146_science_config.json")
    camera = controller.ROOT / config["inputs"]["camera_h5"]
    require(camera.is_file(), "CAMERA_FILE_MISSING:" + str(camera))
    camera_sha = sha_file(camera)
    require(camera_sha == controller.FROZEN_CAMERA_SHA256, "CAMERA_H5_BYTES_CHANGED")

    provenance_path = controller.ROOT / V166_PROVENANCE
    require(provenance_path.is_file(), "V166_PROVENANCE_MISSING")
    provenance = read_json(provenance_path)
    frames = provenance.get("camera_frames") or []
    require(len(frames) == 12, "CAMERA_FRAME_COUNT:" + str(len(frames)))
    require(str(provenance["camera"]["camera_h5_sha256"]) == camera_sha,
            "PROVENANCE_CAMERA_SHA")
    by_group: dict[str, list[str]] = {}
    for row in frames:
        by_group.setdefault(str(row["group"]), []).append(str(row["event_id"]))
    require(sorted(by_group) == list(SCENARIO_GROUPS),
            "SCENARIO_GROUPS:" + ",".join(sorted(by_group)))

    detections = read_json(controller.ROOT / V166_DETECTIONS)
    require(sorted(detections) == list(SCENARIO_GROUPS), "DETECTION_GROUPS")
    scenarios = {}
    for group in SCENARIO_GROUPS:
        events = by_group[group]
        require(len(events) == FRAMES_PER_GROUP and len(set(events)) == FRAMES_PER_GROUP,
                "FRAMES_PER_GROUP:" + group + ":" + json.dumps(events))
        hits = detections[group]
        require(isinstance(hits, list) and len(hits) == FRAMES_PER_GROUP,
                "DETECTION_LENGTH:" + group)
        if group == "ANON_01":
            require(sum(1 for hit in hits if hit) == 0, "ANON_01_MUST_STAY_UNDETECTED")
        else:
            require(sum(1 for hit in hits if hit) == FRAMES_PER_GROUP,
                    "DETECTED_GROUP_LOST_DETECTIONS:" + group)
        source = controller.V166 / "source_context" / (group + ".json")
        require(source.is_file(), "SOURCE_CONTEXT_MISSING:" + group)
        _data, _identity, frames_sha = common.frames_from_document(
            read_json(source), where="test_binding:" + group)
        records = controller.legal_records_document(group)["records"]
        named = sorted({str(row["ordered_event_ids"]) for row in records})
        require(len(named) == 1, "LEGAL_RECORD_EVENT_SET:" + group)
        require(sorted(json.loads(named[0].replace("'", '"'))) == sorted(events),
                "LEGAL_RECORD_EVENTS_VS_CAMERA_IMAGES:" + group)
        scenarios[group] = {
            "source_context_path": _rel(source),
            "source_context_sha256": sha_file(source),
            "git_blob_sha256": controller.git_blob_at_parent(
                "results/v166/source_context/" + group + ".json"),
            "frames_sha256": frames_sha, "frame_count": FRAMES_PER_GROUP,
            "camera_event_ids": sorted(events), "detections": hits,
            "detected_count": sum(1 for hit in hits if hit)}
    return {"schema": "iscat168.input_provenance.1", "scenario_count": len(SCENARIO_GROUPS),
            "camera_image_count": len(frames),
            "camera_h5": {"path": _rel(camera), "sha256": camera_sha},
            "v166_provenance_document": {"path": V166_PROVENANCE,
                                         "sha256": sha_file(provenance_path)},
            "v166_detections_document": {"path": V166_DETECTIONS,
                                         "sha256": sha_file(controller.ROOT / V166_DETECTIONS)},
            "scenarios": scenarios, "model_calls": 0, "new_random_draws": 0,
            "wrote_inside_v166": False}


def _suite_rows(workflow: dict, path: Path, codes: dict) -> list[dict]:
    rows = []
    for index, summary in enumerate(workflow["suites"]):
        suite = read_json(path.parent / f"suite_{index:02d}_receipt.json")
        directory = _suite_dir(path, suite)
        inventory = _inventory(directory, suite)
        outcomes = _outcomes(directory)
        recorded = int(suite.get("tests") or 0)
        require(recorded == inventory["count"],
                "SUITE_TEST_COUNT_VS_INVENTORY:" + str(suite.get("suite"))
                + ":" + str(recorded) + "!=" + str(inventory["count"]))
        require(outcomes["items"] == inventory["count"],
                "SUITE_OUTCOME_ITEMS_VS_INVENTORY:" + str(suite.get("suite")))
        require(not outcomes["problems"],
                "SUITE_HAS_UNHANDLED_PROBLEMS:" + str(suite.get("suite"))
                + ":" + json.dumps(outcomes["problems"][:2])[:600])
        row = {"index": index, "suite": str(suite.get("suite")),
               "suite_dir": str(directory.relative_to(controller.ROOT).as_posix()),
               "receipt_sha256": sha_file(path.parent / f"suite_{index:02d}_receipt.json"),
               "returncode": int(suite["returncode"]),
               "python_version": str(suite.get("python_version")),
               "command": [str(part) for part in (suite.get("command") or [])],
               "inventory": {key: value for key, value in inventory.items()
                             if key != "nodeids"},
               "nodeids_sample": inventory["nodeids"][:2],
               "outcomes": {"channel": outcomes["channel"],
                            "channel_sha256": outcomes["channel_sha256"],
                            "items": outcomes["items"], "counts": outcomes["counts"]},
               "error_log_streams": _streams(directory),
               "recollection": {}}
        if row["suite"] == PRODUCTION_SUITE:
            target = str(suite.get("target") or "tools/v168/tests")
            again = _recollect(target)
            require(again["count"] == inventory["count"],
                    "RECOLLECTED_NODEID_COUNT:" + json.dumps(again))
            require(again["nodeids_sha256"] == inventory["nodeids_digest"],
                    "RECOLLECTED_NODEID_SET:" + json.dumps(again))
            row["recollection"] = again
        rows.append(row)
    require(any(row["suite"] == PRODUCTION_SUITE for row in rows),
            "PRODUCTION_SUITE_ABSENT_FROM_RECEIPT")
    return rows


def build(run_id: str) -> dict:
    """Write the release receipt for one recorded workstation test run."""
    path = workflow_path(run_id)
    workflow = read_workflow(path)
    target = release_path(run_id)
    require(not target.exists(), "RELEASE_RECEIPT_ALREADY_EXISTS:" + str(target))
    codes = controller.code_identities()
    release = {"schema": RELEASE_SCHEMA, "receipt_kind": "WORKSTATION_TEST_RELEASE",
               "generated_at": _utc(), "workflow_run_id": run_id,
               "workflow_receipt_path": _rel(path),
               "workflow_receipt_sha256": sha_file(path),
               "workflow_schema": workflow["schema"],
               "total_tests_recorded": int(workflow["total_tests_recorded"]),
               "all_suites_green": True, "zero_charged_calls_proved": True,
               "real_f2c_constructions_during_tests": 0,
               "budget_state_after": workflow.get("budget_state_after"),
               "git_head": codes["git_head"],
               "code_identity_sha256": codes["identity_sha256"],
               "code_file_count": int(codes["file_count"]),
               "test_suite_sha256": controller.test_suite_sha256(),
               "source_binding": source_binding(workflow, codes),
               "input_provenance": input_provenance(),
        "suites": _suite_rows(workflow, path, codes),
               "refused_receipt_kinds": FORBIDDEN_RECEIPTS,
               "scope": ("These inventories exercise the guard, loader, planning and "
                         "persistence logic on real pytest runs. They do not validate "
                         "experimental absolute diameter accuracy, and they are not the "
                         "authorized V168 fit."),
               "model_calls": 0}
    release["receipt_sha256"] = _self_digest(release)
    common.atomic_json(target, release)
    verify(run_id, codes=codes)
    return release


def find_run_ids() -> list[str]:
    return sorted(p.parent.name for p in WORKSTATION_TESTS_DIR.glob("*/" + RELEASE_NAME))


def verify(run_id: str | None = None, *, codes: dict | None = None) -> dict:
    """Re-verify a release receipt against the bytes and evidence on disk right now.

    This runs before any model authority.  A receipt from another generation, a rewritten
    workflow document, a moved source file, or a node ID list that no longer re-collects
    identically all stop the round here instead of billing against stale evidence.
    """
    if run_id is None:
        found = find_run_ids()
        require(len(found) == 1, "WORKSTATION_RELEASE_RECEIPT_COUNT:" + ",".join(found))
        run_id = found[0]
    path = release_path(run_id)
    require(path.is_file(), "WORKSTATION_TEST_RELEASE_RECEIPT_MISSING:" + str(path))
    release = read_json(path)
    require(str(release.get("schema")) == RELEASE_SCHEMA,
            "RELEASE_RECEIPT_SCHEMA:" + str(release.get("schema")))
    require(_self_digest(release) == release.get("receipt_sha256"), "RELEASE_RECEIPT_SELF_DIGEST")
    workflow_file = controller.ROOT / str(release["workflow_receipt_path"])
    require(workflow_file == workflow_path(run_id), "WORKFLOW_RECEIPT_PATH:" + str(workflow_file))
    require(sha_file(workflow_file) == release["workflow_receipt_sha256"],
            "WORKFLOW_RECEIPT_SHA_CHANGED")
    workflow = read_workflow(workflow_file)
    codes = codes or controller.code_identities()
    require(release["code_identity_sha256"] == codes["identity_sha256"],
            "CODE_CHANGED_AFTER_TESTS:" + str(release["code_identity_sha256"])
            + "!=" + codes["identity_sha256"])
    require(release["test_suite_sha256"] == controller.test_suite_sha256(),
            "FROZEN_TEST_SUITE_CHANGED_BEFORE_RESERVE")
    require(release["git_head"] == codes["git_head"], "RELEASE_RECEIPT_GIT_HEAD")
    require(release["code_file_count"] == int(codes["file_count"]), "RELEASE_CODE_FILE_COUNT")
    source_binding(workflow, codes)
    for index, row in enumerate(release["suites"]):
        suite_path = workflow_file.parent / f"suite_{index:02d}_receipt.json"
        require(sha_file(suite_path) == row["receipt_sha256"],
                "SUITE_RECEIPT_SHA_CHANGED:" + str(row["suite"]))
        suite = read_json(suite_path)
        require(int(row["index"]) == index and str(suite.get("suite")) == str(row["suite"]),
                "SUITE_ROW_ORDER:" + str(row["suite"]))
        directory = controller.ROOT / row["suite_dir"]
        inventory = _inventory(directory, suite)
        require({key: value for key, value in inventory.items() if key != "nodeids"}
                == row["inventory"], "NODEID_INVENTORY_CHANGED:" + str(row["suite"]))
        # The claimed count is re-checked here as well as in build(): a suite receipt that
        # says "38" over an inventory of 39 is a stale claim, and verify() is the gate that
        # actually stands in front of model authority.
        require(int(suite.get("tests") or 0) == inventory["count"],
                "SUITE_TEST_COUNT_VS_INVENTORY:" + str(row["suite"]) + ":"
                + str(suite.get("tests")) + "!=" + str(inventory["count"]))
        outcomes = _outcomes(directory)
        require(outcomes["channel_sha256"] == row["outcomes"]["channel_sha256"],
                "OUTCOME_CHANNEL_SHA:" + row["suite"])
        require(outcomes["counts"] == row["outcomes"]["counts"],
                "OUTCOME_COUNTS:" + row["suite"])
        require(not outcomes["problems"],
                "SUITE_HAS_UNHANDLED_PROBLEMS:" + str(row["suite"]) + ":"
                + json.dumps(outcomes["problems"][:2])[:600])
        require(_streams(directory) == row["error_log_streams"],
                "ERROR_LOG_STREAMS:" + row["suite"])
        if row["suite"] == PRODUCTION_SUITE:
            require(row["recollection"], "PRODUCTION_RECOLLECTION_NOT_RECORDED")
            again = _recollect(row["recollection"]["target"])
            require(again == row["recollection"], "RECOLLECTION_NOT_REPRODUCIBLE:"
                    + json.dumps(again)[:300])
    provenance = input_provenance()
    require(canon(provenance) == canon(release["input_provenance"]), "INPUT_PROVENANCE_CHANGED")
    gate = {"schema": "iscat168.workstation_test_verify.1", "path": str(path),
            "receipt_sha256": release["receipt_sha256"], "workflow_run_id": run_id,
            "workflow_receipt_sha256": release["workflow_receipt_sha256"],
            "total_tests_recorded": release["total_tests_recorded"],
            "suite_count": len(release["suites"]),
            "git_head": release["git_head"],
            "code_identity_sha256": codes["identity_sha256"],
            "test_suite_sha256": release["test_suite_sha256"],
            "scenario_count": provenance["scenario_count"],
            "camera_image_count": provenance["camera_image_count"],
            "WORKSTATION_TEST_RECEIPT_SCHEMA": WORKFLOW_SCHEMA,
            "WORKSTATION_TEST_RECEIPT_VERIFIED": True, "WORKSTATION_TESTS_PASS": True,
            "CODE_BINDING_VERIFIED": True, "INPUT_PROVENANCE_VERIFIED": True,
            "refused_receipt_kinds": FORBIDDEN_RECEIPTS, "model_calls": 0}
    # A gate that hands the freeze an incomplete shape has to fail here, on the way out of
    # verification, and not as a KeyError minutes later inside a billed round's preamble.
    absent = [key for key in FREEZE_RELEASE_KEYS + FREEZE_COMPARED_KEYS if key not in gate]
    require(not absent, "VERIFY_RESULT_MISSING_FREEZE_KEYS:" + ",".join(absent))
    return gate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", metavar="WORKFLOW_RUN_ID")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)
    if args.build:
        release = build(args.build)
        print(json.dumps({"built": release["receipt_sha256"],
                          "total_tests_recorded": release["total_tests_recorded"]}, indent=1))
        return 0
    if args.verify:
        print(json.dumps(verify(), indent=1, sort_keys=True))
        return 0
    parser.error("either --build WORKFLOW_RUN_ID or --verify")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
