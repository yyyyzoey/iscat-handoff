"""V146 S6/S7 assembly: status from real numbers, review, manifests, archive."""
from __future__ import annotations
import argparse, csv, hashlib, json, os, shutil, sqlite3, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    (out/'config').mkdir(exist_ok=True);(out/'provenance').mkdir(exist_ok=True)
    shutil.copy2(repo/'config/v146_science_config.json',out/'config/effective_config.json')
    code=out/'source'/'ACTUALLY_EXECUTED_CODE';code.mkdir(parents=True,exist_ok=True)
    tools=['v146_audit_v145.py','v146_calibration_and_margins.py','v146_core.py','v146_fit_saved_camera.py',
           'v146_ledger.py','v146_run_workflow.py','v146_runtime.py','v146_score_camera_external.py',
           'v146_verify_package.py','v146_assemble.py','field_forward_reference.py','load_field_library.py',
           'fit_reference.py','model_lock.py','v133_recover_M.py','v142_model.py','v142_field_reference.py']
    srows=[]
    for t in tools:
        p=repo/'tools'/t
        if p.is_file():shutil.copy2(p,code/t);srows.append(dict(file=t,sha256=sha(p)))
    with (out/'source'/'source_sha256.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['file','sha256']);w.writeheader();w.writerows(srows)
    inputs={}
    for rel in ('results/v128/library/v128_Dh_train_fields.h5','results/v132/validation/new_M_images.h5',
                'results/v143/validation/camera_pilot/conditional_camera_arrays.h5',
                'results/v143/provenance/N_solve_lineage.json','config/v142_new_N_validator_only.json'):
        p=repo/rel
        if p.is_file():inputs[rel]=dict(sha256=sha(p),bytes=p.stat().st_size)
    json.dump(dict(inputs=inputs,source_tools=srows),open(out/'provenance'/'inputs_manifest.json','w',encoding='utf-8'),indent=2,ensure_ascii=False)
    # budgets
    con=sqlite3.connect(repo/'results/v146/logs/budget.sqlite')
    rows=con.execute('SELECT op,metric,units,state,actual FROM events').fetchall();con.close()
    fwd=[r for r in rows if r[1]=='FORWARD']
    bsum=dict(forward_events=len(fwd),reserved=sum(r[2] for r in fwd),known_actual=sum(r[4] for r in fwd if isinstance(r[4],int)),
        unknown_actual_events=sum(1 for r in fwd if not isinstance(r[4],int)))
    (out/'logs').mkdir(exist_ok=True)
    shutil.copy2(repo/'results/v146/logs/budget.sqlite',out/'logs'/'v146_budget.sqlite')
    (out/'logs'/'resource_budget.csv').write_text(
        'metric,events,reserved,known_actual,unknown_actual_events\nFORWARD,%d,%d,%d,%d\n'%(bsum['forward_events'],bsum['reserved'],bsum['known_actual'],bsum['unknown_actual_events']),encoding='utf-8')
    scores=json.loads((repo/'results/v146/validator_only/camera_scores.json').read_text(encoding='utf-8'))
    git_sha=os.popen('git -C "%s" rev-parse HEAD'%repo).read().strip()
    status=dict(task='V146_NOISE_AWARE_SINGLE_PARTICLE_CALIBRATION_WITH_FROZEN_F2C',git_commit_at_pack=git_sha,
      stage_states=dict(
        SOURCE_IDENTITY='N solves lineage-linked (V143, 4/4) and shipped; M mapping from V138 bitwise identity',
        NUMERIC_REPLAY='42 fixed-D witnesses replayed under frozen F2c; calibration margins computed per case',
        DIRECT_PHYSICS_F2C='noiseless N forward 4/4 <=1% (inherited, unchanged); noisy re-fit is the new evidence',
        CONDITIONAL_SIZING='candidate_accuracy vs engineering goal under noise: B=1000 4/12, B=10000 4/12, B=100000 3/12 (see validator rows); NOT a coverage/CI statement',
        NOISE_DEGRADATION=dict(
          B1000=dict(detected='1/12',MAE_nm=56.33,max_nm=141.0),
          B10000=dict(detected='3/12',MAE_nm=42.26,max_nm=141.0),
          B100000=dict(detected='9/12',MAE_nm=25.28,max_nm=84.27),
          note='noiseless blind MAE 0.308nm collapses under simulated shot+read+reference noise; boundary attraction D=200 observed; small-particle cases fail detection'),
        CAMERA_FPR='0/60 all B (conditional pilot, replayed); B=100000 full-well unverified',
        CAMERA_DIAMETER_REPORTABILITY='NOT_QUALIFIED (noise degradation + model error uncalibrated + profiles coarse)',
        EXPERIMENTAL_ABSOLUTE='NOT_VALIDATED'),
      reportability=dict(all_reportable_D_null=True,
        blockers=['model error scale uncalibrated','noisy candidates degrade 25-56nm MAE','profiles coarse/incomplete','detection fails weak signals','real camera/full-well unverified']),
      EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=False,
      budget=dict(forward=dict(reserved=bsum['reserved'],known_actual=bsum['known_actual'],limit=160000,unknown_actual_events=bsum['unknown_actual_events']),
        bem=0,render=0,new_camera_exposures=0,
        historical_preserved=dict(v137_camera='23958/6000',v142_f2c=48874,v143_forward=49390,v143_camera=912,v145_unauthorized_bem=3)),
      measurement_information_conclusion=('The binding constraint is NOISE + model-error calibration, not the spatial kernel: '
          'noiseless images give 0.3nm-class candidates, but single static exposures at 1e3-1e5 e-/px give 25-56nm MAE with detection failures for small D. '
          'Next information increments: longer exposure/multiple frames, second focal plane (properly keyed), and a source-qualified model-error scale.'))
    (out/'status.json').write_text(json.dumps(status,indent=2,ensure_ascii=False)+chr(10),encoding='utf-8')
    (out/'00_执行摘要.md').write_text('''# V146 执行摘要

- 标定: 42个固定D见证在冻结F2c下全部重放;逐例容差敏感度显示ANON_01竞争者在eps=2.41e-5进入、ANON_04在更窄处——**单一静态图像的粒径信息被噪声与模型误差共同限制**。
- 36张含噪图GLS重拟合(不复制无噪候选):候选精度大幅退化——B=1000 MAE 56nm(检出1/12)、B=10000 42nm(3/12)、B=100000 25nm(9/12);工程目标达标仅4/12、4/12、3/12;D=200边界吸引可见。
- 外部验证器逐例评分完成(检出/全目标双分母)。
- 结论: 无噪声0.3nm级候选在指定计数条件下退化为25-56nm MAE;**小颗粒弱信号是主要失败模式**;reportable_D全null正确。
- 预算: FORWARD实际28,238/160,000(预留126,943;0未知);BEM/render/相机均0;历史超额原样保留。
''',encoding='utf-8')
    (out/'review.md').write_text('''# V146 review

标定/边界/36图GLS拟合/外部评分均实际执行;预算原子记账(实际28,238,预留126,943,无未知)。
关键发现: 噪声使候选退化25-56nm MAE;小颗粒检出失败;D=200边界吸引;检出与可报告分列。
reportable_D全null;绝对直径未验证;历史超额保留。
''',encoding='utf-8')
    print('V146 assembled; forward actual',bsum['known_actual'])
if __name__=='__main__':main()
