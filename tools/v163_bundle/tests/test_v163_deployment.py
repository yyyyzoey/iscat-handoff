import copy,hashlib,json,os,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
import v163_deployment as dep
import v163_run as driver
from v152_budget_store import BudgetStore
from v152_gls_core import GlsData
from v155_pixel_diagnostics import diagnose
from v163_design import complete_design


def init_repo(p):
    p.mkdir();subprocess.run(['git','init','-q',str(p)],check=True)
    dep.git(p,'config','user.name','Test');dep.git(p,'config','user.email','test@example.invalid')
    dep.git(p,'config','core.autocrlf','false')
    return p

def put_commit(p,name='config/a.json',raw=b'{"x":1}\n'):
    q=p/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw)
    dep.git(p,'add','--',name);dep.git(p,'commit','-qm','fixture')
    return dep.git(p,'rev-parse','HEAD').decode().strip()

@pytest.mark.parametrize('actual,expected,classification',[
    (b'a\r\n',b'a\n','UTF8_BOM_OR_CRLF_DIFFERENCE'),
    (b'\xef\xbb\xbfa\n',b'a\n','UTF8_BOM_OR_CRLF_DIFFERENCE'),
    (b'{ "x": 1 }',b'{"x":1}\n','JSON_FORMAT_ONLY'),
    (b'{"x":2}',b'{"x":1}','CONTENT_DIFFERENCE'),
    (b'\xff\x00',b'\xfe\x01','BINARY_DIFFERENCE'),
    (None,b'a','MISSING'),(b'a',b'a','EXACT')])
def test_mismatch_diagnosis_does_not_relax_identity(actual,expected,classification):
    assert dep.classify_bytes(actual,expected)==classification

@pytest.mark.parametrize('path',['../x','/x','C:/x','a\\b'])
def test_unsafe_relative_path_rejected(tmp_path,path):
    with pytest.raises(ValueError):dep.safe_path(tmp_path,path)


def test_collects_all_mismatches_not_only_first(tmp_path):
    p=init_repo(tmp_path/'repo');put_commit(p);base=put_commit(p,'config/b.json',b'{"z":1}\n')
    (p/'config/a.json').write_bytes(b'{"x":1}\r\n');(p/'config/b.json').write_bytes(b'{"z":3}\n')
    r=dep.inspect_inputs(p,base,['config'])
    assert len(r['mismatches'])==2
    assert {x.get('diagnosis') for x in r['files']}=={'UTF8_BOM_OR_CRLF_DIFFERENCE','CONTENT_DIFFERENCE'}


def test_raw_restore_only_new_worktree_preserves_original(tmp_path):
    src=init_repo(tmp_path/'old');base=put_commit(src)
    src_file=src/'config/a.json';src_file.write_bytes(b'{"x":9}\r\n');before=src_file.read_bytes()
    dst=tmp_path/'new';dep.git(src,'worktree','add','--detach',str(dst),base)
    (dst/'.v163-preparation.json').write_text(json.dumps(dict(destination=str(dst.resolve()),base_commit=base,state='PREPARING')))
    (dst/'config/a.json').write_bytes(b'{"x":1}\r\n')
    r=dep.restore_new_worktree(dst,base,['config'])
    assert r[0]['state']=='RESTORED_FROM_RAW_GIT_BLOB'
    assert (dst/'config/a.json').read_bytes()==b'{"x":1}\n'
    assert src_file.read_bytes()==before


def test_restore_refuses_old_worktree(tmp_path):
    src=init_repo(tmp_path/'old');base=put_commit(src)
    with pytest.raises(ValueError):dep.restore_new_worktree(src,base,['config'])


def test_restore_refuses_after_any_ledger(tmp_path):
    src=init_repo(tmp_path/'old');base=put_commit(src);dst=tmp_path/'new'
    dep.git(src,'worktree','add','--detach',str(dst),base)
    (dst/'.v163-preparation.json').write_text(json.dumps(dict(destination=str(dst.resolve()),base_commit=base,state='PREPARING')))
    ledger=dst/'results/v163/logs/v163_budget.sqlite';ledger.parent.mkdir(parents=True);ledger.write_bytes(b'PRESERVE')
    with pytest.raises(ValueError):dep.restore_new_worktree(dst,base,['config'])
    assert ledger.read_bytes()==b'PRESERVE'


def test_wrong_top_level_tools_deployment_rejected(tmp_path):
    with pytest.raises(ValueError):dep.validate_installed_layout(tmp_path/'tools/v163_run.py',tmp_path)
    assert dep.validate_installed_layout(tmp_path/'tools/v163_bundle/code/v163_run.py',tmp_path)==tmp_path/'tools/v163_bundle'


