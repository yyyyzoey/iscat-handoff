"""V127 P4: GLS camera + thresholds + J/K noise with raw data archive."""
import csv, json, os, sys
import numpy as np
from scipy.stats import beta as _beta
from scipy.optimize import least_squares

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v127_canonical_forward as cf

OUT = os.path.join(cf.REPO, 'results', 'v127')
SIG = 2.0
KB = 8

def gls_w(B):
    return 1.0 / np.sqrt(np.clip(B + SIG**2 + (B + SIG**2)/KB, 1e-12, None))

def cp_upper(k, n, conf=0.95):
    if k == 0: return float(1 - (1-conf)**(1/n))
    if k == n: return 1.0
    return float(_beta.ppf(conf, k+1, n-k))

def observe(C13, B, rng):
    Ip = np.clip(B*(1.0+C13), 0, None)
    Y = rng.poisson(Ip) + rng.normal(0, SIG, C13.shape)
    refs = np.stack([rng.poisson(B, C13.shape) + rng.normal(0, SIG, C13.shape) for _ in range(KB)])
    return Y, refs

def fit_T(Y, Bhat, model, cand, w):
    Q_null = float(np.sum(((Y-Bhat)*w)**2))
    def f(p):
        out = model.forward(p)
        if out[2] is None: return np.full(Y.size, 1e6)
        Ibg, I, C, valid, reason = out
        mu = np.clip(Bhat*(1.0+C), 0, None)
        return ((Y-mu)*w).ravel()
    best = None
    for D0 in (50.0, 100.0, 160.0):
        for (dx0, dy0) in ((0,0),(112,-112),(-112,112)):
            try:
                r = least_squares(f, x0=np.array([D0,450.0,dx0,dy0]),
                                  bounds=([30,350,-500,-500],[200,550,500,500]),
                                  x_scale=[50,50,140,140], gtol=1e-12, ftol=1e-12, xtol=1e-10,
                                  max_nfev=250)
            except Exception: continue
            Q = float(np.sum(r.fun**2))
            if best is None or Q < best[0]:
                best = (Q, [float(v) for v in r.x], int(r.nfev), bool(r.status>0))
    return dict(T=Q_null-best[0], theta=best[1], nfev=best[2], converged=best[3])

