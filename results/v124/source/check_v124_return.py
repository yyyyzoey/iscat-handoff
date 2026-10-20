"""Independent V124 return checker: zip CRC/manifest verification, physics replay,
and holdout inversion replay. Writes results/v124_external_receipt.json."""
import argparse, csv, io, json, os, sys, tempfile, zipfile
import numpy as np
import h5py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v124_core as vc
import invert_v124_particle as inv

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(vc.REPO, 'results', 'v124'))
    ap.add_argument('--receipt', default=None)
    args = ap.parse_args()
    receipt_path = args.receipt or os.path.join(os.path.dirname(args.out), 'v124_external_receipt.json')
    zip_path = os.path.join(args.out, 'iscat_v124_return.zip')
    checks = []
    def add(name, ok, detail=''):
        checks.append(dict(check=name, passed=bool(ok), detail=str(detail)))

    with zipfile.ZipFile(zip_path) as z:
        bad = z.testzip()
        add('zip_crc_all_members', bad is None, f'first_bad={bad}')
        names = z.namelist()
        add('members_unique', len(names) == len(set(names)), f'{len(names)} members')
        manifest = {r['member']: r['sha256'] for r in csv.DictReader(io.TextIOWrapper(z.open('manifest_sha256.csv'), encoding='utf-8'))}
        ok_all, missing = True, []
        for member, sha in manifest.items():
            data = z.read(member)
            import hashlib
            if hashlib.sha256(data).hexdigest() != sha:
                ok_all = False; missing.append(member)
        add('manifest_sha256_all_match', ok_all, f'checked={len(manifest)} bad={missing}')

        with tempfile.TemporaryDirectory() as td:
            z.extract('library/valid_physical_fields_or_coefficients.h5', td)
            h5p = os.path.join(td, 'library', 'valid_physical_fields_or_coefficients.h5')
            with h5py.File(h5p, 'r') as lib:
                # physics replay: Er/Es -> pixel -> I -> C for D60_h450
                g = lib['D60_h450']
                Eref = g['Eref'][()]; Esca = g['Esca'][()]
                I0 = vc.pixel_mean(np.sum(np.abs(Eref) ** 2, 2), 5)
                Is = vc.pixel_mean(np.sum(np.abs(Esca) ** 2, 2), 5)
                Ix = vc.pixel_mean(2 * np.real(np.sum(np.conj(Eref) * Esca, 2)), 5)
                It = I0 + Is + Ix
                Ierr = float(np.max(np.abs(It - g['Itotal'][()])) / np.max(np.abs(g['Itotal'][()])))
                Crep = (It - I0) / I0
                Cerr = float(np.max(np.abs(Crep - g['C'][()])))
                add('replay_er_es_to_C_D60h450', Ierr < 1e-10 and Cerr < 1e-10,
                    f'identity={Ierr:.3g} C_abs_err={Cerr:.3g}')
                # holdout inversion replay for D85
                Dg, T = inv.fixed_h_templates(lib, 450.0)
                gh = lib['D85_h450']
                est = inv.invert_D(gh['C'][()], Dg, T)
                hp = list(csv.DictReader(io.TextIOWrapper(z.open('validation/holdout_per_particle.csv'), encoding='utf-8')))
                ref = next(r for r in hp if abs(float(r['D_truth_nm']) - 85.0) < 1e-9)
                ddiff = abs(est['D_est_lsq'] - float(ref['D_est_nm']))
                add('replay_holdout_inversion_D85', ddiff < 1e-6,
                    f'checker_D_est={est["D_est_lsq"]:.6f} shipped={ref["D_est_nm"]} diff={ddiff:.3g}')
    receipt = dict(schema='iscat124.receipt.1', zip=os.path.basename(zip_path),
                   sha256_of_zip=vc.sha256(zip_path),
                   EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=False,
                   verdict='PASS' if all(c['passed'] for c in checks) else 'FAIL',
                   checks=checks)
    with open(receipt_path, 'w', encoding='utf-8') as f:
        json.dump(receipt, f, indent=1, ensure_ascii=False)
    for c in checks:
        print(('PASS' if c['passed'] else 'FAIL'), c['check'], c['detail'])
    print('verdict:', receipt['verdict'], '->', receipt_path)

if __name__ == '__main__':
    main()
