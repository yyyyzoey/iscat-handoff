#!/usr/bin/env python3
"""Strict read-only N MAT/HDF5 source audit; no estimator import and NO BEM solve.

The same MATLAB-to-canonical map used by published V138 is tested as a claim,
not selected from a sweep of flips. Missing solver metadata remains NOT PROVEN.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import h5py
from _shared import load_json,sha,save_json


def replay_camera(raw,Itotal,Iref):
    if any(x.ndim!=2 or x.shape!=raw.shape for x in (raw,Itotal,Iref)):
        raise ValueError('RAW_INTENSITIES_SHAPE_NOT_MATCHED')
    if not all(np.isfinite(x).all() for x in (raw,Itotal,Iref)) or not np.all(Iref>0):
        raise ValueError('BAD_REAL_CAMERA_INTENSITIES')
    return float(np.max(np.abs(raw-(Itotal-Iref)/Iref)))


def canonical(raw):
    if raw.ndim!=2 or raw.shape[0]!=raw.shape[1]:raise ValueError('SOURCE_CAMERA_NOT_SQUARE')
    return np.ascontiguousarray(raw.T[::-1,:])


def audit(repo,cfg,solve_root=None):
    repo=Path(repo);sources=cfg['source_files'];result={'schema':'iscat143.N.source_audit.1',
        'same_camera_operator_identity':'V138 FROZEN RAW.T[::-1,:]; no flip selected by fit',
        'cases':{},'all_origins_proven':False,'external_solve_root_provided':bool(solve_root),
        'not_a_new_solve':True,'separation':'VALIDATOR_ONLY_NO_ESTIMATOR_ACCESS'}
    h5path=repo/sources['N_anonymous_obs'];rawfolder=repo/sources['N_original_mats']
    if not h5path.is_file():raise FileNotFoundError(h5path)
    if not rawfolder.is_dir():raise FileNotFoundError(rawfolder)
    noms=cfg['N_opened_scored_cases'];result['anonymous_h5_sha256']=sha(h5path)
    with h5py.File(h5path,'r') as obs:
        if sorted(obs.keys())!=sorted(noms):raise ValueError('N_ANONYMOUS_CASE_MISMATCH')
        for case in noms:
            rows=[];score=np.asarray(obs[case]['score_C'][()],dtype=float)
            if score.shape!=(13,13) or not np.isfinite(score).all():raise ValueError('INVALID_N_SCORE_ROI:'+case)
            for v in ('default','wide','at_offset'):
                p=rawfolder/(case+'_'+v+'.mat');rec={'variant':v,'path':p.relative_to(repo).as_posix(),
                    'file_exists':p.is_file(),'source_mat_sha256':None,'source_camera_valid':False,
                    'score_matches_anonymous_observation':None,'source_provenance':None}
                if not p.is_file():
                    rec['reason']='RAW_RENDER_ABSENT';rows.append(rec);continue
                rec['source_mat_sha256']=sha(p)
                try:
                    with h5py.File(p,'r') as f:
                        if 'r' not in f or any('r/'+k not in f for k in ('contrast','Itotal','Iref')):
                            raise ValueError('MAT_RENDER_CORE_ARRAYS_MISSING')
                        raw=np.asarray(f['r/contrast'][()],dtype=float)
                        I=np.asarray(f['r/Itotal'][()],dtype=float)
                        B=np.asarray(f['r/Iref'][()],dtype=float)
                        mismatch=replay_camera(raw,I,B)
                        rec['native_camera_shape']=list(raw.shape)
                        rec['max_abs_contrast_from_own_I_Iref']=mismatch
                        rec['source_camera_valid']=bool(mismatch<=1e-12)
                        if raw.shape==(17,17) and v=='at_offset':
                            s=canonical(raw)[2:15,2:15]
                            d=s-score
                            rec['score_matches_anonymous_observation']=bool(np.array_equal(s,score))
                            rec['score_max_abs_difference']=float(np.max(np.abs(d)))
                            rec['score_L2_difference']=float(np.linalg.norm(d))
                        if 'rmeta' in f:
                            rm=f['rmeta']
                            for k in ('dx','dy','q','focus_z'):
                                if k in rm:rec['rmeta_'+k]=float(np.asarray(rm[k][()]).ravel()[0])
                        if 'r/center_nm' in f:
                            rec['render_center_nm']=[float(q) for q in np.asarray(f['r/center_nm'][()]).ravel()]
                except Exception as e:rec['error']=type(e).__name__+': '+str(e)
                rows.append(rec)
            result['cases'][case]={'variants':rows,'anon_observation_sha256':sha_array_safe(score)}
    result['raw_camera_and_offset_obs_qualified']=all(
        all(r.get('source_camera_valid') is True for r in entry['variants']) and
        next(r for r in entry['variants'] if r['variant']=='at_offset').get('score_matches_anonymous_observation') is True
        for entry in result['cases'].values())
    solvers=[]
    dirs=[repo/'results/v142/bem_cache',repo/'results/v142/validation/new_N_solve_mats']
    if solve_root is not None:dirs.insert(0,Path(solve_root))
    for d in dirs:
        if d.is_dir():
            for p in sorted(d.glob('*.mat')):
                if 'sol_' not in p.name and 'solve' not in p.name.lower():continue
                rec={'file':str(p),'sha256':sha(p),'meta_readable':False}
                try:
                    with h5py.File(p,'r') as f:
                        if 'meta' in f:
                            rec['D_nm']=float(f['meta/D_nm'][()]);rec['h_nm']=float(f['meta/h_nm'][()]);
                            rec['mesh']=int(f['meta/mesh'][()]);rec['meta_readable']=True
                except Exception as e:rec['error']=str(e)
                solvers.append(rec)
    result['available_original_N_solver_candidates']=solvers
    result['solve_to_render_linkage']='NOT_PROVEN_BY_THIS_TOOL__MUST_VERIFY_RENDER_CACHE_KEY_LEDGER_AND_SOLVE_CONTENT_HASH'
    result['all_origins_proven']=False
    result['scientific_disposition']='PARTIAL_PROVENANCE_ONLY; use candidates for conditional analysis, not independent Maxwell pass'
    return result


def sha_array_safe(a):
    import hashlib
    b=np.ascontiguousarray(a)
    return hashlib.sha256((str(b.shape)+'|'+str(b.dtype)+'|').encode()+b.tobytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--config',default=None)
    p.add_argument('--out',required=True);p.add_argument('--solve-root',default=None);a=p.parse_args()
    cfg=load_json(a.config or Path(__file__).resolve().parents[1]/'config/v143_science_config.json')
    try:x=audit(a.repo,cfg,a.solve_root)
    except Exception as e:x={'status':'BLOCKED','error':type(e).__name__+': '+str(e)}
    dest=Path(a.out);dest=dest if dest.suffix=='.json' else dest/'N_source_audit.json';save_json(dest,x)
    print('N_SOURCE_AUDIT_WRITTEN__SOURCE_PROOF_SEPARATE_FROM_IMAGE_IDENTITY',dest)
    return 2 if 'status' in x else 0
if __name__=='__main__':raise SystemExit(main())
