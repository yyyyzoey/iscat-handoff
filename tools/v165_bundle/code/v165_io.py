"""Read-only V165 provenance gates, byte-safe I/O and frozen camera binding.

No optics, no estimator, no truth access in this module. Everything here is a
pure verification/format helper so that the production runner can prove its
sources before any model forward attempt is charged.
"""
from __future__ import annotations
import ast
import csv
import hashlib
import json
import math
import re
import sqlite3
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

import h5py
import numpy as np

from v152_budget_store import atomic_json, canonical

PARENT = '2558e24ced48e65d34797a4021cab659aa045566'
V164_CODE_COMMIT = 'd802b9e26d5ace14bb5055e3e1426d68b6e43c23'
V164_ZIP_SHA = '3191f1d5600dd68d464f471480472946147910c0ce0865e7d0b030a134f73dd7'
V164_ZIP_BYTES = 7121109
V164_ZIP_MEMBERS = 2722
MODEL_ID = 'v142-F2c-75860d222dd8e90d8dc2e31111e52ccbbb212a01c0d6a0dfe7fdbcdb241c98c3'
ZIP_SHA = 'abac2611ff6f0618cb73dab4323fc4e7fbd7efc1f746cf35485ab9d5ffd7eec8'
ZIP_BYTES = 27730
ZIP_MEMBERS = 16
PREFIXES = ('config',
            'results/v128/library/v128_Dh_train_fields.h5',
            'results/v143/validation/camera_pilot',
            'results/v146/camera_fits/events',
            'results/v146/source/ACTUALLY_EXECUTED_CODE/v133_recover_M.py',
            'results/v152/all_results.json',
            'results/v156',
            'results/v163',
            'tools/v164_bundle',
            'tools/v142_model.py',
            'tools/v142_field_reference.py',
            'tools/field_forward_reference.py',
            'tools/load_field_library.py',
            'tools/v133_recover_M.py',
            'tools/v146_runtime.py',
            'tools/v146_core.py',
            'tools/v146_fit_saved_camera.py')
FORBIDDEN_PUBLIC_KEYS = ('D_scene_nm', 'h_scene_nm', 'epsilon', 'D_true', 'h_true')


def require(value, message):
    if not value:
        raise ValueError(message)


def safe_path(root, rel):
    q = PurePosixPath(rel)
    require(bool(q.parts) and not q.is_absolute() and '..' not in q.parts
            and '\\' not in rel and not any(':' in part for part in q.parts),
            'UNSAFE_RELATIVE_PATH')
    root = Path(root).resolve()
    p = root.joinpath(*q.parts)
    require(root in p.resolve().parents, 'PATH_ESCAPES_ROOT')
    current = p
    while current != root:
        require(not current.is_symlink(), 'SYMLINK_PATH')
        current = current.parent
    return p


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def blob(p):
    p = Path(p)
    h = hashlib.sha1(b'blob ' + str(p.stat().st_size).encode() + b'\0')
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def array_sha(a):
    a = np.ascontiguousarray(a)
    return hashlib.sha256((str(a.shape) + '|' + str(a.dtype) + '|').encode() + a.tobytes()).hexdigest()


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True).stdout


def entries(repo):
    rows = []
    for line in git(repo, 'ls-tree', '-r', '-z', PARENT, '--', *PREFIXES).split(b'\0'):
        if not line:
            continue
        head, name = line.split(b'\t', 1)
        mode, kind, b = head.decode().split()
        rel = name.decode('utf-8')
        require(kind == 'blob' and mode in ('100644', '100755'), 'UNSUPPORTED_GIT_OBJECT')
        p = PurePosixPath(rel)
        require(not p.is_absolute() and '..' not in p.parts, 'UNSAFE_GIT_PATH')
        rows.append((rel, b))
    for prefix in PREFIXES:
        require(any(p == prefix or p.startswith(prefix + '/') for p, _ in rows),
                'MISSING_PREFIX:' + prefix)
    return rows


