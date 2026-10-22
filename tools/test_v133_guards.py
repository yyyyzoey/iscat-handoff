import json, tempfile, unittest,sys,hashlib
from pathlib import Path
from types import SimpleNamespace
import h5py,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from observation_adapter import read_static_observations,image_schema
from model_lock import LockedF2,ModelLockError,verify_code_lock,passport
from diagnose_existing import direct_field_shift

class Toy:
    kind='F2';model_id='toy-bound'
    def forward(self,p):
        a=np.full((3,3),float(p[0]));return SimpleNamespace(score_C=a,C=a,I=a+1,Ibg=np.ones_like(a),model_id=self.model_id)

class GuardTests(unittest.TestCase):
    def test_no_model_switch(self):
        t=Toy();t.kind='C_MAP'
        with self.assertRaises(ModelLockError):LockedF2(t,'toy-bound')
    def test_wrong_model_identity(self):
        with self.assertRaises(ModelLockError):LockedF2(Toy(),'other')
    def test_mid_run_switch_rejected(self):
        t=Toy();m=LockedF2(t,'toy-bound');t.kind='F1'
        with self.assertRaises(ModelLockError):m.forward([1,2,3,4])
    def test_passport_alias_repeat(self):
        r=passport(LockedF2(Toy(),'toy-bound'),[[1,2,3,4],[5,6,7,8]])
        self.assertTrue(all(x['max_abs_repeat']==0 and x['max_abs_alias']==0 for x in r['rows']))
    def test_hash_lock(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.py';p.write_text('x=1\n');h=hashlib.sha256(p.read_bytes()).hexdigest();verify_code_lock({'a.py':h},d)
            p.write_text('x=2\n')
            with self.assertRaises(ModelLockError):verify_code_lock({'a.py':h},d)
    def file(self,root=False,both=False,missing_wide=False,shape=(17,17)):
        tmp=tempfile.TemporaryDirectory();p=Path(tmp.name)/'x.h5'
        with h5py.File(p,'w') as f:
            g=f.create_group('M01');a=np.arange(np.prod(shape),dtype=float).reshape(shape)
            g.create_dataset('C' if root else 'at_offset/C',data=a)
            if both:g.create_dataset('at_offset/C' if root else 'C',data=a)
            if missing_wide:
                w=g.create_group('wide');w.create_dataset('Esca',data=np.zeros((2,2,3),complex));w.create_dataset('Eref',data=np.ones((2,2,3),complex))
        return tmp,p
    def test_flat_C_supported_without_truth(self):
        t,p=self.file(root=True)
        try:
            r=read_static_observations(p,['M01'])[0]
            self.assertEqual(r['binding']['source_dataset'],'M01/C');self.assertEqual(r['image'].shape,(13,13))
        finally:t.cleanup()
    def test_at_offset_crop_correct(self):
        t,p=self.file()
        try:
            r=read_static_observations(p,['M01'])[0]
            self.assertEqual(r['image'][0,0],36);self.assertEqual(r['image'][6,6],144)
        finally:t.cleanup()
    def test_no_inferred_flip(self):
        t,p=self.file()
        try:
            a=read_static_observations(p,['M01'])[0]['image'];self.assertNotEqual(a[0,1],a[1,0])
        finally:t.cleanup()
    def test_ambiguity_rejected(self):
        t,p=self.file(both=True)
        try:
            with self.assertRaises(ValueError):read_static_observations(p,['M01'])
            self.assertEqual(len(read_static_observations(p,['M01'],dataset='at_offset/C')),1)
        finally:t.cleanup()
    def test_missing_coordinates_not_drop_image(self):
        t,p=self.file(missing_wide=True)
        try:
            r=read_static_observations(p,['M01']);self.assertEqual(len(r),1)
            with h5py.File(p,'r') as f:out=direct_field_shift(f['M01'],Toy(),[1,2,3,4])
            self.assertEqual(out['status'],'MISSING_WIDE_METADATA');self.assertFalse(out['qualified'])
        finally:t.cleanup()
    def test_no_wide_is_not_pass(self):
        t,p=self.file()
        try:
            with h5py.File(p,'r') as f:out=direct_field_shift(f['M01'],Toy(),[1,2,3,4])
            self.assertEqual(out['status'],'MISSING_WIDE');self.assertFalse(out['qualified'])
        finally:t.cleanup()
    def test_nan_image_rejected(self):
        t,p=self.file()
        try:
            with h5py.File(p,'a') as f:f['M01/at_offset/C'][0,0]=np.nan
            with self.assertRaises(ValueError):read_static_observations(p,['M01'])
        finally:t.cleanup()
    def test_complex_image_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.h5'
            with h5py.File(p,'w') as f:f.create_dataset('M01/C',data=np.ones((17,17),complex))
            with self.assertRaises(ValueError):read_static_observations(p,['M01'])
    def test_duplicate_case_rejected(self):
        t,p=self.file()
        try:
            with self.assertRaises(ValueError):read_static_observations(p,['M01','M01'])
        finally:t.cleanup()
    def test_bad_shape_rejected(self):
        t,p=self.file(shape=(15,15))
        try:
            with self.assertRaises(ValueError):read_static_observations(p,['M01'])
        finally:t.cleanup()
    def test_missing_case_rejected(self):
        t,p=self.file()
        try:
            with self.assertRaises(KeyError):read_static_observations(p,['M02'])
        finally:t.cleanup()
    def test_inspection_preserves_source(self):
        t,p=self.file()
        try:
            before=p.read_bytes();a=image_schema(p);self.assertEqual(before,p.read_bytes());self.assertEqual(a['datasets'][0]['shape'],[17,17])
        finally:t.cleanup()

if __name__=='__main__':unittest.main()
