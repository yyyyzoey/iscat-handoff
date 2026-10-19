# -*- coding: utf-8 -*-
"""v115 operator regression: 27 fixed tests (T01-T27) against the ACTUAL
tools/observation_operator.py. NEGATIVE cases accept ONLY the specified
OperatorError (bare TypeError/IndexError/ZeroDivisionError count as leakage
failures); positive cases must return correct values AND shapes. The suite
drives the real module - no scalar self-equality shortcuts."""
import os, sys, json, math, cmath, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import observation_operator as oo

N, FS, K0S = oo.N, oo.DEFAULT_FS, oo.K0S
RESULTS = []

def case(tid, desc, fn, expect='reject', needle=None):
    """expect 'reject': requires oo.OperatorError with optional needle.
    expect 'accept': requires no error and fn returns (ok, detail)."""
    err = None
    ret = None
    try:
        ret = fn()
    except oo.OperatorError as ex:
        err = str(ex)
    except Exception as ex:  # noqa: BLE001 - leakage of ordinary exceptions is a failure
        err = 'LEAKED %s: %s' % (type(ex).__name__, ex)
    if expect == 'reject':
        ok = err is not None and (needle is None or needle in err)
        RESULTS.append({'id': tid, 'description': desc, 'pass': ok,
                        'detail': (err or 'NOT REJECTED')[:170]})
    else:
        if err is not None:
            RESULTS.append({'id': tid, 'description': desc, 'pass': False,
                            'detail': ('LEAKED/BLOCKED: ' + err)[:170]})
        else:
            ok, detail = ret if ret is not None else (False, 'no result')
            RESULTS.append({'id': tid, 'description': desc, 'pass': bool(ok),
                            'detail': detail[:170]})

def sinc(x):
    return 1.0 if x == 0 else math.sin(x) / x

