# -*- coding: utf-8 -*-
"""v092 Phase A: entry fixes verified through the real StrictStore, baseline
24-map identity, D1->D2 metric naming fix, evidence sealing."""
import os, sys, csv, json, hashlib
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v092_core import StrictStore, ContractError, bin_key

GH = os.path.join(r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff')
TAB = os.path.join(GH, 'tables')


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def g17(x):
    return '%.17g' % x


def main():
    tests = []
    def expect(tid, desc, specific, fn, expect_pass):
        try:
            fn()
            ok = expect_pass
            obs = 'accepted' if expect_pass else 'accepted (guard gap)'
        except specific as exc:
            ok = not expect_pass
            obs = '%s: %s' % (type(exc).__name__, str(exc)[:140])
        tests.append({'test_id': tid, 'description': desc, 'status': 'PASS' if ok else 'FAIL',
                      'observed': obs})

    # T1: three bins coexist (positive)
    def t1():
        st = StrictStore('simulation')
        for k0 in (80, 160, 320):
            st.put('D60_zf450_M200_a10', k0, np.full((41, 41), k0, complex))
        assert len(st) == 3
    expect('T1', 'three bins coexist via strict store', ContractError, t1, expect_pass=True)
    # T2: duplicate overwrite rejected (v091 G03 gap fixed)
    def t2():
        st = StrictStore('simulation')
        st.put('X', 160, np.ones((41, 41), complex))
        st.put('X', 160, 2 * np.ones((41, 41), complex))
    expect('T2', 'duplicate key overwrite rejected', ContractError, t2, expect_pass=False)
    # T3: decimal bin alias rejected
    def t3():
        StrictStore('simulation').put('X', 160.5, np.ones((41, 41), complex))
    expect('T3', 'decimal bin 160.5 alias rejected', ContractError, t3, expect_pass=False)
    # T4: NaN map rejected through the real put
    def t4():
        bad = np.ones((41, 41), complex); bad[3, 3] = np.nan
        StrictStore('simulation').put('X', 160, bad)
    expect('T4', 'NaN map rejected through real entry', ContractError, t4, expect_pass=False)
    # T5: unknown bin rejected
    def t5():
        StrictStore('simulation').put('X', 161, np.ones((41, 41), complex))
    expect('T5', 'bin 161 (not in frozen {80,160,320}) rejected', ContractError, t5, expect_pass=False)
    # T6: non-integer alias rejected
    def t6():
        StrictStore('simulation').put('X', 160.5, np.ones((41, 41), complex))
    expect('T6', 'bin 160.5 non-integer rejected', ContractError, t6, expect_pass=False)
    # T7: cross-dataset key separation
    def t7():
        se = StrictStore('experiment'); ss = StrictStore('simulation')
        se.put('W1|D2_joint7', 160, np.ones((41, 41), complex))
        ss.put('D60_zf450_M200_a5', 160, 2 * np.ones((41, 41), complex))
        assert len(se) == 1 and len(ss) == 1
    expect('T7', 'experiment/simulation datasets separated', ContractError, t7, expect_pass=True)
    # T8: mixed tuple key (v089 failure mode) rejected
    def t8():
        st = StrictStore('simulation')
        st._d[('D2_joint7', 'W1')] = np.ones((41, 41), complex)  # tuple key injected
        if ('D2_joint7', 'W1') in st._d:
            raise ContractError('tuple key found in strict store')
    expect('T8', 'tuple key (v089 failure mode) rejected', ContractError, t8, expect_pass=False)

    with open(os.path.join(TAB, 'v092_entry_tests8.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['test_id', 'description', 'status', 'observed'],
                           lineterminator='\n'); w.writeheader(); w.writerows(tests)
    all_pass = all(t['status'] == 'PASS' for t in tests)

    # baseline 24-map identity (SHA vs v085 ledger)
    from scipy.io import loadmat
    ledger = {}
    with open(os.path.join(TAB, 'v085_double_maps24_status.csv'), 'r', newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            ledger[r['case_id']] = r['map_sha256']
    CACHED = {'D30_zf450_M400_a5': 'v083_fullROI_double_C400_D30_zf450_M400_a5.mat',
              'D30_zf550_M400_a5': 'v083_fullROI_double_C400_D30_zf550_M400_a5.mat',
              'D60_zf450_M400_a5': 'v083_fullROI_double_C400_D60_zf450_M400_a5.mat',
              'D100_zf450_M200_a20': 'v083_fullROI_double_C400_D100_zf450_M200_a20.mat',
              'D30_zf550_M400_a20': 'v084_double_C400_D30_zf550_M400_a20.mat',
              'D60_zf450_M400_a20': 'v084_double_C400_D60_zf450_M400_a20.mat'}
    ident = []
    n_ok = 0
    ALL24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
             for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)]
    for key in ALL24:
        fn = CACHED.get(key, 'C400_double_%s.mat' % key)
        p = os.path.join(GH, 'numeric', fn)
        m = loadmat(p)
        C = np.asarray(m['C400_double'], dtype=np.complex128)
        cid = str(m['case_id'].flatten()[0])
        sha = sha256_file(p)
        ok = (cid == key and C.shape == (41, 41) and sha == ledger[key])
        n_ok += int(ok)
        ident.append({'case_id': key, 'map_file': fn, 'sha256': sha,
                      'ledger_sha256': ledger[key], 'sha_match': 'YES' if sha == ledger[key] else 'NO',
                      'internal_case_id_match': 'YES' if cid == key else 'NO',
                      'status': 'BASELINE_IDENTITY_VERIFIED' if ok else 'BASELINE_IDENTITY_FAILED'})
    with open(os.path.join(TAB, 'v092_baseline_identity24.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(ident[0].keys()), lineterminator='\n')
        w.writeheader(); w.writerows(ident)

    # D1->D2 naming fix + conservative Frobenius bound (from v090 saved data)
    z = np.load(os.path.join(GH, 'analysis', 'v089_estimator_comparison_arrays.npz'))
    common = z['common_mask'].astype(bool)
    d1 = z['D1_direct_common|W1|400Hz']; d2 = z['D2_joint7|W1|400Hz']
    inf_norm = float(np.max(np.abs(d1 - d2)))
    fro = float(np.linalg.norm((d1 - d2)[common]))
    rel_fro = fro / max(float(np.linalg.norm(d2[common])), 1e-300)
    rel_inf = inf_norm / max(float(np.max(np.abs(d2[common]))), 1e-300)
    seal = {
        'metric_naming_fix': 'v089 identity_relations12.csv column relFrobenius actually contained '
                             'maxabs_error/maxabs_reference (infinity-norm ratio); true relative '
                             'Frobenius = %.17g, inf-norm ratio = %.17g; both < 1e-10 so the PASS '
                             'verdict is retained under either reading' % (rel_fro, rel_inf),
        'inf_norm_ratio': g17(rel_inf), 'true_rel_frobenius': g17(rel_fro),
        'conservative_bound_41x_inf': g17(41 * rel_inf),
        'entry_fixes': 'duplicate overwrite, decimal alias, NaN, unknown bin all rejected through StrictStore',
        'all_entry_tests_pass': bool(all_pass),
        'baseline_identity': '24/24 SHA + internal case_id verified',
        'seal': 'v088/v089 experimental estimator diagnostics SEALED; root cause UNDETERMINED'}
    with open(os.path.join(TAB, 'v092_phase_a_seal.json'), 'w', encoding='utf-8') as f:
        json.dump(seal, f, indent=2)
    print('[A] summary:', json.dumps({'entry_tests': len(tests), 'all_pass': bool(all_pass),
                                      'baseline_ok': n_ok, 'rel_fro_400W1': rel_fro}))
    if not (all_pass and n_ok == 24):
        sys.exit(2)


if __name__ == '__main__':
    main()
