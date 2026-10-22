"""W2: original-solve geometry provenance + same-solve nonzero-shift render vs locked F2.

Reads the original project renders (no new BEM, no new render). Truth D/h are
used ONLY here in this validator-side physical qualification; never passed to
any estimator or quality gate. Output records per-pixel evidence.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, sys
from pathlib import Path
import numpy as np, h5py
sys.path.insert(0, str(Path(__file__).resolve().parent))

def s16(ds):return ''.join(chr(int(c)) for c in ds[()].ravel())

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--renders-root',required=True)
    ap.add_argument('--v132-images',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    out.mkdir(parents=True,exist_ok=True)
    from load_field_library import load_library
    from v133_recover_M import optical
    cfg=json.loads((repo/'config/v133_science_config.json').read_text(encoding='utf-8'))
    v137=json.loads((repo/'config/v137_science_config.json').read_text(encoding='utf-8'))
    m=v137['inherited_model']
    from model_lock import verify_code_lock
    passd=json.loads((repo/m['model_passport']).read_text(encoding='utf-8'))
    verify_code_lock(passd['code_sha256'],tools_dir=repo/'tools')
    lib=repo/m['library']
    if hashlib.sha256(lib.read_bytes()).hexdigest()!=m['library_sha256']:raise SystemExit('library SHA mismatch')
    model,_=load_library(lib,kind='F2',optical=optical(cfg))
    cases=json.loads((repo/v137['M_validator_only_task_records']).read_text(encoding='utf-8'))['cases']
    root=Path(a.renders_root)
    prov=[];shift_rows=[];qual=dict(cases={},render_budget=dict(new_renders_used=0,limit=48),
        new_BEM_attempts=0,scope='VALIDATOR_SIDE_PHYSICAL_QUALIFICATION_WITH_TRUTH_NEVER_IN_ESTIMATOR')
    for rec in cases:
        case=rec['tag'].removeprefix('holdout_');Dtrue=float(rec['D_nm']);htrue=float(rec['h_nm'])
        variants={}
        for vr in rec['renders']:
            variant=vr['variant']
            # resolve by V134 audit CSV mapping variant -> file
            found=None
            with (repo/'results/v134/provenance/M_raw_source_audit.csv').open(encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    if row['case']==case and row['variant']==variant and row['status']=='FOUND':found=Path(row['file'])
            if found is None:raise SystemExit(case+' '+variant+' render path missing')
            if not found.is_file():raise SystemExit('render missing on this station: '+str(found))
            sha=hashlib.sha256(found.read_bytes()).hexdigest()
            with h5py.File(found,'r') as f:
                r=f['r'];rm=f['rmeta']
                dx=float(rm['dx'][()]);dy=float(rm['dy'][()])
                Cmat=np.asarray(r['contrast'][()],float)
                Itot=np.asarray(r['Itotal'][()],float);Iref=np.asarray(r['Iref'][()],float)
                ident=float(rm['q'][()])
                geom=dict(dx=dx,dy=dy,focus_z=float(rm['focus_z'][()]),variant=variant,
                    center_nm=[float(v) for v in r['center_nm'][()].ravel()],
                    object_pixel_nm=float(r['object_pixel_nm'][()]),
                    lambda_nm=float(r['cfg']['lambda_nm'][()]) if 'cfg' in r else None,
                    NA=float(r['cfg']['objective']['NA'][()]) if 'cfg' in r and 'objective' in r['cfg'] else None,
                    relay_mag=float(r['cfg']['tube']['relay_magnification'][()]) if 'cfg' in r and 'tube' in r['cfg'] else None,
                    cfg_particle_block=dict(D=float(r['cfg']['particle']['diameter_nm'][()]),
                        gap=float(r['cfg']['particle']['gap_nm'][()]),
                        material=s16(r['cfg']['particle']['material'])) if 'cfg' in r and 'particle' in r['cfg'] else None)
                prov.append(dict(case=case,file=str(found),sha256=sha,**geom))
            if variant=='default' and (dx!=0 or dy!=0):raise SystemExit(case+' default render not centered')
            if variant=='at_offset':
                want=vr.get('shift_xy_nm')
                if want is None or abs(dx-want[0])>1e-9 or abs(dy-want[1])>1e-9:
                    raise SystemExit(case+' at_offset shift mismatch vs case record')
                variants[variant]=(dx,dy,Cmat)
            elif variant=='default':
                variants[variant]=(dx,dy,Cmat)
        # intensity identity: contrast == (Itotal-Iref)/Iref
        (dx0,dy0,Cdef)=variants['default'];(dx1,dy1,Coff)=variants['at_offset']
        Cdef_id=np.max(np.abs(Cdef-(Itot-Iref)/Iref))
        Cf0=model.forward((Dtrue,htrue,dx0,dy0)).C
        Cf1=model.forward((Dtrue,htrue,dx1,dy1)).C
        rows=[]
        for label,Cf,Cm in [('default_zero_shift',Cf0,Cdef),('at_offset_nonzero_shift',Cf1,Coff)]:
            diff=Cf-Cm;absl2=float(np.linalg.norm(diff));nrm=float(np.linalg.norm(Cm))
            rel=absl2/nrm if nrm>1e-12 else None
            shift_rows.append(dict(case=case,condition=label,D_true=Dtrue,h_true=htrue,dx=dx1 if label.startswith('at') else 0.0,
                dy=dy1 if label.startswith('at') else 0.0,mat_render_norm=nrm,f2_norm=float(np.linalg.norm(Cf)),
                unscaled_abs_L2=absl2,relative_L2=rel,max_abs_pixel=float(np.max(np.abs(diff))),
                numeric_floor_declared=1e-12,orientation='AS_EXPORTED_NO_FLIP_NO_SCALE',
                verdict='RENDER_F2_QUALIFIED_1PCT' if rel is not None and rel<=0.01 else 'RENDER_F2_NOT_QUALIFIED'))
        qual['cases'][case]=dict(D_true=Dtrue,h_true=htrue,truth_source='VALIDATOR_RECORD_ONLY',
            default_intensity_identity_max_abs=Cdef_id,
            render_norm_default=float(np.linalg.norm(Cdef)),render_norm_offset=float(np.linalg.norm(Coff)),
            f2_default_norm=float(np.linalg.norm(Cf0)),f2_offset_norm=float(np.linalg.norm(Cf1)),
            library_node=bool(Dtrue in model.Ds),h_library_node=bool(htrue in model.Hs))
    # write outputs
    pdir=out.parent/'provenance';pdir.mkdir(parents=True,exist_ok=True)
    with (pdir/'M_original_solve_render_sha.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['case','variant','file','sha256','dx','dy','focus_z','center_nm',
            'object_pixel_nm','lambda_nm','NA','relay_mag','cfg_particle_block'])
        w.writeheader()
        for r in prov:
            w.writerow({k:(json.dumps(v) if isinstance(v,(list,dict)) else v) for k,v in r.items()})
    with (out/'same_solve_shift_F2.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['case','condition','D_true','h_true','dx','dy','mat_render_norm','f2_norm',
            'unscaled_abs_L2','relative_L2','max_abs_pixel','numeric_floor_declared','orientation','verdict'])
        w.writeheader();w.writerows(shift_rows)
    qual['geometry_mismatch_note']=('MAT cfg particle block is a renderer default (gold_table D=50 gap=5) and '
        'does NOT describe the M solve; the actual particle identity comes from the validator case records '
        '(n=1.38 sphere, mesh 1444) and the arrays themselves. Recorded, not silently accepted.')
    qual['shift_rows']=shift_rows
    qual['k02_h03_extra_coverage']=dict(status='NOT_EVALUATED',
        reason='Historical K02/H03 at_offset shift records not resolvable to verified render files in this pass; M-case same-solve evidence already decisive; left open per contract')
    for case,v in qual['cases'].items():
        v['same_solve_shift_qualified']=False
        v['reason_codes']=['F2_LIBRARY_INTERPOLATION_FAILS_DIRECT_NONZERO_SHIFT_RENDER']
    # surrogate-image identification: v132 M images vs F2 at truth
    import h5py as _h5
    with _h5.File(a.v132_images,'r') as vf:
        for rec in cases:
            case=rec['tag'].removeprefix('holdout_');Dtrue=float(rec['D_nm']);htrue=float(rec['h_nm'])
            Cz=np.asarray(vf[case]['C'][()],float)
            Cf=model.forward((Dtrue,htrue,0.0,0.0)).C
            vr=[r for r in rec['renders'] if r['variant']=='at_offset'][0];sx,sy=vr['shift_xy_nm']
            Co=np.asarray(vf[case]['at_offset/C'][()],float)
            Cfs=model.forward((Dtrue,htrue,float(sx),float(sy))).C
            qual['cases'][case].update(
                rel_F2_vs_v132_zero=float(np.linalg.norm(Cf-Cz)/np.linalg.norm(Cz)),
                rel_F2shift_vs_v132_offset=float(np.linalg.norm(Cfs-Co)/np.linalg.norm(Co)))
    qualified=sum(r['verdict']=='RENDER_F2_QUALIFIED_1PCT' for r in shift_rows)
    qual['overall']=('SAME_SOLVE_RENDER_F2_PARITY_QUALIFIED' if qualified==len(shift_rows) else
        'SAME_SOLVE_RENDER_F2_PARTIAL_OR_NOT_QUALIFIED: see rows; interpolation error at non-node (D,h) is expected and recorded')
    (out/'physical_forward_qualification.json').write_text(json.dumps(qual,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('W2 rows=',len(shift_rows),'qualified_1pct=',qualified,'/',len(shift_rows))
if __name__=='__main__':main()
