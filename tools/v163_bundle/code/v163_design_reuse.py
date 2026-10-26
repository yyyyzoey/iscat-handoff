"""Compare pure-algebra evaluations to the reviewed V162 saved-array result.
This validates reuse of coefficients only, never optical source or precision.
"""
import hashlib,json,math
from pathlib import Path
EXPECTED='4c91766adab0952acabde8c90daebfa15e83ebf94e0a670bc0c7a23c45dfc1e5'

def compare_designs(old,current):
    if set(old)!=set(current) or len(old)!=12:raise ValueError('REUSE_GROUP_SET_CHANGED')
    count=0;max_abs=0.
    for key,g in old.items():
        c=current[key]
        if g['theta']!=c['theta'] or g['boundary']!=c['boundary']:
            raise ValueError('REUSE_ANCHOR_CHANGED:'+key)
        for scale in ('coarse','fine'):
            if set(g['designs'][scale])!=set(c['designs'][scale]):raise ValueError('REUSE_DESIGN_SET_CHANGED')
            for name,rs in g['designs'][scale].items():
                cs=c['designs'][scale][name]
                if len(rs)!=3 or len(cs)!=3:raise ValueError('REUSE_RTOL_COUNT')
                for a,b in zip(rs,cs):
                    if a['rtol']!=b['rtol']:raise ValueError('REUSE_RTOL_CHANGED')
                    for field in ['sigma_h_nm','sigma_xy_nm','exact_height','exact_xy','no_height_measurement','no_xy_measurement','nuisance_rank']:
                        if a[field]!=b[field]:raise ValueError('REUSE_CONDITION_CHANGED:'+field)
                    for field in ['total_coefficient_nm_minus2','image_coefficient_nm_minus2','auxiliary_coefficient_nm_minus2','D_squared_norm']:
                        x,y=float(a[field]),float(b[field]);err=abs(x-y);max_abs=max(max_abs,err)
                        if not math.isfinite(x+y) or err>max(1e-14,1e-10*abs(x),1e-12*a['D_squared_norm']):
                            raise ValueError('REUSE_COEFFICIENT_CHANGED:'+key+':'+name+':'+field)
                    count+=1
    if count!=1224:raise ValueError('REUSE_EXPECTED_1224')
    return dict(state='V162_SAVED_ARRAY_ALGEBRA_REPRODUCED',records=count,max_absolute_difference=max_abs,
                model_forward_calls=0,scope='NOT_BOUND_OPTICAL_REPLAY_NOT_EXPERIMENTAL_PRECISION')

def check_reference(bundle,current):
    p=Path(bundle)/'audit/v162_saved_array_designs.json';raw=p.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=EXPECTED:raise ValueError('V162_SAVED_DESIGN_BYTES_CHANGED')
    r=compare_designs(json.loads(raw),current);r['source_sha256']=EXPECTED;return r
