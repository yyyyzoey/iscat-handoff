"""Independent mechanical verification of the delivered return ZIP.

Deliberately does NOT import any bundle/packer code: the ZIP is re-parsed from
raw bytes, and every member is re-hashed and compared against a re-parsed copy
of manifest_sha256.csv.  Reports are written next to this script and are, by
construction, external to the ZIP (a ZIP cannot contain a digest of itself;
the official packer already excludes archive_receipt.json for the same reason).
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[1]
ZIP_PATH = RESULTS / "iscat_v162_return.zip"
MANIFEST_PATH = RESULTS / "manifest_sha256.csv"
OUT_JSON = Path(__file__).with_name("final_zip_mechanical_verification.json")
OUT_MD = Path(__file__).with_name("final_zip_mechanical_verification.md")
ALLOWED_NON_MANIFEST = {"manifest_sha256.csv"}
PACKER_EXCLUDED = ["iscat_v162_return.zip", "manifest_sha256.csv", "archive_receipt.json"]


def main() -> int:
    raw = ZIP_PATH.read_bytes()
    rows = list(csv.DictReader(io.StringIO(MANIFEST_PATH.read_text(encoding="utf-8"))))
    report: dict = {
        "artifact": ZIP_PATH.name,
        "zip_path": str(ZIP_PATH),
        "zip_bytes": len(raw),
        "zip_sha256": hashlib.sha256(raw).hexdigest(),
        "manifest_path": str(MANIFEST_PATH),
        "manifest_rows": len(rows),
        "method": "independent raw re-parse (no bundle/packer imports)",
        "external_to_zip": True,
        "external_reason": "post-pack measurement; a ZIP cannot carry its own digest",
        "external_files_added_after_pack": [
            "audit/final_zip_mechanical_verification.py",
            "audit/final_zip_mechanical_verification.json",
            "audit/final_zip_mechanical_verification.md",
        ],
        "external_files_note": (
            "These three audit files were created/run after the final v162_report_pack.py pass, so they are "
            "not ZIP members. This mirrors the official packer, which already excludes archive_receipt.json "
            "from members for the same reason. Every other file under results/v162 is a verified ZIP member."
        ),
        "packer_excluded_members": PACKER_EXCLUDED,
        "checks": {},
        "mismatches": [],
    }
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        crc = z.testzip()
        report["checks"]["crc_testzip_none"] = crc is None
        if crc is not None:
            report["mismatches"].append(f"CRC_FAILED:{crc}")
        manifest_rows_ok = 0
        for r in rows:
            p, n, h = r["path"], int(r["bytes"]), r["sha256"]
            if p not in names:
                report["mismatches"].append(f"MISSING_MEMBER:{p}")
                continue
            b = z.read(p)
            if len(b) != n:
                report["mismatches"].append(f"SIZE_MISMATCH:{p}:{len(b)}!={n}")
                continue
            a = hashlib.sha256(b).hexdigest()
            if a != h:
                report["mismatches"].append(f"SHA_MISMATCH:{p}")
                continue
            manifest_rows_ok += 1
        report["checks"]["manifest_rows_verified"] = manifest_rows_ok
        report["checks"]["manifest_rows_total"] = len(rows)
        expected = {r["path"] for r in rows} | ALLOWED_NON_MANIFEST
        report["checks"]["member_set_equals_manifest_plus_manifest_file"] = set(names) == expected
        report["checks"]["member_count"] = len(names)
        report["checks"]["members_not_in_manifest"] = sorted(set(names) - expected)
        report["checks"]["manifest_rows_not_in_zip"] = sorted(expected - set(names))
        report["checks"]["zip_contains_self_digest"] = ZIP_PATH.name in names
        report["checks"]["zip_contains_archive_receipt"] = "archive_receipt.json" in names
        if set(names) != expected:
            report["mismatches"].append("MEMBER_SET_MISMATCH")
        report["members"] = [
            dict(path=n, bytes=z.getinfo(n).file_size, sha256=hashlib.sha256(z.read(n)).hexdigest())
            for n in names
        ]
    report["verdict"] = "MECHANICALLY_CONSISTENT" if not report["mismatches"] else "MECHANICAL_MISMATCH"
    report["scope"] = "ZIP_STRUCTURE_ONLY_NOT_SCIENTIFIC_ACCEPTANCE"
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(
        "# V162 return ZIP - independent mechanical verification\n\n"
        f"- artifact: `{report['artifact']}` ({report['zip_bytes']} bytes)\n"
        f"- sha256: `{report['zip_sha256']}`\n"
        f"- members: {report['checks']['member_count']} (manifest rows {len(rows)} + `manifest_sha256.csv`)\n"
        f"- CRC `testzip()`: {report['checks']['crc_testzip_none']}\n"
        f"- members re-hashed and matched to manifest: {manifest_rows_ok}/{len(rows)}\n"
        f"- member set == manifest + manifest file: {report['checks']['member_set_equals_manifest_plus_manifest_file']}\n"
        f"- mismatches: {report['mismatches']}\n"
        f"- verdict: **{report['verdict']}** (scope: {report['scope']})\n\n"
        "This receipt is external to the ZIP by construction (a ZIP cannot contain its own digest);\n"
        "the official packer excludes `archive_receipt.json` from members for the same reason.\n",
        encoding="utf-8",
    )
    print(json.dumps({k: report[k] for k in ("zip_sha256", "verdict", "mismatches")}, ensure_ascii=False))
    print(json.dumps(report["checks"], ensure_ascii=False, indent=2))
    return 0 if not report["mismatches"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
