import sys, json, unittest, importlib.util, hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from template_bank import TemplateBank,fit_with_bank,axis_with_midpoints

class LinearModel:
    Ds=np.array([30.,70.,130.,200.]);Hs=np.array([350.,400.,475.,550.])
    xy_limit=500.;model_id='SYNTHETIC_LINEAR_UNIQUE';n=2;s=2
    def forward(self,p):
        D,h,x,y=map(float,p)
        from types import SimpleNamespace
        if not (30<=D<=200 and 350<=h<=550 and abs(x)<=500 and abs(y)<=500):raise ValueError('outside')
        return SimpleNamespace(score_C=np.array([[D/100,h/500],[x/200,y/200]]))
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=LinearModel();cls.bank=TemplateBank(cls.m,[(0,0),(140,0)],midpoints=True)
    def test_four_axial_strata(self):
        starts,_,_=self.bank.select_starts(self.m.forward([47,381,84,-56]).score_C,6)
        bins=np.minimum(np.floor((starts[:,1]-350)/50).astype(int),3)
        self.assertEqual(set(bins),{0,1,2,3})
    def test_continuous_size(self):
        Y=self.m.forward([83.7,418.75,43.2,-61.9]).score_C
        fit=fit_with_bank(self.m,Y,self.bank,total_calls=10000,max_starts=6)
        self.assertLess(abs(fit['candidate_D']-83.7),1e-5)
        self.assertIsNone(fit['reportable_D'])
    def test_identity_mismatch(self):
        m=LinearModel();m.model_id='different'
        with self.assertRaises(ValueError):fit_with_bank(m,np.ones((2,2)),self.bank)
    def test_bad_image(self):
        with self.assertRaises(ValueError):self.bank.select_starts(np.full((2,2),np.nan))
    def test_midpoints_real_axes(self):
        np.testing.assert_allclose(axis_with_midpoints([30,50,100]),[30,40,50,75,100])
    def test_no_truth_in_bank_identity(self):
        before=self.bank.bank_id
        self.bank.select_starts(np.ones((2,2)))
        self.bank.select_starts(np.zeros((2,2)))
        self.assertEqual(before,self.bank.bank_id)
    def test_config_budget(self):
        c=json.loads((ROOT/'config/v131_science_config.json').read_text())
        p=c['camera'];m=c['motion']
        static=(len(p['dev_D_nm'])*len(p['dev_h_nm'])*3*p['dev_target_repeats']
                +3*p['dev_blanks_per_B']+3*p['validation_blanks_per_B']
                +6*3*p['new_holdout_noise_repeats_per_B'])*(1+p['refs_per_measurement'])
        motion=len(m['D_generation_nm'])*m['tracks_per_D']*2*(m['frames_per_track']+m['shared_reference_frames_per_track_and_exposure'])
        self.assertEqual(static+motion,4782)
        self.assertLessEqual(static+motion,c['budget']['synthetic_camera_exposure_events_max'])
        self.assertEqual(c['model_selection']['initial_kind'],'F2')
    def test_v130_exact_published_source_fix(self):
        path=ROOT/'evidence/v130_published/source.py';b=path.read_bytes()
        self.assertEqual(hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),
                         '37eff61e435914682e22b70fa55d27c2480c43a8')
        spec=importlib.util.spec_from_file_location('v130_exact_test',path)
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        er=np.zeros((125,125,3),complex);er[...,0]=1;es=np.zeros_like(er)
        o=mod.ComplexFieldForward.__new__(mod.ComplexFieldForward)
        o.eval_fields=lambda D,h:(er,es)
        o.fine_x=(np.arange(125)-62)*56.;o.fine_y=o.fine_x.copy()
        self.assertEqual(float(abs(o.C(100,450,28,-28)).max()),0.)
    def test_published_K_arithmetic(self):
        import csv
        with (ROOT/'evidence/v130_published/old_K_per_particle.csv').open() as f:
            r=list(csv.DictReader(f))
        e=np.array([float(t['D_est_nm'])-float(t['D_true']) for t in r])
        self.assertAlmostEqual(float(abs(e).mean()),7.523309083043745,11)
        self.assertEqual(sum(abs(e[i])<=max(5,.1*float(t['D_true'])) for i,t in enumerate(r)),4)
if __name__=='__main__':unittest.main()
