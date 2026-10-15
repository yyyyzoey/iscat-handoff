# -*- coding: utf-8 -*-
"""v092 Phase D: 24 intermediate-amplitude states (a={10,15} nm) - pre-
registered new prescribed motion on the SAME cached anchors. Zero BEM/renders.
No historical C400 comparison exists (NOT_APPLICABLE_NEW_PRESCRIBED_STATE)."""
import os, sys, csv, json, hashlib
import numpy as np
from scipy.io import savemat, loadmat

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v092_core import build_bank_3bin

GH = os.path.join(r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff')
TAB = os.path.join(GH, 'tables')
AN = os.path.join(GH, 'analysis')
BANK = os.path.join(AN, 'bank')
STATES = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
          for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (10, 15)]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    status_rows = []
    for key in STATES:
        p = key.split('_')
        D, zf, ttype, a = int(p[0][1:]), int(p[1][2:]), p[2], int(p[3][1:])
        fn = 'v092_bank_%s.mat' % key
        outp = os.path.join(BANK, fn)
        C, X, Im, mask = build_bank_3bin(D, zf, ttype, a, None)
        savemat(outp, {'C': C, 'X': X, 'Imean_map': Im, 'valid_mask': mask,
                       'case_id': key, 'N': 2001, 'Fs': 5000.0,
                       'k0_bins': np.array([80, 160, 320]),
                       'a_nm': a, 'prescribed': 'NEW_PRESCRIBED_STATE_V092'},
                 do_compression=True)
        m = loadmat(outp)
        ok = np.asarray(m['C'], dtype=np.complex128).shape == (3, 41, 41)
        status_rows.append({'case_id': key, 'a_nm': a, 'map_file': 'analysis/bank/' + fn,
                            'sha256': sha256_file(outp), 'readback_ok': 'YES' if ok else 'NO',
                            'historical_C400_comparison': 'NOT_APPLICABLE_NEW_PRESCRIBED_STATE',
                            'status': 'BANK_BUILT_NEW_PRESCRIBED_STATE'})
        print('  %s built' % key)
    all_f = sorted({k for r in status_rows for k in r})
    with open(os.path.join(TAB, 'v092_intermediate_bank24.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=all_f, lineterminator='\n')
        w.writeheader(); w.writerows(status_rows)
    print('[D] summary:', json.dumps({'built': len(status_rows), 'of': 24}))
    with open(os.path.join(GH, 'logs', 'v092_phase_d_summary.json'), 'w', encoding='utf-8') as f:
        json.dump({'built': len(status_rows)}, f, indent=2)


if __name__ == '__main__':
    main()
