"""V124 figures from real rendered fields and real inversion outputs."""
import csv, glob, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import h5py

import v124_core as vc

OUT = vc.OUT
FIG = os.path.join(OUT, 'figures')

def _lib():
    return h5py.File(os.path.join(OUT, 'library', 'valid_physical_fields_or_coefficients.h5'), 'r')

def fig_iPSF_examples():
    lib = _lib()
    cases = [('D30_h450', 'D=30nm h=450nm'), ('D100_h450', 'D=100nm h=450nm'),
             ('D200_h450', 'D=200nm h=450nm'), ('D100_h200', 'D=100nm h=200nm'),
             ('D100_h1000', 'D=100nm h=1000nm')]
    avail = [(k, t) for k, t in cases if k in lib]
    fig, axes = plt.subplots(1, len(avail), figsize=(4 * len(avail), 3.8), constrained_layout=True)
    for ax, (k, title) in zip(np.atleast_1d(axes), avail):
        g = lib[k]
        C = g['C'][()]
        x = g['x_nm'][:]; y = g['y_nm'][:]
        vmax = np.max(np.abs(C))
        im = ax.imshow(C, origin='lower', extent=[y[0], y[-1], x[0], x[-1]],
                       cmap='RdBu_r', vmin=-vmax, vmax=vmax, aspect='equal')
        ax.set_title(title + f'\npeak|C|={vmax:.4g}')
        ax.set_xlabel('camera_y (nm)'); ax.set_ylabel('camera_x (nm)')
        plt.colorbar(im, ax=ax, shrink=0.85)
    fig.suptitle('Physical signed iSCAT iPSF (NANOBEM stratified BEM, 520nm, NA0.8, 280nm/px) - CONDITIONAL')
    fig.savefig(os.path.join(FIG, 'physical_iPSF_examples.png'), dpi=160)
    plt.close(fig)

def fig_contrast_vs_D():
    lib = _lib()
    Ds, centers, norms, roles = [], [], [], []
    for k in lib:
        g = lib[k]
        if abs(float(g.attrs['h_nm']) - 450) > 1e-9 or abs(float(g.attrs['n_particle']) - 1.38) > 1e-9:
            continue
        C = g['C'][()]
        Ds.append(float(g.attrs['D_nm'])); centers.append(C[8, 8]); norms.append(np.linalg.norm(C))
        roles.append(g.attrs.get('grid_role', 'train'))
    o = np.argsort(Ds); Ds = np.array(Ds)[o]; centers = np.array(centers)[o]
    norms = np.array(norms)[o]; roles = [roles[i] for i in o]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), constrained_layout=True)
    for a, vals, name in zip(ax, (centers, norms), ('center signed C', 'ROI ||C||_F')):
        a.plot(Ds[[i for i, r in enumerate(roles) if r == 'train']],
               np.array(vals)[[i for i, r in enumerate(roles) if r == 'train']], 'o-', label='train (18D)')
        hd = [Ds[i] for i, r in enumerate(roles) if r == 'holdout']
        hv = np.array(vals)[[i for i, r in enumerate(roles) if r == 'holdout']]
        a.plot(hd, hv, 's', mfc='none', label='independent holdout (6D)')
        a.set_xlabel('D (nm)'); a.set_ylabel(name); a.grid(alpha=.3); a.legend()
    fig.suptitle('h=450nm fixed, np=1.38, real BEM renders - CONDITIONAL_FIXED_HEIGHT_CALIBRATION')
    fig.savefig(os.path.join(FIG, 'contrast_vs_D_at_fixed_h.png'), dpi=160)
    plt.close(fig)

def fig_contrast_vs_h():
    lib = _lib()
    hs, centers, norms = [], [], []
    for k in lib:
        g = lib[k]
        if abs(float(g.attrs['D_nm']) - 100) > 1e-9 or abs(float(g.attrs['n_particle']) - 1.38) > 1e-9:
            continue
        C = g['C'][()]
        hs.append(float(g.attrs['h_nm'])); centers.append(C[8, 8]); norms.append(np.linalg.norm(C))
    o = np.argsort(hs)
    hs = np.array(hs)[o]; centers = np.array(centers)[o]; norms = np.array(norms)[o]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), constrained_layout=True)
    for a, vals, name in zip(ax, (centers, norms), ('center signed C', 'ROI ||C||_F')):
        a.plot(hs, vals, 'o-'); a.set_xlabel('h (nm)'); a.set_ylabel(name); a.grid(alpha=.3)
        a.axvline(450, color='k', ls=':', lw=.8)
    fig.suptitle('D100 height response (sphere-interface coupling from BEM, not sin(2kh) fit)')
    fig.savefig(os.path.join(FIG, 'contrast_vs_h_D100.png'), dpi=160)
    plt.close(fig)