def lock_sources(repo):
    out = {}
    for rel, b in entries(repo):
        p = safe_path(repo, rel)
        require(p.is_file() and not p.is_symlink(), 'MISSING_OR_SYMLINK:' + rel)
        require(blob(p) == b, 'FROZEN_BYTE_MISMATCH:' + rel)
        out[rel] = dict(git_blob=b, sha256=sha(p), bytes=p.stat().st_size)
    return out


ESTIMATOR_MODULES = ('v165_objective.py', 'v152_gls_core.py', 'v152_budget_store.py',
                     'v165_task_ids.py', 'v165_io.py', 'v165_run.py')
GUARD_MODULE = 'v165_guard.py'
GUARD_DENY_TUPLES = ('DENY_DIR_PREFIXES', 'DENY_MODULE_PREFIXES', 'DENY_NAME_TOKENS')
# A full Git object id: 40 hexadecimal characters, not embedded in a longer run
# (so model ids and archive digests, which are 64 hex, are not picked up here).
GIT_SHA1_RE = re.compile(r'(?<![0-9a-fA-F])[0-9a-fA-F]{40}(?![0-9a-fA-F])')


def declared_deny_tokens(guard_path):
    """Read the protected identities out of the guard module as literal data.

    The scanner deliberately owns no protected identity of its own: any identity
    written into this estimator module would itself be the contamination the scan
    is looking for.  The guard is the single designated identity holder, so the
    deny list is parsed from its module-level literal tuples with no code
    execution and no import.
    """
    tree = ast.parse(Path(guard_path).read_text(encoding='utf-8'), filename=str(guard_path))
    found = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id in GUARD_DENY_TUPLES:
            found[target.id] = node.value
    missing = [name for name in GUARD_DENY_TUPLES if name not in found]
    require(not missing, 'GUARD_DENY_TUPLE_MISSING:' + ','.join(missing))
    tokens = []
    for name in GUARD_DENY_TUPLES:
        try:
            value = ast.literal_eval(found[name])
        except Exception:
            raise ValueError('GUARD_DENY_TUPLE_NOT_A_LITERAL:' + name)
        require(isinstance(value, tuple) and bool(value), 'GUARD_DENY_TUPLE_EMPTY:' + name)
        require(all(isinstance(item, str) and item for item in value),
                'GUARD_DENY_TUPLE_MEMBER_INVALID:' + name)
        tokens.extend(item.lower() for item in value)
    require(len(set(tokens)) == len(tokens), 'GUARD_DENY_TUPLE_DUPLICATE_TOKEN')
    return tuple(tokens)


def git_object_type(repo, sha1):
    """Return the Git object type for a full object id, or ``ABSENT``."""
    try:
        return git(repo, 'cat-file', '-t', sha1).decode('ascii').strip()
    except subprocess.CalledProcessError:
        return 'ABSENT'


