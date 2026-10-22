"""Handoff-file integrity only. Not a physics or particle-sizing validator."""
from pathlib import Path
import csv,hashlib,json,sys

def main():
    root=Path(__file__).resolve().parents[1];mf=root/'HANDOFF_SHA256.csv'
    if not mf.exists():print('FAIL: missing HANDOFF_SHA256.csv');return 2
    rows=list(csv.DictReader(mf.open(encoding='utf-8',newline='')));errors=[];seen=set()
    for r in rows:
        rel=r['path'];p=(root/rel).resolve()
        if rel in seen:errors.append('duplicate '+rel)
        seen.add(rel)
        if root not in p.parents:errors.append('unsafe '+rel);continue
        if not p.is_file():errors.append('missing '+rel);continue
        b=p.read_bytes()
        if len(b)!=int(r['bytes']) or hashlib.sha256(b).hexdigest()!=r['sha256']:errors.append('content mismatch '+rel)
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='HANDOFF_SHA256.csv'}
    if actual!=seen:errors.append('manifest membership mismatch '+str(sorted(actual.symmetric_difference(seen))))
    for rel in ['01_V131审查与V132完整执行合同.md','config/v132_science_config.json','tools/v132_continue_existing.py','tools/field_forward_reference.py','evidence/recomputed.json']:
        if rel not in seen:errors.append('required missing '+rel)
    try:
        c=json.loads((root/'config/v132_science_config.json').read_text(encoding='utf-8'))
        if c['task_id']!='V132_QUALIFIED_PROFILES_AND_EXPERIMENT_READY_PARTICLE_SIZING':errors.append('wrong task')
    except Exception as e:errors.append('invalid config '+str(e))
    print(json.dumps(dict(scope='handoff bytes only; no scientific acceptance',files=len(rows),integrity_passed=not errors,errors=errors),ensure_ascii=False,indent=2))
    return 2 if errors else 0
if __name__=='__main__':raise SystemExit(main())
