# V162 deployment-condition repair record

Contract section 4 permits repairing the real deployment condition and re-testing the original package, provided no V162 model ledger and no model call exist yet. Both conditions held: `results/v162/logs/v162_budget.sqlite` did not exist, and 0 model forward calls had been made.

## First run (kept as history)

- launcher evidence dir: `C:\iscat\v162_launcher_f32d0e154d434bc79516ae32779a7a5a`
- launcher returncode: 2 (prepare 0, run_all 2, final_pack 0)
- stage states: `{"tests": "BLOCKED_OR_FAILED", "preflight": "NOT_STARTED", "execute": "NOT_STARTED", "verify": "NOT_STARTED"}`
- tests: 197 passed, 25 errored, 222 collected; first run stopped at the `tests` stage
- byte snapshots: `deployment_repair_evidence/first_failed_run_snapshot/` and `.../first_failed_run_pack/`

## Root cause (source-level)

The frozen test module defines a module-level helper `def setup(theta=None)` at `tests/test_v162.py:14`. pytest 7.4.0 still ships the deprecated builtin `nose` plugin (`_pytest/nose.py`), which is listed in `pytest.config.default_plugins`; `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` (set by the bundle runner) only suppresses setuptools entry-point autoloading and does not remove builtin default plugins. `_pytest/python.py:543` then evaluates `has_plugin('nose')`, `:547-551` falls back to `_get_first_non_fixture_func(self.obj, ('setup',))`, and the injected module fixture calls `setup(<Module test_v162>)`. The helper passes that module object into `check_theta`, producing

```
TypeError: float() argument must be a string or a real number, not 'module'
  code/v152_gls_core.py:24  <- tests/test_v162.py:20
```

for all 25 tests of that module. pytest >= 8.0 removed the nose plugin entirely, so the intended semantics is the post-8.0 semantics. This is a real defect of the delivered package and is reported as such; it is not a defect of the approved GLS/design/optics cores.

## Repair actually applied

- `PYTEST_ADDOPTS=-p no:nose` for the resumed run only (plus `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH` removed from the outer environment).
- Package bytes changed: **0**. Checks deleted: **0**. Math cores changed: **0**.
- Payload-vs-installed verdict: `ALL_MANIFEST_ROWS_BYTE_IDENTICAL` (50 files, 0 mismatches, embedded payload sha256 `4dc3f129f46110002dd5c56b7186794a20cfddfafc8e5a1d77cad44a902f840b`).
- A/B: without the opt-out 25 setup errors (rc 1); with it 25/25 nodes pass setup+call+teardown (rc 0). Focal scope only; the official receipt is the 222-node re-run.

## Disclosed deviation and its reversal

During the first repair investigation, one bundle file (`tools/v162_bundle/run_workstation_tests.py`) was edited in the working tree. It was reverted to the exact HEAD blob (`517ccaec0a824cf1f39847937104fb353bb1b774`, 2304 bytes, sha256 `9a5482314e31c705d03ddb49a4643e3630b64f2ea0917f163d96df8555ac611d`) before any commit and before any model call; the pre-revert bytes, the restored bytes and the diff are preserved in `deployment_repair_evidence/runner_edit_reverted_before_commit/`. `git status` is clean and the preflight blob check passes on the restored bytes.

## Why the launcher itself was not re-run

`package/code/v162_bootstrap.py::environment_check` raises `V162_BRANCH_EXISTS_NO_AUTOMATIC_RESET_OR_RERUN` when `refs/heads/v162` exists, so the launcher is single-shot for this worktree by design. The resume therefore executes exactly the launcher's own second stage, in the same worktree and with the same command line:

```
C:\ProgramData\anaconda3\python.exe C:\iscat\v162\tools\v162_bundle\run_all.py --repo C:\iscat\v162
```

## Residual risk

- The opt-out is supplied by the caller, not by the frozen package; a fresh checkout of the bundle on another pytest 7.x station needs the same documented opt-out or a pytest >= 8.
- Disabling the nose plugin also disables nose-style module-level setup/teardown for every test module in this bundle; tests/test_v162.py is the only module that defines one.
- A passing suite remains a software result only and is not optical, physical or experimental acceptance.

A passing suite is a software result only; it is not optical, physical or experimental acceptance.
