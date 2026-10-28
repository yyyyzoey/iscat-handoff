import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'))
sys.path.insert(0,str(ROOT/'generator'))
sys.path.insert(0,str(ROOT/'validator'))
from v165_generate_height import generate
from v165_task_ids import tasks
from v165_validator import validate

def fixture():
 t={'cases':[{'case':f'N{i:02d}','D_nm':d,'h_nm':h} for i,d,h in [(1,59,391.25),(2,101,432.5),(3,143,478.75),(4,181,526.25)]]}
 rd,_=generate(t);inp={'readings':rd}
 r=[{'task_id':x['task_id'],'execution_state':'FINISHED','theta':[101,432.5,0,0]} for x in tasks()]
 return r,t,inp,{g:[True,False,True] for g in ('ANON_01','ANON_02','ANON_03','ANON_04')}

def test_group_mae_preserves_four_independent_scenes():
 r,t,inp,det=fixture();o=validate(r,t,inp,det)
 assert len(o['task_rows'])==28
 assert o['summary']['H1']['group_n']==4
 assert o['summary']['H1']['groups'][0]['planned']==3
 assert o['summary']['H1']['fully_complete']
 assert o['all_reportable_D_null']
 assert o['summary']['H10']['conditional_group_MAE_nm']==o['summary']['NO_HEIGHT']['conditional_group_MAE_nm']

def test_partial_status_is_not_hidden():
 r,t,inp,det=fixture();r[2]['execution_state']='BLOCKED';r[2]['theta']=None
 o=validate(r,t,inp,det)
 assert not o['summary']['H1']['fully_complete'] and o['summary']['H1']['conditional_group_MAE_nm'] is None

def test_missing_task_fails_not_silent():
 r,t,inp,det=fixture()
 with pytest.raises(ValueError):validate(r[:-1],t,inp,det)

def test_wrong_height_group_binding_rejected():
 r,t,inp,det=fixture();inp['readings'][0]['group']='ANON_04'
 with pytest.raises(ValueError):validate(r,t,inp,det)
