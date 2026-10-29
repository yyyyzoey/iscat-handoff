"""V168 read-only legacy audit and continuation policy.

No optical model imports, no ledger creation/reservation, no old-ledger writes.
This is a controller-side integration component, not a production F2c runner.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sqlite3
from typing import Any

CONFIG = Path(__file__).resolve().parents[1] / 'config/v168_authorization.json'
OLD_SHA = '212fc61391070cc0d8f07e41d1a356f31d76a4aed713bfc8c0e0031ef1d1eb34'
PARENT = 'ab0cfeb7c34c8019143498965b5ef8e6ca3843d8'
F2 = 'v131-field-db000d86636ed018cf1f9bd5291c7409b7e9d2aaa481328b3c22dfdb1a689427'
F2C = 'v142-F2c-75860d222dd8e90d8dc2e31111e52ccbbb212a01c0d6a0dfe7fdbcdb241c98c3'
PHASES = {'MODEL_BINDING': 199, 'SEARCH_EXTENSION': 2000,
          'BIAS_STRESS': 7200, 'FINAL_VERIFY': 600}
OLD_PHASES = dict(PHASES, MODEL_BINDING=200)


class RecoveryRefused(ValueError):
    """A source or authorization failure; downstream execution must stop."""


def require(ok: Any, code: str) -> None:
    if not ok:
        raise RecoveryRefused(code)


def canonical(doc: Any) -> bytes:
    return (json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                       allow_nan=False) + '\n').encode('utf-8')


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda: f.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def load_authorization(path: Path = CONFIG) -> dict:
    doc = json.loads(Path(path).read_text(encoding='utf-8'))
    validate_authorization(doc)
    return doc


def validate_authorization(doc: dict) -> None:
    require(doc.get('plan_id') == 'v168', 'WRONG_PLAN_ID')
    require(doc.get('parent_commit') == PARENT, 'WRONG_FIXED_PARENT')
    require(doc.get('historical_consumed_attempts') == 1, 'HISTORICAL_CHARGE_MUST_STAY_ONE')
    require(doc.get('combined_attempt_ceiling') == 10000, 'COMBINED_CEILING_CHANGED')
    require(doc.get('new_attempt_ceiling') == 9999, 'NEW_ALLOWANCE_IS_9999_NOT_10000')
    require(doc.get('phases') == PHASES, 'PHASE_AUTHORITY_CHANGED')
    require(sum(doc['phases'].values()) + 1 == 10000, 'BUDGET_SUM')
    require(doc.get('fixed_task_caps') == {
        'loader': 100, 'binding': 99, 'recovery_count': 5, 'recovery_each': 400,
        'bias_count': 18, 'bias_each': 400, 'final_verify': 600}, 'TASK_CAPS_CHANGED')
    require(doc.get('allowed_new_constructions') == 1, 'CONSTRUCTION_AUTHORITY_CHANGED')
    old = doc.get('prior_round_ledger', {})
    require(old.get('sha256') == OLD_SHA and old.get('attempts') == 1
            and old.get('mutation_allowed') is False, 'OLD_LEDGER_PIN_CHANGED')
    require(doc.get('source_guard', {}).get('model_id') == F2C, 'F2C_ID_CHANGED')
    require(doc.get('source_guard', {}).get('parent_model_id') == F2, 'F2_PARENT_ID_CHANGED')
    require(doc.get('old_ledger_must_remain_byte_identical') is True, 'OLD_LEDGER_MUTATION')
    require(doc.get('no_automatic_retry_after_new_charge') is True, 'SILENT_RETRY_FORBIDDEN')
    for key in ('new_BEM', 'new_render', 'new_camera_exposures', 'new_camera_noise_draws',
                'new_height_random_draws', 'new_fixed_D_scans', 'new_Jacobian_batch', 'new_second_focus'):
        require(type(doc.get(key)) is int and doc[key] == 0, 'FORBIDDEN_COMPUTE:' + key)
    require(doc.get('recovery_tasks') == [
        'B100000_ANON_01_H10_R00', 'B100000_ANON_01_H10_R01',
        'B100000_ANON_01_H1_R00', 'B100000_ANON_01_H1_R01', 'B100000_ANON_01_H1_R02'],
        'RECOVERY_GRID_CHANGED')
    require(doc.get('recovery_source_start') == 1, 'WRONG_OLD_START_INDEX')
    require(doc.get('bias_groups') == ['ANON_02', 'ANON_03', 'ANON_04']
            and doc.get('replicates') == [0, 1, 2]
            and doc.get('bias_nm') == [-2.0, 2.0]
            and doc.get('bias_sigma_nm') == 1.0, 'BIAS_GRID_CHANGED')
    require(doc.get('optimizer') == {
        'method': 'trf', 'jac': '3-point', 'loss': 'linear', 'diff_step': 1e-5,
        'x_scale': [50, 50, 280, 280], 'ftol': 1e-9, 'xtol': 1e-9,
        'gtol': 1e-8, 'max_nfev': 200}, 'OPTIMIZER_CHANGED')
    require(doc.get('domain') == {'lower': [30, 350, -500, -500],
            'upper': [200, 550, 500, 500], 'min_surface_gap_nm': 100}, 'DOMAIN_CHANGED')
    require(doc.get('reportable_D') is None and
            doc.get('EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED') is False,
            'REPORTABILITY_NOT_GRANTED')


def _read_legacy(path: Path, expected_sha: str) -> dict:
    """Internal reader; a fixture SHA is used only by unit tests.

    The production public function below fixes the expected SHA, without a CLI
    option that could silently accept changed historical evidence.
    """
    source = Path(path)
    require(not source.is_symlink(), 'INVALID_LEDGER_PATH')
    path = source.resolve(strict=True)
    require(path.is_file(), 'INVALID_LEDGER_PATH')
    before = file_sha(path)
    require(before == expected_sha, 'OLD_LEDGER_SHA_MISMATCH')
    for suffix in ('-wal', '-journal', '-shm'):
        require(not Path(str(path) + suffix).exists(), 'LEDGER_SIDECAR_REQUIRES_FORENSICS:' + suffix)
    con = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    try:
        con.execute('PRAGMA query_only=ON')
        require(con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'SQLITE_INTEGRITY')
        tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        require({'metadata', 'tasks', 'attempts'}.issubset(tables),
                'MISSING_ATTEMPTS_SCHEMA_NEVER_DEFAULT_TO_ZERO')
        meta_rows = con.execute('SELECT id,value FROM metadata').fetchall()
        require(len(meta_rows) == 1 and meta_rows[0]['id'] == 1, 'METADATA_ROWS')
        meta = json.loads(meta_rows[0]['value'])
        require(meta == {'plan_id': 'v167', 'total': 10000, 'phases': OLD_PHASES}, 'OLD_PLAN_CHANGED')
        tasks = [dict(r) for r in con.execute('SELECT * FROM tasks ORDER BY id')]
        attempts = [dict(r) for r in con.execute('SELECT * FROM attempts ORDER BY task,seq')]
        require(len(tasks) == 26, 'OLD_TASK_COUNT')
        require(len({r['id'] for r in tasks}) == 26, 'DUPLICATE_TASKS')
        require(all(r['state'] == 'RUNNING' for r in tasks), 'OLD_STATES_CHANGED')
        require(sum(r['used'] for r in tasks) == 1 and len(attempts) == 1, 'OLD_ATTEMPT_COUNT_CHANGED')
        require(all(0 <= r['used'] <= r['cap'] for r in tasks), 'OLD_TASK_BUDGET')
        require(all(r['phase'] in OLD_PHASES for r in tasks), 'UNKNOWN_OLD_PHASE')
        caps = {p: sum(r['cap'] for r in tasks if r['phase'] == p) for p in OLD_PHASES}
        require(caps == OLD_PHASES, 'OLD_RESERVATIONS_CHANGED')
        row = attempts[0]
        require(row['task'] == 'V167_LOADER_1' and row['seq'] == 1 and row['state'] == 'CHARGED',
                'OLD_STRANDED_ATTEMPT_CHANGED')
        require(json.loads(row['theta']) == [30.0, 350.0, 0.0, 0.0], 'OLD_THETA_CHANGED')
        detail = json.loads(row['detail'])
        require(detail.get('kind') == 'MODEL_LOADER' and detail.get('invocation') == 'charged_model_forward',
                'OLD_ATTEMPT_KIND')
        require(detail.get('task_id') == row['task'] and detail.get('ledger_seq') == row['seq']
                and detail.get('requested_theta') == json.loads(row['theta']), 'OLD_CHARGE_BINDING')
        used_by_task = {r['id']: r['used'] for r in tasks}
        require(used_by_task.get(row['task']) == 1 and
                all(v == 0 for k, v in used_by_task.items() if k != row['task']), 'OLD_USED_DISTRIBUTION')
        result = dict(schema='iscat168.legacy_readonly_audit.1', old_ledger_sha256=before,
                      old_ledger_bytes=path.stat().st_size, table_names=sorted(tables),
                      native_integrity_check='ok', old_plan=meta, old_tasks=len(tasks),
                      old_attempts=len(attempts), old_used=1, attempts=attempts,
                      historical_unsettled_charge_count=1, old_reservations=caps,
                      historical_task_states={'RUNNING': 26},
                      scope='OLD_SNAPSHOT_ONLY_NO_MODEL_CALLS_NO_MUTATION',
                      old_attempt_settled_by_this_tool=False, refunded_calls=0,
                      new_model_calls=0, preserved_unsettled_state=True)
    finally:
        con.close()
    require(file_sha(path) == before, 'OLD_LEDGER_CHANGED_DURING_AUDIT')
    return result


def audit_legacy_ledger(path: Path) -> dict:
    return _read_legacy(path, OLD_SHA)


def check_returned_model_id(kind: str, returned_model_id: Any) -> None:
    """Strict production identity dispatch: legacy F2 self-check != F2c fit."""
    if kind == 'MODEL_LOADER':
        expected = F2
    elif kind in {'SOURCE_BINDING', 'OPTIMIZER', 'INDEPENDENT_FINAL'}:
        expected = F2C
    else:
        raise RecoveryRefused('UNKNOWN_FORWARD_KIND:' + str(kind))
    require(isinstance(returned_model_id, str) and returned_model_id == expected,
            'RETURNED_MODEL_ID_MISMATCH:' + kind)


def check_constructed_parent(candidate_model_id: str, candidate_parent_id: str,
                             observed_loader_ids: list[str]) -> None:
    require(candidate_model_id == F2C, 'CONSTRUCTED_F2C_ID')
    require(candidate_parent_id == F2, 'CONSTRUCTED_PARENT_ID')
    require(len(observed_loader_ids) > 0 and set(observed_loader_ids) == {F2},
            'LOADER_PARENT_LINK_INCOMPLETE')


def combined_budget_report(new_used_by_phase: dict[str, int]) -> dict:
    require(set(new_used_by_phase) == set(PHASES), 'NEW_PHASE_KEYS')
    for phase, count in new_used_by_phase.items():
        require(type(count) is int and 0 <= count <= PHASES[phase], 'NEW_PHASE_OVER_CAP:' + phase)
    new_total = sum(new_used_by_phase.values())
    require(new_total <= 9999, 'NEW_TOTAL_OVER_CAP')
    return {'historical_v167_consumed': 1, 'historical_unsettled': 1,
            'new_v168_used': new_total, 'combined_consumed': 1 + new_total,
            'combined_remaining': 10000 - 1 - new_total,
            'phases_new': dict(new_used_by_phase), 'old_budget_refunded': 0,
            'new_attempts_are_not_old_ledger_rows': True}


def capsule_digest(executed_files_sha256: dict[str, str], plan: dict,
                   payloads_sha256: dict[str, str], test_receipt_sha256: str) -> str:
    """Stable execution identity, not a mutable branch HEAD or output directory hash."""
    require(bool(executed_files_sha256) and bool(payloads_sha256), 'EMPTY_EXECUTION_BINDING')
    all_hashes = list(executed_files_sha256.values()) + list(payloads_sha256.values()) + [test_receipt_sha256]
    require(all(isinstance(x, str) and len(x) == 64 and all(c in '0123456789abcdef' for c in x)
                for x in all_hashes), 'INVALID_SHA256')
    return digest(canonical({'schema': 'iscat168.execution_capsule.1',
                             'executed_files': executed_files_sha256,
                             'plan': plan, 'payloads': payloads_sha256,
                             'test_receipt_sha256': test_receipt_sha256}))


def require_frozen_capsule(pinned_digest: str, current_digest: str) -> None:
    require(pinned_digest == current_digest, 'CODE_OR_INPUT_CHANGED_BEFORE_RESERVE_NO_MODEL_AUTHORITY')


def require_budget_boundary(charged_this_start: int, cap: int, *, cache_verified: bool) -> None:
    require(type(charged_this_start) is int and type(cap) is int and 0 <= charged_this_start <= cap,
            'INVALID_REAL_CHARGE_COUNTER')
    require(type(cache_verified) is bool, 'CACHE_VERIFICATION_FLAG')
    if not cache_verified:
        require(charged_this_start < cap, 'PER_START_REAL_CALL_CAP')


def old_charge_reconciliation(audit: dict, authorization: dict) -> dict:
    validate_authorization(authorization)
    require(audit.get('old_ledger_sha256') == OLD_SHA and audit.get('old_used') == 1
            and audit.get('old_attempts') == 1, 'MISSING_FROZEN_OLD_AUDIT')
    return {'schema': 'iscat168.continuation_link.1', 'old_snapshot': audit['old_ledger_sha256'],
            'old_state_kept': 'CHARGED', 'external_classification': 'POST_RETURN_VALIDATION_REFUSAL_RECORDED_IN_V167_TRACE',
            'old_charge_carried': 1, 'new_authority': 9999, 'combined_ceiling': 10000,
            'note': 'No RETURNED status or missing prediction is invented; original DB stays unchanged.'}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--old-ledger', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    auth = load_authorization()
    report = audit_legacy_ledger(args.old_ledger)
    out = args.out.resolve()
    old = args.old_ledger.resolve()
    require(out != old and old.parent.parent not in out.parents, 'OUTPUT_INSIDE_OLD_EVIDENCE_FORBIDDEN')
    require(not out.exists(), 'AUDIT_OUTPUT_ALREADY_EXISTS_NO_OVERWRITE')
    report['continuation_link'] = old_charge_reconciliation(report, auth)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('xb') as f:
        f.write(canonical(report))
    print('READ_ONLY_RECOVERY_AUDIT_WRITTEN; NO MODEL WAS IMPORTED OR RUN')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
