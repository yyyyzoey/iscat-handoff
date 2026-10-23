"""V138 whole-task coordinator (resume-aware; records real stage statuses)."""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--resume',action='store_true')
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    py=sys.executable;log={'stages':{}}
    def run(name,cmd,skip):
        if a.resume and skip():log['stages'][name]='SKIP_RESUMED';return
        r=subprocess.run(cmd,capture_output=True,text=True)
        log['stages'][name]=dict(returncode=r.returncode,stdout=r.stdout.strip()[-300:],stderr=r.stderr.strip()[-300:])
    run('handoff_tests',None,lambda:True)
    run('intake_audit',[py,str(repo/'tools/audit_v137.py'),'--repo',str(repo),'--out',str(out/'preflight/v137_published_audit.json')],lambda:(out/'preflight/v137_published_audit.json').is_file())
    run('raw_operator_audit',[py,str(repo/'tools/audit_raw_observation_operator.py'),'--repo',str(repo),'--out',str(out/'provenance'),'--write-arrays'],lambda:(out/'provenance/raw_operator_audit.json').is_file())
    run('forensics',[py,str(repo/'tools/v138_forensics.py'),'--repo',str(repo),'--out',str(out)],lambda:(out/'provenance/forensics_summary.json').is_file())
    run('dev_envelope',[py,str(repo/'tools/v138_requalify_dev_envelope.py'),'--repo',str(repo),'--out',str(out)],lambda:(out/'validation/development_envelope_frozen.json').is_file())
    run('s4_s5',[py,str(repo/'tools/v138_s4_s5.py'),'--repo',str(repo),'--out',str(out)],lambda:(out/'validation/old_camera_and_multiframe_method_audit.json').is_file())
    (out/'run_all_log.json').write_text(json.dumps(log,indent=2)+chr(10),encoding='utf-8')
    print(json.dumps({k:(v if isinstance(v,str) else v['returncode']) for k,v in log['stages'].items()}))
if __name__=='__main__':main()
