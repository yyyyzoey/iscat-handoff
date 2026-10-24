"""V148 engine: counted forward, per-start atomic checkpoints, 3 estimators, joint."""
from __future__ import annotations
import json, os, numpy as np
from scipy.optimize import least_squares, minimize
from pathlib import Path
class BudgetExceeded(RuntimeError):pass
class ForwardCounter:
    def __init__(self,model,global_cap,task_cap,ledger=None,op=None):
        self.model=model;self.global_cap=global_cap;self.task_cap=task_cap
        self.ledger=ledger;self.op=op;self.global_used=0;self.task_used=0
    def forward(self,theta):
        if self.global_used+1>self.global_cap or self.task_used+1>self.task_cap:
            raise BudgetExceeded(f'FORWARD_CAP global={self.global_used} task={self.task_used}')
        self.global_used+=1;self.task_used+=1
        if self.ledger is not None and self.op is not None:
            try:self.ledger.record_attempt(self.op)
            except Exception:pass
        return self.model.forward(tuple(float(v) for v in theta))
    @property
    def model_id(self):return self.model.model_id
def atomic_write_json(path,obj):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_name(p.name+'.tmp')
    with open(tmp,'w',encoding='utf-8') as f:
        json.dump(obj,f,ensure_ascii=False);f.flush();os.fsync(f.fileno())
    os.replace(tmp,p)
def e1_plugin_gls_variance(F,R,read_noise=2.0):
    return (F+read_noise**2)/(R*R)+(F*F)*(R+read_noise**2)/(R**4)
def e3_model_variance(Cm,R,read_noise=2.0):
    mu_F=R*(1.0+Cm)
    if np.any(mu_F<=0):raise ValueError('E3_NONPOSITIVE_MU_F')
    return (mu_F+read_noise**2)/(R*R)+(mu_F*mu_F)*(R+read_noise**2)/(R**4)
def fit_event(fc,Y,V,R,method,starts,task_cap,max_nfev=90):
    records=[];best=None
    for x0 in starts:
        if fc.task_used>=task_cap:
            records.append(dict(start=list(map(float,x0)),status='BUDGET_STOP'));break
        def res_plain(p):
            o=fc.forward(p);Cm=o.score_C;return (Cm-Y).ravel()
        def res_gls(p):
            o=fc.forward(p);Cm=o.score_C;return ((Cm-Y)/np.sqrt(np.maximum(V,1e-12))).ravel()
        def obj_pg(p):
            o=fc.forward(p);Cm=o.score_C;Vm=e3_model_variance(Cm,R)
            return float(np.sum((Cm-Y)**2/Vm+np.log(Vm)))
        try:
            if method=='E1_PLUGIN_DELTA_GLS':
                r=least_squares(res_gls,x0,method='trf',loss='linear',max_nfev=max_nfev,x_scale=[50.,50.,140.,140.],ftol=1e-10,xtol=1e-10,gtol=1e-10)
                rec=dict(start=list(map(float,x0)),theta=[float(v) for v in r.x],Q=float(2*r.cost),success=bool(r.success),status=int(r.status),nfev=int(r.nfev),actual_forwards=fc.task_used,exception=None)
            elif method=='E2_UNWEIGHTED_C_L2':
                r=least_squares(res_plain,x0,method='trf',loss='linear',max_nfev=max_nfev,x_scale=[50.,50.,140.,140.],ftol=1e-10,xtol=1e-10,gtol=1e-10)
                rec=dict(start=list(map(float,x0)),theta=[float(v) for v in r.x],Q=float(2*r.cost),success=bool(r.success),status=int(r.status),nfev=int(r.nfev),actual_forwards=fc.task_used,exception=None)
            elif method=='E3_MODEL_VAR_GAUSSIAN_QUASI':
                r=minimize(obj_pg,x0,method='L-BFGS-B',bounds=[(30.,200.),(350.,550.),(-500.,500.),(-500.,500.)],options=dict(maxiter=max_nfev))
                rec=dict(start=list(map(float,x0)),theta=[float(v) for v in r.x],Q=float(r.fun),success=bool(r.success),status=int(r.status),nfev=int(r.nfev),actual_forwards=fc.task_used,exception=None)
            records.append(rec)
            if rec.get('Q') is not None and (best is None or rec['Q']<best['Q']):best=rec
        except BudgetExceeded:
            records.append(dict(start=list(map(float,x0)),status='BUDGET_EXCEEDED'));break
        except Exception as exc:
            records.append(dict(start=list(map(float,x0)),status='EXCEPTION',error=repr(exc)[:160]))
    return records,best
def joint_shared_sufficient(Ys,Vs):
    Yi=np.stack([np.asarray(y,float) for y in Ys]);Vi=np.stack([np.asarray(v,float) for v in Vs])
    Vbar=1.0/np.sum(1.0/Vi,axis=0);Ybar=Vbar*np.sum(Yi/Vi,axis=0)
    K=float(np.sum((Yi-Ybar)**2/Vi))
    return Ybar,Vbar,K
