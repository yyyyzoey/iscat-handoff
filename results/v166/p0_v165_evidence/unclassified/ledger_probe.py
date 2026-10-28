import sqlite3, statistics
con = sqlite3.connect("file:C:/iscat/v165/results/v164/logs/v164_budget.sqlite?mode=ro", uri=True)
print("phase stats:")
for r in con.execute("SELECT t.phase,COUNT(a.seq),MIN(a.ts),MAX(a.ts) FROM attempts a JOIN tasks t ON t.id=a.task GROUP BY t.phase"):
    print(" ", r)
print("tasks by used (FIXED_D_DESIGN):")
for r in con.execute("SELECT id,used,cap,state FROM tasks WHERE phase='FIXED_D_DESIGN' ORDER BY used DESC LIMIT 6"):
    print(" ", r)
print("tasks by used (MODEL_BINDING):")
for r in con.execute("SELECT id,used,cap,state FROM tasks WHERE phase='MODEL_BINDING' ORDER BY used DESC"):
    print(" ", r)
tid = con.execute("SELECT id FROM tasks WHERE phase='FIXED_D_DESIGN' ORDER BY id LIMIT 1").fetchone()[0]
ts = [x[0] for x in con.execute("SELECT ts FROM attempts WHERE task=? ORDER BY seq", (tid,))]
d = [b-a for a,b in zip(ts, ts[1:])]
print("task", tid, "attempts", len(ts), "median dt", statistics.median(d) if d else None, "mean dt", sum(d)/len(d) if d else None)
allts = [x[0] for x in con.execute("SELECT ts FROM attempts ORDER BY ts")]
alld = [b-a for a,b in zip(allts, allts[1:])]
print("all attempts median dt", statistics.median(alld), "mean", sum(alld)/len(alld))
