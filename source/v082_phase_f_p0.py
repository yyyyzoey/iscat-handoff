# -*- coding: utf-8 -*-
"""v082 Phase F: P0 independent resource gate status.

No MATLAB native run is started this session. Process state is recorded as
evidence; the P0 passive hook (<=1 attempt allowed only when license/process
state is safe) stays NOT_RUN_RESOURCE_GATED. Independent numerical phases A-E
do not depend on this branch.
"""
import os, csv, subprocess, datetime

GH = os.path.join(ROOT if False else r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff')
TAB = os.path.join(GH, 'tables')


def main():
    out = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         "Get-CimInstance Win32_Process -Filter \"Name like 'MATLAB%'\" | "
         'Select-Object ProcessId, Name, CommandLine | ConvertTo-Json -Compress'],
        capture_output=True, text=True, timeout=60)
    procs = out.stdout.strip()
    n_procs = 0 if procs in ('', 'null') else (1 if procs.lstrip().startswith('{') else len(procs.split('},{')))
    rows = [{
        'item': 'P0_passive_hook_direct_reflected_total',
        'gate': 'each < 1e-10 (frozen)',
        'historical_best': '2.58848e-07',
        'status': 'NOT_RUN_RESOURCE_GATED',
        'matlab_processes_detected': str(n_procs),
        'process_evidence': procs[:200] if procs else 'none',
        'reason': 'no MATLAB native run started this session; P0 hook deferred to preserve license/process safety budget (max 1 attempt, only when safe); independent of phases A-E',
        'recorded_utc': datetime.datetime.utcnow().isoformat() + 'Z',
    }, {
        'item': 'rule7_large_reference',
        'gate': 'increment < 0.005 (frozen)',
        'historical_best': 'NOT_RUN',
        'status': 'NOT_RUN_BUDGET_0',
        'matlab_processes_detected': 'NA',
        'process_evidence': '',
        'reason': 'no new budget authorized for rule7 this session',
        'recorded_utc': datetime.datetime.utcnow().isoformat() + 'Z',
    }]
    outp = os.path.join(TAB, 'v082_p0_status.csv')
    with open(outp, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    with open(outp, 'r', newline='', encoding='utf-8') as f:
        rr = list(csv.reader(f))
    assert len(rr) - 1 == 2 and all(len(r) == len(rr[0]) for r in rr)
    print('[F] P0 status written; matlab processes detected:', n_procs)


if __name__ == '__main__':
    main()
