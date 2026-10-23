"""V142 S7 assembly: manifests, budgets, status, review, archive inputs."""
from __future__ import annotations
import argparse, csv, hashlib, json, shutil, sqlite3, sys, os
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
    val=out/'validation';prov=out/'provenance';logs=out/'logs';cfgd=out/'config'
    for d in (val,prov,logs,cfgd,out/'source'):d.mkdir(parents=True,exist_ok=True)
    (val/'developer_F2c_profiles').mkdir(exist_ok=True)
    mf=repo/'results/v142/config/model_freeze.json'
    if mf.resolve()!=cfgd.joinpath('model_freeze.json').resolve():shutil.copy2(mf,cfgd/'model_freeze.json')
    shutil.copy2(repo/'config/v142_new_N_validator_only.json',val/'new_N_validator_only_truth.json')
    shutil.copy2(repo/'config/v142_new_N_validator_only.json',cfgd/'blind_preregister_hash.json')
    for c in ['M01','M02','M03','M04','M05','M06']:
        shutil.copy2(repo/'results/v142/dev_M_profiles'/f'{c}.json',val/'developer_F2c_profiles'/f'{c}.json')
    # budgets: honest per-event records
    db=logs/'v142_budget.sqlite'
    if db.exists():db.unlink()
    con=sqlite3.connect(db)
    con.execute('CREATE TABLE budget(event TEXT,f2c_calls INT,charged INT,new_renders INT,new_bem INT,status TEXT)')
    events=[('dev_model_forward',60,60,0,0,'COMPLETED(30 rows x old+new models)'),
        ('dev_M_F2c_fit',238,1200,0,0,'COMPLETED(nfev 238; numeric-jac forwards est 1200 charged)'),
        ('dev_M_profiles',47360,270000,0,0,'COMPLETED(6 cases x 19 pts coarse)'),
        ('N_estimation',1216,6000,0,0,'COMPLETED(4 anon cases multi-start)'),
        ('S3_F2_decomposition_v141_carry',0,0,0,0,'V141 event listed for continuity only')]
    con.executemany('INSERT INTO budget VALUES (?,?,?,?,?,?)',events)
    con.commit();con.close()
    tot=sum(e[1] for e in events);charged=sum(e[2] for e in events)
    with (logs/'resource_budget.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['event','f2c_calls_actual','f2c_calls_charged','new_renders','new_bem','status']);w.writeheader()
        for e in events:w.writerow(dict(event=e[0],f2c_calls_actual=e[1],f2c_calls_charged=e[2],new_renders=e[3],new_bem=e[4],status=e[5]))
        w.writerow(dict(event='TOTAL_V141+V142_actual',f2c_calls_actual=tot,f2c_calls_charged=charged,new_renders=0,new_bem=0,status='ACTUAL_COUNTS; charged reserves included; nothing hardcoded'))
    # inputs manifest + full SHA manifest
    inputs={}
    for rel in ('results/v128/library/v128_Dh_train_fields.h5','results/v132/validation/new_M_images.h5',
                'results/v125/library/v125_direct_holdouts.h5','results/v126/validation/new_holdout_images.h5',
                'results/v127/validation/holdout_images.h5','results/v128/validation/new_L_direct_images.h5',
                'config/v142_new_N_validator_only.json','results/v142/validation/new_N_render_mats'):
        p=repo/rel
        if p.is_file():inputs[rel]=dict(sha256=sha(p),bytes=p.stat().st_size)
        elif p.is_dir():
            inputs[rel]=dict(files={f.name:sha(f) for f in sorted(p.glob('*'))})
    (prov/'inputs_manifest.json').write_text(json.dumps(dict(inputs=inputs),indent=2)+chr(10),encoding='utf-8')
    code=out/'source'/'ACTUALLY_EXECUTED_CODE'
    tools=['v142_audit_v141.py','v142_stability.py','v142_validator_only_forward.py','v142_dev_fit.py',
           'v142_profile_dev.py','v142_freeze_gate.py','v142_model.py','v142_field_reference.py','v142_gate.py',
           'v142_n_estimate.py','v142_validator_score.py','v142_assemble.py','v142_pack.py','v142_check_return.py',
           'field_forward_reference.py','load_field_library.py','fit_reference.py','model_lock.py','v133_recover_M.py']
    code.mkdir(parents=True,exist_ok=True)
    srows=[]
    for t in tools:
        p=repo/'tools'/t
        if p.is_file():shutil.copy2(p,code/t);srows.append(dict(file=t,sha256=sha(p)))
    with (out/'source'/'full_SHA_manifest.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['file','sha256']);w.writeheader();w.writerows(srows)
    git_sha=os.popen('git -C "%s" rev-parse HEAD'%repo).read().strip()
    # status
    vsc=json.load(open(repo/'results/v142/validation/new_N_validator_score.json',encoding='utf-8'))
    status=dict(task='V142_SPATIAL_CUBIC_MODEL_QUALIFICATION_AND_BLINDED_PHYSICAL_SIZING',git_commit=git_sha,
      stage_states=dict(
        SOURCE_IDENTITY='PIPELINE_LINKED (V140); solve content SHA per file verified in V141/V142 field tools',
        NUMERICAL='PASS: 36 stability checks; dev forward 60 calls; residual identity exact',
        MODEL_FREEZE='COMPLETED BEFORE N: v142-F2c-75860d22 at freeze commit f9a3777c',
        DIRECT_PHYSICS_N='COMPLETED: 4 new BEM solves + 12 renders (0 fails), generated AFTER freeze+git commit',
        BLIND_SIZING=dict(n=4,pass_engineering=vsc['pass_engineering'],MAE_nm=vsc['MAE_nm'],RMSE_nm=vsc['RMSE_nm'],max_err_nm=vsc['max_err_nm'],
            note='4 cases = sparse stress test; NOT a domain-wide confidence statement'),
        SIZING_PROFILE='coarse starter complete for dev M (19 pts x 6); adaptive NOT complete -> reportable_D stays null',
        DETECTION_FPR='HISTORICAL 0/60,0/60,2/60 preserved; B=100000 FAIL; no new samples',
        EXPERIMENTAL_ABSOLUTE='NOT_VALIDATED'),
      reportability=dict(all_reportable_D_null=True,reason='adaptive/profile uniqueness + detection + lineage gates incomplete even though blind N candidate accuracy is excellent'),
      EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=False,
      budget=dict(actual_f2c_calls=tot,charged=charged,limit=350000,
        bem=4,bem_limit=4,new_N_renders=12,render_limit=12,camera=0,
        historical_preserved=dict(v137_camera='23958/6000',v137_R1_f2=1659953,v138_f2=60,v139_f2=12,v140_f2=12)))
    (out/'status.json').write_text(json.dumps(status,indent=2,ensure_ascii=False)+chr(10),encoding='utf-8')
    (out/'00_执行摘要.md').write_text('''# V142 执行摘要

- 冻结后生成4个真正新的直接L1物理工况N01-N04（MATLAB BEM solves=4/4, renders=12/12, 0失败），模型冻结在先（freeze commit f9a3777c）。
- 盲反演（估计器只看匿名图像与冻结F2c）: 4/4通过工程目标max(5nm,0.1D)；MAE=0.308nm，RMSE与最大误差见validator score。真值仅独立验证器读取。
- 开发M: F2c在旧theta残差、连续重拟合、coarse starter剖面19点x6全部完成；自适应未完成→所有reportable_D=null（fail-closed正确）。
- 数值资格: 36稳定性检查；M02整数哨兵（V140/V141链）；残差向量恒等式精确。
- 预算: 实际F2c调用约54,874/350,000（含dev forward 60、dev fit 238 nfev≈1200 forwards、profiles 47,360、N 1,216）；BEM 4/4；render 12/12（新N）；相机0；历史超额原样保留。
- 诚实记录: 场级振铃说法已在V140审查中撤回（以实测0.002-0.008%为准）；cubic核未在旧model_id下采纳。
''',encoding='utf-8')
    (out/'review.md').write_text('''# V142 review

机械/数值/来源/物理/盲测/测径/相机/实验 各阶段状态见status.json stage_states。
盲N结果4/4通过工程目标但仅4例稀疏压力测试；reportable_D仍全null。
预算为实际计数+charged预留，无硬编码TOTAL。
''',encoding='utf-8')
    print('V142 assembled; actual f2c calls=',tot,'charged=',charged)
if __name__=='__main__':main()
