"""Testable V127 primitives. These are NOT an optical forward model.
Units: theta = [D,h,x,y] in nm; time arrays and exposure width use one shared unit.
"""
from __future__ import annotations
import json
import math
import numbers
import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path
from typing import Mapping
import numpy as np
from scipy.stats import beta


class ContractError(ValueError):
    pass


class OutOfDomain(ContractError):
    pass


class BudgetExceeded(RuntimeError):
    pass


def real_array(value, name: str) -> np.ndarray:
    a = np.asarray(value)
    if np.iscomplexobj(a) or a.dtype.kind not in "iuf":
        raise ContractError(f"{name}: finite real numeric array required")
    a = np.asarray(a, dtype=float)
    if not np.isfinite(a).all():
        raise ContractError(f"{name}: non-finite value")
    return a


def require_theta(theta, bounds=((30., 200.), (350., 550.), (-500., 500.), (-500., 500.)),
                  min_gap_nm=100.) -> np.ndarray:
    a = real_array(theta, "theta")
    b = real_array(bounds, "bounds")
    if a.shape != (4,) or b.shape != (4, 2) or np.any(b[:, 0] >= b[:, 1]):
        raise ContractError("Expected theta[4] and ordered bounds[4,2]")
    if np.any(a < b[:, 0]) or np.any(a > b[:, 1]):
        raise OutOfDomain("D/h/x/y outside numerical support; clipping is forbidden")
    if not isinstance(min_gap_nm, numbers.Real) or not math.isfinite(min_gap_nm) or min_gap_nm < 0:
        raise ContractError("min_gap_nm must be finite and nonnegative")
    if a[1] - a[0] / 2 < min_gap_nm:
        raise OutOfDomain("Sphere violates physical surface-gap condition")
    return a.copy()


def window_nodes_weights(times, center: float, exposure: float):
    t = real_array(times, "times")
    if t.ndim != 1 or t.size < 2 or np.any(np.diff(t) <= 0):
        raise ContractError("Strictly increasing 1-D time array required")
    if any(isinstance(v, (bool, np.bool_)) or not isinstance(v, numbers.Real) for v in (center, exposure)):
        raise ContractError("Finite real time parameters required; no booleans or complex values")
    if not np.isfinite([center, exposure]).all() or exposure <= 0:
        raise ContractError("Finite center and positive exposure required")
    left, right = float(center - exposure / 2), float(center + exposure / 2)
    if left < t[0] or right > t[-1]:
        raise OutOfDomain("Incomplete temporal coverage; do not renormalize a partial window")
    # Exact endpoints are inserted even on nonaligned or nonuniform input grids.
    u = np.concatenate(([left], t[(t > left) & (t < right)], [right]))
    dt = np.diff(u)
    if np.any(dt <= 0):
        raise ContractError("Invalid exposure interval")
    w = np.zeros_like(u)
    w[:-1] += dt / (2 * exposure)
    w[1:] += dt / (2 * exposure)
    if not np.isclose(w.sum(), 1., rtol=0., atol=1e-12):
        raise ContractError("Quadrature weights do not integrate the full window")
    return u, w


def sample_exposure_path(times, xyz_nm, center, exposure, D_nm, **domain_options):
    t = real_array(times, "times")
    xyz = real_array(xyz_nm, "xyz_nm")
    if xyz.shape != (len(t), 3):
        raise ContractError("xyz_nm must have shape [time,3], ordered x,y,h")
    u, w = window_nodes_weights(t, center, exposure)
    p = np.stack([np.interp(u, t, xyz[:, j]) for j in range(3)], axis=-1)
    # All piecewise-linear path vertices inside the exposure and both endpoints
    # are tested. This is a finite-path model, not a claim about unseen Brownian bridges.
    for x, y, h in p:
        require_theta([D_nm, h, x, y], **domain_options)
    return u, w, p


def profile_grid(lo=30., hi=200., step=2., witnesses=()):
    if not np.isfinite([lo, hi, step]).all() or step <= 0 or lo >= hi:
        raise ContractError("Invalid profile domain or step")
    wit = real_array(list(witnesses), "witnesses")
    if wit.ndim != 1 or np.any((wit < lo) | (wit > hi)):
        raise ContractError("Profile witnesses must be in the declared domain")
    grid = np.arange(lo, hi, step, dtype=float)
    return np.unique(np.concatenate((grid, [lo, hi], wit)))


