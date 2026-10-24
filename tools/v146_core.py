"""V146 numerical diagnostics, NOT calibrated confidence intervals or physics proofs.
No truth labels, simulator, random draws, renderer, or BEM invocation is accepted.
"""
from __future__ import annotations
import hashlib, json, math, os
from pathlib import Path
import numpy as np


def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20), b''): h.update(b)
    return h.hexdigest()


def array_sha(a):
    a=np.ascontiguousarray(a)
    return hashlib.sha256((str(a.shape)+'|'+str(a.dtype)+'|').encode()+a.tobytes()).hexdigest()


def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def save_json(path, obj):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    os.replace(tmp,p)


def read_json(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def finite_number(x):
    return isinstance(x,(int,float,np.integer,np.floating)) and not isinstance(x,(bool,np.bool_)) and math.isfinite(float(x))


def check_theta(theta, fixed_D=None):
    t=np.asarray(theta,float)
    if t.shape!=(4,) or not np.isfinite(t).all(): raise ValueError('BAD_THETA')
    lo=np.array([30.,350.,-500.,-500.]);hi=np.array([200.,550.,500.,500.])
    if np.any(t<lo) or np.any(t>hi): raise ValueError('THETA_OUTSIDE_DOMAIN_NO_CLIP')
    if fixed_D is not None and abs(float(t[0])-float(fixed_D))>1e-10:
        raise ValueError('INVALID_FIXED_D')
    return t


def valid_witness(theta, residual_L2, fixed_D=None):
    t=check_theta(theta,fixed_D)
    if not finite_number(residual_L2) or residual_L2<0:raise ValueError('BAD_LOSS')
    return {'D':float(t[0]),'theta':t.tolist(),'loss_L2':float(residual_L2)}


def observed_margin(witnesses, candidate_D):
    """Attainable finite losses, NOT lower bounds and NOT continuous intervals.
    epsilon >= returned margin exhibits a distant competing attainable point.
    epsilon < margin does NOT certify absence of unsearched solutions.
    """
    if not finite_number(candidate_D) or not 30<=candidate_D<=200:raise ValueError('BAD_CANDIDATE_D')
    pts=[valid_witness(w['theta'],w['loss_L2'],w.get('fixed_D')) for w in witnesses]
    if not pts:return {'status':'NO_VALID_WITNESSES','unknown_regions_remain':True}
    low=min(p['loss_L2'] for p in pts);half_goal=max(5.,.1*float(candidate_D))
    far=[p for p in pts if abs(p['D']-candidate_D)>half_goal]
    competitor=min(far,key=lambda p:p['loss_L2']) if far else None
    return {'candidate_D':float(candidate_D),'best_observed_L2':low,
            'diameter_half_tolerance_nm':half_goal,
            'lowest_observed_outside_tolerance':competitor,
            'epsilon_at_which_this_competitor_enters':None if competitor is None else max(0.,competitor['loss_L2']-low),
            'unknown_regions_remain':True,'certifies_unique_D':False,
            'scope':'EMPIRICAL_WITNESS_SENSITIVITY_NOT_95PCT_CI'}


def sensitivity_and_information_fractions(jD,Jn):
    d=np.asarray(jD,float).ravel();n=np.asarray(Jn,float)
    if n.ndim!=2 or n.shape[0]!=len(d) or not np.isfinite(d).all() or not np.isfinite(n).all():raise ValueError('BAD_JACOBIAN')
    norm=float(np.linalg.norm(d))
    if norm==0:return {'sensitivity_norm_fraction':None,'iid_equal_variance_information_fraction':None}
    e=d-n@np.linalg.lstsq(n,d,rcond=None)[0]
    ratio=float(np.linalg.norm(e)/norm)
    return {'sensitivity_norm_fraction':ratio,'iid_equal_variance_information_fraction':ratio**2,
            'scope':'LOCAL_LINEAR_ONLY; real noise requires covariance whitening'}


def ratio_contrast_and_variance(foreground,reference,read_noise=2.):
    """Fixed plug-in delta-method variance, CONDITIONAL high-count GLS diagnostic.
    Y,R denote stored photoelectron observations. Assumes independent reference
    and foreground frames and independent pixels, no clipping, saturation,
    background estimation/smoothing, motion, fitted amplitude or phase.
    This is not the exact Poisson-Gaussian likelihood and is not a 95% interval.
    """
    f=np.asarray(foreground,float);r=np.asarray(reference,float)
    if f.shape!=r.shape or f.shape not in ((17,17),(13,13)) or not np.isfinite(f).all() or not np.isfinite(r).all():
        raise ValueError('CAMERA_SHAPE_OR_NONFINITE')
    if not finite_number(read_noise) or read_noise<0 or np.any(f<0) or np.any(r<=0):
        raise ValueError('CAMERA_NONPOSITIVE_COUNTS_NO_CLIP')
    v=(f+read_noise**2)/(r*r)+(f*f)*(r+read_noise**2)/(r**4)
    c=(f-r)/r
    if not np.isfinite(v).all() or np.any(v<=0):raise ValueError('INVALID_VARIANCE')
    return c,v


def score_crop(a):
    a=np.asarray(a,float)
    if a.shape==(17,17):return a[2:15,2:15].copy()
    if a.shape==(13,13):return a.copy()
    raise ValueError('NOT_17_OR_13_CAMERA_ARRAY')


class CallsExhausted(RuntimeError):pass


class Predictor:
    def __init__(self,model,maximum):
        if type(maximum)!=int or maximum<1:raise ValueError('BAD_CALLBACK_CAP')
        self.model=model;self.maximum=maximum;self.used=0
    def __call__(self,theta):
        t=check_theta(theta)
        if self.used>=self.maximum:raise CallsExhausted('CALLBACK_CAP_REACHED')
        self.used+=1 # actual attempt is charged even if the model raises
        obj=self.model.forward(t)
        a=np.asarray(obj.score_C,float)
        if a.shape!=(13,13) or not np.isfinite(a).all():raise ValueError('BAD_MODEL_SCORE')
        return a


def choose_public_starts(bank_thetas,bank_scores,y,variance,max_starts=6):
    theta=np.asarray(bank_thetas,float);scores=np.asarray(bank_scores,float)
    if theta.ndim!=2 or theta.shape[1]!=4 or scores.shape!=(len(theta),13,13):raise ValueError('INVALID_BANK')
    if not np.isfinite(theta).all() or not np.isfinite(scores).all():raise ValueError('NONFINITE_BANK')
    losses=np.sum((scores-y)**2/variance,axis=(1,2));order=np.argsort(losses,kind='stable')
    selected=[]
    # Height-separated public basins. No original N/M theta or labels used.
    for lo,hi in [(350,400),(400,450),(450,500),(500,550.0000001)]:
        candidates=[int(i) for i in order if lo<=theta[i,1]<hi]
        if candidates and candidates[0] not in selected:selected.append(candidates[0])
    for i in order:
        if len(selected)>=max_starts:break
        if int(i) not in selected:selected.append(int(i))
    return [theta[i].tolist() for i in selected[:max_starts]]


def fit_camera(model,y,variance,starts,max_calls=2800,max_nfev=90):
    """Continuous D/h/x/y GLS fit. Returns candidates; never a reportable D.
    Saved finite evaluations survive interrupted/nonconverged local searches.
    """
    from scipy.optimize import least_squares
    y=np.asarray(y,float);v=np.asarray(variance,float)
    if y.shape!=(13,13) or v.shape!=y.shape or not np.isfinite(y).all() or not np.isfinite(v).all() or np.any(v<=0):raise ValueError('BAD_WEIGHTED_OBSERVATION')
    pred=Predictor(model,max_calls);sd=np.sqrt(v);all_seen=[];trials=[]
    def residual(t):
        C=pred(t);delta=C-y;z=delta/sd
        all_seen.append({'theta':list(map(float,t)),'Q':float(np.sum(z*z)),
                         'unscaled_L2':float(np.linalg.norm(delta))})
        return z.ravel()
    for s in starts:
        x0=check_theta(s)
        if pred.used>=max_calls:break
        try:
            r=least_squares(residual,x0,bounds=([30,350,-500,-500],[200,550,500,500]),
                x_scale=[50,50,140,140],method='trf',loss='linear',
                max_nfev=max_nfev,ftol=1e-10,xtol=1e-10,gtol=1e-10)
            trials.append({'start':x0.tolist(),'theta':r.x.tolist(),'Q':float(np.dot(r.fun,r.fun)),
                'success':bool(r.success),'status':int(r.status),'nfev':int(r.nfev),'message':str(r.message)})
        except Exception as e:
            trials.append({'start':x0.tolist(),'success':False,'error':repr(e)})
            if pred.used>=max_calls:break
    best=min(all_seen,key=lambda w:w['Q']) if all_seen else None
    converged=bool(best and any(t.get('success') and abs(t['Q']-best['Q'])<=1e-8*max(1.,best['Q']) for t in trials))
    return {'candidate_D':best['theta'][0] if best else None,'candidate_theta':best['theta'] if best else None,
            'best':best,'trials':trials,'optimizer_converged':converged,
            'attempted_starts':len(trials),'planned_starts':len(starts),
            'callback_cap_reached':pred.used>=max_calls,'actual_forward_calls':pred.used,
            'reportable_D':None,'confidence_interval':None,
            'estimator_kind':'FIXED_PLUGIN_DELTA_GLS_DEVELOPMENT',
            'reason_codes':['CAMERA_SIZING_COVERAGE_UNCALIBRATED','GLOBAL_PROFILE_NOT_CERTIFIED','EXPERIMENTAL_ABSOLUTE_NOT_VALIDATED']}


def fixed_d_minimize(model,D,y,starts,max_calls=1500,max_nfev=90,scale=1.):
    """Strictly three-dimensional nuisance optimization with D captured as constant.
    Uses fixed scalar scaling for conditioning, never changes the raw L2 metric.
    """
    from scipy.optimize import least_squares
    check_theta([D,450,0,0])
    y=np.asarray(y,float)
    if y.shape!=(13,13) or not np.isfinite(y).all() or not finite_number(scale) or scale<=0:raise ValueError('BAD_FIXED_D_INPUT')
    pred=Predictor(model,max_calls);seen=[];attempts=[]
    def fun(z):
        t=[float(D),*map(float,z)];a=pred(t)-y
        seen.append(valid_witness(t,float(np.linalg.norm(a)),D))
        return (a/scale).ravel()
    for z0 in starts:
        if pred.used>=max_calls:break
        if len(z0)!=3:raise ValueError('FIXED_D_OPTIMIZER_ACCEPTS_ONLY_HXY')
        check_theta([D,*z0])
        try:
            r=least_squares(fun,np.asarray(z0,float),bounds=([350,-500,-500],[550,500,500]),
                x_scale=[50,140,140],method='trf',max_nfev=max_nfev,ftol=1e-10,xtol=1e-10,gtol=1e-10)
            attempts.append({'start':list(z0),'theta':[float(D),*r.x.tolist()],
                'loss_L2':float(np.linalg.norm(r.fun)*scale),'success':bool(r.success),'status':int(r.status)})
        except Exception as exc:
            attempts.append({'start':list(z0),'success':False,'error':repr(exc)})
    best=min(seen,key=lambda w:w['loss_L2']) if seen else None
    return {'fixed_D':float(D),'best':best,'attempts':attempts,'actual_forward_calls':pred.used,
            'fixed_D_invariant_passed':all(w['theta'][0]==D for w in seen),
            'finite_witness_only':True,'global_uniqueness_certified':False}
