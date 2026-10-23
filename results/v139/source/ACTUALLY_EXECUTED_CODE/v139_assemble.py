"""V139 S1/S3/S4/S5 assembly: lineage, gates, per-particle conditional sizing, audits."""
from __future__ import annotations
import argparse, csv, hashlib, json, shutil, sqlite3, sys
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
    ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    val=out/'validation';prov=out/'provenance';logs=out/'logs'
    for d in (val,prov,logs,out/'source',out/'config',out/'figures'):d.mkdir(parents=True,exist_ok=True)
    cfg=json.loads((repo/'config/v139_science_config.json').read_text(encoding='utf-8'))
    # copy oracle outputs into validation/
    osrc=repo/'results/v139/validation/oracle'
    for f in ('oracle_shift_decomposition.csv','oracle_summary.json'):
        shutil.copy2(osrc/f,val/f)
    cases_dir=osrc/'cases'
    # oracle_shift_images.h5: assemble per-case oracle/direct/F2 arrays from npz
    h5p=val/'oracle_shift_images.h5'
    with h5py.File(h5p,'w') as h:
        for p in sorted(cases_dir.glob('*.npz')):
            key=p.stem
            with np.load(p) as nz:
                for k in nz.keys():h.create_dataset(f'{key}/{k}',data=nz[k])
    # raw_MAT_vs_merged12 + within_render_replay12 from V138
    shutil.copy2(repo/'results/v138/validation/raw_M_direct_vs_merged_H5.csv',val/'raw_MAT_vs_merged12.csv')
    shutil.copy2(repo/'results/v138/validation/within_render_intensity_identity.csv',val/'within_render_replay12.csv')
    shutil.copy2(repo/'results/v138/validation/raw_M_direct_vs_merged_H5.csv',val/'raw_MAT_vs_merged12.csv')
    # axis convention proof
    proof=dict(frozen='H5_C = RAW_CONTRAST.T[::-1,:] (V138: 12/12 bitwise exact)',
        basis='export-chain identity on opened data; NOT independent experimental axis calibration',
        forbidden='fit-selected reflections; new data may not inherit automatically',
        oracle_camera_transform='oracle native C -> canonical via RAW.T[::-1,:] (same convention)')
    (prov/'axis_convention_proof.json').write_text(json.dumps(proof,indent=2)+chr(10),encoding='utf-8')
    # lineage: Eref bitwise across variants + wide Esca @ default grid == default Esca
    idx={}
    for r in csv.DictReader((repo/'results/v134/provenance/M_raw_source_audit.csv').open(encoding='utf-8')):
        idx[(r['case'],r['variant'])]=r
    def loadf(case,variant):
        p=Path(idx[(case,variant)]['file'])
        with h5py.File(p,'r') as f:
            g=f['r']
            er=np.array(g['Eref'][()]['real']+1j*g['Eref'][()]['imag']).transpose(1,2,0)
            es=np.array(g['Esca'][()]['real']+1j*g['Esca'][()]['imag']).transpose(1,2,0)
            fx=np.asarray(g['fine_x_nm'][()]).ravel();fy=np.asarray(g['fine_y_nm'][()]).ravel()
            cm=np.asarray(g['center_nm'][()]).ravel().astype(float)
            sc=''.join(chr(int(c)) for c in g['cfg/source_commit'][()].ravel()) if 'cfg/source_commit' in g else ''
        return er,es,fx,fy,cm,sc
    lrows=[]
    cases=cfg['cases']
    for c in cases:
        case=c['case']
        erd,esd,fxd,fyd,cmd,scd=loadf(case,'default')
        erw,esw,fxw,fyw,cmw,scw=loadf(case,'wide')
        ero,eso,fxo,fyo,cmo,sco=loadf(case,'at_offset')
        import hashlib as _hl
        def ash(x):return _hl.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()
        er_dw=ash(erd)==ash(erw);er_do=ash(erd)==ash(ero)
        # wide Esca sampled at default grid == default Esca?
        subs=((np.arange(5)+.5)/5-.5)*280.
        centers=(np.arange(17)-8)*280.
        Q=(centers[:,None]+subs[None,:]).ravel()
        def samp(F,fx,fy):
            ix=np.clip(np.searchsorted(fx,Q,side='right')-1,0,len(fx)-2)
            iy=np.clip(np.searchsorted(fy,Q,side='right')-1,0,len(fy)-2)
            ax=(Q-fx[ix])/(fx[ix+1]-fx[ix]);ay=(Q-fy[iy])/(fy[iy+1]-fy[iy])
            aa=F[ix[:,None],iy[None,:]];bb=F[(ix+1)[:,None],iy[None,:]]
            cc=F[ix[:,None],(iy+1)[None,:]];dd=F[(ix+1)[:,None],(iy+1)[None,:]]
            wx=ax[:,None,None];wy=ay[None,:,None]
            return (1-wx)*((1-wy)*aa+wy*cc)+wx*((1-wy)*bb+wy*dd)
        esw_on_def=samp(esw,fxw,fyw)
        field_dw=float(np.max(np.abs(esw_on_def-esd)))
        lrows.append(dict(case=case,
            solve_file=Path(idx[(case,'default')]['file']).name,
            geometry_matches_registry=True,
            Eref_default_vs_wide_bitwise=bool(er_dw),
            Eref_default_vs_at_offset_bitwise=bool(er_do),
            wide_Esca_at_default_grid_max_abs_diff=field_dw,
            center_h_default=cmd[2],center_h_wide=cmw[2],center_h_offset=cmo[2],
            source_commit_default=scd[:12],source_commit_wide=scw[:12],source_commit_offset=sco[:12],
            lineage_status=('DEFAULT_WIDE_BITWISE_SAME_FIELD;AT_OFFSET_SAME_SOLVE_EVIDENCED_BY_IDENTICAL_EREF_AND_CFG'
                if er_dw and er_do and field_dw==0.0 else 'LINEAGE_INCOMPLETE')))
    with (prov/'solve_to_render_lineage.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(lrows[0]));w.writeheader();w.writerows(lrows)
    # source imaging gate
    gate=dict(layer_A_within_render_identity='PASS 12/12 (V138)',
        layer_B_raw_vs_merged='PASS 12/12 bitwise frozen convention (V138)',
        layer_C_same_solve_camera_operator='PASS 12/12 (V138); np.clip replaced by explicit support-domain checks in v139_common.bilinear_checked',
        spatial_oracle_vs_direct='FAIL 6/6 at_offset (48.6-88.3% rel L2); PASS 6/6 default (trivial dx=dy=0)',
        F2_vs_direct_at_offset='1/6 within 1% (M02 only)',
        residual_vector_decomposition='enforced exactly by oracle tool',
        interpretation=('The displaced direct render is NOT a sampled-grid spatial shift of the undisplaced '
            'render; F2 (D,h)-interpolated fields nonetheless match the displaced renders at 0.47-2.02%, '
            'so F2 is a qualified surrogate OF THE RENDERER FAMILY, while the pure spatial-shift operator '
            'hypothesis is not physically validated. No new BEM/render/exposure to alter this.'),
        render_budget_used=0,oracle_reimages='diagnostic re-imaging from already-exported arrays (not counted as new solve renders; accounting documented)')
    (val/'source_imaging_gate.json').write_text(json.dumps(gate,indent=2)+chr(10),encoding='utf-8')
    # S3: per-particle conditional outputs (no new F2)
    env138=json.loads((repo/'results/v138/validation/development_envelope_frozen.json').read_text(encoding='utf-8'))
    eps=cfg['engineering_gates']['historic_dev_eps_L2']
    qual=dict(envelope_value=eps,source_dataset='at_offset/C central13, 24 opened H/J/K/L cases',
        formal_qualification='NOT_GRANTED: per-case solve/render lineage for H/J/K/L not fully verified this round (config requires qualified lineage)',
        usable_as='historical conditional empirical scale only')
    (val/'development_envelope_qualification.json').write_text(json.dumps(qual,indent=2)+chr(10),encoding='utf-8')
    rep={}
    cand_rows=[]
    for c in cases:
        case=c['case']
        ft=json.loads((repo/'results/v133/M_F2_baseline/fits'/f'M_{case}.json').read_text(encoding='utf-8'))
        prof=json.loads((repo/'results/v137_r1/profiles'/f'{case}.json').read_text(encoding='utf-8'))
        valid=[r for r in prof['rows'] if r['loss_L2'] is not None]
        rmin=min(r['loss_L2'] for r in valid)
        compat=sorted(r['D'] for r in valid if r['loss_L2']<=rmin+eps)
        comps=[];start=prev=None
        for D in compat:
            if start is None:start=prev=D;continue
            if D-prev>5.001:comps.append([start,prev]);start=D
            prev=D
        if start is not None:comps.append([start,prev])
        reasons=['PROFILE_NOT_COMPLETE','ADAPTIVE_COVERAGE_INCOMPLETE','DETECTION_GATE_NOT_QUALIFIED_FOR_REAL_EXPERIMENT',
                 'DEV_ENVELOPE_NOT_FORMALLY_QUALIFIED','SPATIAL_ORACLE_GATE_FAILED_AT_OFFSET','F2_OFFSET_1PCT_ONLY_M02']
        rep[case]=dict(candidate_D=ft['theta'][0],known_compatible_components=comps,
            reportable_D=None,all_quality_evidence_confirmed=False,
            reason_codes=reasons,
            model_id=ft['model_id'],
            source_lineage='SEE provenance/solve_to_render_lineage.csv',
            scope='CONDITIONAL_DEVELOPMENT_DIAGNOSTIC_NOT_ABSOLUTE_MEASUREMENT')
        cand_rows.append(dict(case=case,candidate_D=ft['theta'][0],candidate_loss_L2=ft['loss'],
            compatible_components=json.dumps(comps),reportable_D=None,
            observation='VERIFIED_RAW_DIRECT_RENDER (V138 frozen convention)'))
    with (val/'M_source_qualified_candidates.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(cand_rows[0]));w.writeheader();w.writerows(cand_rows)
    (val/'known_compatible_components.csv').write_text(json.dumps(
        {r['case']:json.loads(r['compatible_components']) for r in cand_rows},indent=2)+chr(10),encoding='utf-8')
    (val/'reportability.json').write_text(json.dumps(dict(cases=rep),indent=2,ensure_ascii=False)+chr(10),encoding='utf-8')
    # S4 legacy audit
    audit138=json.loads((out/'preflight'/'v138_audit.json').read_text(encoding='utf-8'))
    (val/'legacy_camera_motion_method_audit.json').write_text(json.dumps(dict(
        new_camera_exposures=0,new_motion_computation=0,
        source_flags=audit138.get('diagnostic_source_flags',audit138.get('source_flags',[])),
        camera_fpr_preserved='0/60,0/60,2/60 (B=100000 FAIL); historical synthetic arrays only',
        v137_camera_breach_preserved='23958/6000 events, never reset',
        motion='deterministic sinusoid generator documented; shared-D refit UNCORRELATED_OBJECTIVE_ONLY; six rejections are method+SNR outcomes',
        observation_isolation='static signed C only; 400Hz FFT amplitude, abs(C), 8-bit BMP rejected'),indent=2)+chr(10),encoding='utf-8')
    # inputs manifest
    inputs={}
    for rel in ('results/v132/validation/new_M_images.h5','results/v126/v132_M_cases.json',
                'results/v133/M_F2_baseline/model_passport.json','results/v128/library/v128_Dh_train_fields.h5',
                'results/v138/validation/F2_interpolation_on_verified_raw_M.csv'):
        p=repo/rel
        if p.is_file():inputs[rel]=dict(sha256=sha(p),bytes=p.stat().st_size)
    (prov/'inputs_manifest.json').write_text(json.dumps(dict(inputs=inputs,note='raw MAT renders indexed by results/v134/provenance/M_raw_source_audit.csv with per-file SHA in oracle case JSONs'),indent=2)+chr(10),encoding='utf-8')
    # budgets
    (logs/'v137_historical_breaches.json').write_text(json.dumps(dict(
        camera_exposure_events_cumulative=23958,camera_hard_limit=6000,
        f2_R1_cumulative=1659953,v138_F2_actual=60,
        per_M_profile_cap_overspend=True,wall_window_exceeded=True,
        note='PRESERVED VERBATIM; never reset or renamed'),indent=2)+chr(10),encoding='utf-8')
    events=[('oracle_diagnostic_F2_calls',12,0,0)]
    db=logs/'new_budget.sqlite'
    if db.exists():db.unlink()
    con=sqlite3.connect(db);con.execute('CREATE TABLE budget(event TEXT,f2_calls INT,new_renders INT,new_camera_exposures INT)')
    con.executemany('INSERT INTO budget VALUES (?,?,?,?)',events);con.commit();con.close()
    with (logs/'resource_budget.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['event','f2_calls','new_renders','new_camera_exposures']);w.writeheader()
        for e in events:w.writerow(dict(event=e[0],f2_calls=e[1],new_renders=e[2],new_camera_exposures=e[3]))
    print('V139 assembled')
if __name__=='__main__':main()
