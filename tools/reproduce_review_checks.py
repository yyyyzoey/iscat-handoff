import argparse, hashlib, json, pathlib, platform, sys
import numpy as np
from scipy.optimize import least_squares
from scipy.stats import beta
parser=argparse.ArgumentParser(description='V126 published-table arithmetic and source-equivalent diagnostic fixtures; NOT BEM or HDF5 replay')
parser.add_argument('--out',default='v126_review_recomputed.json')
parser.add_argument('--prior-contract',default=None,help='Optional exact V126 Markdown bytes for Git-blob comparison')
args=parser.parse_args()
outfile=pathlib.Path(args.out).resolve()
outfile.parent.mkdir(parents=True,exist_ok=True)
D=np.array([41.,67.,89.,123.,151.,183.])
est=np.array([33.93322283462359,67.48123236405084,90.83028724479271,126.6535642093631,159.00091654016853,199.99999999999974])
e=est-D
p=pathlib.Path(args.prior_contract).read_bytes() if args.prior_contract else None
rows=[{'case':f'J{i+1:02}', 'D_true_nm':float(D[i]),'D_est_nm':float(est[i]),'error_nm':float(e[i]),'contract_error_goal_nm':float(max(5.,.1*D[i])), 'error_only_meets_goal':bool(abs(e[i])<=max(5.,.1*D[i]))}for i in range(6)]
# This is a minimal analytic optimizer diagnostic, NOT the optical forward.
weak=lambda x: np.array([1e-8*(x[0]-83.7)])
a=least_squares(weak,[100.],bounds=([30.],[200.]),xtol=1e-10,ftol=1e-12)
b=least_squares(lambda x:weak(x)/1e-6,[100.],bounds=([30.],[200.]),xtol=1e-10,ftol=1e-12,gtol=1e-12)
# Reproduce the exact V126 path generation, but only record support usage.
pathrows=[]
for diameter in [55.,115.,185.]:
 for k in range(4):
  seed=126500+int(diameter)*10+k
  dt=1.25e-6;npre=80;n=1441
  times=(np.arange(n)-npre)*1.25
  diffusion=1.380649e-23*299.15/(3*np.pi*.870e-3*diameter*1e-9)
  pos=np.zeros((n,3));pos[0]=[0,0,450]
  pos[1:]=pos[0]+np.cumsum(np.random.default_rng(seed).normal(0,1e9*np.sqrt(2*diffusion*dt),(n-1,3)),axis=0)
  for exp in [25.,100.]:
   bad=0;badxy=0
   for j in range(8):
    w=pos[(times>=j*200-exp/2)&(times<=j*200+exp/2)]
    bad+=int(np.any((w[:,2]<350)|(w[:,2]>550)))
    badxy+=int(np.any(np.abs(w[:,:2])>500))
   pathrows.append({'D':diameter,'track':k,'exposure_us':exp,'height_outside_frames':bad,'xy_outside_frames':badxy})
r={
 'review_scope':'Recomputed from explicitly transcribed published six-row table; source-equivalent small fixtures, not H5/BEM replay',
 'v126_commit':'b546d80beb0dc4789effac8c192896e5f45876e9',
 'local_received_v126_contract':({'bytes':len(p),'sha256':hashlib.sha256(p).hexdigest(),'git_blob_sha1':hashlib.sha1(b'blob '+str(len(p)).encode()+b'\0'+p).hexdigest()} if p is not None else {'checked_this_run':False,'expected_git_blob_sha1':'f7a47b0c3b607e2fd814185dbaf09fccc87221fb'}),
 'holdout_rows':rows,
 'summary':{'n':6,'bias_nm':float(e.mean()),'mae_nm':float(np.mean(abs(e))),'rmse_nm':float(np.sqrt(np.mean(e*e))),'median_absolute_nm':float(np.median(abs(e))),'max_absolute_nm':float(max(abs(e))),'within_8nm':int((abs(e)<=8).sum()),'error_only_contract_goal_count':sum(r['error_only_meets_goal'] for r in rows)},
 'profile_grid':{'code':'np.arange(30.,200.+1e-9,4.)','last_D':float(np.arange(30.,200.+1e-9,4.)[-1]),'contains_200':bool(200. in np.arange(30.,200.+1e-9,4.))},
 'M2_resolution':{'method':'source exposes 2nm fixed grid near a single winning D node, not continuous optimization', 'max_support_examples':{str(D):list(np.arange(max(30,D-12),min(200,D+12)+1e-9,2.)) for D in [30.,50.,70.,100.,130.,160.,200.]}},
 'binomial_3_of_60':{'published_code_beta_4_58':float(beta.ppf(.95,4,58)),'exact_CP_beta_4_57':float(beta.ppf(.95,4,57)),'zero_of_60_upper':float(1-.05**(1/60))},
 'optical_agnostic_gtol_fixture':{'truth':83.7,'default_gtol_result':float(a.x[0]),'default_status':int(a.status),'default_nfev':int(a.nfev),'scaled_result':float(b.x[0]),'scaled_status':int(b.status),'important':'Demonstrates success flag insufficiency, not proof of the cause of a particular optical case'},
 'source_equivalent_trajectory_support':pathrows,
 'support_violations_frames_out_of_192':sum(r['height_outside_frames'] for r in pathrows),
 'camera_events_single_complete_code_execution':{'E':(16*3*2+3*80+3*60+6*3*5)*9,'F_if_192_frames':192*9,'sum':(16*3*2+3*80+3*60+6*3*5+192)*9,'published_resource_csv':5670,'not_actual_run_audit':True},
}
r['execution_environment']={'python':sys.version.split()[0],'platform':platform.platform(),'numpy':np.__version__}
outfile.write_text(json.dumps(r,indent=2,allow_nan=False),encoding='utf-8')
print(json.dumps({k:v for k,v in r.items() if k not in ['source_equivalent_trajectory_support','M2_resolution']},indent=2))
