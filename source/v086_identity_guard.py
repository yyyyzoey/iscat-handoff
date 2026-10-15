# -*- coding: utf-8 -*-
"""v086 production identity guard.

Single shared source of geometry truth and map validation, used by BOTH the
real map load/save entry points AND the negative-test suite (v086 contract
phase A). No hardcoded throws: every rejection comes from an explicit check
with a specific exception type.

Frozen geometry (demo grid, NOT experimental calibration):
  q=5 subpixels/physical pixel; full camera 65x65 physical; fine 325x325
  centre ROI = physical pixels 13:53 -> fine 61:265 (MATLAB 1-based), 41x41
  physical ROI, 205x205 fine ROI; ROI centre (21,21); full-frame centre (33,33).
  HDF5 anchor arrays: Es[pol, h5ax1, h5ax2] with h5ax1 = MATLAB COLUMN,
  h5ax2 = MATLAB ROW (empirically anchored in v084 at asymmetric pixels
  (21,1), (26,1), (16,1)).
"""
import os
import re
import hashlib
import numpy as np
import h5py

Q = 5
H = 41                      # ROI physical pixels per side
FINE_ROI = 205              # 41*5
PHYSICAL_FULL = 65
ROI_PHYSICAL_START = 13     # 1-based, full-frame physical
ROI_FINE_START = 61         # 1-based, fine
N = 2001
FS = 5000
K0 = 160

FROZEN_24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
             for D in (30, 60, 100) for zf in (450, 550)
             for t in ('M200', 'M400') for a in (5, 20)]
CASE_KEY_RE = re.compile(r'D(30|60|100)_zf(450|550)_(M200|M400)_a(5|20)')


class GuardError(Exception):
    """Base for all production-guard rejections (specific, not generic)."""


class CaseKeyError(GuardError):
    pass


class ShapeError(GuardError):
    pass


class GeometryError(GuardError):
    pass


class IdentityError(GuardError):
    pass


class MaskError(GuardError):
    pass


class SourceHashError(GuardError):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def validate_case_key(key):
    """Frozen-24 exact match, no control characters, no escape tricks."""
    if not isinstance(key, str) or len(key) != len(key.strip()) or key == '':
        raise CaseKeyError('case key empty or has leading/trailing whitespace: %r' % (key,))
    if any(ord(ch) < 32 or ch == '\x7f' for ch in key):
        raise CaseKeyError('control character in case key: %r' % (key,))
    # SQL/string escape cannot create a valid key: the regex admits ONLY the
    # frozen 24 exact forms.
    if not CASE_KEY_RE.fullmatch(key):
        raise CaseKeyError('case key %r does not match the frozen 24-state grammar' % (key,))
    if key not in FROZEN_24:
        raise CaseKeyError('case key %r is not one of the frozen 24 states' % (key,))
    return True


def fine_slice(q, row, col):
    """Production fine-slice derivation (single shared source of truth).

    ROI pixel (row, col) 1-based within the 41x41 ROI -> 0-based fine slices
    (row_slice, col_slice) of the full 325x325 anchor arrays. With q != 5 the
    frozen geometry contract is violated and the guard rejects.
    """
    if q != Q:
        raise GeometryError('subpixel factor q=%r violates frozen q=%d' % (q, Q))
    for name, v in (('row', row), ('col', col)):
        if not (isinstance(v, int) and 1 <= v <= H):
            raise GeometryError('ROI %s=%r outside 1..%d' % (name, v, H))
    r0 = (ROI_PHYSICAL_START - 1) * Q + (row - 1) * Q
    c0 = (ROI_PHYSICAL_START - 1) * Q + (col - 1) * Q
    return slice(r0, r0 + Q), slice(c0, c0 + Q)


def validate_fine_slice(q, row, col, expected):
    """Compare ACTUAL returned slices against frozen geometry metadata.
    `expected` = (row_slice, col_slice) as (start, stop) tuples."""
    rs, cs = fine_slice(q, row, col)
    er, ec = expected
    if (rs.start, rs.stop) != tuple(er) or (cs.start, cs.stop) != tuple(ec):
        raise GeometryError(
            'fine slices %s != frozen geometry %s (row %d, col %d, q %r)' % (
                ((rs.start, rs.stop), (cs.start, cs.stop)), (tuple(er), tuple(ec)), row, col, q))
    return (rs, cs)


