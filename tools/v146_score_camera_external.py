#!/usr/bin/env python3
"""VALIDATOR ONLY. This module must never be imported by any estimator.
Scores frozen noisy-image candidates after inference; no feedback to fitting.
"""
from __future__ import annotations
import argparse,re,math
from pathlib import Path
from v146_core import read_json,save_json,file_sha


def score(summary,truth,mapping):
    labelmap={r['anon']:r['case'] for r in mapping['rows']}
    tmap={r['case']:r['D_nm'] for r in truth['cases']}
    rows=[]
    for d in summary['event_results']:
        if 'fit' not in d:continue
        e=d['event'];f=d['fit'];m=re.fullmatch(r'(ANON_\d{2})_\d{2}',e['label'])
        if not m or m.group(1) not in labelmap:raise ValueError('UNKNOWN_ANON_MAPPING')
        case=labelmap[m.group(1)];true=float(tmap[case]);hat=f['candidate_D']
        if hat is not None and not math.isfinite(hat):raise ValueError('NONFINITE_CANDIDATE')
        rows.append({'event_id':e['event_id'],'case':case,'B':e['B'],'detected':e['detected'],
                     'D_true_nm':true,'candidate_D_nm':hat,'absolute_error_nm':None if hat is None else abs(hat-true),
                     'candidate_within_engineering_goal':None if hat is None else abs(hat-true)<=max(5.,.1*true),
                     'reportable_D':f['reportable_D'],'source':'VALIDATOR_ONLY_OPENED_CAMERA_DIAGNOSTIC'})
    groups=[]
    for B in sorted({r['B'] for r in rows}):
        rr=[r for r in rows if r['B']==B]
        for scope in ('all_targets','detected_only'):
            a=[r for r in rr if scope=='all_targets' or r['detected']]
            errs=[r['absolute_error_nm'] for r in a if r['absolute_error_nm'] is not None]
            groups.append({'B':B,'scope':scope,'n':len(a),'n_finite_candidates':len(errs),
                           'MAE_nm':None if not errs else sum(errs)/len(errs),
                           'max_error_nm':None if not errs else max(errs),
                           'warning':'3 repeats/condition; no statistical coverage certification'})
    return {'schema':'iscat146.external_camera_score.1','rows':rows,'groups':groups,
            'truth_was_not_in_estimator': 'VERIFY_FROM_PROCESS_AND_CODE_SEPARATION',
            'new_independent_blind_experiment':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--summary',required=True);p.add_argument('--truth',required=True)
    p.add_argument('--lineage',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    r=score(read_json(a.summary),read_json(a.truth),read_json(a.lineage))
    r['input_hashes']={k:file_sha(getattr(a,k)) for k in ('summary','truth','lineage')}
    save_json(a.out,r);return 0
if __name__=='__main__':raise SystemExit(main())
