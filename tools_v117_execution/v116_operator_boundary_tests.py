# -*- coding: utf-8 -*-
"""v116: up to 12 additional production-boundary tests against the ACTUAL
tools/observation_operator.py (same entry points as production). If all pass,
the verdict is NO_PRODUCTION_PATCH_REQUIRED - no diffs are invented."""
import os, sys, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import observation_operator as oo

N, FS, K0S = oo.N, oo.DEFAULT_FS, oo.K0S
RESULTS = []

def case(tid, desc, fn):
    err = None
    ret = None
    try:
        ret = fn()
    except oo.OperatorError as ex:
        err = str(ex)
    except Exception as ex:  # noqa: BLE001 - leaks are failures
        err = 'LEAKED %s: %s' % (type(ex).__name__, ex)
    if err is not None:
        RESULTS.append({'id': tid, 'description': desc, 'pass': False,
                        'detail': ('BLOCKED/LEAKED: ' + err)[:200]})
    else:
        ok, detail = ret if ret is not None else (False, 'no result')
        RESULTS.append({'id': tid, 'description': desc, 'pass': bool(ok), 'detail': detail[:200]})

def sinc(x):
    return 1.0 if x == 0 else math.sin(x) / x

def main():
    grid = [0.002 + j / FS for j in range(N)]

    # T01/T02: one synchronized (P,Q) frame per node; stateful counter; exact count
    samples = []  # (t, value) for every node frame; all pixels read the SAME value
    def stateful_cb(t):
        val = 1.0 + len(samples) * 1e-6
        samples.append((t, val))
        return [[val, val, val], [val + 2.0, val + 2.0, val + 2.0]]
    nodes = 64
    T1 = 1e-4
    centers200 = grid[:200]
    r = oo.run_roi(stateful_cb, centers200, T1, spatial_weights=[[1/3]*3, [1/3]*3],
                   mode='intensity')
    expected_calls = 200 * nodes
    # group node frames into exposure windows per center and compare window means
    def t02():
        ok_sync = True
        for j, tc in enumerate(centers200):
            vals = [v for (t, v) in samples if abs(t - tc) <= T1 / 2 + 1e-15]
            if len(vals) != nodes:
                ok_sync = False
                break
            m0 = sum(vals) / len(vals)
            if abs(r['series'][j][0] - m0) > 1e-12:
                ok_sync = False
                break
        return (ok_sync, 'per-center window means match series rows')
    case('T01', 'run_roi callback count exactly N x nodes (stateful counter)',
         lambda: (len(samples) == expected_calls, 'calls=%d expected=%d'
                  % (len(samples), expected_calls)))
    case('T02', 'multi-pixel rows read the SAME synchronized frame (no per-pixel skew)',
         t02)

    # T03: scalar vs P=1,Q=1 strict equality
    sig = lambda t: 1.0 + 0.2 * math.cos(2 * math.pi * 160 * FS / N * t)
    def t03():
        r1 = oo.run_roi(lambda t: [[sig(t)]], grid, 1e-4, spatial_weights=[[1.0]],
                        mode='intensity', k0s=[160])
        r2 = oo.run_pipeline(sig, grid, 1e-4, mode='intensity', k0s=[160])
        s1 = list(r1['series'][:, 0]); s2 = list(r2['series'])
        d = max(abs(a - b) for a, b in zip(s1, s2))
        return (d < 5e-15 and len(s1) == len(s2),
                'max diff=%.3g over %d samples' % (d, len(s1)))
    case('T03', 'scalar pipeline vs P=1,Q=1 run_roi strict equality', t03)

    # T04: P=2,Q=3 no-mixing: pixel0 carries f1 only, pixel1 carries f2 only
    f1, f2 = 160 * FS / N, 320 * FS / N
    def nomix_cb(t):
        return [[1.0 + 0.3 * math.cos(2 * math.pi * f1 * t), 1.0, 1.0],
                [2.0 + 0.3 * math.cos(2 * math.pi * f2 * t), 2.0, 2.0]]
    def t04():
        r = oo.run_roi(nomix_cb, grid, 1e-4, spatial_weights=[[1/3]*3, [1/3]*3],
                       mode='intensity', k0s=[160, 320])
        C0_160 = r['dft'][160][1][0]
        C0_320 = r['dft'][320][1][0]
        C1_160 = r['dft'][160][1][1]
        C1_320 = r['dft'][320][1][1]
        # pixel0: all three sub-samples carry the 0.3 modulation at f1
        # pixel1: only sub-sample 1 carries 0.3 at f2 -> row-normalized amplitude 0.3/3
        B0 = (0.3 / 3.0) * sinc(math.pi * f1 * 1e-4)  # only sub-sample 1 carries 0.3
        B1 = (0.3 / 3.0) * sinc(math.pi * f2 * 1e-4)
        return (abs(abs(C0_160) - B0 / 1.0) < 1e-11 and abs(C0_320) < 1e-12
                and abs(C1_160) < 1e-12 and abs(abs(C1_320) - B1 / 2.0) < 1e-11,
                'pixel0: |C160|=%.4g |C320|=%.2g; pixel1: |C160|=%.2g |C320|=%.4g '
                '(no cross-pixel mixing; per-row sub-pixel amplitudes respected)'
                % (abs(C0_160), abs(C0_320), abs(C1_160), abs(C1_320)))
    case('T04', 'P=2,Q=3 independent pixels keep their own frequencies only', t04)

    # T05: P=1681 (41x41), Q=1 DIMENSION-ONLY fixture on a partial grid (no full solve)
    def t05():
        def cb1681(t):
            return [[1.0 + 0.01 * p] for p in range(1681)]
        r = oo.run_roi(cb1681, grid[:50], 1e-4,
                       spatial_weights=[[1.0] for _ in range(1681)], mode='intensity')
        return (r['series'].shape == (50, 1681),
                'partial-grid series shape=%r (dimension fixture; no full time-domain solve)'
                % (r['series'].shape,))
    case('T05', 'P=1681 shape accepted without expensive full solve (partial grid)', t05)

    # T06: electron scalar broadcast per pixel
    def t06():
        r = oo.run_roi(lambda t: [[1.0, 1.0], [2.0, 2.0]], grid[:50], 2e-4,
                       spatial_weights=[[0.5, 0.5], [0.5, 0.5]], mode='electron',
                       kappa_e_per_U_per_s=3.2)
        ok = (abs(r['series'][0][0] - 3.2 * 2e-4 * 1.0) < 1e-15
              and abs(r['series'][0][1] - 3.2 * 2e-4 * 2.0) < 1e-15)
        return (ok, 'e-row=%r' % (list(r['series'][0]),))
    case('T06', 'electron scalar kappa broadcast per pixel', t06)

    # T07: electron vector kappa per pixel
    def t07():
        r = oo.run_roi(lambda t: [[1.0, 1.0], [2.0, 2.0]], grid[:50], 2e-4,
                       spatial_weights=[[0.5, 0.5], [0.5, 0.5]], mode='electron',
                       kappa_e_per_U_per_s=[3.2, 6.4])
        ok = (abs(r['series'][0][0] - 3.2 * 2e-4 * 1.0) < 1e-15
              and abs(r['series'][0][1] - 6.4 * 2e-4 * 2.0) < 1e-15)
        return (ok, 'e-row=%r' % (list(r['series'][0]),))
    case('T07', 'electron vector kappa per pixel', t07)

    # T08: dn vector b and g per pixel
    def t08():
        r = oo.run_roi(lambda t: [[1.0, 1.0], [2.0, 2.0]], grid[:50], 2e-4,
                       spatial_weights=[[0.5, 0.5], [0.5, 0.5]], mode='dn',
                       kappa_e_per_U_per_s=[3.2, 6.4], g_DN_per_e=[2.5, 5.0],
                       offset_DN=[100.0, 200.0])
        ok = (abs(r['series'][0][0] - (100.0 + 2.5 * 3.2 * 2e-4 * 1.0)) < 1e-15
              and abs(r['series'][0][1] - (200.0 + 5.0 * 6.4 * 2e-4 * 2.0)) < 1e-15)
        return (ok, 'dn-row=%r' % (list(r['series'][0]),))
    case('T08', 'dn per-pixel b and g broadcast', t08)

    # T09: finite outputs; intensity mode does not demand gain
    def t09():
        r = oo.run_roi(lambda t: [[1.0, 2.0], [3.0, 4.0]], grid[:50], 1e-4,
                       spatial_weights=[[0.5, 0.5], [0.5, 0.5]], mode='intensity')
        finite_ok = bool(abs(r['series']).max() < 1e6)
        err = None
        try:
            oo.run_roi(lambda t: [[1.0], [1.0]], grid[:50], 1e-4,
                       mode='intensity', spatial_weights=[[1.0], [1.0]],
                       g_DN_per_e=2.5)
        except oo.OperatorError as ex:
            err = str(ex)
        return (finite_ok and err is None,
                'intensity mode runs without any gain/kappa demand; finite outputs'
                + ('' if err is None else '; gain ignored cleanly'))
    case('T09', 'intensity mode needs no gain; outputs finite', t09)

    # T10: T=0 count mode rejected
    def t10():
        err = None
        try:
            oo.run_roi(lambda t: [[1.0, 1.0]], grid[:50], 0.0, mode='electron',
                       spatial_weights=[[1.0]], kappa_e_per_U_per_s=1.0)
        except oo.OperatorError as ex:
            err = str(ex)
        return (err is not None and 'INVALID_EXPOSURE' in err,
                (err or 'NOT REJECTED')[:110])
    case('T10', 'T=0 rejected in count mode', t10)

    # T11: unified OperatorError with observable stage for static rejects (zero callbacks)
    # FIXED (v117): per-case real booleans with entry/error-type/callback counts;
    # aggregated over the actual boolean field (the v113-era unpack bug is gone).
    def t11():
        counter = [0]
        checks = []
        def cb(t):
            counter[0] += 1
            return [[1.0, 1.0], [2.0, 2.0]]
        for label, fn in (
                ('k0s_empty', lambda: oo.run_roi(cb, grid[:50], 1e-4,
                                                 spatial_weights=[[0.5, 0.5], [0.5, 0.5]],
                                                 mode='intensity', k0s=[])),
                ('duplicate_bin', lambda: oo.run_roi(cb, grid[:50], 1e-4,
                                                     spatial_weights=[[0.5, 0.5], [0.5, 0.5]],
                                                     mode='intensity', k0s=[160, 160])),
                ('nan_fs', lambda: oo.run_roi(cb, grid[:50], 1e-4, fs=float('nan'),
                                              spatial_weights=[[0.5, 0.5], [0.5, 0.5]],
                                              mode='intensity')),
                ('nan_tolerance', lambda: oo.run_roi(cb, grid[:50], 1e-4,
                                                     time_tolerance_s=float('nan'),
                                                     spatial_weights=[[0.5, 0.5], [0.5, 0.5]],
                                                     mode='intensity'))):
            before = counter[0]
            err = None
            etype = None
            try:
                fn()
            except oo.OperatorError as ex:
                err = str(ex)
                etype = 'OperatorError'
            except Exception as ex:  # noqa: BLE001 - leakage recorded, never accepted
                err = '%s' % ex
                etype = type(ex).__name__
            checks.append({'label': label, 'rejected': err is not None,
                           'error_type': etype, 'error': (err or '')[:90],
                           'callback_calls': counter[0] - before})
            counter[0] = 0
        all_rejected = all(c['rejected'] for c in checks)
        all_operator = all(c['error_type'] == 'OperatorError' for c in checks)
        zero_calls = all(c['callback_calls'] == 0 for c in checks)
        return (all_rejected and all_operator and zero_calls,
                json.dumps(checks))
    case('T11', 'static rejects unified OperatorError at zero callbacks', t11)

    # T12: fail-closed per-pixel in run_roi (forced corruption identified by pixel/bin)
    def t12():
        orig = oo.production_fft
        def broken(series, mean, k0s=None):
            res = dict(orig(series, mean, k0s))
            k = list(res)[0]
            X, C = res[k]
            res[k] = (X + 1.0, C + 1.0)  # corrupt the first requested pixel/bin
            return res
        oo.production_fft = broken
        try:
            oo.run_roi(lambda t: [[1.0, 1.0], [2.0, 2.0]], grid, 1e-4,
                       spatial_weights=[[0.5, 0.5], [0.5, 0.5]], mode='intensity',
                       k0s=[160, 320])
            return (False, 'corrupted per-pixel spectrum did NOT raise')
        except oo.OperatorError as ex:
            return (True, 'fail-closed raised: %s' % str(ex)[:110])
        finally:
            oo.production_fft = orig
    case('T12', 'run_roi per-pixel spectral gate failure fails closed', t12)

    # ---- bounded mutations: silent return / TypeError leak must be DETECTED ----
    def t11_checks_against(roi_impl):
        saved = oo.run_roi
        oo.run_roi = roi_impl
        try:
            counter = [0]
            res = []
            for label, fn in (
                    ('k0s_empty', lambda: oo.run_roi(
                        lambda t: (counter.__setitem__(0, counter[0] + 1) or [[1.0, 1.0], [2.0, 2.0]]),
                        grid[:50], 1e-4, spatial_weights=[[0.5, 0.5], [0.5, 0.5]],
                        mode='intensity', k0s=[])),
                    ('nan_fs', lambda: oo.run_roi(
                        lambda t: (counter.__setitem__(0, counter[0] + 1) or [[1.0, 1.0], [2.0, 2.0]]),
                        grid[:50], 1e-4, fs=float('nan'),
                        spatial_weights=[[0.5, 0.5], [0.5, 0.5]], mode='intensity'))):
                err = None
                etype = None
                try:
                    fn()
                except oo.OperatorError as ex:
                    err = str(ex)
                    etype = 'OperatorError'
                except Exception as ex:  # noqa: BLE001
                    err = str(ex)
                    etype = type(ex).__name__
                res.append({'label': label, 'rejected': err is not None,
                            'error_type': etype, 'callback_calls': counter[0]})
                counter[0] = 0
            return res
        finally:
            oo.run_roi = saved
    all_detected = True
    mut1 = t11_checks_against(lambda *a, **k: None)  # silent return mutation
    detected1 = not all(c['rejected'] for c in mut1)
    all_detected &= detected1
    RESULTS.append({'id': 'MUT_silent_return', 'description': 'silently-returning run_roi must be '
                    'caught by the T11 battery', 'pass': detected1,
                    'detail': json.dumps(mut1)[:160]})
    def leaky(*a, **k):
        raise TypeError('object of type float has no len()')
    mut2 = t11_checks_against(leaky)  # TypeError leak mutation
    detected2 = not all(c['rejected'] and c['error_type'] == 'OperatorError' for c in mut2)
    all_detected &= detected2
    RESULTS.append({'id': 'MUT_typeerror_leak', 'description': 'TypeError-leaking run_roi must be '
                    'caught by the T11 battery (not counted as compliant rejection)',
                    'pass': detected2, 'detail': json.dumps(mut2)[:160]})
    return RESULTS

if __name__ == '__main__':
    res = main()
    n_pass = sum(1 for r in res if r['pass'])
    out = sys.argv[1] if len(sys.argv) > 1 else 'v116_boundary_report.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({'tests': res, 'n_pass': n_pass, 'n_total': len(res),
                   'all_pass': n_pass == len(res),
                   'verdict': 'NO_PRODUCTION_PATCH_REQUIRED' if n_pass == len(res)
                              else 'PRODUCTION_PATCH_REQUIRED'}, f, indent=2)
    print('BOUNDARY %d/%d PASS' % (n_pass, len(res)))
    sys.exit(0 if n_pass == len(res) else 2)
