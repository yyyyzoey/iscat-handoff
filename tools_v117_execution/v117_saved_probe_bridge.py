# -*- coding: utf-8 -*-
"""v115 saved-probe bridge: the 576 checks (192 saved series x 3 bins) are run
THROUGH THE ACTUAL FIXED observation_operator module (production_fft +
independent_dft on the SAME stored float64 array) and compared against the
bank X[k,i,j]/C[k,i,j] with the original complex gate < 1e-11. Row PASS now
includes dtype, finiteness, positive mean, and exact key-set membership.
READ-ONLY: no scattering caches, no unsaved pixels, no BMP, no new forwards."""
import os, sys, csv, json, math, hashlib, argparse
import numpy as np
from scipy.io import loadmat
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import observation_operator as oo

N = 2001
K0S = [80, 160, 320]
PROBE_PIXELS = [(20, 20), (20, 0), (0, 20), (25, 0)]
GATE = 1e-11
ALL48 = (['D%d_zf%d_%s_a%d' % (D, zf, t, a)
          for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)] +
         ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
          for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (10, 15)])

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    an = os.path.join(args.root, 'analysis')
    npz_path = os.path.join(an, 'v093_probe_evidence.npz')
    npz_sha = sha256_file(npz_path)
    zs = np.load(npz_path)
    series_keys = sorted(k for k in zs.files if k.startswith('series_'))
    expected_keys = {'series_%s_h5_%d_%d' % (case, i, j)
                     for case in ALL48 for (i, j) in PROBE_PIXELS}
    keys_ok = set(series_keys) == expected_keys
    bank_sha = {}
    bank = {}
    for case in ALL48:
        p = os.path.join(an, 'bank', 'v092_bank_%s.mat' % case)
        bank_sha[case] = sha256_file(p)
        m = loadmat(p)
        bank[case] = {'X': np.asarray(m['X']).astype(np.complex128),
                      'C': np.asarray(m['C']).astype(np.complex128),
                      'Im': np.asarray(m['Imean_map']).astype(np.float64)}
    rows = []
    issues = []
    for sk in series_keys:
        body = sk.replace('series_', '')
        case_id, pix = body.split('_h5_')
        i5, j5 = int(pix.split('_')[0]), int(pix.split('_')[1])
        raw = zs[sk]
        dtype_ok = raw.dtype == np.float64
        s = np.asarray(raw, dtype=np.float64)
        finite_ok = bool(np.isfinite(s).all())
        mean = math.fsum(s) / N
        mean_ok = mean > 0
        # production module paths on the SAME stored array
        prod = oo.production_fft(s, mean, k0s=K0S)
        indep = oo.independent_dft(s, mean, k0s=K0S)
        # bank Imean_map value at this pixel for the v117 mean-identity gate
        Imean_bank = float(bank[case_id]['Im'].reshape(-1)[i5 * 41 + j5])
        for ki, k0 in enumerate(K0S):
            X_p, C_p = prod[k0]
            X_i, C_i = indep[k0]
            X_b = complex(bank[case_id]['X'][ki].reshape(-1)[i5 * 41 + j5])
            C_b = complex(bank[case_id]['C'][ki].reshape(-1)[i5 * 41 + j5])
            d_p = abs(X_p - X_b)
            d_i = abs(X_i - X_b)
            dc_p = abs(C_p - C_b)
            dc_i = abs(C_i - C_b)
            # v117 NEW explicit gates: same-array FFT-DFT agreement and the
            # saved-series mean vs the bank Imean_map
            d_fftdft_x = abs(X_p - X_i)
            d_fftdft_c = abs(C_p - C_i)
            d_mean_bank = abs(mean - Imean_bank)
            ok = (d_p < GATE and d_i < GATE and dc_p < GATE and dc_i < GATE
                  and d_fftdft_x < GATE and d_fftdft_c < GATE
                  and d_mean_bank < 1e-12
                  and dtype_ok and finite_ok and mean_ok)
            if not ok:
                issues.append('%s bin%d: d_prod=%g d_indep=%g dtype=%s finite=%s mean_pos=%s'
                              % (sk, k0, d_p, d_i, dtype_ok, finite_ok, mean_ok))
            rows.append({'record_key': '%s|bin%d|px(%d,%d)' % (case_id, k0, i5, j5),
                         'case_id': case_id, 'pixel_h5': '(%d,%d)' % (i5, j5), 'k0': k0,
                         'X_prod_Re': '%.17g' % X_p.real, 'X_prod_Im': '%.17g' % X_p.imag,
                         'X_indep_Re': '%.17g' % X_i.real, 'X_indep_Im': '%.17g' % X_i.imag,
                         'X_bank_Re': '%.17g' % X_b.real, 'X_bank_Im': '%.17g' % X_b.imag,
                         'C_prod_Re': '%.17g' % C_p.real, 'C_prod_Im': '%.17g' % C_p.imag,
                         'C_indep_Re': '%.17g' % C_i.real, 'C_indep_Im': '%.17g' % C_i.imag,
                         'C_bank_Re': '%.17g' % C_b.real, 'C_bank_Im': '%.17g' % C_b.imag,
                         'abs_dX_production_vs_bank': '%.17g' % d_p,
                         'abs_dX_independent_vs_bank': '%.17g' % d_i,
                         'abs_dC_production_vs_bank': '%.17g' % dc_p,
                         'abs_dC_independent_vs_bank': '%.17g' % dc_i,
                         'abs_dX_fft_vs_dft': '%.17g' % d_fftdft_x,
                         'abs_dC_fft_vs_dft': '%.17g' % d_fftdft_c,
                         'abs_dmean_vs_bank_Imean': '%.17g' % d_mean_bank,
                         'gate': 'bank diffs + same-array FFT-DFT <1e-11; mean vs Imean_map <1e-12',
                         'dtype_float64_in_pass': dtype_ok, 'finite_in_pass': finite_ok,
                         'mean_positive_in_pass': mean_ok,
                         'probe_npz_sha256': npz_sha, 'bank_sha256': bank_sha[case_id],
                         'status': 'PASS' if ok else 'FAIL'})
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    n_pass = sum(1 for r in rows if r['status'] == 'PASS')
    set_ok = (len(rows) == 576 and len({r['record_key'] for r in rows}) == 576 and keys_ok)
    summary = {'checked': len(rows), 'passed': n_pass, 'failed': len(rows) - n_pass,
               'complete_set_576_unique_and_expected': set_ok,
               'backend': 'tools/observation_operator.py production_fft + independent_dft '
                          '(same stored array); original gate < 1e-11',
               'scope': 'READ-ONLY regression of saved simulated probes through the production '
                        'module; NOT new optical forwards and NOT 41x41 full-ROI validation',
               'issues': issues[:20]}
    with open(args.output.replace('.csv', '.summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print('BRIDGE %d/%d PASS complete=%s' % (n_pass, len(rows), set_ok))
    return 0 if (n_pass == 576 and set_ok) else 2

if __name__ == '__main__':
    sys.exit(main())
