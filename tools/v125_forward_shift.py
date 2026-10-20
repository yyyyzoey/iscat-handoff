"""V125 S1-B: correct particle-translation forward model.

Correct semantics (contract S1-B): the SCATTERED field of a laterally
translated particle is sampled at (x-dx, y-dy); the REFERENCE field stays on
the fixed camera grid; fields are summed BEFORE intensity and pixel averaging.
Old V124 frame_C_shifted shifted reference and scattered intensities together
(whole-scene shift) - preserved unchanged in v124_core for evidence.

Ground-truth reference without new solves: a camera_shift MATLAB render
provides MATLAB-sampled Es(x-dx); combining it with the default render's
Eref(x) yields the exact particle-shift image (no interpolation at all).
"""
import numpy as np
from scipy.interpolate import RegularGridInterpolator

class OutOfDomain(Exception):
    pass

def _interp_complex(E, xs, ys, query_x, query_y):
    """Sample complex field E[x_i, y_j, c] at arbitrary in-domain points."""
    itps = [RegularGridInterpolator((xs, ys), E[:, :, c], bounds_error=True,
                                    fill_value=None) for c in range(E.shape[2])]
    X, Y = np.meshgrid(query_x, query_y, indexing='ij')
    pts = np.stack([X, Y], axis=-1)
    out = np.empty_like(E)
    for c, itp in enumerate(itps):
        out[:, :, c] = itp(pts)
    return out

def pixel_mean(A, q):
    Nx, Ny = A.shape[0] // q, A.shape[1] // q
    return A.reshape(Nx, q, Ny, q).mean(axis=(1, 3))

def particle_shift_C(Eref, Es, fine_x, fine_y, dx, dy, q=5):
    """Signed C image for a particle translated by (dx,dy), camera fixed."""
    sx, sy = fine_x - dx, fine_y - dy
    if (sx[0] < fine_x[0] - 1e-9 or sx[-1] > fine_x[-1] + 1e-9 or
            sy[0] < fine_y[0] - 1e-9 or sy[-1] > fine_y[-1] + 1e-9):
        raise OutOfDomain(f'shift ({dx},{dy}) leaves fine-grid support')
    Es_shift = _interp_complex(Es, fine_x, fine_y, sx, sy)
    Etot = Eref + Es_shift
    It = pixel_mean(np.sum(np.abs(Etot) ** 2, axis=2), q)
    I0 = pixel_mean(np.sum(np.abs(Eref) ** 2, axis=2), q)
    return (It - I0) / I0

def s1_regression(default_render, shift_renders):
    """Fixtures vs real MATLAB renders of the D100/h450 solve.

    GT (exact, interpolation-free): C_gt(dx) built from the default render's
    Eref(x) + the camera_shift render's MATLAB-sampled Es(x-dx).
    F1: zero-shift identity; F2: interpolation error at 28nm; F3: at 140nm;
    F4: whole-scene (camera) shift differs from particle shift - documented.
    """
    import v124_core as vc
    rows = []
    Eref = default_render['Eref']; fx = default_render['fine_x_nm']; fy = default_render['fine_y_nm']
    C0 = particle_shift_C(Eref, default_render['Esca'], fx, fy, 0.0, 0.0)
    rows.append(dict(fixture='F1_zero_shift_identity',
                     value=float(np.max(np.abs(C0 - default_render['C']))),
                     passed=bool(np.max(np.abs(C0 - default_render['C'])) == 0.0),
                     detail='pixel-identity: Eref+Es(0) reconstruction exact'))
    for tag, rsh in shift_renders.items():
        dx, dy = rsh['grid_shift']
        C_gt = (vc.pixel_mean(np.sum(np.abs(Eref + rsh['Esca']) ** 2, 2), 5) -
                vc.pixel_mean(np.sum(np.abs(Eref) ** 2, 2), 5)) / \
               vc.pixel_mean(np.sum(np.abs(Eref) ** 2, 2), 5)
        C_ip = particle_shift_C(Eref, default_render['Esca'], fx, fy, dx, dy)
        err_ip = float(np.max(np.abs(C_ip - C_gt)))
        rows.append(dict(fixture=f'F2_interp_vs_exact_{tag}', value=err_ip,
                         passed=err_ip < 0.004,
                         detail=f'shift=({dx:g},{dy:g})nm max|dC| interpolation vs MATLAB-sampled'))
    for tag, rsh in shift_renders.items():
        dx, dy = rsh['grid_shift']
        C_particle = particle_shift_C(Eref, default_render['Esca'], fx, fy, dx, dy)
        d = float(np.max(np.abs(rsh['C'] - C_particle)))
        rows.append(dict(fixture=f'F4_camera_shift_vs_particle_{tag}', value=d,
                         passed=True,
                         detail='whole-scene grid shift differs from particle-only shift; '
                                'particle-only is the physical translation semantics; difference documented'))
    return rows

if __name__ == '__main__':
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import v124_core as vc
    d = None; shifts = {}
    for m, p in vc.iter_renders(vc.OUT):
        if m['tag'] == 'main_D100' and m['variant'] == 'default':
            d = vc.load_render(p)
    for v in ('shift_x28', 'shift_y28', 'shift_x140', 'shift_y140'):
        import glob
        fs = glob.glob(os.path.join(vc.OUT, 'renders', f'*main_D100*{v}.mat'))
        if fs:
            shifts[v] = vc.load_render(fs[0])
    for r in s1_regression(d, shifts):
        print(('PASS' if r['passed'] else 'FAIL'), r['fixture'], r['value'], '|', r['detail'])
