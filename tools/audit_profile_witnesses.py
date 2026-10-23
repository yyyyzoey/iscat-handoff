#!/usr/bin/env python3
"""Read-only V143 fixed-D profile witness auditor.

Science logic: every VALID evaluated theta at fixed D gives an attainable
residual, even if other optimizer starts were truncated. That is sufficient
to exhibit a competing diameter. Conversely, no finite local search certifies
that unseen D regions have high residual, so this module NEVER proves unique D.
The empirical epsilon is conditional and is NOT a statistical 95% confidence.
"""
from __future__ import annotations
import argparse,hashlib,json,math,sys
from pathlib import Path

def finite(x):return isinstance(x,(float,int)) and math.isfinite(x)
def file_sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for buf in iter(lambda:f.read(1<<20),b''):h.update(buf)
    return h.hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

def extract_witness(doc):
    if doc.get('status') not in ('COMPLETED_NUMERICAL_ATTEMPT_NOT_GLOBAL_PROOF','INHERITED_V142_VALID_POINT'):
        return None
    res=doc.get('result') or {}
    best=res.get('best')
    if not best or not finite(best.get('loss_L2')):return None
    th=best.get('theta')
    if not isinstance(th,list) or len(th)!=4 or not all(finite(z) for z in th):return None
    if not finite(res.get('D')) or abs(float(res['D'])-float(th[0]))>1e-6:return None
    return {'D':float(res['D']),'loss_L2':float(best['loss_L2']),
        'theta':[float(z) for z in th], 'all_starts_complete':res.get('point_search_complete') is True,
        'provenance_status':doc.get('status')}

def case_audit(root,case,eps,candidate=None):
    root=Path(root);observations=[];identities=set();bad=[];by_D={};raw_files=0
    for phase in ('coarse','refine'):
        directory=root/phase/case
        if not directory.is_dir():continue
        identity_file=directory/'input_identity.json'
        if not identity_file.is_file():raise ValueError(f'{case}: MISSING_PROFILE_SOURCE_BINDING_{phase}')
        identity=load(identity_file)
        required=('model_id','observation_sha','estimator_source_sha256')
        if any(not isinstance(identity.get(x),str) or not identity.get(x) for x in required):
            raise ValueError(f'{case}: PROFILE_SOURCE_BINDING_INCOMPLETE_{phase}')
        identities.add(tuple(identity[x] for x in required))
        for file in directory.glob('*.json'):
            if file.name in ('input_identity.json','summary.json'):continue
            doc=load(file);raw_files+=1
            w=extract_witness(doc)
            if w is None:
                bad.append(dict(checkpoint=file.relative_to(root).as_posix(),reason='NO_FINITE_VALID_WITNESS'));continue
            w['checkpoint']=file.relative_to(root).as_posix();w['phase']=phase
            observations.append(w)
            D=w['D'];old=by_D.get(D)
            if old is None or old['loss_L2']>w['loss_L2']:by_D[D]=w
    if len(identities)!=1:raise ValueError(f'{case}: MODEL_OBSERVATION_OR_CODE_IDENTITY_MISMATCH')
    witnesses=sorted(by_D.values(),key=lambda r:r['D'])
    eps_safe=[w for w in witnesses if w['loss_L2']<=eps]
    eps_safe.sort(key=lambda r:r['D'])
    incumbent=min(witnesses,key=lambda r:r['loss_L2']) if witnesses else None
    interval_goal=max(5.,.1*candidate) if finite(candidate) else 5.
    far=[]
    for i,one in enumerate(eps_safe):
        for two in eps_safe[i+1:]:
            if two['D']-one['D']>2*interval_goal:
                far.append((two['D']-one['D'],one,two))
    max_pair=max(far,key=lambda z:z[0]) if far else None
    nearest=None
    if finite(candidate) and witnesses:nearest=min(witnesses,key=lambda z:abs(z['D']-candidate))
    return dict(case=case,source_binding={'model_id':next(iter(identities))[0],
          'observation_sha':next(iter(identities))[1],
          'estimator_sha256':next(iter(identities))[2]},
        n_checkpoints=raw_files,n_unique_D=len(witnesses),n_missing_witness=len(bad),
        n_all_starts_completed=sum(w['all_starts_complete'] for w in witnesses),
        n_incomplete_starts_with_valid_witness=sum(not w['all_starts_complete'] for w in witnesses),
        observed_minimum_witness=incumbent,
        nearest_existing_witness_to_candidate=nearest,
        epsilon_L2_unqualified=eps,n_witnesses_below_epsilon=len(eps_safe),
        epsilon_witness_D=[w['D'] for w in eps_safe],
        known_nonunique_under_assumed_epsilon=bool(max_pair),
        separated_compatible_witness_pair=({'D1':max_pair[1]['D'],'R1':max_pair[1]['loss_L2'],
            'D2':max_pair[2]['D'],'R2':max_pair[2]['loss_L2'],
            'separation_nm':max_pair[0]} if max_pair else None),
        supports_claim_unique_D=False,
        candidate_D=candidate,
        scientific_disposition=('TWO_DISTINCT_FINITE_WITNESSES__NOT_UNIQUE_UNDER_ASSUMED_EPS' if max_pair else
                'NO_UNIQUENESS_PROOF_UNSAMPLED_AND/OR_UNCONVERGED_D_REMAIN'),
        reportable_D=None,
        examples_missing_witness=bad[:8],
        all_D_and_residuals=[dict(D=x['D'],R=x['loss_L2'],complete=x['all_starts_complete'],source=x['provenance_status']) for x in witnesses],
        scope='FINITE_WITNESS_COMPATIBILITY_UNDER_UNQUALIFIED_DEV_EPS_NOT_95PCT_CI')

