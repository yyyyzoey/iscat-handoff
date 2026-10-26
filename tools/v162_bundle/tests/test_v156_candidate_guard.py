import json
import sys
from pathlib import Path
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from v156_candidate_guard import (
    read_v152_pool, select_rescored_complete, enforce_non_fallback,
    AnchorSourceError, BS, ANONS)

COMMIT='6d2db46d52509bd6987726dea211781cfa1b4127'

def fixture():
    rows=[]
    for b in BS:
        for anon in ANONS:
            starts=[]
            for j in range(6):
                starts.append(dict(theta=[60+j*6,410+j,10*j,-10*j],
                                   Q_total=float(90+j),status=2))
            rows.append(dict(B=b,anon=anon,results=json.dumps(starts)))
    return {'joint':rows}

def new_score(p, q, k=5.0):
    return dict(source_record_id=p['source_record_id'],theta=p['theta'],
                candidate_D=p['theta'][0],Q_joint=q,Q_model=q-k,K=k,
                Q_per_frame=[q/3]*3,C_sha256='a'*64,
                observation_identity='Y',variance_identity='V',model_id='F2c')

def test_good_source_exact_72():
    pool=read_v152_pool(fixture(),COMMIT)
    assert len(pool)==12 and sum(len(v) for v in pool.values())==72

def test_v150_summary_without_starts_rejected():
    d=fixture();d['joint'][0].pop('results');d['joint'][0]['joint_D']=100.
    with pytest.raises(AnchorSourceError,match='EXPECTED_SIX'):
        read_v152_pool(d,COMMIT)

def test_wrong_commit_is_rejected():
    with pytest.raises(AnchorSourceError,match='COMMIT'):
        read_v152_pool(fixture(),'wrong')

def test_duplicate_group_rejected():
    d=fixture();d['joint'][-1]=d['joint'][0]
    with pytest.raises(AnchorSourceError,match='DUPLICATE'):
        read_v152_pool(d,COMMIT)

def test_missing_group_rejected():
    d=fixture();d['joint'].pop()
    with pytest.raises(AnchorSourceError,match='12_GROUPS'):
        read_v152_pool(d,COMMIT)

def test_clipped_theta_rejected():
    d=fixture();rows=json.loads(d['joint'][0]['results']);rows[0]['theta'][0]=201
    d['joint'][0]['results']=json.dumps(rows)
    with pytest.raises(AnchorSourceError,match='ILLEGAL_THETA'):
        read_v152_pool(d,COMMIT)

def test_best_select_entire_record_no_field_mixing():
    g=read_v152_pool(fixture(),COMMIT)[(1000,'ANON_01')]
    scores=[new_score(p,float(100-i*10)) for i,p in enumerate(g)]
    best=select_rescored_complete(scores)
    assert best['source_record_id']==g[-1]['source_record_id']
    assert best['theta']==g[-1]['theta']

def test_wrong_Q_component_rejected():
    g=read_v152_pool(fixture(),COMMIT)[(1000,'ANON_01')]
    r=new_score(g[0],100.);r['K']=0.
    with pytest.raises(AnchorSourceError,match='Q_MODEL_K'):
        select_rescored_complete([r])

def test_D_mismatch_rejected():
    g=read_v152_pool(fixture(),COMMIT)[(1000,'ANON_01')]
    r=new_score(g[0],100.);r['candidate_D']=200.
    with pytest.raises(AnchorSourceError,match='D_NOT_BOUND'):
        select_rescored_complete([r])

def test_unscored_old_Q_cannot_rank():
    g=read_v152_pool(fixture(),COMMIT)[(1000,'ANON_01')]
    with pytest.raises(AnchorSourceError,match='RESCORE_FIELD'):
        select_rescored_complete(g)

def test_fallback_theta_must_not_be_synthesized():
    pool=read_v152_pool(fixture(),COMMIT)
    chosen={k:new_score(v[0],100.) for k,v in pool.items()}
    chosen[(1000,'ANON_01')]['theta']=[200.,450.,0.,0.]
    with pytest.raises(AnchorSourceError,match='NOT_EXACT_ORIGINAL'):
        enforce_non_fallback(chosen,pool)

def test_historical_Q_not_authoritative_for_select():
    g=read_v152_pool(fixture(),COMMIT)[(1000,'ANON_01')]
    scores=[new_score(p,float(130-i*20)) for i,p in enumerate(g)]
    assert select_rescored_complete(scores)['source_record_id']==g[-1]['source_record_id']
