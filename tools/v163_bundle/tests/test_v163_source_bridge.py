"""V162 regression checks: source-pin satisfiability and pytest 7 nose collision.
No model import or physical computation is performed by these tests.
"""
from pathlib import Path
import ast,hashlib,json,subprocess,sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'))
import v163_source_bridge as bridge
import v163_deployment as dep


def pair():
    p=ROOT/'audit/source_identity'
    return (p/'base_LF.py.txt').read_bytes(),(p/'archived_CRLF.py.txt').read_bytes()


def test_real_129_line_ending_pair_matches_both_published_identities():
    a,b=pair();r=bridge.compare_pair(a,b,bridge.RUNTIME_SHA256)
    assert r['original_bytes']==9533 and r['runtime_bytes']==9662
    assert b.replace(b'\r\n',b'\n')==a
    assert r['AST_equal'] and r['normalized_bytes_equal']

@pytest.mark.parametrize('which',['base','archive','pin'])
def test_any_unreviewed_byte_or_pin_rejected(which):
    a,b=pair();pin=bridge.RUNTIME_SHA256
    if which=='base':a+=b'\n'
    elif which=='archive':b=b.replace(b'q=c[',b'q =c[',1)
    else:pin='0'*64
    with pytest.raises(ValueError):bridge.compare_pair(a,b,pin)

@pytest.mark.parametrize('variant',['lf_archive','crlf_base','bom_base','bom_archive','single_space'])
def test_no_general_line_ending_or_format_waiver(variant):
    a,b=pair()
    if variant=='lf_archive':b=a
    elif variant=='crlf_base':a=b
    elif variant=='bom_base':a=b'\xef\xbb\xbf'+a
    elif variant=='bom_archive':b=b'\xef\xbb\xbf'+b
    else:b+=b' '
    with pytest.raises(ValueError):bridge.compare_pair(a,b,bridge.RUNTIME_SHA256)


def fixture_repo(tmp):
    p=tmp/'repo';p.mkdir();subprocess.run(['git','init','-q',str(p)],check=True)
    def git(*args):return bridge.git(p,*args)
    git('config','user.name','Local source QA');git('config','user.email','qa@example.invalid');git('config','core.autocrlf','false')
    (p/'.gitattributes').write_bytes(b'* -text\n')
    a,b=pair()
    for rel,data in [(bridge.TARGET,a),(bridge.ARCHIVE,b)]:
        q=p/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data)
    q=p/'config/v146_science_config.json';q.parent.mkdir();q.write_text(json.dumps({'frozen':{'source_sha256':{bridge.TARGET:bridge.RUNTIME_SHA256}}}))
    git('add','.');git('commit','-qm','two exact identities')
    return p,git('rev-parse','HEAD').decode().strip()


def test_actual_git_raw_archive_selects_the_runtime_pin(tmp_path):
    p,commit=fixture_repo(tmp_path)
    r=bridge.bridge_from_git(p,commit)
    assert r['runtime_git_blob']==bridge.RUNTIME_BLOB
    with pytest.raises(ValueError,match='UNSATISFIABLE_BEFORE_MODEL'):bridge.verify_runtime_pins(p)
    # Exact archived copy, never hash rewriting or generic normalization.
    (p/bridge.TARGET).write_bytes((p/bridge.ARCHIVE).read_bytes())
    assert bridge.verify_runtime_pins(p)['all_match']


def test_tree_mapping_changes_one_and_only_one_identity(tmp_path):
    p,commit=fixture_repo(tmp_path)
    rows=dep.tree_entries(p,commit,[bridge.TARGET,bridge.ARCHIVE,'config/v146_science_config.json'])
    assert dict(rows)[bridge.TARGET]==bridge.RUNTIME_BLOB
    assert dict(rows)[bridge.ARCHIVE]==bridge.RUNTIME_BLOB
    assert len(rows)==3
    assert (p/bridge.TARGET).read_bytes()==pair()[0] # inspection does not mutate


def test_restore_exact_runtime_bytes_only_in_new_marked_worktree(tmp_path):
    src,commit=fixture_repo(tmp_path);dst=tmp_path/'fresh'
    bridge.git(src,'worktree','add','--detach',str(dst),commit)
    (dst/'.v163-preparation.json').write_text(json.dumps(dict(destination=str(dst.resolve()),base_commit=commit,state='PREPARING')))
    report=dep.restore_new_worktree(dst,commit,[bridge.TARGET,bridge.ARCHIVE,'config/v146_science_config.json'])
    assert (src/bridge.TARGET).read_bytes()==pair()[0]
    assert (dst/bridge.TARGET).read_bytes()==pair()[1]
    assert bridge.verify_runtime_pins(dst)['all_match']
    assert len([r for r in report if r['state']=='RESTORED_FROM_RAW_GIT_BLOB'])==1


def test_source_pin_check_is_before_model_task_creation():
    tree=ast.parse((ROOT/'code/v163_run.py').read_text())
    pre=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='preflight')
    calls=[n.func.id for n in ast.walk(pre) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
    assert 'verify_runtime_pins' in calls and 'BudgetStore' not in calls


def test_no_nose_module_level_setup_helper_in_complete_suite():
    for p in (ROOT/'tests').glob('test_*.py'):
        tree=ast.parse(p.read_text())
        assert not any(isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)) and x.name in ('setup','teardown') for x in tree.body),p.name


def test_original_problem_helper_only_renamed_assertions_remain():
    text=(ROOT/'tests/test_v163.py').read_text()
    assert 'def make_case(theta=None)' in text
    assert 'def setup(' not in text


def test_callers_cannot_silently_inject_pytest_addopts():
    text=(ROOT/'run_workstation_tests.py').read_text()
    assert "env.pop('PYTEST_ADDOPTS',None)" in text
    assert 'pytest_addopts_ignored' in text and 'pytest_version=' in text


def test_budget_and_approved_science_kernels_not_changed():
    cfg=json.loads((ROOT/'config/v163_plan.json').read_text())
    assert cfg['total']==500 and cfg['phases']=={'REPAIR_AND_ANCHOR':260,'NONLINEAR_PROBES':120,'FINAL_VERIFY':120}
    locks=json.loads((ROOT/'config/kernel_lock.json').read_text())
    for name,want in locks.items():
        assert hashlib.sha256((ROOT/'code'/name).read_bytes()).hexdigest()==want


def test_return_context_keeps_exact_source_bytes(tmp_path):
    s=tmp_path/'source.json';d=tmp_path/'context'/'source.json';raw=b'{"x":1}\r\n';s.write_bytes(raw)
    r=bridge.copy_verified_context(s,d,bridge.sha(raw));assert d.read_bytes()==raw and r['model_calls']==0
    bridge.copy_verified_context(s,d,bridge.sha(raw)) # verified idempotent copy only


def test_return_context_wrong_identity_never_overwrites(tmp_path):
    s=tmp_path/'source';d=tmp_path/'dest';s.write_bytes(b'original');d.write_bytes(b'old')
    with pytest.raises(ValueError):bridge.copy_verified_context(s,d,bridge.sha(b'original'))
    assert d.read_bytes()==b'old'
