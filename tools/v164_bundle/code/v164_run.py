"""V164 extension of the verified V163 runner: fixed-D conditional design only."""
from __future__ import annotations
import argparse,contextlib,hashlib,importlib,json,shutil,sqlite3,sys,traceback
from pathlib import Path
import numpy as np
from v152_budget_store import BudgetStore,CountedPredictor,atomic_json,canonical
from v152_gls_core import GlsData
from v157_height_design import local_design,plan_paths,evaluate_path
from v164_profile_core import (Problem,GROUPS,DESIGNS,DELTAS,SIGMAS,solve_profile,
                               pool_profiles,evaluate)
from v164_io import (PARENT,OLD_ZIP_SHA,require,read,sha,blob,git,lock_sources,
                     archive_check,ledger_check,compare_nested)
PHASES={'MODEL_BINDING':160,'FIXED_D_DESIGN':9600,'FINAL_VERIFY':240}
OWNER='v164-single-process'
MODEL='v142-F2c-75860d222dd8e90d8dc2e31111e52ccbbb212a01c0d6a0dfe7fdbcdb241c98c3'


def import_historic(repo,name):
    where=repo/'tools/v163_bundle/code'
    if str(where) not in sys.path:sys.path.insert(0,str(where))
    m=importlib.import_module(name)
    require(Path(m.__file__).resolve()==(where/f'{name}.py').resolve(),'WRONG_HISTORIC_IMPORT:'+name)
    return m


def history(repo):
    old=repo/'results/v163'
    ar=archive_check(old/'iscat_v163_return.zip');require(ar['sha256']==OLD_ZIP_SHA,'WRONG_V163_RETURN')
    ledger=ledger_check(old,plan_id='v163',expected_total=273)
    selected=read(old/'selected_candidates_12.json');designs=read(old/'design/saved_array_designs.json')
    require(len(selected)==12 and len(designs)==12,'HISTORY_GROUPS')
    dep=import_historic(repo,'v163_deployment');root=repo/'tools/v163_bundle'
    receipt=read(old/'workstation_tests/test_receipt.json');outcome=read(old/'workstation_tests/pytest_outcomes.json')
    inv=read(root/'test_inventory.json')
    require(receipt['returncode']==0 and receipt['bundle_sha256']==dep.bundle_hashes(root),'HISTORY_TEST_BINDING')
    require(sorted(outcome['collected'])==inv['nodeids'] and len(inv['nodeids'])==247,'HISTORY_TEST_SET')
    require(outcome['exitstatus']==0 and not outcome['collection_errors'],'HISTORY_TEST_FAILURE')
    require(len(outcome['reports'])==741 and all(x['outcome']=='passed' for x in outcome['reports']),'HISTORY_TEST_PHASES')
    require(sha(old/'workstation_tests/pytest_outcomes.json')==receipt['outcomes_sha256'],'HISTORY_TEST_OUTCOME_HASH')
    dc=import_historic(repo,'v163_design')
    contexts={};rows={};summary=[]
    for name in sorted(selected):
        d=read(old/f'source_context/v156/{name}.json')['diagnostic']
        recomputed=dc.complete_design(d);compare_nested(recomputed,designs[name],name)
        require(np.array_equal(selected[name]['theta'],d['theta']),'HISTORY_ANCHOR_IDENTITY')
        contexts[name]=d
        if name not in GROUPS:continue
        data=GlsData.from_frames(d['frame_Y'],d['frame_V']);c0=np.asarray(d['predictions'][d['base_index']]['C'])
        planned=plan_paths(d['theta'],d['whitened_J_fine']);rr=[]
        require(len(planned)==24,'HISTORY_PLAN_COUNT')
        for i,plan in enumerate(planned):
            r=read(old/f'probes/{name}/{i:02d}.json');require(r['state']=='EVALUATED','OLD_PROBE_NOT_EVALUATED')
            require(np.array_equal(r['theta'],plan['theta']) and r['path']==plan['path'],'OLD_POINT_IDENTITY')
            replay=evaluate_path(plan,c0=c0,data=data,jw=d['whitened_J_fine'],predict=lambda t,r=r:np.asarray(r['C']),persist=lambda _:None)
            compare_nested(replay,r,f'{name}/{i}')
            rr.append(r)
        rows[name]=rr
        for tag in ('free_hxy','exact_height','height_sigma10'):
            sub=[r for r in rr if r['path']==tag]
            summary.append(dict(group=name,path=tag,points=len(sub),
                relative_linearization_passes=sum(1 for r in sub if r['relative_linearization_error']<=.05),
                max_image_distance_squared=max(r['image_distance_squared'] for r in sub),
                endpoint_values=[{k:r[k] for k in ('delta_D_nm','image_distance_squared','predicted_image_distance_squared','total_design_distance_squared','relative_linearization_error','observed_Q_change')} for r in sub if abs(r['delta_D_nm'])==5]))
    return dict(archive=ar,ledger=ledger,tests=247,old_designs=1224,old_probes=72,
                scope='READONLY_PUBLISHED_DATA_RECONSTRUCTION_NOT_NEW_OPTICAL_RUN',by_path=summary),contexts,rows


