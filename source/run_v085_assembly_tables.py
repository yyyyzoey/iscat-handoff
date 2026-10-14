# -*- coding: utf-8 -*-
"""v085 assembly: budget ledger, parameter readiness, P0 status, logs."""
import os, csv, json, subprocess, datetime, hashlib, io

ROOT = r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4'
GH = os.path.join(ROOT, 'github_handoff')
TAB = os.path.join(GH, 'tables')
LOG = os.path.join(GH, 'logs')


def wcsv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader(); w.writerows(rows)


def main():
    ledger = [
        {'item': 'new_BEM_solve', 'budget': '0', 'used': '0', 'status': 'RESPECTED', 'note': ''},
        {'item': 'new_position_field_render', 'budget': '0', 'used': '0', 'status': 'RESPECTED', 'note': 'only v074 cached anchors'},
        {'item': 'A preflight (cache/identity/negative tests)', 'budget': 'zero expensive compute', 'used': '0', 'status': 'COMPLETED', 'note': '8 sources frozen, 6 caches verified, 3 sentinels, 8 negatives'},
        {'item': 'B operator regression (field-first vs QF)', 'budget': '2', 'used': '2', 'status': 'COMPLETED', 'note': 'REGRESSION_PASS both; rF 1.6e-14 / 2.8e-13'},
        {'item': 'C new double full-ROI maps', 'budget': '18', 'used': '18', 'status': 'COMPLETED', 'note': '6 inherited caches reused; 24/24 DOUBLE_MAP_VERIFIED'},
        {'item': 'D 276-pair stability + epsilon24', 'budget': 'derived only', 'used': '276 pairs', 'status': 'COMPLETED', 'note': '192 cross-D + 84 same-D; pure algebra'},
        {'item': 'new exposure quadrature', 'budget': '0', 'used': '0', 'status': 'RESPECTED', 'note': 'v082 16/16, v083 2/2 consumed'},
        {'item': 'new D/zf/a/f/material/tau/noise points', 'budget': '0', 'used': '0', 'status': 'RESPECTED', 'note': ''},
        {'item': 'original 7.29 BMP rereads', 'budget': '0', 'used': '0', 'status': 'RESPECTED', 'note': ''},
        {'item': 'P0 passive hook', 'budget': '1 (inherited)', 'used': '0', 'status': 'NOT_RUN_RESOURCE_GATED', 'note': ''},
        {'item': 'rule7 large reference', 'budget': '0', 'used': '0', 'status': 'RESPECTED', 'note': ''},
    ]
    wcsv(os.path.join(TAB, 'v085_budget_ledger.csv'), ['item', 'budget', 'used', 'status', 'note'], ledger)

    params = [
        ('laser_vacuum_wavelength_nm', 'USER_CONFIRMED', '520', 'allows real optical forward input'),
        ('camera_Fs_fps', 'EXPERIMENTAL_SCRIPT_RECORDED', '5000', 'this batch only'),
        ('analysis_frames', 'EXPERIMENTAL_SCRIPT_RECORDED', '2001 (1000:3000)', 'this batch only'),
        ('dft_bin161_actual_Hz', 'EXPERIMENTAL_SCRIPT_RECORDED', '399.800099950025', 'candidate primary observable'),
        ('ac_magnetic_field_frequency_Hz', 'HISTORICAL_RECORDED_UNVERIFIED_FINAL_SETUP', '200', 'amplitude/geometry/waveform missing; 2f causality unestablished'),
        ('camera_sensor_pixel_um', 'HISTORICAL_RECORDED_UNVERIFIED_FINAL_SETUP', '14', 'object-space scale NOT closed'),
        ('objective_nominal_magnification', 'HISTORICAL_RECORDED_UNVERIFIED_FINAL_SETUP', '50x', '280nm/px only if no extra magnification'),
        ('object_space_scale_nm_per_px', 'MISSING', 'UNDETERMINED', 'blocks experimental absolute-D inversion'),
        ('camera_exposure_time_s', 'MISSING', 'UNDETERMINED', 'all tau SYNTHETIC_TAU'),
        ('camera_trigger_mode', 'MISSING', 'UNDETERMINED', ''),
        ('imaging_NA', 'MISSING', 'UNDETERMINED', 'NA1.3 is simulation assumption'),
        ('objective_model_immersion', 'MISSING', 'UNDETERMINED', ''),
        ('illumination_incidence_polarization', 'MISSING', 'UNDETERMINED', ''),
        ('reference_beam_geometry', 'MISSING', 'UNDETERMINED', ''),
        ('magnetic_field_amplitude_direction_gradient', 'MISSING', 'UNDETERMINED', 'motion NOT preset to 5/20nm'),
        ('Bt_image_synchronization', 'MISSING', 'UNDETERMINED', 'no magnetic phase reference'),
        ('sample_batch_magnetic_material', 'MISSING_PARTIAL_HISTORICAL', 'nominal 100nm Fe3O4', 'needs TEM/SEM/DLS + measured n at 520nm'),
        ('particle_coating_medium_interface_fixation', 'MISSING', 'UNDETERMINED', ''),
        ('particle_diameter_nm', 'MISSING', 'NOT_ESTIMATED', 'frozen state unchanged'),
        ('demo_object_pixel_nm', 'SIMULATION_ASSUMPTION', '65', 'demo grid only'),
        ('demo_translation_amplitudes_nm', 'SIMULATION_ASSUMPTION', '5, 20', 'prescribed kinematics'),
        ('demo_focus_planes_nm', 'SIMULATION_ASSUMPTION', '450, 550', ''),
        ('material_constants_source', 'SIMULATION_ASSUMPTION', 'Fe3O4 Querry 1985; Au 520nm measured', ''),
    ]
    wcsv(os.path.join(TAB, 'v085_parameter_readiness.csv'),
         ['parameter', 'status_category', 'value_or_state', 'blocks_allows_note'],
         [{'parameter': p, 'status_category': c, 'value_or_state': v, 'blocks_allows_note': n}
          for (p, c, v, n) in params])

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
    wcsv(os.path.join(TAB, 'v085_p0_status.csv'), list(p0[0].keys()), p0)

    # logs
    io.open(os.path.join(LOG, 'actual_commands_and_versions.txt'), 'w', encoding='utf-8', newline='\n').write('\n'.join([
        'v085 execution record', 'time_utc: ' + datetime.datetime.utcnow().isoformat() + 'Z',
        'parent_commit: 517ac105948e20b48677b994d8de10cad2c1388b (branch v084)',
        'commands: python source/run_v085_preflight.py; python source/run_v085_operator_regression.py; '
        'python source/run_v085_complete_double_maps.py; python source/run_v085_feature_stability.py; python source/run_v085_assembly_tables.py',
        'phases: A gate released | B REGRESSION_PASS 2/2 | C 18 new + 6 inherited = 24/24 VERIFIED | D 276/276 evaluated',
    ]) + '\n')
    fl = ['v085 failures and stacktraces',
          'transient (resolved before final evidence tables):',
          '  run_v085_preflight.py: NEG-S03/NAG-S07 initially vacuous (self-defeating test params / missing finite check) -> guards fixed, 8/8 rejected',
          'persistent failures: none',
          'skipped by design: MATLAB native FFT cross-check and P0 hook (licence/process safety, resource-gated)']
    io.open(os.path.join(LOG, 'failures_and_stacktraces.log'), 'w', encoding='utf-8', newline='\n').write('\n'.join(fl) + '\n')
    rows = []
    for root, dirs, files in os.walk(os.path.join(ROOT, 'v074_return', 'numeric', 'render_cache')):
        for fn in files:
            p = os.path.join(root, fn)
            rows.append({'path': os.path.relpath(p, ROOT).replace(os.sep, '/'),
                         'sha256': hashlib.sha256(io.open(p, 'rb').read()).hexdigest(),
                         'bytes': str(os.path.getsize(p))})
    for p in (os.path.join(ROOT, 'v076_return', 'numeric', 'v076_dynamic_center_corrected.mat'),
              os.path.join(ROOT, 'v076_return', 'numeric', 'v076_center_roi_harmonic_small_examples.mat')):
        rows.append({'path': os.path.relpath(p, ROOT).replace(os.sep, '/'),
                     'sha256': hashlib.sha256(io.open(p, 'rb').read()).hexdigest(),
                     'bytes': str(os.path.getsize(p))})
    wcsv(os.path.join(LOG, 'cache_source_SHA256.csv'), ['path', 'sha256', 'bytes'], rows)
    print('[assembly] ledger=%d params=%d p0=%d cache_hashes=%d' % (len(ledger), len(params), len(p0), len(rows)))


if __name__ == '__main__':
    main()
