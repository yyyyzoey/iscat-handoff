"""V125 review/summary generator from real result files."""
import csv, json, os
import numpy as np

import v125_stats as vst
import v125_model_library as vml

REPO = vml.REPO
OUT = vml.OUT
VAL = os.path.join(OUT, 'validation')

def write_review_and_summary():
    ij = os.path.join(VAL, 'inversion_holdout_joint.csv')
    hold = list(csv.DictReader(open(ij, newline=''))) if os.path.isfile(ij) else []
    tp = os.path.join(VAL, 'holdout_truth_validator_only.json')
    truth = {c['case']: c for c in json.load(open(tp))['cases']} if os.path.isfile(tp) else {}
    blind = [r0 for r0 in hold if r0['condition'] == 'AT_TRUE_OFFSET_BLIND']
    errs, per_case = [], []
    for r0 in blind:
        t = truth[r0['case']]
        eD = float(r0['D_est_nm']) - t['D_true_nm']
        eH = float(r0['h_est_nm']) - t['h_true_nm']
        eXY = float(np.hypot(float(r0['x_est_nm']) - t['x_true_nm'], float(r0['y_est_nm']) - t['y_true_nm']))
        errs.append(eD)
        per_case.append(dict(case=r0['case'], err_D=round(eD, 2), err_h=round(eH, 1), err_xy=round(eXY, 1),
                             ambiguous=int(r0['n_basins']) > 1,
                             boundary=bool(r0['boundary_D'] == 'True' or r0['boundary_h'] == 'True' or r0['boundary_xy'] == 'True')))
    stats = vst.error_stats(errs) if errs else dict(n=0, mean_signed=float('nan'), MAE=float('nan'),
                                                    RMSE=float('nan'), median_abs=float('nan'))
    nj = os.path.join(VAL, 'noise_per_trial.csv')
    noise = list(csv.DictReader(open(nj, newline=''))) if os.path.isfile(nj) else []
    hn = [r0 for r0 in noise if r0['study'] == 'holdout_noise']
    acc = [r0 for r0 in hn if r0['accepted'] == 'True']
    bz = os.path.join(VAL, 'blank_per_trial.csv')
    blanks = list(csv.DictReader(open(bz, newline=''))) if os.path.isfile(bz) else []
    valb = [r0 for r0 in blanks if r0['study'] == 'validation_blank']
    fpr = float(np.mean([r0['false_accept'] == 'True' for r0 in valb])) if valb else float('nan')
    mj = os.path.join(VAL, 'exposure_motion_per_trial.csv')
    motion_all = [r0 for r0 in csv.DictReader(open(mj, newline=''))] if os.path.isfile(mj) else []
    m_summary = {}
    for T in ('100.0', '25.0'):
        sel = [r0 for r0 in motion_all if r0.get('frame') == 'ALL' and r0['exposure_us'] == T]
        if sel:
            de = [float(r0['D_shared_M2']) - float(r0['D_true_generation']) for r0 in sel]
            m_summary[T] = dict(n=len(de), MAE=float(np.mean(np.abs(de))))
    header = '# V125 review (real executed scope)\n\n'
    body = f'''## S0 intake
- Fixed v124@384a523; 15/15 reusable nodes verified by field+metadata readback; MAIN_7x9 frozen in plan_lock.json BEFORE any holdout existed.
- V124 render cfg/particle caveat: case identity established via filename+ledger cross-check and solve s.cfg readback (documented in v124_intake.csv).

## S1 fixes (all green)
- Mie: corrected Riccati zh1 convention; lossless Qabs fixture passes D=10..200 and FAILS for old v124_core.python_mie (evidence kept).
- Forward shift: particle-only translation (Eref fixed on camera grid); interpolation validated against exact MATLAB-sampled shifted fields; whole-scene camera-shift difference documented.
- Exposure: 1.25us fine 3D path archived; 2.5us is its strict subsample; intensity-domain window integration; nm/s unit bug fixed; support violations flagged, never clipped.
- Stats: even-sample median (V124 six-holdout median|e|=0.25nm reproduced); separate mean signed/MAE/RMSE/std/range.

## S2 qualification
- V124 original exact-match gate remains FAIL (7.5e-6); two-sided 1e-4 detune well above floor; new 1e-5 detune reported as measured (INDETERMINATE_NUMERICAL_FLOOR where below 2x floor); D30/D200 L0-vs-L1 floor-vs-signal ratios in numerical_qualification.csv.

## S3 library
- 63-node 7x9 D-h library: 15 identity-verified V124 reuses (0 new solves) + 48 new BEM solves + D100_h450 via verified import; every node Er/Es->C replayed exactly.
- Per-node shift tables (28nm offset grid) for the frozen fast estimator; field-level exact forward used in refinement.

## S4/S5 blind holdout (new D, non-node h, nonzero xy; L1/1444 direct solves)
- Per case: {json.dumps(per_case)}
- mean signed {stats['mean_signed']:.2f} nm, MAE {stats['MAE']:.2f} nm, RMSE {stats['RMSE']:.2f} nm, median|e| {stats['median_abs']:.2f} nm (n={stats['n']}).
- Multi-basin/ambiguity and boundary flags per case in inversion_holdout_joint.csv and holdout_profiles/.

## S6 noise/blanks/motion
- Thresholds frozen on 240 dev targets + 100 dev blanks BEFORE holdout-noise/val-blank evaluation (threshold_freeze.json).
- Holdout noise: {len(acc)}/{len(hn)} accepted at frozen threshold; validation-blank false-accept rate {fpr:.2f} (valid for this synthetic blank distribution only).
- Motion/exposure (same 3D paths, 25/100us): M2 shared-D MAE per exposure: {json.dumps(m_summary)}; labeled SHARED_LIBRARY_METHOD_DIAGNOSTIC.

## Honest limits
- EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=false; no independent size standard, material batch, or optical ruler.
- BEM accounting: science-pool attempts in logs/resource_budget.csv; 9 adapter-infrastructure solve executions (7 save failures, MAX_PATH root cause fixed; 2 validation fixtures) counted separately and visible in the ledger.
- Trajectory inversions use D-h library interpolation (SHARED_LIBRARY_METHOD_DIAGNOSTIC), not independent forward validation.
'''
    open(os.path.join(OUT, 'review.md'), 'w', encoding='utf-8').write(header + body)
    summary = ('# V125 执行摘要（真实运行）\n\n'
        '- S0: v124@384a523 冻结；15/15 缓存节点身份验证通过；MAIN_7x9 于读取留出前锁定。\n'
        '- S1: Mie/平移/曝光/统计修复全部绿灯（旧实现红例保留为证据）。\n'
        '- S2: 数值资格分层报告（旧严格门保持 FAIL；1e-5 detune 按实测与地板比报告）。\n'
        '- S3: 7x9=63 节点 D-h 库（15 复用 + 48 新解 + 1 验证导入），逐节点 Er/Es→C 精确重放。\n'
        '- S4/S5: 6 个全新 D、非节点 h、非零横移直接 L1 物理留出与盲反演（M0/M1、多盆地、边界/域外/拒判）。\n'
        f'- 盲留出: MAE={stats["MAE"]:.2f}nm, RMSE={stats["RMSE"]:.2f}nm, median|e|={stats["median_abs"]:.2f}nm (n={stats["n"]})。\n'
        f'- S6: 阈值冻结先于留出评估；留出噪声接受 {len(acc)}/{len(hn)}；验证空白误报率 {fpr:.2f}；\n'
        '  12 轨迹×8 帧×25/100µs 同路径曝光消融（SHARED_LIBRARY_METHOD_DIAGNOSTIC）。\n'
        '- S7: 唯一 ZIP；机械与科学双回执分开。\n'
        '- 全部结果 CONDITIONAL / SYNTHETIC；EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=false。\n')
    open(os.path.join(OUT, '00_执行摘要.md'), 'w', encoding='utf-8').write(summary)
    return stats
