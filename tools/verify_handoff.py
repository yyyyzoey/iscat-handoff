#!/usr/bin/env python3
"""Check ONLY the handoff ZIP bytes, manifest and safe membership."""
from __future__ import annotations
import argparse,csv,hashlib,io,json,zipfile
from pathlib import Path,PurePosixPath

def verify(root,zippath):
    errors=[];root=Path(root);zippath=Path(zippath)
    with zipfile.ZipFile(zippath,'r') as z:
        names=z.namelist()
        if z.testzip():errors.append('ZIP_CRC_FAILURE')
        if len(names)!=len(set(names)):errors.append('DUPLICATE_ZIP_MEMBERS')
        for name in names:
            p=PurePosixPath(name)
            if not name or name.startswith('/') or '\\' in name or '..' in p.parts or p.as_posix()!=name:
                errors.append('UNSAFE_MEMBER:'+name)
        if 'HANDOFF_SHA256.csv' not in names:errors.append('MISSING_HASH_MANIFEST');return errors
        man=list(csv.DictReader(io.StringIO(z.read('HANDOFF_SHA256.csv').decode('utf-8'))))
        if not man or set(man[0])!={'path','bytes','sha256'}:errors.append('INVALID_HASH_MANIFEST');return errors
        expected=set()
        for r in man:
            n=r['path'];expected.add(n)
            if n not in names:errors.append('MEMBER_MISSING:'+n);continue
            b=z.read(n)
            if len(b)!=int(r['bytes']) or hashlib.sha256(b).hexdigest()!=r['sha256']:
                errors.append('ARCHIVE_MEMBER_SHA_MISMATCH:'+n)
            local=root/n
            if not local.is_file() or local.stat().st_size!=len(b) or hashlib.sha256(local.read_bytes()).hexdigest()!=r['sha256']:
                errors.append('ON_DISK_BYTES_DIFFER:'+n)
        if len(expected)!=len(man) or set(names)!=expected|{'HANDOFF_SHA256.csv'}:
            errors.append('ZIP_EXTRA_OR_UNMANIFESTED_MEMBERS')
    return errors

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--zip',required=True)
    a=p.parse_args();errs=verify(a.root,a.zip)
    print(json.dumps({'artifact':'V143_HANDOFF_ONLY','status':'PASS' if not errs else 'FAIL','errors':errs},ensure_ascii=False))
    return 0 if not errs else 2
if __name__=='__main__':raise SystemExit(main())
