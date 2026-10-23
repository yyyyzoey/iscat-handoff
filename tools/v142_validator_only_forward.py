#!/usr/bin/env python3
"""External validator ONLY: score old F2 versus new F2c at pre-opened truth points.
Reads H/J/K/L/M truth to evaluate forward discrepancy; NEVER imported into any
estimator, optimizer, profile or reportability module. No new BEM or camera.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,sys
from pathlib import Path
import numpy as np,h5py
from v142_budget import Budget
from v142_model import construct

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--config',required=True)
    p.add_argument('--out',required=True);a=p.parse_args();repo=Path(a.repo).resolve()
    cfg=json.loads(Path(a.config).read_text(encoding='utf-8'));out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(repo/'tools'))
    old,new,_=construct(repo,library_relative=cfg['inputs']['training_library'],
        expected_library_sha256=cfg['frozen_inputs']['training_library_sha256'],
        expected_old_model_id=cfg['frozen_parent']['F2_model_id'])
    groups=[('H',cfg['inputs']['opened_dev_H'],'results/v125/validation/holdout_truth_validator_only.json'),
            ('J',cfg['inputs']['opened_dev_J'],'results/v126/validation/holdout_truth_validator_only.json'),
            ('K',cfg['inputs']['opened_dev_K'],'results/v127/validation/holdout_truth_validator_only.json'),
            ('L',cfg['inputs']['opened_dev_L'],'results/v128/validation/new_L_truth_validator_only.json'),
            ('M',cfg['inputs']['M_observation_h5'],'results/v126/v132_M_cases.json')]
    limits=cfg['budget_limits'];budget=Budget(out/'../logs/v142_budget.sqlite',limits)
    op='DEV_VALIDATOR_OLD_VS_F2C_'+hashlib.sha256((sha(a.config)+new.model_id).encode()).hexdigest()[:16]
    budget.reserve(op,'FORWARD',80,'30 opened truth points x two models; conservative full reservation')
    rows=[];calls=0
    try:
        for family,rel,truth_rel in groups:
            truth=json.loads((repo/truth_rel).read_text(encoding='utf-8-sig'))
            truth=truth['cases'] if isinstance(truth,dict) else truth
            h5_identity=sha(repo/rel)
            with h5py.File(repo/rel,'r') as hf:
                for r in truth:
                    case=r.get('case') or r['tag'].removeprefix('holdout_')
                    if family=='H':
                        theta=[r['D_true_nm'],r['h_true_nm'],r['x_true_nm'],r['y_true_nm']]
                    elif family=='M':
                        off=[v['shift_xy_nm'] for v in r['renders'] if v['variant']=='at_offset']
                        if len(off)!=1:raise ValueError('M_OFFSET_NOT_SINGLE')
                        theta=[r['D_nm'],r['h_nm'],*off[0]]
                    else:theta=[r['D_nm'],r['h_nm'],r['x_nm'],r['y_nm']]
                    if calls+2>80:raise ValueError('VALIDATOR_ALLOCATION_EXHAUSTED')
                    Y=np.asarray(hf[case]['at_offset/C'][()],float)[2:15,2:15]
                    if not np.isfinite(Y).all() or Y.shape!=(13,13):raise ValueError('OBS_NONFINITE_OR_SHAPE')
                    A=old.forward(theta).score_C;calls+=1
                    B=new.forward(theta).score_C;calls+=1
                    norm=float(np.linalg.norm(Y));ea=float(np.linalg.norm(A-Y));eb=float(np.linalg.norm(B-Y))
                    rows.append(dict(family=family,case=case,source_h5_sha256=h5_identity,
                        old_F2_model_id=old.model_id,new_F2c_model_id=new.model_id,
                        old_true_theta_unscaled_L2=ea,new_true_theta_unscaled_L2=eb,
                        old_true_theta_relative_L2=(ea/norm if norm>1e-15 else None),
                        new_true_theta_relative_L2=(eb/norm if norm>1e-15 else None),
                        truth_use='VALIDATOR_ONLY_OPENED_DATA_NOT_BLIND'))
        budget.mark(op,'COMPLETED',actual_units=calls,note='all opened developer truth points, no estimator truth input')
    except Exception as exc:
        budget.mark(op,'FAILED',actual_units=calls,note=repr(exc));raise
    with (out/'dev_true_parameter_forward_comparison.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    m=[r for r in rows if r['family']=='M'];a=[r for r in rows if r['family']!='M']
    mpass=sum(r['new_true_theta_relative_L2'] is not None and r['new_true_theta_relative_L2']<=.01 for r in m)
    mx=max(r['new_true_theta_relative_L2'] for r in m if r['new_true_theta_relative_L2'] is not None)
    degradation=[r for r in a if r['new_true_theta_unscaled_L2']>r['old_true_theta_unscaled_L2']+.001]
    rule=cfg['preregistered_selection']
    candidate_pass=bool(mpass>=rule['new_F2c_direct_M_offset_pass_1pct_at_least'] and
        mx<=rule['new_F2c_direct_M_offset_max_relative_L2_at_most'] and not degradation)
    obj=dict(schema='iscat142.validator_only_forward.1',model_id=new.model_id,source='OPENED_DEV_NOT_NEW_BLIND',
        n_rows=len(rows),m_pass_1pct=mpass,m_max_relative_L2=mx,
        dev_HJKL_new_loss_worse_by_more_than_point001=[(r['family'],r['case']) for r in degradation],
        epsilon_dev_F2c_max_HJKL_unscaled_L2=max(r['new_true_theta_unscaled_L2'] for r in a),
        source_qualification='DEV_SOURCES_REQUIRE_INDEPENDENT_SOLVE_RENDER_LINKAGE_BEFORE_FORMAL_BOUND',
        candidate_selection_numerical_proposal_pass=candidate_pass,
        freeze_eligibility='REQUIRES_ADDITIONAL_DOMAIN_AND_MODEL_ID_GATES; THIS_VERDICT_ALONE_NEVER_FREEZES_N',
        f2_and_f2c_calls_actual=calls)
    (out/'developer_model_selection_proposal.json').write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('VALIDATOR_ONLY_DEV_FORWARD_COMPLETE_NOT_SCIENCE_PASS',len(rows),'M qualifies',mpass,'/6','proposal=',candidate_pass)
if __name__=='__main__':main()
