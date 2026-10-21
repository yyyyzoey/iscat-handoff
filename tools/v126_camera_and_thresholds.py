"""V126 stage E: GLS detection thresholds, blanks, J-noise, and the
detected vs diameter_reportable separation.

Detection statistic T = Q_null - Q_best (weighted, electron domain, fixed
low-contrast GLS variance V = B + sr^2 + (B+sr^2)/K). Threshold per background
= MAX of that background's 80 dev-blank T values; accept if T > threshold.
Validation blanks (60/background) evaluate only. Binomial 95% upper bound
reported per background.
"""
import csv, json, os, sys
import numpy as np
from scipy.stats import beta as beta_dist

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v126_forward_model as fm
import v126_invert_particle as vin

OUT = os.path.join(fm.REPO, 'results', 'v126')
SIGMA_R = 2.0
KB = 8

def gls_weights(B_hat):
    V = B_hat + SIGMA_R ** 2 + (B_hat + SIGMA_R ** 2) / KB
    return 1.0 / np.sqrt(np.clip(V, 1e-12, None))

def observe(C13, B, rng):
    Ip = np.clip(B * (1.0 + C13), 0, None)
    Y = rng.poisson(Ip) + rng.normal(0, SIGMA_R, C13.shape)
    refs = np.stack([rng.poisson(B, C13.shape) + rng.normal(0, SIGMA_R, C13.shape) for _ in range(KB)])
    return Y, refs

def fit_T(Y, Bhat, model, cand, w):
    """Weighted fit + detection statistic T = Q_null - Q_best."""
    mu0 = Bhat
    Q_null = float(np.sum(((Y - mu0) * w) ** 2))
    def f(p):
        Cm = model.forward(cand, *p)
        if Cm is None:
            return np.full(Y.size, 1e6)
        mu = np.clip(Bhat * (1.0 + Cm), 0, None)
        return ((Y - mu) * w).ravel()
    lo = [30.0, 350.0, -500.0, -500.0]; hi = [200.0, 550.0, 500.0, 500.0]
    best = None
    for D0 in (50.0, 100.0, 160.0):
        for (dx0, dy0) in ((0, 0), (112, -112), (-112, 112)):
            try:
                r = least_squares_wrap(f, [D0, 450.0, dx0, dy0], lo, hi)
            except Exception:
                continue
            Q = float(np.sum(r.fun ** 2))
            if best is None or Q < best[0]:
                best = (Q, [float(v) for v in r.x], int(r.nfev), bool(r.status > 0))
    if best is None:
        return None
    return dict(T=Q_null - best[0], theta=best[1], nfev=best[2], converged=best[3],
                Q_null=Q_null, Q_best=best[0])

def least_squares_wrap(f, x0, lo, hi, maxfev=250):
    from scipy.optimize import least_squares
    return least_squares(f, x0=np.array(x0, float), bounds=(lo, hi),
                         max_nfev=maxfev, xtol=1e-10, ftol=1e-12)

def binomial_upper_bound(k, n, conf=0.95):
    if k == 0:
        return float(1 - (1 - conf) ** (1 / n))
    from scipy.stats import beta
    return float(beta.ppf(conf, k + 1, n - k + 1))

