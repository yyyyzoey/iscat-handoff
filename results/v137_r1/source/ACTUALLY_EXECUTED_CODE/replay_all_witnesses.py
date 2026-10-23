"""Replay ALL six exact previously fitted parameter vectors before a long scan.

No truth registry is read. A replay proves identity of numerical outputs only;
it does not certify a physical model, uniqueness or experimental accuracy.
Exit 3: component complete, continue the full V137 contract. Exit 2: blocked.
"""
from __future__ import annotations
import argparse, hashlib, importlib, json, os, sys, time, traceback
from pathlib import Path
import h5py
import numpy as np


def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def array_sha(a):
    a=np.ascontiguousarray(a)
    return hashlib.sha256((str(a.shape)+'|'+str(a.dtype)).encode()+a.tobytes()).hexdigest()


def save(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    os.replace(tmp,path)


def replay_one(model,Y,fit,binding):
    if np.iscomplexobj(Y):raise ValueError('Signed static contrast must be real')
    Y=np.asarray(Y,dtype=float)
    if Y.shape!=(13,13) or not np.isfinite(Y).all():raise ValueError('Finite 13x13 signed image required')
    if fit.get('model_id')!=model.model_id:raise ValueError('Fit/model identity mismatch')
    if fit.get('observation_binding',{}).get('score_array_sha256')!=binding:
        raise ValueError('Fit/observation identity mismatch')
    if array_sha(Y)!=binding:raise ValueError('Actual image bytes differ')
    theta=np.asarray(fit['theta'],dtype=float)
    if theta.shape!=(4,) or not np.isfinite(theta).all():raise ValueError('Invalid stored theta')
    P=np.asarray(model.forward(theta).score_C,dtype=float)
    if P.shape!=Y.shape or not np.isfinite(P).all():raise ValueError('Invalid forward image')
    loss=float(np.linalg.norm(P-Y));known=float(fit['loss'])
    if not np.isfinite(known) or known<0:raise ValueError('Invalid saved residual')
    tolerance=max(1e-12,1e-7*abs(known))
    if abs(loss-known)>tolerance:raise ValueError('Stored legal witness does not replay; no inheritance')
    return dict(theta=theta.tolist(),exact_D=float(theta[0]),loss_L2=loss,
                saved_loss_L2=known,tolerance=tolerance,observation_sha256=binding,
                model_id=model.model_id,status='REPLAYED_FEASIBLE_POINT_ONLY',
                is_global_optimum_proof=False,is_physical_qualification=False,
                reportable_D=None),P


def run(repo,config,out):
    start=time.monotonic();repo=Path(repo).resolve();out=Path(out).resolve()
    out.mkdir(parents=True,exist_ok=True)
    cfg=json.loads(Path(config).read_text(encoding='utf-8-sig'));m=cfg['inherited_model']
    tool_dir=(repo/'tools').resolve();sys.path.insert(0,str(tool_dir))
    passport=json.loads((repo/m['model_passport']).read_text(encoding='utf-8-sig'))
    locks=passport['code_sha256'];actual={}
    for name,expected in locks.items():
        if Path(name).name!=name or not name.endswith('.py'):raise ValueError('Invalid dependency lock name')
        path=tool_dir/name
        if file_sha(path)!=expected:raise ValueError('Dependency byte mismatch: '+name)
        mod=importlib.import_module(name[:-3]);loaded=Path(mod.__file__).resolve()
        if loaded!=path or file_sha(loaded)!=expected:raise ValueError('Wrong imported dependency: '+name)
        actual[name]=dict(path=str(loaded),sha256=expected)
    from load_field_library import load_library
    from v133_recover_M import optical
    lib=repo/m['library'];obs=repo/m['prior_observations']
    if file_sha(lib)!=m['library_sha256']:raise ValueError('Library identity mismatch')
    old_cfg=json.loads((repo/'config/v133_science_config.json').read_text(encoding='utf-8-sig'))
    model,_=load_library(lib,kind='F2',optical=optical(old_cfg))
    if model.model_id!=m['model_id']:raise ValueError('Model ID mismatch')
    class Counter:
        def __init__(self,core): self.core=core; self.calls=0
        def __getattr__(self,name): return getattr(self.core,name)
        def forward(self,theta):
            self.calls+=1
            return self.core.forward(theta)
    model=Counter(model)
    binds=json.loads((repo/m['prior_observation_binding']).read_text(encoding='utf-8-sig'))
    if len({x['case'] for x in binds})!=len(binds):raise ValueError('Duplicate case bindings')
    binds={x['case']:x for x in binds};rows=[];failures=[]
    with h5py.File(obs,'r') as f:
        for case in cfg['M_opened_cases']:
            try:
                fit=json.loads((repo/m['prior_fits']/f'M_{case}.json').read_text(encoding='utf-8-sig'))
                Y=f[case]['score_C'][()]
                row,P=replay_one(model,Y,fit,binds[case]['score_array_sha256']);row['case']=case
                save(out/'cases'/f'{case}.json',row)
                np.savez_compressed(out/'cases'/f'{case}.npz',Y=Y,F_at_saved_theta=P,theta=np.asarray(row['theta']))
                rows.append(row)
            except Exception as exc:
                failures.append(dict(case=case,error=type(exc).__name__+': '+str(exc)))
    result=dict(component='ALL_SIX_EXACT_WITNESSES',model_id=model.model_id,
                library_sha256=file_sha(lib),observations_sha256=file_sha(obs),
                code=actual,runner_sha256=file_sha(__file__),config_sha256=file_sha(config),
                rows=rows,failures=failures,expected_cases=cfg['M_opened_cases'],
                all_replayed=len(rows)==len(cfg['M_opened_cases']) and not failures,
                case_replay_attempts=len(rows)+len(failures),
                canonical_forward_calls=model.calls,
                elapsed_seconds=time.monotonic()-start,full_task_complete=False,
                required_next='SAME_MODEL_F2_PROFILE_AND_PHYSICAL_CHECKS_THEN_CAMERA_EXPOSURE_INTERFACE')
    result['counter_scope']='Actual forward entries in this component; integrate with task-wide event ledger'
    save(out/'witness_manifest.json',result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('repo','config','out'):p.add_argument('--'+n,required=True)
    a=p.parse_args()
    try:
        r=run(a.repo,a.config,a.out)
        print('EXACT_WITNESSES',len(r['rows']),'/',len(r['expected_cases']),'CONTINUE_FULL_CONTRACT')
        return 3 if r['all_replayed'] else 2
    except Exception as exc:
        save(Path(a.out)/'component_error.json',dict(error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),full_task_complete=False))
        return 2
if __name__=='__main__':raise SystemExit(main())
