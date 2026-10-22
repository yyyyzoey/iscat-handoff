import sys,unittest,json,tempfile,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from check_workflow import check,REQUIRED
class Tests(unittest.TestCase):
 def test_offline_not_full(self):
  with tempfile.TemporaryDirectory() as td:self.assertFalse(check(td,{'execution':'OFFLINE_RECOVERY_COMPLETE'})['task_execution_and_evidence_complete'])
 def test_word_pass_not_enough(self):
  with tempfile.TemporaryDirectory() as td:self.assertFalse(check(td,{'passed':False,'verdict':'PASS'})['task_execution_and_evidence_complete'])
 def test_complete_execution_can_contain_failed_performance(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'evidence.json';p.write_text('{"performance_pass": false}')
   out={'path':'evidence.json','sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
   state={'task_id':'V132_QUALIFIED_PROFILES_AND_EXPERIMENT_READY_PARTICLE_SIZING','EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED':False,
          'stages':{k:{'execution':'COMPLETED','evidence':'COMPLETE','validation':'FAIL','outputs':[out]} for k in REQUIRED}}
   r=check(td,state);self.assertTrue(r['task_execution_and_evidence_complete']);self.assertFalse(r['scientific_validation_independently_certified'])
   p.write_text('tampered');self.assertFalse(check(td,state)['task_execution_and_evidence_complete'])
if __name__=='__main__':unittest.main()
