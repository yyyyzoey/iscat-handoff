import tempfile
import unittest
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from contract_core import *


class TestCore(unittest.TestCase):
    def test_domain_inside(self):
        np.testing.assert_array_equal(require_theta([100,450,20,-30]),[100,450,20,-30])
    def test_domain_reject_not_clip(self):
        for p in ([201,450,0,0],[100,600,0,0],[100,450,501,0],[100,np.nan,0,0]):
            with self.assertRaises(ContractError): require_theta(p)
    def test_complex_before_cast(self):
        with self.assertRaises(ContractError): require_theta(np.array([100,450,0,0],complex)+1j)
    def test_exact_window_endpoints(self):
        t=np.array([0.,2.,5.,8.])
        u,w=window_nodes_weights(t,4.,5.)
        self.assertEqual(u[0],1.5);self.assertEqual(u[-1],6.5)
        self.assertAlmostEqual(w.sum(),1.)
        self.assertAlmostEqual(np.dot(w,2*u+3),11.)
    def test_partial_window_refused(self):
        with self.assertRaises(OutOfDomain):window_nodes_weights([0.,1.,2.],0.,1.)
    def test_coarse_uses_own_grid(self):
        tf=np.arange(-100.,1601.25,1.25);tc=tf[::2]
        for j in range(8):
            for T in (25.,100.):
                for t in (tf,tc):
                    u,w=window_nodes_weights(t,j*200.,T)
                    self.assertEqual(u[0],j*200.-T/2)
                    self.assertEqual(u[-1],j*200.+T/2)
                    self.assertAlmostEqual(w.sum(),1.)
    def test_path_physical_support(self):
        t=np.array([0.,1.,2.]);xyz=np.array([[0,0,450],[0,0,600],[0,0,450]])
        with self.assertRaises(OutOfDomain):sample_exposure_path(t,xyz,1.,2.,100.)
    def test_cp_exact(self):
        self.assertAlmostEqual(clopper_pearson_upper(0,60),.04870291331009746,14)
        self.assertAlmostEqual(clopper_pearson_upper(3,60),.12418721047743608,14)
        self.assertEqual(clopper_pearson_upper(60,60),1.)
        with self.assertRaises(ContractError):clopper_pearson_upper(61,60)
    def test_profile_endpoints_witness(self):
        g=profile_grid(step=4,witnesses=[67.48123236405084])
        self.assertIn(200.,g);self.assertIn(67.48123236405084,g)
    def flags(self):
        return dict(detection_required=True,detected=True,optimizer_converged=True,restart_stable=True,
                    forward_qualified=True,in_domain=True,profile_complete=True,identifiable=True,boundary_unresolved=False)
    def test_reportable_requires_identifiability(self):
        f=self.flags();f['identifiable']=False
        r=reportable_decision(100.,f)
        self.assertIsNone(r['reportable_D']);self.assertFalse(r['diameter_reportable'])
        self.assertEqual(r['candidate_D'],100.)
    def test_unknown_not_pass(self):
        f=self.flags();f['profile_complete']='True'
        self.assertFalse(reportable_decision(100,f)['diameter_reportable'])
    def test_budget_failure_counted_and_reservation_hard(self):
        with tempfile.TemporaryDirectory() as td:
            x=BudgetLedger(Path(td)/'budget.sqlite',{'bem':2})
            x.reserve('a','bem');x.finish('a',False)
            self.assertEqual(x.totals()['bem'],1)
            x.reserve('b','bem')
            with self.assertRaises(BudgetExceeded):x.reserve('c','bem')
            with self.assertRaises(ContractError):x.reserve('b','bem')
            self.assertEqual(x.totals()['bem'],2)
    def test_continuous_scalar_fixture_not_lattice(self):
        # Demonstrates a continuous optimizer on an identifiable analytic fixture.
        r=least_squares(lambda p:np.array([(p[0]-83.7)/10.]),[100.],bounds=([30.],[200.]),
                        x_scale=[50.],gtol=1e-12,ftol=1e-12,xtol=1e-10)
        self.assertLess(abs(r.x[0]-83.7),1e-6)
    def test_default_gtol_false_precision_fixture(self):
        r=least_squares(lambda p:np.array([1e-8*(p[0]-83.7)]),[100.],bounds=([30.],[200.]),
                        ftol=1e-12,xtol=1e-10)
        self.assertTrue(r.success)
        self.assertGreater(abs(r.x[0]-83.7),10.)

if __name__=='__main__': unittest.main(verbosity=2)
