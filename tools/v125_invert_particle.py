"""V125 inversion: M0/M1/M2 estimators on anonymous signed-C images.

M0: center-amplitude only, h=450/centered (bias diagnostic).
M1: joint (D,h,x,y) on the central 13x13 ROI; coarse shift-table scan ->
    bounded Nelder-Mead refinement per basin; frozen budget.
M2: K frames, ONE shared D, per-frame (h,x,y).

Rejection/ambiguity thresholds come from v125_thresholds (frozen on dev data
before any V125 holdout is opened). No truth inputs anywhere.
"""
import json, os
import numpy as np
from scipy.optimize import minimize

import v125_stats as vst

OUT_DEFAULT = None
SCORE = (slice(2, 15), slice(2, 15))

def residual_L2(Cobs, Cmod):
    return float(np.linalg.norm(Cobs - Cmod))

class Estimator:
    def __init__(self, model, score_slice=SCORE):
        self.m = model
        self.sl = score_slice

    # ---------------- M0 ----------------
    def m0(self, Cobs, h_fixed=450.0):
        center = Cobs[6, 6]
        Ds = np.linspace(30, 200, 341)
        vals = np.array([self.m.template_C(D, h_fixed)[6, 6] for D in Ds])
        i = int(np.argmin(np.abs(vals - center)))
        roots = []
        for k in range(len(Ds) - 1):
            f0, f1 = vals[k] - center, vals[k + 1] - center
            if f0 * f1 < 0:
                roots.append(float(Ds[k] + (Ds[k + 1] - Ds[k]) * f0 / (f0 - f1)))
        return dict(D_est=float(Ds[i]), roots=roots, method='M0')

    # ---------------- M1 ----------------
    def _objective_table(self, Cobs):
        def f(p):
            D, h, dx, dy = p
            Cm = self.m.c_table(D, h, dx, dy)
            if Cm is None:
                return 1e6
            return residual_L2(Cobs, Cm)
        return f

    def _objective_exact(self, Cobs):
        calls = {'n': 0}
        def f(p):
            D, h, dx, dy = p
            if calls['n'] >= 600:
                return 1e6
            calls['n'] += 1
            Cm = self.m.forward_exact(D, h, dx, dy)
            if Cm is None:
                return 1e6
            return residual_L2(Cobs, Cm)
        f.count = calls
        return f

    def m1(self, Cobs, max_iter_ms=10000, offset_scan=((-224.0, 0.0), (224.0, 0.0), (0.0, -224.0), (0.0, 224.0), (0.0, 0.0), (112.0, -112.0), (-112.0, 112.0), (112.0, 112.0), (-112.0, -112.0))):
        """Frozen search: full node+offset scan -> top basins -> bounded refine."""
        ft = self._objective_table(Cobs)
        scan = []
        for D in self.m.Ds:
            for h in self.m.Hs:
                for (dx, dy) in offset_scan:
                    v = ft((D, h, dx, dy))
                    scan.append((v, D, h, dx, dy))
        scan.sort(key=lambda r0: r0[0])
        basins = []
        for v, D, h, dx, dy in scan:
            if all(abs(D - b[1]) > 20 or abs(h - b[2]) > 60 for b in basins):
                basins.append((v, D, h, dx, dy))
            if len(basins) >= 3:
                break
        fx = self._objective_exact(Cobs)
        results = []
        for v0, D0, h0, dx0, dy0 in basins:
            r = minimize(fx, x0=np.array([D0, h0, dx0, dy0]),
                         method='Nelder-Mead',
                         bounds=[(30, 200), (350, 550), (-500, 500), (-500, 500)],
                         options=dict(maxfev=400, xatol=0.5, fatol=1e-10))
            inb = [bool(abs(r.x[0] - 30) < 1 or abs(r.x[0] - 200) < 1),
                   bool(abs(r.x[1] - 350) < 1 or abs(r.x[1] - 550) < 1),
                   bool(abs(r.x[2]) > 499 or abs(r.x[3]) > 499)]
            results.append(dict(loss=float(r.fun), D=float(r.x[0]), h=float(r.x[1]),
                                x=float(r.x[2]), y=float(r.x[3]), nfev=int(fx.count['n']),
                                boundary_D=inb[0], boundary_h=inb[1], boundary_xy=inb[2]))
        results.sort(key=lambda r0: r0['loss'])
        Dprof = self.d_profile(Cobs, results[0])
        return dict(method='M1', best=results[0], basins=results,
                    D_profile=Dprof, nfev_total=int(fx.count['n']))

    def d_profile(self, Cobs, best):
        """Residual as a function of D at the best (h,x,y): multi-solution evidence."""
        prof = []
        for D in np.arange(30, 200.1, 2.0):
            Cm = self.m.forward_exact(D, best['h'], best['x'], best['y'])
            if Cm is None:
                prof.append((float(D), None)); continue
            prof.append((float(D), residual_L2(Cobs, Cm)))
        return prof

    # ---------------- M2 ----------------
    def m2(self, frames, max_frames=None):
        """frames: list of anonymous Cobs (13x13). Shared D, per-frame (h,x,y)."""
        out = []
        for D in self.m.Ds:
            total = 0.0
            per_frame = []
            for Cobs in frames[:max_frames]:
                ft = self._objective_table(Cobs)
                scan = sorted(((ft((D, h, dx, dy)), h, dx, dy)
                               for h in self.m.Hs for (dx, dy) in ((0, 0), (112, -112), (-112, 112), (112, 112), (-112, -112), (224, 0), (-224, 0), (0, 224), (0, -224))),
                              key=lambda r0: r0[0])
                v0, h0, dx0, dy0 = scan[0]
                fx = self._objective_exact(Cobs)
                r = minimize(lambda p: fx((D, p[0], p[1], p[2])), x0=np.array([h0, dx0, dy0]),
                             method='Nelder-Mead',
                             bounds=[(350, 550), (-500, 500), (-500, 500)],
                             options=dict(maxfev=150, xatol=0.5, fatol=1e-10))
                total += float(r.fun)
                per_frame.append(dict(h=float(r.x[0]), x=float(r.x[1]), y=float(r.x[2]),
                                      loss=float(r.fun), valid_h=bool(350 <= r.x[0] <= 550)))
            out.append(dict(D=float(D), total_loss=total, per_frame=per_frame))
        out.sort(key=lambda r0: r0['total_loss'])
        return dict(method='M2', best_D=out[0]['D'], D_candidates=out)

