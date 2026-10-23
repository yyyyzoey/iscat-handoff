#!/usr/bin/env python3
"""Read-only independent arithmetic audit of v141 published text artifacts.
Never labels published summaries or software tests as independent Maxwell validation.
"""
import argparse,csv,hashlib,json,math,re
from pathlib import Path
CASES=[f'M{x:02d}' for x in range(1,7)]
KERNELS=['S1_BILINEAR','S2_CUBIC']
VARIANTS=['default','at_offset']

def load_rows(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def compute(rows):
    seen={}
    for r in rows:
        k=(r['case'],r['variant'],r['kernel'])
        if k in seen:raise ValueError(f'DUPLICATE_CASE_VARIANT_KERNEL:{k}')
        seen[k]=r
        for key in ('Esca_field_rel_L2','Esca_field_abs_L2','wideEr_interpEs_C_rel_L2','direct_field_replay_C_max_abs','Er_field_rel_L2'):
            v=float(r[key]);
            if not math.isfinite(v) or v<0:raise ValueError(f'NONFINITE_OR_NEGATIVE:{k}:{key}')
    want={(c,v,k) for c in CASES for v in VARIANTS for k in KERNELS}
    if set(seen)!=want:raise ValueError('MISSING_OR_EXTRA_COMBINATIONS:'+repr(sorted(want-set(seen))))
    d={}
    for kernel in KERNELS:
        a=[seen[c,'at_offset',kernel] for c in CASES]
        z=[float(x['wideEr_interpEs_C_rel_L2']) for x in a]
        f=[float(x['Esca_field_rel_L2']) for x in a]
        d[kernel]={'n':len(a),'n_image_at_or_below_1pct':sum(y<=0.01 for y in z),
                   'image_rel_L2_by_case':{c:z[i] for i,c in enumerate(CASES)},
                   'field_rel_L2_by_case':{c:f[i] for i,c in enumerate(CASES)},
                   'image_rel_L2_max':max(z),'field_rel_L2_max':max(f),
                   'image_error_max_percent':100*max(z),'field_error_max_percent':100*max(f)}
    assert max(float(z['direct_field_replay_C_max_abs']) for z in rows)<1e-12
    return d

def audit(repo):
    p=Path(repo)/'results/v141/validation/field_level_error_separation.csv'
    summary=json.loads((Path(repo)/'results/v141/validation/field_level_summary.json').read_text(encoding='utf-8'))
    status=json.loads((Path(repo)/'results/v141/status.json').read_text(encoding='utf-8'))
    s=compute(load_rows(p))
    for kernel in KERNELS:
        if s[kernel]['n']!=summary['per_kernel_offset'][kernel]['n'] or s[kernel]['n_image_at_or_below_1pct']!=summary['per_kernel_offset'][kernel]['n_below_1pct']:
            raise ValueError('CSV_AND_PUBLISHED_FIELD_SUMMARY_DISAGREE')
    claim=status['stage_states']['SPATIAL_INTERPOLATION']
    claim_ringing=bool(re.search(r'(?:600\s*[-–]\s*760\s*%|600\s*%|760\s*%)',claim))
    cubic_field=s['S2_CUBIC']['field_error_max_percent']
    return {'fixed_source_scope':'PUBLISHED_CSV_AND_SOURCE_AUDIT_NO_RAW_MAT_REPLAY',
            'n_published_rows':24,'per_kernel':s,
            'claim_600_to_760_percent_ringing_in_status':claim_ringing,
            'cubic_max_field_relative_error_percent':cubic_field,
            'ringing_metric_independently_published':False,
            'conclusion':'PUBLISHED_600_TO_760_PERCENT_RINGING_NOT_SUPPORTED_BY_FIELD_L2_CSV; NEED_SEPARATE_OVERSHOOT_STABILITY_TEST',
            'model_identity':'V141_CUBIC_IS_SOURCE_WIDE_SPATIAL_DEV_ONLY_NOT_FULL_DH_F2C_SIZING'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();ret=audit(a.repo);dst=Path(a.out);dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_text(json.dumps(ret,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print('V141_CSV_AUDIT_OK__NOT_PHYSICS_CERTIFIED',json.dumps({'s1':ret['per_kernel']['S1_BILINEAR']['n_image_at_or_below_1pct'],'s2':ret['per_kernel']['S2_CUBIC']['n_image_at_or_below_1pct'],'max_cubic_field_pct':ret['cubic_max_field_relative_error_percent']}))
if __name__=='__main__':main()
