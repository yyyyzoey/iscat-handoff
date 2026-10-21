"""V127 canonical forward: formal contract + three real interpolation candidates.

canonical_forward(theta, cand) -> (Ibg, I, C, valid, reason) on the central
13x13 score ROI; raises OutOfDomain for any parameter outside the machine
domain (no clipping, no extrapolation). theta=(D,h,x,y); first axis camera_x,
second camera_y; fields interpolated over the (D,h) node grid, scattered field
shifted at (x-dx, y-dy), reference fixed on the camera grid.

F1_COMPLEX_BILINEAR_BASELINE : bilinear over (D,h)
F2_COMPLEX_TENSOR_CUBIC      : tensor cubic over (D,h), real/imag separately
F3_D3_SCALED_COMPLEX_TENSOR_CUBIC : cubic of Es/s(Dnode), multiply back s(D)
"""
import os
import numpy as np
import h5py
from scipy.interpolate import RegularGridInterpolator

import v125_forward_shift as vfs

REPO = r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff'
LIB = os.path.join(REPO, 'results', 'v126', 'library', 'v126_Dh_train_fields.h5')
DS = np.array([30.0, 50.0, 70.0, 100.0, 130.0, 160.0, 200.0])
HS = np.array([350.0, 375.0, 400.0, 425.0, 450.0, 475.0, 500.0, 525.0, 550.0])
DOMAIN = dict(D=(30.0, 200.0), h=(350.0, 550.0), x=(-500.0, 500.0), y=(-500.0, 500.0), min_gap=100.0)


class OutOfDomain(Exception):
    def __init__(self, theta, reason):
        self.theta = tuple(theta); self.reason = reason
        super().__init__(f'OUT_OF_DOMAIN {reason}: theta={theta}')


def check_domain(theta):
    D, h, x, y = theta
    if not (DOMAIN['D'][0] <= D <= DOMAIN['D'][1]):
        raise OutOfDomain(theta, 'D_outside')
    if not (DOMAIN['h'][0] <= h <= DOMAIN['h'][1]):
        raise OutOfDomain(theta, 'h_outside')
    if not (DOMAIN['x'][0] <= x <= DOMAIN['x'][1] and DOMAIN['y'][0] <= y <= DOMAIN['y'][1]):
        raise OutOfDomain(theta, 'xy_outside')
    if h - D / 2.0 < DOMAIN['min_gap'] - 1e-9:
        raise OutOfDomain(theta, 'gap_below_min')


