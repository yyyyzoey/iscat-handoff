"""Contract 7 tests: the workstation test receipt that is allowed to authorize a run.

Two different things are being tested here and the file keeps them apart.  The refusal,
re-hash, re-collect and tamper tests run against a *synthetic* evidence tree that is built
to the exact schema ``run_workstation_tests.py`` writes: it is a fixture for the guard, not
a test result, and it is written under a ``v168_tb_*`` probe directory that is removed at
teardown.  The provenance tests, and the node ID inventory of the production suite, are
real evidence read from the repository as it stands.  The genuine V168 workstation run is
recorded separately by that driver into ``results/v168/workstation_tests`` and is never
substituted by this file.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import v168_common as common
import v168_controller as controller
import v168_test_binding as binding

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_workstation_tests as workflow_driver  # noqa: E402

PROBE_PREFIX = "v168_tb_"
RUN_ID = "probe_run_001"
# One small real production file: the re-collect guard must run the real collector, so the
# production suite in the synthetic tree points at an inventory that can be collected twice
# with an identical result in about a second.
PRODUCTION_TARGET = "tools/v168/tests/test_v168_persistence.py"
BUNDLE_TARGET = "tools/v168_bundle/tests"
WORKFLOW_SCOPE = ("LOCAL_TEST_INVENTORY_ONLY: synthetic forwards and plan guards, "
                  "NOT physical validation and NOT the authorized V168 fit")
ZERO_MARKER = "ZERO_REAL_F2C_MODEL_CONSTRUCTION_ATTEMPTS"


def _collect_rows(target: str, cwd: Path = controller.ROOT) -> list[str]:
    """Real pytest collection for one target, used to build a schema-exact inventory."""
    result = subprocess.run([sys.executable, "-X", "utf8", "-m", "pytest", target,
                             "--collect-only", "-q", "-p", "no:cacheprovider"],
                            cwd=str(cwd), capture_output=True)
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")[-800:]
    return sorted(line.strip() for line in
                  result.stdout.decode("utf-8", "replace").splitlines() if "::" in line)


def _junit(rows: list[str]) -> str:
    cases = "".join('<testcase classname="{0}" name="{1}"/>'.format(
        re.sub(r"[^0-9A-Za-z_.]", "_", row.split("::")[0]),
        re.sub(r"[^0-9A-Za-z_.\-]", "_", "::".join(row.split("::")[1:]))) for row in rows)
    return ('<?xml version="1.0" encoding="utf-8"?>'
            f'<testsuites tests="{len(rows)}" failures="0" errors="0">'
            f'<testsuite tests="{len(rows)}" failures="0" errors="0" skipped="0">'
            + cases + "</testsuite></testsuites>")


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _streams(suite_dir: Path, stem: str) -> None:
    _write(suite_dir / (stem + ".stdout.txt"), "collected inventory\n")
    _write(suite_dir / (stem + ".stderr.txt"), "")


def _pytest_suite(name: str, run_dir: Path, directory_name: str, rows: list[str],
                  *, target: str, stem: str) -> dict:
    """One ordinary suite: a collector list, a JUnit channel and captured streams."""
    suite_dir = run_dir / directory_name
    suite_dir.mkdir(parents=True, exist_ok=True)
    _write(suite_dir / "nodeids.txt", "".join(row + "\n" for row in sorted(rows)))
    _write(suite_dir / "junit.xml", _junit(rows))
    _streams(suite_dir, stem)
    return {"suite": name, "returncode": 0, "all_green": True, "tests": len(rows),
            "python_version": sys.version, "command": ["pytest", "-q", target],
            "suite_dir": (run_dir / directory_name).relative_to(controller.ROOT).as_posix(),
            "target": target}


def _set_inventory(run_dir: Path, directory_name: str, rows: list[str]) -> None:
    """Replace one suite's recorded inventory and its outcome channel together."""
    suite_dir = run_dir / directory_name
    _write(suite_dir / "nodeids.txt", "".join(row + "\n" for row in sorted(rows)))
    _write(suite_dir / "junit.xml", _junit(rows))


