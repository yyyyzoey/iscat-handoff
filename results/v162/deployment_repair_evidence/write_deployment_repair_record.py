"""Generate the V162 contract-section-4 deployment-repair record from first-hand evidence.

Read-only with respect to the frozen package: this script only reads bytes and
writes its two reports inside results/v162/deployment_repair_evidence/.
"""
import hashlib, json, pathlib, sys

ROOT = pathlib.Path(r"C:\iscat\v162")
EV = ROOT / "results/v162/deployment_repair_evidence"
LAUNCHER = pathlib.Path(r"C:\iscat\v162_launcher_f32d0e154d434bc79516ae32779a7a5a")


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def ident(p):
    p = pathlib.Path(p)
    if not p.is_file():
        return None
    return dict(path=str(p), bytes=p.stat().st_size, sha256=sha(p))


def rel_ident(rel):
    return ident(ROOT / rel)


def main():
    first_run_logs = ROOT / "results/v162/logs"
    stage_states = json.loads(
        (first_run_logs / "9285abb568744494a8fd3784849c229d_stage_states.json").read_text("utf-8")
    )
    stage_commands = json.loads(
        (first_run_logs / "9285abb568744494a8fd3784849c229d_stage_commands.json").read_text("utf-8")
    )
    ab = json.loads((EV / "ab_nose_plugin_summary.json").read_text("utf-8"))
    payload_check = json.loads((EV / "payload_vs_installed_verification.json").read_text("utf-8"))
    revert = json.loads(
        (EV / "runner_edit_reverted_before_commit/revert_record.json").read_text("utf-8")
    )
    marker = json.loads((ROOT / ".v162-preparation.json").read_text("utf-8"))
    staged = {run["label"]: run for run in ab["results"]}

    record = dict(
        task="V162",
        record_type="CONTRACT_SECTION_4_DEPLOYMENT_CONDITION_REPAIR_AND_RESUME",
        contract_clause=(
            "Section 4: if the launcher/installation/tests fail, the real deployment condition may be "
            "repaired provided no V162 model ledger and no actual model call exist, then the original "
            "package is re-tested in full; old logs are kept, no check is deleted by us, no math core is changed."
        ),
        baseline_conditions=dict(
            frozen_science_base="71333a9f193d00012972e8fd6c188805c7a6b18e",
            reviewed_parent="dad7b87554959355926d3523169fae7ac30a39f7",
            code_commit=marker["code_commit"],
            worktree=str(ROOT),
            v162_model_ledger_exists_at_repair_time=revert["v162_ledger_existed_at_revert_time"],
            model_forward_calls_made_before_repair=revert["model_forward_calls_made_before_revert"],
            ledger_path="results/v162/logs/v162_budget.sqlite",
        ),
        first_run=dict(
            launcher_evidence_dir=str(LAUNCHER),
            launcher_artifacts={
                n: ident(LAUNCHER / n)
                for n in [
                    "launcher_state.json",
                    "prepare.json",
                    "prepare.stdout",
                    "prepare.stderr",
                    "run_all.json",
                    "run_all.stdout",
                    "run_all.stderr",
                    "final_pack.json",
                ]
            },
            launcher_returncode=2,
            prepare_returncode=0,
            run_all_returncode=2,
            final_pack_returncode=0,
            stage_states=stage_states,
            stage_commands=[
                dict(stage=r["stage"], returncode=r["returncode"], command=r["command"])
                for r in stage_commands
            ],
            first_failure_stage="tests",
            preserved_evidence={
                "results/v162/logs/9285abb568744494a8fd3784849c229d_tests.stdout": rel_ident(
                    "results/v162/logs/9285abb568744494a8fd3784849c229d_tests.stdout"
                ),
                "results/v162/logs/9285abb568744494a8fd3784849c229d_stage_states.json": rel_ident(
                    "results/v162/logs/9285abb568744494a8fd3784849c229d_stage_states.json"
                ),
                "results/v162/workstation_tests/test_output.txt": rel_ident(
                    "results/v162/workstation_tests/test_output.txt"
                ),
                "results/v162/workstation_tests/test_receipt.json": rel_ident(
                    "results/v162/workstation_tests/test_receipt.json"
                ),
                "results/v162/workstation_tests/pytest_outcomes.json": rel_ident(
                    "results/v162/workstation_tests/pytest_outcomes.json"
                ),
            },
            snapshot_of_first_run=dict(
                directory="results/v162/deployment_repair_evidence/first_failed_run_snapshot",
                note="Byte copies taken before any state was changed; manifest with sha256 beside them.",
                manifest=rel_ident(
                    "results/v162/deployment_repair_evidence/first_failed_run_snapshot/sha256_manifest.json"
                ),
            ),
            snapshot_of_first_run_pack=dict(
                directory="results/v162/deployment_repair_evidence/first_failed_run_pack",
                note="The first-run report pack (a returned ZIP is not a science pass).",
                zip_sha256=sha(EV / "first_failed_run_pack/iscat_v162_return.zip"),
                zip_bytes=(EV / "first_failed_run_pack/iscat_v162_return.zip").stat().st_size,
            ),
        ),
        root_cause=dict(
            summary=(
                "The frozen test module defines a module-level helper `def setup(theta=None)` "
                "(tests/test_v162.py:14). pytest 7.4.0 still ships the deprecated builtin 'nose' plugin "
                "(_pytest/nose.py), which is listed in pytest.config.default_plugins and therefore stays "
                "loaded even though the bundle runner sets PYTEST_DISABLE_PLUGIN_AUTOLOAD=1. With that "
                "plugin active, Module._inject_setup_module_fixture hijacks any callable module-level "
                "`setup` as a nose-style setup hook and invokes it as setup(<Module ...>), so the helper "
                "received a module object as `theta`."
            ),
            mechanism_citations=[
                "_pytest/python.py:543 has_nose = self.config.pluginmanager.has_plugin('nose')",
                "_pytest/python.py:547-551 falls back to _get_first_non_fixture_func(self.obj, ('setup',))",
                "_pytest/nose.py pytest_runtest_setup -> call_optional(..., 'setup', nodeid)",
                "pytest.config.default_plugins contains 'nose' (verified in the installed 7.4.0)",
                "pytest.config.essential_plugins does NOT contain 'nose'",
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD only suppresses setuptools entry-point autoloading, "
                "not builtin default plugins",
            ],
            observed_exception=(
                "TypeError: float() argument must be a string or a real number, not 'module' at "
                "code/v152_gls_core.py:24, raised from tests/test_v162.py:20 with "
                "theta = <module 'test_v162' ...>"
            ),
            exception_count=25,
            affected_nodeids=25,
            tests_passed_in_first_run=197,
            tests_collected=222,
            interpretation=(
                "This is a harness-level name collision in the frozen bundle's test module, not a defect "
                "in the approved GLS/design/optics cores and not a scientific result. pytest >= 8.0 "
                "removed the nose plugin entirely, so the intended semantics (the helper is called "
                "explicitly by the tests) is also the post-8.0 semantics."
            ),
            disclosure=(
                "The frozen package as shipped cannot pass the full suite under pytest 7.x without the "
                "opt-out. This is a real defect of the delivered package and is reported as such."
            ),
        ),
        repair=dict(
            what_was_changed=(
                "Ambient interpreter/deployment condition only: the deprecated builtin 'nose' plugin is "
                "disabled for the test session via an environment variable."
            ),
            environment_variable=dict(
                name="PYTEST_ADDOPTS", value="-p no:nose", scope="the resumed run_all process only"
            ),
            package_bytes_changed=0,
            checks_deleted=0,
            math_cores_changed=0,
            launcher_single_shot_evidence=dict(
                guard="v162_bootstrap.py environment_check raises "
                "V162_BRANCH_EXISTS_NO_AUTOMATIC_RESET_OR_RERUN when refs/heads/v162 exists",
                guard_file="package/code/v162_bootstrap.py in the launcher evidence directory",
                consequence="The launcher cannot be re-run for this worktree by design; the resume uses "
                "exactly the launcher's own second stage: <worktree>/tools/v162_bundle/run_all.py --repo <worktree>.",
            ),
            a_b_evidence=dict(
                script=str(EV / "ab_nose_plugin_reproduction.py"),
                summary=ident(EV / "ab_nose_plugin_summary.json"),
                without_optout=dict(
                    env=staged["without_optout"]["env"],
                    returncode=staged["without_optout"]["returncode"],
                    outcomes=staged["without_optout"]["outcomes"],
                    output_sha256=staged["without_optout"]["output_sha256"],
                ),
                with_no_nose_optout=dict(
                    env=staged["with_no_nose_optout"]["env"],
                    returncode=staged["with_no_nose_optout"]["returncode"],
                    outcomes=staged["with_no_nose_optout"]["outcomes"],
                    output_sha256=staged["with_no_nose_optout"].get("output_sha256"),
                ),
                scope_limit=ab["note"],
                independently_reconfirmed=True,
            ),
            package_byte_identity=dict(
                report="results/v162/deployment_repair_evidence/payload_vs_installed_verification.json",
                generator="results/v162/deployment_repair_evidence/payload_vs_installed_verification.py",
                verdict=payload_check["verdict"],
                manifest_rows=payload_check["manifest_rows"],
                checked_files=payload_check["checked_files"],
                mismatches=len(payload_check["mismatches"]),
                embedded_payload_sha256=payload_check["embedded_payload_sha256"],
                note="Every file listed in the launcher payload manifest is byte-identical to the "
                "installed bundle, so the re-test runs the original package, not a patched copy.",
            ),
            reverted_edit=dict(
                directory="results/v162/deployment_repair_evidence/runner_edit_reverted_before_commit",
                path_rel=revert["path_rel"],
                before_revert=revert["before_revert"],
                head_blob=revert["head_blob"],
                head_blob_id=revert["head_blob_id"],
                status_after_revert="git status clean; working-tree bytes equal HEAD blob",
                disclosure=(
                    "During the first repair investigation one bundle file "
                    "(tools/v162_bundle/run_workstation_tests.py) was edited in the working tree. That "
                    "edit is disclosed here, was fully reverted to the exact HEAD blob before any commit "
                    "and before any model call, and its bytes and diff are preserved. The package-byte "
                    "identity check above was run after the revert."
                ),
            ),
            superseded_earlier_report=dict(
                path="results/v162/deployment_repair_evidence/bundle_vs_payload_diff.json",
                note="Recorded the pre-revert state (exactly one differing file). Superseded by "
                "payload_vs_installed_verification.json; kept unmodified as history.",
            ),
            resume_command=[
                r"C:\ProgramData\anaconda3\python.exe",
                str(ROOT / "tools/v162_bundle/run_all.py"),
                "--repo",
                str(ROOT),
            ],
            resume_environment=dict(
                PYTEST_ADDOPTS="-p no:nose",
                PYTHONDONTWRITEBYTECODE="1",
                PYTHONPATH="<removed>",
                note="run_workstation_tests.py sets PYTHONPATH=<bundle>/code, "
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 and PYTHONDONTWRITEBYTECODE=1 for the child pytest "
                "itself, exactly as in the first run.",
            ),
        ),
        residual_risks=[
            "The opt-out is supplied by the caller, not by the frozen package; a fresh checkout of the "
            "bundle on another pytest 7.x station needs the same documented opt-out or a pytest >= 8.",
            "Disabling the nose plugin also disables nose-style module-level setup/teardown for every "
            "test module in this bundle; tests/test_v162.py is the only module that defines one.",
            "A passing suite remains a software result only and is not optical, physical or "
            "experimental acceptance.",
        ],
        status_vocabulary=dict(
            tests_first_run="FAILED",
            deployment_condition="REPAIRED_BEFORE_RETEST",
            package_bytes="UNCHANGED_AND_VERIFIED_AGAINST_PAYLOAD_MANIFEST",
            model_calls_before_repair=0,
            ledger_before_repair="NOT_CREATED",
        ),
    )
    (EV / "deployment_repair_record.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )

    md = [
        "# V162 deployment-condition repair record",
        "",
        "Contract section 4 permits repairing the real deployment condition and re-testing the "
        "original package, provided no V162 model ledger and no model call exist yet. Both conditions "
        "held: `results/v162/logs/v162_budget.sqlite` did not exist, and 0 model forward calls had been made.",
        "",
        "## First run (kept as history)",
        "",
        f"- launcher evidence dir: `{LAUNCHER}`",
        f"- launcher returncode: 2 (prepare 0, run_all 2, final_pack 0)",
        f"- stage states: `{json.dumps(stage_states)}`",
        f"- tests: 197 passed, 25 errored, 222 collected; first run stopped at the `tests` stage",
        "- byte snapshots: `deployment_repair_evidence/first_failed_run_snapshot/` and "
        "`.../first_failed_run_pack/`",
        "",
        "## Root cause (source-level)",
        "",
        "The frozen test module defines a module-level helper `def setup(theta=None)` at "
        "`tests/test_v162.py:14`. pytest 7.4.0 still ships the deprecated builtin `nose` plugin "
        "(`_pytest/nose.py`), which is listed in `pytest.config.default_plugins`; "
        "`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` (set by the bundle runner) only suppresses setuptools "
        "entry-point autoloading and does not remove builtin default plugins. "
        "`_pytest/python.py:543` then evaluates `has_plugin('nose')`, `:547-551` falls back to "
        "`_get_first_non_fixture_func(self.obj, ('setup',))`, and the injected module fixture calls "
        "`setup(<Module test_v162>)`. The helper passes that module object into `check_theta`, producing",
        "",
        "```",
        "TypeError: float() argument must be a string or a real number, not 'module'",
        "  code/v152_gls_core.py:24  <- tests/test_v162.py:20",
        "```",
        "",
        "for all 25 tests of that module. pytest >= 8.0 removed the nose plugin entirely, so the "
        "intended semantics is the post-8.0 semantics. This is a real defect of the delivered package "
        "and is reported as such; it is not a defect of the approved GLS/design/optics cores.",
        "",
        "## Repair actually applied",
        "",
        "- `PYTEST_ADDOPTS=-p no:nose` for the resumed run only (plus `PYTHONDONTWRITEBYTECODE=1`, "
        "`PYTHONPATH` removed from the outer environment).",
        "- Package bytes changed: **0**. Checks deleted: **0**. Math cores changed: **0**.",
        f"- Payload-vs-installed verdict: `{payload_check['verdict']}` "
        f"({payload_check['checked_files']} files, {len(payload_check['mismatches'])} mismatches, "
        f"embedded payload sha256 `{payload_check['embedded_payload_sha256']}`).",
        "- A/B: without the opt-out 25 setup errors (rc 1); with it 25/25 nodes pass setup+call+teardown "
        "(rc 0). Focal scope only; the official receipt is the 222-node re-run.",
        "",
        "## Disclosed deviation and its reversal",
        "",
        "During the first repair investigation, one bundle file "
        "(`tools/v162_bundle/run_workstation_tests.py`) was edited in the working tree. It was reverted "
        "to the exact HEAD blob (`517ccaec0a824cf1f39847937104fb353bb1b774`, 2304 bytes, sha256 "
        "`9a5482314e31c705d03ddb49a4643e3630b64f2ea0917f163d96df8555ac611d`) before any commit and "
        "before any model call; the pre-revert bytes, the restored bytes and the diff are preserved in "
        "`deployment_repair_evidence/runner_edit_reverted_before_commit/`. `git status` is clean and the "
        "preflight blob check passes on the restored bytes.",
        "",
        "## Why the launcher itself was not re-run",
        "",
        "`package/code/v162_bootstrap.py::environment_check` raises "
        "`V162_BRANCH_EXISTS_NO_AUTOMATIC_RESET_OR_RERUN` when `refs/heads/v162` exists, so the launcher "
        "is single-shot for this worktree by design. The resume therefore executes exactly the "
        "launcher's own second stage, in the same worktree and with the same command line:",
        "",
        "```",
        r"C:\ProgramData\anaconda3\python.exe C:\iscat\v162\tools\v162_bundle\run_all.py --repo C:\iscat\v162",
        "```",
        "",
        "## Residual risk",
        "",
    ] + [f"- {r}" for r in record["residual_risks"]] + [
        "",
        "A passing suite is a software result only; it is not optical, physical or experimental acceptance.",
    ]
    (EV / "deployment_repair_record.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    json.dump(
        dict(
            json_sha256=sha(EV / "deployment_repair_record.json"),
            md_sha256=sha(EV / "deployment_repair_record.md"),
            json_bytes=(EV / "deployment_repair_record.json").stat().st_size,
            md_bytes=(EV / "deployment_repair_record.md").stat().st_size,
        ),
        sys.stdout,
        indent=2,
    )
    print()


if __name__ == "__main__":
    main()
