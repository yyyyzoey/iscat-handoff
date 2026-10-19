# -*- coding: utf-8 -*-
"""v113 measurement operator: original gates restored.

Time contract: seconds, explicit meaning (start/center/end), positive finite
exposure (T=0 ONLY with the explicit instantaneous_limit flag and exposure
exactly 0; a negative exposure is rejected even with the flag), strict
increase, difference-uniformity vs the ideal 1/Fs grid, positive finite Fs and
positive finite explicit time tolerance; every static parameter is validated
BEFORE any intensity callback runs.

Unit contract: Ibar = (1/T) * exposure average of the pixel-averaged INTENSITY
J_p(t) (finite, real, NON-NEGATIVE; complex-field callbacks are refused);
mu_e = kappa_e_per_U_per_s * T * Ibar (kappa positive finite); mu_DN =
offset_DN + g_DN_per_e * mu_e.

Spectral contract: production path = real FFT (numpy.fft) of the stored array;
independent path = direct DFT of the SAME stored array using integer remainder
phases (j*k) % N and math.fsum accumulation. Original gates: same-array X and
C each strictly < 1e-11, mean identity < 1e-12. Phase origin = FIRST exposure
center; constant gain cancels in C under the zero-offset fixed-exposure linear
model, a nonzero offset does not (algebraic fact, not an instrument claim)."""
import math
import numpy as np

N = 2001
K0S = [80, 160, 320]
DEFAULT_FS = 5000.0
X_GATE = 1e-11
C_GATE = 1e-11
MEAN_GATE = 1e-12


class OperatorError(ValueError):
    """Contract violation of the measurement operator."""


def _finite_pos(x, name):
    if x is None or isinstance(x, bool) or not isinstance(x, (int, float)) \
            or not math.isfinite(x) or x <= 0:
        raise OperatorError('INVALID_PARAMETER: %s must be positive finite' % name)


def _legendre_nodes(n):
    nodes, weights = [], []
    for i in range(1, n + 1):
        x = math.cos(math.pi * (i - 0.25) / (n + 0.5))
        for _ in range(100):
            p0, p1 = 1.0, x
            for k in range(2, n + 1):
                p0, p1 = p1, ((2 * k - 1) * x * p1 - (k - 1) * p0) / k
            dp = n * (x * p1 - p0) / (x * x - 1)
            dx = p1 / dp
            x -= dx
            if abs(dx) < 1e-15:
                break
        nodes.append(x)
        weights.append(2 / ((1 - x * x) * dp * dp))
    return nodes, weights


_QUAD_CACHE = {}


def _quad(n):
    if isinstance(n, bool) or not isinstance(n, int) or n < 2 or n > 256:
        raise OperatorError('INVALID_QUADRATURE_ORDER: %r (must be an integer in [2, 256])' % (n,))
    if n not in _QUAD_CACHE:
        _QUAD_CACHE[n] = _legendre_nodes(n)
    return _QUAD_CACHE[n]


