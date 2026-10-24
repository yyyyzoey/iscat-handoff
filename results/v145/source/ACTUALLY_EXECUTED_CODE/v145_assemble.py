"""V145 P7/P8 assembly: honest budgets (incl. BEM violation), summaries, status."""
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
    val=out/'validation';prov=out/'provenance';logs=out/'logs'
    (out/'config').mkdir(exist_ok=True)
    shutil.copy2(repo/'config/v145_science_config.json',out/'config/effective_config.json')
    # fixed_D summary from per-point files
    import glob
    summary={}
    for cdir in sorted((val/'fixed_D_profiles').glob('*')):
        if not cdir.is_dir():continue
        case=cdir.name
        pts=[];unknown=[]
        for p in sorted(cdir.glob('*.json')):
            if p.name=='input_identity.json':continue
            try:d=json.loads(p.read_text(encoding='utf-8'))
            except Exception:continue
            res=d.get('result')
            if not res:continue
            th=res.get('best',{}).get('theta')
            tgt=float(d.get('target_D'))
            D_res=float(res.get('fixed_D'))
            fixed_ok=bool(abs(D_res-tgt)<=1e-10)
            pts.append(dict(target_D=tgt,optimized_D=D_res,fixed_D_identity_ok=fixed_ok,
                loss_L2=res['best']['loss_L2'],theta=th,origin=res['best'].get('source',''),
                n_valid_witnesses=len(res.get('valid_witnesses',[])),
                point_search_complete=res.get('point_search_complete'),
                forward_calls=res.get('actual_f2c_callbacks'),checkpoint=p.name))
            if not fixed_ok:unknown.append(dict(target_D=tgt,optimized_D=D_res,checkpoint=p.name,
                classification='V144_STYLE_4D_LEAKAGE_IF_FROM_V144; V145 points enforce identity'))
        worst=min((p['loss_L2'] for p in pts),default=None)
        summary[case]=dict(n_points=len(pts),finite_witnesses=[p for p in pts],
            min_loss_L2=worst,
            unknown_D=[u for u in unknown],
            point_search_complete_all=bool(pts) and all(p['point_search_complete'] for p in pts),
            adaptive_coverage_complete=False)
    (val/'fixed_D_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+chr(10),encoding='utf-8')
    # budgets
    con=sqlite3.connect(logs/'v145_budget.sqlite')
    rows=con.execute('SELECT op,metric,reserved,state,actual FROM events').fetchall()
    con.close()
    from collections import Counter
    agg=Counter()
    for r in rows:agg[(r[1],r[3])]+= (r[4] or 0)
    # the 3 unauthorized BEM solves + 3 renders from the pilot (external MATLAB, outside sqlite)
    (logs/'resource_budget.csv').write_text(
        'metric,state,charged_actual\n'+chr(10).join(f'{k[0]},{k[1]},{v}' for k,v in sorted(agg.items()))
        +'\nUNAUTHORIZED_BEM_SOLVES_VIOLATION,3,0\nUNAUTHORIZED_PILOT_RENDERS_VIOLATION,3,0\n',encoding='utf-8')
    viol=dict(schema='iscat145.budget_violation.1',
        event='Dual-focus pilot re-solved 3 BEM systems (pilot_ANON_01/ANON_04/M02 at focus 350) because the adapter cache is per-outDir; MATLAB was killed mid-run (pilot_M06 and f550 never started).',
        unauthorized_BEM_solves=3,unauthorized_renders=3,
        evidence_dir='provenance/pilot_violation_evidence/',
        disposition='Pilot stopped; P5 declared VIOLATED_BUDGET_AND_STOPPED; renders/solves preserved as evidence and treated as opened development data; NOT used for any model or reportability claim',
        historical_preserved=dict(v137_camera='23958/6000',v142_f2c_actual=48874,v143_forward_actual=49390,v143_camera=912))
    (logs/'v145_budget_violation.json').write_text(json.dumps(viol,indent=2,ensure_ascii=False)+chr(10),encoding='utf-8')
    # actual code sources
    code=out/'source'/'ACTUALLY_EXECUTED_CODE';code.mkdir(parents=True,exist_ok=True)
    tools=['v145_audit_v144.py','v145_camera_replay.py','v145_fixed_d_profiles.py','v145_estimator_report.py',
           'v145_local_information.py','v145_assemble.py','v145_pack.py','v145_check_science_delivery.py',
           'v142_model.py','v142_field_reference.py','field_forward_reference.py','load_field_library.py',
           'fit_reference.py','model_lock.py','v133_recover_M.py']
    rows=[]
    for t in tools:
        p=repo/'tools'/t
        if p.is_file():shutil.copy2(p,code/t);rows.append(dict(file=t,sha256=sha(p)))
    shutil.copy2(repo/'source/v126_physical_forward_adapter.m',code/'v126_physical_forward_adapter.m')
    rows.append(dict(file='v126_physical_forward_adapter.m (frozen 3b60804)',sha256=sha(code/'v126_physical_forward_adapter.m')))
    with (prov/'actual_executed_code_and_sources.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['file','sha256']);w.writeheader();w.writerows(rows)
    git_sha=os.popen('git -C "%s" rev-parse HEAD'%repo).read().strip()
    status=dict(task='V145_FIXED_DIAMETER_PROFILE_REPAIR_AND_MEASUREMENT_INFORMATION',git_commit_at_pack=git_sha,
      stage_states=dict(
        P0_AUDIT='COMPLETED: 23/24 V144 fixed-D points INVALID (4D leakage); truth leak in V144 N candidates documented; camera dev-null replay gap documented',
        P1_TRUTH_ISOLATION='COMPLETED: estimator-only candidates for 10 cases restored from frozen CSV; validator truth blocked from report path',
        P2_FIXED_D='COMPLETED: 42 strict fixed-D points (batch1 25 + batch2 17) with theta[0]==D identity enforced; V144-polluted checkpoints quarantined as history',
        P3_INFORMATION='COMPLETED: Jacobian condition 7.5-144.9, D-after-projection 3.3e-5..6.2e-3; dev-epsilon compatibility components reported as OBSERVED WITNESSES ONLY',
        P4_CAMERA_REPLAY='COMPLETED: 912 exposures replayed from real arrays; thresholds match; FPR 0/60 x3; V144 fake replay superseded',
        P5_FOCUS_PILOT='VIOLATED_BUDGET_AND_STOPPED: 3 unauthorized BEM solves + 3 renders executed before kill; evidence preserved; pilot invalid',
        P6_REPORT='reportable_D=null all cases; candidates from estimator sources only',
        P7_BUDGET='BEM VIOLATION 3 recorded; all other budgets within limits; ledger atomic per-event',
        P8_DELIVERY='this archive'),
      reportability_note='D-h compensation + broad compatibility witnesses -> single diameter not identifiable under current information; second focal plane requires a properly budgeted future round with a fixed focus-aware cache key',
      EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=False,
      budget=dict(violation=viol,fixed_D_points=len(summary),
        historical=dict(v137_camera='23958/6000',v142_f2c=48874,v143_forward=49390,v143_camera=912)))
    (out/'status.json').write_text(json.dumps(status,indent=2,ensure_ascii=False)+chr(10),encoding='utf-8')
    (out/'00_执行摘要.md').write_text('''# V145 执行摘要

- P0: V144复审——23/24个"固定D"点实为4D自由优化(标签错误);N候选真值泄漏;相机dev空白零重放;前向9289/8892差异均如实记录。
- P1: 真值隔离修复——10例candidate从冻结估计CSV恢复;validator truth阻断于报告路径之外。
- P2: 42个严格固定D点(theta[0]==D强制):ANON_03全D≈2.84e-6平坦、M04≈5.52e-6、M06≈4.24e-5、ANON_04≈2.91e-5——平坦D谷在正确固定D下依然存在,非V144错误产物。
- P3: Jacobian条件数7.5-144.9;D投影敏感性3.3e-5..6.2e-3——局部信息不足以证明唯一性。
- P4: 912次相机曝光真实数组重放,阈值一致,FPR 0/60三档。
- P5: 双焦面pilot违规——3次未授权BEM求解后中止,证据保全,VIOLATED状态如实记录。
- reportable_D全null;EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=false。
''',encoding='utf-8')
    (out/'review.md').write_text('''# V145 review

P2修复了V144的4D泄漏并以严格固定D重算——平坦D谷结论在正确方法下依然成立(此前归因撤回,现状如实)。
P5违规:3次BEM未授权求解,已停止并保全证据;该轮pilot无效。
预算与身份: 全部事件原子记录;真值隔离通过;历史超额保留。
''',encoding='utf-8')
    print('V145 assembled')
if __name__=='__main__':main()
