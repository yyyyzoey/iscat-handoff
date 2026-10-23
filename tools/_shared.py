"""Standard-library-only read-only audit helpers. Nothing here certifies Maxwell physics."""
from __future__ import annotations
import csv, hashlib, json, math
from pathlib import Path


def load_json(path):
    with Path(path).open('r',encoding='utf-8-sig') as h:return json.load(h)


def rows(path):
    with Path(path).open('r',encoding='utf-8-sig',newline='') as h:return list(csv.DictReader(h))


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for x in iter(lambda:f.read(1<<20),b''):h.update(x)
    return h.hexdigest()


def save_json(path,data):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')


def value(x):
    v=float(x)
    if not math.isfinite(v):raise ValueError('nonfinite value')
    return v


def stats(truth,estimate):
    if len(truth)!=len(estimate) or not truth:raise ValueError('wrong sample pairing')
    errors=[value(e)-value(t) for e,t in zip(estimate,truth)]
    return {'count':len(errors),'MAE_nm':sum(abs(e) for e in errors)/len(errors),
            'RMSE_nm':math.sqrt(sum(e*e for e in errors)/len(errors)),
            'max_abs_error_nm':max(map(abs,errors)),'signed_errors_nm':errors,
            'engineer_goal_pass':sum(abs(e)<=max(5.,.1*value(t)) for e,t in zip(errors,truth))}
