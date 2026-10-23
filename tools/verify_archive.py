#!/usr/bin/env python3
"""Independent ZIP member and manifest audit (mechanical integrity only).

No path-specific imports, no fake 'profile point replay', no searching for PASS
substrings. A mechanical PASS cannot mean optical/physics/sizing PASS.
"""
from __future__ import annotations
import argparse,csv,hashlib,io,json,posixpath,zipfile
from pathlib import Path


def safe_name(name):
    if (not isinstance(name,str) or not name or name.startswith(('/', '\\'))
        or '\\' in name or any(p in ('','.', '..') for p in name.split('/'))
        or name.endswith('/') or ':' in name):
        raise ValueError(f'Unsafe archive member: {name!r}')
    return name


def audit(zippath):
    zippath = Path(zippath)
    if not zippath.is_file():raise FileNotFoundError(zippath)
    with zipfile.ZipFile(zippath, 'r') as z:
        infos=z.infolist(); names=[n.filename for n in infos]
        for n in names:safe_name(n)
        if len(names) != len(set(names)):
            raise ValueError('Duplicate ZIP members; ambiguous member mapping')
        if 'manifest_sha256.csv' not in names:
            raise ValueError('Missing manifest_sha256.csv')
        failed = z.testzip()
        if failed is not None: raise ValueError(f'ZIP CRC failed for: {failed}')
        content=z.read('manifest_sha256.csv').decode('utf-8-sig')
        rows=list(csv.DictReader(io.StringIO(content)))
        if not rows:raise ValueError('Empty SHA manifest')
        if not {'path','bytes','sha256'}.issubset(rows[0]):
            raise ValueError('Manifest must have path, bytes, sha256')
        manifest={}
        for r in rows:
            n=safe_name(r['path'])
            if n in manifest or n=='manifest_sha256.csv':raise ValueError('Duplicate/self manifest member')
            manifest[n] = r
        listed=set(manifest)|{'manifest_sha256.csv'}
        if listed != set(names):
            raise ValueError(f'ZIP/list mismatch: missing={sorted(listed-set(names))}; extra={sorted(set(names)-listed)}')
        total=0
        for n,r in manifest.items():
            data=z.read(n)
            total+=len(data)
            if len(data)!=int(r['bytes']) or hashlib.sha256(data).hexdigest()!=r['sha256']:
                raise ValueError(f'ZIP entry size or SHA mismatch: {n}')
        status=None
        if 'status.json' in names:
            status=json.loads(z.read('status.json').decode('utf-8-sig'))
        return {'archive':str(zippath),'sha256':hashlib.sha256(zippath.read_bytes()).hexdigest(),
                'archive_bytes':zippath.stat().st_size,
                'n_members_including_manifest':len(names),
                'total_uncompressed_member_bytes_excluding_manifest':total,
                'status_declared':status,
                'mechanical_integrity':'PASS',
                'scientific_validation':'NOT_EVALUATED_BY_THIS_TOOL',
                'original_solve_geometry':'NOT_EVALUATED_BY_THIS_TOOL',
                'diameter_reportability':'NOT_EVALUATED_BY_THIS_TOOL'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--zip',required=True)
    p.add_argument('--out')
    a=p.parse_args()
    result=audit(a.zip)
    if a.out:
        out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('archive','n_members_including_manifest','mechanical_integrity','scientific_validation')},ensure_ascii=False))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
