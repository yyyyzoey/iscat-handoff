"""V142 pinned reference spatial interpolation primitives (copied from V141 source): strict canonical MATLAB-source arrays.

This code is a reference for workstations holding the original MAT HDF5. Passing
synthetic tests does not certify any real optical solve, experiment or diameter.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import numpy as np


def sha_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def sha_array(arr):
    a = np.ascontiguousarray(arr)
    return hashlib.sha256((str(a.shape)+'|'+str(a.dtype)+'|').encode()+a.tobytes()).hexdigest()


def git_blob_sha(path):
    b = Path(path).read_bytes()
    return hashlib.sha1(b'blob ' + str(len(b)).encode('ascii') + b'\0' + b).hexdigest()


def assert_frozen_git_blobs(repo, mapping):
    actual = {}
    for rel, expected in mapping.items():
        if len(expected)!=40 or any(c not in '0123456789abcdef' for c in expected):
            raise ValueError('FROZEN_SHA_NOT_EXACTLY_40_LOWERCASE_HEX: '+rel)
        p = Path(repo)/rel
        if not p.is_file():
            raise FileNotFoundError(str(p))
        got = git_blob_sha(p)
        if got!=expected:
            raise ValueError('SOURCE_BYTES_DIFFER_FROM_FROZEN_GIT_BLOB: '+rel)
        actual[rel] = {'git_blob':got, 'sha256':sha_file(p), 'bytes':p.stat().st_size}
    return actual


def matlab_field_canonical(dataset):
    arr = dataset[()] if hasattr(dataset, '__getitem__') else np.asarray(dataset)
    if arr.dtype.names is not None:
        if not {'real','imag'}.issubset(arr.dtype.names):
            raise ValueError('UNSUPPORTED_MAT_COMPOUND_FIELD')
        field = arr['real'].astype(np.float64)+1j*arr['imag'].astype(np.float64)
    elif np.iscomplexobj(arr):
        field = np.asarray(arr,dtype=np.complex128)
    else:
        raise ValueError('NO_COMPLEX_VECTOR_FIELD')
    if field.ndim!=3 or field.shape[0]!=3 or field.shape[1]!=field.shape[2]:
        raise ValueError('EXPECTED_MAT_H5_FIELD_3_N_N')
    out = np.transpose(field,(2,1,0))[::-1,:,:].copy()
    if not np.isfinite(out).all():
        raise ValueError('NONFINITE_COMPLEX_FIELD')
    return out


def canonical_axes(fx,fy):
    a=np.asarray(fx,dtype=float).ravel()
    b=np.asarray(fy,dtype=float).ravel()
    if (a.ndim!=1 or b.ndim!=1 or len(a)<2 or len(b)<2 or
        not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)) or
        not np.all(np.diff(a)>0) or not np.all(np.diff(b)>0)):
        raise ValueError('INVALID_FINE_AXES')
    return -a[::-1].copy(),b.copy()


def raw_camera_canonical(arr):
    a=np.asarray(arr,dtype=np.float64)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.isfinite(a).all():
        raise ValueError('INVALID_CAMERA_C')
    return np.ascontiguousarray(a.T[::-1,:])


def camera_query(n=17,q=5,pixel_nm=280.0):
    if not isinstance(n,int) or not isinstance(q,int) or n<1 or q<1 or n%2==0 or pixel_nm<=0:
        raise ValueError('INVALID_CAMERA_GRID')
    center=(np.arange(n)-(n-1)/2)*pixel_nm
    sub=((np.arange(q)+.5)/q-.5)*pixel_nm
    return (center[:,None]+sub[None,:]).reshape(-1)


def validate_in_support(fx,fy,qx,qy):
    x=np.asarray(fx,dtype=float);y=np.asarray(fy,dtype=float)
    xx=np.asarray(qx,dtype=float);yy=np.asarray(qy,dtype=float)
    if (x.ndim!=1 or y.ndim!=1 or xx.ndim!=1 or yy.ndim!=1 or len(x)<2 or len(y)<2 or
        not np.isfinite(x).all() or not np.isfinite(y).all() or
        not np.isfinite(xx).all() or not np.isfinite(yy).all() or
        not np.all(np.diff(x)>0) or not np.all(np.diff(y)>0)):
        raise ValueError('BAD_SAMPLING_GRID')
    tol=1e-10
    if xx.min()<x[0]-tol or xx.max()>x[-1]+tol or yy.min()<y[0]-tol or yy.max()>y[-1]+tol:
        raise ValueError('QUERY_OUTSIDE_SOURCE_SUPPORT')
    return x,y,xx,yy


def sample_bilinear(field,fx,fy,qx,qy):
    x,y,xx,yy=validate_in_support(fx,fy,qx,qy)
    F=np.asarray(field,dtype=np.complex128)
    if F.shape!=(len(x),len(y),3) or not np.isfinite(F).all():
        raise ValueError('FIELD_GRID_MISMATCH')
    ix=np.minimum(np.maximum(np.searchsorted(x,xx,side='right')-1,0),len(x)-2)
    iy=np.minimum(np.maximum(np.searchsorted(y,yy,side='right')-1,0),len(y)-2)
    wx=((xx-x[ix])/(x[ix+1]-x[ix]))[:,None,None]
    wy=((yy-y[iy])/(y[iy+1]-y[iy]))[None,:,None]
    a=F[ix[:,None],iy[None,:]]
    b=F[(ix+1)[:,None],iy[None,:]]
    c=F[ix[:,None],(iy+1)[None,:]]
    d=F[(ix+1)[:,None],(iy+1)[None,:]]
    return (1-wx)*((1-wy)*a+wy*c)+wx*((1-wy)*b+wy*d)


def sample_cubic(field,fx,fy,qx,qy):
    """Not-a-knot, s=0, separate real and imaginary complex spline.

    Globally fixed numerical alternative, not a parameter selected per particle.
    """
    x,y,xx,yy=validate_in_support(fx,fy,qx,qy)
    F=np.asarray(field,dtype=np.complex128)
    if F.shape!=(len(x),len(y),3) or min(len(x),len(y))<4 or not np.isfinite(F).all():
        raise ValueError('CUBIC_NEEDS_4_NODES_EACH_AXIS_AND_FINITE_FIELD')
    from scipy.interpolate import RectBivariateSpline
    out=np.empty((len(xx),len(yy),3),dtype=np.complex128)
    for k in range(3):
        sr=RectBivariateSpline(x,y,F[...,k].real,kx=3,ky=3,s=0)
        si=RectBivariateSpline(x,y,F[...,k].imag,kx=3,ky=3,s=0)
        out[...,k]=sr(xx,yy,grid=True)+1j*si(xx,yy,grid=True)
    if not np.isfinite(out).all():raise ValueError('CUBIC_NONFINITE')
    return out


def pixel_intensities(Eref,Esca,q):
    Er=np.asarray(Eref,dtype=np.complex128);Es=np.asarray(Esca,dtype=np.complex128)
    if Er.shape!=Es.shape or Er.ndim!=3 or Er.shape[2]!=3 or Er.shape[0]%q or Er.shape[1]%q:
        raise ValueError('INVALID_FOCUS_FIELD_SHAPE')
    if not np.isfinite(Er).all() or not np.isfinite(Es).all():raise ValueError('NONFINITE_FIELD')
    def avg(a):
        return a.reshape(a.shape[0]//q,q,a.shape[1]//q,q).mean(axis=(1,3))
    ir=avg(np.sum(np.abs(Er)**2,axis=-1))
    isca=avg(np.sum(np.abs(Es)**2,axis=-1))
    cross=avg(2*np.real(np.sum(np.conj(Er)*Es,axis=-1)))
    total=avg(np.sum(np.abs(Er+Es)**2,axis=-1))
    if np.any(ir<=0):raise ValueError('NONPOSITIVE_BACKGROUND')
    return {'Iref':ir,'Isca':isca,'Icross':cross,'Itotal':total,'C':(total-ir)/ir,
            'coherent_identity_max':float(np.max(np.abs(total-(ir+isca+cross))))}


def error_metrics(a,b):
    aa=np.asarray(a);bb=np.asarray(b)
    if aa.shape!=bb.shape or not np.isfinite(aa).all() or not np.isfinite(bb).all():
        raise ValueError('ERROR_METRIC_SHAPE_OR_VALUE_INVALID')
    d=aa-bb;n=float(np.linalg.norm(bb))
    return {'abs_L2':float(np.linalg.norm(d)),
            'relative_L2':float(np.linalg.norm(d)/n) if n>1e-15 else None,
            'max_abs':float(np.max(np.abs(d))),
            'ref_norm':n}
