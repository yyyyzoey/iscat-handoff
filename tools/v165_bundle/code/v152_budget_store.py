"""Durable, fail-closed budget primitives; no legacy ledger is modified.

Reservations are deliberately cumulative and never refunded. The complete task
plan must fit the phase/global caps before starting. This prevents the previous
whole-task refund bugs. Interrupted tasks require explicit forensic recovery;
there is no automatic owner transfer or revision/retry mechanism here.
"""
from __future__ import annotations
import hashlib, json, os, sqlite3, time, uuid
from pathlib import Path
from contextlib import contextmanager
import numpy as np
from v152_gls_core import CallCapReached

class StoreError(RuntimeError): pass


def canonical(o):
    return json.dumps(o, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def atomic_json(path, obj):
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name+'.'+uuid.uuid4().hex+'.tmp')
    payload = (canonical(obj)+'\n').encode('utf-8')
    try:
        with tmp.open('xb') as f:
            f.write(payload); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, p)
        if os.name == 'posix':
            fd = os.open(p.parent, os.O_RDONLY)
            try: os.fsync(fd)
            finally: os.close(fd)
    finally:
        if tmp.exists(): tmp.unlink()
    if p.read_bytes() != payload: raise StoreError('atomic result readback mismatch')
    return hashlib.sha256(payload).hexdigest()


