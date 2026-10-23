"""Atomic V140 *new* work ledger. Historical V137 budget breach stays separate.

Reserve before executing an expensive operation; even failure still consumes
reserved units. Retry under the same operation ID is disallowed unless the
checkpoint is identity-verified and NO calculation actually re-executes.
"""
from __future__ import annotations
import sqlite3,time
from contextlib import closing
from pathlib import Path
LIMITS={'BEM':0,'RENDER':12,'CAMERA':0,'F2':120000}
class BudgetExceeded(RuntimeError):pass
class DuplicateOperation(RuntimeError):pass
class Ledger:
    def __init__(self,path,limits=None):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.limits=dict(LIMITS if limits is None else limits)
        with closing(sqlite3.connect(self.path,timeout=30)) as c:
            c.execute('PRAGMA journal_mode=WAL')
            c.execute('CREATE TABLE IF NOT EXISTS budget_event (op TEXT PRIMARY KEY,metric TEXT NOT NULL,units INT NOT NULL,state TEXT NOT NULL,stamp REAL NOT NULL,note TEXT)')
            c.commit()
    def usage(self,metric):
        with closing(sqlite3.connect(self.path,timeout=30)) as c:
            return int(c.execute('SELECT COALESCE(SUM(units),0) FROM budget_event WHERE metric=?',(metric,)).fetchone()[0])
    def reserve(self,op,metric,units=1,note=''):
        if not isinstance(op,str) or not op or metric not in self.limits or not isinstance(units,int) or units<1:
            raise ValueError('Bad budget reservation')
        c=sqlite3.connect(self.path,timeout=30,isolation_level=None)
        try:
            c.execute('BEGIN IMMEDIATE')
            if c.execute('SELECT 1 FROM budget_event WHERE op=?',(op,)).fetchone():
                raise DuplicateOperation('Duplicate operation ID '+op)
            used=int(c.execute('SELECT COALESCE(SUM(units),0) FROM budget_event WHERE metric=?',(metric,)).fetchone()[0])
            if used+units>self.limits[metric]:raise BudgetExceeded(f'{metric} {used}+{units}>{self.limits[metric]}')
            c.execute('INSERT INTO budget_event VALUES (?,?,?,?,?,?)',(op,metric,units,'RESERVED',time.time(),note))
            c.execute('COMMIT')
        except Exception:
            if c.in_transaction:c.execute('ROLLBACK')
            raise
        finally:c.close()
    def finish(self,op,state,note=''):
        if state not in ('DONE','FAILED','BLOCKED'):raise ValueError('Unknown finish state')
        with closing(sqlite3.connect(self.path,timeout=30)) as c:
            r=c.execute('UPDATE budget_event SET state=?,note=? WHERE op=?',(state,note,op))
            if r.rowcount!=1:raise ValueError('Reservation not found')
            c.commit()
