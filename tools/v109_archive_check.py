# -*- coding: utf-8 -*-
"""v109 archive checker: strict, independent byte-level verification.
Required: exact fixed gate set with strict booleans; unique members; complete
manifest; 73 roles with EXACT case sets; per-member SHA; status task/source.
archive_integrity and numerical_accepted are recorded separately."""
import os, sys, json, csv, hashlib, zipfile, argparse

REQUIRED_GATES = ['A_source_admission', 'B_independent_decisions', 'C_delta_repair', 'D_physics_contract']

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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--zip', required=True)
    ap.add_argument('--expect-status-sha', default='')
    ap.add_argument('--out', default='')
    args = ap.parse_args()
    res = {'zip_path': os.path.abspath(args.zip), 'checks': {}}
    ok = True
    if not os.path.isfile(args.zip):
        res['checks']['zip_exists'] = False
        return finish(res, args, ok)
    res['checks']['zip_exists'] = True
    data = open(args.zip, 'rb').read()
    res['zip_sha256'] = sha256_bytes(data)
    import io
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except Exception as e:
        res['checks']['zip_open'] = 'FAILED: %s' % e
        return finish(res, args, False)
    names = z.namelist()
    res['checks']['unique_members'] = len(names) == len(set(names))
    if not res['checks']['unique_members']:
        ok = False
    bad = z.testzip()
    res['checks']['crc_all_members'] = bad is None
    if bad is not None:
        ok = False
    man_name = 'iscat_v109_return/manifest_sha256.csv'
    if man_name not in names:
        res['checks']['manifest_present'] = False
        return finish(res, args, False)
    man_rows = list(csv.DictReader(z.read(man_name).decode('utf-8').splitlines()))
    listed = {'iscat_v109_return/' + r['relative_path'] for r in man_rows}
    members = set(names) - {man_name}
    res['checks']['member_set_complete'] = members == listed
    if members != listed:
        res['checks']['member_set_diff'] = {'extra': sorted(members - listed)[:10],
                                            'missing': sorted(listed - members)[:10]}
        ok = False
    sha_bad = [r['relative_path'] for r in man_rows
               if sha256_bytes(z.read('iscat_v109_return/' + r['relative_path'])) != r['sha256']]
    res['checks']['member_sha_all_match'] = not sha_bad
    if sha_bad:
        res['checks']['member_sha_bad'] = sha_bad[:10]
        ok = False
    snap_name = 'iscat_v109_return/logs/v109_snapshot73_manifest.csv'
    if snap_name not in names:
        res['checks']['snapshot_manifest_present'] = False
        return finish(res, args, False)
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
    res['checks']['case_multiset_diff'] = None if observed_pairs == expected_pairs \
        else {'observed_sample': observed_pairs[:5], 'expected_sample': expected_pairs[:5]}
    for r in snap:
        member = 'iscat_v109_return/' + r['target_relative']
        if member not in names or sha256_bytes(z.read(member)) != r['sha256']:
            snap_ok = False
            break
    res['checks']['snapshot73_roles_and_exact_case_set'] = snap_ok
    ok = ok and snap_ok
    st_name = 'iscat_v109_return/status.json'
    if st_name not in names:
        res['checks']['status_present'] = False
        return finish(res, args, False)
    st_data = z.read(st_name)
    st_sha = sha256_bytes(st_data)
    res['checks']['status_sha256'] = st_sha
    res['checks']['status_sha_matches_receipt'] = (not args.expect_status_sha
                                                   or st_sha == args.expect_status_sha)
    if not res['checks']['status_sha_matches_receipt']:
        ok = False
    st = json.loads(st_data.decode('utf-8'))
    res['checks']['status_task_id'] = st.get('task_id')
    res['checks']['status_source_commit'] = st.get('source_commit')
    gates = st.get('gates')
    gates_ok = isinstance(gates, dict) and set(gates.keys()) == set(REQUIRED_GATES) \
        and all(isinstance(gates[g], bool) and gates[g] is True for g in REQUIRED_GATES)
    res['checks']['required_gate_set_exact_strict_bool'] = gates_ok
    if not gates_ok:
        res['checks']['gate_detail'] = {g: gates.get(g, 'MISSING') for g in REQUIRED_GATES} if isinstance(gates, dict) else gates
        ok = False
    res['numerical_accepted'] = bool(gates_ok)
    res['archive_integrity'] = bool(ok and res['checks']['unique_members'] and res['checks']['crc_all_members']
                                    and res['checks']['member_set_complete'] and res['checks']['member_sha_all_match']
                                    and snap_ok and res['checks']['status_sha_matches_receipt'])
    return finish(res, args, ok)

def finish(res, args, ok):
    res['archive_valid'] = bool(ok)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(res, f, indent=2)
    print(json.dumps(res, indent=2))
    return 0 if ok else 2

if __name__ == '__main__':
    sys.exit(main())