def own_receipt(bundle,out):
    from v164_receipts import verify_receipt
    return verify_receipt(bundle,out/'workstation_tests')


def preflight(repo,out):
    bundle=Path(__file__).resolve().parent.parent
    require(bundle==repo/'tools/v164_bundle','INSTALL_COMPLETE_BUNDLE')
    own_receipt(bundle,out)
    require(git(repo,'merge-base','--is-ancestor',PARENT,'HEAD')==b'','WRONG_PARENT')
    sources=lock_sources(repo)
    from v164_receipts import hashes
    for rel_in_bundle in hashes(bundle):
        p=bundle/rel_in_bundle;rel=p.relative_to(repo).as_posix()
        require(git(repo,'rev-parse','HEAD:'+rel).decode().strip()==blob(p),'UNCOMMITTED_EXECUTION_CODE:'+rel)
    for name in ('v152_budget_store.py','v152_gls_core.py','v157_height_design.py'):
        wanted=git(repo,'rev-parse',PARENT+':tools/v163_bundle/code/'+name).decode().strip()
        require(blob(bundle/'code'/name)==wanted,'APPROVED_CORE_CHANGED:'+name)
    cfg=read(bundle/'config/v164_plan.json')
    require(cfg['parent']==PARENT and cfg['phases']==PHASES and cfg['total']==10000,'PLAN_CHANGED')
    require(cfg['groups']==list(GROUPS) and cfg['designs']==list(DESIGNS) and cfg['delta_D_nm']==list(DELTAS),'SCIENCE_GRID_CHANGED')
    require(cfg['task_cap']==400 and cfg['per_start_cap']==200 and cfg['fits']==24 and cfg['starts']==2,'TASK_GRID_CHANGED')
    require(all(cfg[k]==0 for k in ('new_BEM','new_render','new_camera','new_noise','new_four_parameter_fits','new_Jacobian')) and cfg['all_reportable_D_null'] is True,'FORBIDDEN_WORK_ENABLED')
    pins=import_historic(repo,'v163_source_bridge').verify_runtime_pins(repo)
    audit,contexts,rows=history(repo)
    require(all(import_historic(repo,'v163_design').probe_eligible(read(repo/'results/v163/design/saved_array_designs.json')[n]) for n in GROUPS),'ANCHOR_QUALIFICATION')
    atomic_json(out/'history_audit.json',audit)
    atomic_json(out/'preflight.json',dict(parent=PARENT,execution_code_commit=git(repo,'rev-parse','HEAD').decode().strip(),source_lock=sources,runtime_pins=pins,model_calls=0))
    for name in GROUPS:
        raw=(repo/f'results/v163/source_context/v156/{name}.json').read_bytes()
        p=out/f'source_context/{name}.json';p.parent.mkdir(parents=True,exist_ok=True)
        if p.exists():require(p.read_bytes()==raw,'CONTEXT_CHANGED')
        else:p.write_bytes(raw)
    return cfg,contexts,rows


