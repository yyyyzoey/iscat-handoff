"""Estimator-side single-payload gate. No plan, seed or truth knowledge.
This schema gate is NOT an OS sandbox. Production must also isolate read access.
"""
from __future__ import annotations
import json,math
from pathlib import Path

TOP={'schema','task_id','group','B','reading','starts','cap_per_start','task_cap','scope'}
READING={'reading_id','group','B','replicate','sigma_nm','z_nm','hypothetical'}

def validate(p):
 if not isinstance(p,dict) or set(p)!=TOP:raise ValueError('WORKER_PAYLOAD_KEYS')
 r=p.get('reading')
 if not isinstance(r,dict) or set(r)!=READING:raise ValueError('ONE_READING_ONLY')
 if p['schema']!='iscat167.one_task.1' or p['scope']!='OPENED_DEV_NOT_BLIND_NOT_EXPERIMENT':raise ValueError('SCOPE_OR_SCHEMA')
 if not isinstance(p['task_id'],str) or not p['task_id'].startswith('V167_'):raise ValueError('TASK_ID')
 if p['group'] not in ('ANON_01','ANON_02','ANON_03','ANON_04') or p['B']!=100000:raise ValueError('GROUP_OR_B')
 if r['reading_id']!=p['task_id'] or r['group']!=p['group'] or r['B']!=p['B']:raise ValueError('READING_BINDING')
 if type(r['replicate']) is not int or r['replicate'] not in (0,1,2):raise ValueError('REPLICATE')
 if not r['hypothetical'] is True:raise ValueError('HYPOTHETICAL_REQUIRED')
 if type(r['sigma_nm']) not in (int,float) or r['sigma_nm'] not in (1.,10.):raise ValueError('SIGMA')
 if type(r['z_nm']) not in (int,float) or not math.isfinite(r['z_nm']):raise ValueError('Z_FINITE')
 starts=p['starts']
 if not isinstance(starts,list) or len(starts) not in (1,2):raise ValueError('START_COUNT')
 for t in starts:
  if not isinstance(t,list) or len(t)!=4 or not all(type(x) in (int,float) and math.isfinite(x) for x in t):raise ValueError('THETA')
  if not all(l<=x<=h for x,l,h in zip(t,[30,350,-500,-500],[200,550,500,500])) or t[1]-t[0]/2<100:raise ValueError('DOMAIN_NO_CLIP')
 if type(p['task_cap']) is not int or type(p['cap_per_start']) is not int or p['task_cap']!=400 or p['cap_per_start']!=400//len(starts):raise ValueError('CAP')
 return p

def load_single(path):
 return validate(json.loads(Path(path).read_text(encoding='utf-8')))
