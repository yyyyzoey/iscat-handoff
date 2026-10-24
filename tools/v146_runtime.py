"""Bindings to the already-qualified F2c. Never launches external physics."""
from __future__ import annotations
import sys, importlib, csv
from pathlib import Path
import numpy as np
from v146_core import file_sha,read_json,array_sha,check_theta


def construct_bound(repo,cfg):
    repo=Path(repo).resolve()
    for rel,expected in cfg['frozen']['source_sha256'].items():
        if file_sha(repo/rel)!=expected:raise ValueError('FROZEN_SOURCE_CHANGED:'+rel)
    library=repo/cfg['inputs']['training_library']
    if file_sha(library)!=cfg['frozen']['library_sha256']:raise ValueError('LIBRARY_CHANGED')
    sys.path.insert(0,str(repo/'tools'))
    module=importlib.import_module('v142_model')
    if Path(module.__file__).resolve()!=(repo/'tools/v142_model.py').resolve():raise ValueError('WRONG_IMPORTED_MODEL')
    _,model,_=module.construct(repo,library_relative=cfg['inputs']['training_library'],
        expected_library_sha256=cfg['frozen']['library_sha256'],expected_old_model_id=cfg['frozen']['parent_model_id'])
    if model.model_id!=cfg['frozen']['model_id']:raise ValueError('MODEL_ID_CHANGED')
    return model


def load_clean(repo,cfg,case):
    import h5py
    repo=Path(repo)
    if case in cfg['N_cases']:
        if file_sha(repo/cfg['inputs']['N_observations'])!=cfg['frozen']['N_observation_sha256']:raise ValueError('N_OBSERVATION_FILE_CHANGED')
        with h5py.File(repo/cfg['inputs']['N_observations'],'r') as h:y=np.asarray(h[case]['score_C'][()],float)
        with (repo/cfg['inputs']['N_candidates']).open(encoding='utf-8',newline='') as f:
            rows={r['anon_case']:r for r in csv.DictReader(f)}
        r=rows[case];theta=[float(r[k]) for k in ('candidate_D','fit_h','fit_x','fit_y')]
        if r['source_model_id']!=cfg['frozen']['model_id']:raise ValueError('CLEAN_CANDIDATE_MODEL_CHANGED')
    elif case in cfg['M_cases']:
        if file_sha(repo/cfg['inputs']['M_observations'])!=cfg['frozen']['M_observation_sha256']:raise ValueError('M_OBSERVATION_FILE_CHANGED')
        with h5py.File(repo/cfg['inputs']['M_observations'],'r') as h:y=np.asarray(h[case]['at_offset/C'][()],float)[2:15,2:15]
        r=read_json(repo/cfg['inputs']['M_candidates']/(case+'.json'));theta=r['best']['theta']
        if r['new_F2c_model_id']!=cfg['frozen']['model_id']:raise ValueError('CLEAN_CANDIDATE_MODEL_CHANGED')
    else:raise ValueError('CASE_NOT_ALLOWED')
    if y.shape!=(13,13) or not np.isfinite(y).all():raise ValueError('BAD_CLEAN_OBSERVATION')
    check_theta(theta)
    return y,list(map(float,theta)),array_sha(y)
