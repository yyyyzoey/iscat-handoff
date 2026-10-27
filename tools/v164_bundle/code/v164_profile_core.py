"""Bounded fixed-D *model-separation* profiles, not noisy-data diameter fits.
The anchor is a frozen V163 candidate, NOT an independent true diameter/height.
Every returned value is an attainable upper bound, never a certified minimum.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
import math
import numpy as np
from scipy.optimize import least_squares
from v152_gls_core import GlsData, check_theta, CallCapReached
from v157_height_design import local_design

GROUPS = ('100000_ANON_02', '100000_ANON_03', '100000_ANON_04')
DESIGNS = ('free_hxy', 'height_sigma10', 'height_sigma1', 'exact_height')
DELTAS = (-5.0, 5.0)
SIGMAS = {'free_hxy': math.inf, 'height_sigma10': 10.0,
          'height_sigma1': 1.0, 'exact_height': 0.0}
OPTIONS = dict(method='trf', jac='3-point', loss='linear', diff_step=1e-5,
               ftol=1e-9, xtol=1e-9, gtol=1e-8, max_nfev=200)


def require(x: bool, message: str) -> None:
    if not x:
        raise ValueError(message)


def evaluate(theta, c, *, anchor, c0, data: GlsData, design: str) -> dict:
    """No model call. Keep geometric separation separate from observed noisy Q."""
    require(design in DESIGNS, 'UNKNOWN_DESIGN')
    t, a = check_theta(theta), check_theta(anchor)
    c, c0 = data.prediction(c), data.prediction(c0)
    sigma = SIGMAS[design]
    if sigma == 0:
        require(t[1] == a[1], 'EXACT_HEIGHT_MUST_BE_IDENTICAL')
    z = ((c-c0)/np.sqrt(data.vbar)).ravel()
    image = float(z@z)
    auxiliary = 0.0 if sigma == 0 or math.isinf(sigma) else float(((t[1]-a[1])/sigma)**2)
    r0 = ((c0-data.ybar)/np.sqrt(data.vbar)).ravel()
    score, score0 = data.score(c), data.score(c0)
    dq = float(score['Q_joint']-score0['Q_joint'])
    cross = float(2*r0@z)
    require(abs(dq-cross-image) <= max(1e-8, 1e-10*abs(score['Q_joint'])), 'Q_CHANGE_IDENTITY')
    return dict(theta=t.tolist(), image_distance_squared=image,
                hypothetical_auxiliary_distance_squared=auxiliary,
                design_distance_squared=image+auxiliary, observed_Q=score,
                observed_Q_change=dq, observed_Q_cross_term=cross,
                hypothetical_height_center_nm=float(a[1]),
                auxiliary_is_independent_measurement=False,
                interpretation='CONDITIONAL_NOISE_FREE_MEAN_SEPARATION_NOT_REAL_HEIGHT_DATA',
                reportable_D=None)


@dataclass
class Problem:
    group: str
    delta_D_nm: float
    design: str
    anchor: np.ndarray
    c0: np.ndarray
    data: GlsData
    jw: np.ndarray

    def __post_init__(self):
        require(self.group in GROUPS, 'UNAUTHORIZED_GROUP')
        require(self.delta_D_nm in DELTAS, 'UNAUTHORIZED_DELTA')
        require(self.design in DESIGNS, 'UNAUTHORIZED_DESIGN')
        self.anchor = check_theta(self.anchor)
        self.c0 = self.data.prediction(self.c0)
        self.jw = np.asarray(self.jw, float)
        require(self.jw.shape == (169,4) and np.isfinite(self.jw).all(), 'BAD_JACOBIAN')
        self.fixed_D = float(self.anchor[0] + self.delta_D_nm)
        t = self.anchor.copy(); t[0] = self.fixed_D; check_theta(t)
        self.indices = np.array([2,3] if self.design == 'exact_height' else [1,2,3], int)
        self.low = np.array([30.,350.,-500.,-500.])[self.indices]
        self.high = np.array([200.,550.,500.,500.])[self.indices]
        self.scale = np.array([1.,50.,280.,280.])[self.indices]
        self.local = local_design(self.jw, sigma_h=SIGMAS[self.design])
        self.linear_theta = self.anchor + self.delta_D_nm*np.r_[1., self.local['compensation_nm_per_nm']]
        check_theta(self.linear_theta)
        if self.design == 'exact_height':
            require(self.linear_theta[1] == self.anchor[1], 'LINEAR_EXACT_HEIGHT')

    @property
    def task_id(self):
        return f"PROFILE_{self.group}_{'m5' if self.delta_D_nm < 0 else 'p5'}_{self.design}"

    def full(self, u):
        u = np.asarray(u, float)
        require(u.shape == self.indices.shape and np.isfinite(u).all(), 'BAD_NUISANCE_VECTOR')
        t = self.anchor.copy(); t[0] = self.fixed_D; t[self.indices] = u
        return check_theta(t)

    def residual(self, theta, c):
        t = check_theta(theta)
        require(t[0] == self.fixed_D, 'FIXED_D_DRIFT')
        if self.design == 'exact_height':
            require(t[1] == self.anchor[1], 'FIXED_H_DRIFT')
        c = self.data.prediction(c)
        r = ((c-self.c0)/np.sqrt(self.data.vbar)).ravel()
        sigma = SIGMAS[self.design]
        if math.isfinite(sigma) and sigma > 0:
            r = np.r_[r, (t[1]-self.anchor[1])/sigma]
        return r

    def starts(self):
        a = self.anchor.copy(); a[0] = self.fixed_D
        return [self.linear_theta.copy(), a]


def solve_profile(problem: Problem, predict: Callable, counts: Callable,
                  persist: Callable, *, prior_witnesses=(), per_start_cap=200,
                  task_cap=400, optimizer=least_squares) -> dict:
    """Two predetermined starts, cached legal witnesses retained on budget stop.
    predict must persistently charge BEFORE calling the real forward model.
    persist failure or a model error propagates; it is never a numerical success.
    """
    require(type(per_start_cap) is int and per_start_cap > 0, 'BAD_START_CAP')
    require(task_cap == 2*per_start_cap, 'TASK_CAP_MUST_EQUAL_TWO_START_CAPS')
    cache = {}; best = None; sequence = 0; start_rows = []; seen_starts = set()

    def register(t, c, origin):
        nonlocal best, sequence
        t=check_theta(t); c=problem.data.prediction(c)
        require(t[0] == problem.fixed_D, 'FIXED_D_DRIFT')
        score=evaluate(t,c,anchor=problem.anchor,c0=problem.c0,data=problem.data,design=problem.design)
        item={**score,'C':c.tolist(),'origin':origin,'group':problem.group,
              'delta_D_nm':problem.delta_D_nm,'design':problem.design,'sequence':sequence}
        persist('evaluation',sequence,item); sequence+=1
        cache[tuple(t)] = item
        if best is None or item['design_distance_squared'] < best['design_distance_squared']:
            best = item
            persist('best',0,best)
        return item

    for witness in prior_witnesses:
        register(witness['theta'],witness['C'],'V163_VALIDATED_WITNESS:'+witness['source_id'])
    baseline = cache.get(tuple(problem.linear_theta))
    start_task=int(counts())
    for idx, initial in enumerate(problem.starts()):
        initial=check_theta(initial); key=tuple(initial)
        before=int(counts())
        if key in seen_starts:
            row=dict(index=idx,state='SKIPPED_DUPLICATE_INITIAL_POINT',initial_theta=initial.tolist(),actual_calls=0)
            start_rows.append(row);persist('start',idx,row);continue
        seen_starts.add(key)
        def residual(u):
            nonlocal baseline
            t=problem.full(u); key_t=tuple(t)
            if key_t not in cache:
                used=int(counts())
                if used-before >= per_start_cap or used-start_task >= task_cap:
                    raise CallCapReached('FROZEN_START_OR_TASK_REAL_FORWARD_CAP')
                c=predict(t)
                item=register(t,c,f'NEW_START_{idx}')
            else:
                item=cache[key_t]
            if key_t == tuple(problem.linear_theta): baseline=item
            return problem.residual(t,item['C'])
        try:
            # Evaluate the legal initial point before optimization so a witness
            # survives even when the solver terminates at the call cap.
            residual(initial[problem.indices])
            result=optimizer(residual,initial[problem.indices],bounds=(problem.low,problem.high),
                             x_scale=problem.scale,**OPTIONS)
            t=problem.full(result.x)
            rr=residual(result.x)
            reported=float(2*result.cost); actual=float(rr@rr)
            require(abs(actual-reported)<=max(1e-10,1e-8*abs(actual)), 'HALF_COST_OR_STALE_FUN')
            row=dict(index=idx,state='OPTIMIZER_RETURNED',success=bool(result.success),
                     solver_status=int(result.status),message=str(result.message),
                     initial_theta=initial.tolist(),final_theta=t.tolist(),
                     nfev=int(result.nfev),njev=None if result.njev is None else int(result.njev),
                     final_objective=actual,scipy_cost=float(result.cost),
                     optimality=float(result.optimality),active_mask=np.asarray(result.active_mask).tolist(),
                     actual_calls=int(counts())-before)
        except CallCapReached as exc:
            row=dict(index=idx,state='PARTIAL_BUDGET',success=False,reason=str(exc),
                     initial_theta=initial.tolist(),actual_calls=int(counts())-before)
        except Exception as exc:
            import traceback
            persist('start_failure',idx,dict(error=repr(exc),traceback=traceback.format_exc(),
                                           actual_calls=int(counts())-before))
            raise
        require(row['actual_calls']<=per_start_cap, 'START_BUDGET_OVERRUN')
        start_rows.append(row);persist('start',idx,row)
    require(best is not None and baseline is not None, 'MISSING_FEASIBLE_BASELINE')
    tol=max(1e-10,1e-8*abs(baseline['design_distance_squared']))
    require(best['design_distance_squared']<=baseline['design_distance_squared']+tol,'LOST_BETTER_WITNESS')
    require(int(counts())-start_task<=task_cap,'TASK_BUDGET_OVERRUN')
    terminated=all(r['state']=='SKIPPED_DUPLICATE_INITIAL_POINT' or
                   (r['state']=='OPTIMIZER_RETURNED' and r['success']) for r in start_rows)
    return dict(group=problem.group,delta_D_nm=problem.delta_D_nm,design=problem.design,
                fixed_D_nm=problem.fixed_D,anchor_theta=problem.anchor.tolist(),
                method='BOUNDED_FIXED_D_MODEL_SEPARATION_TWO_PREDECLARED_STARTS',
                optimizer_options={**OPTIONS,'x_scale':problem.scale.tolist()},
                best=best,linear_witness=baseline,starts=start_rows,
                actual_new_calls=int(counts())-start_task,
                search_state='LOCAL_TERMINATIONS_ONLY' if terminated else 'PARTIAL_SEARCH',
                interpretation='ATTAINABLE_UPPER_BOUND_NOT_GLOBAL_MINIMUM_NOT_CI',
                reportable_D=None)


def pool_profiles(profiles, data: GlsData, c0, anchor):
    """Explicit post-hoc COMMON feasible pool; no calls and no hidden re-optimization."""
    require(len(profiles)==4 and {p['design'] for p in profiles}==set(DESIGNS), 'POOL_MISSING_DESIGNS')
    require(len({(p['group'],p['fixed_D_nm']) for p in profiles})==1,'CROSS_GROUP_OR_D_POOL')
    candidates=[]
    for p in profiles:
        candidates.extend([p['best'],p['linear_witness']])
    out={}
    for design in DESIGNS:
        values=[]
        for row in candidates:
            if design=='exact_height' and row['theta'][1]!=anchor[1]:continue
            s=evaluate(row['theta'],row['C'],anchor=anchor,c0=c0,data=data,design=design)
            values.append({**s,'C':row['C'],'source_design':row['design'],
                           'source_origin':row['origin'],'source_sequence':row['sequence']})
        require(bool(values),'NO_FEASIBLE_POOL_WITNESS')
        out[design]=min(values,key=lambda r:r['design_distance_squared'])
    vals=[out[x]['design_distance_squared'] for x in DESIGNS]
    require(all(a<=b+max(1e-10,1e-8*abs(b)) for a,b in zip(vals,vals[1:])), 'COMMON_POOL_MONOTONICITY')
    return dict(group=profiles[0]['group'],fixed_D_nm=profiles[0]['fixed_D_nm'],
                own_optimizer_results_preserved=True,common_pool_minima=out,
                interpretation='ATTAINABLE_COMMON_POOL_UPPER_BOUNDS_NOT_GLOBAL_MINIMA',reportable_D=None)