def _inherited_suite(run_dir: Path, rows: list[str]) -> dict:
    """The V166 suite: the driver that owns it leaves no nodeids.txt and no JUnit XML."""
    inner = run_dir / "v166_inherited_41" / "v165_driver"
    reports = [{"nodeid": row, "when": when, "outcome": "passed"} for row in rows
               for when in ("setup", "call", "teardown")]
    outcomes = _write(inner / "pytest_outcomes.json", json.dumps(
        {"schema": "v165_receipt_plugin", "exitstatus": 0, "collected": rows,
         "reports": reports, "collection_errors": []}, indent=1, sort_keys=True))
    _write(inner / "test_receipt.json", json.dumps(
        {"schema": "iscat165.workstation_tests.1", "returncode": 0, "real_F2c_calls": 0,
         "scope": "LOCAL_TEST_INVENTORY_ONLY"}, indent=1, sort_keys=True))
    _streams(run_dir / "v166_inherited_41", "v166_inherited")
    return {"suite": binding.INHERITED_SUITE, "returncode": 0, "all_green": True,
            "tests": len(rows), "python_version": sys.version,
            "command": [sys.executable, "tools/v165_bundle/run_workstation_tests.py"],
            "suite_dir": (run_dir / "v166_inherited_41").relative_to(
                controller.ROOT).as_posix(),
            "target": "tools/v165_bundle/run_workstation_tests.py",
            "inherited_outcomes": {"collected": len(rows), "reported_nodeids": len(rows),
                                   "collection_errors": 0,
                                   "outcomes_sha256": common.sha_file(outcomes),
                                   "schema": "v165_receipt_plugin"}}


def _repin_suite_receipt(run_dir: Path, document: dict, index: int) -> Path:
    suite = run_dir / f"suite_{index:02d}_receipt.json"
    document["suite_receipt_sha256"][f"suite_{index:02d}"] = common.sha_file(suite)
    return suite


def _build_workflow_tree(root: Path) -> Path:
    """Write a workflow receipt tree with the schema the real driver writes."""
    run_dir = root / RUN_ID
    run_dir.mkdir(parents=True, exist_ok=True)
    production_rows = _collect_rows(PRODUCTION_TARGET)
    bundle_rows = _collect_rows(BUNDLE_TARGET)
    # Suite 0 is written first, then 1 and 2, because the receipt binds each suite file
    # by SHA and the workflow binds all three.
    records = [_inherited_suite(run_dir, bundle_rows[:8]),
               _pytest_suite("bundle_plan_and_core", run_dir, "bundle_local_38",
                             bundle_rows, target=BUNDLE_TARGET, stem="run"),
               _pytest_suite(binding.PRODUCTION_SUITE, run_dir, "v168_production_suite",
                             production_rows, target=PRODUCTION_TARGET, stem="run")]
    for index, record in enumerate(records):
        _write(run_dir / f"suite_{index:02d}_receipt.json",
               json.dumps(record, indent=1, sort_keys=True) + "\n")
    sources = workflow_driver._source_hashes()
    wire = _write(run_dir / "v168_production_suite" / "real_f2c_tripwire.txt",
                  ZERO_MARKER + "\n")
    document = {
        "schema": binding.WORKFLOW_SCHEMA, "run_id": RUN_ID,
        "utc": binding._utc(),
        "scope": WORKFLOW_SCOPE,
        "contract_reference": "section 3.3",
        "suites": records,
        "total_tests_recorded": sum(int(row["tests"]) for row in records),
        "all_suites_green": all(bool(row["all_green"]) for row in records),
        "source_hashes_before": sources, "source_hashes_after": dict(sources),
        "source_hashes_unchanged": True,
        "real_f2c_tripwire": {"file": wire.name, "exists": True, "records": 1,
                              "real_construction_attempts": 0, "zero_marker_written": True},
        "budget_proof_mode": "absent_ledger", "budget_ledger_present": False,
        "budget_ledger_opened_mid_run": False, "budget_core_state_unchanged": True,
        "budget_state_before": {"ledger_exists": False},
        "budget_state_after": {"ledger_exists": False},
        "zero_charged_calls_proved": True,
        "suite_receipt_sha256": {f"suite_{index:02d}": common.sha_file(
            run_dir / f"suite_{index:02d}_receipt.json") for index in range(len(records))},
    }
    _write(run_dir / binding.WORKFLOW_NAME, json.dumps(document, indent=1) + "\n")
    return run_dir


