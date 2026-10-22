"""W7 assembly part 1: calibration table, figures, compatible components,
error separation (validator side), fail-closed reportability, final profiles.
"""
from __future__ import annotations
import argparse, csv, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    val=out.parent/'validation';prof_dir=out.parent/'offline_F2_profiles'/'profiles'
    out.mkdir(parents=True,exist_ok=True)
    v137=json.loads((repo/'config/v137_science_config.json').read_text(encoding='utf-8'))
    env=json.loads((val/'development_error_envelope.json').read_text(encoding='utf-8'))
    eps=env['epsilon_dev_L2']
    # calibration D->C at fixed h (conditional only)
    sys.path.insert(0,str(repo/'tools'))
    from load_field_library import load_library
    from v133_recover_M import optical
    cfg=json.loads((repo/'config/v133_science_config.json').read_text(encoding='utf-8'))
    model,_=load_library(repo/v137['inherited_model']['library'],kind='F2',optical=optical(cfg))
    rows=[]
    for h in (350.,450.,550.):
        for D in np.arange(30.,200.1,5.):
            if h-D/2<100:continue
            C=model.forward((float(D),h,0.,0.)).C
            c13=C[2:15,2:15]
            rows.append(dict(D_nm=float(D),h_nm=h,center_C=float(C[8,8]),peak_C=float(np.max(C)),
                min_C=float(np.min(C)),L2_13=float(np.linalg.norm(c13))))
            sys.stdout.flush()
    (out.parent/'library').mkdir(parents=True,exist_ok=True)
    with open(out.parent/'library'/'calibration_D_h.csv','w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['D_nm','h_nm','center_C','peak_C','min_C','L2_13']);w.writeheader();w.writerows(rows)
    # D100 vs h signed variation
    hrows=[]
    for h in np.arange(350.,550.1,10.):
        if h-50<100:continue
        C=model.forward((100.,float(h),0.,0.)).C
        hrows.append(dict(D_nm=100.,h_nm=float(h),center_C=float(C[8,8]),L2_13=float(np.linalg.norm(C[2:15,2:15]))))
    with open(out.parent/'library'/'calibration_D100_vs_h.csv','w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['D_nm','h_nm','center_C','L2_13']);w.writeheader();w.writerows(hrows)
    # figures
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figdir=out.parent/'figures';figdir.mkdir(parents=True,exist_ok=True)
    plt.figure(figsize=(7,5))
    for i in range(1,7):
        c=f'M{i:02d}'
        p=json.loads((prof_dir/f'{c}.json').read_text(encoding='utf-8'))
        pts=sorted((r['D'],r['loss_L2']) for r in p['rows'] if r['loss_L2'] is not None)
        plt.semilogy([x for x,_ in pts],[y for _,y in pts],label=c,linewidth=1)
        plt.scatter([p['known_joint_theta'][0]],[p['known_joint_loss_L2']],marker='x')
    plt.axhline(eps,color='k',ls='--',lw=1,label='epsilon_dev (frozen)')
    plt.xlabel('D (nm)');plt.ylabel('unscaled L2 on central 13');plt.legend(fontsize=7)
    plt.title('V137 locked-F2 coarse D-profiles (budget-honest, NOT complete)')
    plt.tight_layout();plt.savefig(figdir/'M_F2_profiles.png',dpi=150);plt.close()
    plt.figure(figsize=(6,4))
    for h in (350.,450.,550.):
        sub=[r for r in rows if r['h_nm']==h]
        plt.plot([r['D_nm'] for r in sub],[r['center_C'] for r in sub],label=f'h={h}')
    plt.xlabel('D (nm)');plt.ylabel('signed center C');plt.legend()
    plt.title('CONDITIONAL fixed-height calibration (not absolute sizing)')
    plt.tight_layout();plt.savefig(figdir/'calibration_D_h.png',dpi=150);plt.close()
    # compatible components + error separation + reportability (truth only here)
    import h5py
    truths={x['tag'].removeprefix('holdout_'):float(x['D_nm']) for x in json.loads((repo/v137['M_validator_only_task_records']).read_text(encoding='utf-8'))['cases']}
    comp_rows=[];err_rows=[];rep={}
    sys.path.insert(0,str(repo/'tools'))
    from science_gates import check_profile,check_reportability
    with h5py.File(repo/v137['inherited_model']['prior_observations'],'r') as hf:
        for i in range(1,7):
            c=f'M{i:02d}'
            p=json.loads((prof_dir/f'{c}.json').read_text(encoding='utf-8'))
            Y=np.asarray(hf[c]['score_C'][()],float)
            valid=[r for r in p['rows'] if r['loss_L2'] is not None]
            rmin=min(r['loss_L2'] for r in valid)
            compat=sorted(r['D'] for r in valid if r['loss_L2']<=rmin+eps)
            # contiguous components over the evaluated grid
            comps=[];start=None;prev=None
            for D in compat:
                if start is None:start=D;prev=D;continue
                if D-prev>5.001:comps.append([start,prev]);start=D
                prev=D
            if start is not None:comps.append([start,prev])
            for lo,hi in comps:comp_rows.append(dict(case=c,component=[lo,hi],n_points=sum(1 for D in compat if lo<=D<=hi)))
            p['compatible_D_components']=comps;p['empirical_epsilon_L2']=eps
            # candidate at profile minimum
            best=min(valid,key=lambda r:r['loss_L2'])
            cands=min((r['theta'] for r in valid if r['loss_L2']<=rmin+1e-12),default=None)
            gate=check_profile(p,model_id=p['model_id'],observation_sha256=p['observation_sha256'],
                joint_D=p['known_joint_theta'][0],joint_loss=p['known_joint_loss_L2'])
            evidence=dict(observable_valid=True,locked_F2_valid=True,
                raw_geometry_provenance_valid=False,same_solve_shift_qualified=False,
                field_numerical_qualified=True,optimizer_converged=True,
                search_complete=bool(p['grid_coverage_complete']),profile_complete=False,
                adaptive_coverage_complete=False,joint_profile_consistent=True,
                empirical_model_error_frozen=True,h_xy_boundary_independence_qualified=False,
                detection_pass=False,noise_background_FPR_qualified=False,
                observable_type='SIGNED_STATIC_C_FROM_LINEAR_INTENSITY',
                measurement_mode='NOISY_CAMERA_CONDITIONAL')
            rg=check_reportability(best['theta'][0] if best['theta'] else None,comps,evidence)
            p['profile_gate']=gate;p['reportability_gate']=rg
            p['reportable_D']=rg['reportable_D'];p['profile_scientific_complete']=gate['structurally_complete']
            p['adaptive_coverage_complete']=False
            (out/f'{c}.json').write_text(json.dumps(p,indent=2,ensure_ascii=False,allow_nan=False)+chr(10),encoding='utf-8')
            rep[c]=dict(candidate_D=rg['candidate_D'],reportable_D=rg['reportable_D'],
                diameter_reportable=rg['diameter_reportable'],reason_codes=rg['reason_codes'],
                profile_reason_codes=gate['reason_codes'],
                scope='FAIL_CLOSED_CONDITIONAL_NOT_ABSOLUTE')
            err_rows.append(dict(case=c,truth_D=truths[c],profile_min_D=best['D'],profile_min_L2=best['loss_L2'],
                joint_D=p['known_joint_theta'][0],joint_loss=p['known_joint_loss_L2'],
                abs_err_profile=abs(best['D']-truths[c]),abs_err_joint=abs(p['known_joint_theta'][0]-truths[c]),
                compatible_n_points=len(compat),compatible_span_nm=(compat[-1]-compat[0]) if compat else None,
                truth_role='VALIDATOR_SIDE_ONLY_NOT_IN_ESTIMATOR'))
    with (val/'M_compatible_components.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['case','component','n_points']);w.writeheader()
        for r in comp_rows:r['component']=json.dumps(r['component']);w.writerow(r)
    with (val/'M_error_separation.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(err_rows[0].keys()));w.writeheader();w.writerows(err_rows)
    (val/'reportability_per_particle.json').write_text(json.dumps(rep,indent=2,ensure_ascii=False)+chr(10),encoding='utf-8')
    print('assembled: calibration rows',len(rows),'compat comps',len(comp_rows),
          'reportable',sum(1 for r in rep.values() if r['reportable_D'] is not None))
if __name__=='__main__':main()
