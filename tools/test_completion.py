import sys,json,csv,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import fit_reference
from truth_and_score import score_rows,summarize,truth_from_sources
from profile_triage import triage
from complete_profile import targeted_profile,intervals,legacy_usable
from diagnose_existing import project_size_direction,local_jacobian

class Linear:
    Ds=np.array([30.,100.,200.]);Hs=np.array([350.,450.,550.]);xy_limit=500.
    model_id='SYNTHETIC_ONLY_INJECTIVE';n=2;s=2
    def forward(self,p):
        D,h,x,y=map(float,p)
        if not 30<=D<=200 or not 350<=h<=550 or abs(x)>500 or abs(y)>500:raise ValueError('outside')
        return SimpleNamespace(score_C=np.array([[D/100.,h/500.],[x/200.,y/200.]]))

class Tests(unittest.TestCase):
    def test_corrected_J_not_H_truth(self):
        c=[dict(data_set='J',case='J02',candidate_D='72.15291021799182',h='400.0497954963842')]
        t={('J','J02'):dict(D_nm=67,h_nm=402.5,source_sha256='test',scope='TEST')}
        r=score_rows(c,t)[0];self.assertTrue(r['size_error_target_met']);self.assertAlmostEqual(r['err_D'],5.15291021799182)
    def test_duplicate_candidate_rejected(self):
        c=[dict(data_set='J',case='J02',candidate_D='72',h='400')]*2
        t={('J','J02'):dict(D_nm=67,h_nm=402.5,source_sha256='test',scope='TEST')}
        with self.assertRaises(ValueError):score_rows(c,t)
    def test_missing_dataset_key_rejected(self):
        c=[dict(data_set='J',case='J02',candidate_D='72',h='400')]
        t={('H','J02'):dict(D_nm=67,h_nm=402.5,source_sha256='test',scope='TEST')}
        with self.assertRaises(ValueError):score_rows(c,t)
    def test_truth_source_key_collision_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'t.json';p.write_text(json.dumps([dict(case='J02',D_nm=67,h_nm=402.5,x_nm=0,y_nm=0)]*2))
            with self.assertRaises(ValueError):truth_from_sources(td,{'J':dict(path='t.json',format='cases_json')})
    def test_source_object_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td)/'t.json').write_text('[]')
            with self.assertRaises(ValueError):truth_from_sources(td,{'J':dict(path='t.json',format='cases_json',expected_git_blob='0'*40)})
    def test_publication_arithmetic_21_of_24(self):
        D={'H':[37,63,93,117,147,177],'J':[41,67,89,123,151,183],'K':[47,73,107,137,163,193],'L':[49,77,109,139,167,191]}
        truth={(s,f'{s}{i+1:02d}'):dict(D_nm=d,h_nm=400.,source_sha256='TRANSCRIBED_TEST_RECORD',scope='PUBLISHED_RECORD_NOT_SOLVE_VERIFIED') for s,ds in D.items() for i,d in enumerate(ds)}
        with (ROOT/'evidence/v131_candidates.csv').open() as f:c=list(csv.DictReader(f))
        summary=summarize(score_rows(c,truth));self.assertEqual(summary['ALL']['size_error_target_met'],21)
        self.assertAlmostEqual(summary['ALL']['MAE_nm'],3.7918055382955225)
        self.assertEqual(set(summary['not_within_target']),{'K_K02','L_L02','H_H03'})
    def test_status_zero_is_incomplete(self):
        p={'rows':[dict(D=50.,theta=[50,450,0,0],loss=1.,attempts=[dict(status=0,success=False,budget_exhausted=False)])],'profile_complete':True}
        r=triage(p);self.assertFalse(r['coarse_attempts_have_no_known_failure']);self.assertIn('MAX_NFEV_EXIT',r['repair_points'][0]['reasons'])
    def test_old_profile_complete_guard_counterexample(self):
        m=Linear();y=m.forward([83.7,420.,30.,-40.]).score_C;j=dict(theta=[83.7,420.,30.,-40.],loss=0.)
        def stopped(obj,x0,free,**kw):
            return dict(theta=list(x0),loss=None,status=0,success=False,budget_exhausted=False,canonical_calls=0)
        with patch.object(fit_reference,'solve_start',stopped):
            p=fit_reference.diameter_profile(m,y,j,step_nm=170.,total_calls=1000)
        self.assertTrue(p['profile_complete']) # Reproduces legacy criterion, not an endorsement.
        self.assertTrue(triage(p)['repair_points'])
    def test_legacy_failure_never_accepted(self):
        self.assertFalse(legacy_usable(dict(D=50,theta=[50,450,0,0],loss=1,attempts=[dict(status=0,success=False,budget_exhausted=False)])))
    def test_disjoint_empirical_intervals(self):
        r=[dict(D=d,loss=v) for d,v in zip([30,40,50,60,70],[2,.1,2,.1,2])]
        self.assertEqual(len(intervals(r,.2)),2)
    def test_support_touch_marked(self):
        r=[dict(D=30,loss=.1),dict(D=40,loss=2)]
        self.assertTrue(intervals(r,.2)[0]['touches_lower_support'])
    def test_profile_repair_and_not_automatic_reportability(self):
        m=Linear();t=[83.7,420.,30.,-40.];y=m.forward(t).score_C;j=dict(theta=t,loss=0.)
        p=targeted_profile(m,y,j,total_calls=5000,per_point_calls=1000,per_start_calls=500,max_nfev=80,screening_step=170,epsilon=None)
        self.assertTrue(p['coarse_and_scheduled_search_complete']);self.assertFalse(p['adaptive_refinement_complete']);self.assertIsNone(p['reportable_D'])
    def test_resume_observation_change_rejected(self):
        m=Linear();t=[83.7,420.,30.,-40.];y=m.forward(t).score_C;j=dict(theta=t,loss=0.)
        p=targeted_profile(m,y,j,total_calls=4000,per_point_calls=1000,per_start_calls=500,max_nfev=80,screening_step=170)
        with self.assertRaises(ValueError):targeted_profile(m,y+.01,j,total_calls=4000,per_point_calls=1000,per_start_calls=500,max_nfev=80,screening_step=170,resume=p)
    def test_wrong_legacy_model_rejected(self):
        m=Linear();t=[83.7,420.,0,0];j=dict(theta=t,loss=0.)
        with self.assertRaises(ValueError):targeted_profile(m,m.forward(t).score_C,j,old={'model_id':'OTHER','rows':[]})
    def test_legacy_wrong_loss_rejected(self):
        m=Linear();t=[83.7,420.,0,0];j=dict(theta=t,loss=0.)
        old=dict(model_id=m.model_id,rows=[dict(D=100.,theta=[100.,420.,0,0],loss=999.,attempts=[dict(status=1,success=True,budget_exhausted=False)])])
        with self.assertRaises(ValueError):targeted_profile(m,m.forward(t).score_C,j,old=old)
    def test_projection_separable(self):
        J=np.eye(4);e=np.array([2.,3.,4.,5.]);r=project_size_direction(J,e)
        for x in r:self.assertAlmostEqual(x['predicted_delta_D_local_nm'],2.)
    def test_projection_degenerate_is_not_reported(self):
        J=np.eye(4);J[:,0]=J[:,1];r=project_size_direction(J,np.ones(4))
        self.assertTrue(all(x['predicted_delta_D_local_nm'] is None for x in r))
    def test_physical_finite_difference(self):
        J=local_jacobian(Linear(),[83.7,420.,0,0]);np.testing.assert_allclose(J,np.diag([.01,.002,.005,.005]),atol=1e-12)
    def test_budget_plan(self):
        c=json.loads((ROOT/'config/v132_science_config.json').read_text());p=c['camera'];m=c['motion']
        s=(len(p['dev_D_nm'])*len(p['dev_h_nm'])*3*p['dev_target_repeats']+3*p['dev_blanks_per_B']+3*p['validation_blanks_per_B']+6*3*p['new_holdout_noise_repeats_per_B'])*(1+p['refs_per_measurement'])
        motion=len(m['D_generation_nm'])*m['tracks_per_D']*len(m['exposure_us'])*(m['frames_per_track']+m['shared_reference_frames_per_track_and_exposure'])
        self.assertEqual(s+motion,4782);self.assertLessEqual(s+motion,c['budget']['synthetic_camera_exposure_events_max'])
    def test_inherited_core_unchanged(self):
        import hashlib
        c=json.loads((ROOT/'config/v132_science_config.json').read_text())
        for n,h in c['inherited_core_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/'tools'/n).read_bytes()).hexdigest(),h)

if __name__=='__main__':unittest.main()
