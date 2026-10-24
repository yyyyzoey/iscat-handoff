#!/usr/bin/env python3
"""Checks exact ZIP/member byte integrity, never grants science acceptance."""
import argparse,csv,hashlib,io,json,zipfile
from pathlib import Path,PurePosixPath


def verify_zip(path):
    errors=[]
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        if len(names)!=len(set(names)):errors.append('DUPLICATE_PATH')
        for n in names:
            q=PurePosixPath(n)
            if not n or q.is_absolute() or '..' in q.parts or '\\' in n or q.as_posix()!=n:errors.append('UNSAFE_PATH:'+n)
        if z.testzip():errors.append('BAD_CRC')
        if 'HANDOFF_SHA256.csv' not in names:return ['MANIFEST_MISSING']
        rows=list(csv.DictReader(io.StringIO(z.read('HANDOFF_SHA256.csv').decode('utf-8-sig'))))
        m={r['path']:r for r in rows}
        if len(m)!=len(rows) or set(names)!=set(m)|{'HANDOFF_SHA256.csv'}:errors.append('EXACT_MEMBERSHIP_FAIL')
        for n,r in m.items():
            if n not in names:continue
            b=z.read(n)
            if len(b)!=int(r['bytes']) or hashlib.sha256(b).hexdigest()!=r['sha256']:errors.append('DIGEST_FAIL:'+n)
    return errors


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--zip',required=True);a=p.parse_args()
    errors=verify_zip(a.zip);root=Path(a.root)
    with (root/'HANDOFF_SHA256.csv').open(encoding='utf-8-sig',newline='') as stream:
        rows=list(csv.DictReader(stream))
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    expected={r['path'] for r in rows}|{'HANDOFF_SHA256.csv'}
    if actual!=expected:errors.append('ROOT_MEMBERS_DIFFER')
    for r in rows:
        f=root/r['path']
        if not f.is_file():errors.append('ROOT_FILE_MISSING:'+r['path']);continue
        b=f.read_bytes()
        if len(b)!=int(r['bytes']) or hashlib.sha256(b).hexdigest()!=r['sha256']:errors.append('ROOT_DIGEST_FAIL:'+r['path'])
    print(json.dumps({'mechanical':'FAIL' if errors else 'PASS','errors':errors,'scientific_acceptance':'NOT_TESTED'},ensure_ascii=False))
    return 2 if errors else 0
if __name__=='__main__':raise SystemExit(main())
