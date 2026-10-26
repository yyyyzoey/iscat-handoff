"""Package available evidence, including a failed/incomplete run. Never invent PASS."""
from pathlib import Path
import argparse,csv,hashlib,io,json,sqlite3,zipfile
from v152_budget_store import atomic_json

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();o=a.out.resolve()
    if o.name!='v163' or o.parent.name!='results':raise ValueError('EXPECTED_RESULTS_V163')
    o.mkdir(parents=True,exist_ok=True)
    required=['preflight.json','selected_candidates_12.json','design/saved_array_designs.json',
              'logs/v163_budget.sqlite','status.json','verification.json','workstation_tests/test_receipt.json']
    present={x:(o/x).is_file() for x in required}
    failures=[str(p.relative_to(o)) for p in sorted((o/'failures').glob('*.json'))]
    status=json.loads((o/'status.json').read_text(encoding='utf-8')) if present['status.json'] else {'execution_state':'BLOCKED_OR_FAILED_NO_FINAL_STATUS'}
    budget={}
    db=o/'logs/v163_budget.sqlite'
    if db.is_file():
        if any(Path(str(db)+x).exists() for x in ('-wal','-journal')):raise ValueError('LIVE_DATABASE_REQUIRES_FORENSIC_SNAPSHOT')
        with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as con:
            budget=dict(task_counts=con.execute('SELECT phase,count(*),sum(cap),sum(used) FROM tasks GROUP BY phase').fetchall(),
                        attempt_states=con.execute('SELECT state,count(*) FROM attempts GROUP BY state').fetchall(),
                        integrity=con.execute('PRAGMA integrity_check').fetchone()[0])
    stage_logs=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((o/'logs').glob('*_stage_states.json'))]
    truth=dict(stage_state_evidence=stage_logs,task_id='V163_ISOLATED_DEPLOYMENT_AND_FINITE_HEIGHT_VALIDATION',execution_state=status.get('execution_state','BLOCKED_OR_FAILED_NO_VALID_FINAL_STATE'),required_outputs=present,missing=[k for k,v in present.items() if not v],
               failure_files=failures,budget=budget,verification_present=present['verification.json'],
               all_reportable_D_null=True,experimental_absolute_diameter_validated=False,
               scientific_scope='CONDITIONAL_LOCAL_DESIGN_AND_DISCRETE_PATH_ONLY',
               not_a_precision_claim=True)
    atomic_json(o/'execution_integrity.json',truth)
    (o/'00_execution_truth_report.md').write_text('# V163 execution truth report\n\n```json\n'+json.dumps(truth,ensure_ascii=False,indent=2)+'\n```\n',encoding='utf-8')
    with (o/'failures.jsonl').open('w',encoding='utf-8') as f:
        for p in sorted((o/'failures').glob('*.json')):f.write(json.dumps(json.loads(p.read_text(encoding='utf-8')),ensure_ascii=False)+'\n')
    dest=o/'iscat_v163_return.zip';mf=o/'manifest_sha256.csv'
    files=[p for p in sorted(o.rglob('*')) if p.is_file() and p not in (dest,mf,o/'archive_receipt.json')]
    if any(p.is_symlink() for p in files):raise ValueError('NO_SYMLINK_MEMBERS')
    rows=[dict(path=p.relative_to(o).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]
    with mf.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);w.writeheader();w.writerows(rows)
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files+[mf]:z.write(p,p.relative_to(o).as_posix())
    with zipfile.ZipFile(dest) as z:
        if z.testzip() is not None:raise ValueError('ZIP_CRC_FAILED')
        if set(z.namelist())!={r['path'] for r in rows}|{'manifest_sha256.csv'}:raise ValueError('ZIP_MEMBER_MISMATCH')
        for r in rows:
            b=z.read(r['path'])
            if len(b)!=r['bytes'] or hashlib.sha256(b).hexdigest()!=r['sha256']:raise ValueError('ZIP_MANIFEST_FAILED')
    atomic_json(o/'archive_receipt.json',dict(path=dest.name,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),members=len(rows)+1,
                 note='Receipt is external to ZIP; CRC does not establish scientific acceptance.'))
    print('ARCHIVED_AVAILABLE_EVIDENCE__NOT_SCIENCE_PASS')
if __name__=='__main__':main()
