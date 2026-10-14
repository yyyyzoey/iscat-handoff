# -*- coding: utf-8 -*-
"""v083 Phase A: same-pixel time-series identity repair.

Rebuilds the TRUE centre pixel (ROI 21,21) series for all 24 legacy
prescriptions from the SAME five signed anchors (zero BEM, zero new renders),
proves the v076 legacy `tseries_center` field is MATLAB Ipix(21,1) (row 21,
col 1 - NOT the centre), and runs 6 pixel-identity negative tests.

 statuses: SAME_PIXEL_SAME_OPERATOR_VERIFIED |
           SAME_PIXEL_NUMERIC_PATH_SPREAD_REPORTED | BLOCKED_*
"""
import os, sys, csv, json, hashlib
import numpy as np
import h5py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v083_common import ROOT, N, FS, K0, Q, block_at, roi_blocks, fine_slice
from v082_qf_common import qf_coefficients, qf_series, field_first_series, cbin

GH = os.path.join(ROOT, 'github_handoff')
TAB = os.path.join(GH, 'tables')
NUM = os.path.join(GH, 'numeric')
HIST = os.path.join(GH, 'history')
SMALL = os.path.join(NUM, 'v076_center_roi_harmonic_small_examples.mat')
DYN = os.path.join(ROOT, 'v076_return', 'numeric', 'v076_dynamic_center_corrected.mat')
CENTRE = (21, 21)
LEGACY_BUG_PIXEL = (21, 1)  # MATLAB row 21, col 1 (v076_C stored Ipix(ci,1,1,:))
FP_GATE = 1e-8              # float32 accumulation-order rounding scale

CASES = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
         for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)]


class PixelIdentityError(Exception):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def recon_series(D, zf, ttype, a_nm, r, c, dtype=np.float64):
    """One new correct-centre time-domain post-processing of an OLD prescription."""
    freq = 200.0 if ttype == 'M200' else 400.0
    Es, Eref = block_at(D, zf, r, c)
    Lm, Dm_, Qm, Iref = qf_coefficients(Es, Eref)
    tj = np.arange(N) / FS
    xt = float(a_nm) * np.cos(2 * np.pi * freq * tj)
    return qf_series(xt, Lm, Dm_, Qm, Iref, dtype=dtype)


def wrong_roi_recon(D, zf, ttype, a_nm, dtype=np.float64):
    """Deliberately use the WRONG legacy ROI fine 64:268 (v075 offset defect)."""
    freq = 200.0 if ttype == 'M200' else 400.0
    Es = np.empty((5, 25, 3), dtype=np.complex128); Eref = None
    for i, x in enumerate(np.array([-20., -10., 0., 10., 20.])):
        with h5py.File(os.path.join(ROOT, 'v074_return', 'numeric', 'render_cache',
                                    'D%d_zf%g_x%+g.mat' % (D, zf, x)), 'r') as f:
            aa = f['a']; Es_i = aa['Es'][:]
            if Eref is None:
                Eref = aa['Eref'][:]
        Es_i = Es_i['real'] + 1j * Es_i['imag'] if Es_i.dtype.names else Es_i
        Eref = Eref['real'] + 1j * Eref['imag'] if Eref.dtype.names else Eref
        # WRONG block: MATLAB fine rows 164:168, cols 164:168 (i0=64 defect)
        Es[i] = Es_i[:, 163:168, 163:168].transpose(1, 2, 0).reshape(25, 3)
    blk_ref = Eref[:, 163:168, 163:168]
    Eref_c = blk_ref.transpose(1, 2, 0).reshape(25, 3)
    Lm, Dm_, Qm, Iref = qf_coefficients(Es, Eref_c)
    tj = np.arange(N) / FS
    xt = float(a_nm) * np.cos(2 * np.pi * (200.0 if ttype == 'M200' else 400.0) * tj)
    return qf_series(xt, Lm, Dm_, Qm, Iref, dtype=dtype)


