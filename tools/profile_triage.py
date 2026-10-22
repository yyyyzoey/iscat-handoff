"""Read-only triage of legacy finite profiles. This is not a global certificate."""
from __future__ import annotations
import argparse,json,math
from pathlib import Path


def triage(profile):
    rows=profile.get('rows',[]);seen=set(); repairs=[];valid=[]
    for r in rows:
        D=float(r['D'])
        if not math.isfinite(D) or D in seen: raise ValueError('Duplicate or nonfinite diameter')
        seen.add(D);why=[]
        loss=r.get('loss');ats=r.get('attempts',[])
        if loss is None or not math.isfinite(float(loss)) or float(loss)<0: why.append('NO_FINITE_WITNESS')
        else: valid.append((D,float(loss)))
        if not ats:why.append('NO_ATTEMPTS')
        if any(a.get('budget_exhausted',False) for a in ats):why.append('UNRESOLVED_START_BUDGET')
        if any(a.get('success') is not True for a in ats):why.append('UNRESOLVED_OPTIMIZER_EXIT')
        if any(a.get('status')==0 for a in ats):why.append('MAX_NFEV_EXIT')
        if why:repairs.append(dict(D=D,reasons=sorted(set(why))))
    return dict(n_rows=len(rows),legacy_profile_complete=profile.get('profile_complete'),
                repair_points=repairs,coarse_attempts_have_no_known_failure=bool(rows and not repairs),
                min_finite_loss=min((v for d,v in valid),default=None),
                requires_adaptive_compatibility_refinement=True,
                scientific_reportability_certified=False,
                note='A finished finite coarse search is not complete sizing uncertainty or proof of global uniqueness.')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--profiles',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    result={p.stem:triage(json.loads(p.read_text(encoding='utf-8-sig'))) for p in sorted(Path(a.profiles).glob('*.json'))}
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'profiles':len(result),'with_unresolved_points':sum(bool(v['repair_points']) for v in result.values())}))
if __name__=='__main__':main()
