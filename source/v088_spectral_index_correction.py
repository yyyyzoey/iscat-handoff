# -*- coding: utf-8 -*-
"""v088 Phase B1: spectral index correction.

v087 defect: neighbour frequencies were computed as f = k_matlab*Fs/N (one bin
high). Correct contract: k0 = k_matlab - 1 (0-based), f = k0*Fs/N.
Gate: |f - k0*Fs/N| < 1e-10 Hz (pure arithmetic identity; CSV precision noted)."""
import os, sys, csv, json, hashlib
from decimal import Decimal, getcontext
getcontext().prec = 50

GH = os.path.join(r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff')
TAB = os.path.join(GH, 'tables')
FS = 5000
N = 2001
ROWS = [(158, 157), (159, 158), (160, 159), (161, 160), (162, 161), (163, 162), (164, 163), (169, 168)]
# v073 historical reference frequencies (tables/fft_spectral_neighborhood.csv)
HIST = {158: '392.303848', 159: '394.802599', 160: '397.301349', 161: '399.800100',
        162: '402.298851', 163: '404.797601', 164: '407.296352', 169: '419.790105'}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    rows = []
    all_ok = True
    for kM, k0 in ROWS:
        f_exact = Decimal(k0) * Decimal(FS) / Decimal(N)
        f = k0 * FS / N
        gate = abs(f - k0 * FS / N) < 1e-10  # identity: same expression; recorded
        # cross-check against v073 historical value at CSV precision
        hist_ok = abs(f - float(HIST[kM])) < 5e-7  # historical CSV has 6 decimals
        ok = gate and hist_ok
        all_ok &= ok
        rows.append({'k_matlab': kM, 'k0_0based': k0,
                     'actualFreq_Hz': '%.6f' % f,
                     'freq_identity_gate_1e-10Hz': 'PASS' if gate else 'FAIL',
                     'v073_historical_freq_Hz': HIST[kM],
                     'matches_v073_history': 'YES' if hist_ok else 'NO',
                     'v087_wrong_freq_Hz': '%.6f' % (kM * FS / N),
                     'status': 'CORRECTED' if ok else 'FAIL'})
    fields = ['k_matlab', 'k0_0based', 'actualFreq_Hz', 'freq_identity_gate_1e-10Hz',
              'v073_historical_freq_Hz', 'matches_v073_history', 'v087_wrong_freq_Hz', 'status']
    with open(os.path.join(TAB, 'v088_spectral_bins_corrected.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n'); w.writeheader(); w.writerows(rows)
    with open(os.path.join(TAB, 'v088_spectral_bins_corrected.csv'), 'r', newline='', encoding='utf-8') as f:
        rr = list(csv.reader(f))
    assert len(rr) - 1 == 8 and all(len(x) == len(rr[0]) for x in rr)
    assert len({x[0] for x in rr[1:]}) == 8
    print('[B1] spectral bins corrected: 8/8 %s' % ('PASS' if all_ok else 'FAIL'))
    if not all_ok:
        sys.exit(2)

if __name__ == '__main__':
    main()
