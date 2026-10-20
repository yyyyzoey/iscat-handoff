"""V124 inversion, holdout, noise, height-LOO and lateral-motion studies.

Estimators use ONLY the frozen physical library (17x17 signed C from
NANOBEM stratified-BEM fields). No free per-particle amplitude or phase
is fitted anywhere. All results are CONDITIONAL model-internal estimates;
EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED = false.
"""
import csv, os
import numpy as np
import h5py

import v124_core as vc

OUT = vc.OUT
KBT = 1.380649e-23 * 299.15          # J, 26 C
ETA = 0.870e-3                       # Pa s, pure water 26 C (MODEL_ASSUMPTION)
FS = 5000.0
DT = 1.0 / FS
READ_NOISE_E = 2.0                   # e- (MODEL_ASSUMPTION)
RESID_REJECT = 0.10                  # pre-registered rejection threshold
AMBIG_FACTOR = 1.05
AMBIG_SEP_NM = 10.0
SUPPORT_LIMIT_NM = 2000.0            # |xy| beyond this leaves the computed field support

# ---------------------------------------------------------------- templates
HOLDOUT_D = (35.0, 55.0, 85.0, 115.0, 145.0, 185.0)

def fixed_h_templates(h, h_nm=450.0, exclude_D=HOLDOUT_D):
    Ds, Ts = [], []
    for k in h.keys():
        g = h[k]
        D = float(g.attrs['D_nm'])
        if any(abs(D - xd) < 1e-9 for xd in exclude_D):
            continue
        if abs(float(g.attrs['h_nm']) - h_nm) < 1e-9 and abs(float(g.attrs['n_particle']) - 1.38) < 1e-9:
            Ds.append(D); Ts.append(g['C'][()])
    order = np.argsort(Ds)
    return np.array(Ds)[order], np.array(Ts)[order]

def d100_h_templates(h):
    hs, Ts = [], []
    for k in h.keys():
        g = h[k]
        if abs(float(g.attrs['D_nm']) - 100.0) < 1e-9 and abs(float(g.attrs['n_particle']) - 1.38) < 1e-9:
            hs.append(float(g.attrs['h_nm'])); Ts.append(g['C'][()])
    order = np.argsort(hs)
    return np.array(hs)[order], np.array(Ts)[order]

def _template_at(grid, templates, x):
    if x < grid[0] - 1e-9 or x > grid[-1] + 1e-9:
        return None
    x = min(max(x, grid[0]), grid[-1])
    i = int(np.searchsorted(grid, x) - 1)
    i = min(max(i, 0), len(grid) - 2)
    w = (x - grid[i]) / (grid[i + 1] - grid[i])
    return templates[i] * (1 - w) + templates[i + 1] * w

def _profile(grid, templates, C_obs, step=0.5):
    xg = np.arange(grid[0], grid[-1] + 1e-9, step)
    res = np.empty(len(xg))
    for j, x in enumerate(xg):
        T = _template_at(grid, templates, x)
        res[j] = np.linalg.norm(C_obs - T)
    return xg, res

def _minima(xg, res):
    fmin = float(res.min()); xbest = float(xg[res.argmin()])
    cand = []
    for j in range(1, len(xg) - 1):
        if res[j] <= res[j - 1] and res[j] < res[j + 1] and res[j] <= AMBIG_FACTOR * fmin:
            cand.append(float(xg[j]))
    merged = []
    for x in cand:
        if not merged or x - merged[-1] > AMBIG_SEP_NM:
            merged.append(x)
    return xbest, fmin, merged

