"""External V139 return ZIP checker. Mechanical and scientific status are distinct.

A mechanically consistent ZIP is not proof of physical identity or diameter
identifiability. Partial scientific progress returns exit code 3, not PASS.
"""
from __future__ import annotations
import argparse,csv,hashlib,io,json,zipfile
from pathlib import Path,PurePosixPath

REQUIRED_CORE=['status.json','review.md','config/effective_config.json',
 'provenance/inputs_manifest.json','provenance/solve_to_render_lineage.csv',
 'provenance/axis_convention_proof.json',
 'validation/oracle_shift_decomposition.csv',
 'validation/source_imaging_gate.json',
 'validation/reportability.json',
 'logs/new_budget.sqlite','logs/v137_historical_breaches.json',
 'source/source_sha256.csv','manifest_sha256.csv']

def check(zippath):
    errors=[];mechanical={};science={}
    with zipfile.ZipFile(zippath) as z:
        bad=z.testzip()
        if bad:errors.append('CRC_ERROR:'+bad)
        names=z.namelist()
        if len(names)!=len(set(names)):errors.append('DUPLICATE_ZIP_PATH')
        for n in names:
            pp=PurePosixPath(n)
            if n.startswith('/') or '\\' in n or '..' in pp.parts or pp.as_posix()!=n:
                errors.append('UNSAFE_ZIP_PATH:'+n)
        for p in REQUIRED_CORE:
            if p not in names:errors.append('REQUIRED_MISSING:'+p)
        if 'manifest_sha256.csv' in names:
            rows=list(csv.DictReader(io.StringIO(z.read('manifest_sha256.csv').decode('utf-8-sig'))))
            if not rows or set(rows[0])!={'path','bytes','sha256'}:errors.append('BAD_MANIFEST_SCHEMA')
            else:
                expected=set()
                for r in rows:
                    p=r['path']
                    if p in expected:errors.append('DUPLICATE_MANIFEST_ENTRY:'+p)
                    expected.add(p)
                    if p not in names:errors.append('MANIFEST_MEMBER_MISSING:'+p);continue
                    b=z.read(p)
                    if len(b)!=int(r['bytes']) or hashlib.sha256(b).hexdigest()!=r['sha256']:
                        errors.append('MANIFEST_SHA_OR_LENGTH_BAD:'+p)
                if set(names)!=expected|{'manifest_sha256.csv'}:errors.append('UNMANIFESTED_OR_EXTRA_ZIP_MEMBERS')
        if 'status.json' in names:
            try:
                st=json.loads(z.read('status.json'))
                if st.get('EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED') is not False:
                    errors.append('ABSOLUTE_EXPERIMENTAL_VALIDATION_FLAG_INVALID')
                science=st.get('science_gates',{})
                if not isinstance(science,dict):errors.append('SCIENCE_GATES_STRUCT_INVALID');science={}
            except Exception as e:errors.append('STATUS_JSON_INVALID:'+str(e))
        else:errors.append('NO_STATUS')
        if 'validation/reportability.json' in names:
            try:
                r=json.loads(z.read('validation/reportability.json'))
                # No truth should enter the estimator/reportability object.
                cases=r.get('cases',r) if isinstance(r,dict) else r
                if isinstance(cases,dict):cases=list(cases.values())
                for item in cases:
                    if not isinstance(item,dict):continue
                    if any(k in item for k in ('D_true','true_D','ground_truth_D')):
                        errors.append('TRUTH_LEAKAGE_IN_REPORTABILITY')
                    if item.get('reportable_D') is not None and not item.get('all_quality_evidence_confirmed',False):
                        errors.append('UNQUALIFIED_SIZE_REPORTED')
            except Exception as e:errors.append('REPORTABILITY_JSON_INVALID:'+str(e))
    mechanical=dict(status='FAIL' if errors else 'PASS',errors=errors,archive_sha256=hashlib.sha256(Path(zippath).read_bytes()).hexdigest())
    # Scientific stage statuses must be independently re-evaluated; the
    # published declarations alone are never a sufficient acceptance proof.
    status='NOT_INDEPENDENTLY_CERTIFIED'
    if not errors and science:
        status='PUBLISHED_CLAIMS_REQUIRE_EXTERNAL_REPLAY'
    return dict(schema='iscat139.return_receipt.1',mechanical=mechanical,
        published_science_gate_declarations=science,
        independent_science_verdict=status,
        experimental_absolute_validated=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--zip',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    receipt=check(a.zip)
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    Path(a.out).write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('RETURN_MECHANICAL_'+receipt['mechanical']['status']+'; SCIENCE_'+receipt['independent_science_verdict'])
    return 2 if receipt['mechanical']['status']=='FAIL' else 3
if __name__=='__main__':raise SystemExit(main())