def _rewrite_workflow(run_dir: Path, document: dict) -> None:
    _write(run_dir / binding.WORKFLOW_NAME, json.dumps(document, indent=1) + "\n")


def _workflow(run_dir: Path) -> dict:
    return json.loads((run_dir / binding.WORKFLOW_NAME).read_text(encoding="utf-8"))


@pytest.fixture()
def probe_dir(request):
    """A probe evidence root inside the repository, always removed at teardown."""
    # request.node.name carries the parametrised id, which can contain path separators, so
    # an unsanitised probe directory would put the evidence somewhere else entirely.  The
    # name is also truncated, and a truncated name must not end in a dot or a dash:
    # Windows drops a trailing dot when it resolves a path, so the directory the guard
    # records by relative path would never compare equal to the one the fixture handed out.
    # The digest suffix keeps truncated ids from colliding with each other.
    stem = re.sub(r"[^0-9A-Za-z_.\-]", "_", request.node.name)[:44].rstrip("._-")
    digest = hashlib.sha1(request.node.name.encode("utf-8")).hexdigest()[:10]
    root = ((controller.OUT / "workstation_tests").resolve()
            / (PROBE_PREFIX + stem + "_" + digest))
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    original = binding.WORKSTATION_TESTS_DIR
    binding.WORKSTATION_TESTS_DIR = root
    try:
        yield root
    finally:
        binding.WORKSTATION_TESTS_DIR = original
        shutil.rmtree(root, ignore_errors=True)


@pytest.fixture()
def built(probe_dir):
    """A synthetic tree that passes, then the real release receipt built over it."""
    run_dir = _build_workflow_tree(probe_dir)
    release = binding.build(RUN_ID)
    return run_dir, release


def _failure(call, *args, **kwargs) -> str:
    try:
        call(*args, **kwargs)
    except ValueError as exc:
        return str(exc)
    raise AssertionError("EXPECTED_REFUSAL_DID_NOT_FIRE")


class TestReleaseReceiptIsRequired:
    def test_workflow_without_release_receipt_is_refused(self, probe_dir):
        _build_workflow_tree(probe_dir)
        message = _failure(binding.verify, RUN_ID)
        assert message.startswith("WORKSTATION_TEST_RELEASE_RECEIPT_MISSING"), message

    def test_no_receipt_at_all_is_refused_by_name_search(self, probe_dir):
        message = _failure(binding.verify)
        assert message.startswith("WORKSTATION_RELEASE_RECEIPT_COUNT"), message

    def test_two_release_receipts_are_ambiguous(self, built, probe_dir):
        source = binding.release_path(RUN_ID)
        duplicate = probe_dir / ("v168_tb_dup_" + RUN_ID)
        duplicate.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, duplicate / binding.RELEASE_NAME)
        message = _failure(binding.verify)
        assert message.startswith("WORKSTATION_RELEASE_RECEIPT_COUNT"), message


