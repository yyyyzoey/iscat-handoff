"""Independent return-package verifier: CRC, member SHAs vs manifest, required artifacts."""
from __future__ import annotations
import csv,hashlib,json,sys,zipfile
from pathlib import Path
REQUIRED=['00_执行摘要.md','config/effective_config.json','config/model_freeze.json','config/threshold_freeze.json',
 'provenance/inputs_manifest.json','provenance/M_original_solve_render_sha.csv','provenance/train_source_audit.csv',
 'validation/implementation_parity_matrix.csv','validation/actual_F2_replay.csv','validation/same_solve_shift_F2.csv',
 'validation/M_error_separation.csv','validation/M_reconciled_candidates.csv','validation/M_compatible_components.csv',
 'profiles/M01.json','profiles/M02.json','profiles/M03.json','profiles/M04.json','profiles/M05.json','profiles/M06.json',
 'validation/reportability_per_particle.json','validation/development_error_envelope.json','validation/old_HJKL_error_separation.csv',
 'library/calibration_D_h.csv','figures/M_F2_profiles.png','figures/calibration_D_h.png',
 'validation/raw_camera_data.h5','validation/noise_per_trial.csv','validation/blank_per_trial.csv','validation/threshold_validation.json',
 'validation/motion_paths_intensities.h5','validation/motion_per_track.csv','validation/shared_continuous_D.csv',
 'experiment_inference/schema.json','experiment_inference/example_input_output.json',
 'source/ACTUALLY_EXECUTED_CODE','logs/commands_and_errors.txt','logs/events.jsonl','logs/budget.sqlite','logs/resource_budget.csv',
 'status.json','review.md','manifest_sha256.csv']
def sha(b):return hashlib.sha256(b).hexdigest()
def main(zippath):
    problems=[]
    with zipfile.ZipFile(zippath) as z:
        if z.testzip() is not None:problems.append('CRC failure')
        names=set(z.namelist())
        man={r['path']:r for r in csv.DictReader(z.open('manifest_sha256.csv').read().decode('utf-8').splitlines())}
        for n,r in man.items():
            if n=='manifest_sha256.csv':continue  # self-hash excluded by construction
            if n not in names:problems.append('manifest member missing: '+n);continue
            if sha(z.read(n))!=r['sha256'] or int(r['bytes'])!=len(z.read(n)):problems.append('SHA/size mismatch: '+n)
        extra=names-set(man)-{'manifest_sha256.csv'}
        if extra:problems.append('unlisted members: '+sorted(extra)[0]+' ...')
        for r in REQUIRED:
            hit=r in names or any(n.startswith(r.rstrip('/')+'/') for n in names)
            if not hit:problems.append('required artifact missing: '+r)
        st=json.loads(z.read('status.json').decode('utf-8'))
        for c in ('M01','M02','M03','M04','M05','M06'):
            p=json.loads(z.read('profiles/'+c+'.json').decode('utf-8'))
            if p.get('reportable_D') is not None:problems.append(c+' reportable_D unexpectedly not null')
        if st.get('EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED') is not False:problems.append('absolute-diameter flag wrong')
    if problems:
        print('CHECK_RETURN_FAIL');[print(' -',p) for p in problems];return 2
    print('CHECK_RETURN_PASS: archive integrity + required artifacts + fail-closed reportability verified')
    return 0
if __name__=='__main__':raise SystemExit(main(sys.argv[1]))
