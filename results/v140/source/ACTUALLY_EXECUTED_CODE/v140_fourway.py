"""V140 P2b: four-way per-pixel decomposition on the frozen canonical convention.

A_direct (V140 canonical npz), B_canonical_oracle (V140), B_v139_legacy_oracle
(V139 npz), C_frozen_F2 (evaluated at registry parameters, validator side only).
F2 calls are counted in the V140 budget ledger.
"""
from __future__ import annotations
import argparse, csv, json, sqlite3, sys
from pathlib import Path
import numpy as np, h5py
sys.path.insert(0, str(Path(__file__).resolve().parent))
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--config',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    cfg=json.loads(Path(a.config).read_text(encoding='utf-8'))
    sys.path.insert(0,str(repo/'tools'))
    from load_field_library import load_library
    from v133_recover_M import optical
    v133=json.loads((repo/'results/v133/M_F2_baseline/../..'/'config/v133_science_config.json').read_text(encoding='utf-8')) if False else json.loads((repo/'config/v133_science_config.json').read_text(encoding='utf-8'))
    model,_=load_library(repo/cfg['library_h5'],kind='F2',optical=optical(v133))
    rows=[];calls=0
    for c in cfg['M_opened_development_cases']:
        case=c['case'];D=c['D_nm'];h=c['h_nm'];dx=c['dx_nm'];dy=c['dy_nm']
        with np.load(out/'validation'/'cases'/f'{case}_at_offset.npz') as nz:
            A=nz['original_direct_raw_canonical'];B140=nz['canonical_wide_oracle']
        with np.load(repo/'results/v139/validation/oracle/cases'/f'{case}_at_offset.npz') as nz:
            B139=nz['oracle_canonical']
        C=model.forward((D,h,dx,dy)).C;calls+=1
        def m(X,Y):
            d=X-Y;n=float(np.linalg.norm(Y))
            return dict(abs_L2=float(np.linalg.norm(d)),relative_L2=float(np.linalg.norm(d)/n),max_abs=float(np.max(np.abs(d))))
        rows.append(dict(case=case,dx=dx,dy=dy,
            F2_vs_A_canonical=json.dumps(m(C,A)),
            F2_vs_B140_canonical=json.dumps(m(C,B140)),
            F2_vs_B139_legacy=json.dumps(m(C,B139)),
            B140_vs_A=json.dumps(m(B140,A)),
            B139_vs_A=json.dumps(m(B139,A)),
            F2_vs_A_pass1pct=bool(m(C,A)['relative_L2']<=0.01)))
    with (out/'validation'/'fourway_decomposition.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    # budget
    logs=out/'logs';logs.mkdir(parents=True,exist_ok=True)
    db=logs/'new_budget.sqlite'
    con=sqlite3.connect(db) if db.exists() else sqlite3.connect(db)
    con.execute('CREATE TABLE IF NOT EXISTS budget(event TEXT,f2_calls INT,new_renders INT,new_camera_exposures INT)')
    con.execute('INSERT INTO budget VALUES (?,?,?,?)',('P2b_fourway_F2',calls,0,0))
    con.commit()
    tot=con.execute('SELECT SUM(f2_calls) FROM budget').fetchone()[0]
    con.close()
    print('fourway done; F2 this stage=',calls,'total_v140=',tot)
    for r in rows:
        m=json.loads(r['F2_vs_A_canonical']);print(r['case'],'F2_vs_A=%.4f pass=%s'%(m['relative_L2'],r['F2_vs_A_pass1pct']))
if __name__=='__main__':main()