class TestWorkflowReceiptRefusals:
    def test_honest_schemas_from_other_generations_are_refused(self, built, probe_dir):
        path = binding.workflow_path(RUN_ID)
        document = json.loads(path.read_text(encoding="utf-8"))
        for schema, reason in sorted(binding.FORBIDDEN_RECEIPTS.items()):
            stolen = dict(document, schema=schema)
            _write(path, json.dumps(stolen, indent=1) + "\n")
            message = _failure(binding.read_workflow, path)
            assert "WORKSTATION_TEST_RECEIPT_REFUSED:" + reason in message, message

    def test_unknown_schema_is_not_verified(self, built, probe_dir):
        path = binding.workflow_path(RUN_ID)
        _write(path, json.dumps(dict(json.loads(path.read_text(encoding="utf-8")),
                                     schema="iscat169.workstation_tests.1"), indent=1))
        assert _failure(binding.read_workflow, path).startswith("TEST_RECEIPT_NOT_VERIFIED")

    def test_receipt_must_live_in_the_evidence_directory(self, built, probe_dir):
        elsewhere = probe_dir.parent / (probe_dir.name + "_escaped")
        shutil.copytree(probe_dir / RUN_ID, elsewhere / RUN_ID, dirs_exist_ok=True)
        try:
            message = _failure(binding.read_workflow,
                               elsewhere / RUN_ID / binding.WORKFLOW_NAME)
            assert message.startswith("WORKSTATION_TEST_RECEIPT_OUTSIDE_EVIDENCE_DIR"), message
        finally:
            shutil.rmtree(elsewhere, ignore_errors=True)

    def test_wrong_file_name_is_refused(self, built, probe_dir):
        path = binding.workflow_path(RUN_ID)
        renamed = path.parent / "test_receipt.json"
        shutil.copyfile(path, renamed)
        message = _failure(binding.read_workflow, renamed)
        assert message.startswith("WORKSTATION_TEST_RECEIPT_WRONG_NAME"), message

    @pytest.mark.parametrize(("field", "value", "reason"), [
        ("all_suites_green", False, "WORKSTATION_TESTS_NOT_PASS"),
        ("zero_charged_calls_proved", False, "TEST_SUITES_BILLED_MODEL_CALLS"),
        ("source_hashes_unchanged", False, "SOURCE_HASHES_MOVED_DURING_TESTS"),
        ("total_tests_recorded", 0, "TEST_RECEIPT_NO_TESTS"),
        ("contract_reference", "section 5", "TEST_RECEIPT_CONTRACT_REFERENCE"),
        ("scope", "SOME OTHER SCOPE", "TEST_RECEIPT_SCOPE"),
    ])
    def test_workflow_claims_are_re_read_not_trusted(self, built, probe_dir, field, value,
                                                     reason):
        path = binding.workflow_path(RUN_ID)
        document = json.loads(path.read_text(encoding="utf-8"))
        document[field] = value
        _write(path, json.dumps(document, indent=1) + "\n")
        message = _failure(binding.read_workflow, path)
        assert message.startswith(reason), message

    def test_tripwire_attempt_is_refused(self, built, probe_dir):
        path = binding.workflow_path(RUN_ID)
        document = json.loads(path.read_text(encoding="utf-8"))
        document["real_f2c_tripwire"]["real_construction_attempts"] = 1
        _write(path, json.dumps(document, indent=1) + "\n")
        message = _failure(binding.read_workflow, path)
        assert message.startswith("TEST_SUITES_REACHED_REAL_MODEL"), message

    def test_suite_receipt_rewritten_after_the_run_is_refused(self, built, probe_dir):
        suite = binding.workflow_path(RUN_ID).parent / "suite_01_receipt.json"
        record = json.loads(suite.read_text(encoding="utf-8"))
        _write(suite, json.dumps(dict(record, returncode=1), indent=1) + "\n")
        message = _failure(binding.read_workflow, binding.workflow_path(RUN_ID))
        assert message.startswith("SUITE_RECEIPT_SHA_UNBOUND"), message

    def test_missing_suite_receipt_is_refused(self, built, probe_dir):
        (binding.workflow_path(RUN_ID).parent / "suite_02_receipt.json").unlink()
        message = _failure(binding.read_workflow, binding.workflow_path(RUN_ID))
        assert message.startswith("SUITE_RECEIPT_MISSING"), message


