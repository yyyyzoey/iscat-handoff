import hashlib,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from v164_receipts import hashes,verify_receipt


def valid_receipt(tmp_path):
    root=tmp_path/'bundle';root.mkdir();out=tmp_path/'out';out.mkdir()
    for d in ('code','tests','config'):(root/d).mkdir()
    (root/'code/core.py').write_bytes(b'x=1\n');(root/'tests/test_x.py').write_bytes(b'pass\n')
    for f in ('prepare_v164.py','run_all.py','run_workstation_tests.py','launcher_main_template.py'):(root/f).write_bytes(b'# fixture\n')
    node='tests/test_x.py::test_one';(root/'test_inventory.json').write_text(json.dumps({'nodeids':[node]}))
    output=b'1 passed';(out/'test_output.txt').write_bytes(output)
    report=dict(collected=[node],collection_errors=[],exitstatus=0,reports=[dict(nodeid=node,when=w,outcome='passed') for w in ('setup','call','teardown')])
    rb=json.dumps(report).encode();(out/'pytest_outcomes.json').write_bytes(rb)
    r=dict(returncode=0,scope='COMPONENT_AND_SYNTHETIC_MODEL_TESTS_NOT_PHYSICAL_VALIDATION',hashes=hashes(root),before=hashes(root),cwd=str(root),command=[sys.executable,'-m','pytest','-q','-p','v164_receipt_plugin','tests'],output_sha256=hashlib.sha256(output).hexdigest(),outcomes_sha256=hashlib.sha256(rb).hexdigest())
    (out/'test_receipt.json').write_text(json.dumps(r));return root,out,r


def test_production_receipt_roundtrip(tmp_path):
    root,out,r=valid_receipt(tmp_path);assert verify_receipt(root,out)==r

@pytest.mark.parametrize('cause',['code','wrong_root','failed','wrong_command'])
def test_receipt_not_just_pass_word(tmp_path,cause):
    root,out,r=valid_receipt(tmp_path)
    if cause=='code':(root/'code/core.py').write_bytes(b'x=2\n')
    if cause=='wrong_root':r['cwd']=str(tmp_path)
    if cause=='failed':r['returncode']=1
    if cause=='wrong_command':r['command']=[sys.executable,'-m','pytest','old_tests']
    (out/'test_receipt.json').write_text(json.dumps(r))
    with pytest.raises(ValueError):verify_receipt(root,out)
