import csv,hashlib,importlib.util,io,zipfile
from pathlib import Path
import pytest
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('launcher_test',root/'launcher_main_template.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

def payload(name='file.txt',extra=False,badhash=False):
    raw=b'evidence';text=io.StringIO();w=csv.DictWriter(text,fieldnames=['path','bytes','sha256']);w.writeheader()
    w.writerow(dict(path=name,bytes=len(raw),sha256='0'*64 if badhash else hashlib.sha256(raw).hexdigest()))
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as z:
        z.writestr(name,raw);z.writestr('manifest_sha256.csv',text.getvalue())
        if extra:z.writestr('extra.py',b'no')
    return out.getvalue()

def test_complete_embedded_payload_verification():
    b=payload();r=mod.validate(b,hashlib.sha256(b).hexdigest());assert r['members']==2

@pytest.mark.parametrize('mode',['digest','member','hash','escape'])
def test_launcher_refuses_incomplete_or_changed_payload(mode):
    b=payload(name='../escape' if mode=='escape' else 'file.txt',extra=mode=='member',badhash=mode=='hash')
    with pytest.raises(ValueError):mod.validate(b,'0'*64 if mode=='digest' else hashlib.sha256(b).hexdigest())
