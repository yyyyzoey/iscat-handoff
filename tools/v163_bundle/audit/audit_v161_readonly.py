"""Audit V161 original artifacts only. No simulation, no source modification."""
from pathlib import Path,PurePosixPath
import argparse,csv,hashlib,io,json,zipfile
EXPECTED_BLOB='13a11c536e7da5abccefb81cc8aa404b017c014d'
COMMIT='dad7b87554959355926d3523169fae7ac30a39f7'

def audit_zip(path):
    raw=Path(path).read_bytes();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    if blob!=EXPECTED_BLOB:raise ValueError('V161_ORIGINAL_ZIP_IDENTITY_MISMATCH')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=z.namelist()
        if len(set(names))!=len(names) or z.testzip() is not None:raise ValueError('V161_ZIP_CRC_OR_DUPLICATE')
        if any('..' in PurePosixPath(n).parts or n.startswith('/') or '\\' in n for n in names):raise ValueError('UNSAFE_ZIP_PATH')
        manifest=list(csv.DictReader(io.StringIO(z.read('manifest_sha256.csv').decode('utf-8-sig'))))
        if set(names)!={r['path'] for r in manifest}|{'manifest_sha256.csv'}:raise ValueError('MANIFEST_MEMBER_MISMATCH')
        for r in manifest:
            b=z.read(r['path'])
            if len(b)!=int(r['bytes']) or hashlib.sha256(b).hexdigest()!=r['sha256']:raise ValueError('MANIFEST_HASH_FAILED')
        nonfinite=[]
        def constant(v):nonfinite.append(v);return float(v)
        design=json.loads(z.read('design/all_1224_designs.json'),parse_constant=constant)
        probes=json.loads(z.read('probes/nonlinear_probes.json'))
        budget=json.loads(z.read('logs/budget_summary.json'))
    finite=[r for rows in design.values() for r in rows if r['design'].startswith(('height_','xy_'))]
    zero=sum(r['compensation']==[0,0,0] for r in finite)
    anchors=[[r['theta'][0]-r['t'],*r['theta'][1:]] for r in probes]
    return dict(scope='RAW_ARCHIVE_AND_PUBLISHED_NUMBERS_NO_NEW_MODEL_CALLS',commit=COMMIT,
      raw_zip_git_blob=blob,raw_zip_sha256=hashlib.sha256(raw).hexdigest(),zip_bytes=len(raw),members=len(names),manifest_verified=len(manifest),crc_bad_member=None,
      groups=len(design),actual_design_records=sum(map(len,design.values())),expected_design_records=1224,
      finite_design_records=len(finite),finite_zero_compensation=zero,
      all_finite_equal_free=all(all(r['total_coefficient']==rows[0]['total_coefficient'] for r in rows[3:]) for rows in design.values()),
      all_exact_height_equal_exact_xy=all(rows[1]['total_coefficient']==rows[2]['total_coefficient'] for rows in design.values()),
      nonstandard_json_constants=len(nonfinite),probe_records=len(probes),probe_particle_labels=sorted({r['anon'] for r in probes}),recovered_anchor=anchors[0],all_probe_anchors_equal=all(t==anchors[0] for t in anchors),
      published_budget=budget,real_total_calls='UNVERIFIED_LOADER_AND_OTHER_CALLS_NOT_PERSISTENTLY_RECORDED',
      sqlite_members=[p for p in names if p.endswith('.sqlite')],scientific_acceptance=False,
      disposition='QUARANTINE_V161_DESIGN_AND_PROBES_NOT_PHYSICAL_EVIDENCE')

def main():
    p=argparse.ArgumentParser();p.add_argument('--zip',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=audit_zip(a.zip);a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
if __name__=='__main__':main()
