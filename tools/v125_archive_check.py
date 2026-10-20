"""V125 archive check: bundle mechanical checker + outer receipt writer."""
import argparse, hashlib, json, os, subprocess, sys, zipfile

def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--zip', required=True)
    ap.add_argument('--receipt', required=True)
    args = ap.parse_args()
    checks = []
    with zipfile.ZipFile(args.zip) as z:
        bad = z.testzip()
        checks.append(dict(check='zip_crc_all_members', passed=bad is None, detail=str(bad)))
        names = z.namelist()
        checks.append(dict(check='members_unique', passed=len(names) == len(set(names)), detail=f'{len(names)} members'))
        unsafe = [n for n in names if n.startswith('/') or '..' in n]
        checks.append(dict(check='paths_safe', passed=not unsafe, detail=str(unsafe[:3])))
    # run the bundle mechanical checker if present
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        r = subprocess.run([sys.executable, os.path.join(repo, 'tools', 'check_v125_bundle.py'), '--zip', args.zip],
                           capture_output=True, text=True, timeout=300)
        checks.append(dict(check='bundle_checker', passed='PASS' in (r.stdout + r.stderr).upper() or r.returncode == 0,
                           detail=(r.stdout + r.stderr)[-400:]))
    except Exception as e:
        checks.append(dict(check='bundle_checker', passed=False, detail=str(e)))
    verdict = 'PASS' if all(c['passed'] for c in checks) else 'FAIL'
    receipt = dict(schema='iscat125.external_receipt.1', zip=os.path.basename(args.zip),
                   zip_sha256=sha256(args.zip), archive_verified=verdict == 'PASS',
                   note='archive_verified is MECHANICAL only; science verdict is separate (v125_science_validation.json)',
                   checks=checks)
    json.dump(receipt, open(args.receipt, 'w', encoding='utf-8'), indent=1)
    for c in checks:
        print(('PASS' if c['passed'] else 'FAIL'), c['check'], c['detail'][:100])
    print('archive verdict:', verdict)

if __name__ == '__main__':
    main()
