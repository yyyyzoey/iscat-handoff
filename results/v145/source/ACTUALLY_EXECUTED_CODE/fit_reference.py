"""Bounded continuous-D reconstruction reference. Not a physical validation claim.
A budget stop raises an exception; it NEVER changes the objective at the same theta.
The best finite evaluated point and individual optimizer exit states are retained.
"""
from __future__ import annotations
import numpy as np
from scipy.optimize import least_squares

class BudgetStop(RuntimeError): pass

class Objective:
    def __init__(self, model, image, total_limit=20000):
        self.model=model
        if np.iscomplexobj(image): raise ValueError('Static signed image must be real, not complex')
        self.image=np.asarray(image,dtype=float)
        if self.image.ndim!=2 or not np.isfinite(self.image).all(): raise ValueError('Finite real image required')
        self.scale=max(float(np.linalg.norm(self.image)),1e-6)
        self.limit=int(total_limit);self.calls=0;self.stop_at=self.limit;self.best=None;self.best_by_D={}
    def evaluate(self,theta):
        if self.calls>=min(self.limit,self.stop_at): raise BudgetStop('canonical query budget exhausted')
        self.calls+=1
        y=self.model.forward(theta).score_C
        if y.shape!=self.image.shape or not np.isfinite(y).all(): raise ValueError('Invalid model image')
        r=(y-self.image).ravel()/self.scale
        loss=float(np.linalg.norm(r)*self.scale)
        if self.best is None or loss<self.best['loss']:
            self.best=dict(theta=np.asarray(theta,float).tolist(),loss=loss)
        key=float(theta[0]);old=self.best_by_D.get(key)
        if old is None or loss<old['loss']:
            self.best_by_D[key]=dict(theta=np.asarray(theta,float).tolist(),loss=loss)
        return r

def bounds(model):
    return (np.array([model.Ds[0],model.Hs[0],-model.xy_limit,-model.xy_limit],float),
            np.array([model.Ds[-1],model.Hs[-1],model.xy_limit,model.xy_limit],float))

def absolute_jac(fun,p,lower,upper,steps):
    """Finite differences with physical-unit steps; one-sided at bounds."""
    p=np.asarray(p,float);cols=[]
    for j,step in enumerate(steps):
        a=p.copy();b=p.copy();a[j]=max(lower[j],p[j]-step);b[j]=min(upper[j],p[j]+step)
        if not b[j]>a[j]: raise ValueError('Zero finite-difference interval')
        cols.append((fun(b)-fun(a))/(b[j]-a[j]))
    return np.stack(cols,axis=1)

def solve_start(obj,x0,free,per_start_calls=2500,max_nfev=500):
    lo,hi=bounds(obj.model);free=np.array(free,dtype=int);full=np.asarray(x0,float).copy()
    if not np.all((full>=lo)&(full<=hi)): raise ValueError('Start outside model domain')
    n0=obj.calls;obj.stop_at=min(obj.limit,n0+int(per_start_calls))
    def f(p):
        x=full.copy();x[free]=p;return obj.evaluate(x)
    steps=np.array([.02,.02,.05,.05])[free]
    def jac(p):return absolute_jac(f,p,lo[free],hi[free],steps)
    try:
        r=least_squares(f,full[free],jac=jac,bounds=(lo[free],hi[free]),method='trf',
                        x_scale=np.array([50.,50.,140.,140.])[free],loss='linear',
                        max_nfev=int(max_nfev),ftol=1e-12,gtol=1e-12,xtol=1e-10)
        full[free]=r.x
        return dict(theta=full.tolist(),loss=float(np.linalg.norm(r.fun)*obj.scale),
                    success=bool(r.success),status=int(r.status),message=str(r.message),
                    optimality=float(r.optimality),nfev=int(r.nfev),njev=int(r.njev or 0),
                    canonical_calls=obj.calls-n0,budget_exhausted=False,
                    active_mask=r.active_mask.tolist())
    except BudgetStop:
        return dict(theta=full.tolist(),loss=None,success=False,status='BUDGET_EXHAUSTED',
                    canonical_calls=obj.calls-n0,budget_exhausted=True)
    finally:obj.stop_at=obj.limit

