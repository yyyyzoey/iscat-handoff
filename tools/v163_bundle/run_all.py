"""Execute fixed stage order. Always archive available failure evidence. No auto-retry."""
from pathlib import Path
import argparse,json,subprocess,sys,uuid
ROOT=Path(__file__).resolve().parent

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);a=ap.parse_args();repo=a.repo.resolve()
    if ROOT!=repo/'tools/v163_bundle':raise ValueError('RUN_ONLY_FROM_ISOLATED_INSTALLED_BUNDLE')
    out=repo/'results/v163';logs=out/'logs';logs.mkdir(parents=True,exist_ok=True)
    if (out/'logs/v163_budget.sqlite').exists():
        print('EXISTING_LEDGER: use read-only verify; never automatically execute again',file=sys.stderr);return 2
    run_id=uuid.uuid4().hex
    correction = out/'history_corrections.md'
    if not correction.exists():
        correction.write_text('# V163 historical corrections\n\n'
            'V161 used a separate tools/v161_design.py, not the approved full launcher workflow. '
            'Its 204 coefficients have reversed free/exact semantics and finite-design dimension errors caught as zero compensation. '
            'Its eight probes collapse the ANON id and mix all four particles. Do not use them as nonlinearity or precision evidence.\n\n'
            'The original archive is preserved with SHA/CRC evidence. Loader use and full V161 resource total remain unverified. '
            'V163 keeps the approved GLS and optical model, and must complete the exact task set.\n',encoding='utf-8')
    commands=[('tests',[sys.executable,str(ROOT/'run_workstation_tests.py'),'--out',str(out/'workstation_tests')])]
    for mode in ('preflight','execute','verify'):
        commands.append((mode,[sys.executable,str(ROOT/'code/v163_run.py'),'--repo',str(repo),'--config',str(ROOT/'config/v163_plan.json'),'--out',str(out),'--mode',mode]))
    receipts=[];code=0
    stage_states={name:'NOT_STARTED' for name,_ in commands}
    for stage,cmd in commands:
        stage_states[stage]='RUNNING'
        p=subprocess.run(cmd,cwd=repo,capture_output=True)
        name=f'{run_id}_{stage}';(logs/(name+'.stdout')).write_bytes(p.stdout);(logs/(name+'.stderr')).write_bytes(p.stderr)
        receipts.append(dict(stage=stage,command=cmd,returncode=p.returncode,stdout=name+'.stdout',stderr=name+'.stderr'))
        stage_states[stage]='FINISHED' if p.returncode==0 else 'BLOCKED_OR_FAILED'
        (logs/(run_id+'_stage_states.json')).write_text(json.dumps(stage_states,indent=2)+'\n',encoding='utf-8')
        print(stage,'exit',p.returncode,flush=True)
        if p.returncode:
            code=p.returncode;break
    (logs/(run_id+'_stage_commands.json')).write_text(json.dumps(receipts,indent=2)+'\n',encoding='utf-8')
    p=subprocess.run([sys.executable,str(ROOT/'code/v163_report_pack.py'),'--out',str(out)],cwd=repo,capture_output=True)
    print(p.stdout.decode('utf-8',errors='replace'));print(p.stderr.decode('utf-8',errors='replace'),file=sys.stderr)
    print('pack exit',p.returncode,'; FINISHED is not experimental diameter validation')
    return code or p.returncode
if __name__=='__main__':raise SystemExit(main())
