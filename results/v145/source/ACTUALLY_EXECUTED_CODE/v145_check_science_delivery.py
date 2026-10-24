"""Conservative structure/checkpoint checks for a *future* Codex V145 return.

Outputs separate mechanical and scientific statuses. Does not prove Maxwell,
closed-form global identifiability, calibration or experimental core diameter.
"""
from __future__ import annotations
import argparse,csv,hashlib,io,json,zipfile
from pathlib import Path,PurePosixPath
MANDATORY=('status.json','review.md','config/effective_config.json','validation/v144_reaudit.json',
           'validation/camera_array_replay.json','validation/fixed_D_summary.json','validation/particle_reportability.json',
           'logs/v145_budget.sqlite','logs/resource_budget.csv','manifest_sha256.csv')

def evaluate(zip_path):
    errors=[];science={}
    with zipfile.ZipFile(zip_path) as z:
        names=z.namelist();name_set=set(names)
        if z.testzip() is not None:errors.append('BAD_CRC')
        if len(name_set)!=len(names):errors.append('DUPLICATE_MEMBER')
        for name in name_set:
            if not name or '\\' in name or '..' in PurePosixPath(name).parts or PurePosixPath(name).is_absolute():errors.append('UNSAFE_MEMBER')
        for req in MANDATORY:
            if req not in name_set:errors.append('MISSING_REQUIRED:'+req)
        if 'manifest_sha256.csv' in name_set:
            rows=list(csv.DictReader(io.StringIO(z.read('manifest_sha256.csv').decode('utf-8'))))
            if len({r.get('path') for r in rows})!=len(rows) or ({r.get('path') for r in rows}|{'manifest_sha256.csv'})!=name_set:errors.append('MANIFEST_MEMBERS')
            for row in rows:
                p=row['path']
                if p not in name_set:continue
                data=z.read(p)
                if len(data)!=int(row['bytes']) or hashlib.sha256(data).hexdigest()!=row['sha256']:
                    errors.append('MANIFEST_SHA:'+p)
        if 'validation/particle_reportability.json' in name_set:
            ret=json.loads(z.read('validation/particle_reportability.json'))
            for case,r in ret.get('cases',{}).items():
                if any(key in r for key in ('true_D','D_true','ground_truth_D','label_D')):errors.append('ESTIMATOR_TRUTH_LEAK:'+case)
                if r.get('reportable_D') is not None and not r.get('all_required_science_gates_passed') is True:
                    errors.append('REPORTABLE_NOT_FAIL_CLOSED:'+case)
        if 'status.json' in name_set:
            st=json.loads(z.read('status.json'))
            science=st.get('science_gates',{})
            if st.get('EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED') is not False:errors.append('BAD_ABSOLUTE_FLAG')
    return dict(mechanical='FAIL' if errors else 'PASS',errors=errors,claimed_science_gates=science,
        external_maxwell_verdict='NOT_CERTIFIED_BY_ZIP',real_experimental_absolute_magnetic_core_diameter='NOT_VALIDATED')

def main():
    p=argparse.ArgumentParser();p.add_argument('--zip',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    try:r=evaluate(a.zip)
    except Exception as e:r=dict(mechanical='FAIL',errors=[repr(e)],external_maxwell_verdict='NOT_CERTIFIED_BY_ZIP')
    dest=Path(a.out);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n')
    print('RETURN_MECHANICAL_'+r['mechanical']+' SCIENCE_NOT_INDEPENDENTLY_CERTIFIED')
    return 2 if r['mechanical']=='FAIL' else 3
if __name__=='__main__':raise SystemExit(main())
