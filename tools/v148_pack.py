import argparse, csv, hashlib, json, zipfile
from pathlib import Path
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--zip',required=True)
a=p.parse_args();out=Path(a.out)
members=[]
for f in sorted(out.rglob('*')):
    if f.is_file() and f.name!='manifest_sha256.csv' and 'iscat_v148_return.zip' not in f.name and '__pycache__' not in f.parts:
        members.append(f)
with open(out/'manifest_sha256.csv','w',newline='') as mf:
    w=csv.writer(mf);w.writerow(['path','bytes','sha256'])
    for m in members:w.writerow([m.relative_to(out).as_posix(),m.stat().st_size,sha(m)])
zp=Path(a.zip)
with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED) as z:
    for m in members:z.write(m,m.relative_to(out).as_posix())
    z.write(out/'manifest_sha256.csv','manifest_sha256.csv')
print('V148 packed',len(members)+1,'members')