def task(store,name,phase,cap,out,signature,work):
    require(store.reserve(name,signature,phase,cap,OWNER)=='RUNNING' and store.counts()[name]==0,'EXISTING_TASK_NO_AUTO_RETRY')
    p=out/'tasks'/name/'result.json'
    try:
        payload=work(name)
        state='PARTIAL_BUDGET' if isinstance(payload,dict) and any(r.get('state')=='PARTIAL_BUDGET' for r in payload.get('starts',[])) else 'FINISHED'
        atomic_json(p,dict(signature=signature,state=state,actual_calls=store.counts()[name],payload=payload))
        store.seal(name,OWNER,state,p);return payload
    except Exception as exc:
        atomic_json(p,dict(signature=signature,state='FAILED',error=repr(exc),traceback=traceback.format_exc(),actual_calls=store.counts()[name]))
        try:store.seal(name,OWNER,'FAILED',p)
        except Exception as seal:atomic_json(p.with_name('seal_error.json'),dict(error=repr(seal)))
        raise


def predictor(model,store,name,out):
    counted=CountedPredictor(lambda t:model.forward(tuple(map(float,t))).score_C,store,name,OWNER)
    cache={}
    def call(t):
        key=tuple(map(float,t))
        if key in cache:return cache[key].copy()
        c=counted(t);seq=store.counts()[name]
        atomic_json(out/'tasks'/name/'predictions'/f'{seq:04d}.json',dict(theta=list(key),C=c.tolist(),seq=seq,task=name))
        cache[key]=c.copy();return c
    return call


def construct(repo,store,out,signature):
    sys.path.insert(0,str(repo/'tools'))
    runtime=importlib.import_module('v146_runtime');fields=importlib.import_module('field_forward_reference')
    for m in (runtime,fields):require(Path(m.__file__).resolve().parent==repo/'tools','WRONG_MODEL_IMPORT')
    holder={}
    def work(name):
        original=fields.FieldForward.forward
        def wrapped(instance,t):
            seq=store.charge(name,OWNER,t)
            try:
                r=original(instance,t);c=np.asarray(r.score_C,float)
                require(c.shape==(13,13) and np.isfinite(c).all(),'LOADER_ARRAY')
            except Exception as exc:
                store.returned(name,seq,'MODEL_ERROR',dict(error=repr(exc),traceback=traceback.format_exc()));raise
            store.returned(name,seq,'RETURNED',dict(kind='F2_LOADER',C_sha256=hashlib.sha256(np.ascontiguousarray(c).tobytes()).hexdigest()))
            return r
        fields.FieldForward.forward=wrapped
        try:holder['model']=runtime.construct_bound(repo,read(repo/'config/v146_science_config.json'))
        finally:fields.FieldForward.forward=original
        require(holder['model'].model_id==MODEL,'F2C_IDENTITY')
        return dict(model_id=holder['model'].model_id)
    task(store,'LOADER_1','MODEL_BINDING',100,out,signature,work)
    return holder['model']


