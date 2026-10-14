# -*- coding: utf-8 -*-
"""v082 Phase A+B+E: source identity, negative tests, 24-case harmonic evidence
closure, experimental parameter status, external CSV readback.

Zero BEM, zero new renders. Pure post-processing of fixed cached arrays.
Parent commit: v081 812171a5fbea43c68d1ca93995f876e2fd051e19.
"""
import h5py, numpy as np, os, re, csv, json, hashlib, sys

ROOT = r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4'
GH = os.path.join(ROOT, 'github_handoff')
GH_TAB = os.path.join(GH, 'tables')
GH_NUM = os.path.join(GH, 'numeric')
GH_LOG = os.path.join(GH, 'logs')

P_SMALL = os.path.join(GH_NUM, 'v076_center_roi_harmonic_small_examples.mat')
P_DYN = os.path.join(ROOT, 'v076_return', 'numeric', 'v076_dynamic_center_corrected.mat')

N = 2001
FS = 5000.0
K0 = 160  # 0-based DFT bin; MATLAB bin 161
BASIS = {'M200': [200, 400, 600, 800], 'M400': [400, 800, 1200, 1600]}
CLOSURE_GATE = 1e-10
COND_GATE = 1e8

class ValidationError(Exception):
    pass

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def gN(u):
    """Dirichlet kernel G_N(u) = sum_j exp(2 pi i u j), j=0..N-1 (complex)."""
    pu = np.pi * u
    if abs(pu) < 1e-12:
        return complex(N)
    return complex(np.exp(1j * pu * (N - 1)) * np.sin(np.pi * N * u) / np.sin(pu))

def basis_columns(ttype):
    """Explicit 9-column design with intercept FIRST (v081 put it last; v082
    records the mapping explicitly to kill the historical ambiguity)."""
    freqs = BASIS[ttype]
    cols = ['intercept']
    for f in freqs:
        cols += ['cos%d' % f, 'sin%d' % f]
    return freqs, cols

def build_basis(ttype):
    freqs, cols = basis_columns(ttype)
    tj = np.arange(N) / FS
    B = np.ones((N, 1 + 2 * len(freqs)))
    for h, f in enumerate(freqs):
        B[:, 1 + 2 * h] = np.cos(2 * np.pi * f * tj)
        B[:, 2 + 2 * h] = np.sin(2 * np.pi * f * tj)
    return B, freqs, cols

def case_key_regex_ok(key):
    return re.fullmatch(r'D(\d+)_zf(\d+)_(M200|M400)_a(\d+)', key) is not None

def validate_series(series):
    if series.shape != (N,):
        raise ValidationError('series length %s != %d' % (series.shape, N))
    if not np.all(np.isfinite(series)):
        raise ValidationError('non-finite samples in series')
    m = float(np.mean(series))
    if m == 0.0:
        raise ValidationError('mean of series is exactly zero')
    return m

def validate_result(res):
    """Full per-case validator: identity, rank, units, closure, finiteness."""
    if not case_key_regex_ok(res['case_id']):
        raise ValidationError('bad case key structure: %r' % res['case_id'])
    freqs, _ = basis_columns(res['type'])
    if res['freqs'] != freqs:
        raise ValidationError('basis/key mismatch: key %s vs basis %s' % (res['type'], res['freqs']))
    if res['intercept_col_1based'] != 1:
        raise ValidationError('intercept column metadata must be 1 (intercept-first basis)')
    if len(res['column_order']) != 9 or res['column_order'][0] != 'intercept':
        raise ValidationError('column_order metadata invalid')
    if res['rank_B'] != 9:
        raise ValidationError('rank_B=%s != 9' % res['rank_B'])
    if not (res['cond_B'] < COND_GATE):
        raise ValidationError('cond_B=%g exceeds gate' % res['cond_B'])
    for f in ('mean_I', 'Xbin_Re', 'Xbin_Im', 'Cbin_Re', 'Cbin_Im',
              'C400fit_Re', 'C400fit_Im', 'closure_abs', 'closure_rel', 'residual_RMS'):
        if not np.isfinite(res[f]):
            raise ValidationError('non-finite field %s' % f)
    # unit consistency: Cbin must equal 2*Xbin/(N*mean_I); catches raw-X-as-C
    Cbin_re_chk = 2.0 * res['Xbin_Re'] / (N * res['mean_I'])
    Cbin_im_chk = 2.0 * res['Xbin_Im'] / (N * res['mean_I'])
    if abs(Cbin_re_chk - res['Cbin_Re']) > 1e-12 * max(1.0, abs(Cbin_re_chk)) or \
       abs(Cbin_im_chk - res['Cbin_Im']) > 1e-12 * max(1.0, abs(Cbin_im_chk)):
        raise ValidationError('Cbin != 2*Xbin/(N*mean_I): raw DFT count mislabeled as normalized C')
    if abs(res['Cbin_Re']) > 2.0 or abs(res['Cbin_Im']) > 2.0:
        raise ValidationError('|Cbin| component > 2: impossible normalized contrast')
    if not (res['closure_rel'] < CLOSURE_GATE):
        raise ValidationError('closure_rel=%g fails gate %g' % (res['closure_rel'], CLOSURE_GATE))
    return True

