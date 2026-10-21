"""V126 corrected pairwise numerics + axis/nonzero-shift qualification (A1)."""
import csv, glob, json, os
import numpy as np

import v124_core as vc
import v125_forward_shift as vfs

REPO = r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff'
V124 = os.path.join(REPO, 'results', 'v124')
V125 = os.path.join(REPO, 'results', 'v125')

def corrected_pairwise():
    """Same-D, same-h, same-material L0 vs L1 pairs from existing fields."""
    rows = []
    import v125_model_library as vml
    camx = vml._camx_flip
    idx = vml.index_v125_renders(V125)
    def load(tag, variant='default'):
        k = (tag, variant, 0.0, 0.0)
        return vc.load_render(idx[k]) if k in idx else None
    pairs = [
        ('D30_h450_np1.38', ('V124', 'main_D30'), ('V125', 'main_D30_L1'), 30.0),
        ('D200_h450_np1.38', ('V124', 'main_D200'), ('V125', 'main_D200_L1'), 200.0),
        ('D100_h450_np_nwater', ('V124', 'sentinel_match_exact'), ('V125', 'match_D100_L1'), 100.0),
    ]
    v124_idx = {}
    for p in glob.glob(os.path.join(V124, 'renders', 'lam520*.mat')):
        try:
            m = vc._meta_from_name(p)
        except Exception:
            continue
        v124_idx[(m['tag'], m['variant'])] = p
    for name, (r0, l0tag), (r1, l1tag), D in pairs:
        if r0 == 'V124':
            k0 = (l0tag, 'default')
            a = vc.load_render(v124_idx[k0]) if k0 in v124_idx else None
        else:
            k0 = (l0tag, 'default', 0.0, 0.0)
            a = vc.load_render(idx[k0]) if k0 in idx else None
        k1 = (l1tag, 'default', 0.0, 0.0)
        b = vc.load_render(idx[k1]) if k1 in idx else None
        if a is None or b is None:
            rows.append(dict(pair=name, status='MISSING_FIELDS'))
            continue
        d = b['C'] - a['C']
        rel = float(np.linalg.norm(d) / np.linalg.norm(a['C']))
        rows.append(dict(pair=name, D_nm=D, same_material=True, same_h=True, same_optics=True,
                         abs_L2=float(np.linalg.norm(d)),
                         relL2=rel, rms=float(np.sqrt(np.mean(d ** 2))),
                         signal_L2=float(np.linalg.norm(a['C'])),
                         floor_ratio=rel,
                         status='PASS' if rel < 0.02 else 'CAUTION',
                         note='same-D/same-h/same-material L0 vs L1; not a true-solution error bound'))
    # independent 1e-5 detune columns (same D100 scale)
    for tag in ('near_match_D100_minus_L0', 'near_match_D100_plus_L0'):
        r = load(tag)
        ex = load('sentinel_match_exact')
        if r is not None and ex is not None:
            rows.append(dict(pair=f'{tag}_detune_C', measured_peak_abs_C=float(np.max(np.abs(r['C']))),
                             exact_peak_abs_C=float(np.max(np.abs(ex['C']))),
                             status='MEASURED',
                             note='detune response vs its own exact-match floor at the SAME D'))
    keys = sorted({k for r in rows for k in r})
    out = os.path.join(REPO, 'results', 'v126', 'qualification', 'corrected_pairwise_numerics.csv')
    with open(out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in rows: w.writerow(r)
    return rows

def axis_and_nonzero_shift(model_h5= os.path.join(REPO, 'results', 'v125', 'library', 'v125_Dh_train_fields.h5')):
    """Explicit +x/+y sentinel on the D100 wide field using the V125 direct
    particle_shift renders (ps_x28 etc.) of the SAME solve - no new BEM."""
    import h5py
    import v125_model_library as vml
    camx = vml._camx_flip
    ridx = vml.index_v125_renders(V125)
    rows = []
    with h5py.File(model_h5, 'r') as h:
        g = h['D100_h450']
        Eref = g['wide/Eref'][()]; Esca = g['wide/Esca'][()]
        fx = g['wide/fine_x_nm'][:]; fy = g['wide/fine_y_nm'][:]
        C0 = g['C'][()]
        for variant, dx, dy in (('ps_x28', 28.0, 0.0), ('ps_mx28', -28.0, 0.0),
                                ('ps_x140', 140.0, 0.0), ('ps_y140', 0.0, 140.0)):
            rdir = os.path.join(V125, 'renders')
            key = ('train_D100_h450', variant, float(dx), float(dy))
            if key not in ridx:
                rows.append(dict(check=f'nonzero_shift_{variant}', status='NOT_EVALUATED',
                                 note='direct render not found'))
                continue
            r = camx(vc.load_render(ridx[key]))
            try:
                Cm = vfs.particle_shift_C(Eref, Esca, fx, fy, dx, dy, q=5, cam_Nx=17)
            except vfs.OutOfDomain as e:
                rows.append(dict(check=f'nonzero_shift_{variant}', status='NOT_EVALUATED', note=str(e)))
                continue
            err = float(np.max(np.abs(Cm - r['C'])))
            rows.append(dict(check=f'nonzero_shift_{variant}', dx=dx, dy=dy,
                             max_abs_err=err, status='PASS' if err < 0.004 else 'FAIL',
                             note='canonical forward vs MATLAB direct shifted-grid render (same solve)'))
    # zero shift replay
    with h5py.File(model_h5, 'r') as h:
        g = h['D100_h450']
        Eref = g['wide/Eref'][()]; Esca = g['wide/Esca'][()]
        fx = g['wide/fine_x_nm'][:]; fy = g['wide/fine_y_nm'][:]
        Cm = vfs.particle_shift_C(Eref, Esca, fx, fy, 0.0, 0.0, q=5, cam_Nx=17)
        err = float(np.max(np.abs(Cm - g['C'][()])))
        rows.append(dict(check='zero_shift_replay', max_abs_err=err,
                         status='PASS' if err < 2e-6 else 'FAIL',
                         note='wide-grid vs standard-grid imaging discretization consistency'))
    keys = sorted({k for r in rows for k in r})
    out = os.path.join(REPO, 'results', 'v126', 'qualification', 'axis_and_nonzero_shift.csv')
    with open(out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in rows: w.writerow(r)
    return rows

if __name__ == '__main__':
    for r in corrected_pairwise():
        print(r.get('pair', r.get('check')), r.get('status'), r.get('relL2', r.get('measured_peak_abs_C', '')))
    for r in axis_and_nonzero_shift():
        print(r['check'], r['status'], r.get('max_abs_err', ''))