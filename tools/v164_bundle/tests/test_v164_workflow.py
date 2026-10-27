import hashlib,json,sys,shutil
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
import v164_run as run
from v164_profile_core import GROUPS
from v152_gls_core import GlsData
from v157_height_design import plan_paths,evaluate_path
from v152_budget_store import BudgetStore,CountedPredictor,atomic_json
from v164_io import ledger_check


def make_workflow(tmp_path,monkeypatch):
    repo=tmp_path/'repo';repo.mkdir();out=repo/'results/v164';out.mkdir(parents=True)
    anchor=np.array([120.,450.,0.,0.])
    def image(t):
        d,h,x,y=np.asarray(t)-anchor;c=np.zeros(169);c[:4]=[d+h+.05*d*d,.08*d,x,y]
        return c.reshape(13,13)
    j=np.zeros((169,4));j[:4]=[[1,1,0,0],[.08,0,0,0],[0,0,1,0],[0,0,0,1]]
    gd=GlsData.from_frames(np.zeros((3,13,13)),np.ones((3,13,13)))
    diag=dict(theta=anchor.tolist(),frame_Y=gd.y.tolist(),frame_V=gd.variance.tolist(),
              predictions=[dict(C=image(anchor).tolist(),theta=anchor.tolist())],base_index=0,whitened_J_fine=(np.sqrt(3)*j).tolist())
    contexts={name:diag for name in GROUPS};rows={}
    for group in GROUPS:
        rows[group]=[evaluate_path(r,c0=image(anchor),data=gd,jw=diag['whitened_J_fine'],predict=image,persist=lambda _:None) for r in plan_paths(anchor,diag['whitened_J_fine'])]
        atomic_json(out/f'source_context/{group}.json',dict(diagnostic=diag))
    def preflight(repo,out):
        atomic_json(out/'preflight.json',dict(source_lock={}))
        return dict(scope='SYNTHETIC_TEST'),contexts,rows
    def construct(repo,store,out,signature):
        run.task(store,'LOADER_1','MODEL_BINDING',100,out,signature,lambda _:dict(synthetic_loader=True))
        return SimpleNamespace(model_id=run.MODEL,forward=lambda t:SimpleNamespace(score_C=image(t)))
    monkeypatch.setattr(run,'preflight',preflight);monkeypatch.setattr(run,'construct',construct)
    monkeypatch.setattr(run,'own_receipt',lambda *a:None);monkeypatch.setattr(run,'lock_sources',lambda *a:{})
    return repo,out


@pytest.fixture(scope='module')
def completed_workflow(tmp_path_factory):
    # One genuine 24-task execution; mutation tests copy immutable artifacts.
    # This avoids rerunning an identical synthetic optimization four times.
    base=tmp_path_factory.mktemp('v164_complete')
    with pytest.MonkeyPatch.context() as mp:
        repo,out=make_workflow(base,mp)
        status=run.execute(repo,out)
        run.verify(repo,out)
    return repo,out,status


def clone_finished(tmp_path,monkeypatch,completed_workflow):
    source,_,_=completed_workflow
    repo=tmp_path/'repo';shutil.copytree(source,repo);out=repo/'results/v164'
    monkeypatch.setattr(run,'own_receipt',lambda *a:None)
    monkeypatch.setattr(run,'lock_sources',lambda *a:{})
    return repo,out


def test_full_24_profile_execute_and_verify_synthetic(completed_workflow):
    repo,out,status=completed_workflow
    assert status['profiles']==24 and status['common_pools']==6
    assert status['all_reportable_D_null']
    receipt=json.loads((out/'verification.json').read_text())
    assert receipt['new_model_calls']==0
    assert receipt['ledger']['total_used']<=10000
    assert len(receipt['ledger']['tasks'])==27


def test_execute_refuses_existing_ledger_without_erasing(tmp_path,monkeypatch):
    repo,out=make_workflow(tmp_path,monkeypatch)
    p=out/'logs/v164_budget.sqlite';p.parent.mkdir();p.write_bytes(b'PRESERVE')
    with pytest.raises(ValueError,match='EXISTING_LEDGER'):run.execute(repo,out)
    assert p.read_bytes()==b'PRESERVE'


def test_verify_rejects_changed_design_distance(tmp_path,monkeypatch,completed_workflow):
    repo,out=clone_finished(tmp_path,monkeypatch,completed_workflow)
    p=out/'profiles_all.json';doc=json.loads(p.read_text());doc[0]['best']['design_distance_squared']+=1
    atomic_json(p,doc)
    with pytest.raises(ValueError):run.verify(repo,out)


def test_verify_rejects_missing_profile(tmp_path,monkeypatch,completed_workflow):
    repo,out=clone_finished(tmp_path,monkeypatch,completed_workflow)
    p=out/'profiles_all.json';doc=json.loads(p.read_text());atomic_json(p,doc[:-1])
    with pytest.raises(ValueError,match='PROFILE_COUNT'):run.verify(repo,out)


def test_model_error_recorded_and_not_forged_success(tmp_path):
    db=BudgetStore(tmp_path/'budget.sqlite','test',{'X':2},2)
    db.reserve('t','signature','X',2,'owner')
    def model(t):raise RuntimeError('failure')
    call=CountedPredictor(model,db,'t','owner')
    with pytest.raises(RuntimeError):call([120,450,0,0])
    assert db.counts()['t']==1
    with db.db() as c:assert c.execute('select state from attempts').fetchone()[0]=='MODEL_ERROR'


def test_verify_requires_full_final_point_set(tmp_path,monkeypatch,completed_workflow):
    repo,out=clone_finished(tmp_path,monkeypatch,completed_workflow)
    # Seal/hash mismatch itself is enough to reject a missing real confirmation.
    next((out/'tasks/FINAL_VERIFY/predictions').glob('*.json')).unlink()
    with pytest.raises((ValueError,FileNotFoundError)):run.verify(repo,out)


def test_budget_errors_stop_model_before_extra_call(tmp_path):
    from v152_gls_core import CallCapReached
    store=BudgetStore(tmp_path/'b.sqlite','t',{'x':1},1);store.reserve('t','s','x',1,'o')
    calls=[]
    call=CountedPredictor(lambda t:(calls.append(t) or np.zeros((13,13))),store,'t','o')
    call([120,450,0,0])
    with pytest.raises(CallCapReached):call([121,450,0,0])
    assert len(calls)==1
