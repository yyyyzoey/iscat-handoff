# -*- coding: utf-8 -*-
"""v082 Phase D: higher-order exposure quadrature for the 8 legacy synthetic
conditions (D60/zf450 x {M200,M400} x a={5,20} nm x tau={100,200} us).

16/32-node midpoint rules on the SAME cached optical field (v074 anchors,
corrected centre ROI, 25-subpixel centre block), double precision, fixed time
origin t=0, exposure window [t_k, t_k + tau]. 16 pure time-domain evaluations,
no new renders, no BEM. Analytic |sinc(400 tau)| fixture first.
Old 5-node left-rectangular single-precision results are inherited read-only
from v076_dynamic_center_corrected.mat tau keys.
True camera exposure is UNKNOWN: every tau here is SYNTHETIC_TAU.
"""
import os, sys, csv
import numpy as np
import h5py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v082_qf_common import (ROOT, N, FS, K0, load_center_blocks,
                            qf_coefficients, qf_series, cbin)

GH = os.path.join(ROOT, 'github_handoff')
TAB = os.path.join(GH, 'tables')
DYN = os.path.join(ROOT, 'v076_return', 'numeric', 'v076_dynamic_center_corrected.mat')
TAUS = [1e-4, 2e-4]
AMPS = [5.0, 20.0]
TYPES = [('M200', 200.0), ('M400', 400.0)]
METHODS = [('midpoint16', 16), ('midpoint32', 32)]


def sinc_400(tau):
    x = 400.0 * tau
    return float(np.sinc(x))  # numpy sinc(x) = sin(pi x)/(pi x)


def midpoint_attenuation(f, tau, M):
    return float(np.sin(np.pi * f * tau) / (M * np.sin(np.pi * f * tau / M)))


def sinc_fixture(rows):
    """Pure 400 Hz intensity sine fixture.

    The M-node midpoint rule of a pure cosine has EXACT analytic attenuation
    att(f,tau,M) = sin(pi f tau) / (M sin(pi f tau / M)) with phase shift
    pi f tau. Validation is against the full predicted DFT (including the
    bin-160 mirror-term interference), not naive |sinc|; analytic convergence
    att_M -> sinc(400 tau) is checked separately (M=32 closer than M=16).
    """
    m = 0.05
    f = 400.0
    tj = np.arange(N) / FS
    I0 = 1.0 + m * np.cos(2 * np.pi * f * tj)
    C0, _ = cbin(I0)
    c0 = abs(C0)
    att = {}
    for tau in TAUS:
        att[tau] = {M: float(np.sin(np.pi * f * tau) / (M * np.sin(np.pi * f * tau / M)))
                    for (_, M) in METHODS}
    for tau in TAUS:
        for name, M in METHODS:
            nodes = np.arange(M) + 0.5
            Iexp = np.empty(N)
            for k in range(N):
                t = tj[k] + nodes * tau / M
                Iexp[k] = np.mean(1.0 + m * np.cos(2 * np.pi * f * t))
            C, Im = cbin(Iexp)
            ratio = abs(C) / c0
            Cpred, _ = cbin(1.0 + m * att[tau][M] * np.cos(2 * np.pi * f * tj + np.pi * f * tau))
            ratio_pred = abs(Cpred) / c0
            meas_ok = abs(ratio - ratio_pred) < 1e-10
            exact = sinc_400(tau)
            conv_ok = (abs(att[tau][32] - exact) < abs(att[tau][16] - exact) / 3.0)
            rows.append({
                'case': 'FIXTURE_pure400Hz_sine', 'type': 'FIXTURE', 'a_nm': 0,
                'tau_s': '%.17g' % tau, 'quadrature': name,
                'absC400_center': '%.17g' % abs(C), 'C400_Re': '%.17g' % C.real,
                'C400_Im': '%.17g' % C.imag, 'phase_rad': '%.17g' % np.angle(C),
                'Imean': '%.17g' % Im,
                'delta_vs_5node_abs': 'NA', 'delta_vs_5node_rel': 'NA',
                'increment_16_to_32_abs': 'NA',
                'sinc_ref_400Hz': '%.17g' % exact,
                'ratio_vs_tau0': '%.17g' % ratio,
                'predicted_ratio_from_att_model': '%.17g' % ratio_pred,
                'midpoint_att_analytic': '%.17g' % att[tau][M],
                'tau_status': 'SYNTHETIC_TAU',
                'status': 'PASS' if (meas_ok and conv_ok) else 'FAIL',
                'note': 'midpoint %d-node; measured vs full predicted DFT model %s; att->sinc convergence %s' % (
                    M, 'MATCH' if meas_ok else 'MISMATCH', 'OK' if conv_ok else 'FAIL')})


