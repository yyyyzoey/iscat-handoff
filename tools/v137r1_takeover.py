"""R1 takeover: verify every R0 checkpoint row by actual forward replay, then
import into the R1 checkpoint namespace with the SAME cumulative budget.
Identity must match (model/library/observation/code); any mismatch blocks import.
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys
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
    ap.add_argument('--repo',required=True);ap.add_argument('--r1-out',required=True)
    ap.add_argument('--r0-profiles',required=True)
    a=ap.parse_args();repo=Path(a.repo).resolve();r1=Path(a.r1_out).resolve()
    cfg=json.loads((repo/'config/v137_science_config.json').read_text(encoding='utf-8'))
    m=cfg['inherited_model']
    from load_field_library import load_library
    from v133_recover_M import optical
    from observation_adapter import array_sha
    from model_lock import verify_code_lock
    passd=json.loads((repo/m['model_passport']).read_text(encoding='utf-8'))
    code=verify_code_lock(passd['code_sha256'],tools_dir=repo/'tools')
    if sha(repo/m['library'])!=m['library_sha256']:raise SystemExit('library SHA mismatch')
    v133=json.loads((repo/'config/v133_science_config.json').read_text(encoding='utf-8'))
    model,_=load_library(repo/m['library'],kind='F2',optical=optical(v133))
    if model.model_id!=m['model_id']:raise SystemExit('model id mismatch')
    bindings={x['case']:x for x in json.loads((repo/m['prior_observation_binding']).read_text(encoding='utf-8'))}
    calls=0
    report=dict(schema='iscat137r1.takeover.1',cases={},verified_rows=0,rejected_rows=0,verification_calls=0)
    (r1/'checkpoint').mkdir(parents=True,exist_ok=True)
    with h5py.File(repo/m['prior_observations'],'r') as hf:
        for i in range(1,7):
            c=f'M{i:02d}'
            src=Path(a.r0_profiles)/'checkpoint'/f'{c}.json'
            old=json.loads(src.read_text(encoding='utf-8'))
            Y=np.asarray(hf[c]['score_C'][()],float)
            if array_sha(Y)!=bindings[c]['score_array_sha256']:raise SystemExit(c+' observation changed')
            rows=[];kept=0;rejected=0
            for r in old['rows']:
                ok=False;theta=r.get('theta');loss=r.get('loss_L2')
                if theta is not None and loss is not None:
                    P=model.forward(tuple(float(v) for v in theta)).score_C;calls+=1
                    ok=bool(np.isfinite(P).all() and abs(float(np.linalg.norm(P-Y))-float(loss))<=max(1e-12,1e-7*abs(float(loss))))
                    # theta[0] must equal row D (point identity)
                    ok=ok and abs(float(theta[0])-float(r['D']))<=1e-8
                if ok:
                    r=dict(r);r['imported_from']='V137_R0_checkpoint_verified_by_forward_replay'
                    rows.append(r);kept+=1
                else:
                    rows.append(dict(D=r['D'],loss_L2=None,theta=None,
                        point_search_complete=False,
                        import_reject='R0_ROW_FAILED_FORWARD_REPLAY_OR_IDENTITY'));rejected+=1
            new=dict(case=c,run_id='R1_TAKEOVER_PENDING_BINDING',model_id=model.model_id,
                observation_sha256=bindings[c]['score_array_sha256'],
                exact_joint_D=old['exact_joint_D'],exact_joint_loss_L2=old['exact_joint_loss_L2'],
                rows=rows,calls_prior_invocations=int(old['calls_prior_invocations']),
                prior_run_id=old['run_id'])
            (r1/'checkpoint'/f'{c}.json').write_text(json.dumps(new,indent=2,ensure_ascii=False,allow_nan=False)+chr(10),encoding='utf-8')
            report['cases'][c]=dict(kept=kept,rejected=rejected,prior_calls=int(old['calls_prior_invocations']))
            report['verified_rows']+=kept;report['rejected_rows']+=rejected
    report['verification_calls']=calls
    (r1/'preflight').mkdir(parents=True,exist_ok=True)
    (r1/'preflight'/'takeover_report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+chr(10),encoding='utf-8')
    print('TAKEOVER verified=',report['verified_rows'],'rejected=',report['rejected_rows'],'verify_calls=',calls)
if __name__=='__main__':main()