def validate_timestamps(timestamps, exposure_s, meaning='center', fs=DEFAULT_FS,
                        time_tolerance_s=1e-12, instantaneous_limit=False):
    """Full static pre-validation. Raises before any intensity callback runs."""
    _finite_pos(fs, 'Fs')
    _finite_pos(time_tolerance_s, 'time_tolerance_s')
    if time_tolerance_s >= 0.5 / float(fs):
        raise OperatorError('TIME_TOLERANCE_TOO_LARGE: %.17g >= 0.5/Fs=%.17g; this software '
                            'anti-alias bound prevents clearly non-uniform series from passing as '
                            'uniform (NOT an independent clock calibration)' %
                            (time_tolerance_s, 0.5 / float(fs)))
    if meaning not in ('start', 'center', 'end'):
        raise OperatorError('TIME_MEANING: must be start, center or end')
    if timestamps is None:
        raise OperatorError('MISSING_PARAMETER: timestamps')
    ts = list(timestamps)
    if len(ts) == 0:
        raise OperatorError('EMPTY_TIMESTAMPS')
    for t in ts:
        if t is None or isinstance(t, bool) or not isinstance(t, (int, float)) \
                or not math.isfinite(t):
            raise OperatorError('INVALID_TIMESTAMP: NaN/Inf/None/non-numeric')
    for a, b in zip(ts, ts[1:]):
        if not b > a:
            raise OperatorError('NON_STRICTLY_INCREASING_TIMESTAMPS: duplicates or reversal')
    if instantaneous_limit:
        if exposure_s is None:
            raise OperatorError('MISSING_PARAMETER: exposure_time_per_frame')
        if exposure_s != 0:
            raise OperatorError('INSTANTANEOUS_FLAG_CONFLICT: instantaneous_limit '
                                'requires exposure exactly 0; negative exposure is never allowed')
    else:
        if exposure_s is None:
            raise OperatorError('MISSING_PARAMETER: exposure_time_per_frame')
        if isinstance(exposure_s, bool) or not isinstance(exposure_s, (int, float)) \
                or not math.isfinite(exposure_s) or exposure_s <= 0:
            raise OperatorError('INVALID_EXPOSURE: must be a non-bool finite positive number '
                                '(T=0 only with instantaneous_limit flag)')
    diffs = [b - a for a, b in zip(ts, ts[1:])]
    ideal = 1.0 / float(fs)
    tol = float(time_tolerance_s)
    for d in diffs:
        if abs(d - ideal) > tol:
            raise OperatorError('NON_UNIFORM_GRID: diff %.17g vs ideal %.17g (tol %.3g s)'
                                % (d, ideal, tol))
    if meaning == 'start':
        return [t + exposure_s / 2 for t in ts]
    if meaning == 'end':
        return [t - exposure_s / 2 for t in ts]
    return list(ts)


def weighted_pixel_average(vals, weights=None):
    """Explicit pixel-axis reduction. vals must be finite real NON-NEGATIVE
    intensities; weights (when given) must be finite and non-negative with a
    positive sum. A complex value is a complex-field callback and is refused."""
    if isinstance(vals, complex):
        raise OperatorError('COMPLEX_FIELD_CALLBACK: the intensity callback must return '
                            'pixel-averaged INTENSITY, never a complex field')
    if isinstance(vals, (int, float)):
        vals = [vals]  # explicit single-pixel axis
    for v in vals:
        if isinstance(v, complex) or not math.isfinite(v) or v < 0:
            raise OperatorError('INVALID_INTENSITY: callback must return finite, real, '
                                'non-negative pixel intensities (complex-field callbacks refused)')
    if weights is None:
        return sum(vals) / len(vals)
    if len(weights) != len(vals):
        raise OperatorError('PIXEL_WEIGHT_LENGTH mismatch')
    wsum = math.fsum(weights)
    for w in weights:
        if not math.isfinite(w) or w < 0:
            raise OperatorError('INVALID_PIXEL_WEIGHT: weights must be finite and non-negative')
    if wsum <= 0:
        raise OperatorError('INVALID_PIXEL_WEIGHT: weight sum must be positive')
    return math.fsum(w * v for w, v in zip(weights, vals)) / wsum


def exposure_average(J_p, t_center, T, quadrature_nodes=64, instantaneous_limit=False):
    """(1/T) * integral of J_p over the exposure window (Gauss-Legendre).
    instantaneous_limit requires T == 0 and returns J_p(t_center)."""
    if isinstance(quadrature_nodes, bool) or not isinstance(quadrature_nodes, int) \
            or not 2 <= quadrature_nodes <= 256:
        raise OperatorError('INVALID_QUADRATURE_ORDER: %r (must be an integer in [2, 256]; '
                            'fractional orders are rejected, never silently truncated)' % (quadrature_nodes,))
    if instantaneous_limit:
        if T != 0:
            raise OperatorError('INSTANTANEOUS_FLAG_CONFLICT: requires T == 0')
        return J_p(t_center)
    if T is None or not math.isfinite(T) or T <= 0:
        raise OperatorError('INVALID_EXPOSURE: positive exposure required')
    xs, ws = _quad(quadrature_nodes)
    half = T / 2
    vals = [J_p(t_center + half * x) for x in xs]
    total = math.fsum(w * v for w, v in zip(ws, vals))
    return total * half / T  # (1/T) * h * total, h = T/2; GL weights sum to 2


