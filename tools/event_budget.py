"""Single persistent atomic precharge ledger. Never delete or recreate in packagers."""
from __future__ import annotations
import json,sqlite3,time
from contextlib import closing
from pathlib import Path

class BudgetExceeded(RuntimeError):pass
class DuplicateOperation(RuntimeError):pass

class Ledger:
    def __init__(self,path,limits):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);self.limits=dict(limits)
        with closing(sqlite3.connect(self.path,timeout=60)) as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS events (op TEXT PRIMARY KEY, metric TEXT NOT NULL, '
                'units INTEGER NOT NULL, state TEXT NOT NULL, created REAL NOT NULL, '
                'finished REAL, actual INTEGER, payload_json TEXT NOT NULL)')
            db.commit()
    def get(self,op):
        with closing(sqlite3.connect(self.path,timeout=60)) as db:
            r=db.execute('SELECT metric,units,state,actual,payload_json FROM events WHERE op=?',(op,)).fetchone()
            return dict(metric=r[0],units=r[1],state=r[2],actual=r[3],payload=json.loads(r[4])) if r else None
    def spent(self,metric):
        with closing(sqlite3.connect(self.path,timeout=60)) as db:
            return int(db.execute('SELECT COALESCE(SUM(units),0) FROM events WHERE metric=?',(metric,)).fetchone()[0])
    def reserve(self,op,metric,units,payload=None):
        if not isinstance(op,str) or not op or metric not in self.limits or type(units)!=int or units<1:
            raise ValueError('INVALID_BUDGET_RESERVATION')
        with closing(sqlite3.connect(self.path,timeout=60,isolation_level=None)) as db:
            try:
                db.execute('BEGIN IMMEDIATE')
                if db.execute('SELECT 1 FROM events WHERE op=?',(op,)).fetchone():raise DuplicateOperation(op)
                used=int(db.execute('SELECT COALESCE(SUM(units),0) FROM events WHERE metric=?',(metric,)).fetchone()[0])
                if used+units>self.limits[metric]:raise BudgetExceeded(f'{metric}: {used}+{units}>{self.limits[metric]}')
                db.execute('INSERT INTO events (op,metric,units,state,created,payload_json) VALUES (?,?,?,?,?,?)',
                    (op,metric,units,'RESERVED',time.time(),json.dumps(payload or {},sort_keys=True)))
                db.execute('COMMIT')
            except Exception:
                if db.in_transaction:db.execute('ROLLBACK')
                raise
    def finish(self,op,state,actual,info=None):
        if state not in ('COMPLETED','FAILED','BLOCKED'):raise ValueError('INVALID_EVENT_STATE')
        with closing(sqlite3.connect(self.path,timeout=60,isolation_level=None)) as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT units,state,payload_json FROM events WHERE op=?',(op,)).fetchone()
            if row is None:raise ValueError('NO_PRIOR_BUDGET_RESERVATION')
            if row[1]!='RESERVED':raise ValueError('CANNOT_REWRITE_COMPLETED_EVENT')
            if type(actual)!=int or not 0<=actual<=row[0]:raise ValueError('ACTUAL_EXCEEDS_PRECHARGED')
            payload=json.loads(row[2]);payload['finish']=info or {}
            db.execute('UPDATE events SET state=?,finished=?,actual=?,payload_json=? WHERE op=?',
                (state,time.time(),actual,json.dumps(payload,sort_keys=True),op));db.execute('COMMIT')