def execute(repo,out):
    require(not (out/'logs/v164_budget.sqlite').exists(),'EXISTING_LEDGER_NO_AUTO_REEXECUTION')
    cfg,contexts,rows=preflight(repo,out)
    signature=hashlib.sha256(canonical(dict(config=cfg,preflight=read(out/'preflight.json'))).encode()).hexdigest()
    store=BudgetStore(out/'logs/v164_budget.sqlite','v164',PHASES,10000)
    model=construct(repo,store,out,signature)
    def binding(name):
        call=predictor(model,store,name,out);records=[]
        for group in GROUPS:
            d=contexts[group]
            witnesses=[dict(theta=d['theta'],C=d['predictions'][d['base_index']]['C'],kind='anchor')]
            witnesses += [dict(theta=r['theta'],C=r['C'],kind='old_free_plus5') for r in rows[group] if r['path']=='free_hxy' and r['delta_D_nm']==5]
            for w in witnesses:
                c=call(w['theta']);require(np.allclose(c,w['C'],atol=1e-12,rtol=1e-10),'HISTORIC_PIXEL_REPLAY')
                records.append(dict(group=group,kind=w['kind'],theta=w['theta']))
        return records
    task(store,'BINDING','MODEL_BINDING',12,out,signature,binding)
    profiles=[];pools=[]
    for group in GROUPS:
        d=contexts[group];gd=GlsData.from_frames(d['frame_Y'],d['frame_V'])
        c0=np.asarray(d['predictions'][d['base_index']]['C'])
        for delta in DELTAS:
            block=[]
            for design in DESIGNS:
                problem=Problem(group,delta,design,np.asarray(d['theta']),c0,gd,np.asarray(d['whitened_J_fine']))
                prior=[dict(theta=r['theta'],C=r['C'],source_id=f'V163:{group}:{r["path"]}:{delta}') for r in rows[group] if r['path']==design and r['delta_D_nm']==delta]
                def work(name,problem=problem,prior=prior):
                    call=predictor(model,store,name,out)
                    def persist(kind,index,doc):atomic_json(out/'profiles'/name/kind/f'{index:04d}.json',doc)
                    return solve_profile(problem,call,lambda:store.counts()[name],persist,prior_witnesses=prior)
                result=task(store,problem.task_id,'FIXED_D_DESIGN',400,out,signature,work)
                profiles.append(result);block.append(result)
                atomic_json(out/'profiles'/problem.task_id/'summary.json',result)
            pooled=pool_profiles(block,gd,c0,d['theta']);pools.append(pooled)
            atomic_json(out/'pooled'/f'{group}_{"m5" if delta<0 else "p5"}.json',pooled)
    atomic_json(out/'profiles_all.json',profiles);atomic_json(out/'pooled_all.json',pools)
    def final(name):
        call=predictor(model,store,name,out);checks=[]
        all_witnesses=[p['best'] for p in profiles]
        for p in pools:all_witnesses.extend(p['common_pool_minima'].values())
        for r in all_witnesses:
            c=call(r['theta']);require(np.allclose(c,r['C'],rtol=1e-10,atol=1e-12),'FINAL_WITNESS_PIXELS')
            checks.append(dict(theta=r['theta'],checked=True))
        for group in GROUPS:
            d=contexts[group];c=call(d['theta']);require(np.allclose(c,d['predictions'][d['base_index']]['C'],rtol=1e-10,atol=1e-12),'FINAL_ANCHOR')
        return dict(logical_witness_checks=len(checks),anchor_checks=3)
    task(store,'FINAL_VERIFY','FINAL_VERIFY',60,out,signature,final)
    partial=sum(1 for p in profiles if p['search_state']=='PARTIAL_SEARCH')
    status=dict(execution_state='FINISHED_WITH_PARTIAL_SEARCH' if partial else 'FINISHED',
        profiles=24,common_pools=6,partial_search_tasks=partial,actual_calls=store.counts(),
        conditional_anchor_design=True,no_experimental_height_observation=True,
        globally_certified_minima=False,calibrated_confidence_intervals=False,
        all_reportable_D_null=True,EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=False)
    atomic_json(out/'status.json',status)
    return status