def run(repo,cfg):
    repo=Path(repo).resolve();p=repo/cfg['inputs']['v143_profile_root'];eps=cfg['profile']['dev_epsilon_L2_unqualified']
    if not p.is_dir():raise FileNotFoundError(p)
    import csv
    nfit={}
    with (repo/cfg['inputs']['N_estimator_candidates']).open(encoding='utf-8',newline='') as f:
        for r in csv.DictReader(f):nfit[r['anon_case']]=float(r['candidate_D'])
    for m in [f'M{i:02d}' for i in range(1,7)]:
        t=load(repo/cfg['inputs']['M_fits']/(m+'.json'))
        nfit[m]=float(t['candidate_D'])
    cases={c:case_audit(p,c,eps,nfit.get(c)) for c in cfg['profile_cases']}
    # Binding integrity: published checkpoint identifiers must match the actual
    # model source bytes AND the actual current observation arrays. No guessing.
    import h5py,numpy as np
    model_sha=hashlib.sha256((repo/'tools/v142_model.py').read_bytes()).hexdigest()
    for c,r in cases.items():
        binding=r['source_binding']
        if binding['model_id']!=cfg['frozen_parent_F2c_model_id'] or binding['estimator_sha256']!=model_sha:
            raise ValueError(c+': MODEL_SOURCE_BYTES_OR_ID_MISMATCH')
        obsname='N_anonymous_observation' if c.startswith('ANON') else 'M_observation'
        obs_path=repo/cfg['inputs'][obsname]
        if file_sha256(obs_path)!=cfg['known_sha256'][obsname]:
            raise ValueError(c+': OBSERVATION_FILE_SHA_CHANGED')
        with h5py.File(obs_path,'r') as f:
            Y=np.asarray(f[c]['score_C'][()],float) if c.startswith('ANON') else np.asarray(f[c]['at_offset/C'][()],float)[2:15,2:15]
        if Y.shape!=(13,13) or not np.isfinite(Y).all():raise ValueError(c+': OBSERVATION_SHAPE_OR_FINITE_INVALID')
        x=np.ascontiguousarray(Y);actual_sha=hashlib.sha256((str(x.shape)+'|'+str(x.dtype)+'|').encode()+x.tobytes()).hexdigest()
        if actual_sha!=binding['observation_sha']:raise ValueError(c+': OBSERVATION_ARRAY_ID_MISMATCH')
    published=load(repo/cfg['inputs']['v143_profile_inventory'])['cases']
    for c,z in cases.items():
        if c in published:
            components=published[c].get('observed_compatible_components_ONLY',[])
            cand=z['candidate_D']
            if finite(cand) and z['nearest_existing_witness_to_candidate']:
                x=z['nearest_existing_witness_to_candidate']
                z['published_components_miss_near_candidate']=bool(x['loss_L2']<=eps and not any(float(a)-1e-6<=x['D']<=float(b)+1e-6 for a,b in components))
                z['published_components_nearest_missing_D']=x['D'] if z['published_components_miss_near_candidate'] else None
        else:z['published_components_miss_near_candidate']='NO_PUBLISHED_CASE'
    return dict(schema='iscat144.profile_witness_audit.1',epsilon_L2_unqualified=eps,cases=cases,
      cases_with_proven_competing_witness_under_dev_eps=[c for c,a in cases.items() if a['known_nonunique_under_assumed_epsilon']],
      published_compat_missed_known_candidate=[c for c,a in cases.items() if a.get('published_components_miss_near_candidate') is True],
      rule='ALL_FINITE_WITNESSES_CAN_REJECT_UNIQUENESS; NO_FINITE_SAMPLE_CAN_PROVE_UNIQUENESS',
      cannot_claim_statistical_interval=True,experimental_absolute_diameter_validated=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--config',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    try:ret=run(a.repo,load(a.config));dest=Path(a.out);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(ret,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    except Exception as e:
        dest=Path(a.out);dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps({'status':'BLOCKED_NOT_SCIENCE_PASS','error':repr(e)},indent=2)+'\n',encoding='utf-8')
        print('PROFILE_AUDIT_BLOCKED',repr(e),file=sys.stderr);return 2
    print('V144_PROFILE_WITNESSES_ANALYZED_NO_UNIQUENESS_AUTO_PASS',ret['cases_with_proven_competing_witness_under_dev_eps']);return 0
if __name__=='__main__':raise SystemExit(main())
