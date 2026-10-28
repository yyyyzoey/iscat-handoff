import json,sys
from pathlib import Path
sys.path.insert(0,'tools/v165_bundle/code')
from v165_io import read
repo=Path('.').resolve()
cfg=read(repo/'config/v146_science_config.json')
print('camera_fit',cfg.get('camera_fit'))
print('inputs.camera_h5',cfg['inputs']['camera_h5'])
print('N_cases',cfg['N_cases'])
print('frozen keys',sorted(cfg['frozen'].keys()))
print('camera h5 exists',(repo/cfg['inputs']['camera_h5']).is_file())
print('v163 ctx files',sorted(p.name for p in (repo/'results/v163/source_context/v156').glob('100000_*.json')))
print('truth file exists',(repo/'results/v142/validation/new_N_validator_only_truth.json').is_file())
PY
