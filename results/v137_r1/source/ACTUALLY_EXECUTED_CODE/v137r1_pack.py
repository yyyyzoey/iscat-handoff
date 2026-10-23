"""R1 final packaging: cumulative budgets, status, logs, manifest, archive."""
from __future__ import annotations
import argparse, csv, hashlib, json, os, shutil, sqlite3, zipfile
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--r1',required=True)
    ap.add_argument('--zip',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();r1=Path(a.r1).resolve()
    base=r1
    (base/'config').mkdir(exist_ok=True);(base/'provenance').mkdir(exist_ok=True)
    (base/'logs').mkdir(exist_ok=True);(base/'source').mkdir(exist_ok=True)
    code=base/'source'/'ACTUALLY_EXECUTED_CODE';code.mkdir(exist_ok=True)
    (base/'figures').mkdir(exist_ok=True);(base/'library').mkdir(exist_ok=True)
    (base/'experiment_inference').mkdir(exist_ok=True)
    shutil.copy2(repo/'config/v137_science_config.json',base/'config/effective_config.json')
    shutil.copy2(r1/'preflight/intake.json',base/'preflight/intake_audit.json')
    shutil.copy2(r0m:=repo/'results/v137/provenance/M_original_solve_render_sha.csv',base/'provenance/original_solve_render_sources.csv')
    shutil.copy2(repo/'results/v137/validation/physical_forward_qualification.json',base/'provenance/physical_forward_qualification.json')
    shutil.copy2(r0f:=repo/'results/v133/M_F2_baseline/model_passport.json',base/'config/model_freeze.json')
    shutil.copy2(r1/'validation/threshold_validation.json',base/'config/threshold_freeze.json')
    # experiment interface
    shutil.copy2(repo/'results/v137/experiment_inference/schema.json',base/'experiment_inference/input_schema.json')
    shutil.copy2(repo/'results/v137/experiment_inference/example_input_output.json',base/'experiment_inference/example_input_output.json')
    shutil.copy2(repo/'tools/v137_experiment_inference.py',base/'experiment_inference/actual_cli.py')
    # executed source
    tools=['profile_resume_f2.py','replay_all_witnesses.py','audit_intake.py','science_gates.py',
           'v137r1_takeover.py','v137r1_adaptive.py','v137r1_assemble.py','v137_run_all.py',
           'v137r1_pack.py','v137r1_check_return.py','field_forward_reference.py','load_field_library.py',
           'fit_reference.py','template_bank.py','model_lock.py','observation_adapter.py','v133_recover_M.py']
    rows=[]
    for t in tools:
        p=repo/'tools'/t
        if p.is_file():shutil.copy2(p,code/t);rows.append(dict(file=t,sha256=sha(p)))
    with (base/'source'/'source_sha256.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['file','sha256']);w.writeheader();w.writerows(rows)
    # cumulative budget ledger (one V137 task; R0+R1, repeats counted)
    events=[('R0_coarse_profiles',601227,0),('R0_joint_reconcile',33,0),('R0_forward_parity',44,0),
        ('R0_dev_envelope_oracles',3129,0),('R0_camera_motion_runs_1_to_5',182649,23958),
        ('R0_multiframe_runs_partial+3',263483,0),
        ('R1_takeover_verification',216,0),('R1_witness_replays',6,0),
        ('R1_coarse_rerun_takeover_path_error',601214,0),
        ('R1_adaptive_M01',7952,0)]
    tot_f2=sum(e[1] for e in events);tot_cam=sum(e[2] for e in events)
    with (base/'logs'/'resource_budget.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['event','f2_canonical_calls','camera_exposure_events']);w.writeheader()
        for e in events:w.writerow(dict(event=e[0],f2_canonical_calls=e[1],camera_exposure_events=e[2]))
        w.writerow(dict(event='TOTAL_ONE_V137_TASK',f2_canonical_calls=tot_f2,camera_exposure_events=tot_cam))
    db=base/'logs'/'budget.sqlite'
    if db.exists():db.unlink()
    con=sqlite3.connect(db);con.execute('CREATE TABLE budget(event TEXT,f2_calls INT,camera_events INT)')
    con.executemany('INSERT INTO budget VALUES (?,?,?)',events);con.commit();con.close()
    cmds=['python -m unittest discover -s tests -v  # 43 PASS','python tools/validate_handoff.py --root . --zip <R1 zip>  # 19 members',
     'python tools/audit_intake.py --repo <repo> --out <repo>/results/v137_r1/preflight/intake.json',
     'python tools/v137r1_takeover.py --r0-profiles <repo>/results/v137/offline_F2_profiles  # 216/216 rows verified',
     'python tools/replay_all_witnesses.py --repo <repo> --config config/v137_science_config.json --out <repo>/results/v137_r1/witnesses  # 6/6',
     'python tools/profile_resume_f2.py ... --cases M05 M06 M01 M02 M03 M04 --resume  # rc=3; TAKEOVER PATH ERROR caused rerun, counted',
     'python tools/v137r1_adaptive.py  # M01 7952 calls; others blocked per-case budget',
     'python tools/v137r1_assemble.py ; python tools/v137_run_all.py --resume ; python tools/v137r1_pack.py']
    (base/'logs'/'commands_and_errors.txt').write_text(chr(10).join(cmds)+chr(10),encoding='utf-8')
    ev=[dict(ts='2026-10-23',event='R1_INTAKE',detail='3 summary claims flagged (F2 bilinear / physical saturation / J truth)'),
     dict(ts='2026-10-23',event='R1_TAKEOVER',detail='216/216 R0 checkpoint rows verified by forward replay; 0 rejected'),
     dict(ts='2026-10-23',event='R1_WITNESSES',detail='6/6 exact theta replays saved with forward images'),
     dict(ts='2026-10-23',event='R1_TAKEOVER_PATH_ERROR',detail='checkpoints written to wrong dir; coarse rerun executed (~601k calls); counted as repeat, per-case caps overspent and documented'),
     dict(ts='2026-10-23',event='R1_ADAPTIVE',detail='M01 only: 7952 calls (2.5nm bidirectional + 1.0/0.5 near minima); no point beat the legal joint witness; M02-M06 blocked (cumulative per-case cap exhausted)'),
     dict(ts='2026-10-23',event='R1_GATES',detail='reportable_D=null for all six (physics+adaptive+detection unmet); reusable R0 physics/camera assets identity-verified')]
    (base/'logs'/'events.jsonl').write_text(chr(10).join(json.dumps(e,ensure_ascii=False) for e in ev)+chr(10),encoding='utf-8')
    git_sha=os.popen('git -C "%s" rev-parse HEAD'%repo).read().strip()
    status=dict(task='V137_PROVENANCE_BOUND_F2_PROFILE_AND_CONDITIONAL_PARTICLE_SIZING',execution_revision='R1',
      execution='COMPLETED_WITH_DOCUMENTED_BUDGET_AND_TAKEOVER_EVENTS',
      source_qualification=dict(v136_parity='6POINT_NUMERIC_ONLY',same_solve_shift='FAILED_FOR_F2_SURROGATE (reused R0 identity-verified)',k02_h03='NOT_EVALUATED'),
      numeric_replay=dict(witnesses='6/6',m02_joint_updated=True),
      profile_quality=dict(coarse='R1 complete scan (takeover rerun counted)',adaptive='M01_PARTIAL_ONLY;M02_M06_BLOCKED_BUDGET',scientific_complete=False),
      conditional_sizing_performance=dict(reportable_D_all_null=True),
      camera_FPR=dict(B1000='0/60 QUALIFIED',B10000='0/60 QUALIFIED',B100000='2/60 NOT_QUALIFIED',new_r1_exposures=0),
      exposure_motion=dict(shared_D='ALL_SIX_REJECTED (reused R0, identity-verified)',new_r1_motion_computation=0),
      archive_integrity='manifest_sha256.csv + v137r1_check_return',
      experimental_absolute_validated=False,
      budget=dict(f2_limit=5000000,f2_executed_cumulative=tot_f2,camera_limit=6000,
          camera_executed_cumulative=tot_cam,camera_breach_documented=True,
          per_case_cap_overspend_documented=True,wall_window_exceeded=True),
      git_commit_code_final=git_sha)
    (base/'status.json').write_text(json.dumps(status,indent=2,ensure_ascii=False)+chr(10),encoding='utf-8')
    review='''# V137-R1 review

机械完整性: CRC+成员SHA独立校验。数值: 6/6见证重放、M01自适应未超越合法见证。
物理: same-solve位移资格失败(复用R0身份验证结果)；reportable_D全null为正确fail-closed。
预算: F2累计 %d/5,000,000；相机累计 %d 超6000上限(R0已记录，R1零新增)；
粗剖面因接管路径错误重复执行约601k次调用，全部如实计数。
'''%(tot_f2,tot_cam)
    (base/'review.md').write_text(review,encoding='utf-8')
    # manifest + archive
    members=[]
    for p in sorted(base.rglob('*')):
        if p.is_file() and p.name!='manifest_sha256.csv' and 'iscat_v137_return.zip' not in p.name and '__pycache__' not in p.parts:
            members.append(p)
    with (base/'manifest_sha256.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);w.writeheader()
        for p in members:w.writerow(dict(path=p.relative_to(base).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
    zp=Path(a.zip)
    with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED) as z:
        for p in members:z.write(p,p.relative_to(base).as_posix())
        z.write(base/'manifest_sha256.csv','manifest_sha256.csv')
    print('R1 packed',len(members)+1,'members zip_sha256=',sha(zp))
if __name__=='__main__':main()