def receipt_fixture(tmp_path,monkeypatch):
    root=tmp_path/'bundle';root.mkdir();folder=tmp_path/'receipt';folder.mkdir()
    inv={'nodeids':['tests/test_a.py::test_x','tests/test_a.py::test_y']}
    (root/'test_inventory.json').write_text(json.dumps(inv))
    reports=dict(collected=inv['nodeids'],exitstatus=0,collection_errors=[],reports=[dict(nodeid=n,when=w,outcome='passed') for n in inv['nodeids'] for w in ['setup','call','teardown']])
    (folder/'test_output.txt').write_bytes(b'actual output')
    monkeypatch.setattr(dep,'bundle_hashes',lambda p:{'code/driver.py':'hash'})
    receipt=dict(scope=dep.SCOPE,returncode=0,bundle_sha256={'code/driver.py':'hash'},bundle_root=str(root.resolve()),cwd=str(root.resolve()),
                 command_tail=['-m','pytest','-q','-p','v163_receipt_plugin','tests'],output_sha256=dep.digest(b'actual output'))
    return root,folder,receipt,reports

def write_receipt(folder,r,s):
    b=json.dumps(s).encode();(folder/'pytest_outcomes.json').write_bytes(b);r['outcomes_sha256']=dep.digest(b)
    (folder/'test_receipt.json').write_text(json.dumps(r))


def test_receipt_requires_exact_test_inventory(tmp_path,monkeypatch):
    root,o,r,s=receipt_fixture(tmp_path,monkeypatch);write_receipt(o,r,s);dep.verify_test_receipt(root,o)
    s['collected']=s['collected'][:1];write_receipt(o,r,s)
    with pytest.raises(ValueError,match='COLLECTION'):dep.verify_test_receipt(root,o)

@pytest.mark.parametrize('what',['skip','wrong_command','code_changed','output_changed','test_error'])
def test_old_32_pass_or_edited_receipt_not_accepted(tmp_path,monkeypatch,what):
    root,o,r,s=receipt_fixture(tmp_path,monkeypatch)
    if what=='skip':s['reports'][1]['outcome']='skipped'
    if what=='wrong_command':r['command_tail']=['-m','pytest','-q','repo/tests']
    if what=='code_changed':r['bundle_sha256']['code/driver.py']='other'
    if what=='test_error':s['exitstatus']=1
    write_receipt(o,r,s)
    if what=='output_changed':(o/'test_output.txt').write_bytes(b'32 passed')
    with pytest.raises(ValueError):dep.verify_test_receipt(root,o)


def test_actual_cli_blocks_wrong_install_before_model(tmp_path):
    root=Path(__file__).resolve().parents[1];repo=tmp_path/'repo';repo.mkdir()
    cfg=root/'config/v163_plan.json';out=repo/'results/v163'
    r=subprocess.run([sys.executable,str(root/'code/v163_run.py'),'--repo',str(repo),'--out',str(out),'--config',str(cfg),'--mode','execute'],capture_output=True)
    assert r.returncode==2
    fail=json.loads((out/'failures/000.json').read_text());assert 'INSTALL_EXACTLY' in fail['error']
    assert not (out/'logs/v163_budget.sqlite').exists()


