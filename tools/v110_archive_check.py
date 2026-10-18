# -*- coding: utf-8 -*-
"""v110 archive checker: strict, independent byte-level verification.
Fixes the v109 defect: a missing or unreadable ZIP returns archive_valid=False
with a non-zero exit. Rejects path traversal, duplicate members, incomplete
manifests, wrong status SHA, wrong task/source, and non-strict gates.
archive_integrity and numerical_accepted are recorded separately."""
import os, sys, json, csv, hashlib, zipfile, argparse, io

REQUIRED_GATES = ['A_source_admission', 'B_independent_decisions', 'C_delta_repair',
                  'D_readback_audit', 'E_physics_admission', 'F_verifier_selftest']
PREFIX = 'iscat_v110_return/'

def all48():
    return (['D%d_zf%d_%s_a%d' % (D, zf, t, a)
             for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)] +
            ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
             for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (10, 15)])

def all24():
    return ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
            for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)]

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()

def is_traversal(rel):
    rel = rel.replace('\\', '/')
    return (rel.startswith('/') or rel.startswith('../') or '/..' in rel or rel == '..'
            or ':' in rel.split('/')[0])

def run(args, res):
    ok = True
    checks = res['checks']
    if not os.path.isfile(args.zip):
        checks['zip_exists'] = False
        res['archive_integrity'] = False
        res['numerical_accepted'] = False
        res['archive_valid'] = False
        return False
    checks['zip_exists'] = True
    data = open(args.zip, 'rb').read()
    res['zip_sha256'] = sha256_bytes(data)
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except Exception as e:
        checks['zip_open'] = 'FAILED: %s' % e
        res['archive_integrity'] = False
        res['archive_valid'] = False
        return False
    names = z.namelist()
    checks['unique_members'] = len(names) == len(set(names))
    if not checks['unique_members']:
        checks['duplicate_members'] = sorted({n for n in names if names.count(n) > 1})[:5]
        ok = False
    bad = z.testzip()
    checks['crc_all_members'] = bad is None
    if bad is not None:
        checks['crc_bad_member'] = bad
        ok = False
    man_name = PREFIX + 'manifest_sha256.csv'
    if man_name not in names:
        checks['manifest_present'] = False
        res['archive_integrity'] = False
        res['archive_valid'] = False
        return False
    man_rows = list(csv.DictReader(z.read(man_name).decode('utf-8').splitlines()))
    listed = {PREFIX + r['relative_path'] for r in man_rows}
    traversal = [r['relative_path'] for r in man_rows if is_traversal(r['relative_path'])]
    checks['manifest_no_path_traversal'] = not traversal
    if traversal:
        checks['traversal_entries'] = traversal[:5]
        ok = False
    members = set(names) - {man_name}
    checks['member_set_complete'] = members == listed
    if members != listed:
        checks['member_set_diff'] = {'extra': sorted(members - listed)[:5],
                                     'missing': sorted(listed - members)[:5]}
        ok = False
    sha_bad = []
    read_errors = []
    for r in man_rows:
        rel = r['relative_path']
        if is_traversal(rel):
            continue
        try:
            if sha256_bytes(z.read(PREFIX + rel)) != r['sha256']:
                sha_bad.append(rel)
        except Exception as e:
            read_errors.append({'path': rel, 'error': str(e)[:120]})
    checks['member_read_errors'] = read_errors[:5]
    checks['member_sha_all_match'] = not sha_bad and not read_errors
    if read_errors:
        ok = False
    if sha_bad:
        checks['member_sha_bad'] = sha_bad[:5]
        ok = False
    snap_name = PREFIX + 'logs/v110_snapshot73_manifest.csv'
    if snap_name not in names:
        checks['snapshot_manifest_present'] = False
        res['archive_integrity'] = False
        res['archive_valid'] = False
        return False
    snap = list(csv.DictReader(z.read(snap_name).decode('utf-8').splitlines()))
    roles = [r['role'] for r in snap]
    cases = [r['case_id'] for r in snap]
    expected_pairs = sorted([('BANK', k) for k in all48()]
                            + [('BASELINE', k) for k in all24()]
                            + [('SAVED_SIMULATION_PROBES', 'PROBE_EVIDENCE_192_SERIES')])
    observed_pairs = sorted(zip(roles, cases))
    snap_ok = (len(snap) == 73 and roles.count('BANK') == 48
               and roles.count('BASELINE') == 24 and roles.count('SAVED_SIMULATION_PROBES') == 1
               and observed_pairs == expected_pairs)
    res['checks']['snapshot73_roles_and_exact_case_multiset'] = snap_ok
    if not snap_ok:
        res['checks']['case_multiset_diff'] = {'observed_sample': observed_pairs[:5],
                                               'expected_sample': expected_pairs[:5]}
        ok = False
    for r in snap:
        member = PREFIX + r['target_relative']
        try:
            if member not in names or sha256_bytes(z.read(member)) != r['sha256']:
                snap_ok = False
                break
        except Exception:
            snap_ok = False
            break
    res['checks']['snapshot73_roles_and_exact_case_multiset'] = snap_ok
    ok = ok and snap_ok
    st_name = PREFIX + 'status.json'
    if st_name not in names:
        checks['status_present'] = False
        res['archive_integrity'] = False
        res['archive_valid'] = False
        return False
    st_data = z.read(st_name)
    st_sha = sha256_bytes(st_data)
    checks['status_sha256'] = st_sha
    checks['status_sha_matches_receipt'] = (not args.expect_status_sha or st_sha == args.expect_status_sha)
    if not checks['status_sha_matches_receipt']:
        ok = False
    try:
        st = json.loads(st_data.decode('utf-8'))
    except Exception as e:
        checks['status_parse'] = 'FAILED: %s' % e
        res['archive_integrity'] = False
        res['archive_valid'] = False
        return False
    checks['status_task_id'] = st.get('task_id')
    checks['status_source_commit'] = st.get('source_commit')
    task_ok = (not getattr(args, 'expect_task', '') or st.get('task_id') == args.expect_task)
    source_ok = (not getattr(args, 'expect_source_commit', '')
                 or st.get('source_commit') == args.expect_source_commit)
    checks['status_task_matches'] = task_ok
    checks['status_source_matches'] = source_ok
    gates = st.get('gates')
    gates_ok = (isinstance(gates, dict) and set(gates.keys()) == set(REQUIRED_GATES)
                and all(isinstance(gates[g], bool) and gates[g] is True for g in REQUIRED_GATES))
    checks['required_gate_set_exact_strict_bool'] = gates_ok
    if not gates_ok:
        if isinstance(gates, dict):
            checks['gate_detail'] = {g: gates.get(g, 'MISSING') for g in REQUIRED_GATES}
    res['archive_integrity'] = bool(ok and checks['unique_members'] and checks['crc_all_members']
                                    and checks.get('manifest_no_path_traversal', False)
                                    and checks['member_set_complete'] and checks['member_sha_all_match']
                                    and snap_ok and checks['status_sha_matches_receipt'])
    res['numerical_accepted'] = bool(gates_ok and task_ok and source_ok)
    res['archive_valid'] = bool(res['archive_integrity'] and res['numerical_accepted'])
    return res['archive_valid']

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--zip', required=True)
    ap.add_argument('--expect-status-sha', default='')
    ap.add_argument('--expect-task', default='V110')
    ap.add_argument('--expect-source-commit', default='3f894b919d11dd2e8dead92b83ed7ec2d930d08c')
    ap.add_argument('--out', default='')
    args = ap.parse_args()
    res = {'zip_path': os.path.abspath(args.zip), 'checks': {}, 'archive_valid': False}
    try:
        run(args, res)
    except Exception as e:
        res['checks']['unexpected_error'] = str(e)[:300]
        res['archive_valid'] = False
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(res, f, indent=2)
    print(json.dumps(res, indent=2))
    return 0 if res['archive_valid'] else 2

if __name__ == '__main__':
    sys.exit(main())
