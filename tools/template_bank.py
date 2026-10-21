"""Public template initialization cache. NOT a physical interpolator.
Every cached image is evaluated by the SAME canonical model; the cache is used
only to choose public optimizer starts. Truth and observed-image values never
choose its coordinates. Final fits/profiles use canonical forward continuously.
"""
from __future__ import annotations
import hashlib, itertools, json
import numpy as np
from fit_reference import Objective, solve_start, bounds

def axis_with_midpoints(axis):
    a=np.asarray(axis,float)
    if a.ndim!=1 or len(a)<2 or not np.isfinite(a).all() or not np.all(np.diff(a)>0):
        raise ValueError("finite increasing axis required")
    return np.sort(np.r_[a,(a[:-1]+a[1:])/2])

class TemplateBank:
    def __init__(self, model, offsets, *, midpoints=True, strata=4, separation=(15,25,80,80)):
        if not isinstance(model.model_id,str):raise ValueError("model_id must be a bound identity")
        self.model_id=model.model_id
        self.strata=int(strata);self.separation=np.asarray(separation,float)
        if self.strata<1 or self.separation.shape!=(4,) or np.any(self.separation<=0):
            raise ValueError("bad strata/separation")
        lo,hi=bounds(model);self.h_range=(lo[1],hi[1])
        Ds=axis_with_midpoints(model.Ds) if midpoints else np.asarray(model.Ds,float)
        Hs=axis_with_midpoints(model.Hs) if midpoints else np.asarray(model.Hs,float)
        offsets=np.asarray(offsets,float)
        if offsets.ndim!=2 or offsets.shape[1]!=2 or not np.isfinite(offsets).all():
            raise ValueError("offsets must be finite Nx2")
        params=[];images=[]
        for D,H,(x,y) in itertools.product(Ds,Hs,offsets):
            p=np.asarray([D,H,x,y],float)
            if np.any(p<lo) or np.any(p>hi):
                raise ValueError("public bank coordinate outside declared domain")
            z=np.asarray(model.forward(p).score_C,float)
            if not np.isfinite(z).all():raise ValueError("non-finite bank prediction")
            if images and z.shape!=images[0].shape:raise ValueError("inconsistent image shape")
            params.append(p);images.append(z.copy())
        self.theta=np.asarray(params)
        self.shape=images[0].shape
        self.images=np.asarray(images)
        self.matrix=self.images.reshape(len(images),-1)
        identity=json.dumps(dict(model_id=self.model_id,theta=self.theta.tolist()),sort_keys=True).encode()
        self.bank_id=hashlib.sha256(identity+self.images.tobytes()).hexdigest()
        self.n_queries=len(images)
    def manifest(self):
        return dict(model_id=self.model_id,bank_id=self.bank_id,n_templates=len(self.theta),
                    canonical_precomputation_queries=self.n_queries,score_shape=list(self.shape),
                    role="PUBLIC_INITIALIZATION_CACHE_ONLY",uses_true_case_file=False,
                    h_strata=self.strata)
    def select_starts(self,image,max_starts=6):
        Y=np.asarray(image,float)
        if Y.shape!=self.shape or not np.isfinite(Y).all():raise ValueError("invalid observation")
        if max_starts<self.strata:raise ValueError("max_starts must cover declared height strata")
        # Direct differences avoid cancellation of Gram-form squared residuals.
        losses=np.linalg.norm(self.matrix-Y.ravel()[None,:],axis=1)
        order=np.argsort(losses,kind='stable')
        edges=np.linspace(*self.h_range,self.strata+1)
        selected=[]
        for b in range(self.strata):
            eligible=(self.theta[:,1]>=edges[b]) & (
                self.theta[:,1]<=edges[b+1] if b==self.strata-1 else self.theta[:,1]<edges[b+1])
            hit=[i for i in order if eligible[i]]
            if hit:selected.append(int(hit[0]))
        for i in order:
            if len(selected)>=max_starts:break
            if int(i) in selected:continue
            if all(np.any(abs(self.theta[i]-self.theta[j])>self.separation) for j in selected):
                selected.append(int(i))
        # A small synthetic grid may have fewer separated basins.
        return self.theta[selected].copy(), losses[selected].copy(),float(losses[order[0]])

def fit_with_bank(model,image,bank,*,total_calls=20000,max_starts=6):
    if model.model_id!=bank.model_id:raise ValueError("bank/model identity mismatch")
    starts,_,scan_best=bank.select_starts(image,max_starts)
    obj=Objective(model,image,total_calls)
    records=[];incomplete=False
    for x in starts:
        if obj.calls>=obj.limit:
            incomplete=True;break
        rec=solve_start(obj,x,[0,1,2,3],per_start_calls=2500,max_nfev=500)
        records.append(rec)
        incomplete=incomplete or rec['budget_exhausted']
    if obj.best is None:raise RuntimeError("no objective point evaluated")
    finished=[r for r in records if r['success'] and r['loss'] is not None]
    sol=min(finished,key=lambda r:r['loss']) if finished else None
    tol=max(1e-12,1e-7*max(obj.best['loss'],1e-12))
    guarded=sol is None or sol['loss']>obj.best['loss']+tol
    chosen=obj.best if guarded else sol
    theta=chosen['theta'];lo,hi=bounds(model)
    edges=[bool(theta[i]-lo[i]<.05 or hi[i]-theta[i]<.05) for i in range(4)]
    return dict(candidate_D=theta[0],theta=theta,loss=chosen['loss'],
                optimizer_converged=bool(sol is not None and not guarded),
                loss_guard_fallback=guarded,search_complete=not incomplete and len(records)==len(starts),
                boundary_flags=edges,starts=records,canonical_calls=obj.calls,
                bank_id=bank.bank_id,scan_best_loss=scan_best,
                bank_calls_separate_global=bank.n_queries,model_id=model.model_id,
                reportable_D=None,diameter_reportable=False,
                reason_codes=["NEEDS_PHYSICAL_QUALIFICATION_COMPLETE_PROFILE_AND_REPORTABILITY"])
