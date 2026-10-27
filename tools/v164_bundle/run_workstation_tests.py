from pathlib import Path
import argparse,datetime,hashlib,json,os,subprocess,sys,uuid
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'code'))
from v164_receipts import hashes,verify_receipt

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'test_receipt.json').exists():raise ValueError('PRESERVE_OLD_TEST_RECEIPT_NO_OVERWRITE')
    before=hashes(ROOT);env=os.environ.copy();external=env.pop('PYTEST_ADDOPTS',None)
    env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    env.update(PYTHONPATH=str(ROOT/'code'),PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1',V164_PYTEST_OUTCOMES=str(out/'pytest_outcomes.json'))
    cmd=[sys.executable,'-m','pytest','-q','-p','v164_receipt_plugin','tests']
    p=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True)
    raw=p.stdout+b'\n'+p.stderr;(out/'test_output.txt').write_bytes(raw)
    after=hashes(ROOT)
    r=dict(returncode=p.returncode,scope='COMPONENT_AND_SYNTHETIC_MODEL_TESTS_NOT_PHYSICAL_VALIDATION',command=cmd,cwd=str(ROOT),python=sys.version,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),external_pytest_addopts_ignored=external,hashes=after,before=before,real_F2c_calls=0,output_sha256=hashlib.sha256(raw).hexdigest(),outcomes_sha256=hashlib.sha256((out/'pytest_outcomes.json').read_bytes()).hexdigest() if (out/'pytest_outcomes.json').exists() else None)
    (out/'test_receipt.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    print(raw.decode(errors='replace'))
    if p.returncode or before!=after:return 2
    verify_receipt(ROOT,out);return 0
if __name__=='__main__':raise SystemExit(main())
