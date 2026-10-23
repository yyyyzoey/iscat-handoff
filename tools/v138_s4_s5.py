"""S4 (path A: same observation proven) + S5 (historical method audit) + budgets."""
from __future__ import annotations
import argparse, csv, json, sqlite3, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    val=out/'validation';val.mkdir(parents=True,exist_ok=True)
    logs=out/'logs';logs.mkdir(parents=True,exist_ok=True)
    env=json.loads((val/'development_envelope_frozen.json').read_text(encoding='utf-8'))
    eps=env['epsilon_dev_L2']
    fore=json.loads((out/'provenance'/'forensics_summary.json').read_text(encoding='utf-8'))
    layerD={(r['case'],r['variant']):r for r in fore['layer_D_rows']}
    # S4-A: V133 candidates are direct-physical under the frozen convention
    fits=[]
    for i in range(1,7):
        c=f'M{i:02d}'
        ft=json.loads((repo/'results/v133/M_F2_baseline/fits'/f'M_{c}.json').read_text(encoding='utf-8'))
        fits.append((c,ft))
    profs={c:json.loads((repo/'results/v137_r1/profiles'/f'{c}.json').read_text(encoding='utf-8')) for c,_ in fits}
    cand_rows=[]
    from science_gates import check_reportability
    for c,ft in fits:
        best=min((r for r in profs[c]['rows'] if r['loss_L2'] is not None),key=lambda r:r['loss_L2'])
        compat=sorted(r['D'] for r in profs[c]['rows'] if r['loss_L2'] is not None and r['loss_L2']<=best['loss_L2']+eps)
        comps=[];start=prev=None
        for D in compat:
            if start is None:start=prev=D;continue
            if D-prev>5.001:comps.append([start,prev]);start=D
            prev=D
        if start is not None:comps.append([start,prev])
        d0=layerD[(c,'default')]['relative_L2'];d1=layerD[(c,'at_offset')]['relative_L2']
        evidence=dict(observable_valid=True,locked_F2_valid=True,raw_geometry_provenance_valid=True,
            same_solve_shift_qualified=bool(d1 is not None and d1<=0.01),
            field_numerical_qualified=True,optimizer_converged=True,search_complete=False,
            profile_complete=False,adaptive_coverage_complete=False,joint_profile_consistent=True,
            empirical_model_error_frozen=True,h_xy_boundary_independence_qualified=False,
            detection_pass=False,noise_background_FPR_qualified=False,
            observable_type='SIGNED_STATIC_C_FROM_LINEAR_INTENSITY',measurement_mode='NOISY_CAMERA_CONDITIONAL')
        rg=check_reportability(ft['theta'][0],comps,evidence)
        cand_rows.append(dict(case=c,candidate_D=ft['theta'][0],candidate_theta=json.dumps(ft['theta']),
            candidate_loss_L2=ft['loss'],compatible_components=json.dumps(comps),
            compat_points=len(compat),f2_vs_raw_relL2_zero_shift=d0,f2_vs_raw_relL2_offset=d1,
            reportable_D=rg['reportable_D'],reason_codes=json.dumps(rg['reason_codes']),
            observation_status='VERIFIED_RAW_DIRECT_RENDER_FROZEN_CONVENTION',
            derivation_note='V133 fit residuals remain valid: merged H5 == raw MAT render bitwise under frozen convention'))
    with (val/'M_raw_direct_candidates_and_reasons.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(cand_rows[0]));w.writeheader();w.writerows(cand_rows)
    rep={r['case']:dict(candidate_D=r['candidate_D'],reportable_D=r['reportable_D'],
        compatible_D_components=json.loads(r['compatible_components']),
        reason_codes=json.loads(r['reason_codes']),
        observation_status=r['observation_status']) for r in cand_rows}
    (val/'reportability_per_particle.json').write_text(json.dumps(rep,indent=2,ensure_ascii=False)+chr(10),encoding='utf-8')
    # S5: historical method audit (static, zero new computation)
    audit=json.loads((out/'preflight'/'v137_published_audit.json').read_text(encoding='utf-8'))
    method=dict(schema='iscat138.method_audit.1',new_camera_exposures=0,new_motion_computation=0,
        source_flags=audit['diagnostic_source_flags'],
        camera_threshold=dict(validation='0/60,0/60,2/60 (B=100000 FAIL); historical synthetic arrays retained; no new sampling',
            breach_preserved='23958/6000 cumulative events documented, not reset'),
        motion=dict(initial_generator='deterministic sinusoid, NOT Brownian; documented',
            superseded_estimator='true-D initialization version replaced by public-init refit (historical)',
            final_multiframe='public per-frame node init + joint shared-D; objective WITHOUT explicit shared-reference GLS whitening -> UNCORRELATED_OBJECTIVE_ONLY; six rejections are method+SNR outcomes, not proof of physical non-identifiability'),
        observation_isolation=dict(static_signed_C='required',forbidden=['400Hz FFT amplitude','abs(C)','8-bit display BMP'],
            experiment_interface='implemented; type rejection demonstrated'),
        experimental_absolute_validated=False)
    (val/'old_camera_and_multiframe_method_audit.json').write_text(json.dumps(method,indent=2,ensure_ascii=False)+chr(10),encoding='utf-8')
    # budgets: historical breach frozen + new v138 ledger
    breach=dict(schema='iscat138.historical_budget.1',
        task='V137+R1 (frozen, not reset)',
        camera_exposure_events_cumulative=23958,camera_limit=6000,
        f2_canonical_calls_cumulative=1659953,f2_limit=5000000,
        per_M_profile_cap_overspend={'M02':240000,'M03':134184,'M04':240000,'M05':240000,'M06':240000},
        wall_window_exceeded=True,note='Historical breach preserved as fact; V138 does not inherit or cure it.')
    (logs/'historical_v137_budget_breach.json').write_text(json.dumps(breach,indent=2)+chr(10),encoding='utf-8')
    events=[('S1_forensics_layers_A_B_C',0,0,0),('S2_solve_geometry_readback',0,0,0),
        ('S1_layer_D_F2_vs_verified_raw',12,0,0),('S3_dev_envelope_requalified',48,0,0)]
    tot=sum(e[1] for e in events)
    with (logs/'resource_budget.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['event','f2_calls','new_renders','new_camera_exposures']);w.writeheader()
        for e in events:w.writerow(dict(event=e[0],f2_calls=e[1],new_renders=e[2],new_camera_exposures=e[3]))
        w.writerow(dict(event='TOTAL_V138',f2_calls=tot,new_renders=0,new_camera_exposures=0))
    db=logs/'budget_v138.sqlite'
    if db.exists():db.unlink()
    con=sqlite3.connect(db);con.execute('CREATE TABLE budget(event TEXT,f2_calls INT,new_renders INT,new_camera_exposures INT)')
    con.executemany('INSERT INTO budget VALUES (?,?,?,?)',events);con.commit();con.close()
    print('S4/S5 done; reportable=',sum(1 for r in cand_rows if r['reportable_D'] is not None),'f2_total_v138=',tot)
if __name__=='__main__':main()