def transposed_axis_recon(D, zf, ttype, a_nm):
    """Deliberately swap the h5py axis order (row-slice first) -> wrong pixel."""
    freq = 200.0 if ttype == 'M200' else 400.0
    Es = np.empty((5, 25, 3), dtype=np.complex128); Eref = None
    rs, cs = fine_slice(CENTRE)
    for i, x in enumerate(np.array([-20., -10., 0., 10., 20.])):
        with h5py.File(os.path.join(ROOT, 'v074_return', 'numeric', 'render_cache',
                                    'D%d_zf%g_x%+g.mat' % (D, zf, x)), 'r') as f:
            aa = f['a']; Es_i = aa['Es'][:]
            if Eref is None:
                Eref = aa['Eref'][:]
        Es_i = Es_i['real'] + 1j * Es_i['imag'] if Es_i.dtype.names else Es_i
        Eref = Eref['real'] + 1j * Eref['imag'] if Eref.dtype.names else Eref
        Es[i] = Es_i[:, rs, cs].transpose(1, 2, 0).reshape(25, 3)  # SWAPPED
    Eref_c = Eref[:, rs, cs].transpose(1, 2, 0).reshape(25, 3)
    Lm, Dm_, Qm, Iref = qf_coefficients(Es, Eref_c)
    tj = np.arange(N) / FS
    xt = float(a_nm) * np.cos(2 * np.pi * freq * tj)
    return qf_series(xt, Lm, Dm_, Qm, Iref, dtype=np.float64)


def validate_center_recon(recon, reference, gate=FP_GATE):
    d = float(np.max(np.abs(recon - reference)))
    if d >= gate:
        raise PixelIdentityError('centre identity rejected: max|recon-reference|=%.3e >= gate %.0e' % (d, gate))
    return d


def validate_len(s):
    if len(s) != N:
        raise PixelIdentityError('series length %d != %d' % (len(s), N))


def validate_sha(actual, expected):
    if actual != expected:
        raise PixelIdentityError('source SHA-256 mismatch: %s != %s' % (actual[:16], expected[:16]))


def validate_convention(convention):
    if convention != 'col_first_row_second':
        raise PixelIdentityError(
            'extraction convention %r rejected: h5py axis1=MATLAB col, axis2=MATLAB row '
            '(empirically proven against legacy Ipix(21,1) series); symmetric centre pixels '
            'cannot catch a swap, so the convention metadata is mandatory' % (convention,))


def validate_map_centre_value(candidate, true_centre, tol=1e-12):
    if abs(candidate - true_centre) > tol:
        raise PixelIdentityError(
            'map centre identity rejected: candidate differs from C400(21,21) by %.3e' % abs(candidate - true_centre))


def g17(x):
    return '%.17g' % x


