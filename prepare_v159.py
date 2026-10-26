"""Preserve the old workspace; create a new V159 worktree and restore exact frozen bytes.
No model import, no physical simulation, no old-file mutation, no global Git setting.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, shutil, subprocess, sys
from pathlib import Path, PurePosixPath
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'code'))
from v159_deployment import BASE, git, inspect_inputs, restore_new_worktree, verify_locked_inputs, digest, safe_path

def verify_package(root):
    rows=list(csv.DictReader((root/'manifest_sha256.csv').read_text(encoding='utf-8').splitlines()))
    seen=set()
    for r in rows:
        if r['path'] in seen:raise ValueError('DUPLICATE_MANIFEST_PATH')
        seen.add(r['path']);p=safe_path(root,r['path']);b=p.read_bytes()
        if len(b)!=int(r['bytes']) or digest(b)!=r['sha256']:raise ValueError('PACKAGE_HASH_MISMATCH:'+r['path'])
    expected={'manifest_sha256.csv'}|seen
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts}
    if actual!=expected:raise ValueError('PACKAGE_MEMBER_SET_MISMATCH')
    return rows

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-repo',type=Path,required=True);ap.add_argument('--worktree',type=Path,required=True)
    a=ap.parse_args();src=a.source_repo.resolve();dst=a.worktree.resolve()
    if dst.exists() or src==dst or src in dst.parents or dst in src.parents:raise ValueError('NEW_SEPARATE_WORKTREE_PATH_REQUIRED')
    rows=verify_package(ROOT)
    if git(src,'rev-parse',BASE+'^{commit}').decode().strip()!=BASE:raise ValueError('FIXED_V158_COMMIT_UNAVAILABLE')
    # Capture old-workspace diagnostics; these are read-only and never used to waive raw hashes.
    report=inspect_inputs(src)
    old_status=git(src,'status','--porcelain=v1','-uall').decode('utf-8',errors='replace')
    config=subprocess.run(['git','-C',str(src),'config','--show-origin','--get-regexp',r'core\.(autocrlf|eol|safecrlf)'],capture_output=True)
    report.update(old_worktree=str(src),old_git_status=old_status,git_line_ending_config=config.stdout.decode('utf-8',errors='replace'))
    # New branch is deliberate. Existing branch/path is never reset or removed.
    subprocess.run(['git','-C',str(src),'-c','core.autocrlf=false','-c','core.eol=lf','worktree','add','-b','v159',str(dst),BASE],check=True)
    marker=dst/'.v159-preparation.json'
    marker.write_text(json.dumps(dict(destination=str(dst),base_commit=BASE,state='PREPARING'),indent=2)+'\n',encoding='utf-8')
    out=dst/'results/v159/deployment';out.mkdir(parents=True,exist_ok=True)
    (out/'old_worktree_readonly.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    try:
        restored=restore_new_worktree(dst)
        locked=verify_locked_inputs(dst)
        target=dst/'tools/v159_bundle'
        if target.exists():raise ValueError('BUNDLE_TARGET_EXISTS')
        target.mkdir(parents=True)
        for r in rows+[dict(path='manifest_sha256.csv')]:
            rel=r['path'];p=safe_path(target,rel);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/rel).read_bytes())
        verify_package(target)
        # Add only the package. The local -text attributes preserve its exact bytes.
        subprocess.run(['git','-C',str(dst),'-c','core.autocrlf=false','add','--','tools/v159_bundle'],check=True)
        staged=git(dst,'diff','--cached','--name-only','-z').split(b'\0')
        if any(p and not p.decode('utf-8').startswith('tools/v159_bundle/') for p in staged):raise ValueError('UNEXPECTED_STAGED_FILES')
        subprocess.run(['git','-C',str(dst),'-c','core.autocrlf=false','commit','-m','V159: isolated byte-locked deployment and complete recovery workflow'],check=True)
        commit=git(dst,'rev-parse','HEAD').decode().strip()
        (out/'preparation_receipt.json').write_text(json.dumps(dict(state='PREPARED_NOT_SCIENCE_RUN',base_commit=BASE,
            code_commit=commit,old_worktree=str(src),new_worktree=str(dst),restored=restored,source_lock=locked,model_calls=0),indent=2)+'\n',encoding='utf-8')
        marker.write_text(json.dumps(dict(destination=str(dst),base_commit=BASE,state='PREPARED',code_commit=commit),indent=2)+'\n',encoding='utf-8')
        print('PREPARED_NEW_WORKTREE:',dst);print('NEXT: python tools/v159_bundle/run_all.py --repo .')
    except Exception as exc:
        import traceback
        (out/'preparation_failure.json').write_text(json.dumps(dict(error=repr(exc),traceback=traceback.format_exc(),model_calls=0),indent=2)+'\n',encoding='utf-8')
        raise
if __name__=='__main__':main()
