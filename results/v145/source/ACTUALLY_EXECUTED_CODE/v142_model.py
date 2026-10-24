#!/usr/bin/env python3
"""Non-mutating F2-SpatialCubic candidate: inherits pinned physical D/h cubic
coefficients and fixed-reference 17x17 observable from the *loaded* old F2;
ONLY replaces bilinear spatial sampling of scattered field with V141 cubic.
Not a solver, not independently qualified, not backward-compatible with F2 fits.
"""
from __future__ import annotations
import hashlib,json,math
import numpy as np
from v142_field_reference import sample_cubic

class F2SpatialCubic:
    def __init__(self,legacy_f2,*,library_sha256,spatial_kernel_sha256,source_code_sha256=''):
        if getattr(legacy_f2,'kind',None)!='F2':raise ValueError('CAN_WRAP_ONLY_LOCKED_PHYSICAL_DH_F2')
        self.base=legacy_f2
        self.kernel='S2_RECT_BIVARIATE_SPLINE_REAL_IMAG_K3_S0'
        self.identity=dict(parent_model_id=legacy_f2.model_id,library_sha256=library_sha256,
            kernel=self.kernel,kernel_sha256=spatial_kernel_sha256,model_code_sha256=source_code_sha256,
            pixel_nm=legacy_f2.pixel_nm,q=legacy_f2.q,camera_n=legacy_f2.n,score_n=legacy_f2.s)
        raw=json.dumps(self.identity,sort_keys=True,separators=(',',':')).encode('utf-8')
        self.model_id='v142-F2c-'+hashlib.sha256(raw).hexdigest()
    def forward(self,theta):
        from field_forward_reference import Observation,pixel_mean
        D,h,x,y=self.base.check_domain(theta)
        _,es=self.base.fields(D,h)
        shifted=sample_cubic(es,self.base.fx,self.base.fy,self.base.query-x,self.base.query-y)
        I=pixel_mean(np.sum(np.abs(self.base.ref_cam+shifted)**2,axis=-1),self.base.q)
        bg=self.base.Ibg
        C=(I-bg)/bg
        if not np.isfinite(I).all() or not np.isfinite(C).all() or np.any(I<0):
            raise ValueError('F2C_NONFINITE_OR_NEGATIVE_INTENSITY')
        n=self.base.n;s=self.base.s;i=(n-s)//2
        return Observation(bg.copy(),I,C,C[i:i+s,i:i+s].copy(),(D,h,x,y),self.model_id)
    def C(self,D,h,x,y,score=True):
        r=self.forward((D,h,x,y));return r.score_C if score else r.C
    def check_domain(self,theta):return self.base.check_domain(theta)


def construct(repo,*,library_relative='results/v128/library/v128_Dh_train_fields.h5',expected_library_sha256=None,expected_old_model_id=None):
    from pathlib import Path
    import sys
    repo=Path(repo).resolve();sys.path.insert(0,str(repo/'tools'))
    from load_field_library import load_library,sha256
    from v133_recover_M import optical
    config=json.loads((repo/'config/v133_science_config.json').read_text(encoding='utf-8'))
    path=repo/library_relative
    if expected_library_sha256 and sha256(path)!=expected_library_sha256:
        raise ValueError('F2C_LIBRARY_SHA_DIFFERENT_FROM_FROZEN')
    legacy,checks=load_library(path,kind='F2',optical=optical(config))
    if expected_old_model_id and legacy.model_id!=expected_old_model_id:
        raise ValueError('OLD_F2_MODEL_ID_MISMATCH')
    kernel=Path(__file__).with_name('v142_field_reference.py')
    thisfile=Path(__file__)
    cand=F2SpatialCubic(legacy,library_sha256=sha256(path),spatial_kernel_sha256=sha256(kernel),source_code_sha256=sha256(thisfile))
    return legacy,cand,checks
