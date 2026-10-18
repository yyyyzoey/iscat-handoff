# -*- coding: utf-8 -*-
"""v108 archive checker: re-read the actual ZIP bytes and verify independently.
Verifies CRC, complete member set, per-member SHA vs in-zip manifest, the 73
role/case snapshot set, status.json hash, and the release machine gates.
A missing ZIP, PENDING_CREATION receipt, or a bare status text cannot pass."""
import os, sys, json, csv, hashlib, zipfile, argparse

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
        ok = False
        return finish(res, args, ok)
    res['checks']['zip_exists'] = True
    res['zip_sha256'] = sha256_bytes(open(args.zip, 'rb').read())

    try:
        z = zipfile.ZipFile(args.zip)
    except Exception as e:
        res['checks']['zip_open'] = 'FAILED: %s' % e
        return finish(res, args, False)

    names = z.namelist()
    # CRC test for every member (testzip reads bytes and verifies CRC)
    bad = z.testzip()
    res['checks']['crc_all_members'] = bad is None
    if bad is not None:
        ok = False

    # manifest inside zip lists every other member
    man_name = 'iscat_v108_return/manifest_sha256.csv'
    if man_name not in names:
        res['checks']['manifest_present'] = False
        return finish(res, args, False)
    man_rows = list(csv.DictReader(zipfile.ZipFile(args.zip).read(man_name).decode('utf-8').splitlines()))
    listed = {'iscat_v108_return/' + r['relative_path'] for r in man_rows}
    members = set(names) - {man_name}
    res['checks']['member_set_complete'] = members == listed
    if members != listed:
        res['checks']['member_set_diff'] = {
            'extra': sorted(members - listed)[:10], 'missing': sorted(listed - members)[:10]}
        ok = False
    # per-member SHA
    sha_bad = []
    for r in man_rows:
        data = z.read('iscat_v108_return/' + r['relative_path'])
        if sha256_bytes(data) != r['sha256']:
            sha_bad.append(r['relative_path'])
    res['checks']['member_sha_all_match'] = not sha_bad
    if sha_bad:
        res['checks']['member_sha_bad'] = sha_bad[:10]
        ok = False

    # 73 role/case snapshot set
    snap_name = 'iscat_v108_return/logs/v108_snapshot73_manifest.csv'
    if snap_name not in names:
        res['checks']['snapshot_manifest_present'] = False
        return finish(res, args, False)
    snap = list(csv.DictReader(z.read(snap_name).decode('utf-8').splitlines()))
    roles = [r['role'] for r in snap]
    snap_ok = (len(snap) == 73 and roles.count('BANK') == 48
               and roles.count('BASELINE') == 24 and roles.count('SAVED_SIMULATION_PROBES') == 1)
    # verify each snapshot member byte-exists in zip with recorded sha
    for r in snap:
        member = 'iscat_v108_return/' + r['target_relative']
        if member not in names or sha256_bytes(z.read(member)) != r['sha256']:
            snap_ok = False
            break
    res['checks']['snapshot73_roles_cases'] = snap_ok
    ok = ok and snap_ok

    # status.json hash + machine gates
    st_name = 'iscat_v108_return/status.json'
    if st_name not in names:
        res['checks']['status_present'] = False
        return finish(res, args, False)
    st_data = z.read(st_name)
    st_sha = sha256_bytes(st_data)
    res['checks']['status_sha256'] = st_sha
    if args.expect_status_sha and st_sha != args.expect_status_sha:
        res['checks']['status_sha_matches_receipt'] = False
        ok = False
    else:
        res['checks']['status_sha_matches_receipt'] = True
    st = json.loads(st_data.decode('utf-8'))
    gates_ok = all(bool(v) for v in st.get('gates', {}).values())
    res['checks']['status_gates_all_true'] = gates_ok
    res['checks']['status_task_id'] = st.get('task_id')
    res['checks']['status_numerical'] = (st.get('states') or {}).get('numerical')
    # PENDING_CREATION or bare status text cannot pass
    res['checks']['not_pending_creation'] = st.get('states', {}).get('archive') != 'PENDING_CREATION'
    ok = ok and gates_ok and res['checks']['not_pending_creation']

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
