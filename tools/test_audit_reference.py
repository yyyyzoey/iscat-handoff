import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import unittest,tempfile,csv
from pathlib import Path
import h5py,numpy as np
from audit_library import run

class AuditTests(unittest.TestCase):
    def fixture(self,directory,duplicate=False):
        p=Path(directory)/'test.h5'
        with h5py.File(p,'w') as h:
            for H in [350,450]:
                g=h.create_group(f'D100_h{H}')
                er=np.zeros((85,85,3),complex);er[...,0]=1.
                es=np.zeros_like(er);es[...,0]=.001*(1 if duplicate else H/350.)
                C=np.full((17,17),float(abs(1+es[0,0,0])**2-1))
                for k,a in [('Eref',er),('Esca',es),('C',C)]:g.create_dataset(k,data=a)
                g.attrs.update(D_nm=100.,h_nm=float(H),source='SYNTHETIC_UNIT_TEST')
                w=g.create_group('wide')
                w.create_dataset('Eref',data=er);w.create_dataset('Esca',data=es)
                w.create_dataset('fine_x_nm',data=np.arange(85));w.create_dataset('fine_y_nm',data=np.arange(85))
        return p
    def test_valid_synthetic_audit(self):
        with tempfile.TemporaryDirectory() as d:
            r=run(self.fixture(d));self.assertEqual(r['verdict'],'PASS_ARRAY_CHECKS_ONLY')
    def test_duplicate_height_array(self):
        with tempfile.TemporaryDirectory() as d:
            r=run(self.fixture(d,True));self.assertEqual(len(r['duplicate_height_groups']),1)
            self.assertEqual(r['verdict'],'REPAIR_OR_EVIDENCE_REQUIRED')
    def test_metadata_not_group_only(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.fixture(d)
            with h5py.File(p,'a') as h:h['D100_h350'].attrs['h_nm']=450.
            r=run(p);self.assertTrue(any('ATTR_LABEL_MISMATCH:h_nm' in n['errors'] for n in r['nodes']))
    def test_csv_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.fixture(d);c=Path(d)/'bad.csv'
            c.write_text('D_nm,h_nm,center_C,peak_abs_C\n100,350,0,0\n100,450,0,0\n')
            r=run(p,c);self.assertEqual(r['verdict'],'REPAIR_OR_EVIDENCE_REQUIRED')
    def test_baseline_change(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a';b=Path(d)/'b';a.mkdir();b.mkdir()
            old=self.fixture(a);new=self.fixture(b)
            with h5py.File(new,'a') as h:h['D100_h350/C'][...]=0
            r=run(new,baseline=old)
            self.assertTrue(any('BASELINE_CHANGED_REQUIRES_PROVENANCE_REVIEW' in n['errors'] for n in r['nodes']))

if __name__=='__main__':unittest.main(verbosity=2)
