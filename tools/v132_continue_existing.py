"""Continue opened-data diagnostics and selected profiles, NOT all-stage completion.
This CLI deliberately returns 3 after an offline-only success: the authorized
full task still includes direct-source/render qualification, M when admitted,
camera/motion, experiment interface, and complete archive.
"""
from __future__ import annotations
import argparse,csv,json,sys,time
from pathlib import Path
import h5py,numpy as np
from load_field_library import load_library
from truth_and_score import truth_from_sources,score_rows,summarize,write_csv,sha256
from diagnose_existing import run as run_diagnostics,optical,signed_image
from complete_profile import targeted_profile,safe_dump
from profile_triage import triage


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('repo','config','out'):ap.add_argument('--'+n,required=True)
    ap.add_argument('--diagnostics',action='store_true');ap.add_argument('--oracle',action='store_true')
    ap.add_argument('--profiles',nargs='*',default=[]);ap.add_argument('--resume',action='store_true')
    a=ap.parse_args(argv);repo=Path(a.repo).resolve();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
    cfg=json.loads(Path(a.config).read_text(encoding='utf-8'));old=repo/cfg['inheritance']['v131_out']
    status={'task':cfg['task_id'],'component':'OPENED_DATA_CONTINUATION','full_task_complete':False,'stages':{},'errors':[]}
    t0=time.monotonic()
    try:
        truth,tsrc=truth_from_sources(repo,cfg['truth_sources']);cand=list(csv.DictReader((old/'old_per_particle_candidates.csv').open(encoding='utf-8-sig')))
        scored=score_rows(cand,truth);write_csv(out/'corrected_scores.csv',scored);safe_dump(out/'corrected_summary.json',summarize(scored));safe_dump(out/'truth_source_identity.json',tsrc)
        audit={p.stem:triage(json.loads(p.read_text(encoding='utf-8-sig'))) for p in sorted((old/'profiles').glob('*.json'))}
        safe_dump(out/'old_profile_triage.json',audit);status['stages']['record_scoring']='COMPLETED_NOT_PHYSICS_ACCEPTANCE'
        if a.diagnostics:
            ok=run_diagnostics(repo,cfg,out/'diagnostics',oracle=a.oracle)
            status['stages']['opened_direct_diagnostics']='COMPLETED' if ok else 'PARTIAL'
        if a.profiles:
            lib=repo/cfg['inputs']['train']
            if sha256(lib)!=cfg['inheritance']['expected_library_sha256']:raise ValueError('Library bytes do not match V131 run')
            model,report=load_library(lib,kind='F2',optical=optical(cfg))
            if model.model_id!=cfg['inheritance']['expected_model_id']:raise ValueError('Canonical F2 changed; cannot inherit profiles')
            safe_dump(out/'library_array_checks.json',report)
            envelope_path=out/'diagnostics'/'development_envelope.json';epsilon=None
            if envelope_path.exists():
                env=json.loads(envelope_path.read_text())
                if env['model_id']!=model.model_id:raise ValueError('Empirical envelope belongs to another model')
                epsilon=float(env['epsilon_L2'])
            for key in a.profiles:
                try:
                    ds,case=key.split('_',1);hp=repo/cfg['offline_batch']['sets'][ds]
                    oid=json.loads((old/'observation_identity'/f'{ds}.json').read_text(encoding='utf-8-sig'))
                    if sha256(hp)!=oid['sha256']:raise ValueError('Observation file changed; no silent resume')
                    fit=json.loads((old/'fits'/f'{key}.json').read_text(encoding='utf-8-sig'))
                    oldp=old/'profiles'/f'{key}.json';legacy=json.loads(oldp.read_text(encoding='utf-8-sig')) if oldp.exists() else None
                    with h5py.File(hp,'r') as hf:Y=signed_image(hf[case],model,cfg['inputs']['observation_dataset'])
                    p=out/'profiles'/f'{key}.json'
                    if p.exists() and not a.resume:raise ValueError('Existing output requires --resume or a new run directory')
                    resumed=json.loads(p.read_text()) if p.exists() else None
                    pc=cfg['profiles_v132']
                    result=targeted_profile(model,Y,fit,old=legacy,epsilon=epsilon,
                             total_calls=pc['total_calls_per_case'],per_point_calls=pc['per_point_calls'],per_start_calls=pc['per_start_calls'],max_nfev=pc['max_nfev'],screening_step=pc['screening_step_nm'],refinement_step=pc['refinement_step_nm'],checkpoint=p,resume=resumed)
                    status['stages'][key]='PROFILE_COMPUTED_REQUIRES_JOINT_RECONCILIATION_AND_QUALITY' if result['coarse_and_scheduled_search_complete'] else 'PARTIAL_PROFILE'
                except Exception as exc:
                    status['errors'].append({'case':key,'error':f'{type(exc).__name__}: {exc}'})
        status['required_next']=['WORKSTATION_PHYSICAL_SOURCE_AND_DIRECT_RENDER_QUALIFICATION','RECONCILE_PROFILE_WITH_JOINT_AND_FREEZE_EMPIRICAL_QUALITY','REGISTERED_M_IF_METHOD_QUALIFIED','CAMERA_BLANKS_EXPOSURE_SHARED_D','EXPERIMENT_INTERFACE_AND_FINAL_ARCHIVE']
        status['execution']='PARTIAL_COMPONENT' if status['errors'] else 'OFFLINE_COMPONENT_COMPLETED_NOT_ENTIRE_TASK'
    except Exception as exc:
        status['execution']='BLOCKED_COMPONENT';status['errors'].append({'error':f'{type(exc).__name__}: {exc}'})
    status['elapsed_seconds']=time.monotonic()-t0;safe_dump(out/'component_status.json',status)
    print(json.dumps(status,ensure_ascii=False,indent=2))
    return 2 if status['errors'] else 3
if __name__=='__main__':raise SystemExit(main())
