"""Verify the handoff artifact only, never claim a BEM or physics science PASS."""
from __future__ import annotations
import csv,hashlib,sys,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MANIFEST='HANDOFF_SHA256.csv'


def verify(root=ROOT, zip_path=None):
    root=Path(root)
    rows=list(csv.DictReader((root/MANIFEST).open(encoding='utf-8',newline='')))
    if not rows:raise ValueError('Empty manifest')
    known=set()
    for r in rows:
        name=r['member'];expected=r['sha256'];size=int(r['bytes'])
        if name in known or name.startswith('/') or '\\' in name or '..' in Path(name).parts or name==MANIFEST:
            raise ValueError(f'Unsafe or duplicate member: {name}')
        known.add(name);p=root/name
        if not p.is_file():raise FileNotFoundError(name)
        raw=p.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=expected or len(raw)!=size:raise ValueError(f'Checksum mismatch: {name}')
    from_disk={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if from_disk-known!={MANIFEST}:raise ValueError(f'Unlisted files: {sorted(from_disk-known)}; missing listed: {sorted(known-from_disk)}')
    if zip_path is not None:
        with zipfile.ZipFile(zip_path) as z:
            if z.testzip() is not None:raise ValueError('CRC failure')
            names=z.namelist()
            if len(names)!=len(set(names)) or set(names)!=from_disk:raise ValueError('ZIP identity mismatch')
            for name in names:
                if z.read(name)!=(root/name).read_bytes():raise ValueError('ZIP source mismatch: '+name)
    return len(known)

if __name__=='__main__':
    path=sys.argv[1] if len(sys.argv)>1 else None
    print(f'HANDOFF_PACKAGE_ONLY_PASS: {verify(zip_path=path)} verified members; this does not evaluate V135 physics')
