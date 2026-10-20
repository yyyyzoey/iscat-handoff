p = r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff\tools\run_v120_cache_observation.py'
src = open(p, encoding='utf-8-sig').read()
old = '''    with h5py.File(fn, 'r') as h:
        Es_r = h['a/Es/real'][:]
        Es_i = h['a/Es/imag'][:]
        Eref_r = h['a/Eref/real'][:]
        Eref_i = h['a/Eref/imag'][:]
    Es = Es_r + 1j * Es_i
    Eref = Eref_r + 1j * Eref_i'''
new = '''    with h5py.File(fn, 'r') as h:
        Es_c = h['a/Es'][:]
        Eref_c = h['a/Eref'][:]
    Es = Es_c['real'] + 1j * Es_c['imag']
    Eref = Eref_c['real'] + 1j * Eref_c['imag']'''
assert old in src, 'load fix'
src = src.replace(old, new)
open(p, 'w', encoding='utf-8').write(src)
import ast; ast.parse(src)
print('compound read fixed')
