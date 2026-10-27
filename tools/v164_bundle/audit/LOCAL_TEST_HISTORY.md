# Local test history and scope

The final complete suite actually returned 65 passed, with 195 setup/call/teardown reports, and the production receipt validator accepted it.

Earlier development checks are not counted as final validation:
- Several full-suite attempts were externally timed out before a completed receipt. They are not treated as PASS.
- The original mutation tests redundantly repeated an identical synthetic 24-task workflow. They now execute that workflow once and copy its immutable results for corruption tests; the actual execute/verify path still runs.
- A local text edit accidentally changed the receipt inventory path expression to a tuple. Although its then-59 tests passed, the production receipt validator raised AttributeError. The expression was corrected and five receipt roundtrip/failure tests were added.
- A failed-closeout archive test was subsequently added. The final full 65-test run and receipt verification both completed successfully.

No real F2c, BEM, physical render, camera exposure or noise simulation was run in this review environment. Temporary Git worktrees and synthetic image functions are test fixtures, not experimental validation. Windows integration remains to be performed by Codex.
