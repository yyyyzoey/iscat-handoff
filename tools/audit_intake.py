"""Read-only intake validator; not an estimator and not a physics acceptance.

The summary is a narrative source. This tool contrasts its literal claims with
actual stored code/registries and reports presence of local V137 artifacts.
It never concludes that a local file is a validated scientific result.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,subprocess
from pathlib import Path

BASE_NUMERIC='0ca301e6f3f68c596665475d94f8b924ef3356e2'
REVIEWED_INTAKE='24d18d592034df058c4a8edb0acb04d4ccdc2fc1'


def git(repo,*args):
    r=subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True,check=False)
    return {'returncode':r.returncode,'stdout':r.stdout.strip(),'stderr':r.stderr.strip()}


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def audit(repo):
    repo=Path(repo).resolve()
    summary=repo/'V124_V136_HANDOFF_SUMMARY.md'
    source=repo/'tools/field_forward_reference.py'
    jf=repo/'results/v126/validation/holdout_truth_validator_only.json'
    cf=repo/'results/v133/M_F2_baseline/M_F2_candidates.csv'
    tf=repo/'results/v126/v132_M_cases.json'
    for p in (summary,source,jf,cf,tf):
        if not p.is_file():raise FileNotFoundError(p)
    st=summary.read_text(encoding='utf-8-sig');code=source.read_text(encoding='utf-8-sig')
    truths=json.loads(tf.read_text(encoding='utf-8-sig'))['cases']
    registry={c['tag'].removeprefix('holdout_'):float(c['D_nm']) for c in truths}
    if len(registry)!=len(truths):raise ValueError('Duplicate M task records')
    candidates=list(csv.DictReader(cf.open(encoding='utf-8-sig',newline='')))
    cases=[r['case'] for r in candidates]
    if len(cases)!=len(set(cases)) or set(cases)!=set(registry):raise ValueError('M case-set mismatch')
    err=[float(r['candidate_D'])-registry[r['case']] for r in candidates]
    if not all(math.isfinite(e) for e in err):raise ValueError('Non-finite candidate')
    targets=sum(abs(e)<=max(5,.1*registry[r['case']]) for r,e in zip(candidates,err))
    j=json.loads(jf.read_text(encoding='utf-8-sig'))
    actual_J=[float(c['D_nm']) for c in sorted(j,key=lambda x:x['case'])]
    flagged=[]
    if 'Complex-field D/h bilinear interpolation' in st and 'F2: not-a-knot tensor cubic' in code:
        flagged.append({'claim':'F2 uses D/h bilinear interpolation','finding':'CONFLICT_WITH_ACTUAL_F2_CODE',
                        'correction':'F2 physical D/h tensor cubic; spatial field sampling is bilinear'})
    if 'High-D C response saturation is physical, not implementation defect' in st:
        flagged.append({'claim':'High-D failure is conclusively physical saturation',
                        'finding':'NOT_ESTABLISHED_BY_SUMMARY; keep as hypothesis until same-objective diagnostics'})
    if '| J (D=41,67,93,117,147,177)' in st and actual_J!=[41.,67.,93.,117.,147.,177.]:
        flagged.append({'claim':'J diameters in summary table','finding':'CONFLICT_WITH_ORIGINAL_J_REGISTRY',
                        'original_J_D_nm':actual_J})
    local=[]
    for d in ('results/v137','results/v137_r1'):
        p=repo/d
        if p.exists():local.append({'path':d,'role':'LOCAL_ARTIFACTS_TO_CLASSIFY_NOT_AUTOMATICALLY_ACCEPTED',
                                  'files':sorted(str(x.relative_to(repo)) for x in p.rglob('*') if x.is_file())})
    return dict(schema='iscat137r1.intake.1',
        reviewed_numeric_commit=BASE_NUMERIC,reviewed_intake_commit=REVIEWED_INTAKE,
        actual_local_head=git(repo,'rev-parse','HEAD'),
        review_delta=git(repo,'diff','--name-status',BASE_NUMERIC,REVIEWED_INTAKE),
        local_v137_artifacts=local,
        source_sha256={str(p.relative_to(repo)):digest(p) for p in (summary,source,jf,cf,tf)},
        summary_claim_findings=flagged,
        actual_J_registry=actual_J,
        prior_M_record_scoring=dict(n=len(err),MAE_nm=sum(map(abs,err))/len(err),
            RMSE_nm=math.sqrt(sum(e*e for e in err)/len(err)),bias_nm=sum(err)/len(err),
            size_error_target_only_pass=targets,scope='OPENED_DEVELOPMENT_NOT_NEW_V137_RESULT'),
        experimental_absolute_validated=False,
        scientific_acceptance='NOT_ISSUED_BY_INTAKE')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();r=audit(a.repo);dest=Path(a.out);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print('INTAKE_AUDIT_WRITTEN_NOT_SCIENCE_PASS')
    return 0
if __name__=='__main__':raise SystemExit(main())
