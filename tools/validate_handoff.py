"""Validate this handoff's bytes/config/count arithmetic, not a simulation result."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args();root=args.root.resolve()
    errors=[];checks=[]
    def add(name, ok, detail=''):
        checks.append({'check':name,'passed':bool(ok),'detail':str(detail)})
        if not ok:errors.append(name)
    try:
        cfg=json.loads((root/'config/v127_science_config.json').read_text(encoding='utf-8'))
        add('task_identity',cfg['task_id']=='V127_CANONICAL_CALIBRATION_ACCEPTANCE_AND_SUSPENDED_PARTICLE_SIZING')
        add('fixed_source',cfg['source_commit']=='b546d80beb0dc4789effac8c192896e5f45876e9')
        add('plan_not_result',cfg['plan_not_executed'] is True and cfg['initial_state']['EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED'] is False)
        u=cfg['user_confirmed']; a=cfg['assumptions']
        pixel=1000*u['camera_pixel_um'][0]/(u['objective_nominal_magnification']*a['relay_magnification'])
        add('pixel_scale',abs(pixel-a['object_pixel_nm'])<1e-12,f'{pixel} nm conditional, not experimentally calibrated')
        add('native_fine_not_confused',cfg['imaging']['native_pixel_nm']==280. and cfg['imaging']['fine_grid_step_nm']==56.)
        add('reuse_nodes',len(cfg['reuse']['train_D_nm'])*len(cfg['reuse']['train_h_nm'])==63)
        known=set(range(30,201,10))|{35,55,85,115,145,185,37,63,93,117,147,177,41,43,67,89,123,151,153,183}
        ks=cfg['new_holdouts_validator_only']
        add('six_unique_new_D',len(ks)==6 and len({x['case'] for x in ks})==6 and all(x['D_nm'] not in known for x in ks))
        add('truth_geometric_domain',all(30<=x['D_nm']<=200 and 350<x['h_nm']<550 and x['h_nm']-x['D_nm']/2>=100 and abs(x['x_nm'])<=500 and abs(x['y_nm'])<=500 and x['mesh_request']==1444 for x in ks))
        n=cfg['noise'];m=cfg['motion']; b=cfg['budgets']
        backgrounds=len(n['background_e_at_100us']); refs=n['reference_frames']
        dev=len(n['dev_D_nm'])*len(n['dev_h_nm'])*backgrounds*n['dev_target_reps_per_B']*(1+refs)
        db=backgrounds*n['dev_blank_per_B']*(1+refs)
        vb=backgrounds*n['validation_blank_per_B']*(1+refs)
        ho=len(ks)*backgrounds*n['holdout_reps_per_B']*(1+refs)
        mo=len(m['D_nm'])*m['tracks_per_D']*len(m['exposures_us'])*(m['frames_per_track']+m['reference_per_track_per_exposure'])
        total=dev+db+vb+ho+mo
        add('exposure_count',total==5838==b['nominal_exposure_events'] and total<=b['synthetic_exposure_events'],f'{dev}+{db}+{vb}+{ho}+{mo}={total}')
        add('bem_count',b['qualification_max']+b['augmentation_max']+b['blind_L1']==16==b['new_bem_attempts'])
        add('heavy_process_cap',b['heavy_concurrent']==1)
        rows=list(csv.DictReader((root/'HANDOFF_SHA256.csv').open(encoding='utf-8',newline='')))
        names=[r['path'] for r in rows]
        add('manifest_unique',len(names)==len(set(names)))
        for r in rows:
            p=PurePosixPath(r['path'])
            safe=not p.is_absolute() and '..' not in p.parts and '\\' not in r['path']
            add('safe:'+r['path'],safe)
            if not safe:continue
            fp=root/Path(*p.parts)
            add('present:'+r['path'],fp.is_file() and not fp.is_symlink())
            if fp.is_file():
                data=fp.read_bytes()
                add('sha:'+r['path'],hashlib.sha256(data).hexdigest()==r['sha256'] and len(data)==int(r['bytes']))
        actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='HANDOFF_SHA256.csv'}
        add('manifest_complete',set(names)==actual,f'missing={actual-set(names)},extra={set(names)-actual}')
    except Exception as exc:
        add('exception',False,f'{type(exc).__name__}: {exc}')
    verdict='PASS' if not errors else 'FAIL'
    print(json.dumps({'kind':'HANDOFF_VALIDATION_ONLY','verdict':verdict,'checks':checks,'errors':errors},ensure_ascii=False,indent=2,allow_nan=False))
    return 0 if verdict=='PASS' else 1

if __name__=='__main__':sys.exit(main())
