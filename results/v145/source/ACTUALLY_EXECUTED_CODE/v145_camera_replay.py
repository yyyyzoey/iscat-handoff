#!/usr/bin/env python3
"""Strict READ ONLY V143 912-event replay; does not generate new camera trials.

V144's prior replay checked nonexistent top-level names 'B1000_dev_null',
then vacuously returned REPLAY_CONSISTENT with 0 dev groups. Actual structure:
/B1000/dev_null/dev_000/{foreground_counts,reference_counts,C}.
"""
from __future__ import annotations
import argparse,hashlib,json,math
from pathlib import Path
import h5py,numpy as np
from scipy.stats import beta

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def cp_upper(k,n,conf=.95):
    if not(0<=k<=n and n>0):raise ValueError('INVALID_BINOMIAL_COUNTS')
    return 1. if k==n else float(beta.ppf(conf,k+1,n-k))

def check_item(grp):
    for r in ('foreground_counts','reference_counts','C'):
        if r not in grp:raise ValueError('CAMERA_ARRAY_MISSING:'+grp.name+'/'+r)
    f=np.asarray(grp['foreground_counts'][()],float)
    b=np.asarray(grp['reference_counts'][()],float)
    c=np.asarray(grp['C'][()],float)
    if f.shape!=(17,17) or b.shape!=f.shape or c.shape!=f.shape or not np.isfinite(f).all() or not np.isfinite(b).all() or not np.isfinite(c).all() or not np.all(b>0):
        raise ValueError('CAMERA_ARRAY_INVALID:'+grp.name)
    reconstructed=(f-b)/b
    err=float(np.max(np.abs(c-reconstructed)))
    if err>1e-12:raise ValueError('CAMERA_CONTRAST_REPLAY_FAILED:'+grp.name)
    stat=float(np.max(np.abs(c[2:15,2:15])))
    if 'T' not in grp.attrs or abs(float(grp.attrs['T'])-stat)>1e-12:raise ValueError('CAMERA_STAT_REPLAY_FAILED:'+grp.name)
    return stat

def replay(camera_h5,threshold_root,levels=(1000,10000,100000),ndev=80,nval=60,ntarget=12):
    root=Path(threshold_root);result=[]
    with h5py.File(camera_h5,'r') as h:
        for B in levels:
            stages={}
            for stage,required in [('dev_null',ndev),('val_null',nval),('target',ntarget)]:
                path=f'B{B}/{stage}'
                if path not in h:raise ValueError('CAMERA_STAGE_MISSING:'+path)
                groups=h[path]
                names=sorted(groups.keys())
                if len(names)!=required:raise ValueError(f'CAMERA_STAGE_COUNT_{path}: {len(names)} != {required}')
                stages[stage]=[check_item(groups[key]) for key in names]
            threshold=max(stages['dev_null'])
            frozen=json.loads((root/f'B{B}_dev_frozen_threshold.json').read_text(encoding='utf-8'))
            if frozen.get('B')!=B or frozen.get('n_dev')!=ndev or abs(float(frozen['threshold'])-threshold)>1e-12:
                raise ValueError('CAMERA_DEV_THRESHOLD_MISMATCH:'+str(B))
            k=sum(x>threshold for x in stages['val_null']);detections=sum(x>threshold for x in stages['target'])
            result.append(dict(B_electrons_per_pixel=B,threshold=threshold,dev_nulls=len(stages['dev_null']),
                independent_val_nulls=len(stages['val_null']),false_positives=k,
                one_sided95_cp_upper=cp_upper(k,nval),target_n=ntarget,target_detected=detections,
                FPR_qualified=cp_upper(k,nval)<=.05,
                independent_detection_and_sizing_separate=True))
    observed_exposures=len(result)*2*(ndev+nval+ntarget)
    return dict(schema='iscat145.camera_replay.1',source_h5_sha256=digest(camera_h5),
        rows=result,source_pair_exposures=observed_exposures,
        historical_912_replayed=(observed_exposures==912),
        no_new_random_draws=True,no_new_camera_exposures=True,
        real_camera_fullwell_verified=False,real_absolute_diameter_validated=False)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True);ap.add_argument('--config',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    cfg=json.loads(Path(a.config).read_text(encoding='utf-8'))
    src=Path(a.repo)/cfg['camera_pilot_h5'];thresholds=Path(a.repo)/cfg['camera_pilot_root']
    dest=Path(a.out);dest.parent.mkdir(parents=True,exist_ok=True)
    try:
        levels=cfg['camera']['B_assumed_electrons_per_pixel']
        report=replay(src,thresholds,levels,ndev=cfg['camera']['dev_null_each'],nval=cfg['camera']['val_null_each'],ntarget=cfg['camera']['targets_each_B'])
    except Exception as e:
        dest.write_text(json.dumps({'status':'BLOCKED_NOT_EVALUATED','error':repr(e)},indent=2)+'\n')
        print('CAMERA_REPLAY_BLOCKED',repr(e));return 2
    dest.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    print('V143_CAMERA_ARRAY_REPLAY_COMPLETE',[(r['B_electrons_per_pixel'],r['false_positives'],r['target_detected']) for r in report['rows']]);return 0
if __name__=='__main__':raise SystemExit(main())
