"""Independent release checks; no optical model, optimizer or true labels.

Preserves the approved core. np.linalg.lstsq is used only as an independent
augmented-system cross-check against the explicit SVD implementation.
"""
from __future__ import annotations
import hashlib,json,math,re
from pathlib import Path
import numpy as np
from v156_candidate_guard import EXPECTED

PROBE_GROUPS={(100000,'ANON_02'),(100000,'ANON_03'),(100000,'ANON_04')}
SIGMAS=(1.,2.,5.,10.,20.,50.,100.)
RTOLS=(1e-8,1e-10,1e-12)


def require(ok,message):
    if not ok:raise ValueError(message)


def expected_designs():
    d={'free':(math.inf,math.inf),'exact_height':(0.,math.inf),'exact_xy':(math.inf,0.)}
    d.update({f'height_sigma_{s:g}nm':(s,math.inf) for s in SIGMAS})
    d.update({f'xy_sigma_{s:g}nm':(math.inf,s) for s in SIGMAS})
    return d


def verify_kernel_identity(bundle):
    root=Path(bundle).resolve()
    lock=json.loads((root/'config/kernel_lock.json').read_text(encoding='utf-8'))
    required={'v152_budget_store.py','v152_gls_core.py','v155_pixel_diagnostics.py',
              'v155_stage.py','v156_candidate_guard.py','v157_height_design.py','audit_v156_readonly.py'}
    require(set(lock)==required,'KERNEL_LOCK_MEMBERS_CHANGED')
    checked={}
    for name,expected in lock.items():
        actual=hashlib.sha256((root/'code'/name).read_bytes()).hexdigest()
        require(actual==expected,'APPROVED_KERNEL_CHANGED:'+name);checked[name]=actual
    import v157_height_design as implementation
    require(Path(implementation.__file__).resolve()==root/'code/v157_height_design.py','WRONG_MATH_MODULE_IMPORTED')
    return checked


def independent_coefficient(jw,sigma_h,sigma_xy,rtol):
    j=np.asarray(jw,float)
    require(j.shape==(169,4) and np.isfinite(j).all(),'BAD_JACOBIAN')
    s=np.array([sigma_h,sigma_xy,sigma_xy],float)
    require(not np.isnan(s).any() and (s>=0).all(),'BAD_SIGMA')
    active=np.flatnonzero(s!=0)
    b=np.zeros(3)
    if len(active):
        top=j[:,1+active]
        penalty=np.diag([0. if math.isinf(s[k]) else 1./s[k] for k in active])
        matrix=np.vstack([top,penalty]);rhs=np.r_[-j[:,0],np.zeros(len(active))]
        require(matrix.shape[0]==rhs.size,'AUGMENTED_TARGET_LENGTH')
        norms=np.linalg.norm(matrix,axis=0);keep=norms>0
        if keep.any():
            x=np.linalg.lstsq(matrix[:,keep]/norms[keep],rhs,rcond=rtol)[0]
            b[active[keep]]=x/norms[keep]
    image=j[:,0]+j[:,1:]@b
    aux=sum((b[k]/s[k])**2 for k in range(3) if s[k]>0 and np.isfinite(s[k]))
    return float(image@image+aux),b


