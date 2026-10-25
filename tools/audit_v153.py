"""Read-only V153 archive audit. No physics, optimizer, network, or old DB writes."""
from __future__ import annotations
import argparse, csv, hashlib, io, json, sqlite3, tempfile, zipfile
from pathlib import Path, PurePosixPath

EXPECTED_BLOB = '2cfd131e2ddf67c1670e2dbd765e584cbefc9242'
COMMIT = 'e1df35a54a6ca9f91007f68603edf99ac60dc9bc'
# These are published V152 Q_total values, not new predictions. Used only for
# source-table consistency checks; raw-array physical replay remains separate.
BASE_Q = {
 (100000,'ANON_01'):500.0181758515398,(10000,'ANON_01'):451.2208225520118,(1000,'ANON_01'):507.0851298265988,
 (100000,'ANON_02'):527.1683634782148,(10000,'ANON_02'):451.70890360794056,(1000,'ANON_02'):580.6634392767403,
 (100000,'ANON_03'):474.78502328085557,(10000,'ANON_03'):474.70957611041985,(1000,'ANON_03'):510.291702356689,
 (100000,'ANON_04'):492.85607964668293,(10000,'ANON_04'):463.06426423750975,(1000,'ANON_04'):510.90116443640414,
}

def sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()
def audit(archive: Path) -> dict:
    raw=archive.read_bytes()
    blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    if blob != EXPECTED_BLOB: raise ValueError('V153_ARCHIVE_BLOB_MISMATCH')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=z.namelist()
        if len(names)!=len(set(names)): raise ValueError('DUPLICATE_ARCHIVE_MEMBER')
        if any(n.startswith('/') or '\\' in n or '..' in PurePosixPath(n).parts for n in names):
            raise ValueError('UNSAFE_ARCHIVE_PATH')
        if z.testzip() is not None: raise ValueError('ZIP_CRC_FAILED')
        manifest=list(csv.DictReader(io.StringIO(z.read('manifest_sha256.csv').decode('utf-8-sig'))))
        if len({r['path'] for r in manifest})!=len(manifest): raise ValueError('DUPLICATE_MANIFEST_ROW')
        if set(names)!={r['path'] for r in manifest}|{'manifest_sha256.csv'}: raise ValueError('MEMBER_SET_MISMATCH')
        for r in manifest:
            b=z.read(r['path'])
            if len(b)!=int(r['bytes']) or sha(b)!=r['sha256']: raise ValueError('MANIFEST_CONTENT_MISMATCH')
        results=json.loads(z.read('all_results.json'))
        db_bytes=z.read('logs/v153_budget.sqlite')
        joint_file=json.loads(z.read('joint/rescored_v152.json'))
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'readonly.sqlite';p.write_bytes(db_bytes)
        con=sqlite3.connect(p.as_uri()+'?mode=ro&immutable=1',uri=True)
        try:
            integrity=con.execute('PRAGMA integrity_check').fetchone()[0]
            rows=con.execute('SELECT op,phase,reserved,actual,state,payload FROM events ORDER BY op').fetchall()
        finally: con.close()
        if p.read_bytes()!=db_bytes: raise ValueError('READ_ONLY_DB_CHANGED')
    if integrity!='ok': raise ValueError('DB_INTEGRITY_FAILED')
    phase={}
    for op,ph,res,used,state,payload in rows:
        s=phase.setdefault(ph,dict(tasks=0,reserved=0,recorded_actual=0,over_cap=0))
        s['tasks']+=1;s['reserved']+=res;s['recorded_actual']+=used;s['over_cap']+=int(used>res)
    old={r['event_id']:r['v146_Q'] for r in results['replay']}
    e1=[dict(event_id=r['event_id'],reported_best_Q=r['best_Q'],
             twice_reported_Q=2*r['best_Q'],baseline_Q=old[r['event_id']],
             abs_difference_after_factor_correction=abs(2*r['best_Q']-old[r['event_id']]),
             source='ARITHMETIC_ONLY_NOT_A_NEW_F2C_REPLAY') for r in results['e1_regression']]
    joint=[]
    for r in results['joint_rescore']:
        reference=BASE_Q[(r['B'],r['anon'])]
        q=r['Q_model']; per=json.loads(r['Q_frames'])
        joint.append(dict(B=r['B'],anon=r['anon'],reported_D=r['joint_D'],
                          v153_mislabeled_Q_model=q,actual_metric_in_source='Q_joint',
                          v152_Q_total_at_original_best=reference,
                          absolute_disagreement=abs(q-reference),
                          frame_sum_difference=abs(q-sum(per)),
                          agrees_with_original_best_Q=abs(q-reference)<=max(1e-8,1e-10*abs(reference))))
    return dict(review_commit=COMMIT,archive=dict(bytes=len(raw),sha256=sha(raw),git_blob_sha1=blob,
                crc_pass=True,manifest_members_verified=len(manifest),total_members=len(names)),
                sqlite=dict(bytes=len(db_bytes),sha256=sha(db_bytes),integrity=integrity,events=len(rows),by_phase=phase),
                replay=dict(rows=len(results['replay']),ok_rows=sum(r['ok'] is True for r in results['replay']),
                            max_saved_difference=max(abs(r['replay_Q']-r['v146_Q']) for r in results['replay']),
                            scope='PUBLISHED_ROWS_AND_SOURCE_AUDIT_NOT_RAW_CAMERA_REPLAY'),
                e1_scaling=e1,joint_row_consistency=joint,
                joint_duplicate_export_matches=joint_file==results['joint_rescore'],
                recorded_f2c= sum(r[3] for r in rows),
                unledgered_joint_calls_supported_by_source_and_results=len(results['joint_rescore']),
                conditional_f2c_lower_bound=sum(r[3] for r in rows)+len(results['joint_rescore']),
                actual_history_exact_count_certified=False,
                frozen_contract_limit=32000,runner_hardcoded_limit=60000,
                actual_total_exceeds_32000_proven=False,
                no_new_physics_or_fitting_performed_by_this_audit=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();d=audit(a.archive);a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print('READ_ONLY_AUDIT_COMPLETE__NOT_SCIENCE_PASS')
