"""V143 W1: N solve lineage from cache keys + MATLAB ledger + SHAs.

Links each anonymous N image to the actual original BEM solve via the
generation-time cache_key_map and execution ledger; verifies solve geometry
against the preregistered validator registry (validator side only).
"""
from __future__ import annotations
import argparse, csv, hashlib, json, re, sys
from pathlib import Path
import numpy as np, h5py
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--validator-mapping',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    src=out/'n_solve_source'
    kmap=list(csv.DictReader((src/'cache_key_map.csv').open(encoding='utf-8')))
    ledger=list(csv.DictReader((src/'v142_N_matlab_ledger.csv').open(encoding='utf-8-sig')))
    valmap=json.loads(Path(a.validator_mapping).read_text(encoding='utf-8'))
    truth=json.loads((repo/'config/v142_new_N_validator_only.json').read_text(encoding='utf-8'))['cases']
    truth_by_tag={c['case']:c for c in truth}
    rows=[]
    for tag,v in sorted(valmap.items()):
        m=re.search(r'(N\d+)',tag)
        n=m.group(1) if m else tag.replace('holdout_','')
        tr=truth_by_tag[n]
        solve_row=next(r for r in kmap if r['keytype']=='solve' and ('holdout_'+n+'__') in r['full_key'])
        sp=src/Path(solve_row['file']).name
        solve_sha=sha(sp)
        ledger_ok=any(r.get('case_tag')==('holdout_'+n) and r.get('action')=='solve' and r.get('ok')=='1'
                      for r in ledger)
        with h5py.File(sp,'r') as f:
            m=f['meta']
            D=float(m['D_nm'][()]);h=float(m['h_nm'][()]);gap=float(m['gap_nm'][()])
            mesh=int(float(m['mesh'][()]));npr=float(m['np_re'][()]);npi=float(m['np_im'][()])
            lam=float(m['lambda_nm'][()]);NA=float(m['NA'][()]);sid=''.join(chr(int(c)) for c in m['solver_id'][()].ravel())
        geom_ok=bool(abs(D-tr['D_nm'])<1e-9 and abs(h-tr['h_nm'])<1e-9 and mesh==1444)
        renders={}
        for variant,pathinfo in v.items():
            if not isinstance(pathinfo,dict):continue
            renders[variant]=dict(render_sha256=sha(pathinfo['file']),file=pathinfo['file'])
        rows.append(dict(case=n,anon=str(v.get('anon_id',n)),
            solve_filename=sp.name,solve_sha256=solve_sha,solver_id=sid,
            D_nm=D,h_center_nm=h,gap_nm=gap,mesh=mesh,n_particle=f'{npr}{npi:+.1f}j',
            lambda_nm=lam,NA=NA,geometry_matches_registry=geom_ok,
            ledger_execution_ok=bool(ledger_ok),
            renders=renders,
            lineage='CACHE_KEY_PLUS_LEDGER_PLUS_GEOMETRY_LINKED',
            limitation='render-to-solve via generation pipeline identity, not embedded content SHA'))
    fields=list(rows[0].keys())+['render_detail'] if False else list(rows[0].keys())
    with (out/'N_solve_lineage.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in rows:
            rr=dict(r);rr['renders']=json.dumps(r['renders']);w.writerow(rr)
    (out/'N_solve_lineage.json').write_text(json.dumps(dict(rows=rows,
        status='N_SOLVE_LINEAGE_RECONSTRUCTED_FROM_GENERATION_TIME_CACHE_KEYS_AND_LEDGER',
        new_bem_attempts=0),indent=2,ensure_ascii=False)+chr(10),encoding='utf-8')
    print('N_LINEAGE rows=',len(rows),'geom_ok=',sum(r['geometry_matches_registry'] for r in rows),'ledger_ok=',sum(r['ledger_execution_ok'] for r in rows))
if __name__=='__main__':main()