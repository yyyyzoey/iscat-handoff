#!/usr/bin/env python3
"""Read-only V140 publication audit. Uses actual source CSV/JSON, not status slogans.

This audit does not validate raw MAT/HDF5 electromagnetic arrays: V141 field
stage does that. Output status is intentionally SCIENCE_NOT_YET_CERTIFIED.
"""
from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from v141_common import assert_frozen_git_blobs,sha_file

CASES=[f'M{i:02d}' for i in range(1,7)]

def readcsv(p):
    with open(p,encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def audit(repo,cfg):
    repo=Path(repo)
    frozen=assert_frozen_git_blobs(repo,cfg['frozen_source_git_blobs_full_sha1'])
    base=repo/'results/v140'
    rows=readcsv(base/'validation/canonical_oracle_comparison.csv')
    if len(rows)!=12 or {(r['case'],r['variant']) for r in rows}!={(c,v) for c in CASES for v in ('default','at_offset')}:
        raise ValueError('V140_MISSING_OR_DUPLICATE_OBSERVATION_COMPARISON')
    byv={}
    for v in ('default','at_offset'):
        f=[r for r in rows if r['variant']==v]
        rel=[float(r['relative_L2']) for r in f]
        byv[v]=dict(n=len(f),pass_1pct=sum(x<=.01 for x in rel),
            min_relative_L2=min(rel),max_relative_L2=max(rel))
    # normalize typo intentionally reported; do not repair history in-place.
    old=repo/'config/v140_science_config.json'
    oldcfg=json.loads(old.read_text(encoding='utf-8'))
    invalid={k:dict(value=v,length=len(v)) for k,v in oldcfg.get('fixed_source_blobs',{}).items() if len(v)!=40}
    olderr=base/'validation/canonical_oracle_error.json'
    fail_record=json.loads(olderr.read_text(encoding='utf-8')) if olderr.is_file() else None
    summary=json.loads((base/'validation/canonical_oracle_summary.json').read_text(encoding='utf-8'))
    if summary.get('n_rows')!=12:raise ValueError('V140_FINAL_SUMMARY_MISSING_ROWS')
    lineage=readcsv(base/'provenance/cache_key_lineage.csv')
    if len(lineage)!=18:raise ValueError('V140_LINEAGE_INCOMPLETE_18')
    rep=json.loads((base/'validation/reportability.json').read_text(encoding='utf-8'))
    cases=rep.get('cases',rep)
    not_null=[k for k,v in cases.items() if v.get('reportable_D') is not None]
    if not_null:raise ValueError('UNQUALIFIED_V140_REPORTABLE_NON_NULL:'+','.join(not_null))
    out=dict(schema='iscat141.v140_publication_review.1',reviewed_fixed_commit=cfg['fixed_review_commit'],
        frozen_sources_exact_40hex=frozen,comparison=byv,
        final_oracle_report_exists=True,earlier_failure_record=fail_record,
        earlier_failure_disposition=('HISTORICAL_ATTEMPT_PRESENT_SUCCESS_REPORT_REQUIRES_SEPARATE_RUN_PROOF'
                    if fail_record else 'NO_EARLIER_FAILURE_RECORD_SEEN'),
        v140_config_invalid_source_sha_length=invalid,
        lineage_count=len(lineage),lineage_level='CACHE_KEY_AND_LEDGER_LINK_NOT_EMBEDDED_SOLVE_SHA',
        six_reportable_D_all_null=True,
        old_v137_camera_breach_events=23958,old_v137_camera_hard_limit=6000,
        science_verdict='NOT_INDEPENDENTLY_PHYSICS_QUALIFIED_BY_TEXT_RECORDS_ALONE')
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True)
    p.add_argument('--config',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    try:
        cfg=json.loads(Path(a.config).read_text(encoding='utf-8'))
        ret=audit(a.repo,cfg)
        out.write_text(json.dumps(ret,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
        print('V140_PUBLICATION_AUDIT_COMPLETE__SCIENCE_NOT_CERTIFIED',json.dumps(ret['comparison']))
        return 0
    except Exception as e:
        out.write_text(json.dumps(dict(status='AUDIT_BLOCKED',type=type(e).__name__,reason=str(e)),indent=2)+'\n',encoding='utf-8')
        print('AUDIT_BLOCKED',repr(e),file=sys.stderr)
        return 2
if __name__=='__main__':raise SystemExit(main())