def assert_no_truth_literals(code_dir):
    """Auditor static scan: the estimator stack must not name truth identities.

    Two identity-free rules replace the old hand-maintained block list:

    1. Every 40-hex object id written in an estimator module must resolve, in this
       repository, to a Git *commit*.  A truth-bearing file is a *blob*, so the
       identity of the truth file is refused here without this module ever having
       to name it.  An id that resolves to nothing is refused as well.
    2. Protected path/module/name identities are read from the guard module and may
       not appear in an estimator module, in any letter case.

    ``v165_guard.py`` stays outside the scanned list: it is the designated holder of
    the deny list (paths and module names only, never a truth value and never a
    truth-file hash, which rule 1 also forbids inside it).  Its hash is recorded so
    the exclusion is auditable rather than silent.

    This is a literal scan of the execution code only. It cannot prove runtime
    isolation; the binding proof is the sealed-estimate ordering recorded in
    seal.json plus the absence of truth keys in estimator inputs.
    """
    code_dir = Path(code_dir)
    repo = code_dir.resolve().parents[2]
    require((repo / '.git').exists(), 'GUARD_SCAN_REPOSITORY_MISSING')
    guard = code_dir / GUARD_MODULE
    require(guard.is_file(), 'MISSING_RUNTIME_GUARD_MODULE')
    tokens = declared_deny_tokens(guard)
    hits = []
    scanned = {}
    sha1_types = {}
    for name in ESTIMATOR_MODULES:
        p = code_dir / name
        require(p.is_file(), 'MISSING_ESTIMATOR_MODULE:' + name)
        raw = p.read_text(encoding='utf-8')
        scanned[name] = sha(p)
        lowered = raw.lower()
        named = [token for token in tokens if token in lowered]
        if named:
            hits.append(name + ':protected_identity:' + ','.join(named))
        bad = {}
        for token in GIT_SHA1_RE.findall(raw):
            kind = sha1_types.setdefault(token, git_object_type(repo, token))
            if kind != 'commit':
                bad[token] = kind
        if bad:
            hits.append(name + ':non_commit_sha1:' + ','.join(
                token + '=' + bad[token] for token in sorted(bad)))
    require(not hits, 'TRUTH_LITERAL_IN_ESTIMATOR_CODE:' + ';'.join(hits))
    guard_raw = guard.read_text(encoding='utf-8')
    guard_sha1 = GIT_SHA1_RE.findall(guard_raw)
    require(not guard_sha1, 'RUNTIME_GUARD_HOLDS_AN_OBJECT_IDENTITY')
    return dict(scope='STATIC_RULE_BASED_SCAN_NOT_A_SANDBOX',
                protected_identity_source=GUARD_MODULE + ':' + ','.join(GUARD_DENY_TUPLES),
                protected_token_count=len(tokens),
                rule_non_commit_sha1_refused=True,
                git_object_types_by_sha1=sha1_types,
                scanned_modules=scanned, scanned_module_count=len(scanned),
                excluded_guard_module=GUARD_MODULE, guard_module_sha256=sha(guard),
                offenders=hits, estimator_imports_truth_default_to_none=True,
                model_calls=0)


