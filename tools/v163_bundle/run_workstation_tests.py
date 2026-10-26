"""Run the complete bundled suite, bind source/test identities, retain pytest outcomes."""
from pathlib import Path
import argparse, datetime, json, os, subprocess, sys, uuid
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'code'))
from v163_deployment import bundle_hashes, digest, SCOPE

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    # Preserve earlier receipts rather than overwriting evidence.
    if any((out/n).exists() for n in ('test_receipt.json','test_output.txt','pytest_outcomes.json')):
        hist=out/'history'/uuid.uuid4().hex;hist.mkdir(parents=True)
        for n in ('test_receipt.json','test_output.txt','pytest_outcomes.json'):
            if (out/n).exists():(hist/n).write_bytes((out/n).read_bytes())
    before=bundle_hashes(ROOT)
    env=os.environ.copy();env['PYTHONPATH']=str(ROOT/'code')
    ignored_addopts=env.pop('PYTEST_ADDOPTS',None)
    env['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1';env['PYTHONDONTWRITEBYTECODE']='1'
    env['V163_PYTEST_OUTCOMES']=str(out/'pytest_outcomes.json')
    tail=['-m','pytest','-q','-p','v163_receipt_plugin','tests']
    p=subprocess.run([sys.executable,*tail],cwd=ROOT,env=env,capture_output=True)
    raw=p.stdout+b'\n'+p.stderr;(out/'test_output.txt').write_bytes(raw)
    after=bundle_hashes(ROOT)
    result=dict(scope=SCOPE,returncode=p.returncode,python=sys.version,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                command=[sys.executable,*tail],command_tail=tail,cwd=str(ROOT),bundle_root=str(ROOT),bundle_sha256=after,
                before_sha256=before,files_unchanged=before==after,output_sha256=digest(raw),
                outcomes_sha256=digest((out/'pytest_outcomes.json').read_bytes()) if (out/'pytest_outcomes.json').exists() else None,
                real_F2c_calls=0,pytest_addopts_ignored=ignored_addopts,pytest_version=__import__('pytest').__version__)
    (out/'test_receipt.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(raw.decode('utf-8',errors='replace'))
    if p.returncode or before!=after:return 2
    from v163_deployment import verify_test_receipt
    verify_test_receipt(ROOT,out)
    print('COMPLETE_BUNDLE_TESTS_VERIFIED_NOT_REAL_F2C_VALIDATION');return 0
if __name__=='__main__':raise SystemExit(main())