def verify(repo,out):
    own_receipt(Path(__file__).resolve().parent.parent,out)
    pre=read(out/'preflight.json');require(lock_sources(repo)==pre['source_lock'],'SOURCE_CHANGED')
    ledger=ledger_check(out,plan_id='v164',require_success=False)
    require(ledger['meta']==dict(plan_id='v164',phases=PHASES,total=10000),'LEDGER_PLAN_CHANGED')
    profiles=read(out/'profiles_all.json');require(len(profiles)==24,'PROFILE_COUNT')
    expected={(g,t,d) for g in GROUPS for t in DELTAS for d in DESIGNS}
    require({(p['group'],p['delta_D_nm'],p['design']) for p in profiles}==expected,'PROFILE_KEYS')
    expected_task_ids={'LOADER_1','BINDING','FINAL_VERIFY'}
    for r in profiles:
        task_id=f"PROFILE_{r['group']}_{'m5' if r['delta_D_nm']<0 else 'p5'}_{r['design']}"
        expected_task_ids.add(task_id)
        require(canonical(read(out/'tasks'/task_id/'result.json')['payload'])==canonical(r),'PROFILE_NOT_BOUND_TO_SEALED_TASK')
        d=read(out/f'source_context/{r["group"]}.json')['diagnostic'];gd=GlsData.from_frames(d['frame_Y'],d['frame_V']);c0=d['predictions'][d['base_index']]['C']
        require(r['fixed_D_nm']==d['theta'][0]+r['delta_D_nm'],'FIXED_D_SUMMARY')
        for k in ('best','linear_witness'):
            row=r[k];require(row['theta'][0]==r['fixed_D_nm'],'FIXED_D_RESULT')
            score=evaluate(row['theta'],row['C'],anchor=d['theta'],c0=c0,data=gd,design=r['design'])
            for name,value in score.items():compare_nested(value,row[name],name)
        require(r['best']['design_distance_squared']<=r['linear_witness']['design_distance_squared']+1e-9,'LOST_WITNESS')
        require(len(r['starts'])==2 and all(x['actual_calls']<=200 for x in r['starts']),'START_BUDGET')
        actual_task=next(t for t in ledger['tasks'] if t['task']==task_id)
        require(actual_task['cap']==400 and actual_task['used']==r['actual_new_calls']==sum(x['actual_calls'] for x in r['starts']),'PROFILE_CALL_ACCOUNTING')
    require({r['task'] for r in ledger['tasks']}==expected_task_ids,'TASK_SET_MISMATCH')
    pools=read(out/'pooled_all.json');require(len(pools)==6,'POOL_COUNT')
    for p in pools:
        d=read(out/f'source_context/{p["group"]}.json')['diagnostic'];gd=GlsData.from_frames(d['frame_Y'],d['frame_V']);c0=d['predictions'][d['base_index']]['C']
        block=[r for r in profiles if r['group']==p['group'] and r['fixed_D_nm']==p['fixed_D_nm']]
        compare_nested(pool_profiles(block,gd,c0,d['theta']),p)
    final_predictions=[read(p) for p in (out/'tasks/FINAL_VERIFY/predictions').glob('*.json')]
    actual_final={tuple(p['theta']):np.asarray(p['C']) for p in final_predictions}
    requested={}
    for r in profiles:requested[tuple(r['best']['theta'])]=r['best']['C']
    for pooled in pools:
        for r in pooled['common_pool_minima'].values():requested[tuple(r['theta'])]=r['C']
    for name in GROUPS:
        d=read(out/f'source_context/{name}.json')['diagnostic']
        requested[tuple(d['theta'])]=d['predictions'][d['base_index']]['C']
    require(set(actual_final)==set(requested),'FINAL_VERIFICATION_POINT_SET')
    require(all(np.allclose(actual_final[t],c,rtol=1e-10,atol=1e-12) for t,c in requested.items()),'FINAL_C_ARRAY_BINDING')
    atomic_json(out/'verification.json',dict(status='CONDITIONAL_ATTAINABLE_BOUNDS_VERIFIED_NOT_GLOBAL_OR_EXPERIMENTAL',ledger=ledger,new_model_calls=0,all_reportable_D_null=True))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--mode',choices=('preflight','execute','verify'),required=True)
    a=ap.parse_args();repo=a.repo.resolve();out=repo/'results/v164';out.mkdir(parents=True,exist_ok=True)
    try:
        {'preflight':preflight,'execute':execute,'verify':verify}[a.mode](repo,out);return 0
    except Exception as exc:
        i=0
        while (out/f'failures/{i:03d}.json').exists():i+=1
        atomic_json(out/f'failures/{i:03d}.json',dict(mode=a.mode,error=repr(exc),traceback=traceback.format_exc(),reportable_D=None))
        print(traceback.format_exc(),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
