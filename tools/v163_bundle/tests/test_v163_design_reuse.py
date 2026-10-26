from pathlib import Path
import copy,json,sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'))
from v163_design_reuse import check_reference,compare_designs

def source():return json.loads((ROOT/'audit/v162_saved_array_designs.json').read_bytes())

def test_actual_uploaded_design_grid_reused_without_forward_calls():
    r=check_reference(ROOT,source());assert r['records']==1224 and r['model_forward_calls']==0

@pytest.mark.parametrize('fault',['missing_group','changed_theta','wrong_coefficient','wrong_constraint','missing_rtol'])
def test_changed_candidate_or_matrix_result_rejected(fault):
    a=source();b=copy.deepcopy(a);key='100000_ANON_02'
    if fault=='missing_group':del b[key]
    elif fault=='changed_theta':b[key]['theta'][0]+=1
    elif fault=='wrong_coefficient':b[key]['designs']['fine']['free'][0]['total_coefficient_nm_minus2']*=2
    elif fault=='wrong_constraint':b[key]['designs']['fine']['free'][0]['exact_height']=True
    else:b[key]['designs']['coarse']['free'].pop()
    with pytest.raises(ValueError):compare_designs(a,b)
