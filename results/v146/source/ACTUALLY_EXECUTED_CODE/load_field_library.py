"""Strict adapter for the project's exported [x,y,component] complex-field HDF5.
No MATLAB reordering is guessed, no truth-driven axis/phase correction is done.
Checks here establish array consistency, NOT physical-source provenance.
"""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path
import h5py
import numpy as np
from field_forward_reference import FieldForward, pixel_mean

NODE = re.compile(r'^D([-+0-9.eE]+)_h([-+0-9.eE]+)$')

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def complex_array(ds):
    a=ds[()]
    if a.dtype.names:
        if not {'real','imag'}.issubset(a.dtype.names):
            raise ValueError('Unsupported compound complex dtype')
        a=a['real']+1j*a['imag']
    return np.asarray(a,dtype=np.complex128)

def load_library(path, *, kind='F1', optical=None):
    """Return FieldForward and explicit checks. Node attrs must match labels.
    Coordinates/metadata must ALSO be checked against original solves by Codex.
    """
    path=Path(path).resolve()
    optical=dict(optical or {})
    expected=dict(n_particle=1.38,NA=0.8,object_pixel_nm=280.0)
    expected.update(optical.pop('expected_node_metadata',{}))
    choices=dict(pixel_nm=280.,q=5,camera_n=17,score_n=13,
                 xy_limit_nm=500.,min_gap_nm=100.,reference_rtol=1e-10)
    unknown=set(optical)-set(choices)
    if unknown: raise ValueError(f'Unknown optical settings: {unknown}')
    choices.update(optical)
    checks=[]
    with h5py.File(path,'r') as h:
        nodes={}
        for key in h:
            m=NODE.fullmatch(key)
            if not m: continue
            D,H=map(float,m.groups())
            if (D,H) in nodes: raise ValueError('Duplicate physical node')
            g=h[key]
            for attr,v in [('D_nm',D),('h_nm',H)]:
                if attr not in g.attrs or not np.isclose(float(g.attrs[attr]),v,rtol=0,atol=1e-9):
                    raise ValueError(f'{key}: missing/mismatching attr {attr}')
            for attr,v in expected.items():
                if attr not in g.attrs or not np.isclose(complex(g.attrs[attr]),complex(v),rtol=0,atol=1e-9):
                    raise ValueError(f'{key}: missing/mismatching metadata {attr}; do not fill by guessing')
            nodes[D,H]=key
        if not nodes: raise ValueError('No D/h nodes')
        Ds=np.array(sorted({v[0] for v in nodes})); Hs=np.array(sorted({v[1] for v in nodes}))
        if len(nodes)!=len(Ds)*len(Hs): raise ValueError('Incomplete rectangular grid')
        er_all=[];es_all=[];fx0=fy0=None
        for D in Ds:
            er_h=[];es_h=[]
            for H in Hs:
                key=nodes[D,H];g=h[key]
                if 'wide' not in g: raise ValueError(f'{key}: missing wide fields; recover/rerender, do not fake')
                w=g['wide'];fx=np.asarray(w['fine_x_nm'][()],float);fy=np.asarray(w['fine_y_nm'][()],float)
                if fx.ndim!=1 or fy.ndim!=1 or not np.all(np.diff(fx)>0) or not np.all(np.diff(fy)>0):
                    raise ValueError(f'{key}: source axes must be strictly ascending 1D physical nm coordinates')
                er=complex_array(w['Eref']);es=complex_array(w['Esca'])
                if er.shape!=(len(fx),len(fy),3) or es.shape!=er.shape:
                    raise ValueError(f'{key}: requires [x,y,component], do NOT guess a transpose')
                if not np.isfinite(er).all() or not np.isfinite(es).all(): raise ValueError(f'{key}: nonfinite field')
                if fx0 is None: fx0,fy0=fx,fy
                elif not np.array_equal(fx,fx0) or not np.array_equal(fy,fy0):
                    raise ValueError(f'{key}: inconsistent physical grids; rectify at export')
                # Independent within-array replay for the original standard 17x17 render.
                C=np.asarray(g['C'][()]);er0=complex_array(g['Eref']);es0=complex_array(g['Esca'])
                n=choices['camera_n'];q=choices['q']
                if C.shape!=(n,n) or np.iscomplexobj(C) or er0.shape!=(n*q,n*q,3) or es0.shape!=er0.shape:
                    raise ValueError(f'{key}: invalid standard-camera array shapes')
                if not all(np.isfinite(a).all() for a in (C,er0,es0)): raise ValueError(f'{key}: nonfinite standard arrays')
                I0=pixel_mean(np.sum(abs(er0)**2,axis=-1),q)
                if np.any(I0<=0): raise ValueError(f'{key}: invalid reference intensity')
                direct=(pixel_mean(np.sum(abs(er0+es0)**2,axis=-1),q)-I0)/I0
                diff=float(np.max(abs(direct-C)))
                if diff>1e-12: raise ValueError(f'{key}: same-array C replay failed: {diff}')
                checks.append(dict(node=key,D_nm=D,h_nm=H,standard_replay_abs=diff,
                                   center_C=float(C[n//2,n//2]),mesh=int(g.attrs.get('mesh',-1))))
                er_h.append(er);es_h.append(es)
            er_all.append(er_h);es_all.append(es_h)
    cfg=json.dumps(dict(kind=kind,**choices),sort_keys=True).encode()
    core=Path(__file__).with_name('field_forward_reference.py')
    identity=hashlib.sha256(bytes.fromhex(sha256(path))+bytes.fromhex(sha256(core))+bytes.fromhex(sha256(__file__))+cfg).hexdigest()
    model=FieldForward(Ds,Hs,fx0,fy0,np.asarray(er_all),np.asarray(es_all),kind=kind,
                       model_id='v131-field-'+identity,**choices)
    # Do not require independent standard and wide optical grids to be bit-identical.
    with h5py.File(path,'r') as h:
        for row in checks:
            m=model.forward((row['D_nm'],row['h_nm'],0,0))
            ref=h[row['node']]['C'][()]
            row['wide_vs_standard_abs']=float(np.max(abs(m.C-ref)))
    report=dict(library=str(path),library_sha256=sha256(path),forward_sha256=sha256(core),
                loader_sha256=sha256(__file__),model_id=model.model_id,Ds=Ds.tolist(),Hs=Hs.tolist(),
                array_checks_passed=True,physical_source_qualification='REQUIRES_SOURCE_MAPPING_AND_DIRECT_RENDER_TESTS',
                checks=checks)
    return model,report
