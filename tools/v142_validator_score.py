"""V142 S5b: independent validator (separate process logic) scoring N candidates.

Reads the preregistered truth registry ONLY here; never feeds truth back.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, sys
from pathlib import Path
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--candidates',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve()
    truth=json.loads((repo/'config/v142_new_N_validator_only.json').read_text(encoding='utf-8'))['cases']
    mapping=json.load(open('work/v142_n_validator_mapping.json',encoding='utf-8'))
    cands=list(csv.DictReader(Path(a.candidates).open(encoding='utf-8')))
    rows=[]
    for c in truth:
        anon=mapping['holdout_'+c['case']]['anon_id']
        row=next(r for r in cands if r['anon_case']==anon)
        Dhat=float(row['candidate_D']);Dtrue=float(c['D_nm'])
        target=max(5.0,0.10*Dtrue);err=abs(Dhat-Dtrue)
        rows.append(dict(anon_case=anon,case=c['case'],D_true=Dtrue,D_hat=Dhat,abs_err_nm=err,
            engineering_target_nm=target,pass_engineering=bool(err<=target),
            fit_h=float(row['fit_h']),h_true=float(c['h_nm']),abs_err_h_nm=abs(float(row['fit_h'])-float(c['h_nm'])),
            scope='INDEPENDENT_VALIDATOR_ONLY; 4 cases sparse stress test not domain guarantee'))
    errs=[r['abs_err_nm'] for r in rows]
    import math
    summary=dict(schema='iscat142.n_validator_score.1',n=len(rows),
        pass_engineering=sum(r['pass_engineering'] for r in rows),
        MAE_nm=sum(errs)/len(errs),RMSE_nm=math.sqrt(sum(e*e for e in errs)/len(errs)),
        max_err_nm=max(errs),
        note='candidate_accuracy measured; eligible_reportability still null per incomplete profile/adaptive/detection gates',
        rows=rows)
    with (Path(a.out)/'validation'/'new_N_validator_score.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    json.dump(summary,open(Path(a.out)/'validation'/'new_N_validator_score.json','w',encoding='utf-8'),indent=2,ensure_ascii=False)
    print('VALIDATOR_SCORE pass=%d/%d MAE=%.4fnm max=%.4fnm'%(summary['pass_engineering'],len(rows),summary['MAE_nm'],summary['max_err_nm']))
if __name__=='__main__':main()
