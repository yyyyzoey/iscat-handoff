#!/usr/bin/env python3
"""External V141 result-checker: CRC/SHA, array and published-metric replay.

Requires real ZIP creation by Codex. Return 3 after successful mechanical and
array replay because it CANNOT certify original Maxwell physics or real-camera
absolute diameter from exported arrays alone. Return 2 on mechanical/science
replay inconsistency. No hardcoded user workstation paths, no stdout PASS grep.
"""
from __future__ import annotations
import argparse,csv,hashlib,io,json,sys,zipfile
from pathlib import Path,PurePosixPath
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from v141_common import pixel_intensities,error_metrics

REQUIRED=['status.json','review.md','config/effective_config.json',
          'validation/field_level_error_separation.csv',
          'validation/field_level_summary.json',
          'validation/field_cases/M02_at_offset.json',
          'validation/field_cases/M02_at_offset.npz',
          'validation/field_cases/M05_at_offset.json',
          'validation/field_cases/M05_at_offset.npz',
          'logs/resource_budget.csv','manifest_sha256.csv']

def check(zippath):
    errors=[];zippath=Path(zippath);replay={}
    with zipfile.ZipFile(zippath) as z:
        names=z.namelist();nset=set(names)
        if z.testzip() is not None:errors.append('BAD_CRC')
        if len(names)!=len(nset):errors.append('DUPLICATE_PATH')
        for n in names:
            if n.startswith('/') or '\\' in n or '..' in PurePosixPath(n).parts or not n:
                errors.append('UNSAFE_ZIP_ENTRY:'+n)
        for k in REQUIRED:
            if k not in nset:errors.append('REQUIRED_MISSING:'+k)
        if 'manifest_sha256.csv' in nset:
            try:
                rows=list(csv.DictReader(io.StringIO(z.read('manifest_sha256.csv').decode('utf-8-sig'))))
                man={r['path']:r for r in rows}
                if len(man)!=len(rows) or set(nset)!=set(man)|{'manifest_sha256.csv'}:
                    errors.append('MANIFEST_MEMBERS_MISMATCH')
                for name,r in man.items():
                    if name not in nset:continue
                    b=z.read(name)
                    if len(b)!=int(r['bytes']) or hashlib.sha256(b).hexdigest()!=r['sha256']:
                        errors.append('MANIFEST_DIGEST_MISMATCH:'+name)
            except Exception as e:errors.append('MANIFEST_CHECK_EXCEPTION:'+repr(e))
        if all(f'validation/field_cases/{case}_at_offset.npz' in nset and
               f'validation/field_cases/{case}_at_offset.json' in nset for case in ('M02','M05')):
            rows=list(csv.DictReader(io.StringIO(z.read('validation/field_level_error_separation.csv').decode())))
            lookup={(r['case'],r['variant'],r['kernel']):r for r in rows}
            for case in ('M02','M05'):
                with np.load(io.BytesIO(z.read(f'validation/field_cases/{case}_at_offset.npz'))) as n:
                    Er=n['Er_direct'];Es=n['Esca_direct']
                    true=n['C_direct']
                    C=pixel_intensities(Er,Es,5)['C']
                    if np.max(np.abs(C-true))>1e-10:errors.append('DIRECT_FIELD_REPLAY_FAILED:'+case)
                    for kernel in ('S1_BILINEAR','S2_CUBIC'):
                        m=error_metrics(n[kernel+'_C_full'],true)
                        key=(case,'at_offset',kernel)
                        if key not in lookup:errors.append('MISSING_FIELD_CSV_ROW:'+repr(key));continue
                        original=float(lookup[key]['wideEr_interpEs_C_rel_L2'])
                        if m['relative_L2'] is None or abs(m['relative_L2']-original)>1e-12:
                            errors.append('FIELD_METRICS_REPLAY_FAIL:'+repr(key))
                        replay[case+'_'+kernel]=m['relative_L2']
        if 'status.json' in nset:
            try:
                st=json.loads(z.read('status.json'))
                if st.get('EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED') is not False:
                    errors.append('ABSOLUTE_VALIDATION_FLAG_WRONG')
                for particle in st.get('particles',[]):
                    if particle.get('reportable_D') is not None and particle.get('qualified') is not True:
                        errors.append('UNQUALIFIED_DIAMETER_REPORTED')
            except Exception as e:errors.append('STATUS_JSON_ERROR:'+repr(e))
    return dict(schema='iscat141.return_receipt.1',
         mechanical_and_saved_array_replay='FAIL' if errors else 'PASS',
         errors=errors,arithmetic_replay_from_archive=replay,
         independent_maxwell_physics='NOT_CERTIFIED_BY_ARCHIVE_REPLAY',
         real_experimental_absolute_sizing='NOT_VALIDATED',
         archive_sha256=hashlib.sha256(zippath.read_bytes()).hexdigest())

def main():
    p=argparse.ArgumentParser();p.add_argument('--zip',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();dst=Path(a.out);dst.parent.mkdir(parents=True,exist_ok=True)
    try:r=check(a.zip)
    except Exception as e:r=dict(mechanical_and_saved_array_replay='FAIL',errors=[repr(e)],
       independent_maxwell_physics='NOT_CERTIFIED_BY_ARCHIVE_REPLAY')
    dst.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('RETURN_MECHANICAL_'+r['mechanical_and_saved_array_replay']+' SCIENCE_NOT_INDEPENDENTLY_CERTIFIED')
    return 2 if r['mechanical_and_saved_array_replay']=='FAIL' else 3
if __name__=='__main__':raise SystemExit(main())
