"""Write actual V165 pytest collection and phase outcomes; never synthesize PASS."""
from __future__ import annotations

import json
import os
from pathlib import Path


collected = []
reports = []
collection_errors = []


def pytest_collection_modifyitems(session, config, items):
    collected[:] = [item.nodeid for item in items]


def pytest_collectreport(report):
    if report.failed:
        collection_errors.append(str(report.longrepr))


def pytest_runtest_logreport(report):
    row = {
        "nodeid": report.nodeid,
        "when": report.when,
        "outcome": report.outcome,
    }
    if report.failed:
        row["longrepr"] = str(report.longrepr)
    reports.append(row)


def pytest_sessionfinish(session, exitstatus):
    destination = os.environ.get("V165_PYTEST_OUTCOMES")
    if not destination:
        return
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "collected": collected,
                "reports": reports,
                "collection_errors": collection_errors,
                "exitstatus": int(exitstatus),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

