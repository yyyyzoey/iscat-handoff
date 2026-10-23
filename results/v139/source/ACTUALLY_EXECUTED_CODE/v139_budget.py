"""Atomic and conservative new-V139 budget reservations.

An event is charged at reservation, including crashes/failed attempts. Replays
require a verified checkpoint and MUST NOT call the expensive function again.
This component is a ledger primitive; scripts have to call it explicitly.
"""
from __future__ import annotations
import sqlite3, time
from contextlib import closing
from pathlib import Path

LIMITS={'F2':120000,'RENDER':12,'CAMERA':0,'BEM':0}
class BudgetExceeded(RuntimeError):pass
class DuplicateOperation(RuntimeError):pass

class BudgetLedger:
    def __init__(self,path,limits=None):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.limits=dict(LIMITS if limits is None else limits)
        with closing(sqlite3.connect(self.path,timeout=30)) as c:
            c.execute('PRAGMA journal_mode=WAL')
            c.execute('CREATE TABLE IF NOT EXISTS v139_events (op TEXT PRIMARY KEY, metric TEXT NOT NULL, units INTEGER NOT NULL, state TEXT NOT NULL, date REAL NOT NULL, note TEXT)')
            c.commit()
    def spent(self,metric):
        with closing(sqlite3.connect(self.path,timeout=30)) as c:
            return int(c.execute('SELECT COALESCE(SUM(units),0) FROM v139_events WHERE metric=?',(metric,)).fetchone()[0])
    def reserve(self,op,metric,units=1,note=''):
        if not op or metric not in self.limits or not isinstance(units,int) or units<1:
            raise ValueError('invalid operation/metric/units')
        c=sqlite3.connect(self.path,timeout=30,isolation_level=None)
        try:
            c.execute('BEGIN IMMEDIATE')
            if c.execute('SELECT 1 FROM v139_events WHERE op=?',(op,)).fetchone():raise DuplicateOperation('previous reservation exists: '+op)
            used=int(c.execute('SELECT COALESCE(SUM(units),0) FROM v139_events WHERE metric=?',(metric,)).fetchone()[0])
            if used+units>self.limits[metric]:raise BudgetExceeded(f'{metric}: used {used} + {units} > {self.limits[metric]}')
            c.execute('INSERT INTO v139_events VALUES (?,?,?,?,?,?)',(op,metric,units,'RESERVED',time.time(),note))
            c.execute('COMMIT')
        except Exception:
            if c.in_transaction:c.execute('ROLLBACK')
            raise
        finally:c.close()
    def mark(self,op,state,note=''):
        if state not in ('COMPLETED','FAILED','BLOCKED'):
            raise ValueError('invalid final state')
        with closing(sqlite3.connect(self.path,timeout=30)) as c:
            cursor=c.execute('UPDATE v139_events SET state=?,note=? WHERE op=?',(state,note,op))
            if cursor.rowcount!=1:raise ValueError('reservation missing')
            c.commit()
