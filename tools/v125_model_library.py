"""V125 model library: H5 build, shift tables, train/holdout isolation.

- Train nodes: 7 D x 9 h (MAIN_7x9); sources = identity-verified V124 renders
  (15 nodes) + new V125 solves/renders (48 nodes). Each node stores the full
  default render (17x17 C, Ibg, Itot) and the wide render (25x25 fine fields)
  used by the shift-capable forward model.
- Shift table: per node, the CORRECT particle-translation forward
  (Eref fixed on camera grid, Es sampled at x-dx) evaluated on an offset grid.
- Isolation: TrainLibrary opens ONLY the train H5. Holdout truth lives in a
  validator-only JSON and is never imported here.
"""
import glob, hashlib, json, os
import numpy as np
import h5py

import v124_core as vc
import v125_forward_shift as vfs

REPO = vc.REPO
V124 = os.path.join(REPO, 'results', 'v124')
OUT = os.path.join(REPO, 'results', 'v125')

TRAIN_D = [30.0, 50.0, 70.0, 100.0, 130.0, 160.0, 200.0]
TRAIN_H = [350.0, 375.0, 400.0, 425.0, 450.0, 475.0, 500.0, 525.0, 550.0]
HOLDOUTS = [('H01', 37.0, 362.5, 56.0, -84.0), ('H02', 63.0, 387.5, -112.0, 28.0),
            ('H03', 93.0, 412.5, 84.0, 112.0), ('H04', 117.0, 462.5, -56.0, -112.0),
            ('H05', 147.0, 487.5, 112.0, -56.0), ('H06', 177.0, 537.5, -84.0, 84.0)]
OFFSET_STEP = 28.0
OFFSET_MAX = 504.0

def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()

def _camx_flip(d):
    """Global camera-frame normalization (identity of axes).

    The MATLAB chain applies flip(es,1) before storage; combined with ascending
    fine_x labels the stored first axis is mirrored relative to the physical
    camera_x direction (evidence: all six direct holdout renders show a
    consistent x-sign inversion under the same-solve forward model, 6/6).
    The flip is applied ONCE, globally, to every array, with relabeled ascending
    fine_x/x - uniformly for templates, observations and the forward model."""
    d['C'] = d['C'][::-1, :]
    for k in ('Iref', 'Isca', 'Icross', 'Itotal'):
        d[k] = d[k][::-1, :]
    d['Eref'] = d['Eref'][::-1, :, :]
    d['Esca'] = d['Esca'][::-1, :, :]
    d['fine_x_nm'] = -d['fine_x_nm'][::-1]
    d['x_nm'] = -d['x_nm'][::-1]
    return d

def load_v125_render(path):
    out = {}
    with h5py.File(path, 'r') as h:
        r = h['r']
        out['C'] = r['contrast'][()].T
        out['Iref'] = r['Iref'][()].T
        out['Isca'] = r['Isca'][()].T
        out['Icross'] = r['Icross'][()].T
        out['Itotal'] = r['Itotal'][()].T
        out['Eref'] = _cplx(r['Eref'])
        out['Esca'] = _cplx(r['Esca'])
        out['x_nm'] = r['x_nm'][:, 0]
        out['y_nm'] = r['y_nm'][:, 0]
        out['fine_x_nm'] = r['fine_x_nm'][:, 0]
        out['fine_y_nm'] = r['fine_y_nm'][:, 0]
        out['id_err'] = float(r['intensity_identity_relative_error'][0, 0])
        out['mode'] = r['render_mode'][0] if 'render_mode' in r else 'default'
        out['shift'] = r['shift_xy_nm'][:, 0] if 'shift_xy_nm' in r else np.zeros(2)
    out = _camx_flip(out)
    out['path'] = path
    return out

def _cplx(ds):
    a = ds[()]
    arr = a['real'] + 1j * a['imag']
    return np.transpose(arr, (2, 1, 0))

