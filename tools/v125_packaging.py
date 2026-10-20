"""V125 S7 packaging: figures, review/summary, observable contract, ZIP."""
import csv, datetime, hashlib, json, os
import numpy as np

REPO = r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff'
OUT = os.path.join(REPO, 'results', 'v125')
LOG = os.path.join(OUT, 'logs')
VAL = os.path.join(OUT, 'validation')
LIB = os.path.join(OUT, 'library')
FIG = os.path.join(OUT, 'figures')

def build_zip():
    import shutil, zipfile
    stage = os.path.join(OUT, '_zip_stage')
    if os.path.isdir(stage):
        shutil.rmtree(stage)
    os.makedirs(stage)
    include = {
        '00_START_HERE.md': os.path.join(OUT, 'contract', '00_START_HERE.md'),
        '01_V125_Codex_完整执行合同.md': os.path.join(OUT, 'contract', '01_V125_Codex_完整执行合同.md'),
        'status.json': os.path.join(OUT, 'status.json'),
        'review.md': os.path.join(OUT, 'review.md'),
        'config/effective_config.json': os.path.join(REPO, 'config', 'v125_effective_config.json'),
        'logs/source_identity.json': os.path.join(LOG, 'source_identity.json'),
        'logs/actual_commands_and_errors.txt': os.path.join(LOG, 'actual_commands_and_errors.txt'),
        'logs/execution_ledger.csv': os.path.join(LOG, 'v125_matlab_ledger.csv'),
        'logs/cache_key_map.csv': os.path.join(LOG, 'cache_key_map.csv'),
        'logs/cache_hits.csv': os.path.join(LOG, 'cache_import_map.csv'),
        'logs/resource_budget.csv': os.path.join(LOG, 'resource_budget.csv'),
        'logs/budget_counters.json': os.path.join(LOG, 'budget_counters.json'),
        'validation/v124_intake.csv': os.path.join(VAL, 'v124_intake.csv'),
        'validation/s1_regression.csv': os.path.join(VAL, 's1_regression.csv'),
        'validation/s1_red_green.json': os.path.join(VAL, 's1_red_green.json'),
        'validation/numerical_qualification.csv': os.path.join(VAL, 'numerical_qualification.csv'),
        'validation/plan_lock.json': os.path.join(VAL, 'plan_lock.json'),
        'validation/per_case_forward_replay.csv': os.path.join(VAL, 'per_case_forward_replay.csv'),
        'validation/holdout_gate_summary.json': os.path.join(VAL, 'holdout_gate_summary.json'),
        'validation/inversion_holdout_joint.csv': os.path.join(VAL, 'inversion_holdout_joint.csv'),
        'validation/inversion_methods_comparison.csv': os.path.join(VAL, 'inversion_methods_comparison.csv'),
        'validation/noise_per_trial.csv': os.path.join(VAL, 'noise_per_trial.csv'),
        'validation/blank_per_trial.csv': os.path.join(VAL, 'blank_per_trial.csv'),
        'validation/exposure_motion_per_trial.csv': os.path.join(VAL, 'exposure_motion_per_trial.csv'),
        'validation/rejection_ambiguity_summary.csv': os.path.join(VAL, 'rejection_ambiguity_summary.csv'),
        'validation/threshold_freeze.json': os.path.join(VAL, 'threshold_freeze.json'),
        'validation/holdout_truth_validator_only.json': os.path.join(VAL, 'holdout_truth_validator_only.json'),
        'experimental_observable_contract.json': os.path.join(OUT, 'experimental_observable_contract.json'),
        'library/v125_Dh_train_fields.h5': os.path.join(LIB, 'v125_Dh_train_fields.h5'),
        'library/v125_shift_tables.h5': os.path.join(LIB, 'v125_shift_tables.h5'),
        'library/v125_direct_holdouts.h5': os.path.join(LIB, 'v125_direct_holdouts.h5'),
        'library/train_grid_index.csv': os.path.join(LIB, 'train_grid_index.csv'),
        'library/holdout_index.csv': os.path.join(LIB, 'holdout_index.csv'),
        'figures/contrast_vs_D_at_heights.png': os.path.join(FIG, 'contrast_vs_D_at_heights.png'),
        'figures/contrast_vs_h_at_D.png': os.path.join(FIG, 'contrast_vs_h_at_D.png'),
        'figures/D_est_vs_D_true.png': os.path.join(FIG, 'D_est_vs_D_true.png'),
        'figures/ambiguity_and_rejection.png': os.path.join(FIG, 'ambiguity_and_rejection.png'),
        'figures/exposure_noise_comparison.png': os.path.join(FIG, 'exposure_noise_comparison.png'),
    }
    for arc, src in include.items():
        if src and os.path.isfile(src):
            dst = os.path.join(stage, arc)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy(src, dst)
    for sub in ('holdout_profiles', 'experiment_interface_smoketest'):
        sdir = os.path.join(VAL, sub)
        if os.path.isdir(sdir):
            shutil.copytree(sdir, os.path.join(stage, 'validation', sub))
    ssrc = os.path.join(OUT, 'source')
    if os.path.isdir(ssrc):
        shutil.copytree(ssrc, os.path.join(stage, 'source'))
    manifest = []
    for root, _, files in os.walk(stage):
        for fn in files:
            fp = os.path.join(root, fn)
            arc = os.path.relpath(fp, stage).replace(os.sep, '/')
            if arc == 'manifest_sha256.csv':
                continue
            hh = hashlib.sha256(open(fp, 'rb').read()).hexdigest()
            manifest.append((arc, hh))
    with open(os.path.join(stage, 'manifest_sha256.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['member', 'sha256'])
        for a, hh in manifest:
            w.writerow([a, hh])
    zip_path = os.path.join(OUT, 'iscat_v125_return.zip')
    if os.path.isfile(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(stage):
            for fn in files:
                fp = os.path.join(root, fn)
                z.write(fp, os.path.relpath(fp, stage))
    shutil.rmtree(stage)
    print('zip written:', zip_path, os.path.getsize(zip_path), 'bytes')

def make_observable_contract():
    contract = dict(
        schema='iscat125.observable_contract.1',
        static_c=dict(definition='C_p=(I_p-I_bg_p)/I_bg_p on 17x17 camera pixels (score on central 13x13)',
                      use='single-frame D-h-xy calibration and inversion'),
        fft_400hz=dict(definition='C_k = 2 X_k / (N I_mean), N=2001, Fs=5000 (script-recorded), k0=160 -> 399.80009995 Hz',
                       note='NOT equal to static C nor sinc-weighted static C; dynamic D-Ck calibration requires real trajectories + same FFT extraction',
                       status='INTERFACE_ONLY_THIS_ROUND'),
        separation='two independent entry points; never mix static templates with FFT amplitudes')
    json.dump(contract, open(os.path.join(OUT, 'experimental_observable_contract.json'), 'w', encoding='utf-8'),
              indent=1, ensure_ascii=False)