def clopper_pearson_upper(k: int, n: int, confidence=.95) -> float:
    if any(isinstance(v, (bool, np.bool_)) or not isinstance(v, numbers.Integral) for v in (k, n)):
        raise ContractError("k,n must be integers, not booleans")
    if n <= 0 or k < 0 or k > n or not (0. < confidence < 1.):
        raise ContractError("Invalid binomial parameters")
    if k == n:
        return 1.
    if k == 0:
        return float(-np.expm1(np.log1p(-confidence) / n))
    return float(beta.ppf(confidence, k + 1, n - k))


def reportable_decision(candidate_D, flags: Mapping[str, object]):
    required = ["detection_required", "optimizer_converged", "restart_stable",
                "forward_qualified", "in_domain", "profile_complete", "identifiable",
                "boundary_unresolved"]
    reasons = []
    for k in required:
        if k not in flags or not isinstance(flags[k], (bool, np.bool_)):
            reasons.append("MISSING_OR_NONBOOLEAN_" + k.upper())
    candidate = None
    if (isinstance(candidate_D, numbers.Real) and not isinstance(candidate_D, (bool, np.bool_))
            and math.isfinite(candidate_D)):
        candidate = float(candidate_D)
    else:
        reasons.append("NO_FINITE_CANDIDATE")
    if not reasons:
        if flags["detection_required"]:
            if not isinstance(flags.get("detected"), (bool, np.bool_)) or not flags["detected"]:
                reasons.append("NOT_DETECTED_OR_NOT_ASSESSED")
        for k in ("optimizer_converged", "restart_stable", "forward_qualified", "in_domain",
                  "profile_complete", "identifiable"):
            if not flags[k]:
                reasons.append(k.upper())
        if flags["boundary_unresolved"]:
            reasons.append("BOUNDARY_DEPENDENCE_UNRESOLVED")
    ok = not reasons
    return {"candidate_D": candidate, "diameter_reportable": ok,
            "reportable_D": candidate if ok else None, "reason_codes": reasons}


class BudgetLedger:
    """Atomic, append-preserving reservation ledger. No external job is started here.

    A reserved attempt stays charged even if it fails or the process dies. A caller
    must not launch the operation unless reserve() committed successfully.
    """
    def __init__(self, database, limits: Mapping[str, int]):
        self.path = Path(database)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for key, cap in limits.items():
            if not isinstance(key, str) or not isinstance(cap, int) or isinstance(cap, bool) or cap < 0:
                raise ContractError("Budget limits must map strings to nonnegative integers")
        self.limits = dict(limits)
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, kind TEXT NOT NULL, count INTEGER NOT NULL, status TEXT NOT NULL, created TEXT NOT NULL, payload TEXT NOT NULL)")
            val = json.dumps(self.limits, sort_keys=True, allow_nan=False)
            old = db.execute("SELECT value FROM meta WHERE key='limits'").fetchone()
            if old and old[0] != val:
                raise ContractError("Existing budget limits differ; do not silently reset or enlarge")
            db.execute("INSERT OR IGNORE INTO meta VALUES('limits',?)", (val,))

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=30.)
        try:
            with db:
                yield db
        finally:
            db.close()

    def reserve(self, event_id: str, kind: str, count=1, payload=None):
        if not event_id or not isinstance(event_id, str) or kind not in self.limits:
            raise ContractError("Valid unique event id and known budget kind required")
        if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
            raise ContractError("Reservation count must be a positive integer")
        detail = json.dumps(payload or {}, sort_keys=True, ensure_ascii=False, allow_nan=False)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM events WHERE id=?", (event_id,)).fetchone():
                raise ContractError("DUPLICATE_EVENT: do not relaunch a reserved/finished operation")
            used = db.execute("SELECT COALESCE(SUM(count),0) FROM events WHERE kind=?", (kind,)).fetchone()[0]
            if used + count > self.limits[kind]:
                raise BudgetExceeded(f"{kind}: {used}+{count}>{self.limits[kind]}")
            db.execute("INSERT INTO events VALUES(?,?,?,?,?,?)", (event_id, kind, count, "RESERVED",
                       datetime.now(timezone.utc).isoformat(), detail))
        return used + count

    def finish(self, event_id: str, success: bool):
        if not isinstance(success, bool):
            raise ContractError("success must be a strict boolean")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT status FROM events WHERE id=?", (event_id,)).fetchone()
            if row is None or row[0] != "RESERVED":
                raise ContractError("Unknown/already finished event")
            db.execute("UPDATE events SET status=? WHERE id=?", ("SUCCEEDED" if success else "FAILED", event_id))

    def totals(self):
        with self._connect() as db:
            return {k: int(db.execute("SELECT COALESCE(SUM(count),0) FROM events WHERE kind=?", (k,)).fetchone()[0])
                    for k in self.limits}
