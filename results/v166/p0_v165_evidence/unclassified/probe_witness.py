import sys,json,sqlite3
from pathlib import Path
sys.path.insert(0,'tools/v165_bundle/code')
from v165_io import read,sha
from v152_gls_core import GlsData
from v165_objective import augmented_objective
repo=Path('.').resolve()
z=repo/'results/v164/iscat_v164_return.zip'
print('v164 zip bytes',z.stat().st_size,'sha',sha(z))
db=repo/'results/v164/logs/v164_budget.sqlite'
con=sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True)
print('meta',con.execute('select value from metadata').fetchone()[0])
print('phases',con.execute('select phase,count(*),sum(used),sum(cap) from tasks group by phase').fetchall())
print('attempts',con.execute('select count(*) from attempts').fetchone()[0])
print('states',con.execute('select distinct state from attempts').fetchall())
con.close()
p=sorted((repo/'results/v163/rescored').glob('100000_ANON_01_*.json'))[0]
d=read(p);print('record keys',sorted(d.keys()))
print('qj',d['Q_joint'],'start',d['start_index'])
ctx=read(repo/'results/v163/source_context/v156/100000_ANON_01.json')['diagnostic']
print('ctx keys',sorted(ctx.keys()))
gd=GlsData.from_frames(ctx['frame_Y'],ctx['frame_V'])
r=augmented_objective(gd,d['C'],d['theta'])
print('recomputed Q_joint',r['Q_joint'],'stored',d['Q_joint'],'delta',r['Q_joint']-d['Q_joint'])
print('Q_model',r['Q_model'],'K',r['K'])
PY
