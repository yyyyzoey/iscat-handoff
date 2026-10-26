"""No real optics: archive integrity, one-command dependency order, and evidence."""
import csv, hashlib, io, json, os, subprocess, sys, zipfile
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
import v162_bootstrap as b


def fake_payload(remove=None, overrides=None, extra=None):
    files={x:b'x\n' for x in b.REQUIRED if x!='manifest_sha256.csv'}
    files['test_inventory.json']=json.dumps({'nodeids':['tests/test_sample.py::test_ok']}).encode()
    if remove:files.pop(remove,None)
    files.update(overrides or {})
    if extra:files.update(extra)
    s=io.StringIO();w=csv.writer(s);w.writerow(['path','bytes','sha256'])
    for name,raw in sorted(files.items()):w.writerow([name,len(raw),b.digest(raw)])
    files['manifest_sha256.csv']=s.getvalue().encode()
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        for name,raw in files.items():z.writestr(name,raw)
    return buf.getvalue()


def test_intact_payload_contains_tests_inventory_and_orchestration():
    raw=fake_payload();r=b.verify_payload(raw,b.digest(raw))
    assert r['inventory_count']==1
    assert r['members']==len(b.REQUIRED)
    assert 'NOT_TEST' in r['scope']

@pytest.mark.parametrize('missing',['test_inventory.json','run_all.py','run_workstation_tests.py',
                                    'config/v162_plan.json','tests/test_v162_deployment.py'])
def test_missing_required_member_rejected_before_model(missing):
    raw=fake_payload(remove=missing)
    with pytest.raises(ValueError,match='INCOMPLETE'):b.verify_payload(raw,b.digest(raw))


def test_outer_hash_is_enforced():
    raw=fake_payload()
    with pytest.raises(ValueError,match='HASH'):b.verify_payload(raw,'0'*64)

@pytest.mark.parametrize('name',['../escape','/abs','C:/abs','a\\b','a/../x','a//x'])
def test_cross_platform_path_safety(name):
    raw=fake_payload(extra={name:b'x'})
    with pytest.raises(ValueError,match='PATH'):b.verify_payload(raw,b.digest(raw))


def test_unlisted_payload_member_rejected():
    raw=fake_payload();buf=io.BytesIO(raw)
    with zipfile.ZipFile(buf,'a') as z:z.writestr('unlisted','wrong')
    raw=buf.getvalue()
    with pytest.raises(ValueError,match='MEMBER_SET'):b.verify_payload(raw,b.digest(raw))


def test_manifest_hash_mismatch_rejected():
    raw=fake_payload();buf=io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(raw)) as old,zipfile.ZipFile(buf,'w') as new:
        for name in old.namelist():new.writestr(name,b'tampered' if name=='run_all.py' else old.read(name))
    raw=buf.getvalue()
    with pytest.raises(ValueError,match='HASH_MISMATCH'):b.verify_payload(raw,b.digest(raw))


def test_windows_case_collision_rejected():
    raw=fake_payload(extra={'RUN_ALL.PY':b'wrong'})
    with pytest.raises(ValueError,match='COLLIDING'):b.verify_payload(raw,b.digest(raw))


def test_zero_or_duplicate_test_inventory_rejected():
    for nodes in ([],['same','same']):
        raw=fake_payload(overrides={'test_inventory.json':json.dumps({'nodeids':nodes}).encode()})
        with pytest.raises(ValueError,match='INVENTORY'):b.verify_payload(raw,b.digest(raw))


def test_extraction_is_complete_and_does_not_overwrite(tmp_path):
    raw=fake_payload();dest=tmp_path/'payload'
    r=b.extract_verified(raw,dest,b.digest(raw))
    assert (dest/'test_inventory.json').is_file()
    assert len([p for p in dest.rglob('*') if p.is_file()])==r['members']
    before=(dest/'run_all.py').read_bytes()
    with pytest.raises(ValueError,match='EXISTS'):b.extract_verified(raw,dest,b.digest(raw))
    assert (dest/'run_all.py').read_bytes()==before

@pytest.mark.parametrize('exitcode',[1,2,3])
def test_prepare_failure_never_starts_controller(tmp_path,exitcode):
    calls=[]
    def runner(stage,command,cwd,logs,env):
        calls.append(stage);return {'stage':stage,'returncode':exitcode}
    rc,receipts=b.run_pipeline(tmp_path/'package',tmp_path/'old',tmp_path/'new',tmp_path,runner)
    assert rc==exitcode and calls==['prepare']


def test_one_command_keeps_whole_bundle_paths(tmp_path):
    calls=[]
    def runner(stage,command,cwd,logs,env):
        calls.append((stage,command,cwd));return {'stage':stage,'returncode':0}
    rc,_=b.run_pipeline(tmp_path/'package',tmp_path/'old',tmp_path/'new',tmp_path,runner)
    assert rc==0 and [c[0] for c in calls]==['prepare','run_all']
    assert Path(calls[1][1][1])==tmp_path/'new/tools/v162_bundle/run_all.py'
    assert calls[1][2]==tmp_path/'new'


def test_launcher_records_true_child_returncode_and_stderr(tmp_path):
    r=b.run_logged('failed',[sys.executable,'-c','import sys;print("evidence");print("err",file=sys.stderr);sys.exit(7)'],tmp_path,tmp_path,os.environ.copy())
    assert r['returncode']==7
    assert b'evidence' in (tmp_path/'failed.stdout').read_bytes()
    assert b'err' in (tmp_path/'failed.stderr').read_bytes()
    assert json.loads((tmp_path/'failed.json').read_text())['returncode']==7


def test_actual_pyz_inspection_runs_without_model_or_worktree(tmp_path):
    raw=fake_payload();sha=b.digest(raw);app=tmp_path/'launch.pyz'
    module=Path(b.__file__).read_bytes()
    main=f'from pathlib import Path\nimport sys\nfrom v162_bootstrap import main\nraise SystemExit(main(Path(sys.argv[0]),{sha!r}))\n'
    with zipfile.ZipFile(app,'w') as z:
        z.writestr('__main__.py',main);z.writestr('v162_bootstrap.py',module);z.writestr('payload.zip',raw)
    r=subprocess.run([sys.executable,'-I',str(app),'--inspect-only'],capture_output=True)
    assert r.returncode==0,r.stderr.decode()
    assert json.loads(r.stdout)['inventory_count']==1
    assert sorted(p.name for p in tmp_path.iterdir())==['launch.pyz']
