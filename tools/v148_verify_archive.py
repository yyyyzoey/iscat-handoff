import argparse, json, hashlib, io, csv, zipfile
p=argparse.ArgumentParser();p.add_argument('--zip',required=True);p.add_argument('--out',required=True)
a=p.parse_args()
errors=[]
with zipfile.ZipFile(a.zip) as z:
    if z.testzip() is not None:errors.append('BAD_CRC')
    names=set(z.namelist())
    man={r['path']:r for r in csv.DictReader(io.StringIO(z.read('manifest_sha256.csv').decode('utf-8-sig')))}
    for n,r in man.items():
        if n=='manifest_sha256.csv':continue
        if n not in names:errors.append('MISSING:'+n);continue
        b=z.read(n)
        if len(b)!=int(r['bytes']) or hashlib.sha256(b).hexdigest()!=r['sha256']:errors.append('SHA:'+n)
    for req in ['status.json','review.md','config_frozen.json','forensics/ledger_forensics.json',
                'logs/v148_budget.sqlite','logs/resource_budget.csv','manifest_sha256.csv']:
        if req not in names:errors.append('MISSING:'+req)
    st=json.loads(z.read('status.json'))
    if st.get('EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED') is not False:errors.append('FLAG')
if errors:
    print('V148_MECHANICAL_FAIL');[print(' -',e) for e in errors];exit(2)
print('V148_MECHANICAL_PASS SCIENCE_NOT_AUTO_CERTIFIED')
