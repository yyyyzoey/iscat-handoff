"""REAL-DATA V139 source/oracle comparison. Never runs BEM or new render.

Only compares source-native wide complex fields vs source direct render and
locked F2. Does NOT infer free phase/gain, D, x/y, or truth during formal fitting.
All M validator true parameters are read in THIS validation-only tool.

Important: wide->same-solve lineage is NOT certified merely because filename or
(D,h) matches. This script marks missing original cache linkage unqualified.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,sys
from pathlib import Path,PureWindowsPath
import numpy as np,h5py
from v139_common import (load_json,sha_file,finite_array,complex_field,
     canonical_raw_to_merged,intensity_contrast,oracle_same_wide,residual_metrics,central)
from v139_budget import BudgetLedger,DuplicateOperation,BudgetExceeded

CASES=[f'M{i:02d}' for i in range(1,7)]

def txt_scalar(v):
    if isinstance(v,bytes):return v.decode('utf-8','replace')
    if isinstance(v,str):return v
    a=np.asarray(v)
    if a.dtype.kind in 'iu' and a.size>1:return ''.join(chr(int(x)) for x in a.ravel())
    if a.ndim==0:return str(a.item())
    return str(a.tolist())

def resolve_render(repo,original_path,root):
    p=Path(original_path)
    if p.is_file():return p
    name=PureWindowsPath(original_path).name
    for q in [repo/root/name,repo/name]:
        if q.is_file():return q
    raise FileNotFoundError('MISSING_SAME_SOLVE_RAW_RENDER: '+name)

def get_render(path):
    with h5py.File(path,'r') as f:
        if 'r' not in f:raise ValueError('no r group')
        g=f['r']
        if any(k not in g for k in ['contrast','Itotal','Iref']):raise ValueError('missing raw camera arrays')
        C=np.asarray(finite_array(g['contrast'][()]),float)
        it=np.asarray(finite_array(g['Itotal'][()]),float);ir=np.asarray(finite_array(g['Iref'][()]),float)
        if C.shape!=(17,17) and C.shape!=(25,25):raise ValueError('camera array not declared standard/wide shape')
        if C.shape!=it.shape or C.shape!=ir.shape:raise ValueError('raw camera shape mismatch')
        delta=float(np.max(abs(C-intensity_contrast(it,ir))))
        meta={}
        if 'rmeta' in f:
            for n in ('dx','dy','focus_z','q'):
                if n in f['rmeta']:meta[n]=float(np.asarray(f['rmeta'][n][()]).item())
        if 'center_nm' in g:meta['center_nm']=np.asarray(g['center_nm'][()]).ravel().astype(float).tolist()
        if 'x_nm' in g:meta['x_nm']=np.asarray(g['x_nm'][()]).ravel().astype(float).tolist()
        if 'y_nm' in g:meta['y_nm']=np.asarray(g['y_nm'][()]).ravel().astype(float).tolist()
        if 'object_pixel_nm' in g:meta['object_pixel_nm']=float(g['object_pixel_nm'][()])
        # A renderer may or may not contain an explicit reference to the solve.
        hints=[]
        for scope in [f,g,f.get('rmeta',None)]:
            if scope is None:continue
            for n in ('source_solve_sha256','solve_sha256','bem_system_sha256','source_solve_sha'):
                if n in scope.attrs:hints.append((n,txt_scalar(scope.attrs[n])))
                if n in scope and isinstance(scope[n],h5py.Dataset):hints.append((n,txt_scalar(scope[n][()])))
        fields=None
        if all(k in g for k in ('Eref','Esca','fine_x_nm','fine_y_nm')):
            fx=np.asarray(g['fine_x_nm'][()]).ravel().astype(float)
            fy=np.asarray(g['fine_y_nm'][()]).ravel().astype(float)
            er=complex_field(g['Eref'][()],nx=len(fx),ny=len(fy))
            es=complex_field(g['Esca'][()],nx=len(fx),ny=len(fy))
            fields=(er,es,fx,fy)
    return dict(C=C,I=it,Iref=ir,delta=delta,meta=meta,solve_hints=hints,fields=fields)

def map_render_paths(repo,cfg):
    with (repo/cfg['inherited']['v138_original_render_index']).open(encoding='utf-8-sig',newline='') as f:
        entries=list(csv.DictReader(f))
    m={}
    for x in entries:
        if x.get('case') in CASES and x.get('variant') in ('default','wide','at_offset'):
            if (x['case'],x['variant']) in m:raise ValueError('duplicate raw render mapping')
            m[(x['case'],x['variant'])]=resolve_render(repo,x['file'],cfg['source_render_root'])
    if set(m)!={(k,v) for k in CASES for v in ('default','wide','at_offset')}:
        raise ValueError('missing original render variant')
    return m

def expected_solves(repo,cfg):
    m={}
    with (repo/cfg['inherited']['v138_source_geometry']).open(encoding='utf-8-sig',newline='') as f:
        for x in csv.DictReader(f):
            c=x.get('matched_case','')
            if c in CASES:
                if c in m:raise ValueError('duplicate M solve geometry match')
                p=repo/cfg['source_solve_root']/x['solve_file']
                if not p.is_file() or sha_file(p)!=x['solve_sha']:
                    raise ValueError('M solve SHA mismatch: '+c)
                m[c]=dict(path=str(p),sha256=x['solve_sha'],source_record=x)
    if set(m)!=set(CASES):raise ValueError('six M solve metadata records incomplete')
    return m

def do_real(repo,out,cfg,resume=False):
    repo=Path(repo).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    config_hash=sha_file(cfg['_config_path'])
    m=cfg['inherited'];lib=repo/m['library'];h5path=repo/m['merged_M']
    if sha_file(lib)!=m['library_sha256'] or sha_file(h5path)!=m['merged_M_sha256']:
        raise ValueError('PRIMARY_INPUT_SHA_MISMATCH; no F2 inherited work')
    mapping=map_render_paths(repo,cfg);solves=expected_solves(repo,cfg)
    # Honor the actual V133 model lock and numerical dependencies.
    sys.path.insert(0,str(repo/'tools'))
    from load_field_library import load_library
    from v133_recover_M import optical
    from model_lock import verify_code_lock
    v133=load_json(repo/'config/v133_science_config.json')
    passport=load_json(repo/m['v133_model_passport'])
    verify_code_lock(passport['code_sha256'],tools_dir=repo/'tools')
    F2,_=load_library(lib,kind='F2',optical=optical(v133))
    if F2.model_id!=m['F2_model_id']:raise ValueError('model_id changed')
    b=BudgetLedger(out/'logs'/'new_budget.sqlite',limits={
        'F2':cfg['hard_budget_new_v139']['F2_forward_calls_all_stages'],
        'RENDER':cfg['hard_budget_new_v139']['new_render_attempts'],
        'CAMERA':cfg['hard_budget_new_v139']['new_camera_exposure_events'],
        'BEM':cfg['hard_budget_new_v139']['new_BEM_solver_attempts']})
    raws=load_json(repo/'results/v138/provenance/inputs_and_runtime_sha.json')['inputs']
    source_entries=load_json(repo/cfg['true_case_registry_validator_only'])['cases']
    truth={x['tag'].removeprefix('holdout_'):x for x in source_entries}
    if set(truth)!=set(CASES):raise ValueError('M registry changed')
    records=[]
    with h5py.File(h5path,'r') as hh:
        for c in CASES:
            idx={v:get_render(mapping[c,v]) for v in ('default','wide','at_offset')}
            if idx['wide']['fields'] is None:
                raise ValueError('no source-wide complex fields '+c)
            if abs(idx['wide']['meta'].get('dx',float('nan')))>1e-9 or abs(idx['wide']['meta'].get('dy',float('nan')))>1e-9:
                raise ValueError('wide source is not centered: '+c)
            for v in ('default','at_offset'):
                p=mapping[c,v]
                historic=raws.get('raw_render_'+c+'_'+v)
                if historic is None or sha_file(p)!=historic['sha256']:
                    raise ValueError('original render SHA differs from V138: '+c+' '+v)
                obsname='C' if v=='default' else 'at_offset/C'
                direct=canonical_raw_to_merged(idx[v]['C'])
                original_h5=np.asarray(hh[c+'/'+obsname][()],float)
                if not np.array_equal(direct,original_h5):
                    raise ValueError('frozen RAW.T[::-1,:] data link mismatch: '+c+' '+v)
                offsets=[r['shift_xy_nm'] for r in truth[c]['renders'] if r['variant']=='at_offset']
                if len(offsets)!=1:raise ValueError('missing/duplicated original offset record')
                cfg_case=next(z for z in cfg['cases'] if z['case']==c)
                if (float(truth[c]['D_nm'])!=float(cfg_case['D_nm']) or
                    float(truth[c]['h_nm'])!=float(cfg_case['h_nm']) or
                    offsets[0]!=[cfg_case['dx_nm'],cfg_case['dy_nm']]):
                    raise ValueError('user case registry differs from frozen config: '+c)
                dx=0. if v=='default' else float(offsets[0][0])
                dy=0. if v=='default' else float(offsets[0][1])
                if not np.isclose(idx[v]['meta'].get('dx',float('nan')),dx,atol=1e-9) or not np.isclose(idx[v]['meta'].get('dy',float('nan')),dy,atol=1e-9):
                    raise ValueError('render physical offset mismatch: '+c+' '+v)
                if idx[v]['C'].shape!=(cfg['conditional_assumptions']['camera_n'],)*2:
                    raise ValueError('expected 17x17 camera render: '+c+' '+v)
                if 'object_pixel_nm' not in idx[v]['meta'] or abs(idx[v]['meta']['object_pixel_nm']-cfg['conditional_assumptions']['object_pixel_nm'])>1e-9:
                    raise ValueError('raw physical pixel metadata mismatch: '+c+' '+v)
                if 'q' not in idx[v]['meta'] or int(idx[v]['meta']['q'])!=cfg['conditional_assumptions']['q']:
                    raise ValueError('raw quadrature metadata mismatch: '+c+' '+v)
                if abs(idx[v]['delta'])>1e-12:
                    raise ValueError('own-source C intensity replay mismatch: '+c+' '+v)
                path=out/'cases'/f'{c}_{v}.json';npz=out/'cases'/f'{c}_{v}.npz'
                source_key={'library':m['library_sha256'],'merged':m['merged_M_sha256'],'case':c,'variant':v,
                    'rawsha':sha_file(p),'widesha':sha_file(mapping[c,'wide']),
                    'model_id':F2.model_id,'configsha':config_hash}
                signature=__import__('hashlib').sha256(json.dumps(source_key,sort_keys=True).encode()).hexdigest()
                if resume and path.is_file() and npz.is_file():
                    old=load_json(path)
                    if old['input_signature']!=signature:
                        raise ValueError('resume identity mismatch: '+c+' '+v)
                    records.append(old)
                    continue
                if path.exists() or npz.exists():
                    raise ValueError('existing output without fully verified resume: '+c+' '+v)
                w=idx['wide']
                if w['fields'] is None:raise ValueError('missing wide Eref/Esca/fine axes: '+c)
                er,es,fx,fy=w['fields']
                oracle_native,Ioracle,Ibgoracle=oracle_same_wide(er,es,fx,fy,dx=dx,dy=dy,
                     n=cfg['conditional_assumptions']['camera_n'],q=cfg['conditional_assumptions']['q'],
                     pixel_nm=cfg['conditional_assumptions']['object_pixel_nm'])
                oracle_can=canonical_raw_to_merged(oracle_native)
                budget_key='F2_'+signature
                b.reserve(budget_key,'F2',1,'validator true parameters only')
                try:
                    F2_can=F2.forward((float(truth[c]['D_nm']),float(truth[c]['h_nm']),dx,dy)).C
                    b.mark(budget_key,'COMPLETED','F2 forward evaluated and result stored')
                except Exception as e:
                    b.mark(budget_key,'FAILED',repr(e));raise
                oa=residual_metrics(oracle_can,direct);co=residual_metrics(F2_can,oracle_can);ca=residual_metrics(F2_can,direct)
                if not np.allclose((F2_can-direct),(F2_can-oracle_can)+(oracle_can-direct),atol=1e-12,rtol=0):
                    raise ValueError('residual vector decomposition violated')
                source_sha=solves[c]['sha256'].lower()
                all_variants_bound=all(any(str(value).lower().replace('sha256:','')==source_sha
                    for key,value in idx[vv]['solve_hints']) for vv in ('default','wide','at_offset'))
                lineage=('EXPLICIT_ALL_THREE_RENDERS_TO_SOLVE_SHA_PROVEN' if all_variants_bound
                    else 'GEOMETRY_MATCH_ONLY_RENDER_SOLVE_LINK_NOT_PROVEN')
                row={'case':c,'variant':v,'input_signature':signature,'oracle_vs_direct':oa,'F2_vs_oracle':co,'F2_vs_direct':ca,
                     'source_lineage':lineage,'original_solve_sha256':solves[c]['sha256'],
                     'raw_render_sha256':sha_file(p),'wide_render_sha256':sha_file(mapping[c,'wide']),
                     'model_id':F2.model_id,'camera_array_transform':'RAW.T[::-1,:]','dx':dx,'dy':dy,
                     'oracle_vs_direct_1pct':oa['relative_L2'] is not None and oa['relative_L2']<=.01,
                     'F2_vs_oracle_1pct':co['relative_L2'] is not None and co['relative_L2']<=.01,
                     'F2_vs_direct_1pct':ca['relative_L2'] is not None and ca['relative_L2']<=.01,
                     'science_gate':'DIAGNOSTIC_ONLY_UNLESS_RENDER_TO_SOLVE_LINK_AND_AXIS_META_VERIFIED'}
                path.parent.mkdir(parents=True,exist_ok=True)
                np.savez_compressed(npz,source_native_raw=idx[v]['C'],direct_canonical=direct,
                     oracle_camera_native=oracle_native,oracle_canonical=oracle_can,
                     F2_canonical=F2_can,direct_minus_oracle=direct-oracle_can,
                     F2_minus_oracle=F2_can-oracle_can,oracle_intensity=Ioracle,oracle_background=Ibgoracle)
                path.write_text(json.dumps(row,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
                records.append(row)
    # Must never call this scientific PASS: all direct raw scene truth is open development.
    with (out/'oracle_shift_decomposition.csv').open('w',encoding='utf-8',newline='') as f:
        cols=['case','variant','dx','dy','source_lineage','raw_render_sha256','wide_render_sha256','original_solve_sha256',
              'oracle_vs_direct_rel_L2','F2_vs_oracle_rel_L2','F2_vs_direct_rel_L2','oracle_vs_direct_abs_L2','F2_vs_oracle_abs_L2','F2_vs_direct_abs_L2',
              'oracle_vs_direct_1pct','F2_vs_oracle_1pct','F2_vs_direct_1pct','input_signature']
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
        for r in records:
            w.writerow(dict(case=r['case'],variant=r['variant'],dx=r['dx'],dy=r['dy'],
                source_lineage=r['source_lineage'],raw_render_sha256=r['raw_render_sha256'],
                wide_render_sha256=r['wide_render_sha256'],original_solve_sha256=r['original_solve_sha256'],
                oracle_vs_direct_rel_L2=r['oracle_vs_direct']['relative_L2'],F2_vs_oracle_rel_L2=r['F2_vs_oracle']['relative_L2'],F2_vs_direct_rel_L2=r['F2_vs_direct']['relative_L2'],
                oracle_vs_direct_abs_L2=r['oracle_vs_direct']['abs_L2'],F2_vs_oracle_abs_L2=r['F2_vs_oracle']['abs_L2'],F2_vs_direct_abs_L2=r['F2_vs_direct']['abs_L2'],
                oracle_vs_direct_1pct=r['oracle_vs_direct_1pct'],F2_vs_oracle_1pct=r['F2_vs_oracle_1pct'],F2_vs_direct_1pct=r['F2_vs_direct_1pct'],
                input_signature=r['input_signature']))
    summary=dict(task='V139_SOURCE_WIDE_ORACLE_DIAGNOSTIC',n_rows=len(records),
       same_solve_render_proven=sum(r['source_lineage']=='EXPLICIT_ALL_THREE_RENDERS_TO_SOLVE_SHA_PROVEN' for r in records),
       by_variant={v:{'oracle_vs_direct_pass':sum(r['oracle_vs_direct_1pct'] for r in records if r['variant']==v),
                      'F2_vs_oracle_pass':sum(r['F2_vs_oracle_1pct'] for r in records if r['variant']==v),
                      'F2_vs_direct_pass':sum(r['F2_vs_direct_1pct'] for r in records if r['variant']==v)} for v in ('default','at_offset')},
       F2_queries_recorded=b.spent('F2'),
       scientific_verdict='NOT_SCIENTIFICALLY_CERTIFIED_BY_THIS_SCRIPT__SOURCE_LINK_AND_AXIS_PROOF_REQUIRED',
       note='Source native-to-canonical mapping inherited from V138 opened M, not a blind independent axis calibration.')
    (out/'oracle_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return summary

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--out',required=True);p.add_argument('--config',required=True);p.add_argument('--resume',action='store_true');a=p.parse_args()
    cfg=load_json(a.config);cfg['_config_path']=str(Path(a.config).resolve())
    try:
        res=do_real(a.repo,a.out,cfg,a.resume)
        print('ORACLE_DIAGNOSTIC_EXECUTED_NO_BEM',json.dumps(res,ensure_ascii=False))
        return 0
    except Exception as e:
        dest=Path(a.out);dest.mkdir(parents=True,exist_ok=True)
        (dest/'oracle_error.json').write_text(json.dumps(dict(type=type(e).__name__,message=str(e),status='BLOCKED_NOT_SCIENCE_PASS'),indent=2)+'\n')
        print('V139 ORACLE BLOCKED:',type(e).__name__,str(e),file=sys.stderr)
        return 2
if __name__=='__main__':raise SystemExit(main())
