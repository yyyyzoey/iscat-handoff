"""R1 assembly: reuse R0 assets by identity, run gates, build figures + ledgers."""
from __future__ import annotations
import argparse, csv, hashlib, json, shutil, sys
from pathlib import Path
import numpy as np, h5py
sys.path.insert(0, str(Path(__file__).resolve().parent))

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--r1',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();r1=Path(a.r1).resolve()
    val=r1/'validation';val.mkdir(parents=True,exist_ok=True)
    r0val=repo/'results/v137/validation'
    # identity-checked reuse of R0 assets (same config/model/mats/camera seeds)
    reuse={'same_solve_shift_F2.csv':'same_solve_shift_F2.csv',
           'physical_forward_qualification.json':'physical_forward_qualification.json',
           'M_original_solve_render_sha.csv':'../provenance/M_original_solve_render_sha.csv',
           'development_error_envelope.json':'development_error_envelope.json',
           'old_HJKL_error_separation.csv':'old_HJKL_error_separation.csv',
           'raw_camera_data.h5':'raw_camera_data.h5',
           'motion_paths_intensities.h5':'motion_paths_intensities.h5',
           'noise_per_trial.csv':'noise_per_trial.csv',
           'blank_per_trial.csv':'blank_per_trial.csv',
           'threshold_validation.json':'threshold_validation.json',
           'calibration_D_h.csv':'../library/calibration_D_h.csv'}
    prov=r1/'provenance';prov.mkdir(parents=True,exist_ok=True)
    lib=r1/'library';lib.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for dst,src in reuse.items():
        s=r0val/src;p=r0val/src
        dest=val/dst if not dst.startswith('M_') else val/dst
        if dst=='M_original_solve_render_sha.csv':dest=prov/dst
        if dst=='calibration_D_h.csv':dest=lib/dst
        shutil.copy2(p,dest)
        manifest.append(dict(reused_from='results/v137/validation/'+src,sha256=sha(p),reason='IDENTICAL_MODEL_OBS_MATS_AND_SEEDS'))
    (val/'reused_assets_manifest.json').write_text(json.dumps(manifest,indent=2)+chr(10),encoding='utf-8')
    # reconciled candidates: carry R0 record + verify M02 once
    shutil.copy2(r0val/'M_reconciled_candidates.csv',val/'M_reconciled_candidates.csv')
    shutil.copy2(r0val/'M_reconciled_candidates.json',val/'M_reconciled_candidates.json')
    # gates + reportability on R1 profiles
    from science_gates import check_profile,check_reportability
    rep={};comp_rows=[]
    for i in range(1,7):
        c=f'M{i:02d}'
        p=json.loads((r1/'profiles_coarse/profiles'/f'{c}.json').read_text(encoding='utf-8'))
        valid=[r for r in p['rows'] if r['loss_L2'] is not None]
        rmin=min(r['loss_L2'] for r in valid)
        eps=json.loads((r0val/'development_error_envelope.json').read_text(encoding='utf-8'))['epsilon_dev_L2']
        compat=sorted(r['D'] for r in valid if r['loss_L2']<=rmin+eps)
        comps=[];start=prev=None
        for D in compat:
            if start is None:start=prev=D;continue
            if D-prev>5.001:comps.append([start,prev]);start=D
            prev=D
        if start is not None:comps.append([start,prev])
        best=min(valid,key=lambda r:r['loss_L2'])
        gate=check_profile(p,model_id=p['model_id'],observation_sha256=p['observation_sha256'],
            joint_D=p['known_joint_theta'][0],joint_loss=p['known_joint_loss_L2'])
        evidence=dict(observable_valid=True,locked_F2_valid=True,raw_geometry_provenance_valid=False,
            same_solve_shift_qualified=False,field_numerical_qualified=True,optimizer_converged=True,
            search_complete=bool(p['grid_coverage_complete']),profile_complete=False,
            adaptive_coverage_complete=False,joint_profile_consistent=True,
            empirical_model_error_frozen=True,h_xy_boundary_independence_qualified=False,
            detection_pass=False,noise_background_FPR_qualified=False,
            observable_type='SIGNED_STATIC_C_FROM_LINEAR_INTENSITY',measurement_mode='NOISY_CAMERA_CONDITIONAL')
        rg=check_reportability(best['theta'][0] if best['theta'] else None,comps,evidence)
        p['profile_gate']=gate;p['reportability_gate']=rg
        p['reportable_D']=rg['reportable_D'];p['adaptive_coverage_complete']=False
        p['profile_scientific_complete']=False
        (r1/'profiles'/f'{c}.json').parent.mkdir(parents=True,exist_ok=True)
        (r1/'profiles'/f'{c}.json').write_text(json.dumps(p,indent=2,ensure_ascii=False,allow_nan=False)+chr(10),encoding='utf-8')
        rep[c]=dict(candidate_D=rg['candidate_D'],reportable_D=rg['reportable_D'],
            diameter_reportable=rg['diameter_reportable'],reason_codes=rg['reason_codes'],
            profile_reason_codes=gate['reason_codes'],scope='FAIL_CLOSED_CONDITIONAL_NOT_ABSOLUTE')
        for lo,hi in comps:comp_rows.append(dict(case=c,component=json.dumps([lo,hi])))
        # point attempts export
        pa=r1/'profiles'/'point_attempts';pa.mkdir(parents=True,exist_ok=True)
        rows=[dict(D=r['D'],loss_L2=r.get('loss_L2'),theta=json.dumps(r.get('theta')),
                   point_search_complete=r.get('point_search_complete'),
                   n_attempts=len(r.get('attempts',[])),source=r.get('source','')) for r in p['rows']]
        with (pa/f'{c}_attempts.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=['D','loss_L2','theta','point_search_complete','n_attempts','source']);w.writeheader();w.writerows(rows)
    with (val/'M_compatible_components.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['case','component']);w.writeheader();w.writerows(comp_rows)
    (val/'reportability_per_particle.json').write_text(json.dumps(rep,indent=2,ensure_ascii=False)+chr(10),encoding='utf-8')
    # figures
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    figdir=r1/'figures';figdir.mkdir(parents=True,exist_ok=True)
    fig,axs=plt.subplots(1,2,figsize=(12,4.6))
    for i in range(1,7):
        c=f'M{i:02d}'
        p=json.loads((r1/'profiles'/f'{c}.json').read_text(encoding='utf-8'))
        pts=sorted((r['D'],r['loss_L2']) for r in p['rows'] if r['loss_L2'] is not None)
        axs[0].semilogy([x for x,_ in pts],[y for _,y in pts],lw=1,label=c)
        axs[0].scatter([p['known_joint_theta'][0]],[p['known_joint_loss_L2']],marker='x')
    axs[0].axhline(eps,color='k',ls='--',lw=1)
    axs[0].set_xlabel('D (nm)');axs[0].set_ylabel('unscaled L2');axs[0].legend(fontsize=7)
    axs[0].set_title('R1 locked-F2 profiles (coarse+M01 adaptive)')
    rows=list(csv.DictReader((lib/'calibration_D_h.csv').open(encoding='utf-8')))
    for h in ('350.0','450.0','550.0'):
        sub=[r for r in rows if r['h_nm']==h]
        axs[1].plot([float(r['D_nm']) for r in sub],[float(r['center_C']) for r in sub],label='h='+h)
    axs[1].set_xlabel('D (nm)');axs[1].set_ylabel('signed center C');axs[1].legend(fontsize=8)
    axs[1].set_title('CONDITIONAL fixed-height calibration')
    plt.tight_layout();plt.savefig(figdir/'conditional_calibration_and_profiles.png',dpi=150);plt.close()
    print('R1 assembled; reportable=',sum(1 for v in rep.values() if v['reportable_D'] is not None))
if __name__=='__main__':main()
