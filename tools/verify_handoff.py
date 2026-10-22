"""Strict package-byte and ZIP checker. Does NOT evaluate BEM or sizing science."""
from __future__ import annotations
import argparse,csv,hashlib,sys,zipfile
from pathlib import Path

def check(root:Path, archive=None):
    root=root.resolve();manifest=root/'HANDOFF_SHA256.csv'
    rows=list(csv.DictReader(manifest.open(encoding='utf-8-sig',newline='')))
    if not rows:raise ValueError('Empty handoff manifest')
    expected=set()
    for r in rows:
        rel=r['path'];size=int(r['bytes']);digest=r['sha256']
        parts=Path(rel).parts
        if rel in expected or rel.startswith('/') or '\\' in rel or '..' in parts or rel=='HANDOFF_SHA256.csv':
            raise ValueError('Unsafe/duplicated member: '+rel)
        expected.add(rel)
        p=root/rel
        if not p.is_file():raise FileNotFoundError(rel)
        b=p.read_bytes()
        if len(b)!=size or hashlib.sha256(b).hexdigest()!=digest:raise ValueError('Bad SHA/size: '+rel)
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    if actual-{'HANDOFF_SHA256.csv'}!=expected:raise ValueError('Unexpected or missing package member(s): '+str((actual-{'HANDOFF_SHA256.csv'})^expected))
    if archive:
        with zipfile.ZipFile(archive) as z:
            if z.testzip() is not None:raise ValueError('ZIP CRC failed')
            names=z.namelist()
            if len(names)!=len(set(names)) or set(names)!=actual:raise ValueError('ZIP member mismatch')
            for n in names:
                if z.read(n)!=(root/n).read_bytes():raise ValueError('ZIP bytes differ from source: '+n)
    return len(expected)

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='.');p.add_argument('--zip',dest='archive');a=p.parse_args()
    n=check(Path(a.root),a.archive)
    print(f'HANDOFF_PACKAGE_ONLY_PASS: {n} members; NOT a BEM/physics/particle-sizing verdict')
if __name__=='__main__':main()
