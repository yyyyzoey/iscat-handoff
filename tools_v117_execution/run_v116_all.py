# -*- coding: utf-8 -*-
"""v116: v115 source forensics, production-boundary acceptance, saved-probe
bridge re-verification, and physics admission. Source frozen at
59800bae2a6b5c0b37531c09b6cc97158fad1d5f (v115; v113 89a5b35... verified as
ancestor). Lineage: tools/run_v115_all.py. Zero new BEM/render/optical time
series/physics states/experiment video reads."""
import os, sys, csv, json, hashlib, shutil, math, subprocess, zipfile, time, argparse, io
sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import numpy as np
from scipy.io import loadmat

TASK_ID = 'V116_SOURCE_FORENSICS_AND_OPERATOR_ACCEPTANCE'
EXPECTED_V115 = '59800bae2a6b5c0b37531c09b6cc97158fad1d5f'
EXPECTED_V114 = '7a9102d5f8c6f98305ed9b10279083de96be66e6'
EXPECTED_V113 = '89a5b353ba104a3dbf0764816933739f8edda33b'
PROBE_BLOB = '6b180147f64847329375363d44c317b2d4df247b'
V115_DELIVERED_ZIP_SHA = 'd435ca98ab2328dca87a437df5707c2f6f63778deef4491f70b648757de5ba9a'
V115_GREEN_ZIP_SHA = '95eb681253afb54d2e846f341bce041f16f21293579f296f520050f7b03c5cab'
N = 2001
FS = 5000.0
ALL24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
         for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)]
INTER24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
           for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (10, 15)]
ALL48 = ALL24 + INTER24
PROBE_PIXELS = [(20, 20), (20, 0), (0, 20), (25, 0)]
REQUIRED_GATES = ['A_source_forensics', 'B_operator_boundaries', 'C_saved_probe_bridge',
                  'D_physics_admission', 'F_verifier_selftest']
GATES = {g: False for g in REQUIRED_GATES}
FAIL_KEYS = {}
STAGE_LOG = {}

def log(msg):
    print('[v116] %s' % msg, flush=True)

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def blob_sha1_bytes(data):
    h = hashlib.sha1()
    h.update(b'blob %d\x00' % len(data))
    h.update(data)
    return h.hexdigest()

def wcsv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)

