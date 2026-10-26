# V163 execution truth report

```json
{
  "stage_state_evidence": [
    {
      "tests": "FINISHED",
      "preflight": "FINISHED",
      "execute": "FINISHED",
      "verify": "FINISHED"
    }
  ],
  "task_id": "V163_ISOLATED_DEPLOYMENT_AND_FINITE_HEIGHT_VALIDATION",
  "execution_state": "FINISHED",
  "required_outputs": {
    "preflight.json": true,
    "selected_candidates_12.json": true,
    "design/saved_array_designs.json": true,
    "logs/v163_budget.sqlite": true,
    "status.json": true,
    "verification.json": true,
    "workstation_tests/test_receipt.json": true
  },
  "missing": [],
  "failure_files": [],
  "budget": {
    "task_counts": [
      [
        "FINAL_VERIFY",
        1,
        20,
        18
      ],
      [
        "NONLINEAR_PROBES",
        3,
        120,
        72
      ],
      [
        "REPAIR_AND_ANCHOR",
        2,
        226,
        183
      ]
    ],
    "attempt_states": [
      [
        "RETURNED",
        273
      ]
    ],
    "integrity": "ok"
  },
  "verification_present": true,
  "all_reportable_D_null": true,
  "experimental_absolute_diameter_validated": false,
  "scientific_scope": "CONDITIONAL_LOCAL_DESIGN_AND_DISCRETE_PATH_ONLY",
  "not_a_precision_claim": true
}
```
