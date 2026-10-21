"""V129 canonical forward with physical-axis cubic spline (not-a-knot)."""
import os, sys
import numpy as np
import h5py
from scipy.interpolate import make_interp_spline
from scipy.ndimage import map_coordinates

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(REPO, 'results', 'v128', 'library', 'v128_Dh_train_fields.h5')

class OutOfDomain(Exception):
    def __init__(self, theta, reason):
        self.theta = tuple(theta); self.reason = reason
        super().__init__(f'OUT_OF_DOMAIN {reason}: {theta}')

class ComplexFieldForward:
    def __init__(self, lib_path=LIB, kind='F1'):
        self.kind = kind
        with h5py.File(lib_path, 'r') as h:
            self.Ds = sorted(set(float(h[k].attrs['D_nm']) for k in h.keys()))
            self.Hs = sorted(set(float(h[k].attrs['h_nm']) for k in h.keys()))
            nD, nH = len(self.Ds), len(self.Hs)
            self.Er = np.zeros((nD, nH, 125, 125, 3), complex)
            self.Es = np.zeros_like(self.Er)
            for i, D in enumerate(self.Ds):
                for j, hh in enumerate(self.Hs):
                    k = f'D{D:g}_h{hh:g}'
                    if k not in h: continue
                    g = h[k]['wide']
                    a = g['Eref'][()]; b = g['Esca'][()]
                    if a.ndim == 3: a = np.transpose(a, (2,1,0)) if a.shape[0]==3 else a
                    if b.ndim == 3: b = np.transpose(b, (2,1,0)) if b.shape[0]==3 else b
                    if a.shape[0] == 3: a = np.transpose(a, (2,1,0)) if a.shape[0]==3 else a
                    if b.shape[0] == 3: b = np.transpose(b, (2,1,0)) if b.shape[0]==3 else b
                    self.Er[i,j] = a; self.Es[i,j] = b
                    if j == 0:
                        self.fine_x = g['fine_x_nm'][:]
                        self.fine_y = g['fine_y_nm'][:]
        # build splines
        if kind == 'F1':
            self._spl_er = self._make_bilinear(self.Er)
            self._spl_es = self._make_bilinear(self.Es)
        else:
            scaled = self.Es / ((np.array(self.Ds) / 100.0) ** 3)[:, None, None, None, None] if kind == 'F3' else self.Es
            self._spl_er = self._make_cubic(self.Er)
            self._spl_es = self._make_cubic(scaled)
            self._is_f3 = (kind == 'F3')

    def _make_bilinear(self, A):
        return A  # handled by manual bilinear
    def _make_cubic(self, A):
        # make_interp_spline along D and h for each (pixel, comp) - use tensor approach
        # reshape: (nD, nH, ...) -> make spline along axis 0 then axis 1
        from scipy.interpolate import make_interp_spline as mis
        # Step 1: spline along D (axis 0)
        sp_D = mis(self.Ds, A, k=3, axis=0)  # returns callable
        # We need to pre-evaluate on a fine grid? No - store the spline object
        # But calling sp_D on each h is expensive. Use a different approach:
        # Build a single 2-D spline per (pixel, comp)
        # For efficiency, reshape A to (nD, nH*n_pix) and build one spline per column
        nD, nH = len(self.Ds), len(self.Hs)
        flat = A.reshape(nD, nH, -1)  # (nD, nH, n_pix)
        # Build spline coefficients: use make_interp_spline once per axis
        # Along D: for each (h_idx, pix), get 4 coefficients -> but we need full tensor
        # Simpler: store the data and do manual bicubic evaluation
        return A  # store raw data, do manual bicubic

    def _eval_bilinear(self, D, h):
        Di, Hi = np.array(self.Ds), np.array(self.Hs)
        i = int(np.searchsorted(Di, D)-1); i = min(max(i,0), len(Di)-2)
        j = int(np.searchsorted(Hi, h)-1); j = min(max(j,0), len(Hi)-2)
        wd = (D-Di[i])/(Di[i+1]-Di[i]); wh = (h-Hi[j])/(Hi[j+1]-Hi[j])
        er = (1-wd)*(1-wh)*self.Er[i,j] + wd*(1-wh)*self.Er[i+1,j] + \
             (1-wd)*wh*self.Er[i,j+1] + wd*wh*self.Er[i+1,j+1]
        es = (1-wd)*(1-wh)*self.Es[i,j] + wd*(1-wh)*self.Es[i+1,j] + \
             (1-wd)*wh*self.Es[i,j+1] + wd*wh*self.Es[i+1,j+1]
        return er, es

    def _eval_cubic(self, D, h):
        """Tensor cubic spline on physical (D,h) axes using make_interp_spline."""
        nD, nH = len(self.Ds), len(self.Hs)
        flat_shape = self.Er.shape[2:]  # (125,125,3)
        # Step 1: cubic along D for each h
        # Step 2: cubic along h for the result
        # Efficient: use make_interp_spline once per h along D, then once along h
        # Actually: reshape to (nD, nH*n_pix) and use make_interp_spline along D
        # Then evaluate at D to get (nH, n_pix), then spline along h
        flat_er = self.Er.reshape(nD, nH, -1)  # (nD, nH, n_pix)
        flat_es = self.Es.reshape(nD, nH, -1)
        if self.kind == 'F3':
            sn = (np.array(self.Ds) / 100.0) ** 3
            flat_es = flat_es / sn[:, None, None]
        sp_D_er = make_interp_spline(self.Ds, flat_er, k=3, axis=0)
        sp_D_es = make_interp_spline(self.Ds, flat_es, k=3, axis=0)
        er_at_D = sp_D_er(D)  # (nH, n_pix)
        es_at_D = sp_D_es(D)  # (nH, n_pix)
        if self.kind == 'F3':
            es_at_D = es_at_D * (D / 100.0) ** 3
        sp_H_er = make_interp_spline(self.Hs, er_at_D, k=3, axis=0)
        sp_H_es = make_interp_spline(self.Hs, es_at_D, k=3, axis=0)
        er = sp_H_er(h).reshape(flat_shape)
        es = sp_H_es(h).reshape(flat_shape)
        return er, es

    def eval_fields(self, D, h):
        if self.kind == 'F1':
            return self._eval_bilinear(D, h)
        return self._eval_cubic(D, h)

    def C(self, D, h, dx, dy, score=True):
        # domain check
        if not (30 <= D <= 200): raise OutOfDomain((D,h,dx,dy), 'D')
        if not (350 <= h <= 550): raise OutOfDomain((D,h,dx,dy), 'h')
        if not (-500 <= dx <= 500 and -500 <= dy <= 500): raise OutOfDomain((D,h,dx,dy), 'xy')
        if h - D/2 < 100 - 1e-9: raise OutOfDomain((D,h,dx,dy), 'gap')
        er, es = self.eval_fields(D, h)
        # shift scattered field on the FULL 125-point grid
        from scipy.interpolate import RegularGridInterpolator as RGI
        sx, sy = self.fine_x - dx, self.fine_y - dy
        # verify camera area coverage (central 85 fine points = +/-2380nm)
        cam_half = 17 * 280.0 / 2  # 2380nm
        if (sx[0] > -cam_half or sx[-1] < cam_half or
            sy[0] > -cam_half or sy[-1] < cam_half):
            raise OutOfDomain((D,h,dx,dy), 'shift_out')
        es_s = np.zeros_like(es)
        for c in range(3):
            for attr in ('real', 'imag'):
                arr = getattr(es[:,:,c], attr)
                itp = RGI((self.fine_x, self.fine_y), arr, bounds_error=False, fill_value=None)
                X, Y = np.meshgrid(sx, sy, indexing='ij')
                es_s[:,:,c] = es_s[:,:,c] + (itp(np.stack([X,Y],axis=-1)) * (1 if attr=='real' else 1j))
        # pixel average on full 25x25
        q = 5
        Ibg25 = _pixel_mean(np.sum(np.abs(er)**2, 2), q)
        I25 = _pixel_mean(np.sum(np.abs(er + es_s)**2, 2), q)
        C25 = (I25 - Ibg25) / Ibg25
        # crop to central 17x17 (matching standard render) then central 13x13
        C17 = C25[4:21, 4:21]
        C13 = C17[2:15, 2:15]
        return C13

def _pixel_mean(A, q=5):
    Nx, Ny = A.shape[0]//q, A.shape[1]//q
    return A.reshape(Nx, q, Ny, q).mean(axis=(1, 3))