def estimator_inputs_check(docs):
    """Refuse to hand the estimator any input document holding truth-valued keys."""
    problems = []

    def visit(value, path):
        if isinstance(value, dict):
            for key, child in value.items():
                if str(key) in FORBIDDEN_PUBLIC_KEYS:
                    problems.append(path + '.' + str(key))
                visit(child, path + '.' + str(key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, path + f'[{index}]')

    for label, doc in docs.items():
        visit(doc, label)
    require(not problems, 'TRUTH_KEY_IN_ESTIMATOR_INPUT:' + ';'.join(problems))
    return dict(scope='KEY_SCAN_OF_ESTIMATOR_INPUTS_ANONYMOUS_READINGS_ONLY',
                inputs=sorted(docs), offenders=problems, model_calls=0)


def install_check(bundle):
    """Every frozen ZIP member installed byte-for-byte; extra code files listed."""
    bundle = Path(bundle)
    rows = list(csv.DictReader((bundle / 'manifest_sha256.csv').read_text(encoding='utf-8-sig').splitlines()))
    require(len(rows) == ZIP_MEMBERS - 1, 'MANIFEST_ROW_COUNT')
    require(len({r['path'] for r in rows}) == len(rows), 'DUPLICATE_MANIFEST_ROW')
    frozen = {}
    for r in rows:
        p = safe_path(bundle, r['path'])
        require(p.is_file(), 'FROZEN_MEMBER_MISSING:' + r['path'])
        raw = p.read_bytes()
        require(len(raw) == int(r['bytes']) and hashlib.sha256(raw).hexdigest() == r['sha256'],
                'FROZEN_MEMBER_CHANGED:' + r['path'])
        frozen[r['path']] = r['sha256']
    extra = []
    for p in sorted(bundle.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(bundle).as_posix()
        if rel in frozen or rel == 'manifest_sha256.csv':
            continue
        if '.pytest_cache' in rel or '__pycache__' in rel or rel.endswith('.pyc'):
            continue
        extra.append(rel)
    return dict(scope='FROZEN_ZIP_MEMBERS_BYTE_IDENTICAL_PLUS_WORKSTATION_CODE',
                frozen_members=len(frozen), manifest_sha256=sha(bundle / 'manifest_sha256.csv'),
                workstation_code_files=sorted(extra), model_calls=0)


def public_readings_check(doc):
    from v165_task_ids import tasks

    require(isinstance(doc, dict), 'HEIGHT_READING_DOCUMENT_OBJECT')
    rows = doc.get('readings')
    require(isinstance(rows, list) and len(rows) == 24, 'HEIGHT_READINGS_MUST_BE_24')
    require(doc.get('seed') == 16520261027, 'HEIGHT_GENERATOR_SEED_CHANGED')
    require(doc.get('no_camera_noise_draw') is True, 'CAMERA_NOISE_DRAW_FORBIDDEN')
    require(doc.get('no_new_camera_exposures') is True, 'CAMERA_EXPOSURE_FORBIDDEN')
    require(doc.get('no_experimental_height_observation') is True,
            'HYPOTHETICAL_HEIGHT_BOUNDARY_CHANGED')
    expected_ids = {
        row['task_id'] for row in tasks() if row['sigma_nm'] is not None
    }
    seen = set()
    groups = set()
    for r in rows:
        require(isinstance(r, dict), 'READING_MUST_BE_OBJECT')
        required = {
            'reading_id', 'group', 'B', 'replicate', 'sigma_nm', 'z_nm',
            'hypothetical', 'independent_camera_noise_assumption', 'generation'
        }
        require(required.issubset(r), 'READING_REQUIRED_FIELDS')
        rid = r.get('reading_id')
        require(isinstance(rid, str) and rid, 'READING_ID')
        require(rid not in seen, 'DUPLICATE_READING_ID')
        seen.add(rid)
        group = r.get('group')
        require(group in ('ANON_01', 'ANON_02', 'ANON_03', 'ANON_04'),
                'READING_GROUP')
        groups.add(group)
        require(type(r.get('B')) is int and r['B'] == 100000, 'READING_BACKGROUND')
        require(type(r.get('replicate')) is int and r['replicate'] in (0, 1, 2),
                'READING_REPLICATE')
        sigma = r.get('sigma_nm')
        require(type(sigma) in (int, float) and math.isfinite(float(sigma))
                and float(sigma) in (1.0, 10.0), 'READING_SIGMA')
        z = r.get('z_nm')
        require(type(z) in (int, float) and math.isfinite(float(z)), 'READING_Z_NM')
        require(r.get('hypothetical') is True, 'READING_MUST_BE_HYPOTHETICAL')
        require(r.get('independent_camera_noise_assumption') is True,
                'READING_CAMERA_INDEPENDENCE')
        require(r.get('generation') == 'GAUSSIAN_HEIGHT_NOISE_ONLY_NO_NEW_CAMERA_FRAMES',
                'READING_GENERATION_MODE')
        for key in FORBIDDEN_PUBLIC_KEYS:
            require(key not in r, 'TRUTH_LEAK_IN_PUBLIC_READINGS:' + key)
        require(rid == f"B100000_{group}_H{int(sigma)}_R{r['replicate']:02d}",
                'READING_ID_TASK_GRID')
    groups = sorted(groups)
    require(groups == ['ANON_01', 'ANON_02', 'ANON_03', 'ANON_04'], 'READING_GROUPS')
    require(seen == expected_ids, 'READING_ID_SET_DIFFERS_FROM_FROZEN_TASKS')
    counts = {}
    for r in rows:
        key = (r['group'], float(r['sigma_nm']))
        counts[key] = counts.get(key, 0) + 1
    require(all(v == 3 for v in counts.values()) and len(counts) == 8, 'SIGMA_REP_GRID')
    return dict(readings=len(rows), groups=4, per_sigma=3, truth_free=True,
                scope='OPENED_DEVELOPMENT_SIMULATED_READINGS')


def camera_binding(repo, cfg):
    """Prove V143 camera arrays -> V163 frozen frames -> frozen detection labels."""
    repo = Path(repo)
    camera = repo / cfg['inputs']['camera_h5']
    require(sha(camera) == cfg['frozen']['camera_h5_sha256'], 'CAMERA_ARRAY_FILE_CHANGED')
    replay_code = repo / 'tools/v145_camera_replay.py'
    require(sha(replay_code) == cfg['frozen']['camera_replay_code_sha256'], 'CAMERA_REPLAY_CODE_CHANGED')
    threshold_root = repo / cfg['inputs']['camera_root']
    level = int(cfg['camera_fit']['levels'][-1])
    require(level == 100000, 'FROZEN_LEVEL_MUST_BE_100000')
    read_noise = float(cfg['camera_fit']['read_noise_e'])
    frozen = read(threshold_root / f'B{level}_dev_frozen_threshold.json')
    require(frozen['B'] == level and frozen['not_tuned_using_independent_val'] is True, 'THRESHOLD_NOT_FROZEN')
    threshold = float(frozen['threshold'])
    groups = cfg['N_cases']
    require(list(groups) == ['ANON_01', 'ANON_02', 'ANON_03', 'ANON_04'], 'FROZEN_GROUP_LIST')
    binding = {}
    with h5py.File(camera, 'r') as h:
        base = f'B{level}/target'
        require(base in h and len(h[base]) == 12, 'EXPECTED_12_TARGETS_PER_B')
        expected_labels = [f'{g}_{i:02d}' for g in groups for i in range(3)]
        require(sorted(h[base].keys()) == sorted(expected_labels), 'CAMERA_TARGET_LABEL_SET')
        for g in groups:
            d = read(repo / f'results/v163/source_context/v156/{level}_{g}.json')['diagnostic']
            Y = np.asarray(d['frame_Y'], float)
            V = np.asarray(d['frame_V'], float)
            require(Y.shape == (3, 13, 13) and V.shape == Y.shape, 'CONTEXT_FRAME_SHAPE')
            events = []
            for i in range(3):
                label = f'{g}_{i:02d}'
                require(label in h[base], 'MISSING_CAMERA_EVENT:' + label)
                grp = h[f'{base}/{label}']
                f = np.asarray(grp['foreground_counts'][()], float)
                r = np.asarray(grp['reference_counts'][()], float)
                require(f.shape == (17, 17) and r.shape == f.shape, 'CAMERA_COUNT_SHAPE')
                full_c, full_v = ratio_contrast_and_variance(f, r, read_noise)
                require(np.array_equal(np.asarray(full_c, float), np.asarray(grp['C'][()], float)),
                        'CAMERA_C_REPLAY_FAILED:' + label)
                C = score_crop(full_c)
                Vc = score_crop(full_v)
                require(np.array_equal(C, np.asarray(grp['C'][()], float)[2:15, 2:15]),
                        'CAMERA_C_REPLAY_FAILED')
                require(array_sha(Y[i]) == array_sha(C), 'FRAME_Y_NOT_BOUND_TO_CAMERA:' + label)
                require(array_sha(V[i]) == array_sha(Vc), 'FRAME_V_NOT_BOUND_TO_CAMERA:' + label)
                T = float(np.max(np.abs(C)))
                require(abs(float(grp.attrs['T']) - T) <= 1e-12, 'CAMERA_T_REPLAY_FAILED')
                events.append(dict(event_id=f'B{level}_{label}', T=T, threshold=threshold,
                                   detected=bool(T > threshold),
                                   observation_sha256=array_sha(C), variance_sha256=array_sha(Vc)))
            binding[g] = events
    detections = {g: [e['detected'] for e in binding[g]] for g in groups}
    require(set(detections) == {'ANON_01', 'ANON_02', 'ANON_03', 'ANON_04'}, 'DETECTION_GROUPS')
    return dict(level=level, read_noise_e=read_noise, threshold=threshold,
                threshold_file_sha256=sha(threshold_root / f'B{level}_dev_frozen_threshold.json'),
                by_group={g: [dict(event_id=e['event_id'], T=e['T'], detected=e['detected'],
                                   observation_sha256=e['observation_sha256'],
                                   variance_sha256=e['variance_sha256']) for e in binding[g]] for g in groups},
                detections=detections, model_calls=0,
                scope='FROZEN_THRESHOLD_APPLIED_TO_PINNED_CAMERA_EVENTS')


def ratio_contrast_and_variance(foreground, reference, read_noise=2.):
    """Frozen plug-in delta-method contrast/variance.

    Deliberately the same arithmetic as tools/v146_core.ratio_contrast_and_variance
    (the frozen ancestor used to build the saved camera arrays): no clipping,
    nonpositive references raise instead of being repaired, and this is not a
    Poisson-Gaussian likelihood. Reproduction is checked in the test suite
    against the frozen ancestor module itself.
    """
    f = np.asarray(foreground, float)
    r = np.asarray(reference, float)
    require(f.shape == r.shape and f.shape in ((17, 17), (13, 13)), 'CAMERA_SHAPE_OR_NONFINITE')
    require(np.isfinite(f).all() and np.isfinite(r).all(), 'CAMERA_SHAPE_OR_NONFINITE')
    require(np.isfinite(read_noise) and read_noise >= 0 and not np.any(f < 0) and not np.any(r <= 0),
            'CAMERA_NONPOSITIVE_COUNTS_NO_CLIP')
    v = (f + read_noise ** 2) / (r * r) + (f * f) * (r + read_noise ** 2) / (r ** 4)
    c = (f - r) / r
    require(np.isfinite(v).all() and not np.any(v <= 0), 'INVALID_VARIANCE')
    return c, v


def score_crop(a):
    a = np.asarray(a, float)
    if a.shape == (17, 17):
        return a[2:15, 2:15].copy()
    if a.shape == (13, 13):
        return a.copy()
    raise ValueError('NOT_17_OR_13_CAMERA_ARRAY')


def legal_records(repo, groups):
    """Read V152's existing six legal complete starts per group; never re-run them."""
    per_group = {}
    for g in groups:
        rows = []
        for p in sorted((repo / 'results/v163/rescored').glob(f'100000_{g}_*.json')):
            d = read(p)
            require(d['B'] == 100000 and d['anon'] == g, 'RESCORED_IDENTITY')
            require(d['model_id'] == MODEL_ID, 'RESCORED_MODEL_ID')
            require(d['source_commit'] == '6d2db46d52509bd6987726dea211781cfa1b4127', 'RESCORED_SOURCE_COMMIT')
            require(d['source_path'] == 'results/v152/all_results.json', 'RESCORED_SOURCE_PATH')
            require(len(d['theta']) == 4 and all(np.isfinite(d['theta'])), 'RESCORED_THETA')
            require(np.asarray(d['C'], float).shape == (13, 13), 'RESCORED_ARRAY')
            rows.append(dict(d, record_path=p.relative_to(repo).as_posix()))
        require(len(rows) == 6, f'EXPECTED_SIX_LEGAL_STARTS:{g}:{len(rows)}')
        require(len({r['source_record_id'] for r in rows}) == 6, 'DUPLICATE_START_IDENTITY')
        require(len({r['observation_identity'] for r in rows}) == 1, 'START_OBSERVATION_MISMATCH')
        require(len({r['variance_identity'] for r in rows}) == 1, 'START_VARIANCE_MISMATCH')
        require(len({tuple(r['ordered_event_ids']) for r in rows}) == 1, 'START_EVENT_MISMATCH')
        per_group[g] = rows
    return per_group


def frozen_starts(repo, groups):
    """Two common public starts per group, from frozen legal history only.

    First start: lowest frozen Q_joint. Second start: lowest frozen Q_joint among
    the remaining five with |h - h_first| >= 20 nm; if no such stratum exists the
    second-lowest Q is used and NO_HEIGHT_STRATUM_AVAILABLE is recorded.
    """
    legal = legal_records(repo, groups)
    per_group = {}
    for g in groups:
        rows = sorted(legal[g], key=lambda r: (r['Q_joint'], r['start_index']))
        first = rows[0]
        rest = [r for r in rows[1:] if abs(r['theta'][1] - first['theta'][1]) >= 20.0]
        stratum = True
        if not rest:
            rest = rows[1:]
            stratum = False
        second = sorted(rest, key=lambda r: (r['Q_joint'], r['start_index']))[0]
        flag = None if stratum else 'NO_HEIGHT_STRATUM_AVAILABLE'
        per_group[g] = dict(first=first, second=second, stratum_available=stratum,
                            stratum_flag=flag, all_six=[r['start_index'] for r in rows],
                            six=legal[g])
    return per_group


def ledger_check(folder, *, plan_id, phases, expected_total=None, tasks_subdir='tasks',
                 hash_only_arrays_tasks=()):
    """Read-only ledger audit. Attempts of ``hash_only_arrays_tasks`` may carry the
    recorded C_sha256 without a persisted prediction array (the V164 loader did
    exactly that); such attempts are counted and reported, never silently excused.
    """
    folder = Path(folder)
    p = folder / 'logs' / f'{plan_id}_budget.sqlite'
    con = sqlite3.connect(p.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        require(con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'SQLITE_INTEGRITY')
        require(not any(Path(str(p) + s).exists() for s in ('-wal', '-journal')), 'LIVE_WAL_OR_JOURNAL')
        meta = json.loads(con.execute('SELECT value FROM metadata WHERE id=1').fetchone()[0])
        require(meta['plan_id'] == plan_id and meta['phases'] == phases, 'LEDGER_PLAN')
        tasks = con.execute('SELECT id,signature,phase,cap,used,state,result_path,result_sha FROM tasks').fetchall()
        rows = []
        for task, sig, phase, cap, used, state, result_path, digest in tasks:
            require(state in ('FINISHED', 'PARTIAL_BUDGET', 'FAILED'), 'UNSEALED_TASK:' + task)
            require(0 <= used <= cap and phase in phases, 'OVER_BUDGET_OR_UNKNOWN_PHASE:' + task)
            result = folder / tasks_subdir / task / 'result.json'
            require(result.is_file() and sha(result) == digest, 'TASK_SEAL_CHANGED:' + task)
            doc = read(result)
            require(doc['signature'] == sig and doc['actual_calls'] == used, 'TASK_SIGNATURE_OR_COUNT')
            calls = con.execute('SELECT seq,theta,state,detail FROM attempts WHERE task=? ORDER BY seq',
                                (task,)).fetchall()
            require(len(calls) == used, 'TASK_COUNT_MISMATCH:' + task)
            errors = 0
            hash_only = 0
            for seq, theta, st, detail in calls:
                require(st in ('RETURNED', 'MODEL_ERROR'), 'UNKNOWN_OR_UNSEALED_CALL:' + task)
                det = json.loads(detail)
                if st == 'MODEL_ERROR':
                    errors += 1
                    require('error' in det, 'MODEL_ERROR_WITHOUT_DETAIL:' + task)
                    continue
                require('C_sha256' in det, 'ATTEMPT_WITHOUT_RECORDED_C_HASH:' + task)
                pred = folder / tasks_subdir / task / 'predictions' / f'{seq:04d}.json'
                if not pred.is_file():
                    require(task in hash_only_arrays_tasks, 'MISSING_PREDICTION:' + task)
                    hash_only += 1
                    continue
                pd = read(pred)
                require(np.array_equal(np.asarray(pd['theta'], float), np.asarray(json.loads(theta), float)),
                        'PREDICTION_THETA')
                c = np.ascontiguousarray(pd['C'], dtype=np.float64)
                require(c.shape == (13, 13) and np.isfinite(c).all(), 'PREDICTION_ARRAY')
                require(hashlib.sha256(c.tobytes()).hexdigest() == det['C_sha256'],
                        'PREDICTION_HASH')
            rows.append(dict(task=task, phase=phase, cap=cap, used=used, state=state,
                             model_errors=errors, attempts_without_persisted_array=hash_only))
        for phase, limit in phases.items():
            require(sum(r['cap'] for r in rows if r['phase'] == phase) <= limit, 'PHASE_RESERVATION')
        total = sum(r['used'] for r in rows)
        require(sum(r['cap'] for r in rows) <= meta['total'], 'GLOBAL_RESERVATION')
        require(con.execute('SELECT COUNT(*) FROM attempts').fetchone()[0] == total, 'ORPHAN_ATTEMPTS')
        require(con.execute('SELECT COUNT(*) FROM attempts WHERE state=?', ('CHARGED',)).fetchone()[0] == 0,
                'UNFINALIZED_CHARGED_ATTEMPT')
        if expected_total is not None:
            require(total == expected_total, 'UNEXPECTED_TOTAL')
        return dict(meta=meta, tasks=rows, total_used=total, model_error_calls=sum(r['model_errors'] for r in rows),
                    attempts_without_persisted_array=sum(r['attempts_without_persisted_array'] for r in rows),
                    scope='READONLY_STORED_EVIDENCE_NOT_NEW_MODEL_REPLAY')
    finally:
        con.close()


def archive_check(path):
    path = Path(path)
    require(path.is_file(), 'ARCHIVE_MISSING')
    require(path.stat().st_size == V164_ZIP_BYTES, 'V164_ARCHIVE_BYTE_COUNT_CHANGED')
    require(sha(path) == V164_ZIP_SHA, 'V164_ARCHIVE_SHA256_CHANGED')
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        require(len(names) == V164_ZIP_MEMBERS, 'V164_ARCHIVE_MEMBER_COUNT_CHANGED')
        require(len(names) == len(set(names)), 'DUPLICATE_ZIP_MEMBERS')
        require(z.testzip() is None, 'ZIP_CRC_FAILED')
        for n in names:
            p = PurePosixPath(n)
            require(not p.is_absolute() and '..' not in p.parts and '\\' not in n, 'UNSAFE_ZIP_PATH')
        rows = list(csv.DictReader(z.read('manifest_sha256.csv').decode('utf-8-sig').splitlines()))
        require(len(rows) == len({r['path'] for r in rows}), 'DUPLICATE_MANIFEST_ROWS')
        require(set(names) == {'manifest_sha256.csv'} | {r['path'] for r in rows},
                'ZIP_MEMBER_SET_MISMATCH')
        for r in rows:
            raw = z.read(r['path'])
            require(len(raw) == int(r['bytes']) and hashlib.sha256(raw).hexdigest() == r['sha256'],
                    'MANIFEST_MISMATCH:' + r['path'])
    return dict(bytes=path.stat().st_size, sha256=sha(path), members=len(names),
                manifest_rows=len(rows), crc_ok=True)


def write_detections(out, binding):
    atomic_json(out / 'frozen_detections.json', binding['detections'])
    return binding['detections']
