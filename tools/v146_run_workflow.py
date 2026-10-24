#!/usr/bin/env python3
"""Run the provided stages in order, retaining logs and continuing independent work.
Only explicit Python entry points from this handoff are launched. NO MATLAB/BEM.
This is not an automatic scientific acceptance/production-report generator.
"""
from __future__ import annotations
import argparse,subprocess,sys,time
from pathlib import Path
from v146_core import read_json,save_json,file_sha


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--config',required=True);a=p.parse_args()
    repo=Path(a.repo).resolve();cfgp=Path(a.config).resolve();cfg=read_json(cfgp)
    root=repo/'results/v146';logs=root/'logs';logs.mkdir(parents=True,exist_ok=True)
    here=Path(__file__).resolve().parent
    run_id=time.strftime('%Y%m%d_%H%M%S')+'_'+str(__import__('os').getpid())
    records=[];start=time.monotonic();work_limit=(cfg['max_wall_hours_including_finalize']*60-cfg['finalize_minutes'])*60
    common=['--repo',str(repo),'--config',str(cfgp)]
    tasks=[('intake','v146_audit_v145.py',common+['--out',str(root/'preflight/v145_audit.json')]),
           ('calibration','v146_calibration_and_margins.py',common+['--out',str(root/'calibration')]),
           ('camera_fits','v146_fit_saved_camera.py',common+['--out',str(root/'camera_fits')])]
    for stage,name,args in tasks:
        remaining=work_limit-(time.monotonic()-start)
        if remaining<=0:records.append({'stage':stage,'status':'NOT_RUN_WALL_LIMIT'});continue
        cmd=[sys.executable,str(here/name),*args]
        log=logs/f'{run_id}_{stage}.txt'
        try:
            with log.open('x',encoding='utf-8') as out:
                r=subprocess.run(cmd,stdout=out,stderr=subprocess.STDOUT,timeout=remaining,check=False)
            records.append({'stage':stage,'command':cmd,'returncode':r.returncode,
                'status':'COMPONENT_COMPLETE' if r.returncode in (0,3) else 'BLOCKED',
                'log':str(log.relative_to(root)),'log_sha256':file_sha(log)})
        except subprocess.TimeoutExpired:
            records.append({'stage':stage,'status':'TIMED_OUT_RECONCILE_RESERVATIONS','log':str(log.relative_to(root))})
    # Validator uses a separate process, only AFTER camera outputs are saved.
    successful_camera=any(r.get('stage')=='camera_fits' and r.get('status')=='COMPONENT_COMPLETE' for r in records)
    if successful_camera:
        cmd=[sys.executable,str(here/'v146_score_camera_external.py'),
             '--summary',str(root/'camera_fits/summary.json'),
             '--truth',str(repo/'config/v142_new_N_validator_only.json'),
             '--lineage',str(repo/'results/v143/provenance/N_solve_lineage.json'),
             '--out',str(root/'validator_only/camera_scores.json')]
        remaining=work_limit-(time.monotonic()-start)
        if remaining>0:
            log=logs/f'{run_id}_external_score.txt'
            try:
                with log.open('x',encoding='utf-8') as out:
                    r=subprocess.run(cmd,stdout=out,stderr=subprocess.STDOUT,timeout=remaining,check=False)
                records.append({'stage':'external_score','returncode':r.returncode,'command':cmd,
                    'status':'COMPONENT_COMPLETE' if r.returncode==0 else 'BLOCKED','log_sha256':file_sha(log)})
            except subprocess.TimeoutExpired:records.append({'stage':'external_score','status':'TIMED_OUT'})
        else:records.append({'stage':'external_score','status':'NOT_RUN_WALL_LIMIT'})
    else:records.append({'stage':'external_score','status':'BLOCKED_NO_NEW_CAMERA_FITS'})
    save_json(logs/f'{run_id}_workflow.json',{'records':records,'new_physics_authorized':False,
        'full_science_qualification':False,'remaining_contract_work':[
            'source-qualified developer error comparison','whitened Jacobian interpretation',
            'real input interface schema/demo','actual-code/arrays packaging and independent receipt'],
        'instruction':'CONTINUE_ALL_FEASIBLE_REMAINING_CONTRACT_STAGES; DO_NOT_DECLARE_PHYSICS_PASS'})
    print('PROVIDED_COMPONENTS_FINISHED__CONTINUE_CONTRACT_W2_W4_W5_W6')
    return 3
if __name__=='__main__':raise SystemExit(main())
