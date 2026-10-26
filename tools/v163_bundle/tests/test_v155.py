from __future__ import annotations
import copy, json, sys
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from v152_gls_core import GlsData, check_theta, CallCapReached
from v152_budget_store import BudgetStore, StoreError, CountedPredictor, atomic_json
from v155_pixel_diagnostics import diagnose, contrast, gls_score_independent, validate_pixel_record
from v155_stage import run_group

CENTER=np.array([100.,450.,0.,0.])
A=np.zeros((169,4)); A[:4,:]=np.eye(4)*1e-3

def linear(t):return (0.01+A@(np.asarray(t)-CENTER)).reshape(13,13)
def data():
    y=np.stack([linear(CENTER)+v for v in (0.001,0.002,-0.001)])
    return GlsData.from_frames(y,np.ones_like(y)*.0001)


def test_gls_unequal_weights_identity():
    v=np.stack([np.full((13,13),v) for v in (1.,2.,4.)])
    y=np.stack([np.full((13,13),v) for v in (1.,3.,7.)])
    d=GlsData.from_frames(y,v); s=gls_score_independent(np.zeros((13,13)),d)
    assert np.isclose(s['Q_joint'],sum(s['Q_per_frame']))
    assert np.isclose(s['Q_joint'],s['Q_model']+s['K'])


def test_mean_variance_is_not_variance_of_mean():
    d=data(); c=np.zeros((13,13))
    wrong=np.sum((c-d.y.mean(axis=0))**2/d.variance.mean(axis=0))
    assert np.isclose(gls_score_independent(c,d)['Q_model'],3*wrong)


def test_actual_vector_jacobian_full_rank():
    doc=diagnose(data(),CENTER,linear)
    j=np.array(doc['raw_J_fine']); assert j.shape==(169,4)
    assert np.allclose(j,A,rtol=1e-8,atol=1e-12)
    assert np.linalg.matrix_rank(j)==4
    assert doc['projections']['free_hxy'][1]['remaining_D_norm_fraction']>0.999999
    assert doc['unique_predictions']<=21
    validate_pixel_record(doc)


def test_old_scalar_gradient_bug_is_rank_one_on_full_rank_model():
    d=data(); eps=np.array([.2,.2,.5,.5]); bad=np.zeros((169,4))
    for k,h in enumerate(eps):
        dt=np.zeros(4);dt[k]=h
        qp=gls_score_independent(linear(CENTER+dt),d)['Q_joint']
        qm=gls_score_independent(linear(CENTER-dt),d)['Q_joint']
        bad[:,k]=(qp-qm)/(2*h)
    assert np.linalg.matrix_rank(A)==4
    assert np.linalg.matrix_rank(bad)==1


def test_real_dependent_model_not_forced_to_rank_four():
    B=A.copy(); B[:,0]=B[:,1]
    f=lambda t:(0.01+B@(np.asarray(t)-CENTER)).reshape(13,13)
    d=diagnose(data(),CENTER,f)
    assert np.linalg.matrix_rank(d['raw_J_fine'])==3
    assert d['projections']['free_hxy'][1]['remaining_D_norm_fraction']<1e-9
    assert d['physical_degeneracy_confirmed'] is False


@pytest.mark.parametrize('theta',[[200.,450.,0.,0.],[30.,350.,-500.,500.],[100.,550.,500.,-500.]])
def test_one_sided_boundary_has_legal_real_coordinates(theta):
    seen=[]
    def f(t):check_theta(t);seen.append(t.copy());return linear(t)
    doc=diagnose(data(),theta,f)
    assert doc['parameter_boundary']
    assert doc['status']=='BOUNDARY_LOCAL_DIAGNOSTIC_ONLY'
    assert np.allclose(doc['raw_J_fine'],A,rtol=1e-7,atol=1e-12)
    validate_pixel_record(doc)


@pytest.mark.parametrize('bad',[1.2,np.zeros(169),np.zeros((17,17)),np.full((13,13),np.nan)])
def test_scalar_or_wrong_prediction_is_rejected(bad):
    with pytest.raises(ValueError):contrast(bad)


@pytest.mark.parametrize('bad',[0.,-1.,float('nan')])
def test_bad_variance_is_not_floored(bad):
    with pytest.raises(ValueError):GlsData.from_frames(np.zeros((13,13)),np.full((13,13),bad))


def test_scalar_gradient_tampering_fails_independent_validator():
    doc=diagnose(data(),CENTER,linear)
    doc['raw_J_fine']=np.ones((169,4)).tolist()
    with pytest.raises(ValueError,match='PIXEL_DERIVATIVE'):validate_pixel_record(doc)


def test_whitening_tampering_fails():
    doc=diagnose(data(),CENTER,linear);doc['whitened_J_fine']=doc['raw_J_fine']
    with pytest.raises(ValueError,match='WHITENING'):validate_pixel_record(doc)


def test_complete_theta_tampering_fails():
    doc=diagnose(data(),CENTER,linear);doc['theta'][1]+=1
    with pytest.raises(ValueError,match='BASE_THETA'):validate_pixel_record(doc)


def test_scalar_Q_double_tampering_fails():
    doc=diagnose(data(),CENTER,linear);doc['score']['Q_joint']*=2
    with pytest.raises(ValueError,match='Q_IDENTITY'):validate_pixel_record(doc)


def test_reportability_tampering_fails():
    doc=diagnose(data(),CENTER,linear);doc['reportable_D']=100.
    with pytest.raises(ValueError,match='UNQUALIFIED'):validate_pixel_record(doc)


def test_snapshot_failure_stops_future_predictions():
    calls=[]
    def f(t):calls.append(t);return linear(t)
    def fail(*_):raise OSError('write fault')
    with pytest.raises(OSError):diagnose(data(),CENTER,f,fail)
    assert len(calls)==1


