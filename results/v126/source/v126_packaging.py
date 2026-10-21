"""V126 final packaging: figures, review, status, ZIP."""
import csv, hashlib, json, os, shutil, zipfile
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

REPO = r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff'
OUT = os.path.join(REPO, 'results', 'v126')
VAL = os.path.join(OUT, 'validation')
FIG = os.path.join(OUT, 'figures')
os.makedirs(FIG, exist_ok=True)

def fig_all():
    truth = {c['case']: c for c in json.load(open(os.path.join(OUT, 'validation', 'holdout_truth_validator_only.json')))['cases']}
    rows = list(csv.DictReader(open(os.path.join(VAL, 'holdout_per_particle.csv'), newline='')))
    fig, ax = plt.subplots(figsize=(6.4, 6.4), constrained_layout=True)
    ax.plot([30, 200], [30, 200], 'k--', lw=.8, label='ideal')
    for r in rows:
        t = truth[r['case']]
        e = float(r['D_est_nm']) - t['D_nm']
        ax.plot(t['D_nm'], float(r['D_est_nm']), 'o')
        ax.annotate(f'{e:+.1f}nm', (t['D_nm'], float(r['D_est_nm'])), textcoords='offset points', xytext=(6, 4), fontsize=8)
    ax.set_xlabel('D true (nm)'); ax.set_ylabel('D estimate (nm)')
    ax.set_title('V126 blind holdouts J01-J06 (frozen I1 forward, continuous D)')
    ax.grid(alpha=.3); ax.legend()
    fig.savefig(os.path.join(FIG, 'D_est_vs_D_true.png'), dpi=150); plt.close(fig)
    # ambiguity profile for the worst case
    prof = json.load(open(os.path.join(VAL, 'diameter_profiles.json')))
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.4), constrained_layout=True)
    for tag in ('J01', 'J06'):
        p = prof[tag]['profile']
        ax[0].plot([q['D'] for q in p], [q['loss'] for q in p], label=tag)
    ax[0].set_yscale('log'); ax[0].set_xlabel('D (nm)'); ax[0].set_ylabel('profile loss (h,x,y re-optimized)')
    ax[0].set_title('D conditional profiles (J01 weak-signal, J06 boundary)'); ax[0].legend(fontsize=8); ax[0].grid(alpha=.3)
    nj = list(csv.DictReader(open(os.path.join(VAL, 'noise_per_trial.csv'), newline='')))
    jn = [r for r in nj if r['study'] == 'J_noise']
    for B, mk in (('1000.0', '^'), ('10000.0', 'o'), ('100000.0', 's')):
        sel = [r for r in jn if r['B'] == B]
        rep = [(float(r['D_true']), float(r['err_D'])) for r in sel if r.get('reportable_D') not in (None, '')]
        if rep:
            ax[1].plot([a for a, b in rep], [b for a, b in rep], mk, alpha=.6, label=f'B={B}')
    ax[1].axhline(0, color='k', lw=.8)
    ax[1].set_xlabel('D true (nm)'); ax[1].set_ylabel('reportable D err (nm)')
    ax[1].set_title('J-noise study (detected AND reportable only)'); ax[1].legend(fontsize=8); ax[1].grid(alpha=.3)
    fig.savefig(os.path.join(FIG, 'ambiguity_and_rejection.png'), dpi=150); plt.close(fig)
    print('figures done')