def electron_counts(Ibar, kappa_e_per_U_per_s, T):
    if kappa_e_per_U_per_s is None or isinstance(kappa_e_per_U_per_s, bool) \
            or not isinstance(kappa_e_per_U_per_s, (int, float)) \
            or not math.isfinite(kappa_e_per_U_per_s) or kappa_e_per_U_per_s <= 0:
        raise OperatorError('INVALID_RESPONSE_COEFFICIENT: kappa must be positive finite')
    if T is None or isinstance(T, bool) or not math.isfinite(T) or T <= 0:
        raise OperatorError('INVALID_EXPOSURE: count modes require positive exposure')
    if not math.isfinite(Ibar) or Ibar < 0:
        raise OperatorError('INVALID_INTENSITY for count conversion')
    mu_e = kappa_e_per_U_per_s * T * Ibar
    if not math.isfinite(mu_e):
        raise OperatorError('COUNT_OVERFLOW: electron expectation is not finite')
    if mu_e < 0:
        raise OperatorError('NEGATIVE_ELECTRON_EXPECTATION')
    return mu_e


def dn_counts(mu_e, g_DN_per_e, offset_DN):
    if mu_e is None or isinstance(mu_e, bool) or not isinstance(mu_e, (int, float)) \
            or not math.isfinite(mu_e) or mu_e < 0:
        raise OperatorError('INVALID_MU_E: electron expectation must be finite and non-negative')
    if g_DN_per_e is None or not math.isfinite(g_DN_per_e) or g_DN_per_e <= 0:
        raise OperatorError('INVALID_CONVERSION_GAIN: g_DN_per_e must be positive finite')
    if offset_DN is None or not math.isfinite(offset_DN):
        raise OperatorError('INVALID_OFFSET_DN')
    mu_DN = offset_DN + g_DN_per_e * mu_e
    if not math.isfinite(mu_DN):
        raise OperatorError('DN_OVERFLOW: digital count expectation is not finite')
    return mu_DN


def _validate_bins(k0s):
    if k0s is None:
        return K0S
    if len(k0s) == 0:
        raise OperatorError('EMPTY_BIN_LIST')
    if len(set(k0s)) != len(k0s):
        raise OperatorError('DUPLICATE_BINS')
    for k0 in k0s:
        if k0 not in K0S:
            raise OperatorError('ILLEGAL_BIN: %r not in %r' % (k0, K0S))
    return list(k0s)


def production_fft(series, mean, k0s=None):
    """Production spectral path: REAL FFT of the stored array."""
    k0s = _validate_bins(k0s)
    if len(series) != N:
        raise OperatorError('SERIES_LENGTH: expected N=%d, got %d' % (N, len(series)))
    if mean is None or isinstance(mean, bool) or not math.isfinite(mean) or mean <= 0:
        raise OperatorError('INVALID_MEAN: normalization mean must be positive finite')
    arr = np.asarray(series, dtype=np.float64)
    if not np.isfinite(arr).all():
        raise OperatorError('NON_FINITE_SERIES: stored intensity array contains NaN/Inf')
    spec = np.fft.fft(arr - mean)
    out = {}
    for k0 in k0s:
        if k0 not in K0S:
            raise OperatorError('ILLEGAL_BIN: %r not in %r' % (k0, K0S))
        X = complex(spec[k0])
        out[k0] = (X, 2.0 * X / (N * mean))
    return out


def independent_dft(series, mean, k0s=None):
    """Independent path: direct DFT of the SAME stored array via integer
    remainder phases (j*k) % N and math.fsum accumulation."""
    k0s = _validate_bins(k0s)
    if len(series) != N:
        raise OperatorError('SERIES_LENGTH: expected N=%d, got %d' % (N, len(series)))
    if mean is None or isinstance(mean, bool) or not math.isfinite(mean) or mean <= 0:
        raise OperatorError('INVALID_MEAN: normalization mean must be positive finite')
    centered = [v - mean for v in series]
    for v in centered:
        if not math.isfinite(v):
            raise OperatorError('NON_FINITE_SERIES: stored intensity array contains NaN/Inf')
    out = {}
    for k0 in k0s:
        if k0 not in K0S:
            raise OperatorError('ILLEGAL_BIN: %r not in %r' % (k0, K0S))
        re = math.fsum(centered[j] * math.cos(2 * math.pi * ((j * k0) % N) / N)
                       for j in range(N))
        im = -math.fsum(centered[j] * math.sin(2 * math.pi * ((j * k0) % N) / N)
                        for j in range(N))
        X = complex(re, im)
        out[k0] = (X, 2.0 * X / (N * mean))
    return out


