import copy,json,math,sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from v157_height_design import local_design,design_sweep,plan_paths,evaluate_path
from v152_gls_core import GlsData
from v152_budget_store import canonical
from v163_semantics import (independent_coefficient,validate_sweep,expected_designs,
                             group_camera_events,validate_probe_plan,verify_kernel_identity)
from audit_v161_readonly import audit_zip


def matrix():
    j=np.zeros((169,4));j[0,0]=.8;j[1,0]=.6
    j[1,1]=1;j[2,2]=1;j[3,3]=1
    return j

@pytest.mark.parametrize('h,xy,expected',[(math.inf,math.inf,.64),(0.,math.inf,1.),(math.inf,0.,.64),(1.,math.inf,.82),(2.,math.inf,.712),(math.inf,1.,.64)])
def test_analytic_free_exact_and_finite_mean_different_things(h,xy,expected):
    r=local_design(matrix(),sigma_h=h,sigma_xy=xy)
    assert r['total_coefficient_nm_minus2']==pytest.approx(expected,abs=1e-12)
    if h==0:assert r['compensation_nm_per_nm'][0]==0
    if xy==0:assert r['compensation_nm_per_nm'][1:]==[0,0]

@pytest.mark.parametrize('name',list(expected_designs()))
def test_each_required_condition_matches_independent_lstsq(name):
    h,xy=expected_designs()[name]
    for rtol in (1e-8,1e-10,1e-12):
        actual=local_design(matrix(),sigma_h=h,sigma_xy=xy,rtol=rtol)
        expected,b=independent_coefficient(matrix(),h,xy,rtol)
        assert actual['total_coefficient_nm_minus2']==pytest.approx(expected,abs=1e-12)
        assert np.allclose(actual['compensation_nm_per_nm'],b,atol=1e-12)


def test_v161_fallback_pattern_cannot_pass_semantic_validation():
    s=design_sweep(matrix())
    for r in s['height_sigma_1nm']:
        r.update(compensation_nm_per_nm=[0.,0.,0.],total_coefficient_nm_minus2=1.,image_coefficient_nm_minus2=1.,auxiliary_coefficient_nm_minus2=0.)
    with pytest.raises(ValueError,match='INDEPENDENT'):validate_sweep(matrix(),s)


def test_exact_height_cannot_move_height():
    s=design_sweep(matrix());s['exact_height'][0]['compensation_nm_per_nm'][0]=-.6
    with pytest.raises(ValueError,match='NOT_FIXED'):validate_sweep(matrix(),s)


def test_exact_xy_cannot_move_xy():
    s=design_sweep(matrix());s['exact_xy'][0]['compensation_nm_per_nm'][2]=1.
    with pytest.raises(ValueError,match='NOT_FIXED'):validate_sweep(matrix(),s)


def test_required_design_and_rtol_axes_not_collapsed():
    s=design_sweep(matrix());assert validate_sweep(matrix(),s)['records']==51
    s['free']=s['free'][:1]
    with pytest.raises(ValueError,match='RTOL'):validate_sweep(matrix(),s)


def test_solver_error_must_propagate_not_return_zero_compensation(monkeypatch):
    def fail(*a,**kw):raise np.linalg.LinAlgError('injected')
    monkeypatch.setattr(np.linalg,'svd',fail)
    with pytest.raises(np.linalg.LinAlgError):local_design(matrix(),sigma_h=1.)


def events():
    return [dict(B=B,label=f'ANON_{i:02d}_{rep:02d}',event_id=f'B{B}_ANON_{i:02d}_{rep:02d}') for B in (1000,10000,100000) for i in range(1,5) for rep in range(3)]


def test_grouping_preserves_particle_number_and_exact_three_frames():
    grouped,by=group_camera_events(events());assert len(grouped)==12 and len(by)==36
    for (B,anon),rows in grouped.items():
        assert len(rows)==3 and all(r['label'].rsplit('_',1)[0]==anon and r['B']==B for r in rows)

