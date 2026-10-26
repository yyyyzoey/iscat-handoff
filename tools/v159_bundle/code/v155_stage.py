"""Production-facing single-group stage, also invoked by the supplied tests.
The repository loader/source lock is a separate workstation adapter.
"""
from __future__ import annotations
import hashlib, json, traceback
from pathlib import Path
from typing import Callable
import numpy as np
from v152_budget_store import BudgetStore, CountedPredictor, atomic_json, canonical, StoreError
from v152_gls_core import GlsData, CallCapReached, check_theta
from v155_pixel_diagnostics import diagnose, validate_pixel_record


def signature(data: GlsData, theta, source: dict) -> str:
    h = hashlib.sha256()
    h.update(canonical({'schema':'v155.pixel_stage.1', 'theta':check_theta(theta).tolist(), 'source':source}).encode())
    for arr in (data.y, data.variance):
        h.update(str(arr.shape).encode()); h.update(np.ascontiguousarray(arr, dtype=np.float64).tobytes())
    for name in ('v155_stage.py','v155_pixel_diagnostics.py','v152_gls_core.py','v152_budget_store.py'):
        h.update((Path(__file__).parent/name).read_bytes())
    return h.hexdigest()


def run_group(*, store: BudgetStore, task: str, owner: str, data: GlsData,
              theta, source: dict, model_contrast: Callable, out: Path, cap: int=40) -> dict:
    if cap != 40:
        raise ValueError('GROUP_CAP_MUST_MATCH_V155_CONTRACT_40')
    out = Path(out)
    sig = signature(data, theta, source)
    state = store.reserve(task, sig, 'LOCAL_INFORMATION', cap, owner)
    if state != 'RUNNING':
        doc = store.load_result(task, sig)
        if doc['execution_state'] != 'FINISHED':
            raise StoreError('FAILED_OR_PARTIAL_TASK_REQUIRES_FORENSICS_NOT_AUTO_RETRY')
        validate_pixel_record(doc['diagnostic'])
        return doc
    if store.counts()[task] != 0 or (out/'result.json').exists():
        raise StoreError('INCOMPLETE_EXISTING_TASK_REQUIRES_FORENSICS')
    pred = CountedPredictor(model_contrast, store, task, owner)
    out.mkdir(parents=True, exist_ok=True)
    atomic_json(out/'started.json',dict(signature=sig,source=source,theta=check_theta(theta).tolist(),state='RUNNING'))
    def snapshot(meta, c):
        atomic_json(out/'predictions'/f'{meta["index"]:03d}.json',
                    dict(signature=sig,**meta,C=c.tolist(),C_sha256=hashlib.sha256(c.tobytes()).hexdigest()))
    try:
        diagnostic = diagnose(data,theta,pred,snapshot)
        validated = validate_pixel_record(diagnostic)
        doc = dict(signature=sig, source=source, execution_state='FINISHED',
                   validation=validated, diagnostic=diagnostic,
                   actual_forward_attempts=store.counts()[task])
        atomic_json(out/'result.json',doc)
        store.seal(task,owner,'FINISHED',out/'result.json')
        return doc
    except Exception as exc:
        state='PARTIAL_BUDGET' if isinstance(exc,CallCapReached) else 'FAILED'
        failure=dict(signature=sig, source=source, execution_state=state,
                     error_type=type(exc).__name__,error=repr(exc),traceback=traceback.format_exc(),
                     actual_forward_attempts=store.counts()[task],reportable_D=None)
        atomic_json(out/'result.json',failure)
        store.seal(task,owner,state,out/'result.json')
        raise
