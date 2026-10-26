"""Portable mechanical/test/ledger summary for the original uploaded V162 return."""
from pathlib import Path,PurePosixPath
import argparse,collections,csv,hashlib,io,json,sqlite3,tempfile,zipfile

def sha(b):return hashlib.sha256(b).hexdigest()
def J(b):return json.loads(b.decode('utf-8-sig'))
def audit(path,handoff):
    with zipfile.ZipFile(path) as z,zipfile.ZipFile(handoff) as h:
        assert len(z.namelist())==len(set(z.namelist())) and z.testzip() is None
        for n in z.namelist():assert not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts and '\\' not in n
        manifest=list(csv.DictReader(io.StringIO(z.read('manifest_sha256.csv').decode('utf-8-sig'))))
        assert set(z.namelist())=={'manifest_sha256.csv'}|{r['path'] for r in manifest}
        for r in manifest:
            b=z.read(r['path']);assert len(b)==int(r['bytes']) and sha(b)==r['sha256']
        receipt=J(z.read('workstation_tests/test_receipt.json'));tests=J(z.read('workstation_tests/pytest_outcomes.json'));inventory=J(h.read('test_inventory.json'))
        assert sorted(tests['collected'])==inventory['nodeids'] and len(tests['reports'])==666
        assert tests['exitstatus']==0 and not tests['collection_errors']
        for node in inventory['nodeids']:
            rr=[r for r in tests['reports'] if r['nodeid']==node]
            assert len(rr)==3 and {(r['when'],r['outcome']) for r in rr}=={('setup','passed'),('call','passed'),('teardown','passed')}
        for rel,want in receipt['bundle_sha256'].items():assert sha(h.read(rel))==want
        for f,k in [('test_output.txt','output_sha256'),('pytest_outcomes.json','outcomes_sha256')]:assert sha(z.read('workstation_tests/'+f))==receipt[k]
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'budget.sqlite';p.write_bytes(z.read('logs/v162_budget.sqlite'))
            con=sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True)
            assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            tasks=con.execute('SELECT id,cap,used,state,result_sha FROM tasks').fetchall();n=con.execute('SELECT COUNT(*) FROM attempts').fetchone()[0];con.close()
        assert tasks[0][4]==sha(z.read('tasks/LOADER_1/result.json')) and n==0 and len(tasks)==1
        designs=J(z.read('design/saved_array_designs.json'))
        evaluations=sum(len(rs) for g in designs.values() for ds in g['designs'].values() for rs in ds.values())
        return dict(archive_sha256=sha(Path(path).read_bytes()),members=len(z.namelist()),manifest_rows=len(manifest),tests=len(tests['collected']),test_phase_reports=len(tests['reports']),sqlite_integrity='ok',tasks=tasks,attempts=n,groups=len(designs),design_evaluations=evaluations,scope='READONLY_RETURN_FILE_CHECKS_NO_OPTICAL_REPLAY')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--return-zip',type=Path,required=True);p.add_argument('--handoff-zip',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=audit(a.return_zip,a.handoff_zip);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