def main():
    rows = []
    sinc_fixture(rows)
    f2 = h5py.File(DYN, 'r')
    tj = np.arange(N) / FS
    Es, Eref = load_center_blocks(60, 450)
    Lm, Dm_, Qm, Iref = qf_coefficients(Es, Eref)
    results = {}
    n_eval = 0
    for tname, ftraj in TYPES:
        for a in AMPS:
            for tau in TAUS:
                key = 'D60_zf450_%s_a%d_tau0_000%d' % (tname, int(a), int(tau * 1e6) / 100)
                key = 'D60_zf450_%s_a%d' % (tname, int(a)) + '_tau%g' % tau
                key = key.replace('0.0001', '0_0001').replace('0.0002', '0_0002')
                if key not in f2:
                    raise RuntimeError('missing old 5-node key %r' % key)
                old_abs = float(np.array(f2[key]['absCenter']).flatten()[0])
                old_c = f2[key]['C400'][:]
                old_C = complex(old_c[20, 20]['real'], old_c[20, 20]['imag'])
                xt = a * np.cos(2 * np.pi * ftraj * tj)
                prev = None
                for name, M in METHODS:
                    nodes = np.arange(M) + 0.5
                    # exposure-integrated series: mean over M midpoint nodes in [t_k, t_k+tau]
                    tt = tj[:, None] + nodes[None, :] * tau / M
                    xx = a * np.cos(2 * np.pi * ftraj * tt)
                    ser = qf_series(xx, Lm, Dm_, Qm, Iref, dtype=np.float64).mean(axis=1)
                    C, Im = cbin(ser)
                    n_eval += 1
                    inc = '' if prev is None else '%.17g' % abs(abs(C) - prev)
                    if prev is not None:
                        results[(tname, a, tau)] = (abs(C), inc)
                    prev = abs(C)
                    rows.append({
                        'case': 'D60_zf450_%s_a%d' % (tname, int(a)), 'type': tname,
                        'a_nm': int(a), 'tau_s': '%.17g' % tau, 'quadrature': name,
                        'absC400_center': '%.17g' % abs(C), 'C400_Re': '%.17g' % C.real,
                        'C400_Im': '%.17g' % C.imag, 'phase_rad': '%.17g' % np.angle(C),
                        'Imean': '%.17g' % Im,
                        'delta_vs_5node_abs': '%.17g' % abs(abs(C) - old_abs),
                        'delta_vs_5node_rel': '%.17g' % (abs(abs(C) - old_abs) / max(old_abs, 1e-300)),
                        'increment_16_to_32_abs': inc,
                        'sinc_ref_400Hz': '%.17g' % sinc_400(tau),
                        'ratio_vs_tau0': 'NA', 'tau_status': 'SYNTHETIC_TAU',
                        'status': 'COMPLETED',
                        'note': 'midpoint %d-node double precision on cached quadratic-form field; old 5-node left-rectangular single-precision inherited from v076' % M})
                # old 5-node reference row (inherited, not re-evaluated)
                rows.append({
                    'case': 'D60_zf450_%s_a%d' % (tname, int(a)), 'type': tname,
                    'a_nm': int(a), 'tau_s': '%.17g' % tau,
                    'quadrature': '5node_left_rectangular_v076_inherited',
                    'absC400_center': '%.17g' % old_abs,
                    'C400_Re': '%.17g' % old_C.real, 'C400_Im': '%.17g' % old_C.imag,
                    'phase_rad': '%.17g' % np.angle(old_C), 'Imean': 'NA',
                    'delta_vs_5node_abs': '0', 'delta_vs_5node_rel': '0',
                    'increment_16_to_32_abs': 'NA',
                    'sinc_ref_400Hz': '%.17g' % sinc_400(tau),
                    'ratio_vs_tau0': 'NA', 'tau_status': 'SYNTHETIC_TAU',
                    'status': 'INHERITED_V076',
                    'note': 'read-only from v076_dynamic_center_corrected.mat; not re-evaluated'})
    f2.close()
    fields = list(rows[0].keys())
    out = os.path.join(TAB, 'v082_exposure16_convergence.csv')
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    with open(out, 'r', newline='', encoding='utf-8') as f:
        rr = list(csv.reader(f))
    assert all(len(r) == len(rr[0]) for r in rr)
    print('[D] %d new time-domain evaluations (budget 16)' % n_eval)
    for r in rows:
        if r['quadrature'].startswith('midpoint'):
            print('  %-24s tau=%-8s %-11s |C|=%-12s d5node=%s' % (
                r['case'], r['tau_s'], r['quadrature'], r['absC400_center'],
                r['delta_vs_5node_abs']))


if __name__ == '__main__':
    main()



