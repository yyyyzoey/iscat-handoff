# Prior CSV evidence problems (carried into v073 with fixes)

1. `v072 tables/fft_analytic_fixtures.csv`: F12 `phase_wrapdiff` field contained `U+0000`
   (numeric `pdiff=0` printed via `%s`). Fixed by IO_CSV fixture + typed serialization;
   original file preserved untouched.
2. `v072 tables/controlled_ledger_reconciled.csv`: `D_nm,zf_nm` empty because
   `find(strcmp(cid,sprintf('K%02d',1:6)))` returns [] (sprintf concatenates, not a list);
   `render_source_sha256`/`wrapper_source_sha256` columns swapped. Fixed in
   `tables/controlled_ledger_v073_verified.csv` using `r.cfg.particle.diameter_nm`,
   `r.cfg.focus_nm(3)`, and corrected SHA semantics. Original v072 table untouched.
3. `v072 tables/fft_replay_one_case.csv`: frequency rows INVALID_FFT_AXIS (see
   v072_wrong_axis record). meanFloor/mask values re-confirmed identical in v073.
4. `v071 tables/controlled_plan24_v071.csv` name says "24" but holds 36 rows
   (24 sides + 12 NOT_EXECUTABLE): naming kept for lineage, counts documented in status.
