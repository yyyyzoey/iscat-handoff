"""Regression tests for the two estimate tables the authorized round failed to publish.

On the single authorized V168 round the ``estimates`` step died with
``TypeError: Object of type ndarray is not JSON serializable`` while writing
``estimates_merge_reuse.json``, which blocked the seal and the independent score for the
whole round.  No test had ever called the real ``estimates_documents`` entry point, so the
suite passed 187 times around a crash that was waiting in production.  These tests drive
that real function with the real V166-derived zero-bias references, and hold the fix to
three demands at once: both tables must be publishable JSON, the published matrix must be
the same matrix the reference digest was taken over, and the scorer downstream must still
find the array in memory.  ``staged`` is the session context a dry-run ``prepare`` builds,
so every number here comes from pinned V166 evidence and no test bills a forward.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import numpy as np
import pytest

import v168_common as common
import v168_controller as controller

REAL_TASKS = controller.ROOT / "results" / "v168" / "tasks"
REAL_MERGE = controller.ROOT / "results" / "v168" / "controller_only" / "r_merge_table.json"


@pytest.fixture()
def probe_tree():
    """A throwaway results tree inside ROOT, removed again on teardown.

    ``_stage_json`` spells evidence paths relative to ROOT, so a probe outside the
    repository would fail for the wrong reason.  No primary evidence name under
    results/v168 is written here: a dry-run context lands under ``dry_run/<identity>/``.
    """
    parent = controller.ROOT / "results" / "v168" / "workstation_tests"
    parent.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="v168_est_", dir=str(parent)))
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=False)


def _ctx(staged, out: Path, monkeypatch) -> dict:
    """Point the writable controller paths at the probe tree; keep every real reference."""
    monkeypatch.setattr(controller, "OUT", out)
    monkeypatch.setattr(controller, "CONTROL", out / "controller_only")
    ctx = dict(staged)
    ctx["run_id"] = "v168-PROBE-ESTIMATES"
    return ctx


def _published(out: Path, ctx: dict, name: str) -> Path:
    identity = str(ctx["codes"]["identity_sha256"])[:12]
    return out / "dry_run" / identity / name


def _copy_task_results(out: Path, ctx: dict) -> int:
    """Stage the real result documents of the authorized round inside the probe tree."""
    copied = 0
    for entry in ctx["plan"]["entries"]:
        source = REAL_TASKS / str(entry["task_id"]) / "result.json"
        if not source.is_file():
            continue
        target = out / "tasks" / str(entry["task_id"]) / "result.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        copied += 1
    return copied


def _scan_arrays(value, path: str = "$") -> list[str]:
    """Every leaf that is still a numpy object, by JSON path."""
    if isinstance(value, np.ndarray) or isinstance(value, np.generic):
        return [path]
    if isinstance(value, dict):
        return [hit for key, item in value.items()
                for hit in _scan_arrays(item, path + "/" + str(key))]
    if isinstance(value, (list, tuple)):
        return [hit for index, item in enumerate(value)
                for hit in _scan_arrays(item, path + "/" + str(index))]
    return []


def test_both_estimate_tables_publish_as_json_with_no_numpy_left_inside(
        staged, probe_tree, monkeypatch):
    """The exact crash: a live reference matrix must never reach the evidence writer."""
    ctx = _ctx(staged, probe_tree, monkeypatch)
    assert _copy_task_results(probe_tree, ctx) == 23
    control = probe_tree / "controller_only"
    control.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REAL_MERGE, control / "r_merge_table.json")
    sources = sorted(ctx["refs"]["zero_bias"])
    assert sources, "NO_ZERO_BIAS_REFERENCE_TO_PUBLISH"

    receipt = controller.estimates_documents(ctx)

    new_path = _published(probe_tree, ctx, "estimates_new.json")
    merge_path = _published(probe_tree, ctx, "estimates_merge_reuse.json")
    assert new_path.is_file() and merge_path.is_file()
    assert receipt["estimates_new_sha256"] == common.sha_file(new_path)
    assert receipt["merge_reuse_sha256"] == common.sha_file(merge_path)
    # A reader must be able to parse what the round published, with no custom decoder.
    estimates = json.loads(new_path.read_bytes().decode("utf-8"))
    merge = json.loads(merge_path.read_bytes().decode("utf-8"))
    assert _scan_arrays(estimates) == _scan_arrays(merge) == []
    assert merge["zero_bias_reuse_count"] == len(sources)
    assert merge["r_merge_count"] == 5
    assert merge["v166_estimate_rows_rewritten"] == 0
    assert estimates["task_count"] == 23
    assert estimates["estimator_read_access"] is False
    assert estimates["reportable_D"] is None
    assert estimates["experimental_absolute_diameter_validated"] is False

    rows = {row["source_task_id"]: row for row in merge["zero_bias_reuse_rows"]}
    assert set(rows) == set(sources)
    for source in sources:
        reference = ctx["refs"]["zero_bias"][source]
        row = rows[source]
        published = np.asarray(row["prediction_C_array"], dtype=float)
        assert published.shape == tuple(row["prediction_C_shape"])
        # The published nested lists are the same numbers, not a re-explained copy.
        assert np.array_equal(published, np.asarray(reference["prediction_C_array"]))
        assert common.array_sha(published) == row["C_sha256"] == reference["C_sha256"]
        assert row["prediction_C_sha256_reverified"] is True
        assert row["identity"] == "ZERO_BIAS_REFERENCE_NOT_A_NEW_ESTIMATE"
        assert row["reuse_kind"] == "V166_SEALED_H1_FINAL_ANSWER"
    # Nothing published here is a new estimate, and nothing here is reportable.
    assert merge["model_calls"] == 0 and merge["reportable_D"] is None


def test_the_published_matrix_stays_available_to_the_scorer_as_an_array(
        staged, probe_tree, monkeypatch):
    """Guard the other half of the fix: ctx keeps the ndarray the bias witness needs."""
    ctx = _ctx(staged, probe_tree, monkeypatch)
    _copy_task_results(probe_tree, ctx)
    before = {source: np.asarray(reference["prediction_C_array"]).copy()
              for source, reference in ctx["refs"]["zero_bias"].items()}

    controller.estimates_documents(ctx)

    for source, array in before.items():
        kept = ctx["refs"]["zero_bias"][source]["prediction_C_array"]
        assert isinstance(kept, np.ndarray), (
            "THE_FIX_REMOVED_THE_IN_MEMORY_MATRIX_THE_SCORER_READS")
        assert np.array_equal(np.asarray(kept, dtype=float), array)
        assert kept.shape == (13, 13)


def test_a_reference_matrix_that_disagrees_with_its_own_digest_is_refused_unpublished(
        staged, probe_tree, monkeypatch):
    """The re-verification is a gate, not a label: a swapped matrix stops the step."""
    import copy

    ctx = _ctx(staged, probe_tree, monkeypatch)
    _copy_task_results(probe_tree, ctx)
    source = sorted(ctx["refs"]["zero_bias"])[0]
    refs = copy.deepcopy(ctx["refs"])
    tampered = np.asarray(refs["zero_bias"][source]["prediction_C_array"], dtype=float).copy()
    tampered[0][0] += 1.0e-6
    refs["zero_bias"][source]["prediction_C_array"] = tampered
    ctx["refs"] = refs

    with pytest.raises(ValueError) as refused:
        controller.estimates_documents(ctx)
    assert "ZERO_BIAS_REUSE_ARRAY_SHA:" + source in str(refused.value)
    assert not _published(probe_tree, ctx, "estimates_new.json").exists()
    assert not _published(probe_tree, ctx, "estimates_merge_reuse.json").exists()


def test_a_replayed_estimates_pass_reuses_the_published_bytes_instead_of_wedging(
        staged, probe_tree, monkeypatch):
    """An interruption between the two writes must be recoverable, byte for byte.

    Both tables used to go out through ``atomic_json``, which refuses an existing path even
    when it already holds the same document, so a resumed round could neither rewrite the
    table it had written nor lawfully remove it.
    """
    ctx = _ctx(staged, probe_tree, monkeypatch)
    _copy_task_results(probe_tree, ctx)
    first = controller.estimates_documents(ctx)
    bytes_before = {name: _published(probe_tree, ctx, name).read_bytes()
                    for name in ("estimates_new.json", "estimates_merge_reuse.json")}

    again = controller.estimates_documents(ctx)

    assert again == first
    for name, raw in bytes_before.items():
        assert _published(probe_tree, ctx, name).read_bytes() == raw


def test_a_half_written_pair_is_completed_by_the_replay_not_by_a_deletion(
        staged, probe_tree, monkeypatch):
    """Only one table on disk is a recoverable state, and the replay leaves both."""
    ctx = _ctx(staged, probe_tree, monkeypatch)
    _copy_task_results(probe_tree, ctx)
    controller.estimates_documents(ctx)
    merge_path = _published(probe_tree, ctx, "estimates_merge_reuse.json")
    merge_path.unlink()

    receipt = controller.estimates_documents(ctx)

    assert merge_path.is_file()
    assert receipt["merge_reuse_sha256"] == common.sha_file(merge_path)
    assert json.loads(merge_path.read_bytes().decode("utf-8"))["zero_bias_reuse_count"] == \
        len(ctx["refs"]["zero_bias"])


def test_estimates_without_a_task_result_row_say_not_started_and_publish_nothing_false(
        staged, probe_tree, monkeypatch):
    """An empty tree keeps all 23 tasks in the denominator as NOT_STARTED."""
    ctx = _ctx(staged, probe_tree, monkeypatch)

    receipt = controller.estimates_documents(ctx)

    estimates = json.loads(_published(probe_tree, ctx, "estimates_new.json")
                           .read_bytes().decode("utf-8"))
    assert receipt["task_count"] == 23
    assert estimates["state_counts"] == {"NOT_STARTED": 23}
    assert all(row["execution_state"] == "NOT_STARTED" for row in estimates["rows"])
    assert all(row["reportable_D"] is None for row in estimates["rows"])
    assert json.loads(_published(probe_tree, ctx, "estimates_merge_reuse.json")
                      .read_bytes().decode("utf-8"))["r_merge_count"] == 0
