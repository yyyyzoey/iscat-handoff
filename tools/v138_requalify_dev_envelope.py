"""S3: rebuild the H/J/K/L development error scale on the ACTUAL fit observation
dataset (at_offset/C), fixing the V137 root-C + offset-truth mismatch (R05).
Validator side only; truth never enters any estimator.
"""
from __future__ import annotations
import argparse, csv, json, sys
from pathlib import Path
import numpy as np, h5py
sys.path.insert(0, str(Path(__file__).resolve().parent))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();val=Path(a.out).resolve()/'validation';val.mkdir(parents=True,exist_ok=True)
    from load_field_library import load_library
    from v133_recover_M import optical
    v133=json.loads((repo/'config/v133_science_config.json').read_text(encoding='utf-8'))
    model,_=load_library(repo/'results/v128/library/v128_Dh_train_fields.h5',kind='F2',optical=optical(v133))
    sources=[('H','results/v125/library/v125_direct_holdouts.h5','results/v125/validation/holdout_truth_validator_only.json',
              lambda r:(r['D_true_nm'],r['h_true_nm'],r['x_true_nm'],r['y_true_nm'])),
             ('J','results/v126/validation/new_holdout_images.h5','results/v126/validation/holdout_truth_validator_only.json',
              lambda r:(r['D_nm'],r['h_nm'],r['x_nm'],r['y_nm'])),
             ('K','results/v127/validation/holdout_images.h5','results/v127/validation/holdout_truth_validator_only.json',
              lambda r:(r['D_nm'],r['h_nm'],r['x_nm'],r['y_nm'])),
             ('L','results/v128/validation/new_L_direct_images.h5','results/v128/validation/new_L_truth_validator_only.json',
              lambda r:(r['D_nm'],r['h_nm'],r['x_nm'],r['y_nm']))]
    rows=[];calls=0
    for tag,h5p,trup,ext in sources:
        with h5py.File(repo/h5p,'r') as hf:
            _t=json.loads((repo/trup).read_text(encoding='utf-8'))
            truths=_t['cases'] if isinstance(_t,dict) else _t
            for tr in truths:
                case=tr['case'];D0,h0,x0,y0=[float(v) for v in ext(tr)]
                Yoff=np.asarray(hf[case]['at_offset/C'][()],float)[2:15,2:15]
                C=model.forward((D0,h0,x0,y0)).score_C;calls+=1
                R_off=float(np.linalg.norm(C-Yoff))
                # root C is a DIFFERENT observation (zero displacement): document, do not use
                Yroot=np.asarray(hf[case]['C'][()],float)[2:15,2:15]
                C0=model.forward((D0,h0,0.,0.)).score_C;calls+=1
                R_root_at_offset_truth=float(np.linalg.norm(C0-Yoff))  # the V137 (wrong) combination
                rows.append(dict(family=tag,case=case,truth_D=D0,truth_h=h0,truth_x=x0,truth_y=y0,
                    R_at_offset_observation_L2=R_off,R_rootC_with_offset_truth_L2=R_root_at_offset_truth,
                    observation_used='at_offset/C central13',
                    qualified=bool(np.isfinite(R_off)),reason_codes=[]))
    eps=max(max(r['R_at_offset_observation_L2'] for r in rows),1e-12)
    env=dict(schema='iscat138.dev_envelope.1',
        observation_dataset='at_offset/C (the dataset used by the published dev fits)',
        frozen_rule='epsilon_dev = max(1e-12, max truth-point unscaled central13 L2 over opened H/J/K/L)',
        epsilon_dev_L2=eps,
        supersedes='v137 epsilon_dev_L2=0.10972405988601544 (root-C + offset-truth mismatch, R05)',
        n_cases=len(rows),f2_calls_used=calls,
        is_95pct_experimental_confidence_interval=False,
        per_family_max={t:max(r['R_at_offset_observation_L2'] for r in rows if r['family']==t) for t in 'HJKL'})
    with (val/'development_error_requalified.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (val/'development_envelope_frozen.json').write_text(json.dumps(env,indent=2,ensure_ascii=False)+chr(10),encoding='utf-8')
    print('S3 cases',len(rows),'epsilon_dev_new=%.6e'%eps,'f2_calls',calls)
if __name__=='__main__':main()
