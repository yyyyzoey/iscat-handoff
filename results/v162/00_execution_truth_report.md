# V162 execution truth report

```json
{
  "stage_state_evidence": [
    {
      "tests": "BLOCKED_OR_FAILED",
      "preflight": "NOT_STARTED",
      "execute": "NOT_STARTED",
      "verify": "NOT_STARTED"
    },
    {
      "tests": "FINISHED",
      "preflight": "FINISHED",
      "execute": "BLOCKED_OR_FAILED",
      "verify": "NOT_STARTED"
    }
  ],
  "task_id": "V162_ISOLATED_DEPLOYMENT_AND_FINITE_HEIGHT_VALIDATION",
  "execution_state": "BLOCKED_OR_FAILED_NO_FINAL_STATUS",
  "required_outputs": {
    "preflight.json": true,
    "selected_candidates_12.json": false,
    "design/saved_array_designs.json": true,
    "logs/v162_budget.sqlite": true,
    "status.json": false,
    "verification.json": false,
    "workstation_tests/test_receipt.json": true
  },
  "missing": [
    "selected_candidates_12.json",
    "status.json",
    "verification.json"
  ],
  "failure_files": [
    "failures\\000.json"
  ],
  "budget": {
    "task_counts": [
      [
        "REPAIR_AND_ANCHOR",
        1,
        100,
        0
      ]
    ],
    "attempt_states": [],
    "integrity": "ok"
  },
  "verification_present": false,
  "all_reportable_D_null": true,
  "experimental_absolute_diameter_validated": false,
  "scientific_scope": "CONDITIONAL_LOCAL_DESIGN_AND_DISCRETE_PATH_ONLY",
  "not_a_precision_claim": true
}
```
