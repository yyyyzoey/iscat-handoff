"""Conservative atomic reservation ledger, persistent across resume.
Every reserved operation is charged including attempts that fail or crash.
Charges refer to allocated maximum calls; actual used additionally logged.
"""
import sqlite3,time
from contextlib import closing
from pathlib import Path
class BudgetExceeded(Exception):pass
class DuplicateOperation(Exception):pass
class Budget:
    LIMITS={'BEM':4,'RENDER':12,'CAMERA':0,'FORWARD':350000}
    def __init__(self,path,limits=None):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.limits=dict(self.LIMITS if limits is None else limits)
        with closing(sqlite3.connect(self.path,timeout=30)) as c:
            c.execute('PRAGMA journal_mode=WAL')
            c.execute('CREATE TABLE IF NOT EXISTS events (op TEXT PRIMARY KEY,metric TEXT,units INTEGER,state TEXT,created REAL,note TEXT,actual_units INTEGER)')
            c.commit()
    def spent(self,metric):
        with closing(sqlite3.connect(self.path,timeout=30)) as c:
            return int(c.execute('SELECT COALESCE(SUM(units),0) FROM events WHERE metric=?',(metric,)).fetchone()[0])
    def reserve(self,op,metric,units=1,note=''):
        if not op or metric not in self.limits or type(units)!=int or units<1:raise ValueError('INVALID_BUDGET_RESERVATION')
        with closing(sqlite3.connect(self.path,timeout=30,isolation_level=None)) as c:
            try:
                c.execute('BEGIN IMMEDIATE')
                if c.execute('SELECT 1 FROM events WHERE op=?',(op,)).fetchone():raise DuplicateOperation(op)
                used=int(c.execute('SELECT COALESCE(SUM(units),0) FROM events WHERE metric=?',(metric,)).fetchone()[0])
                if used+units>self.limits[metric]:raise BudgetExceeded(f'{metric} {used}+{units}>{self.limits[metric]}')
                c.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?)',(op,metric,units,'RESERVED',time.time(),note,None));c.execute('COMMIT')
            except Exception:
                if c.in_transaction:c.execute('ROLLBACK')
                raise
    def mark(self,op,state,actual_units=None,note=''):
        if state not in ('COMPLETED','FAILED','BLOCKED'):raise ValueError('BAD_STATE')
        with closing(sqlite3.connect(self.path,timeout=30)) as c:
            row=c.execute('SELECT units FROM events WHERE op=?',(op,)).fetchone()
            if row is None:raise ValueError('UNKNOWN_OPERATION')
            if actual_units is not None and (type(actual_units)!=int or not 0<=actual_units<=row[0]):
                raise ValueError('ACTUAL_CALL_COUNT_INVALID')
            c.execute('UPDATE events SET state=?,actual_units=?,note=? WHERE op=?',(state,actual_units,note,op));c.commit()
    def fetch(self,op):
        with closing(sqlite3.connect(self.path,timeout=30)) as c:
            row=c.execute('SELECT metric,units,state,actual_units FROM events WHERE op=?',(op,)).fetchone()
            return dict(zip(('metric','units','state','actual_units'),row)) if row else None
    def summary(self):return {m:{'charged':self.spent(m),'limit':self.limits[m]} for m in self.limits}
