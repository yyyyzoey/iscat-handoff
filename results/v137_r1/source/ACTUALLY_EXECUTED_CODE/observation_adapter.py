"""Read already-exported static signed C without guessing axes or physical truth.
Root C and at_offset/C are allowed only when unambiguous; every selection is logged.
Missing wide coordinates never prevent image-only inference. This is not a
certification that a root C belongs to the declared physical offset.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import h5py
import numpy as np


def file_sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def array_sha(a):
    a=np.ascontiguousarray(a)
    return hashlib.sha256((str(a.shape)+'|'+str(a.dtype)).encode()+a.tobytes()).hexdigest()


def image_schema(path):
    rows=[]
    with h5py.File(path,'r') as f:
        def visit(name,obj):
            if isinstance(obj,h5py.Dataset):
                rows.append(dict(path=name,shape=list(obj.shape),dtype=str(obj.dtype)))
        f.visititems(visit)
    return dict(path=str(Path(path).resolve()),sha256=file_sha256(path),datasets=rows)


def read_static_observations(path, cases, *, dataset='AUTO_UNIQUE_STATIC_C', camera_n=17, score_n=13):
    if len(cases)!=len(set(cases)):raise ValueError('Duplicate observation IDs')
    if camera_n<score_n or (camera_n-score_n)%2:raise ValueError('Noncentral crop')
    records=[]
    with h5py.File(path,'r') as f:
        for case in cases:
            if case not in f:raise KeyError(f'Missing case: {case}')
            g=f[case]
            if dataset=='AUTO_UNIQUE_STATIC_C':
                options=[p for p in ('at_offset/C','C') if p in g and isinstance(g[p],h5py.Dataset)]
                if len(options)!=1:
                    raise ValueError(f'{case}: ambiguous/missing static image {options}; explicitly select dataset using original render evidence')
                selected=options[0]
            else:
                selected=dataset
            a=g[selected][()]
            if np.iscomplexobj(a) or a.dtype.names or a.dtype.kind not in 'fiu':
                raise ValueError(f'{case}: real numerical signed static contrast required')
            a=np.asarray(a,dtype=np.float64)
            if not np.isfinite(a).all():raise ValueError(f'{case}: nonfinite observation')
            original=a.copy()
            if a.shape==(camera_n,camera_n):
                k=(camera_n-score_n)//2;a=a[k:k+score_n,k:k+score_n].copy()
                transform=f'CENTRAL_{score_n}_FROM_{camera_n}_NO_FLIP_NO_SCALE'
            elif a.shape==(score_n,score_n):
                a=a.copy();transform='ALREADY_SCORE_ROI_NO_FLIP_NO_SCALE'
            else:raise ValueError(f'{case}: unexpected image shape {a.shape}')
            missing=[]
            if 'wide' not in g:missing=['wide']
            else:missing=[p for p in ('Eref','Esca','fine_x_nm','fine_y_nm') if p not in g['wide']]
            records.append(dict(case=case,image=a,original=original,
                                binding=dict(case=case,source_dataset=f'{case}/{selected}',
                                  source_file_sha256=file_sha256(path),source_array_sha256=array_sha(original),
                                  score_array_sha256=array_sha(a),transform=transform,
                                  observation='STATIC_SIGNED_C',
                                  physical_role='DECLARED_DIRECT_IMAGE_REQUIRES_RAW_RENDER_COMPARISON',
                                  missing_optional_wide=missing)))
    return records
