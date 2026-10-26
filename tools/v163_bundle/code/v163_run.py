"""V163 single entry. No fits, Jacobian batches, renders, noise draws or truth files.
Real F2c/source integration remains to be validated on the workstation.
"""
from __future__ import annotations
import argparse, contextlib, hashlib, importlib, json, os, sqlite3, subprocess, sys, traceback
from pathlib import Path
import numpy as np
from v152_budget_store import BudgetStore, CountedPredictor, atomic_json, canonical
from v152_gls_core import GlsData, check_theta
from v156_candidate_guard import read_v152_pool, select_rescored_complete, EXPECTED
from v157_height_design import plan_paths, evaluate_path
from v163_design import complete_design, audit_diagnostic, probe_eligible
from audit_v156_readonly import audit as audit156, archive as audit_archive
from v163_semantics import verify_kernel_identity, group_camera_events, validate_probe_plan
from audit_v161_readonly import audit_zip as audit161_zip
from v163_design_reuse import check_reference
from v163_source_bridge import bridge_from_git, verify_runtime_pins, copy_verified_context
from v163_deployment import verify_locked_inputs, verify_test_receipt, validate_installed_layout, bundle_files

BASE='71333a9f193d00012972e8fd6c188805c7a6b18e'
PHASES={'REPAIR_AND_ANCHOR':260,'NONLINEAR_PROBES':120,'FINAL_VERIFY':120}
PROBES={(100000,'ANON_02'),(100000,'ANON_03'),(100000,'ANON_04')}
OWNER='v163-single-process'


