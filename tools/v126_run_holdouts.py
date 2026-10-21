import csv, json, os, sys
import numpy as np
import h5py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v126_forward_model as fm
import v126_invert_particle as vin

OUT = os.path.join(fm.REPO, 'results', 'v126')

def main():
    freeze = json.load(open(os.path.join(OUT, 'config', 'model_freeze.json')))
    cand = freeze['selected_candidate']
    model = fm.CanonicalModel()
    hp = os.path.join(OUT, 'validation', 'new_holdout_images.h5')
    rows, profiles = [], {}
    with h5py.File(hp, 'r') as h:
        for tag in h.keys():
            Cobs = h[tag]['at_offset/C'][()][2:15, 2:15]
            best = vin.fit_joint(Cobs, model, cand,
                                 scan_offsets=((0, 0), (56, -84), (-112, 56), (112, 112), (-84, -84), (140, 0), (0, 140), (-140, 0), (0, -140)))
            prof = vin.d_profile(Cobs, model, cand, step=4.0)
            profiles[tag] = dict(best=best, profile=prof)
            rows.append(dict(case=tag, method='M1_joint', candidate=cand,
                             D_est_nm=best['theta'][0], h_est_nm=best['theta'][1],
                             x_est_nm=best['theta'][2], y_est_nm=best['theta'][3],
                             loss=best['loss'], nfev=best['nfev'],
                             success=best['success'],
                             boundary_D=bool(abs(best['theta'][0]-30) < 1 or abs(best['theta'][0]-200) < 1),
                             boundary_h=bool(abs(best['theta'][1]-350) < 1 or abs(best['theta'][1]-550) < 1),
                             D_profile_min_loss=min(p['loss'] for p in prof),
                             D_profile_argmin=min(prof, key=lambda p: p['loss'])['D']))
            print(f"{tag} D={best['theta'][0]:.1f} h={best['theta'][1]:.1f} x={best['theta'][2]:+.0f} y={best['theta'][3]:+.0f} loss={best['loss']:.2g}", flush=True)
    keys = sorted({k for r in rows for k in r})
    with open(os.path.join(OUT, 'validation', 'holdout_per_particle.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in rows: w.writerow(r)
    with open(os.path.join(OUT, 'validation', 'diameter_profiles.json'), 'w') as f:
        json.dump(profiles, f, indent=1)
    model.close()
    print('J inversion complete')

if __name__ == '__main__':
    main()
