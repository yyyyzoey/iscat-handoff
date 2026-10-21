"""V126 canonical forward model with three pre-registered interpolation candidates.

All estimators call ONLY canonical_forward (I_sel). The three candidates:
  I0: C-map multilinear over the D-h node grid (inherited baseline)
  I1: complex-field D/h bilinear (4 corners), Es shifted at (x-dx,y-dy),
      Eref fixed on camera grid, intensity then 5x5 pixel average
  I2: scaled complex-field: interpolate Es/s(D) (real+imag separately) with
      s(D)=(D/100nm)^3, bilinear in h; node-exact, domain-safe.
Selection is pre-registered: node-exactness, domain safety, then dev diagnostics.
"""
import os
import numpy as np
import h5py
from scipy.interpolate import RegularGridInterpolator

import v125_forward_shift as vfs

REPO = r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff'
LIB = os.path.join(REPO, 'results', 'v125', 'library', 'v125_Dh_train_fields.h5')
DS = np.array([30.0, 50.0, 70.0, 100.0, 130.0, 160.0, 200.0])
HS = np.array([350.0, 375.0, 400.0, 425.0, 450.0, 475.0, 500.0, 525.0, 550.0])
SCORE = (slice(2, 15), slice(2, 15))

def _pixel_mean(A, q=5):
    Nx, Ny = A.shape[0] // q, A.shape[1] // q
    return A.reshape(Nx, q, Ny, q).mean(axis=(1, 3))

class CanonicalModel:
    def __init__(self, h5p=LIB):
        self.h = h5py.File(h5p, 'r')
        self.Ds, self.Hs = DS, HS
        self._wide_cache = {}
    def close(self):
        self.h.close()
    def _node_name(self, D, h):
        Dq = float(self.Ds[np.argmin(np.abs(self.Ds - D))])
        Hq = float(self.Hs[np.argmin(np.abs(self.Hs - h))])
        return f'D{Dq:g}_h{Hq:g}', Dq, Hq
    def _corner_names(self, D, h):
        D = float(np.clip(D, self.Ds[0], self.Ds[-1]))
        h = float(np.clip(h, self.Hs[0], self.Hs[-1]))
        i = int(np.searchsorted(self.Ds, D) - 1); i = min(max(i, 0), len(self.Ds) - 2)
        j = int(np.searchsorted(self.Hs, h) - 1); j = min(max(j, 0), len(self.Hs) - 2)
        wd = (D - self.Ds[i]) / (self.Ds[i + 1] - self.Ds[i])
        wh = (h - self.Hs[j]) / (self.Hs[j + 1] - self.Hs[j])
        names = [(f'D{self.Ds[i+a]:g}_h{self.Hs[j+b]:g}',
                  (1-wd if a == 0 else wd) * (1-wh if b == 0 else wh))
                 for a in (0, 1) for b in (0, 1)]
        return names, (i, j, wd, wh)
    def _get_wide(self, node):
        if node not in self._wide_cache:
            g = self.h[node]['wide']
            self._wide_cache[node] = (g['Eref'][()], g['Esca'][()], g['fine_x_nm'][:], g['fine_y_nm'][:])
        return self._wide_cache[node]
    def node_C(self, D, h, score=True):
        n, _, _ = self._node_name(D, h)
        C = self.h[n]['C'][()]
        return C[2:15, 2:15] if score else C
    # ---------------- I0 ----------------
    def forward_I0(self, D, h, dx, dy):
        """C-map multilinear over nodes; offset handled by table-free linear
        blending of node C images shifted at the C level (approximate)."""
        names, _ = self._corner_names(D, h)
        acc = np.zeros((13, 13)); wsum = 0.0
        for n, w in names:
            Cn = self.h[n]['C'][()]
            # shift the node C image via scipy map_coordinates on the 17x17 grid
            from scipy.ndimage import shift as ndi_shift
            Csh = ndi_shift(Cn, (-dy/56.0, -dx/56.0), order=1, mode='constant', cval=0.0)
            acc += w * Csh[2:15, 2:15]
            wsum += w
        return acc / wsum
    # ---------------- I1 ----------------
    def forward_I1(self, D, h, dx, dy):
        names, _ = self._corner_names(D, h)
        er = np.zeros((125, 125, 3), complex); es = np.zeros_like(er)
        fx = fy = None
        for n, w in names:
            e0, s0, fx, fy = self._get_wide(n)
            er += w * e0; es += w * s0
        try:
            return vfs.particle_shift_C(er, es, fx, fy, float(dx), float(dy), q=5, cam_Nx=17)[2:15, 2:15]
        except vfs.OutOfDomain:
            return None
    # ---------------- I2 ----------------
    def forward_I2(self, D, h, dx, dy):
        sD = (D / 100.0) ** 3
        names, _ = self._corner_names(D, h)
        er = np.zeros((125, 125, 3), complex); es = np.zeros_like(er)
        fx = fy = None
        for n, w in names:
            e0, s0, fx, fy = self._get_wide(n)
            Dn = float(self.h[n].attrs['D_nm'])
            sn = (Dn / 100.0) ** 3
            er += w * e0
            es += w * s0 / sn
        try:
            return vfs.particle_shift_C(er, es * sD, fx, fy, float(dx), float(dy), q=5, cam_Nx=17)[2:15, 2:15]
        except vfs.OutOfDomain:
            return None
    def forward(self, cand, D, h, dx, dy):
        if cand == 'I0':
            return self.forward_I0(D, h, dx, dy)
        if cand == 'I1':
            return self.forward_I1(D, h, dx, dy)
        if cand == 'I2':
            return self.forward_I2(D, h, dx, dy)
        raise ValueError(cand)
    def in_domain(self, D, h, dx, dy):
        return (self.Ds[0] <= D <= self.Ds[-1] and self.Hs[0] <= h <= self.Hs[-1]
                and abs(dx) <= 500.0 and abs(dy) <= 500.0)

