"""V125 S1-C: 3D Brownian trajectory + shared-random-path exposure integration.

Fixes vs V124: (1) nm/s unit bug (delta_nm = 1e9*sqrt(2*Ddiff*dt)*normal);
(2) 3D (x,y,h) motion with the h-domain [350,550] as NUMERICAL support, frames
outside rejected, never clipped; (3) one 1.25us fine path archived, the 2.5us
coarse path is a subsample of the SAME realization; (4) exposure means are
intensity-domain over the window centered at the frame time; (5) 25us window
gets 1/4 photons of 100us at fixed flux.
"""
import numpy as np

KB = 1.380649e-23
T0 = 299.15
ETA = 0.870e-3
FRAME_US = 200.0
FINE_US = 1.25
COARSE_US = 2.5

def diffusion_coeff_m2_s(D_nm):
    return KB * T0 / (3 * np.pi * ETA * (D_nm * 1e-9))

def generate_fine_trajectory(D_nm, n_frames=8, seed=0, h0=450.0,
                             h_support=(350.0, 550.0), lateral_limit_nm=500.0):
    """1.25us fine (x,y,h) path in nm covering all frames with margin.

    Brownian increments in nm: delta = 1e9*sqrt(2*Ddiff*dt_s)*normal.
    h-domain and lateral limit are MODEL SUPPORT (numerical), enforced by
    rejection flags on the affected frames - never clipped."""
    rng = np.random.default_rng(seed)
    Dt = diffusion_coeff_m2_s(D_nm)
    # path starts one half-window BEFORE frame 0 so the frame-0 exposure window
    # [t0-T/2, t0+T/2] is fully covered by the fine path (no negative indices).
    n_pre = int(round((FRAME_US / 2) / FINE_US))
    span_us = n_frames * FRAME_US + FRAME_US
    n = int(round(span_us / FINE_US)) + 1
    t_us = (np.arange(n) - n_pre) * FINE_US
    pos = np.zeros((n, 3))
    pos[0] = (0.0, 0.0, h0)  # position at t=-100us; frame 0 centered at t=0
    sigma_nm = 1e9 * np.sqrt(2 * Dt * (FINE_US * 1e-6))
    steps = rng.normal(0.0, sigma_nm, size=(n - 1, 3))
    pos[1:] = pos[0] + np.cumsum(steps, axis=0)
    # per-frame validity (window fully inside support)
    frame_valid = np.zeros(n_frames, bool)
    frame_center_idx = []
    for j in range(n_frames):
        t_center = j * FRAME_US
        i0 = int(np.searchsorted(t_us, t_center - FRAME_US / 2, side='left'))
        i1 = int(np.searchsorted(t_us, t_center + FRAME_US / 2, side='right'))
        frame_center_idx.append((i0, max(i1, i0 + 1)))  # [i0, i1) window
        win = pos[i0:i1 + 1]
        ok = (np.all(win[:, 2] >= h_support[0]) and np.all(win[:, 2] <= h_support[1])
              and np.all(np.abs(win[:, 0]) <= lateral_limit_nm)
              and np.all(np.abs(win[:, 1]) <= lateral_limit_nm))
        frame_valid[j] = ok
    return dict(t_us=t_us, pos_nm=pos, frame_windows=frame_center_idx,
                frame_valid=frame_valid, D_m2_s=Dt, sigma_nm_fine=sigma_nm,
                D_nm=D_nm, seed=seed, h0=h0,
                support=dict(h=h_support, lateral_nm=lateral_limit_nm))

def coarse_subsample(traj):
    """2.5us path as a strict subsample of the SAME fine realization."""
    idx = np.arange(0, len(traj['t_us']), 2)
    out = dict(traj)
    out['t_us'] = traj['t_us'][idx]
    out['pos_nm'] = traj['pos_nm'][idx]
    out['step_us'] = COARSE_US
    return out

def window_mean_positions(traj, frame, T_us):
    """Positions within the exposure window centered at frame*j*200us.
    Uses the path grid (fine 1.25us or coarse 2.5us); the exposure average is
    over INTENSITY at each sub-time (applied by the forward model)."""
    i0, i1 = traj['frame_windows'][frame]
    idx = np.arange(i0, i1)
    t_us = traj['t_us'][idx]
    t0 = frame * FRAME_US - T_us / 2
    t1 = frame * FRAME_US + T_us / 2
    sel = (t_us >= t0 - 1e-9) & (t_us <= t1 + 1e-9)
    return traj['pos_nm'][idx][sel]

def s1_regression():
    import v125_stats as vs
    rows = []
    # F1: unit fix - rms step must be ~44.7nm/1.25us for D=100nm... check formula
    Dt = diffusion_coeff_m2_s(100.0)
    sigma = 1e9 * np.sqrt(2 * Dt * (FINE_US * 1e-6))
    expected = 1e9 * np.sqrt(2 * Dt * (FINE_US * 1e-6))
    rows.append(dict(fixture='unit_fix_sigma_nm', value=sigma, passed=abs(sigma - expected) < 1e-9 and abs(sigma - 3.55) < 0.1,
                     detail=f'Ddiff={Dt:.4g} m^2/s; 1.25us rms step={sigma:.2f} nm (200us would be 44.9nm)'))
    # F2: same realization for fine/coarse
    tr = generate_fine_trajectory(100.0, seed=3)
    co = coarse_subsample(tr)
    same = np.allclose(co['pos_nm'], tr['pos_nm'][::2])
    rows.append(dict(fixture='coarse_is_subsample_of_fine', value=float(same),
                     passed=same, detail='no re-draw'))
    # F3: out-of-support frames flagged, not clipped
    tr2 = generate_fine_trajectory(100.0, seed=7, h0=549.0)
    rows.append(dict(fixture='h_support_rejection_not_clip',
                     value=float(np.max(tr2['pos_nm'][:, 2])),
                     passed=bool(np.max(tr2['pos_nm'][:, 2]) > 550.0),
                     detail=f'valid frames: {int(tr2["frame_valid"].sum())}/8; max h={np.max(tr2["pos_nm"][:,2]):.1f} (may exceed 550, flagged)'))
    # F4: exposure window uses fine times, not rounded 200us sampling
    i0, i1 = tr['frame_windows'][0]
    rows.append(dict(fixture='window_times_not_rounded', value=float(tr['t_us'][i1-1] - tr['t_us'][i0]),
                     passed=abs((tr['t_us'][i1-1] - tr['t_us'][i0]) - FRAME_US) < 1e-9,
                     detail=f'window span {tr["t_us"][i1-1]-tr["t_us"][i0]:.2f}us at 1.25us grid'))
    return rows

if __name__ == '__main__':
    for r in s1_regression():
        print(('PASS' if r['passed'] else 'FAIL'), r['fixture'], r['value'], '|', r['detail'])