class BudgetStore:
    def __init__(self, path, plan_id, phases, total):
        if type(total) is not int or total < 1 or any(type(v) is not int or v < 0 for v in phases.values()):
            raise ValueError('invalid budget')
        if sum(phases.values()) > total: raise ValueError('phase reservations exceed global cap')
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        self.phases = dict(phases); self.total = total
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS metadata (id INTEGER PRIMARY KEY, value TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, signature TEXT NOT NULL, '
                       'phase TEXT NOT NULL, cap INTEGER NOT NULL, used INTEGER NOT NULL, '
                       'owner TEXT NOT NULL, state TEXT NOT NULL, result_path TEXT, result_sha TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS attempts (task TEXT NOT NULL, seq INTEGER NOT NULL, '
                       'theta TEXT NOT NULL, state TEXT NOT NULL, detail TEXT, ts REAL NOT NULL, '
                       'PRIMARY KEY(task,seq))')
            meta = canonical(dict(plan_id=plan_id, phases=phases, total=total))
            old = db.execute('SELECT value FROM metadata WHERE id=1').fetchone()
            if old and old[0] != meta: raise StoreError('existing ledger identity mismatch')
            if not old: db.execute('INSERT INTO metadata VALUES (1,?)', (meta,))

    @contextmanager
    def db(self):
        con = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        try:
            con.execute('PRAGMA synchronous=FULL')
            con.execute('BEGIN IMMEDIATE')
            yield con
            con.commit()
        except BaseException:
            if con.in_transaction: con.rollback()
            raise
        finally: con.close()

    def reserve(self, task, signature, phase, cap, owner):
        if phase not in self.phases or type(cap) is not int or cap < 1 or not all(isinstance(v,str) and v for v in (task,signature,owner)):
            raise ValueError('invalid task reservation')
        with self.db() as db:
            old = db.execute('SELECT signature,phase,cap,owner,state FROM tasks WHERE id=?', (task,)).fetchone()
            if old:
                if old[:3] != (signature,phase,cap): raise StoreError('task signature changed')
                if old[4] == 'RUNNING' and old[3] != owner: raise StoreError('task owned elsewhere; forensic recovery required')
                return old[4]
            all_caps = db.execute('SELECT COALESCE(SUM(cap),0) FROM tasks').fetchone()[0]
            phase_caps = db.execute('SELECT COALESCE(SUM(cap),0) FROM tasks WHERE phase=?',(phase,)).fetchone()[0]
            if all_caps+cap > self.total or phase_caps+cap > self.phases[phase]:
                raise CallCapReached('reservation exceeds frozen plan')
            db.execute('INSERT INTO tasks VALUES (?,?,?,?,0,?,\'RUNNING\',NULL,NULL)', (task,signature,phase,cap,owner))
        return 'RUNNING'

    def charge(self, task, owner, theta, detail=None):
        encoded = canonical([float(x) for x in theta])
        with self.db() as db:
            row = db.execute('SELECT cap,used,owner,state FROM tasks WHERE id=?',(task,)).fetchone()
            if not row or row[2] != owner or row[3] != 'RUNNING': raise StoreError('no owned active reservation')
            cap, used = row[:2]
            if used >= cap: raise CallCapReached('persistent task cap reached')
            # Global and phase safety also follow from immutable reservation sums.
            seq = used+1
            charge_detail = dict(detail or {})
            charge_detail.update(task_id=task, ledger_seq=seq, requested_theta=[float(x) for x in theta])
            charge_encoded = canonical(charge_detail)
            db.execute('UPDATE tasks SET used=? WHERE id=?', (seq,task))
            db.execute('INSERT INTO attempts VALUES (?,?,?,\'CHARGED\',?,?)', (task,seq,encoded,charge_encoded,time.time()))
            return seq

    def returned(self, task, seq, state, detail):
        if state not in ('RETURNED','MODEL_ERROR'): raise ValueError('invalid attempt final state')
        encoded = canonical(detail)
        with self.db() as db:
            old = db.execute('SELECT state,detail FROM attempts WHERE task=? AND seq=?',(task,seq)).fetchone()
            if not old or old[0] != 'CHARGED': raise StoreError('attempt absent or already finalized')
            charged = json.loads(old[1]) if old[1] is not None else {}
            returned = dict(detail or {})
            overlap = set(charged) & set(returned)
            for key in overlap:
                if charged[key] != returned[key]:
                    raise StoreError('return metadata changes charge field: ' + key)
            charged.update(returned)
            db.execute('UPDATE attempts SET state=?,detail=? WHERE task=? AND seq=?',(state,canonical(charged),task,seq))

    def seal(self, task, owner, state, result_path):
        if state not in ('FINISHED','PARTIAL_BUDGET','FAILED'): raise ValueError('invalid task state')
        p=Path(result_path).resolve(); raw=p.read_bytes(); doc=json.loads(raw)
        digest=hashlib.sha256(raw).hexdigest()
        with self.db() as db:
            row=db.execute('SELECT signature,owner,state,result_sha FROM tasks WHERE id=?',(task,)).fetchone()
            if not row or row[1]!=owner or doc.get('signature')!=row[0]: raise StoreError('task / result identity mismatch')
            if row[2]!='RUNNING':
                if row[2]==state and row[3]==digest: return
                raise StoreError('cannot rewrite a sealed task')
            unknown=db.execute("SELECT COUNT(*) FROM attempts WHERE task=? AND state='CHARGED'",(task,)).fetchone()[0]
            if unknown: raise StoreError('unfinalized attempts; cannot seal task')
            db.execute('UPDATE tasks SET state=?,result_path=?,result_sha=? WHERE id=?',(state,str(p),digest,task))

    def load_result(self, task, signature):
        with self.db() as db:
            row=db.execute('SELECT signature,state,result_path,result_sha FROM tasks WHERE id=?',(task,)).fetchone()
        if not row or row[0]!=signature or row[1]=='RUNNING': raise StoreError('no sealed result with exact identity')
        raw=Path(row[2]).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=row[3]: raise StoreError('result hash mismatch')
        return json.loads(raw)

    def counts(self):
        with self.db() as db:
            return dict(db.execute('SELECT id,used FROM tasks').fetchall())


class CountedPredictor:
    def __init__(self, model_callable, store, task, owner):
        self.model_callable=model_callable; self.store=store; self.task=task; self.owner=owner
    def __call__(self, theta):
        seq=self.store.charge(
            self.task,
            self.owner,
            theta,
            detail=dict(start_index=None, kind='COUNTED_PREDICTOR', invocation='counted_predictor'),
        )
        try:
            c=np.asarray(self.model_callable(theta),dtype=float)
            if c.shape!=(13,13) or not np.isfinite(c).all(): raise ValueError('bad model contrast array')
        except Exception as exc:
            self.store.returned(
                self.task,
                seq,
                'MODEL_ERROR',
                dict(
                    error=repr(exc),
                    error_type=type(exc).__name__,
                    traceback='',
                    start_index=None,
                    kind='COUNTED_PREDICTOR',
                ),
            )
            raise
        self.store.returned(
            self.task,
            seq,
            'RETURNED',
            dict(
                C_sha256=hashlib.sha256(np.ascontiguousarray(c).tobytes()).hexdigest(),
                returned_theta=[float(x) for x in theta],
                start_index=None,
                kind='COUNTED_PREDICTOR',
            ),
        )
        return c
