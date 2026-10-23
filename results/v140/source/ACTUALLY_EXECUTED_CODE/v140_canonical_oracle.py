"""V140 canonical wide-field oracle: source-defined importer, NOT fit-selected axes.

The V139 legacy oracle reads HDF5 compound fields as transpose(1,2,0),
while the project's source import path uses transpose(2,1,0), followed by
first-axis flip and x-axis relabeling. This program tests the *frozen source*
conversion on existing M renders, with no BEM solve or new camera exposures.

This is a validator-side physics/coordinate audit (reads M case registry);
never use true D/h/xy from here to initialize a formal particle estimator.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,os,sys
from pathlib import Path,PureWindowsPath
import numpy as np
import h5py

HERE=Path(__file__).resolve().parent

def sha_file(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()

def git_blob_sha(path):
    raw=Path(path).read_bytes()
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()

def verify_frozen_source(repo,config):
    checks={}
    for rel,expected in config['fixed_source_blobs'].items():
        p=Path(repo)/rel
        if not p.is_file():raise FileNotFoundError('Frozen source missing: '+rel)
        got=git_blob_sha(p)
        if got!=expected:
            # transparent handling of a config typo (41-char hash): accept exact 40-char prefix,
            # recorded as CONFIG_TYPO_PREFIX_MATCH in the audit, never silently.
            if len(expected)==41 and got==expected[:40]:
                checks[rel]={'git_blob':got,'sha256':sha_file(p),'note':'CONFIG_TYPO_41CHAR_PREFIX_MATCH'}
                continue
            raise ValueError('Frozen source Git blob mismatch: '+rel+' '+got)
        checks[rel]={'git_blob':got,'sha256':sha_file(p)}
    return checks

def matlab_h5_compound_to_canonical(ds,n):
    """Match tools/v125_model_library.py::_cplx then _camx_flip, exactly.

    MATLAB field is stored in HDF5 [component,column,row] order. The 2,1,0
    transpose restores MATLAB [row,column,component], and the first-axis flip
    is the historical *pre-frozen camera-x normalization*. No per-case choice.
    """
    a=ds[()]
    if a.dtype.names is not None:
        if not {'real','imag'}.issubset(a.dtype.names):raise ValueError('Unsupported H5 compound complex representation')
        b=np.asarray(a['real'],float)+1j*np.asarray(a['imag'],float)
    elif np.iscomplexobj(a):b=np.asarray(a,dtype=np.complex128)
    else:raise ValueError('Complex 3-vector Eref/Esca required')
    if b.shape!=(3,n,n):raise ValueError(f'MATLAB H5 field requires [3,{n},{n}], got {b.shape}')
    converted=np.transpose(b,(2,1,0))[::-1,:,:].copy()
    if not np.isfinite(converted).all():raise ValueError('Nonfinite complex field')
    return converted

def canonical_axes(fine_x,fine_y):
    a=np.asarray(fine_x,float).ravel();b=np.asarray(fine_y,float).ravel()
    if (len(a)!=len(b) or len(a)<2 or not np.all(np.isfinite(a)) or not np.all(np.isfinite(b))
        or not np.all(np.diff(a)>0) or not np.all(np.diff(b)>0)):
        raise ValueError('Invalid native fine-grid axes')
    x=-a[::-1].copy();y=b.copy()
    if not np.all(np.diff(x)>0):raise ValueError('Canonical x is not ascending')
    return x,y

def sample_complex(F,fx,fy,qx,qy):
    """Independent bilinear interpolation; strict support, no out-of-domain clip."""
    F=np.asarray(F,dtype=np.complex128);fx=np.asarray(fx,float);fy=np.asarray(fy,float)
    qx=np.asarray(qx,float);qy=np.asarray(qy,float)
    if (F.shape!=(len(fx),len(fy),3) or fx.ndim!=1 or fy.ndim!=1 or qx.ndim!=1 or qy.ndim!=1
        or not np.isfinite(F).all() or not np.isfinite(fx).all() or not np.isfinite(fy).all()
        or not np.isfinite(qx).all() or not np.isfinite(qy).all()
        or not np.all(np.diff(fx)>0) or not np.all(np.diff(fy)>0)
        or qx.min()<fx[0] or qx.max()>fx[-1] or qy.min()<fy[0] or qy.max()>fy[-1]):
        raise ValueError('OUTSIDE_SOURCE_SUPPORT_OR_INVALID_FIELD')
    ix=np.minimum(np.maximum(np.searchsorted(fx,qx,'right')-1,0),len(fx)-2)
    iy=np.minimum(np.maximum(np.searchsorted(fy,qy,'right')-1,0),len(fy)-2)
    a=((qx-fx[ix])/(fx[ix+1]-fx[ix]))[:,None,None]
    b=((qy-fy[iy])/(fy[iy+1]-fy[iy]))[None,:,None]
    p00=F[ix[:,None],iy[None,:]]
    p10=F[(ix+1)[:,None],iy[None,:]]
    p01=F[ix[:,None],(iy+1)[None,:]]
    p11=F[(ix+1)[:,None],(iy+1)[None,:]]
    return (1-a)*((1-b)*p00+b*p01)+a*((1-b)*p10+b*p11)

def forward_from_canonical_source(er,es,fx,fy,dx,dy,*,n=17,q=5,pixel_nm=280):
    """Reference on fixed camera; sample scattered field at physical (x-dx,y-dy)."""
    centers=(np.arange(n)-(n-1)/2)*pixel_nm
    offsets=((np.arange(q)+.5)/q-.5)*pixel_nm
    query=(centers[:,None]+offsets[None,:]).reshape(-1)
    Er=sample_complex(er,fx,fy,query,query)
    Es=sample_complex(es,fx,fy,query-float(dx),query-float(dy))
    I=np.sum(abs(Er+Es)**2,axis=-1).reshape(n,q,n,q).mean(axis=(1,3))
    I0=np.sum(abs(Er)**2,axis=-1).reshape(n,q,n,q).mean(axis=(1,3))
    if np.any(I0<=0) or not np.isfinite(I).all() or not np.isfinite(I0).all():
        raise ValueError('Nonpositive background or nonfinite intensity')
    return (I-I0)/I0,I,I0

def raw_camera_to_canonical(raw):
    a=np.asarray(raw)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.isfinite(a).all():raise ValueError('Bad raw camera image')
    return a.T[::-1,:].copy()

def load_wide(path):
    with h5py.File(path,'r') as h:
        g=h['r']
        f1=np.asarray(g['fine_x_nm'][()],float).ravel();f2=np.asarray(g['fine_y_nm'][()],float).ravel()
        nx=len(f1);ny=len(f2)
        if nx!=ny:raise ValueError('Expected square wide grid; non-square needs explicit export schema')
        er=matlab_h5_compound_to_canonical(g['Eref'],nx)
        es=matlab_h5_compound_to_canonical(g['Esca'],nx)
        fx,fy=canonical_axes(f1,f2)
    return er,es,fx,fy

def resolve_render(repo,stored):
    p=Path(stored)
    if p.is_file():return p
    n=PureWindowsPath(stored).name
    opts=[Path(repo)/'results/v126/renders'/n,Path(repo)/n]
    for q in opts:
        if q.is_file():return q
    raise FileNotFoundError('Cannot resolve original render: '+stored)

def load_original_C(path):
    with h5py.File(path,'r') as h:
        a=np.asarray(h['r/contrast'][()],float)
        if 'r/Itotal' not in h or 'r/Iref' not in h:raise ValueError('missing own intensity arrays')
        it=np.asarray(h['r/Itotal'][()],float);ref=np.asarray(h['r/Iref'][()],float)
        if a.shape!=it.shape or a.shape!=ref.shape or not np.all(ref>0):raise ValueError('invalid within-render intensities')
        replay=(it-ref)/ref
        if np.max(abs(a-replay))>1e-12:raise ValueError('same-render contrast identity FAILED')
    return raw_camera_to_canonical(a)

def l2(A,B):
    delta=np.asarray(A)-np.asarray(B)
    norm=float(np.linalg.norm(B))
    return {'abs_L2':float(np.linalg.norm(delta)),
            'relative_L2':float(np.linalg.norm(delta)/norm) if norm>1e-12 else None,
            'max_abs':float(np.max(abs(delta))),'reference_norm':norm}

def run(repo,config,out):
    repo=Path(repo).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    frozen=verify_frozen_source(repo,config)
    case_infos={r['case']:r for r in config['M_opened_development_cases']}
    mapping={}
    with (repo/config['original_render_index']).open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            if r.get('case') in case_infos and r.get('variant') in ('default','wide','at_offset'):
                key=(r['case'],r['variant'])
                if key in mapping:raise ValueError('Duplicate render source: '+str(key))
                mapping[key]=resolve_render(repo,r['file'])
    if len(mapping)!=18:raise ValueError('M source mapping incomplete (expected 18 render identities)')
    # Validator-only registry: freeze the intended geometry and physical shift,
    # never select a transform or estimator start from these truth values.
    registry_path=repo/'results/v126/v132_M_cases.json'
    registry=json.loads(registry_path.read_text(encoding='utf-8-sig'))['cases']
    by_case={r['tag'].removeprefix('holdout_'):r for r in registry}
    if set(by_case)!=set(case_infos):raise ValueError('M validator case registry mismatch')
    for case,params in case_infos.items():
        raw=by_case[case]
        if abs(float(raw['D_nm'])-params['D_nm'])>1e-9 or abs(float(raw['h_nm'])-params['h_nm'])>1e-9:
            raise ValueError('M case registry D/h differs: '+case)
        shift=[r['shift_xy_nm'] for r in raw['renders'] if r['variant']=='at_offset']
        if len(shift)!=1 or [float(x) for x in shift[0]]!=[params['dx_nm'],params['dy_nm']]:
            raise ValueError('M case registry shift differs: '+case)
        for variant in ('default','wide','at_offset'):
            wantx=0. if variant!='at_offset' else params['dx_nm']
            wanty=0. if variant!='at_offset' else params['dy_nm']
            with h5py.File(mapping[(case,variant)],'r') as mat:
                rm=mat.get('rmeta')
                if rm is None or not all(k in rm for k in ('dx','dy','q','focus_z')):
                    raise ValueError('missing actual rmeta: '+case+' '+variant)
                actualx=float(rm['dx'][()]);actualy=float(rm['dy'][()])
                if abs(actualx-wantx)>1e-9 or abs(actualy-wanty)>1e-9:
                    raise ValueError('MAT actual offset differs from registry: '+case+' '+variant)
                if int(float(rm['q'][()]))!=config['conditional_assumptions']['q']:
                    raise ValueError('MAT subpixels differ: '+case+' '+variant)
                if abs(float(rm['focus_z'][()])-config['conditional_assumptions']['focus_z_nm'])>1e-9:
                    raise ValueError('MAT focus differs: '+case+' '+variant)
                g=mat['r']
                if 'object_pixel_nm' not in g or abs(float(g['object_pixel_nm'][()])-config['conditional_assumptions']['object_pixel_nm'])>1e-9:
                    raise ValueError('MAT object pixel size differs: '+case+' '+variant)
    merged=repo/config['merged_M_h5'];if_sha=sha_file(merged)
    if if_sha!=config['merged_M_sha256']:raise ValueError('Merged M H5 SHA changed')
    rows=[];case_dir=out/'cases';case_dir.mkdir(exist_ok=True)
    with h5py.File(merged,'r') as mh:
        for case,params in case_infos.items():
            er,es,fx,fy=load_wide(mapping[(case,'wide')])
            for variant in ('default','at_offset'):
                dx=0 if variant=='default' else params['dx_nm']
                dy=0 if variant=='default' else params['dy_nm']
                raw=load_original_C(mapping[(case,variant)])
                if raw.shape!=(17,17):raise ValueError(case+' camera shape mismatch')
                expected=np.asarray(mh[f'{case}/'+('C' if variant=='default' else 'at_offset/C')][()],float)
                if not np.array_equal(raw,expected):raise ValueError(case+' raw/merged mapping mismatch: '+variant)
                pred,I,I0=forward_from_canonical_source(er,es,fx,fy,dx,dy,
                    n=config['conditional_assumptions']['camera_N'],
                    q=config['conditional_assumptions']['q'],
                    pixel_nm=config['conditional_assumptions']['object_pixel_nm'])
                residual=l2(pred,raw)
                p=case_dir/f'{case}_{variant}.npz'
                np.savez_compressed(p,original_direct_raw_canonical=raw,canonical_wide_oracle=pred,
                    oracle_I=I,oracle_Ibg=I0,difference=pred-raw)
                src={'case':case,'variant':variant,'dx':dx,'dy':dy,
                    'default_render_sha256':sha_file(mapping[(case,'default')]),
                    'wide_render_sha256':sha_file(mapping[(case,'wide')]),
                    'direct_render_sha256':sha_file(mapping[(case,variant)]),
                    'merged_sha256':if_sha, 'npz_sha256':sha_file(p),
                    'relative_L2':residual['relative_L2'], 'abs_L2':residual['abs_L2'],
                    'max_abs':residual['max_abs'],
                    'pass_1pct':bool(residual['relative_L2'] is not None and residual['relative_L2']<=.01),
                    'source_role':'SOURCE_DEFINED_CANONICAL_WIDE_ORACLE__NOT_INDEPENDENT_BEM_SOLVE_PROOF'}
                (case_dir/f'{case}_{variant}.json').write_text(json.dumps(src,indent=2,allow_nan=False)+'\n',encoding='utf-8')
                rows.append(src)
    with (out/'canonical_oracle_comparison.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary={'frozen_source':frozen,'n_rows':len(rows),'new_BEM':0,'new_render':0,'new_camera':0,
         'results_by_variant':{v:{'n':sum(r['variant']==v for r in rows),
                 'oracle_pass_1pct':sum(r['pass_1pct'] for r in rows if r['variant']==v)}
               for v in ('default','at_offset')},
         'verdict':'NUMERIC_ORACLE_DIAGNOSTIC_ONLY__RENDER_SOLVE_LINEAGE_AND_INDEPENDENT_PHYSICS_SEPARATE',
         'note':'Primary source-defined canonicalization frozen by V125 importer and MATLAB shift code; not chosen per case by residual.'}
    (out/'canonical_oracle_summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return summary

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True);ap.add_argument('--config',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();cfg=json.loads(Path(a.config).read_text(encoding='utf-8'))
    try:
        result=run(a.repo,cfg,a.out)
    except Exception as exc:
        dest=Path(a.out);dest.mkdir(parents=True,exist_ok=True)
        (dest/'canonical_oracle_error.json').write_text(json.dumps({'status':'BLOCKED_NOT_EVALUATED','error':repr(exc)},indent=2)+'\n')
        print('BLOCKED_NOT_EVALUATED:',repr(exc),file=sys.stderr);return 2
    print(json.dumps(result['results_by_variant'],ensure_ascii=False));return 0
if __name__=='__main__':raise SystemExit(main())
