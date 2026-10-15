# -*- coding: utf-8 -*-
"""v088 Phase D: bounded segmented/spectral diagnostic of the CACHED
experimental video - the ONLY new cached-video time-domain analysis this round
(one read of roiFrames, pure post-processing).

PRE-REGISTERED (before any result): windows j=0..999 (N1=1000) and
j=1000..2000 (N2=1001) of the SAME 2001-sample record, global time origin
(no per-window clock reset); secondary diagnostic frequencies f in
{200, 400, 420} Hz with EXACT continuous demodulation

  C_f^(w)(p) = 2/(N_w * Imean_w(p)) * sum_{j in w}(I_j(p)-Imean_w(p))
               * exp(-2*pi*i*f*j/Fs).

These are SECONDARY_WITHIN_RECORD_DIAGNOSTIC quantities: different segment
lengths and frequency grid from the main contract FFT (N=2001, k0=160,
399.8001 Hz). They are NOT substitute main-frequency data and support no
displacement, causality, detectability or diameter claims."""
import os, sys, csv, json, hashlib
import numpy as np
import h5py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v083_common import ROOT

GH = os.path.join(ROOT, 'github_handoff')
TAB = os.path.join(GH, 'tables')
NUM = os.path.join(GH, 'numeric')
P = os.path.join(NUM, 'fft400_corrected_small_roi.mat')
WINDOWS = [('W1', 0, 1000), ('W2', 1000, 2001)]   # [lo, hi) sample indices
FREQS = [200.0, 400.0, 420.0]
FS = 5000.0
N = 2001


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def g17(x):
    return '%.17g' % x


def main():
    sha = sha256_file(P)
    with h5py.File(P, 'r') as f:
        frames = np.asarray(f['roiFrames'][:, 0, :, :], dtype=np.float64)  # single read
        maskst = np.asarray(f['validMask']).astype(bool)
        meanFloor = float(np.asarray(f['meanFloor']).flatten()[0])
    assert frames.shape == (N, 41, 41)
    mask_rule = np.isfinite(frames.mean(axis=0)) & (frames.mean(axis=0) > meanFloor)
    common = maskst & mask_rule
    maps = {}
    rows = []
    for wname, lo, hi in WINDOWS:
        Nw = hi - lo
        Iw = frames[lo:hi, :, :]
        Imw = Iw.mean(axis=0)
        jg = np.arange(lo, hi, dtype=np.float64)  # GLOBAL time origin
        for f in FREQS:
            e = np.exp(-2j * np.pi * f * jg / FS)
            X = np.tensordot(e, Iw - Imw[None, :, :], axes=(0, 0))
            with np.errstate(invalid='ignore', divide='ignore'):
                C = 2.0 * X / (Nw * Imw)
            Cm = np.where(common & np.isfinite(C), C, np.nan + 1j * np.nan)
            maps[(wname, f)] = Cm
    # pairwise (per frequency): window1 vs window2
    for f in FREQS:
        C1, C2 = maps[('W1', f)], maps[('W2', f)]
        m = np.isfinite(C1) & np.isfinite(C2)
        v1, v2 = C1[m], C2[m]
        coh = float(abs(np.vdot(v1, v2)) / max(np.linalg.norm(v1) * np.linalg.norm(v2), 1e-300))
        dabs = float(np.linalg.norm(v1 - v2))
        drel = dabs / max(float(np.linalg.norm(v2)), 1e-300)
        rows.append({
            'freq_Hz': '%.1f' % f, 'window1': 'W1 j=0..999 (N=1000)', 'window2': 'W2 j=1000..2000 (N=1001)',
            'n_common_pixels': int(m.sum()),
            'roi_median_absC_W1': g17(float(np.median(np.abs(v1)))),
            'roi_median_absC_W2': g17(float(np.median(np.abs(v2)))),
            'L2_W1': g17(float(np.linalg.norm(v1))), 'L2_W2': g17(float(np.linalg.norm(v2))),
            'complex_inner_product_coherence': g17(coh),
            'abs_change_W1_W2': g17(dabs), 'rel_change_W1_W2': g17(drel),
            'status': 'COMPLETED_REAL_CACHED_DATA',
            'note': 'SECONDARY_WITHIN_RECORD_DIAGNOSTIC: not the main N=2001 k0=160 FFT estimator; '
                    'coherence is a within-record spatial-map consistency description, NOT magnetic causality '
                    'or an independent repeat; 420 Hz is an empirical control, not a proven noise distribution'})
    np.savez_compressed(os.path.join(NUM, 'v088_cached_segment_maps.npz'),
                        source_file='fft400_corrected_small_roi.mat', source_sha256=sha,
                        **{'C_%s_%dHz' % (w, int(f)): maps[(w, f)] for (w, f) in maps},
                        windows=json.dumps(WINDOWS), freqs=json.dumps(FREQS),
                        common_mask=common, meanFloor_full_frame=meanFloor)
    fields = list(rows[0].keys())
    with open(os.path.join(TAB, 'v088_cached_segment_spectra6.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n'); w.writeheader(); w.writerows(rows)
    # summary of the three frequencies
    s3 = []
    for f in FREQS:
        C1, C2 = maps[('W1', f)], maps[('W2', f)]
        m = np.isfinite(C1) & np.isfinite(C2)
        s3.append({'freq_Hz': '%.1f' % f,
                   'coherence': rows[FREQS.index(f)]['complex_inner_product_coherence'],
                   'abs_change': rows[FREQS.index(f)]['abs_change_W1_W2'],
                   'rel_change': rows[FREQS.index(f)]['rel_change_W1_W2']})
    with open(os.path.join(TAB, 'v088_cached_segment_summary3.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['freq_Hz', 'coherence', 'abs_change', 'rel_change'], lineterminator='\n')
        w.writeheader(); w.writerows(s3)
    # readback
    for name, nexp in (('v088_cached_segment_spectra6.csv', 3), ('v088_cached_segment_summary3.csv', 3)):
        with open(os.path.join(TAB, name), 'r', newline='', encoding='utf-8') as f:
            rr = list(csv.reader(f))
        assert len(rr) - 1 == nexp and all(len(x) == len(rr[0]) for x in rr), name
        assert len({x[0] for x in rr[1:]}) == nexp, name
    with np.load(os.path.join(NUM, 'v088_cached_segment_maps.npz')) as z:
        n_maps = sum(1 for k in z.files if k.startswith('C_'))
        assert n_maps == 6
        assert z['C_W1_400Hz'].shape == (41, 41)
    print('[D] summary:', json.dumps({
        'maps': 6, 'windows': 2, 'freqs': 3,
        'coherence_200Hz': s3[0]['coherence'], 'coherence_400Hz': s3[1]['coherence'],
        'coherence_420Hz': s3[2]['coherence'],
        'source_sha': sha[:16], 'new_simulations': 0}))
    with open(os.path.join(GH, 'logs', 'v088_phase_d_summary.json'), 'w', encoding='utf-8') as f:
        json.dump({'maps': 6, 'coherence_200': s3[0]['coherence'],
                   'coherence_400': s3[1]['coherence'], 'coherence_420': s3[2]['coherence']}, f, indent=2)


if __name__ == '__main__':
    main()
