"""V165 Gate A: truth-aware provenance audit.  SEPARATE ROLE FROM THE ESTIMATOR.

This is the only workstation module permitted to read the V142 validator-only
truth document.  It is imported exclusively by ``tools/gate_a.py``, which runs
as its own process before any estimator module exists in memory.

The estimator stack (``v165_run.py`` / ``v165_io.py`` / ``v165_objective.py`` /
``v152_gls_core.py`` / ``v152_budget_store.py``) must never import or name this
module; that is enforced twice:

* static literal scan of the estimator modules (``v165_io.assert_no_truth_literals``)
* the runtime audit hook installed by ``v165_run.execute`` blocks ``open`` of
  the truth file and the sealed validator metadata, and blocks ``import`` of
  this module, the height generator and the post-seal validator.

Everything here is read-only.  No model call, no camera exposure and no new
random draw is performed: the camera replay below re-derives already stored
counts from their frozen seeds and must reproduce them bit-for-bit.
"""
from __future__ import annotations
import hashlib
import json
import sqlite3
from pathlib import Path

import h5py
import numpy as np

from v165_io import require, read, sha, blob

TRUTH_REL = 'results/v142/validation/new_N_validator_only_truth.json'
TRUTH_BLOB_SHA1 = 'cd097e0c5236c331f8b1862e6e301674454a871e'
GROUPS = ('ANON_01', 'ANON_02', 'ANON_03', 'ANON_04')
LEVEL = 100000
SOLVE_DIR = 'results/v143/provenance/n_solve_source'
LINEAGE_REL = 'results/v143/provenance/N_solve_lineage.json'
SOURCE_AUDIT_REL = 'results/v143/provenance/N_source_audit.json'
CAMERA_H5_REL = 'results/v143/validation/camera_pilot/conditional_camera_arrays.h5'
CAMERA_H5_SHA256 = '074305df1b6bbd47f7f523b05d871312309e9b6ffa390cd50d0be18296427e26'
CAMERA_LEDGER_REL = 'results/v143/logs/v143_budget.sqlite'
CAMERA_PILOT_REL = 'tools/camera_pilot.py'
CAMERA_CFG_REL = 'config/v143_science_config.json'
THRESHOLD_REL = 'results/v143/validation/camera_pilot/B100000_dev_frozen_threshold.json'
V146_SCORES_REL = 'results/v146/validator_only/camera_scores.json'


def _f(v):
    return float(np.asarray(v, dtype=float).ravel()[0])


def truth_identity(repo):
    """Read the validator-only truth and prove its frozen Git identity."""
    p = Path(repo) / TRUTH_REL
    require(p.is_file(), 'TRUTH_FILE_MISSING')
    raw = p.read_bytes()
    got = blob(p)
    require(got == TRUTH_BLOB_SHA1, 'TRUTH_GIT_BLOB_CHANGED')
    doc = json.loads(raw.decode('utf-8-sig'))
    cases = doc.get('cases')
    require(isinstance(cases, list) and len(cases) == 4, 'TRUTH_MUST_HOLD_FOUR_SCENES')
    scene = {}
    for c in cases:
        name = str(c['case'])
        require(name in ('N01', 'N02', 'N03', 'N04'), 'UNKNOWN_TRUTH_SCENE')
        anon = f'ANON_{int(name[1:]):02d}'
        vals = {k: _f(c[k]) for k in ('D_nm', 'h_nm', 'x_nm', 'y_nm')}
        require(all(np.isfinite(v) for v in vals.values()), 'NONFINITE_TRUTH')
        scene[anon] = dict(scene=name, **vals)
    require(sorted(scene) == list(GROUPS), 'TRUTH_SCENE_SET')
    return dict(
        path=TRUTH_REL, git_blob_sha1=got, sha256=hashlib.sha256(raw).hexdigest(),
        bytes=len(raw), schema=doc.get('schema'),
        historical_status_field=doc.get('status'),
        status_field_is_not_completion_evidence=True,
        scenes=scene, model_calls=0,
        scope='VALIDATOR_ONLY_ACCESS_OF_OPENED_DEVELOPMENT_SCENES')


