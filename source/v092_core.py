# -*- coding: utf-8 -*-
"""v092 shared core: strict multi-key store, 3-bin bank builder, and the
production entry points used by both fixtures and the real batch.

Key contract: dataset|case|<int(k0)>bin  (dataset in {experiment, simulation};
case = estimator|window for experiment, full case_id for simulation).
Any aliasing (decimal freq, tuple-without-freq, duplicate overwrite) raises."""
import os
import numpy as np

BINS = (80, 160, 320)   # 0-based DFT bins; MATLAB 81/161/321


class ContractError(Exception):
    pass


def bin_key(dataset, case, k0):
    if float(k0) != int(k0):
        raise ContractError('non-integer bin alias %r rejected' % (k0,))
    k0 = int(k0)
    if k0 not in BINS:
        raise ContractError('bin %d not in the frozen set %s' % (k0, BINS))
    return '%s|%s|%dbin' % (dataset, case, k0)


class StrictStore:
    """Multi-key store that rejects duplicate writes and mixed key forms."""

    def __init__(self, dataset):
        self.dataset = dataset
        self._d = {}

    def put(self, case, k0, arr):
        k = bin_key(self.dataset, case, k0)
        if k in self._d:
            raise ContractError('duplicate key overwrite rejected: %s' % k)
        if not (isinstance(arr, np.ndarray) and arr.shape == (41, 41) and np.iscomplexobj(arr)):
            raise ContractError('map %s must be 41x41 complex' % k)
        if not np.isfinite(arr).all():
            raise ContractError('map %s contains NaN/Inf' % k)
        self._d[k] = arr
        return k

    def get(self, case, k0):
        return self._d[bin_key(self.dataset, case, k0)]

    def keys(self):
        return sorted(self._d)

    def __len__(self):
        return len(self._d)


def build_bank_3bin(D, zf, ttype, a, frames=None):
    """3-bin bank for one prescribed state via the streamed QF path.
    If frames is None, build from the v074 anchor quadratic form (the standard
    path used for all 48 states). Returns C[3,41,41], X[3,41,41], Imean, mask.
    Zero BEM, zero renders: reads only v074 cached anchors."""
    import h5py
    from v083_common import ROOT, roi_blocks, qf_coefficients_grid, lin_weights
    CACHE = os.path.join(ROOT, 'v074_return', 'numeric', 'render_cache')
    Es, Eref = roi_blocks(D, zf)
    Lm, Dm_, Qm, Iref = qf_coefficients_grid(Es, Eref)
    del Es, Eref
    tj = np.arange(N) / FS if False else np.arange(2001) / 5000.0
    freq = 200.0 if ttype == 'M200' else 400.0
    x = a * np.cos(2 * np.pi * freq * tj)
    ia_all, wa_all, wb_all = lin_weights(x)
    S1 = np.zeros((41, 41))
    SX = np.zeros((3, 41, 41), dtype=np.complex128)
    K0S = np.array([80, 160, 320])
    eall = np.exp(-2j * np.pi * K0S[:, None] * np.arange(2001)[None, :] / 2001.0)
    N = 2001
    for b0 in range(0, N, 32):
        sl = slice(b0, min(b0 + 32, N))
        ia = ia_all[sl]; wa = wa_all[sl]; wb = wb_all[sl]; ib = ia + 1
        v = (Iref[None, :, :]
             + wa[:, None, None] * Lm[ia] + wb[:, None, None] * Lm[ib]
             + (wa ** 2)[:, None, None] * Dm_[ia] + (wb ** 2)[:, None, None] * Dm_[ib]
             + (wa * wb)[:, None, None] * Qm[ia, ib])
        I = v.reshape(v.shape[0], 41, 5, 41, 5).mean(axis=(2, 4))
        S1 += I.sum(axis=0)
        SX += np.einsum('fb,bij->fij', eall[:, sl], I)
    Im_map = S1 / N
    sum_e = eall.sum(axis=1)
    X = SX - Im_map[None, :, :] * sum_e[:, None, None]
    with np.errstate(invalid='ignore', divide='ignore'):
        C = 2.0 * X / (N * Im_map)[None]
    pos = Im_map[(Im_map > 0) & np.isfinite(Im_map)]
    floor = 0.01 * float(np.median(pos))
    valid = np.isfinite(Im_map) & (Im_map > floor)
    Cm = np.full((3, 41, 41), np.nan + 1j * np.nan)
    Cm[:, valid] = C[:, valid]
    Xm = np.full((3, 41, 41), np.nan + 1j * np.nan)
    Xm[:, valid] = X[:, valid]
    return Cm, Xm, Im_map, valid
