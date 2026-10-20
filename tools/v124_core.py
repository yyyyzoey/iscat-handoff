"""V124 core: MAT-v7.3 render loader, physical library builder, qualification gates.

All science comes from NANOBEM stratified-BEM fields rendered by the frozen
MATLAB chain (build_system/render_system). The rejected V123R1 scalar
C(D,h) is NOT imported or used anywhere.
"""
import glob, hashlib, json, os, re
import h5py
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, 'results', 'v124')

def load_config():
    with open(os.path.join(REPO, 'config', 'v124_model_and_user_inputs.json'), encoding='utf-8') as f:
        return json.load(f)

def _cplx(ds):
    a = ds[()]
    arr = a['real'] + 1j * a['imag']
    # MATLAB 85x85x3 (x,y,comp) -> HDF5 (3,85,85) reversed; restore [x,y,comp]
    return np.transpose(arr, (2, 1, 0))

def load_render(path):
    out = {}
    with h5py.File(path, 'r') as h:
        r = h['r']
        out['C'] = r['contrast'][()].T          # [x_index, y_index]
        out['Iref'] = r['Iref'][()].T
        out['Isca'] = r['Isca'][()].T
        out['Icross'] = r['Icross'][()].T
        out['Itotal'] = r['Itotal'][()].T
        out['Eref'] = _cplx(r['Eref'])          # [x_fine, y_fine, comp]
        out['Esca'] = _cplx(r['Esca'])
        out['x_nm'] = r['x_nm'][:, 0]
        out['y_nm'] = r['y_nm'][:, 0]
        out['fine_x_nm'] = r['fine_x_nm'][:, 0]
        out['fine_y_nm'] = r['fine_y_nm'][:, 0]
        out['object_pixel_nm'] = float(r['object_pixel_nm'][0, 0])
        out['subpixels'] = int(r['subpixels'][0, 0])
        out['id_err'] = float(r['intensity_identity_relative_error'][0, 0])
        out['effective_magnification'] = float(r['effective_magnification'][0, 0])
        out['cfg_D'] = float(r['cfg/particle/diameter_nm'][0, 0])
        out['cfg_gap'] = float(r['cfg/particle/gap_nm'][0, 0])
        out['cfg_mesh'] = int(r['cfg/numerics/mesh_request'][0, 0])
        out['cfg_NA'] = float(r['cfg/objective/NA'][0, 0])
        out['cfg_nwater'] = float(r['cfg/layers/n'][1, 0])
        out['focus_z'] = float(r['cfg/focus_nm'][2, 0])
        out['grid_shift'] = r['grid_shift_xy_nm'][:, 0] if 'grid_shift_xy_nm' in r else np.array([0.0, 0.0])
    out['path'] = path
    return out

def _meta_from_name(path):
    name = os.path.basename(path)
    parts = name.split('__')
    fp, tag, rest, variant = parts[0], parts[1], parts[2], parts[3][:-4]
    d = {}
    mm = re.match(r'D([0-9.]+)_h([0-9.]+)_np([-0-9.]+)([+-][-0-9.]+)_mesh(\d+)', rest)
    d['D'] = float(mm.group(1)); d['h'] = float(mm.group(2))
    d['np_re'] = float(mm.group(3)); d['np_im'] = float(mm.group(4))
    d['mesh'] = int(mm.group(5))
    d['tag'], d['variant'] = tag, variant
    return d

def iter_renders(outdir=OUT, variant='default', np_re=1.38, mesh=576):
    pats = os.path.join(outdir, 'renders', '*.mat')
    for p in sorted(glob.glob(pats)):
        m = _meta_from_name(p)
        if m['variant'] == variant and abs(m['np_re'] - np_re) < 1e-12 and m['mesh'] == mesh and abs(m.get('np_im', 1)) < 1e-12:
            yield m, p

def pixel_mean(A, q):
    # matches src/pixel_mean.m: block average over q x q subpixels
    Nx, Ny = A.shape[0] // q, A.shape[1] // q
    return A.reshape(Nx, q, Ny, q).mean(axis=(1, 3))

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def python_mie(D_nm, lam_nm=520.0, np_=1.38, nw=1.3353, lmax=None):
    """Independent Bohren-Huffman Mie implementation (scattering benchmark only)."""
    m = np_ / nw
    x = np.pi * nw * D_nm / lam_nm
    if lmax is None:
        lmax = int(np.ceil(x + 4 * x ** (1 / 3) + 2))
    ell = np.arange(1, lmax + 1)
    def psi(l, z): return np.sqrt(np.pi / (2 * z)) * _sph_bessel_j(l, z)
    def chi(l, z): return np.sqrt(np.pi / (2 * z)) * _sph_bessel_y(l, z)
    def dpsi(l, z): return psi(l - 1, z) - l / z * psi(l, z)
    def dchi(l, z): return chi(l - 1, z) - l / z * chi(l, z)
    a = np.empty(lmax, complex); b = np.empty(lmax, complex)
    for i, l in enumerate(ell):
        mx = x * m
        a[i] = (m * psi(l, mx) * dpsi(l, x) - psi(l, x) * dpsi(l, mx)) / \
               (m * psi(l, mx) * dchi(l, x) - chi(l, x) * dpsi(l, mx))
        b[i] = (psi(l, mx) * dpsi(l, x) - m * psi(l, x) * dpsi(l, mx)) / \
               (psi(l, mx) * dchi(l, x) - m * chi(l, x) * dpsi(l, mx))
    Qsca = 2 / x ** 2 * np.sum((2 * ell + 1) * (np.abs(a) ** 2 + np.abs(b) ** 2))
    Qext = 2 / x ** 2 * np.sum((2 * ell + 1) * np.real(a + b))
    F = (m ** 2 - 1) / (m ** 2 + 2)
    Qsca_ray = 8 / 3 * x ** 4 * abs(F) ** 2
    return dict(D_nm=D_nm, x=x, lmax=lmax, Qsca=float(Qsca), Qext=float(Qext),
                Qabs=float(Qext - Qsca), Qsca_rayleigh=float(Qsca_ray),
                rel_diff_vs_rayleigh=float(abs(Qsca - Qsca_ray) / Qsca_ray))

