import json, sqlite3, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'audit'))
from audit_existing_v155 import audit, EXPECTED_GROUPS

def test_readonly_detects_twelve_uniform_fake_anchor(tmp_path):
    root=tmp_path/'results'/'v155'
    (root/'logs').mkdir(parents=True)
    for name in EXPECTED_GROUPS:
        d=root/'groups'/name;d.mkdir(parents=True)
        (d/'result.json').write_text(json.dumps({'execution_state':'FINISHED',
             'actual_forward_attempts':20,'diagnostic':{'theta':[200.,450.,0.,0.],
             'status':'BOUNDARY_LOCAL_DIAGNOSTIC_ONLY','predictions':[{}]*20}}))
        (d/'predictions').mkdir()
    c=sqlite3.connect(root/'logs'/'v155_budget.sqlite')
    c.executescript('CREATE TABLE metadata(id integer,value text);'
                    'CREATE TABLE tasks(id text,phase text,cap integer,used integer,state text);'
                    'CREATE TABLE attempts(task text,state text);')
    c.execute('INSERT INTO metadata VALUES(1,?)',(json.dumps({'plan_id':'v155','total':900}),))
    for name in EXPECTED_GROUPS:
        c.execute('INSERT INTO tasks VALUES(?,?,?,?,?)',(name,'LOCAL_INFORMATION',40,20,'FINISHED'))
        c.executemany('INSERT INTO attempts VALUES(?,?)',[(name,'RETURNED')]*20)
    c.commit();c.close()
    result=audit(tmp_path)
    assert result['all_at_same_artificial_anchor']
    assert result['all_boundary_only']
    assert result['sqlite_integrity_check']=='ok'
    assert result['sqlite_attempts']==240
    assert result['sqlite_reserved']==480
    assert result['sqlite_used']==240
    assert result['assessment']=='INVALID_FOR_ACTUAL_CANDIDATE_LOCAL_INFORMATION'
