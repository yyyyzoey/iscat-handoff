"""V126: build anonymous J holdout H5, freeze model, run blind inversion."""
import csv, glob, json, os, sys
import numpy as np
import h5py

sys.path.insert(0, r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff\tools')
import v125_model_library as vml

REPO = vml.REPO
OUT = os.path.join(REPO, 'results', 'v126')
V125 = os.path.join(REPO, 'results', 'v125')

J = [('J01', 41.0, 368.5, 42.0, -98.0), ('J02', 67.0, 402.5, -126.0, 56.0),
     ('J03', 89.0, 437.5, 70.0, 126.0), ('J04', 123.0, 472.5, -98.0, -70.0),
     ('J05', 151.0, 507.5, 126.0, -42.0), ('J06', 183.0, 542.5, -56.0, 98.0)]

def build_holdout_h5():
    ridx = vml.index_v125_renders(os.path.join(V125))
    # V126 renders are indexed from the v126 cache_key_map
    import csv
    v126idx = {}
    p = os.path.join(OUT, 'logs', 'cache_key_map.csv')
    pat = vml.index_v125_renders  # reuse parser via temp map file? build manually:
    for r in csv.DictReader(open(p, newline='')):
        if r['keytype'] != 'render':
            continue
        import re
        mm = re.match(r'^(?P<img>.+?)__(?P<solver>.+?)__(?P<tag>.+?)__(?P<phys>D[-0-9.]+_h[-0-9.]+_np[-+0-9.]+_mesh\d+)__(?P<variant>.+?)_dx(?P<dx>-?[0-9.]+)_dy(?P<dy>-?[0-9.]+)$', r['full_key'])
        if mm:
            v126idx[(mm['tag'], mm['variant'], float(mm['dx']), float(mm['dy']))] = \
                r['file'] if os.path.isabs(r['file']) else os.path.join(REPO, r['file'])
    h5p = os.path.join(OUT, 'validation', 'new_holdout_images.h5')
    with h5py.File(h5p, 'w') as h:
        for tag, D, hh, x, y in J:
            t = f'holdout_{tag}'
            rd = vml.load_v125_render(v126idx[(t, 'default', 0.0, 0.0)])
            g = h.create_group(tag)
            for k in ('C', 'Iref', 'Isca', 'Icross', 'Itotal'):
                g.create_dataset(k, data=rd[k], compression='gzip', compression_opts=4)
            rw = vml.load_v125_render(v126idx[(t, 'wide', 0.0, 0.0)])
            gw = g.create_group('wide')
            gw.create_dataset('Eref', data=rw['Eref'], compression='gzip', compression_opts=4)
            gw.create_dataset('Esca', data=rw['Esca'], compression='gzip', compression_opts=4)
            gw.create_dataset('fine_x_nm', data=rw['fine_x_nm'])
            gw.create_dataset('fine_y_nm', data=rw['fine_y_nm'])
            ro = vml.load_v125_render(v126idx[(t, 'at_offset', float(x), float(y))])
            go = g.create_group('at_offset')
            go.create_dataset('C', data=ro['C'])
            g.attrs.update(dict(case=tag, mesh=1444, source='v126_direct_L1',
                                anonymous=True, status='CONDITIONAL_BLIND_HELDOUT'))
    with open(os.path.join(OUT, 'library', 'holdout_index.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['case', 'mesh', 'source', 'note'])
        for tag, D, hh, x, y in J:
            w.writerow([tag, 1444, 'v126_direct_L1_solve', 'anonymous; truth validator-only'])
    print('J holdout H5 written')

def freeze_model():
    # candidate selection from error_separation.csv (dev H01-H06)
    es = list(csv.DictReader(open(os.path.join(OUT, 'diagnostics', 'error_separation.csv'), newline='')))
    i1 = [r for r in es if r['candidate'] == 'I1']
    i2 = [r for r in es if r['candidate'] == 'I2']
    s1 = sum(float(r['fwd_err_L2']) for r in i1)
    s2 = sum(float(r['fwd_err_L2']) for r in i2)
    # pre-registered ranking: node-exactness -> domain safety -> dev diagnostics.
    # I2 has marginally lower summed fwd error but its full-fit behavior on dev
    # (H06 errH=-145 boundary disaster) is worse; I1 chosen as canonical.
    sel = 'I1'
    freeze = dict(schema='iscat126.model_freeze.1', selected_candidate=sel,
                  selection_evidence=dict(
                      sum_fwd_err_I1=s1, sum_fwd_err_I2=s2,
                      I2_dev_full_fit_failure='H06 errH=-145.5 (boundary); I1 H06 errH=+2.7',
                      node_exactness='all 63 nodes pass for I1 and I2 (<1e-12)',
                      domain_safety='both reject out-of-support; no extrapolation'),
                  frozen_before='any J01-J06 inversion',
                  forward='canonical_forward = I1: complex-field D/h bilinear, Es shifted at (x-dx,y-dy), Eref fixed',
                  score_roi='central 13x13',
                  note='H01-H06 remain DEV diagnostics; J01-J06 are the only blind holdouts')
    json.dump(freeze, open(os.path.join(OUT, 'config', 'model_freeze.json'), 'w', encoding='utf-8'), indent=1)
    print('model frozen:', sel, f'(sum_fwd I1={s1:.4g} I2={s2:.4g})')
    return sel

if __name__ == '__main__':
    build_holdout_h5()
    freeze_model()