def synthetic_workflow(tmp_path,monkeypatch):
    """Real execute/verify control flow, synthetic optics and explicit mocked source gate."""
    repo=tmp_path/'repo';repo.mkdir();out=repo/'results/v163';out.mkdir(parents=True)
    theta=np.array([120.,450.,0.,0.]);matrix=np.zeros((169,4));matrix[:4]=np.eye(4);matrix[:,0]=.4*matrix[:,0]+np.sqrt(.84)*matrix[:,1]
    raw=matrix/np.sqrt(3.)
    def contrast(t):return (raw@(np.asarray(t)-theta)).reshape(13,13)
    gd=GlsData.from_frames(np.zeros((3,13,13)),np.ones((3,13,13)))
    diag=diagnose(gd,theta,contrast);design=complete_design(diag)
    events=[];pool={};saved={};designs={}
    def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d))
    for B,anon in sorted(driver.EXPECTED):
        key=(B,anon);name=driver.group_name(key);pool[key]=[];saved[key]=copy.deepcopy(diag);designs[name]=copy.deepcopy(design)
        for rep in range(3):
            eid=f'B{B}_{anon}_{rep:02d}'
            events.append(dict(event_id=eid,B=B,label=f'{anon}_{rep:02d}',Y=np.zeros((13,13)),V=np.ones((13,13))))
            dump(repo/'results/v146/camera_fits/events'/f'{eid}.json',dict(fit=dict(best=dict(theta=theta.tolist(),Q=0))))
        for i in range(6):
            t=theta.copy();t[0]+=i*.01
            pool[key].append(dict(theta=t.tolist(),source_record_id=f'{name}:{i}',start_index=i))
        dump(repo/f'results/v156/joint/{name}/result.json',dict(diagnostic=saved[key]))
    e1=[dict(event_id=e['event_id'],best_theta=theta.tolist(),best_Q=0) for e in events[:6]]
    dump(repo/'results/v153/all_results.json',dict(e1_regression=e1))
    cam=repo/'camera.h5';cam.write_bytes(b'not real hdf5')
    dump(repo/'config/v146_science_config.json',dict(inputs={'camera_h5':'camera.h5','camera_root':'camera'},frozen={'camera_h5_sha256':driver.sha_file(cam)}))
    model=SimpleNamespace(forward=lambda t:SimpleNamespace(score_C=contrast(t)),model_id='SYNTHETIC_ONLY')
    def gate(repo,cfg,out):
        pre=dict(source_lock={},driver_sha256=driver.sha_file(driver.__file__))
        dump(out/'preflight.json',pre);dump(out/'design/saved_array_designs.json',designs)
        return pre,pool,saved,designs
    def construct(repo,store,out,signature):
        class Loader:
            def forward(self,t):return SimpleNamespace(score_C=contrast(t))
        def work(task):
            with driver.count_loader(Loader,store,task):Loader().forward(theta)
            return dict(model_id='SYNTHETIC_ONLY')
        driver.run_task(store,'LOADER_1','REPAIR_AND_ANCHOR',100,out,signature,work)
        return model
    monkeypatch.setattr(driver,'preflight',gate)
    monkeypatch.setattr(driver,'verify_locked_tree',lambda r:{})
    monkeypatch.setattr(driver,'check_test_receipt',lambda *a:{})
    monkeypatch.setattr(driver,'construct_counted',construct)
    monkeypatch.setattr(driver,'import_repo',lambda r,n:SimpleNamespace(camera_events=lambda *a:events))
    cfg=json.loads((Path(__file__).parents[1]/'config/v163_plan.json').read_text())
    driver.execute(repo,cfg,out)
    return repo,out,cfg


def test_execute_verify_end_to_end_synthetic(tmp_path,monkeypatch):
    repo,out,cfg=synthetic_workflow(tmp_path,monkeypatch)
    r=driver.verify_saved(repo,cfg,out)
    assert r['new_model_calls']==0
    assert len(list((out/'probes').glob('*/*[0-9].json')))==72
    assert json.loads((out/'status.json').read_text())['execution_state']=='FINISHED'

@pytest.mark.parametrize('remove',['probe','selected','rescore','replay','task'])
def test_missing_artifact_cannot_receive_verify_pass(tmp_path,monkeypatch,remove):
    repo,out,cfg=synthetic_workflow(tmp_path,monkeypatch)
    if remove=='probe':p=next((out/'probes').glob('*/00.json'))
    elif remove=='selected':p=out/'selected_candidates_12.json'
    elif remove=='rescore':p=next((out/'rescored').glob('*.json'))
    elif remove=='replay':p=next((out/'replay').glob('*.json'))
    else:p=out/'tasks/FINAL_VERIFY/result.json'
    p.unlink()
    with pytest.raises((ValueError,FileNotFoundError)):driver.verify_saved(repo,cfg,out)


def test_blocked_run_can_be_packaged_without_status(tmp_path):
    import zipfile,csv,io
    root=Path(__file__).parents[1];out=tmp_path/'repo/results/v163';out.mkdir(parents=True)
    (out/'failures').mkdir();(out/'failures/000.json').write_text(json.dumps(dict(state='BLOCKED',error='source mismatch')))
    p=subprocess.run([sys.executable,str(root/'code/v163_report_pack.py'),'--out',str(out)],capture_output=True)
    assert p.returncode==0,p.stderr
    truth=json.loads((out/'execution_integrity.json').read_text())
    assert truth['execution_state']=='BLOCKED_OR_FAILED_NO_FINAL_STATUS' and not truth['verification_present']
    with zipfile.ZipFile(out/'iscat_v163_return.zip') as z:
        assert z.testzip() is None
        rows=list(csv.DictReader(io.StringIO(z.read('manifest_sha256.csv').decode())))
        for row in rows:
            b=z.read(row['path']);assert len(b)==int(row['bytes']) and dep.digest(b)==row['sha256']


def test_numpy_comparison_count_must_be_native_int():
    from v152_budget_store import canonical
    records=[dict(state='EVALUATED',relative_linearization_error=np.float64(.01))]
    legacy=sum(r['state']=='EVALUATED' and r['relative_linearization_error'] is not None and r['relative_linearization_error']<=.05 for r in records)
    assert isinstance(legacy,np.integer)
    with pytest.raises(TypeError):canonical(dict(linear_points=legacy))
    fixed=sum(1 for r in records if r['state']=='EVALUATED' and r['relative_linearization_error'] is not None and r['relative_linearization_error']<=.05)
    assert isinstance(fixed,int) and json.loads(canonical(dict(linear_points=fixed)))=={'linear_points':1}
