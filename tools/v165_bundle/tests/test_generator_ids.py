import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'generator'))
from v165_generate_height import generate
from v165_task_ids import tasks

def test_every_height_task_matches_exact_reading_id():
 t={'cases':[{'case':f'N{i:02d}','D_nm':d,'h_nm':h} for i,d,h in [(1,59,391.25),(2,101,432.5),(3,143,478.75),(4,181,526.25)]]}
 readings,_=generate(t)
 tasks_aug={r['task_id'] for r in tasks() if r['sigma_nm'] is not None}
 assert {r['reading_id'] for r in readings}==tasks_aug
