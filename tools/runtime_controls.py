"""Small, strict runtime utilities; tests do not certify any optical result."""
from __future__ import annotations
import json,sqlite3,uuid
from pathlib import Path
import numpy as np
from scipy.stats import beta

class BudgetExceeded(RuntimeError):pass

class Ledger:
    def __init__(self,path,limits):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.limits=dict(limits)
        with sqlite3.connect(self.path) as c:
            c.execute('CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,kind TEXT,n INTEGER,status TEXT,detail TEXT)')
    def reserve(self,kind,n=1,detail=None):
        if kind not in self.limits or not isinstance(n,int) or isinstance(n,bool) or n<1:
            raise ValueError('Unknown resource or invalid count')
        c=sqlite3.connect(self.path,timeout=30,isolation_level=None)
        try:
            c.execute('BEGIN IMMEDIATE')
            used=int(c.execute('SELECT COALESCE(SUM(n),0) FROM events WHERE kind=?',(kind,)).fetchone()[0])
            if used+n>self.limits[kind]:raise BudgetExceeded(f'{kind}: {used}+{n}>{self.limits[kind]}')
            uid=uuid.uuid4().hex
            c.execute('INSERT INTO events VALUES(?,?,?,?,?)',(uid,kind,n,'RESERVED',json.dumps(detail or {},ensure_ascii=False)))
            c.commit();return uid
        except Exception:c.rollback();raise
        finally:c.close()
    def finish(self,uid,success):
        with sqlite3.connect(self.path) as c:
            row=c.execute('SELECT status FROM events WHERE id=?',(uid,)).fetchone()
            if row is None or row[0]!='RESERVED':raise ValueError('Unknown or already-finished event')
            c.execute('UPDATE events SET status=? WHERE id=?',('SUCCESS' if success else 'FAILED',uid))
    def counts(self):
        with sqlite3.connect(self.path) as c:
            return {k:int(c.execute('SELECT COALESCE(SUM(n),0) FROM events WHERE kind=?',(k,)).fetchone()[0]) for k in self.limits}

def cp_upper(k,n,confidence=.95):
    if not (isinstance(k,int) and isinstance(n,int)) or isinstance(k,bool) or isinstance(n,bool) or n<1 or not 0<=k<=n or not 0<confidence<1:
        raise ValueError('Invalid binomial inputs')
    if k==0:return float(1-(1-confidence)**(1/n))
    if k==n:return 1.
    return float(beta.ppf(confidence,k+1,n-k))

def exposure_nodes(t_us,pos_nm,center_us,T_us):
    t=np.asarray(t_us,float);p=np.asarray(pos_nm,float)
    if t.ndim!=1 or len(t)<2 or p.shape!=(len(t),3) or not np.isfinite(t).all() or not np.isfinite(p).all() or not np.all(np.diff(t)>0):
        raise ValueError('Finite strictly increasing path times and [x,y,h] positions required')
    if not np.isfinite([center_us,T_us]).all() or T_us<=0:raise ValueError('Invalid exposure')
    a=center_us-T_us/2;b=center_us+T_us/2
    if a<t[0] or b>t[-1]:raise ValueError('Path does not cover the complete exposure')
    q=np.r_[a,t[(t>a)&(t<b)],b]
    r=np.stack([np.interp(q,t,p[:,i]) for i in range(3)],axis=1)
    dt=np.diff(q);w=np.zeros(len(q));w[:-1]+=dt/2;w[1:]+=dt/2;w/=T_us
    if not np.isclose(w.sum(),1,rtol=0,atol=1e-12):raise RuntimeError('Incorrect exposure weights')
    return q,r,w

def exposure_observation(model,D,t_us,pos_nm,center_us,T_us):
    q,r,w=exposure_nodes(t_us,pos_nm,center_us,T_us)
    # Check all stored and interpolated exposure positions, never clip.
    for x,y,h in r:model.check_domain((D,h,x,y))
    mean_I=None;Ibg=None
    for (x,y,h),wt in zip(r,w):
        o=model.forward((D,h,x,y))
        if Ibg is None:Ibg=o.Ibg.copy();mean_I=np.zeros_like(o.I)
        elif not np.allclose(Ibg,o.Ibg,rtol=1e-12,atol=0):raise ValueError('Reference changes within exposure')
        mean_I+=wt*o.I
    C=(mean_I-Ibg)/Ibg
    s=(model.n-model.s)//2
    return dict(I=mean_I,Ibg=Ibg,C=C,score_C=C[s:s+model.s,s:s+model.s],
                time_nodes_us=q,positions_nm=r,weights=w,model_id=model.model_id)

def reportable(candidate_D, gates, reason_codes=None):
    required=('model_qualified','detected','optimizer_complete','profile_complete',
              'domain_valid','no_unresolved_boundary','size_compatible_unique',
              'numerical_error_qualified','noise_regime_qualified')
    failed=[k for k in required if gates.get(k) is not True]
    why=list(reason_codes or [])+failed
    valid=np.isfinite(candidate_D) if candidate_D is not None else False
    ok=bool(valid and not why)
    return dict(candidate_D=float(candidate_D) if valid else None,
                reportable_D=float(candidate_D) if ok else None,diameter_reportable=ok,
                reason_codes=why if valid else ['NO_FINITE_CANDIDATE']+why)
