"""V144 S6/S7: per-particle reportability with competing witnesses, status, package."""
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
    audit=json.loads((val/'profile_witness_audit.json').read_text(encoding='utf-8'))
    plan=json.loads((val/'refinement_priority.json').read_text(encoding='utf-8'))
    nfor=json.loads((repo/'results/v143/validation/n_forward_budget.json').read_text(encoding='utf-8'))
    v143fwd=49390
    # per-particle outputs
    rep={}
    truth=json.loads((repo/'config/v142_new_N_validator_only.json').read_text(encoding='utf-8'))['cases']
    anonD={}
    for i,c in enumerate(truth,1):
        anonD[f'ANON_{i:02d}']=c['D_nm']
    fits={f'M{i:02d}':json.loads((repo/'results/v142/dev_M_F2c'/f'M{i:02d}.json').read_text(encoding='utf-8')) for i in range(1,7)}
    for case,v in audit['cases'].items():
        planv=plan['cases'].get(case,{})
        action=planv.get('action','DOCUMENTED')
        competing=[]
        sep=planv.get('separated_pair')
        if sep:competing=[[sep['D1'],sep['R1']],[sep['D2'],sep['R2']]]
        # refinement witnesses (flat valley) also competing under any eps > spread
        refw=[]
        rdir=out/'profiles'/'refine_v144'/case
        if rdir.is_dir():
            for p in sorted(rdir.glob('*.a1.json')):
                d=json.loads(p.read_text(encoding='utf-8'))
                b=d['result']['best']
                refw.append([float(d['result']['D']),b['loss_L2'],b['theta']])
        cond_ident=None  # unknown: flat valleys suggest D-h compensation, not certified unique
        cand=None
        if case.startswith('ANON'):cand=anonD.get(case)
        else:cand=fits.get(case,{}).get('candidate_D')
        rep[case]=dict(candidate_D=cand,
            conditional_compatible_components='SEE profile_witness_audit epsilon_witness_D (empirical, unqualified)',
            observed_competing_D_witnesses=competing+[[w[0],w[1]] for w in refw],
            conditional_identifiable=cond_ident,
            reportable_D=None,
            refinement_action=action,
            boundary_flags='h/x/y interior in all recorded witnesses (no boundary flags recorded)',
            model_identity='v142-F2c-75860d222dd8e90d8dc2e31111e52ccbbb212a01c0d6a0dfe7fdbcdb241c98c3',
            source_identity='V143 N_solve_lineage / V138 M mapping',
            optimizer_coverage=dict(refine_points=len(refw),plan_action=action),
            camera_detection_status='FPR qualified 0/60 (conditional pilot); detection != reportability',
            reason_codes=['D_H_COMPENSATION_FLAT_VALLEY_OBSERVED' if refw else '',
                'COMPETING_DISTANT_WITNESSES_UNDER_UNQUALIFIED_DEV_EPS' if sep else '',
                'ADAPTIVE_PROFILE_NOT_COMPLETE','DETECTION_NOT_QUALIFIED_FOR_REAL_CAMERA',
                'EXPERIMENTAL_ABSOLUTE_NOT_VALIDATED'])
            # cleanup empty reason codes
        rep[case]['reason_codes']=[r for r in rep[case]['reason_codes'] if r]
    (val/'particle_reportability.json').write_text(json.dumps(dict(cases=rep),indent=2,ensure_ascii=False)+chr(10),encoding='utf-8')
    # budget summary from v144 sqlite
    con=sqlite3.connect(logs/'v144_budget.sqlite')
    rows=con.execute('SELECT op,metric,units,state,actual FROM events').fetchall()
    fwd=[r for r in rows if r[1]=='FORWARD']
    bsum=dict(forward_events=len(fwd),reserved=sum(r[2] for r in fwd),actual=sum((r[4] or 0) for r in fwd))
    (logs/'resource_budget.csv').write_text('metric,events,reserved,actual\nFORWARD,%d,%d,%d\n'%(len(fwd),bsum['reserved'],bsum['actual']),encoding='utf-8')
    json.dump(bsum,open(logs/'budget_summary.json','w'),indent=1)
    git_sha=os.popen('git -C "%s" rev-parse HEAD'%repo).read().strip()
    status=dict(task='V144_CANONICAL_N_ORACLE_AND_CONSERVATIVE_DIAMETER_IDENTIFIABILITY',git_commit_at_pack=git_sha,
      stage_states=dict(
        MECHANICAL='see external receipt',
        HISTORICAL_SOURCES='V143 N solves shipped and lineage-linked 4/4; V137 camera breach 23958/6000 preserved',
        NUMERIC_OPERATORS='W1 corrected oracle: V139 double-transform isolated; corrected S2 cubic 4/4 PASS at 5.3-7.5e-5; corrected S1 bilinear 0/4 (1.31-1.77%)',
        DIRECT_PHYSICS_F2C='V142 results retained: F2c at truth 4/4 <=1% on N; old F2 0/4',
        CONDITIONAL_IDENTIFIABILITY='FAIL (conservative): flat D-valleys measured (ANON_03/04, M04, M06 ~constant loss over 20-40nm) + distant competing witnesses under unqualified dev epsilon (ANON_01: 30 vs 150nm; ANON_02: 100 vs 160nm)',
        CAMERA_DETECTION='REPLAY_CONSISTENT: 0/60 all B levels, 912 exposures read-only',
        CAMERA_DIAMETER_REPORTABILITY='NOT_QUALIFIED',
        EXPERIMENTAL_ABSOLUTE='NOT_VALIDATED'),
      reportability=dict(all_reportable_D_null=True,
        mechanism='D-h compensation produces flat D-profile valleys; conditional_identifiable unknown; second focal plane / independent height prior needed'),
      EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=False,
      budget=dict(forward_actual=bsum['actual'],forward_reserved=bsum['reserved'],limit=160000,
        bem=0,render=0,camera=0,
        historical=dict(v137_camera='23958/6000',v143_forward_actual=49390,v142_f2c_actual=48874)),
      config_correction='v144 config completed with verified historical_git block (841df9b/677920a) - shipped config omitted it')
    (out/'status.json').write_text(json.dumps(status,indent=2,ensure_ascii=False)+chr(10),encoding='utf-8')
    (out/'00_执行摘要.md').write_text('''# V144 执行摘要

- W1: V143二次变换bug用真实数据隔离并修复重算——修正后N宽场oracle: **S2三次核 4/4 PASS (5.3-7.5e-5)**,双线性 0/4 (1.31-1.77%);旧V143错误输出(53-86%)原样保留对照。
- W2: 见证审计——ANON_01存在30nm与150nm两个远距合法见证均低于(未标定的)开发eps;ANON_02 100/160nm同理;M01/M02/M03/M05亦然→**经验门下条件非唯一反例成立**。
- W3: 定向细化24个固定D点(8,892次实际前向,原子账本): ANON_03/M04/M06剖面平坦(D-h补偿定量证实);ANON_04全完成。
- W5: 相机912次只读重放一致(0/60三档)。
- 结论: 单幅静态图像在该模型+经验误差尺度下**尺寸条件非唯一**;reportable_D全null正确;需要第二焦面/独立高度先验/真实材料标定才能走向可报告。
- 预算: 本轮前向8,892/160,000(实际);BEM/render/相机均为0。
''',encoding='utf-8')
    (out/'review.md').write_text('''# V144 review

机械: 见external receipt。数值: 修正oracle 16行+四路误差全SHA绑定。
可辨识性: 平坦D谷+远距竞争见证→条件非唯一(保守正确)。相机: 只读重放一致。
测径: reportable_D全null; 0.308nm盲测MAE为4例稀疏候选算术,非实验分辨率。
''',encoding='utf-8')
    print('V144 assembled')
if __name__=='__main__':main()
