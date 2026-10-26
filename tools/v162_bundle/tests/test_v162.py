import copy,json,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from v152_gls_core import GlsData,CallCapReached
from v152_budget_store import BudgetStore
from v155_pixel_diagnostics import diagnose
from v162_design import complete_design,audit_diagnostic,probe_eligible
import v162_run as driver


def setup(theta=None):
    t=np.array([120.,450.,0.,0.] if theta is None else theta)
    j=np.zeros((169,4));j[:4,:]=np.eye(4);j[:,0]=.4*j[:,0]+np.sqrt(.84)*j[:,1]
    raw=j/np.sqrt(3)
    def pred(x):return (raw@(np.asarray(x)-t)).reshape(13,13)
    gd=GlsData.from_frames(np.zeros((3,13,13)),np.ones((3,13,13)))
    return diagnose(gd,t,pred)


def test_complete_exact17_two_scales_three_rtols():
    r=complete_design(setup())
    assert r['design_count']==17 and r['evaluation_count']==102
    assert all(len(x)==17 for x in r['designs'].values())
    assert probe_eligible(r)
    assert r['designs']['fine']['exact_height'][0]['total_coefficient_nm_minus2']==pytest.approx(1.)
    assert r['designs']['fine']['free'][0]['total_coefficient_nm_minus2']==pytest.approx(.16)


@pytest.mark.parametrize('theta',[[200,450,0,0],[120,350,0,0],[120,450,500,0],[120,450,0,-500]])
def test_boundary_cannot_be_ranked(theta):
    r=complete_design(setup(theta));assert r['boundary'];assert not probe_eligible(r)


@pytest.mark.parametrize('key',['derivative_stable','directional_check_pass','parameter_boundary'])
def test_tampered_numerical_flags_rejected(key):
    d=setup();d[key]=not d[key]
    with pytest.raises(ValueError):audit_diagnostic(d)


def test_saved_scalar_broadcast_rejected():
    d=setup();d['raw_J_fine']=np.ones((169,4)).tolist()
    with pytest.raises(ValueError):complete_design(d)


def test_saved_q_tamper_rejected():
    d=setup();d['score']['Q_joint']+=1
    with pytest.raises(ValueError):complete_design(d)


def config():return json.loads((Path(__file__).resolve().parents[1]/'config/v162_plan.json').read_text())


@pytest.mark.parametrize('key,value',[('total',501),('base_commit','main'),('mode','ONLY_DESIGN'),('phases',{'LOCAL_INFORMATION':500}),('probe_groups',[])])
def test_config_edits_fail(key,value):
    c=config();c[key]=value
    with pytest.raises(ValueError):driver.check_config(c)


def test_fixed_config_pass():driver.check_config(config())


def test_loader_calls_are_charged_before_model(tmp_path):
    store=BudgetStore(tmp_path/'b.sqlite','test',{'REPAIR_AND_ANCHOR':1},1)
    store.reserve('L','sig','REPAIR_AND_ANCHOR',1,driver.OWNER)
    seen=[]
    class Loader:
        def forward(self,t):
            assert store.counts()['L']==len(seen)+1
            seen.append(t);return SimpleNamespace(score_C=np.zeros((13,13)))
    original=Loader.forward
    with driver.count_loader(Loader,store,'L'):
        a=Loader().forward([100,450,0,0]);assert a.score_C.shape==(13,13)
        with pytest.raises(CallCapReached):Loader().forward([101,450,0,0])
    assert Loader.forward is original and len(seen)==1


def test_loader_error_and_restore(tmp_path):
    store=BudgetStore(tmp_path/'b.sqlite','test',{'REPAIR_AND_ANCHOR':1},1)
    store.reserve('L','sig','REPAIR_AND_ANCHOR',1,driver.OWNER)
    class Loader:
        def forward(self,t):raise RuntimeError('model crashed')
    orig=Loader.forward
    with pytest.raises(RuntimeError):
        with driver.count_loader(Loader,store,'L'):Loader().forward([100,450,0,0])
    assert Loader.forward is orig and store.counts()['L']==1
    with store.db() as db:assert db.execute('SELECT state FROM attempts').fetchone()[0]=='MODEL_ERROR'


def test_recorded_predictor_no_duplicate_charge_and_array_saved(tmp_path):
    store=BudgetStore(tmp_path/'b.sqlite','test',{'REPAIR_AND_ANCHOR':1},1)
    store.reserve('A','sig','REPAIR_AND_ANCHOR',1,driver.OWNER)
    model=SimpleNamespace(forward=lambda t:SimpleNamespace(score_C=np.ones((13,13))))
    p=driver.recorded_predictor(model,store,'A',tmp_path)
    p([100,450,0,0]);p([100,450,0,0])
    assert store.counts()['A']==1 and (tmp_path/'tasks/A/predictions/0001.json').is_file()


def test_failed_preflight_never_constructs_model(tmp_path,monkeypatch):
    calls=[]
    def fail(*a):raise ValueError('bad source')
    monkeypatch.setattr(driver,'preflight',fail)
    monkeypatch.setattr(driver,'construct_counted',lambda *a:calls.append(1))
    with pytest.raises(ValueError):driver.execute(tmp_path,config(),tmp_path/'out')
    assert calls==[]


def test_existing_ledger_never_removed(tmp_path):
    p=tmp_path/'out/logs/v162_budget.sqlite';p.parent.mkdir(parents=True);p.write_bytes(b'preserve')
    with pytest.raises(ValueError):driver.execute(tmp_path,config(),tmp_path/'out')
    assert p.read_bytes()==b'preserve'


def test_run_task_preserves_failure(tmp_path):
    s=BudgetStore(tmp_path/'b.sqlite','test',{'P':1},1)
    def work(_):raise OSError('disk/mock failure')
    with pytest.raises(OSError):driver.run_task(s,'X','P',1,tmp_path,'sig',work)
    d=driver.read(tmp_path/'tasks/X/result.json');assert d['execution_state']=='FAILED' and 'traceback' in d
    with s.db() as con:assert con.execute('SELECT state FROM tasks').fetchone()[0]=='FAILED'


def test_completed_task_not_reexecuted(tmp_path):
    s=BudgetStore(tmp_path/'b.sqlite','test',{'P':1},1);calls=[]
    driver.run_task(s,'X','P',1,tmp_path,'sig',lambda t:calls.append(t))
    with pytest.raises(ValueError):driver.run_task(s,'X','P',1,tmp_path,'sig',lambda t:calls.append(t))
    assert calls==['X']


def test_contrast_object_not_silently_accepted(tmp_path):
    s=BudgetStore(tmp_path/'b.sqlite','test',{'P':1},1);s.reserve('A','sig','P',1,driver.OWNER)
    model=SimpleNamespace(forward=lambda t:SimpleNamespace(score_C=SimpleNamespace()))
    with pytest.raises((TypeError,ValueError)):driver.recorded_predictor(model,s,'A',tmp_path)([100,450,0,0])
    assert s.counts()['A']==1


def test_historical_example_ratios_not_precision():
    base=.20715307676140854;free=9.073844982784648e-5;h10=.0023792764371563693
    assert base/free==pytest.approx(2282.9690958400734)
    assert h10/free==pytest.approx(26.221259473469644)
    assert h10/base==pytest.approx(.011485595456044008)
    assert np.sqrt(base/free)!=pytest.approx(base/free)