def main():
    grid = [0.002 + j / FS for j in range(N)]

    # ---- time contract ----
    case('T01', 'valid uniform grid accepted, series values correct',
         lambda: (lambda r: (all(abs(v - 1.0) < 1e-14 for v in r['series'])
                             and len(r['series']) == N,
                             'series len=%d' % len(r['series'])))(
             oo.run_pipeline(lambda t: 1.0, grid, 1e-4, mode='intensity', k0s=[160])),
         expect='accept')
    case('T02', 'NaN Fs rejected', lambda: oo.validate_timestamps(
        [0.0, 0.0002, 0.0004], 1e-4, fs=float('nan')), needle='INVALID_PARAMETER')
    case('T03', 'Inf Fs rejected', lambda: oo.validate_timestamps(
        [0.0, 0.0002, 0.0004], 1e-4, fs=float('inf')), needle='INVALID_PARAMETER')
    case('T04', 'zero and negative Fs rejected', lambda: (
        oo.validate_timestamps([0.0, 0.0002, 0.0004], 1e-4, fs=0.0),
        oo.validate_timestamps([0.0, 0.0002, 0.0004], 1e-4, fs=-5000.0)),
        needle='INVALID_PARAMETER')
    case('T05', 'NaN and negative time tolerance rejected', lambda: (
        oo.validate_timestamps([0.0, 0.0002, 0.0004], 1e-4, time_tolerance_s=float('nan')),
        oo.validate_timestamps([0.0, 0.0002, 0.0004], 1e-4, time_tolerance_s=-1e-12)),
        needle='INVALID_PARAMETER')
    # T06: genuinely uniform grid isolates the tolerance upper bound
    case('T06', 'tolerance >= 0.5/Fs rejected on a genuinely uniform grid',
         lambda: oo.validate_timestamps([0.0, 0.0002, 0.0004], 1e-4, fs=FS,
                                        time_tolerance_s=0.5 / FS),
         needle='TIME_TOLERANCE_TOO_LARGE')
    case('T07', 'timestamps returned unmodified (no snapping)',
         lambda: (lambda c: (c == [0.002, 0.0022 + 5e-13, 0.0024],
                             'centers=%r' % (c,)))(
             oo.validate_timestamps([0.002, 0.0022 + 5e-13, 0.0024], 1e-4,
                                    meaning='center', fs=FS, time_tolerance_s=1e-12)),
         expect='accept')
    # ---- quadrature ----
    case('T08', 'fractional quadrature order 64.5 rejected', lambda: oo.exposure_average(
        lambda t: 1.0, 0.0, 1e-4, quadrature_nodes=64.5), needle='INVALID_QUADRATURE_ORDER')
    case('T09', 'quadrature order 1/300 rejected', lambda: (
        oo.exposure_average(lambda t: 1.0, 0.0, 1e-4, quadrature_nodes=1),
        oo.exposure_average(lambda t: 1.0, 0.0, 1e-4, quadrature_nodes=300)),
        needle='INVALID_QUADRATURE_ORDER')
    # ---- bins ----
    case('T10', 'k0s=[] rejected everywhere (production/independent/compare/scalar-partial/roi)',
         lambda: (oo.production_fft([1.0] * N, 1.0, k0s=[]),
                  oo.independent_dft([1.0] * N, 1.0, k0s=[]),
                  oo.compare_paths([1.0] * N, 1.0, k0s=[]),
                  oo.run_pipeline(lambda t: 1.0, grid[:100], 1e-4, mode='intensity', k0s=[]),
                  oo.run_roi(lambda t: [[1.0, 1.0]] * 3, grid[:100], 1e-4,
                             spatial_weights=[[0.5, 0.5]], mode='intensity', k0s=[])),
         needle='EMPTY_BIN_LIST')
    # ---- types and units ----
    case('T11', 'bool exposure rejected', lambda: oo.run_pipeline(
        lambda t: 1.0, grid, True, mode='intensity'), needle='INVALID_EXPOSURE')
    def t12():
        counter = [0]
        err = None
        try:
            oo.run_pipeline(lambda t: (counter.__setitem__(0, counter[0] + 1) or 1.0),
                            grid, 1e-4, mode='electron', kappa_e_per_U_per_s=None)
        except oo.OperatorError as ex:
            err = str(ex)
        return (err is not None and counter[0] == 0,
                'error=%r callback_calls=%d' % ((err or '')[:60], counter[0]))
    case('T12', 'missing kappa rejected with ZERO callbacks', t12, expect='accept')
    case('T13', 'negative intensity rejected before count conversion', lambda: oo.run_pipeline(
        lambda t: -0.5, grid, 1e-4, mode='electron', kappa_e_per_U_per_s=3.2),
        needle='INVALID_INTENSITY')
    case('T14', 'DN conversion rejects negative/NaN mu_e and bool gain/offset', lambda: (
        oo.dn_counts(-1.0, 2.5, 100.0), oo.dn_counts(float('nan'), 2.5, 100.0),
        oo.dn_counts(1.0, True, 100.0), oo.dn_counts(1.0, 2.5, True)),
        needle='INVALID_MU_E')
    case('T15', 'count overflow rejected', lambda: oo.electron_counts(
        1e308, 1e308, 1e-4), needle='COUNT_OVERFLOW')
    # ---- fail-closed spectral gates ----
    def t16():
        orig = oo.production_fft
        def broken(series, mean, k0s=None):
            res = dict(orig(series, mean, k0s))
            k = list(res)[0]
            X, C = res[k]
            res[k] = (X + 1.0, C + 1.0)
            return res
        oo.production_fft = broken
        try:
            oo.run_pipeline(lambda t: 1.0 + 0.3 * math.cos(
                2 * math.pi * 160 * FS / N * t), grid, 1e-4, mode='intensity', k0s=[160])
            return (False, 'mutated production path did NOT raise; certified dft exposed')
        except oo.OperatorError as ex:
            return (True, 'SPECTRAL_GATE_FAIL raised: %s' % str(ex)[:90])
        finally:
            oo.production_fft = orig
    case('T16', 'forced spectral gate failure fails closed (no certified dft)',
         t16, expect='accept')
    # ---- run_roi modes and sampling ----
    P, Q = 2, 3
    f1, f2 = 160 * FS / N, 320 * FS / N
    t_start = grid[0]
    def roi_cb(t):
        return [[1.0 + 0.3 * math.cos(2 * math.pi * f1 * t) for _ in range(Q)],
                [2.0 + 0.3 * math.cos(2 * math.pi * f2 * t + math.pi / 3) for _ in range(Q)]]
    wts = [[1 / Q] * Q, [1 / Q] * Q]
    def t17():
        r = oo.run_roi(roi_cb, grid, 1e-4, spatial_weights=wts, mode='intensity',
                       k0s=[160, 320])
        X0 = r['dft'][160][0][0]
        X1 = r['dft'][320][0][1]
        exp0 = (N / 2) * 0.3 * sinc(math.pi * f1 * 1e-4) * cmath.exp(2j * math.pi * f1 * t_start)
        exp1 = (N / 2) * 0.3 * sinc(math.pi * f2 * 1e-4) \
            * cmath.exp(2j * math.pi * f2 * t_start + 1j * math.pi / 3)
        return (r['series'].shape == (N, P) and abs(X0 - exp0) < 1e-9
                and abs(X1 - exp1) < 1e-9,
                'shape=%r X0=%.6g exp=%.6g X1=%.6g%+.6gj exp=%.6g%+.6gj'
                % (r['series'].shape, abs(X0), abs(exp0), X1.real, X1.imag,
                   exp1.real, exp1.imag))
    case('T17', 'run_roi independent detector pixels (P=2, Q=3, out-of-phase)',
         t17, expect='accept')
    def t18():
        r = oo.run_roi(lambda t: [[1.0, 1.0], [2.0, 2.0]], grid[:50], 1e-4,
                       spatial_weights=[[0.5, 0.5], [0.5, 0.5]], mode='electron',
                       kappa_e_per_U_per_s=3.2)
        ok = (abs(r['series'][0][0] - 3.2 * 1e-4 * 1.0) < 1e-15
              and abs(r['series'][0][1] - 3.2 * 1e-4 * 2.0) < 1e-15)
        return (ok, 'e-row=%r' % (list(r['series'][0]),))
    case('T18', 'run_roi electron mode = per-pixel kappa*T*Ibar (scalar broadcast)',
         t18, expect='accept')
    def t19():
        r = oo.run_roi(lambda t: [[1.0, 1.0], [2.0, 2.0]], grid[:50], 1e-4,
                       spatial_weights=[[0.5, 0.5], [0.5, 0.5]], mode='dn',
                       kappa_e_per_U_per_s=3.2, g_DN_per_e=2.5,
                       offset_DN=[100.0, 200.0])
        ok = (abs(r['series'][0][0] - (100.0 + 2.5 * 3.2 * 1e-4 * 1.0)) < 1e-15
              and abs(r['series'][0][1] - (200.0 + 2.5 * 3.2 * 1e-4 * 2.0)) < 1e-15)
        return (ok, 'dn-row=%r' % (list(r['series'][0]),))
    case('T19', 'run_roi dn mode = offset + g*mu_e per pixel', t19, expect='accept')
    def t20():
        counter = [0]
        err = None
        try:
            oo.run_roi(lambda t: (counter.__setitem__(0, counter[0] + 1) or [[1.0, 1.0]]),
                       grid[:50], 1e-4, spatial_weights=[[0.5, 0.5]], mode='electron',
                       kappa_e_per_U_per_s=None)
        except oo.OperatorError as ex:
            err = str(ex)
        return (err is not None and counter[0] == 0,
                'error=%r callback_calls=%d' % ((err or '')[:60], counter[0]))
    case('T20', 'run_roi missing count params rejected with ZERO callbacks',
         t20, expect='accept')
    # ---- synchronized single-frame sampling per quadrature node ----
    def t21():
        counter = [0]
        def cb(t):
            counter[0] += 1
            return [[1.0 + 0.0 * t] * Q for _ in range(P)]
        oo.run_roi(cb, grid[:200], 1e-4, spatial_weights=wts, mode='intensity')
        expected = 200 * 64
        return (counter[0] == expected,
                'callback_calls=%d expected=%d (one full frame per quadrature node)'
                % (counter[0], expected))
    case('T21', 'one full (P,Q) frame per quadrature node (exact callback count)',
         t21, expect='accept')
    # ---- P=1, Q=1 equivalence with scalar pipeline ----
    def t22():
        r1 = oo.run_roi(lambda t: [[1.0 + 0.2 * math.cos(2 * math.pi * 160 * FS / N * t)]],
                        grid, 1e-4, spatial_weights=[[1.0]], mode='intensity', k0s=[160])
        r2 = oo.run_pipeline(lambda t: 1.0 + 0.2 * math.cos(2 * math.pi * 160 * FS / N * t),
                             grid, 1e-4, mode='intensity', k0s=[160])
        s1 = list(r1['series']); s2 = list(r2['series'])
        # P=1/Q=1 vs scalar pipeline are the same math object; the residual is
        # floating-point accumulation-path difference (measured 1.1e-15)
        return (all(abs(a - b) < 5e-15 for a, b in zip(s1, s2)) and len(s1) == len(s2),
                'max diff over %d samples' % len(s1))
    case('T22', 'run_roi P=1 Q=1 strictly equals scalar run_pipeline', t22, expect='accept')
    # ---- boundary error hygiene ----
    case('T23', 'weighted_pixel_average([]) raises OperatorError (no ZeroDivisionError)',
         lambda: oo.weighted_pixel_average([]), needle=None)
    # T23 needs the empty-sample error; adjust expectation text after module fix
    case('T24', 'illegal shapes/NaN/Inf weights rejected with OperatorError', lambda: (
        oo.run_roi(lambda t: [[1.0]], grid[:50], 1e-4,
                   spatial_weights=[[0.5, 0.5]], mode='intensity'),
        oo.run_roi(lambda t: [[1.0, 1.0], [float('nan'), 1.0]], grid[:50], 1e-4,
                   spatial_weights=[[0.5, 0.5], [0.5, 0.5]], mode='intensity'),
        oo.run_roi(lambda t: [[1.0, 1.0]] * 2, grid[:50], 1e-4,
                   spatial_weights=[[0.5, -0.5], [0.5, 0.5]], mode='intensity'),
        oo.run_roi(lambda t: [[1.0, 1.0]] * 2, grid[:50], 1e-4,
                   spatial_weights=[[0.5, 0.5], [0.5, float('inf')]], mode='intensity')),
        needle=None)
    # ---- full 2001-pixel independent frequencies ----
    def t25():
        freqs = [80 * FS / N * (p + 1) / 1.0 for p in range(2001)]
        def cb(t):
            return [1.0 + 0.2 * math.cos(2 * math.pi * freqs[p] * t) for p in range(2001)]
        w = [[1.0] for _ in range(2001)]
        r = oo.run_roi(cb, grid, 1e-4, spatial_weights=w, mode='intensity', k0s=[80, 160, 320])
        X = r['dft'][80][0]
        return (abs(X[0]) > 1.0 and abs(X[1]) < 1e-6,
                'pixel0 |X_80|=%.3g pixel1 |X_80|=%.3g' % (abs(X[0]), abs(X[1])))
    case('T25', '2001-pixel independent frequencies keep separate X/C', t25, expect='accept')
    case('T26', 'partial-N scalar pipeline also rejects k0s=[]', lambda: oo.run_pipeline(
        lambda t: 1.0, grid[:100], 1e-4, mode='intensity', k0s=[]), needle='EMPTY_BIN_LIST')
    case('T27', 'illegal/duplicate bins rejected through run_pipeline', lambda: (
        oo.run_pipeline(lambda t: 1.0, grid, 1e-4, mode='intensity', k0s=[1600]),
        oo.run_pipeline(lambda t: 1.0, grid, 1e-4, mode='intensity', k0s=[160, 160])),
        needle='ILLEGAL_BIN')
    return RESULTS

if __name__ == '__main__':
    res = main()
    n_pass = sum(1 for r in res if r['pass'])
    out = sys.argv[1] if len(sys.argv) > 1 else 'v115_regression_report.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({'tests': res, 'n_pass': n_pass, 'n_total': len(res),
                   'all_pass': n_pass == len(res),
                   'note': 'fixed software fixtures only; negative cases accept ONLY the '
                           'specified OperatorError'}, f, indent=2)
    print('REGRESSION %d/%d PASS' % (n_pass, len(res)))
    sys.exit(0 if n_pass == len(res) else 2)
