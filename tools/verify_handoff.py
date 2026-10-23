#!/usr/bin/env python3
"""Verify standalone handoff bytes (NOT any simulated scientific result)."""
from __future__ import annotations
import argparse,csv,hashlib,io,json,sys,zipfile
from pathlib import Path,PurePosixPath

def sha(data):return hashlib.sha256(data).hexdigest()
def verify(root,zip_path):
    root=Path(root).resolve();zip_path=Path(zip_path).resolve();errors=[]
    mp=root/'HANDOFF_SHA256.csv'
    if not mp.is_file():return {'ok':False,'errors':['MISSING_MANIFEST']}
    with mp.open(encoding='utf-8-sig',newline='') as f:lines=list(csv.DictReader(f))
    if not lines or set(lines[0])!={'path','bytes','sha256'}:return {'ok':False,'errors':['BAD_MANIFEST_SCHEMA']}
    expected=set()
    for r in lines:
        name=r['path']
        if name in expected:errors.append('DUPLICATE_MANIFEST_PATH:'+name)
        expected.add(name)
        if name.startswith('/') or '\\' in name or '..' in PurePosixPath(name).parts:errors.append('UNSAFE_MANIFEST_PATH:'+name)
        p=root/name
        if not p.is_file():errors.append('MISSING_LOCAL_FILE:'+name);continue
        b=p.read_bytes()
        if len(b)!=int(r['bytes']) or sha(b)!=r['sha256']:errors.append('LOCAL_CONTENT_MISMATCH:'+name)
    found={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p!=mp and p.suffix!='.pyc'}
    if found!=expected:errors.append('LOCAL_FILE_SET_MISMATCH:'+str(sorted(found^expected)[:8]))
    with zipfile.ZipFile(zip_path) as z:
        if z.testzip() is not None:errors.append('BAD_ZIP_CRC')
        names=z.namelist()
        if len(names)!=len(set(names)):errors.append('DUPLICATE_ZIP_MEMBER')
        for k in names:
            if k.startswith('/') or '\\' in k or '..' in PurePosixPath(k).parts:errors.append('UNSAFE_ZIP_PATH:'+k)
        if set(names)!=expected|{'HANDOFF_SHA256.csv'}:errors.append('ZIP_MEMBERS_MISMATCH')
        for r in lines:
            k=r['path']
            if k not in names:continue
            b=z.read(k)
            if len(b)!=int(r['bytes']) or sha(b)!=r['sha256']:errors.append('ZIP_MEMBER_CONTENT_MISMATCH:'+k)
        if 'HANDOFF_SHA256.csv' in names and z.read('HANDOFF_SHA256.csv')!=mp.read_bytes():errors.append('ZIP_MANIFEST_CHANGED')
    return {'schema':'v144.handoff_integrity.1','ok':not errors,'errors':errors,'files':len(expected),'archive_sha256':sha(zip_path.read_bytes()),'disclaimer':'Software handoff check, NOT scientific or physical verification'}

def main():
    a=argparse.ArgumentParser();a.add_argument('--root',required=True);a.add_argument('--zip',required=True);a.add_argument('--out',default=None);o=a.parse_args()
    try:res=verify(o.root,o.zip)
    except Exception as e:res={'ok':False,'errors':[repr(e)]}
    if o.out:
        p=Path(o.out);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(res,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(res,ensure_ascii=False))
    return 0 if res['ok'] else 2
if __name__=='__main__':raise SystemExit(main())
