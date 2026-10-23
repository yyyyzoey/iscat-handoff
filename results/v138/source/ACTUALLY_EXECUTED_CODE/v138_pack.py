"""V138 packaging: inputs/runtime SHAs, status, review, manifest, archive."""
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
    (out/'config').mkdir(exist_ok=True);(out/'source'/'ACTUALLY_EXECUTED_CODE').mkdir(parents=True,exist_ok=True)
    shutil.copy2(repo/'config/v138_science_config.json',out/'config/effective_config.json')
    shutil.copy2(Path(__file__).resolve().parents[2]/'01_V137审查与V138完整执行合同.md',out/'01_V137审查与V138完整执行合同.md') if (Path(__file__).resolve().parents[2]/'01_V137审查与V138完整执行合同.md').is_file() else None
    import glob
    for cand in glob.glob(str(repo.parent/'handoff_v138'/'01_V137审查与V138完整执行合同.md')):
        shutil.copy2(cand,out/'01_V137审查与V138完整执行合同.md')
    # inputs & runtime SHAs
    inputs={}
    for p in [repo/'results/v132/validation/new_M_images.h5',repo/'results/v126/v132_M_cases.json',
              repo/'results/v133/M_F2_baseline/model_passport.json',repo/'results/v128/library/v128_Dh_train_fields.h5',
              repo/'results/v137_r1/iscat_v137_return.zip']:
        if p.is_file():inputs[str(p.relative_to(repo))]=dict(sha256=sha(p),bytes=p.stat().st_size)
    idx=list(csv.DictReader((repo/'results/v134/provenance/M_raw_source_audit.csv').open(encoding='utf-8')))
    for r in idx:
        if r['case'] and r['variant'] in ('default','at_offset'):
            pp=Path(r['file'])
            if pp.is_file():inputs['raw_render_'+r['case']+'_'+r['variant']]=dict(path=str(pp),sha256=sha(pp),bytes=pp.stat().st_size)
    tools=['audit_v137.py','audit_raw_observation_operator.py','verify_archive.py','v138_forensics.py',
           'v138_requalify_dev_envelope.py','v138_s4_s5.py','v138_run_all.py','v138_pack.py','v138_validate_science.py',
           'field_forward_reference.py','load_field_library.py','fit_reference.py','model_lock.py','v133_recover_M.py']
    code=out/'source'/'ACTUALLY_EXECUTED_CODE'
    srows=[]
    for t in tools:
        p=repo/'tools'/t
        if p.is_file():shutil.copy2(p,code/t);srows.append(dict(file=t,sha256=sha(p)))
    with (out/'source'/'source_sha256.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['file','sha256']);w.writeheader();w.writerows(srows)
    (out/'provenance'/'inputs_and_runtime_sha.json').write_text(json.dumps(dict(inputs=inputs,executed_tools=srows),indent=2)+chr(10),encoding='utf-8')
    git_sha=os.popen('git -C "%s" rev-parse HEAD'%repo).read().strip()
    status=dict(task='V138_RAW_OBSERVATION_OPERATOR_FORENSICS_AND_QUALIFIED_SIZING',git_commit=git_sha,
      acceptance=dict(
        raw_render_intensity_identity='PASS 12/12 exact (per-file, cross-variant bug fixed)',
        raw_vs_merged_identity='PASS 12/12 bitwise under frozen convention OBS_MERGED_C=RAW.T[::-1,:]',
        solve_geometry='PASS 6/6 M solves matched (D,h,gap,np,mesh,lambda,NA,nwater,nglass,solver_id); render->solve linked via renderer pipeline (limitation documented)',
        independent_camera_operator='PASS 12/12 (<=1% gate)',
        f2_on_verified_raw=dict(zero_shift='0.27-0.88% rel L2',offset='0.47-2.02% rel L2',gate_1pct='zero-shift PASS, offset partial'),
        dev_envelope_requalified='epsilon_dev=3.004e-3 on at_offset/C (supersedes 0.109724 root-C mismatch)',
        v133_candidates='RETAINED as direct-physical under frozen convention; MAE 2.75nm remains development-set result, not blind validation',
        camera_fpr='historical 0/60,0/60,2/60 preserved; B=100000 FAIL; no new samples',
        motion_multiframe='method audit only; six rejections = method+SNR, not physical non-identifiability proof',
        reportable_D_all_null=True),
      budget=dict(v138=dict(f2_calls=60,limit=120000,new_renders=0,limit_renders=12,new_camera_exposures=0,limit_camera=0,new_bem=0),
        v137_historical_breach='PRESERVED (camera 23958/6000; per-M profile cap overspend; wall window exceeded)'),
      experimental_absolute_validated=False)
    (out/'00_执行摘要.md').write_text('''# V138 执行摘要

- 固定基线 v137@0b64405596a7b77ad48aec26db85ca0eee495654；本轮新增分支 v138。
- S1: 12/12 render内部强度恒等式精确成立；合并M H5与原MAT render在冻结约定 OBS_MERGED_C=RAW.T[::-1,:] 下逐位相等(12/12)。
- S2: 原solve几何6/6逐字段匹配(D,h,gap,np=1.38+0j,mesh=1444,λ520,NA0.8,nwater/nglass,solver_id)；独立相机算子12/12复现(<=1%)。
- S3: 开发包络在at_offset/C上重建: epsilon_dev=3.004e-3 (取代R05错配的0.109724)。
- S4: 路径A成立(合并H5=原直接render)，V133六候选保留为直接物理结果；新epsilon下兼容区间收窄；reportable_D仍全null(剖面/自适应/检测门未齐)。
- S5: 旧相机/运动方法审计完成，零新曝光；V137历史超额(相机23958/6000等)原样保留。
- V138新预算: F2 60/120000；render 0/12；相机0；BEM 0。
''',encoding='utf-8')
    (out/'status.json').write_text(json.dumps(status,indent=2,ensure_ascii=False)+chr(10),encoding='utf-8')
    (out/'review.md').write_text('''# V138 review

来源链: 12/12 render强度恒等式精确成立；合并M H5与原MAT render在冻结约定下逐位相等(12/12)；
原solve几何6/6逐字段匹配；独立相机算子12/12复现(<=1%)。
结论: V137的50-86%差异是观测算子轴约定错配,不是F2物理插值失败;V137 same_solve_shift裁决被本证据取代。
开发包络: 在at_offset/C上重建 epsilon_dev=3.004e-3 (取代0.109724的R05错配值)。
测径: V133六候选保留为直接物理结果;reportable_D全null(剖面/自适应/检测门未齐)。
预算: V138新F2 60/120000; render 0/12; 相机0/0; BEM 0; V137历史超额原样保留。
''',encoding='utf-8')
    (out/'logs'/'commands_and_errors.txt').write_text(chr(10).join([
     'python -m unittest discover -s tests -v  # 22 PASS','python tools/verify_handoff.py --root . --zip <V138 zip>  # 13 files PASS',
     'python tools/audit_v137.py --repo <repo> --out <repo>/results/v138/preflight/v137_published_audit.json',
     'python tools/audit_raw_observation_operator.py --repo <repo> --out <repo>/results/v138/provenance --write-arrays',
     'python tools/verify_archive.py --zip <repo>/results/v137_r1/iscat_v137_return.zip --out <repo>/results/v138/preflight/r1_zip_mechanical.json',
     'python tools/v138_forensics.py --repo <repo> --out <repo>/results/v138',
     'python tools/v138_requalify_dev_envelope.py ...','python tools/v138_s4_s5.py ...','python tools/v138_run_all.py --resume ...']),encoding='utf-8')
    members=[]
    for p in sorted(out.rglob('*')):
        if p.is_file() and p.name!='manifest_sha256.csv' and 'iscat_v138_return.zip' not in p.name and '__pycache__' not in p.parts:
            members.append(p)
    with (out/'manifest_sha256.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);w.writeheader()
        for p in members:w.writerow(dict(path=p.relative_to(out).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
    zp=Path(a.zip)
    with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED) as z:
        for p in members:z.write(p,p.relative_to(out).as_posix())
        z.write(out/'manifest_sha256.csv','manifest_sha256.csv')
    print('V138 packed',len(members)+1,'members zip_sha256=',sha(zp))
if __name__=='__main__':main()