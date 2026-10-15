# -*- coding: utf-8 -*-
"""v086 Phase B: file-source and mathematical re-verification of the 24
double-precision maps. ZERO new 2001-frame evaluations - read-only arrays plus
arithmetic recomputation, compared row-by-row against the v085 published CSVs.

Also re-verifies the fine-slice geometry sentinels through the production
guard, and records the v074 anchor cache SHAs backing each state."""
import os, sys, csv, json, hashlib
import numpy as np
import h5py
from scipy.io import loadmat

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v086_identity_guard as guard
from v083_common import ROOT, fine_slice
from v082_qf_common import cbin

GH = os.path.join(ROOT, 'github_handoff')
TAB = os.path.join(GH, 'tables')
NUM = os.path.join(GH, 'numeric')
DYN = os.path.join(ROOT, 'v076_return', 'numeric', 'v076_dynamic_center_corrected.mat')
ALL24 = guard.FROZEN_24
CACHED = {'D30_zf450_M400_a5': 'v083_fullROI_double_C400_D30_zf450_M400_a5.mat',
          'D30_zf550_M400_a5': 'v083_fullROI_double_C400_D30_zf550_M400_a5.mat',
          'D60_zf450_M400_a5': 'v083_fullROI_double_C400_D60_zf450_M400_a5.mat',
          'D100_zf450_M200_a20': 'v083_fullROI_double_C400_D100_zf450_M200_a20.mat',
          'D30_zf550_M400_a20': 'v084_double_C400_D30_zf550_M400_a20.mat',
          'D60_zf450_M400_a20': 'v084_double_C400_D60_zf450_M400_a20.mat'}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def g17(x):
    return '%.17g' % x


