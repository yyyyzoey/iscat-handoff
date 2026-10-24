"""V146 packaging: manifest + archive."""
from __future__ import annotations
import argparse, csv, hashlib, json, zipfile
from pathlib import Path
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',required=True);ap.add_argument('--zip',required=True)
    a=ap.parse_args();out=Path(a.out).resolve()
    members=[]
    for p in sorted(out.rglob('*')):
        if p.is_file() and p.name!='manifest_sha256.csv' and 'iscat_v146_return.zip' not in p.name and '__pycache__' not in p.parts:
            members.append(p)
    with (out/'manifest_sha256.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);w.writeheader()
        for p in members:w.writerow(dict(path=p.relative_to(out).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
    zp=Path(a.zip)
    with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED) as z:
        for p in members:z.write(p,p.relative_to(out).as_posix())
        z.write(out/'manifest_sha256.csv','manifest_sha256.csv')
    print('V146 packed',len(members)+1,'members zip_sha256=',sha(zp))
if __name__=='__main__':main()
