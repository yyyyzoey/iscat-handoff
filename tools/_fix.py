import re
p = r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff\tools\run_v120_cache_observation.py'
src = open(p, encoding='utf-8-sig').read()
src = src.replace(
    "os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'v074_return'",
    "os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'v074_return'"
)
open(p, 'w', encoding='utf-8').write(src)
print('fixed')
