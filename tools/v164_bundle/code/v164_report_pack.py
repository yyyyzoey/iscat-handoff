from pathlib import Path
import argparse,csv,hashlib,json,sqlite3,zipfile

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    def read(p):return json.loads(p.read_text(encoding='utf-8'))
    failures=[dict(file=p.relative_to(out).as_posix(),**read(p)) for p in sorted((out/'failures').glob('*.json'))]
    status=read(out/'status.json') if (out/'status.json').exists() else dict(execution_state='BLOCKED_OR_FAILED_NOT_COMPLETE')
    required=['preflight.json','profiles_all.json','pooled_all.json','logs/v164_budget.sqlite','verification.json','workstation_tests/test_receipt.json']
    commands=[read(p) for p in sorted((out/'logs').glob('*_commands.json'))]
    info=dict(required_outputs={n:(out/n).is_file() for n in required},missing_outputs=[n for n in required if not (out/n).is_file()],actual_stage_commands=commands,status=status,verification_present=(out/'verification.json').exists(),failures=failures,all_reportable_D_null=True,EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=False)
    (out/'execution_truth_report.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'execution_integrity.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'failures.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in failures),encoding='utf-8')
    (out/'00_execution_truth_report.md').write_text('# V164 execution truth report\n\n```json\n'+json.dumps(info,ensure_ascii=False,indent=2)+'\n```\n\nConditional model-separation bounds only; no experimental diameter or independent height measurement is certified.\n',encoding='utf-8')
    excluded={'manifest_sha256.csv','iscat_v164_return.zip','archive_receipt.json'}
    paths=[p for p in sorted(out.rglob('*')) if p.is_file() and p.relative_to(out).as_posix() not in excluded]
    with (out/'manifest_sha256.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);w.writeheader()
        for p in paths:w.writerow(dict(path=p.relative_to(out).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    target=out/'iscat_v164_return.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for p in paths+[out/'manifest_sha256.csv']:z.write(p,p.relative_to(out).as_posix())
    with zipfile.ZipFile(target) as z:
        if z.testzip() is not None:raise ValueError('RETURN_CRC')
    (out/'archive_receipt.json').write_text(json.dumps(dict(bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),members=len(paths)+1),indent=2)+'\n')
    print(target);return 0
if __name__=='__main__':raise SystemExit(main())
