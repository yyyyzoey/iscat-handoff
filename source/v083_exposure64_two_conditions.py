# -*- coding: utf-8 -*-
"""v083 Phase D: exactly 2 new 64-node midpoint exposure evaluations (the
narrow budget explicitly authorised by the v083 instruction), for the two
frozen conditions with the largest v082 16->32 increments:

  1. D60/zf450/M400/a20, tau=200us - largest RELATIVE increment (~0.35623%)
  2. D60/zf450/M200/a20, tau=200us - largest ABSOLUTE increment (~2.86669e-8)

Same cached quadratic-form field, fixed time origin, window [t_k, t_k+tau],
double precision. The v082 16 evaluations are NOT re-run; 32/16/5-node values
are read from v082 tables / v076 MAT read-only. All tau remain SYNTHETIC_TAU.
A finite 32->64 decrease is limited numerical convergence evidence only; the
pure-cosine O(M^-2) theorem does not extend to piecewise-interpolated
prescribed motion.
"""
import os, sys, csv, json
import numpy as np
import h5py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v083_common import ROOT, N, FS, K0, block_at
from v082_qf_common import qf_coefficients, qf_series, cbin

GH = os.path.join(ROOT, 'github_handoff')
TAB = os.path.join(GH, 'tables')
DYN = os.path.join(ROOT, 'v076_return', 'numeric', 'v076_dynamic_center_corrected.mat')
TAU = 2e-4
TARGETS = [('D60_zf450_M400_a20', 'M400', 400.0, 20.0),
           ('D60_zf450_M200_a20', 'M200', 200.0, 20.0)]


def g17(x):
    return '%.17g' % x


def main():
    # read-only references
    v082 = {}
    with open(os.path.join(TAB, 'v082_exposure16_convergence.csv'), 'r', newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['case'] in ('D60_zf450_M400_a20', 'D60_zf450_M200_a20') and r['tau_s'].startswith(('0.0002', '0.00020000000000000001')):
                v082[(r['case'], r['quadrature'])] = r
    f2 = h5py.File(DYN, 'r')
    tj = np.arange(N) / FS
    Es, Eref = block_at(60, 450, 21, 21)
    Lm, Dm_, Qm, Iref = qf_coefficients(Es, Eref)
    rows = []
    for key, ttype, freq, a in TARGETS:
        tau_key = key + '_tau0_0002'
        old5 = f2[tau_key]
        old5_abs = float(np.array(old5['absCenter']).flatten()[0])
        old5_c = old5['C400'][:]
        old5_C = complex(old5_c[20, 20]['real'], old5_c[20, 20]['imag'])
        # 64-node midpoint evaluation (1 new time-domain evaluation per condition)
        M = 64
        nodes = np.arange(M) + 0.5
        tt = tj[:, None] + nodes[None, :] * TAU / M
        xx = a * np.cos(2 * np.pi * freq * tt)
        ser = qf_series(xx, Lm, Dm_, Qm, Iref, dtype=np.float64).mean(axis=1)
        C, Im = cbin(ser)
        r32 = v082[(key, 'midpoint32')]
        r16 = v082[(key, 'midpoint16')]
        a32, a16 = float(r32['absC400_center']), float(r16['absC400_center'])
        inc32 = abs(abs(C) - a32)
        inc32_rel = inc32 / max(a32, 1e-300)
        decreased = inc32 < abs(a32 - a16)
        rows.append({
            'case_id': key, 'type': ttype, 'a_nm': int(a), 'tau_s': g17(TAU),
            'quadrature': 'midpoint64', 'n_frames': N, 'nodes': M,
            'absC400_center': g17(abs(C)),
            'Cbin_Re': g17(C.real), 'Cbin_Im': g17(C.imag),
            'Cbin_phase_rad': g17(np.angle(C)),
            'Imean': g17(Im),
            'absC400_midpoint32_ref': r32['absC400_center'],
            'absC400_midpoint16_ref': r16['absC400_center'],
            'absC400_5node_left_v076_ref': g17(old5_abs),
            'increment_32_to_64_abs': g17(inc32),
            'increment_32_to_64_rel': g17(inc32_rel),
            'increment_16_to_32_abs_ref': r32['increment_16_to_32_abs'],
            'increment_32_to_64_smaller_than_16_to_32': 'YES' if decreased else 'NO',
            'delta_vs_5node_abs': g17(abs(abs(C) - old5_abs)),
            'delta_vs_5node_rel': g17(abs(abs(C) - old5_abs) / max(old5_abs, 1e-300)),
            'tau_status': 'SYNTHETIC_TAU',
            'status': 'COMPLETED',
            'note': 'finite numerical convergence evidence only; O(M^-2) of pure cosine does not extend to piecewise-interpolated prescribed motion; near-zero relative values are not instrument exposure error'})
    f2.close()
    with open(os.path.join(TAB, 'v083_exposure64_target2.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator='\n'); w.writeheader(); w.writerows(rows)
    with open(os.path.join(TAB, 'v083_exposure64_target2.csv'), 'r', newline='', encoding='utf-8') as f:
        rr = list(csv.reader(f))
    assert len(rr) - 1 == 2 and all(len(x) == len(rr[0]) for x in rr)
    for r in rows:
        print('[D] %s: |C|64=%s inc32->64=%.3e (rel %.3e) smaller_than_16->32: %s' % (
            r['case_id'], r['absC400_center'], float(r['increment_32_to_64_abs']),
            float(r['increment_32_to_64_rel']), r['increment_32_to_64_smaller_than_16_to_32']))
    summary = {'evaluations_used': 2, 'budget': 2, 'tau_status': 'SYNTHETIC_TAU'}
    with open(os.path.join(GH, 'logs', 'v083_phase_d_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)


if __name__ == '__main__':
    main()
