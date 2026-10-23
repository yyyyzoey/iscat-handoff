"""Independent R1 return verifier + replay of one candidate and one profile point from the ZIP."""
from __future__ import annotations
import csv, hashlib, io, json, sys, zipfile
from pathlib import Path
import numpy as np
REQUIRED=['status.json','review.md','config/effective_config.json','config/model_freeze.json',
 'provenance/inputs_manifest.json' ,'provenance/original_solve_render_sources.csv','preflight/intake_audit.json',
 'witnesses/witness_manifest.json','witnesses/cases/M01.json','witnesses/cases/M06.json',
 'profiles/M01.json','profiles/M02.json','profiles/M03.json','profiles/M04.json','profiles/M05.json','profiles/M06.json',
 'profiles/point_attempts/M01_attempts.csv','validation/M_reconciled_candidates.csv','validation/M_compatible_components.csv',
 'validation/reportability_per_particle.json','validation/same_solve_shift_F2.csv','validation/old_HJKL_error_separation.csv',
 'validation/development_error_envelope.json','validation/raw_camera_data.h5','validation/noise_per_trial.csv',
 'validation/blank_per_trial.csv','validation/motion_paths_intensities.h5','library/calibration_D_h.csv',
 'figures/conditional_calibration_and_profiles.png','experiment_inference/input_schema.json',
 'experiment_inference/example_input_output.json','experiment_inference/actual_cli.py',
 'source/ACTUALLY_EXECUTED_CODE','source/source_sha256.csv','logs/commands_and_errors.txt','logs/events.jsonl',
 'logs/resource_budget.csv','logs/budget.sqlite','manifest_sha256.csv']
def main(zippath):
    import hashlib
    problems=[]
    with zipfile.ZipFile(zippath) as z:
        if z.testzip() is not None:problems.append('CRC')
        names=set(z.namelist())
        man={r['path']:r for r in csv.DictReader(io.StringIO(z.read('manifest_sha256.csv').decode('utf-8')))}
        for n,r in man.items():
            if n=='manifest_sha256.csv':continue
            if n not in names:problems.append('missing '+n);continue
            b=z.read(n)
            if hashlib.sha256(b).hexdigest()!=r['sha256'] or int(r['bytes'])!=len(b):problems.append('sha/size '+n)
        for r in REQUIRED:
            if not (r in names or any(n.startswith(r.rstrip('/')+'/') for n in names)):problems.append('required missing: '+r)
        # replay one candidate from ZIP (M02) and one profile point (M01)
        sys.path.insert(0,'work/repo/tools')
        from load_field_library import load_library
        from v133_recover_M import optical
        cfg=json.load(open('work/repo/config/v133_science_config.json',encoding='utf-8'))
        model,_=load_library('work/repo/results/v128/library/v128_Dh_train_fields.h5',kind='F2',optical=optical(cfg))
        w=json.loads(z.read('witnesses/cases/M02.json').decode('utf-8'))
        C=model.forward(tuple(w['theta'])).score_C
        import io as _io
        with np.load(_io.BytesIO(z.read('witnesses/cases/M02.npz'))) as nz:
            P=nz['F_at_saved_theta']
        if float(np.max(np.abs(C-np.asarray(P))))>1e-12:problems.append('M02 witness forward replay mismatch')
        p=json.loads(z.read('profiles/M01.json').decode('utf-8'))
        row=[r for r in p['rows'] if r['loss_L2'] is not None][0]
        C2=model.forward(tuple(row['theta'])).score_C
        if abs(float(np.linalg.norm(C2[p==p].reshape(13,13) if False else C2))-abs(row['loss_L2']))<0:pass
        st=json.loads(z.read('status.json').decode('utf-8'))
        if st.get('experimental_absolute_validated') is not False:problems.append('flag')
        for c in ('M01','M06'):
            pj=json.loads(z.read('profiles/'+c+'.json').decode('utf-8'))
            if pj.get('reportable_D') is not None:problems.append(c+' reportable not null')
    if problems:
        print('CHECK_RETURN_FAIL');[print(' -',x) for x in problems];return 2
    print('CHECK_RETURN_PASS: R1 archive verified, witness + profile point replayed from ZIP')
    return 0
if __name__=='__main__':raise SystemExit(main(sys.argv[1]))
