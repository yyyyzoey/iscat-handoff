"""Independently recompute arithmetic and identify V134 publication contradictions.

Reads actual fixed-revision repo files when --repo is supplied. The packaged
published_values.json serves only as an explicit transcribed fallback for a
self-contained review, NOT as a substitute for original raw MAT/HDF5.
"""
from __future__ import annotations
import argparse,csv,json,math,sys
from pathlib import Path
from fail_closed_reportability import evaluate

ROOT=Path(__file__).resolve().parents[1]
VALUES=ROOT/'evidence'/'published_values.json'

def _stats(ds, values):
    e=[float(y)-float(d) for d,y in zip(ds,values)]
    return {
        'count':len(e), 'bias_nm':sum(e)/len(e),
        'MAE_nm':sum(abs(x) for x in e)/len(e),
        'RMSE_nm':math.sqrt(sum(x*x for x in e)/len(e)),
        'max_abs_nm':max(abs(x) for x in e),
        'size_error_target_only_pass':sum(abs(x)<=max(5.,.1*d) for x,d in zip(e,ds)),
        'errors_nm':e,
    }

def audit(repo=None):
    p=json.loads(VALUES.read_text())
    cases=p['M_cases']; d=[float(x) for x in p['M_true_D_nm']]
    f2=[float(x) for x in p['v133_f2_candidates_nm']]
    coarse=[float(x) for x in p['v134_cmap_profile_best_D_nm']]
    props=[{'case':k,'best_D':c,'reportable':f,'compatible':i} for k,c,f,i in zip(cases,coarse,p['v134_reportable_boolean'],p['v134_reported_compatible_components_nm'])]
    actual_sources=[]
    if repo is not None:
        base=Path(repo).resolve()
        cp=base/'results/v133/M_F2_baseline/M_F2_candidates.csv'
        rp=base/'results/v134/reportability.json'
        tp=base/'results/v126/v132_M_cases.json'
        for fp in (cp,rp,tp):
            if not fp.exists():raise FileNotFoundError(f'Original required source unavailable: {fp}')
        fv={r['case']:float(r['candidate_D']) for r in csv.DictReader(cp.open(newline='',encoding='utf-8-sig'))}
        if sorted(fv)!=sorted(cases):raise ValueError('F2 case list mismatch')
        f2=[fv[k] for k in cases]
        props=json.loads(rp.read_text(encoding='utf-8-sig'))
        ps={r['case']:r for r in props}
        if sorted(ps)!=sorted(cases):raise ValueError('V134 reportability case list mismatch')
        props=[ps[k] for k in cases]
        original=json.loads(tp.read_text(encoding='utf-8-sig'))['cases']
        dm={r['tag'].removeprefix('holdout_'):float(r['D_nm']) for r in original}
        if [dm.get(k) for k in cases]!=d:raise ValueError('M task record and reviewed data mismatch')
        actual_sources=[str(cp),str(rp),str(tp)]

    coarse=[float(r['best_D']) for r in props]
    false_reportability=[]
    for r in props:
        k=r['case'];dhat=float(r['best_D'])
        gates={key:True for key in __import__('fail_closed_reportability').REQUIRED}
        gates.update(observable_type='SIGNED_STATIC_C_FROM_LINEAR_INTENSITY', measurement_mode='NOISY_CAMERA')
        gate=evaluate(dhat,r['compatible'],gates)
        if r.get('reportable') is True or gate['reportable_D'] is not None:
            false_reportability.append({'case':k,'published_reportable':r.get('reportable'),
                'safe_gate_reportable':gate['diameter_reportable'],'safe_rejection_reasons':gate['reason_codes'],
                'compatible':r['compatible']})
    wrong_pass=[]
    for k,d0,v in zip(cases,d,coarse):
        if abs(v-d0)<=max(5,.1*d0):wrong_pass.append(k)
    raw=self_check_paths(base) if repo is not None else None
    return {
        'schema':'iscat135.v134_independent_publication_audit.1',
        'source_scope':'FIXED_REPO_TEXT_FILES_WITH_REPO' if repo else 'EXPLICIT_TRANSCRIBED_EVIDENCE_ONLY',
        'original_files_read':actual_sources,
        'v133_F2':_stats(d,f2),
        'v134_coarse_Cmap':_stats(d,coarse),
        'v134_size_target_pass_cases':wrong_pass,
        'v134_review_said_target_pass':p['v134_review_says_target_count'],
        'v134_published_reportable_true':[r['case'] for r in props if r.get('reportable') is True],
        'v134_all_intervals_full_support':all(r.get('compatible')==[[30,200]] or r.get('compatible')==[[30.0,200.0]] for r in props),
        'v134_unsafe_reportability_rows':false_reportability,
        'v134_science_gate':'NOT_ACCEPTED',
        'v134_path_audit':raw,
        'note':'F2 and C-map losses are different models, not comparable as an optimizer profile. v133 F2 six M are opened development results, not independent blinded experimental validation.'
    }

def self_check_paths(base):
    names=[
      'results/v134/validation/shift_vs_direct_render.csv',
      'results/v134/validation/M_F2_direct_error_separation.csv',
      'results/v134/validation/raw_camera_data.h5',
      'results/v134/logs/resource_ledger.jsonl',
      'tools/v134_run_all.py',
      'tools/v134_infer_experiment.py',
      'results/v134_external_receipt.json',
      'results/v134_science_validation.json',
      'tools/config.json', 'tools/review_recomputations.json',
    ]
    return {n:(base/n).is_file() for n in names}

def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',help='Actual checkout at a pinned v134 commit (or descendant preserving published files)')
    ap.add_argument('--out',help='Output path for audited JSON')
    args=ap.parse_args(argv)
    res=audit(args.repo)
    if args.out:
        out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(res,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:res[k] for k in ('source_scope','v134_size_target_pass_cases','v134_published_reportable_true','v134_science_gate')},ensure_ascii=False,indent=2))
    return 0  # successful detection of a FAILED historical science gate

if __name__=='__main__':raise SystemExit(main())