def compare_paths(series, mean, k0s=None):
    """Same-array FFT vs direct DFT against the ORIGINAL gates."""
    k0s = k0s or K0S
    prod = production_fft(series, mean, k0s)
    indep = independent_dft(series, mean, k0s)
    rows = []
    ok = True
    for k0 in k0s:
        Xp, Cp = prod[k0]
        Xi, Ci = indep[k0]
        dX = abs(Xp - Xi)
        dC = abs(Cp - Ci)
        row_ok = dX < X_GATE and dC < C_GATE
        ok = ok and row_ok
        rows.append({'k0': k0, 'X_fft_Re': '%.17g' % Xp.real, 'X_fft_Im': '%.17g' % Xp.imag,
                     'X_dft_Re': '%.17g' % Xi.real, 'X_dft_Im': '%.17g' % Xi.imag,
                     'C_fft_Re': '%.17g' % Cp.real, 'C_fft_Im': '%.17g' % Cp.imag,
                     'C_dft_Re': '%.17g' % Ci.real, 'C_dft_Im': '%.17g' % Ci.imag,
                     'abs_dX': '%.17g' % dX, 'abs_dC': '%.17g' % dC,
                     'gate': 'X<1e-11 C<1e-11', 'status': 'PASS' if row_ok else 'FAIL'})
    mean_err = abs(math.fsum(series) / N - mean)
    ok = ok and mean_err < MEAN_GATE
    return ok, rows, {'mean_identity_err': '%.17g' % mean_err, 'mean_gate': '<1e-12'}


def run_pipeline(intensity_callback, timestamps, exposure_s, mode='intensity',
                 time_meaning='center', fs=DEFAULT_FS, time_tolerance_s=1e-12,
                 kappa_e_per_U_per_s=None, g_DN_per_e=None, offset_DN=None,
                 pixel_weights=None, quadrature_nodes=64, k0s=None,
                 instantaneous_limit=False):
    """Full chain: static pre-validation -> weighted pixel intensity average per
    exposure -> unit-mode conversion -> production FFT + independent DFT on the
    SAME stored array (only when the series has the full N samples)."""
    centers = validate_timestamps(timestamps, exposure_s, meaning=time_meaning,
                                  fs=fs, time_tolerance_s=time_tolerance_s,
                                  instantaneous_limit=instantaneous_limit)
    if mode not in ('intensity', 'electron', 'dn'):
        raise OperatorError('UNKNOWN_OUTPUT_MODE: %r' % mode)
    if mode in ('electron', 'dn'):
        if instantaneous_limit or exposure_s is None or exposure_s <= 0:
            raise OperatorError('INVALID_EXPOSURE: count modes require positive exposure')
        if kappa_e_per_U_per_s is None:
            raise OperatorError('MISSING_PARAMETER: kappa_e_per_U_per_s')

    def J(t):
        return weighted_pixel_average(intensity_callback(t), pixel_weights)

    series = []
    for tc in centers:
        Ibar = exposure_average(J, tc, exposure_s, quadrature_nodes=quadrature_nodes,
                                instantaneous_limit=instantaneous_limit)
        if mode == 'intensity':
            series.append(Ibar)
        elif mode == 'electron':
            series.append(electron_counts(Ibar, kappa_e_per_U_per_s, exposure_s))
        else:
            series.append(dn_counts(electron_counts(Ibar, kappa_e_per_U_per_s, exposure_s),
                                    g_DN_per_e, offset_DN))
    mean_all = math.fsum(series) / len(series)
    if len(series) == N:
        fft_ok, cmp_rows, meta = compare_paths(series, mean_all, k0s=k0s)
        if not fft_ok:
            err = OperatorError('SPECTRAL_GATE_FAIL_UNSEALED_PARTIAL: same-array X/C failed the '
                                'original gates; no certified dft is exposed')
            err.comparison_rows = cmp_rows
            err.comparison_meta = meta
            raise err
        dft = production_fft(series, mean_all, k0s=k0s)
    else:
        fft_ok, cmp_rows, meta = None, [], {'note': 'partial pipeline: DFT requires full N grid'}
        dft = None
    return {'centers': centers, 'series': series, 'mean': mean_all, 'dft': dft,
            'fft_vs_dft_ok': fft_ok, 'comparison_rows': cmp_rows, 'comparison_meta': meta}