class TestHappyPathIsReproducible:
    def test_verify_passes_on_the_tree_it_just_built(self, built, probe_dir):
        gate = binding.verify(RUN_ID)
        assert gate["WORKSTATION_TESTS_PASS"] is True
        assert gate["WORKSTATION_TEST_RECEIPT_VERIFIED"] is True
        assert gate["CODE_BINDING_VERIFIED"] is True
        assert gate["INPUT_PROVENANCE_VERIFIED"] is True
        assert gate["suite_count"] == 3
        assert gate["model_calls"] == 0
        assert gate["code_identity_sha256"] == controller.code_identities()["identity_sha256"]
        assert gate["test_suite_sha256"] == controller.test_suite_sha256()

    def test_release_receipt_is_new_only_and_self_digest_pinned(self, built, probe_dir):
        run_dir, release = built
        message = _failure(binding.build, RUN_ID)
        assert message.startswith("RELEASE_RECEIPT_ALREADY_EXISTS"), message
        assert release["receipt_sha256"] == binding._self_digest(release)
        assert binding.read_json(binding.release_path(RUN_ID))["receipt_sha256"] == \
            release["receipt_sha256"]

    def test_recollection_uses_the_real_collector_and_matches_the_inventory(self, probe_dir):
        _build_workflow_tree(probe_dir)
        release = binding.build(RUN_ID)
        rows = [row for row in release["suites"] if row["suite"] == binding.PRODUCTION_SUITE]
        assert len(rows) == 1
        real_rows = _collect_rows(PRODUCTION_TARGET)
        assert rows[0]["recollection"]["count"] == len(real_rows)
        assert rows[0]["recollection"]["nodeids_sha256"] == binding.rows_digest(real_rows)
        assert rows[0]["inventory"]["count"] == len(real_rows)
        assert rows[0]["nodeids_sample"] == real_rows[:2]
        # Building verifies, so reaching here already re-collected a second time.
        assert binding.verify(RUN_ID)["WORKSTATION_TESTS_PASS"] is True

    def test_self_consistent_but_trimmed_inventory_is_refused(self, probe_dir):
        """Dropping one recorded item, and its result row, still re-collects four."""
        run_dir = _build_workflow_tree(probe_dir)
        rows = _collect_rows(PRODUCTION_TARGET)
        trimmed = rows[:-1]
        _set_inventory(run_dir, "v168_production_suite", trimmed)
        suite = run_dir / "suite_02_receipt.json"
        record = json.loads(suite.read_text(encoding="utf-8"))
        record["tests"] = len(trimmed)
        _write(suite, json.dumps(record, indent=1) + "\n")
        workflow = _workflow(run_dir)
        workflow["suites"][2]["tests"] = len(trimmed)
        workflow["total_tests_recorded"] = sum(int(row["tests"]) for row in workflow["suites"])
        _repin_suite_receipt(run_dir, workflow, 2)
        _rewrite_workflow(run_dir, workflow)
        message = _failure(binding.build, RUN_ID)
        assert message.startswith("RECOLLECTED_NODEID_COUNT"), message

    def test_inventory_holding_an_item_the_collector_never_saw_is_refused(self, probe_dir):
        """Same count, different set: a padded name that does not exist on disk."""
        run_dir = _build_workflow_tree(probe_dir)
        rows = _collect_rows(PRODUCTION_TARGET)
        swapped = sorted(rows[:-1] + ["zzz_probe.py::test_never_collected"])
        _set_inventory(run_dir, "v168_production_suite", swapped)
        message = _failure(binding.build, RUN_ID)
        assert message.startswith("RECOLLECTED_NODEID_SET"), message

    def test_a_release_without_a_live_recollection_cannot_authorize_a_run(self, built,
                                                                          probe_dir):
        run_dir, release = built
        path = binding.release_path(RUN_ID)
        document = json.loads(path.read_text(encoding="utf-8"))
        production = [row for row in document["suites"]
                      if row["suite"] == binding.PRODUCTION_SUITE]
        assert len(production) == 1 and production[0]["recollection"]
        # Erasing the live re-collection while keeping every pinned digest consistent:
        # such a release would only ever repeat what it already recorded.
        for row in document["suites"]:
            if row["suite"] == binding.PRODUCTION_SUITE:
                row["recollection"] = {}
        document["receipt_sha256"] = binding._self_digest(document)
        _write(path, json.dumps(document, indent=1))
        message = _failure(binding.verify, RUN_ID)
        assert message.startswith("PRODUCTION_RECOLLECTION_NOT_RECORDED"), message
        assert release["suites"][-1]["recollection"]


