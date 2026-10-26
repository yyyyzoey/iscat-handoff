"""Run real local tests; never substitutes for real-F2c/source integration."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,subprocess,sys

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    root=Path(__file__).resolve().parent;a.out.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy();env['PYTHONPATH']=str(root/'code')+os.pathsep+env.get('PYTHONPATH','')
    r=subprocess.run([sys.executable,'-m','pytest','-q',str(root/'tests')],env=env,capture_output=True,text=True)
    log=r.stdout+'\n'+r.stderr;(a.out/'test_output.txt').write_text(log,encoding='utf-8')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    d=dict(scope='COMPONENT_AND_SYNTHETIC_MODEL_TESTS_NOT_PHYSICAL_VALIDATION',
           returncode=r.returncode,python=sys.version,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
           command=[sys.executable,'-m','pytest','-q',str(root/'tests')],
           code_sha256={p.name:sha(p) for p in sorted((root/'code').glob('*.py'))},
           test_sha256={p.name:sha(p) for p in sorted((root/'tests').glob('test_*.py'))},
           output_sha256=sha(a.out/'test_output.txt'),real_F2c_calls=0)
    (a.out/'test_receipt.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
    print(log);return r.returncode
if __name__=='__main__':raise SystemExit(main())
