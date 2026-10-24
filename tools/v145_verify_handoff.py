"""Exact-member, CRC, SHA, size, unsafe-path checks for the provided ZIP."""
from __future__ import annotations
import argparse,csv,hashlib,io,json,zipfile
from pathlib import Path,PurePosixPath

def digest(b):return hashlib.sha256(b).hexdigest()

def verify(root,zip_path):
    root=Path(root);bad=[]
    with zipfile.ZipFile(zip_path,'r') as z:
        names=z.namelist();unique=set(names)
        if z.testzip() is not None:bad.append('CRC_FAILED')
        if len(unique)!=len(names):bad.append('DUPLICATE_MEMBER')
        for n in names:
            q=PurePosixPath(n)
            if not n or q.is_absolute() or '..' in q.parts or '\\' in n or q.as_posix()!=n:bad.append('UNSAFE_MEMBER:'+n)
        if 'HANDOFF_SHA256.csv' not in unique:bad.append('MANIFEST_ABSENT');return dict(ok=False,errors=bad)
        m=list(csv.DictReader(io.StringIO(z.read('HANDOFF_SHA256.csv').decode('utf-8-sig'))))
        if not m or set(m[0])!={'path','bytes','sha256'}:bad.append('BAD_MANIFEST_SCHEMA')
        declared=[r['path'] for r in m]
        if len(declared)!=len(set(declared)) or set(declared)|{'HANDOFF_SHA256.csv'}!=unique:bad.append('MEMBER_SET_WRONG')
        for r in m:
            name=r['path'];src=root/name
            if name not in unique or not src.is_file():bad.append('MISSING:'+name);continue
            contents=z.read(name)
            if len(contents)!=int(r['bytes']) or digest(contents)!=r['sha256'] or src.read_bytes()!=contents:
                bad.append('BYTE_OR_HASH_MISMATCH:'+name)
    return dict(ok=not bad,errors=bad,checked=len(m),zip_sha256=digest(Path(zip_path).read_bytes()))

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--zip',required=True);p.add_argument('--out',default=None);a=p.parse_args()
    try:r=verify(a.root,a.zip)
    except Exception as e:r=dict(ok=False,errors=[repr(e)])
    if a.out:Path(a.out).write_text(json.dumps(r,indent=2)+'\n')
    print('HANDOFF_'+('MECHANICAL_PASS' if r['ok'] else 'FAIL'),r)
    return 0 if r['ok'] else 2
if __name__=='__main__':raise SystemExit(main())
