"""V139 reusable, zero-BEM numerical helpers.

All unit tests use synthetic fields. Functions verify mathematical operations,
not that a retrieved MAT file was produced by the declared BEM solve.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
import numpy as np


def sha_file(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()


def finite_array(x,*,shape=None):
    a=np.asarray(x)
    if a.dtype.kind not in 'fiuc' or not np.isfinite(a).all() or (shape is not None and a.shape!=shape):
        raise ValueError('finite numeric array with expected shape required')
    return a


def canonical_raw_to_merged(native):
    """V138 demonstrated export mapping for THESE M render files; not an inferred transform."""
    a=finite_array(native)
    if a.ndim!=2 or a.shape[0]!=a.shape[1]:raise ValueError('square source camera image required')
    return np.ascontiguousarray(a.T[::-1,:])


def intensity_contrast(Itotal,Iref):
    tot=np.asarray(finite_array(Itotal),float);ref=np.asarray(finite_array(Iref),float)
    if tot.shape!=ref.shape or tot.ndim!=2 or np.any(ref<=0) or np.any(tot<0):
        raise ValueError('inconsistent native intensity and reference')
    return (tot-ref)/ref


def complex_field(x, *,nx,ny):
    a=np.asarray(x)
    if a.dtype.names is not None:
        if not {'real','imag'}.issubset(a.dtype.names):raise ValueError('unsupported complex compound')
        a=a['real'].astype(float)+1j*a['imag'].astype(float)
    a=np.asarray(a,dtype=np.complex128)
    if a.shape==(3,nx,ny):a=np.transpose(a,(1,2,0))
    elif a.shape!=(nx,ny,3):raise ValueError(f'invalid complex field shape {a.shape}; no guessed axes')
    if not np.isfinite(a).all():raise ValueError('non-finite complex field')
    return a


def subsample_query(n=17,q=5,pixel_nm=280.0):
    if n<=0 or q<=0 or n%2!=1 or not np.isfinite(pixel_nm) or pixel_nm<=0:raise ValueError('invalid camera configuration')
    centers=(np.arange(n)-(n-1)/2)*pixel_nm
    offsets=((np.arange(q)+.5)/q-.5)*pixel_nm
    return (centers[:,None]+offsets[None,:]).reshape(-1)


def bilinear_checked(F,fx,fy,query_x,query_y):
    """Independent (non-F2-import) bilinear spatial sample: NEVER extrapolate or clip."""
    x=np.asarray(fx,dtype=float);y=np.asarray(fy,dtype=float)
    qx=np.asarray(query_x,dtype=float);qy=np.asarray(query_y,dtype=float)
    if (len(x)<2 or len(y)<2 or x.ndim!=1 or y.ndim!=1 or
        np.any(np.diff(x)<=0) or np.any(np.diff(y)<=0) or
        qx.ndim!=1 or qy.ndim!=1 or not np.isfinite(x).all() or not np.isfinite(y).all() or
        not np.isfinite(qx).all() or not np.isfinite(qy).all()):
        raise ValueError('axes must be finite ascending 1D')
    f=complex_field(F,nx=len(x),ny=len(y))
    if qx.min()<x[0] or qx.max()>x[-1] or qy.min()<y[0] or qy.max()>y[-1]:
        raise ValueError('OUTSIDE_SOURCE_FIELD_DOMAIN: cannot clip/extrapolate')
    i=np.clip(np.searchsorted(x,qx,side='right')-1,0,len(x)-2)
    j=np.clip(np.searchsorted(y,qy,side='right')-1,0,len(y)-2)
    # Index clipping here only resolves equality at the in-domain last knot;
    # the explicit outside-support guard ABOVE is mandatory.
    wx=((qx-x[i])/(x[i+1]-x[i]))[:,None,None]
    wy=((qy-y[j])/(y[j+1]-y[j]))[None,:,None]
    a=f[i[:,None],j[None,:]]
    b=f[(i+1)[:,None],j[None,:]]
    c=f[i[:,None],(j+1)[None,:]]
    d=f[(i+1)[:,None],(j+1)[None,:]]
    return (1-wx)*((1-wy)*a+wy*c)+wx*((1-wy)*b+wy*d)


def pixel_average_intensity(A,q):
    a=np.asarray(finite_array(A),float)
    if a.ndim!=2 or a.shape[0]%q or a.shape[1]%q or np.any(a<0):
        raise ValueError('invalid intensity integration shape')
    return a.reshape(a.shape[0]//q,q,a.shape[1]//q,q).mean(axis=(1,3))


def oracle_same_wide(Eref,Esca,fx,fy,*,dx,dy,n=17,q=5,pixel_nm=280.):
    """Shift Es physically but keep Er fixed, intensity BEFORE pixel integration."""
    query=subsample_query(n=n,q=q,pixel_nm=pixel_nm)
    er=bilinear_checked(Eref,fx,fy,query,query)
    es=bilinear_checked(Esca,fx,fy,query-float(dx),query-float(dy))
    total=pixel_average_intensity(np.sum(abs(er+es)**2,axis=-1),q)
    bg=pixel_average_intensity(np.sum(abs(er)**2,axis=-1),q)
    if not np.isfinite(total).all() or not np.isfinite(bg).all() or np.any(bg<=0):
        raise ValueError('invalid real camera intensity')
    return (total-bg)/bg,total,bg


def residual_metrics(A,B):
    """A and B MUST already be in the identical coordinate/ROI convention."""
    a=np.asarray(finite_array(A),float);b=np.asarray(finite_array(B),float)
    if a.shape!=b.shape or a.ndim!=2:raise ValueError('mismatched image geometry')
    d=a-b
    n=float(np.linalg.norm(b))
    return dict(abs_L2=float(np.linalg.norm(d)),relative_L2=float(np.linalg.norm(d)/n) if n>1e-12 else None,
                max_abs=float(np.max(abs(d))),ref_norm=n)


def central(a,n=13):
    a=np.asarray(a)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or a.shape[0]<n or (a.shape[0]-n)%2:
        raise ValueError('ambiguous central ROI')
    k=(len(a)-n)//2
    return a[k:k+n,k:k+n]


def load_json(path):
    with open(path,encoding='utf-8-sig') as f:return json.load(f)
