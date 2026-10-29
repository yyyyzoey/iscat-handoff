"""V165 objective-only adapter for frozen three-frame F2c GLS.

No model construction, random generation, camera rendering, truth reading or
optimization is implemented here. The production runner must inject a counted
and checkpointing predict() callback. Values are conditional development data.
"""
from dataclasses import dataclass
from typing import Optional
import math
import numpy as np

LOW=np.array([30.,350.,-500.,-500.],dtype=float)
HIGH=np.array([200.,550.,500.,500.],dtype=float)

@dataclass(frozen=True)
class HeightReading:
    reading_id: str
    group: str
    replicate: int
    sigma_nm: float
    z_nm: float
    hypothetical: bool = True

    def __post_init__(self):
        if not isinstance(self.reading_id,str) or not self.reading_id:
            raise ValueError('INVALID_READING_ID')
        if not isinstance(self.group,str) or not self.group:
            raise ValueError('INVALID_GROUP')
        if not isinstance(self.replicate,int) or self.replicate<0:
            raise ValueError('INVALID_REPLICATE')
        if not self.hypothetical or not (math.isfinite(self.sigma_nm) and self.sigma_nm>0):
            raise ValueError('HEIGHT_IS_HYPOTHETICAL_AND_SIGMA_POSITIVE')
        if not math.isfinite(self.z_nm):
            raise ValueError('NONFINITE_HEIGHT_READING')


def check_theta(theta):
    t=np.asarray(theta,dtype=float)
    if t.shape!=(4,) or not np.isfinite(t).all() or np.any(t<LOW) or np.any(t>HIGH):
        raise ValueError('INVALID_FROZEN_PARAMETER_DOMAIN_NO_CLIP')
    if t[1]-t[0]/2<100.:
        raise ValueError('SURFACE_GAP_OUTSIDE_DOMAIN')
    return t


def _gls(data,c):
    c=np.asarray(c,dtype=float)
    if c.shape!=(13,13) or not np.isfinite(c).all():
        raise ValueError('BAD_SIGNED_CONTRAST_SCORE_C')
    y=np.asarray(data.y,dtype=float);v=np.asarray(data.variance,dtype=float)
    if y.shape!=(3,13,13) or v.shape!=y.shape or not np.isfinite(y).all() or not np.isfinite(v).all() or np.any(v<=0):
        raise ValueError('BAD_FROZEN_THREE_FRAME_DATA')
    optical_res=((c-data.ybar)/np.sqrt(data.vbar)).ravel()
    per_frame=np.sum((c-y)**2/v,axis=(1,2))
    q_direct=float(np.sum(per_frame));qopt=float(optical_res@optical_res)
    constant=float(data.constant_K)
    if abs(q_direct-(qopt+constant))>max(1e-8,1e-10*abs(q_direct)):
        raise ValueError('GLS_AGGREGATE_IDENTITY')
    return optical_res,q_direct,qopt,constant,per_frame.tolist()


def augmented_objective(data,c,theta,reading: Optional[HeightReading]=None):
    """Return residual for SciPy least_squares and independently recomputed Q.

    scipy cost = 0.5*(Q_model+Q_height), not 0.5*(Q_joint+Q_height):
    constant K is independent of theta. A common reading is NEVER an estimate
    of actual height precision unless an externally measured datum is supplied.
    """
    t=check_theta(theta)
    r,qjoint,qmodel,k,perframe=_gls(data,c)
    qheight=0.0
    if reading is not None:
        qheight=float(((t[1]-reading.z_nm)/reading.sigma_nm)**2)
        r=np.r_[r,(t[1]-reading.z_nm)/reading.sigma_nm]
    qtotal=qjoint+qheight
    if abs(float(r@r)+k-qtotal)>max(1e-8,1e-10*abs(qtotal)):
        raise ValueError('AUGMENTED_HALF_COST_IDENTITY')
    return {
        'residual':r,
        'Q_frames':perframe,
        'Q_joint':qjoint,
        'Q_model':qmodel,
        'K':k,
        'Q_height':qheight,
        'Q_total':qtotal,
        'theta':t.tolist(),
        'hypothetical_height_measurement': reading is not None,
        'reportable_D':None,
    }
