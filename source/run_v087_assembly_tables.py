# -*- coding: utf-8 -*-
"""v087 assembly: parameter readiness, budget ledger, P0."""
import os, csv, subprocess, datetime

ROOT = r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4'
GH = os.path.join(ROOT, 'github_handoff')
TAB = os.path.join(GH, 'tables')


def write_csv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader(); w.writerows(rows)


params = [
    ('object_space_scale_nm_per_px', 'MISSING', 'UNDETERMINED', 'blocks experimental absolute-D; 280nm/px only if 14um/50x unverified assumption holds'),
    ('objective_model_NA_immersion', 'MISSING', 'UNDETERMINED', 'blocks PSF match'),
    ('illumination_incidence_polarization_reference_geometry', 'MISSING', 'UNDETERMINED', ''),
    ('true_exposure_gain_trigger_time_origin', 'MISSING', 'UNDETERMINED', 'SYNTHETIC_TAU only'),
    ('magnetic_field_amplitude_vector_gradient_waveform_sync', 'MISSING', 'UNDETERMINED', 'motion mechanism NOT selectable from one 400Hz peak'),
    ('particle_batch_core_coating_medium_fixation_interface', 'MISSING_PARTIAL_HISTORICAL', 'nominal 100nm; batch unverified', 'needs TEM/SEM/DLS + 520nm permittivity'),
    ('independent_calibration_standard_noise_background', 'MISSING', 'UNDETERMINED', 'in-sample distances are NOT independent validation'),
    ('laser_vacuum_wavelength_nm', 'USER_CONFIRMED', '520', ''),
    ('camera_Fs_fps', 'EXPERIMENTAL_SCRIPT_RECORDED', '5000', ''),
    ('analysis_frames', 'EXPERIMENTAL_SCRIPT_RECORDED', '2001 (1000:3000)', ''),
    ('dft_bin161_actual_Hz', 'EXPERIMENTAL_SCRIPT_RECORDED', '399.800099950025', ''),
    ('ac_magnetic_field_frequency_Hz', 'HISTORICAL_RECORDED_UNVERIFIED_FINAL_SETUP', '200', ''),
    ('camera_sensor_pixel_um', 'HISTORICAL_RECORDED_UNVERIFIED_FINAL_SETUP', '14', ''),
    ('objective_nominal_magnification', 'HISTORICAL_RECORDED_UNVERIFIED_FINAL_SETUP', '50x', ''),
    ('demo_object_pixel_nm', 'SIMULATION_ASSUMPTION', '65', ''),
    ('demo_translation_amplitudes_nm', 'SIMULATION_ASSUMPTION', '5, 20', ''),
    ('demo_focus_planes_nm', 'SIMULATION_ASSUMPTION', '450, 550', ''),
    ('demo_NA_gap_medium', 'SIMULATION_ASSUMPTION', '1.3 / 5nm / glass-water', ''),
    ('material_constants_source', 'SIMULATION_ASSUMPTION', 'Fe3O4 Querry 1985; Au 520nm measured', ''),
    ('particle_diameter_nm', 'MISSING', 'NOT_ESTIMATED', ''),
]
write_csv(os.path.join(TAB, 'v087_experimental_parameter_readiness.csv'),
          ['parameter', 'status_category', 'value_or_state', 'blocking_note'],
          [{'parameter': p, 'status_category': c, 'value_or_state': v, 'blocking_note': n}
           for (p, c, v, n) in params])

ledger = [
    {'item': 'new_BEM_solve', 'budget': '0', 'used': '0', 'status': 'RESPECTED', 'note': ''},
    {'item': 'new_position_field_render', 'budget': '0', 'used': '0', 'status': 'RESPECTED', 'note': ''},
    {'item': 'A rank-argmin fix + fixtures', 'budget': '0 simulation', 'used': '3 fixtures + real argmins', 'status': 'COMPLETED', 'note': 'observed_rank_same=YES (true argmins), certified=NO'},
    {'item': 'B guard mask rule + live tests', 'budget': 'small fixtures', 'used': '8 live tests', 'status': 'COMPLETED', 'note': 'incl. disk-file positive; HEAVY_CALLS honesty fix; NEG-G09 renamed'},
    {'item': 'C cached experimental FFT (roiFrames 41x41x2001)', 'budget': '1 pass', 'used': '1', 'status': 'COMPLETED', 'note': 'independent double recompute; 12 probes PASS; crop identity confirmed'},
    {'item': 'new synthetic 2001-frame computations', 'budget': '0', 'used': '0', 'status': 'RESPECTED', 'note': 'cached-video reanalysis is not new imaging'},
    {'item': 'original 7.29 BMP rereads', 'budget': '0', 'used': '0', 'status': 'RESPECTED', 'note': ''},
    {'item': 'new D/zf/a/f/tau/noise/material points', 'budget': '0', 'used': '0', 'status': 'RESPECTED', 'note': ''},
    {'item': 'P0 passive hook', 'budget': '1 (inherited)', 'used': '0', 'status': 'NOT_RUN_RESOURCE_GATED', 'note': ''},
    {'item': 'rule7 large reference', 'budget': '0', 'used': '0', 'status': 'RESPECTED', 'note': ''},
]
write_csv(os.path.join(TAB, 'v087_budget_ledger.csv'), ['item', 'budget', 'used', 'status', 'note'], ledger)

out = subprocess.run(['powershell', '-NoProfile', '-Command',
                      "Get-CimInstance Win32_Process -Filter \"Name like 'MATLAB%'\" | Select-Object ProcessId | ConvertTo-Json -Compress"],
                     capture_output=True, text=True, timeout=60)
procs = out.stdout.strip()
n_procs = 0 if procs in ('', 'null') else (1 if procs.lstrip().startswith('{') else len(procs.split('},{')))
p0 = [{'item': 'P0_passive_hook_direct_reflected_total', 'gate': 'each < 1e-10 (frozen)',
       'historical_best': '2.58848e-07', 'status': 'NOT_RUN_RESOURCE_GATED',
       'matlab_processes_detected': str(n_procs),
       'reason': 'no MATLAB native run; 0 processes is NOT licence-safety proof; inherited budget not consumed',
       'recorded_utc': datetime.datetime.utcnow().isoformat() + 'Z'},
      {'item': 'rule7_large_reference', 'gate': 'increment < 0.005 (frozen)',
       'historical_best': 'NOT_RUN', 'status': 'NOT_RUN_BUDGET_0', 'matlab_processes_detected': 'NA',
       'reason': '0 authorisations', 'recorded_utc': datetime.datetime.utcnow().isoformat() + 'Z'}]
write_csv(os.path.join(TAB, 'v087_p0_status.csv'), list(p0[0].keys()), p0)
print('[assembly] params=%d ledger=%d p0=%d' % (len(params), len(ledger), len(p0)))
