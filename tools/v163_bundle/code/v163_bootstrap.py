"""Standard-library-only, complete-package launcher; never runs a model itself.

A .pyz carries this module and the complete immutable payload. No individual
source file or test receipt is copied by hand. Old workspaces are read-only.
"""
from __future__ import annotations
import argparse
import csv
import datetime
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import traceback
import uuid
import zipfile

VERSION = 'v163'
PARENT = 'dc919aada7cc750c19383470021878fab5814db5'
MAX_UNCOMPRESSED = 64 * 1024 * 1024
REQUIRED = {
    '.gitattributes', 'prepare_v163.py', 'run_all.py',
    'run_workstation_tests.py', 'test_inventory.json', 'manifest_sha256.csv',
    'config/v163_plan.json', 'code/v163_run.py',
    'code/v163_deployment.py', 'code/v163_receipt_plugin.py',
    'tests/test_v163_deployment.py', 'tests/test_v163_intake.py',
    'tests/test_v163_bootstrap.py', 'code/v163_semantics.py', 'config/kernel_lock.json',
    'tests/test_v163_semantics.py','code/v163_source_bridge.py','tests/test_v163_source_bridge.py',
}

def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def relative_name(name: str) -> str:
    p = PurePosixPath(name)
    if (not name or p.is_absolute() or '..' in p.parts or '\\' in name
            or ':' in name or str(p) != name or name.endswith('/')):
        raise ValueError('UNSAFE_OR_NONCANONICAL_ARCHIVE_PATH:' + name)
    return name


def verify_payload(raw: bytes, expected_sha256: str) -> dict:
    if digest(raw) != expected_sha256:
        raise ValueError('EMBEDDED_PAYLOAD_HASH_MISMATCH')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        infos = z.infolist()
        names = [relative_name(x.filename) for x in infos]
        if len(set(names)) != len(names) or len({n.casefold() for n in names}) != len(names):
            raise ValueError('DUPLICATE_OR_CASE_COLLIDING_MEMBER')
        if sum(i.file_size for i in infos) > MAX_UNCOMPRESSED:
            raise ValueError('PAYLOAD_TOO_LARGE')
        if any(stat.S_ISLNK(i.external_attr >> 16) for i in infos):
            raise ValueError('SYMLINK_MEMBER_FORBIDDEN')
        if not REQUIRED.issubset(names):
            raise ValueError('INCOMPLETE_PAYLOAD:' + ','.join(sorted(REQUIRED-set(names))))
        if z.testzip() is not None:
            raise ValueError('PAYLOAD_CRC_FAILED')
        rows = list(csv.DictReader(io.StringIO(z.read('manifest_sha256.csv').decode('utf-8'))))
        paths = [relative_name(r['path']) for r in rows]
        if len(set(paths)) != len(paths):
            raise ValueError('DUPLICATE_MANIFEST_ROW')
        if set(names) != set(paths) | {'manifest_sha256.csv'}:
            raise ValueError('PAYLOAD_MANIFEST_MEMBER_SET_MISMATCH')
        for r in rows:
            b = z.read(r['path'])
            if len(b) != int(r['bytes']) or digest(b) != r['sha256']:
                raise ValueError('PAYLOAD_MANIFEST_HASH_MISMATCH:' + r['path'])
        inventory = json.loads(z.read('test_inventory.json'))
        nodes = inventory.get('nodeids', [])
        if not nodes or len(nodes) != len(set(nodes)):
            raise ValueError('EMPTY_OR_DUPLICATE_TEST_INVENTORY')
        return dict(payload_sha256=digest(raw), members=len(names),
                    manifest_rows=len(rows), inventory_count=len(nodes),
                    scope='PACKAGE_BYTES_ONLY_NOT_TEST_OR_SCIENCE_ACCEPTANCE')


