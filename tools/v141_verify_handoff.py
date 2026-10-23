#!/usr/bin/env python3
"""Verify packaged *handoff* CRC, safe filenames, SHA and exact member set.

Does not validate V141 experimental physics or generate scientific PASS.
"""
from __future__ import annotations
import argparse,csv,hashlib,io,json,sys,zipfile
from pathlib import Path,PurePosixPath

def verify(root,zippath):
    errors=[];root=Path(root)
    with zipfile.ZipFile(zippath,'r') as z:
        n=z.namelist()
        if z.testzip():errors.append('BAD_ZIP_CRC')
        if len(n)!=len(set(n)):errors.append('DUPLICATE_MEMBER')
        for s in n:
            if not s or s.startswith('/') or '\\' in s or '..' in PurePosixPath(s).parts or PurePosixPath(s).as_posix()!=s:
                errors.append('UNSAFE_MEMBER:'+s)
        if 'HANDOFF_SHA256.csv' not in n:errors.append('NO_MANIFEST');return errors
        man=list(csv.DictReader(io.StringIO(z.read('HANDOFF_SHA256.csv').decode('utf-8'))))
        if not man or set(man[0])!={'path','bytes','sha256'}:
            errors.append('BAD_MANIFEST_FIELDS');return errors
        exp={x['path']:x for x in man}
        if len(man)!=len(exp):errors.append('DUPLICATE_MANIFEST')
        if set(n)!=set(exp)|{'HANDOFF_SHA256.csv'}:errors.append('MANIFEST_MEMBER_SET_MISMATCH')
        for key,row in exp.items():
            if key not in n:continue
            zbytes=z.read(key)
            if hashlib.sha256(zbytes).hexdigest()!=row['sha256'] or len(zbytes)!=int(row['bytes']):
                errors.append('ARCHIVE_DIGEST_MISMATCH:'+key)
            src=root/key
            if not src.is_file() or src.read_bytes()!=zbytes:
                errors.append('ON_DISK_SOURCE_BYTES_DIFFER:'+key)
    return errors

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--zip',required=True)
    a=ap.parse_args();e=verify(a.root,a.zip)
    if e:print('V141_HANDOFF_CHECK_FAIL',json.dumps(e));return 2
    print('V141_HANDOFF_CHECK_PASS: software handoff files only; science NOT tested')
    return 0
if __name__=='__main__':raise SystemExit(main())