class TestTamperingIsDetectedAfterBuild:
    def test_code_identity_that_moved_after_the_tests(self, built, probe_dir, monkeypatch):
        identities = controller.code_identities()
        identities["identity_sha256"] = "0" * 64
        monkeypatch.setattr(controller, "code_identities", lambda: identities)
        message = _failure(binding.verify, RUN_ID)
        assert message.startswith("CODE_CHANGED_AFTER_TESTS"), message

    def test_test_suite_pin_that_moved(self, built, probe_dir, monkeypatch):
        monkeypatch.setattr(controller, "test_suite_sha256", lambda: "1" * 64)
        message = _failure(binding.verify, RUN_ID)
        assert message.startswith("FROZEN_TEST_SUITE_CHANGED_BEFORE_RESERVE"), message

    def test_node_id_added_after_the_run_is_refused(self, built, probe_dir):
        inventory = probe_dir / RUN_ID / "v168_production_suite" / "nodeids.txt"
        rows = [line for line in inventory.read_text(encoding="utf-8").splitlines() if line]
        # A well-formed, sorted, distinct extra row: only the inventory digest moves, so
        # the refusal has to come from the binding and not from the shape checks.
        _write(inventory, "".join(line + "\n" for line in rows + ["zzz_probe.py::test_zz"]))
        message = _failure(binding.verify, RUN_ID)
        assert message.startswith("NODEID_INVENTORY_CHANGED"), message

    @pytest.mark.parametrize(("relative", "reason"), [
        ("v168_production_suite/run.stdout.txt", "ERROR_LOG_STREAMS"),
        ("v168_production_suite/run.stderr.txt", "ERROR_LOG_STREAMS"),
        ("suite_02_receipt.json", "SUITE_RECEIPT_SHA_UNBOUND"),
        ("workstation_test_receipt.json", "WORKFLOW_RECEIPT_SHA_CHANGED"),
    ])
    def test_edited_evidence_is_refused(self, built, probe_dir, relative, reason):
        path = probe_dir / RUN_ID / relative
        path.write_bytes(path.read_bytes() + b"tampered\n")
        message = _failure(binding.verify, RUN_ID)
        assert message.startswith(reason), message

    def test_edited_junit_channel_is_refused_by_its_sha(self, built, probe_dir):
        # The edit stays a well-formed JUnit document, so only the pinned channel SHA can
        # be what refuses it, not a parser tripping over damaged bytes.
        path = probe_dir / RUN_ID / "v168_production_suite" / "junit.xml"
        original = path.read_text(encoding="utf-8")
        _write(path, original.replace('failures="0"', 'failures="1"', 1))
        message = _failure(binding.verify, RUN_ID)
        assert message.startswith("OUTCOME_CHANNEL_SHA"), message

    def test_damaged_junit_channel_refuses_by_name(self, built, probe_dir):
        # Damaged XML is refused with a name, because this channel is read in front of
        # model authority and a bare parser traceback is not packable evidence.
        path = probe_dir / RUN_ID / "v168_production_suite" / "junit.xml"
        path.write_bytes(path.read_bytes() + b"tampered\n")
        message = _failure(binding.verify, RUN_ID)
        assert message.startswith("JUNIT_UNPARSEABLE"), message

    def test_removed_error_log_stream_is_refused(self, built, probe_dir):
        # One stream of a pair disappearing leaves a receipt that no longer describes the
        # tree, so the pinned stream map is the thing that refuses the round.
        (probe_dir / RUN_ID / "v168_production_suite" / "run.stderr.txt").unlink()
        message = _failure(binding.verify, RUN_ID)
        assert message.startswith("ERROR_LOG_STREAMS"), message

    def test_suite_with_no_captured_streams_is_refused(self, built, probe_dir):
        # A suite whose whole console capture is gone leaves no complete error log to pack,
        # so the refusal has to be named instead of a silent empty read.
        directory = probe_dir / RUN_ID / "v166_inherited_41"
        for name in ("v166_inherited.stdout.txt", "v166_inherited.stderr.txt"):
            (directory / name).unlink()
        message = _failure(binding.verify, RUN_ID)
        assert message.startswith("NO_CAPTURED_STREAMS"), message

    def test_extra_captured_stream_is_refused(self, built, probe_dir):
        _write(probe_dir / RUN_ID / "bundle_local_38" / "extra.stdout.txt", "appended\n")
        message = _failure(binding.verify, RUN_ID)
        assert message.startswith("ERROR_LOG_STREAMS"), message


