#!/usr/bin/env python3
"""Mechanical verifier for this handoff only, never independent optics certification."""
import argparse,csv,hashlib,io,json,zipfile
from pathlib import Path,PurePosixPath

def digest(b):return hashlib.sha256(b).hexdigest()

def verify(root,zpath):
    root=Path(root);zpath=Path(zpath);errors=[]
    if not zpath.is_file():return ['ZIP_NOT_FOUND']
    with zipfile.ZipFile(zpath) as z:
        names=z.namelist();u=set(names)
        if z.testzip():errors.append('CRC_FAIL')
        if len(names)!=len(u):errors.append('DUPLICATE_ZIP_MEMBERS')
        if any(x.startswith('/') or '\\' in x or '..' in PurePosixPath(x).parts or PurePosixPath(x).as_posix()!=x for x in names):errors.append('UNSAFE_ZIP_PATH')
        try:
            rows=list(csv.DictReader(io.StringIO(z.read('HANDOFF_SHA256.csv').decode('utf-8-sig'))))
            if not rows or set(rows[0])!={'path','bytes','sha256'}:errors.append('BAD_MANIFEST_SCHEMA');return errors
            declared=[r['path'] for r in rows]
            if len(set(declared))!=len(declared):errors.append('DUPLICATE_MANIFEST_RECORDS')
            if u!=set(declared)|{'HANDOFF_SHA256.csv'}:errors.append('ZIP_MEMBERS_DIFFER_FROM_MANIFEST')
            for r in rows:
                name=r['path'];p=root/name
                if name not in u or not p.is_file():errors.append('MISSING_FILE:'+name);continue
                b=z.read(name)
                if digest(b)!=r['sha256'] or len(b)!=int(r['bytes']):errors.append('ZIP_HASH_OR_SIZE:'+name)
                if digest(p.read_bytes())!=r['sha256']:errors.append('LOCAL_FILE_HASH:'+name)
            if digest(z.read('HANDOFF_SHA256.csv'))!=digest((root/'HANDOFF_SHA256.csv').read_bytes()):
                errors.append('MANIFEST_LOCAL_BYTES_DIFFER')
        except Exception as e:errors.append('MANIFEST_UNREADABLE:'+repr(e))
    return errors

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--zip',required=True)
    args=p.parse_args();issues=verify(args.root,args.zip)
    print('HANDOFF_MECHANICAL_'+('FAIL' if issues else 'PASS')+'__NO_SCIENCE_CLAIMS',json.dumps(issues))
    return 2 if issues else 0
if __name__=='__main__':raise SystemExit(main())
