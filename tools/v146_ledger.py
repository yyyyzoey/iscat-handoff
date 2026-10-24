"""Persistent atomic reservations. No renderer/solver can be authorized here.
Never delete/rebuild a ledger. Limits are immutable for a run_id.
"""
from __future__ import annotations
import json,sqlite3,time
from pathlib import Path
from contextlib import closing
class BudgetExceeded(RuntimeError):pass
class Ledger:
    def __init__(self,path,run_id,limits):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.run_id=run_id;self.limits=dict(limits)
        if any(type(v)!=int or v<0 for v in limits.values()):raise ValueError('INVALID_LIMITS')
        with closing(sqlite3.connect(self.path,timeout=60)) as c:
            c.execute('CREATE TABLE IF NOT EXISTS metadata(run_id TEXT PRIMARY KEY, limits_json TEXT)')
            c.execute('CREATE TABLE IF NOT EXISTS events(op TEXT PRIMARY KEY,metric TEXT,units INTEGER,state TEXT,actual INTEGER,signature TEXT,details TEXT,created REAL)')
            rows=c.execute('SELECT run_id,limits_json FROM metadata').fetchall()
            expected=json.dumps(self.limits,sort_keys=True)
            if rows and rows!=[(run_id,expected)]:raise ValueError('LEDGER_RUN_OR_LIMITS_CHANGED')
            if not rows:c.execute('INSERT INTO metadata VALUES(?,?)',(run_id,expected))
            c.commit()
    def get(self,op):
        with closing(sqlite3.connect(self.path)) as c:
            r=c.execute('SELECT metric,units,state,actual,signature,details FROM events WHERE op=?',(op,)).fetchone()
            return dict(zip(('metric','units','state','actual','signature','details'),r)) if r else None
    def reserve(self,op,metric,units,signature):
        if metric not in self.limits or type(units)!=int or units<1 or not op or not signature:raise ValueError('BAD_RESERVATION')
        c=sqlite3.connect(self.path,timeout=60,isolation_level=None)
        try:
            c.execute('BEGIN IMMEDIATE')
            if c.execute('SELECT 1 FROM events WHERE op=?',(op,)).fetchone():raise ValueError('DUPLICATE_OPERATION')
            used=c.execute('SELECT COALESCE(SUM(units),0) FROM events WHERE metric=?',(metric,)).fetchone()[0]
            if used+units>self.limits[metric]:raise BudgetExceeded(metric)
            c.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?,?)',(op,metric,units,'RESERVED',None,signature,'{}',time.time()));c.execute('COMMIT')
        except Exception:
            if c.in_transaction:c.execute('ROLLBACK')
            raise
        finally:c.close()
    def finish(self,op,actual,state='COMPLETED',details=None):
        if state not in ('COMPLETED','PARTIAL','FAILED'):raise ValueError('BAD_STATE')
        c=sqlite3.connect(self.path,timeout=60,isolation_level=None)
        try:
            c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT units,state FROM events WHERE op=?',(op,)).fetchone()
            if not r or r[1]!='RESERVED':raise ValueError('NO_OPEN_RESERVATION')
            if actual is not None and (type(actual)!=int or not 0<=actual<=r[0]):raise ValueError('BAD_ACTUAL')
            c.execute('UPDATE events SET state=?,actual=?,details=? WHERE op=?',(state,actual,json.dumps(details or {},sort_keys=True),op));c.execute('COMMIT')
        except Exception:
            if c.in_transaction:c.execute('ROLLBACK')
            raise
        finally:c.close()
    def summary(self):
        with closing(sqlite3.connect(self.path)) as c:
            rows=c.execute('SELECT metric,COUNT(*),SUM(units),SUM(COALESCE(actual,0)),SUM(actual IS NULL) FROM events GROUP BY metric').fetchall()
        return {'run_id':self.run_id,'limits':self.limits,'metrics':{r[0]:{'events':r[1],'reserved':r[2],
            'known_actual':r[3],'unknown_actual_events':r[4]} for r in rows}}
