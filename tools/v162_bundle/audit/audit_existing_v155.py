"""Read-only mechanical audit of the published V155 working-tree artifacts.

This is NOT a physical calibration and NOT proof of the exact historical model
forward count (which also depends on unmetered model construction).
"""
from __future__ import annotations
import argparse, csv, hashlib, json, sqlite3, zipfile
from pathlib import Path

EXPECTED_GROUPS = {f'{B}_ANON_{i:02d}' for B in (1000, 10000, 100000)
                   for i in range(1,5)}

def digest(raw):return hashlib.sha256(raw).hexdigest()

def audit(repo):
    root=Path(repo)/'results'/'v155'
    output={'audit_scope':'PUBLISHED_FILES_AND_LEDGER_NOT_F2C_REPLAY',
            'scientific_qualification':False,'issues':[]}
    gdirs=[d for d in (root/'groups').iterdir() if d.is_dir()] if (root/'groups').is_dir() else []
    actual={d.name for d in gdirs}
    output['group_set_matches']=actual==EXPECTED_GROUPS
    summaries=[]
    for name in sorted(EXPECTED_GROUPS):
        path=root/'groups'/name/'result.json'
        if not path.is_file():
            output['issues'].append('MISSING_GROUP_RESULT:'+name);continue
        obj=json.loads(path.read_text(encoding='utf-8'))
        diag=obj.get('diagnostic') or {}
        rows=list((path.parent/'predictions').glob('*.json'))
        summaries.append(dict(name=name,theta=diag.get('theta'),
                              numerical_status=diag.get('status'),
                              state=obj.get('execution_state'),
                              used=obj.get('actual_forward_attempts'),
                              predictions_disk=len(rows),
                              predictions_in_doc=len(diag.get('predictions') or [])))
    output['groups']=summaries
    output['all_at_same_artificial_anchor']=len(summaries)==12 and all(
        s['theta']==[200.0,450.0,0.0,0.0] for s in summaries)
    output['all_boundary_only']=len(summaries)==12 and all(
        s['numerical_status']=='BOUNDARY_LOCAL_DIAGNOSTIC_ONLY' for s in summaries)
    if output['all_at_same_artificial_anchor']:
        output['issues'].append('NOT_THE_12_RESC0RED_V152_CANDIDATES')
    dbpath=root/'logs'/'v155_budget.sqlite'
    if dbpath.exists():
        con=sqlite3.connect(dbpath.resolve().as_uri()+'?mode=ro',uri=True)
        try:
            con.execute('PRAGMA query_only=ON')
            output['sqlite_integrity_check']=con.execute('PRAGMA integrity_check').fetchone()[0]
            task_rows=con.execute('SELECT id,phase,cap,used,state FROM tasks ORDER BY id').fetchall()
            attempts=con.execute('SELECT task,state,COUNT(*) FROM attempts GROUP BY task,state').fetchall()
            meta=con.execute('SELECT value FROM metadata WHERE id=1').fetchone()
        finally:con.close()
        output['sqlite_tasks']=len(task_rows)
        output['sqlite_attempts']=sum(r[2] for r in attempts)
        output['sqlite_used']=sum(r[3] for r in task_rows)
        output['sqlite_reserved']=sum(r[2] for r in task_rows)
        output['sqlite_attempt_state_counts']={k:sum(row[2] for row in attempts if row[1]==k) for k in set(r[1] for r in attempts)}
        output['sqlite_meta']=json.loads(meta[0]) if meta else None
        output['sqlite_only_local_tasks']=all(r[1]=='LOCAL_INFORMATION' for r in task_rows)
        if output['sqlite_only_local_tasks']:
            output['issues'].append('NO_REPLAY_ANCHOR_OR_FINAL_VERIFY_TASKS')
    else:output['issues'].append('MISSING_ORIGINAL_SQLITE')
    manifest=root/'manifest_sha256.csv'
    checks={'rows':0,'verified':0,'failures':[]}
    if manifest.is_file():
        with manifest.open(encoding='utf-8',newline='') as f:
            for r in csv.DictReader(f):
                checks['rows']+=1
                p=(root/r['path']).resolve()
                if not p.is_relative_to(root.resolve()) or not p.is_file():
                    checks['failures'].append('MISSING_OR_OUTSIDE:'+r['path']);continue
                raw=p.read_bytes()
                if len(raw)!=int(r['bytes']) or digest(raw)!=r['sha256']:
                    checks['failures'].append('HASH_MISMATCH:'+r['path']);continue
                checks['verified']+=1
    else:checks['failures'].append('MANIFEST_ABSENT')
    output['manifest']=checks
    archive=root/'iscat_v155_return.zip'
    if archive.is_file():
        with zipfile.ZipFile(archive) as z:
            output['zip_members']=len(z.namelist())
            output['zip_crc_bad_member']=z.testzip()
            output['zip_sha256']=digest(archive.read_bytes())
    else:output['issues'].append('ORIGINAL_RETURN_ZIP_MISSING')
    output['assessment']='INVALID_FOR_ACTUAL_CANDIDATE_LOCAL_INFORMATION'
    return output

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True)
    p.add_argument('--out',required=True)
    a=p.parse_args()
    d=audit(a.repo);o=Path(a.out);o.parent.mkdir(parents=True,exist_ok=True)
    o.write_text(json.dumps(d,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    print('V155_READ_ONLY_AUDIT_COMPLETE__NOT_SCIENCE_PASS')
if __name__=='__main__':main()
