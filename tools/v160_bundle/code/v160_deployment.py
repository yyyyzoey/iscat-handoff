"""V160 deployment identities. Never changes historical source files or loads optics."""
from __future__ import annotations
import csv, hashlib, json, os, subprocess, uuid
from pathlib import Path, PurePosixPath

BASE='71333a9f193d00012972e8fd6c188805c7a6b18e'
PREFIXES=(
 'config/v146_science_config.json','config/v133_science_config.json',
 'tools/v142_model.py','tools/v142_field_reference.py','tools/field_forward_reference.py',
 'tools/load_field_library.py','tools/v133_recover_M.py','tools/v146_core.py',
 'tools/v146_runtime.py','tools/v146_fit_saved_camera.py',
 'results/v128/library/v128_Dh_train_fields.h5',
 'results/v143/validation/camera_pilot','results/v146/camera_fits/events',
 'results/v152/all_results.json','results/v153/all_results.json',
 'results/v156','results/v157','results/v158')
SCOPE='COMPONENT_AND_SYNTHETIC_MODEL_TESTS_NOT_PHYSICAL_VALIDATION'

def digest(raw):return hashlib.sha256(raw).hexdigest()
def blob(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
def file_identity(path):
    p=Path(path);size=p.stat().st_size;g=hashlib.sha1(b'blob '+str(size).encode()+b'\0');s=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):g.update(b);s.update(b)
    return dict(bytes=size,git_blob=g.hexdigest(),sha256=s.hexdigest())

def git(repo,*args):
    return subprocess.run(['git','-C',str(repo),*args],capture_output=True,check=True).stdout

def safe_path(root,rel):
    p=PurePosixPath(rel)
    if p.is_absolute() or '..' in p.parts or '\\' in rel or not p.parts or ':' in p.parts[0]:
        raise ValueError('UNSAFE_PATH:'+rel)
    root=Path(root).resolve();target=root.joinpath(*p.parts)
    if any(x.is_symlink() for x in (target,*target.parents) if x!=root.parent):
        raise ValueError('SYMLINK_FORBIDDEN:'+rel)
    if root not in target.resolve().parents:raise ValueError('PATH_ESCAPES_ROOT:'+rel)
    return target

def tree_entries(repo,base=BASE,prefixes=PREFIXES):
    raw=git(repo,'ls-tree','-r','-z',base,'--',*prefixes)
    entries=[]
    for line in raw.split(b'\0'):
        if not line:continue
        header,name=line.split(b'\t',1);mode,kind,sha=header.decode('ascii').split()
        rel=name.decode('utf-8')
        if kind!='blob' or mode not in ('100644','100755'):raise ValueError('UNSUPPORTED_SOURCE:'+rel)
        safe_path(repo,rel);entries.append((rel,sha))
    for prefix in prefixes:
        if not any(p==prefix or p.startswith(prefix+'/') for p,_ in entries):raise ValueError('MISSING_FROZEN_PREFIX:'+prefix)
    return entries

def classify_bytes(actual,expected):
    if actual is None:return 'MISSING'
    if actual==expected:return 'EXACT'
    try:
        a=actual.decode('utf-8-sig');e=expected.decode('utf-8-sig')
        if a.replace('\r\n','\n')==e.replace('\r\n','\n'):return 'UTF8_BOM_OR_CRLF_DIFFERENCE'
        try:
            if json.loads(a)==json.loads(e):return 'JSON_FORMAT_ONLY'
        except (ValueError,TypeError):pass
        return 'CONTENT_DIFFERENCE'
    except UnicodeError:return 'BINARY_DIFFERENCE'

def inspect_inputs(repo,base=BASE,prefixes=PREFIXES):
    """All paths, not only first mismatch. Classification NEVER waives raw identity."""
    rows=[]
    for rel,want in tree_entries(repo,base,prefixes):
        p=safe_path(repo,rel)
        actual=file_identity(p) if p.is_file() else None
        state='EXACT' if actual and actual['git_blob']==want else 'MISMATCH'
        row=dict(path=rel,expected_git_blob=want,actual=actual,state=state)
        if state!='EXACT':
            size=int(git(repo,'cat-file','-s',want))
            if size<=2*1024*1024 and (actual is None or actual['bytes']<=2*1024*1024):
                expected=git(repo,'cat-file','blob',want)
                row['diagnosis']=classify_bytes(p.read_bytes() if p.is_file() else None,expected)
            else:row['diagnosis']='LARGE_OR_BINARY_MISMATCH_NOT_SEMANTICALLY_CLASSIFIED'
        rows.append(row)
    return dict(base_commit=base,scope='RAW_SOURCE_BYTES_NOT_PHYSICS',files=rows,
                mismatches=[r['path'] for r in rows if r['state']!='EXACT'],model_calls=0)

def verify_locked_inputs(repo,base=BASE):
    locked={}
    for rel,want in tree_entries(repo,base):
        p=safe_path(repo,rel)
        if not p.is_file():raise ValueError('MISSING_FROZEN_INPUT:'+rel)
        actual=file_identity(p)
        if actual['git_blob']!=want:raise ValueError('WORKTREE_NOT_FIXED_GIT_BYTES:'+rel)
        locked[rel]=actual
    return locked

