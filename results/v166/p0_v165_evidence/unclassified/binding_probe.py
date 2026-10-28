import sys, json, time
from pathlib import Path
sys.path.insert(0, r"C:\iscat\v165\tools\v165_bundle\code")
sys.path.insert(0, r"C:\iscat\v165\tools")
import v165_io as io
cfg = json.load(open(r"C:\iscat\v165\config\v146_science_config.json", encoding="utf-8-sig"))
t0 = time.time()
b = io.camera_binding(Path(r"C:\iscat\v165"), cfg)
print("binding seconds", round(time.time()-t0,2))
print("threshold", b["threshold"], "detections", b["detections"])
for g in b["by_group"]:
    print(g, [(e["event_id"], round(e["T"],8), e["detected"]) for e in b["by_group"][g]])
s = io.frozen_starts(Path(r"C:\iscat\v165"), ["ANON_01","ANON_02","ANON_03","ANON_04"])
for g in s:
    f = s[g]["first"]; sec = s[g]["second"]
    print(g, "first idx", f["start_index"], "Q", f["Q_joint"], "h", round(f["theta"][1],3),
          "| second idx", sec["start_index"], "Q", sec["Q_joint"], "h", round(sec["theta"][1],3),
          "| stratum", s[g]["stratum_available"], s[g]["stratum_flag"], "| all six", s[g]["all_six"])
