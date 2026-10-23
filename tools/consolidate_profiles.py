#!/usr/bin/env python3
"""Combine source-locked coarse/refinement checkpoints without invented high loss.

Reports observed compatibility GRID COMPONENTS as preliminary evidence; missing
or unconverged D regions remain UNKNOWN rather than automatically excluded.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from _shared import load_json,save_json


def segments(points,threshold,max_gap=5.):
    vals=sorted([(float(r['D']),float(r['loss_L2'])) for r in points if r['loss_L2'] is not None])
    compatible=[x for x in vals if x[1]<=threshold]
    out=[];first=last=None
    for d,r in compatible:
        if first is None:first=last=d
        elif d-last>max_gap+1e-9:out.append([first,last]);first=last=d
        else:last=d
    if first is not None:out.append([first,last])
    return out


def inspect_case(base,case,epsilon):
    best_by_D={};unknown=[];identities=set()
    for phase in ('coarse','refine'):
        d=Path(base)/phase/case
        if not d.is_dir():continue
        i=d/'input_identity.json'
        if i.is_file():
            ident=load_json(i)
            identities.add((ident.get('model_id'),ident.get('observation_sha'),ident.get('estimator_source_sha256')))
        for p in d.glob('*.json'):
            if p.name in ('input_identity.json','summary.json'):continue
            doc=load_json(p);r=doc.get('result',{})
            if 'D' not in r:continue
            D=float(r['D']);entry={'D':D,'loss_L2':r.get('best',{}).get('loss_L2') if r.get('best') else None,
                'point_search_complete':r.get('point_search_complete',False),
                'source':doc.get('status'), 'checkpoint':p.as_posix()}
            if entry['loss_L2'] is None or not entry['point_search_complete']:unknown.append(entry)
            old=best_by_D.get(D)
            if old is None or (entry['loss_L2'] is not None and (old['loss_L2'] is None or entry['loss_L2']<old['loss_L2'])):
                best_by_D[D]=entry
    if len(identities)>1:raise ValueError('DIFFERENT_F2C_MODEL_OR_OBSERVATION_IN_PROFILE_POINTS:'+case)
    valid=[v for v in best_by_D.values() if v.get('loss_L2') is not None and v['point_search_complete']]
    minR=min((v['loss_L2'] for v in valid),default=None)
    comp=segments(valid,minR+epsilon) if minR is not None else []
    return {'case':case,'source_bound_identity':list(identities)[0] if identities else None,
        'n_unique_D_sampled':len(best_by_D),'n_fully_completed_D':len(valid),
        'n_incomplete_or_unknown_attempts':len(unknown),'observed_compatible_components_ONLY':comp,
        'has_D30':30. in best_by_D,'has_D200':200. in best_by_D,
        'scientific_profile_certified':False,
        'reasons':['FINITE_LOCAL_MULTISTART_NOT_GLOBAL_PROOF','UNSAMPLED_D_REGIONS_NOT_EXCLUDED',
                   'EMPIRICAL_DEV_ERROR_NOT_STATISTICAL_95PCT_CI']}


def main():
    p=argparse.ArgumentParser();p.add_argument('--profiles-root',required=True)
    p.add_argument('--out',required=True);p.add_argument('--epsilon',type=float,default=.0015811481066672155)
    p.add_argument('--cases',nargs='+',default=['ANON_01','ANON_02','ANON_03','ANON_04','M01','M02','M03','M04','M05','M06']);a=p.parse_args()
    x={'schema':'iscat143.profile_summary.1','cases':{c:inspect_case(a.profiles_root,c,a.epsilon) for c in a.cases},
       'epsilon_scope':'PREVIOUS_HJKL_OPENED_DEV_ONLY_NOT_CONFIDENCE_LEVEL'}
    save_json(a.out,x);print('LOCAL_PROFILE_SUMMARY_WRITTEN__NOT_IDENTIFIABILITY_PASS')
if __name__=='__main__':main()