def restore_new_worktree(repo,base=BASE,prefixes=PREFIXES):
    """Raw git blobs -> ONLY a newly created linked worktree carrying our marker."""
    repo=Path(repo).resolve();marker=repo/'.v160-preparation.json'
    if not (repo/'.git').is_file() or not marker.is_file():raise ValueError('NEW_LINKED_WORKTREE_MARKER_REQUIRED')
    data=json.loads(marker.read_text(encoding='utf-8'))
    if data.get('destination')!=str(repo) or data.get('base_commit')!=base or data.get('state')!='PREPARING':raise ValueError('PREPARATION_IDENTITY_MISMATCH')
    if (repo/'results/v160/logs/v160_budget.sqlite').exists():raise ValueError('NO_REPAIR_AFTER_MODEL_RUN')
    rows=[]
    for rel,want in tree_entries(repo,base,prefixes):
        p=safe_path(repo,rel);p.parent.mkdir(parents=True,exist_ok=True)
        before=file_identity(p) if p.is_file() else None
        if before and before['git_blob']==want:
            rows.append(dict(path=rel,state='ALREADY_EXACT',identity=before));continue
        tmp=p.with_name(p.name+'.'+uuid.uuid4().hex+'.restore')
        try:
            with tmp.open('xb') as f:
                proc=subprocess.run(['git','-C',str(repo),'cat-file','blob',want],stdout=f,stderr=subprocess.PIPE)
                f.flush();os.fsync(f.fileno())
            if proc.returncode:raise RuntimeError('GIT_OBJECT_READ_FAILED:'+rel+':'+proc.stderr.decode(errors='replace'))
            after=file_identity(tmp)
            if after['git_blob']!=want:raise ValueError('RAW_OBJECT_IDENTITY_FAILED:'+rel)
            os.replace(tmp,p)
            rows.append(dict(path=rel,state='RESTORED_FROM_RAW_GIT_BLOB',before=before,identity=after))
        finally:
            if tmp.exists():tmp.unlink()
    return rows

def bundle_files(root):
    root=Path(root)
    files=[p.relative_to(root).as_posix() for folder,pattern in [('code','*.py'),('tests','test_*.py'),('config','*.json')] for p in sorted((root/folder).glob(pattern))]
    files += ['prepare_v160.py','run_workstation_tests.py','run_all.py','test_inventory.json']
    if not files or any(not (root/p).is_file() for p in files):raise ValueError('INCOMPLETE_EXECUTION_BUNDLE')
    return sorted(files)

def bundle_hashes(root):return {rel:digest((Path(root)/rel).read_bytes()) for rel in bundle_files(root)}

def validate_installed_layout(driver,repo):
    expected=Path(repo).resolve()/'tools/v160_bundle/code/v160_run.py'
    if Path(driver).resolve()!=expected:raise ValueError('INSTALL_EXACTLY_TO_TOOLS_V160_BUNDLE_CODE')
    return expected.parent.parent

def verify_test_receipt(root,folder):
    root,folder=Path(root).resolve(),Path(folder).resolve()
    receipt=json.loads((folder/'test_receipt.json').read_text(encoding='utf-8'))
    inv=json.loads((root/'test_inventory.json').read_text(encoding='utf-8'))
    reports=json.loads((folder/'pytest_outcomes.json').read_text(encoding='utf-8'))
    if receipt.get('scope')!=SCOPE or receipt.get('returncode')!=0:raise ValueError('WORKSTATION_TESTS_NOT_SUCCESSFUL')
    if receipt.get('bundle_sha256')!=bundle_hashes(root):raise ValueError('TESTED_BUNDLE_CHANGED')
    if receipt.get('bundle_root')!=str(root) or Path(receipt.get('cwd','')).resolve()!=root:raise ValueError('TEST_RECEIPT_WRONG_BUNDLE_ROOT')
    if receipt.get('command_tail')!=['-m','pytest','-q','-p','v160_receipt_plugin','tests']:raise ValueError('WRONG_TEST_SUITE_COMMAND')
    if digest((folder/'test_output.txt').read_bytes())!=receipt.get('output_sha256'):raise ValueError('TEST_OUTPUT_CHANGED')
    if digest((folder/'pytest_outcomes.json').read_bytes())!=receipt.get('outcomes_sha256'):raise ValueError('TEST_OUTCOMES_CHANGED')
    if sorted(reports.get('collected',[]))!=inv['nodeids']:raise ValueError('TEST_COLLECTION_NOT_COMPLETE')
    if reports.get('exitstatus')!=0 or reports.get('collection_errors'):raise ValueError('TEST_SESSION_NOT_SUCCESSFUL')
    outcomes=reports.get('reports',[])
    for node in inv['nodeids']:
        phases=[r for r in outcomes if r['nodeid']==node]
        if {(r['when'],r['outcome']) for r in phases}!={('setup','passed'),('call','passed'),('teardown','passed')} or len(phases)!=3:
            raise ValueError('TEST_SKIPPED_FAILED_OR_INCOMPLETE:'+node)
    if len(outcomes)!=3*len(inv['nodeids']):raise ValueError('EXTRA_OR_DUPLICATE_TEST_REPORTS')
    return receipt
