#!/usr/bin/env python3
"""External ZIP mechanical + self-consistency checks; never auto-certifies physics."""
from __future__ import annotations
import argparse,csv,hashlib,io,json,zipfile
from pathlib import Path,PurePosixPath
REQUIRED={'status.json','review.md','manifest_sha256.csv','provenance/N_source_audit.json',
 'preflight/v142_audit.json','preflight/profile_inventory.json',
 'logs/v143_budget.sqlite','validation/per_particle_reportability.json'}

def verify(p):
    p=Path(p);errors=[];scientific={}
    with zipfile.ZipFile(p) as z:
        names=z.namelist();nset=set(names)
        if z.testzip() is not None:errors.append('BAD_CRC')
        if len(names)!=len(nset):errors.append('DUPLICATE_MEMBERS')
        for k in names:
            q=PurePosixPath(k)
            if not k or q.is_absolute() or '..' in q.parts or '\\' in k or q.as_posix()!=k:errors.append('UNSAFE_MEMBER:'+k)
        for r in REQUIRED:
            if r not in nset:errors.append('MISSING_REQUIRED:'+r)
        if 'manifest_sha256.csv' in nset:
            man=list(csv.DictReader(io.StringIO(z.read('manifest_sha256.csv').decode('utf-8-sig'))))
            entries=set();fields=set(man[0]) if man else set()
            if fields!={'path','bytes','sha256'}:errors.append('INVALID_MANIFEST_SCHEMA')
            for row in man:
                k=row['path'];entries.add(k)
                if k not in nset:errors.append('MISSING_MANIFEST_ITEM:'+k);continue
                b=z.read(k)
                if len(b)!=int(row['bytes']) or hashlib.sha256(b).hexdigest()!=row['sha256']:
                    errors.append('MANIFEST_DIGEST_MISMATCH:'+k)
            if len(entries)!=len(man) or nset!=entries|{'manifest_sha256.csv'}:
                errors.append('MISSING_OR_EXTRA_MEMBERS')
        if 'status.json' in nset:
            st=json.loads(z.read('status.json'));scientific=st.get('science_gates',{})
            if st.get('EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED') is not False:
                errors.append('EXPERIMENTAL_ABSOLUTE_FLAG_INVALID')
        if 'validation/per_particle_reportability.json' in nset:
            r=json.loads(z.read('validation/per_particle_reportability.json'))
            vals=r['cases'].values() if isinstance(r.get('cases'),dict) else r.get('cases',[])
            for x in vals:
                if any(k in x for k in ('D_true','truth_D','ground_truth_D')):
                    errors.append('ESTIMATOR_AND_REPORTABILITY_TRUTH_LEAK')
                if x.get('reportable_D') is not None and x.get('all_required_quality_gates_verified') is not True:
                    errors.append('UNQUALIFIED_REPORTABLE_D')
    return {'schema':'iscat143.external_receipt.1','mechanical':{'status':'PASS' if not errors else 'FAIL','errors':errors},
        'published_science_claims':scientific,'independent_science_verdict':'NOT_CERTIFIED_BY_THIS_ARCHIVE_CHECKER',
        'real_experimental_absolute_validated':False,'zip_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}

def main():
    p=argparse.ArgumentParser();p.add_argument('--zip',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();r=verify(a.zip);Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    Path(a.out).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('V143_RETURN_MECHANICAL_'+r['mechanical']['status']+'_SCIENCE_NOT_INDEPENDENTLY_CERTIFIED')
    return 2 if r['mechanical']['status']=='FAIL' else 3
if __name__=='__main__':raise SystemExit(main())
