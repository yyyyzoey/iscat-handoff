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