# ---------------------------------------------------------------- inversion
def invert_D(C_obs, D_grid, D_templates):
    xg, res = _profile(D_grid, D_templates, C_obs)
    xbest, fmin, competing = _minima(xg, res)
    center_obs = C_obs[8, 8]
    center_lib = np.array([T[8, 8] for T in D_templates])
    roots = []
    for i in range(len(D_grid) - 1):
        f0, f1 = center_lib[i] - center_obs, center_lib[i + 1] - center_obs
        if f0 == 0:
            roots.append(float(D_grid[i]))
        elif f0 * f1 < 0:
            w = f0 / (f0 - f1)
            roots.append(float(D_grid[i] + w * (D_grid[i + 1] - D_grid[i])))
    return dict(D_est_lsq=xbest, rel_residual=float(fmin / max(np.linalg.norm(C_obs), 1e-30)),
                competing_minima=competing, peak_sign_roots=roots,
                rejected=bool(fmin / max(np.linalg.norm(C_obs), 1e-30) > RESID_REJECT),
                boundary=bool(abs(xbest - D_grid[0]) < 1e-9 or abs(xbest - D_grid[-1]) < 1e-9))

def invert_h(C_obs, h_grid, h_templates):
    xg, res = _profile(h_grid, h_templates, C_obs)
    xbest, fmin, competing = _minima(xg, res)
    return dict(h_est_lsq=xbest, rel_residual=float(fmin / max(np.linalg.norm(C_obs), 1e-30)),
                competing_minima=competing,
                rejected=bool(fmin / max(np.linalg.norm(C_obs), 1e-30) > RESID_REJECT))

# ------------------------------------------------------------ observation
def bilinear_stack(A, xs, ys):
    """Sample A[i,j] defined on fine grid (xs[i], ys[j]) at the SAME shifted
    coordinates, i.e. evaluate the field pattern translated by (-shift)."""
    from scipy.interpolate import RegularGridInterpolator
    itp = RegularGridInterpolator((xs, ys), A, bounds_error=False, fill_value=None)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    return itp(np.stack([X, Y], axis=-1))

def frame_C_shifted(fine, dx, dy):
    """C camera image for the particle laterally displaced by (dx,dy):
    sample solved fine-grid intensities at (fx-dx, fy-dy), pixel-average."""
    Iref_f, Isca_f, Icross_f, fx, fy = fine
    sx, sy = fx - dx, fy - dy
    Iref_s = bilinear_stack(Iref_f, sx, sy)
    Isca_s = bilinear_stack(Isca_f, sx, sy)
    Icross_s = bilinear_stack(Icross_f, sx, sy)
    q = 5
    I0 = vc.pixel_mean(Iref_s, q)
    It = vc.pixel_mean(Iref_s + Isca_s + Icross_s, q)
    return (It - I0) / I0

def exposure_frame_counts(C_func, B_e, rng, positions, Texp_us, n_sub=5):
    """Intensity-domain exposure average -> Poisson counts + read noise.
    positions: list of (dx,dy) per sub-time within the exposure window."""
    acc = None
    for (dx, dy) in positions:
        Cf = C_func(dx, dy)
        Ip = B_e * (1.0 + Cf)
        acc = Ip if acc is None else acc + Ip
    Ip_mean = acc / len(positions)
    counts = rng.poisson(np.clip(Ip_mean, 0, None)) + rng.normal(0, READ_NOISE_E, Ip_mean.shape)
    return counts

def static_noisy_observation(C, B_e, rng):
    Ip = B_e * (1.0 + C)
    counts = rng.poisson(np.clip(Ip, 0, None)) + rng.normal(0, READ_NOISE_E, C.shape)
    Ibg_est = rng.poisson(B_e, size=(8,) + C.shape).mean(axis=0)  # 8 blank frames
    return (counts - Ibg_est) / Ibg_est

