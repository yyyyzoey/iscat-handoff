"""V131 executable OFFLINE batch; no BEM and no absolute-size certification.
All old-image candidates are produced before expensive profiles. F2 follows
V130's repaired branch. Cached public starts cover four axial strata.
Codex must continue the project physical validation/count/motion stages in
the same authorized run; exit 0 here means OFFLINE computation only.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,os,platform,sys,time,traceback
from pathlib import Path
import h5py
import numpy as np
from load_field_library import load_library,sha256
from determinism_gate import deterministic_gate
from fit_reference import diameter_profile
from template_bank import TemplateBank,fit_with_bank

class DeadlineStop(RuntimeError):pass
class TimedModel:
    def __init__(self,core,deadline):self.core=core;self.deadline=deadline;self.calls=0
    def __getattr__(self,k):return getattr(self.core,k)
    def forward(self,theta):
        if time.monotonic()>=self.deadline:raise DeadlineStop("OFFLINE_DEADLINE")
        self.calls+=1;return self.core.forward(theta)
    def C(self,D,h,x,y,score=True):
        o=self.forward((D,h,x,y));return o.score_C if score else o.C

def dump(path,val):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.tmp')
    t.write_text(json.dumps(val,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8');os.replace(t,p)
def write_csv(path,rows):
    if not rows:return
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=sorted({k for r in rows for k in r}));w.writeheader();w.writerows(rows)
def optical_from(cfg):
    c=cfg['conditional_model']
    return dict(pixel_nm=c['object_pixel_nm'],q=c['q'],camera_n=c['camera_n'],score_n=c['score_n'],
                xy_limit_nm=c['xy_limit_nm'],min_gap_nm=c['min_surface_gap_nm'],
                expected_node_metadata=dict(n_particle=complex(*c['particle_n_re_im']),NA=c['NA'],object_pixel_nm=c['object_pixel_nm']))
def fit_row(setname,name,fit):
    return dict(data_set=setname,case=name,candidate_D=fit['candidate_D'],reportable_D=None,
                h=fit['theta'][1],x=fit['theta'][2],y=fit['theta'][3],loss=fit['loss'],
                optimizer_converged=fit['optimizer_converged'],search_complete=fit['search_complete'],
                profile_complete=fit.get('profile_complete',False),
                boundary_flags=json.dumps(fit['boundary_flags']),
                scope=fit['scope'],reason="PENDING_PHYSICAL_NUMERICAL_AND_PROFILE_GATES")

def main(argv=None):
    ap=argparse.ArgumentParser()
    for n in ('repo','config','out'):ap.add_argument('--'+n,required=True)
    ap.add_argument('--kind',choices=['F1','F2','F3'],default='F2')
    ap.add_argument('--resume',action='store_true')
    ap.add_argument('--sets',nargs='*')
    ap.add_argument('--no-profiles',action='store_true')
    ap.add_argument('--wall-hours',type=float)
    args=ap.parse_args(argv)
    repo=Path(args.repo).resolve();cp=Path(args.config).resolve();out=Path(args.out).resolve()
    cfg=json.loads(cp.read_text(encoding='utf-8'));lib=repo/cfg['inputs']['train']
    sources={p.name:sha256(p) for p in Path(__file__).parent.glob('*.py')}
    sets=args.sets if args.sets is not None else cfg['offline_batch']['sets_order']
    identity=dict(library_path=str(lib),library_sha256=sha256(lib),configuration_sha256=sha256(cp),
                  sources=sources,kind=args.kind,sets=sets,profiles=not args.no_profiles)
    run_id=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    ip=out/'source_identity.json'
    if ip.exists():
        old=json.loads(ip.read_text())
        if old['run_id']!=run_id or not args.resume:raise ValueError('New identity or missing --resume; use a new output directory')
    out.mkdir(parents=True,exist_ok=True)
    dump(ip,dict(run_id=run_id,**identity,python=sys.version,platform=platform.platform(),argv=sys.argv))
    hours=cfg['budget']['wall_clock_hours_max']
    if args.wall_hours is not None:hours=min(hours,args.wall_hours)
    reserve=cfg['budget']['reserve_for_archive_minutes']*60
    if hours*3600<=reserve:raise ValueError('Archive reserve exceeds available time')
    start=time.monotonic();deadline=start+hours*3600-reserve
    status=dict(task_id=cfg['task_id'],run_id=run_id,execution='RUNNING',stages={},errors=[],
                bem_new=0,render_new=0,camera_exposures=0,experimental_absolute_validated=False,
                reportable_size_validation='NOT_CERTIFIED')
    model=None;candidate_rows=[];profile_tasks=[];full_closure=False
    try:
        core,report=load_library(lib,kind=args.kind,optical=optical_from(cfg))
        model=TimedModel(core,deadline);dump(out/'library_array_checks.json',report)
        status['stages']['intake']='ARRAY_CHECKS_ONLY_REQUIRES_SOLVE_IDENTITY'
        dc=cfg['initial_determinism']
        gate=deterministic_gate(model,dc['points'],dc['repeats'],dc['absolute_C_tolerance'])
        dump(out/'actual_entry_determinism.json',gate)
        if not gate['passed']:raise RuntimeError('NONDETERMINISTIC_OR_SPLIT_FORWARD')
        status['stages']['determinism']='PASS'
        # Save conditional calibration observations even when later inversion has problems.
        curves=[]
        with h5py.File(out/'calibration_observations.h5','w') as hf:
            hf.attrs.update(model_id=model.model_id,run_id=run_id)
            for D in model.Ds:
                for H in model.Hs:
                    o=model.forward([float(D),float(H),0,0]);g=hf.create_group(f'D{D:g}_h{H:g}')
                    for key,arr in [('C17',o.C),('score_C13',o.score_C),('Ibg17',o.Ibg),('I17',o.I)]:
                        g.create_dataset(key,data=arr,compression='gzip')
                    curves.append(dict(D=float(D),h=float(H),center_C=float(o.score_C[model.s//2,model.s//2]),
                                       peak_abs_C=float(abs(o.score_C).max()),rms_C=float(np.sqrt(np.mean(o.score_C**2)))))
        write_csv(out/'calibration_nodes.csv',curves)
        bc=cfg['template_bank']
        bank=TemplateBank(model,bc['offsets_nm'],midpoints=bc['include_axis_midpoints'],
                          strata=bc['height_strata_count'],separation=bc['separation_nm'])
        dump(out/'template_bank_manifest.json',bank.manifest())
        with h5py.File(out/'public_initialization_bank.h5','w') as hf:
            hf.attrs.update(model_id=bank.model_id,bank_id=bank.bank_id,role="INITIALIZATION_ONLY")
            hf.create_dataset('theta',data=bank.theta)
            hf.create_dataset('score_C',data=bank.images,compression='gzip')
        # Every input is the same-model numerical diagnostic, never direct-physics evidence.
        closures=[]
        for i,p in enumerate(cfg['closure']['samples']):
            dest=out/'closure'/f'{i:02d}.json'
            if args.resume and dest.exists():r=json.loads(dest.read_text())
            else:
                Y=model.forward(p).score_C.copy();w=model.forward(p).score_C
                if np.max(abs(w-Y))>dc['absolute_C_tolerance']:raise RuntimeError("GENERATOR_WITNESS_MISMATCH")
                fit=fit_with_bank(model,Y,bank,total_calls=cfg['fit']['single_total_canonical_calls'],max_starts=bc['max_starts'])
                tol=max(1e-12,1e-6*float(np.linalg.norm(Y)))
                r=dict(sample=i,theta_generator=list(map(float,p)),tolerance=tol,
                       witness_residual=float(np.linalg.norm(w-Y)),closed=bool(fit['loss']<=tol),fit=fit)
                dump(dest,r);np.savez_compressed(dest.with_suffix('.npz'),Y=Y,F_at_true=w,theta_generator=p)
            closures.append(dict(sample=i,D_generator=r['theta_generator'][0],candidate_D=r['fit']['candidate_D'],
                                 residual=r['fit']['loss'],tolerance=r['tolerance'],closed=r['closed'],
                                 search_complete=r['fit']['search_complete']))
            write_csv(out/'closure_summary.csv',closures)
            print(f"closure {i+1}: {r['closed']}",flush=True)
            if i+1==cfg['closure']['smoke_first_n'] and not all(r['closed'] for r in closures):break
        full_closure=len(closures)==len(cfg['closure']['samples']) and all(r['closed'] for r in closures)
        status['stages']['closure']='PASS_SAME_MODEL_ONLY' if full_closure else 'FAILED_OR_PARTIAL'
        # Existing data can still diagnose failures. They are NEVER certified on failed closure.
        scope='DEVELOPMENT_NO_SIZE_CERTIFICATION' if full_closure else 'UNQUALIFIED_OPTIMIZER_DIAGNOSTIC'
        for setname in sets:
            path=repo/cfg['offline_batch']['sets'][setname]
            if not path.exists():
                status['errors'].append(dict(set=setname,error='MISSING_INPUT',path=str(path)));continue
            dump(out/'observation_identity'/f'{setname}.json',dict(path=str(path),sha256=sha256(path),role='OPENED_DEVELOPMENT'))
            with h5py.File(path,'r') as hf:
                for name in sorted(hf):
                    dest=out/'fits'/f'{setname}_{name}.json'
                    try:
                        raw=hf[name][cfg['inputs']['observation_dataset']][()]
                        if np.iscomplexobj(raw):raise ValueError('Static signed contrast must be real')
                        Y=np.asarray(raw,float)
                        if Y.shape==(model.n,model.n):
                            k=(model.n-model.s)//2;Y=Y[k:k+model.s,k:k+model.s]
                        if Y.shape!=(model.s,model.s) or not np.isfinite(Y).all():raise ValueError('Invalid image')
                        if args.resume and dest.exists():fit=json.loads(dest.read_text())
                        else:
                            fit=fit_with_bank(model,Y,bank,total_calls=cfg['fit']['single_total_canonical_calls'],max_starts=bc['max_starts'])
                            fit.update(case=name,data_set=setname,scope=scope,run_id=run_id);dump(dest,fit)
                        candidate_rows.append(fit_row(setname,name,fit))
                        write_csv(out/'old_per_particle_candidates.csv',candidate_rows)
                        if setname in cfg['offline_batch']['profile_sets']:profile_tasks.append((setname,name,Y.copy(),fit,dest))
                        print(f"{setname}/{name}: candidate={fit['candidate_D']:.6f}; reportable=null",flush=True)
                    except DeadlineStop:raise
                    except Exception as exc:
                        status['errors'].append(dict(set=setname,case=name,error=str(exc),traceback=traceback.format_exc()))
                        dump(out/'failures'/f'{setname}_{name}.json',status['errors'][-1])
        status['stages']['all_old_candidates']='COMPLETED' if not status['errors'] else 'PARTIAL'
        dump(out/'status.json',status)
        # Second pass: do not spend a whole round profiling the first case before other candidates exist.
        if not args.no_profiles:
            priority=cfg['offline_batch']['profile_priority']
            profile_tasks.sort(key=lambda z:priority.index(z[0]+'_'+z[1]) if z[0]+'_'+z[1] in priority else len(priority))
            if not full_closure:
                profile_tasks=[z for z in profile_tasks if z[0]+'_'+z[1] in priority[:2]]
            for setname,name,Y,fit,dest in profile_tasks:
                ppath=out/'profiles'/f'{setname}_{name}.json'
                if args.resume and ppath.exists():prof=json.loads(ppath.read_text())
                else:
                    prof=diameter_profile(model,Y,fit,step_nm=cfg['fit']['profile_initial_step_nm'],
                                          total_calls=cfg['fit']['profile_total_canonical_calls'])
                    dump(ppath,prof)
                fit['profile_complete']=prof['profile_complete'];fit['profile_updates_joint']=prof['update_joint_required']
                dump(dest,fit)
                for row in candidate_rows:
                    if row['data_set']==setname and row['case']==name:row.update(fit_row(setname,name,fit))
                write_csv(out/'old_per_particle_candidates.csv',candidate_rows)
                print(f"profile {setname}/{name}: complete={prof['profile_complete']}; further adaptive/profile gate required",flush=True)
        status['execution']='OFFLINE_RECOVERY_COMPLETE' if full_closure and not status['errors'] else 'PARTIAL_OFFLINE'
        status['stages']['physical_qualification']='REQUIRES_PROJECT_DIRECT_RENDER_AND_SOURCE_CHECK'
        status['stages']['formal_reportability']='NOT_CERTIFIED'
    except DeadlineStop as exc:
        status['execution']='PARTIAL_DEADLINE';status['errors'].append(dict(error=str(exc)))
    except Exception as exc:
        status['execution']='BLOCKED_OR_FAILED';status['errors'].append(dict(error=str(exc),traceback=traceback.format_exc()))
    finally:
        status['elapsed_seconds']=time.monotonic()-start
        status['canonical_calls_this_invocation']=model.calls if model is not None else 0
        status['note']='OFFLINE component only. Codex must continue project physical checks, adaptive complete profiles, inference gates, conditional M/camera/motion and final archive.'
        dump(out/'status.json',status)
    print(json.dumps({k:status[k] for k in ('execution','stages','canonical_calls_this_invocation')},ensure_ascii=False))
    return 0 if status['execution']=='OFFLINE_RECOVERY_COMPLETE' else 2
if __name__=='__main__':raise SystemExit(main())