@pytest.mark.parametrize('mutation',['ANON','wrong_event','duplicate','missing'])
def test_grouping_rejects_v161_prefix_collapse_and_other_corruption(mutation):
    e=events()
    if mutation=='ANON':e[0]['label']='ANON'
    if mutation=='wrong_event':e[0]['event_id']='B1000_ANON_02_00'
    if mutation=='duplicate':e[0]=e[1]
    if mutation=='missing':e=e[:-1]
    with pytest.raises(ValueError):group_camera_events(e)


def test_probe_case_01_is_not_an_authorized_replacement():
    t=[120,450,0,0];rows=plan_paths(t,matrix())
    with pytest.raises(ValueError,match='UNAUTHORIZED'):validate_probe_plan((100000,'ANON_01'),t,rows)
    assert validate_probe_plan((100000,'ANON_02'),t,rows)


def test_probe_path_set_cannot_be_only_eight_points():
    t=[120,450,0,0]
    with pytest.raises(ValueError,match='NOT_24'):validate_probe_plan((100000,'ANON_02'),t,plan_paths(t,matrix())[:8])

@pytest.mark.parametrize('delta',[-5.,-2.,-1.,-.5,.5,1.,2.,5.])
def test_increment_not_noisy_residual_is_linearization_target(delta):
    theta=np.array([120.,450.,0.,0.]);jw=matrix();raw=jw/np.sqrt(3.)
    def model(t):return (raw@(np.asarray(t)-theta)).reshape(13,13)
    gd=GlsData.from_frames(np.full((3,13,13),.2),np.ones((3,13,13)))
    row=next(r for r in plan_paths(theta,jw) if r['path']=='free_hxy' and r['delta_D_nm']==delta)
    records=[];out=evaluate_path(row,c0=model(theta),data=gd,jw=jw,predict=model,persist=records.append)
    assert out['relative_linearization_error']<1e-11
    assert len(records)==1
    actual_residual=((np.asarray(out['C'])-gd.ybar)/np.sqrt(gd.vbar)).ravel()
    predicted=jw@(np.asarray(row['theta'])-theta)
    wrong=np.linalg.norm(actual_residual-predicted)/np.linalg.norm(predicted)
    assert wrong>0.5


def test_hypothetical_infinity_is_not_written_as_invalid_json_token():
    raw=canonical(design_sweep(matrix()))
    assert 'Infinity' not in raw and 'NaN' not in raw
    assert json.loads(raw)['free'][0]['no_height_measurement'] is True


def test_original_v161_archive_mechanical_integrity_not_science_pass():
    root=Path(__file__).parents[1]
    r=audit_zip(root/'audit/iscat_v161_return_original.zip')
    assert r['zip_bytes']==4243 and r['manifest_verified']==5 and r['members']==6
    assert r['actual_design_records']==204 and r['finite_zero_compensation']==168
    assert r['probe_particle_labels']==['ANON'] and r['probe_records']==8
    assert not r['sqlite_members'] and not r['scientific_acceptance']


def test_original_v161_archive_tampering_rejected(tmp_path):
    root=Path(__file__).parents[1];b=bytearray((root/'audit/iscat_v161_return_original.zip').read_bytes());b[-1]^=1
    p=tmp_path/'bad.zip';p.write_bytes(b)
    with pytest.raises(ValueError,match='IDENTITY'):audit_zip(p)


def test_seven_approved_kernel_files_are_frozen():
    result=verify_kernel_identity(Path(__file__).parents[1]);assert len(result)==7


def test_kernel_lock_not_just_a_file_name(tmp_path):
    import shutil
    root=Path(__file__).parents[1];target=tmp_path/'bundle';(target/'code').mkdir(parents=True);(target/'config').mkdir()
    lock=json.loads((root/'config/kernel_lock.json').read_text())
    for n in lock:shutil.copy2(root/'code'/n,target/'code'/n)
    shutil.copy2(root/'config/kernel_lock.json',target/'config/kernel_lock.json')
    with (target/'code/v157_height_design.py').open('ab') as f:f.write(b'\n# changed\n')
    with pytest.raises(ValueError,match='KERNEL_CHANGED'):verify_kernel_identity(target)