def solve_identity(repo, truth):
    """Prove archived BEM solve meta == truth geometry for all four scenes."""
    lineage = read(Path(repo) / LINEAGE_REL)
    rows = lineage['rows']
    require(len(rows) == 4, 'LINEAGE_MUST_HOLD_FOUR_SOLVES')
    out = {}
    for r in rows:
        anon = r['anon']
        require(anon in truth['scenes'], 'LINEAGE_UNKNOWN_SCENE:' + anon)
        t = truth['scenes'][anon]
        p = Path(repo) / SOLVE_DIR / r['solve_filename']
        require(p.is_file(), 'SOLVE_FILE_MISSING:' + anon)
        got = sha(p)
        require(got == r['solve_sha256'], 'SOLVE_SHA_CHANGED:' + anon)
        with h5py.File(p, 'r') as f:
            meta = {k: _f(f['meta/' + k][()]) for k in
                    ('D_nm', 'h_nm', 'gap_nm', 'mesh', 'np_re', 'np_im', 'lambda_nm', 'NA')}
            solver_id = bytes(np.asarray(f['meta/solver_id'][()]).astype(np.uint8).ravel()).decode()
            cfg_d = _f(f['s/cfg/particle/diameter_nm'][()])
            cfg_gap = _f(f['s/cfg/particle/gap_nm'][()])
            cfg_xy = np.asarray(f['s/cfg/particle/xy_nm'][()], float).ravel().tolist()
        require(abs(meta['D_nm'] - t['D_nm']) <= 1e-9, 'SOLVE_D_DISAGREES_WITH_SCENE:' + anon)
        require(abs(meta['h_nm'] - t['h_nm']) <= 1e-9, 'SOLVE_H_DISAGREES_WITH_SCENE:' + anon)
        require(abs(meta['gap_nm'] - (t['h_nm'] - t['D_nm'] / 2.0)) <= 1e-9,
                'SOLVE_GAP_NOT_H_MINUS_R:' + anon)
        require(abs(meta['np_re'] - 1.38) <= 1e-12 and abs(meta['np_im']) <= 1e-12,
                'SOLVE_MATERIAL_CHANGED:' + anon)
        require(abs(meta['NA'] - 0.8) <= 1e-12 and abs(meta['lambda_nm'] - 520.0) <= 1e-12,
                'SOLVE_OPTICS_CHANGED:' + anon)
        require(abs(cfg_d - t['D_nm']) <= 1e-9 and abs(cfg_gap - meta['gap_nm']) <= 1e-9,
                'SOLVE_CONFIG_GEOMETRY_CHANGED:' + anon)
        require(all(abs(v) <= 1e-12 for v in cfg_xy), 'SOLVE_CONFIG_NOT_CENTERED:' + anon)
        require(solver_id == r['solver_id'], 'SOLVE_ID_CHANGED:' + anon)
        out[anon] = dict(solve_file=r['solve_filename'], solve_sha256=got,
                         solver_id=solver_id, meta=meta, cfg_diameter_nm=cfg_d,
                         cfg_gap_nm=cfg_gap, cfg_xy_nm=cfg_xy,
                         truth_D_nm=t['D_nm'], truth_h_nm=t['h_nm'],
                         lineage_status=r.get('lineage'),
                         lineage_limitation=r.get('limitation'))
    return out


def _load_render(p):
    with h5py.File(p, 'r') as f:
        out = {}
        for k in ('Itotal', 'Iref', 'Isca', 'Icross', 'contrast'):
            out[k] = np.asarray(f['r/' + k][()], float).T[::-1, :]
        out['shift_xy_nm'] = np.asarray(f['r/shift_xy_nm'][()], float).ravel()
        out['center_nm'] = np.asarray(f['r/center_nm'][()], float).ravel()
        out['particle_n'] = _f(f['r/particle_n'][()])
        out['render_mode'] = bytes(np.asarray(f['r/render_mode'][()]).astype(np.uint8).ravel()).decode()
        out['intensity_identity_relative_error'] = _f(f['r/intensity_identity_relative_error'][()])
    return out


