#!/usr/bin/env python3
import argparse,csv,hashlib,zipfile
from pathlib import Path
def sha(b):return hashlib.sha256(b).hexdigest()
def verify(root,archive):
 root=Path(root);errors=[]
 with zipfile.ZipFile(archive,'r') as z:
  if z.testzip():errors.append('CRC_FAIL')
  names=z.namelist()
  if len(names)!=len(set(names)):errors.append('DUPLICATE_MEMBER')
  for x in names:
   if x.startswith('/') or '..' in Path(x).parts or '\\' in x:errors.append('UNSAFE_MEMBER')
  man={r['path']:r for r in csv.DictReader((root/'HANDOFF_SHA256.csv').open())}
  if set(names)!=set(man)|{'HANDOFF_SHA256.csv'}:errors.append('MEMBER_SET_MISMATCH')
  for n,v in man.items():
   if n not in names or not(root/n).is_file():errors.append('MISSING:'+n);continue
   b=z.read(n);bb=(root/n).read_bytes()
   if b!=bb or sha(b)!=v['sha256'] or len(b)!=int(v['bytes']):errors.append('CONTENT:'+n)
 return errors
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--zip',required=True);a=p.parse_args();e=verify(a.root,a.zip);print('HANDOFF_PASS__NOT_SCIENCE_PASS' if not e else 'HANDOFF_FAIL '+repr(e));raise SystemExit(2 if e else 0)
