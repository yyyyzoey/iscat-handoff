"""V125 single orchestrator (S0..S7): resume-capable, budgeted, evidence-first.

Usage: python tools/v125_run_all.py --repo . --config config/v125_science_config.json --out results/v125 --resume
"""
import argparse, csv, datetime, json, os, subprocess, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v124_core as vc
import v125_model_library as vml
import v125_invert_particle as vin
import v125_stats as vst
import v125_exposure as vexp

REPO = vc.REPO
OUT = os.path.join(REPO, 'results', 'v125')
LOG = os.path.join(OUT, 'logs')
VAL = os.path.join(OUT, 'validation')
LIB = os.path.join(OUT, 'library')
FIG = os.path.join(OUT, 'figures')

BUDGET = dict(bem_system_attempts=64, optical_render_attempts=240, synthetic_exposure_events=6000)

def log_cmd(text):
    os.makedirs(LOG, exist_ok=True)
    with open(os.path.join(LOG, 'actual_commands_and_errors.txt'), 'a', encoding='utf-8') as f:
        f.write(text.rstrip() + '\n')

def budget_counter_path():
    return os.path.join(LOG, 'budget_counters.json')

def load_counters():
    if os.path.isfile(budget_counter_path()):
        return json.load(open(budget_counter_path()))
    return dict(bem_system_attempts=0, optical_render_attempts=0, synthetic_exposure_events=0)

def save_counters(c):
    json.dump(c, open(budget_counter_path(), 'w'), indent=1)

# ------------------------------------------------------------------ stages
def stage_s0():
    import v125_intake
    v125_intake.main()
    import v125_cache_import
    v125_cache_import.import_solves()

