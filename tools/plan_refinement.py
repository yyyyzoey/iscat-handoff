#!/usr/bin/env python3
"""Read-only, truth-independent priorities from V144 profile witness audit.

The plan is an optimization SCHEDULE, not an inference result. Does NOT call F2c.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path

def plan(audit,max_points=6):
    cases={}
    for case,r in audit['cases'].items():
        if r.get('known_nonunique_under_assumed_epsilon'):
            cases[case]=dict(action='STOP_UNIQUE_SIZING__DOCUMENT_COMPETING_WITNESSES',
                reason='Existing distant attainable D values both under the UNQUALIFIED empirical epsilon',
                separated_pair=r['separated_compatible_witness_pair'],new_forward_needed=False,target_D=[])
            continue
        candidate=r.get('candidate_D');incumbent=r.get('observed_minimum_witness')
        points=r.get('all_D_and_residuals',[])
        seen={float(p['D']) for p in points}
        # Unconverged already-sampled points with low attainable loss are most
        # informative; never treat an unsampled D as high loss.
        marked=sorted([p for p in points if not p['complete'] and math.isfinite(float(p['R']))],
            key=lambda p:(p['R'],abs(p['D']-candidate) if candidate is not None else 0))
        targets=[p['D'] for p in marked[:max_points]]
        # If little remains to optimize on coarse grid, suggest local midpoints.
        if len(targets)<max_points and candidate is not None:
            for delta in (2.5,-2.5,5.,-5.,10.,-10.):
                D=float(candidate)+delta
                if 30<=D<=200 and all(abs(D-z)>1e-8 for z in list(seen)+targets):
                    targets.append(D)
                if len(targets)>=max_points:break
        cases[case]=dict(action='TARGETED_FIXED_D_NUISANCE_REFINEMENT',
            reason='No distant competing witness yet; incomplete/untested diameters remain UNKNOWN',
            new_forward_needed=bool(targets),target_D=targets[:max_points],
            every_fixed_D_must_optimize='h,x,y from multiple independent height basins; preserve prior valid point',
            may_certify_global_uniqueness=False)
    return dict(schema='iscat144.refinement_plan.1',cases=cases,
      context='DO_NOT_RUN_WITHOUT_FROZEN_MODEL_AND_OBSERVATION_IDENTITY_AND_PERSISTENT_PRECHARGED_BUDGET',
      truth_not_used=True,no_global_optimum_claim=True,reported_diameters=[])

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--audit',required=True);ap.add_argument('--out',required=True);ap.add_argument('--max-points-per-case',type=int,default=6);a=ap.parse_args()
    if a.max_points_per_case<1 or a.max_points_per_case>12:raise SystemExit('1<=max-points-per-case<=12 required')
    doc=json.loads(Path(a.audit).read_text(encoding='utf-8'));ret=plan(doc,a.max_points_per_case)
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(ret,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('V144_REFINEMENT_PRIORITIES_ONLY_NOT_F2C_PROFILE_FINISHED')
if __name__=='__main__':main()
