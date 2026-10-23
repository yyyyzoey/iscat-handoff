"""External V140 package check: mechanically check manifest + science declarations.

Even if mechanical PASS and all declarations say PASS, independent physical
science is NOT certified by this tool. Return 3 for mechanically complete
scientifically partial/unchecked results; return 2 for malformed archives.
"""
from __future__ import annotations
import argparse,csv,hashlib,io,json,zipfile
from pathlib import Path,PurePosixPath
CORE=['status.json','review.md','config/effective_config.json','provenance/cache_key_lineage.csv',
  'provenance/axis_map_source_proof.json','validation/canonical_oracle_comparison.csv',
  'validation/canonical_oracle_summary.json','validation/conditional_F2_qualification.json',
  'validation/M_conditional_sizing.json','logs/resource_budget.csv','manifest_sha256.csv']

def verify(zippath):
    errors=[];published={}
    with zipfile.ZipFile(zippath) as z:
        fail=z.testzip()
        if fail:errors.append('BAD_CRC:'+fail)
        names=z.namelist();name_set=set(names)
        if len(names)!=len(name_set):errors.append('DUPLICATE_ZIP_MEMBER')
        for s in names:
            if s.startswith('/') or '\\' in s or '..' in PurePosixPath(s).parts or not s or PurePosixPath(s).as_posix()!=s:
                errors.append('UNSAFE_PATH:'+s)
        for r in CORE:
            if r not in name_set:errors.append('MISSING_CORE:'+r)
        if 'manifest_sha256.csv' in name_set:
            try:
                man=list(csv.DictReader(io.StringIO(z.read('manifest_sha256.csv').decode('utf-8-sig'))))
                keys=[r['path'] for r in man]
                if not keys or len(keys)!=len(set(keys)) or set(name_set)!=set(keys)|{'manifest_sha256.csv'}:
                    errors.append('MANIFEST_MEMBER_MISMATCH')
                for r in man:
                    if r['path'] not in name_set:errors.append('MISSING_MANIFEST_MEMBER:'+r['path']);continue
                    b=z.read(r['path'])
                    if len(b)!=int(r['bytes']) or hashlib.sha256(b).hexdigest()!=r['sha256']:
                        errors.append('MANIFEST_SHA_BAD:'+r['path'])
            except Exception as e:errors.append('MANIFEST_CANNOT_PARSE:'+repr(e))
        if 'status.json' in name_set:
            try:
                st=json.loads(z.read('status.json'))
                published=st.get('science_gates',{})
                if st.get('EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED') is not False:
                    errors.append('ABSOLUTE_VALIDATION_FLAG_WRONG')
            except Exception as e:errors.append('INVALID_STATUS_JSON:'+repr(e))
    return dict(schema='iscat140.external_return_receipt.1',
       mechanical=dict(status='FAIL' if errors else 'PASS',errors=errors),
       published_science_gate_declarations=published,
       independent_science_verdict='NOT_CERTIFIED_BY_MANIFEST_CHECKER_REQUIRES_ORIGINAL_FIELD_REPLAY',
       independent_experimental_absolute_diameter='NOT_VALIDATED')

def main():
    p=argparse.ArgumentParser();p.add_argument('--zip',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    ret=verify(a.zip)
    o=Path(a.out);o.parent.mkdir(parents=True,exist_ok=True)
    o.write_text(json.dumps(ret,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('MECHANICAL_'+ret['mechanical']['status']+' SCIENCE_'+ret['independent_science_verdict'])
    return 2 if ret['mechanical']['status']=='FAIL' else 3
if __name__=='__main__':raise SystemExit(main())
