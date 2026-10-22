"""F2 identity lock. No C-map fallback; no assertion of physical qualification."""
from __future__ import annotations
import hashlib,json,time
from pathlib import Path
import numpy as np
from observation_adapter import file_sha256,array_sha

class ModelLockError(RuntimeError):pass
class SessionBudgetStop(RuntimeError):pass


def verify_code_lock(expected, tools_dir=None):
    root=Path(tools_dir or Path(__file__).parent)
    actual={}
    for name,sha in expected.items():
        if Path(name).name!=name:raise ModelLockError('Lock names must be local module filenames')
        p=root/name
        if not p.is_file():raise ModelLockError(f'Missing numerical dependency {name}')
        actual[name]=file_sha256(p)
        if actual[name]!=sha:raise ModelLockError(f'Unexpected dependency bytes: {name}; no silent implementation switch')
    return actual


class LockedF2:
    def __init__(self,core,expected_model_id,deadline=None,call_limit=5000000):
        if getattr(core,'kind',None)!='F2':raise ModelLockError('F2 required; C-map/F1/F3 cannot silently substitute')
        if core.model_id!=expected_model_id:raise ModelLockError('Library/core/config identity differs from approved F2')
        self.core=core;self.expected_model_id=expected_model_id
        self._func=getattr(core.forward,'__func__',core.forward)
        self.deadline=deadline;self.call_limit=int(call_limit);self.calls=0
    def __getattr__(self,k):return getattr(self.core,k)
    def forward(self,theta):
        if self.core.kind!='F2' or self.core.model_id!=self.expected_model_id or getattr(self.core.forward,'__func__',self.core.forward) is not self._func:
            raise ModelLockError('Bound forward changed during execution')
        if self.calls>=self.call_limit or (self.deadline is not None and time.monotonic()>=self.deadline):
            raise SessionBudgetStop('SESSION_LIMIT; save real best candidates; do not alter residual')
        self.calls+=1;return self.core.forward(theta)
    def C(self,D,h,x,y,score=True):
        o=self.forward((D,h,x,y));return o.score_C if score else o.C


def passport(model,points,tolerance=1e-12):
    originals=[model.forward(p).score_C.copy() for p in points]
    rows=[]
    for i in list(range(len(points)))+list(reversed(range(len(points)))):
        o=model.forward(points[i]);alias=model.C(*points[i]);e=float(np.max(abs(o.score_C-originals[i])))
        e2=float(np.max(abs(alias-o.score_C)))
        if not np.isfinite(o.score_C).all() or e>tolerance or e2>tolerance:
            raise ModelLockError('Model passport repeat/alias failure')
        rows.append(dict(theta=list(points[i]),max_abs_repeat=e,max_abs_alias=e2,
                         score_sha256=array_sha(o.score_C),model_id=o.model_id))
    return dict(kind='F2',model_id=model.model_id,rows=rows,
                role='NUMERICAL_BINDING_NOT_PHYSICAL_OR_EXPERIMENTAL_VALIDATION')
