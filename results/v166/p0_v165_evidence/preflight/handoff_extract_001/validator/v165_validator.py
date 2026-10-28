"""Post-seal validator for V165 opened-development synthetic-scene pilot.

Must be launched AFTER estimator has written a durable estimate file and SHA.
No model or camera is called; no rewriting of estimated outputs is permitted.
Does NOT produce experiment-calibrated uncertainty or reportable diameters.
"""
from __future__ import annotations
import hashlib,json,statistics,argparse
from pathlib import Path
from math import isfinite

GROUPS=('ANON_01','ANON_02','ANON_03','ANON_04')


def validate(estimates, truth_doc, readings, detections):
    from collections import defaultdict
    scene={f'ANON_{int(x["case"][1:]):02d}':x for x in truth_doc['cases']}
    if set(scene)!=set(GROUPS):raise ValueError('UNKNOWN_SCENE_MAPPING')
    rd={r['reading_id']:r for r in readings['readings']}
    if len(rd)!=24 or any(r['group'] not in scene for r in rd.values()):raise ValueError('BAD_READINGS')
    from v165_task_ids import tasks
    planned=tasks(); expected={r['task_id']:r for r in planned}
    if len(estimates)!=28 or {r['task_id'] for r in estimates}!=set(expected):
        raise ValueError('MISSING_OR_DUPLICATE_OR_UNKNOWN_ESTIMATE_TASKS')
    if set(detections)!=set(GROUPS) or any(type(detections[g]) is not list or len(detections[g])!=3 or any(type(v) is not bool for v in detections[g]) for g in GROUPS):
        raise ValueError('FROZEN_DETECTION_STATUS_REQUIRED_FOR_EACH_OF_THREE_FRAMES')
    group_scores=defaultdict(lambda:defaultdict(list))
    output=[]
    for row in estimates:
        task=expected[row['task_id']];group=task['group'];h=float(scene[group]['h_nm']);D=float(scene[group]['D_nm'])
        rdv=rd.get(row['task_id']) if task['sigma_nm'] is not None else None
        if (rdv is None)!=(task['sigma_nm'] is None):raise ValueError('READING_ID_DOES_NOT_MATCH_TASK')
        if rdv and (rdv['group']!=group or rdv['replicate']!=task['replicate'] or rdv['sigma_nm']!=task['sigma_nm']):
            raise ValueError('WRONG_READING_BINDING')
        t=row.get('theta');status=row.get('execution_state')
        if not isinstance(status,str) or status not in ('FINISHED','PARTIAL_SEARCH','FAILED','BLOCKED'):
            raise ValueError('INVALID_EXECUTION_STATE')
        if t is not None:
            if len(t)!=4 or not all(isfinite(float(v)) for v in t):raise ValueError('INVALID_THETA_IN_REPORT')
            Dhat=float(t[0]);hhat=float(t[1]);eD=abs(Dhat-D);eh=abs(hhat-h)
        else:
            Dhat=hhat=eD=eh=None
            if status=='FINISHED':raise ValueError('FINISHED_WITHOUT_THETA')
        design='NO_HEIGHT' if task['sigma_nm'] is None else f'H{int(task["sigma_nm"])}'
        eligible=(status=='FINISHED' and Dhat is not None)
        if eligible:group_scores[group][design].append(eD)
        output.append(dict(task_id=row['task_id'],group=group,design=design,status=status,
                           candidate_D_nm=Dhat,candidate_h_nm=hhat,simulated_D_scene_nm=D,
                           simulated_h_scene_nm=h,abs_D_error_nm=eD,abs_h_error_nm=eh,
                           reading_id=rdv['reading_id'] if rdv else None,
                           detected_frame_count=sum(detections[group]),any_frame_detected=any(detections[group]),
                           reportable_D=None,scope='OPENED_SIMULATED_DEV_NOT_REAL_SIZING'))
    summary={}
    for key,expected_reps in [('NO_HEIGHT',1),('H1',3),('H10',3)]:
        per=[]
        for group in GROUPS:
            values=group_scores[group][key]
            per.append(dict(group=group,planned=expected_reps,scored=len(values),
                            mean_abs_error_nm=(sum(values)/len(values)) if len(values)==expected_reps else None,
                            incomplete=len(values)!=expected_reps))
        fully_complete=all(x['scored']==expected_reps for x in per)
        summary[key]=dict(groups=per,conditional_group_MAE_nm=(sum(x['mean_abs_error_nm'] for x in per)/4 if fully_complete else None),
                          group_n=4,fully_complete=fully_complete,scope='DESCRIPTIVE_OPENED_DEVELOPMENT')
    return dict(task_rows=output,summary=summary,all_reportable_D_null=True,
                strict_blind_validation=False,experimental_absolute_diameter_validated=False)


def main():
    p=argparse.ArgumentParser()
    for a in ('estimates','estimates-sha256','truth','readings','frozen-detections','out'):
        p.add_argument('--'+a,required=True)
    a=p.parse_args();est=Path(a.estimates);raw=est.read_bytes();actual=hashlib.sha256(raw).hexdigest()
    want=Path(a.estimates_sha256).read_text().strip()
    if actual!=want:raise ValueError('ESTIMATE_SHA_UNSEALED_OR_CHANGED')
    def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    out=validate(json.loads(raw.decode('utf-8')),read(a.truth),read(a.readings),read(a.frozen_detections))
    dest=Path(a.out)
    if dest.exists():raise FileExistsError('DO_NOT_OVERWRITE_VALIDATOR_SCORE')
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(out,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    print('POST_SEAL_VALIDATOR_SCORED_28_TASK_RECORDS_NOT_REAL_SIZING')
if __name__=='__main__':main()
