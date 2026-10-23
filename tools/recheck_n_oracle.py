#!/usr/bin/env python3
"""V144 validator-side N field oracle correction. NEVER called by estimator.

V143 field import was canonical (MAT: transpose(2,1,0), flip0). Its 17x17
pixel_intensities output is already canonical. Repeating .T[::-1,:] before
comparison was a second axis transform; this verifier reports both paths.
No BEM, no new MATLAB render, no F2c forward calls, no new camera events.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,sys
from pathlib import Path
import numpy as np,h5py

def file_sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def load_case_render(path, common):
    with h5py.File(path,'r') as hf:
        r=hf['r']
        fields=common.matlab_field_canonical(r['Eref']),common.matlab_field_canonical(r['Esca'])
        fx,fy=common.canonical_axes(r['fine_x_nm'][()],r['fine_y_nm'][()])
        raw=np.asarray(r['contrast'][()],float)
        Itot=np.asarray(r['Itotal'][()],float);Iref=np.asarray(r['Iref'][()],float)
        if raw.shape!=Itot.shape or raw.shape!=Iref.shape or np.any(Iref<=0):raise ValueError('SOURCE_INTENSITIES_INVALID')
        if np.max(abs(raw-(Itot-Iref)/Iref))>1e-12:raise ValueError('SOURCE_OWN_CONTRAST_NOT_REPLAYED')
        meta={k:float(np.asarray(hf['rmeta'][k][()]).ravel()[0]) for k in ('dx','dy','q','focus_z')}
        camera=common.raw_camera_canonical(raw)
    return dict(Er=fields[0],Es=fields[1],fx=fx,fy=fy,C=camera,meta=meta)

def compute_oracles(wide,direct,dx,dy,common,n=17,q=5,pixel_nm=280):
    """The returned C images and direct.C already share CANONICAL camera axes."""
    Q=common.camera_query(n=n,q=q,pixel_nm=pixel_nm)
    er=common.sample_bilinear(wide['Er'],wide['fx'],wide['fy'],Q,Q)
    # The reference is unchanged by particle position. Compare independently.
    if er.shape!=direct['Er'].shape:raise ValueError('CAMERA_FIELD_SHAPE_MISMATCH')
    result=dict(Er_vs_direct=common.error_metrics(er,direct['Er']),
                kernels={},source_integrity=common.error_metrics(
                    common.pixel_intensities(direct['Er'],direct['Es'],q)['C'],direct['C']))
    for kernel,sampler in (('S1_BILINEAR',common.sample_bilinear),('S2_CUBIC',common.sample_cubic)):
        es=sampler(wide['Es'],wide['fx'],wide['fy'],Q-dx,Q-dy)
        cam=common.pixel_intensities(er,es,q)['C']
        # V143 BUG FOR DIAGNOSTIC REPRO ONLY: second transform already-canonical C.
        old_wrong=cam.T[::-1,:]
        result['kernels'][kernel]=dict(correct_C=cam,old_double_transformed_C=old_wrong,
            correct_17=common.error_metrics(cam,direct['C']),
            correct_13=common.error_metrics(cam[2:15,2:15],direct['C'][2:15,2:15]),
            legacy_double_transform_17=common.error_metrics(old_wrong,direct['C']),
            Es_vs_direct=common.error_metrics(es,direct['Es']),
            Icross_vs_direct=common.error_metrics(common.pixel_intensities(er,es,q)['Icross'],
                                                  common.pixel_intensities(direct['Er'],direct['Es'],q)['Icross']))
    return result

def run(repo,cfg,out):
    repo=Path(repo).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(repo/'tools'))
    import v141_common as common
    model_src=repo/'tools/v141_common.py'
    if not model_src.is_file():raise ValueError('SOURCE_IMPORTER_NOT_FOUND')
    sources=cfg['inputs'];linage=json.loads((repo/sources['N_lineage']).read_text(encoding='utf-8'))
    m={r['anon']:r for r in linage['rows']}
    expected={f'ANON_{i:02d}' for i in range(1,5)}
    if set(m)!=expected:raise ValueError('N_SOLVE_LINEAGE_COVERS_WRONG_CASES')
    true_registry={r['case']:r for r in json.loads((repo/sources['N_validator_truth']).read_text(encoding='utf-8'))['cases']}
    expected_h5=cfg['known_sha256']['N_anonymous_observation'];h5path=repo/sources['N_anonymous_observation']
    if file_sha(h5path)!=expected_h5:raise ValueError('ANON_N_HDF5_IDENTITY_CHANGED')
    base=repo/sources['N_original_renders'];rows=[];events=[];casesdir=out/'cases';casesdir.mkdir(parents=True,exist_ok=True)
    with h5py.File(h5path,'r') as h5:
        for anon in sorted(m):
            lr=m[anon];ncase=lr['case'];tr=true_registry[ncase]
            wp=base/f'{anon}_wide.mat';sp=base/f'{anon}_at_offset.mat';dp=base/f'{anon}_default.mat'
            for label,p in (('wide',wp),('at_offset',sp),('default',dp)):
                if file_sha(p)!=lr['renders'][label]['render_sha256']:raise ValueError(f'{anon} ORIGINAL_{label}_SHA_CHANGED')
            wide=load_case_render(wp,common);direct=load_case_render(sp,common)
            centered=load_case_render(dp,common)
            dx,dy=float(tr['x_nm']),float(tr['y_nm'])
            if abs(direct['meta']['dx']-dx)>1e-9 or abs(direct['meta']['dy']-dy)>1e-9:raise ValueError(anon+' OFFSET_METADATA_MISMATCH')
            if wide['meta']['dx']!=0 or wide['meta']['dy']!=0 or centered['meta']['dx']!=0 or centered['meta']['dy']!=0:raise ValueError(anon+' WIDE_NOT_CENTERED')
            if int(direct['meta']['q'])!=cfg['conditional_assumptions']['q']:raise ValueError('Q_MISMATCH')
            if abs(direct['meta']['focus_z']-cfg['conditional_assumptions']['focus_nm'])>1e-9:raise ValueError('FOCUS_MISMATCH')
            expected_obs=np.asarray(h5[anon]['score_C'][()],float)
            if expected_obs.shape!=(13,13) or not np.array_equal(expected_obs,direct['C'][2:15,2:15]):raise ValueError(anon+' ANON_OBSERVATION_MISMATCH')
            for variant,rr,px,py in (('default',centered,0.,0.),('at_offset',direct,dx,dy)):
                metrics=compute_oracles(wide,rr,px,py,common,n=cfg['conditional_assumptions']['camera_n'],q=cfg['conditional_assumptions']['q'],pixel_nm=cfg['conditional_assumptions']['object_pixel_nm'])
                if metrics['source_integrity']['max_abs']>1e-12:raise ValueError('RAW_FIELD_C_IDENTITY_FAIL')
                fn=casesdir/f'{anon}_{variant}.npz'
                np.savez_compressed(fn,C_direct=rr['C'],
                  S1_C_canonical=metrics['kernels']['S1_BILINEAR']['correct_C'],
                  S2_C_canonical=metrics['kernels']['S2_CUBIC']['correct_C'],
                  V143_double_transform_S1=metrics['kernels']['S1_BILINEAR']['old_double_transformed_C'],
                  V143_double_transform_S2=metrics['kernels']['S2_CUBIC']['old_double_transformed_C'])
                for method,k in metrics['kernels'].items():
                    result=dict(anon_case=anon,variant=variant,kernel=method,dx_nm=px,dy_nm=py,
                        correct_relative_L2_17=k['correct_17']['relative_L2'],
                        correct_relative_L2_13=k['correct_13']['relative_L2'],
                        wrong_v143_double_transform_relative_L2_17=k['legacy_double_transform_17']['relative_L2'],
                        scattered_field_relative_L2=k['Es_vs_direct']['relative_L2'],
                        reference_field_relative_L2=metrics['Er_vs_direct']['relative_L2'],
                        observed_sha256=file_sha(sp if variant=='at_offset' else dp),
                        wide_sha256=file_sha(wp),archive_image_sha256=file_sha(fn),
                        qualification_relative_L2_max=cfg['qualification']['sourcewide_rel_L2_gate'],
                        passed_corrected_1pct=bool(k['correct_17']['relative_L2']<=cfg['qualification']['sourcewide_rel_L2_gate']),
                        source_proof_scope='PIPELINE_CACHE_KEY_LEDGER_GEOMETRY_NOT_EMBEDDED_SOLVE_SHA')
                    rows.append(result)
    p=out/'N_corrected_sourcewide.csv'
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary=dict(rows=len(rows),S1_pass=sum(x['passed_corrected_1pct'] for x in rows if x['variant']=='at_offset' and x['kernel']=='S1_BILINEAR'),
                 S2_pass=sum(x['passed_corrected_1pct'] for x in rows if x['variant']=='at_offset' and x['kernel']=='S2_CUBIC'),
                 double_transform_error_isolated=True,independent_Maxwell_validation=False,
                 note='Validator-only, old N opened development; no BEM/render/new camera and no estimator reads truth')
    (out/'N_corrected_sourcewide_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    return summary

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True);ap.add_argument('--config',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    try:
        result=run(a.repo,json.loads(Path(a.config).read_text(encoding='utf-8')),a.out)
        print('V144_N_ORACLE_AUDIT_COMPLETED_NOT_ABSOLUTE_PHYSICS_PASS',json.dumps(result));return 0
    except Exception as exc:
        dst=Path(a.out);dst.mkdir(parents=True,exist_ok=True)
        (dst/'N_oracle_blocked.json').write_text(json.dumps({'status':'BLOCKED','type':type(exc).__name__,'error':str(exc)},indent=2)+'\n')
        print('V144_N_ORACLE_BLOCKED',repr(exc),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
