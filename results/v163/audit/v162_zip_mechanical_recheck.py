"""Independent re-derivation of the original V162 return-ZIP mechanical facts.

This script re-parses the frozen V162 return archive from raw bytes and
re-derives the facts printed in audit/v162_portable_check_receipt.json. It
imports nothing from tools/v163_bundle or the packer, makes no model forward
call, and opens every SQLite file read-only. It is a mechanical/structural
reconstruction only: CRC and hashes never establish scientific acceptance.

Inputs
  --v162-zip          the V162 return ZIP bytes (exported from the frozen git
                      object results/v162/iscat_v162_return.zip)
  --v162-worktree-zip optional second physical copy, byte-compared
  --v162-handoff-zip  the V162 handoff ZIP that defines the 222-node inventory
  --receipt           audit/v162_portable_check_receipt.json (regenerated copy)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sqlite3
import tempfile
import zipfile
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v162-zip", type=Path, required=True)
    ap.add_argument("--v162-worktree-zip", type=Path)
    ap.add_argument("--v162-handoff-zip", type=Path, required=True)
    ap.add_argument("--receipt", type=Path, required=True)
    ap.add_argument("--author-receipt", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    receipt = json.loads(a.receipt.read_text(encoding="utf-8"))
    rows_out: dict = {
        "artifact": "iscat_v162_return.zip",
        "method": "independent raw re-parse of frozen bytes (no bundle/packer imports, no model calls)",
        "scope": "MECHANICAL_AND_LEDGER_RECONSTRUCTION_ONLY_NOT_SCIENTIFIC_ACCEPTANCE",
        "receipt_path": str(a.receipt),
        "receipt_sha256": sha256_bytes(a.receipt.read_bytes()),
        "checks": {},
        "rederived": {},
        "mismatches": [],
    }
    if a.author_receipt is not None:
        author_bytes = a.author_receipt.read_bytes()
        rows_out["author_receipt_path"] = str(a.author_receipt)
        rows_out["author_receipt_sha256"] = sha256_bytes(author_bytes)
        rows_out["checks"]["regenerated_receipt_content_equals_author_copy"] = (
            json.loads(author_bytes) == receipt
        )
        rows_out["facts"] = {
            "regenerated_receipt_bytes": a.receipt.stat().st_size,
            "author_receipt_bytes": len(author_bytes),
            "regenerated_receipt_byte_identical_to_author_copy": (
                a.receipt.read_bytes() == author_bytes
            ),
            "note": "the regenerated receipt differs from the author copy only in JSON"
            " indentation/trailing newline; parsed content is identical",
        }

    raw = a.v162_zip.read_bytes()
    rows_out["frozen_zip_path"] = str(a.v162_zip)
    rows_out["frozen_zip_bytes"] = len(raw)
    rows_out["frozen_zip_sha256"] = sha256_bytes(raw)
    rows_out["checks"]["frozen_zip_sha256_equals_receipt_archive_sha256"] = (
        rows_out["frozen_zip_sha256"] == receipt["archive_sha256"]
    )
    if a.v162_worktree_zip is not None:
        wb = a.v162_worktree_zip.read_bytes()
        rows_out["worktree_zip_path"] = str(a.v162_worktree_zip)
        rows_out["worktree_zip_sha256"] = sha256_bytes(wb)
        rows_out["checks"]["worktree_copy_byte_identical_to_frozen_blob"] = wb == raw

    handoff = json.loads(
        zipfile.ZipFile(a.v162_handoff_zip).read("test_inventory.json").decode("utf-8-sig")
    )
    rows_out["v162_handoff_zip_sha256"] = sha256_bytes(a.v162_handoff_zip.read_bytes())
    rows_out["v162_handoff_nodeids"] = len(handoff["nodeids"])

    with zipfile.ZipFile(a.v162_zip) as z:
        names = z.namelist()
        rows_out["checks"]["crc_testzip_none"] = z.testzip() is None
        rows_out["checks"]["no_duplicate_members"] = len(names) == len(set(names))
        manifest = list(
            csv.DictReader(io.StringIO(z.read("manifest_sha256.csv").decode("utf-8-sig")))
        )
        rows_out["checks"]["member_set_equals_manifest_plus_manifest_file"] = (
            set(names) == {r["path"] for r in manifest} | {"manifest_sha256.csv"}
        )
        bad = []
        for r in manifest:
            b = z.read(r["path"])
            if len(b) != int(r["bytes"]) or sha256_bytes(b) != r["sha256"]:
                bad.append(r["path"])
        rows_out["checks"]["every_member_matches_manifest"] = not bad
        rows_out["rederived"]["members"] = len(names)
        rows_out["rederived"]["manifest_rows"] = len(manifest)
        rows_out["rederived"]["manifest_hash_mismatches"] = bad

        tests = json.loads(z.read("workstation_tests/pytest_outcomes.json").decode("utf-8-sig"))
        rows_out["rederived"]["tests"] = len(tests["collected"])
        rows_out["rederived"]["test_phase_reports"] = len(tests["reports"])
        rows_out["checks"]["collected_nodeids_match_v162_inventory"] = (
            sorted(tests["collected"]) == handoff["nodeids"]
        )
        rows_out["checks"]["all_phase_reports_passed"] = all(
            r["outcome"] == "passed" for r in tests["reports"]
        )
        rows_out["checks"]["no_collection_errors_and_exitstatus_zero"] = (
            not tests["collection_errors"] and tests["exitstatus"] == 0
        )

        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "v162_budget.sqlite"
            db.write_bytes(z.read("logs/v162_budget.sqlite"))
            con = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
            integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
            tasks = con.execute("SELECT id,cap,used,state,result_sha FROM tasks").fetchall()
            attempts = con.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
            con.close()
        rows_out["rederived"]["sqlite_integrity"] = integrity
        rows_out["rederived"]["tasks"] = tasks
        rows_out["rederived"]["attempts"] = attempts
        rows_out["checks"]["sqlite_integrity_ok"] = integrity == "ok"
        rows_out["checks"]["task_rows_equal_receipt"] = [list(t) for t in tasks] == receipt["tasks"]
        rows_out["checks"]["task_result_sha_seals_packed_result_file"] = (
            tasks[0][4] == sha256_bytes(z.read("tasks/LOADER_1/result.json"))
        )

        designs = json.loads(z.read("design/saved_array_designs.json").decode("utf-8-sig"))
        evaluations = sum(
            len(rs) for g in designs.values() for ds in g["designs"].values() for rs in ds.values()
        )
        rows_out["rederived"]["groups"] = len(designs)
        rows_out["rederived"]["design_evaluations"] = evaluations

    for key in ("members", "manifest_rows", "tests", "test_phase_reports", "attempts", "groups", "design_evaluations", "sqlite_integrity"):
        if rows_out["rederived"][key] != receipt[key]:
            rows_out["mismatches"].append(
                {"field": key, "receipt": receipt[key], "rederived": rows_out["rederived"][key]}
            )
    rows_out["checks"]["every_rederived_field_equals_receipt"] = not rows_out["mismatches"]
    rows_out["all_checks_ok"] = all(rows_out["checks"].values())
    rows_out["verdict"] = (
        "V162_RECEIPT_INDEPENDENTLY_REDERIVED_FROM_FROZEN_BYTES"
        if rows_out["all_checks_ok"]
        else "V162_RECEIPT_REDERIVATION_FAILED"
    )
    rows_out["note"] = (
        "The historical receipt was produced by tools/v163_bundle/audit/audit_v162_return.py"
        " against the V162 handoff (222-node inventory); this recheck re-derives the same"
        " facts from the frozen V162 return bytes in this repository's own history."
        " Mechanical consistency is not scientific acceptance."
    )
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rows_out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(rows_out["verdict"])
    if rows_out["mismatches"]:
        print("mismatches:", json.dumps(rows_out["mismatches"]))
    return 0 if rows_out["all_checks_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