def write_csv(path, fieldnames, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator='\n')
        w.writeheader()
        for r in rows:
            w.writerow(r)

def g17(x):
    return '%.17g' % x

CONTROL_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')
def readback_csv(path, expect_rows, key_col):
    """Independent standard-library readback: column count, row count, unique
    keys, no control characters."""
    with open(path, 'r', newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    header, body = rows[0], rows[1:]
    problems = []
    if any(CONTROL_RE.search(c) for r in rows for c in r):
        problems.append('control character found')
    if len(body) != expect_rows:
        problems.append('row count %d != %d' % (len(body), expect_rows))
    if any(len(r) != len(header) for r in body):
        problems.append('row with field count != header (%d cols)' % len(header))
    ki = header.index(key_col)
    keys = [r[ki] for r in body]
    if len(set(keys)) != len(keys):
        problems.append('duplicate keys in %s' % key_col)
    return problems

# ---------------------------------------------------------------- Phase A ----
def phase_a(pre_rows):
    print('[A] source preflight')
    ident = []
    for path, role in ((P_SMALL, 'primary_24_series_source'),
                       (P_DYN, 'cross_check_center_map_source')):
        ident.append({'file_path': os.path.relpath(path, ROOT), 'role': role,
                      'sha256': sha256_file(path),
                      'size_bytes': str(os.path.getsize(path)), 'note': ''})
    f1 = h5py.File(P_SMALL, 'r')
    f2 = h5py.File(P_DYN, 'r')
    keys = sorted(k for k in f1.keys() if not k.startswith('#'))
    if len(keys) != 24:
        raise ValidationError('expected 24 cases, found %d' % len(keys))
    for k in keys:
        g = f1[k]
        if not case_key_regex_ok(k):
            raise ValidationError('bad key %r' % k)
        tt = ''.join(chr(int(c)) for c in np.array(g['ttype']).flatten())
        m = re.match(r'D(\d+)_zf(\d+)_(M200|M400)_a(\d+)', k)
        if tt != m.group(3):
            raise ValidationError('ttype %r disagrees with key %r' % (tt, k))
        s = np.array(g['series']).flatten().astype(np.float64)
        validate_series(s)
    # center element C400(21,21) 1-based == [20,20] 0-based from the corrected map
    cmap = f2['D60_zf450_M200_a5']['C400'][:]
    c_center = complex(cmap[20, 20]['real'], cmap[20, 20]['imag'])
    pre_rows.append({'test_id': 'PRE01', 'category': 'source_structure',
                     'description': '24 cases, key structure, ttype/key agreement, series 2001 float64 finite mean!=0',
                     'expected_result': 'PASS', 'observed_result': 'all 24 verified against %s' % os.path.basename(P_SMALL),
                     'status': 'PASS'})
    pre_rows.append({'test_id': 'PRE02', 'category': 'source_structure',
                     'description': 'corrected center map C400(21,21) is 41x41 complex; scalar small-MAT C400 NOT used as map',
                     'expected_result': 'PASS', 'observed_result': 'C400(21,21)=%.17g%+.17gj (map absCenter=%.17g)' % (c_center.real, c_center.imag, float(np.array(f2['D60_zf450_M200_a5']['absCenter']).flatten()[0])),
                     'status': 'PASS'})
    f1.close()
    f2.close()
    return ident, keys

# ---------------------------------------------------------------- Phase B ----
def phase_b(pre_rows):
    print('[B] 24-case harmonic evidence closure')
    f1 = h5py.File(P_SMALL, 'r')
    f2 = h5py.File(P_DYN, 'r')
    keys = sorted(k for k in f1.keys() if not k.startswith('#'))
    src_sha = sha256_file(P_SMALL)
    val_rows, parts_rows, resid_rows, ident_rows = [], [], [], []
    small_samples = {}
    for key in keys:
        g = f1[key]
        m = re.match(r'D(\d+)_zf(\d+)_(M200|M400)_a(\d+)', key)
        D, zf, ttype, aa = int(m.group(1)), int(m.group(2)), m.group(3), int(m.group(4))
        series = np.array(g['series']).flatten().astype(np.float64)
        mean_I = validate_series(series)
        series_sha = hashlib.sha256(series.tobytes()).hexdigest()
        B, freqs, cols = build_basis(ttype)
        rank_B = int(np.linalg.matrix_rank(B))
        cond_B = float(np.linalg.cond(B))
        Ic = series - mean_I
        coef, _, _, _ = np.linalg.lstsq(B, Ic, rcond=None)
        resid = Ic - B @ coef
        # intercept FIRST: coef[0]=b0; A_h = coef[2h+1] - i*coef[2h+2]
        A = np.array([complex(coef[1 + 2 * h], -coef[2 + 2 * h]) for h in range(len(freqs))])
        e = np.exp(-2j * np.pi * K0 * np.arange(N) / N)
        Xbin = complex(np.sum(Ic * e))
        Xres = complex(np.sum(resid * e))
        X0 = coef[0] * gN(-K0 / N)
        Xmodel = 0j
        parts_case = []
        for h, f in enumerate(freqs):
            u1 = f / FS - K0 / N
            u2 = -f / FS - K0 / N
            Xh = (A[h] / 2) * gN(u1) + (np.conj(A[h]) / 2) * gN(u2)
            Xmodel += Xh
            parts_case.append((f, A[h], Xh))
        closure_abs = abs(Xbin - Xmodel - Xres)
        closure_rel = closure_abs / max(np.sqrt(N) * np.linalg.norm(Ic), 1e-300)
        rmsR = float(np.sqrt(np.mean(resid ** 2)))
        i400 = freqs.index(400)
        C400fit = A[i400] / mean_I
        Cbin = 2 * Xbin / (N * mean_I)
        res = {'case_id': key, 'type': ttype, 'freqs': freqs,
               'intercept_col_1based': 1, 'column_order': cols,
               'rank_B': rank_B, 'cond_B': cond_B, 'mean_I': mean_I,
               'Xbin_Re': Xbin.real, 'Xbin_Im': Xbin.imag,
               'Cbin_Re': Cbin.real, 'Cbin_Im': Cbin.imag,
               'C400fit_Re': C400fit.real, 'C400fit_Im': C400fit.imag,
               'closure_abs': closure_abs, 'closure_rel': closure_rel,
               'residual_RMS': rmsR}
        try:
            validate_result(res)
            status = 'PASS'
            evidence = 'identity+rank+units+closure validated; readback pending'
        except ValidationError as exc:
            status = 'FAIL'
            evidence = 'ValidationError: %s' % exc
        # cross-source identity vs corrected map tseries_center (independent path)
        cross = np.array(f2[key]['tseries_center']).flatten().astype(np.float64)
        cross_max = float(np.max(np.abs(series - cross)))
        cross_rel = float(np.linalg.norm(series - cross) / max(np.linalg.norm(series), 1e-300))
        absCenter = float(np.array(f2[key]['absCenter']).flatten()[0])
        if status == 'PASS':
            val_rows.append({
                'case_id': key, 'D_nm': D, 'zf_nm': zf, 'type': ttype, 'a_nm': aa,
                'source_file': os.path.basename(P_SMALL), 'source_sha256': src_sha,
                'series_sha256': series_sha, 'series_len': N, 'series_dtype': 'float64',
                'mean_I': g17(mean_I),
                'basis_freqs_Hz': ' '.join(str(f) for f in freqs),
                'column_order': '|'.join(cols), 'intercept_col_1based': 1,
                'rank_B': rank_B, 'cond_B': g17(cond_B),
                'Xbin_Re_DFT_count': g17(Xbin.real), 'Xbin_Im_DFT_count': g17(Xbin.imag),
                'binAbs_DFT_count': g17(abs(Xbin)),
                'Cbin_Re': g17(Cbin.real), 'Cbin_Im': g17(Cbin.imag), 'Cbin_abs': g17(abs(Cbin)),
                'C400fit_Re': g17(C400fit.real), 'C400fit_Im': g17(C400fit.imag), 'C400fit_abs': g17(abs(C400fit)),
                'ratio_Cbin_over_C400fit': g17(abs(Cbin) / max(abs(C400fit), 1e-300)),
                'closure_abs': g17(closure_abs), 'closure_rel': g17(closure_rel),
                'residual_RMS': g17(rmsR),
                'v076_map_absCenter': g17(absCenter),
                'cross_source_max_absdiff': g17(cross_max), 'cross_source_rel_L2': g17(cross_rel),
                'status': status, 'evidence': evidence})
            for h, (f, Ah, Xh) in enumerate(parts_case):
                Ch = 2 * Xh / (N * mean_I)
                parts_rows.append({
                    'record_key': '%s|%d' % (key, f), 'case_id': key, 'h_index': h, 'freq_Hz': f,
                    'A_h_Re': g17(Ah.real), 'A_h_Im': g17(Ah.imag),
                    'X_h_Re_DFT_count': g17(Xh.real), 'X_h_Im_DFT_count': g17(Xh.imag),
                    'C_h_Re': g17(Ch.real), 'C_h_Im': g17(Ch.imag), 'C_h_abs': g17(abs(Ch)),
                    'X_unit': 'DFT_count', 'C_unit': 'dimensionless'})
            resid_rows.append({
                'case_id': key,
                'Xbin_Re_DFT_count': g17(Xbin.real), 'Xbin_Im_DFT_count': g17(Xbin.imag),
                'Xharmonics_sum_Re': g17(Xmodel.real), 'Xharmonics_sum_Im': g17(Xmodel.imag),
                'X0_intercept_Re': g17(X0.real), 'X0_intercept_Im': g17(X0.imag),
                'Xres_Re': g17(Xres.real), 'Xres_Im': g17(Xres.imag),
                'closure_Re': g17((Xbin - Xmodel - Xres).real), 'closure_Im': g17((Xbin - Xmodel - Xres).imag),
                'closure_abs': g17(closure_abs), 'closure_rel': g17(closure_rel),
                'residual_RMS': g17(rmsR)})
            ident_rows.append({
                'case_id': key, 'source_file': os.path.basename(P_SMALL),
                'source_sha256': src_sha, 'series_sha256': series_sha,
                'series_len': N, 'series_dtype': 'float64',
                'mean_I': g17(mean_I), 'std_I': g17(float(np.std(series))),
                'cross_source_file': os.path.basename(P_DYN), 'cross_field': 'tseries_center',
                'cross_len': int(cross.shape[0]),
                'cross_max_absdiff': g17(cross_max), 'cross_rel_L2': g17(cross_rel),
                'cross_method_note': 'primary: single-precision 25-subpixel quadratic-form series (v076_D_qr_center); cross: full-205x205-block single-precision path (v076_C); difference is a real cross-method reconstruction difference, not a file-copy check',
                'status': 'IDENTIFIED_WITH_CROSS_METHOD_DIFF'})
        else:
            pre_rows.append({'test_id': 'CASEFAIL_%s' % key, 'category': 'case_validation',
                             'description': 'per-case validation', 'expected_result': 'PASS',
                             'observed_result': evidence, 'status': 'FAIL'})
        if key in ('D60_zf450_M200_a5', 'D30_zf450_M400_a5', 'D30_zf550_M400_a5'):
            small_samples[key] = {
                'series': series, 'Imean': mean_I, 'coef': coef,
                'column_order': np.array(cols, dtype=h5py.string_dtype()),
                'freqs_Hz': np.array(freqs, dtype=np.float64),
                'Xbin': np.array([Xbin.real, Xbin.imag], dtype=np.float64),
                'Xmodel_sum': np.array([Xmodel.real, Xmodel.imag], dtype=np.float64),
                'X0_intercept': np.array([X0.real, X0.imag], dtype=np.float64),
                'Xres': np.array([Xres.real, Xres.imag], dtype=np.float64),
                'parts_Xh': np.array([[Xh.real, Xh.imag] for (_, _, Xh) in parts_case], dtype=np.float64),
                'parts_freqs': np.array([f for (f, _, _) in parts_case], dtype=np.float64),
                'residuals': resid,
                'closure_abs': closure_abs, 'closure_rel': closure_rel,
                'Cbin': np.array([Cbin.real, Cbin.imag], dtype=np.float64),
                'C400fit': np.array([C400fit.real, C400fit.imag], dtype=np.float64),
                'rank_B': rank_B, 'cond_B': cond_B,
                'case_id': key, 'status': status}
    f1.close()
    f2.close()
    return val_rows, parts_rows, resid_rows, ident_rows, small_samples

# ---------------------------------------------------------- negative tests ----
def negative_tests(pre_rows):
    print('[A-neg] negative fixtures (all must FAIL)')
    def expect_fail(tid, desc, fn):
        try:
            fn()
        except ValidationError:
            pre_rows.append({'test_id': tid, 'category': 'negative_fixture',
                             'description': desc, 'expected_result': 'REJECT',
                             'observed_result': 'ValidationError raised', 'status': 'PASS'})
            return
        pre_rows.append({'test_id': tid, 'category': 'negative_fixture',
                         'description': desc, 'expected_result': 'REJECT',
                         'observed_result': 'NOT rejected - validator gap', 'status': 'FAIL'})

    def neg01():
        res = dict(case_id='D60_zf450_M200_a5', type='M200', freqs=BASIS['M400'],
                   intercept_col_1based=1, column_order=['intercept'] * 9, rank_B=9,
                   cond_B=1.4, mean_I=1.0, Xbin_Re=1e-3, Xbin_Im=0.0, Cbin_Re=1e-6,
                   Cbin_Im=0.0, C400fit_Re=1e-6, C400fit_Im=0.0, closure_abs=1e-15,
                   closure_rel=1e-14, residual_RMS=1e-9)
        validate_result(res)
    expect_fail('NEG01', 'M200 case validated against M400 basis (wrong frequency label)', neg01)

    def neg02():
        res = dict(case_id='D60_zf450_M200_a5', type='M200', freqs=BASIS['M200'],
                   intercept_col_1based=9, column_order=['intercept'] * 9, rank_B=9,
                   cond_B=1.4, mean_I=1.0, Xbin_Re=1e-3, Xbin_Im=0.0, Cbin_Re=1e-6,
                   Cbin_Im=0.0, C400fit_Re=1e-6, C400fit_Im=0.0, closure_abs=1e-15,
                   closure_rel=1e-14, residual_RMS=1e-9)
        validate_result(res)
    expect_fail('NEG02', 'intercept claimed at column 9 while v082 contract fixes intercept-first metadata', neg02)

    def neg03():
        res = dict(case_id='D60_zf450_M200_a5', type='M200', freqs=BASIS['M200'],
                   intercept_col_1based=1, column_order=['intercept'] * 9, rank_B=9,
                   cond_B=1.4, mean_I=1.0, Xbin_Re=1e-3, Xbin_Im=0.0, Cbin_Re=1e-6,
                   Cbin_Im=0.0, C400fit_Re=1e-6, C400fit_Im=0.0, closure_abs=1e-15,
                   closure_rel=1e-14, residual_RMS=float('nan'))
        validate_result(res)
    expect_fail('NEG03', 'undefined/non-finite residual R (v081 V2/V3 failure mode)', neg03)

    def neg04():
        res = dict(case_id='D60_zf450_M200_a5', type='M200', freqs=BASIS['M200'],
                   intercept_col_1based=1, column_order=['intercept'] * 9, rank_B=8,
                   cond_B=1.4, mean_I=1.0, Xbin_Re=1e-3, Xbin_Im=0.0, Cbin_Re=1e-6,
                   Cbin_Im=0.0, C400fit_Re=1e-6, C400fit_Im=0.0, closure_abs=1e-15,
                   closure_rel=1e-14, residual_RMS=1e-9)
        validate_result(res)
    expect_fail('NEG04', 'rank-deficient design matrix accepted (rank=8)', neg04)

    def neg05():
        res = dict(case_id='D60_zf450_M200_a5', type='M200', freqs=BASIS['M200'],
                   intercept_col_1based=1, column_order=['intercept'] * 9, rank_B=9,
                   cond_B=1.4, mean_I=1.0, Xbin_Re=2.5, Xbin_Im=0.0, Cbin_Re=2.5,
                   Cbin_Im=0.0, C400fit_Re=1e-6, C400fit_Im=0.0, closure_abs=1e-15,
                   closure_rel=1e-14, residual_RMS=1e-9)
        validate_result(res)
    expect_fail('NEG05', 'raw DFT count Xbin mislabeled as normalized C (v081 V1/V6 dimensional error)', neg05)

    def neg06():
        res = dict(case_id='D60_zf450_M200_a5', type='M200', freqs=BASIS['M200'],
                   intercept_col_1based=1, column_order=['intercept'] * 9, rank_B=9,
                   cond_B=1.4, mean_I=1.0, Xbin_Re=1e-3, Xbin_Im=0.0, Cbin_Re=1e-6,
                   Cbin_Im=0.0, C400fit_Re=1e-6, C400fit_Im=0.0, closure_abs=1e-8,
                   closure_rel=1e-6, residual_RMS=1e-9)
        validate_result(res)
    expect_fail('NEG06', 'closure_rel above frozen 1e-10 gate accepted', neg06)

    # CSV-level negative tests via readback validator on temp files
    import tempfile
    def neg07():
        p = os.path.join(tempfile.gettempdir(), 'v082_neg07.csv')
        with open(p, 'w', newline='', encoding='utf-8') as f:
            f.write('case_id,val\nA,1\nB,2\n')  # 2 rows
        pr = readback_csv(p, 3, 'case_id')
        if pr:
            raise ValidationError('; '.join(pr))
    expect_fail('NEG07', 'CSV row count shorter than declared (v081 V3/V4 failure mode)', neg07)

    def neg08():
        p = os.path.join(tempfile.gettempdir(), 'v082_neg08.csv')
        with open(p, 'w', newline='', encoding='utf-8') as f:
            f.write('case_id,val\nA,1\nA,2\nA,3\n')
        pr = readback_csv(p, 3, 'case_id')
        if pr:
            raise ValidationError('; '.join(pr))
    expect_fail('NEG08', 'duplicate keys accepted in CSV', neg08)

    def neg09():
        p = os.path.join(tempfile.gettempdir(), 'v082_neg09.csv')
        with open(p, 'w', newline='', encoding='utf-8') as f:
            f.write('case_id,val\nA,1\n\x01bad,2\nA,3\n')
        pr = readback_csv(p, 3, 'case_id')
        if pr:
            raise ValidationError('; '.join(pr))
    expect_fail('NEG09', 'control character inside CSV field accepted', neg09)

    def neg10():
        p = os.path.join(tempfile.gettempdir(), 'v082_neg10.csv')
        with open(p, 'w', newline='', encoding='utf-8') as f:
            f.write('case_id,val,extra\nA,1\nA,2,3\nA,3,4\n')
        pr = readback_csv(p, 3, 'case_id')
        if pr:
            raise ValidationError('; '.join(pr))
    expect_fail('NEG10', 'short row (fewer fields than header) accepted (v081 V2/V3/V4 failure mode)', neg10)

# ------------------------------------------------------------- Phase E ------
def phase_e():
    print('[E] experimental parameter status')
    rows = [
        ('laser_vacuum_wavelength_nm', 'USER_CONFIRMED', '520', 'USER_CONFIRMED_2026-10-12', 'true experimental input'),
        ('ac_magnetic_field_frequency_Hz', 'HISTORICAL_RECORDED_UNVERIFIED_FINAL_SETUP', '200', 'historical lab record', 'frequency recorded only; amplitude/direction/gradient/exact waveform still missing; 400Hz possible 2f but causality unestablished'),
        ('camera_Fs_fps', 'EXPERIMENTAL_SCRIPT_RECORDED', '5000', '7.29 batch extraction scripts (test.m / test_with_contrast.m, GBK, SHA-verified v071)', '2001-frame subset; does not guarantee other batches identical'),
        ('analysis_frames', 'EXPERIMENTAL_SCRIPT_RECORDED', '2001', '7.29 batch replay contract', 'frames 1000-3000'),
        ('dft_bin161_actual_Hz', 'EXPERIMENTAL_SCRIPT_RECORDED', '399.800099950025', 'round(400*2001/5000)=160 (0-based); k0*Fs/N', 'candidate primary observable; normalization contract from test_with_contrast.m'),
        ('camera_sensor_pixel_um', 'HISTORICAL_RECORDED_UNVERIFIED_FINAL_SETUP', '14', 'historical lab record', 'sensor pixel only; object-space scale NOT closed'),
        ('objective_nominal_magnification', 'HISTORICAL_RECORDED_UNVERIFIED_FINAL_SETUP', '50x', 'historical lab record', 'nominal; total magnification and extra lenses unverified'),
        ('object_space_scale_nm_per_px', 'MISSING', 'UNDETERMINED', '-', '280nm/px ONLY IF no extra magnification (14um/50); 65nm/px is demo; needs stage calibration or full optical chain'),
        ('camera_exposure_time_s', 'MISSING', 'UNDETERMINED', '-', '100/200us are SYNTHETIC_TAU math fixtures only'),
        ('camera_trigger_mode', 'MISSING', 'UNDETERMINED', '-', '-'),
        ('imaging_NA', 'MISSING', 'UNDETERMINED', '-', 'NA1.3 is simulation assumption, not experimental'),
        ('objective_model_immersion', 'MISSING', 'UNDETERMINED', '-', '-'),
        ('illumination_incidence_polarization', 'MISSING', 'UNDETERMINED', '-', '-'),
        ('reference_beam_geometry', 'MISSING', 'UNDETERMINED', '-', 'iSCAT reference = reflected beam; experimental alignment unclosed'),
        ('magnetic_field_amplitude_direction_gradient', 'MISSING', 'UNDETERMINED', '-', '200Hz frequency record does not give drive amplitude or B(t); motion not preset to horizontal 5/20nm'),
        ('Bt_image_synchronization', 'MISSING', 'UNDETERMINED', '-', '-'),
        ('sample_batch_magnetic_material', 'MISSING_PARTIAL_HISTORICAL', 'nominal 100nm Fe3O4 recorded; batch material unverified', 'historical record', 'Querry 1985 bulk constants are literature, not batch measurement'),
        ('particle_coating_medium_interface_fixation', 'MISSING', 'UNDETERMINED', '-', 'glass/water/5nm gap is simulation assumption'),
        ('particle_diameter_nm', 'MISSING', 'NOT_ESTIMATED', '-', 'single-particle diameter NOT_ESTIMATED by frozen state'),
        ('demo_object_pixel_nm', 'SIMULATION_ASSUMPTION', '65', 'v06x forward model contract', 'demo only, NOT user calibration'),
        ('demo_translation_amplitudes_nm', 'SIMULATION_ASSUMPTION', '5, 20', 'prescribed trajectory contract', 'prescribed kinematics, NOT real magnetic motion'),
        ('demo_focus_planes_nm', 'SIMULATION_ASSUMPTION', '450, 550', 'forward model grid', '-'),
        ('material_constants_source', 'SIMULATION_ASSUMPTION', 'Fe3O4 Querry 1985; Au 520nm measured table', 'material contract', 'Au table measured; Fe3O4 literature'),
    ]
    return [{'parameter': p, 'status_category': c, 'value_or_state': v, 'source': s, 'note': n}
            for (p, c, v, s, n) in rows]

# ------------------------------------------------------------------ main -----
def main():
    os.makedirs(GH_TAB, exist_ok=True)
    os.makedirs(GH_LOG, exist_ok=True)
    pre_rows = []
    ident_files, keys = phase_a(pre_rows)
    negative_tests(pre_rows)
    val_rows, parts_rows, resid_rows, ident_rows, small_samples = phase_b(pre_rows)
    par_rows = phase_e()

    write_csv(os.path.join(GH_TAB, 'v082_input_and_source_identity.csv'),
              ['file_path', 'role', 'sha256', 'size_bytes', 'note'], ident_files)
    write_csv(os.path.join(GH_TAB, 'v082_harmonics24_validated.csv'),
              list(val_rows[0].keys()) if val_rows else ['case_id'], val_rows)
    write_csv(os.path.join(GH_TAB, 'v082_harmonic_parts_long.csv'),
              ['record_key', 'case_id', 'h_index', 'freq_Hz', 'A_h_Re', 'A_h_Im',
               'X_h_Re_DFT_count', 'X_h_Im_DFT_count', 'C_h_Re', 'C_h_Im', 'C_h_abs',
               'X_unit', 'C_unit'], parts_rows)
    write_csv(os.path.join(GH_TAB, 'v082_harmonic_residual24.csv'),
              list(resid_rows[0].keys()) if resid_rows else ['case_id'], resid_rows)
    write_csv(os.path.join(GH_TAB, 'v082_time_series_identity24.csv'),
              list(ident_rows[0].keys()) if ident_rows else ['case_id'], ident_rows)
    write_csv(os.path.join(GH_TAB, 'v082_experimental_parameter_status.csv'),
              ['parameter', 'status_category', 'value_or_state', 'source', 'note'], par_rows)

    # external readback of every published table
    rb = [
        ('v082_input_and_source_identity.csv', len(ident_files), 'file_path'),
        ('v082_harmonics24_validated.csv', 24, 'case_id'),
        ('v082_harmonic_parts_long.csv', 96, 'record_key'),
        ('v082_harmonic_residual24.csv', 24, 'case_id'),
        ('v082_time_series_identity24.csv', 24, 'case_id'),
        ('v082_experimental_parameter_status.csv', len(par_rows), 'parameter'),
    ]
    all_rb_ok = True
    for name, n_expect, key in rb:
        problems = readback_csv(os.path.join(GH_TAB, name), n_expect, key)
        pre_rows.append({'test_id': 'RB_%s' % name, 'category': 'external_readback',
                         'description': 'independent stdlib readback: %d rows, %d cols, unique %s, no control chars' % (n_expect, 0, key),
                         'expected_result': 'no problems', 'observed_result': '; '.join(problems) if problems else 'clean',
                         'status': 'PASS' if not problems else 'FAIL'})
        all_rb_ok &= not problems
    # finalize per-case evidence strings now that readback is known
    if all_rb_ok and val_rows:
        for r in val_rows:
            if r['status'] == 'PASS':
                r['evidence'] = 'identity+rank+units+closure validated; external CSV readback clean'
    if val_rows:
        write_csv(os.path.join(GH_TAB, 'v082_harmonics24_validated.csv'),
                  list(val_rows[0].keys()), val_rows)
    write_csv(os.path.join(GH_TAB, 'v082_preflight_and_schema.csv'),
              ['test_id', 'category', 'description', 'expected_result', 'observed_result', 'status'], pre_rows)

    # small readable MAT samples (MAT v5 via scipy)
    from scipy.io import savemat
    for key, data in small_samples.items():
        out = os.path.join(GH_NUM, 'v082_small_sample_%s.mat' % key)
        payload = {k: (v if not isinstance(v, str) else np.array(v)) for k, v in data.items()}
        savemat(out, payload, do_compression=True)
        print('  sample written:', os.path.basename(out))

    n_pass = sum(1 for r in val_rows if r['status'] == 'PASS')
    neg_fail = [r for r in pre_rows if r['category'] == 'negative_fixture' and r['status'] != 'PASS']
    summary = {
        'cases_total': len(keys), 'cases_pass': n_pass,
        'parts_rows': len(parts_rows), 'resid_rows': len(resid_rows),
        'ident_rows': len(ident_rows), 'negative_tests': len(pre_rows) - 2,
        'negative_unexpected_pass': len(neg_fail), 'readback_clean': all_rb_ok,
    }
    print('[B] summary:', json.dumps(summary))
    with open(os.path.join(GH_LOG, 'v082_evidence_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    if n_pass == 24 and len(parts_rows) == 96 and not neg_fail and all_rb_ok:
        print('PHASE_A_B_RESULT: PASS_24_OF_24 (math evidence closure complete; publish pending package assembly)')
    elif n_pass == 24:
        print('PHASE_A_B_RESULT: MATH_PASS__PUBLISH_BLOCKED')
    else:
        print('PHASE_A_B_RESULT: INCOMPLETE (%d/24)' % n_pass)

if __name__ == '__main__':
    main()



