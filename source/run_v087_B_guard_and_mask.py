# -*- coding: utf-8 -*-
"""v087 Phase B: guard live tests - mask rule recheck through the production
validator, disk-file positive case, and honest bookkeeping fixes:
  - HEAVY_CALLS pseudo-counter removed from claims (marked TEST_FRAMEWORK_LOCAL)
  - NEG-G09 renamed TEST_FRAMEWORK_SELFTEST
  - q/slice geometry proven by versioned source (PROVEN_BY_VERSIONED_SOURCE),
    not claimed as self-contained file metadata."""
import os, sys, csv, json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v086_identity_guard as guard
from v083_common import ROOT

GH = os.path.join(ROOT, 'github_handoff')
TAB = os.path.join(GH, 'tables')
NUM = os.path.join(GH, 'numeric')
DISK_MAP = os.path.join(NUM, 'C400_double_D60_zf550_M400_a5.mat')
MEAN_FLOOR_FULL_FRAME = 0.0001176160731120035  # from fft400_corrected_small_roi.mat (sourced)


def main():
    tests = []
    # POS on disk through the real loader
    meta = guard.load_double_map(DISK_MAP, 'D60_zf550_M400_a5')
    tests.append({'test_id': 'LIVE-POS01', 'description': 'existing disk map through real load_double_map',
                  'input_mutation': 'none (existing file %s)' % os.path.basename(DISK_MAP),
                  'guard_function': 'load_double_map -> validate_map_metadata',
                  'expected': 'accept', 'observed': 'accepted; sha=%s' % meta['source_sha256'][:16],
                  'status': 'PASS'})

    # mask-rule checks
    from scipy.io import loadmat
    m = loadmat(DISK_MAP)
    Im = np.asarray(m['Imean_map'], dtype=np.float64)
    mask = np.asarray(m['valid_mask']).astype(bool)
    # LIVE-02: demo map mask consistent with rule using full-frame floor
    ok, ndiff, det = guard.check_mask_rule(Im, mask, MEAN_FLOOR_FULL_FRAME)
    tests.append({'test_id': 'LIVE-02', 'description': 'demo map mask vs full-frame floor rule (1681/1681 valid expected)',
                  'input_mutation': 'none', 'guard_function': 'check_mask_rule',
                  'expected': 'n_disagree=0', 'observed': 'n_disagree=%d (%s)' % (ndiff, det),
                  'status': 'PASS' if ok else 'FAIL'})
    # LIVE-03: injected mask hiding a below-floor pixel must be rejected
    Im2 = Im.copy(); Im2[3, 4] = MEAN_FLOOR_FULL_FRAME * 0.5
    bad_mask = np.ones((41, 41), dtype=bool)
    ok2, nd2, _ = guard.check_mask_rule(Im2, bad_mask, MEAN_FLOOR_FULL_FRAME)
    tests.append({'test_id': 'LIVE-03', 'description': 'stored mask includes a below-floor pixel (Imean halved)',
                  'input_mutation': 'Imean[3,4] set to floor*0.5; stored mask still marks it valid',
                  'guard_function': 'check_mask_rule', 'expected': 'REJECT (rule disagrees)',
                  'observed': 'n_disagree=%d -> %s' % (nd2, 'rejected' if not ok2 else 'accepted'),
                  'status': 'PASS' if not ok2 else 'FAIL'})
    # LIVE-04: stored mask claims invalid but pixel is above floor
    m3 = np.ones((41, 41), dtype=bool); m3[7, 7] = False
    ok3, nd3, _ = guard.check_mask_rule(Im, m3, MEAN_FLOOR_FULL_FRAME)
    tests.append({'test_id': 'LIVE-04', 'description': 'stored mask marks an above-floor pixel invalid',
                  'input_mutation': 'valid_mask[7,7]=False while Imean>floor',
                  'guard_function': 'check_mask_rule', 'expected': 'REJECT',
                  'observed': 'n_disagree=%d -> %s' % (nd3, 'rejected' if not ok3 else 'accepted'),
                  'status': 'PASS' if not ok3 else 'FAIL'})
    # LIVE-05: NaN Imean
    Im4 = Im.copy(); Im4[1, 1] = np.nan
    ok5, nd5, _ = guard.check_mask_rule(Im4, mask, MEAN_FLOOR_FULL_FRAME)
    rejected4 = (not ok5) and nd5 > 0
    tests.append({'test_id': 'LIVE-05', 'description': 'NaN in Imean map',
                  'input_mutation': 'Imean[1,1]=NaN', 'guard_function': 'check_mask_rule',
                  'expected': 'REJECT (NaN fails isfinite; rule disagrees with stored mask)',
                  'observed': 'n_disagree=%d -> %s' % (nd5, 'rejected' if rejected4 else 'accepted'),
                  'status': 'PASS' if rejected4 else 'FAIL'})
    # LIVE-06: wrong full-frame shape
    try:
        guard.check_mask_rule(np.zeros((40, 41)), np.ones((41, 41), bool), MEAN_FLOOR_FULL_FRAME)
        rejected6 = False
    except guard.ShapeError:
        rejected6 = True
    tests.append({'test_id': 'LIVE-06', 'description': 'Imean/mask full-shape mismatch (40x41 vs 41x41)',
                  'input_mutation': 'Imean (40,41)', 'guard_function': 'check_mask_rule',
                  'expected': 'REJECT (ShapeError)', 'observed': 'rejected' if rejected6 else 'accepted',
                  'status': 'PASS' if rejected6 else 'FAIL'})
    # LIVE-07: disk-file negative - wrong internal case_id through real loader
    try:
        guard.load_double_map(DISK_MAP, 'D30_zf450_M400_a5')
        rejected7 = False
    except guard.IdentityError:
        rejected7 = True
    tests.append({'test_id': 'LIVE-07', 'description': 'disk map with wrong expected case_id',
                  'input_mutation': 'expected case_id changed', 'guard_function': 'load_double_map',
                  'expected': 'REJECT (IdentityError)', 'observed': 'rejected' if rejected7 else 'accepted',
                  'status': 'PASS' if rejected7 else 'FAIL'})
    # LIVE-08: geometry by versioned source
    rs, cs = guard.fine_slice(5, 26, 1)
    tests.append({'test_id': 'LIVE-08', 'description': 'q/fine-slice provenance',
                  'input_mutation': 'none', 'guard_function': 'fine_slice (versioned source)',
                  'expected': 'row26,col1 -> rows 185:190, cols 60:65 (0-based)',
                  'observed': 'rows %d:%d, cols %d:%d' % (rs.start, rs.stop, cs.start, cs.stop),
                  'status': 'PASS' if (rs.start, rs.stop, cs.start, cs.stop) == (185, 190, 60, 65) else 'FAIL'})

    # geometry source contract
    geom = [{'item': 'fine_slice_source', 'value': 'v086_identity_guard.fine_slice (single shared source); mirrors v083_common.fine_slice',
             'status': 'PROVEN_BY_VERSIONED_SOURCE'},
            {'item': 'q', 'value': '5 (frozen)', 'status': 'PROVEN_BY_VERSIONED_SOURCE'},
            {'item': 'h5py_axis_convention', 'value': 'axis1=MATLAB col, axis2=MATLAB row (anchored v084 at (21,1),(26,1),(16,1))', 'status': 'PROVEN_BY_VERSIONED_SOURCE'},
            {'item': 'map_loader_mask_check', 'value': 'load_double_map validates mask shape/1681/finite; mask RULE recheck added as check_mask_rule (v087)', 'status': 'IMPLEMENTED_V087'},
            {'item': 'heavy_compute_counter', 'value': 'v086 HEAVY_CALLS was a test-local stub; renamed TEST_FRAMEWORK_LOCAL and NOT claimed as production instrumentation', 'status': 'HONESTY_FIX_V087'},
            {'item': 'NEG-G09', 'value': 'renamed TEST_FRAMEWORK_SELFTEST (not a data-level guard)', 'status': 'RENAMED_V087'},
            {'item': 'old demo MAT q/coord metadata', 'value': 'not stored in MAT files; provenance via versioned fine_slice source', 'status': 'PROVEN_BY_VERSIONED_SOURCE'}]
    with open(os.path.join(TAB, 'v087_geometry_source_contract.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['item', 'value', 'status'], lineterminator='\n'); w.writeheader(); w.writerows(geom)

    fields = ['test_id', 'description', 'input_mutation', 'guard_function', 'expected', 'observed', 'status']
    with open(os.path.join(TAB, 'v087_mask_guard_live_tests.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n'); w.writeheader(); w.writerows(tests)
    with open(os.path.join(TAB, 'v087_mask_guard_live_tests.csv'), 'r', newline='', encoding='utf-8') as f:
        rr = list(csv.reader(f))
    assert len(rr) - 1 == len(tests) and all(len(x) == len(rr[0]) for x in rr)
    all_pass = all(t['status'] == 'PASS' for t in tests)
    print('[B] summary:', json.dumps({'tests': len(tests), 'all_pass': bool(all_pass)}))
    if not all_pass:
        sys.exit(2)


if __name__ == '__main__':
    main()