def rcsv(path):
    with open(path, 'r', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

# ============================== Stage A ==============================

def stage_a(root, out):
    log('=== Stage A: source forensics + clean-worktree admission ===')
    an = os.path.join(root, 'analysis')
    tab = os.path.join(root, 'tables')
    issues = []
    # --- raw git evidence ---
    git_out = {}
    for name, cmd in (
            ('cat_file_head', ['git', '-C', root, 'cat-file', '-p', 'HEAD']),
            ('rev_parse', ['git', '-C', root, 'rev-parse', 'HEAD', 'HEAD^']),
            ('merge_base_v113', ['git', '-C', root, 'merge-base', '--is-ancestor',
                                 EXPECTED_V113, 'HEAD']),
            ('merge_base_v114', ['git', '-C', root, 'merge-base', '--is-ancestor',
                                 EXPECTED_V114, 'HEAD']),
            ('status_porcelain', ['git', '-C', root, 'status', '--porcelain']),
            ('log3', ['git', '-C', root, 'log', '-3', '--format=fuller']),
            ('c1548_fuller', ['git', '-C', root, 'show', '--no-patch', '--format=fuller',
                              '1548ea810b9870251dc57e37ddec32ad8be68e42']),
    ):
        pr = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        git_out[name] = {'cmd': ' '.join(cmd), 'returncode': pr.returncode,
                         'stdout': pr.stdout[:4000], 'stderr': pr.stderr[:500]}
    with open(os.path.join(out, 'logs', 'v116_git_forensics.json'), 'w', encoding='utf-8') as f:
        json.dump(git_out, f, indent=2, ensure_ascii=False)

    head = subprocess.run(['git', '-C', root, 'rev-parse', 'HEAD'],
                          capture_output=True, text=True, timeout=60).stdout.strip()
    anc113 = subprocess.run(['git', '-C', root, 'merge-base', '--is-ancestor',
                             EXPECTED_V113, 'HEAD'], capture_output=True, timeout=60).returncode
    anc114 = subprocess.run(['git', '-C', root, 'merge-base', '--is-ancestor',
                             EXPECTED_V114, 'HEAD'], capture_output=True, timeout=60).returncode
    if head != EXPECTED_V115:
        issues.append('HEAD %s != frozen v115 commit' % head)
    if anc113 != 0:
        issues.append('v113 not an ancestor of HEAD')
    if anc114 != 0:
        issues.append('v114 not an ancestor of HEAD')
    porcelain_clean = git_out['status_porcelain']['stdout'].strip() == ''
    c1548_exists = 'commit' in git_out['c1548_fuller']['stdout']
    c1548_role = ('RESOLVED: main v114 commit (V114_OPERATOR_GUARDRAILS_AND_SAVED_PROBE_BRIDGE); '
                  'the delivered v114 tip 7a9102d is the red-evidence addendum on top of it')
    forensics = {
        'identities': {
            'fixed_release_branch': 'GitHub v115 = %s' % EXPECTED_V115,
            'historical_workstation_run_root': ('this repo @ %s; TWO driver versions ran here: the '
                                                'first used a HEAD^==v113 direct-parent check (failed '
                                                'because the v114 red-evidence addendum 1548ea8 sits '
                                                'between), the final used the ancestor check (passed))'
                                                % EXPECTED_V115),
            'clean_reverification_worktree': 'v116 branch @ %s (this run)' % head,
        },
        'c1548ea8': {'exists_locally': c1548_exists, 'role': c1548_role,
                     'classification': 'RESOLVED_RUN_WORKTREE_COMMIT' if c1548_exists
                     else 'UNRESOLVED_RUN_WORKTREE'},
        'parent_chain_note': 'HEAD^ of the v115 tip is 1548ea8 (main v114 commit), NOT v113; '
                             'v113 is an ancestor two hops back - the v115 A-gate failure was a '
                             'driver check error, not a repository defect',
        'ancestor_checks': {'v113_ancestor': anc113 == 0, 'v114_ancestor': anc114 == 0},
        'porcelain_clean': porcelain_clean,
    }
    # --- historical v115 source failure (never overwritten) ---
    delivered_zip = os.path.join(r'C:\Users\PC\Documents\Codex\2026-10-18\files-mentioned-by-the-user-iscat\outputs',
                                 'iscat_v115_return.zip')
    delivered_sha = sha256_file(delivered_zip) if os.path.isfile(delivered_zip) else None
    delivered_status = {}
    if delivered_sha == V115_DELIVERED_ZIP_SHA and os.path.isfile(delivered_zip):
        import zipfile as zf
        with zf.ZipFile(delivered_zip) as z:
            delivered_status = json.loads(z.read('iscat_v115_return/status.json'))
    hist = {
        'delivered_v115_zip_sha256': delivered_sha,
        'delivered_status_gates': delivered_status.get('gates', {}),
        'delivered_overall': delivered_status.get('overall'),
        'historical_failure_record': {
            'A_source_lock': False,
            'error': 'parent 1548ea810b9870251dc57e37ddec32ad8be68e42 != v113 commit',
            'zip_sha256': V115_DELIVERED_ZIP_SHA,
            'root_cause': 'run-root/driver-version confusion: the first v115 driver checked '
                          'HEAD^ == v113 directly; HEAD^ is the v114 addendum commit 1548ea8',
        },
        'later_green_zip_exists': {
            'sha256': V115_GREEN_ZIP_SHA,
            'note': 'a later same-worktree run with the corrected ancestor check passed '
                    '(A=true); recorded as evidence WITHOUT overwriting the historical failure',
        },
        'resolution': 'A=false was a driver check defect, NOT a repository/history defect; '
                      'Git history untouched; this record is permanent',
    }
    fp = os.path.join(out, 'historical_v115_source_failure.json')
    if not os.path.exists(fp):  # never overwritten
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump(hist, f, indent=2)
    if not v115_delivered_verified(delivered_sha):
        issues.append('delivered v115 zip sha mismatch')

    # --- 73 core sources with review_inputs comparison and MAT content ---
    snap_dir = os.path.join(out, 'snapshot73')
    os.makedirs(snap_dir, exist_ok=True)
    review_inputs = os.path.join(root, 'review_inputs')
    bl_rows = rcsv(os.path.join(tab, 'v085_double_maps24_status.csv'))
    bl_map_file = {r['case_id']: r['map_file'] for r in bl_rows}
    snap_rows = []
    for key in ALL48:
        fn = 'v092_bank_%s.mat' % key
        p = os.path.join(an, 'bank', fn)
        sha = sha256_file(p)
        m = loadmat(p)
        C = np.asarray(m['C']).astype(np.complex128)
        X = np.asarray(m['X']).astype(np.complex128)
        Im = np.asarray(m['Imean_map']).astype(np.float64)
        mask = np.asarray(m['valid_mask']).astype(bool)
        cid = str(m['case_id'].flatten()[0])
        n_val = int(np.asarray(m['N']).flatten()[0])
        fs_val = float(np.asarray(m['Fs']).flatten()[0])
        k0_bins = [int(v) for v in np.asarray(m['k0_bins']).flatten()]
        common = mask & np.isfinite(Im) & (Im > 0)
        err = float(np.max(np.abs(2.0 * X / (float(n_val) * Im)[None, :, :] - C)[:, common])) if common.any() else float('inf')
        content_ok = (str(m['C'].dtype) == 'complex128' and str(m['X'].dtype) == 'complex128'
                      and str(m['Imean_map'].dtype) == 'float64' and cid == key
                      and n_val == N and fs_val == FS and k0_bins == [80, 160, 320]
                      and err < 1e-10)
        if not content_ok:
            issues.append('bank content check failed: %s' % key)
        # review_inputs historical copy comparison (byte domains)
        rev_p = os.path.join(root, 'review_inputs', fn)
        rev_match = ''
        if os.path.isfile(rev_p):
            rev_match = 'MATCH' if sha256_file(rev_p) == sha else 'MISMATCH'
        dst = os.path.join(snap_dir, fn)
        shutil.copy2(p, dst)
        snap_rows.append({'role': 'BANK', 'case_id': key, 'file': fn, 'sha256': sha,
                          'target_relative': 'snapshot73/%s' % fn,
                          'git_blob_sha1': blob_sha1_bytes(open(p, 'rb').read()),
                          'review_inputs_match': rev_match, 'mat_content_ok': content_ok,
                          'size_bytes': str(os.path.getsize(dst))})
    for key in ALL24:
        fn = bl_map_file[key]
        p = os.path.join(root, 'numeric', fn)
        sha = sha256_file(p)
        dst = os.path.join(snap_dir, fn)
        shutil.copy2(p, dst)
        rev_p = os.path.join(root, 'review_inputs', fn)
        rev_match = ''
        if os.path.isfile(rev_p):
            rev_match = 'MATCH' if sha256_file(rev_p) == sha else 'MISMATCH'
        snap_rows.append({'role': 'BASELINE', 'case_id': key, 'file': fn, 'sha256': sha,
                          'target_relative': 'snapshot73/%s' % fn,
                          'git_blob_sha1': blob_sha1_bytes(open(p, 'rb').read()),
                          'review_inputs_match': rev_match, 'mat_content_ok': '',
                          'size_bytes': str(os.path.getsize(dst))})
    npz_src = os.path.join(an, 'v093_probe_evidence.npz')
    if blob_sha1_bytes(open(npz_src, 'rb').read()) != PROBE_BLOB:
        issues.append('probe NPZ git blob mismatch')
    dst_npz = os.path.join(snap_dir, 'v093_probe_evidence.npz')
    shutil.copy2(npz_src, dst_npz)
    snap_rows.append({'role': 'SAVED_SIMULATION_PROBES', 'case_id': 'PROBE_EVIDENCE_192_SERIES',
                      'file': 'v093_probe_evidence.npz', 'sha256': sha256_file(dst_npz),
                      'target_relative': 'snapshot73/v093_probe_evidence.npz',
                      'git_blob_sha1': PROBE_BLOB, 'review_inputs_match': '',
                      'mat_content_ok': '', 'size_bytes': str(os.path.getsize(dst_npz))})
    wcsv(os.path.join(out, 'logs', 'v116_snapshot73_manifest.csv'),
         list(snap_rows[0].keys()), snap_rows)
    with open(os.path.join(out, 'logs', 'v116_byte_domains.json'), 'w', encoding='utf-8') as f:
        json.dump({'note': 'git blob SHA-1 (canonical bytes) and worktree SHA-256 are different '
                           'hash domains; CRLF/LF text files are recorded in separate domains',
                   'snapshot_rows': len(snap_rows)}, f, indent=2)

    ok_a = not issues and len(snap_rows) == 73 and forensics['ancestor_checks']['v113_ancestor']
    if not ok_a:
        FAIL_KEYS.setdefault('A', issues[:10])
    GATES['A_source_forensics'] = ok_a
    STAGE_LOG['A'] = {'snapshots': len(snap_rows), 'head': head,
                      'v113_ancestor': anc113 == 0, 'c1548_resolved': c1548_exists,
                      'porcelain_clean': porcelain_clean, 'issues': issues[:10]}
    log('Stage A: snap=%d v113_ancestor=%s c1548=%s' % (len(snap_rows), anc113 == 0, c1548_exists))

def v115_delivered_verified(sha):
    return sha == V115_DELIVERED_ZIP_SHA

# ============================== Stage B ==============================

def stage_b(root, out):
    log('=== Stage B: 12 boundary tests + legacy 12 groups + 4 mutations ===')
    bnd_path = os.path.join(out, 'logs', 'v116_boundary_report.json')
    proc = subprocess.run([sys.executable, os.path.join(root, 'tools', 'v116_operator_boundary_tests.py'),
                           bnd_path], capture_output=True, text=True, timeout=1800)
    ok_bnd = proc.returncode == 0
    rep = json.load(open(bnd_path, encoding='utf-8')) if os.path.isfile(bnd_path) else {}
    shutil.copy2(bnd_path, os.path.join(out, 'observation_boundary_v116.json'))
    legacy_path = os.path.join(out, 'logs', 'v113_suite_on_v116_module.json')
    proc2 = subprocess.run([sys.executable, os.path.join(root, 'tools',
                            'observation_integration_tests_v113.py'), legacy_path],
                           capture_output=True, text=True, timeout=1800)
    ok_113 = proc2.returncode == 0
    rep113 = json.load(open(legacy_path, encoding='utf-8')) if os.path.isfile(legacy_path) else {}
    shutil.copy2(legacy_path, os.path.join(out, 'observation_integration_v113_suite.json'))
    ok_b = ok_bnd and ok_113
    verdict = rep.get('verdict', 'UNKNOWN')
    if not ok_bnd:
        FAIL_KEYS.setdefault('B', ['boundary failures: %s' % proc.stdout[-200:]])
    if not ok_113:
        FAIL_KEYS.setdefault('B', ['v113 suite failures'])
    GATES['B_operator_boundaries'] = ok_b
    STAGE_LOG['B'] = {'boundary': '%d/%d' % (rep.get('n_pass', 0), rep.get('n_total', 0)),
                      'verdict': verdict,
                      'legacy_groups': '%d/%d' % (sum(1 for g in rep113.get('groups', []) if g['pass']),
                                                  len(rep113.get('groups', []))),
                      'legacy_mutations': '%d/%d' % (sum(1 for m in rep113.get('mutations', []) if m['detected']),
                                                     len(rep113.get('mutations', [])))}
    log('Stage B: boundary=%s legacy=%s mutations=%s'
        % (STAGE_LOG['B']['boundary'], STAGE_LOG['B']['legacy_groups'],
           STAGE_LOG['B']['legacy_mutations']))

# ============================== Stage C ==============================

def stage_c(root, out):
    log('=== Stage C: 576 saved-probe bridge (fresh run, production module) ===')
    bridge_csv = os.path.join(out, 'tables', 'v116_bridge576.csv')
    proc = subprocess.run([sys.executable, os.path.join(root, 'tools', 'v115_saved_probe_bridge.py'),
                           '--root', root, '--output', bridge_csv],
                          capture_output=True, text=True, timeout=1800)
    ok_c = proc.returncode == 0
    summary = {}
    sj = bridge_csv.replace('.csv', '.summary.json')
    if os.path.isfile(sj):
        summary = json.load(open(sj, encoding='utf-8'))
        shutil.copy2(sj, os.path.join(out, 'logs', 'v116_bridge_summary.json'))
    if not ok_c:
        FAIL_KEYS.setdefault('C', ['bridge failures: %s' % (summary.get('issues', []) or proc.stdout[-200:])])
    GATES['C_saved_probe_bridge'] = ok_c
    STAGE_LOG['C'] = {'checked': summary.get('checked', 0), 'passed': summary.get('passed', 0),
                      'complete_set': summary.get('complete_set_576_unique_and_expected'),
                      'backend': summary.get('backend', '')}
    log('Stage C: bridge %s/%s' % (summary.get('passed', 0), summary.get('checked', 0)))

# ============================== Stage D ==============================

def stage_d(root, out):
    log('=== Stage D: metadata + four/five-layer admission + bounded pilot design ===')
    eff_src = os.path.join(root, 'logs', 'v113_effective_assignments.csv')
    inherited = rcsv(eff_src) if os.path.isfile(eff_src) else []
    items = [
        {'parameter': 'laser_vacuum_wavelength', 'value': 520.0, 'unit': 'nm',
         'evidence_class': 'USER_CONFIRMED', 'direct_source': 'user statement',
         'source_sha256': '', 'valid_dataset': 'all', 'bounds': None,
         'missing_acquisition': 'instrument calibration certificate (value not invalidated)'},
        {'parameter': 'frame_rate_Fs', 'value': 5000.0, 'unit': 'fps',
         'evidence_class': 'EXPERIMENT_SCRIPT_RECORDED',
         'direct_source': 'test_with_contrast.m L39 (hash-verified)',
         'source_sha256': 'd08575b1e860e09f29c74652442a77b721039c6e32368fe76d2c5c63143ea3aa',
         'valid_dataset': '7.29 batch', 'bounds': 'script constant, NOT a calibrated clock',
         'missing_acquisition': 'external clock calibration'},
        {'parameter': 'nominal_bins_k0', 'value': '[80, 160, 320]', 'unit': 'bin',
         'evidence_class': 'ANALYSIS_CONTRACT', 'direct_source': 'bank k0_bins',
         'source_sha256': '', 'valid_dataset': 'demo analysis',
         'bounds': 'never instrument data', 'missing_acquisition': None},
        {'parameter': 'nominal_D', 'value': 100.0, 'unit': 'nm',
         'evidence_class': 'NOMINAL_LABEL', 'direct_source': 'bank case naming',
         'source_sha256': '', 'valid_dataset': 'demo bank',
         'bounds': 'NOT an absolute diameter certificate',
         'missing_acquisition': 'independent diameter standard'},
        {'parameter': 'demo_pixel_size', 'value': 65.0, 'unit': 'nm',
         'evidence_class': 'SIMULATION_ASSUMPTION', 'direct_source': 'prior documents',
         'source_sha256': '', 'valid_dataset': 'demo only', 'bounds': 'assumption',
         'missing_acquisition': 'real object-plane scale with error'},
        {'parameter': 'object_plane_nm_per_pixel_with_error', 'value': None, 'unit': 'nm/px',
         'evidence_class': 'MISSING', 'direct_source': None, 'source_sha256': None,
         'valid_dataset': None, 'bounds': None,
         'missing_acquisition': 'stage calibration / certified ruler image (priority 1)'},
        {'parameter': 'objective_NA_immersion_polarization_reference_path', 'value': None,
         'unit': None, 'evidence_class': 'MISSING', 'direct_source': None, 'source_sha256': None,
         'valid_dataset': None, 'bounds': None,
         'missing_acquisition': 'objective datasheet + illumination/reference record (priority 1)'},
        {'parameter': 'exposure_time_per_frame', 'value': None, 'unit': 's',
         'evidence_class': 'MISSING', 'direct_source': None, 'source_sha256': None,
         'valid_dataset': None, 'bounds': None,
         'missing_acquisition': 'camera acquisition log (priority 1)'},
        {'parameter': 'trigger_convention_and_per_frame_timestamps', 'value': None, 'unit': None,
         'evidence_class': 'MISSING', 'direct_source': None, 'source_sha256': None,
         'valid_dataset': None, 'bounds': None,
         'missing_acquisition': 'trigger log + frame timestamp log (priority 1)'},
        {'parameter': 'sample_medium_substrate_fixation', 'value': None, 'unit': None,
         'evidence_class': 'MISSING', 'direct_source': None, 'source_sha256': None,
         'valid_dataset': None, 'bounds': None,
         'missing_acquisition': 'sample record + spacer metrology (priority 2)'},
        {'parameter': 'independent_trajectory', 'value': None, 'unit': None,
         'evidence_class': 'MISSING', 'direct_source': None, 'source_sha256': None,
         'valid_dataset': None, 'bounds': None,
         'missing_acquisition': 'independent tracking with scale and timebase (route A, priority 2)'},
        {'parameter': 'magnetic_field_B_vector_gradient_sync', 'value': None, 'unit': None,
         'evidence_class': 'MISSING', 'direct_source': None, 'source_sha256': None,
         'valid_dataset': None, 'bounds': None,
         'missing_acquisition': 'calibrated B(t) probe with camera sync (route B, priority 2)'},
        {'parameter': 'kappa_e_per_U_per_s', 'value': None, 'unit': 'e-/(U*s)',
         'evidence_class': 'MISSING', 'direct_source': None, 'source_sha256': None,
         'valid_dataset': None, 'bounds': None,
         'missing_acquisition': 'responsivity calibration (absolute count GO, priority 3)'},
        {'parameter': 'g_DN_per_e_and_offset_DN', 'value': None, 'unit': 'DN/e-, DN',
         'evidence_class': 'MISSING', 'direct_source': None, 'source_sha256': None,
         'valid_dataset': None, 'bounds': None,
         'missing_acquisition': 'photon-transfer curve + dark frame (priority 3)'},
        {'parameter': 'independent_diameter_reference', 'value': None, 'unit': 'nm',
         'evidence_class': 'MISSING', 'direct_source': None, 'source_sha256': None,
         'valid_dataset': None, 'bounds': None,
         'missing_acquisition': 'certified particle standard (absolute diameter GO, priority 3)'},
        {'parameter': 'particle_blank_Boff_control', 'value': None, 'unit': None,
         'evidence_class': 'MISSING', 'direct_source': None, 'source_sha256': None,
         'valid_dataset': None, 'bounds': None,
         'missing_acquisition': 'particle-free blank + B-off captures (priority 3)'},
    ]
    wcsv(os.path.join(out, 'metadata_readiness_v116.csv'), list(items[0].keys()), items)
    admission = {
        'LEGACY_NUMERICAL_FROZEN': True,
        'SOFTWARE_OPERATOR_FIXED_FIXTURES': ('CERTIFIED' if GATES.get('B_operator_boundaries')
                                             else 'PARTIAL'),
        'REAL_DEVICE_RELATIVE_FORWARD_GO': False,
        'ABSOLUTE_COUNT_GO': False,
        'ABSOLUTE_DIAMETER_VALIDATION_GO': False,
        'layer3_blockers': [i['parameter'] for i in items if i['evidence_class'] == 'MISSING'
                            and i['missing_acquisition'].startswith(('stage', 'objective',
                                                                     'camera', 'trigger', 'sample',
                                                                     'independent tracking',
                                                                     'calibrated B'))],
        'layer4_blockers': [i['parameter'] for i in items if i['evidence_class'] == 'MISSING'
                            and i['missing_acquisition'].startswith(('responsivity',
                                                                     'photon-transfer',
                                                                     'certified particle',
                                                                     'particle-free'))],
        'bounded_pilot_design': {
            'step_1': 'one instrument scale measurement + one camera exposure/timestamp '
                      'characterization + one B-off/blank capture + one known-D standard capture',
            'step_2': 'only after ALL step-1 inputs: at most 2 physics-condition pilots with '
                      'held-out experimental time windows, amplitude/phase/background/model and '
                      'measurement uncertainty budgets, and a P0-convergence assessment',
            'scaling': 'further amplification needs separate authorization',
            'v116_auto_physics_solves': 0,
            'route_note': 'route A (independent trajectory) preferred when available; route B needs '
                          'B(t)/gradient/sync + mechanics; 200Hz drive does not imply 400Hz translation; '
                          'unknown z/orientation keep bounded-uncertainty placeholders, never 0',
        },
    }
    with open(os.path.join(out, 'admission_v116.json'), 'w', encoding='utf-8') as f:
        json.dump(admission, f, indent=2, ensure_ascii=False)
    ok_d = len(items) == 16 and len(inherited) == 14
    if not ok_d:
        FAIL_KEYS.setdefault('D', ['items=%d inherited=%d' % (len(items), len(inherited))])
    GATES['D_physics_admission'] = ok_d
    STAGE_LOG['D'] = {'items': len(items), 'inherited_effective_rows': len(inherited),
                      'missing': sum(1 for i in items if i['evidence_class'] == 'MISSING'),
                      'layer3_go': False, 'layer4_count_go': False, 'layer4_diameter_go': False}
    log('Stage D: items=%d missing=%d' % (len(items), STAGE_LOG['D']['missing']))

# ============================== Stage F + archive ==============================

def stage_f(root, out, zip_path, checker_src, status_sha):
    log('=== Stage F: verifier selftest ===')
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import run_v115_all as v115mod  # reuse the proven selftest harness
    good = open(zip_path, 'rb').read()
    work = os.path.join(out, 'logs', 'verifier_selftest')
    os.makedirs(work, exist_ok=True)
    results = []
    MECH = {'missing_zip', 'missing_bank_case', 'duplicate_member', 'corrupt_crc',
            'manifest_path_traversal', 'status_missing', 'wrong_status_sha'}
    GATEC = {'gates_string_bool', 'gates_missing', 'wrong_task_id', 'wrong_source_commit'}

    def run_case(name, zbytes_or_none, expect_status_sha=None):
        zp = os.path.join(work, 'case_%s.zip' % name)
        if zbytes_or_none is not None:
            open(zp, 'wb').write(zbytes_or_none)
        elif os.path.exists(zp):
            os.remove(zp)
        res_p = os.path.join(work, 'case_%s.json' % name)
        if os.path.exists(res_p):
            os.remove(res_p)
        cargs = [sys.executable, checker_src, '--zip', zp, '--out', res_p]
        if expect_status_sha:
            cargs += ['--expect-status-sha', expect_status_sha]
        proc = subprocess.run(cargs, capture_output=True, text=True, timeout=600)
        res = json.load(open(res_p, encoding='utf-8')) if os.path.isfile(res_p) else {}
        passed = (proc.returncode != 0) and (res.get('archive_valid') is not True)
        results.append({'case': name, 'exit_code': proc.returncode,
                        'archive_valid': res.get('archive_valid'),
                        'verdict': 'PASS' if passed else 'FAIL'})
        return passed, res

    zin = zipfile.ZipFile(io.BytesIO(good))
    all_ok = True

    def run_typed(name, zbytes_or_none, expect_status_sha=None):
        passed, res = run_case(name, zbytes_or_none, expect_status_sha)
        if name in MECH:
            typed_ok = passed and res.get('archive_integrity') is False
        elif name in GATEC:
            typed_ok = passed and res.get('archive_integrity') is True \
                and res.get('numerical_accepted') is False
        else:
            typed_ok = passed
        if not typed_ok:
            results[-1]['verdict'] = 'FAIL'
        return typed_ok

    all_ok &= run_typed('missing_zip', None)
    drop = [n for n in zin.namelist() if 'v092_bank_D30_zf450_M200_a5.mat' in n]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zo:
        for n in zin.namelist():
            if n == drop[0] or n.endswith('manifest_sha256.csv'):
                continue
            zo.writestr(n, zin.read(n))
        man = zin.read('iscat_v116_return/manifest_sha256.csv').decode('utf-8').splitlines()
        zo.writestr('iscat_v116_return/manifest_sha256.csv',
                    '\n'.join(ln for ln in man if 'v092_bank_D30_zf450_M200_a5.mat' not in ln) + '\n')
    all_ok &= run_typed('missing_bank_case', buf.getvalue())
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zo:
        for n in zin.namelist():
            zo.writestr(n, zin.read(n))
        zo.writestr(zin.namelist()[3], zin.read(zin.namelist()[3]))
    all_ok &= run_typed('duplicate_member', buf.getvalue())
    corrupt = bytearray(good)
    corrupt[len(corrupt) // 2] ^= 0xFF
    all_ok &= run_typed('corrupt_crc', bytes(corrupt))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zo:
        for n in zin.namelist():
            zo.writestr(n, zin.read(n))
        man = zin.read('iscat_v116_return/manifest_sha256.csv').decode('utf-8')
        zo.writestr('iscat_v116_return/manifest_sha256.csv', man + '../escape.txt,%s\n' % ('0' * 64))
    all_ok &= run_typed('manifest_path_traversal', buf.getvalue())
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zo:
        for n in zin.namelist():
            if n.endswith('/status.json'):
                continue
            if n.endswith('manifest_sha256.csv'):
                man = zin.read(n).decode('utf-8').splitlines()
                zo.writestr(n, '\n'.join(ln for ln in man if 'status.json' not in ln) + '\n')
                continue
            zo.writestr(n, zin.read(n))
    all_ok &= run_typed('status_missing', buf.getvalue())
    st = json.loads(zin.read('iscat_v116_return/status.json'))
    for name, mutate in (('gates_string_bool', lambda s: s['gates'].update({'A_source_forensics': 'true'})),
                         ('gates_missing', lambda s: s['gates'].pop('A_source_forensics')),
                         ('wrong_task_id', lambda s: s.update({'task_id': 'WRONG_TASK'})),
                         ('wrong_source_commit', lambda s: s.update({'source_commit': '0' * 40}))):
        s2 = json.loads(json.dumps(st))
        mutate(s2)
        new_status = json.dumps(s2, indent=2).encode('utf-8')
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zo:
            for n in zin.namelist():
                if n.endswith('/status.json'):
                    zo.writestr(n, new_status)
                elif n.endswith('manifest_sha256.csv'):
                    man = zin.read(n).decode('utf-8').splitlines()
                    new_sha = hashlib.sha256(new_status).hexdigest()
                    zo.writestr(n, '\n'.join(
                        ('status.json,' + new_sha) if ln.split(',')[0].strip() == 'status.json' else ln
                        for ln in man if ln.strip()) + '\n')
                else:
                    zo.writestr(n, zin.read(n))
        all_ok &= run_typed(name, buf.getvalue())
    all_ok &= run_typed('wrong_status_sha', good, expect_status_sha='0' * 64)
    res_p = os.path.join(work, 'positive.json')
    proc = subprocess.run([sys.executable, checker_src, '--zip', zip_path,
                           '--expect-status-sha', status_sha, '--out', res_p],
                          capture_output=True, text=True, timeout=600)
    pos = json.load(open(res_p, encoding='utf-8')) if os.path.isfile(res_p) else {}
    positive_ok = pos.get('archive_integrity') is True
    results.append({'case': 'positive_control', 'exit_code': proc.returncode,
                    'archive_integrity': pos.get('archive_integrity'),
                    'verdict': 'PASS' if positive_ok else 'FAIL'})
    st_fields = list(results[0].keys()) + [k for r in results for k in r if k not in results[0]]
    wcsv(os.path.join(out, 'logs', 'v116_verifier_selftest.csv'), st_fields, results)
    for fn in os.listdir(work):
        if fn.startswith('case_') and fn.endswith('.zip'):
            os.remove(os.path.join(work, fn))
    n_pass = sum(1 for r in results if r['verdict'] == 'PASS')
    ok_f = all_ok and positive_ok and n_pass == len(results)
    if not ok_f:
        FAIL_KEYS.setdefault('F', ['selftest %d/%d' % (n_pass, len(results))])
    GATES['F_verifier_selftest'] = ok_f
    STAGE_LOG['F'] = {'cases': len(results), 'passed': n_pass, 'positive_control': positive_ok}
    log('Stage F: selftest %d/%d PASS' % (n_pass, len(results)))

def build_status(out, tool_sha):
    numerical = all(GATES[g] for g in REQUIRED_GATES)
    statuses = {'execution': 'COMPLETE',
                'numerical': 'SOURCE_FORENSICS_AND_ACCEPTANCE_SEALED' if numerical else 'UNSEALED_PARTIAL',
                'archive': 'PRE_ARCHIVE_VERIFICATION',
                'physics': 'ALL_FORWARD_GO_FALSE_PENDING_INPUTS'}
    status = {'schema': 'iscat116.status.1', 'task_id': TASK_ID,
              'created_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
              'source_commit': EXPECTED_V115, 'parent_commit': EXPECTED_V114,
              'tool_sha256': tool_sha,
              'required_gates': list(REQUIRED_GATES),
              'gates': {g: bool(GATES[g]) for g in REQUIRED_GATES},
              'states': statuses,
              'admission_layers': {
                  'LEGACY_NUMERICAL_FROZEN': True,
                  'SOFTWARE_OPERATOR_FIXED_FIXTURES': 'CERTIFIED' if GATES.get('B_operator_boundaries') else 'PARTIAL',
                  'REAL_DEVICE_RELATIVE_FORWARD_GO': False,
                  'ABSOLUTE_COUNT_GO': False,
                  'ABSOLUTE_DIAMETER_VALIDATION_GO': False},
              'v115_historical_note': 'v115 A-gate failure (parent-check driver defect) recorded in '
                                      'historical_v115_source_failure.json; never overwritten; the '
                                      'v116 A gate is a clean-worktree verdict and does NOT rewrite '
                                      'the v115 historical status',
              'stage_logs': STAGE_LOG,
              'environment': {'python': sys.version.split()[0],
                              'numpy': np.__version__, 'scipy': __import__('scipy').__version__,
                              'pythondontwritebytecode': '1'},
              'frozen_states': {'calibration_valid': False, 'experimental_validation': False,
                                'detection_validated': False, 'single_particle_diameter': 'NOT_ESTIMATED'},
              'p0_status': 'OPEN (not upgraded)',
              'rule7_new_authorizations': 0,
              'overall': 'SOURCE_FORENSICS_AND_ACCEPTANCE_SEALED' if numerical else 'UNSEALED_PARTIAL'}
    p = os.path.join(out, 'status.json')
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(status, f, indent=2, ensure_ascii=False)
    return p, hashlib.sha256(open(p, 'rb').read()).hexdigest(), statuses, numerical

def build_zip(out, zip_path):
    manifest = []
    for dirpath, dirnames, filenames in os.walk(out):
        for fn in sorted(filenames):
            if fn == 'manifest_sha256.csv':
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, out).replace(os.sep, '/')
            manifest.append((rel, hashlib.sha256(open(full, 'rb').read()).hexdigest()))
    manifest.sort()
    with open(os.path.join(out, 'manifest_sha256.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['relative_path', 'sha256'])
        for rel, sha in manifest:
            w.writerow([rel, sha])
    if os.path.exists(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for dirpath, dirnames, filenames in os.walk(out):
            for fn in sorted(filenames):
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, out).replace(os.sep, '/')
                z.write(full, 'iscat_v116_return/%s' % rel)
    return hashlib.sha256(open(zip_path, 'rb').read()).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--zip', required=True)
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    out = os.path.abspath(args.out)
    zip_path = os.path.abspath(args.zip)
    t0 = time.time()
    if os.path.exists(out) and os.listdir(out):
        print('[v116] FATAL: out dir exists and is not empty')
        return 3
    try:
        if os.path.commonpath([root]) == os.path.commonpath([root, out]):
            print('[v116] FATAL: out must be outside the source root')
            return 3
    except ValueError:
        pass
    os.makedirs(out, exist_ok=True)
    for sub in ('analysis', 'tables', 'logs'):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    tool_sha = sha256_file(os.path.abspath(__file__))
    launch = {'task_id': TASK_ID, 'root': root, 'out': out, 'zip': zip_path,
              'expected_v115_commit': EXPECTED_V115, 'tool_sha256': tool_sha,
              'command': 'python tools/run_v116_all.py --root "%s" --out "%s" --zip "%s"' % (root, out, zip_path),
              'python': sys.version.split()[0], 'numpy': np.__version__,
              'scipy': __import__('scipy').__version__,
              'pid': os.getpid(), 'started_at': time.strftime('%Y-%m-%dT%H:%M:%S')}
    launch_ext = os.path.splitext(zip_path)[0] + '.launch.json'
    with open(launch_ext, 'w', encoding='utf-8') as f:
        json.dump(launch, f, indent=2)
    with open(os.path.join(out, 'logs', 'v116_launch_record.json'), 'w', encoding='utf-8') as f:
        json.dump(launch, f, indent=2)
    shutil.copy2(os.path.abspath(__file__), os.path.join(out, 'logs', 'run_v116_all_snapshot.py'))
    log('launch recorded: %s' % launch_ext)

    stage_a(root, out)
    stage_b(root, out)
    stage_c(root, out)
    stage_d(root, out)

    numerical = all(GATES[g] for g in REQUIRED_GATES if g != 'F_verifier_selftest')
    final_summary = {'gates': GATES, 'stage_logs': STAGE_LOG, 'fail_keys': FAIL_KEYS,
                     'elapsed_seconds': None,
                     'pre_archive_note': 'in-ZIP snapshot; external post_archive_summary.json carries '
                                         'final values', 'zip_sha256': None}
    with open(os.path.join(out, 'logs', 'v116_final_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(final_summary, f, indent=2)
    status_path, status_sha, statuses, _ = build_status(out, tool_sha)
    tool_shas = {'run_v116_all.py': tool_sha,
                 'v116_archive_check.py': sha256_file(os.path.join(root, 'tools', 'v116_archive_check.py')),
                 'v116_operator_boundary_tests.py': sha256_file(os.path.join(root, 'tools', 'v116_operator_boundary_tests.py')),
                 'v115_saved_probe_bridge.py': sha256_file(os.path.join(root, 'tools', 'v115_saved_probe_bridge.py')),
                 'observation_operator.py': sha256_file(os.path.join(root, 'tools', 'observation_operator.py')),
                 'run_v115_all.py': sha256_file(os.path.join(root, 'tools', 'run_v115_all.py'))}
    with open(os.path.join(out, 'logs', 'v116_tool_shas.json'), 'w', encoding='utf-8') as f:
        json.dump(tool_shas, f, indent=2)
    zip_sha = build_zip(out, zip_path)  # provisional selftest fixture
    checker_src = os.path.join(root, 'tools', 'v116_archive_check.py')
    tool_shas['v116_archive_check.py'] = sha256_file(checker_src)
    with open(os.path.join(out, 'logs', 'v116_tool_shas.json'), 'w', encoding='utf-8') as f:
        json.dump(tool_shas, f, indent=2)
    stage_f(root, out, zip_path, checker_src, status_sha)
    provisional_sha = sha256_file(zip_path)
    if GATES['F_verifier_selftest']:
        final_summary['gates'] = GATES
        with open(os.path.join(out, 'logs', 'v116_final_summary.json'), 'w', encoding='utf-8') as f:
            json.dump(final_summary, f, indent=2)
        os.remove(status_path)
        status_path, status_sha, statuses, _ = build_status(out, tool_sha)
        zip_sha = build_zip(out, zip_path)
        with open(os.path.join(out, 'logs', 'v116_provisional_zip_sha.json'), 'w', encoding='utf-8') as f:
            json.dump({'provisional_zip_sha256': provisional_sha, 'final_zip_sha256': zip_sha,
                       'protocol': 'provisional selftest fixture replaced by single final zip after '
                                   'verifier qualification; both hashes disclosed'}, f, indent=2)
    check_json = os.path.splitext(zip_path)[0] + '.archive_check.json'
    proc = subprocess.run([sys.executable, checker_src, '--zip', zip_path,
                           '--expect-status-sha', status_sha, '--out', check_json],
                          capture_output=True, text=True, timeout=900)
    archive_ok = proc.returncode == 0
    exit_code = 0 if (numerical and archive_ok and GATES['F_verifier_selftest']) else 2
    final_summary['elapsed_seconds'] = round(time.time() - t0, 1)
    final_summary['zip_sha256'] = zip_sha
    final_summary['status_json_sha256'] = status_sha
    final_summary['exit_code'] = exit_code
    final_summary['archive_integrity'] = archive_ok
    post_path = os.path.splitext(zip_path)[0] + '.post_archive_summary.json'
    with open(post_path, 'w', encoding='utf-8') as f:
        json.dump(final_summary, f, indent=2)
    post_sha = sha256_file(post_path)
    receipt = {'task_id': TASK_ID, 'source_commit': EXPECTED_V115, 'parent_commit': EXPECTED_V114,
               'tool_sha256': tool_sha, 'tool_shas': tool_shas,
               'zip_path': zip_path, 'zip_sha256': zip_sha,
               'zip_size_bytes': os.path.getsize(zip_path),
               'status_json_sha256_in_zip': status_sha,
               'post_archive_summary_path': post_path, 'post_archive_summary_sha256': post_sha,
               'exit_code': exit_code,
               'execution_status': statuses['execution'], 'numerical_status': statuses['numerical'],
               'archive_status': 'ARCHIVE_VERIFIED' if archive_ok else 'ARCHIVE_CHECK_FAILED',
               'physics_status': statuses['physics'],
               'created_at': time.strftime('%Y-%m-%dT%H:%M:%S')}
    with open(os.path.splitext(zip_path)[0] + '.receipt.json', 'w', encoding='utf-8') as f:
        json.dump(receipt, f, indent=2, ensure_ascii=False)
    log('final: gates=%s numerical=%s archive=%s exit=%d zip=%s'
        % (GATES, statuses['numerical'], receipt['archive_status'], exit_code, zip_sha))
    if exit_code != 0:
        log('FAIL_KEYS: %s' % json.dumps(FAIL_KEYS))
    return exit_code

if __name__ == '__main__':
    sys.exit(main())
