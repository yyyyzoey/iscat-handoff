"""Read-only audit of immutable V138 *published* text and optional 12 NPZ arrays.

A successful exit means the audit ran. Science status is explicitly separate.
"""
from __future__ import annotations
import argparse,csv,json,math
from pathlib import Path
import numpy as np
from v139_common import load_json,canonical_raw_to_merged,sha_file

SOURCE_COMMIT='ec2f9e81b0a43b7081e383e80361862e7ae200eb'
CASES=[f'M{i:02d}' for i in range(1,7)]

def rows(p):
    with open(p,encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def audit(repo,verify_arrays=False):
    root=Path(repo).resolve();base=root/'results/v138';status=load_json(base/'status.json')
    if status.get('task')!='V138_RAW_OBSERVATION_OPERATOR_FORENSICS_AND_QUALIFIED_SIZING':
        raise ValueError('unexpected task')
    raw=rows(base/'validation/raw_M_direct_vs_merged_H5.csv')
    if len(raw)!=12 or set((r['case'],r['variant']) for r in raw)!={(c,v) for c in CASES for v in ('default','at_offset')}:
        raise ValueError('missing/duplicate raw source pairs')
    original=rows(base/'validation/within_render_intensity_identity.csv')
    if len(original)!=12:raise ValueError('per-file intensity rows incomplete')
    direct=rows(base/'validation/F2_interpolation_on_verified_raw_M.csv')
    if len(direct)!=12:raise ValueError('F2/direct rows incomplete')
    samples={};failed=[]
    for r in raw:
        k=(r['case'],r['variant'])
        if r['status']!='PASS_BITWISE' or float(r['abs_L2'])!=0.:
            failed.append((k,'published raw/H5 identity not PASS'))
        if verify_arrays:
            p=base/f'provenance/{r["case"]}_{r["variant"]}_raw_and_merged.npz'
            with np.load(p,allow_pickle=False) as z:
                nat=np.asarray(z['original_render_C']);merged=np.asarray(z['combined_M_H5_C']);own=np.asarray(z['replay_from_its_own_I_and_Ibg'])
            if not np.array_equal(canonical_raw_to_merged(nat),merged):failed.append((k,'independent raw/H5 numerical replay changed'))
            if not np.array_equal(nat,own):failed.append((k,'raw intensity replay changed'))
            samples[f'{r["case"]}_{r["variant"]}']={'npz_sha256':sha_file(p),'native_shape':list(nat.shape),'merged_shape':list(merged.shape)}
    by_variant={}
    for variant in ('default','at_offset'):
        subset=[r for r in direct if r['variant']==variant]
        if len(subset)!=6:raise ValueError('F2 variant records incomplete')
        vals=[float(r['relative_L2']) for r in subset]
        by_variant[variant]=dict(n=6,within_original_1pct=sum(v<=0.01 for v in vals),
               fail_cases=[r['case'] for r in subset if float(r['relative_L2'])>0.01],
               min_relative_L2=min(vals),max_relative_L2=max(vals),mean_relative_L2=sum(vals)/6)
    env=load_json(base/'validation/development_envelope_frozen.json')
    if env.get('n_cases')!=24 or not math.isfinite(env.get('epsilon_dev_L2',math.nan)):raise ValueError('missing dev epsilon')
    hist=load_json(base/'logs/historical_v137_budget_breach.json')
    b=rows(base/'logs/resource_budget.csv');tot=[r for r in b if r['event']=='TOTAL_V138']
    if len(tot)!=1:raise ValueError('missing V138 budget total')
    sf=(root/'tools/v138_forensics.py').read_text(encoding='utf-8')
    sd=(root/'tools/v138_requalify_dev_envelope.py').read_text(encoding='utf-8')
    sr=(root/'tools/v138_run_all.py').read_text(encoding='utf-8')
    report={'schema':'iscat139.published_v138_audit.1','source_commit_expected':SOURCE_COMMIT,
       'basis':'V138_FIXED_GIT_TEXT_FILES_AND_12_PUBLISHED_NPZ_IF_ENABLED__NOT_BEM_REDERIVATION',
       'source_binary_npz_verified':bool(verify_arrays),'paired_source_checks':samples,
       'raw_mat_h5_bitwise_publication_pass':12-len([x for x in failed if 'raw/H5' in x[1]]),
       'issues_from_independent_replay':failed,'F2_vs_raw':by_variant,
       'epsilon_dev_L2_published':env['epsilon_dev_L2'],
       'epsilon_scope':'OPENED_HJKL_CONDITIONAL_EMPIRICAL_ERROR_NOT_GLOBAL_BOUND',
       'historical_v137_camera_exposures':hist['camera_exposure_events_cumulative'],
       'historical_v137_camera_limit':hist['camera_limit'],
       'v138_new_budget':{k:int(tot[0][k]) for k in ('f2_calls','new_renders','new_camera_exposures')},
       'source_code_flags':{
           'same_render_camera_replay_uses_index_clamping': 'np.clip(np.searchsorted' in sf,
           'v138_root_mismatch_control_is_center_prediction_vs_offset_observation':'C0-Yoff' in sd,
           'v138_run_all_none_command_on_nonresume':"run('handoff_tests',None" in sr,
           'resume_skips_based_only_on_output_file_existence':'SKIP_RESUMED' in sr,
           'render_to_original_solve_hash_link_not_closed':True,
           'camera_axis_transform_not_independent_experimental_calibration':True},
       'science_verdict':'PARTIAL__RAW_SOURCE_MAPPING_ESTABLISHED__F2_SHIFT_PHYSICS_UNQUALIFIED',
       'no_absolute_experimental_diameter':True}
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--out',required=True);p.add_argument('--verify-arrays',action='store_true');a=p.parse_args()
    report=audit(a.repo,a.verify_arrays)
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    print('PUBLISHED_AUDIT_EXECUTED_NOT_SCIENCE_PASS',json.dumps({'raw_pairs':12,'F2_offset_gate':report['F2_vs_raw']['at_offset']['within_original_1pct'],'science_verdict':report['science_verdict']}))
    return 2 if report['issues_from_independent_replay'] else 0
if __name__=='__main__':raise SystemExit(main())
