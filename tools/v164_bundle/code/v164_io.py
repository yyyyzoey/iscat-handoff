"""Read-only V163 provenance gates and byte-safe I/O. No optics imported here."""
from __future__ import annotations
import csv,hashlib,json,sqlite3,subprocess,zipfile
from pathlib import Path,PurePosixPath
import numpy as np
from v152_budget_store import atomic_json,canonical

PARENT='06c54419c590b6ddadc50cd6117a7a54b2cf5ddf'
OLD_ZIP_SHA='9bc04fc03ea194ae4b1abaf61baa2b73a7d843679df67d71f3114ffb820bd8b7'
PREFIXES=('tools','config','results/v128/library/v128_Dh_train_fields.h5',
 'results/v143/validation/camera_pilot','results/v146/camera_fits/events',
 'results/v146/source/ACTUALLY_EXECUTED_CODE/v133_recover_M.py',
 'results/v152/all_results.json','results/v153/all_results.json','results/v156','results/v163')

def require(x,msg):
    if not x:raise ValueError(msg)

def safe_path(root,rel):
    q=PurePosixPath(rel)
    require(bool(q.parts) and not q.is_absolute() and '..' not in q.parts and '\\' not in rel and not any(':' in part for part in q.parts),'UNSAFE_RELATIVE_PATH')
    root=Path(root).resolve();p=root.joinpath(*q.parts)
    require(root in p.resolve().parents,'PATH_ESCAPES_ROOT')
    current=p
    while current!=root:
        require(not current.is_symlink(),'SYMLINK_PATH')
        current=current.parent
    return p

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def blob(p):
    p=Path(p);h=hashlib.sha1(b'blob '+str(p.stat().st_size).encode()+b'\0')
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def git(repo,*a):return subprocess.run(['git','-C',str(repo),*a],check=True,capture_output=True).stdout

def entries(repo):
    rows=[]
    for line in git(repo,'ls-tree','-r','-z',PARENT,'--',*PREFIXES).split(b'\0'):
        if not line:continue
        head,name=line.split(b'\t',1);mode,kind,b=head.decode().split();rel=name.decode('utf-8')
        require(kind=='blob' and mode in ('100644','100755'),'UNSUPPORTED_GIT_OBJECT')
        p=PurePosixPath(rel);require(not p.is_absolute() and '..' not in p.parts,'UNSAFE_GIT_PATH')
        rows.append((rel,b))
    for prefix in PREFIXES:require(any(p==prefix or p.startswith(prefix+'/') for p,_ in rows),'MISSING_PREFIX:'+prefix)
    return rows

def lock_sources(repo):
    out={}
    for rel,b in entries(repo):
        p=safe_path(repo,rel);require(p.is_file() and not p.is_symlink(),'MISSING_OR_SYMLINK:'+rel)
        require(blob(p)==b,'FROZEN_BYTE_MISMATCH:'+rel)
        out[rel]=dict(git_blob=b,sha256=sha(p),bytes=p.stat().st_size)
    return out

def archive_check(path):
    path=Path(path)
    with zipfile.ZipFile(path) as z:
        names=z.namelist();require(len(names)==len(set(names)),'DUPLICATE_ZIP_MEMBERS')
        require(z.testzip() is None,'ZIP_CRC_FAILED')
        for n in names:
            p=PurePosixPath(n);require(not p.is_absolute() and '..' not in p.parts and '\\' not in n,'UNSAFE_ZIP_PATH')
        rows=list(csv.DictReader(z.read('manifest_sha256.csv').decode('utf-8-sig').splitlines()))
        require(len(rows)==len({r['path'] for r in rows}),'DUPLICATE_MANIFEST_ROWS')
        require(set(names)=={'manifest_sha256.csv'}|{r['path'] for r in rows},'ZIP_MEMBER_SET_MISMATCH')
        for r in rows:
            raw=z.read(r['path']);require(len(raw)==int(r['bytes']) and hashlib.sha256(raw).hexdigest()==r['sha256'],'MANIFEST_MISMATCH:'+r['path'])
    return dict(bytes=path.stat().st_size,sha256=sha(path),members=len(names),manifest_rows=len(rows),crc_ok=True)