def render_identity(repo, truth):
    """Prove the at-offset render MAT is the frozen 17x17 direct camera image."""
    audit = read(Path(repo) / SOURCE_AUDIT_REL)
    rows = {}
    for anon in GROUPS:
        t = truth['scenes'][anon]
        variants = {v['variant']: v for v in audit['cases'][anon]['variants']}
        require(set(variants) == {'default', 'wide', 'at_offset'}, 'RENDER_VARIANTS:' + anon)
        checked = {}
        for name, v in variants.items():
            p = Path(repo) / v['path']
            require(p.is_file(), 'RENDER_MAT_MISSING:' + anon + ':' + name)
            got = sha(p)
            require(got == v['source_mat_sha256'], 'RENDER_SHA_CHANGED:' + anon + ':' + name)
            checked[name] = dict(path=v['path'], sha256=got,
                                 bytes=p.stat().st_size,
                                 native_camera_shape=v['native_camera_shape'])
        p = Path(repo) / variants['at_offset']['path']
        d = _load_render(p)
        require(d['Itotal'].shape == (17, 17) and d['Iref'].shape == (17, 17), 'RENDER_SHAPE:' + anon)
        for k in ('Itotal', 'Iref', 'Isca', 'Icross', 'contrast'):
            require(np.isfinite(d[k]).all(), 'NONFINITE_RENDER:' + k + ':' + anon)
        require(bool((d['Iref'] > 0).all()), 'NONPOSITIVE_REFERENCE:' + anon)
        rel_c = float(np.max(np.abs((d['Itotal'] - d['Iref']) / d['Iref'] - d['contrast'])))
        require(rel_c <= 1e-12, 'CONTRAST_IDENTITY:' + anon)
        rel_i = float(np.max(np.abs(d['Itotal'] - (d['Iref'] + d['Isca'] + d['Icross']))
                             / np.maximum(np.abs(d['Iref']), 1e-300)))
        require(rel_i <= 1e-12, 'INTENSITY_DECOMPOSITION_IDENTITY:' + anon)
        require(d['render_mode'] == 'particle_shift', 'RENDER_MODE:' + anon)
        require(abs(d['particle_n'] - 1.38) <= 1e-12, 'RENDER_MATERIAL:' + anon)
        require(np.allclose(d['shift_xy_nm'], [t['x_nm'], t['y_nm']], rtol=0, atol=1e-9),
                'RENDER_OFFSET_DISAGREES_WITH_SCENE:' + anon)
        require(abs(d['center_nm'][2] - t['h_nm']) <= 1e-9, 'RENDER_HEIGHT_DISAGREES_WITH_SCENE:' + anon)
        require(d['intensity_identity_relative_error'] <= 1e-12, 'RENDER_IDENTITY_ERROR:' + anon)
        score = d['contrast'][2:15, 2:15]
        rows[anon] = dict(variants=checked, at_offset_sha256=checked['at_offset']['sha256'],
                          shift_xy_nm=d['shift_xy_nm'].tolist(),
                          center_nm=d['center_nm'].tolist(), particle_n=d['particle_n'],
                          contrast_identity_max_abs=rel_c,
                          intensity_identity_max_rel=rel_i,
                          score_C_sha256=hashlib.sha256(np.ascontiguousarray(score).tobytes()).hexdigest(),
                          score_C_max_abs=float(np.max(np.abs(score))))
    return rows


