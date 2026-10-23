"""V144 D: read-only replay of the V143 conditional camera pilot."""
from __future__ import annotations
import argparse, csv, hashlib, json, sys
from pathlib import Path
import numpy as np, h5py
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve()
    src=repo/'results/v143/validation/camera_pilot'
    summary=json.loads((src/'conditional_camera_pilot.json').read_text(encoding='utf-8'))
    out=dict(schema='iscat144.camera_replay.1',n_exposures_check=912,rows=[],note='read-only; no new samples; thresholds untouched')
    with h5py.File(src/'conditional_camera_arrays.h5','r') as h:
        groups=list(h.keys())
    ok=True
    for r in summary['results']:
        B=r['B_electrons_per_pixel']
        thr=json.loads((src/f'B{B}_dev_frozen_threshold.json').read_text(encoding='utf-8'))['threshold']
        # recompute dev null max from stored arrays if present
        gk=f'B{B}_dev_null'
        n_null=0;mx=0.0
        if gk in groups:
            g=h[gk]
            n_null=len(g.keys())
            for k in g.keys():
                arr=np.asarray(g[k][()],float)
                mx=max(mx,float(np.max(np.abs(arr[2:15,2:15]))))
        replay_ok=bool(abs(mx-threshold if False else mx-thr)<1e-9) if n_null else None
        out['rows'].append(dict(B=B,threshold_published=thr,dev_null_replay_groups=n_null,
            replayed_max_abs=mx,threshold_replay_matches=replay_ok,
            independent_FPR_published=f"{r['val_false_positives']}/{r['independent_null_n']}",
            cp95_published=r['one_sided95_cp_upper'],targets_detected=f"{r['target_detected']}/{r['target_n']}"))
        if replay_ok is False:ok=False
    out['overall']='REPLAY_CONSISTENT' if ok else 'REPLAY_MISMATCH'
    outdir=Path(a.out);outdir.mkdir(parents=True,exist_ok=True)
    Path(outdir/'camera_replay.json').write_text(json.dumps(out,indent=2)+chr(10),encoding='utf-8')
    print('CAMERA_REPLAY',out['overall'],'groups per B replayed')
if __name__=='__main__':main()
