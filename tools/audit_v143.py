#!/usr/bin/env python3
"""Read-only external audit of published V143 tables, freeze history and ledger.

It never declares science PASS from a successful script exit. Published scores
are source facts; checks are independent arithmetic and mechanical chronology.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,sqlite3,subprocess,sys
from pathlib import Path

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for x in iter(lambda:f.read(1<<20),b''):h.update(x)
    return h.hexdigest()
def in_git_tree(repo,gitsha,path):
    return subprocess.run(['git','-C',str(repo),'cat-file','-e',f'{gitsha}:{path}'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0

def run(repo,cfg):
    repo=Path(repo).resolve();status=load(repo/'results/v143/status.json')
    score=load(repo/'results/v142/validation/new_N_validator_score.json')
    scores=[abs(float(x['D_hat'])-float(x['D_true'])) for x in score['rows']]
    mae=sum(scores)/len(scores);rmse=math.sqrt(sum(x*x for x in scores)/len(scores))
    score_replay=dict(n=len(scores),n_within_goal=sum(float(x['abs_err_nm'])<=float(x['engineering_target_nm']) for x in score['rows']),
       MAE_nm=mae,RMSE_nm=rmse,max_err_nm=max(scores),matches_published=abs(mae-float(score['MAE_nm']))<1e-12)
    camera=load(repo/'results/v143/validation/camera_pilot/conditional_camera_pilot.json')
    camrows=[]
    for r in camera['results']:
        k=int(r['val_false_positives']);n=int(r['independent_null_n'])
        if k==0:up=1-.05**(1/n)
        else:
            from scipy.stats import beta
            up=float(beta.ppf(.95,k+1,n-k)) if k<n else 1.
        camrows.append(dict(B=r['B_electrons_per_pixel'],k=k,n=n,CP95=up,
          reported_CP95=r['one_sided95_cp_upper'],replay_diff=abs(up-r['one_sided95_cp_upper']),
          target_detected=r['target_detected'],target_total=r['target_n']))
    db=repo/cfg['inputs']['v143_budget_sqlite']
    with sqlite3.connect(db) as con:rows=con.execute('SELECT metric,units,actual,state FROM events').fetchall()
    ledger={metric:dict(events=sum(r[0]==metric for r in rows),reserved=sum(r[1] for r in rows if r[0]==metric),
                 actual=sum((r[2] or 0) for r in rows if r[0]==metric),
                 states=sorted({r[3] for r in rows if r[0]==metric})) for metric in ('FORWARD','CAMERA','RENDER','BEM')}
    extra=load(repo/cfg['inputs']['v143_extra_F2_calls'])
    extra_n=int(extra.get('f2_calls',0))
    freeze=load(repo/'results/v142/config/model_freeze.json')
    published_preN=cfg['historical_git']['V142_preN_model_development']
    postN=cfg['historical_git']['V142_N_data_added']
    declared_freeze=freeze['freeze_git_commit']
    source_presence=dict(
      declared_freeze_has_F2c_model=in_git_tree(repo,declared_freeze,'tools/v142_model.py'),
      preN_commit_has_F2c_model=in_git_tree(repo,published_preN,'tools/v142_model.py'),
      preN_commit_has_N_estimator=in_git_tree(repo,published_preN,'tools/v142_n_estimate.py'),
      N_data_commit_has_N_estimator=in_git_tree(repo,postN,'tools/v142_n_estimate.py'))
    phys=[]
    with (repo/'results/v143/validation/N_same_solve_and_F2c_forward.csv').open(encoding='utf-8',newline='') as f:
        for x in csv.DictReader(f):
            phys.append(dict(case=x['anon_case'],F2c_rel=float(x['relative_L2_F2c_at_truth']),
                 F2_rel=float(x['relative_L2_F2_at_truth']),
                 sourcewide_S1_rel_as_published=float(x['relative_L2_SourceWide_S1']),
                 sourcewide_S2_rel_as_published=float(x['relative_L2_SourceWide_S2'])))
    raw_sha=sha(repo/cfg['inputs']['N_anonymous_observation'])
    issues=[]
    if raw_sha!=cfg['known_sha256']['N_anonymous_observation']:issues.append('N_H5_SHA_MISMATCH')
    if not source_presence['declared_freeze_has_F2c_model']:
        issues.append('DECLARED_FREEZE_PARENT_COMMIT_LACKS_F2C_MODEL_SOURCE')
    if not source_presence['preN_commit_has_N_estimator']:
        issues.append('ANONYMOUS_N_ESTIMATOR_NOT_PRESENT_IN_EARLIER_PREN_GIT_COMMIT')
    if extra_n>0:issues.append('AUXILIARY_N_FORWARD_CALLS_NOT_INCLUDED_IN_V143_MAIN_LEDGER_AS_EVIDENCED_BY_SCRIPT')
    if any(r['replay_diff']>1e-12 for r in camrows):issues.append('CAMERA_CP95_ARITHMETIC_MISMATCH')
    if ledger['FORWARD']['actual']!=int(status['budget']['forward_actual']):issues.append('PUBLISHED_V143_FORWARD_STATUS_MISMATCH')
    return dict(schema='iscat144.v143_audit.1',fixed_git=cfg['fixed_source_git'],
      score_replay=score_replay,camera=camrows,budget_main_ledger=ledger,
      aux_v143_n_forward_published_calls=extra_n,
      at_least_forward_callbacks_including_auxiliary=ledger['FORWARD']['actual']+extra_n,
      no_claim_of_exact_full_global_execution_counter=True,
      freeze_chronology=source_presence,
      inherited_F2c_N_direct_checks=phys,
      issues=issues,
      source_scope='GITHUB_PUBLISHED_CSV_JSON_AND_WORKSTATION_LEDGER_REPLAY',
      experimental_absolute_diameter_validated=False,scientific_verdict='PARTIAL_NEEDS_PHYSICS_AND_PROFILE_CORRECTIONS')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True);ap.add_argument('--config',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    try:res=run(a.repo,load(a.config));out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(res,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    except Exception as e:
        out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({'status':'BLOCKED','error':repr(e)},indent=2)+'\n',encoding='utf-8')
        print('V143_AUDIT_BLOCKED',repr(e),file=sys.stderr);return 2
    print('V143_PUBLICATION_AUDIT_COMPLETED_NOT_SCIENCE_PASS',json.dumps(res['issues'],ensure_ascii=False));return 0
if __name__=='__main__':raise SystemExit(main())
