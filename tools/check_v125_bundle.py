#!/usr/bin/env python3
"""V125 minimal *mechanical* archive checker: CRC, membership, SHA, ID, stage status and budget.

NOT a physics or inverse-validation checker. Run OUTSIDE the final ZIP:
    python tools/check_v125_bundle.py --zip results/v125/iscat_v125_return.zip \
        --receipt results/v125_external_receipt.json

A COMPLETE/PASS report here means ARCHIVE MECHANICS ONLY. Requires a separate independent
scientific replay of Er/Es -> pixel -> C and of at least one new direct-physics holdout.
"""
import argparse
import csv
import hashlib
import io
import json
import pathlib
import stat
import sys
import zipfile

TASK = 'V125_SUSPENDED_DH_CALIBRATION_AND_BLIND_VALIDATION'
BASE = '384a52304f77490c410d395dd150e0ea82760d1f'
BUDGETS = {'bem_system_attempts': 64, 'optical_render_attempts': 240, 'synthetic_exposure_events': 6000}
BASE_FILES = {
    '00_START_HERE.md', '01_V125_Codex_完整执行合同.md',
    'status.json', 'review.md', 'config/effective_config.json',
    'logs/source_identity.json', 'logs/actual_commands_and_errors.txt',
    'logs/execution_ledger.csv', 'logs/resource_budget.csv',
    'validation/numerical_qualification.csv',
    'validation/plan_lock.json', 'manifest_sha256.csv',
}
REQUIRED_BY_PASS = {
    'S3': {'library/v125_Dh_train_fields.h5', 'library/train_grid_index.csv'},
    'S4': {'library/v125_direct_holdouts.h5', 'library/holdout_index.csv',
           'validation/inversion_holdout_joint.csv', 'validation/holdout_gate_summary.json'},
    'S6': {'validation/noise_per_trial.csv', 'validation/blank_per_trial.csv',
           'validation/exposure_motion_per_trial.csv'},
}


def safe_name(s):
    if not s or '\\' in s or s.startswith('/') or '\x00' in s:
        return False
    parts = s.split('/')
    return all(p and p not in ('.', '..') for p in parts) and pathlib.PurePosixPath(s).as_posix() == s


def run(path):
    errors, checks = [], []
    def check(name, condition, detail=''):
        checks.append({'check': name, 'passed': bool(condition), 'detail': str(detail)})
        if not condition:
            errors.append(f'{name}: {detail}')

    with zipfile.ZipFile(path) as z:
        members = z.infolist()
        names = [f.filename for f in members]
        check('no_duplicate_members', len(names) == len(set(names)), len(names))
        check('all_safe_paths', all(safe_name(n) for n in names))
        check('no_unix_symlinks', all(not stat.S_ISLNK(f.external_attr >> 16) for f in members))
        check('all_regular_files', all(not f.is_dir() for f in members))
        check('zip_crc', z.testzip() is None)
        s = set(names)
        check('required_base_members', BASE_FILES <= s, 'missing=' + str(sorted(BASE_FILES - s)))
        if 'manifest_sha256.csv' not in s or 'status.json' not in s:
            return checks, errors
        try:
            rows = list(csv.DictReader(io.TextIOWrapper(z.open('manifest_sha256.csv'), encoding='utf-8')))
            keys = [r['member'] for r in rows]
            check('manifest_no_duplicate_keys', len(keys) == len(set(keys)))
            check('manifest_complete_member_set', set(keys) == s - {'manifest_sha256.csv'},
                  'missing=' + str(sorted(s - {'manifest_sha256.csv'} - set(keys))) +
                  ' extra=' + str(sorted(set(keys) - s)))
            sha_bad = []
            for r in rows:
                member = r['member']
                if member not in s or not safe_name(member):
                    sha_bad.append(f'{member}: missing/unsafe')
                    continue
                h = hashlib.sha256()
                with z.open(member) as f:
                    while True:
                        chunk = f.read(1 << 20)
                        if not chunk:
                            break
                        h.update(chunk)
                if h.hexdigest() != r['sha256']:
                    sha_bad.append(member)
            check('manifest_sha256', not sha_bad, str(sha_bad))
        except Exception as exc:
            check('manifest_parse', False, repr(exc))
        try:
            status = json.loads(z.read('status.json'))
            check('v125_task_id', status.get('task_id') == TASK, status.get('task_id'))
            check('source_commit_identity', status.get('fixed_source_commit') == BASE,
                  status.get('fixed_source_commit'))
            claims = status.get('scientific_claims')
            check('experimental_absolute_diameter_must_be_false',
                  isinstance(claims, dict) and claims.get('EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED') is False)
            st = status.get('stages')
            check('all_stage_status_present', isinstance(st, dict) and all(f'S{i}' in st for i in range(8)))
            if isinstance(st, dict):
                for k, req in REQUIRED_BY_PASS.items():
                    v = st.get(k, {})
                    if isinstance(v, dict) and v.get('validation') == 'PASS':
                        check(k+'_claimed_pass_has_required_artifacts', req <= s,
                              'missing=' + str(sorted(req - s)))
                allowed_exe = {'NOT_STARTED','RUNNING','COMPLETED','PARTIAL','BLOCKED','FAILED'}
                allowed_val = {'PASS','FAIL','NOT_EVALUATED','INDETERMINATE'}
                for k in [f'S{i}' for i in range(8)]:
                    v = st.get(k)
                    if isinstance(v, dict):
                        check(k+'_status_enums', v.get('execution') in allowed_exe and
                              v.get('validation') in allowed_val, repr(v))
        except Exception as exc:
            check('status_parse', False, repr(exc))
        try:
            b = list(csv.DictReader(io.TextIOWrapper(z.open('logs/resource_budget.csv'), encoding='utf-8')))
            actual = {r['resource']: r for r in b}
            for name, cap in BUDGETS.items():
                if name not in actual:
                    check('budget_'+name, False, 'missing')
                    continue
                r = actual[name]
                n = int(r['attempted'])
                failures = int(r.get('failed', 0))
                limit = int(r['limit'])
                check('budget_'+name, 0 <= failures <= n <= cap and limit == cap,
                      f'attempted={n},failed={failures},limit={limit},cap={cap}')
        except Exception as exc:
            check('resource_budget_parse', False, repr(exc))
    return checks, errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--zip', required=True)
    ap.add_argument('--receipt', default='')
    a = ap.parse_args()
    p = pathlib.Path(a.zip)
    try:
        checks, errors = run(p)
    except Exception as exc:
        checks, errors = [{'check':'archive_open','passed':False,'detail':repr(exc)}], [repr(exc)]
    sha = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    record = {'schema':'iscat125.mechanical_receipt.1', 'zip_name':p.name,
              'zip_sha256':sha, 'mechanical_verdict':'PASS' if not errors else 'FAIL',
              'scientific_replay_verdict':'NOT_CHECKED_BY_THIS_SCRIPT',
              'checks':checks, 'errors':errors}
    print(json.dumps(record, indent=2, ensure_ascii=False))
    if a.receipt:
        dest = pathlib.Path(a.receipt)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(record, indent=2, ensure_ascii=False)+'\n',encoding='utf-8')
    return 0 if not errors else 1

if __name__ == '__main__':
    sys.exit(main())
