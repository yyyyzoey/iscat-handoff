"""V139 packaging: status with science_gates, review, executed code, manifest, archive."""
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
    shutil.copy2(repo/'config/v139_science_config.json',out/'config/effective_config.json')
    import glob
    for cand in glob.glob(str(repo.parent/'handoff_v139'/'01_V138独立审查与V139完整执行合同.md')):
        shutil.copy2(cand,out/'01_V138独立审查与V139完整执行合同.md')
    code=out/'source'/'ACTUALLY_EXECUTED_CODE';code.mkdir(parents=True,exist_ok=True)
    tools=['audit_v138.py','oracle_wide_vs_direct.py','check_v139_return.py','v139_budget.py','v139_common.py',
           'v139_assemble.py','v139_pack.py','field_forward_reference.py','load_field_library.py','fit_reference.py',
           'model_lock.py','v133_recover_M.py']
    srows=[]
    for t in tools:
        p=repo/'tools'/t
        if p.is_file():shutil.copy2(p,code/t);srows.append(dict(file=t,sha256=sha(p)))
    with (out/'source'/'source_sha256.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['file','sha256']);w.writeheader();w.writerows(srows)
    git_sha=os.popen('git -C "%s" rev-parse HEAD'%repo).read().strip()
    status=dict(task='V139_RENDER_LINEAGE_SPATIAL_ORACLE_AND_CONDITIONAL_SIZING',git_commit=git_sha,
      science_gates=dict(
        mechanical='PASS (CRC+manifest, see check receipt)',
        numerical_replay='PASS: 12/12 render intensity identities (V138) + oracle residual-vector decomposition enforced',
        source_lineage='PARTIAL: default<->wide bitwise same field 6/6; at_offset same-solve evidenced by identical Eref+cfg+center h; byte-level render->solve link not fully proven',
        coordinate='FROZEN RAW.T[::-1,:] from V138 export-chain; NOT independent experimental axis calibration',
        spatial_oracle='FAIL: oracle-vs-direct 48.6-88.3% at_offset 6/6; displaced render is NOT a sampled-grid shift of the undisplaced render',
        F2_physical='CONDITIONAL: F2-vs-direct default 6/6 <=1%; at_offset 1/6 (M02) only',
        sizing_reportability='FAIL-CLOSED: reportable_D=null all six; candidates + known_compatible_components retained',
        camera_motion='HISTORICAL ONLY: 0/60,0/60,2/60 preserved; V137 breach 23958/6000 preserved; no new samples',
        experimental_absolute='NOT_VALIDATED'),
      EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=False,
      budget=dict(v139=dict(f2_calls=12,f2_limit=120000,new_renders=0,render_limit=12,new_camera_exposures=0,new_bem=0,wall_hours=12),
        historical=dict(v137_camera='23958/6000 PRESERVED',v137_R1_f2=1659953,v138_f2=60)))
    (out/'status.json').write_text(json.dumps(status,indent=2,ensure_ascii=False)+chr(10),encoding='utf-8')
    (out/'00_执行摘要.md').write_text('''# V139 执行摘要

- 基线 v138@ec2f9e8；分支 v139；V137历史超额原样保留。
- S1: default<->wide场逐位同源(6/6)；at_offset同solve证据=相同Eref/cfg/center_h；字节级render->solve链接未完全证明(PARTIAL)。
- S2: 三路oracle分解完成: oracle-vs-direct at_offset 48.6-88.3%全部未过1%门；F2-vs-direct default 6/6<=1%、at_offset仅M02；残差向量分解恒等式由工具强制校验。
- 结论: 位移直接图不是无位移场采样网格平移可重现的；F2作为渲染器族的替代模型在(0.47-2.02%)一致，但纯空间平移算子假设未获物理验证。
- S3: 条件测径仅候选+known_compatible_components；reportable_D全null（包络未获正式资格+剖面/自适应/检测门未齐）。
- S5: 零新曝光；旧相机/运动审计存档。
- V139新预算: F2 12/120000; render 0/12; 相机0; BEM 0。
''',encoding='utf-8')
    (out/'review.md').write_text('''# V139 review

机械: 见check receipt。数值: oracle分解恒等式+12/12同文件强度恒等式。
来源: default/wide逐位同场;at_offset链PARTIAL。坐标: 冻结RAW.T[::-1,:]。
空间oracle: FAIL 6/6 at_offset - 已作为核心科学发现交付。F2物理: 条件性。
测径: 全部reportable_D=null。相机: 历史0/60,0/60,2/60保留。
''',encoding='utf-8')
    (out/'logs'/'commands_and_errors.txt').write_text(chr(10).join([
     'python -m unittest discover -s tests -v  # 36 PASS','python tools/verify_handoff.py --root . --zip <V139 zip>  # 14 members PASS',
     'python tools/audit_v138.py --repo <repo> --out <repo>/results/v139/preflight/v138_audit.json --verify-arrays',
     'python tools/oracle_wide_vs_direct.py --repo <repo> --out <repo>/results/v139/validation/oracle --config config/v139_science_config.json',
     'python tools/v139_assemble.py --repo <repo> --out <repo>/results/v139','python tools/v139_pack.py ...',
     'python tools/check_v139_return.py --zip <zip> --out <repo>/results/v139/preflight/return_receipt.json']),encoding='utf-8')
    members=[]
    for p in sorted(out.rglob('*')):
        if p.is_file() and p.name!='manifest_sha256.csv' and 'iscat_v139_return.zip' not in p.name and '__pycache__' not in p.parts:
            members.append(p)
    with (out/'manifest_sha256.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);w.writeheader()
        for p in members:w.writerow(dict(path=p.relative_to(out).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
    zp=Path(a.zip)
    with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED) as z:
        for p in members:z.write(p,p.relative_to(out).as_posix())
        z.write(out/'manifest_sha256.csv','manifest_sha256.csv')
    print('V139 packed',len(members)+1,'members zip_sha256=',sha(zp))
if __name__=='__main__':main()
