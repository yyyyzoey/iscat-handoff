"""V140 handoff ZIP and hash *mechanical* verification only, never physics."""
from __future__ import annotations
import argparse,csv,hashlib,io,zipfile
from pathlib import Path,PurePosixPath

def safe_path(s):
    pp=PurePosixPath(s)
    return bool(s and not s.startswith('/') and '\\' not in s and '..' not in pp.parts and pp.as_posix()==s and not s.endswith('/'))

def verify(root,archive=None):
    root=Path(root).resolve();manifest=root/'HANDOFF_SHA256.csv'
    rows=list(csv.DictReader(io.StringIO(manifest.read_text(encoding='utf-8-sig'))))
    if not rows or set(rows[0])!={'path','bytes','sha256'}:raise ValueError('Unexpected or empty SHA manifest schema')
    expect=set()
    for r in rows:
        key=r['path']
        if not safe_path(key) or key in expect or key=='HANDOFF_SHA256.csv':raise ValueError('Unsafe or duplicate manifest member: '+key)
        expect.add(key)
        p=root/key
        if not p.is_file():raise FileNotFoundError(p)
        b=p.read_bytes()
        if len(b)!=int(r['bytes']) or hashlib.sha256(b).hexdigest()!=r['sha256']:
            raise ValueError('Bad hash or length: '+key)
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    if actual!=expect|{'HANDOFF_SHA256.csv'}:raise ValueError('Disk members do not match manifest: '+str(actual^(expect|{'HANDOFF_SHA256.csv'})))
    if archive:
        with zipfile.ZipFile(archive) as z:
            if z.testzip() is not None:raise ValueError('ZIP CRC failed')
            names=z.namelist()
            if len(names)!=len(set(names)) or any(not safe_path(n) for n in names):raise ValueError('ZIP unsafe or duplicated paths')
            if set(names)!=actual:raise ValueError('ZIP has extra/missing members')
            for n in names:
                if z.read(n)!=(root/n).read_bytes():raise ValueError('ZIP bytes differ: '+n)
    return dict(status='HANDOFF_PACKAGE_ONLY_PASS',verified_members=len(expect),
        BEM_or_physics='NOT_EVALUATED',particle_diameter_accuracy='NOT_EVALUATED')

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='.');p.add_argument('--zip');a=p.parse_args()
    print(verify(a.root,a.zip))
if __name__=='__main__':main()
