"""First-pass, checkpointed F2 nuisance-profile computation on existing real fields.

This is a RUNNABLE INITIAL PROFILE COMPONENT, not a complete scientific
qualification or the full V137 workstation orchestrator. It NEVER reads M truth.
It preserves the exact V133 joint witness at its original continuous D, tries
multiple h basins and both D scan directions, records real optimizer exits,
and explicitly marks adaptive coverage and scientific acceptance UNFINISHED.

Usage: python tools/profile_resume_f2.py --repo PATH --config ../config/v137_science_config.json --out PATH --resume
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, sys, time, traceback
from pathlib import Path
import numpy as np
import h5py

CASE_IDS=tuple(f'M{i:02d}' for i in range(1,7))

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def write_json(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_name(p.name+'.tmp')
    tmp.write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    os.replace(tmp,p)


class ForwardCallMeter:
    """Counts every canonical query in this offline component, including sentinels.

    A full V137 run-all must additionally reserve these calls in the shared
    atomic work ledger. This meter cannot coordinate OTHER processes.
    """
    def __init__(self,core,limit):
        self.core=core;self.limit=int(limit);self.calls=0
    def __getattr__(self,k):return getattr(self.core,k)
    def forward(self,theta):
        if self.calls>=self.limit:
            raise RuntimeError('COMPONENT_CANONICAL_GLOBAL_BUDGET_EXCEEDED')
        self.calls+=1
        return self.core.forward(theta)

def seeds_at_D(D,joint,bank_seeds,axial,forward=None,reverse=None):
    """Public-data seeds + previous valid fit; true D/h/xy never supplied."""
    seeds=[('JOINT_NUISANCE',[D,*joint[1:]])]
    for h in axial:seeds.append(('AXIAL_'+str(h),[D,float(h),joint[2],joint[3]]))
    for q in bank_seeds[:4]:seeds.append(('PUBLIC_BANK',[D,*list(q[1:])]))
    for label,q in [('FORWARD',forward),('REVERSE',reverse)]:
        if q is not None:seeds.append((label,[D,*list(q[1:])]))
    out=[];used=set()
    for tag,q in seeds:
        v=tuple(round(float(x),8) for x in q)
        if v not in used:out.append((tag,list(map(float,q))));used.add(v)
    return out

def replay_gate(model,Y,fit,expected_model,expected_binding):
    from observation_adapter import array_sha
    if fit.get('model_id')!=expected_model or fit['observation_binding']['score_array_sha256']!=expected_binding:
        raise ValueError('F2 fit/model/observation mismatch')
    actual=array_sha(Y)
    if actual!=expected_binding:raise ValueError('Observed pixel values changed')
    p=np.asarray(fit['theta'],float)
    if p.shape!=(4,) or not np.all(np.isfinite(p)):raise ValueError('Invalid stored joint theta')
    loss=float(np.linalg.norm(model.forward(p).score_C-Y))
    old=float(fit['loss'])
    if abs(loss-old)>max(1e-12,1e-7*abs(old)):
        raise ValueError('Known valid V133 candidate fails same-model replay')
    return loss

def read_bank(repo,model,cfg):
    p=repo/cfg['inherited_model']['prior_public_bank']
    with h5py.File(p,'r') as f:
        if str(f.attrs['model_id'])!=model.model_id or str(f.attrs['bank_id'])!=cfg['inherited_model']['prior_bank_id']:
            raise ValueError('Public bank/model identity mismatch')
        theta=np.asarray(f['theta'][()],float);images=np.asarray(f['score_C'][()],float)
    if theta.ndim!=2 or theta.shape[1]!=4 or images.shape!=(len(theta),13,13) or not np.isfinite(images).all():
        raise ValueError('Invalid stored bank arrays')
    # Validate a few fixed bank indices against actual locked forward before using.
    for j in np.unique(np.linspace(0,len(theta)-1,7,dtype=int)):
        if np.max(np.abs(model.forward(theta[j]).score_C-images[j]))>1e-12:
            raise ValueError('Stored public bank does not match canonical F2')
    identity=json.dumps(dict(model_id=model.model_id,theta=theta.tolist()),sort_keys=True).encode()
    calc=hashlib.sha256(identity+images.tobytes()).hexdigest()
    if calc!=cfg['inherited_model']['prior_bank_id']:
        raise ValueError('Public bank SHA of content does not match expected bank ID')
    return theta,images

def fixed_D_point(model,Y,D,joint,axial,bank_seeds,obj,budget,history,prior=None):
    """Attempts at fixed D. Exceptions never alter objective, keep valid witnesses."""
    from fit_reference import solve_start,BudgetStop
    attempts=[];seen=set();failure=False
    seed_list=seeds_at_D(D,joint,bank_seeds,axial,forward=history.get('ascending'),reverse=history.get('descending'))
    if prior is not None:seed_list.append(('OLD_SAME_D_WITNESS',list(map(float,prior))))
    for label,theta in seed_list:
        key=tuple(round(float(v),8) for v in theta)
        if key in seen:continue
        seen.add(key)
        if obj.calls>=obj.limit or time.monotonic()>budget['deadline']:
            failure=True;attempts.append(dict(seed=label,theta_start=theta,status='OUT_OF_TIME_OR_BUDGET',success=False,budget_exhausted=True));break
        start_call=obj.calls
        try:
            r=obj.evaluate(theta)
            loss0=float(np.linalg.norm(r)*obj.scale)
            rec=solve_start(obj,theta,[1,2,3],per_start_calls=budget['per_start_calls'],max_nfev=budget['max_nfev'])
            rec=dict(rec)
            rec.update(seed=label,theta_start=theta,witness_L2=loss0,witness_canonical_calls=1)
            if rec.get('success') is not True or rec.get('budget_exhausted') is True:
                failure=True
            attempts.append(rec)
        except BudgetStop as exc:
            failure=True;attempts.append(dict(seed=label,theta_start=theta,status='BUDGET_STOP',success=False,
                    canonical_calls=obj.calls-start_call,budget_exhausted=True,error=str(exc)))
        except Exception as exc:
            failure=True;attempts.append(dict(seed=label,theta_start=theta,status='EXCEPTION',success=False,
                    canonical_calls=obj.calls-start_call,budget_exhausted=False,error=type(exc).__name__+': '+str(exc)))
    best=obj.best_by_D.get(float(D))
    return dict(D=float(D),theta=best['theta'] if best else None,loss_L2=best['loss'] if best else None,
            point_search_complete=bool(attempts and not failure and len(attempts)==len(seen)),
            attempts=attempts,optimizer_starts_used=len(attempts),source='NEW_F137_FIXED_D_F2_NUMERIC_DIAGNOSTIC')

def run(repo,cfg_path,out,case_ids,max_wall_minutes,resume):
    root=Path(repo).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    cfg=json.loads(Path(cfg_path).read_text(encoding='utf-8'))
    mcfg=cfg['inherited_model'];pg=cfg['F2_profile']
    case_ids=case_ids or cfg.get('M_processing_order',list(CASE_IDS))
    if len(case_ids)!=len(set(case_ids)):raise ValueError('Duplicate requested case')
    tools=root/'tools';sys.path.insert(0,str(tools))
    from load_field_library import load_library
    from v133_recover_M import optical
    from observation_adapter import array_sha
    from fit_reference import Objective
    from model_lock import verify_code_lock
    passfile=root/mcfg['model_passport'];passdata=json.loads(passfile.read_text(encoding='utf-8'))
    expected_code=passdata['code_sha256'];actual_code=verify_code_lock(expected_code,tools_dir=tools)
    lib=root/mcfg['library']
    if sha(lib)!=mcfg['library_sha256']:raise ValueError('H5 library SHA differs; do not reuse V133 fit')
    # use original V133 optical config; copy only when its bytes have not changed
    v133cfg=json.loads((root/'config/v133_science_config.json').read_text(encoding='utf-8'))
    model,_=load_library(lib,kind='F2',optical=optical(v133cfg))
    if model.model_id!=mcfg['model_id']:raise ValueError('Bound original F2 model identity mismatch')
    meter=ForwardCallMeter(model,cfg['budget_new_work_hard_limits']['canonical_F2_calls_all_stages'])
    model=meter
    fits=root/mcfg['prior_fits'];obs=root/mcfg['prior_observations']
    bindings={x['case']:x for x in json.loads((root/mcfg['prior_observation_binding']).read_text(encoding='utf-8'))}
    obsfile_sha=sha(obs)
    source_id=dict(model_id=model.model_id,library_sha256=sha(lib),prior_observations_sha256=obsfile_sha,
          locked_code_sha256=actual_code,runner_sha256=sha(__file__),config_sha256=sha(cfg_path),
          score_shape=[13,13],loss_type='UNSCALED_L2_ON_CENTRAL13_SIGNED_STATIC_C')
    run_id=hashlib.sha256(json.dumps(source_id,sort_keys=True).encode()).hexdigest()
    cfgout=out/'source_binding.json'
    if cfgout.exists():
        if not resume:raise ValueError('Output exists; use --resume or a new directory')
        old=json.loads(cfgout.read_text(encoding='utf-8'))
        if old['run_id']!=run_id:raise ValueError('Resume source identity mismatch; do not mix losses')
    write_json(cfgout,dict(run_id=run_id,source=source_id,scope='STARTER_GRID_PROFILE_COMPONENT_NOT_PHYSCIAL_QUALIFICATION'))
    bt,bimgs=read_bank(root,model,cfg)
    t0=time.monotonic();deadline=t0+60*max_wall_minutes
    logs=[]
    with h5py.File(obs,'r') as hf:
        for case in case_ids:
            case_meter_start=meter.calls
            if case not in CASE_IDS:raise ValueError('Non-M case not authorized')
            Y=np.asarray(hf[case]['score_C'][()],float)
            if Y.shape!=(13,13) or not np.isfinite(Y).all():raise ValueError('Bad M signed-score image')
            binding=bindings[case]['score_array_sha256']
            if array_sha(Y)!=binding:raise ValueError(case+': score array has changed')
            oldfit=json.loads((fits/f'M_{case}.json').read_text(encoding='utf-8'))
            exact_loss=replay_gate(model,Y,oldfit,model.model_id,binding)
            joint=[float(x) for x in oldfit['theta']]
            grid=np.unique(np.r_[np.arange(model.Ds[0],model.Ds[-1]+1e-9,pg['initial_D_nm_step']),model.Ds,joint[0],model.Ds[-1]])
            priorpath=out/'checkpoint'/f'{case}.json';rows={};call_prior=0
            if priorpath.is_file():
                prior=json.loads(priorpath.read_text(encoding='utf-8'))
                if prior['run_id']!=run_id or prior['case']!=case or prior['observation_sha256']!=binding:
                    raise ValueError(case+': checkpoint identity mismatch')
                rows={float(v['D']):v for v in prior['rows']};call_prior=int(prior['calls_prior_invocations'])
            remaining=int(pg['single_case_canonical_max'])-call_prior
            if remaining<=0:
                # Persist only existing points; never reset the per-case science budget on resume.
                obj=Objective(model,Y,1)
                write_json(out/'budget_exhausted_'+case+'.json',dict(case=case,cap=pg['single_case_canonical_max'],prior_calls=call_prior,status='PARTIAL_PROFILE_NO_NEW_CALLS'))
            else:
                obj=Objective(model,Y,remaining)
                obj.evaluate(joint)
            # Public bank selects starts from observed image, not from truth.
            bank_resid=np.linalg.norm(bimgs.reshape(len(bimgs),-1)-Y.ravel()[None,:],axis=1)
            idx=np.argsort(bank_resid,kind='stable')[:8];bank_seeds=bt[idx]
            budget=dict(deadline=deadline,per_start_calls=pg['per_start_call_limit'],max_nfev=pg['max_nfev_per_start'])
            # Two directions; already completed, sha-bound points are reused.
            for direction,order in ([('ascending',grid),('descending',grid[::-1])] if remaining>0 else []):
                hist={'ascending':None,'descending':None}
                for D in order:
                    D=float(D)
                    if time.monotonic()>deadline:break
                    existing=rows.get(D)
                    if existing and direction in existing.get('directions_completed',[]):
                        hist[direction]=existing['theta'];continue
                    if obj.calls>=obj.limit:break
                    witness=joint if abs(D-joint[0])<1e-8 else (existing['theta'] if existing and existing.get('theta') else None)
                    row=fixed_D_point(model,Y,D,joint,pg['axial_start_nm'],bank_seeds,obj,budget,hist,prior=witness)
                    row['direction_last_processed']=direction
                    row['directions_completed']=(existing.get('directions_completed',[]) if existing else []) + ([direction] if row['point_search_complete'] else [])
                    if existing:
                        row['attempts']=(existing.get('attempts',[])+row['attempts'])
                        if existing.get('loss_L2') is not None and (row.get('loss_L2') is None or existing['loss_L2']<row['loss_L2']):
                            row['loss_L2']=existing['loss_L2'];row['theta']=existing['theta'];row['witness_source']='PRESERVED_BETTER_CHECKPOINT_WITNESS'
                        # A later complete retry can supersede an incomplete old attempt;
                        # retain old failed attempts as explicit historical evidence.
                        row['point_search_complete']=bool(row['point_search_complete'])
                    rows[D]=row
                    if row['theta'] is not None:hist[direction]=row['theta']
                    write_json(priorpath,dict(case=case,run_id=run_id,model_id=model.model_id,
                        observation_sha256=binding,exact_joint_D=joint[0],exact_joint_loss_L2=exact_loss,
                        calls_prior_invocations=call_prior+obj.calls,rows=[rows[k] for k in sorted(rows)]))
            # The replayed old optimum is a valid feasible point even if the grid scan stops early.
            # It must not be silently omitted merely because ascending D never reached its D.
            jd=float(joint[0]);known=rows.get(jd)
            if known is None:
                rows[jd]=dict(D=jd,theta=joint.copy(),loss_L2=exact_loss,
                    point_search_complete=False,attempts=[],directions_completed=[],
                    source='REPLAYED_EXACT_JOINT_WITNESS_NOT_SEARCH_CERTIFICATE')
            elif known.get('loss_L2') is None or known['loss_L2']>exact_loss:
                known['theta']=joint.copy();known['loss_L2']=exact_loss
                known['witness_source']='PRESERVED_REPLAYED_EXACT_JOINT'
            write_json(priorpath,dict(case=case,run_id=run_id,model_id=model.model_id,
                observation_sha256=binding,exact_joint_D=joint[0],exact_joint_loss_L2=exact_loss,
                calls_prior_invocations=call_prior+obj.calls,rows=[rows[k] for k in sorted(rows)]))
            current=[rows[k] for k in sorted(rows)]
            grid_complete=all(float(D) in rows and rows[float(D)].get('point_search_complete') is True and set(rows[float(D)].get('directions_completed',[]))=={'ascending','descending'} for D in grid)
            local_min=min((z for z in current if z.get('loss_L2') is not None),key=lambda z:z['loss_L2'],default=None)
            output=dict(case=case,model_id=model.model_id,observation_sha256=binding,
                run_id=run_id,loss_type='UNSCALED_L2_ON_CENTRAL13_SIGNED_STATIC_C',
                known_joint_theta=joint,known_joint_loss_L2=exact_loss,rows=current,
                grid_coverage_complete=grid_complete,adaptive_coverage_complete=False,
                joint_reconciled=False,profile_scientific_complete=False,reportable_D=None,
                empirical_epsilon_L2=None,compatible_D_components=None,
                stage='COARSE_GRID_DIAGNOSTIC_REQUIRES_ADAPTIVE_DEV_ENVELOPE_AND_PHYSICAL_GATE',
                per_case_new_canonical_calls=obj.calls,
                prior_checkpoint_calls=call_prior,source='LOCKED_V133_F2')
            write_json(out/'profiles'/f'{case}.json',output)
            logs.append(dict(case=case,grid_points_expected=len(grid),grid_points_saved=len(current),
                grid_complete=grid_complete,known_joint_D=joint[0],known_joint_loss_L2=exact_loss,
                current_best_D=local_min['D'] if local_min else None,
                current_min_loss_L2=local_min['loss_L2'] if local_min else None,
                new_canonical_calls=obj.calls,actual_forward_calls_including_replay=meter.calls-case_meter_start,scientific_complete=False))
            print(case,'coarse-grid',len(current),'/',len(grid),'complete=',grid_complete,
                  'calls=',obj.calls,'reportable_D=null',flush=True)
    write_json(out/'component_status.json',dict(run_id=run_id,component='V137_INITIAL_LOCKED_F2_PROFILE',
        rows=logs,full_task_complete=False,physical_qualified=False,
        required_next=['SOURCE_GEOMETRY_AND_SAME_SOLVE_SHIFT','ADAPTIVE_COMPETITOR_REFINEMENT',
        'FROZEN_DEV_ERROR_ENVELOPE','FAIL_CLOSED_REPORTABILITY','CAMERA_AND_EXPOSURE_SHARED_D','EXPERIMENT_INPUT_AND_INDEPENDENT_ARCHIVE'],
        elapsed_seconds=time.monotonic()-t0,actual_component_canonical_forward_calls=meter.calls))
    return logs

def main():
    a=argparse.ArgumentParser();a.add_argument('--repo',required=True);a.add_argument('--config',required=True)
    a.add_argument('--out',required=True);a.add_argument('--cases',nargs='*',default=None)
    a.add_argument('--max-wall-minutes',type=float,default=240);a.add_argument('--resume',action='store_true')
    z=a.parse_args()
    try:run(z.repo,z.config,z.out,z.cases,z.max_wall_minutes,z.resume)
    except Exception as exc:
        err=Path(z.out)/'component_error.json';write_json(err,dict(type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),scientific_pass=False))
        print('PARTIAL_OR_BLOCKED '+str(exc),file=sys.stderr);return 2
    return 3 # intentional: first-pass stage done; full contract MUST continue
if __name__=='__main__':raise SystemExit(main())
