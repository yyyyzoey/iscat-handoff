# V163: one-path source reconciliation; finish the remaining finite-height validation

Use the supplied `iscat_v163_launcher.pyz` intact:

```powershell
python -I "<download>\iscat_v163_launcher.pyz" --source-repo "C:\iscat\v162" --worktree "C:\iscat\v163"
```

The source repository HEAD must descend from the V162 executed code commit `dc919aada7cc750c19383470021878fab5814db5`. The actual parent is recorded; old results and ledgers are never reset. The target path and branch must not already exist.

Read `00_V163_Codex_唯一执行合同.md`. This version fixes exactly the confirmed LF/CRLF source pin contradiction, with dual original/runtime provenance and exact archived bytes; it does not waive hashes, alter historical configuration or change the optical/mathematical kernels.

The module-level `setup` test helper is renamed to avoid pytest 7.x nose semantics. All test assertions remain. Complete test receipts and 247 actual local tests, rather than a hand-entered count, are required. Workstation execution still has to pass.

Previous V162 1224 matrix evaluations are retained and checked against the frozen arrays. No fitting, new noise, BEM, render, camera exposure, Jacobian batch or second focus is allowed. Maximum new model attempts: 500 including loader selfchecks; the new ledger is independent of the sealed zero-call V162 failure.

The new return includes the 12 locked source diagnostic files so an offline reviewer can reconstruct pixel Jacobians and design coefficients.
