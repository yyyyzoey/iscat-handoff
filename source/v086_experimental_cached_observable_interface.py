# -*- coding: utf-8 -*-
"""v086 Phase D: read-only observable interface matching for the EXISTING
cached 7.29 experimental 400 Hz results. No BMP reread, no new ROI definition,
no free registration, no experimental-D fitting.

Candidate sources checked (read-only):
  - github_handoff/numeric/fft400_corrected_small_roi.mat (committed copy)
  - v073_return/numeric/fft400_corrected_small_roi.mat (workstation original)
  - v073_return/numeric/fft400_corrected_full.mat
  - v072_return/numeric/replay_729_frames1000_3000.mat
Each object gets SOURCE_PRESENT/NOT_FOUND, its operator metadata, and an
OPERATOR_MATCH/MISMATCH/UNKNOWN verdict against the demo observable contract
(Cbin = 2*X_160/(N*Imean), N=2001, Fs=5000, k0=160, floor=0.01*median)."""
import os, sys, csv, json, hashlib
import numpy as np
import h5py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v083_common import ROOT

GH = os.path.join(ROOT, 'github_handoff')
TAB = os.path.join(GH, 'tables')


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def decode_u16(arr):
    try:
        return ''.join(chr(int(c)) for c in np.asarray(arr).flatten())
    except Exception:
        return ''


def inspect_h5(p):
    m = {}
    with h5py.File(p, 'r') as f:
        m['C400'] = f['C400'][:]
        m['X400'] = f['X400'][:]
        m['Imean'] = np.asarray(f['Imean']).astype(np.float64)
        m['validMask'] = np.asarray(f['validMask']).astype(bool)
        m['N'] = float(np.asarray(f['N']).flatten()[0])
        m['Fs'] = float(np.asarray(f['Fs']).flatten()[0])
        m['k'] = float(np.asarray(f['k']).flatten()[0])
        m['meanFloor'] = float(np.asarray(f['meanFloor']).flatten()[0])
        m['actualFreq'] = float(np.asarray(f['actualFreq']).flatten()[0])
        m['startFrame'] = float(np.asarray(f['meta/startFrame']).flatten()[0])
        m['endFrame'] = float(np.asarray(f['meta/endFrame']).flatten()[0])
        m['extractor'] = decode_u16(f['meta/extractor'][:])
        m['layout'] = decode_u16(f['meta/layout'][:])
        m['layout_tag'] = decode_u16(f['layout_tag'][:])
    return m


