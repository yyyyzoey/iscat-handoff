# -*- coding: utf-8 -*-
"""v112 executable observation operator.

One importable module implementing the time-exposure-count-complex-DFT contract:

  Ibar[p,j] = (1/Tj) * integral over the exposure window of J_p(t) dt
  mu_e[p,j] = kappa_e_per_U_per_s * Tj * Ibar[p,j]
  mu_DN[p,j] = offset_DN + g_DN_per_e * mu_e[p,j]

J_p is an explicit pixel-averaged INTENSITY callback (never a complex-field
average). Timestamps carry an explicit meaning (start/center/end), units in
seconds, and an explicit software time tolerance. The complex DFT uses
N=2001, zero-based k0 in {80,160,320}, real frequency k0*Fs/N, and its phase
origin is the FIRST exposure center. A constant gain cancels in
C = 2X/(N*mean) under the zero-offset fixed-exposure linear model; a nonzero
offset does NOT cancel (algebraic fact, not an instrument claim).
"""
import math

N = 2001
K0S = [80, 160, 320]
DEFAULT_FS = 5000.0
SINC = math.sin  # noqa: naming clarity only


class OperatorError(ValueError):
    """Contract violation of the observation operator."""


def _legendre_nodes(n):
    """Gauss-Legendre nodes/weights on [-1, 1] via Newton iteration on Legendre polynomials."""
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
    if n not in _QUAD_CACHE:
        _QUAD_CACHE[n] = _legendre_nodes(n)
    return _QUAD_CACHE[n]


def validate_timestamps(timestamps, exposure_s, meaning='center', fs=DEFAULT_FS,
                        time_tolerance_s=1e-12, instantaneous_limit=False):
    """Time contract validation. Returns the list of exposure CENTERS in seconds.
    Rejections happen here, before any intensity callback is invoked."""
    if meaning not in ('start', 'center', 'end'):
        raise OperatorError('TIME_MEANING: must be start, center or end')
    if timestamps is None:
        raise OperatorError('MISSING_PARAMETER: timestamps')
    ts = list(timestamps)
    if len(ts) == 0:
        raise OperatorError('EMPTY_TIMESTAMPS')
    for t in ts:
        if t is None or not math.isfinite(t):
            raise OperatorError('INVALID_TIMESTAMP: NaN/Inf/None')
    for a, b in zip(ts, ts[1:]):
        if not b > a:
            raise OperatorError('NON_STRICTLY_INCREASING_TIMESTAMPS: duplicates or reversal')
    if not instantaneous_limit:
        if exposure_s is None:
            raise OperatorError('MISSING_PARAMETER: exposure_time_per_frame')
        if not math.isfinite(exposure_s) or exposure_s <= 0:
            raise OperatorError('INVALID_EXPOSURE: must be finite and positive '
                                '(T=0 only allowed in instantaneous_limit mode)')
    # uniformity is checked on DIFFERENCES against the ideal 1/fs grid, never on
    # timestamp values being equal to each other
    diffs = [b - a for a, b in zip(ts, ts[1:])]
    ideal = 1.0 / float(fs)
    tol = time_tolerance_s
    for d in diffs:
        if abs(d - ideal) > tol:
            raise OperatorError('NON_UNIFORM_GRID: diff %.17g vs ideal %.17g (tol %.3g s)'
                                % (d, ideal, tol))
    if meaning == 'start':
        centers = [t + exposure_s / 2 for t in ts]
    elif meaning == 'end':
        centers = [t - exposure_s / 2 for t in ts]
    else:
        centers = list(ts)
    return centers


def exposure_average(J_p, t_center, T, quadrature_nodes=64, instantaneous_limit=False):
    """(1/T) * integral over [t_center - T/2, t_center + T/2] of J_p dt.
    T must be positive; T=0 is ONLY allowed in instantaneous_limit mode and
    returns J_p(t_center) (the math limit, not a camera default)."""
    if instantaneous_limit:
        v = J_p(t_center)
        if isinstance(v, complex):
            raise OperatorError('COMPLEX_FIELD_CALLBACK: the intensity callback must return '
                                'pixel-averaged INTENSITY, never a complex field')
        return v
    if T is None or not math.isfinite(T) or T <= 0:
        raise OperatorError('INVALID_EXPOSURE: positive exposure required '
                            '(T=0 only in instantaneous_limit mode)')
    xs, ws = _quad(quadrature_nodes)
    half = T / 2
    total = 0.0
    for x, w in zip(xs, ws):
        v = J_p(t_center + half * x)
        if isinstance(v, complex):
            raise OperatorError('COMPLEX_FIELD_CALLBACK: the intensity callback must return '
                                'pixel-averaged INTENSITY, never a complex field')
        total += w * v
    return total / 2 * half * 2 / T  # = sum(w*J)/2 * half * 2/T


def exposure_average_fixed(J_p, t_center, T, quadrature_nodes=64):
    """Same as exposure_average (kept explicit for the fixed-quadrature test)."""
    return exposure_average(J_p, t_center, T, quadrature_nodes)


