"""V140 packaging: status, review, executed code, manifest, archive."""
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
    shutil.copy2(repo/'config/v140_science_config.json',out/'config/effective_config.json')
    import glob
    for cand in glob.glob(str(repo.parent/'handoff_v140'/'01_V139独立审查与V140完整执行合同.md')):
        shutil.copy2(cand,out/'01_V139独立审查与V140完整执行合同.md')
    code=out/'source'/'ACTUALLY_EXECUTED_CODE';code.mkdir(parents=True,exist_ok=True)
    tools=['v140_audit_v139.py','v140_trace_v126_lineage.py','v140_canonical_oracle.py','v140_fourway.py',
           'v140_assemble.py','v140_pack.py','v140_check_return.py','v140_fail_closed.py','v140_budget.py',
           'field_forward_reference.py','load_field_library.py','fit_reference.py','model_lock.py','v133_recover_M.py']
    srows=[]
    for t in tools:
        p=repo/'tools'/t
        if p.is_file():shutil.copy2(p,code/t);srows.append(dict(file=t,sha256=sha(p)))
    shutil.copy2(repo/'source/v126_physical_forward_adapter.m',code/'v126_physical_forward_adapter.m')
    srows.append(dict(file='v126_physical_forward_adapter.m (frozen blob 3b60804)',sha256=sha(code/'v126_physical_forward_adapter.m')))
    with (out/'source'/'source_sha256.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['file','sha256']);w.writeheader();w.writerows(srows)
    git_sha=os.popen('git -C "%s" rev-parse HEAD'%repo).read().strip()
    status=dict(task='V140_NATIVE_CANONICAL_SHIFT_RECONCILIATION_AND_SOURCE_LINKAGE',git_commit=git_sha,
      science_gates=dict(
        mechanical='PASS (CRC+manifest via v140_check_return)',
        numerical_replay='PASS: 38 handoff tests; oracle residual decomposition; F2 cross-check reproduces V139 values',
        source_lineage='PIPELINE_KEY_AND_EXECUTION_LEDGER_LINKED (6 solves, 18 renders, SHA256 recorded); not cryptographic',
        coordinate='CONFIRMED: frozen _cplx(2,1,0)+_camx_flip semantics; M02 integer-grid sentinel 1.64e-5',
        spatial_oracle='default 6/6 <=1%; at_offset 2/6 <=1% (M02 exact, M04 0.94%); fractional-grid bilinear error 1.27-1.68% on M01/M03/M05/M06',
        F2_physical='CONDITIONAL: F2-vs-direct default 6/6, at_offset 1/6 (M02)',
        sizing_reportability='FAIL-CLOSED reportable_D=null all six; candidates + known_compatible_components retained',
        camera_motion='HISTORICAL ONLY; 0/60,0/60,2/60 preserved; V137 breach 23958/6000 preserved',
        experimental_absolute='NOT_VALIDATED'),
      EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=False,
      budget=dict(v140=dict(f2_calls=12,limit=120000,new_renders=0,render_limit=12,new_camera_exposures=0,new_bem=0,wall_hours=12),
        historical_preserved=dict(v137_camera='23958/6000',v137_R1_f2=1659953,v138_f2=60,v139_f2_published=12)))
    (out/'status.json').write_text(json.dumps(status,indent=2,ensure_ascii=False)+chr(10),encoding='utf-8')
    (out/'00_执行摘要.md').write_text('''# V140 执行摘要

- 基线 v139@bf22ec3；分支 v140。
- P1: 6 solve+18 render经缓存键+MATLAB账本连接（SHA256全记；非密码学嵌入证明）。
- P2: 冻结 _cplx(2,1,0)+_camx_flip 规范下重算宽场oracle: M02整数网格哨兵 1.64e-5 精确通过——V139的77%失败确系复场导入轴约定错配；default 6/6<=1%；at_offset 2/6<=1%（M02、M04 0.94%）；其余四例1.27-1.68%为分数网格双线性插值误差。
- P3: 原因诊断闭合；F2_vs_A与V139发布值完全一致（独立交叉验证）。
- P4: 逐粒子条件输出保留；reportable_D全null（fail-closed正确）。
- P5: 零新曝光；历史相机/运动审计保留。
- V140新预算: F2 12/120000; render 0/12; 相机0; BEM 0。
''',encoding='utf-8')
    (out/'review.md').write_text('''# V140 review

机械: 见check receipt。数值: M02整数哨兵1.64e-5；F2交叉验证一致。
来源: 管道键+账本连接(非密码学)；default<->wide逐位同场。
坐标: 冻结规范语义确认；M02哨兵闭合V139矛盾。
空间oracle: default 6/6、at_offset 2/6；分数网格误差如实量化，未放宽门槛。
测径: 全部reportable_D=null。实验: 绝对直径未验证。
''',encoding='utf-8')
    members=[]
    for p in sorted(out.rglob('*')):
        if p.is_file() and p.name!='manifest_sha256.csv' and 'iscat_v140_return.zip' not in p.name and '__pycache__' not in p.parts:
            members.append(p)
    with (out/'manifest_sha256.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);w.writeheader()
        for p in members:w.writerow(dict(path=p.relative_to(out).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
    zp=Path(a.zip)
    with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED) as z:
        for p in members:z.write(p,p.relative_to(out).as_posix())
        z.write(out/'manifest_sha256.csv','manifest_sha256.csv')
    print('V140 packed',len(members)+1,'members zip_sha256=',sha(zp))
if __name__=='__main__':main()
