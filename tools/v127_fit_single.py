"""V127 P1: closure on 24 pre-registered samples + single-frame fit machinery.

Closure: same-model Y=F(theta_true) (noiseless), inverted from a common start;
require optimal residual <= max(1e-12, 1e-6*||Y||) or document compatible set.
Optimizer: least_squares TRF, x_scale=[50,50,140,140], gtol=ftol=1e-12, xtol=1e-10,
fixed residual scale s_Y=max(||Y||,1e-6), per-start nfev<=800, multi-start <=6
separated basins from a full node+offset coarse scan.
"""
import json, os, sys
import numpy as np
from scipy.optimize import least_squares

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v127_canonical_forward as cf

OUT = os.path.join(cf.REPO, 'results', 'v127')
BOUNDS = ([30.0, 350.0, -500.0, -500.0], [200.0, 550.0, 500.0, 500.0])
XS = [50.0, 50.0, 140.0, 140.0]

# 24 pre-registered in-domain non-node closure samples: cover weak signal (small D),
# small D, high h, two h-basins (h<450 / h>450), nonzero xy; deterministic list.
CLOSURE_SAMPLES = [
    (33.0, 362.5, 40.0, -30.0), (33.0, 537.5, -60.0, 45.0),
    (39.0, 387.5, -80.0, 20.0), (39.0, 512.5, 30.0, -70.0),
    (45.0, 412.5, 0.0, 0.0),   (45.0, 487.5, 70.0, 60.0),
    (58.0, 362.5, -40.0, 80.0), (58.0, 537.5, 90.0, -40.0),
    (67.0, 437.5, -110.0, -60.0), (67.0, 462.5, 55.0, 95.0),
    (83.0, 387.5, 25.0, -85.0), (83.0, 512.5, -65.0, 35.0),
    (95.0, 412.5, 100.0, 40.0), (95.0, 487.5, -95.0, -95.0),
    (112.0, 362.5, -30.0, 65.0), (112.0, 537.5, 45.0, -25.0),
    (135.0, 437.5, 80.0, -110.0), (135.0, 462.5, -55.0, 75.0),
    (152.0, 412.5, -120.0, 30.0), (152.0, 487.5, 65.0, 110.0),
    (176.0, 437.5, 35.0, -55.0), (176.0, 462.5, -45.0, -115.0),
    (193.0, 412.5, 90.0, 20.0), (193.0, 487.5, -75.0, -40.0),
]

def fit_single(Cobs, model, cand, scale, starts, maxfev=800, cap=None):
    """TRF fit with contract settings. Returns list of per-start results."""
    lo, hi = ([30.0, 350.0, -500.0, -500.0], [200.0, 550.0, 500.0, 500.0])
    calls = {'n': 0}
    def f(p):
        if cap is not None and calls['n'] >= cap:
            return np.full(Cobs.size, np.nan_to_num(np.inf) if False else 1e30)
        calls['n'] += 1
        Cm = model.C(*p)
        if Cm is None:
            return np.full(Cobs.size, 1e30)
        return ((Cm - Cobs) / scale).ravel()
    out = []
    for x0 in starts:
        r = least_squares(f, x0=np.array(x0, float), bounds=(lo, hi), method='trf',
                          loss='linear', x_scale=XS, gtol=1e-12, ftol=1e-12, xtol=1e-10,
                          max_nfev=maxfev)
        out.append(dict(theta=[float(v) for v in r.x], cost=float(r.cost),
                        loss=float(np.linalg.norm(r.fun * scale)),  # un-scaled
                        opt=float(r.optimality), nfev=int(r.nfev), njev=int(r.njev or 0),
                        status=int(r.status), message=str(r.message), success=bool(r.status > 0),
                        active_mask=[int(v) for v in np.atleast_1d(r.active_mask)] if hasattr(r, 'active_mask') else []))
    out.sort(key=lambda r: r['loss'])
    return out, calls['n']

def coarse_scan_starts(Cobs, model, cand, offsets, max_basins=6, min_sep=(20.0, 60.0, 100.0, 100.0)):
    scan = []
    for D in model.Ds:
        for h in model.Hs:
            for (dx, dy) in offsets:
                Cm = model.C(D, h, float(dx), float(dy))
                if Cm is None:
                    continue
                scan.append((float(np.linalg.norm(Cobs - Cm)), D, h, float(dx), float(dy)))
    scan.sort(key=lambda r: r[0])
    basins = []
    for v, D, h, dx, dy in scan:
        if all(abs(D - b[1]) > min_sep[0] or abs(h - b[2]) > min_sep[1]
               or abs(dx - b[3]) > min_sep[2] or abs(dy - b[4]) > min_sep[3] for b in basins):
            basins.append((v, D, h, dx, dy))
        if len(basins) >= max_basins:
            break
    return basins, scan

def run_closure(cand):
    model = cf.Candidate(cand)
    rows = []
    common_start = [60.0, 400.0, 0.0, 0.0]
    for theta_true in CLOSURE_SAMPLES:
        Y = model.C(*theta_true)
        nY = float(np.linalg.norm(Y))
        tol = max(1e-12, 1e-6 * nY)
        basins, scan = coarse_scan_starts(Y, model, cand,
                                          offsets=((0, 0), (112, -112), (-112, 112), (112, 112), (-112, -112), (140, 0), (0, 140), (-140, 0), (0, -140)))
        starts = [[b[1], b[2], b[3], b[4]] for b in basins] + [common_start]
        out, ncall = fit_single(Y, model, cand, scale=1.0, starts=starts, maxfev=800)
        best = out[0]
        resid_norm = best['loss']
        closed = bool(resid_norm <= tol)
        errD = best['theta'][0] - theta_true[0]
        errH = best['theta'][1] - theta_true[1]
        rows.append(dict(sample=len(rows), candidate=cand, D_true=theta_true[0], h_true=theta_true[1],
                         x_true=theta_true[2], y_true=theta_true[3],
                         D_hat=best['theta'][0], h_hat=best['theta'][1],
                         x_hat=best['theta'][2], y_hat=best['theta'][3],
                         errD=errD, errH=errH, resid_norm=resid_norm, tol=tol,
                         closed=closed, nfev=best['nfev'], success=best['success'],
                         n_starts=len(out), n_calls=ncall,
                         status=best['status']))
        print(f'{cand} s{len(rows)-1:02d} D={theta_true[0]:g}: Dhat={best["theta"][0]:.2f} errD={errD:+.2f} '
              f'errH={errH:+.1f} resid={resid_norm:.3g} tol={tol:.3g} closed={closed}', flush=True)
    return rows

if __name__ == '__main__':
    all_rows = []
    for cand in ('F1', 'F2', 'F3'):
        rows = run_closure(cand)
        all_rows += rows
    import csv
    keys = sorted({k for r in all_rows for k in r})
    with open(os.path.join(OUT, 'diagnostics', 'canonical_closure.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in all_rows: w.writerow(r)
    n_closed = sum(1 for r in all_rows if r['closed'])
    print('closure:', n_closed, '/', len(all_rows))
