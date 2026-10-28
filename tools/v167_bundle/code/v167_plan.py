"""Trusted preparation only: deterministic task inputs; NO model or truth access.

This module is NOT an estimator and must not be imported in estimator workers.
Workers receive one validated payload, not this controller's full input maps.
The integration with the proven V166 runner remains a workstation task.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any

PARENT = '06b35cd4e0a47f7f49ef4b05401a07266f2c03b6'
GROUPS = ('ANON_01','ANON_02','ANON_03','ANON_04')
RECOVERY = (
 'B100000_ANON_01_H10_R00','B100000_ANON_01_H10_R01',
 'B100000_ANON_01_H1_R00','B100000_ANON_01_H1_R01','B100000_ANON_01_H1_R02')
PHASES={'MODEL_BINDING':200,'SEARCH_EXTENSION':2000,'BIAS_STRESS':7200,'FINAL_VERIFY':600}
PINS={
 'estimates.json':'242958afa607deee2f84b564c8f4eb8fda01ac24',
 'height_input/height_readings.json':'b087156cf60d2b16fbfe3da3d9e4a20bef902dd0',
 'starts_by_group.json':'3b7b46f0e7cde72e09a50a6cfddc7613f32f6f95'}


def canon(value: Any) -> bytes:
 return (json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8')


def require(test: bool, message: str) -> None:
 if not test: raise ValueError(message)


def finite_number(value: Any) -> bool:
 return type(value) in (float,int) and math.isfinite(float(value))


def theta_ok(theta: Any) -> list[float]:
 require(isinstance(theta,(list,tuple)) and len(theta)==4,'FOUR_PARAMETER_THETA_REQUIRED')
 require(all(finite_number(x) for x in theta),'NONFINITE_THETA')
 t=list(map(float,theta)); lo=(30,350,-500,-500); hi=(200,550,500,500)
 require(all(l<=x<=h for x,l,h in zip(t,lo,hi)) and t[1]-t[0]/2>=100,'DOMAIN_VIOLATION_NO_CLIP')
 return t


def identity(kind: str, old_id: str, bias: float | None = None) -> str:
 # Bias is deliberately absent in the readable worker id.
 h=hashlib.sha256(canon({'parent':PARENT,'kind':kind,'source':old_id,'bias':bias})).hexdigest()
 return 'V167_'+h[:24]


def one_reading(row: dict, task_id: str, *, add_nm: float = 0.) -> dict:
 require(row['group'] in GROUPS and row['B']==100000,'READING_GROUP_OR_B')
 require(type(row['replicate']) is int and row['replicate'] in (0,1,2),'READING_REPLICATE')
 require(finite_number(row['sigma_nm']) and row['sigma_nm'] in (1.,10.),'READING_SIGMA')
 require(finite_number(row['z_nm']) and finite_number(add_nm),'READING_FINITE')
 require(row.get('hypothetical') is True,'READING_NOT_HYPOTHETICAL')
 # A strict projection, not a copy of arbitrary original metadata.
 return {'reading_id':task_id,'group':row['group'],'B':100000,
         'replicate':row['replicate'],'sigma_nm':float(row['sigma_nm']),
         'z_nm':float(row['z_nm'])+float(add_nm),'hypothetical':True}


def validate_payload(p: dict) -> None:
 allowed={'schema','task_id','group','B','reading','starts','cap_per_start','task_cap','scope'}
 require(isinstance(p,dict) and set(p)==allowed,'PAYLOAD_KEYS_NOT_ALLOWLIST')
 require(p['schema']=='iscat167.one_task.1','PAYLOAD_SCHEMA')
 require(isinstance(p['task_id'],str) and p['task_id'].startswith('V167_'),'PAYLOAD_ID')
 require(p['group'] in GROUPS and p['B']==100000,'PAYLOAD_GROUP')
 r=p['reading']
 require(isinstance(r,dict) and set(r)=={'reading_id','group','B','replicate','sigma_nm','z_nm','hypothetical'},'SINGLE_READING_STRICT_SCHEMA')
 require(r['reading_id']==p['task_id'] and r['group']==p['group'] and r['B']==p['B'],'READING_BINDING')
 one_reading(r,p['task_id'])
 require(isinstance(p['starts'],list) and len(p['starts']) in (1,2),'START_COUNT')
 for t in p['starts']:theta_ok(t)
 require(type(p['cap_per_start']) is int and type(p['task_cap']) is int,'CAP_TYPE')
 require(p['task_cap']==400 and p['cap_per_start']==400//len(p['starts']),'CAP_GRID')
 require(p['scope']=='OPENED_DEV_NOT_BLIND_NOT_EXPERIMENT','SCOPE')


def make_payload(task_id: str, reading: dict, starts: list, cap: int) -> dict:
 p={'schema':'iscat167.one_task.1','task_id':task_id,'group':reading['group'],'B':100000,
    'reading':reading,'starts':[theta_ok(t) for t in starts],
    'cap_per_start':cap,'task_cap':400,'scope':'OPENED_DEV_NOT_BLIND_NOT_EXPERIMENT'}
 validate_payload(p);return p


def expected_old_ids() -> set[str]:
 return {f'B100000_{g}_NO_HEIGHT' for g in GROUPS}|{
  f'B100000_{g}_H{s}_R{r:02d}' for g in GROUPS for s in (1,10) for r in range(3)}


def build_plan(estimates: list, readings_doc: dict, starts_doc: dict,
               pending_starts: dict) -> tuple[dict,dict]:
 require(isinstance(estimates,list) and len(estimates)==28,'ESTIMATE_COUNT')
 by_id={r['task_id']:r for r in estimates}
 require(len(by_id)==28 and set(by_id)==expected_old_ids(),'ESTIMATE_ID_SET')
 partial={r['task_id'] for r in estimates if r['execution_state']=='PARTIAL_SEARCH'}
 require(partial==set(RECOVERY),'PARENT_PARTIAL_SET_CHANGED')
 require(all(r['execution_state'] in ('FINISHED','PARTIAL_SEARCH') for r in estimates),'OLD_TASK_UNKNOWN_STATE')
 rr=readings_doc.get('readings',[])
 require(len(rr)==24,'READING_COUNT')
 rmap={r['reading_id']:r for r in rr}
 require(len(rmap)==24 and set(rmap)==expected_old_ids()-{f'B100000_{g}_NO_HEIGHT' for g in GROUPS},'READING_ID_SET')
 require(set(starts_doc)==set(GROUPS),'GROUP_START_SET')
 records=[];payloads={}
 for old_id in RECOVERY:
  s=pending_starts[old_id]
  require(s.get('execution_state')=='PARTIAL_SEARCH' and s.get('start_index')==1,'RECOVERY_SOURCE_NOT_PENDING_START_1')
  require(s.get('error',{}).get('error_type')=='CallCapReached','RECOVERY_NOT_AUTHORIZED_FOR_OTHER_ERRORS')
  require(isinstance(s.get('best'),dict),'RECOVERY_BEST_MISSING')
  tid=identity('REFINEMENT',old_id)
  p=make_payload(tid,one_reading(rmap[old_id],tid),[s['best']['theta']],400)
  payloads[tid]=p
  records.append({'task_id':tid,'kind':'SEARCH_EXTENSION','source_task_id':old_id,
    'source_start_index':1,'warm_start_record':'starts/001.json:best',
    'old_start_consumption':s.get('actual_calls'),'old_status_preserved':'PARTIAL_SEARCH',
    'merge_rule':'MINIMUM_Q_TOTAL_OVER_OLD_BEST_AND_NEW_LEGAL_POINTS',
    'task_cap':400,'payload_sha256':hashlib.sha256(canon(p)).hexdigest()})
 for group in GROUPS[1:]:
  starts=[starts_doc[group][k]['theta'] for k in ('first','second')]
  for rep in range(3):
   old_id=f'B100000_{group}_H1_R{rep:02d}'
   require(by_id[old_id]['execution_state']=='FINISHED','ZERO_BIAS_REFERENCE_NOT_FINISHED')
   for b in (-2.,2.):
    tid=identity('BIAS_STRESS',old_id,b)
    p=make_payload(tid,one_reading(rmap[old_id],tid,add_nm=b),starts,200)
    payloads[tid]=p
    records.append({'task_id':tid,'kind':'BIAS_STRESS','source_task_id':old_id,
     'controlled_offset_nm':b,'sigma_nm':1.,'replicate':rep,'group':group,
     'task_cap':400,'payload_sha256':hashlib.sha256(canon(p)).hexdigest()})
 require(len(payloads)==23 and len(records)==23,'NEW_TASK_COUNT')
 require(sum(PHASES.values())==10000,'BUDGET_SUM')
 manifest={'schema':'iscat167.controller_plan.1','role':'CONTROLLER_ONLY_NOT_WORKER_INPUT',
  'parent':PARENT,'phases':PHASES,'total_new_model_attempts':10000,
  'new_fit_jobs':23,'new_height_random_draws':0,'entries':records,
  'new_truth_read_before_seal':False,
  'note':'Only one payload may be mounted/passed to each worker; never mount this plan or all payloads.'}
 return manifest,payloads


def pinned_json(path: Path, blob_sha: str) -> Any:
 raw=path.read_bytes()
 got=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
 require(got==blob_sha,'SOURCE_BLOB_CHANGED:'+str(path))
 return json.loads(raw.decode('utf-8-sig'))


def write_new(path: Path, value: Any) -> None:
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('xb') as f:f.write(canon(value))


def main() -> int:
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--v166-results',type=Path,required=True)
 ap.add_argument('--out',type=Path,required=True)
 a=ap.parse_args();source=a.v166_results.resolve();out=a.out.resolve()
 require(not out.exists(),'OUTPUT_EXISTS_NO_AUTORETRY')
 require(out!=source and source not in out.parents,'OUTPUT_MUST_NOT_MODIFY_PARENT_RESULT_TREE')
 docs={rel:pinned_json(source/rel,pin) for rel,pin in PINS.items()}
 pending={}
 # Retrieve the immutable blob identity of each warm-start checkpoint from Git.
 # No numerical replay, checkout, source mutation or model construction occurs.
 require(source.name=='v166' and source.parent.name=='results','EXPECTED_V166_RESULT_ROOT')
 repo=source.parents[1]
 for tid in RECOVERY:
  rel=f'results/v166/tasks/{tid}/starts/001.json'
  b=subprocess.run(['git','-C',str(repo),'rev-parse',f'{PARENT}:{rel}'],
                   check=True,capture_output=True).stdout.decode('ascii').strip()
  require(len(b)==40,'INVALID_GIT_BLOB_ID')
  pending[tid]=pinned_json(repo/rel,b)
 plan,payloads=build_plan(docs['estimates.json'],docs['height_input/height_readings.json'],docs['starts_by_group.json'],pending)
 # Controller staging root, not a directory that workers can browse.
 out.mkdir(parents=True,exist_ok=False)
 write_new(out/'controller_only/plan.json',plan)
 for tid,p in payloads.items():write_new(out/'controller_staging'/tid/'input.json',p)
 write_new(out/'preparation_receipt.json',{'model_calls':0,'random_draws':0,'new_payloads':23,
  'parent_commit':PARENT,'source_blobs':PINS,'requires_workstation_integration':True})
 print('PREPARATION_ONLY__23_TASK_PAYLOADS__NO_MODEL_CALLS__NOT_PRODUCTION_EXECUTION')
 return 0

if __name__=='__main__':raise SystemExit(main())
