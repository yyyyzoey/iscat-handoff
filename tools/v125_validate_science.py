"""V125 scientific validator: replay physics and blind inversion FROM the ZIP data."""
import argparse, csv, io, json, os, sys, zipfile
import numpy as np
import h5py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v124_core as vc
import v125_model_library as vml
import v125_forward_shift as vfs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default='.')
    ap.add_argument('--out', default='results/v125')
    ap.add_argument('--strict', action='store_true')
    args = ap.parse_args()
    zip_path = os.path.join(args.out, 'iscat_v125_return.zip')
    checks = []
    def add(name, ok, detail=''):
        checks.append(dict(check=name, passed=bool(ok), detail=str(detail)))
        print(('PASS' if ok else 'FAIL'), name, detail)
    with zipfile.ZipFile(zip_path) as z:
        add('zip_crc', z.testzip() is None)
        names = z.namelist()
        add('members_unique', len(names) == len(set(names)), f'{len(names)} members')
        man = {r['member']: r['sha256'] for r in csv.DictReader(io.TextIOWrapper(z.open('manifest_sha256.csv'), encoding='utf-8'))}
        import hashlib
        bad = [m for m, s in man.items() if hashlib.sha256(z.read(m)).hexdigest() != s]
        add('manifest_sha256_all_match', not bad, f'{len(man)} checked, bad={bad}')
        with tempfile_dir() as td:
            z.extract('library/v125_Dh_train_fields.h5', td)
            z.extract('library/v125_shift_tables.h5', td)
            # physics replay: old cache node (V124-verified D100_h450) and a new node
            with h5py.File(os.path.join(td, 'library', 'v125_Dh_train_fields.h5'), 'r') as h:
                for node, expect_new in (('D100_h450', False), ('D130_h475', True)):
                    if node not in h:
                        add(f'replay_{node}', False, 'missing'); continue
                    g = h[node]
                    Eref, Esca = g['Eref'][()], g['Esca'][()]
                    I0 = vc.pixel_mean(np.sum(np.abs(Eref) ** 2, 2), 5)
                    It = vc.pixel_mean(np.sum(np.abs(Eref + Esca) ** 2, 2), 5)
                    Crep = (It - I0) / I0
                    err = float(np.max(np.abs(Crep - g['C'][()])))
                    add(f'replay_er_es_to_C_{node}', err < 1e-12, f'err={err:.3g} new_node={expect_new}')
            # blind inversion replay: holdout H03 via shift-table model
            z.extract('library/v125_direct_holdouts.h5', td)
            lib = vml.TrainLibrary(os.path.join(td, 'library', 'v125_Dh_train_fields.h5'),
                                   os.path.join(td, 'library', 'v125_shift_tables.h5'))
            import v125_invert_particle as vin
            with h5py.File(os.path.join(td, 'library', 'v125_direct_holdouts.h5'), 'r') as h:
                if 'H03' in h:
                    Cobs = h['H03']['at_offset/C'][()][2:15, 2:15]
                    est = vin.Estimator(lib)
                    r0 = est.m1(Cobs)
                    shipped = list(csv.DictReader(io.TextIOWrapper(
                        z.open('validation/inversion_holdout_joint.csv'), encoding='utf-8')))
                    ref = next(r0 for r0 in shipped if r0['case'] == 'H03' and r0['condition'] == 'AT_TRUE_OFFSET_BLIND')
                    dD = abs(r0['best']['D'] - float(ref['D_est_nm']))
                    add('replay_blind_inversion_H03', dD < 1.0,
                        f"checker D={r0['best']['D']:.2f} shipped={ref['D_est_nm']} dD={dD:.3g} (tolerance 1nm for optimizer restart variance)")
            lib.close()
    receipt = dict(schema='iscat125.science_validation.1', verdict='PASS' if all(c['passed'] for c in checks) else 'FAIL', checks=checks)
    out = os.path.join(os.path.dirname(os.path.abspath(args.out)), 'v125_science_validation.json')
    json.dump(receipt, open(out, 'w', encoding='utf-8'), indent=1)
    print('verdict:', receipt['verdict'], '->', out)

import contextlib, tempfile
@contextlib.contextmanager
def tempfile_dir():
    with tempfile.TemporaryDirectory() as td:
        yield td

if __name__ == '__main__':
    main()
