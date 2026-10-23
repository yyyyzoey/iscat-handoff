#!/usr/bin/env python3
"""Opened model library numerical stability sentinels for original F2 and F2c.
No developer truth used; no BEM. A PASS here is necessary, never physical accuracy.
"""
import argparse,json,sys,hashlib
from pathlib import Path
import numpy as np
from v142_model import construct
from v142_budget import Budget

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--config',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();root=Path(a.repo).resolve();cfg=json.loads(Path(a.config).read_text(encoding='utf-8'))
    dest=Path(a.out).resolve();dest.parent.mkdir(parents=True,exist_ok=True)
    old,new,_=construct(root,library_relative=cfg['inputs']['training_library'],expected_library_sha256=cfg['frozen_inputs']['training_library_sha256'],
                      expected_old_model_id=cfg['frozen_parent']['F2_model_id'])
    tests=[(30,350,0,0),(50,375,0,0),(100,450,-112,56),(130,450,56,112),(200,550,0,0),
       (47.5,381.25,42,-70),(73.3,406.25,-98,70),(109.5,442.5,84,98),(143.3,468.75,126,-42),
       (183.3,531.25,-70,98),(199.9,549.9,-499.,499.),(30.1,350.1,499.,-499.)]
    budget=Budget(dest.parent/'../logs/v142_budget.sqlite',cfg['budget_limits'])
    budget.reserve('F2C_STABILITY_12POINTS_'+sha(a.config)[:12],'FORWARD',48,'12 sentinels x 2 models x F2c duplicate; charge upper allocation')
    rows=[];calls=0
    try:
        for z in tests:
            o=old.forward(z);calls+=1;c=new.forward(z);calls+=1;c2=new.forward(z);calls+=1
            diff=float(np.max(abs(c.C-c2.C)));between=float(np.max(abs(o.C-c.C)))
            rows.append(dict(theta=z,old_model_id=old.model_id,new_model_id=new.model_id,max_abs_repeat=diff,
                old_vs_new_max_abs_C=between,old_C_norm=float(np.linalg.norm(o.C)),new_C_norm=float(np.linalg.norm(c.C)),
                image_valid=bool(np.isfinite(c.C).all() and np.isfinite(c.I).all() and np.all(c.I>=0))))
        # No allocation on intentional OOD tests: check_domain is cheap, no forward field evaluation.
        ood=[]
        for x in [(25,450,0,0),(205,450,0,0),(100,340,0,0),(100,560,0,0),(100,450,501,0),(100,450,0,-501),
                  (float('nan'),450,0,0)]:
            try:new.check_domain(x);status='FAILED_TO_REJECT'
            except Exception:status='REJECT'
            ood.append(dict(theta=[v if np.isfinite(v) else None for v in x],status=status))
        passes=all(r['image_valid'] and r['max_abs_repeat']<=1e-12 for r in rows) and all(v['status']=='REJECT' for v in ood)
        obj=dict(model_id=new.model_id,old_model_id=old.model_id,n_sentinels=len(rows),sentinels=rows,
            domain_rejection=ood,software_stability_pass=passes,source_scope='NUMERICAL_SENTINELS_NOT_PHYSICAL_SOURCE',
            numeric_overshoot_extra_metrics='NOT_ESTIMATED_BY_THIS_TOOL; Codex should calculate source-grid local overshoot separately',
            forward_actual_calls=calls,experimental_absolute_diameter_validated=False)
        dest.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
        budget.mark('F2C_STABILITY_12POINTS_'+sha(a.config)[:12],'COMPLETED',actual_units=calls)
        if not passes:raise RuntimeError('STABILITY_SENTINEL_FAILED__NO_MODEL_FREEZE')
        print('STABILITY_SENTS_OK_NOT_PHYSICAL_GATE',len(rows),calls)
    except Exception as e:
        x=budget.fetch('F2C_STABILITY_12POINTS_'+sha(a.config)[:12])
        if x and x['state']=='RESERVED':budget.mark('F2C_STABILITY_12POINTS_'+sha(a.config)[:12],'FAILED',actual_units=calls,note=repr(e))
        raise
if __name__=='__main__':main()
