"""Validator only: join M candidates to published task records, never called by fitting.
Task labels are not a substitute for raw-solve geometry verification.
"""
import argparse,csv,hashlib,json
from pathlib import Path
import numpy as np

def score(candidate_csv,task_json):
    cases=json.loads(Path(task_json).read_text(encoding='utf-8-sig'))['cases']
    registry={}
    for c in cases:
        k=c['tag'].removeprefix('holdout_')
        if k in registry:raise ValueError('Duplicate task case')
        off=[r for r in c['renders'] if r['variant']=='at_offset']
        if len(off)!=1:raise ValueError('Unique offset render required')
        registry[k]=(float(c['D_nm']),float(c['h_nm']),off[0]['shift_xy_nm'])
    rows=list(csv.DictReader(Path(candidate_csv).open(encoding='utf-8-sig',newline='')));seen=set();out=[]
    for r in rows:
        k=r['case']
        if k in seen or k not in registry:raise ValueError('Duplicate/unmapped candidate')
        seen.add(k);D,h,xy=registry[k];v=float(r['candidate_D'])
        if not np.isfinite(v):raise ValueError('Nonfinite candidate')
        e=v-D;out.append(dict(case=k,D_recorded_nm=D,D_candidate_nm=v,err_D_nm=e,
               size_error_target_only_pass=bool(abs(e)<=max(5,.1*D)),h_recorded_nm=h,
               record_scope='PUBLISHED_TASK_RECORD_REQUIRES_RAW_GEOMETRY_CHECK',
               role='OPENED_DIRECT_DEVELOPMENT',reportable_D=r.get('reportable_D','')))
    e=np.array([r['err_D_nm'] for r in out])
    return out,dict(n=len(out),bias_nm=float(e.mean()) if len(e) else None,MAE_nm=float(abs(e).mean()) if len(e) else None,
                   RMSE_nm=float(np.sqrt(np.mean(e*e))) if len(e) else None,
                   size_error_target_only_pass=sum(r['size_error_target_only_pass'] for r in out),
                   note='Size-error scoring is not a reportability or physical validation gate; no new blind test.')

def main():
    p=argparse.ArgumentParser();p.add_argument('--candidates',required=True);p.add_argument('--task-records',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    r,s=score(a.candidates,a.task_records);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    if r:
        with (out/'M_scored.csv').open('w',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(r[0]));w.writeheader();w.writerows(r)
    (out/'summary.json').write_text(json.dumps(s,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
if __name__=='__main__':main()
