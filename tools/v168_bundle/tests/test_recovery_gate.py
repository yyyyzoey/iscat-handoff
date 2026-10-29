from __future__ import annotations
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'))
import v168_recovery_gate as g


def fixture_db(path, *, include_attempts=True):
    con=sqlite3.connect(path)
    con.executescript('''CREATE TABLE metadata(id INTEGER PRIMARY KEY,value TEXT);
    CREATE TABLE tasks(id TEXT PRIMARY KEY,signature TEXT,phase TEXT,cap INTEGER,used INTEGER,state TEXT);
    ''')
    con.execute('INSERT INTO metadata VALUES(1,?)',(json.dumps({'plan_id':'v167','total':10000,'phases':g.OLD_PHASES}),))
    rows=[('V167_LOADER_1','s','MODEL_BINDING',100,1,'RUNNING'),
          ('V167_BINDING','s','MODEL_BINDING',100,0,'RUNNING')]
    rows += [(f'R{i}','s','SEARCH_EXTENSION',400,0,'RUNNING') for i in range(5)]
    rows += [(f'B{i}','s','BIAS_STRESS',400,0,'RUNNING') for i in range(18)]
    rows += [('V167_FINAL_VERIFY','s','FINAL_VERIFY',600,0,'RUNNING')]
    con.executemany('INSERT INTO tasks VALUES(?,?,?,?,?,?)',rows)
    if include_attempts:
        con.execute('CREATE TABLE attempts(task TEXT,seq INTEGER,theta TEXT,state TEXT,detail TEXT,ts REAL)')
        detail={'kind':'MODEL_LOADER','invocation':'charged_model_forward','task_id':'V167_LOADER_1',
                'ledger_seq':1,'requested_theta':[30.,350.,0.,0.]}
        con.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?)',('V167_LOADER_1',1,'[30.0,350.0,0.0,0.0]',
                    'CHARGED',json.dumps(detail),1793214295.0581424))
    con.commit();con.close()
    return g.file_sha(path)


def test_legacy_audit_does_not_modify(tmp_path):
    path=tmp_path/'old.sqlite'; sh=fixture_db(path);before=path.read_bytes()
    r=g._read_legacy(path,sh)
    assert path.read_bytes()==before
    assert r['old_used']==1 and r['historical_task_states']=={'RUNNING':26}
    assert r['attempts'][0]['state']=='CHARGED' and not r['old_attempt_settled_by_this_tool']


def test_missing_attempts_does_not_mean_zero(tmp_path):
    path=tmp_path/'old.sqlite';sh=fixture_db(path,include_attempts=False)
    with pytest.raises(g.RecoveryRefused,match='MISSING_ATTEMPTS_SCHEMA'):
        g._read_legacy(path,sh)


def test_public_audit_rejects_synthetic_unpinned_db(tmp_path):
    path=tmp_path/'old.sqlite';fixture_db(path)
    with pytest.raises(g.RecoveryRefused,match='SHA_MISMATCH'):
        g.audit_legacy_ledger(path)


@pytest.mark.parametrize('suffix',['-wal','-shm','-journal'])
def test_no_live_sidecars(tmp_path,suffix):
    path=tmp_path/'old.sqlite'; sh=fixture_db(path); Path(str(path)+suffix).write_bytes(b'')
    with pytest.raises(g.RecoveryRefused,match='SIDECAR'):
        g._read_legacy(path,sh)


@pytest.mark.parametrize('mutation',[
    "UPDATE tasks SET used=0 WHERE id='V167_LOADER_1'",
    "UPDATE attempts SET state='RETURNED'",
    "UPDATE tasks SET state='FINISHED' WHERE id='V167_LOADER_1'",
    "DELETE FROM attempts",
    "UPDATE attempts SET theta='[31,350,0,0]'",
    "UPDATE tasks SET cap=99 WHERE id='V167_BINDING'",
])
def test_changed_legacy_evidence_rejected(tmp_path,mutation):
    path=tmp_path/'old.sqlite'; fixture_db(path)
    con=sqlite3.connect(path);con.execute(mutation);con.commit();con.close()
    with pytest.raises(g.RecoveryRefused):g._read_legacy(path,g.file_sha(path))


def test_authorization_sums():
    d=g.load_authorization()
    assert sum(d['phases'].values())==9999
    assert 100+99+5*400+18*400+600==9999


