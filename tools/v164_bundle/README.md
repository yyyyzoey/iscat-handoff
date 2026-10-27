# V164: bounded fixed-D conditional model-separation experiment

Read `00_V164_Codex_唯一执行合同.md` before executing. The only approved parent is V163 `06c54419c590b6ddadc50cd6117a7a54b2cf5ddf`.

Recommended single-file command:

```powershell
python -I "<download>\iscat_v164_launcher.pyz" --source-repo "C:\iscat\v163" --worktree "C:\iscat\v164"
```

The target directory must not exist. Do not manually create the branch or flatten package files. The launcher verifies the embedded complete package, creates a new worktree, commits the package, runs all 65 new tests, then executes preflight / profiles / verification / archive. Existing ledgers are never automatically retried.

The new science is 24 fixed-D nuisance-only optimization tasks, not a rerun of V163 or a new measured diameter estimate. Maximum 10,000 model attempts including loader and verification. Three prior core files remain byte-identical. No new BEM/render/camera/noise/full-Jacobian batch.

Local test evidence and earlier local test failures are in `audit/`. Local tests used synthetic optics, not real F2c. A failed or incomplete optimization retains a feasible upper bound; it does not certify uniqueness or calibrated uncertainty.