class TestEvidenceClaimsAreRefused:
    """A receipt that lies about its own suite is refused, before the release is written and
    afterwards alike: the same claims are re-read on every path."""

    def test_source_file_edited_after_the_tests(self, probe_dir):
        run_dir = _build_workflow_tree(probe_dir)
        document = _workflow(run_dir)
        stale = dict(document["source_hashes_after"])
        target = sorted(stale)[0]
        stale[target] = "9" * 64
        document["source_hashes_after"] = stale
        _rewrite_workflow(run_dir, document)
        message = _failure(binding.build, RUN_ID)
        assert message.startswith("BOUNDED_SOURCE_SHA:" + target), message

    def test_suite_claimed_count_below_its_own_inventory(self, probe_dir):
        run_dir = _build_workflow_tree(probe_dir)
        suite = run_dir / "suite_01_receipt.json"
        record = json.loads(suite.read_text(encoding="utf-8"))
        record["tests"] = int(record["tests"]) - 1
        _write(suite, json.dumps(record, indent=1) + "\n")
        document = _workflow(run_dir)
        document["suites"][1]["tests"] = record["tests"]
        document["total_tests_recorded"] = sum(int(row["tests"]) for row in document["suites"])
        _repin_suite_receipt(run_dir, document, 1)
        _rewrite_workflow(run_dir, document)
        message = _failure(binding.build, RUN_ID)
        assert message.startswith("SUITE_TEST_COUNT_VS_INVENTORY"), message

    def test_inherited_suite_with_a_failed_row_cannot_claim_green(self, probe_dir):
        run_dir = _build_workflow_tree(probe_dir)
        outcomes = run_dir / "v166_inherited_41" / "v165_driver" / "pytest_outcomes.json"
        document = json.loads(outcomes.read_text(encoding="utf-8"))
        document["reports"] = [row for row in document["reports"] if row["when"] != "call"]
        document["reports"].append({"nodeid": sorted(document["collected"])[-1],
                                    "when": "call", "outcome": "failed"})
        _write(outcomes, json.dumps(document, indent=1, sort_keys=True))
        suite = run_dir / "suite_00_receipt.json"
        record = json.loads(suite.read_text(encoding="utf-8"))
        record["inherited_outcomes"]["outcomes_sha256"] = common.sha_file(outcomes)
        _write(suite, json.dumps(record, indent=1) + "\n")
        workflow = _workflow(run_dir)
        workflow["suites"][0]["inherited_outcomes"]["outcomes_sha256"] = \
            record["inherited_outcomes"]["outcomes_sha256"]
        _repin_suite_receipt(run_dir, workflow, 0)
        _rewrite_workflow(run_dir, workflow)
        message = _failure(binding.build, RUN_ID)
        assert message.startswith("SUITE_HAS_UNHANDLED_PROBLEMS"), message

    def test_green_claim_with_a_nonzero_return_code(self, probe_dir):
        run_dir = _build_workflow_tree(probe_dir)
        suite = run_dir / "suite_01_receipt.json"
        record = json.loads(suite.read_text(encoding="utf-8"))
        record["returncode"] = 1
        _write(suite, json.dumps(record, indent=1) + "\n")
        workflow = _workflow(run_dir)
        workflow["suites"][1]["returncode"] = 1
        _repin_suite_receipt(run_dir, workflow, 1)
        _rewrite_workflow(run_dir, workflow)
        message = _failure(binding.build, RUN_ID)
        assert message.startswith("SUITE_RETURN_CODE"), message

    def test_inventory_row_without_an_item_id_is_not_an_inventory(self, built, probe_dir):
        inventory = probe_dir / RUN_ID / "bundle_local_38" / "nodeids.txt"
        _write(inventory, "no item separator here\n")
        message = _failure(binding.verify, RUN_ID)
        assert message.startswith("NODEIDS_NOT_ITEM_INVENTORY"), message

    def test_duplicate_inventory_rows_are_refused(self, built, probe_dir):
        inventory = probe_dir / RUN_ID / "bundle_local_38" / "nodeids.txt"
        rows = [line for line in inventory.read_text(encoding="utf-8").splitlines() if line]
        _write(inventory, "".join(row + "\n" for row in sorted(rows + [rows[0]])))
        assert "NODEID_INVENTORY_DUPLICATES" in _failure(binding.verify, RUN_ID)

    def test_only_the_inherited_suite_may_lack_a_node_id_file(self, built, probe_dir):
        (probe_dir / RUN_ID / "bundle_local_38" / "nodeids.txt").unlink()
        message = _failure(binding.verify, RUN_ID)
        assert message.startswith("NODEID_INVENTORY_MISSING"), message

    def test_inherited_outcomes_re_hashed_into_a_different_list(self, built, probe_dir):
        outcomes = (probe_dir / RUN_ID / "v166_inherited_41" / "v165_driver" /
                    "pytest_outcomes.json")
        document = json.loads(outcomes.read_text(encoding="utf-8"))
        document["collected"] = document["collected"][:-1]
        _write(outcomes, json.dumps(document, indent=1, sort_keys=True))
        message = _failure(binding.verify, RUN_ID)
        assert message.startswith("INHERITED_OUTCOMES_SHA_UNBOUND"), message


