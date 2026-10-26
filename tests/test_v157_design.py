import math
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'code'))
from v157_height_design import (local_design, design_sweep, height_formula_crosscheck,
                               plan_paths, evaluate_path, RTOLS)
from v152_gls_core import GlsData


def matrix():
    q = np.zeros((169,4)); q[:4,:] = np.eye(4)
    j=q.copy();j[:,0]=.4*q[:,0]+np.sqrt(.84)*q[:,1]
    return j


@pytest.mark.parametrize('rtol', RTOLS)
def test_free_and_exact_height_and_xy(rtol):
    j=matrix()
    f=local_design(j, rtol=rtol)
    h=local_design(j,sigma_h=0,rtol=rtol)
    xy=local_design(j,sigma_xy=0,rtol=rtol)
    assert f['total_coefficient_nm_minus2']==pytest.approx(.16)
    assert h['total_coefficient_nm_minus2']==pytest.approx(1.)
    assert xy['total_coefficient_nm_minus2']==pytest.approx(.16)
    assert h['compensation_nm_per_nm'][0] == 0


@pytest.mark.parametrize('sigma',[1.,2.,5.,10.,20.,50.,100.,math.inf])
def test_finite_sigma_analytic_and_monotonic(sigma):
    j=matrix();r=local_design(j,sigma_h=sigma)
    expected=.16 if math.isinf(sigma) else .16+.84/(1+sigma**2)
    assert r['total_coefficient_nm_minus2']==pytest.approx(expected)
    c=height_formula_crosscheck(j,sigma)['coefficient_by_subtraction']
    assert r['total_coefficient_nm_minus2']==pytest.approx(c)
    assert .16-1e-12 <= c <= 1+1e-12


def test_sigma_design_sweep_complete_without_model():
    s=design_sweep(matrix())
    assert len(s)==17
    assert all(len(rows)==3 for rows in s.values())
    values=[s[f'height_sigma_{v}nm'][0]['total_coefficient_nm_minus2'] for v in (1,2,5,10,20,50,100)]
    assert np.all(np.diff(values)<=0)


@pytest.mark.parametrize('bad',[np.zeros((4,169)),np.zeros((169,)),np.full((169,4),np.nan)])
def test_bad_j_fails(bad):
    with pytest.raises(ValueError):local_design(bad)


@pytest.mark.parametrize('sigma',[-1.,-math.inf,float('nan')])
def test_bad_sigma_fails(sigma):
    with pytest.raises(ValueError):local_design(matrix(),sigma_h=sigma)


@pytest.mark.parametrize('rtol',[0.,-1.,1.,float('nan')])
def test_bad_rtol_fails(rtol):
    with pytest.raises(ValueError):local_design(matrix(),rtol=rtol)


def test_zero_columns_no_divide_by_zero():
    r=local_design(np.zeros((169,4)))
    assert r['total_coefficient_nm_minus2']==0
    assert r['fraction_of_all_nuisance_fixed'] is None
    assert r['reportable_D'] is None


def test_rank_deficient_no_inverse_normal_matrix():
    j=matrix();j[:,2]=j[:,1]
    r=local_design(j)
    assert r['nuisance_rank']==2
    assert r['total_coefficient_nm_minus2']==pytest.approx(.16)


def test_fraction_is_squared_not_norm():
    r=local_design(matrix())
    assert r['fraction_of_all_nuisance_fixed']==pytest.approx(.16)
    assert math.sqrt(r['fraction_of_all_nuisance_fixed'])==pytest.approx(.4)


def test_paths_fixed_and_bounded_without_clipping():
    plans=plan_paths([199.9,450,0,0],matrix())
    assert len(plans)==24
    assert sum(r['state']=='SKIPPED_OUT_OF_DOMAIN' for r in plans)==12
    assert any(r['theta'][0]>200 for r in plans)
    for r in plans:
        if r['path']=='exact_height': assert r['theta'][1]==450


def test_skipped_makes_zero_predictions():
    row=next(r for r in plan_paths([199.9,450,0,0],matrix()) if r['state'].startswith('SKIPPED'))
    gd=GlsData.from_frames(np.zeros((3,13,13)),np.ones((3,13,13)))
    def bomb(*_):raise AssertionError('must not call')
    result=evaluate_path(row,c0=np.zeros((13,13)),data=gd,jw=matrix(),predict=bomb,persist=bomb)
    assert result['state'].startswith('SKIPPED')


def linear_setup():
    j=matrix();t=np.array([120.,450.,0.,0.]);raw=j/np.sqrt(3)
    def pred(theta):return (raw@(np.asarray(theta)-t)).reshape(13,13)
    ys=np.full((3,13,13),.01);gd=GlsData.from_frames(ys,np.ones_like(ys))
    return t,j,pred,gd


@pytest.mark.parametrize('name',['free_hxy','exact_height','height_sigma10'])
def test_path_linear_model_distance_and_q_identity(name):
    t,j,pred,gd=linear_setup()
    row=next(r for r in plan_paths(t,j) if r['path']==name and r['delta_D_nm']==1)
    saved=[]
    r=evaluate_path(row,c0=pred(t),data=gd,jw=j,predict=pred,persist=saved.append)
    assert r['relative_linearization_error']<1e-11
    assert r['image_distance_squared']==pytest.approx(r['predicted_image_distance_squared'])
    assert r['total_design_distance_squared']==pytest.approx(row['design']['total_coefficient_nm_minus2'])
    assert r['observed_Q_change']==pytest.approx(r['observed_Q_cross_term']+r['image_distance_squared'])
    assert len(saved)==1


def test_persist_failure_not_success():
    t,j,pred,gd=linear_setup();row=plan_paths(t,j)[0]
    def bad(_): raise OSError('disk error')
    with pytest.raises(OSError):evaluate_path(row,c0=pred(t),data=gd,jw=j,predict=pred,persist=bad)


def test_scalar_q_not_accepted_as_contrast():
    t,j,pred,gd=linear_setup()
    with pytest.raises(ValueError):
        evaluate_path(plan_paths(t,j)[0],c0=pred(t),data=gd,jw=j,predict=lambda _:0.,persist=lambda _:None)


def test_curved_model_detected_without_claiming_profile():
    t,j,pred,gd=linear_setup()
    def curved(theta):
        c=pred(theta).copy();c[0,0]+=.05*(theta[0]-t[0])**2;return c
    row=next(r for r in plan_paths(t,j) if r['path']=='free_hxy' and r['delta_D_nm']==5)
    r=evaluate_path(row,c0=pred(t),data=gd,jw=j,predict=curved,persist=lambda _:None)
    assert r['relative_linearization_error']>.05
    assert r['method']=='LINEAR_COMPENSATION_PATH_NOT_PROFILE_MINIMUM'
    assert r['reportable_D'] is None
