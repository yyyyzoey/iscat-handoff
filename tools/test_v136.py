import json
import math
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from audit_v134_v135 import score,CASE_IDS
from fail_closed_reportability import evaluate,REQUIRED
from profile_science_gate import check

class AuditMath(unittest.TestCase):
    def setUp(self):
        self.truth=dict(zip(CASE_IDS,[53,81,119,149,171,187]))
        self.f2=dict(zip(CASE_IDS,[48.421809635083875,81.27358906303667,122.11998103353119,151.07969710737842,167.83725685498712,190.29730590514112]))
        self.cmap=dict(zip(CASE_IDS,[50.,135.,200.,200.,155.,200.]))

    def test_f2_6of6(self):
        p=score(self.f2,self.truth)
        self.assertAlmostEqual(p['MAE_nm'],2.751917769836067,places=9)
        self.assertEqual(len(p['target_pass_cases']),6)

    def test_v134_Cmap_target_three_not_two(self):
        p=score(self.cmap,self.truth)
        self.assertAlmostEqual(p['MAE_nm'],36.33333333333333)
        self.assertEqual(p['target_pass_cases'],['M01','M05','M06'])

    def test_new_v135_profile_grid_minima_are_not_f2_candidates(self):
        v=dict(zip(CASE_IDS,[50,75,120,150,30,45]))
        self.assertGreater(abs(v['M05']-self.f2['M05']),130.)
        self.assertGreater(abs(v['M06']-self.f2['M06']),140.)

class FailClosed(unittest.TestCase):
    def complete(self):
        a={x:True for x in REQUIRED}
        a.update(observable_type='SIGNED_STATIC_C_FROM_LINEAR_INTENSITY',measurement_mode='NOISY_CAMERA')
        return a

    def test_small_unique_good_when_all_gates_are_true(self):
        a=evaluate(100.0,[[95.,105.]],self.complete())
        self.assertEqual(a['reportable_D'],100.)

    def test_full_support_is_not_reportable(self):
        a=evaluate(135.,[[30.,200.]],self.complete())
        self.assertIsNone(a['reportable_D'])
        self.assertIn('COMPATIBILITY_TOO_WIDE',a['reason_codes'])

    def test_two_components_are_not_reportable(self):
        self.assertIsNone(evaluate(100.,[[90.,100.],[101.,110.]],self.complete())['reportable_D'])

    def test_missing_physics_gate_is_not_reportable(self):
        a=self.complete();a.pop('same_solve_forward_qualified')
        self.assertIsNone(evaluate(100.,[[95.,105.]],a)['reportable_D'])

    def test_truth_cannot_go_into_estimator_gate(self):
        a=self.complete();a['D_true']=100.
        self.assertIsNone(evaluate(100.,[[95.,105.]],a)['reportable_D'])

    def test_clean_simulation_is_not_noisy_camera_certification(self):
        a=self.complete();a['measurement_mode']='CLEAN_MODEL_DIAGNOSTIC'
        self.assertIsNone(evaluate(100.,[[95.,105.]],a)['reportable_D'])

    def test_FFT_amplitude_cannot_use_static_C_gate(self):
        a=self.complete();a['observable_type']='FFT_400HZ_AMPLITUDE'
        self.assertIsNone(evaluate(100.,[[95.,105.]],a)['reportable_D'])

    def test_exact_booleans_required(self):
        a=self.complete();a['profile_complete']=1
        self.assertIsNone(evaluate(100.,[[95.,105.]],a)['reportable_D'])

class ProfileGate(unittest.TestCase):
    def base(self):
        return dict(model_id='f2-same', observation_sha256='obs',loss_type='UNSCALED_L2_SAME_13x13_SIGNED_C',
         profile_complete=True,adaptive_coverage_complete=True,joint_update_performed=False,
         rows=[{'D':30.,'theta':[30.,450.,0.,0.],'loss':1.,'point_search_complete':True,'attempts':[{'status':2}]},
               {'D':83.7,'theta':[83.7,450.,0.,0.],'loss':0.01,'point_search_complete':True,'attempts':[{'status':2}]},
               {'D':200.,'theta':[200.,450.,0.,0.],'loss':1.,'point_search_complete':True,'attempts':[{'status':2}]}])
    def gate(self,p):return check(p,expected_model_id='f2-same',expected_observation_sha='obs',joint_D=83.7,joint_loss=.01)

    def test_structural_precondition_passes(self):
        self.assertTrue(self.gate(self.base())['structurally_qualified'])

    def test_missing_model_binding_fails(self):
        a=self.base();a.pop('model_id');self.assertFalse(self.gate(a)['structurally_qualified'])

    def test_missing_exact_joint_witness_fails(self):
        a=self.base();a['rows'][1]['D']=85.;a['rows'][1]['theta'][0]=85.
        self.assertIn('JOINT_D_WITNESS_NOT_INCLUDED',self.gate(a)['reason_codes'])

    def test_missing_per_D_optimization_evidence_fails(self):
        a=self.base();a['rows'][1]['attempts']=[]
        self.assertIn('NO_START_EXIT_EVIDENCE',self.gate(a)['reason_codes'])

    def test_dropping_known_best_at_identical_D_fails(self):
        a=self.base();a['rows'][1]['loss']=.03
        self.assertIn('PROFILE_DROPS_KNOWN_SAME_D_JOINT_WITNESS',self.gate(a)['reason_codes'])

    def test_better_profile_requires_joint_reconciliation(self):
        a=self.base();a['rows'][1]['loss']=.005
        self.assertIn('PROFILE_BETTER_THAN_UNRECONCILED_JOINT',self.gate(a)['reason_codes'])

    def test_incomplete_profile_is_not_compliant(self):
        a=self.base();a['profile_complete']=False
        self.assertIn('PROFILE_SEARCH_NOT_COMPLETE',self.gate(a)['reason_codes'])

