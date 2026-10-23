#!/usr/bin/env python3
"""Standalone return ZIP checker: mechanical consistency != scientific success."""
from __future__ import annotations
import argparse,csv,hashlib,io,json,zipfile
from pathlib import Path,PurePosixPath
CORE={'status.json','review.md','config/effective_config.json',
 'validation/N_oracle_corrected/N_corrected_sourcewide.csv',
 'validation/profile_witness_audit.json','logs/v144_budget.sqlite',
 'provenance/input_shas.json','source/actual_code_sha256.csv','manifest_sha256.csv'}

def check(path):
    path=Path(path);errors=[];science={}
    with zipfile.ZipFile(path) as z:
        members=z.namelist();names=set(members)
        if z.testzip() is not None:errors.append('BAD_ZIP_CRC')
        if len(names)!=len(members):errors.append('DUPLICATE_MEMBERS')
        for x in members:
            if x.startswith('/') or '\\' in x or '..' in PurePosixPath(x).parts:errors.append('UNSAFE_MEMBER:'+x)
        for required in CORE:
            if required not in names:errors.append('MISSING_REQUIRED:'+required)
        if 'manifest_sha256.csv' in names:
            with io.StringIO(z.read('manifest_sha256.csv').decode('utf-8-sig')) as s:table=list(csv.DictReader(s))
            if not table or set(table[0])!={'path','bytes','sha256'}:errors.append('MANIFEST_FORMAT')
            else:
                inds={r['path'] for r in table}
                if len(inds)!=len(table) or names!=inds|{'manifest_sha256.csv'}:errors.append('MANIFEST_MEMBER_SET')
                for r in table:
                    if r['path'] not in names:continue
                    data=z.read(r['path'])
                    if len(data)!=int(r['bytes']) or hashlib.sha256(data).hexdigest()!=r['sha256']:
                        errors.append('MANIFEST_ENTRY_DIGEST:'+r['path'])
        if 'status.json' in names:
            try:
                st=json.loads(z.read('status.json'))
                science=st.get('stage_states',{})
                if st.get('EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED') is not False:errors.append('ABSOLUTE_VALIDATION_FALSE_REQUIRED')
            except Exception as e:errors.append('STATUS_UNPARSABLE:'+repr(e))
        if 'validation/particle_reportability.json' in names:
            r=json.loads(z.read('validation/particle_reportability.json'))
            items=r.get('cases',r)
            if isinstance(items,dict):items=items.values()
            for item in items:
                if any(k in item for k in ('D_true','ground_truth_D','true_D')):errors.append('TRUTH_LEAK_TO_REPORTABILITY')
                if item.get('reportable_D') is not None and item.get('all_required_quality_gates_verified') is not True:
                    errors.append('UNQUALIFIED_REPORTABLE_D')
    return dict(schema='iscat144.return_external.1',mechanical={'status':'FAIL' if errors else 'PASS','errors':errors},
         published_stage_declarations=science,independent_physics_verdict='NOT_CERTIFIED_BY_ZIP_MANIFEST_ALONE',
         absolute_magnetic_core_sizing='NOT_VALIDATED',sha256=hashlib.sha256(path.read_bytes()).hexdigest())

def main():
    p=argparse.ArgumentParser();p.add_argument('--zip',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    try:res=check(a.zip)
    except Exception as e:res=dict(mechanical=dict(status='FAIL',errors=[repr(e)]),independent_physics_verdict='NOT_CERTIFIED')
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(res,indent=2,ensure_ascii=False)+'\n')
    print('V144_MECHANICAL_'+res['mechanical']['status']+'_SCIENTIFICALLY_NOT_AUTO_CERTIFIED')
    return 2 if res['mechanical']['status']=='FAIL' else 3
if __name__=='__main__':raise SystemExit(main())
