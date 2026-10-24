"""V131: inherited deterministic reference core, NOT an electromagnetic solver.
Origin: the earlier handoff reference core; NOT the defective V129 repository wrapper.

Input arrays must have independently verified physical metadata and camera axes.
Interpolates an existing complex-field grid and forms signed iSCAT contrast.
This module has no hidden path, no D/h clipping, no node-value shortcut, and
only ONE observation implementation. Project integration still needs real-field
checks against the direct MATLAB renders before scientific acceptance.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from scipy.interpolate import make_interp_spline, BSpline

class OutOfDomain(ValueError):
    pass

@dataclass(frozen=True)
class Observation:
    Ibg: np.ndarray
    I: np.ndarray
    C: np.ndarray
    score_C: np.ndarray
    theta: tuple[float, float, float, float]
    model_id: str

def _axis(x, name):
    a = np.asarray(x, dtype=float)
    if a.ndim != 1 or a.size < 2 or not np.isfinite(a).all() or not np.all(np.diff(a)>0):
        raise ValueError(f'{name}: finite, strictly increasing 1D axis required')
    return a

def _linear_weights(axis, v):
    if not np.isfinite(v) or not axis[0] <= v <= axis[-1]:
        raise OutOfDomain(f'value {v} outside [{axis[0]},{axis[-1]}]')
    k = min(max(int(np.searchsorted(axis, v, side='right'))-1, 0), len(axis)-2)
    t = (v-axis[k])/(axis[k+1]-axis[k])
    w = np.zeros(len(axis)); w[k]=1-t; w[k+1]=t
    return w

def _tensor_coeff(axis_d, axis_h, values):
    """Cubic coefficients along physical D and h axes ONLY; spatial axes untouched."""
    def real_coeff(a):
        sd = make_interp_spline(axis_d, a, k=3, axis=0, bc_type='not-a-knot')
        sh = make_interp_spline(axis_h, np.moveaxis(sd.c, 1, 0), k=3,
                                axis=0, bc_type='not-a-knot')
        return np.moveaxis(sh.c, 0, 1), sd.t, sh.t
    cr, td, th = real_coeff(values.real)
    ci, td2, th2 = real_coeff(values.imag)
    if not np.array_equal(td,td2) or not np.array_equal(th,th2):
        raise RuntimeError('inconsistent spline knots')
    return cr + 1j*ci, td, th

def sample_complex(field, xs, ys, query_x, query_y):
    """Bilinear interpolation on fixed source axes, with STRICT query-domain check."""
    qx=np.asarray(query_x,dtype=float); qy=np.asarray(query_y,dtype=float)
    if (qx.ndim!=1 or qy.ndim!=1 or not np.isfinite(qx).all() or not np.isfinite(qy).all()
        or qx.min()<xs[0] or qx.max()>xs[-1] or qy.min()<ys[0] or qy.max()>ys[-1]):
        raise OutOfDomain('spatial query leaves field support')
    ix=np.minimum(np.searchsorted(xs,qx,side='right')-1,len(xs)-2)
    iy=np.minimum(np.searchsorted(ys,qy,side='right')-1,len(ys)-2)
    ax=(qx-xs[ix])/(xs[ix+1]-xs[ix]); ay=(qy-ys[iy])/(ys[iy+1]-ys[iy])
    a00=field[ix[:,None],iy[None,:]]
    a10=field[(ix+1)[:,None],iy[None,:]]
    a01=field[ix[:,None],(iy+1)[None,:]]
    a11=field[(ix+1)[:,None],(iy+1)[None,:]]
    wx=ax[:,None,None]; wy=ay[None,:,None]
    return (1-wx)*((1-wy)*a00+wy*a01)+wx*((1-wy)*a10+wy*a11)

def pixel_mean(a,q):
    if a.ndim!=2 or a.shape[0]%q or a.shape[1]%q:
        raise ValueError('intensity array incompatible with pixel quadrature')
    return a.reshape(a.shape[0]//q,q,a.shape[1]//q,q).mean(axis=(1,3))

class FieldForward:
    """Er/Es [D,h,x_fine,y_fine,component]; output camera axes [x,y].

    kind F1: physical-axis bilinear; F2: not-a-knot tensor cubic;
    F3: same cubic applied to Es/(D/100)^3. No free fitted gain or phase.
    """
    def __init__(self, Ds, Hs, fine_x, fine_y, Eref, Esca, *, kind='F1',
                 pixel_nm=280., q=5, camera_n=17, score_n=13,
                 xy_limit_nm=500., min_gap_nm=100., reference_rtol=1e-10,
                 model_id='UNQUALIFIED_REFERENCE_COMPONENT'):
        self.Ds=_axis(Ds,'Ds');self.Hs=_axis(Hs,'Hs')
        self.fx=_axis(fine_x,'fine_x');self.fy=_axis(fine_y,'fine_y')
        er=np.asarray(Eref,dtype=np.complex128);es=np.asarray(Esca,dtype=np.complex128)
        shp=(len(self.Ds),len(self.Hs),len(self.fx),len(self.fy),3)
        if er.shape!=shp or es.shape!=shp or not np.isfinite(er).all() or not np.isfinite(es).all():
            raise ValueError(f'finite fields with shape {shp} required')
        if (kind not in ('F1','F2','F3') or pixel_nm<=0 or not np.isfinite(pixel_nm)
            or q<1 or int(q)!=q or camera_n%2!=1 or score_n%2!=1
            or score_n<1 or score_n>camera_n or xy_limit_nm<0):
            raise ValueError('invalid observation configuration')
        if kind!='F1' and (len(self.Ds)<4 or len(self.Hs)<4):
            raise ValueError('cubic requires at least 4 nodes on each physical axis')
        # The interface reference in this experiment should not vary with particle D/h.
        # Fail rather than independently rephase or rescale individual nodes.
        ref=er[0,0].copy();norm=float(np.max(np.abs(ref)))
        if norm<=0 or np.max(np.abs(er-ref))>reference_rtol*norm:
            raise ValueError('reference varies across nodes or is zero; investigate provenance/optics')
        self.ref=ref;self.kind=kind;self.q=int(q);self.n=int(camera_n);self.s=int(score_n)
        self.xy_limit=float(xy_limit_nm);self.min_gap=float(min_gap_nm)
        self.model_id=str(model_id);self.pixel_nm=float(pixel_nm)
        centers=(np.arange(self.n)-(self.n-1)/2)*pixel_nm
        subs=((np.arange(self.q)+.5)/self.q-.5)*pixel_nm
        self.query=(centers[:,None]+subs[None,:]).reshape(-1)
        self.ref_cam=sample_complex(ref,self.fx,self.fy,self.query,self.query)
        self.Ibg=pixel_mean(np.sum(np.abs(self.ref_cam)**2,axis=-1),self.q)
        if not np.isfinite(self.Ibg).all() or np.any(self.Ibg<=0):
            raise ValueError('non-positive/non-finite reference intensity')
        if kind=='F1':
            self.coeff=es.copy();self.bd=None;self.bh=None
        else:
            src=es if kind=='F2' else es/((self.Ds/100.)**3)[:,None,None,None,None]
            self.coeff,td,th=_tensor_coeff(self.Ds,self.Hs,src)
            self.bd=BSpline(td,np.eye(self.coeff.shape[0]),3,extrapolate=False)
            self.bh=BSpline(th,np.eye(self.coeff.shape[1]),3,extrapolate=False)
    def check_domain(self, theta):
        p=np.asarray(theta,dtype=float)
        if p.shape!=(4,) or not np.isfinite(p).all(): raise OutOfDomain('finite D,h,x,y required')
        D,h,x,y=map(float,p)
        if (not self.Ds[0]<=D<=self.Ds[-1] or not self.Hs[0]<=h<=self.Hs[-1]
            or abs(x)>self.xy_limit or abs(y)>self.xy_limit or h-D/2<self.min_gap):
            raise OutOfDomain('D/h/xy/gap outside declared model domain')
        return D,h,x,y
    def fields(self,D,h):
        if not np.isfinite([D,h]).all() or not self.Ds[0]<=D<=self.Ds[-1] or not self.Hs[0]<=h<=self.Hs[-1]:
            raise OutOfDomain('D/h outside interpolation support')
        if self.kind=='F1':
            wd=_linear_weights(self.Ds,D);wh=_linear_weights(self.Hs,h)
        else:
            wd=np.asarray(self.bd(D));wh=np.asarray(self.bh(h))
        di=np.flatnonzero(wd!=0);hi=np.flatnonzero(wh!=0)
        es=np.einsum('i,j,ijabc->abc',wd[di],wh[hi],self.coeff[np.ix_(di,hi)],optimize=True)
        if self.kind=='F3':es*= (D/100.)**3
        return self.ref,es
    def forward(self,theta):
        D,h,x,y=self.check_domain(theta)
        _,es=self.fields(D,h)
        shifted=sample_complex(es,self.fx,self.fy,self.query-x,self.query-y)
        I=pixel_mean(np.sum(np.abs(self.ref_cam+shifted)**2,axis=-1),self.q)
        C=(I-self.Ibg)/self.Ibg
        if not np.isfinite(I).all() or not np.isfinite(C).all() or np.any(I<0):
            raise ValueError('invalid observation')
        i=(self.n-self.s)//2
        return Observation(self.Ibg.copy(),I,C,C[i:i+self.s,i:i+self.s].copy(),
                           (D,h,x,y),self.model_id)
    def C(self,D,h,x,y,score=True):
        out=self.forward((D,h,x,y))
        return out.score_C if score else out.C
