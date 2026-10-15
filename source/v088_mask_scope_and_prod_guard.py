# -*- coding: utf-8 -*-
"""v088 Phase C: mask-scope contract through the REAL production entry.

Two scopes with separate source contracts:
  DEMO_ROI_LOCAL            - floor derived from the map's own Imean
                              (0.01*median positive), per extract_fft_v073
                              applied to the demo ROI;
  EXPERIMENT_FULL_FRAME_SOURCE - the sourced full-frame floor (inherited by
                              the small ROI), NOT the demo-derived value.
All positive and negative cases go through the REAL production functions
(load_double_map / load_experiment_small_roi). 8 tests."""
import os, sys, csv, json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v086_identity_guard as guard
from v083_common import ROOT

GH = os.path.join(ROOT, 'github_handoff')
TAB = os.path.join(GH, 'tables')
NUM = os.path.join(GH, 'numeric')
DISK_MAP = os.path.join(NUM, 'C400_double_D60_zf550_M400_a5.mat')
EXP_ROI = os.path.join(NUM, 'fft400_corrected_small_roi.mat')
FULL = os.path.join(ROOT, 'v073_return', 'numeric', 'fft400_corrected_full.mat')


def main():
    tests = []
    def rec(tid, desc, fn, expect_accept):
        try:
            fn()
            accepted = True
            obs = 'accepted'
        except guard.GuardError as exc:
            accepted = False
            obs = '%s: %s' % (type(exc).__name__, str(exc)[:140])
        tests.append({'test_id': tid, 'description': desc,
                      'expected': 'accept' if expect_accept else 'reject',
                      'observed': obs,
                      'status': 'PASS' if accepted == expect_accept else 'FAIL'})

    # 0) full-frame floor identity (read-only)
    import h5py
    with h5py.File(FULL, 'r') as f:
        floor_stored = float(np.asarray(f['meanFloor']).flatten()[0])
        Im_full = np.asarray(f['Imean']).astype(np.float64)
    pos = Im_full[np.isfinite(Im_full) & (Im_full > 0)]
    floor_calc = 0.01 * float(np.median(pos))
    absd = abs(floor_stored - floor_calc)
    reld = absd / max(abs(floor_stored), 1e-300)
    rows = [{'item': 'full_frame_meanFloor_stored', 'value': '%.17g' % floor_stored},
            {'item': 'full_frame_floor_recomputed_0.01median_positive', 'value': '%.17g' % floor_calc},
            {'item': 'abs_diff', 'value': '%.17g' % absd},
            {'item': 'rel_diff', 'value': '%.17g' % reld},
            {'item': 'identity_status', 'value': 'CONFIRMED_SINGLE_PRECISION_ROUNDING' if reld < 1e-5 else 'MISMATCH'},
            {'item': 'small_ROI_inheritance', 'value': 'EXPERIMENT_FULL_FRAME_SOURCE floor inherited by fft400_corrected_small_roi.mat'}]
    with open(os.path.join(TAB, 'v088_experimental_full_floor_identity.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(['item', 'value']); w.writerows(rows)
    EXP_FLOOR = floor_stored  # sourced full-frame threshold

    # 1) POS demo disk map, DEMO_ROI_LOCAL
    rec('MS-01', 'demo disk map via real loader, DEMO_ROI_LOCAL scope',
        lambda: guard.load_double_map(DISK_MAP, 'D60_zf550_M400_a5', mask_scope='DEMO_ROI_LOCAL'),
        expect_accept=True)
    # 2) POS experimental small ROI, EXPERIMENT_FULL_FRAME_SOURCE
    rec('MS-02', 'experimental small ROI via real loader, EXPERIMENT_FULL_FRAME_SOURCE (sourced floor)',
        lambda: guard.load_experiment_small_roi(EXP_ROI, EXP_FLOOR),
        expect_accept=True)
    # 3) NEG: missing/unknown scope
    rec('MS-03', 'load_double_map without explicit mask_scope contract',
        lambda: guard.load_double_map(DISK_MAP, 'D60_zf550_M400_a5', mask_scope='SOME_UNDEFINED_SCOPE'),
        expect_accept=False)
    # 4) NEG: scope misuse - experiment floor passed to DEMO scope
    rec('MS-04', 'EXPERIMENT floor passed while DEMO_ROI_LOCAL scope derives its own',
        lambda: guard.load_double_map(DISK_MAP, 'D60_zf550_M400_a5', mask_scope='DEMO_ROI_LOCAL',
                                      mean_floor=EXP_FLOOR),
        expect_accept=False)
    # 5) NEG: EXPERIMENT scope without sourced floor
    rec('MS-05', 'EXPERIMENT_FULL_FRAME_SOURCE without sourced floor',
        lambda: guard.load_experiment_small_roi(EXP_ROI, None),
        expect_accept=False)
    # 6) NEG: tampered stored mask including a below-floor pixel (demo scope)
    def tamper_mask():
        from scipy.io import loadmat, savemat
        m = loadmat(DISK_MAP)
        m['valid_mask'] = np.ones((41, 41), dtype=bool)
        im = np.asarray(m['Imean_map'], dtype=np.float64).copy()
        im[3, 4] = 1e-12  # far below the derived DEMO_ROI_LOCAL floor
        m['Imean_map'] = im
        tmp = os.path.join(NUM, 'v088_tampered_mask_demo.mat')
        savemat(tmp, {k: v for k, v in m.items() if not k.startswith('__')})
        try:
            guard.load_double_map(tmp, 'D60_zf550_M400_a5', mask_scope='DEMO_ROI_LOCAL')
        finally:
            os.remove(tmp)
    rec('MS-06', 'demo map with all-True stored mask while rule excludes below-floor pixels',
        tamper_mask, expect_accept=False)
    # 7) NEG: NaN in Imean (demo scope, real entry)
    def tamper_nan():
        from scipy.io import loadmat, savemat
        m = loadmat(DISK_MAP)
        im = np.asarray(m['Imean_map'], dtype=np.float64).copy()
        im[9, 9] = np.nan
        m['Imean_map'] = im
        tmp = os.path.join(NUM, 'v088_tampered_nan_demo.mat')
        savemat(tmp, {k: v for k, v in m.items() if not k.startswith('__')})
        try:
            guard.load_double_map(tmp, 'D60_zf550_M400_a5', mask_scope='DEMO_ROI_LOCAL')
        finally:
            os.remove(tmp)
    rec('MS-07', 'demo map with NaN inside Imean', tamper_nan, expect_accept=False)
    # 8) NEG: SHA mismatch through the real entry
    rec('MS-08', 'claimed SHA != actual file bytes (real loader, ledger arg)',
        lambda: guard.load_double_map(DISK_MAP, 'D60_zf550_M400_a5', mask_scope='DEMO_ROI_LOCAL',
                                      sha_ledger={os.path.basename(DISK_MAP): '0' * 64}),
        expect_accept=False)

    fields = ['test_id', 'description', 'expected', 'observed', 'status']
    with open(os.path.join(TAB, 'v088_mask_prod_live_tests.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n'); w.writeheader(); w.writerows(tests)
    # scope source contract
    contract = [
        {'scope': 'DEMO_ROI_LOCAL', 'floor_source': 'the map itself: 0.01*median(positive finite Imean_map) per extract_fft_v073 on the demo ROI',
         'applies_to': 'v085/v086 24 demo double maps', 'notes': 'external floor must match derived; mismatch rejected'},
        {'scope': 'EXPERIMENT_FULL_FRAME_SOURCE', 'floor_source': 'full-frame floor from v073 extractor (0.01*median positive full Imean), inherited by the small ROI',
         'applies_to': 'fft400_corrected_small_roi.mat / fft400_corrected_full.mat', 'notes': 'sourced floor REQUIRED; never the demo-derived value'},
    ]
    with open(os.path.join(TAB, 'v088_mask_scope_source_contract.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['scope', 'floor_source', 'applies_to', 'notes'], lineterminator='\n')
        w.writeheader(); w.writerows(contract)
    with open(os.path.join(TAB, 'v088_mask_prod_live_tests.csv'), 'r', newline='', encoding='utf-8') as f:
        rr = list(csv.reader(f))
    assert len(rr) - 1 == 8 and all(len(x) == len(rr[0]) for x in rr)
    all_pass = all(t['status'] == 'PASS' for t in tests)
    print('[C] summary:', json.dumps({'tests': 8, 'all_pass': bool(all_pass),
                                      'floor_identity_rel_diff': '%.3g' % reld}))
    with open(os.path.join(GH, 'logs', 'v088_phase_c_summary.json'), 'w', encoding='utf-8') as f:
        json.dump({'all_pass': bool(all_pass), 'floor_rel_diff': reld}, f, indent=2)
    if not all_pass:
        sys.exit(2)


if __name__ == '__main__':
    main()
