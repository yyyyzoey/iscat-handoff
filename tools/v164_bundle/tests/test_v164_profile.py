import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
import math
from types import SimpleNamespace
import numpy as np
import pytest
from v152_gls_core import GlsData,CallCapReached
from v164_profile_core import *


def fixture_case(design='free_hxy',delta=5.,beta=0.):
    anchor=np.array([120.,450.,0.,0.]);eps=.08
    def model(t):
        dd,dh,dx,dy=np.asarray(t)-anchor
        c=np.zeros(169);c[:4]=[dd+dh+beta*dd**2,eps*dd,dx,dy]
        return c.reshape(13,13)
    j=np.zeros((169,4));j[:4]=[[1,1,0,0],[eps,0,0,0],[0,0,1,0],[0,0,0,1]]
    data=GlsData.from_frames(np.zeros((3,13,13)),np.ones((3,13,13)))
    p=Problem(GROUPS[0],delta,design,anchor,model(anchor),data,np.sqrt(3)*j)
    calls=[];writes=[]
    def predict(t):calls.append(np.array(t));return model(t)
    def persist(kind,index,doc):writes.append((kind,index,doc))
    return p,model,predict,lambda:len(calls),persist,calls,writes,eps

@pytest.mark.parametrize('delta',[-5.,5.])
@pytest.mark.parametrize('design',DESIGNS)
def test_linear_exact_objective_not_noisy_Q(design,delta):
    p,m,pred,counts,persist,calls,wr,eps=fixture_case(design,delta)
    out=solve_profile(p,pred,counts,persist)
    sigma=SIGMAS[design]
    expected=3*eps**2*delta**2+(0 if math.isinf(sigma) else 3*delta**2/(1+3*sigma*sigma))
    assert out['best']['design_distance_squared']==pytest.approx(expected,rel=2e-7,abs=1e-9)
    assert all(t[0]==p.fixed_D for t in calls)
    if design=='exact_height': assert all(t[1]==p.anchor[1] for t in calls)
    assert counts()<=400
    assert len(out['starts'])==2
    assert out['reportable_D'] is None
    assert any(k=='evaluation' for k,_,_ in wr)

@pytest.mark.parametrize('design',DESIGNS)
def test_curved_model_keeps_original_linear_witness(design):
    p,m,pred,counts,persist,calls,wr,eps=fixture_case(design,beta=.2)
    w={'theta':p.linear_theta.tolist(),'C':m(p.linear_theta).tolist(),'source_id':'saved'}
    out=solve_profile(p,pred,counts,persist,prior_witnesses=[w])
    assert out['best']['design_distance_squared']<=out['linear_witness']['design_distance_squared']+1e-9
    if design=='free_hxy':
        assert out['best']['theta'][1]==pytest.approx(440.,abs=1e-4)
        assert out['best']['design_distance_squared']<out['linear_witness']['design_distance_squared']/10


def test_budget_stop_has_finite_witness_and_not_success():
    p,m,pred,counts,persist,calls,wr,eps=fixture_case(beta=.2)
    r=solve_profile(p,pred,counts,persist,per_start_cap=2,task_cap=4)
    assert counts()<=4 and r['search_state']=='PARTIAL_SEARCH'
    assert r['best']['design_distance_squared']>=0
    assert any(x['state']=='PARTIAL_BUDGET' for x in r['starts'])


def test_model_error_propagates_not_zero_compensation():
    p,m,_,counts,persist,calls,wr,eps=fixture_case()
    def bad(t):raise RuntimeError('MODEL_BROKEN')
    with pytest.raises(RuntimeError,match='MODEL_BROKEN'):solve_profile(p,bad,counts,persist)
    assert any(x[0]=='start_failure' for x in wr)


def test_write_error_propagates():
    p,m,pred,counts,_,calls,wr,eps=fixture_case()
    def bad(*a):raise OSError('DISK_BROKEN')
    with pytest.raises(OSError,match='DISK_BROKEN'):solve_profile(p,pred,counts,bad)

@pytest.mark.parametrize('bad', [np.zeros((17,17)),np.zeros(169),0.,np.full((13,13),np.nan)])
def test_model_array_shape_errors_not_ignored(bad):
    p,m,pred,counts,persist,calls,wr,eps=fixture_case()
    with pytest.raises(ValueError):solve_profile(p,lambda t:bad,counts,persist)

@pytest.mark.parametrize('design',DESIGNS)
def test_noisy_residual_is_separate_from_image_distance(design):
    p,m,pred,counts,persist,calls,wr,eps=fixture_case(design)
    frames=np.full((3,13,13),.123)
    data=GlsData.from_frames(frames,np.ones_like(frames))
    row=evaluate(p.anchor,p.c0,anchor=p.anchor,c0=p.c0,data=data,design=design)
    assert row['design_distance_squared']==0
    assert row['observed_Q']['Q_joint']>0
    assert row['observed_Q_change']==0


def test_exact_height_change_rejected():
    p,m,pred,counts,persist,calls,wr,eps=fixture_case('exact_height')
    t=p.anchor.copy();t[1]+=.01
    with pytest.raises(ValueError,match='EXACT_HEIGHT'):evaluate(t,m(t),anchor=p.anchor,c0=p.c0,data=p.data,design='exact_height')

@pytest.mark.parametrize('bad',['100000_ANON','100000_ANON_01','10000_ANON_02'])
def test_full_authorized_group_not_prefix(bad):
    p,*_=fixture_case()
    with pytest.raises(ValueError,match='GROUP'):Problem(bad,5.,p.design,p.anchor,p.c0,p.data,p.jw)

@pytest.mark.parametrize('delta',[0.,1.,2.,10.])
def test_scope_is_fixed_delta(delta):
    p,*_=fixture_case()
    with pytest.raises(ValueError,match='DELTA'):Problem(p.group,delta,p.design,p.anchor,p.c0,p.data,p.jw)


def test_common_pool_monotone_and_no_model_calls():
    rows=[]
    for design in DESIGNS:
        p,m,pred,counts,persist,calls,wr,eps=fixture_case(design,beta=.2)
        rows.append(solve_profile(p,pred,counts,persist))
    result=pool_profiles(rows,p.data,p.c0,p.anchor)
    values=[result['common_pool_minima'][d]['design_distance_squared'] for d in DESIGNS]
    assert values==sorted(values)
    assert result['own_optimizer_results_preserved']


def test_common_pool_rejects_different_groups():
    rows=[]
    for design in DESIGNS:
        p,m,pred,counts,persist,*_=fixture_case(design)
        rows.append(solve_profile(p,pred,counts,persist))
    rows[-1]['group']=GROUPS[-1]
    with pytest.raises(ValueError,match='CROSS_GROUP'):pool_profiles(rows,p.data,p.c0,p.anchor)


def test_wrong_scipy_half_cost_rejected():
    p,m,pred,counts,persist,*_=fixture_case()
    def wrong(fun,x0,**kwargs):
        r=fun(x0)
        return SimpleNamespace(x=x0,cost=float(r@r),success=True,status=1,message='bad',nfev=1,njev=1,optimality=0.,active_mask=np.zeros_like(x0))
    with pytest.raises(ValueError,match='HALF_COST'):solve_profile(p,pred,counts,persist,optimizer=wrong)


def test_fixed_d_drift_rejected():
    p,m,*_=fixture_case();t=p.anchor.copy();t[0]=p.fixed_D+.1
    with pytest.raises(ValueError,match='FIXED_D'):p.residual(t,m(t))
