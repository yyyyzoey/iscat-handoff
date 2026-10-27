"""Standard-library-only launcher. Complete immutable payload; no optical code."""
from pathlib import Path,PurePosixPath
import argparse,csv,hashlib,importlib.util,io,json,os,subprocess,sys,tempfile,traceback,zipfile
PAYLOAD_SHA256='__PAYLOAD_SHA256__'

def validate(raw,expected):
    if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('EMBEDDED_PAYLOAD_SHA256_MISMATCH')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or z.testzip() is not None:raise ValueError('DUPLICATE_OR_BAD_CRC')
        if sum(i.file_size for i in z.infolist())>50_000_000:raise ValueError('UNEXPECTED_PACKAGE_SIZE')
        for n in names:
            p=PurePosixPath(n)
            if not p.parts or p.is_absolute() or '..' in p.parts or '\\' in n or any(':' in x for x in p.parts):raise ValueError('UNSAFE_PACKAGE_PATH')
            if (z.getinfo(n).external_attr>>16)&0o170000==0o120000:raise ValueError('SYMLINK_PACKAGE_ENTRY')
        rows=list(csv.DictReader(z.read('manifest_sha256.csv').decode('utf-8').splitlines()))
        if len(rows)!=len({r['path'] for r in rows}):raise ValueError('DUPLICATE_MANIFEST')
        if set(names)!={'manifest_sha256.csv'}|{r['path'] for r in rows}:raise ValueError('PACKAGE_MEMBER_SET')
        for r in rows:
            b=z.read(r['path'])
            if len(b)!=int(r['bytes']) or hashlib.sha256(b).hexdigest()!=r['sha256']:raise ValueError('PACKAGE_FILE_HASH:'+r['path'])
    return dict(payload_sha256=expected,members=len(names),manifest_rows=len(rows),bytes=len(raw))

def main():
    ap=argparse.ArgumentParser(description='V164: complete installation, tests and bounded fixed-D design diagnostics')
    ap.add_argument('--inspect-only',action='store_true')
    ap.add_argument('--source-repo',type=Path);ap.add_argument('--worktree',type=Path)
    a=ap.parse_args()
    with zipfile.ZipFile(Path(sys.argv[0]).resolve()) as outer:raw=outer.read('payload.zip')
    verified=validate(raw,PAYLOAD_SHA256)
    if a.inspect_only:
        print(json.dumps(dict(**verified,real_model_calls=0,scope='PACKAGE_BYTES_ONLY'),indent=2));return 0
    if a.source_repo is None or a.worktree is None:ap.error('--source-repo and --worktree are required')
    missing=[m for m in ('numpy','scipy','h5py','pytest') if importlib.util.find_spec(m) is None]
    if missing:raise RuntimeError('MISSING_LOCAL_DEPENDENCIES:'+','.join(missing))
    src=a.source_repo.resolve();dst=a.worktree.resolve()
    if dst.exists() or src==dst or src in dst.parents or dst in src.parents:raise ValueError('NEW_SEPARATE_WORKTREE_REQUIRED')
    temp=Path(tempfile.mkdtemp(prefix='iscat_v164_verified_'));bundle=temp/'bundle';bundle.mkdir()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for name in z.namelist():
            p=bundle.joinpath(*PurePosixPath(name).parts);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
    cmds=[('prepare',[sys.executable,str(bundle/'prepare_v164.py'),'--source-repo',str(src),'--worktree',str(dst)]),
          ('run_all',[sys.executable,str(dst/'tools/v164_bundle/run_all.py'),'--repo',str(dst)])]
    records=[]
    for label,cmd in cmds:
        p=subprocess.run(cmd,capture_output=True)
        (temp/(label+'.stdout')).write_bytes(p.stdout);(temp/(label+'.stderr')).write_bytes(p.stderr)
        records.append(dict(stage=label,command=cmd,returncode=p.returncode))
        print(p.stdout.decode('utf-8',errors='replace'));print(p.stderr.decode('utf-8',errors='replace'),file=sys.stderr)
        record=dict(package=verified,stages=records,scope='EXECUTION_COMMANDS_NOT_SCIENTIFIC_CERTIFICATION')
        (temp/'launcher_receipt.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
        if dst.exists():
            dest=dst/'results/v164/launcher';dest.mkdir(parents=True,exist_ok=True)
            for source in temp.iterdir():
                if source.is_file():(dest/source.name).write_bytes(source.read_bytes())
        if p.returncode:
            print('STOPPED_WITH_EVIDENCE:',temp,file=sys.stderr);return p.returncode
    # Include launcher receipts in the final archive; no model computation here.
    q=subprocess.run([sys.executable,str(dst/'tools/v164_bundle/code/v164_report_pack.py'),'--out',str(dst/'results/v164')])
    print('READ_STATUS_AND_VERIFICATION; no experimental absolute sizing is certified.')
    return q.returncode

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        traceback.print_exc();raise SystemExit(2)
