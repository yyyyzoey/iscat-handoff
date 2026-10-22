"""Runnable zero-BEM recovery of the already opened M images with LOCKED F2.
Never reads a truth file. Does not certify physical accuracy or finish the full
V133 task. Successful component exit code is 3 (CONTINUE FULL CONTRACT).
"""
from __future__ import annotations
import argparse,csv,hashlib,json,os,sys,time,traceback
from pathlib import Path
import h5py,numpy as np
from load_field_library import load_library
from observation_adapter import file_sha256,read_static_observations,image_schema
from model_lock import verify_code_lock,LockedF2,passport
from template_bank import TemplateBank,fit_with_bank


def dump(path,obj):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.tmp')
    t.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8');os.replace(t,p)


def write_csv(path,rows):
    if not rows:return
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=sorted({k for r in rows for k in r}));w.writeheader();w.writerows(rows)


def optical(cfg):
    c=cfg['conditional_model']
    return dict(pixel_nm=c['object_pixel_nm'],q=c['q'],camera_n=c['camera_n'],score_n=c['score_n'],
                xy_limit_nm=c['xy_limit_nm'],min_gap_nm=c['min_surface_gap_nm'],
                expected_node_metadata=dict(n_particle=complex(*c['particle_n_re_im']),NA=c['NA'],object_pixel_nm=c['object_pixel_nm']))