class Config(unittest.TestCase):
    def test_camera_budget(self):
        a=json.loads((ROOT/'config/v136_science_config.json').read_text())
        c=a['camera'];m=a['motion'];b=a['hard_budget_new_work']
        dev=len(c['dev_D_nm'])*len(c['dev_h_nm'])*len(c['B_e_per_pixel'])*c['dev_target_repetitions']
        blanks=len(c['B_e_per_pixel'])*(c['dev_blanks_per_B']+c['independent_validation_blanks_per_B'])
        M=len(a['M_case_ids'])*len(c['B_e_per_pixel'])*c['M_opened_development_repetitions_per_B']
        self.assertEqual((dev+blanks+M)*(1+c['reference_frames']),4590)
        self.assertEqual(len(m['D_nm'])*m['n_paths_each_D']*len(m['exposure_us'])*(m['frames_each_path']+c['reference_frames']),192)
        self.assertEqual(b['nominal_combined_camera_events'],4782)
        self.assertLessEqual(4782,b['synthetic_camera_exposure_events'])

    def test_never_claim_experimental_absolute(self):
        a=json.loads((ROOT/'config/v136_science_config.json').read_text())
        self.assertIs(a['EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED'],False)
        self.assertEqual(a['hard_budget_new_work']['BEM_solver_attempts'],0)

if __name__=='__main__':unittest.main()

# Integration fixture deliberately appended below the direct unittest entrypoint;
# the test runner discovers it independently even though __main__ is above.
class ReadOnlyAuditIntegration(unittest.TestCase):
    def test_audit_reads_actual_repo_shaped_inputs_without_missing_embedded_evidence(self):
        import csv, tempfile
        from audit_v134_v135 import audit
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            def save(rel,text):
                p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
            truth=[53,81,119,149,171,187]
            data={'cases':[{'tag':f'holdout_M{i:02d}','D_nm':v} for i,v in enumerate(truth,1)]}
            save('results/v126/v132_M_cases.json',json.dumps(data))
            f2=[48.421809635083875,81.27358906303667,122.11998103353119,151.07969710737842,167.83725685498712,190.29730590514112]
            model='v131-field-db000d86636ed018cf1f9bd5291c7409b7e9d2aaa481328b3c22dfdb1a689427'
            save('results/v133/M_F2_baseline/M_F2_candidates.csv','case,model_id,candidate_D\n'+''.join(f'M{i:02d},{model},{v}\n' for i,v in enumerate(f2,1)))
            coarse=[50,135,200,200,155,200]
            props=[{'case':f'M{i:02d}','best_D':v,'compatible':[[30.,200.]],'reportable':i in (1,2,5)} for i,v in enumerate(coarse,1)]
            save('results/v134/reportability.json',json.dumps(props))
            save('results/v134/status.json',json.dumps({'fixed_v133_commit':'cc8722bba7af19e2296665fe562f24ab2afcb077'}))
            for i,Dm in enumerate([50,75,120,150,30,45],1):
                grid=[{'D':float(d),'loss':abs(d-Dm)+1.,'h':450.,'x':0.,'y':0.} for d in range(30,201,5)]
                save(f'results/v135/profiles/M{i:02d}.json',json.dumps({'case':f'M{i:02d}','profile':grid}))
            save('tools/v135_run_profiles.py','import v129_field_forward as ff\nM_truth = {}\nfor D in D_grid:\n  except Exception:\n    return np.full(Cobs.size, 1e6)\n  warm = [450.,0.,0.]\n')
            result=audit(root)
            self.assertEqual(result['science_verdict'],'PARTIAL_UNQUALIFIED__NO_REPORTABLE_SIZE_CERTIFIED')
            self.assertEqual(result['v134_published_reportable_true'],['M01','M02','M05'])
            self.assertEqual(result['v134_coarse_Cmap_statistics']['target_pass_cases'],['M01','M05','M06'])
            self.assertEqual(len(result['v135_new_profiles']),6)
            self.assertIn('evidence/published_values.json',result['missing_expected_files'])
            self.assertEqual(result['v134_historical_zip_changed_in_descendant'],'NOT_EVALUATED_MISSING_GIT_OBJECT')
