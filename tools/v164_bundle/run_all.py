from pathlib import Path
import argparse,json,subprocess,sys,uuid
ROOT=Path(__file__).resolve().parent

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);a=ap.parse_args();repo=a.repo.resolve()
    if ROOT!=repo/'tools/v164_bundle':raise ValueError('WRONG_INSTALLATION')
    out=repo/'results/v164';logs=out/'logs';logs.mkdir(parents=True,exist_ok=True)
    if (logs/'v164_budget.sqlite').exists():raise ValueError('NO_AUTOMATIC_REEXECUTION_WITH_EXISTING_LEDGER')
    cmds=[('tests',[sys.executable,str(ROOT/'run_workstation_tests.py'),'--out',str(out/'workstation_tests')])]
    cmds += [(mode,[sys.executable,str(ROOT/'code/v164_run.py'),'--repo',str(repo),'--mode',mode]) for mode in ('preflight','execute','verify')]
    run_id=uuid.uuid4().hex;receipts=[];result=0
    for stage,cmd in cmds:
        p=subprocess.run(cmd,cwd=repo,capture_output=True);name=run_id+'_'+stage
        (logs/(name+'.stdout')).write_bytes(p.stdout);(logs/(name+'.stderr')).write_bytes(p.stderr)
        receipts.append(dict(stage=stage,command=cmd,returncode=p.returncode,stdout=name+'.stdout',stderr=name+'.stderr'))
        (logs/(run_id+'_commands.json')).write_text(json.dumps(receipts,indent=2)+'\n',encoding='utf-8')
        print(stage,p.returncode,flush=True)
        if p.returncode:result=p.returncode;break
    p=subprocess.run([sys.executable,str(ROOT/'code/v164_report_pack.py'),'--out',str(out)],cwd=repo)
    return result or p.returncode
if __name__=='__main__':raise SystemExit(main())