def main():
    # frozen ledger from v085 status table
    ledger = {}
    with open(os.path.join(TAB, 'v085_double_maps24_status.csv'), 'r', newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            ledger[r['case_id']] = r
    # anchor cache SHAs (identity chain)
    anchor_sha = {}
    cache_dir = os.path.join(ROOT, 'v074_return', 'numeric', 'render_cache')
    for fn in sorted(os.listdir(cache_dir)):
        anchor_sha[fn] = sha256_file(os.path.join(cache_dir, fn))

    f2 = h5py.File(DYN, 'r')
    rows = []
    n_ok = 0
    for key in ALL24:
        try:
            parts = key.split(chr(95))
            D = int(parts[0][1:]); zf = int(parts[1][2:])
            fn = CACHED.get(key, 'C400_double_%s.mat' % key)
            path = os.path.join(NUM, fn)
            if not os.path.isfile(path):
                rows.append({'case_id': key, 'status': 'MISSING_SOURCE',
                             'evidence_status': 'map file not found: %s' % fn})
                continue
            # production entry (shared validator) with frozen ledger SHA
            meta = guard.load_double_map(path, key,
                                         sha_ledger={fn: ledger[key]['map_sha256']})
            arrays = meta['arrays']
            C = np.asarray(arrays['C400_double'], dtype=np.complex128)
            mask = np.asarray(arrays['valid_mask']).astype(bool)
            Im = np.asarray(arrays['Imean_map'], dtype=np.float64)
            actual_sha = sha256_file(path)
            # recompute rF vs stored single map from ACTUAL arrays
            cm = f2[key]['C400'][:]
            Cs = cm['real'].astype(np.float64) + 1j * cm['imag'].astype(np.float64)
            common = mask & np.isfinite(Cs.real) & np.isfinite(Cs.imag)
            rF = float(np.linalg.norm((C - Cs)[common]) / max(np.linalg.norm(Cs[common]), 1e-300))
            v085_rF = float(ledger[key]['rF_double_vs_single'])
            rF_match = abs(rF - v085_rF) <= 1e-12 * max(1.0, abs(rF))
            # shape-path epsilon recompute
            nd = float(np.linalg.norm(np.abs(C[common])))
            ns = float(np.linalg.norm(np.abs(Cs[common])))
            ud = np.where(common, np.abs(C) / max(nd, 1e-300), 0.0)
            us = np.where(common, np.abs(Cs) / max(ns, 1e-300), 0.0)
            eps = float(np.linalg.norm(ud - us))
            v085_eps_row = None
            with open(os.path.join(TAB, 'v085_shape_numerical_delta24.csv'), 'r', newline='', encoding='utf-8') as f:
                for r in csv.DictReader(f):
                    if r['case_id'] == key:
                        v085_eps_row = float(r['epsilon_shape_path'])
            eps_match = v085_eps_row is not None and abs(eps - v085_eps_row) <= 1e-12 * max(1.0, eps)
            # fine-slice geometry sentinels through the production guard
            guard.validate_fine_slice(5, 26, 1, ((185, 190), (60, 65)))
            guard.validate_fine_slice(5, 16, 1, ((135, 140), (60, 65)))
            guard.validate_fine_slice(5, 21, 1, ((160, 165), (60, 65)))
            anchor_list = ';'.join('%s:%s' % (k, v[:16]) for k, v in sorted(anchor_sha.items())
                                   if k.startswith('D%d_zf%g_' % (D, zf)))
            ok = rF_match and eps_match
            n_ok += int(ok)
            rows.append({
                'case_id': key, 'map_file': fn,
                'source_SHA': actual_sha, 'ledger_SHA': ledger[key]['map_sha256'],
                'sha_match': 'YES' if actual_sha == ledger[key]['map_sha256'] else 'NO',
                'algorithm_SHA': sha256_file(os.path.join(GH, 'source', 'v086_identity_guard.py')),
                'object_metadata': json.dumps(meta, default=str)[:200],
                'actual_sha': actual_sha, 'readback_sha': sha256_file(path),
                'n_valid': int(mask.sum()), 'dtype': str(C.dtype),
                'rF_recomputed': g17(rF), 'rF_v085_published': g17(v085_rF),
                'rF_match': 'YES' if rF_match else 'NO',
                'epsilon_recomputed': g17(eps), 'epsilon_v085_published': g17(v085_eps_row or float('nan')),
                'epsilon_match': 'YES' if eps_match else 'NO',
                'fine_slice_sentinels': 'row26->(185,190)x(60,65); row16->(135,140)x(60,65); row21->(160,165)x(60,65) - production guard PASS',
                'anchor_cache_sha_identity': anchor_list[:200],
                'status': 'ARRAY_RECHECK_VERIFIED' if ok else 'ARRAY_RECHECK_FAILED',
                'evidence_status': 'actual MAT read + production guard + arithmetic recomputation'})
        except Exception as exc:
            rows.append({'case_id': key, 'status': 'ARRAY_RECHECK_FAILED',
                         'evidence_status': 'exception: %s' % exc})
    f2.close()
    fields = ['case_id', 'map_file', 'source_SHA', 'ledger_SHA', 'sha_match', 'algorithm_SHA',
              'object_metadata', 'actual_sha', 'readback_sha', 'n_valid', 'dtype',
              'rF_recomputed', 'rF_v085_published', 'rF_match',
              'epsilon_recomputed', 'epsilon_v085_published', 'epsilon_match',
              'fine_slice_sentinels', 'anchor_cache_sha_identity', 'status', 'evidence_status']
    with open(os.path.join(TAB, 'v086_24map_source_identity.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n'); w.writeheader(); w.writerows(rows)
    with open(os.path.join(TAB, 'v086_24map_source_identity.csv'), 'r', newline='', encoding='utf-8') as f:
        rr = list(csv.reader(f))
    assert len(rr) - 1 == 24 and all(len(x) == len(rr[0]) for x in rr)
    assert len(set(x[0] for x in rr[1:])) == 24
    n_failed = sum(1 for r in rows if r['status'] != 'ARRAY_RECHECK_VERIFIED')
    summary = {'phase': 'B', 'verified': n_ok, 'failed': n_failed, 'of': 24,
               'new_2001frame_evaluations': 0}
    print('[B] summary:', json.dumps(summary))
    with open(os.path.join(GH, 'logs', 'v086_phase_b_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    if n_ok < 24:
        sys.exit(2)


if __name__ == '__main__':
    main()
