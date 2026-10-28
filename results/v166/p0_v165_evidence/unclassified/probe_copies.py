import hashlib
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
a=sha(r'C:\iscat\v164\tools\v164_bundle\code\v152_budget_store.py')
b=sha(r'C:\iscat\v165\tools\v163_bundle\code\v152_budget_store.py')
c=sha(r'C:\iscat\v165\tools\v165_bundle\code\v152_budget_store.py')
print('v164copy',a);print('v163copy',b);print('v165copy',c);print('all_equal',a==b==c)
g=sha(r'C:\iscat\v165\tools\v165_bundle\code\v152_gls_core.py')
h=sha(r'C:\iscat\v165\tools\v164_bundle\code\v152_gls_core.py')
i=sha(r'C:\iscat\v165\tools\v163_bundle\code\v152_gls_core.py')
print('gls v165',g);print('gls v164',h);print('gls v163',i);print('gls_all_equal',g==h==i)