def run(seeds=dict(dev=126100, dev_blank=126200, holdout=126300, val_blank=126400, motion=126500)):
    model = fm.CanonicalModel()
    cand = json.load(open(os.path.join(OUT, 'config', 'model_freeze.json')))['selected_candidate']
    events = 0
    rows_noise, rows_blank = [], []
    thresholds = {}
    # ---- dev targets: 16 conditions x 3 B x 2 reps ----
    rng = np.random.default_rng(seeds['dev'])
    for D in (50.0, 100.0, 160.0, 200.0):
        for h in (375.0, 425.0, 475.0, 525.0):
            Cn = model.node_C(D, h)
            for B in (1e3, 1e4, 1e5):
                w = gls_weights(B)
                for rep in range(2):
                    Y, refs = observe(Cn, B, rng)
                    events += 9
                    Bhat = refs.mean(axis=0)
                    res = fit_T(Y, Bhat, model, cand, w)
                    rows_noise.append(dict(study='dev_target', D_true=D, h_true=h, B=B, rep=rep,
                                           T=res['T'], detected=bool(res['T'] > 0),
                                           D_est=res['theta'][0], h_est=res['theta'][1],
                                           converged=res['converged']))
    # ---- dev blanks: 3 x 80 ----
    for B in (1e3, 1e4, 1e5):
        rng = np.random.default_rng(seeds['dev_blank'] + int(np.log10(B)) * 1000)
        Ts = []
        w = gls_weights(B)
        for i in range(80):
            Y = rng.poisson(B, (13, 13)) + rng.normal(0, SIGMA_R, (13, 13))
            refs = np.stack([rng.poisson(B, (13, 13)) + rng.normal(0, SIGMA_R, (13, 13)) for _ in range(KB)])
            events += 9
            Bhat = refs.mean(axis=0)
            res = fit_T(Y, Bhat, model, cand, w)
            Ts.append(res['T'])
            rows_blank.append(dict(study='dev_blank', B=B, idx=i, T=res['T'], D_est=res['theta'][0]))
        thresholds[B] = float(max(Ts))
    # ---- validation blanks: 3 x 60 (evaluate only) ----
    fpr = {}
    for B in (1e3, 1e4, 1e5):
        rng = np.random.default_rng(seeds['val_blank'] + int(np.log10(B)) * 1000)
        w = gls_weights(B)
        fp = 0
        for i in range(60):
            Y = rng.poisson(B, (13, 13)) + rng.normal(0, SIGMA_R, (13, 13))
            refs = np.stack([rng.poisson(B, (13, 13)) + rng.normal(0, SIGMA_R, (13, 13)) for _ in range(KB)])
            events += 9
            Bhat = refs.mean(axis=0)
            res = fit_T(Y, Bhat, model, cand, w)
            acc = bool(res['T'] > thresholds[B])
            fp += int(acc)
            rows_blank.append(dict(study='validation_blank', B=B, idx=i, T=res['T'],
                                   false_accept=acc, D_est=res['theta'][0]))
        ub = binomial_upper_bound(fp, 60)
        fpr[B] = dict(fp=fp, n=60, rate=fp / 60.0, binom95_upper=ub,
                      target_met=bool(ub <= 0.05))
    json.dump(dict(schema='iscat126.threshold_freeze.1', rule='T > max(dev blank T) per background',
                   thresholds=thresholds, validation_blank_fpr=fpr,
                   note='frozen before J-noise evaluation; 60-validation-blank FPR is evaluation-only'),
              open(os.path.join(OUT, 'config', 'threshold_freeze.json'), 'w', encoding='utf-8'), indent=1)
    # ---- J noise: 6 x 3 x 5 ----
    import h5py
    hp = os.path.join(OUT, 'validation', 'new_holdout_images.h5')
    rng = np.random.default_rng(seeds['holdout'])
    with h5py.File(hp, 'r') as h:
        for tag, D, hnm, x, y in [('J01',41.0,368.5,42.0,-98.0),('J02',67.0,402.5,-126.0,56.0),
                                   ('J03',89.0,437.5,70.0,126.0),('J04',123.0,472.5,-98.0,-70.0),
                                   ('J05',151.0,507.5,126.0,-42.0),('J06',183.0,542.5,-56.0,98.0)]:
            Cn = h[tag]['at_offset/C'][()][2:15, 2:15]
            for B in (1e3, 1e4, 1e5):
                w = gls_weights(B)
                for rep in range(5):
                    Y, refs = observe(Cn, B, rng)
                    events += 9
                    Bhat = refs.mean(axis=0)
                    res = fit_T(Y, Bhat, model, cand, w)
                    detected = bool(res['T'] > thresholds[B])
                    # diameter_reportable: detected + converged + in-domain + non-boundary + identifiable
                    D_est = res['theta'][0]
                    in_domain = bool(30 <= D_est <= 200 and 350 <= res['theta'][1] <= 550)
                    boundary = bool(abs(D_est-30) < 1 or abs(D_est-200) < 1)
                    rows_noise.append(dict(study='J_noise', case=tag, D_true=D, h_true=hnm, B=B, rep=rep,
                                           T=res['T'], detected=detected, converged=res['converged'],
                                           in_domain=in_domain, boundary=boundary,
                                           diameter_reportable=bool(detected and res['converged'] and in_domain and not boundary),
                                           candidate_D=D_est if detected else None,
                                           reportable_D=(D_est if (detected and res['converged'] and in_domain and not boundary) else None),
                                           err_D=(D_est - D) if detected else None))
    json.dump(dict(exposure_events=events), open(os.path.join(OUT, 'logs', 'exposure_events_e.json'), 'w'), indent=1)
    # write CSVs
    keys = sorted({k for r in rows_noise for k in r})
    with open(os.path.join(OUT, 'validation', 'noise_per_trial.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in rows_noise: w.writerow(r)
    keys = sorted({k for r in rows_blank for k in r})
    with open(os.path.join(OUT, 'validation', 'blank_per_trial.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in rows_blank: w.writerow(r)
    model.close()
    return dict(thresholds=thresholds, fpr=fpr, events=events)

if __name__ == '__main__':
    print(run())
