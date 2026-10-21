import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
"""Synthetic numerical tests only. They do NOT qualify project BEM fields."""
import unittest
import numpy as np
from field_forward_reference import FieldForward, OutOfDomain, sample_complex

D=np.array([30.,50.,100.,200.]); H=np.array([350.,375.,387.5,450.,550.])
X=np.arange(-15.,16.); Y=X.copy()

def fixture(kind='F1',scaled=False,dx_limit=3):
    shape=(len(D),len(H),len(X),len(Y),3)
    er=np.zeros(shape,complex);es=np.zeros(shape,complex);er[...,0]=1.0+.2j
    spatial=1.+.01*X[:,None]+.02*Y[None,:]
    for i,d in enumerate(D):
        for j,h in enumerate(H):
            f=(d/100.)**3 if scaled else .4+.002*d+1e-5*d*d+2e-8*d**3
            a=.005*f*(1.+.001*(h-450)+1e-8*(h-450)**3)
            es[i,j,:,:,0]=a*spatial*(1+.3j)
    m=FieldForward(D,H,X,Y,er,es,kind=kind,pixel_nm=1,q=1,camera_n=17,score_n=13,
                   xy_limit_nm=dx_limit)
    return m,er,es

class Tests(unittest.TestCase):
    def test_node_recovery_all_candidates(self):
        for kind in ('F1','F2','F3'):
            m,er,es=fixture(kind)
            for i,d in enumerate(D):
                for j,h in enumerate(H):
                    _,v=m.fields(d,h)
                    self.assertLess(np.max(np.abs(v-es[i,j])),2e-14)
    def test_cubic_physical_nonuniform_axes(self):
        m,_,_=fixture('F2');d=83.7;h=411.2
        f=.4+.002*d+1e-5*d*d+2e-8*d**3
        a=.005*f*(1+.001*(h-450)+1e-8*(h-450)**3)
        expected=a*(1+.01*X[:,None]+.02*Y[None,:])*(1+.3j)
        self.assertLess(np.max(np.abs(m.fields(d,h)[1][...,0]-expected)),2e-14)
    def test_scaled_cubic(self):
        m,_,_=fixture('F3',True);d=83.7;h=411.2
        a=.005*(d/100)**3*(1+.001*(h-450)+1e-8*(h-450)**3)
        expect=a*(1+.01*X[:,None]+.02*Y[None,:])*(1+.3j)
        self.assertLess(np.max(np.abs(m.fields(d,h)[1][...,0]-expect)),2e-14)
    def test_no_node_jump(self):
        m,_,_=fixture('F2')
        self.assertLess(np.max(np.abs(m.fields(50+1e-8,387.5)[1]-m.fields(50,387.5)[1])),1e-10)
    def test_single_entry_alias(self):
        m,_,_=fixture();p=(60.,400.,1.5,-2.)
        self.assertTrue(np.array_equal(m.forward(p).score_C,m.C(*p)))
        self.assertTrue(np.array_equal(m.forward(p).C,m.C(*p,score=False)))
    def test_nonzero_shift_analytic(self):
        m,_,_=fixture('F2');d,h,x,y=83.7,411.2,1.5,-2.
        r=m.forward((d,h,x,y))
        q=m.query
        f=.4+.002*d+1e-5*d*d+2e-8*d**3
        a=.005*f*(1+.001*(h-450)+1e-8*(h-450)**3)
        es=a*(1+.01*(q[:,None]-x)+.02*(q[None,:]-y))*(1+.3j)
        expected=(np.abs(1+.2j+es)**2-abs(1+.2j)**2)/abs(1+.2j)**2
        self.assertLess(np.max(abs(r.C-expected)),1e-14)
        self.assertGreater(np.max(abs(r.C-m.C(d,h,0,0,score=False))),1e-6)
    def test_centered_crop(self):
        m,_,_=fixture();o=m.forward((100,450,0,0))
        self.assertAlmostEqual(o.C[8,8],o.score_C[6,6],places=15)
    def test_index_match_zero(self):
        m,er,es=fixture();es[:]=0
        z=FieldForward(D,H,X,Y,er,es,pixel_nm=1,q=1,camera_n=17,score_n=13,xy_limit_nm=3)
        self.assertEqual(float(np.max(abs(z.C(83.7,411.2,1,2)))),0.)
    def test_common_complex_gain_cancels(self):
        m,er,es=fixture();g=2+3j
        mg=FieldForward(D,H,X,Y,er*g,es*g,pixel_nm=1,q=1,camera_n=17,score_n=13,xy_limit_nm=3)
        self.assertLess(np.max(abs(m.C(70,410,1,-1)-mg.C(70,410,1,-1))),1e-14)
    def test_domain(self):
        m,_,_=fixture()
        for p in [(201,450,0,0),(100,600,0,0),(100,450,4,0),(np.nan,450,0,0),(100,np.inf,0,0)]:
            with self.assertRaises(OutOfDomain):m.forward(p)
    def test_reference_invariance(self):
        _,er,es=fixture();er[1,0]*=1.01
        with self.assertRaises(ValueError):FieldForward(D,H,X,Y,er,es,pixel_nm=1,q=1)
    def test_source_query_distinct(self):
        A=np.stack(list(np.meshgrid(X,Y,indexing='ij'))+[np.ones((31,31))],axis=-1).astype(complex)
        got=sample_complex(A,X,Y,np.array([.5,1.5]),np.array([-1.5,.5]))
        self.assertTrue(np.allclose(got[...,0],[[.5,.5],[1.5,1.5]]))
    def test_q5_averages_intensity_not_field(self):
        fx=np.arange(-12.,13.)*56.
        er=np.zeros((len(D),len(H),25,25,3),complex);es=np.zeros_like(er)
        er[...,0]=1.
        es[...,0]=.01*(fx[:,None]/56.)
        m=FieldForward(D,H,fx,fx,er,es,pixel_nm=280,q=5,camera_n=3,score_n=1,xy_limit_nm=100)
        actual=m.C(100,450,0,0)[0,0]
        self.assertAlmostEqual(actual,.0002,places=13)
        self.assertGreater(actual,0)  # square-of-average field would give zero
    def test_spatial_outside_rejected(self):
        A=np.zeros((31,31,3),complex)
        with self.assertRaises(OutOfDomain):sample_complex(A,X,Y,np.array([-16.]),np.array([0.]))

if __name__=='__main__':unittest.main(verbosity=2)
