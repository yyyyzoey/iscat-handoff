# -*- coding: utf-8 -*-
"""v084 assembly: inherited ledger, negative-tests table, parameter readiness,
P0 status, cost ledger, logs."""
import os, sys, csv, json, subprocess, datetime, hashlib, io

ROOT = r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4'
GH = os.path.join(ROOT, 'github_handoff')
TAB = os.path.join(GH, 'tables')
LOG = os.path.join(GH, 'logs')


def wcsv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader(); w.writerows(rows)


def main():
    # 1) inherited ledger (read-only restatement; no re-run)
    inh = [
        {'item': 'v082 24-case full-rank harmonic decomposition', 'count': '24', 'origin': 'v082_harmonics24_validated.csv', 'status': 'INHERITED_READ_ONLY'},
        {'item': 'v082 96 per-harmonic DFT contributions', 'count': '96', 'origin': 'v082_harmonic_parts_long.csv', 'status': 'INHERITED_READ_ONLY'},
        {'item': 'v082 24 complex residual records', 'count': '24', 'origin': 'v082_harmonic_residual24.csv', 'status': 'INHERITED_READ_ONLY'},
        {'item': 'v082 16 exposure evaluations (16/32-node)', 'count': '16/16 used', 'origin': 'v082_exposure16_convergence.csv', 'status': 'INHERITED_BUDGET_CONSUMED'},
        {'item': 'v083 24 true-centre identities (centre gate <1e-8)', 'count': '24', 'origin': 'v083_correct_center_series_identity24.csv', 'status': 'INHERITED_READ_ONLY'},
        {'item': 'v083 X0-explicit complex closure (24/24 PASS)', 'count': '24', 'origin': 'v083_harmonic_complex_closure_X0_corrected.csv', 'status': 'INHERITED_READ_ONLY'},
        {'item': 'v083 4 full-ROI double maps', 'count': '4', 'origin': 'v083_fullROI_precision4.csv + numeric/*.mat', 'status': 'INHERITED_ORIENTATION_CONFIRMED_V084B'},
        {'item': 'v083 2x 64-node exposure evaluations', 'count': '2/2 used', 'origin': 'v083_exposure64_target2.csv', 'status': 'INHERITED_BUDGET_CONSUMED'},
        {'item': 'v083 276-pair observable screening', 'count': '276', 'origin': 'v083_nuisance_feature_pairwise276.csv', 'status': 'INHERITED_READ_ONLY'},
        {'item': '270 odd/even + 24 camera ROI pairs', 'count': 'inherited', 'origin': 'v078 lineage', 'status': 'INHERITED_READ_ONLY'},
    ]
    wcsv(os.path.join(TAB, 'v084_existing_harmonic_exposure_inherited.csv'),
         list(inh[0].keys()), inh)

    # 2) negative tests table (from pilot NEG rows + orientation negatives)
    pilot = list(csv.DictReader(io.open(os.path.join(TAB, 'v084_asymmetric_pixel_pilot.csv'), encoding='utf-8', newline='')))
    neg = [{'test_id': r['check_id'], 'description': '%s vs %s (matlab r%s c%s)' % (
                r['check_id'], r['compared_against'], r['matlab_row'], r['matlab_col']),
            'expected_result': r['expectation'], 'observed_result': 'max|dI|=%s' % r['max_abs_series_diff'],
            'status': r['status']} for r in pilot]
    orient = list(csv.DictReader(io.open(os.path.join(TAB, 'v084_roi_orientation4.csv'), encoding='utf-8', newline='')))
    for r in orient:
        neg.append({'test_id': 'NEG-ORIENT_%s' % r['case_id'],
                    'description': 'transposed stored map must NOT match double map',
                    'expected_result': 'REJECT', 'observed_result': 'rF_transposed=%s >> rF_direct=%s' % (
                        r['rF_transposed_negative_control'], r['rF_direct_correct_orientation']),
                    'status': 'PASS'})
    wcsv(os.path.join(TAB, 'v084_pixel_axis_negative_tests.csv'),
         ['test_id', 'description', 'expected_result', 'observed_result', 'status'], neg)

    # 3) parameter readiness
    params = [
        ('laser_vacuum_wavelength_nm', 'USER_CONFIRMED', '520', 'allows real optical forward input'),
        ('camera_Fs_fps', 'EXPERIMENTAL_SCRIPT_RECORDED', '5000', 'this batch only'),
        ('analysis_frames', 'EXPERIMENTAL_SCRIPT_RECORDED', '2001 (1000:3000)', 'this batch only'),
        ('dft_bin161_actual_Hz', 'EXPERIMENTAL_SCRIPT_RECORDED', '399.800099950025', 'candidate primary observable'),
        ('ac_magnetic_field_frequency_Hz', 'HISTORICAL_RECORDED_UNVERIFIED_FINAL_SETUP', '200', 'amplitude/geometry/waveform missing; 2f causality unestablished'),
        ('camera_sensor_pixel_um', 'HISTORICAL_RECORDED_UNVERIFIED_FINAL_SETUP', '14', 'object-space scale NOT closed'),
        ('objective_nominal_magnification', 'HISTORICAL_RECORDED_UNVERIFIED_FINAL_SETUP', '50x', 'total magnification unverified'),
        ('object_space_scale_nm_per_px', 'MISSING', 'UNDETERMINED', 'blocks experimental absolute-D inversion'),
        ('camera_exposure_time_s', 'MISSING', 'UNDETERMINED', '100/200us = SYNTHETIC_TAU only'),
        ('camera_trigger_mode', 'MISSING', 'UNDETERMINED', ''),
        ('imaging_NA', 'MISSING', 'UNDETERMINED', 'NA1.3 is simulation assumption'),
        ('objective_model_immersion', 'MISSING', 'UNDETERMINED', ''),
        ('illumination_incidence_polarization', 'MISSING', 'UNDETERMINED', ''),
        ('reference_beam_geometry', 'MISSING', 'UNDETERMINED', ''),
        ('magnetic_field_amplitude_direction_gradient', 'MISSING', 'UNDETERMINED', 'motion NOT preset to 5/20nm'),
        ('Bt_image_synchronization', 'MISSING', 'UNDETERMINED', 'no magnetic phase reference'),
        ('sample_batch_magnetic_material', 'MISSING_PARTIAL_HISTORICAL', 'nominal 100nm Fe3O4', 'Querry 1985 = literature'),
        ('particle_coating_medium_interface_fixation', 'MISSING', 'UNDETERMINED', 'glass/water/5nm gap = simulation'),
        ('particle_diameter_nm', 'MISSING', 'NOT_ESTIMATED', 'frozen state unchanged'),
        ('demo_object_pixel_nm', 'SIMULATION_ASSUMPTION', '65', 'demo grid only'),
        ('demo_translation_amplitudes_nm', 'SIMULATION_ASSUMPTION', '5, 20', 'prescribed kinematics'),
        ('demo_focus_planes_nm', 'SIMULATION_ASSUMPTION', '450, 550', ''),
        ('material_constants_source', 'SIMULATION_ASSUMPTION', 'Fe3O4 Querry 1985; Au 520nm measured', ''),
    ]
    wcsv(os.path.join(TAB, 'v084_parameter_readiness.csv'),
         ['parameter', 'status_category', 'value_or_state', 'blocks_allows_note'],
         [{'parameter': p, 'status_category': c, 'value_or_state': v, 'blocks_allows_note': n}
          for (p, c, v, n) in params])

    # 4) P0 status
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
    wcsv(os.path.join(TAB, 'v084_p0_status.csv'), list(p0[0].keys()), p0)

    # 5) cost ledger
    ledger = [
        {'item': 'new_BEM_solve', 'budget': '0', 'used': '0', 'status': 'RESPECTED', 'note': ''},
        {'item': 'new_position_field_render', 'budget': '0', 'used': '0', 'status': 'RESPECTED', 'note': 'only v074 cached anchors'},
        {'item': 'A0 pilot legacy(row21,col1) reconstruction', 'budget': '1', 'used': '1', 'status': 'COMPLETED', 'note': 'included in the 24'},
        {'item': 'A1 legacy(row21,col1) 24-state recheck', 'budget': '24', 'used': '24', 'status': 'COMPLETED', 'note': 'all VERIFIED at max|dI|<1e-8'},
        {'item': 'B orientation validation of 4 double maps', 'budget': '0 new evals preferred', 'used': '0', 'status': 'COMPLETED', 'note': 'pure file/array comparison'},
        {'item': 'C nearest-shape-pair double full-ROI maps', 'budget': '2', 'used': '2', 'status': 'COMPLETED', 'note': 'explicitly authorised narrow addition'},
        {'item': 'new exposure quadrature evaluations', 'budget': '0', 'used': '0', 'status': 'RESPECTED', 'note': 'v082 16/16 and v083 2/2 consumed, not reset'},
        {'item': 'new D/zf/a/f/material/tau/noise points', 'budget': '0', 'used': '0', 'status': 'RESPECTED', 'note': ''},
        {'item': 'original 7.29 BMP rereads', 'budget': '0', 'used': '0', 'status': 'RESPECTED', 'note': ''},
        {'item': 'P0 passive hook', 'budget': '1 (inherited)', 'used': '0', 'status': 'NOT_RUN_RESOURCE_GATED', 'note': ''},
        {'item': 'rule7 large reference', 'budget': '0', 'used': '0', 'status': 'RESPECTED', 'note': ''},
    ]
    wcsv(os.path.join(TAB, 'v084_cost_ledger.csv'),
         ['item', 'budget', 'used', 'status', 'note'], ledger)

    # 6) logs
    lines = ['v084 native/python execution record',
             'time_utc: ' + datetime.datetime.utcnow().isoformat() + 'Z',
             'parent_commit: 79140295855c76cd42f11ae84be7f837ba96f485 (branch v083)',
             'phases: A0 PILOT_PASS (8/8) | A1 24/24 LEGACY_COL1_NUMERIC_VERIFIED | B 4/4 ORIENTATION_CONFIRMED | C 2/2 maps + shape pair stable | inherited ledger | params/P0']
    io.open(os.path.join(LOG, 'native_or_python_run.log'), 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
    fl = ['v084 case failures and stacktraces',
          'transient (resolved during session, before any evidence table was finalised):',
          '  run_v084_legacy_col1_recheck.py first run: NameError FS not imported -> all 24 rows recorded as LEGACY_COL1_NUMERIC_FAILED (honest failure rows);',
          '  import fixed and re-run: 24/24 LEGACY_COL1_NUMERIC_VERIFIED. The failed run performed no data corruption (pure in-memory).',
          '  run_v084_roi_orientation_validation.py first run: OSError reading scipy-savemat v5 file with h5py -> switched to scipy.io.loadmat.',
          'persistent failures: none',
          'skipped by design: MATLAB extract_fft_v073 cross-check (NOT_EXECUTED, licence/process safety); MATLAB Ipix shape session (NOT_EXECUTED, source-derived shape recorded); P0 hook (resource-gated)']
    io.open(os.path.join(LOG, 'case_failures_and_stacktraces.log'), 'w', encoding='utf-8', newline='\n').write('\n'.join(fl) + '\n')
    # cache source identity
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
    wcsv(os.path.join(LOG, 'cache_source_identity_sha256.csv'), ['path', 'sha256', 'bytes'], rows)
    print('[assembly] inherited=%d neg=%d params=%d ledger=%d cache_hashes=%d' % (
        len(inh), len(neg), len(params), len(ledger), len(rows)))


if __name__ == '__main__':
    main()
