"""Generate ONLY hypothetical auxiliary-height measurements for V165.

Truth access is deliberately restricted to this generator and the separate
post-estimation validator. This is OPENED development data, NOT new blind data.
Generated readings are independent of saved camera noise by construction.
The production estimator must NEVER import this module or open the truth file.
"""
from __future__ import annotations
import hashlib,json,argparse
from pathlib import Path
import numpy as np

GROUPS=('ANON_01','ANON_02','ANON_03','ANON_04')
SIGMAS=(10.0,1.0)
REPS=3
SEED=16520261027


def generate(truth_doc, *, seed=SEED):
    cases=truth_doc['cases']
    truth={f'ANON_{int(x["case"][1:]):02d}':x for x in cases}
    if sorted(truth)!=list(GROUPS) or len(cases)!=4:
        raise ValueError('FOUR_FROZEN_N_SCENES_REQUIRED')
    rng=np.random.Generator(np.random.PCG64(seed))
    eps=rng.standard_normal((4,REPS))
    readings=[];validator=[]
    for gi,group in enumerate(GROUPS):
        src=truth[group]
        h=float(src['h_nm']);D=float(src['D_nm'])
        if not np.isfinite(h) or not np.isfinite(D):raise ValueError('INVALID_VALIDATOR_TRUTH')
        for rep in range(REPS):
            for sig in SIGMAS:
                reading_id=f'B100000_{group}_H{int(sig)}_R{rep:02d}'
                z=float(h+sig*eps[gi,rep])
                readings.append(dict(reading_id=reading_id,group=group,
                       B=100000,replicate=rep,sigma_nm=sig,
                       z_nm=z,hypothetical=True,
                       independent_camera_noise_assumption=True,
                       generation='GAUSSIAN_HEIGHT_NOISE_ONLY_NO_NEW_CAMERA_FRAMES'))
                validator.append(dict(reading_id=reading_id,group=group,
                      B=100000,replicate=rep,sigma_nm=sig,
                      h_scene_nm=h,D_scene_nm=D,epsilon=float(eps[gi,rep]),z_nm=z))
    if len(readings)!=24 or len({r['reading_id'] for r in readings})!=24:
        raise AssertionError('READING_COUNT_OR_DUPLICATE')
    return readings,validator


def main():
    p=argparse.ArgumentParser();p.add_argument('--truth',type=Path,required=True)
    p.add_argument('--height-input-out',type=Path,required=True)
    p.add_argument('--validator-sealed-out',type=Path,required=True)
    a=p.parse_args()
    if a.height_input_out.resolve()==a.validator_sealed_out.resolve():
        raise ValueError('SEPARATE_ESTIMATOR_AND_VALIDATOR_PATHS')
    raw=a.truth.read_bytes()
    doc=json.loads(raw.decode('utf-8-sig'))
    readings,validator=generate(doc)
    public=dict(schema='iscat165.hypothetical_height_readings.1',
        scope='OPENED_DEV_SIMULATION_NOT_INDEPENDENT_EXPERIMENT',
        seed=SEED,groups=list(GROUPS),sigma_nm=list(SIGMAS),replicates=REPS,
        readings=readings,truth_file_sha256=hashlib.sha256(raw).hexdigest(),
        no_camera_noise_draw=True,no_new_camera_exposures=True,
        no_experimental_height_observation=True)
    private=dict(schema='iscat165.validator_only.1',seed=SEED,
        source_truth_sha256=hashlib.sha256(raw).hexdigest(),rows=validator)
    for path,obj in [(a.height_input_out,public),(a.validator_sealed_out,private)]:
        path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():raise FileExistsError('NEVER_OVERWRITE_EXISTING_MEASUREMENT_OR_VALIDATOR_FILE')
        path.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'scope':public['scope'],'public_readings':24,'groups':4,
          'replicates':3,'seed':SEED,'height_out':str(a.height_input_out),
          'validator_out':str(a.validator_sealed_out)}))
if __name__=='__main__':main()
