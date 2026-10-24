#!/usr/bin/env python3
"""Predefined plan only. DOES NOT perform inversions or accept science."""
import argparse,json
from pathlib import Path

def make_plan(audit,cfg):
    assert audit['n_events']==36 and not audit['errors'];b=cfg['budget_new_v147'];assert b['FORWARD']>=1 and all(b[k]==0 for k in ('BEM','RENDER','CAMERA'))
    return {'status':'PLAN_ONLY_NOT_EXECUTED','fixed_git_commit':cfg['fixed_git_commit'],'models':['PARENT_V146_DELTA_GLS','FROZEN_TEMPLATE_VARIANCE_GLS','OPTIONAL_NUMERIC_PG_LIKELIHOOD_IF_VALIDATED'],'group_design':'four opened anonymous particle types at B=1000/10000/100000, 3 saved independent exposures each; static shared theta vs per-frame nuisance','no_truth_initialization':True,'no_new_exposure':True,'forward_budget':b['FORWARD'],'priorities':cfg['research_priorities'],'criteria':'All 36 diagnostic results, all starts and cost per method, detected-only separated from full denominator, reportability fail-closed'}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--audit',required=True);p.add_argument('--config',required=True);p.add_argument('--out',required=True);a=p.parse_args();d=make_plan(json.loads(Path(a.audit).read_text()),json.loads(Path(a.config).read_text()));f=Path(a.out);f.parent.mkdir(parents=True,exist_ok=True);f.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');print('PLAN_ONLY__SCIENCE_MUST_RUN')