def vml_repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def index_v125_renders(outdir=OUT):
    """key_map CSV: full key -> short file. Returns dict keyed by
    (tag, variant, dx, dy)."""
    import csv
    amap = {}
    p = os.path.join(outdir, 'logs', 'cache_key_map.csv')
    for r in csv.DictReader(open(p, newline='')):
        amap[r['full_key']] = r['file']
    out = {}
    import re
    pat = re.compile(r'^(?P<img>[^_]+(?:_[^_]+)*)__(?P<solver>.+?)__(?P<tag>.+?)__'
                     r'(?P<phys>D[-0-9.]+_h[-0-9.]+_np[-+0-9.]+_mesh\d+)__'
                     r'(?P<variant>.+?)_dx(?P<dx>-?[0-9.]+)_dy(?P<dy>-?[0-9.]+)$')
    for full, fname in amap.items():
        if not full.startswith('v125img'):
            continue
        mm = pat.match(full)
        if not mm:
            continue
        fp = fname if os.path.isabs(fname) else os.path.join(vml_repo_root(), fname)
        out[(mm['tag'], mm['variant'], float(mm['dx']), float(mm['dy']))] = fp
    # wide re-images map (tag -> file) takes precedence over early broken 'wide' rows
    wmap = os.path.join(outdir, 'logs', 'wide_render_map.csv')
    if os.path.isfile(wmap):
        for r in csv.DictReader(open(wmap, newline='')):
            out[(r['tag'], 'wide', 0.0, 0.0)] = r['file'] if os.path.isabs(r['file']) else os.path.join(vml_repo_root(), r['file'])
    return out

def _node_tag(D, h):
    return f'train_D{D:g}_h{h:g}'