def validate_map_metadata(arrays, expected_case_id, source_path=None,
                          expected_sha256=None, sha_ledger=None):
    """Production validator for one C400 double-map object.

    arrays: dict with C400_double, Imean_map, valid_mask, case_id (as stored).
    Checks: key grammar/control chars, internal case_id, shapes, complex dtype,
    mask consistency and finiteness, Imean presence/consistency, and (when a
    source file is given) its ACTUAL byte SHA against the frozen ledger.
    Returns a metadata dict. This is the SAME function used by the map loading
    entry point `load_double_map`.
    """
    cid = arrays.get('case_id')
    if isinstance(cid, np.ndarray):
        cid = str(np.asarray(cid).flatten()[0])
    elif not isinstance(cid, str):
        cid = str(cid)
    validate_case_key(expected_case_id)
    if cid != expected_case_id:
        raise IdentityError('internal case_id %r != expected %r' % (cid, expected_case_id))
    C = arrays.get('C400_double')
    if C is None or C.shape != (H, H):
        raise ShapeError('C400_double shape %s != (41, 41)' % (getattr(C, 'shape', None),))
    if not np.iscomplexobj(C):
        raise ShapeError('C400_double is not complex (dtype %s)' % (C.dtype,))
    mask = arrays.get('valid_mask')
    if mask is None or mask.shape != (H, H):
        raise ShapeError('valid_mask shape %s != (41, 41)' % (getattr(mask, 'shape', None),))
    maskb = np.asarray(mask).astype(bool)
    if int(maskb.sum()) != H * H:
        raise MaskError('valid pixels %d != %d (frozen full-ROI mask)' % (int(maskb.sum()), H * H))
    if not np.isfinite(C[maskb]).all():
        raise MaskError('non-finite C400 values inside the valid mask')
    Im = arrays.get('Imean_map')
    if Im is None or Im.shape != (H, H):
        raise ShapeError('Imean_map shape %s != (41, 41)' % (getattr(Im, 'shape', None),))
    if not np.isfinite(Im[maskb]).all() or not (np.asarray(Im)[maskb] > 0).all():
        raise MaskError('Imean_map not strictly positive/finite on the valid mask')
    meta = {'case_id': cid, 'shape': tuple(C.shape), 'dtype': str(C.dtype),
            'n_valid': int(maskb.sum()),
            'mask_rule': 'v073 frozen: Imean > 0.01*median(positive Imean); frozen full 1681/1681'}
    if source_path is not None:
        actual = sha256_file(source_path)
        meta['source_sha256'] = actual
        if expected_sha256 is not None and actual != expected_sha256:
            raise SourceHashError('file SHA %s != frozen ledger %s for %s' % (
                actual[:16], expected_sha256[:16], os.path.basename(source_path)))
        if sha_ledger is not None and os.path.basename(source_path) in sha_ledger:
            if actual != sha_ledger[os.path.basename(source_path)]:
                raise SourceHashError('file SHA not in frozen ledger for %s' % os.path.basename(source_path))
    return meta


def load_double_map(path, expected_case_id, sha_ledger=None):
    """Real map-loading entry point - shares validate_map_metadata with the
    negative-test suite (contract requirement: guards live in production)."""
    from scipy.io import loadmat
    m = loadmat(path)
    arrays = {'C400_double': m.get('C400_double'),
              'Imean_map': m.get('Imean_map'),
              'valid_mask': m.get('valid_mask'),
              'case_id': m.get('case_id')}
    meta = validate_map_metadata(arrays, expected_case_id, source_path=path, sha_ledger=sha_ledger)
    meta['arrays'] = arrays
    return meta

def check_mask_rule(Imean, stored_mask, mean_floor, tolerance_pixels=0):
    """Production mask-rule recheck against the FULL-FRAME operator threshold.

    expected = finite(Imean) & (Imean > mean_floor), where mean_floor must be
    the sourced full-frame threshold (e.g. 0.01*median of the positive full-
    frame Imean from the v073 extractor) - NOT a ROI-local median.
    Returns (mask_ok, n_diff, details)."""
    Im = np.asarray(Imean, dtype=np.float64)
    sm = np.asarray(stored_mask).astype(bool)
    if Im.shape != sm.shape:
        raise ShapeError('Imean shape %s != mask shape %s' % (Im.shape, sm.shape))
    expected = np.isfinite(Im) & (Im > float(mean_floor))
    n_diff = int(np.sum(expected != sm))
    details = {'mean_floor': float(mean_floor), 'n_stored_valid': int(sm.sum()),
               'n_rule_valid': int(expected.sum()), 'n_disagree': n_diff}
    return (n_diff <= tolerance_pixels), n_diff, details

# ---------------- v088 mask-scope production integration ----------------
MASK_SCOPES = ('DEMO_ROI_LOCAL', 'EXPERIMENT_FULL_FRAME_SOURCE')


def derive_demo_roi_floor(Imean_map):
    """DEMO_ROI_LOCAL rule (extract_fft_v073 applied to the demo ROI itself):
    floor = 0.01 * median(positive, finite Imean of THIS map)."""
    Im = np.asarray(Imean_map, dtype=np.float64)
    pos = Im[np.isfinite(Im) & (Im > 0)]
    if pos.size == 0:
        raise MaskError('no positive finite Imean values - cannot derive DEMO_ROI_LOCAL floor')
    return 0.01 * float(np.median(pos))


