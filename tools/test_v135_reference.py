import json,math,tempfile,unittest,sys
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'tools'))
from fail_closed_reportability import evaluate,REQUIRED
from audit_published_results import audit,_stats


def valid_gates():
    x={n:True for n in REQUIRED}
    x['observable_type']='SIGNED_STATIC_C_FROM_LINEAR_INTENSITY'
    x['measurement_mode']='NOISY_CAMERA'
    return x

class PublishedEvidenceTests(unittest.TestCase):
    def test_F2_stats(self):
        x=audit();self.assertAlmostEqual(x['v133_F2']['MAE_nm'],2.751917769836067,places=12)
        self.assertEqual(x['v133_F2']['size_error_target_only_pass'],6)
    def test_Cmap_target_is_three_not_two(self):
        x=audit();self.assertEqual(x['v134_coarse_Cmap']['size_error_target_only_pass'],3)
        self.assertEqual(x['v134_size_target_pass_cases'],['M01','M05','M06'])
        self.assertAlmostEqual(x['v134_coarse_Cmap']['MAE_nm'],36.333333333333336)
    def test_published_false_positive_cases(self):
        x=audit();self.assertEqual(x['v134_published_reportable_true'],['M01','M02','M05'])
        self.assertEqual([q['case'] for q in x['v134_unsafe_reportability_rows']],['M01','M02','M05'])
        self.assertEqual(x['v134_science_gate'],'NOT_ACCEPTED')
    def test_no_truth_error_as_acceptance(self):
        self.assertEqual(_stats([171],[155])['size_error_target_only_pass'],1) # 16 <= 17.1

class FailClosedTests(unittest.TestCase):
    def test_valid_small_interval(self):
        x=evaluate(100,[[95,105]],valid_gates());self.assertEqual(x['reportable_D'],100.0)
    def test_all_domain_rejected(self):
        x=evaluate(135,[[30,200]],valid_gates());self.assertIsNone(x['reportable_D']);self.assertIn('COMPATIBILITY_TOO_WIDE',x['reason_codes'])
    def test_zero_science_gates_even_if_good_point(self):
        x=evaluate(100,[[95,105]],{});self.assertIsNone(x['reportable_D'])
    def test_missing_one_required_gate(self):
        g=valid_gates();g.pop('same_solve_forward_qualified');x=evaluate(100,[[95,105]],g);self.assertIsNone(x['reportable_D'])
    def test_nonunique(self):
        x=evaluate(100,[[95,100],[101,105]],valid_gates());self.assertIsNone(x['reportable_D'])
    def test_touches_boundary(self):
        x=evaluate(35,[[30,38]],valid_gates());self.assertIsNone(x['reportable_D'])
    def test_too_wide(self):
        x=evaluate(100,[[75,125]],valid_gates());self.assertIsNone(x['reportable_D'])
    def test_noiseless_not_claimed(self):
        g=valid_gates();g['measurement_mode']='CLEAN_MODEL_DIAGNOSTIC';x=evaluate(100,[[95,105]],g);self.assertIsNone(x['reportable_D'])
    def test_FFT_observable_not_static(self):
        g=valid_gates();g['observable_type']='FFT_400HZ_AMPLITUDE';x=evaluate(100,[[95,105]],g);self.assertIsNone(x['reportable_D'])
    def test_truth_leak(self):
        g=valid_gates();g['D_true']=100;x=evaluate(100,[[95,105]],g);self.assertIsNone(x['reportable_D'])
    def test_invalid_interval(self):
        x=evaluate(100,[[105,95]],valid_gates());self.assertIsNone(x['reportable_D'])
    def test_boundary_candidate(self):
        x=evaluate(200,[[194,200]],valid_gates());self.assertIsNone(x['reportable_D'])
    def test_nan(self):
        x=evaluate(math.nan,[[95,105]],valid_gates());self.assertIsNone(x['reportable_D'])
    def test_missing_components(self):
        x=evaluate(100,[],valid_gates());self.assertIsNone(x['reportable_D'])
    def test_false_exact_booleans(self):
        g=valid_gates();g['profile_complete']=1;x=evaluate(100,[[95,105]],g);self.assertIsNone(x['reportable_D'])

if __name__=='__main__':unittest.main()
