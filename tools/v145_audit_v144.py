#!/usr/bin/env python3
"""Read-only independent V144 source-and-record audit (not physics replay).

Any truth registry opened here is VALIDATOR ONLY and must never be imported by
v145_fixed_d_profiles or a production estimator.  Reports fail-closed science
issues, retaining source bytes and prior failures unchanged.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,sqlite3
from pathlib import Path


def digest(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()

def load_json(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def read_csv(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def fixed_d_violations(root:Path,tol=1e-6):
    files=sorted(root.glob('*/*.a1.json'))
    entries=[];errors=[]
    for p in files:
        try:
            o=load_json(p);r=o['result'];theta=r['best']['theta'];D=float(r['D']);fitD=float(theta[0]);
            if len(theta)!=4 or not all(math.isfinite(float(v)) for v in theta):raise ValueError('theta invalid')
            entries.append(dict(case=p.parent.name,path=p.as_posix(),target_D=D,actual_fit_D=fitD,
                abs_mismatch_nm=abs(D-fitD),fixed_D=(abs(D-fitD)<=tol),point_search_complete=r.get('point_search_complete')))
        except Exception as e:errors.append(dict(path=p.as_posix(),error=repr(e)))
    return dict(checkpoints=len(files),readable=len(entries),mismatched_fixed_D=sum(not e['fixed_D'] for e in entries),
        max_D_deviation_nm=max((e['abs_mismatch_nm'] for e in entries),default=None),
        examples=sorted((e for e in entries if not e['fixed_D']),key=lambda x:x['abs_mismatch_nm'],reverse=True)[:12],errors=errors,
        scientific_disposition='ALL_V144_REFINEMENT_ROWS_MUST_BE_QUARANTINED_AS_FIXED_D_EVIDENCE__4D_OPTIMIZER_USED')

def budget_sqlite(path):
    if not Path(path).is_file():return {'status':'MISSING'}
    with sqlite3.connect(path) as db:
        tab=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        if 'events' not in tab:return dict(status='UNEXPECTED_SCHEMA',tables=tab)
        cols=[r[1] for r in db.execute('PRAGMA table_info(events)')]
        needed={'op','metric','units','state','actual'}
        if not needed<=set(cols):return dict(status='MISSING_FIELDS',available=cols)
        raw=db.execute('SELECT op,metric,units,state,actual FROM events').fetchall()
    by={}
    for op,m,u,s,a in raw:
        z=by.setdefault(m,dict(events=0,reserved=0,actual=0,states={}))
        z['events']+=1;z['reserved']+=u;z['actual']+=a or 0;z['states'][s]=z['states'].get(s,0)+1
    return dict(status='RECORDED_LEDGER_ONLY',metrics=by)

def run(repo,cfg):
    repo=Path(repo);v=repo/'results/v144';source=(repo/'tools/v144_refine.py').read_text(encoding='utf-8')
    asm=(repo/'tools/v144_assemble.py').read_text(encoding='utf-8')
    cam=(repo/'tools/v144_camera_replay.py').read_text(encoding='utf-8')
    oracle=read_csv(repo/cfg['v144_oracle_csv'])
    pairs={}
    for kernel in ('S1_BILINEAR','S2_CUBIC'):
        s=[r for r in oracle if r['variant']=='at_offset' and r['kernel']==kernel]
        vals=[float(r['correct_relative_L2_17']) for r in s]
        pairs[kernel]=dict(n=len(s),pass_1pct=sum(x<=.01 for x in vals),min_relative_L2=min(vals),max_relative_L2=max(vals))
    refined=fixed_d_violations(repo/cfg['v144_invalid_refine_root'])
    reported=load_json(repo/cfg['v144_report'])['cases'];estimates=read_csv(repo/cfg['N_candidates'])
    etable={r['anon_case']:float(r['candidate_D']) for r in estimates}
    mismatches=[]
    for case,d in etable.items():
        stated=reported.get(case,{}).get('candidate_D')
        if stated is None or abs(float(stated)-d)>1e-8:
            mismatches.append(dict(case=case,v144_candidate_D=stated,original_anonymous_estimate_D=d))
    ledger=budget_sqlite(repo/cfg['v144_budget_sqlite']);status=load_json(v/'status.json')
    return dict(schema='iscat145.v144_audit.1',fixed_source_commit=cfg['fixed_review_commit'],
        reviewed_files={r:digest(repo/r) for r in ['tools/v144_refine.py','tools/v144_assemble.py','tools/v144_camera_replay.py','results/v144/status.json']},
        corrected_N_sourcewide= pairs,
        v144_refinement=refined,
        v144_source_code_contains_4D_trf=("bounds=([30.,350.,-500.,-500.],[200.,550.,500.,500.])" in source and 'cand.forward(tuple(float(v) for v in p))' in source),
        truth_leak_to_candidate_proven=("anonD[f'ANON_{i:02d}']=c['D_nm']" in asm),
        N_candidates_disagree_with_saved_anonymous_estimator=mismatches,
        camera_replay_development_null_groups_read=load_json(v/'validation/camera_replay.json')['rows'][0]['dev_null_replay_groups'],
        camera_source_reads_after_close=("with h5py.File" in cam and 'groups=list(h.keys())' in cam and "g=h[gk]" in cam),
        camera_v144_independent_threshold_replay_qualified=False,
        event_ledger=ledger,
        v144_status_declared_actual=status['budget']['forward_actual'],
        v144_executive_summary_refinement_calls=cfg['historical_budget_must_preserve']['v144_summary_mentions_refinement_calls'],
        historical_errors_preserved=True,
        correct_decision='RETAIN_N_ORACLE_S2_4_OF_4; REJECT_V144_FIXED_D_REFINEMENT_AND_TRUTH_TAINTED_CANDIDATE; CAMERA_REPLAY_NOT_PERFORMED',
        experimental_absolute_diameter_validated=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--config',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    dest=Path(a.out);dest.parent.mkdir(parents=True,exist_ok=True)
    try:r=run(a.repo,load_json(a.config))
    except Exception as e:r=dict(status='BLOCKED_NOT_EVALUATED',error=repr(e));dest.write_text(json.dumps(r,indent=2)+'\n');print('BLOCKED',e);return 2
    dest.write_text(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print('AUDITED V144; invalid fixed-D pts:',r['v144_refinement']['mismatched_fixed_D'],'of',r['v144_refinement']['readable'])
    return 0
if __name__=='__main__':raise SystemExit(main())