def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha_bytes(x): return hashlib.sha256(x).hexdigest()
def sha_file(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def sha_array(a):return sha_bytes(np.ascontiguousarray(a,dtype=np.float64).tobytes())
def close_q(x,y): return abs(float(x)-float(y))<=max(1e-8,1e-10*abs(float(y)))
def same_c(a,b):return np.allclose(a,b,rtol=1e-10,atol=1e-12)
def group_name(k):return f'{k[0]}_{k[1]}'
def require(x,msg):
    if not x:raise ValueError(msg)


def git(repo,*args):
    r=subprocess.run(['git','-C',str(repo),*args],capture_output=True,check=True)
    return r.stdout


def check_config(cfg):
    require(cfg.get('base_commit')==BASE,'BASE_CHANGED')
    require(cfg.get('phases')==PHASES and cfg.get('total')==500,'BUDGET_PLAN_CHANGED')
    require(cfg.get('probe_groups')==[[100000,'ANON_02'],[100000,'ANON_03'],[100000,'ANON_04']], 'PROBE_CASES_CHANGED')
    require(cfg.get('mode')=='COMPLETE_V157_NOT_NEW_FITTING', 'SCOPE_CHANGED')
    require(cfg.get('designs_per_group')==17 and cfg.get('jacobian_scales')==['coarse','fine'],'DESIGN_GRID_CHANGED')
    require(cfg.get('svd_rtols')==[1e-8,1e-10,1e-12] and cfg.get('sigma_nm')==[1,2,5,10,20,50,100],'NUMERICAL_GRID_CHANGED')
    require(cfg.get('probe_designs')==['free_hxy','exact_height','height_sigma10'] and cfg.get('delta_D_nm')==[-5,-2,-1,-.5,.5,1,2,5],'PROBE_GRID_CHANGED')
    require(all(cfg.get(k)==0 for k in ['new_BEM','new_render','new_exposure','new_noise_draw','new_fit','new_fixed_D_optimization','new_Jacobian_batch','new_second_focus']),'FORBIDDEN_WORK_ENABLED')


def verify_locked_tree(repo):
    return verify_locked_inputs(Path(repo), BASE)


def check_test_receipt(repo,out):
    root=validate_installed_layout(Path(__file__).resolve(), Path(repo))
    return verify_test_receipt(root, Path(out)/'workstation_tests')


def preflight(repo,cfg,out):
    check_config(cfg)
    check_test_receipt(repo,out)
    kernel_checked=verify_kernel_identity(Path(__file__).resolve().parent.parent)
    audited161=audit161_zip(repo/'results/v161/iscat_v161_return.zip')
    atomic_json(out/'audit/v161_archive_and_errors.json',audited161)
    root=(repo/'results/v163').resolve()
    require(out.resolve()==root,'OUTPUT_MUST_BE_RESULTS_V163')
    locked=verify_locked_tree(repo)
    source_bridge=bridge_from_git(repo,BASE)
    runtime_pins=verify_runtime_pins(repo)
    atomic_json(out/'audit/source_bridge.json',source_bridge)
    atomic_json(out/'audit/runtime_pin_consistency.json',runtime_pins)
    code_commit=git(repo,'rev-parse','HEAD').decode().strip()
    require(git(repo,'rev-parse',code_commit+':tools/v133_recover_M.py').decode().strip()==source_bridge['runtime_git_blob'],'SOURCE_BRIDGE_NOT_COMMITTED')
    git(repo,'merge-base','--is-ancestor',BASE,code_commit)
    bundle=Path(__file__).resolve().parent.parent
    for rel_in_bundle in bundle_files(bundle):
        p=bundle/rel_in_bundle
        rel=p.relative_to(repo).as_posix()
        committed=git(repo,'rev-parse',f'{code_commit}:{rel}').decode().strip()
        raw=p.read_bytes();actual=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        require(actual==committed,'UNCOMMITTED_EXECUTION_CODE:'+rel)
    report=audit156(repo)
    require(report.get('groups_complete') and not report.get('failures'),'SAVED_V156_AUDIT_FAILED')
    ar156=report['archive']
    require(not ar156.get('crc_bad_member') and not ar156.get('duplicates') and not ar156.get('manifest_failures') and not ar156.get('unlisted_files'),'V156_ARCHIVE_INTEGRITY_FAILED')
    require(all(r.get('integrity_check')=='ok' and not r.get('task_over_cap') and r.get('task_attempt_count_matches',False) for r in report['ledgers']),'V156_LEDGER_STRUCTURAL_CHECK_FAILED')
    ar=audit_archive(repo/'results/v157/iscat_v157_return.zip')
    require(not ar.get('crc_bad_member') and not ar.get('duplicates') and not ar.get('manifest_failures') and not ar.get('unlisted_files'), 'V157_ARCHIVE_INTEGRITY_FAILED')
    ar158=audit_archive(repo/'results/v158/iscat_v158_return.zip')
    require(not ar158.get('crc_bad_member') and not ar158.get('duplicates') and not ar158.get('manifest_failures') and not ar158.get('unlisted_files'), 'V158_ARCHIVE_INTEGRITY_FAILED')
    pool=read_v152_pool(read(repo/'results/v152/all_results.json'),'6d2db46d52509bd6987726dea211781cfa1b4127')
    designs={};saved={}
    for k in sorted(EXPECTED):
        d=read(repo/f'results/v156/joint/{group_name(k)}/result.json')['diagnostic']
        require(any(np.array_equal(r['theta'],d['theta']) for r in pool[k]),'SAVED_ANCHOR_NOT_IN_POOL')
        designs[group_name(k)]=complete_design(d);saved[k]=d
    context={}
    for k in sorted(EXPECTED):
        name=group_name(k);rel=f'results/v156/joint/{name}/result.json'
        context[name]=copy_verified_context(repo/rel,out/f'source_context/v156/{name}.json',locked[rel]['sha256'])
    atomic_json(out/'source_context/manifest.json',context)
    reuse=check_reference(bundle,designs)
    atomic_json(out/'audit/v162_algebra_reuse.json',reuse)
    receipt=dict(scope='SAVED_ARRAY_AND_SOURCE_CHECKS_NOT_NEW_OPTICAL_REPLAY',base_commit=BASE,
                 source_lock=locked,source_bridge=source_bridge,runtime_pins=runtime_pins,v156_readonly=report,v157_archive=ar,v158_archive=ar158,
                 approved_kernel=kernel_checked,v161_history_audit=audited161,
                 group_count=len(saved),designs_per_group=17,n_model_calls=0,
                 driver_sha256=sha_file(__file__),execution_code_commit=code_commit)
    atomic_json(out/'preflight.json',receipt)
    atomic_json(out/'design/saved_array_designs.json',designs)
    return receipt,pool,saved,designs


def run_task(store,name,phase,cap,out,signature,work):
    state=store.reserve(name,signature,phase,cap,OWNER)
    require(state=='RUNNING' and store.counts()[name]==0,'EXISTING_TASK_REQUIRES_FORENSIC_RECOVERY')
    path=out/'tasks'/name/'result.json'
    try:
        payload=work(name)
        doc=dict(signature=signature,execution_state='FINISHED',payload=payload,
                 actual_model_forward_attempts=store.counts()[name])
        atomic_json(path,doc);store.seal(name,OWNER,'FINISHED',path)
        return payload
    except Exception as exc:
        doc=dict(signature=signature,execution_state='FAILED',error=repr(exc),
                 traceback=traceback.format_exc(),actual_model_forward_attempts=store.counts()[name],reportable_D=None)
        atomic_json(path,doc)
        # An unknown CHARGED call must remain unsealed, never changed to zero.
        try:store.seal(name,OWNER,'FAILED',path)
        except Exception as seal_error:atomic_json(path.with_name('seal_failure.json'),dict(error=repr(seal_error)))
        raise


@contextlib.contextmanager
def count_loader(cls,store,task):
    original=cls.forward
    def counted(instance,theta):
        seq=store.charge(task,OWNER,theta)
        try:
            value=original(instance,theta)
            c=np.asarray(value.score_C,float)
            require(c.shape==(13,13) and np.isfinite(c).all(),'BAD_LOADER_C')
        except Exception as exc:
            store.returned(task,seq,'MODEL_ERROR',dict(kind='F2_LOADER',error=repr(exc),traceback=traceback.format_exc()));raise
        store.returned(task,seq,'RETURNED',dict(kind='F2_LOADER',C_sha256=sha_array(c)))
        return value
    cls.forward=counted
    try:yield
    finally:cls.forward=original


def import_repo(repo,name):
    module=importlib.import_module(name)
    require(Path(module.__file__).resolve()==(repo/'tools'/f'{name}.py').resolve(),'WRONG_IMPORTED_MODULE:'+name)
    return module


def construct_counted(repo,store,out,signature):
    sys.path.insert(0,str(repo/'tools'))
    core=import_repo(repo,'field_forward_reference')
    runtime=import_repo(repo,'v146_runtime')
    cfg146=read(repo/'config/v146_science_config.json')
    holder={}
    def work(task):
        with count_loader(core.FieldForward,store,task):
            holder['model']=runtime.construct_bound(repo,cfg146)
        return dict(model_id=holder['model'].model_id,kind='F2_LOADER')
    run_task(store,'LOADER_1','REPAIR_AND_ANCHOR',100,out,signature,work)
    return holder['model']


def recorded_predictor(model,store,task,out):
    counter=CountedPredictor(lambda theta:model.forward(tuple(float(v) for v in theta)).score_C,store,task,OWNER)
    cache={}
    def predict(theta):
        t=check_theta(theta);key=tuple(t.tolist())
        if key in cache:return cache[key].copy()
        c=counter(t)
        seq=store.counts()[task]
        atomic_json(out/'tasks'/task/'predictions'/f'{seq:04d}.json',
                    dict(theta=t.tolist(),C=c.tolist(),C_sha256=sha_array(c),task=task,seq=seq))
        cache[key]=c.copy()
        return c
    return predict


def score_anchors(repo,model,store,out,pool,saved,signature):
    cam=import_repo(repo,'v146_fit_saved_camera')
    cfg=read(repo/'config/v146_science_config.json')
    require(sha_file(repo/cfg['inputs']['camera_h5'])==cfg['frozen']['camera_h5_sha256'],'CAMERA_HASH_CHANGED')
    events=cam.camera_events(repo/cfg['inputs']['camera_h5'],repo/cfg['inputs']['camera_root'],[1000,10000,100000],2.)
    require(len(events)==36,'EXPECTED_36_EVENTS')
    grouped,byid=group_camera_events(events)
    data={k:GlsData.from_frames([e['Y'] for e in evs],[e['V'] for e in evs]) for k,evs in grouped.items()}
    def work(task):
        predict=recorded_predictor(model,store,task,out);replay=[];registry=[];selected={}
        for ev in events:
            old=read(repo/'results/v146/camera_fits/events'/f'{ev["event_id"]}.json')['fit']['best']
            th=check_theta(old['theta']);c=predict(th)
            score=GlsData.from_frames(ev['Y'],ev['V']).score(c)
            r=dict(event_id=ev['event_id'],theta=th.tolist(),old_Q=old['Q'],**score)
            atomic_json(out/'replay'/f'{ev["event_id"]}.json',r)
            require(close_q(score['Q_joint'],old['Q']),'OLD_Q_REGRESSION_FAILED:'+ev['event_id']);replay.append(r)
        e1=read(repo/'results/v153/all_results.json')['e1_regression']
        require(len(e1)==6,'EXPECTED_SIX_E1')
        for row in e1:
            ev=byid[row['event_id']];c=predict(row['best_theta'])
            score=GlsData.from_frames(ev['Y'],ev['V']).score(c)
            require(close_q(score['Q_joint'],2*row['best_Q']),'E1_HALF_Q_RECHECK_FAILED')
            atomic_json(out/'e1'/f'{ev["event_id"]}.json',dict(theta=row['best_theta'],historical_half_Q=row['best_Q'],**score))
        for k in sorted(EXPECTED):
            gd=data[k];d=saved[k]
            require(np.array_equal(gd.y,np.asarray(d['frame_Y'])) and np.array_equal(gd.variance,np.asarray(d['frame_V'])), 'SAVED_OBSERVATION_MISMATCH')
            rows=[]
            for src in pool[k]:
                c=predict(src['theta']);score=gd.score(c)
                r={**{x:v for x,v in src.items() if x!='historic_record'},'B':k[0],'anon':k[1],
                   'candidate_D':src['theta'][0], 'C':c.tolist(),'C_sha256':sha_array(c),**score,
                   'model_id':model.model_id,'observation_identity':sha_array(gd.y),
                   'variance_identity':sha_array(gd.variance),
                   'ordered_event_ids':[e['event_id'] for e in grouped[k]]}
                atomic_json(out/'rescored'/f'{group_name(k)}_{src["start_index"]}.json',r);rows.append(r);registry.append(r)
            winner=select_rescored_complete(rows)
            candidates=[r for r in rows if np.array_equal(r['theta'],d['theta'])]
            require(bool(candidates),'OLD_ANCHOR_NOT_IN_RESCORED_POOL')
            anchor=min(candidates,key=lambda r:r['source_record_id'])
            require(close_q(anchor['Q_joint'],winner['Q_joint']),'KNOWN_LOWER_Q_WITNESS_REQUIRES_NEW_REVIEW')
            c0=np.asarray(d['predictions'][d['base_index']]['C'])
            require(same_c(anchor['C'],c0) and close_q(anchor['Q_joint'],d['score']['Q_joint']), 'ANCHOR_PIXEL_OR_Q_MISMATCH')
            selected[group_name(k)]={**anchor,'selection':'V156_ANCHOR_NUMERICALLY_TIED_WITH_CURRENT_MINIMUM',
                                     'current_minimum_source_record_id':winner['source_record_id']}
        require(len(registry)==72 and len(selected)==12,'INCOMPLETE_ANCHOR_STAGE')
        return dict(replay_count=len(replay),registry=registry,selected=selected)
    result=run_task(store,'ANCHORS','REPAIR_AND_ANCHOR',126,out,signature,work)
    atomic_json(out/'selected_candidates_12.json',result['selected'])
    return result,data


def execute(repo,cfg,out):
    db=out/'logs/v163_budget.sqlite'
    require(not db.exists(),'EXISTING_LEDGER_USE_READONLY_VERIFY_OR_FORENSICS_NO_AUTO_REEXECUTION')
    require(not any((out/'tasks').glob('*/result.json')),'EVIDENCE_WITHOUT_LEDGER_REQUIRES_FORENSICS')
    pre,pool,saved,designs=preflight(repo,cfg,out)
    # Fixed source/config/driver identity is included in every task signature.
    signature=sha_bytes(canonical(dict(config=cfg,source_lock=pre['source_lock'],
                                      bundle_code={p.name:sha_file(p) for p in sorted(Path(__file__).parent.glob('*.py'))})).encode())
    store=BudgetStore(db,'v163',PHASES,500)
    model=construct_counted(repo,store,out,signature)
    anchors,data=score_anchors(repo,model,store,out,pool,saved,signature)
    probe_docs={}; blocked=[]
    for k in sorted(PROBES):
        name=group_name(k);design=designs[name];d=saved[k]
        if not probe_eligible(design):
            blocked.append(name);atomic_json(out/'probes'/name/'blocked.json',dict(state='BLOCKED_LOCAL_NUMERICS',qualification=design['qualification']));continue
        rows=plan_paths(d['theta'],np.asarray(d['whitened_J_fine']))
        validate_probe_plan(k,d['theta'],rows)
        atomic_json(out/'probes'/name/'plan.json',rows)
        def work(task,k=k,name=name,d=d,rows=rows):
            predict=recorded_predictor(model,store,task,out);rr=[]
            for i,row in enumerate(rows):
                path=out/'probes'/name/f'{i:02d}.json'
                rec=evaluate_path(row,c0=d['predictions'][d['base_index']]['C'],data=data[k],
                                  jw=d['whitened_J_fine'],predict=predict,persist=lambda x:atomic_json(path,x))
                if rec['state']!='EVALUATED':atomic_json(path,rec)
                rr.append(rec)
            return rr
        probe_docs[name]=run_task(store,'PROBE_'+name,'NONLINEAR_PROBES',40,out,signature,work)
    def final_work(task):
        predict=recorded_predictor(model,store,task,out);checks=[]
        for k in sorted(EXPECTED):
            d=saved[k];c=predict(d['theta']);ref=d['predictions'][d['base_index']]['C']
            require(same_c(c,ref),'FINAL_BASE_PIXEL_MISMATCH')
            checks.append(dict(group=group_name(k),kind='base',C_sha256=sha_array(c),**data[k].score(c)))
        # Fixed subset: all six |delta_D|=5 endpoints for ANON_02, no result-based selection.
        for r in probe_docs.get('100000_ANON_02',[]):
            if r['state']=='EVALUATED' and abs(r['delta_D_nm'])==5:
                c=predict(r['theta']);require(same_c(c,r['C']),'FINAL_ENDPOINT_PIXEL_MISMATCH')
                checks.append(dict(group='100000_ANON_02',kind=r['path'],delta=r['delta_D_nm'],C_sha256=sha_array(c)))
        return checks
    run_task(store,'FINAL_VERIFY','FINAL_VERIFY',20,out,signature,final_work)
    states={name:{'evaluated':sum(r['state']=='EVALUATED' for r in rows),
                  'skipped':sum(r['state']=='SKIPPED_OUT_OF_DOMAIN' for r in rows),
                  'linear_points':sum(1 for r in rows if r['state']=='EVALUATED' and r['relative_linearization_error'] is not None and r['relative_linearization_error']<=.05)} for name,rows in probe_docs.items()}
    status=dict(execution_state='PARTIAL_BLOCKED' if blocked else 'FINISHED',base_commit=BASE,
                scope='CONDITIONAL_LOCAL_AND_PREDECLARED_PATH_DIAGNOSTICS',
                candidates_verified=12,design_groups=12,designs_per_group=17,
                design_evaluations_per_group=102,blocked_probe_groups=blocked,
                probes=states,model_attempts_by_task=store.counts(),
                all_reportable_D_null=True,EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=False,
                global_uniqueness_certified=False,unperformed_new_fits=0)
    atomic_json(out/'status.json',status)
    return status


def verify_output_completeness(repo,out):
    """Reject missing tasks/files, including a falsely empty probe directory."""
    st=read(out/'status.json')
    require(st.get('execution_state') in ('FINISHED','PARTIAL_BLOCKED'),'EXECUTION_NOT_FINISHED')
    require(st.get('all_reportable_D_null') is True and st.get('EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED') is False,'UNQUALIFIED_STATUS')
    selected=read(out/'selected_candidates_12.json')
    require(set(selected)=={group_name(k) for k in EXPECTED},'SELECTED_GROUP_SET_INCOMPLETE')
    require(len(list((out/'replay').glob('*.json')))==36,'REPLAY_FILE_COUNT')
    require(len(list((out/'e1').glob('*.json')))==6,'E1_FILE_COUNT')
    require(len(list((out/'rescored').glob('*.json')))==72,'RESCORED_FILE_COUNT')
    anchor=read(out/'tasks/ANCHORS/result.json')['payload']
    require(anchor.get('replay_count')==36 and len(anchor.get('registry',[]))==72,'ANCHOR_PAYLOAD_COUNT')
    require(canonical(anchor['selected'])==canonical(selected),'SELECTED_PAYLOAD_MISMATCH')
    expected_tasks={'LOADER_1','ANCHORS','FINAL_VERIFY'}
    expected_blocked=[];expected_probe_states={}
    designs=read(out/'design/saved_array_designs.json')
    require(set(designs)==set(selected),'DESIGN_GROUP_SET')
    for key in sorted(PROBES):
        name=group_name(key);folder=out/'probes'/name
        if not probe_eligible(designs[name]):
            expected_blocked.append(name)
            require((folder/'blocked.json').is_file(),'MISSING_BLOCKED_RECORD')
            require(not list(folder.glob('[0-9][0-9].json')),'BLOCKED_GROUP_HAS_PROBES')
            continue
        expected_tasks.add('PROBE_'+name)
        require({p.stem for p in folder.glob('[0-9][0-9].json')}=={f'{i:02d}' for i in range(24)},'MISSING_OR_EXTRA_PROBE_FILES')
        d=read(repo/f'results/v156/joint/{name}/result.json')['diagnostic']
        plan=plan_paths(d['theta'],d['whitened_J_fine'])
        validate_probe_plan(key,d['theta'],plan)
        require(canonical(read(folder/'plan.json'))==canonical(plan),'PROBE_PLAN_CHANGED')
        returned=[]
        for i,pr in enumerate(plan):
            row=read(folder/f'{i:02d}.json');returned.append(row)
            if pr['state']=='PLANNED':
                require(row['state']=='EVALUATED','PLANNED_PROBE_NOT_EVALUATED')
            else:require(canonical(pr)==canonical(row),'SKIP_RECORD_CHANGED')
        payload=read(out/'tasks'/('PROBE_'+name)/'result.json')['payload']
        require(canonical(payload)==canonical(returned),'PROBE_TASK_FILE_MISMATCH')
        expected_probe_states[name]={'evaluated':sum(x['state']=='EVALUATED' for x in returned),
          'skipped':sum(x['state']=='SKIPPED_OUT_OF_DOMAIN' for x in returned),
          'linear_points':sum(1 for x in returned if x['state']=='EVALUATED' and x['relative_linearization_error'] is not None and x['relative_linearization_error']<=.05)}
    require({p.parent.name for p in (out/'tasks').glob('*/result.json')}==expected_tasks,'TASK_SET_INCOMPLETE')
    require(sorted(st.get('blocked_probe_groups',[]))==sorted(expected_blocked),'BLOCKED_STATUS_MISMATCH')
    require(canonical(st.get('probes'))==canonical(expected_probe_states),'PROBE_STATUS_MISMATCH')
    require(st['execution_state']==('PARTIAL_BLOCKED' if expected_blocked else 'FINISHED'),'GLOBAL_STATE_MISMATCH')
    return dict(expected_tasks=sorted(expected_tasks),probe_states=expected_probe_states)


def verify_saved(repo,cfg,out):
    check_config(cfg)
    locked=verify_locked_tree(repo)
    pre=read(out/'preflight.json')
    require(locked==pre['source_lock'],'SOURCE_CHANGED_AFTER_RUN')
    require(pre['driver_sha256']==sha_file(__file__),'DRIVER_CHANGED_AFTER_RUN')
    check_test_receipt(repo,out)
    verify_output_completeness(repo,out)
    status=read(out/'status.json');db=out/'logs/v163_budget.sqlite'
    con=sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True)
    try:
        require(con.execute('PRAGMA integrity_check').fetchone()[0]=='ok','SQLITE_FAILED')
        meta=json.loads(con.execute('SELECT value FROM metadata WHERE id=1').fetchone()[0])
        require(meta==dict(plan_id='v163',phases=PHASES,total=500),'LEDGER_PLAN_MISMATCH')
        tasks=con.execute('SELECT id,signature,phase,cap,used,state,result_path,result_sha FROM tasks').fetchall()
        totals={p:0 for p in PHASES};reservations={p:0 for p in PHASES}
        for task,sig,phase,cap,used,state,path,digest in tasks:
            require(phase in PHASES and used<=cap,'TASK_BUDGET_VIOLATION');totals[phase]+=used;reservations[phase]+=cap
            n=con.execute('SELECT COUNT(*) FROM attempts WHERE task=?',(task,)).fetchone()[0]
            require(n==used,'ATTEMPT_COUNT_MISMATCH');require(state=='FINISHED','TASK_NOT_FINISHED')
            target=out/'tasks'/task/'result.json'
            require(target.is_file() and sha_file(target)==digest and read(target)['signature']==sig,'SEALED_RESULT_MISMATCH')
            for seq,theta,state2,detail in con.execute('SELECT seq,theta,state,detail FROM attempts WHERE task=? ORDER BY seq',(task,)):
                require(state2=='RETURNED','UNKNOWN_OR_FAILED_ATTEMPT')
                if task!='LOADER_1':
                    p=read(out/'tasks'/task/'predictions'/f'{seq:04d}.json')
                    require(np.array_equal(p['theta'],json.loads(theta)) and sha_array(p['C'])==json.loads(detail)['C_sha256'],'PREDICTION_LEDGER_MISMATCH')
        require(all(reservations[p]<=PHASES[p] for p in PHASES),'PHASE_RESERVATION_VIOLATION')
    finally:con.close()
    design=read(out/'design/saved_array_designs.json')
    for k in sorted(EXPECTED):
        d=read(repo/f'results/v156/joint/{group_name(k)}/result.json')['diagnostic']
        recomputed=complete_design(d)
        require(canonical(design[group_name(k)])==canonical(recomputed),'DESIGN_OUTPUT_MISMATCH')
    for p in sorted((out/'probes').glob('*/[0-9][0-9].json')):
        r=read(p)
        if r['state']!='EVALUATED':continue
        name=p.parent.name;d=read(repo/f'results/v156/joint/{name}/result.json')['diagnostic']
        gd=GlsData.from_frames(d['frame_Y'],d['frame_V']);planned=plan_paths(d['theta'],d['whitened_J_fine'])[int(p.stem)]
        require(np.array_equal(r['theta'],planned['theta']),'PROBE_THETA_PLAN_MISMATCH')
        require(r['path']==planned['path'] and canonical(r['design'])==canonical(planned['design']),'PROBE_DESIGN_MISMATCH')
        c0=np.asarray(d['predictions'][d['base_index']]['C']);c=np.asarray(r['C'])
        z=((c-c0)/np.sqrt(gd.vbar)).ravel();lin=np.asarray(d['whitened_J_fine'])@(np.asarray(r['theta'])-d['theta'])
        err=float(np.linalg.norm(z-lin)/np.linalg.norm(z)) if np.linalg.norm(z)>1e-12 else None
        require(close_q(float(z@z),r['image_distance_squared']),'PROBE_DISTANCE_MISMATCH')
        require(close_q(float(lin@lin),r['predicted_image_distance_squared']),'PROBE_LINEAR_DISTANCE_MISMATCH')
        dh=np.asarray(r['theta'])-np.asarray(d['theta']);cfgd=r['design']
        aux=0. if cfgd['no_height_measurement'] or cfgd['exact_height'] else float((dh[1]/cfgd['sigma_h_nm'])**2)
        require(close_q(aux,r['hypothetical_auxiliary_distance_squared']),'PROBE_AUXILIARY_MISMATCH')
        residual=((c0-gd.ybar)/np.sqrt(gd.vbar)).ravel();cross=float(2*residual@z)
        dq=gd.score(c)['Q_joint']-gd.score(c0)['Q_joint']
        require(close_q(dq,r['observed_Q_change']) and close_q(cross,r['observed_Q_cross_term']) and close_q(dq,cross+float(z@z)),'PROBE_DELTA_Q_IDENTITY_MISMATCH')
        require(err is not None and np.isclose(err,r['relative_linearization_error'],rtol=1e-9,atol=1e-12) or err is None and r['relative_linearization_error'] is None,'PROBE_ERROR_MISMATCH')
        require(close_q(gd.score(c)['Q_joint'],r['score_at_proposal']['Q_joint']),'PROBE_Q_MISMATCH')
    receipt=dict(status='SAVED_FILE_IDENTITIES_AND_DESIGNS_VERIFIED_NOT_EXPERIMENTAL_VALIDATION',
                 phase_used=totals,phase_reserved=reservations,new_model_calls=0,
                 global_uniqueness_certified=False,experimental_absolute_diameter_validated=False)
    atomic_json(out/'verification.json',receipt);return receipt


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--config',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--mode',choices=('preflight','execute','verify'),required=True)
    args=ap.parse_args();repo=args.repo.resolve();out=args.out.resolve();cfg=read(args.config)
    require(out==(repo/'results/v163').resolve(),'OUTPUT_MUST_BE_RESULTS_V163')
    out.mkdir(parents=True,exist_ok=True)
    try:
        if args.mode=='preflight':preflight(repo,cfg,out)
        elif args.mode=='execute':
            result=execute(repo,cfg,out)
            if result['execution_state']!='FINISHED':
                print('V163_PARTIAL_BLOCKED__SEE_STATUS');return 3
        else:verify_saved(repo,cfg,out)
        print('V163_STAGE_RETURNED__READ_STATUS_AND_VERIFICATION__NOT_EXPERIMENTAL_PASS')
        return 0
    except Exception as exc:
        # Unique forensic report; do not overwrite a previous failure or ledger.
        i=0
        while (out/'failures'/f'{i:03d}.json').exists():i+=1
        atomic_json(out/'failures'/f'{i:03d}.json',dict(mode=args.mode,state='BLOCKED_OR_FAILED',error=repr(exc),traceback=traceback.format_exc(),all_reportable_D_null=True))
        print('V163_BLOCKED_OR_FAILED__DEPENDENT_COMPUTATION_STOPPED',file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
