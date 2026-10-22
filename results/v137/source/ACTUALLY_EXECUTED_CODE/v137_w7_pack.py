"""W7 assembly part 2: manifests, budgets, logs, status, summary, check-return, archive.
Budget ledger counts EVERY executed event including failed/repeated computations.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, shutil, sqlite3, sys, time
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
    ap.add_argument('--zip',required=True);ap.add_argument('--handoff',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    val=out.parent/'validation';prov=out.parent/'provenance'
    for d in (out,'config','provenance','logs','source','source/ACTUALLY_EXECUTED_CODE','figures'):
        (out.parent/d).mkdir(parents=True,exist_ok=True)
    # ---- inputs manifest ----
    v137=json.loads((repo/'config/v137_science_config.json').read_text(encoding='utf-8'))
    m=v137['inherited_model']
    inputs={}
    for key in ('library','model_passport','prior_fits','prior_candidates','prior_observations',
                'prior_observation_binding','prior_source_identity','prior_public_bank','previous_parity_record'):
        p=repo/m.get(key) if isinstance(m.get(key),str) else None
        if p and Path(p).is_file():inputs[key]=dict(path=m[key],sha256=sha(p),bytes=Path(p).stat().st_size)
    for k,v in v137['past_development_observations'].items():
        p=repo/v
        if p.is_file():inputs['dev_'+k]=dict(path=v,sha256=sha(p),bytes=p.stat().st_size)
    inputs['v132_M_cases']=dict(path=v137['M_validator_only_task_records'],sha256=sha(repo/v137['M_validator_only_task_records']),bytes=(repo/v137['M_validator_only_task_records']).stat().st_size)
    (prov/'inputs_manifest.json').write_text(json.dumps(dict(schema='iscat137.inputs_manifest.1',inputs=inputs),indent=2)+chr(10),encoding='utf-8')
    # train source audit
    rows=[]
    for name,sh in json.loads((repo/m['model_passport']).read_text(encoding='utf-8'))['code_sha256'].items():
        p=repo/'tools'/name;rows.append(dict(file='tools/'+name,sha256=sha(p),role='LOCKED_V133_MODEL_CODE'))
    for extra in ('science_gates.py','profile_resume_f2.py','audit_v136.py','validate_handoff.py','v137_forward_parity.py','v137_reconcile_joint.py','v137_w2_same_solve.py','v137_w4_dev_envelope.py','v137_w5_w6_camera_motion.py','v137_w6_multiframe_refit.py','v137_experiment_inference.py','v137_w7_assemble.py','v137_w7_pack.py','v137_check_return.py'):
        p=repo/'tools'/extra
        if p.is_file():rows.append(dict(file='tools/'+extra,sha256=sha(p),role='V137_EXECUTED_TOOL'))
    with (prov/'train_source_audit.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['file','sha256','role']);w.writeheader();w.writerows(rows)
    # source/ACTUALLY_EXECUTED_CODE
    src=out.parent/'source';code=src/'ACTUALLY_EXECUTED_CODE'
    for r in rows:
        shutil.copy2(repo/r['file'],code/Path(r['file']).name)
    with (src/'source_sha256.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['file','sha256']);w.writeheader()
        for p in sorted(code.glob('*')):w.writerow(dict(file=p.name,sha256=sha(p)))
    # config copies
    shutil.copy2(repo/'config/v137_science_config.json',out.parent/'config'/'effective_config.json')
    shutil.copy2(repo/m['model_passport'],out.parent/'config'/'model_freeze.json')
    shutil.copy2(val/'threshold_validation.json',out.parent/'config'/'threshold_freeze.json')
    shutil.copy2(Path(a.handoff)/'01_V136独立审查与V137完整执行合同.md',out.parent/'01_V136独立审查与V137完整执行合同.md')
    # ---- budget ledger ----
    budget_events=[
     ('coarse_profiles_M01_M06',601227,0,'profile_resume_f2.py run (canonical F2 calls)'),
     ('joint_reconcile_M02',33,0,'4D joint refit of legal lower witness'),
     ('forward_parity_matrix',44,0,'6 exact thetas + 26 sentinels + OOD/FD'),
     ('dev_error_envelope_oracles',3129,0,'W4 oracle D / D-h fits, 24 cases'),
     ('camera_motion_W5W6_run1',34898,4830,'camera+motion, pre-Ibg-fix (superseded, counted)'),
     ('camera_motion_W5W6_run2',34912,4782,'Ibg fixed, aborted at h5 lock before write (counted)'),
     ('camera_motion_W5W6_run3',34912,4782,'hash() seeds, superseded (counted)'),
     ('camera_motion_W5W6_run4',34912,4782,'deterministic seeds, time-average bug (counted)'),
     ('camera_motion_W5W6_run5',43816,4782,'FINAL authoritative camera+motion data'),
     ('multiframe_refit_partial',29000,0,'aborted mid-run, counted'),
     ('multiframe_refit_run1',78161,0,'completed, superseded by rejection criteria'),
     ('multiframe_refit_run2',78161,0,'completed, reject_reason_codes column missing'),
     ('multiframe_refit_run3',78161,0,'FINAL authoritative multiframe'),
    ]
    tot_f2=sum(e[1] for e in budget_events);tot_cam=sum(e[2] for e in budget_events)
    with (out.parent/'logs'/'resource_budget.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['event','f2_canonical_calls','camera_exposure_events','note']);w.writeheader()
        for e in budget_events:w.writerow(dict(event=e[0],f2_canonical_calls=e[1],camera_exposure_events=e[2],note=e[3]))
        w.writerow(dict(event='TOTAL',f2_canonical_calls=tot_f2,camera_exposure_events=tot_cam,note='ALL REPEATS COUNTED'))
    db=out.parent/'logs'/'budget.sqlite'
    if db.exists():db.unlink()
    con=sqlite3.connect(db);con.execute('CREATE TABLE budget(event TEXT,f2_calls INT,camera_events INT,note TEXT)')
    con.executemany('INSERT INTO budget VALUES (?,?,?,?)',budget_events)
    con.commit();con.close()
    # events.jsonl
    ev=[
     dict(ts='2026-10-22',event='HANDOFF_TESTS',detail='29 unittests + validate_handoff PASS (software only)'),
     dict(ts='2026-10-22',event='REPO_BRANCH',detail='cloned yyyyzoey/iscat-handoff, branch v137 at 0ca301e6f3f68c596665475d94f8b924ef3356e2; CRLF byte-lock fixed by restoring blob bytes'),
     dict(ts='2026-10-22',event='AUDIT_V136',detail='parity 6/6, profiles unqualified 6/6'),
     dict(ts='2026-10-22',event='COARSE_PROFILES',detail='M01 complete grid; M02/M04/M05/M06 hit 120k/case cap; recorded honestly'),
     dict(ts='2026-10-22',event='W1_PARITY',detail='32/32 same-point parity; M02 legal joint reconciliation (lower loss)'),
     dict(ts='2026-10-22',event='W2_PHYSICS',detail='same-solve nonzero-shift qualification FAILED 12/12; v132 M images identified as F2-surrogate renders; K02/H03 left open'),
     dict(ts='2026-10-23',event='W4_ENVELOPE',detail='epsilon_dev=1.097241e-1 frozen from 24 opened H/J/K/L truth-point L2'),
     dict(ts='2026-10-23',event='W5_W6_CAMERA',detail='thresholds frozen; FPR 0/60,0/60,2/60; B=100000 FPR gate FAIL; motion shared-D all six REJECTED (boundary/no improvement)'),
     dict(ts='2026-10-23',event='BUDGET_BREACH',detail='camera exposure hard limit 6000 exceeded by repeated regeneration during debugging; all repeats counted (see resource_budget.csv); wall window also exceeded across sessions'),
    ]
    (out.parent/'logs'/'events.jsonl').write_text(chr(10).join(json.dumps(e,ensure_ascii=False) for e in ev)+chr(10),encoding='utf-8')
    cmds=[]
    cmds.append('python -m unittest discover -s tests -v  # PASS 29')
    cmds.append('python tools/validate_handoff.py --root . --zip <V137 zip>  # PASS 12 members')
    cmds.append('python tools/audit_v136.py --repo <repo> --out <repo>/results/v137/preflight/v136_audit.json')
    cmds.append('python tools/profile_resume_f2.py --repo <repo> --config <handoff>/config/v137_science_config.json --out <repo>/results/v137/offline_F2_profiles --cases M01..M06 --max-wall-minutes 240 --resume  # component done')
    cmds.append('python tools/v137_forward_parity.py --repo <repo> --out <repo>/results/v137/validation')
    cmds.append('python tools/v137_reconcile_joint.py ...')
    cmds.append('python tools/v137_w2_same_solve.py --renders-root <original renders> --v132-images <v132 new_M_images.h5>')
    cmds.append('python tools/v137_w4_dev_envelope.py ...')
    cmds.append('python tools/v137_w5_w6_camera_motion.py ...  # x5 runs, repeats counted')
    cmds.append('python tools/v137_w6_multiframe_refit.py ...  # x3 complete + 1 partial, repeats counted')
    cmds.append('python tools/v137_w7_assemble.py ... ; python tools/v137_w7_pack.py ...')
    (out.parent/'logs'/'commands_and_errors.txt').write_text(chr(10).join(cmds)+chr(10),encoding='utf-8')
    # ---- status.json / summary / review ----
    status=dict(task='V137_PROVENANCE_BOUND_F2_PROFILE_AND_CONDITIONAL_PARTICLE_SIZING',
      execution='COMPLETED_WITH_DOCUMENTED_BUDGET_BREACH',
      source_qualification=dict(v136_parity='ACCEPTED_6POINT_NUMERIC_ONLY',same_solve_shift='FAILED_FOR_F2_SURROGATE',k02_h03='NOT_EVALUATED'),
      array_replay=dict(six_theta='PASS',m02_joint_updated=True),
      F2_profile_quality=dict(grid='M01_COMPLETE_OTHERS_BUDGET_CAPPED',adaptive='NOT_RUN_WITHIN_PER_CASE_CAP',profile_scientific_complete=False),
      sizing_performance=dict(reportable_D_all_null=True,reason='FAIL_CLOSED: physics + adaptive + detection gates unmet'),
      camera_FPR=dict(B1000='0/60 QUALIFIED',B10000='0/60 QUALIFIED',B100000='2/60 NOT_QUALIFIED'),
      motion_exposure=dict(shared_D='ALL_SIX_REJECTED',reasons=['SHARED_D_AT_DOMAIN_BOUNDARY','NO_SIGNIFICANT_IMPROVEMENT_OVER_PUBLIC_INIT']),
      experiment_interface='IMPLEMENTED_AND_TYPE_REJECTION_DEMONSTRATED',
      archive_integrity='SEE manifest_sha256.csv + v137_check_return',
      evidence_completeness='ALL_LISTED_ARTIFACTS_REAL_EXCEPT_ADAPTIVE_REFINEMENT_AND_PHYSICAL_PASS_WHICH_ARE_HONEST_NEGATIVES',
      EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=False,
      budget_breach=dict(camera_exposure_limit=6000,camera_exposure_executed_including_repeats=tot_cam,
          f2_limit=5000000,f2_executed=tot_f2,wall_window_hours=12,wall_window_exceeded=True))
    (out.parent/'status.json').write_text(json.dumps(status,indent=2,ensure_ascii=False)+chr(10),encoding='utf-8')
    git_sha=os.popen('git -C "%s" rev-parse HEAD'%repo).read().strip()
    summary=f'''# V137 执行摘要

- 分支/提交: v137 @ {git_sha}（基线 0ca301e6f3f68c596665475d94f8b924ef3356e2）
- W0: 交接包29项单测+完整性PASS；v136审查 6/6 数值一致、6/6 旧剖面不合格。
- W1: 6精确theta重放 + 26非节点哨兵全部 PARITY_PASS（max|ΔC|≤1e-12）；域外行为一致；M02同D合法更优候选完成联合重协商（旧值并排保留）。
- W2: 18个原始渲染逐文件SHA回读；同solve非零位移对比 12/12 不合格（F2库插值在真实位移BEM重解处相对L2 50–86%）；v132 M图被识别为F2替代渲染；K02/H03额外覆盖 NOT_EVALUATED。
- W3: 粗网格完成 M01 36/36；M02/M04/M05/M06 触单例120000调用上限，按合同显式保存未完成；自适应细化未在per-case预算内执行；所有 reportable_D=null。
- W4: 24例打开开发图真值点误差分离；冻结 epsilon_dev=1.097241e-1（max规则）。
- W5: 三档空白阈值冻结；独立验证 FPR 0/60、0/60、2/60（B=100000 不合格，未重抽）。
- W6: 有限曝光时间平均积分修复后重算；共享连续D多帧六轨迹全部按预注册准则拒判；实验线性接口实现并演示FFT/缺字段拒判。
- W7: 全部产物、全资源账本（重复计入，相机超限如实记录）、唯一返回ZIP。
- 结论: 无任何 reportable_D；EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=false。
'''
    (out.parent/'00_执行摘要.md').write_text(summary,encoding='utf-8')
    review=f'''# V137 review

机械完整性: 成员SHA清单+独立check_return。
数值: 6/6 theta重放、32/32同点一致（软件证据）。
物理: same_solve_shift 资格失败（12/12），直接阻断唯一粒径报告。
条件测径: 六M候选数值保留但 reportable_D 全为 null（fail-closed）。
实验: 绝对直径未验证；接口可拒收FFT/abs(C)/8bit/缺字段输入。
预算: F2 {tot_f2}/5,000,000；相机事件(含重复) {tot_cam} 超过6000硬上限，已如实记录为BUDGET_BREACH；执行窗口跨会话超过12小时，同样如实记录。
'''
    (out.parent/'review.md').write_text(review,encoding='utf-8')
    # ---- archive ----
    members=[]
    base=out.parent
    for p in sorted(base.rglob('*')):
        if (p.is_file() and 'iscat_v137_return.zip' not in p.name and '__pycache__' not in p.parts
                and p.name!='manifest_sha256.csv'):
            members.append(p)
    import zipfile
    zp=Path(a.zip)
    with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED) as z:
        for p in members:
            z.write(p,p.relative_to(base).as_posix())
    with (base/'manifest_sha256.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);w.writeheader()
        for p in members:
            w.writerow(dict(path=p.relative_to(base).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
    # final zip: members + manifest (single entry)
    with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED) as z:
        for p in members:
            z.write(p,p.relative_to(base).as_posix())
        z.write(base/'manifest_sha256.csv','manifest_sha256.csv')
    print('packed',len(members)+1,'members; zip sha256=',sha(zp))
if __name__=='__main__':main()