def electron_counts(Ibar, kappa_e_per_U_per_s, T):
    """mu_e = kappa_e_per_U_per_s * Tj * Ibar. kappa units: e- per (U * s)."""
    if kappa_e_per_U_per_s is None:
        raise OperatorError('MISSING_PARAMETER: kappa_e_per_U_per_s')
    if T is None or not math.isfinite(T) or T <= 0:
        raise OperatorError('INVALID_EXPOSURE: electron-count mode requires positive exposure')
    if kappa_e_per_U_per_s <= 0:
        raise OperatorError('INVALID_RESPONSE_COEFFICIENT')
    return kappa_e_per_U_per_s * T * Ibar


def dn_counts(mu_e, g_DN_per_e, offset_DN):
    """mu_DN = offset_DN + g_DN_per_e * mu_e."""
    if g_DN_per_e is None:
        raise OperatorError('MISSING_PARAMETER: g_DN_per_e')
    if offset_DN is None:
        raise OperatorError('MISSING_PARAMETER: offset_DN')
    return offset_DN + g_DN_per_e * mu_e


def complex_dft(series, mean, k0s=None, fs=DEFAULT_FS):
    """Zero-based DFT of the exposure-averaged series with phase origin at the
    FIRST exposure center (t=0 there). Returns {k0: (X, C)} with
    C = 2X/(N*mean). series[j] corresponds to center j."""
    k0s = k0s or K0S
    if len(series) != N:
        raise OperatorError('SERIES_LENGTH: expected N=%d, got %d' % (N, len(series)))
    if mean is None or not math.isfinite(mean) or mean == 0:
        raise OperatorError('INVALID_MEAN for normalization')
    out = {}
    for k0 in k0s:
        if k0 not in K0S:
            raise OperatorError('ILLEGAL_BIN: %r not in %r' % (k0, K0S))
        X = complex(0)
        for j, v in enumerate(series):
            X += (v - mean) * math.cos(2 * math.pi * k0 * j / N)
            X -= 1j * (v - mean) * math.sin(2 * math.pi * k0 * j / N)
        C = 2.0 * X / (N * mean)
        out[k0] = (X, C)
    return out


def run_pipeline(intensity_callback, timestamps, exposure_s, mode='intensity',
                 time_meaning='center', fs=DEFAULT_FS, time_tolerance_s=1e-12,
                 kappa_e_per_U_per_s=None, g_DN_per_e=None, offset_DN=None,
                 pixel_weights=None, quadrature_nodes=64, k0s=None,
                 instantaneous_limit=False):
    """Full chain: timestamp validation -> pixel-weighted intensity average over
    each exposure -> unit mode conversion -> complex DFT.
    intensity_callback(t) must return the pixel-averaged intensity at time t
    (seconds). pixel_weights is an explicit weight vector; if None, uniform
    weights are used on the callback's returned sequence."""
    centers = validate_timestamps(timestamps, exposure_s, meaning=time_meaning,
                                  fs=fs, time_tolerance_s=time_tolerance_s,
                                  instantaneous_limit=instantaneous_limit)
    if mode not in ('intensity', 'electron', 'dn'):
        raise OperatorError('UNKNOWN_OUTPUT_MODE: %r' % mode)
    if mode in ('electron', 'dn'):
        if instantaneous_limit or exposure_s is None or exposure_s <= 0:
            raise OperatorError('INVALID_EXPOSURE: count modes require positive exposure')
        if kappa_e_per_U_per_s is None:
            raise OperatorError('MISSING_PARAMETER: kappa_e_per_U_per_s '
                                '(no predicted electron counts without response data)')
    series = []
    means = []
    for tc in centers:
        def J(t):
            vals = intensity_callback(t)
            if isinstance(vals, (int, float, complex)):
                vals = [vals]
            if pixel_weights is None:
                vs = list(vals)
                return sum(vs) / len(vs)
            if len(pixel_weights) != len(vals):
                raise OperatorError('PIXEL_WEIGHT_LENGTH mismatch')
            wsum = sum(pixel_weights)
            return sum(w * v for w, v in zip(pixel_weights, vals)) / wsum
        Ibar = exposure_average(J, tc, exposure_s, quadrature_nodes=quadrature_nodes,
                                instantaneous_limit=instantaneous_limit)
        means.append(Ibar)
        if mode == 'intensity':
            series.append(Ibar)
        elif mode == 'electron':
            series.append(electron_counts(Ibar, kappa_e_per_U_per_s, exposure_s))
        else:
            series.append(dn_counts(electron_counts(Ibar, kappa_e_per_U_per_s, exposure_s),
                                    g_DN_per_e, offset_DN))
    mean_all = sum(series) / len(series)
    if len(series) == N:
        dft = complex_dft(series, mean_all, k0s=k0s, fs=fs)
    else:
        dft = None  # partial pipeline: DFT requires the full N=2001 exposure-center grid
    return {'centers': centers, 'series': series, 'mean': mean_all, 'dft': dft}