def test_fixed_D_postfit_observation_is_not_array():
    @dataclass
    class Obs:score_C:np.ndarray
    o=Obs(np.zeros((13,13)))
    with pytest.raises(TypeError):o-np.zeros((13,13))
    assert np.sum((o.score_C-np.zeros((13,13)))**2)==0


def test_stage_true_path_and_idempotent_reuse(tmp_path):
    store=BudgetStore(tmp_path/'ledger.sqlite','test',{'LOCAL_INFORMATION':40},40)
    calls=[]
    def f(t):calls.append(t.copy());return linear(t)
    args=dict(store=store,task='g',owner='owner',data=data(),theta=CENTER,
              source={'model_id':'FAKE_TEST_ONLY'},model_contrast=f,out=tmp_path/'g')
    doc=run_group(**args); n=len(calls)
    assert 1<=n<=21 and store.counts()['g']==n
    doc2=run_group(**args)
    assert len(calls)==n and doc==doc2
    assert len(list((tmp_path/'g'/'predictions').glob('*.json')))==n


def test_hard_cap_before_model(tmp_path):
    store=BudgetStore(tmp_path/'ledger.sqlite','t',{'P':2},2)
    store.reserve('t','sig','P',2,'o');calls=[]
    pred=CountedPredictor(lambda t:(calls.append(t) or linear(t)),store,'t','o')
    pred(CENTER);pred(CENTER)
    with pytest.raises(CallCapReached):pred(CENTER)
    assert len(calls)==2 and store.counts()['t']==2


def test_counter_records_model_exception(tmp_path):
    store=BudgetStore(tmp_path/'ledger.sqlite','t',{'P':2},2)
    store.reserve('t','sig','P',2,'o')
    def fail(_):raise ValueError('model fault')
    with pytest.raises(ValueError):CountedPredictor(fail,store,'t','o')(CENTER)
    assert store.counts()['t']==1
    with store.db() as db:
        assert db.execute('SELECT state FROM attempts').fetchone()[0]=='MODEL_ERROR'


def test_missing_reservation_blocks_model(tmp_path):
    store=BudgetStore(tmp_path/'ledger.sqlite','t',{'P':2},2);calls=[]
    with pytest.raises(StoreError):CountedPredictor(lambda t:(calls.append(t) or linear(t)),store,'x','o')(CENTER)
    assert calls==[]


def test_phase_reservation_overrun_blocked(tmp_path):
    store=BudgetStore(tmp_path/'ledger.sqlite','t',{'P':2,'Q':3},5)
    store.reserve('a','s1','P',2,'o')
    with pytest.raises(CallCapReached):store.reserve('b','s2','P',1,'o')


def test_existing_ledger_plan_cannot_change(tmp_path):
    p=tmp_path/'ledger.sqlite';BudgetStore(p,'t',{'P':2},2)
    with pytest.raises(StoreError):BudgetStore(p,'t',{'P':3},3)


def test_stage_real_error_sealed_and_propagated(tmp_path):
    store=BudgetStore(tmp_path/'ledger.sqlite','test',{'LOCAL_INFORMATION':40},40)
    def fail(_):raise RuntimeError('integration fault')
    with pytest.raises(RuntimeError):
        run_group(store=store,task='g',owner='o',data=data(),theta=CENTER,source={},model_contrast=fail,out=tmp_path/'g')
    d=json.loads((tmp_path/'g'/'result.json').read_text());assert d['execution_state']=='FAILED'
    assert 'RuntimeError' in d['traceback'] and store.counts()['g']==1


def test_parameter_outside_domain_not_clipped():
    calls=[]
    with pytest.raises(ValueError):diagnose(data(),[201,450,0,0],lambda t:(calls.append(t) or linear(t)))
    assert not calls


def test_best_is_not_first_and_moves_whole_record():
    from v155_pixel_diagnostics import select_complete_best
    rows=[dict(theta=[100,450,0,0],candidate_D=100,Q_joint=10,source_record_id='a'),
          dict(theta=[120,400,20,30],candidate_D=120,Q_joint=3,source_record_id='b')]
    assert select_complete_best(rows) is rows[1]


def test_mixed_candidate_d_is_rejected():
    from v155_pixel_diagnostics import select_complete_best
    with pytest.raises(ValueError,match='D_THETA'):
        select_complete_best([dict(theta=[100,450,0,0],candidate_D=120,Q_joint=3,source_record_id='b')])


def test_q_model_label_mix_is_rejected():
    doc=diagnose(data(),CENTER,linear);doc['score']['Q_model']=doc['score']['Q_joint']
    with pytest.raises(ValueError,match='Q_COMPONENTS'):validate_pixel_record(doc)


def test_fabricated_projection_is_rejected():
    doc=diagnose(data(),CENTER,linear)
    doc['projections']['free_hxy'][0]['remaining_D_norm_fraction']=0
    with pytest.raises(ValueError,match='PROJECTION_RATIO'):validate_pixel_record(doc)


def test_mutated_stencil_coordinate_is_rejected():
    doc=diagnose(data(),CENTER,linear);doc['predictions'][1]['theta'][1]+=.1
    with pytest.raises(ValueError,match='STENCIL_COORDINATE'):validate_pixel_record(doc)


def test_true_constant_pixel_rank_one_model_is_allowed():
    def f(t):return np.full((13,13),np.dot(np.asarray(t)-CENTER,[1e-3,2e-3,3e-3,4e-3]))
    doc=diagnose(data(),CENTER,f)
    validate_pixel_record(doc)
    assert np.linalg.matrix_rank(doc['raw_J_fine'])==1
    assert doc['physical_degeneracy_confirmed'] is False
