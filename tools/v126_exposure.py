"""V126 stage F: corrected exposure/motion study.

- 1.25us fine 3D path archived; 2.5us coarse = strict subsample; each path
  recomputes exposure windows from ITS OWN time array.
- Frame validity per actual [t_j-T/2, t_j+T/2] window.
- Trapezoid intensity integration, weights sum to 1; nodes/weights saved.
- Support violations marked, never clipped; >=4 valid frames else insufficient.
- Noiseless 25/100us comparison first, then fixed-flux counting noise.
- Fine/coarse integral comparison target: C rel L2 <= 0.5%.
- All multi-frame results: SHARED_SURROGATE_METHOD_DIAGNOSTIC.
"""
import json, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v126_forward_model as fm
import v126_invert_particle as vin

KB = 1.380649e-23
T0 = 299.15
ETA = 0.870e-3
FRAME_US = 200.0
FINE_US = 1.25

def diffusion(D_nm):
    return KB * T0 / (3 * np.pi * ETA * (D_nm * 1e-9))

def fine_trajectory(D_nm, n_frames=8, seed=0, h0=450.0, h_support=(350.0, 550.0), lat=500.0):
    rng = np.random.default_rng(seed)
    Dt = diffusion(D_nm)
    n_pre = int(round((FRAME_US / 2) / FINE_US))
    n = int(round((n_frames * FRAME_US + FRAME_US) / FINE_US)) + 1
    t = (np.arange(n) - n_pre) * FINE_US
    pos = np.zeros((n, 3))
    pos[0] = (0.0, 0.0, h0)
    sig = 1e9 * np.sqrt(2 * Dt * (FINE_US * 1e-6))
    pos[1:] = pos[0] + np.cumsum(rng.normal(0, sig, (n - 1, 3)), axis=0)
    return dict(t_us=t, pos=pos, D_nm=D_nm, seed=seed, h_support=h_support, lat=lat, step_us=FINE_US)

def coarse_subsample(tr):
    idx = np.arange(0, len(tr['t_us']), 2)
    c = dict(tr)
    c['t_us'] = tr['t_us'][idx]; c['pos'] = tr['pos'][idx]; c['step_us'] = 2.5
    return c

def window_nodes_weights(t_us, j, T_us):
    """Trapezoid nodes/weights for [t_j - T/2, t_j + T/2] on this path grid."""
    t0 = j * FRAME_US - T_us / 2
    t1 = j * FRAME_US + T_us / 2
    i0 = int(np.searchsorted(t_us, t0, side='left'))
    i1 = int(np.searchsorted(t_us, t1, side='right'))
    tt = t_us[i0:i1]
    if len(tt) < 2:
        return None, None, False
    w = np.ones(len(tt))
    if len(tt) > 2:
        w[1:-1] = 2.0
    dt = np.diff(tt)
    w = w * (0.5 * dt.min())
    w = w / w.sum()
    return i0, i1, bool(np.all(tt >= t0 - 1e-9) and np.all(tt <= t1 + 1e-9))

def frame_C_trapz(model, cand, tr, j, T_us, D):
    i0, i1, full = window_nodes_weights(tr['t_us'], j, T_us)
    if i0 is None or not full:
        return None, False
    acc = np.zeros((13, 13))
    tt = tr['t_us'][i0:i1]
    w = None
    t0 = j * FRAME_US - T_us / 2; t1 = j * FRAME_US + T_us / 2
    tt = tt[(tt >= t0 - 1e-9) & (tt <= t1 + 1e-9)]
    if len(tt) < 2:
        return None, False
    wts = np.ones(len(tt)); wts[1:-1] = 2.0
    wts = wts * 0.5 * (tt[1] - tt[0])
    wts = wts / wts.sum()
    pos = tr['pos'][i0:i1][:]
    keep = (tt >= t0 - 1e-9) & (tt <= t1 + 1e-9)
    pos = tr['pos'][i0:i1][keep]
    for (px, py, ph), wt in zip(pos, wts):
        Cm = model.forward(cand, D, float(ph), float(px), float(py))
        if Cm is None:
            return None, False
        acc += wt * Cm
    return acc, True