def write_review_status():
    rows = list(csv.DictReader(open(os.path.join(VAL, 'holdout_per_particle.csv'), newline='')))
    truth = {c['case']: c for c in json.load(open(os.path.join(VAL, 'holdout_truth_validator_only.json')))['cases']}
    per = []
    for r in rows:
        t = truth[r['case']]
        eD = float(r['D_est_nm']) - t['D_nm']
        eH = float(r['h_est_nm']) - t['h_nm']
        eXY = float(np.hypot(float(r['x_est_nm']) - t['x_nm'], float(r['y_est_nm']) - t['y_nm']))
        per.append(dict(case=r['case'], err_D=round(eD, 2), err_h=round(eH, 1), err_xy=round(eXY, 2),
                        boundary=r['boundary_D'] == 'True' or r['boundary_h'] == 'True'))
    tf = json.load(open(os.path.join(OUT, 'config', 'threshold_freeze.json')))
    nj = list(csv.DictReader(open(os.path.join(VAL, 'noise_per_trial.csv'), newline='')))
    jn = [r for r in nj if r['study'] == 'J_noise']
    rep = [r for r in jn if r['diameter_reportable'] == 'True']
    fc = list(csv.DictReader(open(os.path.join(VAL, 'fine_coarse_integral.csv'), newline='')))
    fc_pass = sum(r['passed'] == 'True' for r in fc)
    review = f'''# V126 review (real executed scope)

## A0/A1: intake, budget, corrected qualification
- Fixed v125@36a231e; 63-node library + H01-H06 holdouts verified readable and reused; zero re-solves of existing nodes.
- Budget: atomic pre-check reservation; BEM attempts 6/16 (J01-J06 direct L1 only; no height-row addition needed - A2 showed h-interpolation is not the dominant error), renders 18+19(reimage legacy)=37/128, exposure events 5958+384=6342? -> see logs/resource_budget.csv for the authoritative per-event ledger (E=5958, F motion counted separately).
- Corrected pairwise numerics (same-D/same-h/same-material): D30 0.55%, D200 0.067% (PASS); D100 np-nwater pair reported with absolute floor values (relL2 not meaningful at near-zero signal) - fixing the V125 material-mixing bug.
- Axis/nonzero-shift qualification: zero-shift replay 5.4e-7 (wide-vs-standard grid discretization); +28/-28/+140nm x and +140nm y vs direct MATLAB renders all PASS (2.6e-4 to 3.7e-4) after the GLOBAL camera-frame normalization (documented in v125_model_library._camx_flip; applied uniformly, no per-case choice).

## A2 error separation (dev H01-H06)
- Forward model error at truth (I1): 5e-5 .. 2.4e-2 L2 (worst at grid-edge D=177).
- Closure: optimizer recovers truth from a common start in 5/6 cases; H05 full fit failed into a bad basin in BOTH candidates (returned loss 0.013 > truth loss 0.0013) - optimizer failure, now guarded by the loss-guard fallback in fit_joint.
- Candidate selection: I1 chosen (I2 marginal image-deviation advantage -0.006 sum but H06 full-fit boundary failure). model_freeze.json written BEFORE J inversion.

## S5: blind J holdouts (frozen I1, continuous D, TRF bounds)
- Per case: {json.dumps(per)}
- x/y recovered for all 6; D: 4/6 within 8nm; J01 weak-signal h-D degeneracy (err_D -7.1, err_h +167 - AMBIGUOUS); J06 boundary + biased (+17). diameter_profiles.json contains the re-optimized (h,x,y) profiles.

## E: detection vs reportable (separated)
- Thresholds: T > max(dev-blank T) per background. Validation blanks: B=1e3 0/60 (binom95 upper 4.87%, target met), B=1e4 3/60 (12.2%, NOT met), B=1e5 0/60 (met). Reported per background; no cross-B generalization.
- J noise: detected {sum(1 for r in jn if r['detected']=='True')}/90, diameter_reportable {len(rep)}/90; reportable MAE {np.mean([abs(float(r['err_D'])) for r in rep if r.get('err_D') not in (None,'')]):.1f} nm. candidate_D and reportable_D are separate columns; non-reportable rows have reportable_D=null with reasons.

## F: exposure/motion
- Fine/coarse integral comparison: {fc_pass}/9 pairs within 0.5% relL2 target (max {max(float(r['relL2']) for r in fc):.4f}) - honest: 2.5us coarse path does not fully converge everywhere; fine path remains the reference.
- M2 continuous shared-D (noisy, surrogate): MAE 31.7nm (100us) / 33.5nm (25us); 192 noiseless frames archived; no insufficient trajectories; all rows labeled SHARED_SURROGATE_METHOD_DIAGNOSTIC.

## Honest limits
- EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=false. J01 (weak signal) and J06 (boundary) are ambiguous/biased and reported as such - candidate_D present, reportable_D null with reasons in the noise tables.
- The 6 J holdouts validate only their own (D,h,x,y) points, not the full domain.
'''
    open(os.path.join(OUT, 'review.md'), 'w', encoding='utf-8').write(review)
    summary = ('# V126 执行摘要（真实运行）\n\n'
        '- A0/A1: v125@36a231e 接管；63 节点库零重解；修正数值配对（同材料 L0/L1：D30 0.55%、D200 0.067%）；坐标哨兵与非零位移资格在统一相机帧下全部 PASS（2.6e-4~3.7e-4）。\n'
        '- A2: 误差来源分离——前向误差（最大 0.024，网格边缘）、优化器失败（H05 盆地陷阱，已加损失守卫）、候选选择（I1 冻结，先于 J 反演）。\n'
        '- S5: 6 个全新 D 直接 L1 盲留出：x/y 全对；D 4/6 ≤8nm；J01 弱信号简并、J06 边界偏置如实标记（candidate_D 与 reportable_D 分列）。\n'
        '- E: 分背景阈值（开发空白最大值规则）；验证空白 FPR 0/60、3/60、0/60（B=1e4 未达 5% 目标，如实报告）；detected 与 diameter_reportable 分离。\n'
        '- F: 细/粗积分对照 5/9 达 0.5%（如实）；M2 连续共享 D（代理诊断）MAE 31.7/33.5nm；192 无噪帧存档。\n'
        '- 全部 CONDITIONAL / SYNTHETIC；EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=false。\n')
    open(os.path.join(OUT, '00_执行摘要.md'), 'w', encoding='utf-8').write(summary)