@pytest.mark.parametrize('key,value',[
 ('historical_consumed_attempts',0),('new_attempt_ceiling',10000),('combined_attempt_ceiling',20000),
 ('allowed_new_constructions',2),('old_ledger_must_remain_byte_identical',False),
 ('no_automatic_retry_after_new_charge',False),('new_height_random_draws',1),('new_BEM',1),
 ('reportable_D',100),('EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED',True)])
def test_authorization_tamper_rejected(key,value):
    d=g.load_authorization();d[key]=value
    with pytest.raises(g.RecoveryRefused):g.validate_authorization(d)


def test_phase_budget_may_not_be_reallocated():
    d=g.load_authorization();d['phases']['MODEL_BINDING']+=1;d['phases']['FINAL_VERIFY']-=1
    with pytest.raises(g.RecoveryRefused):g.validate_authorization(d)


def test_role_specific_identity_accepts_exact_parent():
    g.check_returned_model_id('MODEL_LOADER',g.F2)
    for kind in ['OPTIMIZER','SOURCE_BINDING','INDEPENDENT_FINAL']:
        g.check_returned_model_id(kind,g.F2C)
    g.check_constructed_parent(g.F2C,g.F2,[g.F2]*70)


@pytest.mark.parametrize('kind,identity',[
 ('MODEL_LOADER',g.F2C),('OPTIMIZER',g.F2),('INDEPENDENT_FINAL',None),
 ('SOURCE_BINDING','v142-F2c-'+ '0'*64),('MODEL_LOADER','v131-field-'+'0'*64),('UNLISTED',g.F2C)])
def test_wrong_forward_identity_rejected(kind,identity):
    with pytest.raises(g.RecoveryRefused):g.check_returned_model_id(kind,identity)


@pytest.mark.parametrize('observed',[[],[g.F2,g.F2C],['v131-field-'+'0'*64]])
def test_parent_link_rejects_empty_or_mixed(observed):
    with pytest.raises(g.RecoveryRefused):g.check_constructed_parent(g.F2C,g.F2,observed)


def test_combined_budget_keeps_the_old_charge():
    r=g.combined_budget_report(dict(g.PHASES))
    assert r['combined_consumed']==10000 and r['combined_remaining']==0
    assert g.combined_budget_report({k:0 for k in g.PHASES})['combined_consumed']==1


@pytest.mark.parametrize('count',[200,-1,True,199.5])
def test_phase_counter_types_and_caps(count):
    d={k:0 for k in g.PHASES};d['MODEL_BINDING']=count
    with pytest.raises(g.RecoveryRefused):g.combined_budget_report(d)


def test_identity_stable_to_dict_key_order_but_not_code_edit():
    f={'b.py':'b'*64,'a.py':'a'*64};p={'s':'c'*64};test='d'*64
    d=g.capsule_digest(f,{'stage':'one'},p,test)
    assert d==g.capsule_digest(dict(reversed(list(f.items()))),{'stage':'one'},p,test)
    f['a.py']='e'*64
    with pytest.raises(g.RecoveryRefused):
        g.require_frozen_capsule(d,g.capsule_digest(f,{'stage':'one'},p,test))


def test_nan_cannot_be_sealed():
    with pytest.raises(ValueError):g.canonical({'nan':float('nan')})


def test_cache_hits_are_not_charges():
    g.require_budget_boundary(200,200,cache_verified=True)
    with pytest.raises(g.RecoveryRefused):g.require_budget_boundary(200,200,cache_verified=False)
    for i in range(400):g.require_budget_boundary(i,400,cache_verified=False)
    with pytest.raises(g.RecoveryRefused):g.require_budget_boundary(400,400,cache_verified=False)


def test_r_pass_not_cut_at_two_hundred():
    # Actual-charge policy allows a SINGLE R least_squares instance to reach 400.
    g.require_budget_boundary(200,400,cache_verified=False)
    g.require_budget_boundary(399,400,cache_verified=False)


def test_reconciliation_does_not_invent_old_success():
    d=g.load_authorization()
    r=g.old_charge_reconciliation({'old_ledger_sha256':g.OLD_SHA,'old_used':1,'old_attempts':1},d)
    assert r['old_state_kept']=='CHARGED' and r['old_charge_carried']==1
    assert r['new_authority']==9999


@pytest.mark.parametrize('key,value',[
    ('recovery_tasks',[]),('recovery_source_start',0),('bias_groups',['ANON_01']),
    ('replicates',[0,1]),('bias_nm',[-5,5]),('bias_sigma_nm',10),
    ('optimizer',{}),('domain',{})])
def test_science_grid_cannot_drift(key,value):
    d=g.load_authorization();d[key]=value
    with pytest.raises(g.RecoveryRefused):g.validate_authorization(d)
