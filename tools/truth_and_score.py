"""Validator-only truth joins. Never import this module in an estimator.
A published JSON/config is documentary truth, not independent solve-geometry proof.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math
from pathlib import Path
import numpy as np


def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()


def truth_from_sources(repo, sources):
    repo=Path(repo).resolve(); result={}; identities={}
    for dataset, spec in sources.items():
        p=(repo/spec['path']).resolve()
        raw=p.read_bytes()
        if spec.get('expected_git_blob'):
            def git_sha(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
            if spec['expected_git_blob'] not in {git_sha(raw),git_sha(raw.replace(b'\r\n',b'\n'))}:
                raise ValueError(f'{dataset}: truth source differs from fixed published Git object')
        o=json.loads(raw.decode('utf-8-sig'))
        identities[dataset]={'path':str(p),'sha256':sha256(p),'scope':'PUBLISHED_RECORD_NOT_SOLVE_VERIFIED'}
        if spec['format']=='v125_config':
            selection=o.get('plan_selection')
            choices={'MAIN_7x9':'main','FALLBACK_7x7':'fallback'}
            if selection not in choices: raise ValueError('H source lacks an unambiguous plan_selection')
            cases=o['six_new_holdouts']; heights=o['plans'][choices[selection]]['holdout_h_nm']
            if len(cases)!=len(heights): raise ValueError('H case/height lengths differ')
            cases=[dict(c,h_nm=h) for c,h in zip(cases,heights)]
        elif spec['format']=='cases_json':
            cases=o if isinstance(o,list) else o['cases']
        else: raise ValueError('Unknown truth format')
        seen=set()
        for c in cases:
            case=str(c['case']); key=(str(dataset),case)
            if not case.startswith(dataset) or case in seen or key in result: raise ValueError(f'Duplicate/misassigned truth key {key}')
            seen.add(case)
            vals=[float(c[k]) for k in ('D_nm','h_nm','x_nm','y_nm')]
            if not np.isfinite(vals).all() or vals[0]<=0: raise ValueError(f'Invalid truth {key}')
            result[key]=dict(dataset=dataset,case=case,**dict(zip(('D_nm','h_nm','x_nm','y_nm'),vals)),source_sha256=identities[dataset]['sha256'],scope=identities[dataset]['scope'])
    return result,identities


def score_rows(candidates, truth):
    out=[];seen=set()
    for c in candidates:
        key=(c['data_set'],c['case'])
        if key in seen or key not in truth: raise ValueError(f'Duplicate candidate or missing exact truth key {key}')
        seen.add(key); t=truth[key]; d=float(c['candidate_D'])
        if not math.isfinite(d): raise ValueError(f'Nonfinite candidate {key}')
        e=d-t['D_nm']; target=max(5.,.1*t['D_nm'])
        out.append(dict(data_set=key[0],case=key[1],D_true=t['D_nm'],candidate_D=d,err_D=e,abs_err_D=abs(e),target_nm=target,size_error_target_met=abs(e)<=target,
                        h_true=t['h_nm'],h_candidate=float(c['h']),err_h=float(c['h'])-t['h_nm'],
                        reported_D=c.get('reportable_D',''),source_truth_sha256=t['source_sha256'],truth_scope=t['scope'],
                        note='ERROR_SCORING_ONLY_NOT_MEASUREMENT_ACCEPTANCE'))
    return out


def summarize(rows):
    answer={}
    for s in sorted({r['data_set'] for r in rows})+['ALL']:
        a=[r for r in rows if s=='ALL' or r['data_set']==s]
        e=np.asarray([r['err_D'] for r in a],float)
        answer[s]={'n':len(a),'size_error_target_met':sum(r['size_error_target_met'] for r in a),'MAE_nm':float(np.mean(abs(e))),'RMSE_nm':float(np.sqrt(np.mean(e*e))), 'bias_nm':float(np.mean(e)),'median_abs_nm':float(np.median(abs(e))),'max_abs_nm':float(max(abs(e)))}
    answer['not_within_target']=[r['data_set']+'_'+r['case'] for r in rows if not r['size_error_target_met']]
    answer['scientific_limit']='Development record scoring; does not certify source geometry, uniqueness, reportability, or experimental accuracy.'
    return answer


def write_csv(p,rows):
    if not rows: raise ValueError('No result rows')
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo',required=True);ap.add_argument('--config',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();c=json.loads(Path(a.config).read_text(encoding='utf-8'));root=Path(a.repo)
    truth,src=truth_from_sources(root,c['truth_sources'])
    p=root/c['inheritance']['v131_out']/'old_per_particle_candidates.csv'
    rows=score_rows(list(csv.DictReader(p.open(encoding='utf-8-sig',newline=''))),truth)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    write_csv(out/'v131_corrected_scores.csv',rows)
    (out/'v131_corrected_summary.json').write_text(json.dumps(summarize(rows),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'truth_source_identity.json').write_text(json.dumps(src,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summarize(rows)['ALL'],ensure_ascii=False))

if __name__=='__main__':main()
