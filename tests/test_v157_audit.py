import csv, hashlib, io, json, sqlite3, sys, zipfile
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'audit'))
from audit_v156_readonly import archive, ledger


def test_archive_good(tmp_path):
    p=tmp_path/'a.zip';b=b'preserved\n'
    s=io.StringIO();w=csv.writer(s);w.writerow(['path','bytes','sha256']);w.writerow(['a.txt',len(b),hashlib.sha256(b).hexdigest()])
    with zipfile.ZipFile(p,'w') as z:z.writestr('a.txt',b);z.writestr('manifest_sha256.csv',s.getvalue())
    r=archive(p)
    assert r['manifest_failures']==[] and r['crc_bad_member'] is None
    assert r['unlisted_files']==[]


def test_archive_bad_hash(tmp_path):
    p=tmp_path/'a.zip'
    with zipfile.ZipFile(p,'w') as z:
        z.writestr('a.txt','wrong');z.writestr('manifest_sha256.csv','path,bytes,sha256\na.txt,5,'+'0'*64+'\n')
    assert archive(p)['manifest_failures'][0]['reason']=='SIZE_OR_HASH'


def test_archive_path_traversal_rejected(tmp_path):
    p=tmp_path/'a.zip'
    with zipfile.ZipFile(p,'w') as z:z.writestr('../escape','x')
    with pytest.raises(ValueError):archive(p)


def test_native_read_only_ledger(tmp_path):
    p=tmp_path/'a.sqlite';c=sqlite3.connect(p)
    c.executescript('CREATE TABLE metadata (id,value);CREATE TABLE tasks (id,signature,phase,cap,used,owner,state,result_path,result_sha);CREATE TABLE attempts (task,state);')
    c.execute('INSERT INTO metadata VALUES(1,?)',(json.dumps({'total':40}),))
    c.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?)',('t','sig','p',40,1,'o','FINISHED','x','h'))
    c.execute('INSERT INTO attempts VALUES(?,?)',('t','RETURNED'));c.commit();c.close()
    raw=p.read_bytes();r=ledger(p)
    assert r['integrity_check']=='ok' and r['recorded_used']==1
    assert r['task_attempt_count_matches'] and p.read_bytes()==raw


def test_wal_not_silently_ignored(tmp_path):
    p=tmp_path/'a.sqlite';p.write_bytes(b'fake');Path(str(p)+'-wal').write_bytes(b'x')
    assert ledger(p)['status']=='NEEDS_TRANSACTION_SNAPSHOT_DO_NOT_IGNORE_WAL'
