"""Zero-new-BEM REAL-HDF5 identity experiment on V133 official F2 and V135 legacy F2.

Run on the user's existing full checkout with verified HDF5 and SciPy. This
compares *exactly the same theta and image*; it does not assert a universal
physical model truth or automatically change the original model.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,sys
from pathlib import Path
import numpy as np
import h5py

EXPECTED_MODEL='v131-field-db000d86636ed018cf1f9bd5291c7409b7e9d2aaa481328b3c22dfdb1a689427'
EXPECTED_LIBRARY_SHA='203e9e5f2d888503b62d48888a0f2e5365477b06101227109a3e98286f541c0f'
CASES=[f'M{i:02d}' for i in range(1,7)]


def sha256(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda:f.read(1<<20),b''):h.update(c)
    return h.hexdigest()


def audit(repo:Path):
    repo=repo.resolve()
    tool_dir=(repo/'tools').resolve()
    if not tool_dir.is_dir():raise FileNotFoundError(tool_dir)
    sys.path.insert(0,str(tool_dir))
    from load_field_library import load_library
    from v133_recover_M import optical
    from v129_field_forward import ComplexFieldForward
    cfg=json.loads((repo/'config/v133_science_config.json').read_text(encoding='utf-8-sig'))
    lib=repo/'results/v128/library/v128_Dh_train_fields.h5'
    if sha256(lib)!=EXPECTED_LIBRARY_SHA:raise ValueError('Library SHA differs: no reuse of historical fits')
    base,_=load_library(lib,kind='F2',optical=optical(cfg))
    if base.model_id!=EXPECTED_MODEL:raise ValueError('Official V133 F2 model identity changed')
    old=ComplexFieldForward(lib_path=str(lib),kind='F2')
    obs=repo/'results/v133/M_F2_baseline/anonymous_M_images.h5'
    fits=repo/'results/v133/M_F2_baseline/fits'
    out=[]
    with h5py.File(obs,'r') as hh:
        for k in CASES:
            fit=json.loads((fits/f'M_{k}.json').read_text(encoding='utf-8'))
            if fit.get('model_id')!=EXPECTED_MODEL:raise ValueError(f'{k}: unqualified fit source')
            theta=np.array(fit['theta'],float)
            if theta.shape!=(4,) or not np.isfinite(theta).all():raise ValueError(f'{k}: bad theta')
            Y=np.array(hh[k]['score_C'][()],float)
            official=np.asarray(base.forward(theta).score_C,float)
            legacy_error=None
            try:
                legacy=np.asarray(old.C(*theta),float)
            except Exception as exc:
                legacy_error=f'{type(exc).__name__}: {exc}'
                legacy=None
            if official.shape!=(13,13) or Y.shape!=official.shape:
                raise ValueError(f'{k}: incompatible official image shape')
            if legacy is not None and legacy.shape!=official.shape:
                legacy_error=f'LEGACY_SHAPE_MISMATCH: {legacy.shape}'
                legacy=None
            r_off=float(np.linalg.norm(official-Y));r_old=float(np.linalg.norm(legacy-Y)) if legacy is not None else None
            r_known=float(fit['loss'])
            tol=max(1e-12,1e-7*abs(r_known))
            if abs(r_off-r_known)>tol:
                raise ValueError(f'{k}: official replay mismatches shipped fit; investigate library / code / image IDs')
            max_delta=float(np.max(np.abs(official-legacy))) if legacy is not None else None
            is_equal=bool(max_delta is not None and max_delta<=1e-12)
            out.append(dict(case=k,theta_D=theta[0],theta_h=theta[1],theta_x=theta[2],theta_y=theta[3],
                      v133_F2_model_id=base.model_id,official_reference_residual_L2=r_off,
                      v133_shipped_residual_L2=r_known,v129_legacy_residual_L2=r_old,
                      official_vs_legacy_C_max_abs=max_delta,legacy_error=legacy_error,
                      same_numeric_forward_to_1e_minus_12=is_equal,
                      verdict='PARITY_PASS' if is_equal else 'DIFFERENT_OR_FAILED_FORWARD_NOT_INTERCHANGEABLE'))
    return out


def main():
    a=argparse.ArgumentParser()
    a.add_argument('--repo',required=True);a.add_argument('--out',required=True)
    x=a.parse_args();dest=Path(x.out);dest.parent.mkdir(parents=True,exist_ok=True)
    try:
        rows=audit(Path(x.repo))
        with dest.open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        mismatches=[r['case'] for r in rows if r['verdict']!='PARITY_PASS']
        print(f'V133_F2_REPLAY=PASS; OLD_V129_F2_EQUIVALENCE={"PASS" if not mismatches else "FAIL"}; cases={mismatches}')
        return 0 if not mismatches else 3
    except Exception as e:
        dest.with_suffix(dest.suffix+'.error.json').write_text(json.dumps({'stage':'REAL_FIELD_IMPLEMENTATION_PARITY','error':f'{type(e).__name__}: {e}','status':'BLOCKED_NOT_EVALUATED'},indent=2)+'\n')
        print(f'NOT_EVALUATED: {type(e).__name__}: {e}',file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
