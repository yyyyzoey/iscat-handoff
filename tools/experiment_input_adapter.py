#!/usr/bin/env python3
"""Strict observable isolation. This is an adapter, NOT a calibrated estimator.

Input NPZ must contain I_linear and Ibg_linear, same camera ROI, un-stretched
(non-integer) float intensities. Historical ~400Hz FFT amplitude cannot use
this STATIC signed-C model.
"""
from __future__ import annotations
import argparse,hashlib
from pathlib import Path
import numpy as np
from _shared import save_json,sha

ACCEPTED='LINEAR_STATIC_INTENSITY_WITH_MATCHED_BACKGROUND'

def signed_C_from_linear(I,B,kind=ACCEPTED):
    if kind!=ACCEPTED:raise ValueError('REQUIRES_TYPED_STATIC_LINEAR_OBSERVATION__FFT_OR_ABS_C_FORBIDDEN')
    a=np.asarray(I);b=np.asarray(B)
    if a.dtype.kind!='f' or b.dtype.kind!='f':raise ValueError('NO_8BIT_OR_INTEGER_DISPLAY_INTENSITIES')
    if a.ndim!=2 or a.shape!=b.shape or a.shape not in ((17,17),(13,13)):
        raise ValueError('MATCHED_13_OR_17_CAMERA_ROI_REQUIRED')
    if not np.isfinite(a).all() or not np.isfinite(b).all() or np.any(b<=0) or np.any(a<0):
        raise ValueError('NONFINITE_NEGATIVE_OR_UNMATCHED_BACKGROUND')
    return (a.astype(float)-b.astype(float))/b.astype(float)

def main():
    p=argparse.ArgumentParser();p.add_argument('--npz',required=True);p.add_argument('--observable-kind',required=True)
    p.add_argument('--out',required=True);a=p.parse_args()
    with np.load(a.npz) as z:
        if 'I_linear' not in z or 'Ibg_linear' not in z:raise ValueError('I_linear/Ibg_linear_REQUIRED')
        C=signed_C_from_linear(z['I_linear'],z['Ibg_linear'],a.observable_kind)
    d=Path(a.out);d.mkdir(parents=True,exist_ok=True)
    np.save(d/'signed_static_C.npy',C)
    save_json(d/'input_receipt.json',{'status':'SIGNED_STATIC_C_CREATED_NOT_SIZING_CERTIFIED',
        'input_npz_sha256':sha(a.npz),'camera_shape':list(C.shape),'output_sha256':sha(d/'signed_static_C.npy'),
        'needs_actual_calibrated_material_optics_and_noise':'TRUE','experimental_absolute_diameter_validated':False})
    print('STATIC_SIGNED_C_CREATED_WITH_EXPLICIT_TYPE',d)
if __name__=='__main__':main()
