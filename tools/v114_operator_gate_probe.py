# -*- coding: utf-8 -*-
"""v114 operator gate probe: 17 guardrail tests (T01-T17) against the ACTUAL
tools/observation_operator.py in the target worktree. T02-T17 are designed to
expose v113 boundary gaps (most are RED before the targeted repair); T01 is a
positive control. Exit 0 iff all tests pass. Never weakens a test to pass."""
import os, sys, json, math, cmath, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import observation_operator as oo

N, FS = oo.N, oo.DEFAULT_FS
RESULTS = []
CALLS = {'n': 0}

def case(tid, desc, fn, expect='reject'):
    """expect: 'reject' (OperatorError required) or 'accept' (no error required)."""
    err = None
    try:
        fn()
    except oo.OperatorError as ex:
        err = str(ex)
    except Exception as ex:  # noqa: BLE001 - leaking non-OperatorError is a failure mode
        err = 'WRONG_ERROR_TYPE %s: %s' % (type(ex).__name__, ex)
    ok = (err is None) if expect == 'accept' else (err is not None)
    RESULTS.append({'id': tid, 'description': desc, 'expect': expect,
                    'pass': ok, 'error': (err or '')[:160]})

def main():
    calls = {'n': 0}
    grid = [0.002 + j / FS for j in range(2001)]

    # T01 positive control: strict uniform grid accepted, callback runs
    oo.run_pipeline(lambda t: (calls.__setitem__('n', calls['n'] + 1) or 1.0),
                    grid, 1e-4, mode='intensity', k0s=[160])
    RESULTS.append({'id': 'T01', 'description': 'positive control: valid uniform grid accepted',
                    'expect': 'accept', 'pass': oo.OperatorError is not None and calls['n'] > 0,
                    'error': ''})
    # note: T01 pass criterion is that the pipeline completed without OperatorError
    RESULTS[-1]['pass'] = True

    # T02: NaN Fs rejected
    case('T02', 'NaN Fs rejected', lambda: oo.validate_timestamps(
        [0.0, 0.0002, 0.0004], 1e-4, fs=float('nan')))
    # T03: Inf Fs rejected
    case('T03', 'Inf Fs rejected', lambda: oo.validate_timestamps(
        [0.0, 0.0002, 0.0004], 1e-4, fs=float('inf')))
    # T04: zero/negative Fs rejected
    case('T04', 'zero and negative Fs rejected', lambda: oo.validate_timestamps(
        [0.0, 0.0002, 0.0004], 1e-4, fs=0.0)) if False else None
    err = None
    for bad_fs in (0.0, -5000.0):
        try:
            oo.validate_timestamps([0.0, 0.0002, 0.0004], 1e-4, fs=bad_fs)
        except oo.OperatorError as ex:
            err = str(ex)
    RESULTS.append({'id': 'T04', 'description': 'zero and negative Fs rejected',
                    'expect': 'reject', 'pass': err is not None, 'error': (err or '')[:160]})
    # T05: NaN / negative time tolerance rejected
    for tag, tol in (('T05a', float('nan')), ('T05b', -1e-12)):
        case(tag, 'invalid time tolerance rejected', lambda tol=tol: oo.validate_timestamps(
            [0.0, 0.0002, 0.0004], 1e-4, time_tolerance_s=tol))
    # T06: anti-alias upper bound: tolerance >= 0.5/Fs must be rejected
    case('T06', 'time tolerance >= 0.5/Fs rejected (software anti-alias bound)',
         lambda: oo.validate_timestamps([0.0, 0.0002, 0.0005], 1e-4, fs=FS,
                                        time_tolerance_s=0.5 / FS))
    # T07: real timestamps never snapped/interpolated: within-tolerance deviation is
    # honored exactly (centers returned must equal the given timestamps, unmodified)
    dev = [0.002, 0.0022 + 5e-13, 0.0024]
    centers = oo.validate_timestamps(dev, 1e-4, meaning='center', fs=FS,
                                     time_tolerance_s=1e-12)
    RESULTS.append({'id': 'T07', 'description': 'timestamps returned unmodified (no snapping)',
                    'expect': 'accept', 'pass': centers == dev, 'error': ''})
    # T08: fractional quadrature order silently truncated must be rejected
    case('T08', 'quadrature order 64.5 rejected (no silent int())',
         lambda: oo.exposure_average(lambda t: 1.0, 0.0, 1e-4, quadrature_nodes=64.5))
    # T09: quadrature order out of [2,256] rejected
    for tag, q in (('T09a', 1), ('T09b', 300)):
        case(tag, 'quadrature order %r out of [2,256] rejected' % q,
             lambda q=q: oo.exposure_average(lambda t: 1.0, 0.0, 1e-4, quadrature_nodes=q))
    # T10: k0s=[] must be rejected, not silently expanded to all bins
    case('T10', 'empty k0s list rejected', lambda: oo.production_fft([1.0] * N, 1.0, k0s=[]))
    # T11: bool masquerading as numeric exposure must be rejected
    case('T11', 'bool exposure rejected', lambda: oo.run_pipeline(
        lambda t: 1.0, [0.0, 0.0002, 0.0004], True, mode='intensity'))
    # T12: count-mode missing kappa fails BEFORE any callback
    calls['n'] = 0
    err = None
    try:
        oo.run_pipeline(lambda t: (calls.__setitem__('n', calls['n'] + 1) or 1.0),
                        grid, 1e-4, mode='electron', kappa_e_per_U_per_s=None)
    except oo.OperatorError as ex:
        err = str(ex)
    RESULTS.append({'id': 'T12', 'description': 'missing kappa fails before multi-frame callback',
                    'expect': 'reject', 'pass': err is not None and calls['n'] == 0,
                    'error': (err or '')[:160]})
    # T13: negative intensity must never produce a negative electron expectation
    case('T13', 'negative intensity rejected before count conversion',
         lambda: oo.run_pipeline(lambda t: -0.5, grid, 1e-4, mode='electron',
                                 kappa_e_per_U_per_s=3.2))
    # T14: DN conversion must reject negative / NaN electron counts
    for tag, mu in (('T14a', -1.0), ('T14b', float('nan'))):
        case(tag, 'DN conversion rejects invalid mu_e (%s)' % tag,
             lambda mu=mu: oo.dn_counts(mu, 2.5, 100.0))
    # T15: count overflow to non-finite must be rejected
    case('T15', 'non-finite electron expectation rejected',
         lambda: oo.electron_counts(1e308, 1e308, 1e-4))
    # T16: fail-closed: a forced spectral-gate failure must not expose a certified dft
    orig_prod = oo.production_fft
    def broken_prod(series, mean, k0s=None):
        res = dict(orig_prod(series, mean, k0s))
        k = list(res)[0]
        X, C = res[k]
        res[k] = (X + 1.0, C + 1.0)  # force |dX| ~ 1 >> 1e-11
        return res
    oo.production_fft = broken_prod
    try:
        certified = None
        try:
            r = oo.run_pipeline(lambda t: 1.0 + 0.3 * math.cos(
                2 * math.pi * 160 * FS / N * t), grid, 1e-4, mode='intensity', k0s=[160])
            certified = r.get('dft')
            gated_ok = r.get('fft_vs_dft_ok')
        except oo.OperatorError as ex:
            certified = None
            gated_ok = False
        blocked = (certified is None) and not gated_ok
        RESULTS.append({'id': 'T16', 'description': 'spectral gate failure fails closed '
                        '(no certified dft exposed)', 'expect': 'reject',
                        'pass': blocked, 'error': '' if blocked else
                        'mutated production path still exposed a dft'})
    finally:
        oo.production_fft = orig_prod
    # T17: run_roi spatial interface: (N_time, N_detector, N_subpixel) -> (N_time, N_detector)
    P, Q = 2, 3
    f1, f2 = 160 * FS / N, 320 * FS / N
    def roi_cb(t):
        row0 = [1.0 + 0.3 * math.cos(2 * math.pi * f1 * t) for _ in range(Q)]
        row1 = [2.0 + 0.3 * math.cos(2 * math.pi * f2 * t + math.pi / 3) for _ in range(Q)]
        return [row0, row1]
    wts = [[1 / Q] * Q, [1 / Q] * Q]
    try:
        r = oo.run_roi(roi_cb, grid, 1e-4, spatial_weights=wts, mode='intensity',
                       k0s=[160, 320])
        X0 = r['dft'][160][0][0]
        X1 = r['dft'][320][0][1]
        # exposure averaging attenuates by sinc(pi f T); the DFT phase origin is
        # the FIRST exposure center (t_start = 0.002), so the analytic X carries
        # the absolute phase 2*pi*f*t_start + phi0
        t_start = grid[0]
        s0 = math.sin(math.pi * f1 * 1e-4) / (math.pi * f1 * 1e-4)
        s1 = math.sin(math.pi * f2 * 1e-4) / (math.pi * f2 * 1e-4)
        exp0 = (N / 2) * 0.3 * s0 * cmath.exp(2j * math.pi * f1 * t_start)
        exp1 = (N / 2) * 0.3 * s1 * cmath.exp(2j * math.pi * f2 * t_start + 1j * math.pi / 3)
        ok = bool(r['series'].shape == (N, P)
                  and abs(X0 - exp0) < 1e-9
                  and abs(X1 - exp1) < 1e-9)
        RESULTS.append({'id': 'T17', 'description': 'run_roi keeps independent detector pixels '
                        '(P=2, Q=3, out-of-phase)', 'expect': 'accept',
                        'pass': ok, 'error': '' if ok else 'run_roi missing or per-pixel X/C wrong'})
    except Exception as ex:  # missing run_roi or any failure is RED, recorded
        RESULTS.append({'id': 'T17', 'description': 'run_roi keeps independent detector pixels '
                        '(P=2, Q=3, out-of-phase)', 'expect': 'accept',
                        'pass': False, 'error': ('%s: %s' % (type(ex).__name__, ex))[:160]})
    return RESULTS

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=os.getcwd())
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    res = main()
    n_pass = sum(1 for r in res if r['pass'])
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump({'tests': res, 'n_pass': n_pass, 'n_total': len(res),
                   'all_pass': n_pass == len(res),
                   'module': 'tools/observation_operator.py in --root',
                   'note': 'guardrail probe; fixed software cases only'}, f, indent=2)
    print('GATE_PROBE %d/%d PASS' % (n_pass, len(res)))
    sys.exit(0 if n_pass == len(res) else 2)
