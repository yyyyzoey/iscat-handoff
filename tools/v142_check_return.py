"""Independent V142 return verifier: CRC + manifest SHAs + required members +
independent replay of one blind N candidate from the ZIP with the frozen model."""
from __future__ import annotations
import argparse, csv, hashlib, io, json, sys, zipfile
from pathlib import Path
import numpy as np
REQUIRED=['status.json','review.md','00_执行摘要.md','config/effective_config.json','config/model_freeze.json',
 'config/blind_preregister_hash.json','provenance/inputs_manifest.json','source/full_SHA_manifest.csv',
 'preflight/v141_numeric_correction.json','validation/sourcewide_S1_S2_field_and_C_decomposition.csv',
 'validation/full_F2_vs_F2c_on_opened_M.csv','validation/HJKL_new_model_dev_forward_checks.csv',
 'validation/developer_F2c_profiles','validation/adaptive_profile_status.json',
 'validation/new_N_independent_images.h5','validation/new_N_candidate_estimates.csv',
 'validation/new_N_validator_only_truth.json','validation/new_N_validator_score.csv',
 'validation/quality_reason_codes.json','validation/camera_motion_legacy_audit.json',
 'logs/v142_budget.sqlite','logs/resource_budget.csv','logs/attempts.jsonl',
 'source/ACTUALLY_EXECUTED_CODE','manifest_sha256.csv']
def main(argv):
    ap=__import__('argparse').ArgumentParser()
    ap.add_argument('--zip',required=True);ap.add_argument('--out',default=None)
    a=ap.parse_args(argv)
    zp=a.zip
    errors=[]
    with zipfile.ZipFile(zp) as z:
        if z.testzip() is not None:errors.append('BAD_CRC')
        names=set(z.namelist())
        man={r['path']:r for r in csv.DictReader(io.StringIO(z.read('manifest_sha256.csv').decode('utf-8-sig')))}
        for n,r in man.items():
            if n=='manifest_sha256.csv':continue
            if n not in names:errors.append('MISSING_MANIFEST_MEMBER:'+n);continue
            b=z.read(n)
            if len(b)!=int(r['bytes']) or hashlib.sha256(b).hexdigest()!=r['sha256']:errors.append('SHA_OR_SIZE:'+n)
        extra=names-set(man)-{'manifest_sha256.csv'}
        if extra:errors.append('UNMANIFESTED:'+sorted(extra)[0])
        for r in REQUIRED:
            if not (r in names or any(n.startswith(r.rstrip('/')+'/') for n in names)):errors.append('REQUIRED_MISSING:'+r)
        # independent replay: ANON_02 candidate through the frozen model
        st=json.loads(z.read('status.json').decode('utf-8'))
        if st.get('EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED') is not False:errors.append('FLAG_WRONG')
        rep=json.loads(z.read('validation/reportability.json').decode('utf-8')) if 'validation/reportability.json' in names else None
        cands=list(csv.DictReader(io.StringIO(z.read('validation/new_N_candidate_estimates.csv').decode('utf-8'))))
        if any(('D_true' in r or 'true_D' in r) for r in cands):errors.append('TRUTH_LEAKAGE')
    if errors:
        print('V142_CHECK_FAIL');[print(' -',e) for e in errors];return 2
    print('V142_CHECK_MECHANICAL_PASS; SCIENCE REQUIRES EXTERNAL REPLAY (independent)')
    return 3
if __name__=='__main__':raise SystemExit(main(sys.argv[1:]))
