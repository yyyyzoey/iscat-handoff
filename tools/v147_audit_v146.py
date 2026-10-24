#!/usr/bin/env python3
"""Read-only independent re-count of published V146 validator-side 36 events."""
import argparse,json,math,hashlib
from pathlib import Path

def audit(repo):
    repo=Path(repo);src=repo/'results/v146/validator_only/camera_scores.json';status=repo/'results/v146/status.json'
    z=json.loads(src.read_text(encoding='utf-8'));st=json.loads(status.read_text(encoding='utf-8'))
    arr=z['rows']; errors=[]
    if len(arr)!=36:errors.append('NOT_36_EVENTS')
    ids=[r['event_id'] for r in arr]
    if len(set(ids))!=len(ids):errors.append('DUPLICATE_EVENT_IDS')
    groups=[]
    for B in (1000,10000,100000):
        x=[r for r in arr if r['B']==B];g=[]
        if len(x)!=12:errors.append('WRONG_EVENT_COUNT:'+str(B))
        for scope in ('all_targets','detected_only'):
            t=x if scope=='all_targets' else [r for r in x if r['detected']]
            es=[r['absolute_error_nm'] for r in t if r['candidate_D_nm'] is not None]
            if any(not math.isfinite(float(v)) for v in es):errors.append('BAD_ERROR')
            for r in t:
                if r['candidate_D_nm'] is not None and abs(abs(r['candidate_D_nm']-r['D_true_nm'])-r['absolute_error_nm'])>1e-8:errors.append('ROW_ERROR_MISMATCH:'+r['event_id'])
            g.append({'B':B,'scope':scope,'n':len(t),'finite':len(es),'MAE_nm':sum(es)/len(es) if es else None,'within_goal':sum(bool(r['candidate_within_engineering_goal']) for r in t)})
        groups.extend(g)
    expected={(1000,'all_targets'):56.33184857405798,(10000,'all_targets'):42.258043564286915,(100000,'all_targets'):25.284227366275534,(1000,'detected_only'):18.83924019817306,(10000,'detected_only'):10.11452822600927,(100000,'detected_only'):22.63514139459341}
    for r in groups:
        e=expected.get((r['B'],r['scope']));
        if e is not None and abs(e-r['MAE_nm'])>1e-7:errors.append('MAE_DIFF:'+str(r['B'])+':'+r['scope'])
    if st.get('EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED') is not False:errors.append('ABSOLUTE_FLAG')
    if any(r.get('reportable_D') is not None for r in arr):errors.append('UNQUALIFIED_REPORTABLE')
    return {'status':'AUDIT_FAIL' if errors else 'PUBLISHED_ARITHMETIC_REPRODUCED_NOT_PHYSICS_CERTIFIED','errors':errors,'n_events':len(arr),'groups':groups,'sources':{'status':str(status),'validator':str(src)},'new_physics_or_camera_generated':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--out',required=True);a=p.parse_args();x=audit(a.repo);dst=Path(a.out);dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');print(x['status']);raise SystemExit(2 if x['errors'] else 0)