def ledger_check(folder,*,plan_id,expected_total=None,require_success=True):
    folder=Path(folder);p=folder/'logs'/f'{plan_id}_budget.sqlite'
    con=sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True)
    try:
        require(con.execute('PRAGMA integrity_check').fetchone()[0]=='ok','SQLITE_INTEGRITY')
        meta=json.loads(con.execute('SELECT value FROM metadata WHERE id=1').fetchone()[0]);require(meta['plan_id']==plan_id,'LEDGER_PLAN')
        tasks=con.execute('SELECT id,signature,phase,cap,used,state,result_sha FROM tasks').fetchall();rows=[]
        for task,sig,phase,cap,used,state,digest in tasks:
            allowed=('FINISHED',) if require_success else ('FINISHED','PARTIAL_BUDGET')
            require(state in allowed and 0<=used<=cap and phase in meta['phases'],'UNFINISHED_OR_OVER_BUDGET:'+task)
            result=folder/'tasks'/task/'result.json';require(sha(result)==digest,'TASK_SEAL_CHANGED:'+task)
            require(read(result)['signature']==sig,'TASK_SIGNATURE')
            calls=con.execute('SELECT seq,theta,state,detail FROM attempts WHERE task=? ORDER BY seq',(task,)).fetchall()
            require(len(calls)==used,'TASK_COUNT_MISMATCH')
            for seq,theta,s,detail in calls:
                require(s=='RETURNED','UNKNOWN_OR_FAILED_CALL')
                if task.startswith('LOADER'):continue
                pred=read(folder/'tasks'/task/'predictions'/f'{seq:04d}.json')
                require(np.array_equal(pred['theta'],json.loads(theta)),'PREDICTION_THETA')
                c=np.ascontiguousarray(pred['C'],dtype=np.float64)
                require(c.shape==(13,13) and np.isfinite(c).all(),'PREDICTION_ARRAY')
                require(hashlib.sha256(c.tobytes()).hexdigest()==json.loads(detail)['C_sha256'],'PREDICTION_HASH')
            rows.append(dict(task=task,phase=phase,cap=cap,used=used,state=state))
        for phase,limit in meta['phases'].items():
            require(sum(r['cap'] for r in rows if r['phase']==phase)<=limit,'PHASE_RESERVATION')
        total=sum(r['used'] for r in rows)
        require(con.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]==total,'ORPHAN_OR_EXTRA_ATTEMPTS')
        require(sum(r['cap'] for r in rows)<=meta['total'],'GLOBAL_RESERVATION')
        if expected_total is not None:require(total==expected_total,'UNEXPECTED_TOTAL')
        return dict(meta=meta,tasks=rows,total_used=total,scope='READONLY_STORED_EVIDENCE_NOT_NEW_MODEL_REPLAY')
    finally:con.close()

def compare_nested(a,b,path='root'):
    if isinstance(a,dict):
        require(isinstance(b,dict) and set(a)==set(b),'KEY_MISMATCH:'+path)
        for k in a:compare_nested(a[k],b[k],path+'.'+k)
    elif isinstance(a,list):
        require(isinstance(b,list) and len(a)==len(b),'LIST_MISMATCH:'+path)
        for i,(x,y) in enumerate(zip(a,b)):compare_nested(x,y,f'{path}[{i}]')
    elif isinstance(a,(float,int)) and not isinstance(a,bool):
        require(isinstance(b,(float,int)) and np.isclose(a,b,rtol=1e-8,atol=1e-10),'NUMBER_MISMATCH:'+path)
    else:require(a==b,'VALUE_MISMATCH:'+path)
