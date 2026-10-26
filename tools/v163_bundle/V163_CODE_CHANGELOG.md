# V163 changes relative to the supplied V162 approved package

1. Versioned deployment/driver labels only; the seven science and accounting cores remain byte-identical to `config/kernel_lock.json`.
2. New `v163_source_bridge.py`: accepts only the two reviewed whole-file identities and their exact 129-CRLF difference. New worktree restoration copies the archived Git blob to ONE tool path. Original history is preserved. The old runtime source pin and config are unchanged.
3. Preflight verifies all configured runtime source pins before model task reservation. The coordinated source blob must be committed. New branch parent is the actual source HEAD descended from V162 code commit, not a guessed result SHA.
4. `tests/test_v163.py` ordinary `setup` helper renamed to `make_case`, all assertions unchanged. No nose-plugin waiver is required. Caller PYTEST_ADDOPTS is ignored and recorded; actual pytest version is recorded.
5. `v163_design_reuse.py`: compares all 1224 prior matrix conditions against the recalculated frozen-array evaluations without new optical calls.
6. Return copies twelve verified original V156 result files and their hashes for self-contained offline audit.
7. Added 25 source-bridge/reuse/context regressions to the original 222 tests (247 total). Original science fixture assertions remain.
8. Tests are local component/Git fixture/synthetic-model evidence, not Windows real-F2c verification. All first local development receipts are retained under audit when included.
