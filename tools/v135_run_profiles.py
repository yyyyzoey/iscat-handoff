import sys, os, json, time
sys.path.insert(0, 'tools')
import numpy as np, h5py
from scipy.optimize import least_squares
import v129_field_forward as ff

model = ff.ComplexFieldForward(kind='F2')
OUT = 'results/v135/profiles'
os.makedirs(OUT, exist_ok=True)
hp = 'results/v132/validation/new_M_images.h5'
M_truth = dict(M01=53.0, M02=81.0, M03=119.0, M04=149.0, M05=171.0, M06=187.0)
D_grid = sorted(set(list(np.arange(30, 201, 5.0)) + [30.0, 200.0]))
lo3 = [350.0, -500.0, -500.0]
hi3 = [550.0, 500.0, 500.0]
all_res = {}
for case in ('M01','M02','M03','M04','M05','M06'):
    D_true = M_truth[case]
    with h5py.File(hp, 'r') as h:
        Cobs = h[case]['at_offset/C'][()][2:15, 2:15]
    t0 = time.time()
    prof = []
    warm = [450.0, 0.0, 0.0]
    for D in D_grid:
        def g(p):
            try:
                Cm = model.C(D, p[0], p[1], p[2])
                if Cm is None:
                    return np.full(Cobs.size, 1e6)
                return (Cm - Cobs).ravel()
            except Exception:
                return np.full(Cobs.size, 1e6)
        try:
            r = least_squares(g, x0=np.array(warm), bounds=(lo3,hi3), x_scale=[50,140,140], max_nfev=200)
            warm = [float(r.x[0]), float(r.x[1]), float(r.x[2])]
            prof.append(dict(D=float(D), loss=float(np.linalg.norm(r.fun)), h=warm[0], x=warm[1], y=warm[2]))
        except Exception:
            prof.append(dict(D=float(D), loss=None))
    valid = [p for p in prof if p['loss'] is not None]
    if not valid:
        print(case, 'ALL FAILED')
        all_res[case] = dict(profile=prof, error='all_failed')
        continue
    min_p = min(valid, key=lambda p: p['loss'])
    print(case, 'best_D=', min_p['D'], flush=True)
    all_res[case] = dict(profile=prof, min_loss=min_p['loss'], best_D=min_p['D'])
    with open(os.path.join(OUT, case + '.json'), 'w') as f:
        json.dump(dict(case=case, profile=prof, min_loss=min_p['loss']), f, indent=1, default=str)
json.dump(all_res, open(os.path.join(OUT, 'all_profiles.json'), 'w'), indent=1, default=str)
print('ALL PROFILES DONE')
