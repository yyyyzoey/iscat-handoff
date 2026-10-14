# -*- coding: utf-8 -*-
"""v083 shared helpers: pixel-addressed anchor blocks with an EXPLICIT axis
convention, plus full-ROI (205x205) quadratic-form coefficients.

Axis convention (empirically proven in v083 Phase A against the legacy
tseries_center field):
  h5py anchor array a['Es'] has shape (3, 325, 325) = (pol, h5_ax1, h5_ax2)
  where h5_ax1 corresponds to MATLAB COLUMN index and h5_ax2 to MATLAB ROW
  index of the MATLAB array E(row, col, pol).
  Therefore MATLAB fine rows 161:165 / cols 61:65 are read as
  Es[:, 60:65, 160:165] (h5py order: col-slice first, row-slice second).

Zero BEM, zero new renders: reads only v074 render_cache anchors.
"""
import os
import numpy as np
import h5py

ROOT = r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4'
CACHE = os.path.join(ROOT, 'v074_return', 'numeric', 'render_cache')
XS = np.array([-20.0, -10.0, 0.0, 10.0, 20.0])
N = 2001
FS = 5000.0
K0 = 160
Q = 5  # subpixels per physical pixel
# corrected centre ROI: physical pixels 13:53 -> fine 61:265 (1-based)
ROI_I0 = 61  # 1-based fine start of the 205x205 block


def _complexify(arr):
    if arr.dtype.names is not None:
        return arr['real'].astype(np.float64) + 1j * arr['imag'].astype(np.float64)
    return arr.astype(np.complex128)


def load_anchor(D, zf, x):
    with h5py.File(os.path.join(CACHE, 'D%d_zf%g_x%+g.mat' % (D, zf, x)), 'r') as f:
        a = f['a']
        return _complexify(a['Es'][:]), _complexify(a['Eref'][:])


def fine_slice(roi_pixel_1based):
    """ROI pixel (r,c) 1-based -> (fine_row_slice, fine_col_slice) 0-based."""
    r, c = roi_pixel_1based
    r0 = (13 - 1) * Q + (r - 1) * Q   # fine row start, 0-based (61 for r=1)
    c0 = (13 - 1) * Q + (c - 1) * Q
    return slice(r0, r0 + Q), slice(c0, c0 + Q)


def block_at(D, zf, r, c):
    """25-subpixel x 3-pol complex blocks for MATLAB ROI pixel (r, c).

    Returns (Es (5,25,3), Eref (25,3)). Uses the documented h5py axis order:
    col slice first, row slice second.
    """
    rs, cs = fine_slice((r, c))
    Es = np.empty((5, 25, 3), dtype=np.complex128)
    Eref = None
    for i, x in enumerate(XS):
        Es_i, Eref_i = load_anchor(D, zf, x)
        # h5py array (pol, h5ax1=MATLAB col, h5ax2=MATLAB row)
        if Eref is None:
            Eref = Eref_i[:, cs, rs].transpose(1, 2, 0).reshape(25, 3)
        Es[i] = Es_i[:, cs, rs].transpose(1, 2, 0).reshape(25, 3)
    return Es, Eref


def roi_blocks(D, zf, half=20):
    """Full (2*half+1)x(2*half+1)-physical-pixel ROI blocks (205x205 for 41x41).

    Returns (Es (5, h5r, h5c, 3) complex128, Eref (h5r, h5c, 3)) in h5py axis
    order (axis1 = MATLAB col, axis2 = MATLAB row) with the CORRECTED ROI
    fine 61:265.
    """
    L = 2 * half + 1
    r0 = (13 - 1) * Q          # 60, 0-based fine row start
    c0 = (13 - 1) * Q
    sl_r = slice(r0, r0 + L * Q)
    sl_c = slice(c0, c0 + L * Q)
    Es = np.empty((5, L * Q, L * Q, 3), dtype=np.complex128)
    Eref = None
    for i, x in enumerate(XS):
        Es_i, Eref_i = load_anchor(D, zf, x)
        if Eref is None:
            Eref = Eref_i[:, sl_c, sl_r].transpose(1, 2, 0)
        Es[i] = Es_i[:, sl_c, sl_r].transpose(1, 2, 0)
    return Es, Eref


def qf_coefficients_grid(Es, Eref):
    """Quadratic-form coefficients for full grids.
    Es: (5, H, W, 3); Eref: (H, W, 3). Returns Lm,Dm (5,H,W), Qm (5,5,H,W), Iref (H,W)."""
    nA = Es.shape[0]
    Lm = np.empty((nA, Es.shape[1], Es.shape[2]))
    Dm = np.empty((nA, Es.shape[1], Es.shape[2]))
    Qm = np.empty((nA, nA, Es.shape[1], Es.shape[2]))
    for i in range(nA):
        Lm[i] = 2.0 * np.real(np.sum(np.conj(Eref) * Es[i], axis=2))
        Dm[i] = np.sum(np.abs(Es[i]) ** 2, axis=2)
        for j in range(nA):
            Qm[i, j] = 2.0 * np.real(np.sum(np.conj(Es[i]) * Es[j], axis=2))
    Iref = np.sum(np.abs(Eref) ** 2, axis=2)
    return Lm, Dm, Qm, Iref


def lin_weights(x):
    x = np.clip(np.asarray(x, dtype=np.float64), XS[0], XS[-1])
    ia = np.searchsorted(XS, x, side='right') - 1
    ia = np.clip(ia, 0, len(XS) - 2)
    wb = (x - XS[ia]) / (XS[ia + 1] - XS[ia])
    return ia, 1.0 - wb, wb


def qf_series(xt, Lm, Dm, Qm, Iref, dtype=np.float64):
    """Elementwise quadratic-form series for 25-subpixel blocks (as v082)."""
    ia, wa, wb = lin_weights(np.asarray(xt, dtype=np.float64).ravel())
    ib = ia + 1
    cast = (lambda v: v.astype(dtype)) if dtype is not np.float64 else (lambda v: v)
    Lmr = cast(Lm.T); Dmr = cast(Dm.T); Qmr = cast(Qm.transpose(1, 2, 0))
    Ir = cast(Iref)
    w = lambda a: cast(a.astype(dtype))[:, None]
    v = (Ir[None, :] + w(wa) * Lmr[ia]
         + w(wb) * Lmr[ib]
         + w(wa ** 2) * Dmr[ia]
         + w(wb ** 2) * Dmr[ib]
         + w(wa * wb) * Qmr[ia, ib])
    out = cast(v).mean(axis=-1).astype(np.float64)
    return out.reshape(np.shape(xt))


def field_first_series(xt, Es, Eref):
    xf = np.asarray(xt, dtype=np.float64).ravel()
    ia, wa, wb = lin_weights(xf)
    ib = ia + 1
    EsI = wa[:, None, None] * Es[ia] + wb[:, None, None] * Es[ib]
    It = np.sum(np.abs(Eref[None, :, :] + EsI) ** 2, axis=2)
    return It.mean(axis=1).reshape(np.shape(xt))


def dft_bin(series):
    s = np.asarray(series, dtype=np.float64).ravel()
    Im = s.mean()
    e = np.exp(-2j * np.pi * K0 * np.arange(N) / N)
    return complex(np.sum((s - Im) * e)), Im


def cbin(series):
    X, Im = dft_bin(series)
    return 2.0 * X / (N * Im), Im


