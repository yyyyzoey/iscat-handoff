from pathlib import Path
import hashlib,json

def hashes(root):
    root=Path(root)
    paths=[p for f,g in [('code','*.py'),('tests','test_*.py'),('config','*.json')] for p in sorted((root/f).glob(g))]
    paths += [root/n for n in ('prepare_v164.py','run_all.py','run_workstation_tests.py','test_inventory.json','launcher_main_template.py')]
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

def verify_receipt(root,folder):
    root=Path(root);folder=Path(folder)
    r=json.loads((folder/'test_receipt.json').read_text());o=json.loads((folder/'pytest_outcomes.json').read_text());inv=json.loads((root/'test_inventory.json').read_text())
    if r.get('returncode')!=0 or r.get('scope')!='COMPONENT_AND_SYNTHETIC_MODEL_TESTS_NOT_PHYSICAL_VALIDATION':raise ValueError('TEST_RETURN_CODE')
    if r.get('hashes')!=hashes(root) or r.get('before')!=r.get('hashes'):raise ValueError('TESTED_FILES_CHANGED')
    if Path(r.get('cwd','')).resolve()!=root.resolve():raise ValueError('WRONG_TEST_ROOT')
    if r.get('command',[])[1:]!=['-m','pytest','-q','-p','v164_receipt_plugin','tests']:raise ValueError('WRONG_TEST_COMMAND')
    if sorted(o['collected'])!=inv['nodeids'] or o['collection_errors'] or o['exitstatus']!=0:raise ValueError('TEST_SET_OR_COLLECTION')
    if len(o['reports'])!=3*len(inv['nodeids']):raise ValueError('TEST_REPORT_COUNT')
    for n in inv['nodeids']:
        rs=[x for x in o['reports'] if x['nodeid']==n]
        if len(rs)!=3 or {(x['when'],x['outcome']) for x in rs}!={('setup','passed'),('call','passed'),('teardown','passed')}:raise ValueError('INCOMPLETE_TEST:'+n)
    for key,name in [('outcomes_sha256','pytest_outcomes.json'),('output_sha256','test_output.txt')]:
        if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=r[key]:raise ValueError('TEST_OUTPUT_CHANGED')
    return r
