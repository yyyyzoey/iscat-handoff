"""Atomic conservative budget reservations; reservation/failed attempt counts.

An F2 optimization must instrument every canonical forward call, INCLUDING
finite difference calls. Book a bounded batch BEFORE execution, settle actual
counts conservatively; never exceed allocation; crashes charge reservation.
"""
from __future__ import annotations
import sqlite3,time
from contextlib import closing
from pathlib import Path

LIMITS={'BEM':0,'RENDER':12,'CAMERA':0,'F2':120000}
class BudgetExceeded(RuntimeError):pass
class DuplicateOperation(RuntimeError):pass
class Budget:
    def __init__(self,path,limits=None):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.limits=dict(LIMITS if limits is None else limits)
        with closing(sqlite3.connect(self.path,timeout=30)) as c:
            c.execute('PRAGMA journal_mode=WAL')
            c.execute('CREATE TABLE IF NOT EXISTS events (op TEXT PRIMARY KEY,metric TEXT NOT NULL,units INTEGER NOT NULL,state TEXT NOT NULL,ts REAL,note TEXT)')
            c.commit()
    def spent(self,metric):
        with closing(sqlite3.connect(self.path,timeout=30)) as c:
            return int(c.execute('SELECT COALESCE(SUM(units),0) FROM events WHERE metric=?',(metric,)).fetchone()[0])
    def reserve(self,op,metric,units=1,note=''):
        if not op or metric not in self.limits or not isinstance(units,int) or units<1:raise ValueError('BAD_RESERVATION')
        c=sqlite3.connect(self.path,isolation_level=None,timeout=30)
        try:
            c.execute('BEGIN IMMEDIATE')
            if c.execute('SELECT 1 FROM events WHERE op=?',(op,)).fetchone():raise DuplicateOperation(op)
            n=int(c.execute('SELECT COALESCE(SUM(units),0) FROM events WHERE metric=?',(metric,)).fetchone()[0])
            if n+units>self.limits[metric]:raise BudgetExceeded(f'{metric} {n}+{units}>{self.limits[metric]}')
            c.execute('INSERT INTO events VALUES (?,?,?,?,?,?)',(op,metric,units,'RESERVED',time.time(),note))
            c.execute('COMMIT')
        except Exception:
            if c.in_transaction:c.execute('ROLLBACK')
            raise
        finally:c.close()
    def mark(self,op,status,note=''):
        if status not in ('COMPLETED','FAILED','BLOCKED'):raise ValueError('BAD_STATUS')
        with closing(sqlite3.connect(self.path,timeout=30)) as c:
            x=c.execute('UPDATE events SET state=?,note=? WHERE op=?',(status,note,op))
            if x.rowcount!=1:raise ValueError('UNKNOWN_OPERATION')
            c.commit()