def _sph_bessel_j(l, z):
    from scipy.special import spherical_jn
    return spherical_jn(l, z)

def _sph_bessel_y(l, z):
    from scipy.special import spherical_yn
    return spherical_yn(l, z)

def qualification_gates(outdir=OUT, cfg=None):
    """Zero-response, units/axes, q5/q7, mesh 576vs1444, and Python-vs-MATLAB Mie gates."""
    cfg = cfg or load_config()
    rows = []
    # zero-index gate
    vals = {}
    for p in sorted(glob.glob(os.path.join(outdir, 'renders', '*sentinel_match_*_default.mat'))):
        mm = _meta_from_name(p)
        r = load_render(p)
        vals[mm['tag']] = dict(peak_abs_C=float(np.max(np.abs(r['C']))),
                               center_abs_C=float(abs(r['C'][8, 8])),
                               id_err=r['id_err'], np_re=mm['np_re'])
    exact = vals['sentinel_match_exact']
    minus, plus = vals['sentinel_match_minus'], vals['sentinel_match_plus']
    detuned_mean = 0.5 * (minus['peak_abs_C'] + plus['peak_abs_C'])
    rows.append(dict(gate='zero_index_exact_np_eq_nwater',
                     pre_registered_target='max|C|<=1e-10 (engineering ideal)',
                     measured=exact['peak_abs_C'], passed=bool(exact['peak_abs_C'] <= 1e-10),
                     note='actual BEM numerical residual reported without relaxation'))
    rows.append(dict(gate='zero_index_two_sided_convergence',
                     pre_registered_target='|C(np=nw+-1e-4)| converging toward 0 and >> exact residual',
                     measured=detuned_mean,
                     ratio_detuned_over_exact=detuned_mean / max(exact['peak_abs_C'], 1e-30),
                     passed=bool(detuned_mean > 10 * exact['peak_abs_C'] and detuned_mean < 1e-2),
                     note='scattering must vanish continuously as np->nwater'))
    # units / axes / identity gate on main D100
    main100 = None
    for m, p in iter_renders(outdir):
        if m['tag'] == 'main_D100':
            main100 = p
    assert main100 is not None, 'main_D100 render missing'
    r = load_render(main100)
    I0r = pixel_mean(np.sum(np.abs(r['Eref']) ** 2, axis=2), 5)
    Isr = pixel_mean(np.sum(np.abs(r['Esca']) ** 2, axis=2), 5)
    Ixr = pixel_mean(2 * np.real(np.sum(np.conj(r['Eref']) * r['Esca'], axis=2)), 5)
    Itr = I0r + Isr + Ixr
    replay_err = float(np.max(np.abs(Itr - r['Itotal'])) / np.max(np.abs(r['Itotal'])))
    C_replay = (r['Itotal'] - I0r) / I0r
    C_err = float(np.max(np.abs(C_replay - r['C'])))
    px_ok = abs(r['object_pixel_nm'] - 280.0) < 1e-9
    rows.append(dict(gate='er_es_to_intensity_to_C_replay',
                     pre_registered_target='identity err<1e-10 and C replay exact',
                     measured_max_identity_err=replay_err, measured_max_C_abs_err=C_err,
                     passed=bool(replay_err < 1e-10 and C_err < 1e-12),
                     note='independent Python replay of Er/Es -> pixel -> I -> C'))
    rows.append(dict(gate='object_pixel_280nm_conditional',
                     pre_registered_target='1000*14um/(50x*1x)=280nm/px',
                     measured=r['object_pixel_nm'], passed=bool(px_ok),
                     note='CONDITIONAL_DERIVED scale, not an experimentally calibrated ruler'))
    # q5/q7
    q7 = None
    for p2 in glob.glob(os.path.join(outdir, 'renders', '*main_D100*q7.mat')):
        q7 = load_render(p2)
    if q7 is not None:
        rel = float(np.linalg.norm(q7['C'] - r['C']) / np.linalg.norm(r['C']))
        rows.append(dict(gate='q5_vs_q7_pixel_quadrature',
                         pre_registered_target='relL2(C) small; discretization diagnostic',
                         measured=rel, passed=bool(rel < 0.02),
                         note='17x17 pixels, 5x5 vs 7x7 intensity quadrature'))
    # mesh 576 vs 1444
    ref = None
    for p2 in glob.glob(os.path.join(outdir, 'renders', '*refmesh_D100*_default.mat')):
        ref = load_render(p2)
    if ref is not None:
        rel = float(np.linalg.norm(ref['C'] - r['C']) / np.linalg.norm(r['C']))
        rows.append(dict(gate='mesh_576_vs_1444_relL2',
                         pre_registered_target='<=2% relL2 in full 17x17 ROI',
                         measured=rel, passed=bool(rel < 0.02),
                         note='BEM discretization reference check at D100/h450/np1.38'))
    # Python Mie vs MATLAB Mie vs Rayleigh
    py_mie = [python_mie(D) for D in (10, 15, 20, 30)]
    import csv
    mat_csv = os.path.join(outdir, 'validation', 'mie_matlab_reference.csv')
    mat_rows = []
    if os.path.isfile(mat_csv):
        with open(mat_csv, newline='') as f:
            for row in csv.DictReader(f):
                mat_rows.append(row)
    for pm in py_mie:
        mt = next((m2 for m2 in mat_rows if abs(float(m2['D_nm']) - pm['D_nm']) < 1e-9), None)
        rel_mie = abs(pm['Qsca'] - float(mt['Qsca_mie'])) / float(mt['Qsca_mie']) if mt else float('nan')
        rows.append(dict(gate=f'mie_independent_D{pm["D_nm"]:.0f}',
                         pre_registered_target='Python vs MATLAB Mie agree; both near Rayleigh limit at small x',
                         measured_rel_diff_python_vs_matlab=rel_mie,
                         measured_rel_diff_mie_vs_rayleigh=pm['rel_diff_vs_rayleigh'],
                         Qsca_python=pm['Qsca'], Qsca_rayleigh=pm['Qsca_rayleigh'],
                         passed=bool(rel_mie < 1e-6 and pm['rel_diff_vs_rayleigh'] < 0.05),
                         note='isolated-sphere scattering benchmark only, never an iSCAT C'))
    os.makedirs(os.path.join(outdir, 'validation'), exist_ok=True)
    keys = sorted({k for row in rows for k in row})
    with open(os.path.join(outdir, 'validation', 'zero_index_and_units.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for row in rows:
            w.writerow(row)
    return rows

def build_library(outdir=OUT):
    """Aggregate default-variant np=1.38 mesh576 renders into an HDF5 library + grid CSV."""
    lib_dir = os.path.join(outdir, 'library')
    os.makedirs(lib_dir, exist_ok=True)
    h5_path = os.path.join(lib_dir, 'valid_physical_fields_or_coefficients.h5')
    grid = []
    with h5py.File(h5_path, 'w') as h:
        for m, p in iter_renders(outdir):
            r = load_render(p)
            g = h.create_group(f'D{m["D"]:g}_h{m["h"]:g}')
            for k in ('C', 'Iref', 'Isca', 'Icross', 'Itotal', 'Eref', 'Esca'):
                g.create_dataset(k, data=r[k], compression='gzip', compression_opts=4)
            g.create_dataset('x_nm', data=r['x_nm'])
            g.create_dataset('y_nm', data=r['y_nm'])
            g.create_dataset('fine_x_nm', data=r['fine_x_nm'])
            g.create_dataset('fine_y_nm', data=r['fine_y_nm'])
            g.attrs['D_nm'] = m['D']; g.attrs['h_nm'] = m['h']
            g.attrs['n_particle'] = complex(m['np_re'], m['np_im']).real
            g.attrs['mesh'] = m['mesh']; g.attrs['source_render'] = os.path.basename(p)
            g.attrs['intensity_identity_rel_err'] = r['id_err']
            g.attrs['diameter_type'] = 'UNIFORM_SPHERE_OPTICAL_EQUIVALENT'
            g.attrs['status'] = 'CONDITIONAL_MODEL'
            g.attrs['grid_role'] = ('holdout' if m['tag'].startswith('holdout') else
                                    'sentinel' if m['tag'].startswith('sentinel') else 'train')
            role = ('holdout' if m['tag'].startswith('holdout') else
                    'sentinel' if m['tag'].startswith('sentinel') else 'train')
            grid.append(dict(role=role, D_nm=m['D'], h_nm=m['h'], n_particle=m['np_re'], mesh=m['mesh'],
                             peak_abs_C=float(np.max(np.abs(r['C']))),
                             center_C=float(r['C'][8, 8]),
                             identity_rel_err=r['id_err'], source=os.path.basename(p)))
    import csv
    with open(os.path.join(lib_dir, 'valid_training_grid.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(grid[0].keys()))
        w.writeheader()
        for row in grid:
            w.writerow(row)
    return h5_path, grid
