# -*- coding: utf-8 -*-
"""v089 Phase B: 8 math/software fixtures, ALL executed through the real
estimator functions (no hardcoded throws). Gates: amplitude/phase recovery
abs error < 1e-11 (analytic software fixture gate); complex DFT closure
rel < 1e-10 (abs < 1e-12 when |X| <= 1e-12 -> NEAR_ZERO_ABSOLUTE_ONLY)."""
import os, sys, csv, json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v089_estimators import (demodulate, fit_joint, component_decomposition,
                             norm_inner_prod, EstimatorError)

FS = 5000.0
results = []


def rec(fid, desc, ok, observed):
    results.append({'fixture_id': fid, 'description': desc, 'status': 'PASS' if ok else 'FAIL',
                    'observed': observed})


def main():
    # F1: known pure 400 Hz with arbitrary phase - recovery through fit AND demod
    j = np.arange(1000, 2001)
    phi = 0.7
    s = 1.0 + 0.05 * np.cos(2 * np.pi * 400.0 * j / FS + phi)
    fit = fit_joint(s, j, [200.0, 400.0, 420.0])
    A = fit['A_f'][400.0]
    A_true = 0.05 * np.exp(1j * phi)
    err = abs(A - A_true)
    rec('F1', 'pure 400 Hz arbitrary phase: joint-fit amplitude/phase recovery',
        err < 1e-11, '|A_fit - A_true|=%.3g (gate 1e-11)' % err)
    # F2: known mixture + linear trend, trend model recovers amplitudes
    s2 = (1.0 + 0.03 * np.cos(2 * np.pi * 200.0 * j / FS + 0.3)
          + 0.05 * np.cos(2 * np.pi * 400.0 * j / FS - 1.1)
          + 0.02 * np.cos(2 * np.pi * 420.0 * j / FS + 2.0)
          + 0.01 * (j - j.mean()) / 500.0)
    fit2 = fit_joint(s2, j, [200.0, 400.0, 420.0], trend=True)
    errs = [abs(fit2['A_f'][400.0] - 0.05 * np.exp(-1j * 1.1)),
            abs(fit2['A_f'][200.0] - 0.03 * np.exp(1j * 0.3)),
            abs(fit2['A_f'][420.0] - 0.02 * np.exp(1j * 2.0))]
    rec('F2', 'mixture 200/400/420 + linear trend: recovery with trend column',
        max(errs) < 1e-11, 'max |A_err|=%.3g over 3 freqs' % max(errs))
    # F3: clock-reset negative - non-integer-period start 1003; per-window reset
    # clock differs from global origin -> must be DETECTED (not silently equal)
    j2 = np.arange(1003, 2003)   # fixed non-integer-period synthetic start
    s3 = 1.0 + 0.05 * np.cos(2 * np.pi * 400.0 * j2 / FS + phi)
    _, X_global, _ = demodulate(s3, 400.0, j2)
    _, X_reset, _ = demodulate(s3, 400.0, j2 - j2[0])   # WRONG: reset clock
    d = abs(X_global - X_reset)
    rec('F3', 'clock-reset negative (window start 1003): reset clock must differ from global',
        d > 1e-6, '|X_global - X_reset|=%.3g > 1e-6 detected' % d)
    # F4: off-model component + complex residual closure
    s4 = 1.0 + 0.05 * np.cos(2 * np.pi * 400.0 * j / FS) + 0.02 * np.cos(2 * np.pi * 300.0 * j / FS + 0.5)
    fit4 = fit_joint(s4, j, [200.0, 400.0, 420.0])
    dec = component_decomposition(s4, j, [200.0, 400.0, 420.0], fit4)
    clo_ok = all(dec[f]['closure_ok'] for f in dec)
    rec('F4', 'off-model 300 Hz component: complex closure X_obs=X_model+X_res holds; off-mode in residual',
        clo_ok, 'closure modes: %s' % {f: dec[f]['closure_mode'] for f in dec})
    # F5: normalized inner product invariance to global phase and gain
    rng = np.random.default_rng(7)
    C1 = rng.normal(size=41) + 1j * rng.normal(size=41)
    C2 = rng.normal(size=41) + 1j * rng.normal(size=41)
    r0 = norm_inner_prod(C1, C2, np.ones(41, dtype=bool))
    g = 3.0; ph = np.exp(1j * 1.234)
    r1 = norm_inner_prod(C1 * g * ph, C2 * g * ph, np.ones(41, dtype=bool))
    rec('F5', 'normalized inner product invariant to common gain and global phase',
        abs(r0 - r1) < 1e-12, '|r0-r1|=%.3g (r0=%.6f)' % (abs(r0 - r1), r0))
    # F6: NaN input rejected
    s6 = s.copy(); s6[10] = np.nan
    try:
        demodulate(s6, 400.0, j)
        rec('F6', 'NaN input rejected', False, 'accepted (guard gap)')
    except EstimatorError as exc:
        rec('F6', 'NaN input rejected', True, 'EstimatorError: %s' % exc)
    # F7: degenerate time axis rejected
    try:
        fit_joint(s, np.ones(1001), [200.0, 400.0, 420.0])
        rec('F7', 'degenerate (constant) time axis rejected', False, 'accepted (guard gap)')
    except EstimatorError as exc:
        rec('F7', 'degenerate (constant) time axis rejected', True, 'EstimatorError: %s' % exc)
    # F8: zero-norm relative quantity undefined
    Z = np.zeros(41, dtype=np.complex128)
    r = norm_inner_prod(Z, C1, np.ones(41, dtype=bool))
    rec('F8', 'zero-norm relative quantity -> UNDEFINED_ZERO_NORM',
        r is None, 'returned %r' % r)

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'analysis',
                           'v089_fixed_fixture_results8.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['fixture_id', 'description', 'status', 'observed'],
                           lineterminator='\n'); w.writeheader(); w.writerows(results)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tables',
                           'v089_fixed_fixture_results8.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['fixture_id', 'description', 'status', 'observed'],
                           lineterminator='\n'); w.writeheader(); w.writerows(results)
    all_pass = all(r['status'] == 'PASS' for r in results)
    print('[B] summary:', json.dumps({'fixtures': len(results), 'all_pass': bool(all_pass)}))
    if not all_pass:
        sys.exit(2)


if __name__ == '__main__':
    main()
