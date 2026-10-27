# V164 execution truth report

```json
{
  "required_outputs": {
    "preflight.json": true,
    "profiles_all.json": true,
    "pooled_all.json": true,
    "logs/v164_budget.sqlite": true,
    "verification.json": true,
    "workstation_tests/test_receipt.json": true
  },
  "missing_outputs": [],
  "actual_stage_commands": [
    [
      {
        "stage": "tests",
        "command": [
          "C:\\ProgramData\\anaconda3\\python.exe",
          "C:\\iscat\\v164\\tools\\v164_bundle\\run_workstation_tests.py",
          "--out",
          "C:\\iscat\\v164\\results\\v164\\workstation_tests"
        ],
        "returncode": 0,
        "stdout": "4cfebbe7b33f47c39089025106c362fe_tests.stdout",
        "stderr": "4cfebbe7b33f47c39089025106c362fe_tests.stderr"
      },
      {
        "stage": "preflight",
        "command": [
          "C:\\ProgramData\\anaconda3\\python.exe",
          "C:\\iscat\\v164\\tools\\v164_bundle\\code\\v164_run.py",
          "--repo",
          "C:\\iscat\\v164",
          "--mode",
          "preflight"
        ],
        "returncode": 0,
        "stdout": "4cfebbe7b33f47c39089025106c362fe_preflight.stdout",
        "stderr": "4cfebbe7b33f47c39089025106c362fe_preflight.stderr"
      },
      {
        "stage": "execute",
        "command": [
          "C:\\ProgramData\\anaconda3\\python.exe",
          "C:\\iscat\\v164\\tools\\v164_bundle\\code\\v164_run.py",
          "--repo",
          "C:\\iscat\\v164",
          "--mode",
          "execute"
        ],
        "returncode": 0,
        "stdout": "4cfebbe7b33f47c39089025106c362fe_execute.stdout",
        "stderr": "4cfebbe7b33f47c39089025106c362fe_execute.stderr"
      },
      {
        "stage": "verify",
        "command": [
          "C:\\ProgramData\\anaconda3\\python.exe",
          "C:\\iscat\\v164\\tools\\v164_bundle\\code\\v164_run.py",
          "--repo",
          "C:\\iscat\\v164",
          "--mode",
          "verify"
        ],
        "returncode": 0,
        "stdout": "4cfebbe7b33f47c39089025106c362fe_verify.stdout",
        "stderr": "4cfebbe7b33f47c39089025106c362fe_verify.stderr"
      }
    ]
  ],
  "status": {
    "EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED": false,
    "actual_calls": {
      "BINDING": 6,
      "FINAL_VERIFY": 27,
      "LOADER_1": 70,
      "PROFILE_100000_ANON_02_m5_exact_height": 34,
      "PROFILE_100000_ANON_02_m5_free_hxy": 56,
      "PROFILE_100000_ANON_02_m5_height_sigma1": 63,
      "PROFILE_100000_ANON_02_m5_height_sigma10": 62,
      "PROFILE_100000_ANON_02_p5_exact_height": 34,
      "PROFILE_100000_ANON_02_p5_free_hxy": 49,
      "PROFILE_100000_ANON_02_p5_height_sigma1": 63,
      "PROFILE_100000_ANON_02_p5_height_sigma10": 56,
      "PROFILE_100000_ANON_03_m5_exact_height": 39,
      "PROFILE_100000_ANON_03_m5_free_hxy": 55,
      "PROFILE_100000_ANON_03_m5_height_sigma1": 56,
      "PROFILE_100000_ANON_03_m5_height_sigma10": 49,
      "PROFILE_100000_ANON_03_p5_exact_height": 34,
      "PROFILE_100000_ANON_03_p5_free_hxy": 55,
      "PROFILE_100000_ANON_03_p5_height_sigma1": 63,
      "PROFILE_100000_ANON_03_p5_height_sigma10": 50,
      "PROFILE_100000_ANON_04_m5_exact_height": 34,
      "PROFILE_100000_ANON_04_m5_free_hxy": 63,
      "PROFILE_100000_ANON_04_m5_height_sigma1": 63,
      "PROFILE_100000_ANON_04_m5_height_sigma10": 62,
      "PROFILE_100000_ANON_04_p5_exact_height": 34,
      "PROFILE_100000_ANON_04_p5_free_hxy": 62,
      "PROFILE_100000_ANON_04_p5_height_sigma1": 63,
      "PROFILE_100000_ANON_04_p5_height_sigma10": 55
    },
    "all_reportable_D_null": true,
    "calibrated_confidence_intervals": false,
    "common_pools": 6,
    "conditional_anchor_design": true,
    "execution_state": "FINISHED",
    "globally_certified_minima": false,
    "no_experimental_height_observation": true,
    "partial_search_tasks": 0,
    "profiles": 24
  },
  "verification_present": true,
  "failures": [],
  "all_reportable_D_null": true,
  "EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED": false
}
```

Conditional model-separation bounds only; no experimental diameter or independent height measurement is certified.
