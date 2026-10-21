"""V126 error separation (stage A2) on the H01-H06 DEV diagnostic set.

Truth enters ONLY this diagnostic script. Four error classes per case:
  FWD   : canonical_forward(theta_true) vs the direct L1 render (model/interp error)
  CLOSURE: same-model synthetic Y=F(theta_true) inverted from a common start
           (pure optimizer error; SAME_MODEL_CLOSURE, not physical validation)
  NUIS  : fit D only with true h/xy fixed; fit D/h with true xy fixed
  FULL  : all-unknown fit; loss at true params vs returned loss
"""
import csv, json, os
import numpy as np
from scipy.optimize import least_squares

import v126_forward_model as fm

OUT = r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff\results\v126'
DEV = [('H01', 37.0, 362.5, 56.0, -84.0), ('H02', 63.0, 387.5, -112.0, 28.0),
       ('H03', 93.0, 412.5, 84.0, 112.0), ('H04', 117.0, 462.5, -56.0, -112.0),
       ('H05', 147.0, 487.5, 112.0, -56.0), ('H06', 177.0, 537.5, -84.0, 84.0)]

def _fit(Cobs, model, cand, x0, fix=None, maxfev=400):
    """Bounded continuous fit; fix = dict of pinned params."""
    lo = [30.0, 350.0, -500.0, -500.0]
    hi = [200.0, 550.0, 500.0, 500.0]
    names = ['D', 'h', 'x', 'y']
    free = [k for k in names if fix is None or k not in fix]
    x0v = [float(x0[names.index(k)]) for k in free]
    blo = [lo[names.index(k)] for k in free]
    bhi = [hi[names.index(k)] for k in free]
    def resid(p):
        full = dict(zip(free, p))
        theta = [full.get('D', x0[0]), full.get('h', x0[1]), full.get('x', x0[2]), full.get('y', x0[3])]
        Cm = model.forward(cand, *theta)
        if Cm is None:
            return np.full(Cobs.size, 1e3)
        return (Cobs - Cm).ravel()
    r = least_squares(resid, x0v, bounds=(blo, bhi), max_nfev=maxfev, xtol=1e-10, ftol=1e-12)
    full = dict(zip(free, r.x.tolist()))
    theta = [full.get('D', x0[0]), full.get('h', x0[1]), full.get('x', x0[2]), full.get('y', x0[3])]
    return dict(theta=theta, cost=float(0.5 * np.sum(r.fun ** 2)),
                loss=float(np.linalg.norm(r.fun)), nfev=int(r.nfev),
                status=int(r.status), success=bool(r.status > 0))

def run(cand='I1', suffix=''):
    model = fm.CanonicalModel()
    import h5py
    ho = os.path.join(model.h.filename.replace('v125_Dh_train_fields.h5', 'v125_direct_holdouts.h5'))
    rows = []
    with h5py.File(ho, 'r') as h:
        for tag, D, hnm, x, y in DEV:
            g = h[tag]
            Cobs = g['at_offset/C'][()][2:15, 2:15]
            theta_true = [D, hnm, x, y]
            # FWD: forward at truth vs direct render
            Fw = model.forward(cand, *theta_true)
            fwd_err = float(np.linalg.norm(Fw - Cobs)) if Fw is not None else float('nan')
            # CLOSURE: Y = F(theta_true) from the same model
            Y = Fw
            closure = _fit(Y, model, cand, [60.0, 400.0, 0.0, 0.0]) if Y is not None else None
            clos_err = float(np.linalg.norm(np.array(closure['theta']) - theta_true)) if closure else float('nan')
            clos_loss = closure['loss'] if closure else float('nan')
            # NUIS1: fit D with true h/xy
            n1 = _fit(Cobs, model, cand, [60.0, hnm, x, y], fix={'h': True, 'x': True, 'y': True})
            # NUIS2: fit D/h with true xy
            n2 = _fit(Cobs, model, cand, [60.0, 400.0, x, y], fix={'x': True, 'y': True})
            # FULL
            full = _fit(Cobs, model, cand, [60.0, 400.0, 0.0, 0.0])
            # loss at true vs returned
            loss_true = float(np.linalg.norm(Cobs - Fw)) if Fw is not None else float('nan')
            rows.append(dict(case=tag, candidate=cand, D_true=D, h_true=hnm, x_true=x, y_true=y,
                             fwd_err_L2=fwd_err,
                             closure_D=closure['theta'][0] if closure else None,
                             closure_param_err=clos_err, closure_loss=clos_loss,
                             nuisD_D=n1['theta'][0], nuisD_err=n1['theta'][0] - D,
                             nuisDH_D=n2['theta'][0], nuisDH_h=n2['theta'][1],
                             nuisDH_errD=n2['theta'][0] - D,
                             full_D=full['theta'][0], full_h=full['theta'][1],
                             full_x=full['theta'][2], full_y=full['theta'][3],
                             full_errD=full['theta'][0] - D, full_errH=full['theta'][1] - hnm,
                             full_loss=full['loss'], loss_at_true=loss_true,
                             full_nfev=full['nfev'], full_success=full['success'],
                             optimizer_found_better=bool(full['loss'] < loss_true)))
    model.close()
    keys = sorted({k for r in rows for k in r})
    with open(os.path.join(OUT, 'diagnostics', 'error_separation' + suffix + '.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in rows: w.writerow(r)
    return rows

if __name__ == '__main__':
    for cand in ('I1', 'I2'):
        rows = run(cand)
        print(f'--- candidate {cand} ---')
        for r in rows:
            print(r['case'], 'fwd=%.5f' % r['fwd_err_L2'], 'clos_err=%.1f' % r['closure_param_err'],
                  'nuisD_err=%+.1f' % r['nuisD_err'], 'full_errD=%+.1f' % r['full_errD'],
                  'full_errH=%+.1f' % r['full_errH'], 'loss_true=%.2g full=%.2g' % (r['loss_at_true'], r['full_loss']))
