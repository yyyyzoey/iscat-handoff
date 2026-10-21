"""Check the actual loaded observation, not an unrelated toy forward.
These checks establish numerical repeatability only, NOT physical correctness.
"""
from __future__ import annotations
import time
import numpy as np

def deterministic_gate(model, points, repeats=3, atol=1e-12):
    points=[tuple(map(float,p)) for p in points]
    if not points or repeats<2: raise ValueError('At least one point and two repeats required')
    ref={};rows=[]
    for p in points:
        obs=model.forward(p)
        for name in ('I','Ibg','C','score_C'):
            a=np.asarray(getattr(obs,name))
            if not np.isfinite(a).all():raise ValueError(f'{p}: nonfinite {name}')
        if np.any(obs.Ibg<=0) or np.any(obs.I<0):raise ValueError('Invalid intensity')
        ref[p]=obs.score_C.copy()
    for j in range(repeats):
        # Interleave different parameters and memory allocations; avoid depending
        # on whatever happens to be in a freshly allocated block.
        scratch=np.full((125,125,3),complex(j+1,-j),dtype=np.complex128)
        order=points if j%2==0 else points[::-1]
        for p in order:
            start=time.perf_counter();obs=model.forward(p);elapsed=time.perf_counter()-start
            if not np.isfinite(obs.score_C).all():raise ValueError(f'{p}: nonfinite repeated image')
            err=float(np.max(np.abs(obs.score_C-ref[p])))
            alias=model.C(*p)
            alias_err=float(np.max(np.abs(alias-obs.score_C)))
            rows.append(dict(theta=list(p),repeat=j,max_abs_C_difference=err,
                             alias_max_abs_difference=alias_err,seconds=elapsed,
                             passed=bool(err<=atol and alias_err<=atol)))
        del scratch
    return dict(model_id=model.model_id,passed=all(r['passed'] for r in rows),
                atol=atol,scope='same-process numerical determinism and single-entry consistency',checks=rows)