# ---------------- noise objective (S6-A) ----------------
def electron_objective(Y, B_hat, C_model, sigma_r=2.0, K_blank=8):
    """Weighted NLL-like residual in the electron domain (contract variance)."""
    mu = np.clip(B_hat * (1.0 + C_model), 0, None)
    C = mu / B_hat - 1.0
    var = mu + sigma_r ** 2 + (1.0 + C) ** 2 * (B_hat + sigma_r ** 2) / K_blank
    w = (Y - mu) / np.sqrt(np.clip(var, 1e-12, None))
    return float(np.sqrt(np.mean(w ** 2)))

def m1_noisy(Y, B_hat, model, C_of, sigma_r=2.0, K_blank=8):
    chi_null = electron_objective(Y, B_hat, np.zeros_like(Y), sigma_r, K_blank)
    """M1 with the electron-domain objective; C_of(D,h,x,y) -> 13x13 model C."""
    calls = {'n': 0}
    def f(p):
        D, h, dx, dy = p
        if calls['n'] >= 600:
            return 1e6
        calls['n'] += 1
        Cm = C_of(D, h, dx, dy)
        if Cm is None:
            return 1e6
        return electron_objective(Y, B_hat, Cm, sigma_r, K_blank)
    # coarse scan via table (C-domain proxy for basin finding)
    scan = []
    for D in model.Ds:
        for h in model.Hs:
            for (dx, dy) in ((0, 0), (112, -112), (-112, 112), (112, 112), (-112, -112)):
                scan.append((residual_L2(Y / B_hat - 1.0, model.c_table(D, h, dx, dy)), D, h, dx, dy))
    scan.sort(key=lambda r0: r0[0])
    basins = []
    for v, D, h, dx, dy in scan:
        if all(abs(D - b[1]) > 20 or abs(h - b[2]) > 60 for b in basins):
            basins.append((v, D, h, dx, dy))
        if len(basins) >= 2:
            break
    best = None
    for v0, D0, h0, dx0, dy0 in basins:
        r = minimize(f, x0=np.array([D0, h0, dx0, dy0]), method='Nelder-Mead',
                     bounds=[(30, 200), (350, 550), (-500, 500), (-500, 500)],
                     options=dict(maxfev=150, xatol=0.5, fatol=1e-8))
        if best is None or r.fun < best.fun:
            best = r
    return dict(D=float(best.x[0]), h=float(best.x[1]), x=float(best.x[2]), y=float(best.x[3]),
                wres=float(best.fun), chi_null=chi_null,
                delta=chi_null - float(best.fun), nfev=calls['n'])
