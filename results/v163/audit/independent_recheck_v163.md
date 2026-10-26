# V163 independent recheck (read-only)

- verdict: `MECHANICALLY_AND_NUMERICALLY_RECONSISTENT`
- zip: `C:\iscat\v163\results\v163\iscat_v163_return.zip`
- zip sha256: `9bc04fc03ea194ae4b1abaf61baa2b73a7d843679df67d71f3114ffb820bd8b7` (2235181 bytes)
- members: 454, manifest rows: 453
- failed checks: none
- scope: STRUCTURAL_AND_NUMERIC_RECONSTRUCTION_ONLY_NOT_SCIENTIFIC_ACCEPTANCE

## Ledger (read-only re-derivation)

- integrity_check: `ok`
- total used: 273 / 500
- reserved per phase: {'FINAL_VERIFY': 20, 'NONLINEAR_PROBES': 120, 'REPAIR_AND_ANCHOR': 226}
- attempts by state: {'RETURNED': 273}

| task | cap | used | state | sealed |
|---|---:|---:|---|---|
| FINAL_VERIFY | 20 | 18 | FINISHED | True |
| PROBE_100000_ANON_02 | 40 | 24 | FINISHED | True |
| PROBE_100000_ANON_03 | 40 | 24 | FINISHED | True |
| PROBE_100000_ANON_04 | 40 | 24 | FINISHED | True |
| ANCHORS | 126 | 113 | FINISHED | True |
| LOADER_1 | 100 | 70 | FINISHED | True |

## Tests

- collected nodes: 247, phase reports: 741
- report outcomes: {'passed': 741}
- collection errors: 0, scope: `COMPONENT_AND_SYNTHETIC_MODEL_TESTS_NOT_PHYSICAL_VALIDATION`

## Probes

- 100000_ANON_02: n=24 min=0.000557165 median=0.541691 max=1.11322 <=0.05(diagnostic)=8
- 100000_ANON_03: n=24 min=0.00176012 median=0.0477456 max=0.312621 <=0.05(diagnostic)=12
- 100000_ANON_04: n=24 min=0.0215152 median=0.850997 max=1.13247 <=0.05(diagnostic)=4

max reconstruction deviations:

- Q_change_identity: max_abs=1.48e-13 max_rel=9.13e-10
- Q_cross_term: max_abs=8.88e-16 max_rel=9.07e-12
- Q_joint_equals_Q_model_plus_K: max_abs=1.14e-13 max_rel=2.39e-16
- Q_model_at_proposal: max_abs=5.68e-14 max_rel=3.84e-16
- anchor_Q_joint: max_abs=5.68e-14 max_rel=1.2e-16
- anchor_Q_model: max_abs=0 max_rel=0
- anchor_theta_matches_selected_anchor: max_abs=0 max_rel=0
- image_distance_squared: max_abs=2.22e-16 max_rel=3.22e-16
- predicted_image_distance_squared: max_abs=0 max_rel=0
- relative_linearization_error: max_abs=2.22e-16 max_rel=1.2e-13
- theta_equals_anchor_plus_step: max_abs=0 max_rel=0
- whitened_jacobian_reconstruction: max_abs=1.11e-16 max_rel=1.82e-16

declared status: `{"EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED": false, "all_reportable_D_null": true, "execution_state": "FINISHED", "global_uniqueness_certified": false, "verification_new_model_calls": 0, "verification_status": "SAVED_FILE_IDENTITIES_AND_DESIGNS_VERIFIED_NOT_EXPERIMENTAL_VALIDATION"}`
