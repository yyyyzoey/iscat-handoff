"""V167 P1 production test: a worker sees one reading and its own group's frames.

These are workstation tests against the real staged jails produced by the real
controller prepare step.  They assert facts about bytes on disk, and one of them
starts the real worker subprocess in probe mode so that the access refusals are
recorded by the guard itself rather than asserted by the test author.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

import v167_common as common
import v167_controller as controller
import v167_jail as jail
import v167_runner as runner

from conftest import JAIL_ROOT

THREE_FILES = ["frames.json", "input.json", "legal_records.json"]
BANNED_JAIL_FILENAMES = ("height_readings", "plan.json", "source_mapping",
                         "task_signatures", "budget.sqlite", "truth", "validator",
                         "estimates", "seed")


def rows(staged) -> list[dict]:
    return staged["staging"]["mapping"]["tasks"]


def _reading_shaped_objects(value, found=None):
    """Every dict whose key set equals the seven published reading keys."""
    if found is None:
        found = []
    if isinstance(value, dict):
        if set(value) == set(common.READING_KEYS):
            found.append(value)
        for child in value.values():
            _reading_shaped_objects(child, found)
    elif isinstance(value, list):
        for child in value:
            _reading_shaped_objects(child, found)
    return found


def test_prepare_staged_exactly_the_authorized_23_tasks(staged):
    assert staged["dry_run"] is True
    assert len(rows(staged)) == 23
    kinds = [row["kind"] for row in rows(staged)]
    assert kinds.count("SEARCH_EXTENSION") == 5
    assert kinds.count("BIAS_STRESS") == 18
    mapping = staged["staging"]["mapping"]
    assert mapping["model_calls"] == 0
    assert mapping["new_random_draws"] == 0
    assert mapping["v166_height_file"]["read_by_controller_only"] is True
    assert mapping["plan"]["read_by_controller_only"] is True


@pytest.mark.parametrize("row_index", range(23), ids=[str(i) for i in range(23)])
def test_jail_holds_exactly_three_files(staged, row_index):
    row = rows(staged)[row_index]
    jail_dir = JAIL_ROOT / row["task_id"]
    present = sorted(path.name for path in jail_dir.iterdir() if path.is_file())
    assert present == THREE_FILES, row["task_id"]
    assert row["jail_files"] == THREE_FILES
    for name in present:
        for banned in BANNED_JAIL_FILENAMES:
            assert banned not in name, (row["task_id"], name)


def test_payload_carries_one_single_reading_document(staged):
    for row in rows(staged):
        payload = common.read_json(JAIL_ROOT / row["task_id"] / "input.json")
        assert set(payload) == set(common.PAYLOAD_KEYS), row["task_id"]
        assert set(payload["reading"]) == set(common.READING_KEYS)
        assert payload["task_id"] == row["task_id"]
        assert payload["reading"]["reading_id"] == row["task_id"]
        assert payload["group"] == row["group"]
        assert payload["B"] == 100000
        assert payload["schema"] == "iscat167.one_task.1"
        assert payload["scope"] == "OPENED_DEV_NOT_BLIND_NOT_EXPERIMENT"
        # The V166 defect was two sigma rows in one task document.
        assert len(_reading_shaped_objects(payload)) == 1, row["task_id"]
        assert common.scan_forbidden(payload, row["task_id"]) == []
        # A payload cannot name a sibling reading: its only reading id is its own.
        assert json.dumps(payload).count(str(payload["reading"]["sigma_nm"])) >= 1
        assert len({d["sigma_nm"] for d in _reading_shaped_objects(payload)}) == 1


def test_no_jail_document_contains_a_truth_or_controller_key(staged):
    for row in rows(staged):
        for name in THREE_FILES:
            document = common.read_json(JAIL_ROOT / row["task_id"] / name)
            offenders = common.scan_forbidden(document, row["task_id"] + "." + name)
            assert offenders == [], (row["task_id"], name, offenders)


def test_paired_table_and_generator_metadata_stay_controller_only(staged):
    document = json.loads((common.V166 / "height_input" / "height_readings.json")
                          .read_text(encoding="utf-8"))
    assert len(document["readings"]) == 24
    assert {"seed", "truth_file_sha256", "sigma_nm"} <= set(document)
    assert document["seed"] not in ("", None)
    public = controller.public_readings()
    assert len(public) == 24
    staged_text = []
    for row in rows(staged):
        for name in THREE_FILES:
            staged_text.append((JAIL_ROOT / row["task_id"] / name).read_text(encoding="utf-8"))
    blob = "\n".join(staged_text)
    assert str(document["seed"]) not in blob
    assert str(document["truth_file_sha256"]) not in blob
    assert "height_readings" not in blob
    assert str(controller.PLAN_PATH) not in blob
    assert "truth_file_sha256" not in blob
    # The plan and the 24-row table themselves must not sit under the jail root.
    stray = [str(path) for path in JAIL_ROOT.rglob("*")
             if path.is_file() and path.parent.name.startswith("V167_")
             and path.name not in THREE_FILES]
    assert stray == []


def _scalars(value, found=None):
    """Every scalar anywhere inside a document, for exact-value leak checks."""
    if found is None:
        found = []
    if isinstance(value, dict):
        for child in value.values():
            _scalars(child, found)
    elif isinstance(value, list):
        for child in value:
            _scalars(child, found)
    else:
        found.append(value)
    return found


def test_bias_payload_reveals_neither_zero_bias_value_nor_sibling_bias(staged):
    public = controller.public_readings()
    by_source: dict[str, list[dict]] = {}
    for row in rows(staged):
        by_source.setdefault(row["source_task_id"], []).append(row)
    biased = {source: group for source, group in by_source.items()
              if group[0]["kind"] == "BIAS_STRESS"}
    assert len(biased) == 9
    for source, pair in biased.items():
        assert len(pair) == 2, source
        zero = float(public[source]["z_nm"])
        offsets = sorted(float(row["controlled_offset_nm"]) for row in pair)
        assert offsets == [-2.0, 2.0], (source, offsets)
        projected = sorted(float(row["reading_projection"]["z_nm"]) for row in pair)
        assert projected == [zero - 2.0, zero + 2.0], (source, projected)
        assert projected[1] - projected[0] == 4.0
        for row, value in zip(sorted(pair, key=lambda r: r["reading_projection"]["z_nm"]),
                              projected):
            payload = common.read_json(JAIL_ROOT / row["task_id"] / "input.json")
            assert payload["reading"]["z_nm"] == value
            text = json.dumps(payload)
            assert repr(zero) not in text
            assert repr(projected[0] if value == projected[1] else projected[1]) not in text
            numbers = [item for item in _scalars(payload) if isinstance(item, (int, float))]
            numbers = [item for item in numbers if not isinstance(item, bool)]
            # Neither the un-biased value nor the sibling scenario's biased value.
            assert zero not in numbers, row["task_id"]
            other = projected[1] if value == projected[0] else projected[0]
            assert other not in numbers, row["task_id"]
            start_values = [float(v) for group in payload["starts"] for v in group]
            extra = [item for item in numbers if type(item) is float
                     and float(item) not in start_values
                     and item not in (payload["reading"]["z_nm"],
                                      payload["reading"]["sigma_nm"])]
            # Outside the prescribed starts the only floats a worker may hold are its
            # own biased z and its own sigma: that rules out the controlled offset,
            # the sibling row and any other scenario number reaching the estimator.
            assert extra == [], (row["task_id"], extra)


def test_extension_payloads_reuse_the_frozen_reading_without_a_redraw(staged):
    public = controller.public_readings()
    extended = [row for row in rows(staged) if row["kind"] == "SEARCH_EXTENSION"]
    assert len(extended) == 5
    assert {row["group"] for row in extended} == {"ANON_01"}
    for row in extended:
        source = public[row["source_task_id"]]
        payload = common.read_json(JAIL_ROOT / row["task_id"] / "input.json")
        # Same source reading, byte-identical value: no new Gaussian draw in V167.
        assert payload["reading"]["z_nm"] == source["z_nm"]
        assert payload["reading"]["sigma_nm"] == source["sigma_nm"]
        assert payload["reading"]["replicate"] == source["replicate"]
        assert payload["reading"]["group"] == source["group"]
        assert row["old_public_reading_reference"]["reading_id"] == row["source_task_id"]
        assert row["controlled_offset_nm"] is None
        assert len(payload["starts"]) == 1


def test_estimator_code_never_imports_controller_or_validator_modules():
    forbidden = {"v167_controller", "v167_service", "v167_runner", "v167_validator",
                 "v167_plan", "run_all", "v166_controller", "v166_production",
                 "v165_validator", "v165_io", "v165_run"}
    for name in common.ESTIMATOR_CODE_FILES:
        path = common.ROOT / "tools" / "v167" / name
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        assert not (imported & forbidden), (name, sorted(imported & forbidden))
    # The guard's own deny list must still name every controller-only module.
    for module in ("v167_controller", "v167_service", "v167_runner", "v167_validator",
                   "v167_plan", "run_all"):
        assert module in jail.DENIED_MODULE_PREFIXES


def test_guard_denies_the_controller_paths_a_worker_might_try(tmp_path, monkeypatch):
    """Decision table for the same function the audit hook calls, in-process."""
    root = tmp_path
    own_jail = root / "results" / "v167" / "estimator_inputs" / "V167_EX"
    own_task = root / "results" / "v167" / "tasks" / "V167_EX"
    validator_truth = root / "results" / "v165" / "validator_only" / "truth.json"
    height_table = root / "results" / "v166" / "height_input" / "height_readings.json"
    plan = root / "results" / "v167_prepared" / "controller_only" / "plan.json"
    sibling = root / "results" / "v167" / "estimator_inputs" / "V167_OTHER" / "input.json"
    own_jail.mkdir(parents=True)
    # Same normalisation install() applies, so the table tests the shipped logic.
    def roots(items):
        return tuple(sorted(os.path.normcase(os.path.abspath(str(p))) for p in items))

    monkeypatch.setattr(jail, "READ_OK", roots((own_jail, own_task)))
    monkeypatch.setattr(jail, "WRITE_OK", roots((own_task,)))
    monkeypatch.setattr(jail, "DENIED_READ", roots((plan,)))
    jail.LOG.clear()

    jail._check_path("open", str(own_jail / "input.json"), write=False)
    jail._check_path("open", str(own_task / "starts" / "000.json"), write=True)
    jail._check_path("open", str(own_task / "best" / "start_000_pass_01.json"),
                     write=False)
    for target in (validator_truth, height_table, plan, sibling):
        with pytest.raises(common.JailViolation):
            jail._check_path("open", str(target), write=False)
    # Readable is not writable: the worker may not write into its own input jail.
    with pytest.raises(common.JailViolation):
        jail._check_path("open", str(own_jail / "notes.json"), write=True)
    reasons = [entry["reason"] for entry in jail.LOG]
    assert reasons.count("DENIED_CONTROLLER_ONLY_SOURCE") == 1
    assert reasons.count("OUTSIDE_ALLOW_LIST") == 4


def test_guard_denies_with_the_real_production_allow_list(staged, monkeypatch):
    """Same roots the worker itself installs, applied to the real controller files."""
    row = rows(staged)[0]
    jail_dir = JAIL_ROOT / row["task_id"]
    task_dir = common.OUT / "tasks" / row["task_id"]
    denied = tuple(sorted(os.path.normcase(os.path.abspath(str(
        common.ROOT / "tools" / "v167" / name)))
        for name in common.CONTROLLER_ONLY_CODE_FILES if name != "v167_rpc.py"))
    allowed = tuple(sorted(os.path.normcase(os.path.abspath(str(p))) for p in (
        jail_dir, task_dir, common.ROOT / "tools" / "v167", common.APPROVED_CORE,
        common.PAYLOAD_GATE)))
    monkeypatch.setattr(jail, "READ_OK", allowed)
    monkeypatch.setattr(jail, "WRITE_OK", (os.path.normcase(os.path.abspath(str(task_dir))),))
    monkeypatch.setattr(jail, "DENIED_READ", denied)
    jail.LOG.clear()

    own = {"input.json", "frames.json", "legal_records.json"}
    assert own == {p.name for p in jail_dir.iterdir()}
    for name in sorted(own):
        jail._check_path("open", str(jail_dir / name), write=False)
    # The 24-row paired table, the plan, the mapping, the old truth and the ledger.
    controller_targets = (
        common.V166 / "height_input" / "height_readings.json",
        controller.PLAN_PATH,
        controller.CONTROL / "source_mapping.json",
        controller.CONTROL / "task_signatures.json",
        controller.LEDGER_PATH,
        common.V166 / "estimates.json",
        common.OUT / "validator_only" / "v167_scores.json",
        common.ROOT / "results" / "v165" / "validator_only" / "v166_height_truth_sealed.json",
        common.ROOT / "tools" / "v167" / "v167_service.py",
        common.ROOT / "tools" / "v167" / "v167_validator.py",
        common.ROOT / "tools" / "v167_bundle" / "config" / "v167_plan.json",
    )
    for target in controller_targets:
        with pytest.raises(common.JailViolation):
            jail._check_path("open", str(target), write=False)
    denial_reasons = [entry["reason"] for entry in jail.LOG]
    assert denial_reasons.count("DENIED_CONTROLLER_ONLY_SOURCE") == 2
    assert denial_reasons.count("OUTSIDE_ALLOW_LIST") == len(controller_targets) - 2
    assert task_dir not in jail_dir.parents


def test_real_worker_subprocess_refuses_every_forbidden_target(staged):
    """The guard refuses with JailViolation, proven by the production worker."""
    row = rows(staged)[6]
    report = runner.probe_task(task_id=row["task_id"])
    assert report["exit_code"] == 0, report["stderr"][-1500:]
    probe = report["probe_report"]
    assert probe is not None, report["stderr"][-1500:]
    assert probe["refusal_count"] == len(probe["attempted"]) + 3
    # Any entry carrying "|ExceptionName" is a refusal for the wrong reason.
    wrong_reason = [item for item in probe["refused"] if "|" in item
                    and not item.startswith("LIST:")]
    assert wrong_reason == []
    listed_wrong = [item for item in probe["refused"]
                    if item.startswith("LIST:") and "|" in item]
    assert listed_wrong == []
    refused = {Path(str(item)).name for item in probe["refused"]}
    assert {"plan.json", "estimates.json", "v165_budget.sqlite",
            "v166_height_truth_sealed.json", "v167_service.py",
            "v167_controller.py", "v167_plan.json", "input.json"} <= refused
    assert len(probe["guard_log"]) >= probe["refusal_count"]
    assert all(entry["reason"] in ("DENIED_CONTROLLER_ONLY_SOURCE", "OUTSIDE_ALLOW_LIST",
                                   "DENIED_EVENT") for entry in probe["guard_log"])
    assert "model_calls" not in json.dumps(probe) or probe.get("model_calls") in (None, 0)
import ast
import json
import os
from pathlib import Path
