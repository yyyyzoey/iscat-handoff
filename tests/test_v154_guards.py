from pathlib import Path
import sys, json, numpy as np, pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reference'))
from v152_gls_core import GlsData, InvariantError, CallCapReached, solve_one_start
from v152_budget_store import BudgetStore, CountedPredictor, StoreError, atomic_json
from v154_evidence_guard import (verify_returned_cost,select_saved_best,bind_prediction,
                                validate_binding,two_far_D_points,local_sensitivity)

def data(n=3):
    y=np.arange(n*169,dtype=float).reshape(n,13,13)*1e-6
    v=(np.arange(n*169,dtype=float).reshape(n,13,13)+100)*1e-7
    return GlsData.from_frames(y,v)

def source(obs='B1000_ANON_02'):
    return dict(commit='f'*40,path='results/source.json',row_id='0',model_id='FROZEN',
                observation_id=obs,variance_sha256='a'*64)

def witness(D=100.,obs='B1000_ANON_02',value=0.):
    return bind_prediction(source(obs),[D,450,0,0],np.full((13,13),value),data())

def test_cost_semantics():
    assert verify_returned_cost([3.,4.],12.5)==25.

def test_cost_wrong_factor_rejected():
    with pytest.raises(InvariantError):verify_returned_cost([3.,4.],25.)

def test_best_record_not_first():
    rs=[dict(theta=[40,450,0,0],Q_model=99),dict(theta=[100,470,10,20],Q_model=4)]
    i,r=select_saved_best(rs);assert i==1 and r['theta']==[100.,470.,10.,20.]

def test_select_preserves_finite_nonconvergence():
    i,r=select_saved_best([dict(theta=[40,450,0,0],Q_model=2,success=False)])
    assert r['success'] is False

def test_nonfinite_source_rejected():
    with pytest.raises(ValueError):select_saved_best([dict(theta=[40,450,0,0],Q_model=float('nan'))])

def test_full_theta_bind():
    r=witness();assert validate_binding(r);assert r['candidate_D']==r['theta'][0]

def test_binding_rejects_D_from_other_start():
    r=witness();r['candidate_D']=59.
    with pytest.raises(InvariantError):validate_binding(r)

def test_binding_rejects_Q_model_named_joint():
    r=witness();r['Q_joint']=r['Q_model']
    with pytest.raises(InvariantError):validate_binding(r)

def test_binding_no_reportability():
    r=witness();r['reportable_D']=100.
    with pytest.raises(InvariantError):validate_binding(r)

def test_cross_B_rejected():
    with pytest.raises(InvariantError):two_far_D_points(witness(),[witness(50.,'B10000_ANON_02')])

def test_two_distant_points():
    a=witness(100.);r=two_far_D_points(a,[witness(50.),witness(150.),witness(101.)])
    assert [z['candidate_D'] for z in r]==[50.,150.]

def test_singleton_aggregation():
    d=data(1);assert d.constant_K==0.;assert np.array_equal(d.ybar,d.y[0]);assert np.array_equal(d.vbar,d.variance[0])

def test_joint_identity_and_weights():
    d=data();c=np.full((13,13),.001);s=d.score(c)
    assert abs(s['Q_joint']-s['Q_model']-s['K'])<1e-8
    other=GlsData.from_frames(d.y,d.variance*4)
    assert np.isclose(other.score(c)['Q_joint'],s['Q_joint']/4)

def test_nonpositive_variance():
    with pytest.raises(ValueError):GlsData.from_frames(np.zeros((13,13)),np.zeros((13,13)))

def test_wrong_camera_shape():
    with pytest.raises(ValueError):GlsData.from_frames(np.zeros((17,17)),np.ones((17,17)))

def test_input_arrays_frozen():
    with pytest.raises(ValueError):data().ybar[0,0]=0.

def test_source_outside_rejected_no_clip():
    with pytest.raises(ValueError):bind_prediction(source(),[201,450,0,0],np.zeros((13,13)),data())

def fake_model():
    # Deterministic orthogonal sensitivity fixture, not simulated camera photons.
    q,_=np.linalg.qr(np.random.default_rng(4).normal(size=(169,4)))
    J=q*1e-5
    return lambda t:(J@np.asarray(t)).reshape(13,13),J

def test_sensitivity_linear_center():
    f,J=fake_model();r=local_sensitivity(data(),[100,450,0,0],f)
    assert r['step_stable'] and not r['at_parameter_boundary']
    assert r['actual_predictor_requests']<=17
    assert np.allclose(r['raw_J'],J,atol=1e-14)
    assert r['confidence_interval'] is None

def test_sensitivity_boundary_no_clip():
    f,J=fake_model();seen=[]
    def p(t):
        assert t[0]<=200 and t[1]>=350;seen.append(t.copy());return f(t)
    r=local_sensitivity(data(),[200,350,0,0],p)
    assert r['at_parameter_boundary'];assert r['schemes'][0][:2]==['backward2','forward2']
    assert r['interpretation']=='NUMERICAL_OR_BOUNDARY_LIMITED_NO_PRECISION_CLAIM'