def run_roi(intensity_callback, timestamps, exposure_s, *, spatial_weights,
            mode='intensity', k0s=None, fs=DEFAULT_FS, time_tolerance_s=1e-12,
            time_meaning='center', quadrature_nodes=64,
            kappa_e_per_U_per_s=None, g_DN_per_e=None, offset_DN=None,
            instantaneous_limit=False):
    """Spatial detector-pixel interface: callback returns a (P, Q) real intensity
    frame (P detector pixels x Q sub-pixel samples); spatial_weights is (P, Q),
    normalized ROW-WISE inside each detector pixel (adjacent camera pixels are
    never mixed). Returns series shape (N, P) and dft[k] = (X[P], C[P])."""
    centers = validate_timestamps(timestamps, exposure_s, meaning=time_meaning,
                                  fs=fs, time_tolerance_s=time_tolerance_s,
                                  instantaneous_limit=instantaneous_limit)
    if mode not in ('intensity', 'electron', 'dn'):
        raise OperatorError('UNKNOWN_OUTPUT_MODE: %r' % mode)
    if mode in ('electron', 'dn'):
        if instantaneous_limit or exposure_s is None or exposure_s <= 0:
            raise OperatorError('INVALID_EXPOSURE: count modes require positive exposure')
        if kappa_e_per_U_per_s is None:
            raise OperatorError('MISSING_PARAMETER: kappa_e_per_U_per_s')
    if spatial_weights is None:
        raise OperatorError('MISSING_PARAMETER: spatial_weights')
    W = [list(row) for row in spatial_weights]
    P = len(W)
    if P == 0:
        raise OperatorError('EMPTY_DETECTOR_AXIS')
    Q = len(W[0])
    if Q == 0 or any(len(row) != Q for row in W):
        raise OperatorError('SPATIAL_WEIGHT_SHAPE: all rows must have length Q')
    for row in W:
        for w in row:
            if isinstance(w, bool) or not isinstance(w, (int, float)) \
                    or not math.isfinite(w) or w < 0:
                raise OperatorError('INVALID_SPATIAL_WEIGHT: weights must be finite and non-negative')
        if math.fsum(row) <= 0:
            raise OperatorError('INVALID_SPATIAL_WEIGHT: each detector pixel needs a positive '
                                'sub-pixel weight sum')
    probe = intensity_callback(centers[0])
    if not hasattr(probe, '__len__') or len(probe) != P:
        raise OperatorError('CALLBACK_SHAPE: callback must return (P, Q) = (%d, %d) frames' % (P, Q))
    if len(probe[0]) != Q:
        raise OperatorError('CALLBACK_SHAPE: sub-pixel axis length mismatch')
    k0s = _validate_bins(k0s)

    def make_J(p):
        def J(t):
            fr = intensity_callback(t)
            return weighted_pixel_average(fr[p], W[p])
        return J

    series = []
    for tc in centers:
        row_out = [exposure_average(make_J(p), tc, exposure_s,
                                    quadrature_nodes=quadrature_nodes,
                                    instantaneous_limit=instantaneous_limit)
                   for p in range(P)]
        series.append(row_out)
    mean_all = [math.fsum(row[p] for row in series) / len(series) for p in range(P)]
    arr = np.asarray(series, dtype=np.float64)  # shape (N, P) - interface contract
    if arr.shape[0] != N:
        return {'centers': centers, 'series': arr, 'mean': mean_all, 'dft': None,
                'note': 'partial pipeline: DFT requires full N grid'}
    dft = {}
    for k0 in k0s:
        Xs, Cs = [], []
        for p in range(P):
            sp = arr[:, p]
            ok_p, _, _ = compare_paths(sp, mean_all[p], k0s=[k0])
            if not ok_p:
                raise OperatorError('SPECTRAL_GATE_FAIL_UNSEALED_PARTIAL: pixel %d failed the '
                                    'same-array gates for k0=%d; no certified dft exposed' % (p, k0))
            Xp, Cp = production_fft(sp, mean_all[p], k0s=[k0])[k0]
            Xs.append(Xp)
            Cs.append(Cp)
        dft[k0] = (np.asarray(Xs, dtype=np.complex128), np.asarray(Cs, dtype=np.complex128))
    return {'centers': centers, 'series': arr, 'mean': np.asarray(mean_all), 'dft': dft,
            'shape': (N, P)}
