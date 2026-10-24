"""One persistent atomic reservation ledger. No budget reset on resume.

Reservations (including failed/crashed) stay charged. Successful completion may
record fewer actual callbacks but does not refund the precharged hard limit.
"""
from __future__ import annotations
import sqlite3,time,json
from contextlib import closing
from pathlib import Path
class BudgetLimit(RuntimeError):pass
class DuplicateOperation(RuntimeError):pass
class Ledger:
    def __init__(self,location,limits):
        self.path=Path(location);self.path.parent.mkdir(parents=True,exist_ok=True);self.limits=dict(limits)
        with closing(sqlite3.connect(self.path,timeout=60)) as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS events (op TEXT PRIMARY KEY, metric TEXT NOT NULL, '
                       'reserved INTEGER NOT NULL, actual INTEGER, state TEXT NOT NULL, ts REAL NOT NULL, payload TEXT NOT NULL)')
    def get(self,op):
        with closing(sqlite3.connect(self.path,timeout=60)) as db:
            r=db.execute('SELECT metric,reserved,actual,state,payload FROM events WHERE op=?',(op,)).fetchone()
        return dict(zip(['metric','reserved','actual','state','payload'],r)) if r else None
    def spent(self,metric):
        with closing(sqlite3.connect(self.path,timeout=60)) as db:
            return int(db.execute('SELECT COALESCE(SUM(reserved),0) FROM events WHERE metric=?',(metric,)).fetchone()[0])
    def reserve(self,op,metric,n,payload):
        if not op or metric not in self.limits or type(n)!=int or n<=0:raise ValueError('INVALID_RESERVATION')
        db=sqlite3.connect(self.path,timeout=60,isolation_level=None)
        try:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM events WHERE op=?',(op,)).fetchone():raise DuplicateOperation(op)
            total=int(db.execute('SELECT COALESCE(SUM(reserved),0) FROM events WHERE metric=?',(metric,)).fetchone()[0])
            if total+n>self.limits[metric]:raise BudgetLimit(f'{metric} budget exceeded {total}+{n}>{self.limits[metric]}')
            db.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?)',(op,metric,n,None,'RESERVED',time.time(),json.dumps(payload,sort_keys=True)))
            db.execute('COMMIT')
        except Exception:
            if db.in_transaction:db.execute('ROLLBACK')
            raise
        finally:db.close()
    def finish(self,op,status,actual,details=None):
        if status not in ('COMPLETED','FAILED','BLOCKED'):raise ValueError('INVALID_EVENT_STATE')
        db=sqlite3.connect(self.path,timeout=60,isolation_level=None)
        try:
            db.execute('BEGIN IMMEDIATE')
            r=db.execute('SELECT reserved,state,payload FROM events WHERE op=?',(op,)).fetchone()
            if not r or r[1]!='RESERVED' or type(actual)!=int or not 0<=actual<=r[0]:
                raise ValueError('INVALID_SETTLEMENT')
            obj=json.loads(r[2]);obj['finish']=details or {}
            db.execute('UPDATE events SET actual=?,state=?,payload=? WHERE op=?',(actual,status,json.dumps(obj,sort_keys=True),op))
            db.execute('COMMIT')
        except Exception:
            if db.in_transaction:db.execute('ROLLBACK')
            raise
        finally:db.close()
    def summary(self):
        return {k:{'limit':v,'reserved':self.spent(k)} for k,v in self.limits.items()}
