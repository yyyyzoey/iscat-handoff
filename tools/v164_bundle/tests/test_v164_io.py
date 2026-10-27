import csv,hashlib,importlib.util,json,os,subprocess,sys,zipfile
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from v164_io import safe_path,archive_check,git,blob

@pytest.mark.parametrize('name',['../x','/absolute','C:/absolute','a\\b','a/../../x','','x:y'])
def test_unsafe_members_rejected(tmp_path,name):
    with pytest.raises(ValueError):safe_path(tmp_path,name)


def test_relative_member_is_not_relocated(tmp_path):
    assert safe_path(tmp_path,'code/test.py')==tmp_path/'code/test.py'


def make_zip(tmp_path,damage=False,extra=False):
    target=tmp_path/'a.zip';payload=b'actual evidence'
    import io
    output=io.StringIO();w=csv.DictWriter(output,fieldnames=['path','bytes','sha256']);w.writeheader()
    w.writerow(dict(path='data.json',bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest()))
    with zipfile.ZipFile(target,'w') as z:
        z.writestr('data.json',payload+(b'changed' if damage else b''))
        z.writestr('manifest_sha256.csv',output.getvalue())
        if extra:z.writestr('unlisted.txt',b'extra')
    return target


def test_archive_full_member_set_and_hashes(tmp_path):
    r=archive_check(make_zip(tmp_path));assert r['members']==2 and r['crc_ok']

@pytest.mark.parametrize('mode',['damage','extra'])
def test_archive_rejects_changed_or_unlisted(tmp_path,mode):
    with pytest.raises(ValueError):archive_check(make_zip(tmp_path,damage=mode=='damage',extra=mode=='extra'))


def test_real_new_worktree_install_preserves_dirty_old_source(tmp_path,monkeypatch):
    root=Path(__file__).resolve().parents[1]
    spec=importlib.util.spec_from_file_location('v164_prepare_test',root/'prepare_v164.py')
    prepare=importlib.util.module_from_spec(spec);spec.loader.exec_module(prepare)
    src=tmp_path/'old';src.mkdir();subprocess.run(['git','init','-q',str(src)],check=True)
    git(src,'config','user.name','Synthetic test');git(src,'config','user.email','test@example.invalid');git(src,'config','core.autocrlf','false')
    p=src/'config/a.json';p.parent.mkdir();p.write_bytes(b'{"a":1}\n')
    git(src,'add','.');git(src,'commit','-qm','base');base=git(src,'rev-parse','HEAD').decode().strip();want=blob(p)
    p.write_bytes(b'{"a":2}\r\n');dirty=p.read_bytes()
    bundle=tmp_path/'bundle';bundle.mkdir();(bundle/'code').mkdir();(bundle/'code/example.py').write_bytes(b'x=1\n')
    with (bundle/'manifest_sha256.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);w.writeheader()
        w.writerow(dict(path='code/example.py',bytes=4,sha256=hashlib.sha256(b'x=1\n').hexdigest()))
    dst=tmp_path/'new'
    monkeypatch.setattr(prepare,'ROOT',bundle);monkeypatch.setattr(prepare,'PARENT',base)
    monkeypatch.setattr(prepare,'entries',lambda repo:[('config/a.json',want)])
    def lock(repo):
        assert blob(repo/'config/a.json')==want
        return {'config/a.json':{'git_blob':want}}
    monkeypatch.setattr(prepare,'lock_sources',lock)
    monkeypatch.setattr(sys,'argv',['prepare','--source-repo',str(src),'--worktree',str(dst)])
    assert prepare.main()==0
    assert p.read_bytes()==dirty
    assert (dst/'config/a.json').read_bytes()==b'{"a":1}\n'
    assert (dst/'tools/v164_bundle/code/example.py').read_bytes()==b'x=1\n'
    assert json.loads((dst/'results/v164/deployment/receipt.json').read_text())['model_calls']==0


def test_failure_closeout_does_not_invent_science_pass(tmp_path):
    root=Path(__file__).resolve().parents[1];out=tmp_path/'partial';out.mkdir()
    (out/'failures').mkdir();(out/'failures/000.json').write_text(json.dumps(dict(mode='preflight',error='real failure')))
    p=subprocess.run([sys.executable,str(root/'code/v164_report_pack.py'),'--out',str(out)],capture_output=True)
    assert p.returncode==0
    report=json.loads((out/'execution_integrity.json').read_text())
    assert report['status']['execution_state']=='BLOCKED_OR_FAILED_NOT_COMPLETE'
    assert report['missing_outputs'] and not report['verification_present']
    checked=archive_check(out/'iscat_v164_return.zip');assert checked['crc_ok']