def validate_mask_scope(mask_scope, mean_floor=None, derived_floor=None):
    """Scope/floor source contract:
    - scope must be one of MASK_SCOPES (missing/unknown -> reject);
    - DEMO_ROI_LOCAL uses the map's own derived floor; an externally supplied
      floor that DISAGREES with the derived one is a scope/floor mismatch;
    - EXPERIMENT_FULL_FRAME_SOURCE requires a SOURCED full-frame floor
      (missing -> reject)."""
    if mask_scope not in MASK_SCOPES:
        raise GuardError('mask_scope %r missing or unknown; must be one of %s' % (mask_scope, MASK_SCOPES))
    if mask_scope == 'EXPERIMENT_FULL_FRAME_SOURCE':
        if mean_floor is None:
            raise GuardError('EXPERIMENT_FULL_FRAME_SOURCE requires a sourced full-frame mean_floor')
    if mask_scope == 'DEMO_ROI_LOCAL' and mean_floor is not None and derived_floor is not None:
        if abs(float(mean_floor) - derived_floor) > 1e-12 * max(1.0, abs(derived_floor)):
            raise GuardError('scope/floor mismatch: DEMO_ROI_LOCAL derives floor %g but %g was supplied '
                             '(experiment thresholds must not be applied to demo maps)' % (derived_floor, float(mean_floor)))
    return True


def load_double_map(path, expected_case_id, sha_ledger=None, mask_scope='DEMO_ROI_LOCAL',
                    mean_floor=None):
    """Real map-loading entry point (v086) now WITH the mask-rule recheck and
    explicit mask scope (v088). Rejections raise specific GuardErrors."""
    from scipy.io import loadmat
    m = loadmat(path)
    arrays = {'C400_double': m.get('C400_double'),
              'Imean_map': m.get('Imean_map'),
              'valid_mask': m.get('valid_mask'),
              'case_id': m.get('case_id')}
    meta = validate_map_metadata(arrays, expected_case_id, source_path=path, sha_ledger=sha_ledger)
    Im = np.asarray(arrays['Imean_map'], dtype=np.float64)
    maskb = np.asarray(arrays['valid_mask']).astype(bool)
    derived = derive_demo_roi_floor(Im) if mask_scope == 'DEMO_ROI_LOCAL' else None
    validate_mask_scope(mask_scope, mean_floor=mean_floor, derived_floor=derived)
    floor = derived if mask_scope == 'DEMO_ROI_LOCAL' else float(mean_floor)
    ok, n_diff, details = check_mask_rule(Im, maskb, floor)
    if not ok:
        raise MaskError('mask rule disagrees with stored mask under scope %s: %s' % (mask_scope, details))
    meta['mask_scope'] = mask_scope
    meta['mask_floor_used'] = floor
    meta['mask_rule_disagreements'] = n_diff
    meta['arrays'] = arrays
    return meta


def load_experiment_small_roi(path, mean_floor):
    if mean_floor is None:
        raise GuardError('EXPERIMENT_FULL_FRAME_SOURCE requires a sourced full-frame mean_floor')
    """Production entry for the CACHED EXPERIMENTAL small-ROI object
    (fft400_corrected_small_roi.mat, HDF5 keys X400/C400/Imean/validMask).
    The mean_floor MUST be the sourced full-frame threshold."""
    from scipy.io import loadmat  # noqa: F401 (symmetry)
    with h5py.File(path, 'r') as f:
        Cst = f['C400'][:]; Cst = Cst['real'].astype(np.float64) + 1j * Cst['imag'].astype(np.float64)
        Im = np.asarray(f['Imean']).astype(np.float64)
        mask = np.asarray(f['validMask']).astype(bool)
        N_ = float(np.asarray(f['N']).flatten()[0])
        Fs_ = float(np.asarray(f['Fs']).flatten()[0])
        k_ = float(np.asarray(f['k']).flatten()[0])
    if Cst.shape != (H, H) or Im.shape != (H, H) or mask.shape != (H, H):
        raise ShapeError('experimental small-ROI arrays must be 41x41')
    if N_ != N or Fs_ != FS or k_ not in (K0, K0 + 1):
        raise IdentityError('experimental operator metadata N/Fs/k mismatch: %s/%s/%s' % (N_, Fs_, k_))
    if not np.isfinite(Im[mask]).all() or not (Im[mask] > 0).all():
        raise MaskError('experimental Imean not strictly positive/finite on the stored mask')
    ok, n_diff, details = check_mask_rule(Im, mask, mean_floor)
    if not ok:
        raise MaskError('experimental mask rule disagrees with the sourced full-frame floor: %s' % details)
    return {'case': 'EXPERIMENT_SMALL_ROI', 'sha256': sha256_file(path),
            'n_valid': int(mask.sum()), 'mean_floor': float(mean_floor),
            'mask_rule_disagreements': n_diff,
            'N': N_, 'Fs': Fs_, 'k_matlab': k_}