def fit_single(model,image,total_calls=20000,max_starts=6,offsets=None):
    """Public grid starts, multiple h basins; never takes truth as input."""
    obj=Objective(model,image,total_calls)
    offsets=offsets or [(0,0),(140,0),(-140,0),(0,140),(0,-140),
                        (112,112),(-112,112),(112,-112),(-112,-112)]
    scan=[];records=[];incomplete=False
    try:
        for D in model.Ds:
            for h in model.Hs:
                for x,y in offsets:
                    theta=[float(D),float(h),float(x),float(y)]
                    r=obj.evaluate(theta);scan.append((float(np.linalg.norm(r)),theta))
    except BudgetStop:incomplete=True
    scan.sort(key=lambda z:z[0])
    starts=[]
    # retain separated basins in the physical parameter space
    for loss,x in scan:
        if all(any(abs(np.array(x)-np.array(b))>np.array([20,40,100,100])) for b in starts):
            starts.append(x)
        if len(starts)>=max_starts:break
    # Ensure upper/lower axial regions have public starts when available.
    mid=float((model.Hs[0]+model.Hs[-1])/2)
    for side in (0,1):
        pool=[x for _,x in scan if (x[1]<=mid if side==0 else x[1]>mid)]
        if pool and not any(x[1]<=mid if side==0 else x[1]>mid for x in starts):
            if len(starts)>=max_starts:starts[-1]=pool[0]
            else:starts.append(pool[0])
    for x in starts:
        if obj.calls>=obj.limit:incomplete=True;break
        rec=solve_start(obj,x,[0,1,2,3])
        incomplete=incomplete or rec['budget_exhausted'];records.append(rec)
    finished=[r for r in records if r['success'] and r['loss'] is not None]
    sol=min(finished,key=lambda r:r['loss']) if finished else None
    best=obj.best
    if best is None:raise ValueError('No finite objective evaluation')
    tol=max(1e-12,1e-7*max(best['loss'],1e-12))
    guarded=sol is None or sol['loss']>best['loss']+tol
    chosen=best if guarded else sol
    theta=chosen['theta'];lo,hi=bounds(model)
    edge=[bool(theta[i]-lo[i]<.05 or hi[i]-theta[i]<.05) for i in range(4)]
    return dict(candidate_D=theta[0],theta=theta,loss=chosen['loss'],
                optimizer_converged=bool(sol is not None and not guarded),
                loss_guard_fallback=guarded,search_complete=not incomplete and len(records)==len(starts),
                boundary_flags=edge,starts=records,canonical_calls=obj.calls,
                model_id=model.model_id,reportable_D=None,diameter_reportable=False,
                reason_codes=['REQUIRES_FORWARD_QUALIFICATION_AND_COMPLETE_PROFILE'])

def diameter_profile(model,image,joint,step_nm=5.,total_calls=120000):
    """Finite multi-start profile, endpoints & joint D included, both directions.
    A completed prescribed search is NOT a mathematical global-optimum proof.
    """
    obj=Objective(model,image,total_calls)
    Ds=np.unique(np.r_[np.arange(model.Ds[0],model.Ds[-1]+1e-9,step_nm),
                       model.Ds,model.Ds[-1],joint['theta'][0]])
    midHs=np.linspace(model.Hs[0],model.Hs[-1],3)
    best_by_D={};attempts_by_D={float(d):[] for d in Ds};incomplete=False
    xy=joint['theta'][2:]
    for direction in (Ds,Ds[::-1]):
        warm=joint['theta'].copy()
        for D in direction:
            D=float(D)
            seeds=[[D,warm[1],warm[2],warm[3]],[D,joint['theta'][1],*xy]]
            seeds += [[D,float(h),*xy] for h in midHs]
            # Duplicate starts need not consume the budget.
            seen=set()
            for x in seeds:
                key=tuple(np.round(x,9))
                if key in seen:continue
                seen.add(key)
                if obj.calls>=obj.limit:incomplete=True;break
                before=obj.calls
                try:
                    witness=float(np.linalg.norm(obj.evaluate(x))*obj.scale)
                except BudgetStop:incomplete=True;break
                cand=dict(D=D,theta=x.copy(),loss=witness,witness_only=True)
                old=best_by_D.get(D)
                if old is None or cand['loss']<old['loss']:best_by_D[D]=cand
                rec=solve_start(obj,x,[1,2,3],per_start_calls=900,max_nfev=180)
                attempts_by_D[D].append({k:rec[k] for k in ('status','success','budget_exhausted','canonical_calls')})
                incomplete=incomplete or rec['budget_exhausted']
                # Preserve every finite better point at this D, including budget-stop evaluations.
                if rec['loss'] is not None and rec['loss']<best_by_D[D]['loss']:
                    best_by_D[D]=dict(D=D,theta=rec['theta'],loss=rec['loss'],witness_only=not rec['success'])
                local=obj.best_by_D.get(D)
                if local and local['loss']<best_by_D[D]['loss']:
                    best_by_D[D]=dict(D=D,theta=local['theta'],loss=local['loss'],witness_only=True)
            if D in best_by_D:warm=best_by_D[D]['theta'].copy()
            if obj.calls>=obj.limit:break
        if obj.calls>=obj.limit:break
    rows=[]
    for D in Ds:
        d=float(D);r=best_by_D.get(d,dict(D=d,theta=None,loss=None,witness_only=True)).copy()
        r['attempts']=attempts_by_D[d];rows.append(r)
    valid=[r for r in rows if r['loss'] is not None]
    best=min(valid,key=lambda r:r['loss']) if valid else None
    # New smaller loss is a candidate for a fresh 4D refinement, not silently ignored.
    return dict(model_id=model.model_id,rows=rows,canonical_calls=obj.calls,
                profile_complete=not incomplete and all(r['attempts'] for r in rows),
                best_profile=best,update_joint_required=bool(best and best['loss']<joint['loss']-max(1e-12,1e-7*joint['loss'])),
                reportable_D=None,scope='finite prescribed multi-start empirical profile; requires adaptive refinement and model-error envelope')

