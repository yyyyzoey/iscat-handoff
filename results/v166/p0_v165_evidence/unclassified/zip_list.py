import zipfile
z = zipfile.ZipFile(r"C:\iscat\v165\results\v164\iscat_v164_return.zip")
names = z.namelist()
print("members:", len(names))
for n in names:
    if n.startswith("audit/") or n.startswith("validator") or n in ("status.json","execution_integrity.json","execution_truth_report.json","verification.json","archive_receipt.json","failures.jsonl"):
        print(" ", n, z.getinfo(n).file_size)
print("has manifest:", "manifest_sha256.csv" in names)
import json
print("status:", json.loads(z.read("status.json")) if "status.json" in names else None)