class Candidate:
    """One interpolation candidate over the in-memory 63-node wide fields."""

    def __init__(self, kind, h5p=LIB):
        assert kind in ('F1', 'F2', 'F3')
        self.kind = kind
        self.h5p = h5p
        self.Ds, self.Hs = DS, HS
        Es = np.zeros((len(DS), len(HS), 125, 125, 3), complex)
        Er = np.zeros_like(Es)
        with h5py.File(h5p, 'r') as h:
            for i, D in enumerate(DS):
                for j, hh in enumerate(HS):
                    g = h[f'D{D:g}_h{hh:g}/wide']
                    a = g['Esca'][()]; b = g['Eref'][()]
                    def cplx(v):
                        if v.dtype.names:  # MATLAB compound real/imag
                            return v['real'] + 1j * v['imag']
                        return v
                    # HDF5 (3,125,125) reversed -> [x,y,comp]
                    av, bv = cplx(a), cplx(b)
                    # H5-stored fields are already [x,y,comp]; raw MAT would be reversed
                    Es[i, j] = np.transpose(av, (2, 1, 0)) if av.shape[0] == 3 else av
                    Er[i, j] = np.transpose(bv, (2, 1, 0)) if bv.shape[0] == 3 else bv
        self.fine_x = h5py.File(h5p, 'r')[f'D{DS[0]:g}_h{HS[0]:g}/wide/fine_x_nm'][:]
        self.fine_y = h5py.File(h5p, 'r')[f'D{DS[0]:g}_h{HS[0]:g}/wide/fine_y_nm'][:]
        # RGI over (D,h) with trailing pixel dims; cubic for F2/F3
        if kind == 'F1':
            pts = (DS, HS)
            self._rgi_er = RegularGridInterpolator(pts, Er, method='linear', bounds_error=False, fill_value=None)
            self._rgi_es = RegularGridInterpolator(pts, Es, method='linear', bounds_error=False, fill_value=None)
        else:
            # tensor cubic via ONCE-prefiltered arrays + map_coordinates (vectorized;
            # interior identical to the not-a-knot tensor spline, edge-clamped)
            from scipy.ndimage import spline_filter1d
            def pre(A):
                A = spline_filter1d(A, order=3, axis=0, mode='nearest')
                A = spline_filter1d(A, order=3, axis=1, mode='nearest')
                return A
            # split into 6 real arrays (3 components x re/im) of shape (7,9,125,125)
            self._pf_er = [pre(Er[..., c].real) for c in range(3)] + [pre(Er[..., c].imag) for c in range(3)]
            src_es = Es
            if kind == 'F3':
                sn = (DS / 100.0) ** 3
                src_es = Es / sn[:, None, None, None, None]
                self._scales = sn
            self._pf_es = [pre(src_es[..., c].real) for c in range(3)] + [pre(src_es[..., c].imag) for c in range(3)]
            self._d_idx = np.arange(len(DS), dtype=float)
            self._build_node_cache()
            self._h_idx = np.arange(len(HS), dtype=float)
        self._Er = Er  # kept for node-exactness checks

    def node_C(self, D, h):
        i = int(np.argmin(np.abs(self.Ds - D)))
        j = int(np.argmin(np.abs(self.Hs - h)))
        with h5py.File(self.h5p, 'r') as h:
            return h[f'D{self.Ds[i]:g}_h{self.Hs[j]:g}/C'][()][2:15, 2:15]

    def _node_fields(self, D, h):
        i = int(np.argmin(np.abs(self.Ds - D)))
        j = int(np.argmin(np.abs(self.Hs - h)))
        if abs(self.Ds[i] - D) > 1e-9 or abs(self.Hs[j] - h) > 1e-9:
            return None
        return self._node_cache[(i, j)]

    def _build_node_cache(self):
        if getattr(self, "_node_cache", None):
            return
        Es = np.zeros((len(self.Ds), len(self.Hs), 125, 125, 3), complex)
        Er = np.zeros_like(Es)
        with h5py.File(self.h5p, "r") as h:
            for i, D in enumerate(self.Ds):
                for j, hh in enumerate(self.Hs):
                    g = h[f"D{D:g}_h{hh:g}/wide"]
                    a = g["Esca"][()]; b = g["Eref"][()]
                    Es[i, j] = a if a.ndim == 3 else np.transpose(a, (2, 1, 0))
                    Er[i, j] = b if b.ndim == 3 else np.transpose(b, (2, 1, 0))
        self._node_cache = {(i, j): (Er[i, j].copy(), Es[i, j].copy())
                            for i in range(len(self.Ds)) for j in range(len(self.Hs))}

    def _eval_fields(self, D, h):
        if getattr(self, "_node_cache", None):
            nf = self._node_fields(D, h)
            if nf is not None:
                return nf
        if self.kind == 'F1':
            er = self._rgi_er([[D, h]])[0]
            es = self._rgi_es([[D, h]])[0]
            return er, es
        from scipy.ndimage import map_coordinates
        di = float(np.interp(D, self.Ds, self._d_idx))
        hi_ = float(np.interp(h, self.Hs, self._h_idx))
        coords = np.stack([np.full(er := self._pf_er.shape[2:], di),
                           np.full(er, hi_),
                           *np.meshgrid(np.arange(er[0]), np.arange(er[1]), indexing='ij')]) if False else None
        # coordinates: axis0=D index, axis1=h index, axes2..4 pixel/component indices
        nxx, nyy = self._pf_er[0].shape[2], self._pf_er[0].shape[3]
        c0 = np.full((nxx, nyy), di)
        c1 = np.full((nxx, nyy), hi_)
        c2 = np.repeat(np.arange(nxx)[:, None], nyy, 1)
        c3 = np.repeat(np.arange(nyy)[None, :], nxx, 0)
        coords = np.stack([c0, c1, c2, c3])
        erc = [map_coordinates(A, coords, order=3, mode='nearest', prefilter=False) for A in self._pf_er]
        esc = [map_coordinates(A, coords, order=3, mode='nearest', prefilter=False) for A in self._pf_es]
        er = np.stack(erc[:3] + [0j] * 0, axis=-1).astype(complex)
        er += 1j * np.stack(erc[3:], axis=-1)
        es = np.stack(esc[:3], axis=-1).astype(complex)
        es += 1j * np.stack(esc[3:], axis=-1)
        if self.kind == 'F3':
            es = es * (D / 100.0) ** 3
        return er, es

    def C(self, D, h, dx, dy, score=True):
        """Signed C on the central 17x17 (then 13x13 if score)."""
        check_domain((D, h, dx, dy))
        er, es = self._eval_fields(D, h)
        C17 = vfs.particle_shift_C(er, es, self.fine_x, self.fine_y, float(dx), float(dy), q=5, cam_Nx=17)
        return C17[2:15, 2:15] if score else C17

    def forward(self, theta):
        """Formal contract: returns (Ibg, I, C, valid, reason) on 13x13."""
        D, h, dx, dy = theta
        try:
            check_domain(theta)
        except OutOfDomain as e:
            return None, None, None, False, e.reason
        er, es = self._eval_fields(D, h)
        try:
            sx, sy = self.fine_x - dx, self.fine_y - dy
            if (sx[0] < self.fine_x[0] - 1e-9 or sx[-1] > self.fine_x[-1] + 1e-9 or
                    sy[0] < self.fine_y[0] - 1e-9 or sy[-1] > self.fine_y[-1] + 1e-9):
                return None, None, None, False, 'shift_out_of_support'
            from scipy.interpolate import RegularGridInterpolator as RGI
            def bil(A, xs, ys):
                it = RGI((xs, ys), A, bounds_error=False, fill_value=None)
                X, Y = np.meshgrid(xs, ys, indexing='ij')
                return it(np.stack([X, Y], axis=-1))
            es_s = np.empty_like(es)
            for c in range(3):
                es_s[:, :, c] = bil(es[:, :, c], sx, sy)
            q = 5
            Ibg = _pixel_mean(np.sum(np.abs(er) ** 2, 2), q)
            I = _pixel_mean(np.sum(np.abs(er + es_s) ** 2, 2), q)
            C = (I - Ibg) / Ibg
            C13 = C[2:15, 2:15]
            if not np.isfinite(C13).all():
                return Ibg[2:15, 2:15], I[2:15, 2:15], None, False, 'non_finite_C'
            return Ibg[2:15, 2:15], I[2:15, 2:15], C13, True, 'ok'
        except vfs.OutOfDomain as e:
            return None, None, None, False, str(e)


def _pixel_mean(A, q=5):
    Nx, Ny = A.shape[0] // q, A.shape[1] // q
    return A.reshape(Nx, q, Ny, q).mean(axis=(1, 3))
