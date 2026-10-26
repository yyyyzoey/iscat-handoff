"""One-path, two-identity reconciliation. Never weakens hashes or changes optics.
The approved runtime bytes are copied from an immutable archived Git object;
LF normalization is used ONLY as an additional comparison, never as a write.
"""
from __future__ import annotations
import ast,hashlib,json,subprocess
from pathlib import Path
BASE='71333a9f193d00012972e8fd6c188805c7a6b18e'
TARGET='tools/v133_recover_M.py'
ARCHIVE='results/v146/source/ACTUALLY_EXECUTED_CODE/v133_recover_M.py'
BASE_SHA256='142052e012a89191bd0d6fa943af06d8ca1fec5d3ae8f09298fb8e9bec997a4c'
RUNTIME_SHA256='4b89adf9354c468e706da9d63e70d545fb8b3ad18da69ec87f6fb87a7e01d4ba'
BASE_BLOB='0ee71c80664d5661ed4f7eea5d620d1c24adc461'
RUNTIME_BLOB='a00f7b3cfe0ca0c86288f9dcade93cdcd37d9c8a'

def sha(b):return hashlib.sha256(b).hexdigest()
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def git(repo,*args):return subprocess.run(['git','-C',str(repo),*args],capture_output=True,check=True).stdout

def compare_pair(base:bytes,archived:bytes,pin:str)->dict:
    if sha(base)!=BASE_SHA256 or blob(base)!=BASE_BLOB or len(base)!=9533:
        raise ValueError('UNREVIEWED_BASE_SOURCE_BYTES')
    if sha(archived)!=RUNTIME_SHA256 or blob(archived)!=RUNTIME_BLOB or len(archived)!=9662:
        raise ValueError('UNREVIEWED_ARCHIVED_SOURCE_BYTES')
    if pin!=RUNTIME_SHA256:raise ValueError('HISTORICAL_RUNTIME_PIN_CHANGED')
    if b'\r' in base or archived.count(b'\r\n')!=129 or archived.replace(b'\r\n',b'\n')!=base:
        raise ValueError('SOURCE_DIFFERENCE_IS_NOT_EXACT_REVIEWED_CRLF_ONLY')
    if ast.dump(ast.parse(base),include_attributes=False)!=ast.dump(ast.parse(archived),include_attributes=False):
        raise ValueError('SOURCE_AST_MISMATCH')
    return dict(target_path=TARGET,archive_path=ARCHIVE,original_git_blob=BASE_BLOB,
        original_sha256=BASE_SHA256,original_bytes=len(base),runtime_git_blob=RUNTIME_BLOB,
        runtime_sha256=RUNTIME_SHA256,runtime_bytes=len(archived),LF_lines=129,
        difference='129_LF_TO_CRLF_LINE_TERMINATORS_ONLY',normalized_bytes_equal=True,AST_equal=True,
        policy='ONE_EXPLICIT_PATH_USES_EXACT_HISTORICALLY_PINNED_ARCHIVE_BYTES',
        historical_configuration_changed=False,physics_code_semantics_changed=False,
        physical_model_validation='STILL_REQUIRES_COUNTED_MODEL_ID_AND_Q_REPLAY')

def bridge_from_git(repo,base=BASE):
    old=git(repo,'cat-file','blob',base+':'+TARGET)
    archived=git(repo,'cat-file','blob',base+':'+ARCHIVE)
    cfg=json.loads(git(repo,'cat-file','blob',base+':config/v146_science_config.json'))
    r=compare_pair(old,archived,cfg['frozen']['source_sha256'][TARGET])
    r['source_commit']=base
    return r

def verify_runtime_pins(repo):
    """Pure byte checks, before model import/construction/ledger reservation."""
    repo=Path(repo).resolve();cfg=json.loads((repo/'config/v146_science_config.json').read_bytes())
    rows=[]
    for rel,expected in cfg['frozen']['source_sha256'].items():
        p=repo/rel
        if not p.is_file():raise ValueError('RUNTIME_PIN_FILE_MISSING:'+rel)
        actual=sha(p.read_bytes());rows.append(dict(path=rel,expected_sha256=expected,actual_sha256=actual,matches=actual==expected))
    bad=[r['path'] for r in rows if not r['matches']]
    if bad:raise ValueError('RUNTIME_SOURCE_PIN_UNSATISFIABLE_BEFORE_MODEL:'+','.join(bad))
    if not any(r['path']==TARGET and r['expected_sha256']==RUNTIME_SHA256 for r in rows):
        raise ValueError('APPROVED_RUNTIME_PIN_MISSING')
    return dict(scope='RAW_RUNTIME_SOURCE_PINS_NO_OPTICAL_CALLS',rows=rows,all_match=True,model_calls=0)


def copy_verified_context(source,destination,expected_sha256):
    """Persist exact already-locked source bytes; never a new model computation."""
    import os,uuid
    src,dst=Path(source),Path(destination);raw=src.read_bytes()
    if sha(raw)!=expected_sha256:raise ValueError('SOURCE_CONTEXT_HASH_CHANGED:'+str(source))
    if dst.exists():
        if dst.read_bytes()!=raw:raise ValueError('EXISTING_CONTEXT_DIFFERS:'+str(destination))
    else:
        dst.parent.mkdir(parents=True,exist_ok=True);tmp=dst.with_name(dst.name+'.'+uuid.uuid4().hex+'.tmp')
        with tmp.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        os.replace(tmp,dst)
    return dict(source=str(src),file_sha256=expected_sha256,bytes=len(raw),model_calls=0)
