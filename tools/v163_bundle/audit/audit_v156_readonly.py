"""Read-only V156 archive, SQLite, and pixel-record audit. No F2/F2c import.

Run against a workstation checkout. This establishes saved-file consistency,
not original optical-source provenance. Both V156 ledgers are kept separate.
"""
from __future__ import annotations
import argparse, csv, hashlib, io, json, sqlite3, sys, zipfile
from pathlib import Path, PurePosixPath
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reference'))
from v155_pixel_diagnostics import validate_pixel_record
from v156_candidate_guard import read_v152_pool

HEAD='797d8e5232b93fdfcfe796f429ff5fa749118c00'
V152='6d2db46d52509bd6987726dea211781cfa1b4127'
V152_BLOB='21e9d1b96f61e2fd9af57f0a038941d07f7d207b'
EXPECTED={(b,f'ANON_{a:02d}') for b in (1000,10000,100000) for a in range(1,5)}


def digest(b):return hashlib.sha256(b).hexdigest()
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))


def ledger(path: Path) -> dict:
    raw=path.read_bytes()
    out={'path':path.name,'bytes':len(raw),'sha256':digest(raw),'git_blob':blob(raw)}
    if any(Path(str(path)+s).exists() for s in ('-wal','-journal')):
        return dict(out,status='NEEDS_TRANSACTION_SNAPSHOT_DO_NOT_IGNORE_WAL')
    con=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
    try:
        con.execute('PRAGMA query_only=ON')
        out['integrity_check']=con.execute('PRAGMA integrity_check').fetchone()[0]
        tables={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        out['tables']=sorted(tables)
        if {'tasks','attempts','metadata'}<=tables:
            out['metadata']=[dict(zip(('id','value'),r)) for r in con.execute('SELECT id,value FROM metadata')]
            out['tasks']=[dict(zip(('id','signature','phase','cap','used','owner','state','result_path','result_sha'),r)) for r in con.execute('SELECT id,signature,phase,cap,used,owner,state,result_path,result_sha FROM tasks')]
            out['attempt_states']=dict(con.execute('SELECT state,count(*) FROM attempts GROUP BY state'))
            out['attempts']=con.execute('SELECT count(*) FROM attempts').fetchone()[0]
            out['recorded_used']=sum(r['used'] for r in out['tasks'])
            out['reserved']=sum(r['cap'] for r in out['tasks'])
            out['task_over_cap']=[r['id'] for r in out['tasks'] if r['used']>r['cap']]
            counted=dict(con.execute('SELECT task,count(*) FROM attempts GROUP BY task'))
            out['task_attempt_count_matches']=all(counted.get(r['id'],0)==r['used'] for r in out['tasks'])
        else:out['status']='UNEXPECTED_SCHEMA_REQUIRES_INSPECTION'
    finally:con.close()
    if digest(path.read_bytes())!=out['sha256']:raise RuntimeError('READONLY_AUDIT_CHANGED_DB')
    return out


def archive(path: Path) -> dict:
    raw=path.read_bytes();r={'bytes':len(raw),'sha256':digest(raw),'git_blob':blob(raw)}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=[i.filename for i in z.infolist() if not i.is_dir()]
        r['members']=len(names);r['duplicates']=len(names)!=len(set(names))
        if any(PurePosixPath(n).is_absolute() or '..' in PurePosixPath(n).parts or '\\' in n for n in names):
            raise ValueError('UNSAFE_ZIP_MEMBER')
        r['crc_bad_member']=z.testzip()
        ms=[n for n in names if PurePosixPath(n).name=='manifest_sha256.csv']
        if len(ms)!=1:raise ValueError('ONE_MANIFEST_REQUIRED')
        m=ms[0];prefix=str(PurePosixPath(m).parent)
        prefix='' if prefix=='.' else prefix+'/'
        text=z.read(m).decode('utf-8-sig')
        rows=list(csv.DictReader(io.StringIO(text)));bad=[];seen=set()
        for row in rows:
            rel=row['path'];p=PurePosixPath(rel)
            if p.is_absolute() or '..' in p.parts or '\\' in rel:raise ValueError('UNSAFE_MANIFEST_PATH')
            name=prefix+rel;seen.add(name)
            if name not in names:bad.append({'path':name,'reason':'MISSING'});continue
            b=z.read(name)
            if len(b)!=int(row['bytes']) or digest(b)!=row['sha256']:
                bad.append({'path':name,'reason':'SIZE_OR_HASH'})
        r.update(manifest_rows=len(rows),manifest_failures=bad,
                 unlisted_files=sorted(set(names)-seen-{m}))
    return r


def audit(repo: Path) -> dict:
    root=repo/'results'/'v156';result={'commit_requested':HEAD,
       'scope':'READONLY_SAVED_ARTIFACTS_NOT_SOURCE_LOCK_OR_NEW_OPTICAL_REPLAY',
       'scientific_acceptance':False,'failures':[],'groups':[]}
    raw=(repo/'results/v152/all_results.json').read_bytes()
    if blob(raw)!=V152_BLOB:raise ValueError('V152_SOURCE_BLOB_MISMATCH')
    pool=read_v152_pool(json.loads(raw.decode('utf-8-sig')),V152)
    scored=load(root/'rescored/all_72_thetas.json')
    if len(scored)!=72:raise ValueError('EXPECTED_72_RESCORED_ROWS')
    seen=set()
    for b,a in sorted(EXPECTED):
        p=root/'joint'/f'{b}_{a}'/'result.json';doc=load(p);d=doc['diagnostic']
        check=validate_pixel_record(d)
        group=[r for r in scored if r['B']==b and r['anon']==a]
        if len(group)!=6:raise ValueError('GROUP_RESCORING_COUNT')
        # Require a multiset equality, not just membership, against all 6 originals.
        tup=lambda r:tuple(float(x) for x in r['theta'])
        if sorted(map(tup,group))!=sorted(map(tup,pool[b,a])):raise ValueError('CLIP_OR_SOURCE_THETA_CHANGE')
        best=min(group,key=lambda r:r['Q_joint'])
        if tup(best)!=tup(d):raise ValueError('LOCAL_ANCHOR_NOT_MINIMUM_RECORD')
        if abs(best['Q_joint']-d['score']['Q_joint'])>max(1e-8,1e-10*abs(best['Q_joint'])):raise ValueError('ANCHOR_Q_MISMATCH')
        for pred in d['predictions']:
            disk=load(p.parent/'predictions'/f'{pred["index"]:03d}.json')
            arr=np.asarray(pred['C'],dtype=np.float64)
            if not np.array_equal(np.asarray(disk['C']),arr) or disk['theta']!=pred['theta']:
                raise ValueError('DISK_PREDICTION_MISMATCH')
            if digest(np.ascontiguousarray(arr).tobytes())!=disk['C_sha256']:
                raise ValueError('DISK_ARRAY_HASH_MISMATCH')
        # Independently recompute step and directional stability from saved arrays.
        v=np.asarray(d['frame_V']);vb=1/(1/v).sum(axis=0);sc=np.sqrt(vb).ravel()
        coarse=np.asarray(d['raw_J_coarse'])/sc[:,None];fine=np.asarray(d['raw_J_fine'])/sc[:,None]
        norms=np.maximum(np.linalg.norm(coarse,axis=0),np.linalg.norm(fine,axis=0))
        diff=np.divide(np.linalg.norm(fine-coarse,axis=0),norms,out=np.zeros(4),where=norms>0)
        c0=np.asarray(d['predictions'][d['base_index']]['C']);directions=[]
        for item in d['directional_checks']:
            pred=d['predictions'][item['index']]
            if not np.array_equal(np.asarray(pred['theta']),np.asarray(d['theta'])+np.asarray(item['delta_nm'])):raise ValueError('DIRECTION_THETA_MISMATCH')
            dc=(np.asarray(pred['C'])-c0).ravel()/sc;n=np.linalg.norm(dc)
            directions.append(None if n<=1e-12 else float(np.linalg.norm(dc-fine@np.asarray(item['delta_nm']))/n))
        fractions={k:d['projections'][k][0]['remaining_D_squared_norm_fraction'] for k in ('free_hxy','height_fixed','xy_fixed')}
        result['groups'].append(dict(B=b,anon=a,theta=d['theta'],Q_joint=check['Q_joint'],
            saved_predictions=check['n_predictions'],parameter_boundary=d['parameter_boundary'],
            step_relative_errors=diff.tolist(),directional_relative_errors=directions,
            saved_status=d['status'],squared_fractions=fractions))
        seen.add((b,a))
    result['groups_complete']=seen==EXPECTED
    result['ledgers']=[ledger(p) for p in sorted((root/'logs').glob('*.sqlite'))]
    result['ledger_totals_combined']=None
    result['ledger_warning']='DO_NOT_SUM_TWO_RUNS_OR_DEDUP_WITHOUT_RUN_IDENTITIES'
    result['archive']=archive(root/'iscat_v156_return.zip')
    result['cross_background_best_files']=[str(p.relative_to(root)) for p in sorted((root/'joint').glob('ANON_*_best.json'))]
    result['excluded_from_science']=result['cross_background_best_files']
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();target=args.out.resolve();old=(args.repo/'results/v156').resolve()
    if target==old or old in target.parents:raise ValueError('NO_WRITES_TO_HISTORY')
    r=audit(args.repo.resolve());target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print('READONLY_CONSISTENCY_AUDIT_NOT_SCIENCE_ACCEPTANCE')
