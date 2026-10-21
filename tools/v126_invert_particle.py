"""V126 continuous-D inversion with robust multi-start and real profiles.

- fit_joint: bounded least_squares (TRF) over (D,h,x,y), multi-start from a
  coarse node+offset scan; loss guard (returned loss must not exceed the best
  scan-model point; otherwise the scan point is returned with flag).
- d_profile: for each D on a grid, (h,x,y) are RE-OPTIMIZED (continuation);
  this is the ambiguity evidence, not a 1-D curve readout.
- fit_shared_D: K frames, ONE continuous D, per-frame (h,x,y) warm-started.
"""
import numpy as np
from scipy.optimize import least_squares

BOUNDS = ([30.0, 350.0, -500.0, -500.0], [200.0, 550.0, 500.0, 500.0])
NAMES = ['D', 'h', 'x', 'y']

def _resid_fn(Cobs, model, cand):
    def f(p):
        Cm = model.forward(cand, *p)
        if Cm is None:
            return np.full(Cobs.size, 1e3)
        return (Cobs - Cm).ravel()
    return f

def fit_joint(Cobs, model, cand, extra_starts=(), maxfev=300, scan_offsets=((0,0),)):
    lo, hi = BOUNDS
    # coarse scan over nodes x offsets
    scan = []
    for D in model.Ds:
        for h in model.Hs:
            for (dx, dy) in scan_offsets:
                Cm = model.forward(cand, D, h, float(dx), float(dy))
                if Cm is None:
                    continue
                scan.append((float(np.linalg.norm(Cobs - Cm)), D, h, float(dx), float(dy)))
    scan.sort(key=lambda r: r[0])
    starts = [(v, D, h, dx, dy) for v, D, h, dx, dy in scan[:5]]
    for ex in extra_starts:
        starts.append((np.inf, *ex))
    best = None
    f = _resid_fn(Cobs, model, cand)
    for v0, D0, h0, dx0, dy0 in starts:
        r = least_squares(f, x0=np.array([D0, h0, dx0, dy0]), bounds=(lo, hi),
                          max_nfev=maxfev, xtol=1e-10, ftol=1e-12)
        loss = float(np.linalg.norm(r.fun))
        if best is None or loss < best['loss']:
            best = dict(loss=loss, theta=[float(v) for v in r.x], nfev=int(r.nfev),
                        status=int(r.status), success=bool(r.status > 0))
    # loss guard vs best scan-model point
    if scan and best['loss'] > scan[0][0] * 1.000001:
        best['loss_guard_fallback'] = True
        best['theta'] = [scan[0][1], scan[0][2], scan[0][3], scan[0][4]]
        best['loss'] = scan[0][0]
    best['scan_best_loss'] = scan[0][0] if scan else None
    return best

def d_profile(Cobs, model, cand, step=4.0, maxfev=150):
    """For each D: re-optimize (h,x,y) with continuation warm start."""
    prof = []
    warm = [450.0, 0.0, 0.0]
    f = _resid_fn(Cobs, model, cand)
    for D in np.arange(30.0, 200.0 + 1e-9, step):
        r = least_squares(lambda p: f([D, p[0], p[1], p[2]]), x0=np.array(warm),
                          bounds=([350.0, -500.0, -500.0], [550.0, 500.0, 500.0]),
                          max_nfev=maxfev, xtol=1e-10, ftol=1e-12)
        warm = [float(r.x[0]), float(r.x[1]), float(r.x[2])]
        prof.append(dict(D=float(D), h=warm[0], x=warm[1], y=warm[2],
                         loss=float(np.linalg.norm(r.fun)), nfev=int(r.nfev)))
    return prof

def fit_shared_D(frames, model, cand, D_candidates=None, per_frame_maxfev=60):
    """K frames, ONE continuous D; per-frame (h,x,y) warm-started. Returns the
    continuous-D solution and the D-profile over the node grid (continuation)."""
    Dc = D_candidates or list(model.Ds)
    results = []
    warm = [450.0, 0.0, 0.0]
    for D in Dc:
        total = 0.0
        per = []
        w = list(warm)
        for Cobs in frames:
            def g(p):
                Cm = model.forward(cand, D, p[0], p[1], p[2])
                if Cm is None:
                    return np.full(Cobs.size, 1e3)
                return (Cobs - Cm).ravel()
            r = least_squares(g, x0=np.array(w), bounds=([350.0, -500.0, -500.0], [550.0, 500.0, 500.0]),
                              max_nfev=per_frame_maxfev, xtol=1e-10, ftol=1e-12)
            w = [float(r.x[0]), float(r.x[1]), float(r.x[2])]
            total += float(np.linalg.norm(r.fun))
            per.append(dict(h=w[0], x=w[1], y=w[2], loss=float(np.linalg.norm(r.fun))))
        results.append(dict(D=float(D), total_loss=total, per_frame=per))
    results.sort(key=lambda r: r['total_loss'])
    best = results[0]
    # continuous refinement of D around the best node (scalar golden-section-like
    # via least_squares on D with per-frame warm starts frozen at node solution)
    def total_at(D):
        tot = 0.0
        w = [best['per_frame'][0]['h'], best['per_frame'][0]['x'], best['per_frame'][0]['y']]
        for Cobs in frames:
            def g(p):
                Cm = model.forward(cand, D, p[0], p[1], p[2])
                if Cm is None:
                    return np.full(Cobs.size, 1e3)
                return (Cobs - Cm).ravel()
            r = least_squares(g, x0=np.array(w), bounds=([350.0, -500.0, -500.0], [550.0, 500.0, 500.0]),
                              max_nfev=per_frame_maxfev, xtol=1e-10, ftol=1e-12)
            w = [float(r.x[0]), float(r.x[1]), float(r.x[2])]
            tot += float(np.linalg.norm(r.fun))
        return tot, w
    Dgrid_fine = np.arange(max(30.0, best['D'] - 12.0), min(200.0, best['D'] + 12.0) + 1e-9, 2.0)
    fine = []
    for D in Dgrid_fine:
        tot, _ = total_at(D)
        fine.append((float(D), tot))
    fine.sort(key=lambda r: r[1])
    return dict(best_D=fine[0][0], best_loss=fine[0][1], D_profile_fine=fine,
                node_results=results)
