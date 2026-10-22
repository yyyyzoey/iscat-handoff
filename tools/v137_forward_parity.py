"""W1: same-point numerical parity between locked official F2 and legacy v129 diagnostic.

Scope: software numerical identity ONLY. Passing rows do not certify Maxwell
correctness, physical provenance, or any diameter. No truth is read.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))

SENTINELS = [
 (33.7,362.5, 123.4,-267.8),(41.3,377.5,-311.2,  45.6),(57.9,412.5,  88.9,-499.0),
 (66.5,437.5,-249.9, 249.9),(74.1,462.5, 499.0, -88.9),(88.8,487.5,-123.4, 311.2),
 (95.2,522.5,  45.6, -45.6),(103.6,537.5,-499.0, 123.4),(111.4,362.5, 267.8,-311.2),
 (127.9,377.5, -88.9, 499.0),(135.7,412.5, 311.2,  88.9),(143.2,437.5,-249.9,-249.9),
 (158.3,462.5,  88.9, 499.0),(166.1,487.5,-311.2, -45.6),(174.9,522.5, 249.9, 249.9),
 (182.4,537.5, -45.6,-499.0),(191.6,362.5, 499.0, 311.2),(198.7,412.5,-499.0, -88.9),
 (30.1,537.5, 123.4, 123.4),(199.3,475.0,-123.4,-123.4),(100.3,450.2, 234.5,-123.4),
 (120.4,500.1,-234.5, 234.5),(140.6,425.1,  12.3, 456.7),(160.8,549.9, -456.7, -12.3),
 (50.2,350.4,  78.9, -78.9),(190.1,475.3, -78.9,  78.9),
]
OOD_POINTS=[(25.0,450.0,0.0,0.0,'D_below'),(205.0,450.0,0.0,0.0,'D_above'),
 (100.0,340.0,0.0,0.0,'h_below'),(100.0,560.0,0.0,0.0,'h_above'),
 (100.0,450.0,501.0,0.0,'x_out'),(100.0,450.0,0.0,-501.0,'y_out'),
 (200.0,450.0,0.0,0.0,'gap_violation'),(float('nan'),450.0,0.0,0.0,'nonfinite')]

def sha_arr(a):
    import hashlib
    return hashlib.sha256(np.ascontiguousarray(a,dtype=np.float64).tobytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    out.mkdir(parents=True,exist_ok=True)
    from load_field_library import load_library
    from v133_recover_M import optical
    from v129_field_forward import ComplexFieldForward,OutOfDomain as LegacyOOD
    from field_forward_reference import OutOfDomain as OfficialOOD
    cfg=json.loads((repo/'config/v133_science_config.json').read_text(encoding='utf-8'))
    v137=json.loads((repo/'config/v137_science_config.json').read_text(encoding='utf-8'))
    lib=repo/v137['inherited_model']['library']
    model,_=load_library(lib,kind='F2',optical=optical(cfg))
    expected=v137['inherited_model']['model_id']
    if model.model_id!=expected:raise SystemExit('model identity mismatch')
    legacy=ComplexFieldForward(str(lib),kind='F2')
    fits=[]
    for i in range(1,7):
        c=f'M{i:02d}'
        ft=json.loads((repo/v137['inherited_model']['prior_fits']/f'M_{c}.json').read_text(encoding='utf-8'))
        fits.append((c,[float(v) for v in ft['theta']],float(ft['loss'])))
    rows=[]
    def evaluate(tag,theta):
        D,h,x,y=theta
        try:co=model.forward(tuple(theta)).score_C
        except OfficialOOD as e:co=None;ood_off=str(e)
        else:ood_off=''
        try:cl=legacy.C(D,h,x,y)
        except LegacyOOD as e:cl=None;ood_leg=str(e)
        else:ood_leg=''
        if co is None and cl is None:
            rows.append(dict(point_id=tag,D=D,h=h,x=x,y=y,both_domain_reject=True,
                official_ood=ood_off,legacy_ood=ood_leg,verdict='BOTH_OOD',max_abs_C_diff=''))
            return
        if co is None or cl is None:
            rows.append(dict(point_id=tag,D=D,h=h,x=x,y=y,both_domain_reject=False,
                official_ood=ood_off,legacy_ood=ood_leg,verdict='DOMAIN_BEHAVIOR_MISMATCH',max_abs_C_diff=''))
            return
        d=float(np.max(np.abs(co-cl)))
        rows.append(dict(point_id=tag,D=D,h=h,x=x,y=y,both_domain_reject=False,
            official_ood='',legacy_ood='',
            official_C_shape='x'.join(map(str,co.shape)),legacy_C_shape='x'.join(map(str,cl.shape)),
            max_abs_C_diff=repr(d),official_C_sha256=sha_arr(co),legacy_C_sha256=sha_arr(cl),
            verdict='PARITY_PASS' if d<=1e-12 else 'PARITY_FAIL'))
    for c,th,ls in fits:evaluate('EXACT_JOINT_'+c,th)
    for i,s in enumerate(SENTINELS,1):evaluate(f'SENTINEL_{i:02d}',list(s))
    ood=[]
    for t in OOD_POINTS:
        theta,label=list(t[:-1]),t[-1]
        def r(f):
            try:f();return 'NO_REJECT'
            except (OfficialOOD,LegacyOOD) as e:return 'REJECT'
            except Exception as e:return 'OTHER:'+type(e).__name__
        ood.append(dict(label=label,theta=json.dumps([None if isinstance(v,float) and not np.isfinite(v) else v for v in theta]),
            official=r(lambda:model.forward(tuple(theta))),legacy=r(lambda:legacy.C(*theta))))
    fd=[]
    D0,h0,x0,y0=100.3,450.2,123.4,-267.8
    for delta in (1e-3,1e-2,1e-1):
        go=model.forward((D0+delta,h0,x0,y0)).score_C-model.forward((D0-delta,h0,x0,y0)).score_C
        gl=legacy.C(D0+delta,h0,x0,y0)-legacy.C(D0-delta,h0,x0,y0)
        fd.append(dict(axis='D',delta_nm=delta,official_fd_max=repr(float(np.max(np.abs(go)))),
            legacy_fd_max=repr(float(np.max(np.abs(gl)))),fd_max_abs_diff=repr(float(np.max(np.abs(go-gl))))))
    # actual F2 replay of the six exact thetas (same target, same Y already SHA-bound in profiles)
    replay=[]
    for c,th,old in fits:
        pth=out.parent/'offline_F2_profiles'/'profiles'/f'{c}.json'
        prof=json.loads(pth.read_text(encoding='utf-8'))
        wit=min((r for r in prof['rows'] if abs(r['D']-th[0])<=1e-8),key=lambda r:r['loss_L2'])
        replay.append(dict(case=c,joint_D=th[0],v133_loss_L2=old,
            new_witness_loss_L2=wit['loss_L2'],abs_diff=abs(wit['loss_L2']-old),
            tol=max(1e-12,1e-7*abs(old)),verdict='REPLAY_PASS' if abs(wit['loss_L2']-old)<=max(1e-12,1e-7*abs(old)) else 'REPLAY_FAIL'))
    with (out/'forward_parity_matrix.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=sorted({k for r in rows for k in r}));w.writeheader();w.writerows(rows)
    with (out/'actual_F2_replay.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['case','joint_D','v133_loss_L2','new_witness_loss_L2','abs_diff','tol','verdict'])
        w.writeheader();w.writerows(replay)
    (out/'domain_and_derivative_behavior.json').write_text(json.dumps(
        dict(out_of_domain=ood,finite_difference_diagnostic=fd,
             scope='SOFTWARE_NUMERIC_BEHAVIOR_ONLY'),indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    npass=sum(r['verdict']=='PARITY_PASS' for r in rows)
    print(f'W1_PARITY rows={len(rows)} pass={npass} exact_replay={sum(r["verdict"]=="REPLAY_PASS" for r in replay)}/6')
if __name__=='__main__':main()

