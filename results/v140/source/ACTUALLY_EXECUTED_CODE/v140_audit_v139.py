"""Read-only V139 publication audit; returns successful AUDIT != scientific PASS."""
from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path

def readcsv(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def summarize(rows,variant,name):
    rs=[r for r in rows if r['variant']==variant]
    vals=[float(r[name]) for r in rs]
    if len(rs)!=6:raise ValueError('six cases required per variant '+variant)
    return dict(n=6,min_relative_L2=min(vals),max_relative_L2=max(vals),
        mean_relative_L2=sum(vals)/len(vals),passes_1pct=sum(v<=.01 for v in vals))

def audit(repo):
    root=Path(repo).resolve();base=root/'results/v139'
    rows=readcsv(base/'validation/oracle_shift_decomposition.csv')
    summary=json.loads((base/'validation/oracle_summary.json').read_text(encoding='utf-8'))
    status=json.loads((base/'status.json').read_text(encoding='utf-8'))
    lineage=readcsv(base/'provenance/solve_to_render_lineage.csv')
    report=json.loads((base/'validation/reportability.json').read_text(encoding='utf-8'))
    budget=readcsv(base/'logs/resource_budget.csv')
    result={'schema':'iscat140.v139_text_evidence_audit.1',
       'source_scope':'PUBLISHED_CSV_JSON_AND_CODE_ONLY_NO_ORIGINAL_MAT_REPLAY',
       'source_commit_claimed':'bf22ec3b3374f32f75d9c724d290494da3ec959b',
       'n_oracle_rows':len(rows),'oracle_direct':{},'F2_direct':{},'F2_oracle':{}}
    for v in ('default','at_offset'):
        result['oracle_direct'][v]=summarize(rows,v,'oracle_vs_direct_rel_L2')
        result['F2_direct'][v]=summarize(rows,v,'F2_vs_direct_rel_L2')
        result['F2_oracle'][v]=summarize(rows,v,'F2_vs_oracle_rel_L2')
    result['reported_numeric_summary']=summary
    result['v139_status_gate_claims']=status.get('science_gates',{})
    result['lineage_rows']=len(lineage)
    result['lineage_statuses']=sorted(set(r.get('lineage_status','') for r in lineage))
    result['lineage_solve_filename_is_render_filename']=all(r.get('solve_file','').startswith('ren_') for r in lineage)
    result['lineage_default_wide_bitwise_false_rows']=sum(r['Eref_default_vs_wide_bitwise']=='False' for r in lineage)
    result['reportable_D_all_null']=all(r.get('reportable_D') is None for r in report['cases'].values())
    result['new_f2_query_events_published']=sum(int(r['f2_calls']) for r in budget)
    result['v139_science_verdict']='PARTIAL_ASSETS_ACCEPTED_ORACLE_SHIFT_PHYSICS_NOT_CERTIFIED'
    result['material_issues']=[
      'same-solve wide oracle uses a complex-field transpose different from frozen v125 MATLAB-to-Python importer',
      'MATLAB source efield(...x-dx,y-dy) then flip(es0,1) requires field-space shift coordinate mapping',
      '6 M nonzero oracle/direct fail 1% but F2/direct has one passing case; do not infer universal physical non-translation',
      'cache map+execution ledger available to trace solve->render without adding new BEM',
      'lineage file solve_file contains ren_ filename and geometry_matches_registry assigned literally',
      'current numeric source lineage and profile data insufficient for reportable diameter',
    ]
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    try: result=audit(a.repo)
    except Exception as e:print('AUDIT_BLOCKED '+repr(e),file=sys.stderr);return 2
    dest=Path(a.out);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['oracle_direct','F2_direct','lineage_statuses','reportable_D_all_null','v139_science_verdict']},ensure_ascii=False,indent=2))
    return 0
if __name__=='__main__':raise SystemExit(main())