def get_bank(model,repo,cfg):
    bc=cfg['template_bank'];p=repo/cfg['reuse']['public_bank']
    if p.is_file():
        with h5py.File(p,'r') as f:
            if str(f.attrs['model_id'])!=model.model_id:raise ValueError('Old bank model identity mismatch; no silent reuse')
            theta=f['theta'][()];images=f['score_C'][()];stored_id=str(f.attrs['bank_id'])
        if theta.ndim!=2 or theta.shape[1]!=4 or images.shape!=(len(theta),model.s,model.s) or not np.isfinite(images).all():raise ValueError('Invalid public bank')
        ident=json.dumps(dict(model_id=model.model_id,theta=theta.tolist()),sort_keys=True).encode()
        got=hashlib.sha256(ident+images.tobytes()).hexdigest()
        if got!=stored_id or got!=cfg['reuse']['expected_bank_id']:raise ValueError('Public bank content identity mismatch')
        for i in np.unique(np.linspace(0,len(theta)-1,7,dtype=int)):
            if np.max(abs(model.forward(theta[i]).score_C-images[i]))>1e-12:raise ValueError('Public bank does not replay')
        b=TemplateBank.__new__(TemplateBank)
        b.model_id=model.model_id;b.strata=int(bc['height_strata_count']);b.separation=np.asarray(bc['separation_nm'],float)
        b.h_range=(model.Hs[0],model.Hs[-1]);b.theta=theta;b.images=images;b.shape=images.shape[1:];b.matrix=images.reshape(len(images),-1)
        b.bank_id=got;b.n_queries=0
        return b,dict(source='REUSED_BOUND_PUBLIC_BANK',path=str(p),sha256=file_sha256(p),bank_id=got)
    b=TemplateBank(model,bc['offsets_nm'],midpoints=bc['include_axis_midpoints'],strata=bc['height_strata_count'],separation=bc['separation_nm'])
    return b,dict(source='REBUILT_ONCE_FROM_SAME_F2',**b.manifest())


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('repo','config','out'):ap.add_argument('--'+n,required=True)
    ap.add_argument('--resume',action='store_true');a=ap.parse_args(argv)
    repo=Path(a.repo).resolve();out=Path(a.out).resolve();cfg=json.loads(Path(a.config).read_text(encoding='utf-8'))
    out.mkdir(parents=True,exist_ok=True);start=time.monotonic();rows=[];model=None
    status=dict(task_id=cfg['task_id'],component='F2_M_RECOVERY',full_task_complete=False,stages={},errors=[],new_BEM=0,new_render=0,new_camera_exposures=0)
    try:
        code=verify_code_lock(cfg['model_lock']['numerical_source_sha256'])
        actual_imports={}
        for filename,expected in cfg['model_lock']['numerical_source_sha256'].items():
            mod=sys.modules.get(filename[:-3])
            if mod is None or not getattr(mod,'__file__',None):raise ValueError(f'Expected dependency not imported: {filename}')
            loaded=Path(mod.__file__).resolve()
            if loaded.parent!=Path(__file__).resolve().parent or file_sha256(loaded)!=expected:
                raise ValueError(f'Actual import is not the locked dependency: {filename}')
            actual_imports[filename]=dict(path=str(loaded),sha256=file_sha256(loaded))
        lib=repo/cfg['inputs']['train'];obs=repo/cfg['M_observations']['path']
        if file_sha256(lib)!=cfg['model_lock']['library_sha256']:raise ValueError('Library bytes changed; dataset/attrs audit required before this lock can be updated')
        dump(out/'observation_schema.json',image_schema(obs))
        identity=dict(library_sha256=file_sha256(lib),observation_sha256=file_sha256(obs),config_sha256=file_sha256(a.config),
                      sources={p.name:file_sha256(p) for p in Path(__file__).parent.glob('*.py')})
        run_id=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
        ip=out/'source_identity.json'
        if ip.exists():
            previous=json.loads(ip.read_text(encoding='utf-8'))
            if not a.resume or previous['run_id']!=run_id:raise ValueError('Resume identity mismatch or missing --resume; use new output directory')
        dump(ip,dict(run_id=run_id,**identity,argv=sys.argv,actual_imports=actual_imports,python=sys.version))
        core,report=load_library(lib,kind='F2',optical=optical(cfg))
        model=LockedF2(core,cfg['model_lock']['model_id'],deadline=start+cfg['component_limits']['wall_minutes']*60,call_limit=cfg['component_limits']['canonical_calls'])
        dump(out/'library_array_checks.json',report)
        gate=passport(model,cfg['model_lock']['sentinel_theta_nm'])
        dump(out/'model_passport.json',dict(run_id=run_id,code_sha256=code,**gate))
        records=read_static_observations(obs,cfg['M_observations']['cases'],dataset=cfg['M_observations']['dataset'],camera_n=model.n,score_n=model.s)
        dump(out/'observation_binding.json',[r['binding'] for r in records])
        with h5py.File(out/'anonymous_M_images.h5','w') as f:
            f.attrs.update(model_id=model.model_id,run_id=run_id,role='OPENED_DIRECT_DEVELOPMENT_NOT_NEW_BLIND')
            for r in records:
                g=f.create_group(r['case']);g.create_dataset('score_C',data=r['image']);g.create_dataset('source_C',data=r['original'])
                g.attrs.update(source_dataset=r['binding']['source_dataset'],score_sha256=r['binding']['score_array_sha256'])
        bank,binding=get_bank(model,repo,cfg);dump(out/'bank_binding.json',binding)
        status['stages']['locked_F2']='NUMERICALLY_BOUND_PHYSICAL_QUALIFICATION_SEPARATE'
        for r in records:
            fp=out/'fits'/f"M_{r['case']}.json"
            if fp.exists():
                if not a.resume:raise ValueError('Existing candidate without --resume')
                fit=json.loads(fp.read_text(encoding='utf-8'))
                if fit['run_id']!=run_id or fit['observation_binding']!=r['binding']:raise ValueError('Candidate binding differs')
                actual=float(np.linalg.norm(model.forward(fit['theta']).score_C-r['image']))
                if abs(actual-fit['loss'])>max(1e-12,1e-7*abs(fit['loss'])):raise ValueError('Resumed candidate no longer replays')
            else:
                fit=fit_with_bank(model,r['image'],bank,total_calls=cfg['fit']['single_total_canonical_calls'],max_starts=cfg['template_bank']['max_starts'])
                # Do not equate a completed invocation with all required starts converged.
                fit['search_complete']=bool(fit['search_complete'] and all(x.get('success') is True and not x.get('budget_exhausted',False) for x in fit['starts']))
                fit.update(case=r['case'],data_set='M',run_id=run_id,observation_binding=r['binding'],
                    reportable_D=None,diameter_reportable=False,scope='OPENED_DIRECT_DEVELOPMENT_NOT_NEW_BLIND',
                    reason_codes=['PHYSICAL_QUALIFICATION_PROFILE_AND_REPORTABILITY_PENDING'])
                dump(fp,fit)
            rows.append(dict(case=r['case'],candidate_D=fit['candidate_D'],reportable_D=None,h=fit['theta'][1],x=fit['theta'][2],y=fit['theta'][3],
                             loss=fit['loss'],optimizer_converged=fit['optimizer_converged'],search_complete=fit['search_complete'],
                             model_id=model.model_id,run_id=run_id,scope=fit['scope']))
            write_csv(out/'M_F2_candidates.csv',rows)
            print(f"{r['case']}: candidate {fit['candidate_D']:.6f} nm; reportable=null",flush=True)
        status['execution']='F2_M_CANDIDATES_COMPUTED_NOT_TASK_COMPLETE'
        status['required_next']=['RAW_SOURCE_AND_SAME_SOLVE_SHIFT_CHECK','L_OPTIONAL_METADATA_RECOVERY_AND_DIAGNOSTICS','PROFILE_AND_JOINT_RECONCILIATION','CAMERA_EXPOSURE_SHARED_D_WITH_SAME_F2','EXPERIMENT_INTERFACE_AND_CHECKED_RETURN']
        result=3
    except Exception as e:
        status['execution']='PARTIAL_OR_BLOCKED';status['errors'].append(dict(error=f'{type(e).__name__}: {e}',traceback=traceback.format_exc()));result=2
    finally:
        status['elapsed_seconds']=time.monotonic()-start;status['canonical_calls']=model.calls if model is not None else 0
        status['candidate_rows_saved']=len(rows);status['experimental_absolute_validated']=False
        dump(out/'component_status.json',status)
    return result

if __name__=='__main__':raise SystemExit(main())
