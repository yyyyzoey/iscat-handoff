"""Byte-exact intake of launcher receipts that live outside the v162 worktree.

Only copies; never edits, truncates or re-serialises the source bytes.  Each
row records the original absolute path, its sha256 before and after copying,
and the destination.  Refuses to overwrite a destination that already holds
different bytes.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[1]
LAUNCH_F32 = Path(r"C:\iscat\v162_launcher_f32d0e154d434bc79516ae32779a7a5a")
LAUNCH_FB = Path(r"C:\iscat\v162_launcher_fb50457c049f444e8945c7a3ab03b1cb")

PAIRS = [
    (LAUNCH_F32 / "final_pack.json", "launcher/v162_launcher_f32d0e154d434bc79516ae32779a7a5a/final_pack.json"),
    (LAUNCH_F32 / "final_pack.stdout", "launcher/v162_launcher_f32d0e154d434bc79516ae32779a7a5a/final_pack.stdout"),
    (LAUNCH_F32 / "final_pack.stderr", "launcher/v162_launcher_f32d0e154d434bc79516ae32779a7a5a/final_pack.stderr"),
    (LAUNCH_FB / "launcher_state.json", "launcher/v162_launcher_fb50457c049f444e8945c7a3ab03b1cb/launcher_state.json"),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    rows, failures = [], []
    for src, rel in PAIRS:
        dst = RESULTS / rel
        if not src.is_file():
            failures.append(f"MISSING_SOURCE:{src}")
            continue
        src_sha, src_bytes = sha(src), src.stat().st_size
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.is_file():
            if sha(dst) != src_sha:
                failures.append(f"DEST_EXISTS_DIFFERENT_BYTES:{dst}")
                continue
            state = "ALREADY_IDENTICAL"
        else:
            dst.write_bytes(src.read_bytes())
            state = "COPIED"
        rows.append(
            dict(source=str(src), destination=str(dst.relative_to(RESULTS).as_posix()),
                 bytes=src_bytes, source_sha256=src_sha, destination_sha256=sha(dst),
                 byte_identical=sha(dst) == src_sha, state=state)
        )
    report = dict(
        audit_kind="V162_OUT_OF_TREE_LAUNCHER_RECEIPT_INTAKE",
        method="byte-exact copy, sha256 compared before and after",
        rows=rows,
        failures=failures,
        verdict="INTAKE_OK" if not failures else "INTAKE_INCOMPLETE",
        scope="source preservation only; not a test or science acceptance",
        note=(
            "The f32d0e15 launcher's extracted payload directory and the two launch attempts' "
            "absolute paths are recorded here; payload digests are in each launcher_state.json."
        ),
    )
    out = Path(__file__).with_name("out_of_tree_receipt_intake.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