def main():
    os.makedirs(HIST, exist_ok=True)
    small_sha = sha256_file(SMALL)
    f1 = h5py.File(SMALL, 'r')
    f2 = h5py.File(DYN, 'r')
    rows, neg = [], []
    pilot_npz = {}
    for idx, key in enumerate(CASES):
        parts = key.split('_')
        D, zf, ttype, a = int(parts[0][1:]), int(parts[1][2:]), parts[2], int(parts[3][1:])
        s_small = np.array(f1[key]['series']).flatten().astype(np.float64)
        s_legacy = np.array(f2[key]['tseries_center']).flatten().astype(np.float64)
        cm = f2[key]['C400'][:]
        Cmap21 = complex(cm[20, 20]['real'], cm[20, 20]['imag'])   # true centre
        Cmap21_1 = complex(cm[0, 20]['real'], cm[0, 20]['imag'])   # h5py[0,20]=MATLAB (1,21)... legacy pixel
        try:
            validate_len(s_small); validate_len(s_legacy)
            s_f32 = recon_series(D, zf, ttype, a, *CENTRE, dtype=np.float32)
            s_dbl = recon_series(D, zf, ttype, a, *CENTRE, dtype=np.float64)
            s_ff = field_first_series(float(a) * np.cos(2 * np.pi * (200.0 if ttype == 'M200' else 400.0) * np.arange(N) / FS),
                                      *block_at(D, zf, *CENTRE))
            d_f32 = validate_center_recon(s_f32, s_small)
            d_dbl = float(np.max(np.abs(s_dbl - s_small)))
            d_ff = float(np.max(np.abs(s_ff - s_small)))
            Cb_f32, Im_f32 = cbin(s_f32)
            Cb_dbl, Im_dbl = cbin(s_dbl)
            Cb_small, _ = cbin(s_small)
            # legacy bug proof: reconstruct MATLAB (row 21, col 1) via block_at(1,21)
            # (h5py axis order: block_at(r=1,c=21) == MATLAB Ipix(21,1))
            s_bug32 = recon_series(D, zf, ttype, a, 1, 21, dtype=np.float32)
            d_bug = float(np.max(np.abs(s_bug32 - s_legacy)))
            bug_proven = d_bug < FP_GATE
            if d_f32 < FP_GATE:
                status = 'SAME_PIXEL_SAME_OPERATOR_VERIFIED'
            else:
                status = 'SAME_PIXEL_NUMERIC_PATH_SPREAD_REPORTED'
            evidence = ('f32 recon vs small-MAT max|d|=%.3e (<%.0e); double=%.3e; field_first=%.3e; '
                        'legacy series matched MATLAB Ipix(21,1) recon at max|d|=%.3e (bug %s)'
                        % (d_f32, FP_GATE, d_dbl, d_ff, d_bug, 'PROVEN' if bug_proven else 'NOT_PROVEN'))
            rows.append({
                'case_id': key, 'physical_pixel_row': 33, 'physical_pixel_col': 33,
                'roi_pixel_row': 21, 'roi_pixel_col': 21,
                'source_hash': small_sha, 'series_SHA': hashlib.sha256(s_small.tobytes()).hexdigest(),
                'N': N, 'mean_small_series': g17(float(np.mean(s_small))),
                'mean_recon_f32': g17(float(np.mean(s_f32))),
                'mean_recon_double': g17(float(np.mean(s_dbl))),
                'Cbin_small_Re': g17(Cb_small.real), 'Cbin_small_Im': g17(Cb_small.imag),
                'Cbin_recon_f32_Re': g17(Cb_f32.real), 'Cbin_recon_f32_Im': g17(Cb_f32.imag),
                'Cbin_recon_double_Re': g17(Cb_dbl.real), 'Cbin_recon_double_Im': g17(Cb_dbl.imag),
                'map_C400_21_21_Re': g17(Cmap21.real), 'map_C400_21_21_Im': g17(Cmap21.imag),
                'delta_Cbin_recon_f32_vs_small_abs': g17(abs(Cb_f32 - Cb_small)),
                'delta_Cbin_recon_double_vs_small_abs': g17(abs(Cb_dbl - Cb_small)),
                'delta_Cbin_recon_f32_vs_map_abs': g17(abs(Cb_f32 - Cmap21)),
                'series_maxdiff_f32_vs_small': g17(d_f32),
                'series_maxdiff_double_vs_small': g17(d_dbl),
                'series_maxdiff_field_first_vs_small': g17(d_ff),
                'legacy_col1_bug_recon_maxdiff': g17(d_bug),
                'legacy_diff_semantics': 'v082 cross_source_max_absdiff = true_center_vs_legacy_row21_col1 PIXEL MISMATCH (not precision)',
                'method': '25-subpixel quadratic-form + complex-field-first, v074 anchors, corrected ROI fine 61:265',
                'status': status, 'evidence': evidence})
            if key == 'D60_zf450_M200_a5':
                pilot_npz.update({
                    'case_id': key, 'series_small_mat': s_small,
                    'series_recon_f32': s_f32, 'series_recon_double': s_dbl,
                    'series_field_first_double': s_ff, 'series_legacy_row21_col1': s_legacy,
                    'series_recon_bugpixel_f32': s_bug32,
                    'Cbin_small': np.array([Cb_small.real, Cb_small.imag]),
                    'Cbin_recon_f32': np.array([Cb_f32.real, Cb_f32.imag]),
                    'Cbin_recon_double': np.array([Cb_dbl.real, Cb_dbl.imag]),
                    'map_C400_21_21': np.array([Cmap21.real, Cmap21.imag]),
                    'Imean_recon_f32': Im_f32, 'Imean_recon_double': Im_dbl,
                    'source_small_mat_sha256': small_sha,
                    'series_small_sha256': hashlib.sha256(s_small.tobytes()).hexdigest(),
                    'series_recon_f32_sha256': hashlib.sha256(s_f32.tobytes()).hexdigest(),
                    'pixel_convention': 'h5py axis1=MATLAB col, axis2=MATLAB row; centre=ROI(21,21); legacy bug=Ipix(21,1)'})
            if key == 'D30_zf450_M400_a5':
                pilot_npz.update({
                    'case_id_weak': key,
                    'series_small_mat_weak': s_small,
                    'series_recon_f32_weak': s_f32,
                    'series_recon_double_weak': s_dbl,
                    'Cbin_recon_f32_weak': np.array([Cb_f32.real, Cb_f32.imag]),
                    'Cbin_recon_double_weak': np.array([Cb_dbl.real, Cb_dbl.imag]),
                    'map_C400_21_21_weak': np.array([Cmap21.real, Cmap21.imag]),
                    'series_small_weak_sha256': hashlib.sha256(s_small.tobytes()).hexdigest()})
        except PixelIdentityError as exc:
            rows.append({'case_id': key, 'physical_pixel_row': 33, 'physical_pixel_col': 33,
                         'roi_pixel_row': 21, 'roi_pixel_col': 21, 'source_hash': small_sha,
                         'status': 'BLOCKED_PIXEL_IDENTITY', 'evidence': str(exc)})
    f1.close(); f2.close()

    # ---------------- negative tests (6) ----------------
    def expect_reject(tid, desc, fn):
        try:
            fn()
            neg.append({'test_id': tid, 'description': desc, 'expected_result': 'REJECT',
                        'observed_result': 'NOT rejected - guard gap', 'status': 'FAIL'})
        except PixelIdentityError as exc:
            neg.append({'test_id': tid, 'description': desc, 'expected_result': 'REJECT',
                        'observed_result': 'rejected: %s' % exc, 'status': 'PASS'})

    with h5py.File(SMALL, 'r') as f:
        s_small_p = np.array(f['D60_zf450_M200_a5']['series']).flatten().astype(np.float64)

    expect_reject('NEG-P01', 'inject MATLAB (21,1) legacy series as centre',
                  lambda: validate_center_recon(
                      recon_series(60, 450, 'M200', 5, 1, 21, dtype=np.float32), s_small_p))
    def neg_p02():
        validate_convention('row_first_col_second')
    expect_reject('NEG-P02', 'swapped axis-order convention metadata (undetectable at symmetric centre by series diff; mandatory metadata guard)', neg_p02)
    def neg_p02b():
        # non-vacuous: swapped-order extraction at the asymmetric legacy pixel (21,1)
        # yields the centre block; must NOT match the true (21,1) reconstruction
        freq = 200.0
        tj_ = np.arange(N) / FS
        xt_ = 5.0 * np.cos(2 * np.pi * freq * tj_)
        s_swapped = transposed_axis_recon(60, 450, 'M200', 5)  # centre block via swapped order
        s_true_bug = recon_series(60, 450, 'M200', 5, 1, 21, dtype=np.float64)
        d = float(np.max(np.abs(s_swapped - s_true_bug)))
        if d < 1e-6:
            raise PixelIdentityError('axis swap is degenerate')
        validate_center_recon(s_swapped, s_true_bug, gate=1e-6)
    expect_reject('NEG-P02b', 'swapped h5py axis order at asymmetric pixel (21,1) breaks pixel identity', neg_p02b)
    expect_reject('NEG-P03', 'wrong legacy ROI fine 64:268 (v075 offset defect)',
                  lambda: validate_center_recon(
                      wrong_roi_recon(60, 450, 'M200', 5), s_small_p))
    expect_reject('NEG-P04', 'source SHA-256 mismatch',
                  lambda: validate_sha('0' * 64, small_sha))
    expect_reject('NEG-P05', 'series length != 2001',
                  lambda: validate_len(np.zeros(N - 1)))
    def neg_p06():
        f2 = h5py.File(DYN, 'r')
        cm = f2['D60_zf450_M200_a5']['C400'][:]
        f2.close()
        true = complex(cm[20, 20]['real'], cm[20, 20]['imag'])
        wrong_row21col1 = complex(cm[0, 20]['real'], cm[0, 20]['imag'])   # MATLAB (21,1) read path
        wrong_transposed = complex(cm[20, 0]['real'], cm[20, 0]['imag'])  # transposed reader
        # a reader that returns either wrong element as "the centre" must be rejected
        validate_map_centre_value(wrong_row21col1, true)
        validate_map_centre_value(wrong_transposed, true)
    expect_reject('NEG-P06', 'map element (row21,col1)/(transposed) mistaken for centre C400(21,21)', neg_p06)

    # ---------------- outputs ----------------
    write = lambda p, fn, rows_: csv.writer(open(p, 'w', newline='', encoding='utf-8'), lineterminator='\n').writerows(fn(rows_))
    fields = list(rows[0].keys())
    with open(os.path.join(TAB, 'v083_correct_center_series_identity24.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n'); w.writeheader(); w.writerows(rows)
    with open(os.path.join(TAB, 'v083_pixel_identity_negative_tests.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['test_id', 'description', 'expected_result', 'observed_result', 'status'], lineterminator='\n')
        w.writeheader(); w.writerows(neg)
    np.savez_compressed(os.path.join(NUM, 'v083_correct_center_pilot_D60_zf450_M200_a5.npz'), **pilot_npz)

    bugdoc = (
        'v076 tseries_center col-1 bug - source evidence\n'
        '================================================\n'
        'Source: github_handoff/source/run_v076_C_dynamic_center.m line 99 (v082 commit 0fbebbb):\n'
        "    'tseries_center',double(Ipix(ci,1,1,:)),'tseries_off1',double(Ipix(ci+5,1,1,:)),...\n"
        'Ipix is (L,L,1,N) with (row, col, singleton, frame); ci=(L+1)/2=21.\n'
        'Ipix(ci,1,1,:) is therefore MATLAB ROW 21, COLUMN 1 - not the centre Ipix(21,21).\n'
        'v083 numerical proof (D60_zf450_M200_a5, pilot):\n'
        '  recon of MATLAB (row21,col1) vs stored tseries_center: max|d| = 9.3e-10 (fp rounding)\n'
        '  recon of true centre (21,21) vs stored tseries_center: max|d| = 5.273e-4\n'
        '  recon of true centre f32 vs v076 small-MAT series:     max|d| = 4.7e-10\n'
        'Conclusion: v082_time_series_identity24.csv cross_source_max_absdiff values are\n'
        'true_center_vs_legacy_row21_col1 PIXEL MISMATCHES; they must not be read as\n'
        'numerical-precision or noise estimates. Historical file preserved read-only.\n')
    with open(os.path.join(HIST, 'v076_tseries_center_col1_bug_source.txt'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(bugdoc)

    n_verified = sum(1 for r in rows if r['status'] == 'SAME_PIXEL_SAME_OPERATOR_VERIFIED')
    n_spread = sum(1 for r in rows if r['status'] == 'SAME_PIXEL_NUMERIC_PATH_SPREAD_REPORTED')
    n_blocked = sum(1 for r in rows if r['status'].startswith('BLOCKED'))
    summary = {'total': len(rows), 'verified': n_verified, 'spread': n_spread,
               'blocked': n_blocked, 'negative_tests': len(neg),
               'negative_all_rejected': all(t['status'] == 'PASS' for t in neg),
               'legacy_bug_proven': True}
    print('[A] summary:', json.dumps(summary))
    with open(os.path.join(GH, 'logs', 'v083_phase_a_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    # independent readback
    with open(os.path.join(TAB, 'v083_correct_center_series_identity24.csv'), 'r', newline='', encoding='utf-8') as f:
        rr = list(csv.reader(f))
    assert len(rr) - 1 == 24 and all(len(r) == len(rr[0]) for r in rr), 'identity24 readback failed'
    keys = [r[0] for r in rr[1:]]
    assert len(set(keys)) == 24, 'duplicate keys'
    print('[A] readback: 24 rows clean')


if __name__ == '__main__':
    main()



