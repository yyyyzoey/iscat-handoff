"""V148 atomic ledger: per-event reserve / forward-attempt counting / finish / release."""
from __future__ import annotations
import json, sqlite3, time
from contextlib import closing
from pathlib import Path

class BudgetExceeded(RuntimeError):pass
class DuplicateOperation(RuntimeError):pass

class Ledger:
    def __init__(self,path,limits):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.limits=dict(limits)
        with closing(sqlite3.connect(self.path,timeout=60)) as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS events (op TEXT PRIMARY KEY, metric TEXT NOT NULL, units INTEGER NOT NULL, state TEXT NOT NULL, created REAL NOT NULL, finished REAL, actual INTEGER, payload_json TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS forward_attempts (op TEXT NOT NULL, seq INTEGER NOT NULL, ts REAL NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS released (op TEXT PRIMARY KEY, released_units INTEGER NOT NULL, ts REAL NOT NULL)')
            db.commit()
    def _payload(self,p):return json.dumps(p if isinstance(p,(dict,list)) else {'note':str(p)})
    def get(self,op):
        with closing(sqlite3.connect(self.path,timeout=60)) as db:
            r=db.execute('SELECT metric,units,state,actual,payload_json FROM events WHERE op=?',(op,)).fetchone()
            return dict(metric=r[0],units=r[1],state=r[2],actual=r[3],payload=json.loads(r[4])) if r else None
    def spent(self,metric):
        with closing(sqlite3.connect(self.path,timeout=60)) as db:
            return int(db.execute("SELECT COALESCE(SUM(units),0) FROM events WHERE metric=? AND state!='RELEASED_UNUSED'",(metric,)).fetchone()[0])
    def reserve(self,op,metric,units,payload=None):
        with closing(sqlite3.connect(self.path,timeout=60,isolation_level=None)) as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM events WHERE op=?',(op,)).fetchone():raise DuplicateOperation(op)
            used=db.execute("SELECT COALESCE(SUM(units),0) FROM events WHERE metric=? AND state!='RELEASED_UNUSED'",(metric,)).fetchone()[0]
            if used+units>self.limits[metric]:raise BudgetExceeded(f'{metric}: {used}+{units}>{self.limits[metric]}')
            db.execute('INSERT INTO events VALUES (?,?,?,?,?,NULL,NULL,?)',(op,metric,units,'RESERVED',time.time(),self._payload(payload)))
            db.commit()
    def record_attempt(self,op):
        with closing(sqlite3.connect(self.path,timeout=60,isolation_level=None)) as db:
            db.execute('BEGIN IMMEDIATE')
            seq=db.execute('SELECT COALESCE(MAX(seq),0)+1 FROM forward_attempts WHERE op=?',(op,)).fetchone()[0]
            db.execute('INSERT INTO forward_attempts VALUES (?,?,?)',(op,seq,time.time()));db.commit()
    def attempts(self,op):
        with closing(sqlite3.connect(self.path,timeout=60)) as db:
            return db.execute('SELECT COUNT(*) FROM forward_attempts WHERE op=?',(op,)).fetchone()[0]
    def finish(self,op,state,actual,info=None):
        with closing(sqlite3.connect(self.path,timeout=60,isolation_level=None)) as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT units,payload_json FROM events WHERE op=?',(op,)).fetchone()
            if not row:raise ValueError('FINISH_MISSING_OP:'+op)
            units,pj=row
            payload=json.loads(pj)
            if not isinstance(payload,dict):raise TypeError('PAYLOAD_NOT_DICT:'+op)
            if actual is not None and (not isinstance(actual,int) or actual<0 or actual>units):
                raise ValueError('ACTUAL_EXCEEDS_PRECHARGED:'+op)
            payload['finish']=info or {}
            db.execute('UPDATE events SET state=?,finished=?,actual=?,payload_json=? WHERE op=?',(state,time.time(),actual,json.dumps(payload,ensure_ascii=False),op))
            db.commit()
    def release_unused(self,op,released_units,info=None):
        with closing(sqlite3.connect(self.path,timeout=60,isolation_level=None)) as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT payload_json FROM events WHERE op=?',(op,)).fetchone()
            if not row:raise ValueError('RELEASE_MISSING_OP:'+op)
            payload=json.loads(row[0])
            if not isinstance(payload,dict):raise TypeError('PAYLOAD_NOT_DICT:'+op)
            payload['release']=dict(released_units=released_units,info=info or {})
            db.execute("UPDATE events SET state='RELEASED_UNUSED',payload_json=? WHERE op=?",(json.dumps(payload,ensure_ascii=False),op))
            db.execute('INSERT OR REPLACE INTO released VALUES (?,?,?)',(op,released_units,time.time()))
            db.commit()
