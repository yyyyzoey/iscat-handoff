"""V137/R1 whole-task coordinator (resume-aware). Running stages is the point;
this orchestrator records real stage statuses, it never fabricates completion."""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True);ap.add_argument('--config',required=True)
    ap.add_argument('--out',required=True);ap.add_argument('--resume',action='store_true')
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve()
    log={'stages':{}}
    def run(name,cmd,skip_if):
        if a.resume and skip_if():
            log['stages'][name]='SKIP_RESUMED';return
        r=subprocess.run(cmd,capture_output=True,text=True)
        log['stages'][name]=dict(returncode=r.returncode,stdout=r.stdout.strip()[-400:],stderr=r.stderr.strip()[-400:])
    py=sys.executable
    run('intake',[py,str(repo/'tools/audit_intake.py'),'--repo',str(repo),'--out',str(out/'preflight/intake.json')],
        lambda:(out/'preflight/intake.json').is_file())
    run('witnesses',[py,str(repo/'tools/replay_all_witnesses.py'),'--repo',str(repo),'--config',a.config,'--out',str(out/'witnesses')],
        lambda:(out/'witnesses/witness_manifest.json').is_file())
    run('coarse',[py,str(repo/'tools/profile_resume_f2.py'),'--repo',str(repo),'--config',a.config,
                  '--out',str(out/'profiles_coarse'),'--cases','M05','M06','M01','M02','M03','M04','--resume'],
        lambda:(out/'profiles_coarse/profiles/M01.json').is_file() and (out/'profiles_coarse/profiles/M06.json').is_file())
    run('adaptive',[py,str(repo/'tools/v137r1_adaptive.py'),'--repo',str(repo),'--out',str(out/'profiles_coarse')],
        lambda:(out/'profiles_coarse/adaptive_status.json').is_file())
    run('gates',[py,str(repo/'tools/v137r1_assemble.py'),'--repo',str(repo),'--r1',str(out)],
        lambda:(out/'validation/reportability_per_particle.json').is_file())
    (out/'run_all_log.json').write_text(json.dumps(log,indent=2)+chr(10),encoding='utf-8')
    print(json.dumps({k:(v if isinstance(v,str) else v['returncode']) for k,v in log['stages'].items()}))
if __name__=='__main__':main()