def extract_verified(raw: bytes, dest: Path, expected_sha256: str) -> dict:
    result = verify_payload(raw, expected_sha256)
    if dest.exists():
        raise ValueError('EXTRACTION_DESTINATION_EXISTS')
    dest.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for name in z.namelist():
            target = dest.joinpath(*PurePosixPath(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as f:
                f.write(z.read(name))
        for r in csv.DictReader(io.StringIO(z.read('manifest_sha256.csv').decode('utf-8'))):
            b = (dest/r['path']).read_bytes()
            if len(b) != int(r['bytes']) or digest(b) != r['sha256']:
                raise ValueError('EXTRACTED_FILE_MISMATCH:' + r['path'])
    return result


def save_json(path: Path, obj: dict) -> None:
    b = (json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode('utf-8')
    tmp = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    with tmp.open('xb') as f:
        f.write(b); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)


def run_logged(stage: str, command: list[str], cwd: Path, logroot: Path, env: dict) -> dict:
    """Keep exact bytes and return code. Never invent a test count or success."""
    started = utc()
    print(stage + ': starting', flush=True)
    with (logroot/(stage+'.stdout')).open('xb') as out, (logroot/(stage+'.stderr')).open('xb') as err:
        p = subprocess.run(command, cwd=cwd, stdout=out, stderr=err, env=env)
    rec = dict(stage=stage, command=command, cwd=str(cwd), returncode=p.returncode,
               started_utc=started, ended_utc=utc(),
               stdout_sha256=digest((logroot/(stage+'.stdout')).read_bytes()),
               stderr_sha256=digest((logroot/(stage+'.stderr')).read_bytes()))
    save_json(logroot/(stage+'.json'), rec)
    print(stage + ': exit ' + str(p.returncode), flush=True)
    return rec


def run_pipeline(payload_root: Path, src: Path, dst: Path, logs: Path, runner=run_logged) -> tuple[int, list[dict]]:
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    commands = [
        ('prepare', [sys.executable, str(payload_root/'prepare_v163.py'),
                     '--source-repo', str(src), '--worktree', str(dst)], payload_root),
        ('run_all', [sys.executable, str(dst/'tools/v163_bundle/run_all.py'),
                     '--repo', str(dst)], dst),
    ]
    receipts = []
    for name, cmd, cwd in commands:
        r = runner(name, cmd, cwd, logs, env)
        receipts.append(r)
        if r['returncode']:
            return int(r['returncode']), receipts
    return 0, receipts


def environment_check(src: Path, dst: Path) -> dict:
    if sys.version_info < (3, 10):
        raise ValueError('PYTHON_3_10_OR_NEWER_REQUIRED')
    missing = [m for m in ('numpy','scipy','h5py','pytest') if importlib.util.find_spec(m) is None]
    if missing:
        raise ValueError('MISSING_DEPENDENCIES_IN_THIS_INTERPRETER:' + ','.join(missing))
    if shutil.which('git') is None:
        raise ValueError('GIT_EXECUTABLE_NOT_FOUND')
    if dst.exists() or src == dst or src in dst.parents or dst in src.parents:
        raise ValueError('NEW_SEPARATE_WORKTREE_REQUIRED')
    r = subprocess.run(['git','-C',str(src),'rev-parse','--show-toplevel'],capture_output=True,check=True)
    if Path(os.fsdecode(r.stdout).strip()).resolve() != src:
        raise ValueError('SOURCE_REPO_MUST_BE_REPOSITORY_ROOT')
    subprocess.run(['git','-C',str(src),'cat-file','-e',PARENT+'^{commit}'],capture_output=True,check=True)
    head=subprocess.run(['git','-C',str(src),'rev-parse','HEAD'],capture_output=True,check=True).stdout.decode().strip()
    subprocess.run(['git','-C',str(src),'merge-base','--is-ancestor',PARENT,head],capture_output=True,check=True)
    branch = subprocess.run(['git','-C',str(src),'show-ref','--verify','--quiet','refs/heads/v163'])
    if branch.returncode == 0:
        raise ValueError('V163_BRANCH_EXISTS_NO_AUTOMATIC_RESET_OR_RERUN')
    if branch.returncode != 1:
        raise ValueError('CANNOT_CHECK_V163_BRANCH')
    return dict(python=sys.version, executable=sys.executable, reviewed_parent=PARENT,
                source_repo=str(src), new_worktree=str(dst))


def main(archive_path: Path, expected_payload_sha256: str) -> int:
    ap=argparse.ArgumentParser(description='V163 complete-package launcher; no manual file copying.')
    ap.add_argument('--inspect-only', action='store_true', help='Verify the embedded package without creating a worktree or calling a model.')
    ap.add_argument('--source-repo', type=Path)
    ap.add_argument('--worktree', type=Path)
    args=ap.parse_args()
    with zipfile.ZipFile(archive_path) as outer:
        raw=outer.read('payload.zip')
    check=verify_payload(raw, expected_payload_sha256)
    if args.inspect_only:
        print(json.dumps(check, ensure_ascii=False, indent=2));return 0
    if args.source_repo is None or args.worktree is None:
        ap.error('--source-repo and --worktree are required unless --inspect-only')
    src=args.source_repo.resolve();dst=args.worktree.resolve()
    # Forensic logs live outside BOTH workspaces; never overwrite old logs.
    if dst.parent == src or src in dst.parent.parents:
        raise ValueError('DESTINATION_MUST_BE_OUTSIDE_OLD_REPO')
    dst.parent.mkdir(parents=True, exist_ok=True)
    evidence=dst.parent/('v163_launcher_'+uuid.uuid4().hex)
    evidence.mkdir(exist_ok=False)
    state=dict(task='V163',started_utc=utc(),package=check,
               launcher_sha256=digest(archive_path.read_bytes()),
               reviewed_parent=PARENT, scientific_acceptance=False,
               experimental_absolute_diameter_validated=False)
    code=2
    try:
        state['environment']=environment_check(src,dst)
        package=evidence/'package'
        extract_verified(raw,package,expected_payload_sha256)
        state['state']='PACKAGE_VERIFIED_NOT_SCIENCE_EXECUTED'
        save_json(evidence/'launcher_state.json',state)
        code,receipts=run_pipeline(package,src,dst,evidence)
        state.update(command_receipts=receipts,returncode=code,
                     state='PIPELINE_RETURNED_READ_VERIFICATION' if code==0 else 'BLOCKED_OR_FAILED',
                     resource_statement='Model counts must be read from the persistent ledger; no zero is inferred from a failed command.')
    except Exception as exc:
        state.update(state='BLOCKED_OR_FAILED',error_type=type(exc).__name__,error=repr(exc),traceback=traceback.format_exc(),returncode=2)
    finally:
        state['ended_utc']=utc();save_json(evidence/'launcher_state.json',state)
        # The pipeline's own packer may already have run; append launcher evidence
        # only after commands finish, then regenerate one complete result archive.
        result=dst/'results/v163'
        if (result/'deployment/preparation_receipt.json').is_file():
            target=result/'launcher'/evidence.name
            target.mkdir(parents=True,exist_ok=False)
            for p in evidence.iterdir():
                if p.is_file():shutil.copyfile(p,target/p.name)
            packer=dst/'tools/v163_bundle/code/v163_report_pack.py'
            env=os.environ.copy();env.pop('PYTHONPATH',None);env['PYTHONDONTWRITEBYTECODE']='1'
            rr=run_logged('final_pack',[sys.executable,str(packer),'--out',str(result)],dst,evidence,env)
            if rr['returncode']:code=code or rr['returncode']
        print('LAUNCHER_EVIDENCE:',evidence,flush=True)
        print('Read stage_commands, failures and verification; a returned process is not experimental validation.',flush=True)
    return code
