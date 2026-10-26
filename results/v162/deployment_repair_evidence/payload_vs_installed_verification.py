import csv, hashlib, io, json, zipfile
from pathlib import Path

PYZ = Path(r"C:\Users\PC\Downloads\iscat_v162_launcher.pyz")
BUNDLE = Path(r"C:\iscat\v162\tools\v162_bundle")
OUT = Path(r"C:\iscat\v162\results\v162\deployment_repair_evidence\payload_vs_installed_verification.json")

with zipfile.ZipFile(PYZ) as z:
    raw = z.read("payload.zip")
payload_sha = hashlib.sha256(raw).hexdigest()
with zipfile.ZipFile(io.BytesIO(raw)) as pz:
    members = pz.namelist()
    rows = list(csv.DictReader(io.StringIO(pz.read("manifest_sha256.csv").decode("utf-8"))))

result = dict(
    purpose="Prove that after reverting the one uncommitted deployment-repair edit, every installed bundle file is byte-identical to the bytes inside the executable launcher payload.",
    launcher_pyz=str(PYZ),
    launcher_pyz_sha256=hashlib.sha256(PYZ.read_bytes()).hexdigest(),
    embedded_payload_sha256=payload_sha,
    payload_members=len(members),
    manifest_rows=len(rows),
    mismatches=[], extras=[], checked_files=0,
)
blobs = zipfile.ZipFile(io.BytesIO(raw))
for r in rows:
    b = blobs.read(r["path"])
    inst = BUNDLE / r["path"]
    want = r["sha256"]
    if hashlib.sha256(b).hexdigest() != want:
        raise SystemExit("PAYLOAD_MANIFEST_SELF_INCONSISTENT:" + r["path"])
    if not inst.is_file():
        result["mismatches"].append(dict(path=r["path"], state="MISSING"))
        continue
    got = hashlib.sha256(inst.read_bytes()).hexdigest()
    result["checked_files"] += 1
    if got != want:
        result["mismatches"].append(dict(path=r["path"], state="DIFFERENT", payload_sha256=want, installed_sha256=got,
                                         payload_bytes=int(r["bytes"]), installed_bytes=inst.stat().st_size))

manifest_paths = {r["path"] for r in rows}
blobs.close()
for p in sorted(BUNDLE.rglob("*")):
    if p.is_file():
        rel = p.relative_to(BUNDLE).as_posix()
        if rel not in manifest_paths and rel != "manifest_sha256.csv":
            result["extras"].append(dict(path=rel, bytes=p.stat().st_size, in_payload_zip=rel in members))

result["verdict"] = "ALL_MANIFEST_ROWS_BYTE_IDENTICAL" if not result["mismatches"] else "MISMATCH_PRESENT"
OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print("verdict:", result["verdict"], "| checked:", result["checked_files"], "| mismatches:", len(result["mismatches"]), "| extras:", len(result["extras"]))
for e in result["extras"]:
    print("EXTRA:", e["path"], e["bytes"], "in_payload=", e["in_payload_zip"])