def validate_sweep(jw,sweep):
    j=np.asarray(jw,float);cases=expected_designs()
    require(set(sweep)==set(cases),'DESIGN_SET_NOT_17_REQUIRED_CONDITIONS')
    baseline=float(j[:,0]@j[:,0]);tol=max(1e-20,1e-9*baseline)
    for name,(h,xy) in cases.items():
        rows=sweep[name]
        require(len(rows)==3 and [r['rtol'] for r in rows]==list(RTOLS),'MISSING_RTOL_AXIS:'+name)
        for r in rows:
            require(r['sigma_h_nm']==(None if math.isinf(h) else h),'HEIGHT_LABEL_MISMATCH:'+name)
            require(r['sigma_xy_nm']==(None if math.isinf(xy) else xy),'XY_LABEL_MISMATCH:'+name)
            require(r['no_height_measurement']==math.isinf(h) and r['no_xy_measurement']==math.isinf(xy),'AUX_FLAGS_MISMATCH')
            require(r['exact_height']==(h==0) and r['exact_xy']==(xy==0),'EXACT_FLAGS_MISMATCH')
            b=np.asarray(r['compensation_nm_per_nm'],float)
            require(b.shape==(3,) and np.isfinite(b).all(),'BAD_COMPENSATION')
            if h==0:require(b[0]==0.,'EXACT_HEIGHT_NOT_FIXED')
            if xy==0:require(np.array_equal(b[1:],np.zeros(2)),'EXACT_XY_NOT_FIXED')
            image=j[:,0]+j[:,1:]@b;image2=float(image@image)
            aux2=(0. if h==0 or math.isinf(h) else (b[0]/h)**2)
            aux2+=0. if xy==0 or math.isinf(xy) else float(np.sum((b[1:]/xy)**2))
            require(abs(image2-r['image_coefficient_nm_minus2'])<=tol,'IMAGE_TERM_MISMATCH')
            require(abs(aux2-r['auxiliary_coefficient_nm_minus2'])<=tol,'AUXILIARY_TERM_MISMATCH')
            value=r['total_coefficient_nm_minus2']
            require(np.isfinite(value) and abs(value-image2-aux2)<=tol,'TOTAL_TERM_MISMATCH')
            expected,_=independent_coefficient(j,h,xy,r['rtol'])
            require(abs(value-expected)<=tol,'INDEPENDENT_AUGMENTED_LSTSQ_MISMATCH:'+name)
            require(-tol<=value<=baseline+tol,'OUTSIDE_LOCAL_COEFFICIENT_BOUNDS')
    for k in range(3):
        free=sweep['free'][k]['total_coefficient_nm_minus2']
        for name in cases:require(free<=sweep[name][k]['total_coefficient_nm_minus2']+tol,'AUX_WORSE_THAN_FREE')
        for prefix in ('height','xy'):
            ordered=[sweep['exact_'+prefix][k]['total_coefficient_nm_minus2']]
            ordered += [sweep[f'{prefix}_sigma_{s:g}nm'][k]['total_coefficient_nm_minus2'] for s in SIGMAS]
            ordered.append(free)
            require(all(a+tol>=b for a,b in zip(ordered,ordered[1:])),'PRECISION_MONOTONICITY_FAILED:'+prefix)
    return {'state':'INDEPENDENT_AUGMENTED_OBJECTIVE_CHECKED','records':51,'new_optical_calls':0}


def group_camera_events(events):
    require(len(events)==36,'EXPECTED_36_EVENTS')
    grouped={k:[] for k in EXPECTED};byid={}
    for ev in events:
        match=re.fullmatch(r'(ANON_0[1-4])_(0[0-2])',str(ev.get('label','')))
        require(match is not None,'INVALID_FULL_PARTICLE_FRAME_LABEL')
        B=ev['B'];key=(B,match.group(1))
        require(key in grouped,'UNKNOWN_BACKGROUND_OR_PARTICLE')
        expected_id=f'B{B}_{ev["label"]}'
        require(ev['event_id']==expected_id,'EVENT_ID_AND_LABEL_MISMATCH')
        require(expected_id not in byid,'DUPLICATE_EVENT')
        grouped[key].append(ev);byid[expected_id]=ev
    for key,evs in grouped.items():
        evs.sort(key=lambda r:r['event_id'])
        require([e['label'] for e in evs]==[f'{key[1]}_{i:02d}' for i in range(3)],'NOT_EXACTLY_THE_THREE_FRAMES')
    return grouped,byid


def validate_probe_plan(key,theta,rows):
    require(key in PROBE_GROUPS,'UNAUTHORIZED_PROBE_PARTICLE')
    require(len(rows)==24,'PROBE_GRID_NOT_24')
    expected={(p,t) for p in ('free_hxy','exact_height','height_sigma10') for t in (-5.,-2.,-1.,-.5,.5,1.,2.,5.)}
    require({(r['path'],r['delta_D_nm']) for r in rows}==expected,'WRONG_PROBE_PATHS_OR_DELTAS')
    for r in rows:
        require(np.array_equal(r['anchor_theta'],theta),'PROBE_ANCHOR_CHANGED')
        require(r['state'] in ('PLANNED','SKIPPED_OUT_OF_DOMAIN'),'UNKNOWN_PLANNED_STATE')
        if r['path']=='exact_height':
            require(r['direction_nm_per_nm'][1]==0.,'HEIGHT_FIXED_PATH_HAS_HEIGHT_MOTION')
        require(r['direction_nm_per_nm'][0]==1.,'DIAMETER_PATH_NOT_UNIT_PARAMETER')
    return True
