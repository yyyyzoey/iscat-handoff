"""Whole-package installation only into a new worktree. Does not run physics."""
from pathlib import Path
import argparse,csv,hashlib,json,os,subprocess,sys,uuid
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'code'))
from v164_io import PARENT,entries,git,blob,lock_sources,safe_path

def package_check():
    rows=list(csv.DictReader((ROOT/'manifest_sha256.csv').read_text(encoding='utf-8').splitlines()))
    wanted={'manifest_sha256.csv'}|{r['path'] for r in rows}
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts}
    if wanted!=actual or len(wanted)!=len(rows)+1:raise ValueError('PACKAGE_SET_OR_DUPLICATE')
    for row in rows:
        p=safe_path(ROOT,row['path']);raw=p.read_bytes()
        if len(raw)!=int(row['bytes']) or hashlib.sha256(raw).hexdigest()!=row['sha256']:raise ValueError('PACKAGE_HASH:'+row['path'])
    return sorted(wanted)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-repo',type=Path,required=True);ap.add_argument('--worktree',type=Path,required=True);a=ap.parse_args()
    src=a.source_repo.resolve();dst=a.worktree.resolve();files=package_check()
    if dst.exists() or src==dst or src in dst.parents or dst in src.parents:raise ValueError('NEW_SEPARATE_DIRECTORY_REQUIRED')
    if git(src,'rev-parse',PARENT+'^{commit}').decode().strip()!=PARENT:raise ValueError('FETCH_FIXED_V163_COMMIT_FIRST')
    old_status=git(src,'status','--porcelain=v1','-uall').decode('utf-8',errors='replace')
    subprocess.run(['git','-C',str(src),'-c','core.autocrlf=false','worktree','add','-b','v164',str(dst),PARENT],check=True)
    out=dst/'results/v164/deployment';out.mkdir(parents=True,exist_ok=True)
    (out/'old_worktree_status.txt').write_text(old_status,encoding='utf-8')
    restored=[]
    try:
        # Copies exact immutable raw blobs only into this newly created worktree.
        for rel,want in entries(dst):
            p=dst/rel
            if p.is_file() and blob(p)==want:continue
            p.parent.mkdir(parents=True,exist_ok=True);temp=p.with_name(p.name+'.'+uuid.uuid4().hex+'.restore')
            with temp.open('xb') as f:
                r=subprocess.run(['git','-C',str(dst),'cat-file','blob',want],stdout=f,stderr=subprocess.PIPE)
                f.flush();os.fsync(f.fileno())
            if r.returncode or blob(temp)!=want:raise ValueError('OBJECT_RESTORE_FAILED:'+rel)
            os.replace(temp,p);restored.append(rel)
        locked=lock_sources(dst)
        target=dst/'tools/v164_bundle'
        if target.exists():raise ValueError('NEW_BUNDLE_PATH_EXISTS')
        for rel in files:
            p=safe_path(target,rel);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/rel).read_bytes())
        subprocess.run(['git','-C',str(dst),'-c','core.autocrlf=false','add','--','tools/v164_bundle'],check=True)
        staged=git(dst,'diff','--cached','--name-only','-z').split(b'\0')
        if any(p and not p.startswith(b'tools/v164_bundle/') for p in staged):raise ValueError('UNEXPECTED_STAGED_PATH')
        subprocess.run(['git','-C',str(dst),'-c','core.autocrlf=false','commit','-m','V164: bounded fixed-D conditional model-separation experiment'],check=True)
        (out/'receipt.json').write_text(json.dumps(dict(parent=PARENT,code_commit=git(dst,'rev-parse','HEAD').decode().strip(),source_repo=str(src),worktree=str(dst),restored=restored,source_lock=locked,model_calls=0),indent=2)+'\n',encoding='utf-8')
        print('PREPARED',dst);return 0
    except Exception as exc:
        import traceback
        (out/'failure.json').write_text(json.dumps(dict(error=repr(exc),traceback=traceback.format_exc(),model_calls=0),indent=2)+'\n',encoding='utf-8')
        raise
if __name__=='__main__':raise SystemExit(main())
