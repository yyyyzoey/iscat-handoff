import copy,hashlib,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'))
from v167_plan import (build_plan,RECOVERY,GROUPS,expected_old_ids,one_reading,theta_ok,
                      validate_payload,PHASES,pinned_json,write_new,canon)
from v167_payload_gate import validate


def fixture_data():
 estimates=[]; readings=[]; starts={}; pending={}
 for g in GROUPS:
  estimates.append({'task_id':f'B100000_{g}_NO_HEIGHT','execution_state':'FINISHED'})
  starts[g]={'first':{'theta':[80.,430.,0.,0.]},'second':{'theta':[100.,480.,20.,-20.]}}
  for s in (1,10):
   for r in range(3):
    tid=f'B100000_{g}_H{s}_R{r:02d}'
    estimates.append({'task_id':tid,'execution_state':'PARTIAL_SEARCH' if tid in RECOVERY else 'FINISHED'})
    readings.append({'reading_id':tid,'group':g,'B':100000,'replicate':r,'sigma_nm':float(s),'z_nm':430.+r*s/10,'hypothetical':True,'arbitrary_generator_metadata':'not_for_solver'})
 for tid in RECOVERY:
  pending[tid]={'execution_state':'PARTIAL_SEARCH','start_index':1,'actual_calls':200,
                'error':{'error_type':'CallCapReached'},'best':{'theta':[85.,429.,1.,-1.]}}
 return estimates,{'readings':readings,'seed':'controller_only','truth_file_sha256':'controller_only'},starts,pending


def test_exact_task_matrix():
 m,p=build_plan(*fixture_data())
 assert len(p)==23
 assert sum(e['kind']=='SEARCH_EXTENSION' for e in m['entries'])==5
 assert sum(e['kind']=='BIAS_STRESS' for e in m['entries'])==18
 assert sum(PHASES.values())==10000
 for v in p.values():assert validate(v)==v


def test_metadata_removed_but_data_preserved():
 e,r,s,w=fixture_data();m,p=build_plan(e,r,s,w);rm={v['reading_id']:v for v in r['readings']}
 for row in m['entries']:
  payload=p[row['task_id']]; base=rm[row['source_task_id']]
  assert payload['reading']['z_nm']==base['z_nm']+row.get('controlled_offset_nm',0)
  assert 'seed' not in canon(payload).decode() and 'truth' not in canon(payload).decode()
  assert 'controlled_offset_nm' not in canon(payload).decode()


def test_bias_reuses_original_starts_both_signs_and_all_replicates():
 e,r,s,w=fixture_data();m,p=build_plan(e,r,s,w)
 for row in m['entries']:
  if row['kind']=='BIAS_STRESS':
   assert p[row['task_id']]['starts']==[s[row['group']][k]['theta'] for k in ('first','second')]
   assert p[row['task_id']]['reading']['sigma_nm']==1.


def test_pending_warm_start_not_original_start():
 e,r,s,w=fixture_data();m,p=build_plan(e,r,s,w)
 for row in m['entries']:
  if row['kind']=='SEARCH_EXTENSION':
   assert p[row['task_id']]['starts']==[w[row['source_task_id']]['best']['theta']]
   assert p[row['task_id']]['cap_per_start']==400


def test_deterministic_plan_and_no_mutation():
 args=fixture_data();old=copy.deepcopy(args)
 assert build_plan(*args)==build_plan(*args)
 assert args==old


@pytest.mark.parametrize('key',['seed','epsilon','truth_file_sha256','h_true','D_true','reading_map','all_readings','controlled_offset_nm'])
def test_worker_rejects_extra_top_fields(key):
 _,p=build_plan(*fixture_data());d=copy.deepcopy(next(iter(p.values())));d[key]='blocked'
 with pytest.raises(ValueError):validate(d)


@pytest.mark.parametrize('key',['seed','epsilon','truth_file_sha256','h_scene_nm','D_scene_nm','readings','bias_nm'])
def test_worker_rejects_extra_reading_fields(key):
 _,p=build_plan(*fixture_data());d=copy.deepcopy(next(iter(p.values())));d['reading'][key]='blocked'
 with pytest.raises(ValueError):validate(d)


@pytest.mark.parametrize('which',[0,1,2,3])
def test_no_clip(which):
 t=[80.,430.,0.,0.];t[which]=[201.,551.,501.,-501.][which]
 with pytest.raises(ValueError):theta_ok(t)


def test_partial_set_cannot_be_changed():
 e,r,s,w=fixture_data();next(x for x in e if x['task_id'] in RECOVERY)['execution_state']='FINISHED'
 with pytest.raises(ValueError):build_plan(e,r,s,w)


def test_failures_are_not_reclassified_as_budget_stops():
 e,r,s,w=fixture_data();w[RECOVERY[0]]['error']['error_type']='RuntimeError'
 with pytest.raises(ValueError):build_plan(e,r,s,w)


def test_missing_best_blocks():
 e,r,s,w=fixture_data();w[RECOVERY[0]]['best']=None
 with pytest.raises(ValueError):build_plan(e,r,s,w)


def test_missing_reading_blocks():
 e,r,s,w=fixture_data();r['readings'].pop()
 with pytest.raises(ValueError):build_plan(e,r,s,w)


def test_duplicate_reading_blocks():
 e,r,s,w=fixture_data();r['readings'][-1]=r['readings'][0]
 with pytest.raises(ValueError):build_plan(e,r,s,w)


def test_source_blob_identity(tmp_path):
 raw=b'{"value":1}\n';p=tmp_path/'a.json';p.write_bytes(raw)
 expected=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
 assert pinned_json(p,expected)=={'value':1}
 p.write_bytes(raw+b' ')
 with pytest.raises(ValueError):pinned_json(p,expected)


def test_never_overwrite(tmp_path):
 p=tmp_path/'x.json';write_new(p,{'state':'PARTIAL_SEARCH'})
 with pytest.raises(FileExistsError):write_new(p,{'state':'FINISHED'})
 assert b'PARTIAL_SEARCH' in p.read_bytes()


def test_pair_can_algebraically_reveal_center_audit_fixture_only():
 h=430.;eps=.35;z1=h+eps;z10=h+10*eps
 assert abs((10*z1-z10)/9-h)<1e-12


def test_all_modes_fixed_condition_not_known_bias_compensation():
 m,p=build_plan(*fixture_data())
 for row in m['entries']:
  if row['kind']=='BIAS_STRESS':
   inp=p[row['task_id']]
   assert 'bias' not in inp['task_id'].lower()
   assert set(inp['reading'])=={'reading_id','group','B','replicate','sigma_nm','z_nm','hypothetical'}
