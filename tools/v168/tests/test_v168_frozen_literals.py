"""Freeze the scientific literals the round runs on, against bytes and contract text.

v168_common claims in its module docstring that these frozen definitions are copied
verbatim from the byte-verified V166 production runner and are cross-checked here.
This file makes that claim true: every pin is re-read from disk, and every number
the optimiser and budget use is re-read from the unique contract markdown, so an
edit to either side has to fail loudly rather than silently change the research
definition mid-round.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys

import pytest

import v168_common as common
import v168_controller as controller

from conftest import (CONTRACT_PATH, INHERITED_CONTRACT_PATH, contract_budget_table,
                      contract_text as read_contract, normalised)

assert CONTRACT_PATH.is_file(), "V168_BUNDLE_CONTRACT_MISSING"
assert INHERITED_CONTRACT_PATH.is_file(), "V167_INHERITED_CONTRACT_MISSING"
AUTHORIZATION = common.AUTHORIZATION


@pytest.fixture(scope="module")
def contract_text() -> str:
    return read_contract(CONTRACT_PATH)


@pytest.fixture(scope="module")
def inherited_contract_text() -> str:
    """The V167 contract, which is still the authority for the inherited V166 pins."""
    return read_contract(INHERITED_CONTRACT_PATH)


@pytest.fixture(scope="module")
def authorization() -> dict:
    """The machine-readable grant this round spends against."""
    return json.loads(AUTHORIZATION.read_text(encoding="utf-8"))


def test_frozen_module_sha_literals_match_disk_bytes():
    literals = {
        "GLS_CORE_SHA256": common.sha_file(common.APPROVED_CORE / "v152_gls_core.py"),
        "OBJECTIVE_SHA256": common.sha_file(common.APPROVED_CORE / "v165_objective.py"),
        "PAYLOAD_GATE_SHA256": common.sha_file(common.PAYLOAD_GATE),
        "BUDGET_STORE_SHA256": common.sha_file(common.BUDGET_STORE),
        "V166_RUN_SHA256": common.sha_file(common.ROOT / "tools" / "v165_bundle" / "code" / "v165_run.py"),
    }
    for name, actual in literals.items():
        assert getattr(common, name) == actual, name
        assert re.fullmatch(r"[0-9a-f]{64}", getattr(common, name)), name


def test_controller_identity_driver_recomputes_and_accepts_the_same_pins():
    identities = controller.code_identities()
    frozen = identities["frozen_literals"]
    assert frozen["approved_core_v152_gls_core"] == common.GLS_CORE_SHA256
    assert frozen["approved_core_v165_objective"] == common.OBJECTIVE_SHA256
    assert frozen["v168_payload_gate"] == common.PAYLOAD_GATE_SHA256
    assert frozen["v152_budget_store"] == common.BUDGET_STORE_SHA256
    assert frozen["v165_run"] == common.V166_RUN_SHA256
    assert all(identities["identity_checks"].values()), identities["identity_checks"]
    assert identities["v166_release_commit"] == common.PARENT_COMMIT
    assert identities["file_count"] == len(identities["files"]) > 0


def _estimator_role_identity_in_a_fresh_process() -> dict:
    """A worker-shaped interpreter: estimator bootstrap, then the real verification."""
    script = (
        "import json,sys;sys.path.insert(0,r'{tools}');import v168_common as c;"
        "c.bootstrap_paths(estimator=True);"
        "print(json.dumps(c.verify_frozen_module_identities(estimator=True)))"
    ).format(tools=str(common.ROOT / "tools" / "v168"))
    proc = subprocess.run([sys.executable, "-X", "utf8", "-c", script],
                          capture_output=True, text=True, cwd=str(common.ROOT))
    assert proc.returncode == 0, proc.stderr[-2000:]
    return json.loads(proc.stdout)


def test_frozen_module_identity_verification_passes_in_the_estimator_role():
    doc = _estimator_role_identity_in_a_fresh_process()
    assert doc["role"] == "estimator"
    assert set(doc["modules"]) == {"v152_gls_core", "v165_objective", "v168_payload_gate"}
    assert "v152_budget_store" not in doc["modules"]
    assert doc["absent_from_sys_modules"]


def test_estimator_role_verification_refuses_a_trusted_process():
    # This pytest process bootstrapped the trusted service paths, so the estimator
    # branch must refuse here.  The guard is tested in both directions on purpose.
    trusted = common.verify_frozen_module_identities(estimator=False)
    assert "v152_budget_store" in trusted["modules"]
    assert "detail" in trusted["budget_store_charge_parameters"]
    with pytest.raises(ValueError) as caught:
        common.verify_frozen_module_identities(estimator=True)
    assert str(caught.value) == "ESTIMATOR_PATH_EXPOSES_V166_RUNNER_DIR"


def test_optimizer_and_bounds_are_the_contract_recipe_verbatim():
    assert common.OPTIMIZER == {
        "method": "trf", "jac": "3-point", "loss": "linear", "diff_step": 1e-5,
        "x_scale": [50.0, 50.0, 280.0, 280.0], "ftol": 1e-9, "xtol": 1e-9,
        "gtol": 1e-8, "max_nfev": 200,
    }
    assert common.LOW == [30.0, 350.0, -500.0, -500.0]
    assert common.HIGH == [200.0, 550.0, 500.0, 500.0]


def test_frozen_recipe_literals_are_named_in_the_contract_text(contract_text,
                                                               inherited_contract_text):
    flat = normalised(contract_text)
    assert common.MODEL_ID in contract_text
    # The two frozen input digests are not repeated in the V168 prose.  They are pinned
    # in the V167 contract that V168 inherits, and in the machine-readable authorization
    # this round reads at prepare time, so the literal check belongs there -- not in an
    # invented search of a document that never carried them.
    inherited = normalised(inherited_contract_text)
    assert controller.FROZEN_LIBRARY_SHA256 in inherited
    assert controller.FROZEN_CAMERA_SHA256 in inherited
    for needle in ("method='trf'", "jac='3-point'", "loss='linear'", "diff_step=1e-5",
                   "x_scale=[50,50,280,280]", "ftol=1e-9, xtol=1e-9, gtol=1e-8",
                   "max_nfev=200", "bounds=([30,350,-500,-500],[200,550,500,500])"):
        assert normalised(needle) in flat, needle
    for needle in ("2*SciPy.cost=Q_model+Q_height", "Q_total=2*cost+K",
                   "检查h−D/2≥100nm"):
        assert normalised(needle) in flat, needle


def test_frozen_input_digests_are_pinned_in_the_authorization_and_on_disk(authorization):
    """The input pins the removed markdown search wanted, taken from their real source."""
    guard = authorization["source_guard"]
    assert guard["library_sha256"] == controller.FROZEN_LIBRARY_SHA256
    assert guard["camera_h5_sha256"] == controller.FROZEN_CAMERA_SHA256
    assert guard["model_id"] == common.MODEL_ID
    assert guard["parent_model_id"] == common.load_recovery_gate().F2
    assert common.sha_file(AUTHORIZATION) == common.AUTHORIZATION_SHA256
    config = common.read_json(common.ROOT / "config" / "v146_science_config.json")
    assert config["frozen"]["library_sha256"] == controller.FROZEN_LIBRARY_SHA256
    assert config["frozen"]["camera_h5_sha256"] == controller.FROZEN_CAMERA_SHA256
    assert common.sha_file(common.ROOT / config["inputs"]["training_library"]) \
        == controller.FROZEN_LIBRARY_SHA256
    assert common.sha_file(common.ROOT / config["inputs"]["camera_h5"]) \
        == controller.FROZEN_CAMERA_SHA256


def test_phase_caps_and_model_identity_match_the_contract_table(contract_text,
                                                                authorization):
    flat = normalised(contract_text)
    rows = contract_budget_table(contract_text)
    phases = tuple(common.PHASES)
    assert set(rows) == {*phases, "TOTAL"}, rows
    # Column 2 is what V167 already spent and can never spend again; column 3 is this
    # round's new ceiling, the number the frozen ledger gate enforces; column 4 is the
    # merged ceiling the combined effort may not exceed.
    historical = {phase: rows[phase][0] for phase in phases}
    new_limit = {phase: rows[phase][1] for phase in phases}
    combined = {phase: rows[phase][2] for phase in phases}
    assert dict(common.PHASES) == new_limit, rows
    assert common.TOTAL == sum(new_limit.values()) == 9_999
    assert rows["TOTAL"] == (1, 9_999, 10_000)
    assert historical == {"MODEL_BINDING": 1, "SEARCH_EXTENSION": 0,
                          "BIAS_STRESS": 0, "FINAL_VERIFY": 0}
    assert sum(combined.values()) == 10_000
    assert all(combined[phase] >= new_limit[phase] for phase in phases)
    assert dict(common.load_recovery_gate().PHASES) == new_limit
    assert authorization["phases"] == new_limit
    assert authorization["new_attempt_ceiling"] == 9_999
    assert authorization["combined_attempt_ceiling"] == 10_000
    assert authorization["historical_consumed_attempts"] == 1
    caps = authorization["fixed_task_caps"]
    assert (caps["loader"], caps["binding"]) == (100, 99)
    assert caps["loader"] + caps["binding"] == new_limit["MODEL_BINDING"]
    assert caps["recovery_count"] * caps["recovery_each"] == new_limit["SEARCH_EXTENSION"]
    assert caps["bias_count"] * caps["bias_each"] == new_limit["BIAS_STRESS"]
    assert caps["final_verify"] == new_limit["FINAL_VERIFY"]
    assert "5×400" in flat and "18×400" in flat and normalised("预约26项") in flat


def test_task_names_for_binding_loader_and_final_verify_are_stable():
    assert common.LOADER_TASK == "V168_LOADER_1"
    assert common.BINDING_TASK == "V168_BINDING"
    assert common.FINAL_TASK == "V168_FINAL_VERIFY"
    assert common.OWNER == "v168-model-service"
    assert common.PARENT_COMMIT == "06b35cd4e0a47f7f49ef4b05401a07266f2c03b6"


def test_contract_pinned_input_files_are_the_ones_this_round_rereads(
        inherited_contract_text):
    pins = controller.CONTRACT_PINS
    flat67 = normalised(inherited_contract_text)
    for rel, digest in pins.items():
        assert re.fullmatch(r"[0-9a-f]{64}", digest), rel
        assert digest in flat67, rel
        path = common.ROOT / rel
        assert path.is_file(), "CONTRACT_FILE_MISSING:" + rel
        assert common.sha_file(path) == digest, rel
    assert pins["results/v166/estimates.json"] == (
        "8f97339e9645a29ec929e5c792d234a28821970338cf92a62d2982bfebba7634")
    assert pins["results/v166/height_input/height_readings.json"] == (
        "bbfd793aff48247623081dd607168cd9afbba2deeff5f37c7a0cbd62b032ad4e")
    assert pins["results/v166/logs/v165_budget.sqlite"] == (
        "254b5485164a57865328c81f8890ea4aa458d1386ed6f5f34533f2848f7e4ece")
    assert pins["results/v166/iscat_v166_return_001.zip"] == (
        "866feed02333f244df72f55e38ccf74060962007a5010c5c29df5ebe9f16a74e")
    assert controller.CONTRACT_ZIP_BYTES == 17_554_667
    assert normalised("17,554,667") in flat67
    zip_path = common.ROOT / "results/v166/iscat_v166_return_001.zip"
    assert zip_path.is_file()
    assert zip_path.stat().st_size == controller.CONTRACT_ZIP_BYTES
    assert common.sha_file(INHERITED_CONTRACT_PATH) == (
        "d842922f340ad0f31f136d486c26d25536c33898e9dc1f3be2815455709069c5")
    assert INHERITED_CONTRACT_PATH.stat().st_size == 20_875


def test_forbidden_key_list_covers_every_truth_bearing_name_in_the_contract(
        contract_text, inherited_contract_text):
    flat = normalised(contract_text)
    for key in ("D_scene_nm", "h_scene_nm", "epsilon", "seed", "truth_file_sha256",
                "controlled_offset_nm", "bias_nm", "z_nm_zero_bias", "plan", "readings"):
        assert key in common.FORBIDDEN_PAYLOAD_KEYS, key
    # The contract states the ban in prose; each term maps to a key the scanner knows,
    # so rewording the rule cannot quietly drop a protected name.
    this_round = {"seed": "seed", "epsilon": "epsilon",
                  "truth哈希": "truth_file_sha256",
                  "完整24条配对读数": "readings",
                  "控制器偏差b": "controlled_offset_nm",
                  "不见原z/b": "z_nm_zero_bias", "新随机数=0": "seed"}
    inherited = {"种子": "seed", "真实场景表": "D_scene_nm", "全24条读数": "readings",
                 "规划总表": "entries", "偏差": "bias_nm"}
    for term, key in this_round.items():
        assert normalised(term) in flat, term
        assert key in common.FORBIDDEN_PAYLOAD_KEYS, (term, key)
    for term, key in inherited.items():
        assert normalised(term) in normalised(inherited_contract_text), term
        assert key in common.FORBIDDEN_PAYLOAD_KEYS, (term, key)
    assert normalised("禁止把字段拆开、改名或编码后继续传入") in normalised(
        inherited_contract_text)
    # the controller-only readings file really does carry the two pinned truth keys
    raw = (common.V166 / "height_input" / "height_readings.json").read_bytes().decode("utf-8-sig")
    assert '"seed"' in raw and '"truth_file_sha256"' in raw
    assert common.PAYLOAD_KEYS == {"schema", "task_id", "group", "B", "reading", "starts",
                                   "cap_per_start", "task_cap", "scope"}
    assert "z_nm" in common.READING_KEYS and "sigma_nm" in common.READING_KEYS
    # the single-reading projection key set must not contain any forbidden name
    assert not (set(common.READING_KEYS) & set(common.FORBIDDEN_PAYLOAD_KEYS))
    assert not (common.PAYLOAD_KEYS & set(common.FORBIDDEN_PAYLOAD_KEYS))
