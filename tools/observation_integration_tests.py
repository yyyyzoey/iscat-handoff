# -*- coding: utf-8 -*-
"""v112: 12 fixed integration test groups for the executable observation operator.
Every group drives the actual importable tools/observation_operator.py module
(positive AND negative cases where applicable). These are fixed software
fixtures - not new physical states, camera captures, or bank exposure scans."""
import os, sys, json, math, cmath
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import observation_operator as oo

N, K0S, FS = oo.N, oo.K0S, oo.DEFAULT_FS
eps64 = sys.float_info.epsilon

def sinc(x):
    return 1.0 if x == 0 else math.sin(x) / x

def run_group(name, cases):
    ok = all(c['pass'] for c in cases)
    return {'group': name, 'pass': ok, 'cases': cases}

def main():
    results = []
    GATE = 1e-11

    # ---- Group 1: timestamp grid acceptance/rejection BEFORE intensity callback ----
    calls = {'n': 0}
    def cb_guard(t):
        calls['n'] += 1
        return 1.0
    cases = []
    for label, ts, should_pass in (
            ('normal_5000Hz_grid', [0.0, 0.0002, 0.0004], True),
            ('duplicates', [0.0, 0.0, 0.0], False),
            ('reversed', [0.0004, 0.0002, 0.0], False),
            ('non_uniform', [0.0, 0.0002, 0.0005], False),
            ('fs_mismatch', [0.0, 0.0004, 0.0008], False)):
        err = None
        try:
            oo.validate_timestamps(ts, exposure_s=1e-4, meaning='center', fs=FS)
            accepted = True
        except oo.OperatorError as ex:
            accepted = False
            err = str(ex)
        cases.append({'case': label, 'pass': accepted == should_pass,
                      'detail': 'accepted=%s err=%s' % (accepted, (err or '')[:80])})
    # rejection must happen before the intensity callback is invoked
    err = None
    try:
        oo.run_pipeline(cb_guard, [0.0, 0.0, 0.0], 1e-4, mode='intensity')
    except oo.OperatorError as ex:
        err = str(ex)
    cases.append({'case': 'reject_before_callback', 'pass': calls['n'] == 0 and err is not None,
                  'detail': 'callback invocations=%d (must be 0)' % calls['n']})
    results.append(run_group('G1_timestamp_grid', cases))

    # ---- Group 2: constant intensity invariant under two explicit exposure windows ----
    cases = []
    f2 = lambda t: 2.5
    a1 = oo.exposure_average(f2, 0.001, 1e-4)
    a2 = oo.exposure_average(f2, 0.001, 3e-4)
    cases.append({'case': 'two_windows_constant', 'pass': abs(a1 - 2.5) < GATE and abs(a2 - 2.5) < GATE,
                  'detail': 'Ibar(T=1e-4)=%.17g Ibar(T=3e-4)=%.17g' % (a1, a2)})
    results.append(run_group('G2_constant_intensity', cases))

    # ---- Group 3: same physical window via start vs center convention ----
    cases = []
    f3 = lambda t: 1.0 + 0.5 * math.cos(2 * math.pi * 50.0 * t)
    c3 = [0.001, 0.0012]
    T3 = 2e-4
    r_center = oo.run_pipeline(f3, c3, T3, mode='intensity', time_meaning='center')
    r_start = oo.run_pipeline(f3, [t - T3 / 2 for t in c3], T3, mode='intensity', time_meaning='start')
    dmax = max(abs(x - y) for x, y in zip(r_center['series'], r_start['series']))
    cases.append({'case': 'start_center_same_window', 'pass': r_center['centers'] == r_start['centers']
                  and dmax < 1e-12,
                  'detail': 'identical centers %s; max series diff %.3g' % (r_center['centers'], dmax)})
    results.append(run_group('G3_time_origin_equivalence', cases))

    # ---- Group 4: three original bins, analytic amplitude AND phase ----
    cases = []
    A, B, T4 = 2.0, 0.4, 1e-4
    t_first = 0.05
    for k0 in K0S:
        f_hz = k0 * FS / N
        phi = 0.7
        cb = lambda t, f=f_hz: A + B * math.cos(2 * math.pi * f * (t - t_first) + phi)
        r = oo.run_pipeline(cb, [t_first + j / FS for j in range(N)], T4,
                            mode='intensity', time_meaning='center', k0s=[k0])
        X, C = r['dft'][k0]
        B_eff = B * sinc(math.pi * f_hz * T4)
        X_exp = (N / 2) * B_eff * complex(math.cos(phi), math.sin(phi))
        C_exp = 2 * X_exp / (N * A)
        # X accumulates rounding over 2001 quadrature windows (~1e-10); the
        # normalization identity C = 2X/(N*mean) stays at ~1e-14
        ok = abs(X - X_exp) < 1e-9 and abs(C - C_exp) < GATE
        cases.append({'case': 'bin%d_analytic' % k0, 'pass': ok,
                      'detail': 'f=%.9fHz |X|=%.12g/%.12g argX=%.12g/%.12g'
                                % (f_hz, abs(X), abs(X_exp),
                                   math.atan2(X.imag, X.real), math.atan2(X_exp.imag, X_exp.real))})
    results.append(run_group('G4_analytic_bins', cases))

    # ---- Group 5: intensity average vs field-average-squared; complex callback rejected ----
    cases = []
    E0, e5 = 1.0, 0.5
    field = lambda t: complex(E0, 0.0) * (1 + e5 * math.cos(2 * math.pi * 400.0 * t))
    n5 = 40001
    ts5 = [0.001 - 1e-4 / 2 + 1e-4 * i / (n5 - 1) for i in range(n5)]
    int_avg = sum(abs(field(t)) ** 2 for t in ts5) / n5
    fld_avg = abs(sum(field(t) for t in ts5) / n5) ** 2
    cases.append({'case': 'not_equal', 'pass': abs(int_avg - fld_avg) > 1e-6,
                  'detail': '<|E|^2>=%.12g vs |<E>|^2=%.12g' % (int_avg, fld_avg)})
    rejected = False
    try:
        oo.run_pipeline(field, [0.0, 0.0002, 0.0004], 1e-4, mode='intensity')
    except oo.OperatorError as ex:
        rejected = 'COMPLEX_FIELD_CALLBACK' in str(ex)
    cases.append({'case': 'complex_callback_rejected', 'pass': rejected,
                  'detail': 'complex field callback refused as intensity input'})
    results.append(run_group('G5_intensity_vs_field', cases))

    # ---- Group 6: zero exposure limits ----
    cases = []
    inst = oo.exposure_average(f2, 0.001, 0.0, instantaneous_limit=True)
    cases.append({'case': 'instantaneous_limit_mode', 'pass': abs(inst - 2.5) < GATE,
                  'detail': 'T=0 in instantaneous_limit mode returns the instantaneous value'})
    rej = False
    try:
        oo.run_pipeline(f2, [0.0, 0.0002, 0.0004], 0.0, mode='intensity')
    except oo.OperatorError:
        rej = True
    cases.append({'case': 'T0_default_rejected', 'pass': rej,
                  'detail': 'T=0 without instantaneous_limit mode is rejected (not a camera default)'})
    rej6 = False
    try:
        oo.run_pipeline(f2, [0.0, 0.0002, 0.0004], 0.0, mode='electron', kappa_e_per_U_per_s=1.0)
    except oo.OperatorError as ex:
        rej6 = 'INVALID_EXPOSURE' in str(ex)
    cases.append({'case': 'count_mode_zero_exposure_rejected', 'pass': rej6,
                  'detail': 'electron-count mode refuses zero exposure'})
    results.append(run_group('G6_zero_exposure', cases))

    # ---- Group 7: exposure linear scaling at fixed kappa; electron/DN/offset ----
    cases = []
    kappa = 3.2
    I7 = 1.7
    f7 = lambda t: I7
    mu1 = oo.electron_counts(oo.exposure_average(f7, 0.0, 1e-4), kappa, 1e-4)
    mu2 = oo.electron_counts(oo.exposure_average(f7, 0.0, 2e-4), kappa, 2e-4)
    cases.append({'case': 'mu_e_linear_in_T', 'pass': abs(mu2 - 2 * mu1) < GATE and abs(mu1 - kappa * I7 * 1e-4) < GATE,
                  'detail': 'mu_e(1e-4)=%.12g mu_e(2e-4)=%.12g ratio=%.12g' % (mu1, mu2, mu2 / mu1)})
    g, off = 2.5, 100.0
    dn1 = oo.dn_counts(mu1, g, off)
    dn2 = oo.dn_counts(mu2, g, off)
    cases.append({'case': 'DN_offset_separate', 'pass': abs(dn1 - (off + g * mu1)) < GATE
                  and abs(dn2 - (off + g * mu2)) < GATE and abs((dn2 - off) - 2 * (dn1 - off)) < GATE,
                  'detail': 'mu_DN = offset + g*mu_e; offset stays fixed while counts scale linearly'})
    results.append(run_group('G7_units_scaling', cases))

    # ---- Group 8: real interface rejections ----
    cases = []
    rejections = {
        'missing_exposure': lambda: oo.validate_timestamps([0.0, 0.0002, 0.0004], None),
        'negative_exposure': lambda: oo.run_pipeline(f2, [0.0, 0.0002, 0.0004], -1e-4, mode='intensity'),
        'inf_exposure': lambda: oo.run_pipeline(f2, [0.0, 0.0002, 0.0004], float('inf'), mode='intensity'),
        'illegal_bin': lambda: oo.complex_dft([1.0] * N, 1.0, k0s=[1600]),
        'missing_kappa': lambda: oo.run_pipeline(f2, [0.0, 0.0002, 0.0004], 1e-4,
                                                 mode='electron', kappa_e_per_U_per_s=None),
        'missing_gain': lambda: oo.dn_counts(1.0, None, 0.0),
    }
    for label, fn in rejections.items():
        err = None
        try:
            fn()
        except oo.OperatorError as ex:
            err = str(ex)
        except (TypeError, ValueError) as ex:
            err = 'TypeError:%s' % ex
        cases.append({'case': label, 'pass': err is not None,
                      'detail': (err or 'NOT REJECTED')[:100]})
    results.append(run_group('G8_interface_rejections', cases))

    # ---- Group 9: explicit pixel weights connected to the same exposure/DFT entry ----
    cases = []
    def pix_cb(t):
        return [1.0 + 0.1 * math.cos(2 * math.pi * 160 * FS / N * t),
                2.0 + 0.1 * math.cos(2 * math.pi * 160 * FS / N * t),
                3.0 + 0.1 * math.cos(2 * math.pi * 160 * FS / N * t)]
    wts = [1.0, 1.0, 2.0]
    r9 = oo.run_pipeline(pix_cb, [0.05 + j / FS for j in range(N)], 1e-4,
                         mode='intensity', pixel_weights=wts, k0s=[160])
    f9 = 160 * FS / N
    manual_first = sum(w * oo.exposure_average(lambda t, p=p: p[0] + p[1] * math.cos(2 * math.pi * f9 * t),
                                               0.05, 1e-4)
                       for w, p in zip(wts, [(1.0, 0.1), (2.0, 0.1), (3.0, 0.1)])) / sum(wts)
    cases.append({'case': 'weighted_pixel_average', 'pass': abs(r9['series'][0] - manual_first) < 1e-9,
                  'detail': 'exposure-averaged series[0]=%.17g manual=%.17g'
                            % (r9['series'][0], manual_first)})
    X9, C9 = r9['dft'][160]
    mean9 = r9['mean']
    B9 = 0.1 * sinc(math.pi * f9 * 1e-4)  # each pixel carries the same 0.1 modulation
    cases.append({'case': 'same_dft_entry', 'pass': abs(abs(C9) - B9 / mean9) < GATE,
                  'detail': '|C|=%.12g expected B_w_eff/mean=%.12g (mean=%.12g)'
                            % (abs(C9), B9 / mean9, mean9)})
    results.append(run_group('G9_pixel_weights', cases))

    # ---- Group 10: exact 400 Hz off-bin; FFT vs independent DFT; leakage retained ----
    cases = []
    A10, B10 = 2.0, 0.4
    cb10 = lambda t: A10 + B10 * math.cos(2 * math.pi * 400.0 * t)
    r10 = oo.run_pipeline(cb10, [0.05 + j / FS for j in range(N)], 1e-12, mode='intensity',
                          instantaneous_limit=False) if False else None
    # use true instantaneous series: T -> ~0 via tiny exposure is NOT the same as
    # instantaneous; use instantaneous_limit pipeline for a pure instantaneous series
    r10 = oo.run_pipeline(cb10, [0.05 + j / FS for j in range(N)], None, mode='intensity',
                          instantaneous_limit=True)
    s10 = r10['series']
    dft10 = oo.complex_dft(s10, r10['mean'], k0s=[160])
    X_mod, C_mod = dft10[160]
    mean10 = sum(s10) / N
    e10 = [cmath.exp(-2j * math.pi * 160 * j / N) for j in range(N)]
    X_direct = complex(sum((s10[j] - mean10) * e10[j] for j in range(N)))
    ok10 = abs(X_mod - X_direct) < 1e-9 and abs(X_mod) > 0  # leakage: |X| nonzero at 160 despite 400 Hz
    cases.append({'case': 'fft_vs_independent_dft', 'pass': ok10,
                  'detail': 'X_module=%.12g%+.12gj X_direct=%.12g%+.12gj (leakage retained)'
                            % (X_mod.real, X_mod.imag, X_direct.real, X_direct.imag)})
    f_fft = 400.0
    f_bin = 160 * FS / N
    cases.append({'case': 'off_bin_leakage_magnitude', 'pass': abs(abs(C_mod)) > 1e-6,
                  'detail': '|C_160|=%.12g at f=%.1fHz vs bin %.9fHz (finite-window leakage)'
                            % (abs(C_mod), f_fft, f_bin)})
    results.append(run_group('G10_offbin_400Hz', cases))

    # ---- Group 11: relative complex phase consistency under joint shift ----
    cases = []
    f11 = 160 * FS / N
    cb11 = lambda t: A10 + B10 * math.cos(2 * math.pi * f11 * t)
    r_a = oo.run_pipeline(cb11, [0.05 + j / FS for j in range(N)], None, mode='intensity',
                          instantaneous_limit=True, k0s=[160])
    delta = 3.0 / FS
    cb11b = lambda t: A10 + B10 * math.cos(2 * math.pi * f11 * (t - delta))
    r_b = oo.run_pipeline(cb11b, [0.05 + delta + j / FS for j in range(N)], None, mode='intensity',
                          instantaneous_limit=True, k0s=[160])
    Xa = r_a['dft'][160][0]
    Xb = r_b['dft'][160][0]
    cases.append({'case': 'joint_shift_phase_invariant', 'pass': abs(Xa - Xb) < 1e-9,
                  'detail': 'shifting signal and time coordinates together leaves the sampled series '
                            '(and X) invariant: dX=%.3g' % abs(Xa - Xb)})
    results.append(run_group('G11_relative_phase', cases))

    # ---- Group 12: gain/offset effect on normalized C; 32/64-node quadrature consistency ----
    cases = []
    g12 = 2.0
    cb12 = lambda t: A10 + B10 * math.cos(2 * math.pi * f11 * t)
    r_ref = oo.run_pipeline(cb12, [0.05 + j / FS for j in range(N)], None, mode='intensity',
                            instantaneous_limit=True, k0s=[160])
    r_gain = oo.run_pipeline(lambda t: g12 * cb12(t), [0.05 + j / FS for j in range(N)], None,
                             mode='intensity', instantaneous_limit=True, k0s=[160])
    C_ref = r_ref['dft'][160][1]
    C_gain = r_gain['dft'][160][1]
    cases.append({'case': 'constant_gain_cancels', 'pass': abs(C_ref - C_gain) < GATE,
                  'detail': 'C unchanged under constant gain (zero-offset linear model): dC=%.3g'
                            % abs(C_ref - C_gain)})
    off12 = 0.05
    r_off = oo.run_pipeline(lambda t: cb12(t) + off12, [0.05 + j / FS for j in range(N)], None,
                            mode='intensity', instantaneous_limit=True, k0s=[160])
    C_off = r_off['dft'][160][1]
    cases.append({'case': 'offset_does_not_cancel', 'pass': abs(C_ref - C_off) > 1e-9,
                  'detail': 'nonzero offset changes normalized C: |dC|=%.3g (algebraic fact, '
                            'not an instrument linearity claim)' % abs(C_ref - C_off)})
    T12 = 1e-4
    q32 = oo.exposure_average(lambda t: 1.0 + 0.3 * math.cos(2 * math.pi * 400.0 * t), 0.001, T12, quadrature_nodes=32)
    q64 = oo.exposure_average(lambda t: 1.0 + 0.3 * math.cos(2 * math.pi * 400.0 * t), 0.001, T12, quadrature_nodes=64)
    cases.append({'case': 'quadrature_32_vs_64', 'pass': abs(q32 - q64) < GATE,
                  'detail': '32-node=%.17g 64-node=%.17g' % (q32, q64)})
    results.append(run_group('G12_gain_offset_quadrature', cases))

    all_pass = all(r['pass'] for r in results)
    return results, all_pass

if __name__ == '__main__':
    results, all_pass = main()
    out = sys.argv[1] if len(sys.argv) > 1 else 'observation_integration_report.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({'groups': results, 'all_pass': all_pass,
                   'status': 'OBSERVATION_OPERATOR_TESTED_ON_FIXED_FIXTURES' if all_pass else 'FAILED',
                   'note': 'fixed software fixtures only; NOT a validation of arbitrary physical inputs'}, f, indent=2)
    n_groups = len(results)
    n_pass = sum(1 for r in results if r['pass'])
    print('INTEGRATION_GROUPS %d/%d PASS all=%s' % (n_pass, n_groups, all_pass))
    sys.exit(0 if all_pass else 2)
