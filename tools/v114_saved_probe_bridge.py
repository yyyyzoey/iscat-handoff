# -*- coding: utf-8 -*-
"""v114 saved-probe bridge (READ-ONLY regression of old simulated probes).

Reads analysis/v093_probe_evidence.npz (192 saved pixel time series) and the 48
v092 bank MAT files. For each of the 192 series x 3 bins = 576 checks, the SAME
stored float64 series is run through NumPy FFT and through an integer-remainder
math.fsum direct DFT, and both are compared against the bank X[k,i,j] / C[k,i,j]
with the original complex absolute gate < 1e-11. No scattering-field caches, no
unsaved optical pixels, no BMP files, no new optical forwards."""
import os, sys, csv, json, math, hashlib, argparse
import numpy as np
from scipy.io import loadmat

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
    expected = {'series_%s_h5_%d_%d' % (case, i, j)
                for case in ALL48 for (i, j) in PROBE_PIXELS}
    bank_sha = {}
    bank = {}
    for case in ALL48:
        p = os.path.join(an, 'bank', 'v092_bank_%s.mat' % case)
        bank_sha[case] = sha256_file(p)
        m = loadmat(p)
        bank[case] = {'X': np.asarray(m['X']).astype(np.complex128),
                      'C': np.asarray(m['C']).astype(np.complex128)}
    rows = []
    issues = []
    n_checked = 0
    for sk in series_keys:
        body = sk.replace('series_', '')
        case_id, pix = body.split('_h5_')
        i5, j5 = int(pix.split('_')[0]), int(pix.split('_')[1])
        s = zs[sk]
        dtype_ok = s.dtype == np.float64
        s = np.asarray(s, dtype=np.float64)
        finite_ok = bool(np.isfinite(s).all())
        mean = math.fsum(s) / N
        mean_ok = mean > 0
        arr = np.asarray(s) - mean
        spec = np.fft.fft(arr)
        for ki, k0 in enumerate(K0S):
            X_fft = complex(spec[k0])
            C_fft = 2.0 * X_fft / (N * mean)
            # independent direct DFT on the SAME stored array, integer remainder phases
            ph = np.exp(-2j * math.pi * ((np.arange(N) * k0) % N) / N)
            X_dft = complex(math.fsum((arr * ph.real).tolist())
                            + 1j * math.fsum((arr * ph.imag).tolist()))
            C_dft = 2.0 * X_dft / (N * mean)
            X_bank = complex(bank[case_id]['X'][ki].reshape(-1)[i5 * 41 + j5])
            C_bank = complex(bank[case_id]['C'][ki].reshape(-1)[i5 * 41 + j5])
            dX_fft = abs(X_fft - X_bank)
            dX_dft = abs(X_dft - X_bank)
            dC_fft = abs(C_fft - C_bank)
            dC_dft = abs(C_dft - C_bank)
            ok = (dX_fft < GATE and dX_dft < GATE and dC_fft < GATE and dC_dft < GATE)
            n_checked += 1
            if not ok:
                issues.append('%s bin%d: dX_fft=%g dX_dft=%g dC_fft=%g dC_dft=%g'
                              % (sk, k0, dX_fft, dX_dft, dC_fft, dC_dft))
            rows.append({'record_key': '%s|bin%d|px(%d,%d)' % (case_id, k0, i5, j5),
                         'case_id': case_id, 'pixel_h5': '(%d,%d)' % (i5, j5), 'k0': k0,
                         'X_fft_Re': '%.17g' % X_fft.real, 'X_fft_Im': '%.17g' % X_fft.imag,
                         'X_dft_Re': '%.17g' % X_dft.real, 'X_dft_Im': '%.17g' % X_dft.imag,
                         'X_bank_Re': '%.17g' % X_bank.real, 'X_bank_Im': '%.17g' % X_bank.imag,
                         'C_fft_Re': '%.17g' % C_fft.real, 'C_fft_Im': '%.17g' % C_fft.imag,
                         'C_dft_Re': '%.17g' % C_dft.real, 'C_dft_Im': '%.17g' % C_dft.imag,
                         'C_bank_Re': '%.17g' % C_bank.real, 'C_bank_Im': '%.17g' % C_bank.imag,
                         'abs_dX_fft': '%.17g' % dX_fft, 'abs_dX_dft': '%.17g' % dX_dft,
                         'abs_dC_fft': '%.17g' % dC_fft, 'abs_dC_dft': '%.17g' % dC_dft,
                         'gate': 'all complex abs diffs < 1e-11',
                         'mean_positive': mean_ok, 'dtype_float64': dtype_ok, 'finite': finite_ok,
                         'probe_npz_sha256': npz_sha, 'bank_sha256': bank_sha[case_id],
                         'status': 'PASS' if ok else 'FAIL'})
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    n_pass = sum(1 for r in rows if r['status'] == 'PASS')
    set_ok = (len(rows) == 576 and len({r['record_key'] for r in rows}) == 576)
    summary = {'checked': n_checked, 'passed': n_pass, 'failed': n_checked - n_pass,
               'complete_set_576_unique': set_ok,
               'scope': 'READ-ONLY regression of saved simulated probes; NOT new optical '
                        'forwards and NOT a 41x41 full-ROI independent time-domain validation',
               'issues': issues[:20]}
    with open(args.output.replace('.csv', '.summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print('BRIDGE %d/%d PASS complete=%s' % (n_pass, n_checked, set_ok))
    return 0 if (n_pass == 576 and set_ok) else 2

if __name__ == '__main__':
    sys.exit(main())
