"""V157: finite-precision auxiliary measurement design using V156 real candidate Jacobians."""
from __future__ import annotations
import argparse, json, os, sys, glob
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v157_height_design import local_design, SIGMAS_NM
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    out.mkdir(parents=True,exist_ok=True)
    # Load V156 real candidate Jacobians
    jacobians={}
    for p in sorted((repo/'results/v156/joint').glob('*/result.json')):
        grp=p.parent.name
        d=json.loads(p.read_text(encoding='utf-8'))
        diag=d.get('diagnostic',{})
        jw=diag.get('whitened_J_fine')
        if jw and len(jw)==169 and len(jw[0])==4:
            jacobians[grp]=np.asarray(jw,dtype=float)
    print(f'Loaded {len(jacobians)} real candidate Jacobians',flush=True)
    # Run design analysis for each group
    designs={}
    for grp,jw in sorted(jacobians.items()):
        results=[]
        # No constraint (ideal known h/x/y)
        r=local_design(jw,sigma_h=0,sigma_xy=0)
        results.append(dict(design='ideal_known_hxy',**{k:v for k,v in r.items() if not isinstance(v,np.ndarray)}))
        # No constraint (no auxiliary)
        r=local_design(jw,sigma_h=float('inf'),sigma_xy=float('inf'))
        results.append(dict(design='no_auxiliary',**{k:v for k,v in r.items() if not isinstance(v,np.ndarray)}))
        # Height only at various sigma
        for s in SIGMAS_NM:
            r=local_design(jw,sigma_h=s,sigma_xy=float('inf'))
            results.append(dict(design=f'height_sigma_{s}nm',**{k:v for k,v in r.items() if not isinstance(v,np.ndarray)}))
        # xy only at various sigma
        for s in SIGMAS_NM:
            r=local_design(jw,sigma_h=float('inf'),sigma_xy=s)
            results.append(dict(design=f'xy_sigma_{s}nm',**{k:v for k,v in r.items() if not isinstance(v,np.ndarray)}))
        designs[grp]=results
        # Extract key metric: remaining D norm fraction for ideal vs no_aux
        ideal=[r for r in results if r['design']=='ideal_known_hxy'][0]
        noaux=[r for r in results if r['design']=='no_auxiliary'][0]
        print(f'{grp}: ideal={ideal.get("remaining_D_norm","?")} no_aux={noaux.get("remaining_D_norm","?")}',flush=True)
    json.dump(designs,open(out/'height_design_results.json','w'),indent=1,default=str)
    print(f'V157 design done for {len(designs)} groups',flush=True)
if __name__=='__main__':main()
