# -*- coding: utf-8 -*-
"""v083 Phase F: experimental parameter readiness gate (with last-verified
status column) and P0 independent-branch safety record.

No MATLAB run is started; the inherited P0 passive-hook budget (max 1, only
when safe) is not consumed. Detecting 0 MATLAB processes does NOT prove
licence safety; the P0 branch stays NOT_RUN_RESOURCE_GATED.
"""
import os, csv, json, subprocess, datetime

ROOT = r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4'
GH = os.path.join(ROOT, 'github_handoff')
TAB = os.path.join(GH, 'tables')

PARAMS = [
    ('laser_vacuum_wavelength_nm', 'USER_CONFIRMED', '520', 'USER_CONFIRMED_2026-10-12', 'verified 2026-10-14 v083', 'true experimental input'),
    ('camera_Fs_fps', 'EXPERIMENTAL_SCRIPT_RECORDED', '5000', '7.29 extraction scripts (GBK, SHA-verified v071)', 'verified 2026-10-14 v083', 'does not guarantee other batches'),
    ('analysis_frames', 'EXPERIMENTAL_SCRIPT_RECORDED', '2001 (1000:3000)', '7.29 replay contract', 'verified 2026-10-14 v083', ''),
    ('dft_bin161_actual_Hz', 'EXPERIMENTAL_SCRIPT_RECORDED', '399.800099950025', 'k0=160 (0-based); k0*Fs/N', 'verified 2026-10-14 v083', 'candidate primary observable'),
    ('ac_magnetic_field_frequency_Hz', 'HISTORICAL_RECORDED_UNVERIFIED_FINAL_SETUP', '200', 'historical lab record', 'NOT verified against final setup', 'amplitude/direction/gradient/waveform missing; 400Hz causality unestablished'),
    ('camera_sensor_pixel_um', 'HISTORICAL_RECORDED_UNVERIFIED_FINAL_SETUP', '14', 'historical lab record', 'NOT verified against final setup', 'object-space scale NOT closed'),
    ('objective_nominal_magnification', 'HISTORICAL_RECORDED_UNVERIFIED_FINAL_SETUP', '50x', 'historical lab record', 'NOT verified against final setup', 'total magnification unverified'),
    ('object_space_scale_nm_per_px', 'MISSING', 'UNDETERMINED', '-', '-', '280nm/px only if no extra magnification; 65nm/px is demo'),
    ('camera_exposure_time_s', 'MISSING', 'UNDETERMINED', '-', '-', '100/200us are SYNTHETIC_TAU math fixtures'),
    ('camera_trigger_mode', 'MISSING', 'UNDETERMINED', '-', '-', ''),
    ('imaging_NA', 'MISSING', 'UNDETERMINED', '-', '-', 'NA1.3 is simulation assumption'),
    ('objective_model_immersion', 'MISSING', 'UNDETERMINED', '-', '-', ''),
    ('illumination_incidence_polarization', 'MISSING', 'UNDETERMINED', '-', '-', ''),
    ('reference_beam_geometry', 'MISSING', 'UNDETERMINED', '-', '-', ''),
    ('magnetic_field_amplitude_direction_gradient', 'MISSING', 'UNDETERMINED', '-', '-', 'motion NOT preset to horizontal 5/20nm'),
    ('Bt_image_synchronization', 'MISSING', 'UNDETERMINED', '-', '-', 'no magnetic phase reference exists for experiments'),
    ('sample_batch_magnetic_material', 'MISSING_PARTIAL_HISTORICAL', 'nominal 100nm Fe3O4 recorded', 'historical record', 'batch material unverified', 'Querry 1985 = literature, not batch measurement'),
    ('particle_coating_medium_interface_fixation', 'MISSING', 'UNDETERMINED', '-', '-', 'glass/water/5nm gap is simulation assumption'),
    ('particle_diameter_nm', 'MISSING', 'NOT_ESTIMATED', '-', '-', 'frozen state unchanged'),
    ('demo_object_pixel_nm', 'SIMULATION_ASSUMPTION', '65', 'forward model contract', 'n/a (assumption)', 'demo only'),
    ('demo_translation_amplitudes_nm', 'SIMULATION_ASSUMPTION', '5, 20', 'prescribed trajectory contract', 'n/a (assumption)', 'not real magnetic motion'),
    ('demo_focus_planes_nm', 'SIMULATION_ASSUMPTION', '450, 550', 'forward model grid', 'n/a (assumption)', ''),
    ('material_constants_source', 'SIMULATION_ASSUMPTION', 'Fe3O4 Querry 1985; Au 520nm measured table', 'material contract', 'n/a (assumption)', 'Au table measured'),
]
GATING = [
    'total_magnification_or_calibrated_nm_per_px', 'objective_model_NA_immersion',
    'true_exposure_and_trigger', 'magnetic_field_amplitude_gradient_geometry_waveform_sync',
    'particle_batch_material_coating', 'actual_particle_position_motion_mechanism']


