"""V140 source-cache lineage: solve -> 3 render keys -> files -> ledger.

A successful result establishes a deterministic key/ledger/pipeline link,
NOT embedded cryptographic solve SHA inside the renderer. Truth is used only
for this source audit, never in a sizing estimator.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,sys
from pathlib import Path,PureWindowsPath
import h5py

CASES=tuple('M%02d'%i for i in range(1,7))

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def digest_filename(full_key,kind):
    return ('sol_' if kind=='solve' else 'ren_')+hashlib.sha1(full_key.encode('ascii')).hexdigest()+'.mat'

def basename(s):return PureWindowsPath(str(s).replace('/','\\')).name

def solve_record(root,mapping,ledger,case,registry):
    tag=f'holdout_{case}'
    matches=[r for r in mapping if r['keytype']=='solve' and ('__'+tag+'__') in r['full_key']]
    if len(matches)!=1:raise ValueError(f'{case}: expected one solve map row, got {len(matches)}')
    source=matches[0];skey=source['full_key']
    if basename(source['file'])!=digest_filename(skey,'solve'):
        raise ValueError(f'{case}: solver file name does not equal SHA1 of source key')
    solve_path=root/'results/v126/bem_cache'/basename(source['file'])
    if not solve_path.is_file():raise FileNotFoundError(solve_path)
    with h5py.File(solve_path,'r') as hf:
        g=hf['meta']; got={k:float(g[k][()]) for k in ('D_nm','h_nm','gap_nm','np_re','np_im','mesh','lambda_nm','NA','nwater','nglass')}
    if (abs(got['D_nm']-registry['D_nm'])>1e-9 or abs(got['h_nm']-registry['h_nm'])>1e-9
        or abs(got['gap_nm']-(got['h_nm']-got['D_nm']/2))>1e-9 or int(got['mesh'])!=1444):
        raise ValueError(f'{case}: solve meta and original task disagree')
    records=[]
    for variant in ('default','wide','at_offset'):
        suffix=('__'+variant+'_dx'+ ('0' if variant!='at_offset' else '%g'%registry['dx_nm'])+'_dy'+('0' if variant!='at_offset' else '%g'%registry['dy_nm']))
        renders=[r for r in mapping if r['keytype']=='render' and ('__'+skey+suffix)==r['full_key'][r['full_key'].find('__'+skey):]]
        if len(renders)!=1:raise ValueError(f'{case}: expected one {variant} render key; got {len(renders)}')
        r=renders[0];rkey=r['full_key']
        if basename(r['file'])!=digest_filename(rkey,'render'):
            raise ValueError(f'{case}/{variant}: render SHA1 filename and render key disagree')
        rp=root/'results/v126/renders'/basename(r['file'])
        if not rp.is_file():raise FileNotFoundError(rp)
        ok_s=[x for x in ledger if x['case_tag']==tag and x['case_key']==skey and x['action'] in ('solve','cache_hit','cache_hit_imported') and x['ok']=='1']
        ok_r=[x for x in ledger if x['case_tag']==tag and x['case_key']==rkey and x['action'] in ('render','render_cache_hit') and x['ok']=='1']
        if not ok_s or not ok_r:raise ValueError(f'{case}/{variant}: expected successful solver/render ledger entries')
        records.append(dict(case=case,variant=variant,solver_key=skey,render_key=rkey,
            solve_filename=basename(source['file']),render_filename=basename(r['file']),
            solve_sha256=sha(solve_path),render_sha256=sha(rp),
            source_D_nm=got['D_nm'],source_h_nm=got['h_nm'],source_gap_nm=got['gap_nm'],
            registered_dx_nm=0 if variant!='at_offset' else registry['dx_nm'],
            registered_dy_nm=0 if variant!='at_offset' else registry['dy_nm'],
            source_identity='PIPELINE_CACHE_KEY_LEDGER_LINKED_NOT_EMBEDDED_SOLVE_CONTENT_SHA',
            code_dependency='source/v126_physical_forward_adapter.m'))
    return records

def run(repo,cfg,out):
    repo=Path(repo).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    with (repo/cfg['original_cache_key_map']).open(encoding='utf-8-sig',newline='') as f:mapping=list(csv.DictReader(f))
    with (repo/cfg['original_matlab_ledger']).open(encoding='utf-8-sig',newline='') as f:ledger=list(csv.DictReader(f))
    cases={r['case']:r for r in cfg['M_opened_development_cases']}
    if set(cases)!=set(CASES):raise ValueError('Case identities do not cover M01-M06')
    rows=[]
    for c in CASES:rows.extend(solve_record(repo,mapping,ledger,c,cases[c]))
    with (out/'cache_key_lineage.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    result=dict(n_solve_cases=6,n_render_rows=len(rows),source_link_status='PIPELINE_KEY_AND_EXECUTION_LEDGER_LINKED',
       cryptographic_render_embedded_solve_sha=False,
       scope='HISTORICAL_PIPELINE_EXECUTION_EVIDENCE_NOT_INDEPENDENT_MAXWELL_REDERIVATION')
    (out/'cache_key_lineage_summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--config',required=True);p.add_argument('--out',required=True);args=p.parse_args()
    cfg=json.loads(Path(args.config).read_text(encoding='utf-8'))
    try: res=run(args.repo,cfg,args.out)
    except Exception as e:
        o=Path(args.out);o.mkdir(parents=True,exist_ok=True)
        (o/'lineage_error.json').write_text(json.dumps(dict(status='BLOCKED',error=repr(e)),indent=2)+'\n')
        print(repr(e),file=sys.stderr);return 2
    print(json.dumps(res,ensure_ascii=False));return 0
if __name__=='__main__':raise SystemExit(main())
