"""Frozen V165 task identifiers; do not replace or auto-expand."""
GROUPS=('ANON_01','ANON_02','ANON_03','ANON_04')
REPS=(0,1,2)
SIGMAS=(10,1)

def tasks():
    rows=[]
    for g in GROUPS:
        rows.append(dict(task_id=f'B100000_{g}_NO_HEIGHT',group=g,replicate=None,sigma_nm=None))
        for rep in REPS:
            for sigma in SIGMAS:
                rows.append(dict(task_id=f'B100000_{g}_H{sigma}_R{rep:02d}',group=g,
                                 replicate=rep,sigma_nm=float(sigma)))
    if len(rows)!=28 or len({r['task_id'] for r in rows})!=28:raise AssertionError('TASK_COUNT')
    return rows