def fit_shared_D(model, frames, total_calls=150000, max_nfev=400, whitening=None):
    """ONE continuous D plus independent per-frame h/x/y, no true trajectory input.
    Default is noiseless/unweighted diagnostic. For counts, Codex must supply the
    specified fixed GLS whitening or use a joint count-background likelihood.
    This function does not certify exposure-blur modeling or diameter accuracy.
    """
    from scipy.sparse import lil_matrix
    frames=[np.asarray(f,float) for f in frames]
    if len(frames)<2 or not all(f.shape==frames[0].shape and np.isfinite(f).all() for f in frames):
        raise ValueError('At least two finite same-shape frames required')
    K=len(frames);P=frames[0].size
    scale=max(float(np.linalg.norm(np.concatenate([x.ravel() for x in frames]))),1e-6)
    low0,up0=bounds(model)
    low=np.r_[low0[0],np.tile(low0[1:],K)];up=np.r_[up0[0],np.tile(up0[1:],K)]
    sparse=lil_matrix((K*P,1+3*K),dtype=int)
    for k in range(K):
        sparse[k*P:(k+1)*P,0]=1;sparse[k*P:(k+1)*P,1+3*k:4+3*k]=1
    # A general cross-frame whitening destroys this sparsity pattern; do not reuse it.
    calls=0;best=None;records=[]
    def residual(p):
        nonlocal calls,best
        if calls+K>total_calls:raise BudgetStop('shared-D canonical-query budget exhausted')
        rr=[]
        for k,Y in enumerate(frames):
            theta=[p[0],*p[1+3*k:4+3*k]]
            calls+=1;rr.append((model.forward(theta).score_C-Y).ravel())
        raw=np.stack(rr)
        z=(np.asarray(whitening(raw),float) if whitening is not None else raw).ravel()/scale
        val=float(np.dot(z,z))
        if best is None or val<best['objective']:best=dict(parameters=p.tolist(),objective=val)
        return z
    D_starts=np.linspace(low0[0]+.15*(up0[0]-low0[0]),up0[0]-.15*(up0[0]-low0[0]),3)
    H_starts=np.array([.25,.75])*(up0[1]-low0[1])+low0[1]
    for D in D_starts:
        for H in H_starts:
            p=np.r_[D,np.tile([H,0,0],K)]
            try:
                r=least_squares(residual,p,bounds=(low,up),method='trf',
                                jac_sparsity=sparse.tocsr() if whitening is None else None,
                                x_scale=np.r_[50.,np.tile([50.,140.,140.],K)],
                                max_nfev=max_nfev,gtol=1e-12,ftol=1e-12,xtol=1e-10)
                records.append(dict(parameters=r.x.tolist(),objective=float(np.dot(r.fun,r.fun)),
                                    success=bool(r.success),status=int(r.status),message=str(r.message)))
            except BudgetStop:
                records.append(dict(success=False,status='BUDGET_EXHAUSTED'));break
        if calls>=total_calls-K:break
    if best is None:raise RuntimeError('No shared-D objective was evaluated')
    return dict(candidate_D=best['parameters'][0],parameters=best['parameters'],objective=best['objective'],
                starts=records,canonical_calls=calls,D_is_continuous=True,
                reportable_D=None,diameter_reportable=False,
                reason_codes=['REQUIRES_MODEL_QUALIFICATION_SHARED_D_PROFILE_AND_EXPOSURE_VALIDATION'])
