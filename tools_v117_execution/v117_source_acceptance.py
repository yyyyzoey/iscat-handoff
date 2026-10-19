# -*- coding: utf-8 -*-
"""v117 source acceptance gate (S1): clean tree, exact 73 roles/cases, per-file
blob/length/SHA vs the fixed tree, review_inputs mapping failures become
gate failures, full BANK content checks with rebuilt 1%-median mask, C identity
<1e-10 with full-precision residual. Supports targeted negative controls on
small replica trees: every fault MUST produce gate=false with the reason."""
import os, sys, csv, json, math, hashlib, shutil, argparse
import numpy as np
from scipy.io import loadmat, savemat

ALL48 = (['D%d_zf%d_%s_a%d' % (D, zf, t, a)
          for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)] +
         ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
          for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (10, 15)])
ALL24 = ALL48[:24]
PROBE_PIXELS = [(20, 20), (20, 0), (0, 20), (25, 0)]

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def blob_sha1_bytes(data):
    h = hashlib.sha1()
    h.update(b'blob %d\x00' % len(data))
    h.update(data)
    return h.hexdigest()

def rcsv(p):
    with open(p, 'r', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def evaluate(root, snapshot_dir, review_dir, mini=False):
    """Returns {'gate': bool, 'issues': [...], 'checks': {...}}."""
    issues = []
    checks = {}
    tab = os.path.join(root, 'tables')
    bl_map_file = {r['case_id']: r['map_file'] for r in rcsv(os.path.join(tab, 'v085_double_maps24_status.csv'))}
    manifest = {}
    man_path = os.path.join(root, 'manifest_sha256.csv')
    if os.path.isfile(man_path):
        manifest = {r['path']: r['sha256'] for r in rcsv(man_path)}
    expected = []
    for key in ALL48:
        expected.append(('BANK', key, 'analysis/bank/v092_bank_%s.mat' % key))
    for key in ALL24:
        expected.append(('BASELINE', key, 'numeric/%s' % bl_map_file[key]))
    expected.append(('SAVED_SIMULATION_PROBES', 'PROBE_EVIDENCE_192_SERIES',
                     'analysis/v093_probe_evidence.npz'))
    # role/case multiset + per-file checks
    n_ok = 0
    for role, key, rel in expected:
        src = os.path.join(root, rel)
        if not os.path.isfile(src):
            issues.append('missing source: %s' % rel)
            continue
        sha = sha256_file(src)
        blob = blob_sha1_bytes(open(src, 'rb').read())
        length = os.path.getsize(src)
        ok = True
        if rel in manifest and manifest[rel] != sha:
            issues.append('sha mismatch vs manifest: %s' % rel)
            ok = False
        # snapshot copy
        snap = os.path.join(snapshot_dir, os.path.basename(rel))
        if os.path.isfile(snap):
            if sha256_file(snap) != sha:
                issues.append('snapshot byte mismatch: %s' % rel)
                ok = False
        else:
            issues.append('snapshot missing: %s' % rel)
            ok = False
        # review_inputs copy
        rev = os.path.join(review_dir, os.path.basename(rel))
        if os.path.isfile(rev):
            if sha256_file(rev) != sha:
                issues.append('review_inputs copy mismatch: %s' % rel)
                ok = False
        checks[rel] = {'sha256': sha, 'git_blob_sha1': blob, 'bytes': length,
                       'review_inputs': 'MATCH' if (os.path.isfile(rev) and
                                                    sha256_file(rev) == sha) else
                       ('COPY_MISSING' if not os.path.isfile(rev) else 'MISMATCH')}
        n_ok += int(ok)
    # BANK content checks
    bank_ok = 0
    for key in ALL48:
        p = os.path.join(root, 'analysis', 'bank', 'v092_bank_%s.mat' % key)
        if not os.path.isfile(p):
            continue
        try:
            m = loadmat(p)
        except Exception as ex:  # corrupt bytes must yield gate=false, never crash
            issues.append('unreadable bank file: %s (%s: %s)' % (key, type(ex).__name__, ex))
            continue
        try:
            C = np.asarray(m['C'])
            X = np.asarray(m['X'])
            Im = np.asarray(m['Imean_map'])
            mask_raw = np.asarray(m['valid_mask'])
            mask = mask_raw.astype(bool)
            cid = str(m['case_id'].flatten()[0])
            n_val = int(np.asarray(m['N']).flatten()[0])
            fs_val = float(np.asarray(m['Fs']).flatten()[0])
            k0_bins = [int(v) for v in np.asarray(m['k0_bins']).flatten()]
            ok = (str(C.dtype) == 'complex128' and str(X.dtype) == 'complex128'
                  and str(Im.dtype) == 'float64' and C.shape == (3, 41, 41)
                  and X.shape == (3, 41, 41) and Im.shape == (41, 41)
                  and cid == key and n_val == 2001 and fs_val == 5000.0
                  and k0_bins == [80, 160, 320])
            pos = Im[np.isfinite(Im) & (Im > 0)]
            floor = 0.01 * float(np.median(pos)) if pos.size else 0.0
            rebuilt = np.isfinite(Im) & (Im > floor)
            if not np.array_equal(mask, rebuilt):
                issues.append('mask does not match rebuilt 1%%-median rule: %s' % key)
                ok = False
            common = mask & np.isfinite(Im) & (Im > 0)
            resid = float(np.max(np.abs(2.0 * X / (float(n_val) * Im)[None, :, :] - C)[:, common])) if common.any() else float('inf')
            if not resid < 1e-10:
                issues.append('C identity residual >= 1e-10: %s (%g)' % (key, resid))
                ok = False
            if not (bool(np.isfinite(C[:, common]).all()) and bool(np.isfinite(X[:, common]).all())):
                issues.append('non-finite C/X: %s' % key)
                ok = False
            bank_ok += int(ok)
        except Exception as ex:  # noqa: BLE001
            issues.append('bank content exception: %s: %s' % (key, ex))
    probe_blob_ok = True
    npz_p = os.path.join(root, 'analysis', 'v093_probe_evidence.npz')
    if os.path.isfile(npz_path_guard := npz_p):
        if blob_sha1_bytes(open(npz_p, 'rb').read()) != '6b180147f64847329375363d44c317b2d4df247b':
            issues.append('probe NPZ git blob mismatch')
            probe_blob_ok = False
    gate = (not issues) and n_ok == 73 and bank_ok == 48 and probe_blob_ok
    return {'gate': gate, 'issues': issues[:60],
            'checks': {'files_ok': '%d/73' % n_ok, 'bank_content_ok': '%d/48' % bank_ok,
                       'probe_blob_ok': probe_blob_ok}}

def npz_path_guard(x):
    return x

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--snapshot-dir', required=True)
    ap.add_argument('--review-dir', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--negative-controls-dir', default='')
    args = ap.parse_args()
    res = evaluate(args.root, args.snapshot_dir, args.review_dir)
    negatives = []
    if args.negative_controls_dir:
        import zipfile
        nc_dir = args.negative_controls_dir
        os.makedirs(nc_dir, exist_ok=True)
        def build_mini(fault):
            mini = os.path.join(nc_dir, 'mini_%s' % fault)
            if os.path.isdir(mini):
                shutil.rmtree(mini)
            os.makedirs(os.path.join(mini, 'analysis', 'bank'))
            os.makedirs(os.path.join(mini, 'numeric'))
            os.makedirs(os.path.join(mini, 'review_inputs'))
            os.makedirs(os.path.join(mini, 'tables'))
            for fn in os.listdir(os.path.join(args.root, 'analysis', 'bank')):
                shutil.copy2(os.path.join(args.root, 'analysis', 'bank', fn),
                             os.path.join(mini, 'analysis', 'bank', fn))
            shutil.copy2(os.path.join(args.root, 'tables', 'v085_double_maps24_status.csv'),
                         os.path.join(mini, 'tables', 'v085_double_maps24_status.csv'))
            man = os.path.join(args.root, 'manifest_sha256.csv')
            if os.path.isfile(man):
                shutil.copy2(man, os.path.join(mini, 'manifest_sha256.csv'))
            npz = os.path.join(args.root, 'analysis', 'v093_probe_evidence.npz')
            if os.path.isfile(npz):
                os.makedirs(os.path.join(mini, 'analysis'), exist_ok=True)
                shutil.copy2(npz, os.path.join(mini, 'analysis', 'v093_probe_evidence.npz'))
            return mini
        # fault 1: wrong source bytes (flip a byte inside one bank file)
        mini = build_mini('wrong_bytes')
        bp = os.path.join(mini, 'analysis', 'bank', 'v092_bank_D30_zf450_M200_a5.mat')
        data = bytearray(open(bp, 'rb').read())
        data[len(data) // 2] ^= 0xFF
        open(bp, 'wb').write(bytes(data))
        r1 = evaluate(mini, os.path.join(mini, 'snapshot'), os.path.join(mini, 'review_inputs'))
        negatives.append({'fault': 'wrong_bytes', 'gate': r1['gate'], 'detected': not r1['gate'],
                          'issues': r1['issues'][:3]})
        # fault 2: review_inputs copy mismatch
        mini = build_mini('copy_mismatch')
        src_b = os.path.join(mini, 'analysis', 'bank', 'v092_bank_D30_zf450_M200_a20.mat')
        dst_b = os.path.join(mini, 'review_inputs', 'v092_bank_D30_zf450_M200_a20.mat')
        shutil.copy2(src_b, dst_b)
        data = bytearray(open(dst_b, 'rb').read())
        data[100] ^= 0xFF
        open(dst_b, 'wb').write(bytes(data))
        # snapshot dir mirrors sources so ONLY the copy mismatch fires
        snap = os.path.join(mini, 'snapshot')
        os.makedirs(snap, exist_ok=True)
        for fn in os.listdir(os.path.join(mini, 'analysis', 'bank')):
            shutil.copy2(os.path.join(mini, 'analysis', 'bank', fn), os.path.join(snap, fn))
        npz = os.path.join(args.root, 'analysis', 'v093_probe_evidence.npz')
        shutil.copy2(npz, os.path.join(mini, 'analysis', 'v093_probe_evidence.npz'))
        shutil.copy2(npz, os.path.join(snap, 'v093_probe_evidence.npz'))
        r2 = evaluate(mini, snap, os.path.join(mini, 'review_inputs'))
        negatives.append({'fault': 'copy_mismatch', 'gate': r2['gate'], 'detected': not r2['gate'],
                          'issues': r2['issues'][:3]})
        # fault 3: wrong mask (rebuilt rule fails)
        mini = build_mini('wrong_mask')
        bp = os.path.join(mini, 'analysis', 'bank', 'v092_bank_D60_zf550_M400_a10.mat')
        m = loadmat(bp)
        m['valid_mask'] = (np.asarray(m['valid_mask']).astype(bool) ^ True).astype('uint8')
        savemat(bp, m)
        r3 = evaluate(mini, os.path.join(mini, 'snapshot'), os.path.join(mini, 'review_inputs'))
        negatives.append({'fault': 'wrong_mask', 'gate': r3['gate'], 'detected': not r3['gate'],
                          'issues': r3['issues'][:3]})
        # fault 4: wrong dtype
        mini = build_mini('wrong_dtype')
        bp = os.path.join(mini, 'analysis', 'bank', 'v092_bank_D100_zf450_M200_a5.mat')
        m = loadmat(bp)
        m['X'] = np.asarray(m['X']).astype(np.complex64)
        savemat(bp, m)
        r4 = evaluate(mini, os.path.join(mini, 'snapshot'), os.path.join(mini, 'review_inputs'))
        negatives.append({'fault': 'wrong_dtype', 'gate': r4['gate'], 'detected': not r4['gate'],
                          'issues': r4['issues'][:3]})
        # fault 5: wrong case identity
        mini = build_mini('wrong_case')
        bp = os.path.join(mini, 'analysis', 'bank', 'v092_bank_D30_zf550_M200_a5.mat')
        m = loadmat(bp)
        m['case_id'] = 'WRONG_CASE'
        savemat(bp, m)
        r5 = evaluate(mini, os.path.join(mini, 'snapshot'), os.path.join(mini, 'review_inputs'))
        negatives.append({'fault': 'wrong_case', 'gate': r5['gate'], 'detected': not r5['gate'],
                          'issues': r5['issues'][:3]})
        shutil.rmtree(nc_dir, ignore_errors=True)
    out = {'gate': res['gate'], 'issues': res['issues'][:60],
           'checks': res['checks'], 'negative_controls': negatives,
           'negatives_all_detected': all(n['detected'] for n in negatives) if negatives else None}
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2)
    print('SOURCE_ACCEPTANCE gate=%s issues=%d negatives=%s'
          % (res['gate'], len(res['issues']),
             'ALL_DETECTED' if negatives and out['negatives_all_detected'] else
             ('NONE' if not negatives else 'MISSED')))
    return 0 if (res['gate'] and (not negatives or out['negatives_all_detected'])) else 2

if __name__ == '__main__':
    sys.exit(main())
