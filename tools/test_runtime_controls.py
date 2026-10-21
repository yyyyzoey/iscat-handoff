import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import numpy as np
from runtime_controls import Ledger,BudgetExceeded,cp_upper,exposure_nodes,reportable
class RuntimeTests(unittest.TestCase):
    def test_budget_failure_consumes(self):
        with tempfile.TemporaryDirectory() as d:
            l=Ledger(Path(d)/'b.sqlite',{'bem':2});a=l.reserve('bem');l.finish(a,False)
            b=l.reserve('bem');l.finish(b,True)
            with self.assertRaises(BudgetExceeded):l.reserve('bem')
            self.assertEqual(l.counts()['bem'],2)
    def test_binomial(self):
        self.assertAlmostEqual(cp_upper(0,60),.04870291331009746)
        self.assertAlmostEqual(cp_upper(1,60),.07663999493450441)
        self.assertEqual(cp_upper(60,60),1)
    def test_nonuniform_endpoint_weights(self):
        t=np.array([-20.,-5.,0.,7.,20.]);p=np.column_stack([t,2*t,450+t])
        q,r,w=exposure_nodes(t,p,1.,25.7)
        self.assertAlmostEqual(q[0],1-25.7/2);self.assertAlmostEqual(q[-1],1+25.7/2)
        self.assertAlmostEqual(float(w.sum()),1.);np.testing.assert_allclose(w@r,[1,2,451])
    def test_window_not_fully_covered_rejected(self):
        with self.assertRaises(ValueError):exposure_nodes([0,1],[[0,0,450],[1,1,450]],0,2)
    def test_missing_quality_gate_rejects(self):
        r=reportable(99.,{'detected':True,'optimizer_complete':True})
        self.assertFalse(r['diameter_reportable']);self.assertIsNone(r['reportable_D'])
if __name__=='__main__':unittest.main()
