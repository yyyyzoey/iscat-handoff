"""One consistent fixed-variance GLS objective for E1, static repeats and fixed D.

No physical solver, random camera generation, truth file, threshold or confidence
interval is implemented here. The workstation adapter must supply a persistently
counted predictor and durable callbacks. Tested locally with fake models only.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Any
import numpy as np
from scipy.optimize import least_squares

LOW = np.array([30., 350., -500., -500.])
HIGH = np.array([200., 550., 500., 500.])

class CallCapReached(RuntimeError):
    pass

class InvariantError(RuntimeError):
    pass


def _finite_array(x: Any, name: str) -> np.ndarray:
    a = np.array(x, dtype=np.float64, copy=True)
    if not np.isfinite(a).all():
        raise ValueError(name + ': nonfinite')
    return a


def check_theta(theta: Any) -> np.ndarray:
    t = _finite_array(theta, 'theta')
    if t.shape != (4,) or np.any(t < LOW) or np.any(t > HIGH):
        raise ValueError('theta outside the frozen box; clipping is forbidden')
    if t[1] - t[0]/2 < 100.:
        raise ValueError('gap outside frozen support')
    return t


@dataclass(frozen=True)
class GlsData:
    """Fixed observed plug-in variances; no Gaussian-likelihood claim is made."""
    y: np.ndarray
    variance: np.ndarray
    ybar: np.ndarray
    vbar: np.ndarray
    constant_K: float

    @classmethod
    def from_frames(cls, y: Any, variance: Any) -> 'GlsData':
        ys = _finite_array(y, 'Y')
        vs = _finite_array(variance, 'V')
        if ys.ndim == 2:
            ys = ys[None, ...]
        if vs.ndim == 2:
            vs = vs[None, ...]
        if ys.shape != vs.shape or ys.ndim != 3 or ys.shape[1:] != (13, 13):
            raise ValueError('Y and V must have shape (n,13,13) or (13,13)')
        if ys.shape[0] not in (1, 3) or np.any(vs <= 0.):
            raise ValueError('expect one or three frames and strictly positive V')
        if ys.shape[0] == 1:
            ybar, vbar, k = ys[0].copy(), vs[0].copy(), 0.
        else:
            precision = 1. / vs
            vbar = 1. / np.sum(precision, axis=0)
            ybar = vbar * np.sum(precision * ys, axis=0)
            k = float(np.sum((ys-ybar)**2 / vs))
        if not all(np.isfinite(a).all() for a in (ybar, vbar)) or not np.isfinite(k):
            raise ValueError('aggregation overflow or invalid numerical range')
        for a in (ys, vs, ybar, vbar):
            a.flags.writeable = False
        return cls(ys, vs, ybar, vbar, k)

    def prediction(self, value: Any) -> np.ndarray:
        c = _finite_array(value, 'predicted C')
        if c.shape != (13, 13):
            raise ValueError('prediction must be a signed 13x13 contrast map')
        return c

    def residual(self, c: Any) -> np.ndarray:
        c = self.prediction(c)
        return ((c-self.ybar)/np.sqrt(self.vbar)).ravel()

    def score(self, c: Any) -> dict:
        c = self.prediction(c)
        q_frames = np.sum((c-self.y)**2/self.variance, axis=(1, 2))
        q_direct = float(q_frames.sum())
        r = self.residual(c)
        q_model = float(r @ r)
        q_aggregate = q_model + self.constant_K
        error = abs(q_direct-q_aggregate)
        if error > max(1e-8, 1e-10*abs(q_direct)):
            raise InvariantError('direct / aggregated GLS mismatch')
        return dict(Q_joint=q_direct, Q_model=q_model, K=self.constant_K,
                    Q_per_frame=q_frames.tolist(), identity_abs_error=error,
                    unweighted_to_ybar=float(np.sum((c-self.ybar)**2)),
                    unweighted_per_frame=np.sum((c-self.y)**2, axis=(1,2)).tolist())


def solve_one_start(
    data: GlsData, predict: Callable[[np.ndarray], Any], x0: Any, *,
    cap: int, checkpoint: Callable[[dict], None],
    persist_best: Callable[[dict, np.ndarray], None],
    fixed_D: float | None = None, max_nfev: int = 90,
) -> dict:
    """Exactly one real start. Persist best finite evaluations and final outcome.

    predict must charge its persistent task/phase/global ledger BEFORE F2c.
    This local cap is an additional guard, not a replacement for that ledger.
    Unexpected implementation/model errors abort the dependent workflow.
    The caller saves signatures and controls reuse/resume before this function.
    """
    if type(cap) is not int or cap < 1 or type(max_nfev) is not int or max_nfev < 1:
        raise ValueError('invalid local cap / max_nfev')
    p0 = _finite_array(x0, 'x0')
    if fixed_D is None:
        check_theta(p0)
        lower, upper, scale = LOW, HIGH, [50., 50., 140., 140.]
        def to_theta(p):
            return check_theta(p)
    else:
        D = float(fixed_D)
        if p0.shape != (3,):
            raise ValueError('fixed-D optimizer accepts exactly h/x/y, not D/h/x/y')
        check_theta([D, *p0])
        lower, upper, scale = LOW[1:], HIGH[1:], [50., 140., 140.]
        def to_theta(p):
            t = check_theta([D, *p])
            if t[0] != D:
                raise InvariantError('fixed D changed')
            return t
    calls = 0
    best = None
    def residual(p):
        nonlocal calls, best
        t = to_theta(p)
        if calls >= cap:
            raise CallCapReached('local forward-attempt cap reached')
        calls += 1
        c = data.prediction(predict(t))
        score = data.score(c)
        witness = dict(theta=t.tolist(), calls_at_witness=calls, **score)
        if best is None or witness['Q_joint'] < best['Q_joint']:
            # Commit before returning to the optimizer. A write failure is fatal.
            persist_best(witness, c)
            best = witness
        return data.residual(c)
    record = dict(x0=p0.tolist(), fixed_D=fixed_D, state='RUNNING')
    checkpoint(record)
    try:
        opt = least_squares(residual, p0, bounds=(lower, upper), method='trf',
                            jac='2-point', loss='linear', x_scale=scale,
                            max_nfev=max_nfev, ftol=1e-10, xtol=1e-10, gtol=1e-10)
        final_theta = to_theta(opt.x).tolist()
        record.update(state='FINISHED', theta=final_theta,
                      optimizer_success=bool(opt.success), status=int(opt.status),
                      nfev=int(opt.nfev), message=str(opt.message),
                      Q_model_at_return=float(np.dot(opt.fun, opt.fun)))
    except CallCapReached as exc:
        record.update(state='PARTIAL_BUDGET', optimizer_success=False, error=str(exc))
    except Exception as exc:
        record.update(state='FAILED', optimizer_success=False,
                      error_type=type(exc).__name__, error=repr(exc),
                      predictor_requests=calls, best=best)
        checkpoint(record)
        raise
    record.update(predictor_requests=calls, best=best,
                  reportable_D=None, global_uniqueness_certified=False)
    checkpoint(record)
    return record
