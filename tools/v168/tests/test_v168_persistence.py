"""V168 P1 persistence tests: replay, refusal and the litter a refused write leaves.

Three defects stopped the first rehearsal at the bind step.  The witness receipt was
written with a write-new-only writer, so a replayed bind refused instead of accepting
its own identical bytes; a rehearsal could occupy the primary evidence name that the
authorized run needs; and a refused write abandoned a ``.tmp.<pid>`` file beside the
evidence.  These tests drive the real writers and the real V166 witness tree.  The
F2c model stays behind the session tripwire, so nothing here spends budget.
"""
from __future__ import annotations

from pathlib import Path

import v168_common as common
import v168_controller as controller
import v168_service as service_mod


def _litter(directory):
    return sorted(str(item) for item in directory.rglob("*.tmp.*") if item.is_file())


def test_a_refused_atomic_write_leaves_no_staging_litter(tmp_path):
    path = tmp_path / "evidence.json"
    common.atomic_json(path, {"schema": "t.1", "value": 1})

    try:
        common.atomic_json(path, {"schema": "t.1", "value": 2})
    except common.FatalPersistenceError as exc:
        assert "OUTPUT_PATH_ALREADY_EXISTS" in str(exc)
    else:
        raise AssertionError("REFUSED_OVERWRITE_DID_NOT_RAISE")

    assert _litter(tmp_path) == []
    assert common.read_json(path) == {"schema": "t.1", "value": 1}


def test_replay_json_accepts_only_its_own_bytes(tmp_path):
    path = tmp_path / "receipt.json"
    digest, first = common.replay_json(path, {"schema": "t.1", "value": 1})
    assert (first, digest) == (False, common.sha_file(path))

    digest_again, replayed = common.replay_json(path, {"schema": "t.1", "value": 1})
    assert (replayed, digest_again) == (True, digest)

    try:
        common.replay_json(path, {"schema": "t.1", "value": 999})
    except common.FatalPersistenceError as exc:
        assert "REPLAY_BYTES_DIFFER" in str(exc)
    else:
        raise AssertionError("CHANGED_BYTES_WERE_NOT_REFUSED")

    assert _litter(tmp_path) == []
    assert common.read_json(path) == {"schema": "t.1", "value": 1}


def test_a_replayed_bind_imports_the_same_v166_witnesses_to_the_same_receipt(tmp_path):
    """Two fresh processes over the published V166 tree must not fork a second receipt."""
    out = tmp_path / "service_out"
    out.mkdir(parents=True)
    log = out / "logs" / "v166_witness_import.json"
    v166_root, v166_ledger = controller.PARENT_WS, controller.V166 / "logs" / "v165_budget.sqlite"

    first = service_mod.PredictionService(service_mod.make_store(tmp_path / "a.sqlite"), out=out)
    summary_one = first.import_v166_predictions(v166_root, v166_ledger, log_path=log)
    second = service_mod.PredictionService(service_mod.make_store(tmp_path / "b.sqlite"), out=out)
    summary_two = second.import_v166_predictions(v166_root, v166_ledger, log_path=log)

    assert summary_one["receipt_replayed_byte_identical"] is False
    assert summary_two["receipt_replayed_byte_identical"] is True
    assert summary_two["receipt_sha256"] == summary_one["receipt_sha256"]
    assert summary_two["distinct_theta_imported"] == summary_one["distinct_theta_imported"] > 0
    # Contract section 0 pins 4,937 published attempts, of which the 70 V166 loader
    # self-check predictions carry the v131 field id rather than the F2c model id.  They
    # are refused on model identity, never silently accepted.
    assert summary_one["documents_seen"] == summary_two["documents_seen"] == 4937
    assert summary_one["refused"] == summary_two["refused"] == 70
    assert all(row["reason"] == "ValueError:MODEL_ID" and "LOADER_1" in row["path"]
               for row in summary_one["refused_examples"])
    assert sorted((out / "logs").glob("v166_witness_import_*.json")) == []
    assert _litter(out) == []


def test_a_dry_run_bind_writes_its_witness_receipt_outside_the_primary_name(staged):
    """The rehearsal may not burn the name the authorized run has to sign with."""
    primary = common.OUT / "logs" / "v166_witness_import.json"
    before = primary.read_bytes() if primary.is_file() else None

    report = controller.bind_model(staged)

    assert report["status"] == "NOT_STARTED_DRY_RUN"
    assert report["model_calls"] == 0
    receipt = Path(staged["service"].import_summary["receipt_path"])
    assert receipt.is_relative_to(common.OUT / "dry_run" / staged["codes"]["identity_sha256"][:12])
    assert receipt != primary
    if before is not None:
        assert primary.read_bytes() == before
    assert _litter(receipt.parent) == []
