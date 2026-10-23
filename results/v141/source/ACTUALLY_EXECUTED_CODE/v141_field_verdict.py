#!/usr/bin/env python3
"""Mechanically summarize S1/S2 developer field tests without certifying sizing.

All opened M cases are development data. An improved S2 is a *new numerical
model proposal*, not a retroactive repair of F2 fits or a new blind benchmark.
"""
from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path

CASES={f'M{i:02d}' for i in range(1,7)}
KERNELS={'S1_BILINEAR','S2_CUBIC'}

def grade(rows):
    valid=[r for r in rows if r['variant']=='at_offset']
    if {(r['case'],r['kernel']) for r in valid}!={(c,k) for c in CASES for k in KERNELS}:
        raise ValueError('MISSING_SIX_OPENED_M_CASES_FOR_BOTH_KERNELS')
    by={}
    for k in sorted(KERNELS):
        vals=[float(r['wideEr_interpEs_C_rel_L2']) for r in valid if r['kernel']==k]
        if any(not (0<=x<float('inf')) for x in vals):raise ValueError('NONFINITE_ERROR')
        by[k]=dict(n=len(vals),pass_1pct=sum(x<=0.01 for x in vals),
                   max_relative_L2=max(vals),mean_relative_L2=sum(vals)/len(vals))
    S1=by['S1_BILINEAR'];S2=by['S2_CUBIC']
    proposal=(S2['pass_1pct']==6 and S2['max_relative_L2']<S1['max_relative_L2'])
    return dict(schema='iscat141.field_kernel_comparison.1',statistics=by,
       S2_development_proposal=proposal,
       recommendation=('CUBIC_NEW_MODEL_ID_AND_REQUALIFY_ALL_DEPENDENCIES' if proposal
           else 'KEEP_FROZEN_SPATIAL_BILINEAR_OR_DIAGNOSE_OTHER_CAUSES'),
       M_data_scope='OPENED_DEVELOPMENT_NOT_INDEPENDENT_VALIDATION',
       current_F2_model_still_locked=True,
       particle_diameter_reportability_granted=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--field-csv',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();dest=Path(a.out);dest.parent.mkdir(parents=True,exist_ok=True)
    try:
        with open(a.field_csv,encoding='utf-8') as f:rows=list(csv.DictReader(f))
        summary=grade(rows)
        dest.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        print('S1_S2_DEVELOPER_GRADING_COMPLETE_NO_SIZING_PASS')
        return 0
    except Exception as e:
        dest.write_text(json.dumps({'status':'NOT_EVALUATED','reason':repr(e)},indent=2)+'\n',encoding='utf-8')
        print('FIELD_GRADE_BLOCKED',repr(e),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
