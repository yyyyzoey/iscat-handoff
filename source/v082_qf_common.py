# -*- coding: utf-8 -*-
"""v082 shared quadratic-form machinery (center 25-subpixel block, corrected ROI).

Replicates run_v076_D_qr_center.m / run_v076_C_dynamic_center.m center-pixel
path exactly: fine block 161:165 (1-based) of the 325x325 anchor fields =
physical centre pixel 33; 5 anchors x=[-20,-10,0,10,20] nm; quadratic-form
intensity I(x) = Iref + wa*Lm[ia] + wb*Lm[ia+1] + wa^2*Dm[ia] + wb^2*Dm[ia+1]
+ wa*wb*Qm[ia,ia+1], mean over the 25 subpixels.
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


def _complexify(arr):
    """h5py compound (real,imag) -> complex128."""
    if arr.dtype.names is not None:
        return arr['real'].astype(np.float64) + 1j * arr['imag'].astype(np.float64)
    return arr.astype(np.complex128)


def load_center_blocks(D, zf):
    """Return (E (5,25,3) complex128, Eref (25,3) complex128) for the centre
    physical pixel fine block 161:165 from the five cached anchors."""
    Es = np.empty((5, 25, 3), dtype=np.complex128)
    Eref = None
    for i, x in enumerate(XS):
        key = 'D%d_zf%g_x%+g' % (D, zf, x)
        p = os.path.join(CACHE, key + '.mat')
        with h5py.File(p, 'r') as f:
            a = f['a']
            Es_i = _complexify(a['Es'][:])
            if Eref is None:
                Eref = _complexify(a['Eref'][:])
        # MATLAB (3,325,325) -> numpy same; block rows/cols 161:165 (1-based)
        blk = Es_i[:, 160:165, 160:165]          # (3,5,5)
        Es[i] = np.transpose(blk, (1, 2, 0)).reshape(25, 3)
    blk_ref = Eref[:, 160:165, 160:165]
    Eref_c = np.transpose(blk_ref, (1, 2, 0)).reshape(25, 3)
    return Es, Eref_c


def qf_coefficients(Es, Eref):
    """Lm,Dm (25,5), Qm (25,5,5), Iref (25,) - per-subpixel quadratic form."""
    nA = 5
    Lm = np.empty((25, nA)); Dm = np.empty((25, nA))
    Qm = np.zeros((25, nA, nA))
    for i in range(nA):
        Lm[:, i] = 2.0 * np.real(np.sum(np.conj(Eref) * Es[i], axis=1))
        Dm[:, i] = np.sum(np.abs(Es[i]) ** 2, axis=1)
        for j in range(nA):
            Qm[:, i, j] = 2.0 * np.real(np.sum(np.conj(Es[i]) * Es[j], axis=1))
    Iref = np.sum(np.abs(Eref) ** 2, axis=1)
    return Lm, Dm, Qm, Iref


def lin_weights(x):
    """Vectorized linWeights vs XS: returns (ia, wa, wb) with ia in 0..3."""
    x = np.clip(x, XS[0], XS[-1])
    ia = np.searchsorted(XS, x, side='right') - 1
    ia = np.clip(ia, 0, 3)
    wb = (x - XS[ia]) / (XS[ia + 1] - XS[ia])
    return ia, 1.0 - wb, wb


def qf_series(xt, Lm, Dm, Qm, Iref, dtype=np.float64):
    """Quadratic-form intensity series for displacement samples xt (any shape).
    Returns series with xt.shape, accumulated in dtype (float32 replicates the
    v076 single-precision path)."""
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
    """Interpolate the COMPLEX field first (bilinear in x), then intensity,
    then mean over 25 subpixels - the 'integrate field first' path."""
    xf = np.asarray(xt, dtype=np.float64).ravel()
    ia, wa, wb = lin_weights(xf)
    ib = ia + 1
    EsI = wa[:, None, None] * Es[ia] + wb[:, None, None] * Es[ib]   # (M,25,3)
    It = np.sum(np.abs(Eref[None, :, :] + EsI) ** 2, axis=2)        # (M,25)
    return It.mean(axis=1).reshape(np.shape(xt))


def dft_bin(series):
    """Complex DFT of mean-subtracted series at bin K0 (0-based)."""
    s = np.asarray(series, dtype=np.float64).ravel()
    Im = s.mean()
    e = np.exp(-2j * np.pi * K0 * np.arange(N) / N)
    return complex(np.sum((s - Im) * e)), Im


def cbin(series):
    X, Im = dft_bin(series)
    return 2.0 * X / (N * Im), Im



