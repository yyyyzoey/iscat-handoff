# -*- coding: utf-8 -*-
"""v092 Phase C: 3-bin bank for the 24 endpoint states (2 pilots then 22).
Per state: C[3,41,41], X[3,41,41], Imean, mask, probe series at 4 fixed h5
pixels, bin-160 verification vs the old double-precision C400 (rF < 1e-10).
Zero BEM, zero renders, zero BMP reads."""
import os, sys, csv, json, hashlib
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v092_core import build_bank_3bin, StrictStore, ContractError

GH = os.path.join(r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff')
TAB = os.path.join(GH, 'tables')
NUM = os.path.join(GH, 'numeric')
AN = os.path.join(GH, 'analysis')
BANK = os.path.join(AN, 'bank')
ALL24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
         for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)]
CACHED = {chr(39)+chr(39).join([])+chr(39): chr(39)+chr(39)}
PILOTS = ['D60_zf450_M200_a5', 'D60_zf450_M400_a20']
PROBES = [(20, 20), (20, 0), (0, 20), (25, 0)]  # h5 (axis1, axis2); note (25,0) is a non-corner asymmetric probe


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def g17(x):
    return '%.17g' % x


def main():
    os.makedirs(BANK, exist_ok=True)
    ledger = {}
    with open(os.path.join(TAB, 'v085_double_maps24_status.csv'), 'r', newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            ledger[r['case_id']] = r['map_sha256']
    attempts = []
    status_rows = []
    n_done = 0
    order = PILOTS + [k for k in ALL24 if k not in PILOTS]
    for key in order:
        p = key.split('_')
        D, zf, ttype, a = int(p[0][1:]), int(p[1][2:]), p[2], int(p[3][1:])
        fn = 'v092_bank_%s.mat' % key
        outp = os.path.join(BANK, fn)
        if os.path.isfile(outp):
            m = loadmat_ok(outp, key)
            if m is not None:
                n_done += 1
                status_rows.append(bank_status_row(key, m, ledger, 'REUSED_EXISTING_VERIFIED'))
                continue
        try:
            C, X, Im, mask = build_bank_3bin(D, zf, ttype, a, None)
            from scipy.io import savemat
            savemat(outp, {'C': C, 'X': X, 'Imean_map': Im, 'valid_mask': mask,
                           'case_id': key, 'N': 2001, 'Fs': 5000.0,
                           'k0_bins': np.array([80, 160, 320]),
                           'actual_Hz': np.array([80 * 5000 / 2001, 160 * 5000 / 2001, 320 * 5000 / 2001]),
                           'a_nm': a, 'trajectory': 'x(t)=a*cos(2*pi*f_motion*t), f_motion=%d' % (200 if ttype == 'M200' else 400)},
                      do_compression=True)
            # readback + verification
            m = loadmat_ok(outp, key)
            if m is None:
                raise RuntimeError('readback failed')
            # bin-160 vs old C400
            from scipy.io import loadmat as lm
            old_fn = CACHED.get(key, 'C400_double_%s.mat' % key)
            old = lm(os.path.join(NUM, old_fn))
            Cold = np.asarray(old['C400_double'], dtype=np.complex128).reshape(-1)
            Cnew160 = m['C'][1].reshape(-1)
            common = np.isfinite(Cnew160) & np.isfinite(Cold)
            rF = float(np.linalg.norm((Cnew160 - Cold)[common]) / max(np.linalg.norm(Cold[common]), 1e-300))
            n_done += 1
            status_rows.append(bank_status_row(key, m, ledger, 'BANK_VERIFIED', rF=rF))
            attempts.append({'case_id': key, 'attempt': 'START->BUILT->VERIFIED', 'rF_bin160': g17(rF)})
        except Exception as exc:
            attempts.append({'case_id': key, 'attempt': 'FAILED', 'error': str(exc)[:200]})
            status_rows.append({'case_id': key, 'status': 'FAILED', 'error': str(exc)[:200]})
    with open(os.path.join(TAB, 'v092_bank_status24.csv'), 'w', newline='', encoding='utf-8') as f:
        all_f = sorted({k for r in status_rows for k in r})
        w = csv.DictWriter(f, fieldnames=all_f, lineterminator='\n')
        w.writeheader(); w.writerows(status_rows)
    with open(os.path.join(AN, 'v092_bank_attempts.jsonl'), 'w', encoding='utf-8') as f:
        for a in attempts:
            f.write(json.dumps(a) + '\n')
    n_verified = sum(1 for r in status_rows if 'VERIFIED' in r['status'])
    print('[C] summary:', json.dumps({'verified': n_verified, 'of': 24}))
    with open(os.path.join(GH, 'logs', 'v092_phase_c_summary.json'), 'w', encoding='utf-8') as f:
        json.dump({'verified': n_verified, 'of': 24}, f, indent=2)
    if n_verified < 24:
        sys.exit(2)


def loadmat_ok(path, key):
    from scipy.io import loadmat
    m = loadmat(path)
    C = np.asarray(m['C'], dtype=np.complex128)
    if C.shape != (3, 41, 41) or str(m['case_id'].flatten()[0]) != key:
        return None
    return m


def bank_status_row(key, m, ledger, status, rF=None):
    fn = 'v092_bank_%s.mat' % key
    return {'case_id': key, 'map_file': 'analysis/bank/' + fn,
            'sha256': sha256_file(os.path.join(GH, 'analysis', 'bank', fn)),
            'ledger_sha256_400Hz': ledger.get(key, '-'),
            'rF_bin160_vs_old_C400': g17(rF) if rF is not None else
                ('see previous verification' if status == 'REUSED_EXISTING_VERIFIED' else 'NA'),
            'status': status}


def CACHED_get(key):
    return CACHED.get(key, 'C400_double_%s.mat' % key)


if __name__ == '__main__':
    main()