def build_train_library(outdir=OUT):
    """Assemble v125_Dh_train_fields.h5 from V124-verified + new V125 renders."""
    rend = index_v125_renders(outdir)
    # V124 fallback for the 15 reusable nodes (identity verified at intake)
    v124_idx = {}
    for m, p in vc.iter_renders(V124):
        v124_idx[(m['tag'], m['variant'])] = p
    h5p = os.path.join(outdir, 'library', 'v125_Dh_train_fields.h5')
    os.makedirs(os.path.dirname(h5p), exist_ok=True)
    grid_rows = []
    with h5py.File(h5p, 'w') as h:
        for D in TRAIN_D:
            for hh in TRAIN_H:
                tag = _node_tag(D, hh)
                src = None; source_repo = ''
                key = (tag, 'default', 0.0, 0.0)
                if key in rend:
                    src = rend[key]; source_repo = 'v125_new'
                else:
                    # resolve the V124 source tag for the 15 verified reusable nodes
                    if D == 100.0 and hh != 450.0:
                        v124tag = f'hscan_h{hh:g}'
                    elif hh == 450.0:
                        v124tag = f'main_D{D:g}'
                    else:
                        v124tag = None
                    if v124tag and (v124tag, 'default') in v124_idx:
                        src = v124_idx[(v124tag, 'default')]; source_repo = 'v124_verified_intake'
                if src is None:
                    grid_rows.append(dict(D_nm=D, h_nm=hh, status='MISSING', source=''))
                    continue
                r = _camx_flip(vc.load_render(src))
                g = h.create_group(f'D{D:g}_h{hh:g}')
                for k in ('C', 'Iref', 'Isca', 'Icross', 'Itotal'):
                    g.create_dataset(k, data=r[k], compression='gzip', compression_opts=4)
                g.create_dataset('Eref', data=r['Eref'], compression='gzip', compression_opts=4)
                g.create_dataset('Esca', data=r['Esca'], compression='gzip', compression_opts=4)
                g.create_dataset('x_nm', data=r['x_nm']); g.create_dataset('y_nm', data=r['y_nm'])
                g.create_dataset('fine_x_nm', data=r['fine_x_nm'])
                g.create_dataset('fine_y_nm', data=r['fine_y_nm'])
                # wide fields when available (new nodes)
                wkey = (tag, 'wide', 0.0, 0.0)
                has_wide = wkey in rend
                if has_wide:
                    rw = load_v125_render(rend[wkey])
                    gw = g.create_group('wide')
                    gw.create_dataset('Eref', data=rw['Eref'], compression='gzip', compression_opts=4)
                    gw.create_dataset('Esca', data=rw['Esca'], compression='gzip', compression_opts=4)
                    gw.create_dataset('fine_x_nm', data=rw['fine_x_nm'])
                    gw.create_dataset('fine_y_nm', data=rw['fine_y_nm'])
                    gw.create_dataset('C', data=rw['C'])
                g.attrs.update(dict(D_nm=D, h_nm=hh, n_particle=1.38, mesh=576,
                                    source=source_repo, has_wide=int(has_wide),
                                    object_pixel_nm=r['object_pixel_nm'], NA=0.8,
                                    status='CONDITIONAL_MODEL',
                                    diameter_type='UNIFORM_SPHERE_OPTICAL_EQUIVALENT'))
                grid_rows.append(dict(D_nm=D, h_nm=hh, status='OK', source=source_repo,
                                      has_wide=has_wide,
                                      peak_abs_C=float(np.max(np.abs(r['C']))),
                                      center_C=float(r['C'][8, 8]),
                                      identity_rel_err=r['id_err']))
    import csv
    with open(os.path.join(outdir, 'library', 'train_grid_index.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for r0 in grid_rows for k in r0}))
        w.writeheader()
        for r0 in grid_rows: w.writerow(r0)
    return h5p, grid_rows

def _shift_table_worker(args):
    name, Eref, Esca, fx, fy = args
    offsets = np.arange(-OFFSET_MAX, OFFSET_MAX + 1e-9, OFFSET_STEP)
    tab = np.empty((len(offsets), len(offsets), 13, 13))
    for ix, dx in enumerate(offsets):
        for iy, dy in enumerate(offsets):
            C = vfs.particle_shift_C(Eref, Esca, fx, fy, float(dx), float(dy), q=5, cam_Nx=17)
            tab[ix, iy] = C[2:15, 2:15]
    return name, tab

def build_shift_table(h5p, outdir=OUT, workers=None):
    """Per-node C_off(dx,dy) tables via the corrected particle-shift forward."""
    offsets = np.arange(-OFFSET_MAX, OFFSET_MAX + 1e-9, OFFSET_STEP)
    nodes = []
    with h5py.File(h5p, 'r') as h:
        for D in TRAIN_D:
            for hh in TRAIN_H:
                g = h[f'D{D:g}_h{hh:g}']
                if 'wide' in g:
                    nodes.append((f'D{D:g}_h{hh:g}', g['wide/Eref'][()], g['wide/Esca'][()],
                                  g['wide/fine_x_nm'][:], g['wide/fine_y_nm'][:]))
    from multiprocessing import Pool
    results = []
    if workers and workers > 1:
        with Pool(workers) as pool:
            for name, tab in pool.imap_unordered(_shift_table_worker, nodes, chunksize=1):
                results.append((name, tab)); print('table', name, flush=True)
    else:
        for nd in nodes:
            name, tab = _shift_table_worker(nd); results.append((name, tab)); print('table', name, flush=True)
    tabp = os.path.join(outdir, 'library', 'v125_shift_tables.h5')
    with h5py.File(tabp, 'w') as h:
        h.create_dataset('offsets_nm', data=offsets)
        for name, tab in results:
            h.create_dataset(name, data=tab.astype(np.float32), compression='gzip', compression_opts=4)
    return tabp, offsets

class TrainLibrary:
    """Frozen offline model; optimizer callbacks may ONLY use this class."""
    def __init__(self, h5p=None, tabp=None):
        self.h5p = h5p or os.path.join(OUT, 'library', 'v125_Dh_train_fields.h5')
        self.tabp = tabp or os.path.join(OUT, 'library', 'v125_shift_tables.h5')
        self._h = h5py.File(self.h5p, 'r')
        self._t = h5py.File(self.tabp, 'r')
        self.offsets = self._t['offsets_nm'][:]
        self.Ds = np.array(TRAIN_D); self.Hs = np.array(TRAIN_H)
        self._wide = {}
    def close(self):
        self._h.close(); self._t.close()
    def _node(self, D, h):
        Dq = float(self.Ds[np.argmin(np.abs(self.Ds - D))])
        Hq = float(self.Hs[np.argmin(np.abs(self.Hs - h))])
        return f'D{Dq:g}_h{Hq:g}', Dq, Hq
    def template_C(self, D, h):
        """Bilinear C-image interpolation over the rectangular train grid."""
        D = float(np.clip(D, self.Ds[0], self.Ds[-1]))
        h = float(np.clip(h, self.Hs[0], self.Hs[-1]))
        i = int(np.searchsorted(self.Ds, D) - 1); i = min(max(i, 0), len(self.Ds) - 2)
        j = int(np.searchsorted(self.Hs, h) - 1); j = min(max(j, 0), len(self.Hs) - 2)
        wd = (D - self.Ds[i]) / (self.Ds[i + 1] - self.Ds[i])
        wh = (h - self.Hs[j]) / (self.Hs[j + 1] - self.Hs[j])
        C00 = self._h[f'D{self.Ds[i]:g}_h{self.Hs[j]:g}/C'][()][2:15, 2:15]
        C10 = self._h[f'D{self.Ds[i+1]:g}_h{self.Hs[j]:g}/C'][()][2:15, 2:15]
        C01 = self._h[f'D{self.Ds[i]:g}_h{self.Hs[j+1]:g}/C'][()][2:15, 2:15]
        C11 = self._h[f'D{self.Ds[i+1]:g}_h{self.Hs[j+1]:g}/C'][()][2:15, 2:15]
        return ((1-wd)*((1-wh)*C00 + wh*C01) + wd*((1-wh)*C10 + wh*C11))
    def c_table(self, D, h, dx, dy):
        """Multi-linear interpolation of the shift table over (D,h,dx,dy)."""
        D = float(np.clip(D, self.Ds[0], self.Ds[-1]))
        h = float(np.clip(h, self.Hs[0], self.Hs[-1]))
        o = self.offsets
        dx = float(np.clip(dx, o[0], o[-1])); dy = float(np.clip(dy, o[0], o[-1]))
        i = int(np.searchsorted(self.Ds, D) - 1); i = min(max(i, 0), len(self.Ds) - 2)
        j = int(np.searchsorted(self.Hs, h) - 1); j = min(max(j, 0), len(self.Hs) - 2)
        wd = (D - self.Ds[i]) / (self.Ds[i + 1] - self.Ds[i])
        wh = (h - self.Hs[j]) / (self.Hs[j + 1] - self.Hs[j])
        ix = int(np.searchsorted(o, dx) - 1); ix = min(max(ix, 0), len(o) - 2)
        iy = int(np.searchsorted(o, dy) - 1); iy = min(max(iy, 0), len(o) - 2)
        wx = (dx - o[ix]) / (o[ix + 1] - o[ix]); wy = (dy - o[iy]) / (o[iy + 1] - o[iy])
        acc = np.zeros((13, 13)); wsum = 0.0
        for a, wa in ((0, 1-wd), (1, wd)):
            for b, wb in ((0, 1-wh), (1, wh)):
                n = f'D{self.Ds[i+a]:g}_h{self.Hs[j+b]:g}'
                T = self._t[n]
                acc += wa * wb * ((1-wy)*T[ix, iy] + wy*T[ix, iy+1] if False else
                                  (1-wx)*((1-wy)*T[ix, iy] + wy*T[ix, iy+1]) +
                                  wx*((1-wy)*T[ix+1, iy] + wy*T[ix+1, iy+1]))
                wsum += wa * wb
        return acc / wsum
    def wide_fields(self, D, h):
        """4-corner interpolated wide complex fields (cached)."""
        Dq = float(np.clip(D, self.Ds[0], self.Ds[-1]))
        Hq = float(np.clip(h, self.Hs[0], self.Hs[-1]))
        i = int(np.searchsorted(self.Ds, Dq) - 1); i = min(max(i, 0), len(self.Ds) - 2)
        j = int(np.searchsorted(self.Hs, Hq) - 1); j = min(max(j, 0), len(self.Hs) - 2)
        wd = (Dq - self.Ds[i]) / (self.Ds[i + 1] - self.Ds[i])
        wh = (Hq - self.Hs[j]) / (self.Hs[j + 1] - self.Hs[j])
        Erefs, Escas, fx, fy = [], [], None, None
        for a in (0, 1):
            for b in (0, 1):
                n = f'D{self.Ds[i+a]:g}_h{self.Hs[j+b]:g}'
                if n not in self._wide:
                    g = self._h[n]['wide']
                    self._wide[n] = (g['Eref'][()], g['Esca'][()], g['fine_x_nm'][:], g['fine_y_nm'][:])
                er, es, fx, fy = self._wide[n]
                w = (1-wd if a == 0 else wd) * (1-wh if b == 0 else wh)
                Erefs.append(er * w); Escas.append(es * w)
        return (sum(Erefs), sum(Escas), fx, fy)
    def forward_exact(self, D, h, dx, dy):
        """Field-level exact particle-shift forward on the central 17x17 ROI."""
        er, es, fx, fy = self.wide_fields(D, h)
        try:
            C = vfs.particle_shift_C(er, es, fx, fy, float(dx), float(dy), q=5, cam_Nx=17)
        except vfs.OutOfDomain:
            return None
        return C[2:15, 2:15]
