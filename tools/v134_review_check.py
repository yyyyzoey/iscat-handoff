#!/usr/bin/env python3
"""Published V133 M result arithmetic, not a BEM or physical-model test."""
import json,math
from pathlib import Path
p=Path(__file__).resolve().parent
s=json.loads((p/'review_recomputations.json').read_text())
d=[53,81,119,149,171,187]
y=[48.421809635083875,81.27358906303667,122.11998103353119,151.07969710737842,167.83725685498712,190.29730590514112]
e=[v-t for v,t in zip(y,d)]
assert len(e)==s['cases']==6
assert abs(sum(map(abs,e))/6-s['MAE_nm'])<1e-12
assert abs(math.sqrt(sum(a*a for a in e)/6)-s['RMSE_nm'])<1e-12
assert sum(abs(a)<=max(5,.1*t) for a,t in zip(e,d))==s['target_only_pass']==6
c=json.loads((p/'config.json').read_text())
assert c['budget_hard_limits']['new_bem_attempts']==0
assert c['experiment_absolute_diameter_validated'] is False
assert len(c['actual_reuse_M'])==6
print('PASS: arithmetic and V134 handoff config (not physics qualification)')
