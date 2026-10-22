"""W4: development-set error separation and frozen empirical epsilon_dev.

Reads opened H/J/K/L direct images and validator truth records (validator side
only). Published candidate losses are REUSED read-only, never refitted here.
epsilon_dev is frozen from the maximum truth-point unscaled L2 over qualified
dev direct images, merged with a 1e-12 numeric floor.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, sys
from pathlib import Path
import numpy as np, h5py
sys.path.insert(0, str(Path(__file__).resolve().parent))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
    from load_field_library import load_library
    from v133_recover_M import optical
    from scipy.optimize import minimize_scalar, least_squares
    cfg=json.loads((repo/'config/v133_science_config.json').read_text(encoding='utf-8'))
    v137=json.loads((repo/'config/v137_science_config.json').read_text(encoding='utf-8'))
    m=v137['inherited_model']
    model,_=load_library(repo/m['library'],kind='F2',optical=optical(cfg))
    lo=np.array([model.Ds[0],model.Hs[0]]);hi=np.array([model.Ds[-1],model.Hs[-1]])
    sources=[
     ('H','results/v125/library/v125_direct_holdouts.h5','results/v125/validation/holdout_truth_validator_only.json',
      lambda r:(r['D_true_nm'],r['h_true_nm'],r['x_true_nm'],r['y_true_nm']),'v125','results/v125/validation/holdout_profiles'),
     ('J','results/v126/validation/new_holdout_images.h5','results/v126/validation/holdout_truth_validator_only.json',
      lambda r:(r['D_nm'],r['h_nm'],r['x_nm'],r['y_nm']),'v126',None),
     ('K','results/v127/validation/holdout_images.h5','results/v127/validation/holdout_truth_validator_only.json',
      lambda r:(r['D_nm'],r['h_nm'],r['x_nm'],r['y_nm']),'v127',None),
     ('L','results/v128/validation/new_L_direct_images.h5','results/v128/validation/new_L_truth_validator_only.json',
      lambda r:(r['D_nm'],r['h_nm'],r['x_nm'],r['y_nm']),'v128',None)]
    rows=[];truth_losses=[];calls_total=0
    for tag,h5p,trup,ext,ver,profdir in sources:
        with h5py.File(repo/h5p,'r') as hf:
            _t=json.loads((repo/trup).read_text(encoding='utf-8'));truths=_t['cases'] if isinstance(_t,dict) else _t
            for tr in truths:
                case=tr['case'];D0,h0,x0,y0=[float(v) for v in ext(tr)]
                Y=np.asarray(hf[case]['C'][()],float)
                if Y.shape==(17,17):Y=Y[2:15,2:15]
                if Y.shape!=(13,13):raise SystemExit(case+' unexpected score shape '+str(Y.shape))
                C=model.forward((D0,h0,x0,y0)).score_C
                R=float(np.linalg.norm(C-Y));truth_losses.append(R)
                # oracle D only (truth h/xy fixed)
                fD=lambda D: float(np.linalg.norm(model.forward((float(D),h0,x0,y0)).score_C-Y))
                rs=minimize_scalar(fD,bounds=(model.Ds[0],model.Ds[-1]),method='bounded',
                    options=dict(xatol=0.05))
                calls_total+=getattr(rs,'nfev',0)+2
                # oracle D/h (truth xy fixed)
                fh=lambda p: float(np.linalg.norm(model.forward((float(p[0]),float(p[1]),x0,y0)).score_C-Y))
                rr=least_squares(lambda p:[fh(p)],x0=[D0,h0],bounds=(lo,hi),max_nfev=120,
                    x_scale=[50.,50.])
                calls_total+=int(rr.nfev)
                rows.append(dict(family=tag,case=case,truth_D=D0,truth_h=h0,truth_x=x0,truth_y=y0,
                    R_truth_full_L2=R,R_oracle_D_only_L2=float(rs.fun),D_oracle_D_only=float(rs.x),
                    R_oracle_Dh_L2=float(np.sqrt(rr.fun[0]**2)) if rr.fun.ndim else float(abs(rr.fun[0])),
                    D_oracle_Dh=float(rr.x[0]),h_oracle_Dh=float(rr.x[1]),
                    numeric_floor=1e-12))
    # published candidates reused read-only
    pub={}
    import csv as _csv
    p=repo/'results/v127/validation/holdout_per_particle.csv'
    if p.is_file():
        for r in _csv.DictReader(p.open(encoding='utf-8')):pub['K_'+r.get('case',r.get('particle','?'))]=r
    p=repo/'results/v126/validation/holdout_per_particle.csv'
    if p.is_file():
        for r in _csv.DictReader(p.open(encoding='utf-8')):pub['J_'+r.get('case',r.get('particle','?'))]=r
    for r in rows:
        key=r['family']+'_'+r['case']
        if key in pub:
            c=pub[key]
            r['published_candidate_D']=c.get('candidate_D') or c.get('D_candidate') or c.get('fit_D')
            r['published_candidate_loss_L2']=c.get('loss_L2') or c.get('loss') or c.get('residual_L2')
            r['published_source']='REUSED_READ_ONLY_'+r['family'].replace('K_','v127_').replace('J_','v126_')
        else:
            r['published_candidate_D']=None;r['published_candidate_loss_L2']=None;r['published_source']='NOT_RESOLVED_IN_THIS_PASS'
    epsilon=max(max(truth_losses),1e-12)
    env=dict(schema='iscat137.dev_error_envelope.1',
        frozen_rule='epsilon_dev = max(1e-12, max over opened H/J/K/L truth-point unscaled central13 L2)',
        epsilon_dev_L2=epsilon,per_family_max={t:max(r['R_truth_full_L2'] for r in rows if r['family']==t) for t in 'HJKL'},
        n_cases=len(rows),numeric_floor=1e-12,
        compatible_rule='R_p(D) <= R_min + epsilon_dev_L2 (same unsquared L2)',
        is_95pct_experimental_confidence_interval=False,
        oracle_F2_calls=calls_total)
    with (out/'old_HJKL_error_separation.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)
    (out/'development_error_envelope.json').write_text(json.dumps(env,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('W4 cases=',len(rows),'epsilon_dev=%.6e'%epsilon,'oracle_calls=',calls_total)
if __name__=='__main__':main()
