"""Task-completion guard, NOT an independent electromagnetic science checker.
A legitimate PARTIAL archive is allowed to exist, but this command exits nonzero
until the full declared execution/evidence requirements are met. Scientific
metrics must still be recomputed by the project validator from archived arrays.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path

REQUIRED=('truth_and_identity','physical_source_and_render','error_separation','profiles_and_calibration','frozen_M_evaluation','camera_and_motion','experiment_interface','archive')

def check(root,state):
    root=Path(root).resolve();issues=[]
    if state.get('task_id')!='V132_QUALIFIED_PROFILES_AND_EXPERIMENT_READY_PARTICLE_SIZING':issues.append('TASK_ID')
    if state.get('EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED') is not False:issues.append('UNSUPPORTED_EXPERIMENTAL_CLAIM')
    stages=state.get('stages',{})
    for name in REQUIRED:
        s=stages.get(name)
        if not isinstance(s,dict):issues.append(name+':MISSING_STAGE');continue
        if s.get('execution')!='COMPLETED':issues.append(name+':EXECUTION_INCOMPLETE')
        # A completed experiment may have failed its performance target. Do not
        # conflate execution completeness with passing a scientific metric.
        if s.get('evidence')!='COMPLETE':issues.append(name+':EVIDENCE_INCOMPLETE')
        if s.get('validation') not in ('PASS','FAIL','PARTIAL','NOT_EVALUATED'):issues.append(name+':BAD_VALIDATION_ENUM')
        outputs=s.get('outputs',[])
        if not outputs:issues.append(name+':NO_OUTPUTS')
        for o in outputs:
            p=(root/o.get('path','')).resolve()
            if not p.is_relative_to(root) or not p.is_file():issues.append(name+':MISSING_OR_UNSAFE_FILE');continue
            h=hashlib.sha256(p.read_bytes()).hexdigest()
            if not o.get('sha256') or h!=o['sha256']:issues.append(name+':BAD_SHA256')
    return dict(task_execution_and_evidence_complete=not issues,issues=issues,
                scientific_validation_independently_certified=False,
                note='Execution/evidence guard only; completed scientific failures remain failures, never converted to PASS.')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--state',required=True);a=ap.parse_args()
    state=json.loads(Path(a.state).read_text(encoding='utf-8'));r=check(a.out,state);print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if not r['issues'] else 2
if __name__=='__main__':raise SystemExit(main())
