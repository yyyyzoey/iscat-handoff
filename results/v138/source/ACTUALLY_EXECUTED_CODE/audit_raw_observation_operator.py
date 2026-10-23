#!/usr/bin/env python3
"""Read-only M original-render vs merged-H5 contrast identity investigation.

Matches declared default -> root C and at_offset -> at_offset/C at the SAME
render/case and SAME array convention. Transpose/flip results are exploratory,
NEVER applied to the data nor selected as calibration by residual minimization.

This is a source-operator audit, not original-BEM solve geometry acceptance.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math
from pathlib import Path, PureWindowsPath
import numpy as np
import h5py

CASE_IDS = [f'M{i:02d}' for i in range(1,7)]
VARIANT_TO_DATASET = {'default': 'C', 'at_offset': 'at_offset/C'}


def sha_file(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def sha_array(a):
    a = np.ascontiguousarray(a)
    return hashlib.sha256((str(a.shape) + '|' + str(a.dtype)).encode() + a.tobytes()).hexdigest()


def load_float(dataset, label):
    x = dataset[()]
    if np.iscomplexobj(x) or x.dtype.names or x.ndim != 2 or not np.isfinite(x).all():
        raise ValueError(label + ': expected finite real 2D array')
    return np.asarray(x, dtype=float)


def central(a, n=13):
    if a.ndim != 2 or a.shape[0] != a.shape[1] or a.shape[0] < n or (a.shape[0]-n)%2:
        raise ValueError('No unambiguous central score ROI')
    k = (a.shape[0]-n)//2
    return a[k:k+n, k:k+n]


def compare(a, b):
    if a.shape != b.shape:
        return {'status': 'SHAPE_MISMATCH', 'shape_A': list(a.shape), 'shape_B': list(b.shape)}
    err = a-b
    norm_b = float(np.linalg.norm(b))
    return {
        'status': 'CALCULATED_NOT_QUALIFIED',
        'shape': list(a.shape),
        'abs_L2': float(np.linalg.norm(err)),
        'relative_L2': float(np.linalg.norm(err)/norm_b) if norm_b > 0 else None,
        'max_abs': float(np.max(np.abs(err))),
        'reference_norm_L2': norm_b,
    }


def exploratory_symmetries(src, dst):
    if src.shape != dst.shape:
        return {}
    tx = {
        'IDENTITY': src,
        'TRANSPOSE_ONLY': src.T,
        'FLIP_FIRST_AXIS_ONLY': src[::-1,:],
        'FLIP_SECOND_AXIS_ONLY': src[:,::-1],
        'ROTATE_180_ONLY': src[::-1,::-1],
        'TRANSPOSE_FLIP_FIRST': src.T[::-1,:],
        'TRANSPOSE_FLIP_SECOND': src.T[:,::-1],
        'TRANSPOSE_ROTATE_180': src.T[::-1,::-1]
    }
    return {name: float(np.linalg.norm(a-dst)) for name,a in tx.items()}


def original_render_arrays(path):
    with h5py.File(path, 'r') as f:
        if 'r' not in f:raise ValueError(f'{path}: missing r group')
        r = f['r']
        for x in ('contrast', 'Itotal', 'Iref'):
            if x not in r:raise ValueError(f'{path}: missing r/{x}')
        C = load_float(r['contrast'], 'r/contrast')
        I = load_float(r['Itotal'], 'r/Itotal')
        B = load_float(r['Iref'], 'r/Iref')
        if I.shape != B.shape or I.shape != C.shape:raise ValueError('render intensity vs contrast shape mismatch')
        if np.any(B <= 0):raise ValueError('nonpositive per-pixel reference intensity')
        C_replayed = (I-B)/B
        meta = {}
        if 'rmeta' in f:
            q = f['rmeta']
            for k in ('dx','dy','focus_z','q'):
                if k in q and q[k].size == 1:meta[k]=float(np.asarray(q[k][()]).item())
        if 'cfg' in r and 'particle' in r['cfg']:
            part = r['cfg']['particle']
            for k in ('diameter_nm', 'gap_nm'):
                if k in part and part[k].size == 1:meta['render_cfg_'+k]=float(part[k][()])
        if 'center_nm' in r:meta['render_center_nm'] = np.asarray(r['center_nm'][()]).ravel().astype(float).tolist()
        if 'object_pixel_nm' in r:meta['render_object_pixel_nm'] = float(r['object_pixel_nm'][()])
        return C, C_replayed, meta


def resolve_source(original_path, root):
    p = Path(original_path)
    if p.exists():return p
    filename = PureWindowsPath(original_path).name
    possible = [root/'results'/'v126'/'renders'/filename, root/filename]
    for k in possible:
        if k.is_file():return k
    raise FileNotFoundError(f'Original render missing: {original_path}; tried {possible}')


def audit(repo: Path, out: Path, *, write_arrays=False):
    repo = Path(repo).resolve()
    out = Path(out).resolve();out.mkdir(parents=True, exist_ok=True)
    with (repo/'results/v134/provenance/M_raw_source_audit.csv').open('r',encoding='utf-8-sig',newline='') as f:
        index = list(csv.DictReader(f))
    mapping = {}
    for r in index:
        if r['case'] in CASE_IDS and r['variant'] in VARIANT_TO_DATASET:
            key=(r['case'],r['variant'])
            if key in mapping:raise ValueError('Duplicate raw render mapping: '+str(key))
            mapping[key]=r
    if set(mapping)!={(c,v) for c in CASE_IDS for v in VARIANT_TO_DATASET}:
        raise ValueError('Incomplete M default / at_offset original render mapping')
    cases = json.loads((repo/'results/v126/v132_M_cases.json').read_text(encoding='utf-8-sig'))['cases']
    case_info = {}
    for r in cases:
        k=r['tag'].removeprefix('holdout_')
        offsets=[v['shift_xy_nm'] for v in r['renders'] if v['variant']=='at_offset']
        if k in case_info or len(offsets)!=1:raise ValueError('Duplicated M task key or offset')
        case_info[k] = {'D_record': r['D_nm'], 'h_record':r['h_nm'],'xy_offset_record':offsets[0]}
    if sorted(case_info)!=CASE_IDS:raise ValueError('M task registry identity mismatch')
    h5path=repo/'results/v132/validation/new_M_images.h5'
    outputs=[]
    with h5py.File(h5path,'r') as h:
        for case in CASE_IDS:
            for variant,dataset in VARIANT_TO_DATASET.items():
                idx=mapping[case,variant]
                row={'case':case,'variant':variant,'merged_dataset':f'{case}/{dataset}',
                     'recorded_D':case_info[case]['D_record'],
                     'recorded_h':case_info[case]['h_record'],
                     'qualification':'NOT_YET_PHYSICAL_QUALIFIED'}
                try:
                    orig = resolve_source(idx['file'],repo)
                    row['original_render_path']=str(orig)
                    row['original_render_file_sha256']=sha_file(orig)
                    C,C_replay,meta=original_render_arrays(orig)
                    row['raw_render_C_sha256']=sha_array(C)
                    row['raw_render_intensity_identity']=compare(C,C_replay)
                    row['render_meta']=meta
                    if case not in h or dataset not in h[case]:
                        raise KeyError(f'{case}/{dataset} absent in published combined H5')
                    merged = load_float(h[case][dataset],f'{case}/{dataset}')
                    row['merged_C_sha256']=sha_array(merged)
                    row['same_array_convention_raw_vs_merged']=compare(C,merged)
                    row['central13_raw_vs_merged']=compare(central(C),central(merged))
                    row['exploratory_NOT_ACCEPTED_symmetry_L2']=exploratory_symmetries(C,merged)
                    want = [0.,0.] if variant == 'default' else case_info[case]['xy_offset_record']
                    row['expected_xy_offset']=want
                    row['render_offset_exact']=(abs(meta.get('dx',math.nan)-want[0])<1e-9 and
                                                abs(meta.get('dy',math.nan)-want[1])<1e-9)
                    # Even byte-identical image observations cannot certify solve geometry.
                    row['mapping_consistent_no_transform'] = (
                        row['render_offset_exact'] and
                        row['same_array_convention_raw_vs_merged']['status']=='CALCULATED_NOT_QUALIFIED' and
                        row['same_array_convention_raw_vs_merged']['max_abs']<=1e-10)
                    if write_arrays:
                        np.savez_compressed(out/f'{case}_{variant}_raw_and_merged.npz',
                            original_render_C=C, replay_from_its_own_I_and_Ibg=C_replay,
                            combined_M_H5_C=merged)
                except Exception as exc:
                    row['error'] = f'{type(exc).__name__}: {exc}'
                    row['mapping_consistent_no_transform']=False
                outputs.append(row)
    result = {'schema':'iscat138.raw_observation_audit.1',
              'scope':'RAW_RENDER_MAT_TO_COMBINED_H5_OBSERVATION_IDENTITY__NO_GEOMETRY_CERTIFICATE',
              'combined_h5_sha256':sha_file(h5path),
              'pairs':outputs,
              'n_matched_without_transform':sum(bool(x.get('mapping_consistent_no_transform')) for x in outputs),
              'n_required':12,
              'truth_use':'CASE_REGISTRY_ONLY_IN_EXTERNAL_SOURCE_AUDITOR_NOT_IN_ESTIMATOR',
              'transform_selection_forbidden':'SYMMETRY_COMPARISON_DIAGNOSTIC_ONLY',
              'next_action':'AUDIT_SOLVE_PARTICLE_GEOMETRY_AND_SAME_SOLVE_WIDE_FIELD_RENDER_AFTER_IDENTITY_CHECK'}
    (out/'raw_operator_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    slim=[]
    for x in outputs:
        q=x.get('central13_raw_vs_merged') or {}
        r=x.get('raw_render_intensity_identity') or {}
        slim.append({'case':x['case'],'variant':x['variant'],
                     'raw_render_mat_file_sha256':x.get('original_render_file_sha256'),
                     'raw_C_minus_own_intensities_L2':r.get('abs_L2'),
                     'raw_vs_combined_central13_relative_L2':q.get('relative_L2'),
                     'raw_vs_combined_central13_absolute_L2':q.get('abs_L2'),
                     'same_orientation_no_transform_match':x.get('mapping_consistent_no_transform',False),
                     'error':x.get('error')})
    with (out/'raw_operator_audit.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(slim[0]));w.writeheader();w.writerows(slim)
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--repo',required=True)
    p.add_argument('--out',required=True)
    p.add_argument('--write-arrays',action='store_true')
    a=p.parse_args()
    r=audit(Path(a.repo),Path(a.out),write_arrays=a.write_arrays)
    print(json.dumps({'n_matched_without_transform':r['n_matched_without_transform'],
                      'n_required':r['n_required'],
                      'scope':r['scope']},indent=2,ensure_ascii=False))
    return 0  # File inspection successful; any scientific mismatches are in JSON.

if __name__=='__main__':
    raise SystemExit(main())