def main():
    rows = [{'parameter': p, 'status_category': c, 'value_or_state': v, 'source': s,
             'last_verified_status': lv, 'note': n} for (p, c, v, s, lv, n) in PARAMS]
    p1 = os.path.join(TAB, 'v083_experimental_parameter_contract.csv')
    with open(p1, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator='\n')
        w.writeheader(); w.writerows(rows)
    gating = {'schema': 'iscat083.paramgate.1', 'export_time': '2026-10-14',
              'blocking_gaps_before_magnet_dynamics_to_absolute_D_model': GATING,
              'statement': 'These cannot be filled from demo parameters; user must provide instrument setup material. Does NOT block phases A-E pure numerical work.',
              'frozen_states': {'calibration_valid': False, 'experimental_validation': False,
                                'detection_validated': False, 'single_particle_diameter': 'NOT_ESTIMATED'}}
    with open(os.path.join(TAB, 'v083_experimental_parameter_contract.json'), 'w', encoding='utf-8') as f:
        json.dump(gating, f, indent=2)

    out = subprocess.run(['powershell', '-NoProfile', '-Command',
                          "Get-CimInstance Win32_Process -Filter \"Name like 'MATLAB%'\" | Select-Object ProcessId, Name | ConvertTo-Json -Compress"],
                         capture_output=True, text=True, timeout=60)
    procs = out.stdout.strip()
    n_procs = 0 if procs in ('', 'null') else (1 if procs.lstrip().startswith('{') else len(procs.split('},{')))
    p0 = [{'item': 'P0_passive_hook_direct_reflected_total', 'gate': 'each < 1e-10 (frozen)',
           'historical_best': '2.58848e-07', 'status': 'NOT_RUN_RESOURCE_GATED',
           'matlab_processes_detected': str(n_procs),
           'reason': 'no MATLAB native run; 0 detected processes do NOT prove licence safety; inherited budget (max 1) not consumed; independent of phases A-E',
           'recorded_utc': datetime.datetime.utcnow().isoformat() + 'Z'},
          {'item': 'rule7_large_reference', 'gate': 'increment < 0.005 (frozen)',
           'historical_best': 'NOT_RUN', 'status': 'NOT_RUN_BUDGET_0',
           'matlab_processes_detected': 'NA', 'reason': '0 authorisations', 'recorded_utc': datetime.datetime.utcnow().isoformat() + 'Z'}]
    p2 = os.path.join(TAB, 'v083_p0_status.csv')
    with open(p2, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(p0[0].keys()), lineterminator='\n')
        w.writeheader(); w.writerows(p0)
    for path, nexp, key in ((p1, len(rows), 'parameter'), (p2, 2, 'item')):
        with open(path, 'r', newline='', encoding='utf-8') as f:
            rr = list(csv.reader(f))
        assert len(rr) - 1 == nexp and all(len(x) == len(rr[0]) for x in rr), path
        assert len(set(x[0] for x in rr[1:])) == nexp, path
    print('[F] parameter contract (%d rows) + P0 status written; matlab processes: %d' % (len(rows), n_procs))


if __name__ == '__main__':
    main()
