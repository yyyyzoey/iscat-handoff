import json, hashlib
from pathlib import Path
repo = Path(r"C:\iscat\v165")
cfg = json.load(open(repo/"config/v146_science_config.json", encoding="utf-8-sig"))
for rel, exp in cfg["frozen"]["source_sha256"].items():
    p = repo/rel
    act = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    print(("OK " if act==exp else "BAD"), rel, act[:12] if act else None, exp[:12])
print("model_id", cfg["frozen"]["model_id"])
print("library", cfg["inputs"]["training_library"], hashlib.sha256((repo/cfg["inputs"]["training_library"]).read_bytes()).hexdigest()[:12])
print("results/v165 exists:", (repo/"results/v165").exists())