class TestInputProvenanceIsRealEvidence:
    def test_four_scenarios_and_twelve_existing_camera_images(self):
        provenance = binding.input_provenance()
        assert provenance["scenario_count"] == 4
        assert provenance["camera_image_count"] == 12
        assert provenance["model_calls"] == 0
        assert provenance["new_random_draws"] == 0
        assert provenance["wrote_inside_v166"] is False
        assert provenance["camera_h5"]["sha256"] == controller.FROZEN_CAMERA_SHA256
        assert sorted(provenance["scenarios"]) == list(binding.SCENARIO_GROUPS)

    def test_three_frames_per_group_and_undisturbed_detection_states(self):
        provenance = binding.input_provenance()
        for group, row in sorted(provenance["scenarios"].items()):
            assert row["frame_count"] == binding.FRAMES_PER_GROUP
            assert len(set(row["camera_event_ids"])) == binding.FRAMES_PER_GROUP
            assert len(row["detections"]) == binding.FRAMES_PER_GROUP
            if group == "ANON_01":
                assert row["detected_count"] == 0
            else:
                assert row["detected_count"] == binding.FRAMES_PER_GROUP
            assert row["source_context_sha256"]
            assert row["frames_sha256"]

    def test_provenance_is_deterministic_and_binds_the_release_receipt(self, built):
        run_dir, release = built
        assert common.canon(binding.input_provenance()) == \
            common.canon(release["input_provenance"])
        assert binding.verify(RUN_ID)["scenario_count"] == 4

    def test_binding_refuses_a_moved_camera_pin(self, monkeypatch):
        monkeypatch.setattr(controller, "FROZEN_CAMERA_SHA256", "2" * 64)
        assert _failure(binding.input_provenance).startswith("CAMERA_H5_BYTES_CHANGED")

    def test_bound_source_list_covers_the_production_modules(self, built):
        run_dir, release = built
        binding_module = "tools/v168/v168_test_binding.py"
        assert binding_module in release["source_binding"]["production_files"]
        assert release["source_binding"]["files"][binding_module]["in_code_identity"] is True
        assert release["source_binding"]["bound_file_count"] == \
            len(run_workflow_source_count(run_dir))


def run_workflow_source_count(run_dir: Path) -> list[str]:
    document = json.loads((run_dir / binding.WORKFLOW_NAME).read_text(encoding="utf-8"))
    return sorted(document["source_hashes_after"])
