"""V167 P5 delivery helper: full code SHA and full results SHA manifests.

Contract section 10.6 line 230 asks for "最终发布代码完整SHA、结果完整SHA、唯一ZIP和
外部SHA回执". This script builds the first two as reviewable CSVs.

It is deliberately shipped under results/v167/, not under tools/v167/, because
code_identities() scans only tools/v167 and tools/v167_bundle: a file placed there
would move the run identity of an already-blocked round. This helper therefore never
changes the identity it reports.

Behaviour: read-only over the repo. It opens the budget ledger only through
sqlite3 in mode=ro, calls no model, and writes only under results/v167/p5_delivery/.
Existing output paths are refused rather than overwritten.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("C:/iscat/v167")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import v167.v167_common as common  # noqa: E402
import v167.v167_controller as ctrl  # noqa: E402

OUT = ROOT / "results" / "v167"
HERE = OUT / "p5_delivery"
LEDGER = OUT / "logs" / "v167_budget.sqlite"


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_new(path: Path, text: str) -> str:
    """Append-only evidence: the repo's own write-new helper, never an overwrite."""
    return common.write_text_new(path, text)


def csv_text(rows: list[tuple[str, int, str]]) -> str:
    body = "".join(f"{sha},{size},{path}\n" for sha, size, path in rows)
    return "sha256,bytes,path\n" + body


def emit(rows: list[tuple[str, int, str]], name: str) -> dict:
    csv_path = HERE / name
    text = csv_text(rows)
    write_new(csv_path, text)
    aggregate = common.sha_file(csv_path)
    sidecar = HERE / (name + ".aggregate.sha256")
    write_new(sidecar, aggregate + "\n")
    return {
        "manifest": csv_path.relative_to(ROOT).as_posix(),
        "rows": len(rows),
        "manifest_sha256": aggregate,
        "manifest_bytes": csv_path.stat().st_size,
        "aggregate_sidecar": sidecar.relative_to(ROOT).as_posix(),
        "aggregate_sidecar_bytes": sidecar.stat().st_size,
        "aggregate_sidecar_format": "64 lowercase hex then one LF; sha256 of the CSV bytes",
        "sum_bytes_of_listed_files": sum(row[1] for row in rows),
    }


def code_rows(codes: dict) -> list[tuple[str, int, str]]:
    return sorted((row["sha256"], row["bytes"], rel)
                  for rel, row in codes["files"].items())


def results_rows(excluded: set[Path]) -> list[tuple[str, int, str]]:
    rows = []
    for path in sorted(OUT.rglob("*")):
        if not path.is_file() or path in excluded or "__pycache__" in path.parts:
            continue
        rows.append((common.sha_file(path), path.stat().st_size,
                     path.relative_to(ROOT).as_posix()))
    return rows


def ledger_readonly_summary() -> dict:
    con = sqlite3.connect("file:" + LEDGER.resolve().as_posix() + "?mode=ro", uri=True)
    try:
        tasks = list(con.execute("SELECT id, phase, state, cap, used FROM tasks"))
        attempts = list(con.execute("SELECT task, seq, state FROM attempts"))
    finally:
        con.close()
    states: dict[str, int] = {}
    for _, _, state, _, _ in tasks:
        states[state] = states.get(state, 0) + 1
    attempt_states: dict[str, int] = {}
    for _t, _s, state in attempts:
        attempt_states[state] = attempt_states.get(state, 0) + 1
    return {
        "ledger": LEDGER.relative_to(ROOT).as_posix(),
        "ledger_sha256": common.sha_file(LEDGER),
        "opened": "sqlite mode=ro",
        "tasks": len(tasks),
        "task_states": states,
        "used_calls_total": sum(row[4] or 0 for row in tasks),
        "cap_total": sum(row[3] or 0 for row in tasks),
        "attempts": len(attempts),
        "attempt_states": attempt_states,
    }


def main() -> int:
    codes = ctrl.code_identities()
    # The delivery manifests live in the tree they inventory, so they cannot hash
    # themselves; they are listed here and published beside the archive.
    planned = {HERE / name for name in (
        "v167_code_sha256_manifest.csv",
        "v167_code_sha256_manifest.csv.aggregate.sha256",
        "v167_results_sha256_manifest.csv",
        "v167_results_sha256_manifest.csv.aggregate.sha256",
        "delivery_manifest_receipt.json",
    )}
    code_summary = emit(code_rows(codes), "v167_code_sha256_manifest.csv")
    results_summary = emit(results_rows(planned), "v167_results_sha256_manifest.csv")

    receipt = {
        "schema": "iscat167.delivery_manifests.1",
        "utc": utc(),
        "produced_by": "results/v167/p5_delivery/build_delivery_manifests.py",
        "contract_reference": "section 10.6 line 230 (full code SHA, full results SHA)",
        "git_head": codes["git_head"],
        "v166_release_commit": codes["v166_release_commit"],
        "code_identity_sha256": codes["identity_sha256"],
        "code_identity_checks_all_true": all(codes["identity_checks"].values()),
        "code_manifest": code_summary,
        "results_manifest": results_summary,
        "self_exclusion": {
            "excluded_from_results_manifest": sorted(
                p.relative_to(ROOT).as_posix() for p in planned),
            "reason": ("a manifest cannot contain the SHA-256 of its own bytes; these five "
                       "paths are published beside the archive and their digests appear in "
                       "this receipt"),
        },
        "scope": {
            "code_manifest_scope": ("exactly the file set code_identities() binds the run to: "
                                    "tools/v167, tools/v167_bundle, the nine pinned V165/shared "
                                    "code files, and the five frozen literals"),
            "results_manifest_scope": "every file under results/v167 at generation time",
            "model_calls": 0,
            "ledger_writes": 0,
            "budget": ledger_readonly_summary(),
            "reportable_D": None,
            "experimental_absolute_diameter_validated": False,
        },
    }
    text = json.dumps(receipt, indent=1, ensure_ascii=False, sort_keys=True) + "\n"
    write_new(HERE / "delivery_manifest_receipt.json", text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
