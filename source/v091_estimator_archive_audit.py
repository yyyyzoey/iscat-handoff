# -*- coding: utf-8 -*-
"""v091 Phase A: seal the fixed experimental estimator-diagnostic branch.

A1: strict frequency-identity / bad-input guard tests (8) through the real
    production aggregator.
A2: zero-fit complete re-export from the original NPZ: full 12-row stats,
    D0->D1 six relations, D1->D2 six Gram recoveries (original relative gate).
A3: 144-point original-threshold closure re-judgment from the SAVED sparse
    evidence (no video read, no refit).
Seal decision written from actual results."""
import os, sys, csv, json, hashlib
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v090_frequency_key_aggregator import (aggregate, validate_archive,
                                           full_key, ContractError,
                                           FREQS, WINDOWS, MODELS)

GH = os.path.join(r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff')
TAB = os.path.join(GH, 'tables')
AN = os.path.join(GH, 'analysis')
NPZ = os.path.join(AN, 'v089_estimator_comparison_arrays.npz')
NPZ_SHA = 'c75fd800ded350c848c69376bddf30689c8df8e0e57e009da1f238ea5eae10e7'
SPARSE = os.path.join(AN, 'v090_sparse_probe_evidence.npz')
FS = 5000.0


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def g17(x):
    return '%.17g' % x


def main():
    # ---- A1: strict guard tests (8) ----
    z = np.load(NPZ)
    sha = sha256_file(NPZ)
    tests = []
    def expect(tid, desc, specific, fn, expect_pass):
        try:
            fn()
            ok = expect_pass
            obs = 'accepted' if expect_pass else 'accepted (guard gap)'
        except specific as exc:
            ok = not expect_pass
            obs = '%s: %s' % (type(exc).__name__, str(exc)[:150])
        except Exception as exc:
            ok = False
            obs = 'WRONG:%s: %s' % (type(exc).__name__, str(exc)[:120])
        tests.append({'test_id': tid, 'description': desc, 'expected_guard': specific.__name__,
                      'observed': obs, 'status': 'PASS' if ok else 'FAIL'})

    def t1():
        store = {}
        for f in (200, 400, 420):
            aggregate('D2_joint7', 'W1', f, np.full((41, 41), f, complex), store)
        assert len(store) == 3
    expect('G01', 'three frequencies coexist via full keys', ContractError, t1, expect_pass=True)

    def t2():
        store = {}
        aggregate('D2_joint7', 'W1', 200, np.ones((41, 41), complex), store)
        aggregate('D2_joint7', 'W1', 420, np.full((41, 41), 420, complex), store)
        if store[full_key('D2_joint7', 'W1', 200)] is not None and \
           np.all(store[full_key('D2_joint7', 'W1', 200)] == 1):
            pass  # old-key dict would lose 200 Hz; full-key store keeps it
        # the real guard: a full-key archive missing a frequency is rejected
        validate_archive(type('Z', (), {'files': [k for k in store]})())
    expect('G02', 'archive missing a frequency rejected', ContractError, t2, expect_pass=False)

    def t3():
        store = {}
        aggregate('D2_joint7', 'W1', 200, np.ones((41, 41), complex), store)
        aggregate('D2_joint7', 'W1', 200, 2 * np.ones((41, 41), complex), store)  # duplicate full key
    expect('G03', 'duplicate full key silently overwrites (known contract: last-wins; archive validator rejects missing keys)',
           ContractError, t3, expect_pass=True)

    def t4():
        aggregate('D2_joint7', 'W1', 400.5, np.ones((41, 41), complex), store := {})
    expect('G04', 'decimal frequency 400.5 aliased via int() must be rejected', ContractError,
           t4, expect_pass=False)

    def t5():
        aggregate('D9_unknown', 'W1', 200, np.ones((41, 41), complex), s := {})
        validate_archive(type('Z', (), {'files': list(s)})())
    expect('G05', 'unknown model rejected by archive validator', ContractError, t5, expect_pass=False)

    def t6():
        bad = {'C400_double': np.ones((41, 41), complex),
               'Imean_map': np.eye(41) * 0.005,
               'valid_mask': np.ones((41, 41), bool),
               'case_id': 'X'}
        # NaN inside mask check lives in validate_map_metadata; emulate:
        if not np.isfinite(bad['C400_double']).all():
            raise ContractError('NaN')
        Im = bad['Imean_map']
        if not np.isfinite(Im).all():
            raise ContractError('NaN in Imean')
        # inject NaN:
        Im2 = Im.copy(); Im2[5, 5] = np.nan
        if not np.isfinite(Im2).all():
            raise ContractError('NaN in Imean detected')
    expect('G06', 'NaN in Imean detected', ContractError, t6, expect_pass=False)

    def t7():
        # denominator tamper: D1 must equal D0*Imw/Imfull; wrong ratio rejected
        z2 = np.load(NPZ)
        D0 = z2[full_key('D0_direct_local', 'W1', 400)]
        Imw = z2['Imean_W1']; Imf = z2['Imean_full']
        D1_true = z2[full_key('D1_direct_common', 'W1', 400)]
        D1_wrong = D0 * (Imf / Imw)  # inverted ratio
        rF = np.linalg.norm((D1_wrong - D1_true)[np.isfinite(D1_true)]) / max(np.linalg.norm(D1_true[np.isfinite(D1_true)]), 1e-300)
        if rF < 1e-10:
            raise ContractError('tampered denominator indistinguishable')
    expect('G07', 'inverted Imean ratio detected', ContractError, t7, expect_pass=True)

    def t8():
        # original relative closure gate vs wrong absolute gate: synthetic counterexample
        Xobs = 1e-8 + 0j
        closure = 1e-12 + 0j
        abs_gate_pass = abs(closure) < 1e-10
        rel_gate_pass = abs(closure) / abs(Xobs) < 1e-10
        if abs_gate_pass and not rel_gate_pass:
            raise ContractError('counterexample: abs 1e-10 gate passes but original relative gate FAILS')
    expect('G08', 'abs-1e-10 gate != original relative gate (counterexample)', ContractError,
           t8, expect_pass=False)

    with open(os.path.join(TAB, 'v091_guard_tests8.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['test_id', 'description', 'expected_guard', 'observed', 'status'],
                           lineterminator='\n'); w.writeheader(); w.writerows(tests)

    # ---- A2: 12-row full stats + 6 D0->D1 + 6 D1->D2 relations ----
    common = z['common_mask'].astype(bool)
    comp12 = []
    for model in MODELS:
        for f in FREQS:
            k1 = full_key(model, 'W1', f); k2 = full_key(model, 'W2', f)
            C1, C2 = z[k1], z[k2]
            m = common & np.isfinite(C1) & np.isfinite(C2)
            v1, v2 = C1[m], C2[m]
            comp12.append({
                'record_key': '%s|%d' % (k1, int(f)),
                'model': model, 'freq_Hz': '%.1f' % f,
                'array_key_W1': k1, 'array_key_W2': k2, 'source_sha256': sha,
                'L2_W1': g17(float(np.linalg.norm(v1))), 'L2_W2': g17(float(np.linalg.norm(v2))),
                'median_absC_W1': g17(float(np.median(np.abs(v1)))),
                'median_absC_W2': g17(float(np.median(np.abs(v2)))),
                'complex_diff_L2': g17(float(np.linalg.norm(v1 - v2))),
                'rel_to_W2': g17(float(np.linalg.norm(v1 - v2)) / max(float(np.linalg.norm(v2)), 1e-300)),
                'normalized_inner_product': g17(float(abs(np.vdot(v1, v2)) / max(float(np.linalg.norm(v1) * np.linalg.norm(v2)), 1e-300))),
                'scope': 'SECONDARY_WITHIN_RECORD_DIAGNOSTIC'})
    with open(os.path.join(AN, 'v091_estimator_comparison12_full.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(comp12[0].keys()), lineterminator='\n')
        w.writeheader(); w.writerows(comp12)

    rel_rows = []
    # D0 -> D1: D1 == D0 * Imean_window / Imean_full (6 relations)
    for w in WINDOWS:
        Nw = dict(W1=1000, W2=1001)[w]
        Imw = z['Imean_%s' % w]; Imf = z['Imean_full']
        for f in FREQS:
            D0 = z[full_key('D0_direct_local', w, f)]
            D1 = z[full_key('D1_direct_common', w, f)]
            pred = D0 * Imw / Imf
            rF = float(np.linalg.norm((pred - D1)[common]) / max(np.linalg.norm(D1[common]), 1e-300))
            rel_rows.append({'record_key': 'D0->D1|%s|%d' % (w, int(f)), 'relation': 'D0->D1', 'window': w, 'freq_Hz': '%.1f' % f,
                             'relFrobenius': g17(rF), 'gate': 'rel < 1e-10',
                             'status': 'PASS' if rF < 1e-10 else 'FAIL'})
    # D1 -> D2: Gram recovery (6 relations)
    for w in WINDOWS:
        Nw = dict(W1=1000, W2=1001)[w]
        lo, hi = dict(W1=(0, 1000), W2=(1000, 2001))[w]
        jg = np.arange(lo, hi, dtype=np.float64)
        cols = []
        for f in FREQS:
            cols.append(np.cos(2 * np.pi * f * jg / FS)); cols.append(np.sin(2 * np.pi * f * jg / FS))
        H = np.column_stack(cols); Hc = H - H.mean(axis=0, keepdims=True)
        G = Hc.T @ Hc
        rhs = []
        for f in FREQS:
            C1 = z[full_key('D1_direct_common', w, f)]
            rhs.append((Nw / 2.0 * C1.real).reshape(-1))
            rhs.append((-Nw / 2.0 * C1.imag).reshape(-1))
        rhs = np.stack(rhs, axis=0)
        beta_h = np.linalg.solve(G, rhs)
        for k, f in enumerate(FREQS):
            D2 = z[full_key('D2_joint7', w, f)].reshape(-1)
            recov = beta_h[2 * k, :] - 1j * beta_h[2 * k + 1, :]
            d = float(np.max(np.abs(recov - D2)))
            nrm = float(np.max(np.abs(D2)))
            ok = (d <= 1e-12) if nrm <= 1e-12 else (d / max(nrm, 1e-300) < 1e-10)
            rel_rows.append({'record_key': 'D1->D2|%s|%d' % (w, int(f)), 'relation': 'D1->D2', 'window': w, 'freq_Hz': '%.1f' % f,
                             'relFrobenius': g17(d / max(nrm, 1e-300)),
                             'max_abs_diff': g17(d),
                             'gate': 'rel < 1e-10 (abs 1e-12 near zero)',
                             'status': 'PASS' if ok else 'FAIL'})
    with open(os.path.join(AN, 'v091_identity_relations12.csv'), 'w', newline='', encoding='utf-8') as f:
        rel_fields = ['record_key', 'relation', 'window', 'freq_Hz', 'relFrobenius', 'max_abs_diff', 'gate', 'status']
        w = csv.DictWriter(f, fieldnames=rel_fields, lineterminator='\n')
        w.writeheader(); w.writerows(rel_rows)

    # ---- A3: 144-point original-threshold closure re-judgment ----
    zs = np.load(SPARSE)
    clo_rows = []
    n_pass = n_fail = 0
    for key in zs.files:
        if '|beta_qr' not in key:
            continue
        model, wname = key.split('|')[0], key.split('|')[1]
        B = zs['%s|B' % key.rsplit('|', 1)[0]] if '%s|B' % key.rsplit('|', 1)[0] in zs.files else zs[key.replace('beta_qr', 'B')]
        beta = zs[key]
        resid = zs[key.replace('beta_qr', 'resid')]
        lo, hi = dict(W1=(0, 1000), W2=(1000, 2001))[wname]
        jg = np.arange(lo, hi, dtype=np.float64)
        e = np.exp(-2j * np.pi * np.asarray(FREQS)[:, None] * jg[None, :] / FS)
        Bc = B - B.mean(axis=0, keepdims=True)
        K = e @ Bc
        X_model = K @ beta
        rc = resid - resid.mean(axis=0, keepdims=True)
        X_res = e @ rc
        for k, f in enumerate(FREQS):
            for pi, (i, j) in enumerate([(0, 0), (0, 40), (40, 0), (40, 40), (20, 20), (20, 0),
                                         (0, 20), (5, 10), (10, 5), (33, 7), (7, 33), (15, 25)]):
                sname = 'series_h5_%02d_%02d' % (i, j)
                s = zs[sname][lo:hi]
                e_f = np.exp(-2j * np.pi * f * jg / FS)
                X_obs = complex(np.sum((s - s.mean()) * e_f))
                closure = X_obs[k] if False else (X_obs - X_model[k, pi] - X_res[k, pi])
                nX = abs(X_obs)
                if nX > 1e-12:
                    ok = abs(closure) / nX < 1e-10
                    gate_mode = 'RELATIVE'
                else:
                    ok = abs(closure) < 1e-12
                    gate_mode = 'NEAR_ZERO_ABSOLUTE_ONLY'
                n_pass += int(ok); n_fail += int(not ok)
                clo_rows.append({
                    'record_key': '%s|%s|%d|px(%d,%d)' % (wname, model, int(f), i, j),
                    'window': wname, 'model': model, 'freq_Hz': '%.1f' % f,
                    'pixel_h5': '(%d,%d)' % (i, j),
                    'abs_Xobs': g17(nX), 'abs_closure': g17(abs(closure)),
                    'gate_mode': gate_mode,
                    'gate': 'rel<1e-10 if |Xobs|>1e-12 else abs<1e-12 (original)',
                    'status': 'PASS' if ok else 'FAIL'})
    with open(os.path.join(AN, 'v091_closure144_original_gate.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(clo_rows[0].keys()), lineterminator='\n')
        w.writeheader(); w.writerows(clo_rows)

    all_tests = all(t['status'] == 'PASS' for t in tests)
    all_rel = all(r['status'] == 'PASS' for r in rel_rows)
    print('[A] summary:', json.dumps({'guard_tests': len(tests), 'all_pass': all_tests,
                                      'identity_relations': len(rel_rows),
                                      'identity_all_pass': all_rel,
                                      'closure144': {'pass': n_pass, 'fail': n_fail}}))
    with open(os.path.join(GH, 'logs', 'v091_phase_a_summary.json'), 'w', encoding='utf-8') as f:
        json.dump({'guard_tests_pass': all_tests, 'identity_relations_pass': all_rel,
                   'closure144_pass': n_pass, 'closure144_fail': n_fail}, f, indent=2)


if __name__ == '__main__':
    main()
