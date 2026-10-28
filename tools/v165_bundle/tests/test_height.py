import sys
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'))
sys.path.insert(0,str(ROOT/'generator'))
from v165_objective import augmented_objective,HeightReading,check_theta
from v165_generate_height import generate
sys.path.insert(0,str(ROOT.parent))
# Reference math core copied unchanged from V164 handoff to test adapter parity
from v152_gls_core import GlsData


def fake():
    y=np.arange(3*169,dtype=float).reshape(3,13,13)*1e-5
    v=np.broadcast_to(np.array([1.,2.,3.])[:,None,None],y.shape).copy()
    d=GlsData.from_frames(y,v)
    c=np.ones((13,13))*0.002
    return d,c


def test_noheight_identity():
    d,c=fake();r=augmented_objective(d,c,[101,432.5,1,2])
    assert r['Q_height']==0
    assert abs(r['Q_joint']-r['Q_model']-r['K'])<1e-12
    assert len(r['residual'])==169
    assert abs(float(r['residual']@r['residual'])+r['K']-r['Q_total'])<1e-12


def test_height_penalty_and_half_cost():
    d,c=fake();a=HeightReading('r','ANON_02',0,1.,432.5)
    r=augmented_objective(d,c,[101,434.5,1,2],a)
    assert r['Q_height']==4
    assert len(r['residual'])==170
    assert abs(float(r['residual']@r['residual'])+r['K']-r['Q_total'])<1e-11
    assert r['reportable_D'] is None


def test_h_center_not_candidate_height():
    d,c=fake();a=HeightReading('r','ANON_02',0,1.,432.5)
    r=augmented_objective(d,c,[124,412,0,0],a)
    assert abs(r['Q_height']-420.25)<1e-10


def test_no_clipping_and_signed_pixels():
    with pytest.raises(ValueError):check_theta([205,432,0,0])
    with pytest.raises(ValueError):check_theta([101,432,600,0])
    d,c=fake()
    with pytest.raises(ValueError):augmented_objective(d,np.zeros((17,17)),[101,432,0,0])


def test_height_generator_reproducible_without_true_in_public():
    t={'cases':[{'case':f'N{i:02d}','D_nm':d,'h_nm':h} for i,d,h in [(1,59,391.25),(2,101,432.5),(3,143,478.75),(4,181,526.25)]]}
    a,b=generate(t);aa,bb=generate(t)
    assert a==aa and b==bb and len(a)==24 and len(b)==24
    assert sorted(set(x['group'] for x in a))==['ANON_01','ANON_02','ANON_03','ANON_04']
    assert all('D_scene_nm' not in x and 'h_scene_nm' not in x and 'epsilon' not in x for x in a)
    assert all(x['sigma_nm'] in (1.,10.) and x['hypothetical'] for x in a)
    # paired latent epsilons are shared for the two hypothetical sensor precisions
    for group in sorted(set(x['group'] for x in a)):
      for rep in range(3):
        r1=next(x for x in a if x['group']==group and x['replicate']==rep and x['sigma_nm']==1.)
        r10=next(x for x in a if x['group']==group and x['replicate']==rep and x['sigma_nm']==10.)
        h=next(x['h_nm'] for x in t['cases'] if f'ANON_{int(x["case"][1:]):02d}'==group)
        assert abs((r1['z_nm']-h)*10 -(r10['z_nm']-h))<1e-10


def test_invalid_height_definition():
    for sig in [0.,float('inf'),float('nan'),-1.]:
        with pytest.raises(ValueError):HeightReading('id','ANON_03',0,sig,450.)


def test_task_matrix_and_total_reservation():
    from v165_task_ids import tasks
    ts=tasks()
    assert len(ts)==28
    assert len([x for x in ts if x['sigma_nm'] is None])==4
    assert len([x for x in ts if x['sigma_nm']==10])==12
    assert len([x for x in ts if x['sigma_nm']==1])==12
    assert len(ts)*400+200+600==12000
