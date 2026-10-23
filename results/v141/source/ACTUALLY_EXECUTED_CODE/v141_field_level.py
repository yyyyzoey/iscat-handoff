#!/usr/bin/env python3
"""Real original MAT/HDF5 complex-field diagnostic for V141.

No new BEM, no new renderer, no camera sampling. Reuses published original
solve/render arrays. Uses M truth/offset registry only on the validator side;
NEVER feeds truth to any parameter estimator. Does NOT grant science PASS.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,sys
from pathlib import Path
import numpy as np
import h5py
sys.path.insert(0,str(Path(__file__).resolve().parent))
from v141_common import (sha_file,sha_array,assert_frozen_git_blobs,matlab_field_canonical,
                         canonical_axes,raw_camera_canonical,camera_query,sample_bilinear,
                         sample_cubic,pixel_intensities,error_metrics)


def load_render(path):
    with h5py.File(path,'r') as hf:
        g=hf['r'];rm=hf['rmeta']
        raw=np.asarray(g['contrast'][()],float)
        it=np.asarray(g['Itotal'][()],float);bg=np.asarray(g['Iref'][()],float)
        if raw.shape!=it.shape or raw.shape!=bg.shape or not (bg>0).all():
            raise ValueError('RAW_CAMERA_SHAPE_OR_BACKGROUND_INVALID')
        if float(np.max(np.abs(raw-(it-bg)/bg)))>1e-12:
            raise ValueError('RAW_CONTRAST_NOT_MATCH_OWN_INTENSITIES')
        Er=matlab_field_canonical(g['Eref']);Es=matlab_field_canonical(g['Esca'])
        fx,fy=canonical_axes(g['fine_x_nm'][()],g['fine_y_nm'][()])
        if Er.shape!=(len(fx),len(fy),3) or Es.shape!=Er.shape:
            raise ValueError('RAW_FIELD_AND_AXES_MISMATCH')
        meta={k:float(rm[k][()]) for k in ('dx','dy','q','focus_z')}
        return {'Er':Er,'Es':Es,'fx':fx,'fy':fy,'C':raw_camera_canonical(raw),
                'I':raw_camera_canonical(it),'Iref':raw_camera_canonical(bg),'meta':meta}


def get_map(repo,cfg):
    with open(repo/cfg['inputs']['lineage_csv'],encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    mp={}
    for r in rows:
        key=r['case'],r['variant']
        if key in mp:raise ValueError('DUPLICATE_LINEAGE_ROW:'+str(key))
        mp[key]=r
    cases=[m['case'] for m in cfg['M_opened_development_cases']]
    if set(mp)!={(c,v) for c in cases for v in ('default','wide','at_offset')}:
        raise ValueError('MISSING_OR_EXTRA_CASE_LINEAGE')
    return mp


def validate_solve_provenance(repo,mp,cfg,case):
    rows=[mp[case,v] for v in ('default','wide','at_offset')]
    sha={r['solve_sha256'] for r in rows}
    if len(sha)!=1:raise ValueError('SOLVE_IDENTITIES_DISAGREE:'+case)
    sp=repo/'results/v126/bem_cache'/rows[0]['solve_filename']
    if not sp.is_file() or sha_file(sp)!=rows[0]['solve_sha256']:
        raise ValueError('SOURCE_SOLVE_SHA_NOT_VERIFIED:'+case)
    meta_expected=next(x for x in cfg['M_opened_development_cases'] if x['case']==case)
    with h5py.File(sp,'r') as f:
        m=f['meta']
        D=float(m['D_nm'][()]);h=float(m['h_nm'][()]);gap=float(m['gap_nm'][()])
        if abs(D-meta_expected['D_nm'])>1e-9 or abs(h-meta_expected['h_nm'])>1e-9 or abs(gap-(h-D/2))>1e-9:
            raise ValueError('SOURCE_SOLVE_CASE_MISMATCH:'+case)
        for k,target in [('mesh',1444),('np_re',1.38),('np_im',0.0),('lambda_nm',520.0),('NA',0.8),('nwater',1.3353),('nglass',1.5)]:
            if abs(float(m[k][()])-target)>1e-9:raise ValueError('SOLVE_PHYSICS_DIFF:'+case+':'+k)
    return {'source_solve_path':str(sp),'sha256':rows[0]['solve_sha256'],
            'source_linkage':'PIPELINE_CACHE_KEY_LEDGER_LINKED_NOT_EMBEDDED_SOLVE_CONTENT_SHA'}


def evaluate_case(repo,out,cfg,mp,case,variant):
    conf=next(m for m in cfg['M_opened_development_cases'] if m['case']==case)
    prev=mp[case,variant];wide=mp[case,'wide']
    dpath=repo/'results/v126/renders'/prev['render_filename']
    wpath=repo/'results/v126/renders'/wide['render_filename']
    if not dpath.is_file() or sha_file(dpath)!=prev['render_sha256']:
        raise ValueError('RAW_DIRECT_SHA_MISMATCH:'+case+':'+variant)
    if not wpath.is_file() or sha_file(wpath)!=wide['render_sha256']:
        raise ValueError('RAW_WIDE_SHA_MISMATCH:'+case)
    direct=load_render(dpath);w=load_render(wpath)
    dx=float(conf['dx_nm']) if variant=='at_offset' else 0.0
    dy=float(conf['dy_nm']) if variant=='at_offset' else 0.0
    if abs(direct['meta']['dx']-dx)>1e-9 or abs(direct['meta']['dy']-dy)>1e-9:
        raise ValueError('DIRECT_OFFSET_META_MISMATCH:'+case)
    if abs(w['meta']['dx'])>1e-9 or abs(w['meta']['dy'])>1e-9:
        raise ValueError('WIDE_NOT_CENTERED:'+case)
    q=cfg['conditional_assumptions']['subsamples_per_pixel']
    cam=cfg['conditional_assumptions']['camera_n']
    pitch=cfg['conditional_assumptions']['camera_pixel_object_nm']
    Q=camera_query(cam,q,pitch)
    if direct['Er'].shape!=(len(Q),len(Q),3):raise ValueError('INVALID_DIRECT_FINE_SHAPE')
    # At offset MATLAB samples efield(x-dx,y-dy) but still labels the camera
    # field by the FIXED unshifted physical camera grid. Check that identity.
    if np.max(np.abs(Q-direct['fx']))>1e-8 or np.max(np.abs(Q-direct['fy']))>1e-8:
        raise ValueError('DIRECT_FINE_CAMERA_AXES_DIFFER_FROM_FROZEN_QUERY')
    exact=pixel_intensities(direct['Er'],direct['Es'],q)
    direct_identity=error_metrics(exact['C'],direct['C'])
    if direct_identity['max_abs']>1e-10:
        raise ValueError('DIRECT_Eref_Esca_TO_C_IDENTITY_FAILED:'+case+':'+variant)
    wide_er=sample_bilinear(w['Er'],w['fx'],w['fy'],Q,Q)
    er_err=error_metrics(wide_er,direct['Er'])
    rows=[];products={
        'Er_direct':direct['Er'],'Esca_direct':direct['Es'],
        'Er_from_wide':wide_er,'C_direct':direct['C'],
        'Icross_direct':exact['Icross'],'Isca_direct':exact['Isca']}
    for kernel,sampler in [('S1_BILINEAR',sample_bilinear),('S2_CUBIC',sample_cubic)]:
        es=sampler(w['Es'],w['fx'],w['fy'],Q-dx,Q-dy)
        eerr=error_metrics(es,direct['Es'])
        mixed=pixel_intensities(direct['Er'],es,q)
        full=pixel_intensities(wide_er,es,q)
        mixerr=error_metrics(mixed['C'],direct['C'])
        fullerr=error_metrics(full['C'],direct['C'])
        cross=error_metrics(mixed['Icross'],exact['Icross'])
        isc=error_metrics(mixed['Isca'],exact['Isca'])
        data=dict(case=case,variant=variant,kernel=kernel,dx=dx,dy=dy,
            raw_sha256=prev['render_sha256'],wide_sha256=wide['render_sha256'],
            source_solve_sha256=prev['solve_sha256'],
            direct_field_replay_C_max_abs=direct_identity['max_abs'],
            Er_field_abs_L2=er_err['abs_L2'],Er_field_rel_L2=er_err['relative_L2'],
            Esca_field_abs_L2=eerr['abs_L2'],Esca_field_rel_L2=eerr['relative_L2'],
            directEr_interpEs_C_abs_L2=mixerr['abs_L2'],
            directEr_interpEs_C_rel_L2=mixerr['relative_L2'],
            wideEr_interpEs_C_abs_L2=fullerr['abs_L2'],
            wideEr_interpEs_C_rel_L2=fullerr['relative_L2'],
            C_max_abs_error=fullerr['max_abs'],
            Icross_abs_L2=cross['abs_L2'],Icross_rel_L2=cross['relative_L2'],
            Isca_abs_L2=isc['abs_L2'],Isca_rel_L2=isc['relative_L2'],
            qualified_spatial_1pct=fullerr['relative_L2'] is not None and fullerr['relative_L2']<=.01,
            source_role='VALIDATOR_SIDE_OPENED_DEVELOPMENT_NOT_NEW_BLIND')
        rows.append(data)
        products[f'{kernel}_Esca']=es
        products[f'{kernel}_C_mixed']=mixed['C']
        products[f'{kernel}_C_full']=full['C']
        products[f'{kernel}_Icross']=mixed['Icross']
        products[f'{kernel}_Isca']=mixed['Isca']
    out.mkdir(parents=True,exist_ok=True)
    fname=f'{case}_{variant}'
    npz=out/(fname+'.npz')
    np.savez_compressed(npz,**products)
    manifest={'case':case,'variant':variant,'source_solve':prev['solve_filename'],
        'source_solve_sha256':prev['solve_sha256'],'render_direct_sha256':prev['render_sha256'],
        'render_wide_sha256':wide['render_sha256'],'output_npz_sha256':sha_file(npz),
        'arrays':{k:sha_array(v) for k,v in products.items()},'rows':rows,
        'approval':'NUMERICAL_DEVELOPMENT_DIAGNOSTIC_ONLY_NOT_ABSOLUTE_EXPERIMENTAL_SIZING'}
    (out/(fname+'.json')).write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return rows


def run(repo,out,cfg):
    repo=Path(repo).resolve();out=Path(out).resolve()
    if sha_file(repo/cfg['inputs']['v133_library'])!=cfg['expected_sha256']['library_h5']:
        raise ValueError('LIBRARY_SHA_CHANGED')
    if sha_file(repo/cfg['inputs']['v140_camera_h5'])!=cfg['expected_sha256']['merged_M_h5']:
        raise ValueError('CAMERA_H5_SHA_CHANGED')
    frozen=assert_frozen_git_blobs(repo,cfg['frozen_source_git_blobs_full_sha1'])
    mp=get_map(repo,cfg)
    (out/'validation'/'field_cases').mkdir(parents=True,exist_ok=True)
    solved={};errors=[]
    for case in [r['case'] for r in cfg['M_opened_development_cases']]:
        try:
            solved[case]=validate_solve_provenance(repo,mp,cfg,case)
        except Exception as exc:
            errors.append({'case':case,'variant':'all', 'type':type(exc).__name__,
                           'reason':'SOURCE_LINEAGE_BLOCKED: '+str(exc)})
    rows=[]
    for case in solved:
        for variant in ('default','at_offset'):
            try:
                rr=evaluate_case(repo,out/'validation'/'field_cases',cfg,mp,case,variant)
                rows.extend(rr)
            except Exception as exc:
                errors.append({'case':case,'variant':variant,'type':type(exc).__name__,'reason':str(exc)})
    val=out/'validation';val.mkdir(parents=True,exist_ok=True)
    cols=list(rows[0]) if rows else ['case','variant','kernel','reason']
    with (val/'field_level_error_separation.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
    with (val/'zero_shift_regression.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows([r for r in rows if r.get('variant')=='default'])
    with (val/'interference_component_comparison.csv').open('w',newline='',encoding='utf-8') as f:
        fields=['case','variant','kernel','Icross_abs_L2','Icross_rel_L2','Isca_abs_L2','Isca_rel_L2']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows([{k:r[k] for k in fields} for r in rows])
    summary={'schema':'iscat141.field-level.1','frozen_source_verified':frozen,
        'source_solve_checks':solved,'n_rows':len(rows),'n_expected_rows':24,
        'errors':errors,
        'per_kernel_offset':{k:{'n':sum(r['variant']=='at_offset' and r['kernel']==k for r in rows),
                 'n_below_1pct':sum(r['variant']=='at_offset' and r['kernel']==k and r['qualified_spatial_1pct'] for r in rows)}
            for k in ('S1_BILINEAR','S2_CUBIC')},
        'science_verdict':'DIAGNOSTIC_ONLY_REQUIRES_INDEPENDENT_GATE_AND_SIZING_CHECKS'}
    (val/'field_level_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    return summary


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--config',required=True)
    a=ap.parse_args();out=Path(a.out)
    try:
        cfg=json.loads(Path(a.config).read_text(encoding='utf-8'))
        r=run(a.repo,out,cfg)
        print(json.dumps({'n_rows':r['n_rows'],'errors':len(r['errors']),
            'per_kernel_offset':r['per_kernel_offset']},ensure_ascii=False))
        return 0 if not r['errors'] and r['n_rows']==24 else 3
    except Exception as exc:
        out.mkdir(parents=True,exist_ok=True)
        (out/'v141_field_component_error.json').write_text(json.dumps(
            dict(status='BLOCKED_NO_SCIENCE_PASS',type=type(exc).__name__,reason=str(exc)),indent=2)+'\n',encoding='utf-8')
        print('FIELD_LEVEL_BLOCKED',repr(exc),file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())