def node_exactness(model):
    """All candidates must reproduce node C exactly at nodes, zero offset."""
    rows = []
    for D in model.Ds:
        for h in model.Hs:
            Cn = model.node_C(D, h)
            for cand in ('I1', 'I2'):
                Cf = model.forward(cand, D, h, 0.0, 0.0)
                err = float(np.max(np.abs(Cf - Cn))) if Cf is not None else float('nan')
                rows.append(dict(candidate=cand, D=D, h=h, max_abs_err=err,
                                 passed=bool(err < 1e-12)))
    return rows

def interpolator_comparison(model, offsets=((0.0, 0.0), (28.0, 0.0), (70.0, -98.0), (140.0, 0.0), (0.0, 140.0))):
    """Quantify I0/I1/I2 differences at off-node parameters (dev diagnostics)."""
    rows = []
    rng = np.random.default_rng(126)
    for _ in range(40):
        D = float(rng.choice(model.Ds[:-1]) + 5.0)   # mid-cell
        h = float(rng.choice(model.Hs[:-1]) + 12.5)
        dx, dy = [float(v) for v in rng.choice(np.arange(-224, 225, 56.0), 2)]
        outs = {}
        for cand in ('I0', 'I1', 'I2'):
            outs[cand] = model.forward(cand, D, h, dx, dy)
        if any(v is None for v in outs.values()):
            continue
        rows.append(dict(D=D, h=h, dx=dx, dy=dy,
                         dI0_I1=float(np.linalg.norm(outs['I0'] - outs['I1'])),
                         dI1_I2=float(np.linalg.norm(outs['I1'] - outs['I2'])),
                         dI0_I2=float(np.linalg.norm(outs['I0'] - outs['I2'])),
                         norm_I1=float(np.linalg.norm(outs['I1']))))
    return rows