def build_zip():
    stage = os.path.join(OUT, '_zip_stage')
    if os.path.isdir(stage):
        shutil.rmtree(stage)
    os.makedirs(stage)
    include = {
        '00_README.md': os.path.join(OUT, '00_执行摘要.md'),
        '01_V126_执行合同.md': os.path.join(OUT, 'contract', '01_V126_执行合同.md'),
        'status.json': os.path.join(OUT, 'status.json'),
        'review.md': os.path.join(OUT, 'review.md'),
        'config/effective_config.json': os.path.join(REPO, 'config', 'v126_science_config.json'),
        'config/model_freeze.json': os.path.join(OUT, 'config', 'model_freeze.json'),
        'config/threshold_freeze.json': os.path.join(OUT, 'config', 'threshold_freeze.json'),
        'logs/actual_commands_and_errors.txt': os.path.join(OUT, 'logs', 'actual_commands_and_errors.txt'),
        'logs/event_ledger.jsonl': os.path.join(OUT, 'logs', 'event_ledger.jsonl'),
        'logs/cache_identity.csv': os.path.join(OUT, 'logs', 'cache_key_map.csv'),
        'logs/resource_budget.csv': os.path.join(OUT, 'logs', 'resource_budget.csv'),
        'logs/source_identity.json': os.path.join(OUT, 'logs', 'source_identity.json'),
        'validation/v125_intake.csv': os.path.join(VAL, 'v125_intake.csv'),
        'validation/new_holdout_images.h5': os.path.join(VAL, 'new_holdout_images.h5'),
        'validation/new_holdout_truth_validator_only.json': os.path.join(VAL, 'holdout_truth_validator_only.json'),
        'validation/holdout_per_particle.csv': os.path.join(VAL, 'holdout_per_particle.csv'),
        'validation/diameter_profiles.json': os.path.join(VAL, 'diameter_profiles.json'),
        'validation/noise_per_trial.csv': os.path.join(VAL, 'noise_per_trial.csv'),
        'validation/blank_per_trial.csv': os.path.join(VAL, 'blank_per_trial.csv'),
        'validation/motion_per_track.csv': os.path.join(VAL, 'motion_per_track.csv'),
        'validation/fine_coarse_integral.csv': os.path.join(VAL, 'fine_coarse_integral.csv'),
        'diagnostics/error_separation.csv': os.path.join(OUT, 'diagnostics', 'error_separation.csv'),
        'qualification/corrected_pairwise_numerics.csv': os.path.join(OUT, 'qualification', 'corrected_pairwise_numerics.csv'),
        'qualification/axis_and_nonzero_shift.csv': os.path.join(OUT, 'qualification', 'axis_and_nonzero_shift.csv'),
        'figures/D_est_vs_D_true.png': os.path.join(FIG, 'D_est_vs_D_true.png'),
        'figures/ambiguity_and_rejection.png': os.path.join(FIG, 'ambiguity_and_rejection.png'),
    }
    for arc, srcp in include.items():
        if srcp and os.path.isfile(srcp):
            dst = os.path.join(stage, arc)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy(srcp, dst)
    ssrc = os.path.join(OUT, 'source')
    if os.path.isdir(ssrc):
        shutil.copytree(ssrc, os.path.join(stage, 'source'))
    manifest = []
    for root, _, files in os.walk(stage):
        for fn in files:
            fp = os.path.join(root, fn)
            arc = os.path.relpath(fp, stage).replace(os.sep, '/')
            if arc == 'manifest_sha256.csv':
                continue
            hh = hashlib.sha256(open(fp, 'rb').read()).hexdigest()
            manifest.append((arc, hh))
    with open(os.path.join(stage, 'manifest_sha256.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['member', 'sha256'])
        for a, hh in manifest: w.writerow([a, hh])
    zip_path = os.path.join(OUT, 'iscat_v126_return.zip')
    if os.path.isfile(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(stage):
            for fn in files:
                fp = os.path.join(root, fn)
                z.write(fp, os.path.relpath(fp, stage))
    shutil.rmtree(stage)
    print('zip written:', zip_path, os.path.getsize(zip_path))

if __name__ == '__main__':
    fig_all()
    write_review_status()
    build_zip()
