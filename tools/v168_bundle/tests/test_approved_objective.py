import sys,hashlib
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'approved_core'))
from v152_gls_core import GlsData
from v165_objective import HeightReading,augmented_objective


def test_original_core_blob_pins():
 for name,pin in [('v165_objective.py','e18490bc093610415518c995430b13585428ff3c'),('v152_gls_core.py','a5820663028322cc1934e66e2d1f6668b0fe34f3')]:
  b=(ROOT/'approved_core'/name).read_bytes()
  assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==pin


@pytest.mark.parametrize('sigma',[None,1.,10.])
def test_optical_and_auxiliary_cost_identity(sigma):
 y=np.stack([np.full((13,13),q) for q in [.001,.002,-.001]])
 v=np.stack([np.full((13,13),q) for q in [.01,.02,.03]])
 d=GlsData.from_frames(y,v);c=np.full((13,13),.0005);t=[80.,430.,0.,0.]
 r=None if sigma is None else HeightReading('task','ANON_02',0,sigma,432.)
 result=augmented_objective(d,c,t,r)
 assert abs(result['Q_joint']-sum(result['Q_frames']))<1e-10
 assert abs(result['Q_total']-(result['residual']@result['residual']+result['K']))<1e-10
 assert result['Q_height']==pytest.approx((0. if sigma is None else 4/sigma**2),rel=1e-14,abs=1e-15)


def test_simulated_bias_not_silently_subtracted():
 d=GlsData.from_frames(np.zeros((3,13,13)),np.ones((3,13,13)))
 r=HeightReading('opaque','ANON_02',0,1.,432.)
 q=augmented_objective(d,np.zeros((13,13)),[80.,430.,0.,0.],r)
 assert q['Q_height']==4.