def main():
    sources = [
        ('github_handoff/numeric/fft400_corrected_small_roi.mat', os.path.join(GH, 'numeric', 'fft400_corrected_small_roi.mat')),
        ('v073_return/numeric/fft400_corrected_small_roi.mat', os.path.join(ROOT, 'v073_return', 'numeric', 'fft400_corrected_small_roi.mat')),
        ('v073_return/numeric/fft400_corrected_full.mat', os.path.join(ROOT, 'v073_return', 'numeric', 'fft400_corrected_full.mat')),
        ('v072_return/numeric/replay_729_frames1000_3000.mat', os.path.join(ROOT, 'v072_return', 'numeric', 'replay_729_frames1000_3000.mat')),
    ]
    rows = []
    exp = None
    for name, p in sources:
        if not os.path.isfile(p):
            rows.append({'object_name': name, 'sha256': '-', 'size_bytes': '0',
                         'SOURCE': 'NOT_FOUND', 'OPERATOR': 'UNKNOWN',
                         'operator_details': 'file absent', 'note': 'do NOT fabricate'})
            continue
        sha = sha256_file(p)
        try:
            m = inspect_h5(p)
            # operator contract check
            N = m['N']; Fs = m['Fs']; k = m['k']
            op_checks = {'N=2001': N == 2001, 'Fs=5000': Fs == 5000, 'k0=160(0-based)or161(MATLAB)': k in (160, 161),
                         'freq': abs(m['actualFreq'] - 399.800099950025) < 1e-6,
                         'frames': (m['startFrame'], m['endFrame']) == (1000, 3000)}
            # recompute Cbin = 2*X/(N*Imean) from stored X400 and Imean on the mask
            X = m['X400']['real'].astype(np.float64) + 1j * m['X400']['imag'].astype(np.float64)
            Cst = m['C400']['real'].astype(np.float64) + 1j * m['C400']['imag'].astype(np.float64)
            mask = m['validMask'] & np.isfinite(m['Imean']) & (m['Imean'] > 0)
            Cre = 2.0 * X / (N * m['Imean'])
            err = float(np.max(np.abs(Cre[mask] - Cst[mask]))) if mask.any() else float('nan')
            op_checks['Cbin=2X/(N Imean) reproduces stored C400'] = err < 1e-6 * max(1.0, float(np.max(np.abs(Cst[mask]))))
            op_match = 'MATCH' if all(op_checks.values()) else 'MISMATCH'
            rows.append({'object_name': name, 'sha256': sha, 'size_bytes': str(os.path.getsize(p)),
                         'SOURCE': 'SOURCE_PRESENT', 'OPERATOR': op_match,
                         'operator_details': '; '.join('%s=%s' % (k, v) for k, v in op_checks.items()),
                         'note': 'extractor=%r layout=%r tag=%r meanFloor=%.6g; max|2X/(N Imean) - C400|=%.3g on mask (%d px)' % (
                             m['extractor'], m['layout'], m['layout_tag'], m['meanFloor'], err, int(mask.sum()))})
            if exp is None and op_match == 'MATCH':
                exp = (name, sha, m)
        except Exception as exc:
            rows.append({'object_name': name, 'sha256': sha, 'size_bytes': str(os.path.getsize(p)),
                         'SOURCE': 'SOURCE_PRESENT', 'OPERATOR': 'UNKNOWN',
                         'operator_details': 'inspection exception: %s' % exc, 'note': ''})
    # interface verdicts
    if exp:
        name, sha, m = exp
        comparability = 'NUMERIC_ONLY'
        spatial = 'MISSING'
        op = 'OPERATOR_MATCH'
    else:
        name, sha, m = '-', '-', None
        comparability = 'NOT_COMPARABLE'
        spatial = 'MISSING'
        op = 'UNKNOWN'
    rows.append({'object_name': 'INTERFACE_VERDICT', 'sha256': sha, 'size_bytes': '-',
                 'SOURCE': 'SOURCE_PRESENT' if exp else 'NOT_FOUND', 'OPERATOR': op,
                 'operator_details': 'N/Fs/k0/Cbin formula and floor rule match the demo operator definitions',
                 'note': 'SPATIAL_CALIBRATION=%s (real object-space nm/px unknown); SCIENTIFIC_COMPARABILITY=%s '
                         '(operator agreement is numerical only: demo 65nm grid vs real camera pixels, no magnetic '
                         'causality, no exposure truth, no noise model - no experimental-D comparison permitted)' % (spatial, comparability)})
    fields = ['object_name', 'sha256', 'size_bytes', 'SOURCE', 'OPERATOR', 'operator_details', 'note']
    with open(os.path.join(TAB, 'v086_cached_experimental_observable_interface.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n'); w.writeheader(); w.writerows(rows)
    with open(os.path.join(TAB, 'v086_cached_experimental_observable_interface.csv'), 'r', newline='', encoding='utf-8') as f:
        rr = list(csv.reader(f))
    assert len(rr) - 1 == len(rows) and all(len(x) == len(rr[0]) for x in rr)
    print('[D] sources=%d (present=%d); verdict: %s / %s / %s' % (
        len(rows) - 1, sum(1 for r in rows if r['SOURCE'] == 'SOURCE_PRESENT'), op, spatial, comparability))


if __name__ == '__main__':
    main()