# ---------------------------------------------------------------- runners
def run_all(seed=20261020):
    rng = np.random.default_rng(seed)
    os.makedirs(os.path.join(OUT, 'validation', 'diameter_profile_per_case'), exist_ok=True)
    lib = open_library()
    Dg, T = fixed_h_templates(lib, 450.0)
    hg, Th = d100_h_templates(lib)
    rows_holdout, rows_noise, rows_hloo = [], [], []

    # ---- clean holdout D inversion --------------------------------------
    import glob
    for p in sorted(glob.glob(os.path.join(OUT, 'renders', '*holdout_D*_default.mat'))):
        m = vc._meta_from_name(p)
        if not (abs(m['np_re'] - 1.38) < 1e-12 and m['mesh'] == 576):
            continue
        r = vc.load_render(p)
        est = invert_D(r['C'], Dg, T)
        rows_holdout.append(dict(case=m['tag'], D_truth_nm=m['D'], h_truth_nm=m['h'],
                                 D_est_nm=est['D_est_lsq'], error_nm=est['D_est_lsq'] - m['D'],
                                 rel_residual=est['rel_residual'], rejected=est['rejected'],
                                 boundary=est['boundary'],
                                 n_competing_minima=len(est['competing_minima']),
                                 competing_minima_nm=';'.join(f'{x:.1f}' for x in est['competing_minima']),
                                 peak_sign_roots_nm=';'.join(f'{x:.1f}' for x in est['peak_sign_roots']),
                                 condition='CLEAN_STATIC'))
        prof_path = os.path.join(OUT, 'validation', 'diameter_profile_per_case', f'{m["tag"]}_profile.csv')
        with open(prof_path, 'w', newline='') as f:
            w = csv.writer(f); w.writerow(['D_nm', 'residual_L2'])
            for xx, rr in zip(*_profile(Dg, T, r['C'], step=0.5)):
                w.writerow([f'{xx:.1f}', f'{rr:.10g}'])

    # ---- static noise sensitivity on holdout D --------------------------
    for p in sorted(glob.glob(os.path.join(OUT, 'renders', '*holdout_D*_default.mat'))):
        m = vc._meta_from_name(p)
        if not (abs(m['np_re'] - 1.38) < 1e-12 and m['mesh'] == 576):
            continue
        r = vc.load_render(p)
        for B in (1e3, 1e4, 1e5):
            for rep in range(5):
                Cobs = static_noisy_observation(r['C'], B, rng)
                est = invert_D(Cobs, Dg, T)
                rows_noise.append(dict(study='static_noise', case=m['tag'], D_truth_nm=m['D'],
                                       background_e_per_pix=B, rep=rep,
                                       D_est_nm=est['D_est_lsq'], error_nm=est['D_est_lsq'] - m['D'],
                                       rel_residual=est['rel_residual'], rejected=est['rejected'],
                                       n_competing_minima=len(est['competing_minima'])))
    # ---- leave-one-out height inversion at D100 -------------------------
    for i, h_true in enumerate(hg):
        mask = np.ones(len(hg), bool); mask[i] = False
        est = invert_h(Th[i], hg[mask], Th[mask])
        rows_hloo.append(dict(study='height_LOO_D100', h_truth_nm=h_true,
                              h_est_nm=est['h_est_lsq'], error_nm=est['h_est_lsq'] - h_true,
                              rel_residual=est['rel_residual'], rejected=est['rejected'],
                              n_competing_minima=len(est['competing_minima'])))
    # ---- lateral motion + exposure study at D100 ------------------------
    g100 = lib['D100_h450']
    fine = (g100['Eref'][()] ** 2)
    Iref_f = np.sum(np.abs(g100['Eref'][()]) ** 2, axis=2)
    Isca_f = np.sum(np.abs(g100['Esca'][()]) ** 2, axis=2)
    Eref_c = g100['Eref'][()]; Esca_c = g100['Esca'][()]
    Icross_f = 2 * np.real(np.sum(np.conj(Eref_c) * Esca_c, axis=2))
    fx, fy = g100['fine_x_nm'][:], g100['fine_y_nm'][:]
    fine_data = (Iref_f, Isca_f, Icross_f, fx, fy)

    # validation of the interpolation forward model against MATLAB shifted renders
    interp_check = {}
    for variant, dxy in (('shift_x140', (140.0, 0.0)), ('shift_y140', (0.0, 140.0))):
        p = glob.glob(os.path.join(OUT, 'renders', f'*main_D100*{variant}.mat'))[0]
        r = vc.load_render(p)
        C_interp = frame_C_shifted(fine_data, *dxy)
        interp_check[variant] = float(np.max(np.abs(C_interp - r['C'])))
    C0 = frame_C_shifted(fine_data, 0.0, 0.0)
    interp_check['zero_shift_max_abs_err'] = float(np.max(np.abs(C0 - g100['C'][()])))

    Dt = KBT / (3 * np.pi * ETA * 100e-9)   # m^2/s, SYNTHETIC_ASSUMPTION Dh=D
    rows_motion = []
    n_traj, n_frames = 12, 8
    for traj in range(n_traj):
        pos = np.zeros((n_frames * 10 + 20, 2))  # 2 ms trajectory at 0.2 ms, padded
        for t in range(1, len(pos)):
            pos[t] = pos[t - 1] + rng.normal(0, np.sqrt(2 * Dt * DT), 2)
        est_by_exp = {}
        for Texp_us, B_e in ((100.0, 1e4), (25.0, 2.5e3)):
            counts_acc = []
            rejected = False
            for j in range(n_frames):
                t0 = j * DT
                subs = []
                for k in range(5):
                    ts = t0 + (k + 0.5) * (Texp_us * 1e-6) / 5
                    idx = int(round(ts / DT)) + 10
                    if abs(pos[idx, 0]) > SUPPORT_LIMIT_NM or abs(pos[idx, 1]) > SUPPORT_LIMIT_NM:
                        rejected = True
                    subs.append(pos[idx])
                counts = exposure_frame_counts(lambda dx, dy: frame_C_shifted(fine_data, dx, dy),
                                               B_e, rng, subs, Texp_us)
                counts_acc.append(counts)
            Cobs = (np.mean(counts_acc, axis=0) - B_e) / B_e
            est = invert_D(Cobs, Dg, T)
            est_by_exp[Texp_us] = (est, rejected)
            rows_motion.append(dict(study='lateral_motion_D100', traj=traj,
                                    exposure_us=Texp_us, background_e_per_pix=B_e,
                                    frames=n_frames, D_est_nm=est['D_est_lsq'],
                                    rel_residual=est['rel_residual'], rejected=bool(est['rejected'] or rejected),
                                    domain_violation=rejected,
                                    n_competing_minima=len(est['competing_minima'])))
    # write CSVs
    def write_csv(name, rows):
        if not rows:
            return
        keys = sorted({k for r0 in rows for k in r0})
        with open(os.path.join(OUT, 'validation', name), 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
            for r0 in rows:
                w.writerow(r0)
    write_csv('holdout_per_particle.csv', rows_holdout)
    write_csv('noise_motion_results.csv', rows_noise + rows_hloo + rows_motion)
    summary = dict(holdout=rows_holdout, interp_check=interp_check,
                  Dt_m2_per_s=Dt,
                   n_motion_rows=len(rows_motion), n_noise_rows=len(rows_noise),
                   n_hloo_rows=len(rows_hloo))
    return summary

if __name__ == '__main__':
    import json
    s = run_all()
    with open(os.path.join(OUT, 'logs', 'invert_summary.json'), 'w') as f:
        json.dump({k: v for k, v in s.items() if k != 'holdout'}, f, indent=1, default=str)
    for r0 in s['holdout']:
        print(r0['case'], 'D_est=%.2f' % r0['D_est_nm'], 'err=%+.2f' % r0['error_nm'],
              'res=%.4f' % r0['rel_residual'], 'reject=%d' % r0['rejected'],
              'multi=%d' % r0['n_competing_minima'])
    print('interp_check:', s['interp_check'])
