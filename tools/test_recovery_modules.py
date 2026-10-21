import sys,unittest,tempfile,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import numpy as np,h5py
from types import SimpleNamespace
from load_field_library import load_library
from field_forward_reference import pixel_mean
from fit_reference import Objective,BudgetStop,fit_single,fit_shared_D,diameter_profile

class LinearIdentifiable:
    Ds=np.array([30.,70.,130.,200.]);Hs=np.array([350.,400.,450.,500.,550.])
    xy_limit=500.;model_id='TEST_ONLY_LINEAR_IDENTIFIABLE'
    def forward(self,t):
        d,h,x,y=t
        return SimpleNamespace(score_C=np.array([[d/100.,h/500.],[x/500.,y/500.]]))

class Fits(unittest.TestCase):
    def test_single_continuous(self):
        m=LinearIdentifiable();true=[83.7,433.2,23.1,-37.4]
        r=fit_single(m,m.forward(true).score_C,total_calls=5000,max_starts=4)
        self.assertLess(np.linalg.norm(np.array(r['theta'])-true),1e-4)
        self.assertIsNone(r['reportable_D'])
    def test_budget_does_not_change_objective(self):
        m=LinearIdentifiable();o=Objective(m,m.forward([80,420,0,0]).score_C,2)
        a=o.evaluate([70,410,1,2]);b=o.evaluate([70,410,1,2]);np.testing.assert_array_equal(a,b)
        with self.assertRaises(BudgetStop):o.evaluate([70,410,1,2])
    def test_shared_D_is_really_continuous(self):
        m=LinearIdentifiable();frames=[m.forward([83.7,410+8*k,30-3*k,-20+7*k]).score_C for k in range(3)]
        r=fit_shared_D(m,frames,total_calls=30000,max_nfev=100)
        self.assertLess(abs(r['candidate_D']-83.7),1e-3)
        self.assertIsNone(r['reportable_D'])
    def test_profile_includes_joint_and_endpoints(self):
        m=LinearIdentifiable();Y=m.forward([83.7,430.,20.,-30.]).score_C
        j=fit_single(m,Y,total_calls=5000,max_starts=3)
        r=diameter_profile(m,Y,j,step_nm=35,total_calls=100000)
        ds=[x['D'] for x in r['rows']]
        self.assertIn(30.,ds);self.assertIn(200.,ds);self.assertIn(j['theta'][0],ds)
        witness=min(r['rows'],key=lambda x:abs(x['D']-j['theta'][0]))
        self.assertLessEqual(witness['loss'],j['loss']+1e-12)

class Loader(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name)/'f.h5'
        ds=[30.,70.,120.,200.];hs=[350.,387.5,450.,550.]
        x=(np.arange(125)-62)*56.;X,Y=np.meshgrid(x,x,indexing='ij')
        er=np.zeros((125,125,3),complex);er[...,0]=1
        with h5py.File(self.p,'w') as h:
            for d in ds:
                for z in hs:
                    es=np.zeros_like(er);es[...,0]=.03*(d/100)**2*np.exp(-(X*X+Y*Y)/1e6)*np.exp(1j*z/110.)
                    g=h.create_group(f'D{d:g}_h{z:g}')
                    g.attrs.update(D_nm=d,h_nm=z,n_particle=1.38,NA=.8,object_pixel_nm=280.,mesh=576)
                    g.create_dataset('Eref',data=er[20:105,20:105]);g.create_dataset('Esca',data=es[20:105,20:105])
                    c=(pixel_mean(np.sum(abs(er[20:105,20:105]+es[20:105,20:105])**2,-1),5)-1)
                    g.create_dataset('C',data=c)
                    w=g.create_group('wide')
                    w.create_dataset('Eref',data=er,compression='gzip');w.create_dataset('Esca',data=es,compression='gzip')
                    w.create_dataset('fine_x_nm',data=x);w.create_dataset('fine_y_nm',data=x)
    def tearDown(self):self.tmp.cleanup()
    def test_load_dynamic_irregular_axis(self):
        m,r=load_library(self.p)
        self.assertIn(387.5,m.Hs);self.assertTrue(r['array_checks_passed'])
        o=m.forward([70.,387.5,28.,-28.]);self.assertEqual(o.score_C.shape,(13,13))
        np.testing.assert_array_equal(o.score_C,m.C(70.,387.5,28.,-28.))
    def test_mismatched_attr_rejected(self):
        with h5py.File(self.p,'r+') as h:h['D30_h350'].attrs['h_nm']=450.
        with self.assertRaises(ValueError):load_library(self.p)
    def test_bad_stored_C_rejected(self):
        with h5py.File(self.p,'r+') as h:h['D30_h350/C'][8,8]=.55
        with self.assertRaises(ValueError):load_library(self.p)
    def test_missing_wide_rejected(self):
        with h5py.File(self.p,'r+') as h:del h['D30_h350/wide']
        with self.assertRaises(ValueError):load_library(self.p)

if __name__=='__main__':unittest.main()
