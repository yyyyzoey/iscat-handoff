"""Independent V146 return verifier: CRC, manifest, required members, D-invariant
replay from calibration witnesses inside the ZIP, truth-leak and flag checks."""
from __future__ import annotations
import argparse, csv, hashlib, io, json, sys, zipfile
from pathlib import Path
import numpy as np
REQUIRED=['status.json','review.md','00_执行摘要.md','config/effective_config.json',
 'validation/v145_audit.json','validation/camera_array_replay.json','validation/fixed_D_summary.json',
 'validation/particle_reportability.json','validation/local_D_hxy_information.json',
 'camera_fits/summary.json','validator_only/camera_scores.json','logs/v146_budget.sqlite',
 'logs/resource_budget.csv','manifest_sha256.csv']
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--zip',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();errors=[]
    with zipfile.ZipFile(a.zip) as z:
        if z.testzip() is not None:errors.append('BAD_CRC')
        names=set(z.namelist())
        man={r['path']:r for r in csv.DictReader(io.StringIO(z.read('manifest_sha256.csv').decode('utf-8-sig')))}
        for n,r in man.items():
            if n=='manifest_sha256.csv':continue
            if n not in names:errors.append('MISSING:'+n);continue
            b=z.read(n)
            if len(b)!=int(r['bytes']) or hashlib.sha256(b).hexdigest()!=r['sha256']:errors.append('SHA/SIZE:'+n)
        extra=names-set(man)-{'manifest_sha256.csv'}
        if extra:errors.append('UNMANIFESTED:'+sorted(extra)[0])
        for r in REQUIRED:
            if not (r in names or any(n.startswith(r.rstrip('/')+'/') for n in names)):errors.append('REQUIRED_MISSING:'+r)
        # D-invariant replay from calibration_replay.json (all witnesses: theta[0]==D)
        crep=json.loads(z.read('calibration/calibration_replay.json').decode('utf-8-sig')) if 'calibration/calibration_replay.json' in names else json.loads(z.read('validation/calibration_replay.json').decode('utf-8-sig'))
        n=0;bad=0
        for case,wits in crep.get('verified_witnesses',{}).items():
            for w in wits:
                n+=1
                if abs(float(w['theta'][0])-float(w['D']))>1e-10:bad+=1
        if n==0:errors.append('NO_WITNESSES_FOR_D_INVARIANT')
        if bad:errors.append(f'D_INVARIANT_VIOLATIONS:{bad}')
        cands=list(csv.DictReader(io.StringIO(z.read('camera_fits/new_N_candidate_estimates.csv').decode('utf-8-sig')))) if 'camera_fits/new_N_candidate_estimates.csv' in names else []
        if any(k in r for r in cands for k in ('D_true','true_D')):errors.append('TRUTH_LEAK')
        st=json.loads(z.read('status.json').decode('utf-8'))
        if st.get('EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED') is not False:errors.append('FLAG_WRONG')
    if errors:
        print('V146_CHECK_FAIL');[print(' -',e) for e in errors];return 2
    print(f'V146_CHECK_MECHANICAL_PASS; D-invariant replay {n} witnesses OK; science requires external replay')
    return 3
if __name__=='__main__':raise SystemExit(main())
