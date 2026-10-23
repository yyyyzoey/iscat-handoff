"""V141 packaging: status with explicit stage states, review, executed code, manifest, archive."""
from __future__ import annotations
import argparse, csv, hashlib, json, os, shutil, zipfile
from pathlib import Path
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True);ap.add_argument('--zip',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    (out/'config').mkdir(exist_ok=True)
    shutil.copy2(repo/'config/v141_science_config.json',out/'config/effective_config.json')
    import glob
    for cand in glob.glob(str(repo.parent/'handoff_v141'/'01_V140独立审查与V141完整执行合同.md')):
        shutil.copy2(cand,out/'01_V140独立审查与V141完整执行合同.md')
    code=out/'source'/'ACTUALLY_EXECUTED_CODE';code.mkdir(parents=True,exist_ok=True)
    tools=['v141_audit_v140.py','v141_field_level.py','v141_field_verdict.py','v141_common.py','v141_s3_s6.py',
           'v141_pack.py','v141_check_return.py','v141_budget.py','field_forward_reference.py','load_field_library.py',
           'fit_reference.py','model_lock.py','v133_recover_M.py']
    srows=[]
    for t in tools:
        p=repo/'tools'/t
        if p.is_file():shutil.copy2(p,code/t);srows.append(dict(file=t,sha256=sha(p)))
    with (out/'source'/'source_sha256.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['file','sha256']);w.writeheader();w.writerows(srows)
    git_sha=os.popen('git -C "%s" rev-parse HEAD'%repo).read().strip()
    status=dict(task='V141_SUBPIXEL_COMPLEX_FIELD_ERROR_SEPARATION_AND_QUALIFIED_SIZING',git_commit=git_sha,
      stage_states=dict(
        SOURCE_IDENTITY='PARTIAL_PASS: pipeline-key+ledger linked; solve content SHA verified per file; no embedded cryptographic proof',
        SOURCE_FIELD_REPLAY='PASS: direct-field C replay max_abs 5.17e-16-6.86e-16 across 12 variants',
        SPATIAL_INTERPOLATION='DIAGNOSED: bilinear fractional-grid error 0.94-1.68% (M02 integer exact 1.6e-5); S2 cubic kernel passes image gate 6/6 BUT field-level ringing 600-760% -> NOT adopted; new spatial_kernel_id+model_id required for formal use',
        D_H_MODEL='CONDITIONAL: frozen F2 vs direct default 6/6<=1%, at_offset 1/6 (M02); three-way residual identity exact',
        SIZING_PROFILE='NOT_EXTENDED this round (forward qualification partial); historic R1 profiles retained',
        DETECTION_FPR='HISTORICAL 0/60,0/60,2/60 preserved (B=100000 FAIL); no new samples',
        EXPERIMENTAL_ABSOLUTE='NOT_VALIDATED'),
      reportability=dict(all_six_reportable_D_null=True,
        note='candidates + known_compatible_components retained; dev epsilon 0.003004 still lineage-unqualified'),
      EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=False,
      budget=dict(v141=dict(f2_calls=6,limit=120000,new_renders=0,render_limit=12,new_camera_exposures=0,new_bem=0),
        v140_budget_reconciliation='BUDGET_RECONCILIATION_CONFIRMED (6+6=12 actual calls; failed first run counted)',
        historical_preserved=dict(v137_camera='23958/6000',v137_R1_f2=1659953,v138_f2=60,v139_f2=12,v140_f2=12)))
    (out/'status.json').write_text(json.dumps(status,indent=2,ensure_ascii=False)+chr(10),encoding='utf-8')
    (out/'00_执行摘要.md').write_text('''# V141 执行摘要

- 基线 v140@81dc2dc；分支 v141。
- S0: 身份冻结、40字符blob校验（V140的41字符typo已归档为历史）、V140账本调和确认（6+6=12次真实F2调用，两次运行均计入）。
- S1 场级误差分离（24行,0错误）：M02整数哨兵双线性精确(1.6e-5)；分数网格双线性场误差0.91-1.80%→图像0.94-1.68%；**证实V140剩余误差确为双线性空间插值**。
- S2: S2_CUBIC核图像级6/6<=1%，但场级振铃600-760%——如实记录，未采纳换核；正式采用需新spatial_kernel_id+model_id并全部重资格。
- S3: 三元分解 (F2-direct)=(F2-oracle)+(oracle-direct) 逐像元恒等式精确(0.0)。
- S4: 六M reportable_D=null（候选+兼容区保留；开发MAE 2.75nm不称实验精度）。
- S5: 零新曝光；历史相机/运动审计保留。
- V141新预算: F2 6/120000; render 0/12; 相机0; BEM 0。
''',encoding='utf-8')
    (out/'review.md').write_text('''# V141 review

机械: 见check receipt。数值: 场级分离24/24完成; 三元恒等式精确。
空间: 双线性误差定量化; cubic图像过门但场级振铃巨大——未采纳，不夸大。
测径: reportable_D全null正确; 无真值泄漏。实验: 绝对直径未验证。
''',encoding='utf-8')
    members=[]
    for p in sorted(out.rglob('*')):
        if p.is_file() and p.name!='manifest_sha256.csv' and 'iscat_v141_return.zip' not in p.name and '__pycache__' not in p.parts:
            members.append(p)
    with (out/'manifest_sha256.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);w.writeheader()
        for p in members:w.writerow(dict(path=p.relative_to(out).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
    zp=Path(a.zip)
    with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED) as z:
        for p in members:z.write(p,p.relative_to(out).as_posix())
        z.write(out/'manifest_sha256.csv','manifest_sha256.csv')
    print('V141 packed',len(members)+1,'members zip_sha256=',sha(zp))
if __name__=='__main__':main()