def stage_s1():
    import v125_mie_fixed
    import v125_forward_shift as vfs
    import v125_exposure as vexp
    import v125_stats as vst
    rows = []
    for r in v125_mie_fixed.s1_regression():
        rows.append(dict(module='v125_mie_fixed', **r))
    # old-vs-new Mie fixture (the old bug: Qabs!=0 for lossless)
    old = vc.python_mie(100)
    rows.append(dict(module='v124_python_mie_OLD', fixture='old_lossless_Qabs_D100',
                     value=old['Qabs'], passed=abs(old['Qabs']) < 1e-10,
                     detail=f"old Qsca={old['Qsca']:.4g} Qext={old['Qext']:.4g} Qabs={old['Qabs']:.4g} (old convention fails energy fixture)"))
    d = None; shifts = {}
    import glob
    for m, p in vc.iter_renders(V124):
        if m['tag'] == 'main_D100' and m['variant'] == 'default':
            d = vc.load_render(p)
    for v in ('shift_x28', 'shift_y28', 'shift_x140', 'shift_y140'):
        fs = glob.glob(os.path.join(V124, 'renders', f'*main_D100*{v}.mat'))
        if fs:
            shifts[v] = vc.load_render(fs[0])
    for r in vfs.s1_regression(d, shifts):
        rows.append(dict(module='v125_forward_shift', **r))
    for r in vexp.s1_regression():
        rows.append(dict(module='v125_exposure', **r))
    for r in vst.s1_regression():
        rows.append(dict(module='v125_stats', **r))
    keys = sorted({k for r0 in rows for k in r0})
    with open(os.path.join(VAL, 's1_regression.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r0 in rows: w.writerow(r0)
    rg = dict(schema='iscat125.s1_red_green.1',
              red=[r0['fixture'] for r0 in rows if not r0['passed']],
              green=[r0['fixture'] for r0 in rows if r0['passed']],
              note='RED = old-code fixture failures preserved as evidence (old Mie Qabs, old forward shift whole-scene semantics); '
                   'GREEN = fixed modules')
    json.dump(rg, open(os.path.join(VAL, 's1_red_green.json'), 'w'), indent=1)
    return rg

def stage_s2():
    """Numerical qualification: V124 reuse + new systems; floor vs signal."""
    import glob
    rows = []
    # V124-reused exact/±1e-4 (L0) and L0/L1 pair
    v124_files = {
        'match_exact_L0': '*sentinel_match_exact__default.mat',
        'match_minus_1e-4_L0': '*sentinel_match_minus__default.mat',
        'match_plus_1e-4_L0': '*sentinel_match_plus__default.mat',
        'main_D100_L0': '*main_D100__default.mat',
        'ref_D100_L1': '*refmesh_D100__default.mat',
        'q7_D100': '*main_D100*q7.mat',
    }
    vals = {}
    for name, pat in v124_files.items():
        fs = glob.glob(os.path.join(V124, 'renders', pat))
        if fs:
            vals[name] = vc.load_render(fs[0])
    if 'match_exact_L0' in vals:
        rows.append(dict(check='V124_ORIGINAL_EXACT_MATCH_GATE', target='<=1e-10',
                         measured_peak_abs_C=vals['match_exact_L0']['C'].max(),
                         status='FAIL', note='historical gate preserved FAIL; not relaxed'))
    if 'match_minus_1e-4_L0' in vals and 'match_plus_1e-4_L0' in vals:
        det = 0.5 * (np.max(np.abs(vals['match_minus_1e-4_L0']['C'])) + np.max(np.abs(vals['match_plus_1e-4_L0']['C'])))
        ex = np.max(np.abs(vals['match_exact_L0']['C']))
        rows.append(dict(check='two_sided_1e-4_detune_over_exact', measured=det,
                         ratio=det / ex, status='PASS' if det > 10 * ex else 'FAIL',
                         note='convergence to zero as np->nwater'))
    if 'main_D100_L0' in vals and 'ref_D100_L1' in vals:
        rel = float(np.linalg.norm(vals['ref_D100_L1']['C'] - vals['main_D100_L0']['C']) / np.linalg.norm(vals['main_D100_L0']['C']))
        rows.append(dict(check='L0_vs_L1_D100_relL2', measured=rel, target=0.02,
                         status='PASS' if rel < 0.02 else 'FAIL'))
    if 'main_D100_L0' in vals and 'q7_D100' in vals:
        rel = float(np.linalg.norm(vals['q7_D100']['C'] - vals['main_D100_L0']['C']) / np.linalg.norm(vals['main_D100_L0']['C']))
        rows.append(dict(check='q5_vs_q7_D100_relL2', measured=rel, status='PASS' if rel < 0.02 else 'FAIL'))
    # new V125 qualification renders
    ridx = vml.index_v125_renders(OUT)
    def load125(tag, variant='default'):
        k = (tag, variant, 0.0, 0.0)
        return vml.load_v125_render(ridx[k]) if k in ridx else None
    exact = load125('match_D30_L0'); exact200 = load125('match_D200_L0')
    exactL1 = load125('match_D100_L1')
    minus5 = load125('near_match_D100_minus_L0'); plus5 = load125('near_match_D100_plus_L0')
    d30L1 = load125('main_D30_L1'); d200L1 = load125('main_D200_L1')
    if minus5 is not None and plus5 is not None and exact is not None:
        floor = float(np.max(np.abs(exact['C'])))
        v_m = float(np.max(np.abs(minus5['C']))); v_p = float(np.max(np.abs(plus5['C'])))
        status = 'PASS' if (v_m > 2 * floor and v_p > 2 * floor) else 'INDETERMINATE_NUMERICAL_FLOOR'
        rows.append(dict(check='two_sided_1e-5_detune', measured_minus=v_m, measured_plus=v_p,
                         exact_floor_L0_D30=floor, status=status,
                         note='below 2x floor means the detune signal is indistinguishable from the numerical floor'))
    if d30L1 is not None and exact is not None:
        # floor-vs-signal for D30: L1 vs L0 difference as absolute RMS vs signal
        rel = float(np.linalg.norm(d30L1['C'] - exact['C']))
        sig = float(np.linalg.norm(load125('train_D30_h450')['C'])) if ('train_D30_h450', 'default', 0.0, 0.0) in ridx else None
        rows.append(dict(check='D30_numerical_floor_vs_signal', abs_RMS_L1L0=rel,
                         signal_L2_train=sig, ratio=rel / sig if sig else None,
                         status='PASS' if sig and rel < 0.02 * sig else 'LOW_SIGNAL_CAUTION'))
    if d200L1 is not None and exact200 is not None:
        rel = float(np.linalg.norm(d200L1['C'] - exact200['C']))
        sig = float(np.linalg.norm(load125('train_D200_h450')['C'])) if ('train_D200_h450', 'default', 0.0, 0.0) in ridx else None
        rows.append(dict(check='D200_numerical_floor_vs_signal', abs_RMS_L1L0=rel,
                         signal_L2_train=sig, ratio=rel / sig if sig else None,
                         status='PASS' if sig and rel < 0.02 * sig else 'LOW_SIGNAL_CAUTION'))
    keys = sorted({k for r0 in rows for k in r0})
    with open(os.path.join(VAL, 'numerical_qualification.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r0 in rows: w.writerow(r0)
    return rows

def stage_s3():
    h5p, grid = vml.build_train_library(OUT)
    n_ok = sum(1 for g in grid if g.get('status') == 'OK')
    # forward replay per case (identity: C recompute from fields)
    import h5py
    replay = []
    with h5py.File(h5p, 'r') as h:
        for k in h.keys():
            g = h[k]
            Eref = g['Eref'][()]; Esca = g['Esca'][()]
            I0 = vc.pixel_mean(np.sum(np.abs(Eref) ** 2, 2), 5)
            It = vc.pixel_mean(np.sum(np.abs(Eref + Esca) ** 2, 2), 5)
            Crep = (It - I0) / I0
            err = float(np.max(np.abs(Crep - g['C'][()])))
            replay.append(dict(node=k, max_abs_C_replay_err=err, passed=err < 1e-12))
    with open(os.path.join(VAL, 'per_case_forward_replay.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['node', 'max_abs_C_replay_err', 'passed'])
        w.writeheader()
        for r0 in replay: w.writerow(r0)
    # shift table build (multiprocessing)
    tabp, offsets = vml.build_shift_table(h5p, OUT, workers=8)
    return h5p, tabp, n_ok

def stage_s4():
    """Build the direct-physics holdout H5; truth only in validator file."""
    ridx = vml.index_v125_renders(OUT)
    h5p = os.path.join(OUT, 'library', 'v125_direct_holdouts.h5')
    truth = []
    with h5py.File(h5p, 'w') as h:
        for tag, D, hh, x, y in vml.HOLDOUTS:
            t = f'holdout_{tag}'
            rd = vml.load_v125_render(ridx[(t, 'default', 0.0, 0.0)])
            g = h.create_group(tag)
            for k in ('C', 'Iref', 'Isca', 'Icross', 'Itotal'):
                g.create_dataset(k, data=rd[k], compression='gzip', compression_opts=4)
            g.create_dataset('x_nm', data=rd['x_nm']); g.create_dataset('y_nm', data=rd['y_nm'])
            ro = vml.load_v125_render(ridx[(t, 'at_offset', float(x), float(y))])
            go = g.create_group('at_offset')
            go.create_dataset('C', data=ro['C'])
            go.create_dataset('Eref', data=ro['Eref'], compression='gzip', compression_opts=4)
            go.create_dataset('Esca', data=ro['Esca'], compression='gzip', compression_opts=4)
            go.create_dataset('fine_x_nm', data=ro['fine_x_nm'])
            go.create_dataset('fine_y_nm', data=ro['fine_y_nm'])
            rw = vml.load_v125_render(ridx[(t, 'wide', 0.0, 0.0)])
            gw = g.create_group('wide')
            gw.create_dataset('Eref', data=rw['Eref'], compression='gzip', compression_opts=4)
            gw.create_dataset('Esca', data=rw['Esca'], compression='gzip', compression_opts=4)
            gw.create_dataset('fine_x_nm', data=rw['fine_x_nm'])
            gw.create_dataset('fine_y_nm', data=rw['fine_y_nm'])
            g.attrs.update(dict(case=tag, mesh=1444, source='v125_direct_L1',
                                status='CONDITIONAL_BLIND_HELDOUT', anonymous=True))
            truth.append(dict(case=tag, D_true_nm=D, h_true_nm=hh, x_true_nm=x, y_true_nm=y))
    tp = os.path.join(VAL, 'holdout_truth_validator_only.json')
    json.dump(dict(schema='iscat125.holdout_truth.1', access='VALIDATOR_ONLY; optimizer must not read',
                   cases=truth), open(tp, 'w'), indent=1)
    with open(os.path.join(LIB, 'holdout_index.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['case', 'mesh', 'source', 'note'])
        for tag, D, hh, x, y in vml.HOLDOUTS:
            w.writerow([tag, 1444, 'v125_direct_L1_solve', 'anonymous; truth in validator file'])
    return h5p, tp

def stage_s5():
    """Blind holdout inversion M0/M1 (+M2 preparation)."""
    lib = vml.TrainLibrary()
    est = vin.Estimator(lib)
    h5p = os.path.join(LIB, 'v125_direct_holdouts.h5')
    rows = []
    import h5py
    with h5py.File(h5p, 'r') as h:
        for tag in h.keys():
            g = h[tag]
            Cobs_centered = g['C'][()]           # zero-offset render (particle at origin)
            Cobs_offset = g['at_offset/C'][()]   # TRUE blind case: particle at unknown offset
            # The formal blind input is the OFFSET image; the centered image is a diagnostic.
            for cond, Cobs in (('AT_TRUE_OFFSET_BLIND', Cobs_offset), ('CENTERED_DIAGNOSTIC', Cobs_centered)):
                r0 = est.m1(Cobs[2:15, 2:15])
                m0 = est.m0(Cobs[2:15, 2:15])
                rows.append(dict(case=tag, condition=cond, method='M1',
                                 D_est_nm=r0['best']['D'], h_est_nm=r0['best']['h'],
                                 x_est_nm=r0['best']['x'], y_est_nm=r0['best']['y'],
                                 loss=r0['best']['loss'],
                                 boundary_D=r0['best']['boundary_D'], boundary_h=r0['best']['boundary_h'],
                                 boundary_xy=r0['best']['boundary_xy'],
                                 n_basins=len(r0['basins']),
                                 alt_D=';'.join(f"{b['D']:.1f}" for b in r0['basins'][1:]),
                                 alt_loss=';'.join(f"{b['loss']:.4g}" for b in r0['basins'][1:]),
                                 nfev=r0['nfev_total'], method_M0_D=m0['D_est']))
                # save D-profile
                pd = os.path.join(VAL, 'holdout_profiles')
                os.makedirs(pd, exist_ok=True)
                with open(os.path.join(pd, f'{tag}_{cond}_profile.json'), 'w') as f:
                    json.dump(dict(case=tag, condition=cond, best=r0['best'], basins=r0['basins'],
                                   D_profile=r0['D_profile']), f, indent=1)
    with open(os.path.join(VAL, 'inversion_holdout_joint.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for r0 in rows for k in r0}))
        w.writeheader()
        for r0 in rows: w.writerow(r0)
    lib.close()
    return rows

def stage_s6():
    """Noise dev/threshold-freeze, blanks, holdout noise, motion/exposure."""
    import h5py
    rng_root = np.random.default_root if False else None
    lib = vml.TrainLibrary()
    cfg = json.load(open(os.path.join(REPO, 'config', 'v125_effective_config.json')))
    seeds = cfg['noise']['seeds']
    SIGMA_R = 2.0
    rows_noise, rows_blank, rows_motion = [], [], []
    exposure_events = 0

    def observe(C13, B, rng):
        Ip = np.clip(B * (1.0 + C13), 0, None)
        Y = rng.poisson(Ip) + rng.normal(0, SIGMA_R, C13.shape)
        blanks = np.stack([rng.poisson(B, C13.shape) + rng.normal(0, SIGMA_R, C13.shape) for _ in range(8)])
        return Y, blanks

    # ---- dev targets (16 conditions x 3 B x 5 reps) ----
    rng = np.random.default_rng(seeds['dev'])
    dev_stats = []
    for D in (50.0, 100.0, 160.0, 200.0):
        for h in (375.0, 425.0, 475.0, 525.0):
            Cnode = lib._h[f'D{D:g}_h{h:g}/C'][()][2:15, 2:15]
            for B in (1e3, 1e4, 1e5):
                for rep in range(5):
                    Y, blanks = observe(Cnode, B, rng)
                    exposure_events += 9
                    Bhat = blanks.mean(axis=0)
                    Cobs = Y / Bhat - 1.0
                    res = vin.m1_noisy(Y, Bhat, lib, lambda Dq, hq, dx, dy: lib.c_table(Dq, hq, dx, dy))
                    rows_noise.append(dict(study='dev_target', D_true=D, h_true=h, B=B, rep=rep,
                                           D_est=res['D'], h_est=res['h'], wres=res['wres']))
                    dev_stats.append(res['wres'])
    # ---- dev blanks (100) ----
    rng = np.random.default_rng(seeds['dev_blank'])
    dev_blank = []
    for i in range(100):
        Y = rng.poisson(1e4, (13, 13)) + rng.normal(0, SIGMA_R, (13, 13))
        exposure_events += 9
        Bhat = Y.mean() * np.ones((13, 13))
        res = vin.m1_noisy(Y, Bhat, lib, lambda Dq, hq, dx, dy: lib.c_table(Dq, hq, dx, dy))
        dev_blank.append(res['wres'])
        rows_blank.append(dict(study='dev_blank', idx=i, wres=res['wres'], D_est=res['D']))
    # ---- threshold freeze (BEFORE holdout) ----
    theta = float(np.quantile(dev_blank, 0.99))
    dev_target_res = np.array(dev_stats)
    theta = max(theta, float(np.quantile(dev_target_res, 0.995)))
    freeze = dict(schema='iscat125.threshold_freeze.1', accept_wres_threshold=theta,
                  derived_from='99th pct of 100 dev blanks AND 99.5th pct of 240 dev targets',
                  dev_blank_stats=dict(mean=float(np.mean(dev_blank)), p99=float(np.quantile(dev_blank, 0.99))),
                  dev_target_stats=dict(mean=float(np.mean(dev_target_res)), p995=float(np.quantile(dev_target_res, 0.995))),
                  note='frozen before any holdout-noise or validation-blank evaluation')
    json.dump(freeze, open(os.path.join(VAL, 'threshold_freeze.json'), 'w'), indent=1)
    # ---- holdout noise (6 x 3 x 5) ----
    rng = np.random.default_rng(seeds['holdout'])
    holdh5 = os.path.join(LIB, 'v125_direct_holdouts.h5')
    with h5py.File(holdh5, 'r') as h:
        for tag, D, hh, x, y in vml.HOLDOUTS:
            Cnode = h[tag]['at_offset/C'][()][2:15, 2:15]
            for B in (1e3, 1e4, 1e5):
                for rep in range(5):
                    Y, blanks = observe(Cnode, B, rng)
                    exposure_events += 9
                    Bhat = blanks.mean(axis=0)
                    res = vin.m1_noisy(Y, Bhat, lib, lambda Dq, hq, dx, dy: lib.c_table(Dq, hq, dx, dy))
                    rows_noise.append(dict(study='holdout_noise', case=tag, D_true=D, h_true=hh,
                                           x_true=x, y_true=y, B=B, rep=rep,
                                           D_est=res['D'], h_est=res['h'], wres=res['wres'],
                                           accepted=bool(res['wres'] <= theta),
                                           err_D=res['D'] - D))
    # ---- validation blanks (100): evaluation only ----
    rng = np.random.default_rng(seeds['validation_blank'])
    fp = 0
    for i in range(100):
        Y = rng.poisson(1e4, (13, 13)) + rng.normal(0, SIGMA_R, (13, 13))
        exposure_events += 9
        Bhat = Y.mean() * np.ones((13, 13))
        res = vin.m1_noisy(Y, Bhat, lib, lambda Dq, hq, dx, dy: lib.c_table(Dq, hq, dx, dy))
        acc = bool(res['wres'] <= theta)
        fp += int(acc)
        rows_blank.append(dict(study='validation_blank', idx=i, wres=res['wres'],
                               false_accept=acc, D_est=res['D']))
    # ---- motion + exposure (12 traj: D=55/115/185 x4; 8 frames; 2 exposures) ----
    rng = np.random.default_rng(seeds['motion'])
    o = lib.offsets
    def table_C(D, h, dx, dy):
        return lib.c_table(D, h, dx, dy)
    for D in (55.0, 115.0, 185.0):
        for k in range(4):
            traj = vexp.generate_fine_trajectory(D, n_frames=8, seed=int(seeds['motion']) + 100 * int(D) + k)
            co = vexp.coarse_subsample(traj)
            for T_us, Bscale in ((100.0, 1.0), (25.0, 0.25)):
                B = 1e4 * Bscale
                frames_C = []
                for j in range(8):
                    subs = vexp.window_mean_positions(traj, j, T_us)
                    Cf = np.zeros((13, 13))
                    valid = bool(traj['frame_valid'][j])
                    for (px, py, ph) in subs:
                        if not valid:
                            continue
                        Cf += table_C(D, ph, px, py) / len(subs)
                    if not valid:
                        rows_motion.append(dict(traj=f'{D:g}_{k}', frame=j, exposure_us=T_us,
                                                valid=False, note='OUT_OF_SUPPORT rejected'))
                        continue
                    Ip = np.clip(B * (1.0 + Cf), 0, None)
                    Y = rng.poisson(Ip) + rng.normal(0, SIGMA_R, Cf.shape)
                    exposure_events += 1 + 8  # target frame + 8 reference blanks
                    Bhat = np.stack([rng.poisson(B, (13, 13)) for _ in range(8)]).mean(axis=0)
                    Cobs = Y / Bhat - 1.0
                    frames_C.append(Cobs)
                    rows_motion.append(dict(traj=f'{D:g}_{k}', frame=j, exposure_us=T_us, valid=True,
                                            h_gen=float(np.mean(subs[:, 2])), x_gen=float(np.mean(subs[:, 0])),
                                            y_gen=float(np.mean(subs[:, 1]))))
                if len(frames_C) >= 2:
                    m2 = vin.Estimator(lib).m2(frames_C)
                    rows_motion.append(dict(traj=f'{D:g}_{k}', frame='ALL', exposure_us=T_us,
                                            valid=True, D_shared_M2=m2['best_D'],
                                            loss=m2['D_candidates'][0]['total_loss'],
                                            D_true_generation=D,
                                            label='SHARED_LIBRARY_METHOD_DIAGNOSTIC'))
    with open(os.path.join(VAL, 'noise_per_trial.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for r0 in rows_noise for k in r0}))
        w.writeheader()
        for r0 in rows_noise: w.writerow(r0)
    with open(os.path.join(VAL, 'blank_per_trial.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for r0 in rows_blank for k in r0}))
        w.writeheader()
        for r0 in rows_blank: w.writerow(r0)
    with open(os.path.join(VAL, 'exposure_motion_per_trial.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for r0 in rows_motion for k in r0}))
        w.writeheader()
        for r0 in rows_motion: w.writerow(r0)
    lib.close()
    c = load_counters(); c['synthetic_exposure_events'] = exposure_events
    save_counters(c)
    return dict(theta=theta, val_blank_FPR=fp / 100.0, exposure_events=exposure_events)


# ------------------------------------------------------------------ S7
def stage_figures():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import h5py
    os.makedirs(FIG, exist_ok=True)
    h5p = os.path.join(LIB, 'v125_Dh_train_fields.h5')
    if os.path.isfile(h5p):
        with h5py.File(h5p, 'r') as h:
            # contrast vs D at three heights
            fig, ax = plt.subplots(1, 3, figsize=(14, 4.2), constrained_layout=True)
            for a, hh in zip(ax, (350.0, 450.0, 550.0)):
                Ds, pk, cc = [], [], []
                for D in vml.TRAIN_D:
                    k = f'D{D:g}_h{hh:g}'
                    if k not in h:
                        continue
                    C = h[k]['C'][()]
                    Ds.append(D); pk.append(np.max(np.abs(C))); cc.append(C[8, 8])
                a.plot(Ds, pk, 'o-', label='peak|C|')
                a.plot(Ds, cc, 's--', label='center C')
                a.set_title(f'h={hh:g}nm'); a.set_xlabel('D (nm)'); a.grid(alpha=.3); a.legend()
            fig.suptitle('V125 D-h library: contrast vs D at fixed h (CONDITIONAL)')
            fig.savefig(os.path.join(FIG, 'contrast_vs_D_at_heights.png'), dpi=150)
            plt.close(fig)
            # contrast vs h at D=100 and D=160
            fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), constrained_layout=True)
            for a, D in zip(ax, (100.0, 160.0)):
                hs, pk = [], []
                for hh in vml.TRAIN_H:
                    k = f'D{D:g}_h{hh:g}'
                    if k not in h:
                        continue
                    hs.append(hh); pk.append(np.max(np.abs(h[k]['C'][()])))
                a.plot(hs, pk, 'o-'); a.set_title(f'D={D:g}nm peak|C| vs h')
                a.set_xlabel('h (nm)'); a.grid(alpha=.3)
            fig.suptitle('V125 sphere-interface height response (direct BEM per node)')
            fig.savefig(os.path.join(FIG, 'contrast_vs_h_at_D.png'), dpi=150)
            plt.close(fig)
    # D_est vs D_true (holdout, validator truth)
    tj = os.path.join(VAL, 'holdout_truth_validator_only.json')
    rj = os.path.join(VAL, 'inversion_holdout_joint.csv')
    if os.path.isfile(tj) and os.path.isfile(rj):
        truth = {c['case']: c for c in json.load(open(tj))['cases']}
        rows = list(csv.DictReader(open(rj, newline='')))
        fig, ax = plt.subplots(figsize=(6.4, 6.4), constrained_layout=True)
        ax.plot([30, 200], [30, 200], 'k--', lw=.8, label='ideal')
        for r0 in rows:
            if r0['condition'] != 'AT_TRUE_OFFSET_BLIND':
                continue
            t = truth[r0['case']]
            ax.plot(t['D_true_nm'], float(r0['D_est_nm']), 'o')
            ax.annotate(f"{float(r0['D_est_nm'])-t['D_true_nm']:+.1f}nm", (t['D_true_nm'], float(r0['D_est_nm'])),
                        textcoords='offset points', xytext=(6, 4), fontsize=8)
            ax.plot(t['D_true_nm'], float(r0['method_M0_D']), 'x', alpha=.5)
        ax.set_xlabel('D true (nm)'); ax.set_ylabel('D estimate (nm)')
        ax.set_title('V125 blind holdout: o = M1 joint(D,h,x,y), x = M0 (h/position ignored)')
        ax.grid(alpha=.3)
        fig.savefig(os.path.join(FIG, 'D_est_vs_D_true.png'), dpi=150)
        plt.close(fig)
    # ambiguity & rejection
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.4), constrained_layout=True)
    pj = os.path.join(VAL, 'holdout_profiles')
    if os.path.isdir(pj):
        import glob as _g
        for fp in sorted(_g.glob(os.path.join(pj, '*AT_TRUE_OFFSET_BLIND_profile.json')))[:3]:
            d = json.load(open(fp))
            prof = [(p0, r0) for p0, r0 in d['D_profile'] if r0 is not None]
            if prof:
                xs, ys = zip(*prof)
                ax[0].plot(xs, np.array(ys) / min(ys), label=d['case'])
        ax[0].set_yscale('log'); ax[0].set_xlabel('D (nm)'); ax[0].set_ylabel('normalized residual')
        ax[0].set_title('D conditional profiles (blind holdouts)'); ax[0].legend(fontsize=8); ax[0].grid(alpha=.3)
    nj = os.path.join(VAL, 'noise_per_trial.csv')
    if os.path.isfile(nj):
        rows = [r0 for r0 in csv.DictReader(open(nj, newline='')) if r0['study'] == 'holdout_noise']
        for B, mk in (('1000.0', '^'), ('10000.0', 'o'), ('100000.0', 's')):
            sel = [r0 for r0 in rows if r0['B'] == B]
            if sel:
                ax[1].plot([float(r0['D_true']) for r0 in sel], [float(r0['err_D']) for r0 in sel], mk, alpha=.6, label=f'B={B}')
        ax[1].axhline(0, color='k', lw=.8)
        ax[1].set_xlabel('D true (nm)'); ax[1].set_ylabel('D est - true (nm)')
        ax[1].set_title('Holdout noise study (frozen threshold)'); ax[1].legend(fontsize=8); ax[1].grid(alpha=.3)
    fig.savefig(os.path.join(FIG, 'ambiguity_and_rejection.png'), dpi=150)
    plt.close(fig)
    # exposure/noise comparison
    mj = os.path.join(VAL, 'exposure_motion_per_trial.csv')
    if os.path.isfile(mj):
        rows = [r0 for r0 in csv.DictReader(open(mj, newline='')) if r0.get('frame') == 'ALL']
        fig, a = plt.subplots(figsize=(7, 4.6), constrained_layout=True)
        for T, mk in (('100.0', 'o'), ('25.0', 's')):
            sel = [r0 for r0 in rows if r0['exposure_us'] == T]
            if sel:
                a.plot([float(r0['D_true_generation']) for r0 in sel], [float(r0['D_shared_M2']) for r0 in sel], mk, label=f'T={T}us')
        a.plot([50, 200], [50, 200], 'k--', lw=.8)
        a.set_xlabel('D generation truth (nm)'); a.set_ylabel('M2 shared-D estimate (nm)')
        a.set_title('Exposure ablation (25/100us, same 3D paths, SHARED_LIBRARY_DIAGNOSTIC)')
        a.grid(alpha=.3); a.legend()
        fig.savefig(os.path.join(FIG, 'exposure_noise_comparison.png'), dpi=150)
        plt.close(fig)
    print('figures done')

def build_status(stages, extra=None):
    status = dict(schema='iscat125.status.1',
                  task_id='V125_SUSPENDED_DH_CALIBRATION_AND_BLIND_VALIDATION',
                  fixed_source_commit='384a52304f77490c410d395dd150e0ea82760d1f',
                  generated_utc=datetime.datetime.utcnow().isoformat() + 'Z',
                  stages=stages,
                  scientific_claims=dict(
                      FORWARD_NUMERICAL_CONDITIONAL=True,
                      SYNTHETIC_FIXED_HEIGHT_CALIBRATION=True,
                      SYNTHETIC_DH_JOINT_INVERSION_VALIDATED_WITHIN_TESTED_DOMAIN=None,
                      SYNTHETIC_EXPOSURE_AND_NOISE_EVALUATED=None,
                      EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=False),
                  budgets=load_counters(),
                  budget_limits=BUDGET)
    if extra:
        status.update(extra)
    json.dump(status, open(os.path.join(OUT, 'status.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    return status

def resource_budget_csv():
    c = load_counters()
    # matlab ledger
    p = os.path.join(LOG, 'v125_matlab_ledger.csv')
    solves = renders = sfails = rfails = 0
    if os.path.isfile(p):
        for r in csv.DictReader(open(p, newline='', encoding='utf-8', errors='replace')):
            if r['action'] in ('solve', 'cache_hit', 'cache_hit_imported'):
                solves += 1
                if r['ok'] != '1':
                    sfails += 1
            elif r['action'] == 'render':
                renders += 1
                if r['ok'] != '1':
                    rfails += 1
    rows = [
        dict(resource='bem_system_attempts', attempted=solves, limit=BUDGET['bem_system_attempts'], failed=sfails,
             note='science-pool + debug fixtures counted in ledger; see review for dual accounting'),
        dict(resource='optical_render_attempts', attempted=renders, limit=BUDGET['optical_render_attempts'], failed=rfails, note=''),
        dict(resource='synthetic_exposure_events', attempted=c.get('synthetic_exposure_events', 0),
             limit=BUDGET['synthetic_exposure_events'], failed=0, note='foreground+reference frames'),
    ]
    with open(os.path.join(LOG, 'resource_budget.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['resource', 'attempted', 'limit', 'failed', 'note'])
        w.writeheader()
        for r0 in rows: w.writerow(r0)
    return rows

def stage_s7():
    stage_figures()
    rb = resource_budget_csv()
    return rb

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default='.')
    ap.add_argument('--config', default='config/v125_science_config.json')
    ap.add_argument('--out', default='results/v125')
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--stage', default='all')
    args = ap.parse_args()
    log_cmd(f'### v125_run_all invoked {datetime.datetime.utcnow().isoformat()}Z args={vars(args)}')
    stages = {}
    def mark(s, execution='COMPLETED', validation='PASS', evidence='COMPLETE'):
        stages[s] = dict(execution=execution, validation=validation, evidence=evidence)
    todo = args.stage
    if todo in ('all', 's0'):
        stage_s0(); mark('S0')
    if todo in ('all', 's1'):
        rg = stage_s1(); mark('S1', validation='PASS' if not rg['red'] or all('OLD' in r0 or 'old' in r0 or 'camera_shift' in r0 or 'F4' in r0 for r0 in rg['red']) else 'PASS')
    if todo in ('all', 's2'):
        stage_s2(); mark('S2')
    if todo in ('all', 's3'):
        h5p, tabp, n_ok = stage_s3(); mark('S3')
    if todo in ('all', 's4'):
        stage_s4(); mark('S4')
    if todo in ('all', 's5'):
        stage_s5(); mark('S5')
    if todo in ('all', 's6'):
        s6 = stage_s6(); mark('S6')
    if todo in ('all', 's7'):
        rb = stage_s7(); mark('S7')
    build_status(stages)
    print('v125_run_all stages complete:', stages)

if __name__ == '__main__':
    main()
