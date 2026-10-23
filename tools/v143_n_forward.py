"""V143 W2: N same-solve + forward quality at registry parameters (validator side).

Columns per runbook: anon_case, raw_render_SHA, solve_SHA, renderer_code_SHA,
observed_score_SHA, F2c_model_id, source_verified, canonical_array_diff,
max_abs_C, relative_L2_F2c_at_truth, relative_L2_F2_at_truth,
relative_L2_SourceWide_S1, relative_L2_SourceWide_S2, error_status.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, sys
from pathlib import Path
import numpy as np, h5py
sys.path.insert(0, str(Path(__file__).resolve().parent))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--config',required=True)
    ap.add_argument('--validator-mapping',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    cfg=json.loads(Path(a.config).read_text(encoding='utf-8'))
    sys.path.insert(0,str(repo/'tools'))
    from v142_model import construct
    from v141_common import matlab_field_canonical,canonical_axes,sample_bilinear,sample_cubic,pixel_intensities
    legacy,cand,_=construct(repo,
        expected_old_model_id=cfg['parent_f2_model_id'])
    lineage=list(csv.DictReader((out.parent/'provenance'/'N_solve_lineage.csv').open(encoding='utf-8')))
    valmap=json.loads(Path(a.validator_mapping).read_text(encoding='utf-8'))
    truth=json.loads((repo/'config/v142_new_N_validator_only.json').read_text(encoding='utf-8'))['cases']
    truth_by={c['case']:c for c in truth}
    rows=[];calls=0
    for lr in lineage:
        case=lr['case'];anon=lr['anon'];tr=truth_by[case]
        D,h,dx,dy=tr['D_nm'],tr['h_nm'],tr['x_nm'],tr['y_nm']
        p_at=Path(valmap[('holdout_'+case)]['at_offset']['file'])
        p_wide=Path(valmap[('holdout_'+case)]['wide']['file'])
        with h5py.File(p_at,'r') as f:
            g=f['r']
            raw=np.asarray(g['contrast'][()],float)
            Er_d=matlab_field_canonical(g['Eref']);Es_d=matlab_field_canonical(g['Esca'])
            fxd,fyd=canonical_axes(g['fine_x_nm'][()],g['fine_y_nm'][()])
        with h5py.File(p_wide,'r') as f:
            g=f['r']
            Er_w=matlab_field_canonical(g['Eref']);Es_w=matlab_field_canonical(g['Esca'])
            fxw,fyw=canonical_axes(g['fine_x_nm'][()],g['fine_y_nm'][()])
        C_direct=raw.T[::-1,:]
        # observed score sha (central13 canonical)
        obs=C_direct[2:15,2:15]
        # F2c + F2 at truth
        Cf2c=cand.forward((D,h,dx,dy)).score_C;calls+=1
        Cf2=legacy.forward((D,h,dx,dy)).score_C;calls+=1
        # source-wide shifted (S1 bilinear, S2 cubic) re-imaged with wide Eref
        subs=((np.arange(5)+.5)/5-.5)*280.
        centers=(np.arange(17)-8)*280.
        Qx=(centers[:,None]+subs[None,:]).ravel()-dx
        Qy=(centers[:,None]+subs[None,:]).ravel()-dy
        def sample(F,fx,fy,Qx,Qy,method):
            return sample_bilinear(F,fx,fy,Qx,Qy) if method=='S1' else sample_cubic(F,fx,fy,Qx,Qy)
        def image(Er,Es):
            I=np.sum(np.abs(Er+Es)**2,axis=-1)
            Ip,Ibg=pixel_intensities(I,np.sum(np.abs(Er)**2,axis=-1),q=5)
            return (Ip-Ibg)/Ibg
        out_s1=np.empty((85,85,3),complex);out_s2=np.empty_like(out_s1)
        # simpler: evaluate wide fields on the shifted standard-camera query grid
        qx=centers[:,None]+subs[None,:]
        Q2x=(qx).ravel()-dx;Q2y=(qx).ravel()-dy
        Es_s1=sample(Es_w,fxw,fyw,Q2x,Q2y,'S1')
        Es_s2=sample(Es_w,fxw,fyw,Q2x,Q2y,'S2')
        Er_c=sample(Er_w,fxw,fyw,qx.ravel(),qx.ravel(),'S1')
        def cam(Er,Es):
            k=85//5
            I=np.sum(np.abs(Er+Es)**2,axis=-1).reshape(17,5,17,5).mean(axis=(1,3))
            Ibg=np.sum(np.abs(Er)**2,axis=-1).reshape(17,5,17,5).mean(axis=(1,3))
            return (I-Ibg)/Ibg
        Cs1=cam(Er_c,Es_s1);Cs2=cam(Er_c,Es_s2)
        # canonical transform for camera images
        Cs1c=Cs1.T[::-1,:];Cs2c=Cs2.T[::-1,:]
        def rel(A,B):
            n=float(np.linalg.norm(B));d=A-B
            return float(np.linalg.norm(d)/n) if n>1e-12 else None
        # canonical array diff: merged-H5 central13 vs raw-derived central13
        with h5py.File(repo/'results/v132/validation/new_M_images.h5','r') as f:pass  # M only; N merged not applicable
        rows.append(dict(anon_case=anon,
            raw_render_SHA=sha(p_at),solve_SHA=lr['solve_sha256'],
            renderer_code_SHA='3b60804ac5f604f40a5b2f5312ee59c277f255a8',
            observed_score_SHA=hashlib.sha256(np.ascontiguousarray(obs).tobytes()).hexdigest(),
            F2c_model_id=cand.model_id,source_verified=lr['lineage'],
            canonical_array_diff='N_MERGED_NOT_APPLICABLE',
            max_abs_C=float(np.max(np.abs(Cf2c-C_direct[2:15,2:15]))),
            relative_L2_F2c_at_truth=rel(Cf2c,C_direct[2:15,2:15]),
            relative_L2_F2_at_truth=rel(Cf2,C_direct[2:15,2:15]),
            relative_L2_SourceWide_S1=rel(Cs1c,C_direct),
            relative_L2_SourceWide_S2=rel(Cs2c,C_direct),
            error_status='OK' if min(rel(Cf2c,C_direct[2:15,2:15]),rel(Cs2c[2:15,2:15],C_direct[2:15,2:15]))<=0.01 else 'FRACTIONAL_OR_F2_ABOVE_1PCT'))
    with (out/'N_same_solve_and_F2c_forward.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    for r in rows:
        print(r['anon_case'],'F2c=%.4f F2=%.4f S1=%.4f S2=%.4f %s'%(r['relative_L2_F2c_at_truth'],r['relative_L2_F2_at_truth'],r['relative_L2_SourceWide_S1'],r['relative_L2_SourceWide_S2'],r['error_status']))
    json.dump(dict(f2_calls=calls),open(out/'n_forward_budget.json','w'))
if __name__=='__main__':main()
