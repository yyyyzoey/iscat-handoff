# -*- coding: utf-8 -*-
"""v086 assembly: experimental parameter readiness, budget ledger, P0."""
import os, csv, subprocess, datetime

ROOT = r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4'
GH = os.path.join(ROOT, 'github_handoff')
TAB = os.path.join(GH, 'tables')

PARAMS = [
    ('object_space_scale_nm_per_px', 'MISSING', 'UNDETERMINED', 'blocks: experimental absolute-D inversion; 280nm/px ONLY IF 14um/50x with no extra magnification (unverified); demo 65nm/px is NOT calibration'),
    ('objective_model_NA_immersion', 'MISSING', 'UNDETERMINED', 'blocks: PSF match to demo system'),
    ('illumination_incidence_polarization_reference_geometry', 'MISSING', 'UNDETERMINED', 'blocks: interference reference match'),
    ('true_exposure_gain_trigger_time_origin', 'MISSING', 'UNDETERMINED', '100/200us are SYNTHETIC_TAU fixtures'),
    ('magnetic_field_amplitude_vector_gradient_waveform_sync', 'MISSING', 'UNDETERMINED', '200Hz frequency record only; motion mechanism (none/lateral/axial/rotation) NOT selectable from one 400Hz peak'),
    ('particle_batch_core_coating_medium_fixation_interface', 'MISSING_PARTIAL_HISTORICAL', 'nominal 100nm recorded; batch material unverified', 'needs TEM/SEM/DLS + measured 520nm complex permittivity'),
    ('independent_calibration_standard_noise_background', 'MISSING', 'UNDETERMINED', 'needed for any detectability/error claim; in-sample 24-state distances are NOT independent validation'),
    ('laser_vacuum_wavelength_nm', 'USER_CONFIRMED', '520', 'allows real optical forward input'),
    ('camera_Fs_fps', 'EXPERIMENTAL_SCRIPT_RECORDED', '5000', 'this batch only'),
    ('analysis_frames', 'EXPERIMENTAL_SCRIPT_RECORDED', '2001 (1000:3000)', 'this batch only'),
    ('dft_bin161_actual_Hz', 'EXPERIMENTAL_SCRIPT_RECORDED', '399.800099950025', 'k0=160 (0-based) / MATLAB bin 161'),
    ('ac_magnetic_field_frequency_Hz', 'HISTORICAL_RECORDED_UNVERIFIED_FINAL_SETUP', '200', ''),
    ('camera_sensor_pixel_um', 'HISTORICAL_RECORDED_UNVERIFIED_FINAL_SETUP', '14', ''),
    ('objective_nominal_magnification', 'HISTORICAL_RECORDED_UNVERIFIED_FINAL_SETUP', '50x', ''),
    ('demo_object_pixel_nm', 'SIMULATION_ASSUMPTION', '65', ''),
    ('demo_translation_amplitudes_nm', 'SIMULATION_ASSUMPTION', '5, 20', ''),
    ('demo_focus_planes_nm', 'SIMULATION_ASSUMPTION', '450, 550', ''),
    ('demo_NA_gap_medium', 'SIMULATION_ASSUMPTION', '1.3 / 5nm / glass-water', ''),
    ('material_constants_source', 'SIMULATION_ASSUMPTION', 'Fe3O4 Querry 1985; Au 520nm measured', ''),
    ('particle_diameter_nm', 'MISSING', 'NOT_ESTIMATED', 'frozen state unchanged'),
]
wcsv = lambda path, fields, rws: (_ for _ in ()).throw(SystemExit) if False else [
    csv.DictWriter(open(path, 'w', newline='', encoding='utf-8'), fieldnames=fields, lineterminator='\n').writeheader(),
    [dict(w_row) for w_row in [None]] and None]
# simpler explicit writer
def write_csv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader(); w.writerows(rows)

rows = [{'parameter': p, 'status_category': c, 'value_or_state': v, 'blocking_note': n}
        for (p, c, v, n) in PARAMS]
write_csv(os.path.join(TAB, 'v086_experimental_parameter_readiness.csv'),
          ['parameter', 'status_category', 'value_or_state', 'blocking_note'], rows)

ledger = [
    {'item': 'new_BEM_solve', 'budget': '0', 'used': '0', 'status': 'RESPECTED', 'note': ''},
    {'item': 'new_position_field_render', 'budget': '0', 'used': '0', 'status': 'RESPECTED', 'note': ''},
    {'item': 'A production guard fixes + 8 injections + 1 positive + detector', 'budget': '8+1', 'used': '10 tests', 'status': 'COMPLETED', 'note': 'incl. escape and hardcoded-throw detector; heavy_compute_calls=0'},
    {'item': 'B 24-map file/array identity re-verification', 'budget': '24 read-only', 'used': '24', 'status': 'COMPLETED', 'note': 'SHA vs frozen ledger, rF/epsilon recomputed from arrays'},
    {'item': 'C 276-pair recompute + rank certification intervals', 'budget': '276 pure algebra', 'used': '276', 'status': 'COMPLETED', 'note': 'rank_certified=NO (nearest two intervals overlap)'},
    {'item': 'D experimental cached observable interface', 'budget': 'read-only', 'used': '4 sources', 'status': 'COMPLETED', 'note': 'OPERATOR_MATCH / SPATIAL_CALIBRATION=MISSING / NUMERIC_ONLY'},
    {'item': 'new 2001-frame evaluations', 'budget': '0', 'used': '0', 'status': 'RESPECTED', 'note': ''},
    {'item': 'original 7.29 BMP rereads', 'budget': '0', 'used': '0', 'status': 'RESPECTED', 'note': ''},
    {'item': 'new D/zf/a/f/tau/noise points', 'budget': '0', 'used': '0', 'status': 'RESPECTED', 'note': ''},
    {'item': 'P0 passive hook', 'budget': '1 (inherited)', 'used': '0', 'status': 'NOT_RUN_RESOURCE_GATED', 'note': ''},
    {'item': 'rule7 large reference', 'budget': '0', 'used': '0', 'status': 'RESPECTED', 'note': ''},
]
write_csv(os.path.join(TAB, 'v086_budget_ledger.csv'),
          ['item', 'budget', 'used', 'status', 'note'], ledger)

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
write_csv(os.path.join(TAB, 'v086_p0_status.csv'), list(p0[0].keys()), p0)
print('[assembly] params=%d ledger=%d p0=%d' % (len(rows), len(ledger), len(p0)))
