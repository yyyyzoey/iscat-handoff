# v089 wrong-table evidence index (read-only)

The v089 published `analysis/v089_estimator_comparison12.csv` (Git blob
`adf7a53cb07808c8f3b131547dc23b0fae03ae1f5f5df8d9bb8fa2307007a12b` SHA-256 of
the file content) contains the frequency-key overwrite defect: D2/D3 rows for
200/400 Hz hold the 420 Hz maps because the summary dict was keyed
(model, window) without the frequency.

v090 disposition: the 4 affected rows are corrected in
`tables/analysis v090_legacy_vs_corrected12.csv`; the v089 file is preserved
read-only and must not be regenerated. The NPZ
`analysis/v089_estimator_comparison_arrays.npz`
(SHA-256 c75fd800ded350c848c69376bddf30689c8df8e0e57e009da1f238ea5eae10e7)
saved all 24 maps with full frequency keys and is the recovery source.