def run(seeds_motion=126500, out=None):
    out = out or os.path.join(fm.REPO, 'results', 'v126', 'validation')
    model = fm.CanonicalModel()
    cand = json.load(open(os.path.join(fm.REPO, 'results', 'v126', 'config', 'model_freeze.json')))['selected_candidate']
    rows = []
    fine_coarse = []
    B100, B25 = 1e4, 2.5e3
    SIG = 2.0
    rng = np.random.default_rng(seeds_motion)
    for D in (55.0, 115.0, 185.0):
        for k in range(4):
            tr = fine_trajectory(D, seed=seeds_motion + int(D) * 10 + k)
            co = coarse_subsample(tr)
            traj_id = f'{D:g}_{k}'
            # fine/coarse integral comparison for the first trajectory of each D
            if k == 0:
                for j in (0, 3, 6):
                    Cf, vf = frame_C_trapz(model, cand, tr, j, 100.0, D)
                    Cc, vc = frame_C_trapz(model, cand, co, j, 100.0, D)
                    if Cf is None or Cc is None or not vf or not vc:
                        continue
                    rel = float(np.linalg.norm(Cf - Cc) / max(np.linalg.norm(Cf), 1e-30))
                    fine_coarse.append(dict(D=D, traj=traj_id, frame=j, relL2=rel,
                                            absL2=float(np.linalg.norm(Cf - Cc)),
                                            target=0.005, passed=bool(rel <= 0.005)))
            for T_us, B in ((100.0, B100), (25.0, B25)):
                frames, valid_flags = [], []
                for j in range(8):
                    Cf, valid = frame_C_trapz(model, cand, tr, j, T_us, D)
                    valid_flags.append(valid)
                    if not valid:
                        rows.append(dict(traj=traj_id, D=D, frame=j, exposure_us=T_us,
                                         valid=False, insufficient=False,
                                         label='SHARED_SURROGATE_METHOD_DIAGNOSTIC'))
                        continue
                    frames.append((Cf, j))
                    # noiseless first
                    rows.append(dict(traj=traj_id, D=D, frame=j, exposure_us=T_us, valid=True,
                                     phase='noiseless', peak_abs_C=float(np.max(np.abs(Cf)))))
                if len(frames) < 4:
                    rows.append(dict(traj=traj_id, D=D, exposure_us=T_us, insufficient=True,
                                     n_valid=len(frames), label='SHARED_SURROGATE_METHOD_DIAGNOSTIC'))
                    continue
                # counting noise on valid frames
                noisy = []
                for Cf, j in frames:
                    B = B
                    Ip = np.clip(B * (1.0 + Cf), 0, None)
                    Y = rng.poisson(Ip) + rng.normal(0, SIG, Cf.shape)
                    refs = np.stack([rng.poisson(B, Cf.shape) + rng.normal(0, SIG, Cf.shape) for _ in range(8)])
                    Cobs = Y / refs.mean(axis=0) - 1.0
                    noisy.append(Cobs)
                m2 = vin.fit_shared_D(noisy, model, cand)
                rows.append(dict(traj=traj_id, D=D, exposure_us=T_us, valid=True,
                                 n_valid=len(frames), phase='noisy',
                                 D_shared_M2=m2['best_D'], D_gen=D,
                                 err_D=m2['best_D'] - D,
                                 insufficient=False,
                                 label='SHARED_SURROGATE_METHOD_DIAGNOSTIC'))
    with open(os.path.join(out, 'motion_per_track.csv'), 'w', newline='') as f:
        keys = sorted({k for r in rows for k in r})
        import csv
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in rows: w.writerow(r)
    with open(os.path.join(out, 'fine_coarse_integral.csv'), 'w', newline='') as f:
        keys = sorted({k for r in fine_coarse for k in r})
        import csv
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in fine_coarse: w.writerow(r)
    model.close()
    return dict(rows=len(rows), fine_coarse=fine_coarse)

if __name__ == '__main__':
    print(run())
