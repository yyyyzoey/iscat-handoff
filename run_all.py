"""Execute fixed stage order. Always archive available failure evidence. No auto-retry."""
from pathlib import Path
import argparse,json,subprocess,sys,uuid
ROOT=Path(__file__).resolve().parent

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);a=ap.parse_args();repo=a.repo.resolve()
    if ROOT!=repo/'tools/v159_bundle':raise ValueError('RUN_ONLY_FROM_ISOLATED_INSTALLED_BUNDLE')
    out=repo/'results/v159';logs=out/'logs';logs.mkdir(parents=True,exist_ok=True)
    if (out/'logs/v159_budget.sqlite').exists():
        print('EXISTING_LEDGER: use read-only verify; never automatically execute again',file=sys.stderr);return 2
    run_id=uuid.uuid4().hex
    commands=[('tests',[sys.executable,str(ROOT/'run_workstation_tests.py'),'--out',str(out/'workstation_tests')])]
    for mode in ('preflight','execute','verify'):
        commands.append((mode,[sys.executable,str(ROOT/'code/v159_run.py'),'--repo',str(repo),'--config',str(ROOT/'config/v159_plan.json'),'--out',str(out),'--mode',mode]))
    receipts=[];code=0
    for stage,cmd in commands:
        p=subprocess.run(cmd,cwd=repo,capture_output=True)
        name=f'{run_id}_{stage}';(logs/(name+'.stdout')).write_bytes(p.stdout);(logs/(name+'.stderr')).write_bytes(p.stderr)
        receipts.append(dict(stage=stage,command=cmd,returncode=p.returncode,stdout=name+'.stdout',stderr=name+'.stderr'))
        print(stage,'exit',p.returncode,flush=True)
        if p.returncode:
            code=p.returncode;break
    (logs/(run_id+'_stage_commands.json')).write_text(json.dumps(receipts,indent=2)+'\n',encoding='utf-8')
    p=subprocess.run([sys.executable,str(ROOT/'code/v159_report_pack.py'),'--out',str(out)],cwd=repo,capture_output=True)
    print(p.stdout.decode('utf-8',errors='replace'));print(p.stderr.decode('utf-8',errors='replace'),file=sys.stderr)
    print('pack exit',p.returncode,'; FINISHED is not experimental diameter validation')
    return code or p.returncode
if __name__=='__main__':raise SystemExit(main())