def make_store(tmp_path):return BudgetStore(tmp_path/'b.sqlite','plan',{'A':10},10)

def test_charge_before_model_and_hard_cap(tmp_path):
    s=make_store(tmp_path);s.reserve('t','sig','A',2,'o');calls=[]
    def f(t):calls.append(1);return np.zeros((13,13))
    p=CountedPredictor(f,s,'t','o');p([100,450,0,0]);p([100,450,0,0])
    with pytest.raises(CallCapReached):p([100,450,0,0])
    assert len(calls)==2 and s.counts()['t']==2

def test_unreserved_prediction_never_runs(tmp_path):
    s=make_store(tmp_path);calls=[]
    def f(t):calls.append(1);return np.zeros((13,13))
    with pytest.raises(StoreError):CountedPredictor(f,s,'missing','o')([100,450,0,0])
    assert not calls

def test_model_exception_charged(tmp_path):
    s=make_store(tmp_path);s.reserve('t','sig','A',2,'o')
    def f(t):raise RuntimeError('expected model fault')
    with pytest.raises(RuntimeError):CountedPredictor(f,s,'t','o')([100,450,0,0])
    assert s.counts()['t']==1

def test_partial_persistent_resume_not_reset(tmp_path):
    s=make_store(tmp_path);s.reserve('t','sig','A',2,'o');s.charge('t','o',[100,450,0,0])
    s2=make_store(tmp_path)
    assert s2.counts()['t']==1
    with pytest.raises(StoreError):s2.reserve('t','sig','A',2,'newowner')

def test_finished_resume_no_new_calls(tmp_path):
    s=make_store(tmp_path);s.reserve('t','sig','A',2,'o')
    p=CountedPredictor(lambda t:np.zeros((13,13)),s,'t','o');p([100,450,0,0])
    dst=tmp_path/'r.json';atomic_json(dst,{'signature':'sig','state':'FINISHED'})
    s.seal('t','o','FINISHED',dst)
    assert s.reserve('t','sig','A',2,'different')=='FINISHED'
    assert s.load_result('t','sig')['state']=='FINISHED';assert s.counts()['t']==1

def test_result_tamper_rejected(tmp_path):
    s=make_store(tmp_path);s.reserve('t','sig','A',2,'o');dst=tmp_path/'r.json'
    atomic_json(dst,{'signature':'sig'});s.seal('t','o','FINISHED',dst)
    dst.write_text('{"signature":"other"}')
    with pytest.raises(StoreError):s.load_result('t','sig')

def test_fixed_D_three_variables_and_cap(tmp_path):
    f,_=fake_model();d=GlsData.from_frames(f([120,460,20,30]),np.full((13,13),1e-6))
    seen=[];checkpoints=[];best=[]
    def p(t):seen.append(t.copy());assert t[0]==100.;return f(t)
    r=solve_one_start(d,p,[450,0,0],cap=7,checkpoint=checkpoints.append,
                      persist_best=lambda w,c:best.append(w),fixed_D=100.)
    assert len(seen)==7 and r['state']=='PARTIAL_BUDGET' and best
    assert all(t[0]==100. for t in seen)

def test_fixed_D_rejects_four_coordinates():
    with pytest.raises(ValueError):solve_one_start(data(),lambda t:np.zeros((13,13)),[100,450,0,0],cap=5,
                   checkpoint=lambda x:None,persist_best=lambda x,c:None,fixed_D=100.)

def test_durable_callback_failure_aborts():
    def fail(w,c):raise OSError('storage unavailable')
    with pytest.raises(OSError):solve_one_start(data(),lambda t:np.zeros((13,13)),[100,450,0,0],cap=5,
                   checkpoint=lambda x:None,persist_best=fail)

def test_phase_reservation_overflow(tmp_path):
    s=make_store(tmp_path);s.reserve('t1','s1','A',6,'o')
    with pytest.raises(CallCapReached):s.reserve('t2','s2','A',5,'o')

def test_plan_change_does_not_reset(tmp_path):
    s=make_store(tmp_path)
    with pytest.raises(StoreError):BudgetStore(tmp_path/'b.sqlite','changed',{'A':10},10)

def test_nuisance_split_height_confounded():
    f,J=fake_model();J[:,1]=J[:,0]
    def p(t):return (J@np.asarray(t)).reshape(13,13)
    d=GlsData.from_frames(np.zeros((3,13,13)),np.ones((3,13,13)))
    r=local_sensitivity(d,[100,450,0,0],p)
    split=r['nuisance_split']
    assert split['remove_hxy']['information_fraction']<1e-10
    assert split['remove_xy_height_fixed_hypothesis']['information_fraction']>.99

def test_joint_information_same_theta_fixture():
    f,J=fake_model();d=GlsData.from_frames(np.zeros((3,13,13)),np.ones((3,13,13)))
    r=local_sensitivity(d,[100,450,0,0],f)
    joint=r['projection'][1]['D_residual_squared_sensitivity']
    single=r['single_frame_at_same_theta'][0]['D_residual_squared_sensitivity']
    assert np.isclose(joint,3*single,rtol=1e-9)
