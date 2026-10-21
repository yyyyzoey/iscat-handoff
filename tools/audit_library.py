"""Read-only local HDF5/CSV audit. No inference from a filename to physical truth.

Usage:
 python tools/audit_library.py --h5 PATH --csv PATH --baseline FIXED_OLD_H5 --report out.json
Run against original V127 evidence first, then a separately restored library.
This is a NUMERICAL/IDENTITY audit component, NOT a BEM qualification certificate.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,re
from pathlib import Path
from collections import defaultdict
import numpy as np
import h5py

NODE=re.compile(r'^D([-+0-9.eE]+)_h([-+0-9.eE]+)$')
def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def arr_hash(a):
    a=np.ascontiguousarray(a)
    b=str(a.dtype).encode()+str(a.shape).encode()+a.tobytes()
    return hashlib.sha256(b).hexdigest()
def cmplx(a):
    if a.dtype.names:
        if set(a.dtype.names)>={'real','imag'}:return a['real']+1j*a['imag']
        raise ValueError('unknown compound complex layout')
    return a

def run(h5_path,csv_path=None,baseline=None):
    errors=[];nodes=[];tables={}
    if csv_path:
        with open(csv_path,encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f):
                key=(float(row['D_nm']),float(row['h_nm']))
                if key in tables:errors.append(f'DUPLICATE_CSV_KEY:{key}')
                tables[key]=row
    by_D=defaultdict(lambda:defaultdict(list))
    with h5py.File(h5_path,'r') as h:
        for name in sorted(h.keys()):
            match=NODE.fullmatch(name)
            if not match:continue
            D,H=map(float,match.groups());g=h[name]
            r={'node':name,'D_label_nm':D,'h_label_nm':H,'errors':[]}
            for key,v in (('D_nm',D),('h_nm',H)):
                if key not in g.attrs:r['errors'].append('MISSING_ATTR:'+key)
                elif abs(float(g.attrs[key])-v)>1e-9:r['errors'].append('ATTR_LABEL_MISMATCH:'+key)
            if 'C' not in g:
                r['errors'].append('MISSING_C');nodes.append(r);continue
            C=g['C'][()]
            if C.shape!=(17,17) or np.iscomplexobj(C) or not np.isfinite(C).all():r['errors'].append('INVALID_C')
            else:
                r.update(C_sha256=arr_hash(C),center_C=float(C[8,8]),peak_abs_C=float(np.max(abs(C))))
                by_D[D][r['C_sha256']].append(H)
                if (D,H) in tables:
                    row=tables[(D,H)]
                    for k in ('center_C','peak_abs_C'):
                        if row.get(k) and not np.isclose(r[k],float(row[k]),rtol=1e-10,atol=1e-12):r['errors'].append('CSV_ARRAY_MISMATCH:'+k)
            for key in ('Eref','Esca'):
                if key not in g:r['errors'].append('MISSING_FIELD:'+key)
            if 'Eref' in g and 'Esca' in g:
                er=cmplx(g['Eref'][()]);es=cmplx(g['Esca'][()])
                if er.shape!=(85,85,3) or es.shape!=er.shape or not np.isfinite(er).all() or not np.isfinite(es).all():
                    r['errors'].append('INVALID_STANDARD_FIELDS_EXPECT_X_Y_COMPONENT')
                else:
                    q=int(g.attrs.get('subpixels',5))
                    def pm(a):return a.reshape(17,q,17,q).mean(axis=(1,3))
                    i0=pm(np.sum(abs(er)**2,axis=-1));it=pm(np.sum(abs(er+es)**2,axis=-1))
                    if np.any(i0<=0):r['errors'].append('INVALID_BACKGROUND')
                    else:
                        cr=(it-i0)/i0
                        r['max_abs_replay_C']=float(np.max(abs(cr-C)))
                        if r['max_abs_replay_C']>1e-12:r['errors'].append('C_REPLAY_FAIL')
                    r['Eref_sha256']=arr_hash(er);r['Esca_sha256']=arr_hash(es)
            if 'wide' not in g:r['errors'].append('MISSING_WIDE_FIELDS')
            else:
                wg=g['wide']
                for key in ('Eref','Esca','fine_x_nm','fine_y_nm'):
                    if key not in wg:r['errors'].append('MISSING_WIDE:'+key)
            r['provenance_attrs_present']={k:str(g.attrs[k]) for k in g.attrs if 'source' in k.lower() or 'sha' in k.lower()}
            nodes.append(r)
        if baseline:
            with h5py.File(baseline,'r') as old:
                for r in nodes:
                    if r['node'] in old and 'C' in old[r['node']] and 'C' in h[r['node']]:
                        oc=old[r['node']]['C'][()];nc=h[r['node']]['C'][()]
                        if oc.shape==nc.shape:
                            r['max_abs_C_change_from_fixed_baseline']=float(np.max(abs(nc-oc)))
                            # Changed arrays need an explicit provenance/physical explanation, never silent inheritance.
                            if r['max_abs_C_change_from_fixed_baseline']>1e-12:r['errors'].append('BASELINE_CHANGED_REQUIRES_PROVENANCE_REVIEW')
    duplicates=[{'D_nm':D,'heights_nm':hs,'C_sha256':sh} for D,vals in by_D.items() for sh,hs in vals.items() if len(hs)>1]
    if duplicates:errors.append('EXACT_DUPLICATE_C_ACROSS_HEIGHTS_REQUIRES_PROVENANCE_REVIEW')
    Ds=sorted(set(r['D_label_nm'] for r in nodes));Hs=sorted(set(r['h_label_nm'] for r in nodes))
    pairs={(r['D_label_nm'],r['h_label_nm']) for r in nodes}
    missing=[(d,h) for d in Ds for h in Hs if (d,h) not in pairs]
    if missing:errors.append('INCOMPLETE_RECTANGULAR_GRID')
    if tables and set(tables)!=pairs:errors.append('CSV_H5_KEYSET_MISMATCH')
    if not nodes:errors.append('NO_TRAIN_NODES')
    return {'scope':'read-only identity/array audit; physical provenance and coordinates require direct-source verification',
            'h5':str(h5_path),'h5_sha256':digest(h5_path),'baseline_sha256':digest(baseline) if baseline else None,
            'n_nodes':len(nodes),'Ds':Ds,'Hs':Hs,'missing_pairs':missing,'nodes':nodes,'duplicate_height_groups':duplicates,
            'errors':errors,'verdict':'PASS_ARRAY_CHECKS_ONLY' if not errors and not any(r['errors'] for r in nodes) else 'REPAIR_OR_EVIDENCE_REQUIRED',
            'electromagnetic_or_experimental_validation':False}

def main():
    a=argparse.ArgumentParser();a.add_argument('--h5',required=True);a.add_argument('--csv');a.add_argument('--baseline');a.add_argument('--report',required=True)
    p=a.parse_args();r=run(p.h5,p.csv,p.baseline)
    Path(p.report).parent.mkdir(parents=True,exist_ok=True)
    Path(p.report).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    print(r['verdict'],'nodes=',r['n_nodes'],'duplicate_height_groups=',len(r['duplicate_height_groups']))
    return 0 if r['verdict']=='PASS_ARRAY_CHECKS_ONLY' else 2
if __name__=='__main__':raise SystemExit(main())