def run(seeds=dict(dev=127100, dev_blank=127200, holdout=127300, val_blank=127400)):
    model = cf.Candidate('F1')
    truth = json.load(open(os.path.join(OUT, 'validation', 'holdout_truth_validator_only.json')))
    thresholds, rows_noise, rows_blank, raw = {}, {}, [], []
    events = 0
    # dev targets
    rng = np.random.default_rng(seeds['dev'])
    cfg = json.load(open(os.path.join(cf.REPO, 'config', 'v127_science_config.json')))
    devD, devH = cfg['noise']['dev_D_nm'], cfg['noise']['dev_h_nm']
    for D in devD:
        for h in devH:
            Cn = model.node_C(D, h)
            for B in (1e3, 1e4, 1e5):
                w = gls_w(B)
                for rep in range(2):
                    Y, refs = observe(Cn, B, rng); events += 9
                    raw.append(dict(kind='dev_target', D=D, h=h, B=B, rep=rep, Y=Y, refs=refs))
                    Bhat = refs.mean(axis=0)
                    res = fit_T(Y, Bhat, model, 'F1', w)
                    rows_noise.append(dict(study='dev_target', D_true=D, h_true=h, B=B, rep=rep,
                                           T=res['T'], detected=bool(res['T']>0), D_est=res['theta'][0]))
    # dev blanks: threshold = max dev blank T per B
    for B in (1e3, 1e4, 1e5):
        rng = np.random.default_rng(seeds['dev_blank'] + int(np.log10(B))*1000)
        w = gls_w(B); Ts = []
        for i in range(80):
            Y = rng.poisson(B, (13,13)) + rng.normal(0, SIG, (13,13))
            refs = np.stack([rng.poisson(B, (13,13)) + rng.normal(0, SIG, (13,13)) for _ in range(KB)])
            events += 9
            raw.append(dict(kind='dev_blank', B=B, idx=i, Y=Y, refs=refs))
            Bhat = refs.mean(axis=0)
            res = fit_T(Y, Bhat, model, 'F1', w)
            Ts.append(res['T'])
            rows_blank.append(dict(study='dev_blank', B=B, idx=i, T=res['T']))
        thresholds[B] = float(max(Ts))
    # validation blanks
    fpr = {}
    for B in (1e3, 1e4, 1e5):
        rng = np.random.default_rng(seeds['val_blank'] + int(np.log10(B))*1000)
        w = gls_w(B); fp = 0
        for i in range(60):
            Y = rng.poisson(B, (13,13)) + rng.normal(0, SIG, (13,13))
            refs = np.stack([rng.poisson(B, (13,13)) + rng.normal(0, SIG, (13,13)) for _ in range(KB)])
            events += 9
            raw.append(dict(kind='val_blank', B=B, idx=i, Y=Y, refs=refs))
            Bhat = refs.mean(axis=0)
            res = fit_T(Y, Bhat, model, 'F1', w)
            acc = bool(res['T'] > thresholds[B]); fp += int(acc)
            rows_blank.append(dict(study='validation_blank', B=B, idx=i, T=res['T'], false_accept=acc))
        fpr[B] = dict(fp=fp, n=60, rate=fp/60, cp95=cp_upper(fp,60), target_met=bool(cp_upper(fp,60)<=0.05))
    # K noise
    import h5py
    hp = os.path.join(OUT, 'validation', 'holdout_images.h5')
    rng = np.random.default_rng(seeds['holdout'])
    with h5py.File(hp, 'r') as h:
        for c in truth:
            Cn = h[c['case']]['at_offset/C'][()][2:15, 2:15]
            for B in (1e3, 1e4, 1e5):
                w = gls_w(B)
                for rep in range(5):
                    Y, refs = observe(Cn, B, rng); events += 9
                    raw.append(dict(kind='K_noise', case=c['case'], B=B, rep=rep, Y=Y, refs=refs))
                    Bhat = refs.mean(axis=0)
                    res = fit_T(Y, Bhat, model, 'F1', w)
                    detected = bool(res['T'] > thresholds[B])
                    D_est = res['theta'][0]
                    in_domain = bool(30<=D_est<=200 and 350<=res['theta'][1]<=550)
                    boundary = bool(abs(D_est-30)<1 or abs(D_est-200)<1)
                    reportable = bool(detected and res['converged'] and in_domain and not boundary)
                    rows_noise.append(dict(study='K_noise', case=c['case'], D_true=c['D_nm'], B=B, rep=rep,
                                           T=res['T'], detected=detected, converged=res['converged'],
                                           in_domain=in_domain, boundary=boundary,
                                           diameter_reportable=reportable,
                                           candidate_D=D_est if detected else None,
                                           reportable_D=D_est if reportable else None,
                                           err_D=(D_est-c['D_nm']) if reportable else None))
    # raw archive
    import h5py
    with h5py.File(os.path.join(OUT, 'validation', 'raw_camera_data.h5'), 'w') as h:
        for i, r in enumerate(raw):
            g = h.create_group(f'ev{i}')
            g.create_dataset('Y', data=r['Y']); g.create_dataset('refs', data=r['refs'])
            for k in ('kind','D','h','B','rep','case','idx'):
                if k in r: g.attrs[k] = r[k]
    # CSVs + threshold freeze
    json.dump(dict(schema='iscat127.threshold_freeze.1', rule='T > max(dev blank T) per B',
                   thresholds=thresholds, val_blank_fpr=fpr,
                   note='frozen before K-noise; 60-blank CP95 evaluated only'),
              open(os.path.join(OUT, 'config', 'threshold_freeze.json'), 'w'), indent=1)
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
