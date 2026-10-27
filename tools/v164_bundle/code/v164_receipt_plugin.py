"""Write actual pytest collection/outcomes, not a hand-entered PASS count."""
import json, os
from pathlib import Path
collected=[]
reports=[]
collection_errors=[]
def pytest_collection_modifyitems(session,config,items):
    collected[:]=[i.nodeid for i in items]
def pytest_collectreport(report):
    if report.failed:collection_errors.append(str(report.longrepr))
def pytest_runtest_logreport(report):
    reports.append(dict(nodeid=report.nodeid,when=report.when,outcome=report.outcome))
def pytest_sessionfinish(session,exitstatus):
    dest=os.environ.get('V164_PYTEST_OUTCOMES')
    if dest:
        p=Path(dest);p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(dict(collected=collected,reports=reports,collection_errors=collection_errors,exitstatus=int(exitstatus)),indent=2)+'\n',encoding='utf-8')
