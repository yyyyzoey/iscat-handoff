# iscat-handoff v073

Readable handoff after the v073 round (v072 replay FFT-axis correction + 400 Hz primary observable).

- `status.json` / `review.md` - three-field statuses and the round narrative.
- `tables/` - axis negative tests, fixture corrections (F07/F09/F10/F12 gaps closed), bin audit, corrected replay summary (replaces v072 INVALID rows), 12-pixel direct-DFT checks + independent recheck, spectral neighborhood, mask/quality, verified controlled ledger (real D/zf, fixed SHA semantics), physical input gap, cost ledger, 2001-frame input provenance (SHA-256 each).
- `numeric/` - small ROI + control mats, analytic fixture examples, numeric_inventory.json (workstation-only full arrays with sha/status).
- `experimental/` - 520 nm user-confirmed inputs, formal 400 Hz observable contract, extractor versions.
- `history/` - v072 wrong-axis frozen record and prior CSV evidence problems.
- `source/` - extract_fft_v073.m and all v073 entry points (original user scripts unmodified).
