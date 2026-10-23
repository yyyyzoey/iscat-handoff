"""Fail-closed V138 verifier: mechanical + scientific replay from the ZIP."""
from __future__ import annotations
import csv, hashlib, io, json, sys, zipfile
from pathlib import Path
import numpy as np
REQUIRED=['00_执行摘要.md','config/effective_config.json','provenance/inputs_and_runtime_sha.json',
 'provenance/raw_operator_audit.json','provenance/raw_operator_audit.csv','provenance/raw_solve_geometry_audit.csv',
 'validation/raw_M_direct_vs_merged_H5.csv','validation/within_render_intensity_identity.csv',
 'validation/same_solve_wide_vs_camera.csv','validation/F2_interpolation_on_verified_raw_M.csv',
 'validation/development_error_requalified.csv','validation/development_envelope_frozen.json',
 'validation/M_raw_direct_candidates_and_reasons.csv','validation/reportability_per_particle.json',
 'validation/old_camera_and_multiframe_method_audit.json','logs/historical_v137_budget_breach.json',
 'logs/budget_v138.sqlite','logs/commands_and_errors.txt','logs/resource_budget.csv',
 'source/ACTUALLY_EXECUTED_CODE','source/source_sha256.csv','status.json','review.md','manifest_sha256.csv']
def main(zp):
    problems=[]
    with zipfile.ZipFile(zp) as z:
        if z.testzip() is not None:problems.append('CRC')
        names=set(z.namelist())
        man={r['path']:r for r in csv.DictReader(io.StringIO(z.read('manifest_sha256.csv').decode('utf-8')))}
        for n,r in man.items():
            if n=='manifest_sha256.csv':continue
            if n not in names:problems.append('missing '+n);continue
            b=z.read(n)
            if hashlib.sha256(b).hexdigest()!=r['sha256'] or int(r['bytes'])!=len(b):problems.append('sha/size '+n)
        for r in REQUIRED:
            if not (r in names or any(n.startswith(r.rstrip('/')+'/') for n in names)):problems.append('required missing '+r)
        # scientific replay 1: within-render intensity identity for M01 default from ZIP npz
        if 'provenance/M01_default_raw_and_merged.npz' in names:
            with np.load(io.BytesIO(z.read('provenance/M01_default_raw_and_merged.npz'))) as nz:
                C=nz['original_render_C'];R=nz['replay_from_its_own_I_and_Ibg']
            if float(np.max(np.abs(C-R)))!=0.0:problems.append('M01 intensity identity replay FAIL')
        else:problems.append('npz arrays missing from archive')
        # scientific replay 2: raw vs merged bitwise under frozen convention
        with np.load(io.BytesIO(z.read('provenance/M02_at_offset_raw_and_merged.npz'))) as nz:
            conv=nz['original_render_C'].T[::-1,:]
            if float(np.linalg.norm(conv-nz['combined_M_H5_C']))!=0.0:problems.append('M02 raw-vs-merged bitwise FAIL')
        st=json.loads(z.read('status.json').decode('utf-8'))
        if st.get('experimental_absolute_validated') is not False:problems.append('flag wrong')
        if st['acceptance']['raw_vs_merged_identity'].startswith('PASS') is False:problems.append('acceptance text wrong')
    if problems:
        print('V138_CHECK_FAIL');[print(' -',p) for p in problems];return 2
    print('V138_CHECK_PASS: archive verified; identity and bitwise provenance replayed from ZIP')
    return 0
if __name__=='__main__':raise SystemExit(main(sys.argv[1]))
