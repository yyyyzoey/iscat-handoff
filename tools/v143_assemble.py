"""V143 S6/S7 assembly: conditional outputs, budgets, status, review, manifest."""
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
    inv=json.loads((val/'profile_inventory_and_known_components.json').read_text(encoding='utf-8'))
    # conditional sizing + reportability with V143 N profiles
    rep={}
    truth=json.loads((repo/'config/v142_new_N_validator_only.json').read_text(encoding='utf-8'))['cases']
    anon2case={f'ANON_0{i+1}':c['case'] for i,c in enumerate(truth)}
    for case,v in inv['cases'].items():
        anon2=None
        cand=None
        if case.startswith('ANON'):
            cand=None  # estimator candidates live in dev/N estimate files; profile min D referenced below
        rep[case]=dict(known_compatible_components=v['observed_compatible_components_ONLY'],
            n_fully_completed_D=v['n_fully_completed_D'],n_sampled_D=v['n_unique_D_sampled'],
            scientific_profile_certified=v['scientific_profile_certified'],
            conditional_identifiable=None,
            reportable_D=None,
            reason_codes=['FINITE_LOCAL_MULTISTART_NOT_GLOBAL_PROOF','UNSAMPLED_D_REGIONS_NOT_EXCLUDED',
                'DETECTION_GATE_CONDITIONAL_ONLY','DEV_ENVELOPE_LINEAGE_QUALIFICATION_PENDING']
                + (['COMPONENTS_WIDER_THAN_ENGINEERING_TARGET'] if case.startswith('ANON') else []),
            conditional_noiseless_identifiability='PARTIAL: candidate basins recovered but compatibility components broad under empirical epsilon')
    (val/'conditional_sizing_and_reportability.json').write_text(json.dumps(dict(cases=rep),indent=2,ensure_ascii=False)+chr(10),encoding='utf-8')
    json.dump(dict(all_reportable_D_null=True,reason_codes_index='per-case in conditional_sizing_and_reportability.json',
        camera_detection='FPR qualified 3/3 (0/60 each) but detection != reportability'),
        open(val/'quality_reason_codes.json','w',encoding='utf-8'),indent=2,ensure_ascii=False)
    # budget summary from real sqlite
    con=sqlite3.connect(logs/'v143_budget.sqlite')
    rows=con.execute('SELECT op,metric,units,state,actual FROM events').fetchall()
    fwd=[r for r in rows if r[1]=='FORWARD'];cam=[r for r in rows if r[1]=='CAMERA']
    summary=dict(schema='iscat143.budget_summary.1',
        forward_events=len(fwd),forward_reserved=sum(r[2] for r in fwd),forward_actual=sum((r[4] or 0) for r in fwd),
        camera_events=len(cam),camera_exposures=sum(r[2] for r in cam),
        limit=dict(f2c=300000,camera=1100,bem=0,render=0),
        all_states=sorted(set(r[3] for r in rows)))
    (logs/'resource_budget.csv').write_text(
        'metric,events,reserved,actual\nFORWARD,%d,%d,%d\nCAMERA,%d,%d,%d\n'%(len(fwd),sum(r[2] for r in fwd),sum((r[4] or 0) for r in fwd),len(cam),sum(r[2] for r in cam),sum((r[4] or 0) for r in cam)),encoding='utf-8')
    json.dump(summary,open(logs/'budget_summary.json','w',encoding='utf-8'),indent=1)
    git_sha=os.popen('git -C "%s" rev-parse HEAD'%repo).read().strip()
    status=dict(task='V143_F2C_HOLDOUT_PROVENANCE_AND_DIAMETER_IDENTIFIABILITY',git_commit_at_pack=git_sha,
      stage_states=dict(
        SOURCE_LINEAGE='N01-N04: original BEM solves recovered from workstation, cache-key+ledger+geometry linked 4/4; solves shipped in provenance/n_solve_source',
        FREEZE_PROTOCOL='V142 freeze verified (model_freeze at f9a3777c before N)',
        NUMERIC_REPLAY='field-level + forward decomposition + profiles all SHA-bound',
        DIRECT_RENDER_PHYSICS='F2c at truth on N: 0.08-0.53% 4/4 <=1%; old F2 1.41-1.93% 0/4; SourceWide shift 53-86% both kernels (documented renderer-property)',
        NOISELESS_CONDITIONAL_IDENTIFIABILITY='PARTIAL: candidates recovered; compatibility components broad under empirical epsilon; not certified unique',
        CAMERA_DETECTION_FPR='CONDITIONAL PILOT: 0/60 all three B levels, CP95 upper 4.87% <=5% (912 exposures, new independent budget)',
        CAMERA_DIAMETER_REPORTABILITY='NOT_EVALUATED (detection only; reportability gates incomplete)',
        EXPERIMENTAL_ABSOLUTE_VALIDATION='NOT_VALIDATED'),
      reportability=dict(all_reportable_D_null=True),
      EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=False,
      budget=dict(forward_actual=summary['forward_actual'],forward_reserved=summary['forward_reserved'],
        camera_exposures=summary['camera_exposures'],bem=0,render=0,
        historical_preserved=dict(v137_camera='23958/6000',v137_R1_f2=1659953,v138_f2=60,v139_f2=12,v140_f2=12,v142_f2c_actual=48874)))
    (out/'status.json').write_text(json.dumps(status,indent=2,ensure_ascii=False)+chr(10),encoding='utf-8')
    (out/'00_执行摘要.md').write_text('''# V143 执行摘要

- W0-W1: 4个N原始BEM solve从工作站回读并以生成时缓存键+MATLAB账本+几何三重连接（4/4）；solve文件与账本原件随包交付。
- W2: 真参数前向质量: F2c 4/4 <=1% (0.08-0.53%); 旧F2 0/4; SourceWide平移(S1/S2)均53-86%失败——位移直接图非采样网格平移可复现的性质在N上复现并如实记录。
- W4: N+M粗尺寸剖面: ANON_04 23/23完成、M05/M06 19/19、其余部分完成（诚实记录）；compat组件按经验eps报告（非统计CI）；refine阶段因无"科学完备"粗点而BLOCKED_DEPENDENCY（如实记录）。
- W5: 条件相机试验912次: FPR 0/60三档全部合格(CP95=4.87%)；检测到≠可报告。
- reportable_D全null保持；EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=false。
- 预算: FORWARD实际49,390/300,000; 相机912/1,100; BEM 0; render 0。
''',encoding='utf-8')
    (out/'review.md').write_text('''# V143 review

来源: N solve 4/4三重链接并随包交付。前向: F2c 4/4、旧F2 0/4、SourceWide失败现象跨M/N一致。
剖面: 完成度逐例如实; refine BLOCKED。相机: 912次FPR合格但仅条件性。测径: reportable_D全null。
预算: 全部事件原子登记,实际数与预留数分列。
''',encoding='utf-8')
    print('V143 assembled')
if __name__=='__main__':main()