def _v143_ledger_events(repo):
    p = Path(repo) / CAMERA_LEDGER_REL
    require(p.is_file(), 'V143_LEDGER_MISSING')
    con = sqlite3.connect(p.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        require(con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'V143_LEDGER_INTEGRITY')
        cols = [r[1] for r in con.execute('PRAGMA table_info(events)')]
        require(cols == ['op', 'metric', 'units', 'state', 'created', 'finished', 'actual', 'payload_json'],
                'V143_LEDGER_IS_NOT_THE_EXPECTED_EVENTS_TABLE')
        rows = {}
        for op, metric, units, state, created, finished, actual, payload in con.execute(
                'SELECT op,metric,units,state,created,finished,actual,payload_json FROM events'):
            rows[op] = dict(metric=metric, units=units, state=state, created=created,
                            finished=finished, actual=actual,
                            payload=json.loads(payload))
        totals = dict(con.execute('SELECT metric,SUM(actual) FROM events GROUP BY metric').fetchall())
        n = con.execute('SELECT COUNT(*) FROM events').fetchone()[0]
        state_counts = dict(con.execute('SELECT state,COUNT(*) FROM events GROUP BY state').fetchall())
    finally:
        con.close()
    return rows, totals, n, state_counts


def camera_chain(repo, truth, cfg143):
    """MAT bytes -> V143 signature -> ledger -> H5 counts -> C -> V163 frames -> detections."""
    pc = cfg143['camera_optional_pilot']
    levels = [int(x) for x in pc['B_electrons_per_pixel_per_100us']]
    require(LEVEL in levels, 'FROZEN_LEVEL_ABSENT')
    seed = int(pc['rng_seeds_by_B'][levels.index(LEVEL)])
    require(seed == 1431003, 'B100000_SEED_CHANGED')
    read_noise = float(pc['read_noise_electrons'])
    anon = cfg143['N_opened_scored_cases']
    require(list(anon) == list(GROUPS), 'V143_ANONYMISATION_ORDER')
    folder = Path(repo) / cfg143['source_files']['N_original_mats']

    images = {}
    for a in anon:
        p = folder / (a + '_at_offset.mat')
        with h5py.File(p, 'r') as f:
            I = np.asarray(f['r/Itotal'][()], float).T[::-1, :]
            B = np.asarray(f['r/Iref'][()], float).T[::-1, :]
            C = np.asarray(f['r/contrast'][()], float).T[::-1, :]
        require(I.shape == (17, 17) and np.isfinite(I).all() and np.isfinite(B).all(),
                'CAMERA_PILOT_SOURCE_UNQUALIFIED:' + a)
        require(not np.any(B <= 0), 'NONPOSITIVE_REFERENCE:' + a)
        require(float(np.max(np.abs((I - B) / B - C))) <= 1e-12, 'CONTRAST_IDENTITY:' + a)
        images[a] = (I, B, sha(p))

    h5p = Path(repo) / CAMERA_H5_REL
    require(sha(h5p) == CAMERA_H5_SHA256, 'CAMERA_H5_CHANGED')
    threshold_doc = read(Path(repo) / THRESHOLD_REL)
    require(threshold_doc['B'] == LEVEL and threshold_doc['not_tuned_using_independent_val'] is True,
            'THRESHOLD_NOT_FROZEN')
    threshold = float(threshold_doc['threshold'])
    ledger, totals, n_events, state_counts = _v143_ledger_events(repo)
    v146 = {r['event_id']: r for r in read(Path(repo) / V146_SCORES_REL)['rows']
            if int(r['B']) == LEVEL}

    evidence = {}
    with h5py.File(h5p, 'r') as h:
        require(f'B{LEVEL}/target' in h, 'CAMERA_TARGET_GROUP_MISSING')
        require(len(h[f'B{LEVEL}/target']) == 12, 'EXPECTED_TWELVE_TARGETS')
        for a in GROUPS:
            I, B, msha = images[a]
            frames = []
            for j in range(3):
                label = f'{a}_{j:02d}'
                path = f'B{LEVEL}/target/{label}'
                require(path in h, 'MISSING_CAMERA_EVENT:' + label)
                g = h[path]
                expected_sig = hashlib.sha256(
                    (str(LEVEL) + '|' + str(seed) + '|target|' + label + '|' + a + '|' + msha).encode()
                ).hexdigest()
                require(str(g.attrs['signature']) == expected_sig, 'H5_SIGNATURE_NOT_BOUND_TO_MAT:' + label)
                op = f'V143_CAMERA_B{LEVEL}_target_{label}'
                require(op in ledger, 'V143_LEDGER_EVENT_MISSING:' + label)
                ev = ledger[op]
                require(ev['state'] == 'COMPLETED' and ev['metric'] == 'CAMERA' and ev['actual'] == 2,
                        'V143_EVENT_NOT_COMPLETED:' + label)
                require(ev['payload']['source_signature'] == expected_sig,
                        'V143_LEDGER_SIGNATURE_MISMATCH:' + label)
                require(ev['payload']['rng_seed'] == seed and ev['payload']['B'] == LEVEL
                        and ev['payload']['anon'] == a, 'V143_LEDGER_IDENTITY:' + label)
                stored_fg = np.asarray(g['foreground_counts'][()], float)
                stored_ref = np.asarray(g['reference_counts'][()], float)
                require(stored_fg.shape == (17, 17) and stored_ref.shape == (17, 17)
                        and np.isfinite(stored_fg).all() and np.isfinite(stored_ref).all(),
                        'STORED_COUNT_SHAPE_OR_NONFINITE:' + label)
                require(np.all(stored_ref > 0), 'NONPOSITIVE_STORED_REFERENCE:' + label)
                c_full = (stored_fg - stored_ref) / stored_ref
                v_full = ((stored_fg + read_noise ** 2) / (stored_ref * stored_ref)
                          + (stored_fg * stored_fg) * (stored_ref + read_noise ** 2)
                          / (stored_ref ** 4))
                require(np.isfinite(v_full).all() and np.all(v_full > 0),
                        'INVALID_STORED_VARIANCE:' + label)
                require(np.array_equal(c_full, np.asarray(g['C'][()], float)),
                        'CAMERA_C_REPLAY_FAILED:' + label)
                c_score = c_full[2:15, 2:15]
                v_score = v_full[2:15, 2:15]
                T = float(np.max(np.abs(c_score)))
                require(abs(float(g.attrs['T']) - T) <= 1e-15, 'CAMERA_T_REPLAY_FAILED:' + label)
                require(abs(float(ev['payload']['finish']['score']) - T) <= 1e-15,
                        'LEDGER_T_MISMATCH:' + label)
                ctx = read(Path(repo) / f'results/v163/source_context/v156/{LEVEL}_{a}.json')['diagnostic']
                Y = np.asarray(ctx['frame_Y'], float)[j]
                V = np.asarray(ctx['frame_V'], float)[j]
                require(np.array_equal(Y, c_score), 'V163_FRAME_Y_NOT_CAMERA_C:' + label)
                require(np.array_equal(V, v_score), 'V163_FRAME_V_NOT_CAMERA_V:' + label)
                detected = bool(T > threshold)
                frozen = v146.get(f'B{LEVEL}_{label}')
                require(frozen is not None, 'V146_FROZEN_DETECTION_MISSING:' + label)
                require(bool(frozen['detected']) == detected, 'V146_DETECTION_DISAGREES:' + label)
                frames.append(dict(event_id=f'B{LEVEL}_{label}', label=label,
                                   v143_op=op, source_signature=expected_sig,
                                   v143_event_state=ev['state'],
                                   v143_event_metric=ev['metric'],
                                   v143_event_actual=ev['actual'],
                                   foreground_sha256=hashlib.sha256(
                                       np.ascontiguousarray(stored_fg).tobytes()).hexdigest(),
                                   reference_sha256=hashlib.sha256(
                                       np.ascontiguousarray(stored_ref).tobytes()).hexdigest(),
                                   C_sha256=hashlib.sha256(np.ascontiguousarray(c_full).tobytes()).hexdigest(),
                                   score_C_sha256=hashlib.sha256(
                                       np.ascontiguousarray(c_score).tobytes()).hexdigest(),
                                   variance_sha256=hashlib.sha256(
                                       np.ascontiguousarray(v_score).tobytes()).hexdigest(),
                                   foreground_counts_sha256=hashlib.sha256(
                                       np.ascontiguousarray(stored_fg).tobytes()).hexdigest(),
                                   reference_counts_sha256=hashlib.sha256(
                                       np.ascontiguousarray(stored_ref).tobytes()).hexdigest(),
                                   T=T, threshold=threshold, detected=detected,
                                   v146_frozen_detected=bool(frozen['detected'])))
            evidence[a] = dict(source_mat_sha256=msha, frames=frames)
    return dict(level=LEVEL, rng_seed=seed, read_noise_e=read_noise,
                threshold=threshold, threshold_file_sha256=sha(Path(repo) / THRESHOLD_REL),
                camera_h5_sha256=CAMERA_H5_SHA256,
                v143_ledger_events=n_events, v143_ledger_metric_totals=totals,
                v143_ledger_states=state_counts, by_group=evidence,
                detections={g: [f['detected'] for f in evidence[g]['frames']] for g in GROUPS},
                new_camera_exposures=0, new_camera_noise_draws=0,
                replay_scope='READ_ONLY_AUDIT_OF_STORED_COUNTS_NO_RNG_NO_NEW_DRAW')


def source_chain(repo):
    rels = [CAMERA_CFG_REL, CAMERA_PILOT_REL, CAMERA_LEDGER_REL, CAMERA_H5_REL,
            THRESHOLD_REL, V146_SCORES_REL, LINEAGE_REL, SOURCE_AUDIT_REL]
    rows = {}
    for rel in rels:
        p = Path(repo) / rel
        require(p.is_file(), 'SOURCE_CHAIN_FILE_MISSING:' + rel)
        rows[rel] = dict(sha256=sha(p), bytes=p.stat().st_size,
                         git_blob=blob(p) if (Path(repo) / '.git').exists() else None)
    for g in GROUPS:
        rel = f'results/v163/source_context/v156/{LEVEL}_{g}.json'
        p = Path(repo) / rel
        require(p.is_file(), 'V163_CONTEXT_MISSING:' + g)
        rows[rel] = dict(sha256=sha(p), bytes=p.stat().st_size, git_blob=blob(p))
    return rows


def build(repo, cfg143):
    """Assemble Gate A.  Raises on any unaudited/mismatched link."""
    repo = Path(repo)
    truth = truth_identity(repo)
    solves = solve_identity(repo, truth)
    renders = render_identity(repo, truth)
    chain = source_chain(repo)
    camera = camera_chain(repo, truth, cfg143)
    require(sorted(camera['by_group']) == list(GROUPS), 'CAMERA_GROUP_SET')
    checks = {
        'four_scenes_present': len(truth['scenes']) == 4,
        'four_solve_bytes_match_truth_geometry': len(solves) == 4,
        'four_at_offset_renders_match_scene_offsets': len(renders) == 4,
        'twelve_frames_replay_from_mat_bytes': sum(
            len(v['frames']) for v in camera['by_group'].values()) == 12,
        'twelve_v143_events_completed': all(
            f['v143_event_state'] == 'COMPLETED'
            and f['v143_event_metric'] == 'CAMERA'
            and f['v143_event_actual'] == 2
            for v in camera['by_group'].values() for f in v['frames']),
        'detections_match_v146_frozen_record': all(
            f['detected'] == f['v146_frozen_detected']
            for v in camera['by_group'].values() for f in v['frames']),
        'no_new_camera_exposure': True,
        'no_new_camera_noise_draws': True,
    }
    require(all(checks.values()), 'GATE_A_CHECK_FAILED')
    return dict(
        schema='iscat165.gate_a.1', pass_=True, status='PASS',
        truth=truth, solves=solves, renders=renders, camera=camera,
        source_chain_sha256=chain,
        render_to_solve_link='CACHE_KEY_PLUS_MATLAB_LEDGER_PLUS_GEOMETRY',
        render_to_solve_limitation=(
            'the render MAT does not embed the solve content SHA; the link rests on the '
            'v126 cache key, the preserved MATLAB operation ledger and matching geometry/material'),
        checks=checks, model_calls=0, new_bem=0, new_render=0, new_camera_exposures=0,
        scope='READ_ONLY_PROVENANCE_ONLY_NOT_A_PHYSICAL_OR_SIZING_RESULT')


def estimator_projection(gate, *, full_report_sha256):
    """Truth-free Gate A summary handed to the estimator-side preflight.

    The projection contains only booleans, file hashes and frozen detection
    labels. No scene D/h value, no scene name and no solve geometry is exposed.
    """
    require(gate['status'] == 'PASS' and gate['pass_'] is True, 'GATE_A_NOT_PASS')
    frames = {}
    for a, evidence in gate['camera']['by_group'].items():
        frames[a] = [
            dict(event_id=f['event_id'], T=f['T'], threshold=f['threshold'],
                 detected=bool(f['detected']),
                 foreground_counts_sha256=f['foreground_counts_sha256'],
                 reference_counts_sha256=f['reference_counts_sha256'],
                 score_C_sha256=f['score_C_sha256'], variance_sha256=f['variance_sha256'],
                 v143_event_state=f['v143_event_state'],
                 v143_event_metric=f['v143_event_metric'],
                 v143_event_actual=f['v143_event_actual'])
            for f in evidence['frames']]
    return dict(schema='iscat165.gate_a_estimator_projection.1', pass_=True, status='PASS',
                full_report_scope='VALIDATOR_ONLY_TRUTH_AWARE_REPORT_NOT_HANDED_TO_ESTIMATOR',
                full_report_sha256=full_report_sha256,
                camera_h5_sha256=gate['camera']['camera_h5_sha256'],
                threshold=gate['camera']['threshold'],
                threshold_file_sha256=gate['camera']['threshold_file_sha256'],
                level=gate['camera']['level'],
                source_chain_sha256=gate['source_chain_sha256'],
                by_group=frames,
                detections=gate['camera']['detections'],
                checks=gate['checks'], model_calls=0,
                new_camera_exposures=0, new_camera_noise_draws=0,
                scope='READ_ONLY_PROVENANCE_PASS_NOT_A_PHYSICAL_OR_SIZING_RESULT')