def fig_D_est_vs_truth():
    rows = []
    p = os.path.join(OUT, 'validation', 'holdout_per_particle.csv')
    if os.path.isfile(p):
        with open(p, newline='') as f:
            rows = [r for r in csv.DictReader(f)]
    pn = os.path.join(OUT, 'validation', 'noise_motion_results.csv')
    noise = []
    if os.path.isfile(pn):
        with open(pn, newline='') as f:
            noise = [r for r in csv.DictReader(f) if r.get('study') == 'static_noise']
    fig, ax = plt.subplots(figsize=(6.4, 6.4), constrained_layout=True)
    ax.plot([30, 200], [30, 200], 'k--', lw=.8, label='ideal')
    if rows:
        dt = [float(r['D_truth_nm']) for r in rows]; de = [float(r['D_est_nm']) for r in rows]
        ax.plot(dt, de, 'o', label='clean holdout')
        for r in rows:
            ax.annotate(f"{float(r['error_nm']):+.1f}nm", (float(r['D_truth_nm']), float(r['D_est_nm'])),
                        textcoords='offset points', xytext=(6, 4), fontsize=8)
    for B, mk in ((1000.0, '^'), (10000.0, 'v'), (100000.0, 'x')):
        sel = [r for r in noise if abs(float(r['background_e_per_pix']) - B) < 1e-9]
        if sel:
            ax.plot([float(r['D_truth_nm']) for r in sel], [float(r['D_est_nm']) for r in sel],
                    mk, alpha=.5, label=f'noisy B={B:.0e}')
    ax.set_xlabel('D truth (nm)'); ax.set_ylabel('D estimate (nm)')
    ax.grid(alpha=.3); ax.legend(fontsize=8)
    ax.set_title('Model-internal holdout inversion (SYNTHETIC, not experimental metrology)')
    fig.savefig(os.path.join(FIG, 'D_est_vs_D_truth.png'), dpi=160)
    plt.close(fig)

def fig_fidelity_ambiguity():
    lib = _lib()
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.4), constrained_layout=True)
    # (1) mesh fidelity difference map
    g576 = lib['D100_h450'] if 'D100_h450' in lib else None
    p1444 = glob.glob(os.path.join(OUT, 'renders', '*refmesh_D100*_default.mat'))
    if g576 is not None and p1444:
        r1444 = vc.load_render(p1444[0])
        diff = r1444['C'] - g576['C'][()]
        x = g576['x_nm'][:]; y = g576['y_nm'][:]
        vmax = np.max(np.abs(diff)) or 1
        im = ax[0].imshow(diff, origin='lower', extent=[y[0], y[-1], x[0], x[-1]],
                          cmap='RdBu_r', vmin=-vmax, vmax=vmax, aspect='equal')
        ax[0].set_title(f'1444-576 mesh C diff (relL2={np.linalg.norm(diff)/np.linalg.norm(g576["C"][()]):.4f})')
        plt.colorbar(im, ax=ax[0], shrink=.85)
    # (2) ambiguity: residual profiles for two holdout cases
    p = os.path.join(OUT, 'validation', 'diameter_profile_per_case')
    files = sorted(glob.glob(os.path.join(p, '*.csv')))[:3]
    for fp in files:
        data = list(csv.reader(open(fp)))[1:]
        d = np.array([float(r[0]) for r in data]); r = np.array([float(r[1]) for r in data])
        ax[1].plot(d, r / r.min(), label=os.path.basename(fp).replace('_profile.csv', ''))
    ax[1].axhline(1.05, color='k', ls=':', lw=.8)
    ax[1].set_yscale('log'); ax[1].set_xlabel('D (nm)'); ax[1].set_ylabel('normalized residual')
    ax[1].set_title('D ambiguity profiles (dotted = 1.05x competing level)')
    ax[1].legend(fontsize=7); ax[1].grid(alpha=.3)
    # (3) height LOO errors
    pn = os.path.join(OUT, 'validation', 'noise_motion_results.csv')
    if os.path.isfile(pn):
        with open(pn, newline='') as f:
            loo = [r for r in csv.DictReader(f) if r.get('study') == 'height_LOO_D100']
        if loo:
            ht = [float(r['h_truth_nm']) for r in loo]; he = [float(r['error_nm']) for r in loo]
            ax[2].stem(ht, he)
        ax[2].set_xlabel('h truth (nm)'); ax[2].set_ylabel('h est - truth (nm)')
        ax[2].set_title('D100 leave-one-out height inversion')
        ax[2].grid(alpha=.3)
    fig.suptitle('Model fidelity and ambiguity - CONDITIONAL / EXPERIMENTAL_NOT_VALIDATED')
    fig.savefig(os.path.join(FIG, 'model_fidelity_and_ambiguity.png'), dpi=160)
    plt.close(fig)

def make_all():
    os.makedirs(FIG, exist_ok=True)
    fig_iPSF_examples(); fig_contrast_vs_D(); fig_contrast_vs_h()
    fig_D_est_vs_truth(); fig_fidelity_ambiguity()
    print('figures written to', FIG)

if __name__ == '__main__':
    make_all()
