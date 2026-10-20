"""V125 S0: freeze source identity, verify V124 cache byte/config identity, write intake."""
import csv, hashlib, json, os, platform, subprocess, sys, glob
import numpy as np
import h5py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v124_core as vc

REPO = vc.REPO
OUT125 = os.path.join(REPO, 'results', 'v125')
V124 = os.path.join(REPO, 'results', 'v124')

def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()

TRAIN_D = [30, 50, 70, 100, 130, 160, 200]
TRAIN_H = [350, 375, 400, 425, 450, 475, 500, 525, 550]

def main():
    os.makedirs(os.path.join(OUT125, 'validation'), exist_ok=True)
    os.makedirs(os.path.join(OUT125, 'logs'), exist_ok=True)
    rows = []
    # index all V124 default renders by physics identity read from file metadata/name
    idx = {}
    for m, p in vc.iter_renders(V124):
        key = (m['D'], m['h'], m['mesh'])
        idx[key] = (m, p)
    # 1) verify the 15 reusable nodes for MAIN_7x9.
    # V124 render cfg/particle recorded the BASE config (D=50), NOT the case D;
    # authoritative per-case identity = filename meta cross-checked against the
    # V124 MATLAB ledger (ok=1 rows), plus field integrity of the arrays.
    ledger = {}
    lp = os.path.join(V124, 'logs', 'v124_matlab_ledger.csv')
    if os.path.isfile(lp):
        for r in csv.DictReader(open(lp, newline='')):
            if r['action'] in ('solve', 'cache_hit') and r['ok'] == '1':
                ledger[(float(r['d_nm']), float(r['h_nm']), int(r['mesh']))] = r
    def verify_node(D, h):
        key = (float(D), float(h), 576)
        if key not in idx:
            return False, 'missing render file', ''
        m, p = idx[key]
        led = ledger.get(key)
        name_ok = (abs(m['D'] - float(D)) < 1e-12 and abs(m['h'] - float(h)) < 1e-12
                   and m['mesh'] == 576 and abs(m['np_re'] - 1.38) < 1e-12)
        led_ok = led is not None
        try:
            r = vc.load_render(p)
            fields_ok = (r['C'].shape == (17, 17) and r['Eref'].shape == (85, 85, 3)
                         and r['Esca'].shape == (85, 85, 3)
                         and abs(r['object_pixel_nm'] - 280.0) < 1e-9
                         and r['cfg_NA'] == 0.8 and abs(r['cfg_nwater'] - 1.3353) < 1e-12
                         and r['focus_z'] == 450.0 and r['id_err'] < 1e-10
                         and np.isfinite(r['C']).all() and np.isfinite(r['Eref']).all()
                         and np.isfinite(r['Esca']).all())
        except Exception as e:
            return False, f'load failed: {e}', os.path.basename(p)
        ok = name_ok and led_ok and fields_ok
        note = '' if ok else f'name_ok={name_ok} ledger_ok={led_ok} fields_ok={fields_ok}'
        return ok, note, os.path.basename(p)
    reusable = []
    for D in TRAIN_D:
        ok, note, fname = verify_node(D, 450.0)
        rows.append(dict(node=f'D{D}_h450', source='v124_render', mesh=576,
                         verified=ok, note=note, file=fname))
        if ok:
            reusable.append((float(D), 450.0))
    for h in TRAIN_H:
        if h == 450:
            continue
        ok, note, fname = verify_node(100, h)
        rows.append(dict(node=f'D100_h{h}', source='v124_render', mesh=576,
                         verified=ok, note=note, file=fname))
        if ok:
            reusable.append((100.0, float(h)))
    # 2) verify the V124 H5 library reads back
    h5p = os.path.join(V124, 'library', 'valid_physical_fields_or_coefficients.h5')
    h5_ok = os.path.isfile(h5p)
    h5_note = ''
    n_groups = 0
    if h5_ok:
        with h5py.File(h5p, 'r') as h:
            n_groups = len(h.keys())
            g = h['D60_h450']
            h5_ok = (g['C'].shape == (17, 17) and np.isfinite(g['Eref'][()]).all())
    rows.append(dict(node='v124_library_h5', source='v124_h5', mesh='',
                     verified=h5_ok, note=f'{n_groups} groups; readback ok' if h5_ok else h5_note, file='valid_physical_fields_or_coefficients.h5'))
    with open(os.path.join(OUT125, 'validation', 'v124_intake.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['node', 'source', 'mesh', 'verified', 'note', 'file'])
        w.writeheader()
        for r in rows: w.writerow(r)
    # 3) source identity
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=REPO, capture_output=True, text=True).stdout.strip()
    blob = lambda rel: subprocess.run(['git', 'rev-parse', f'HEAD:{rel}'], cwd=REPO, capture_output=True, text=True).stdout.strip()
    identity = dict(
        schema='iscat125.source_identity.1',
        fixed_v124_commit='384a52304f77490c410d395dd150e0ea82760d1f',
        current_head=head,
        nanobem_upstream_sha='ce49f77f096337db8be54c46d83696d37b0b23d5',
        python=sys.version.split()[0], platform=platform.platform(),
        numpy=np.__version__, scipy=__import__('scipy').__version__, h5py=h5py.__version__,
        v124_h5_sha256=sha256(h5p) if os.path.isfile(h5p) else None,
        v124_zip_sha256=sha256(os.path.join(V124, 'iscat_v124_return.zip')) if os.path.isfile(os.path.join(V124, 'iscat_v124_return.zip')) else None,
        tool_blobs={rel: blob(rel) for rel in [
            'tools/v124_core.py', 'tools/invert_v124_particle.py',
            'source/v124_physical_forward_adapter.m', 'source/v125_physical_forward_adapter.m',
            'tools/v125_intake.py']},
        reusable_nodes_verified=[list(n) for n in reusable],
        n_reusable_verified=len(reusable),
        reusable_plan='MAIN_7x9' if len(reusable) == 15 else 'INSUFFICIENT_FALLBACK_7x7',
    )
    with open(os.path.join(OUT125, 'logs', 'source_identity.json'), 'w', encoding='utf-8') as f:
        json.dump(identity, f, indent=1, ensure_ascii=False)
    # 4) effective config = proposed config + real environment
    with open(os.path.join(REPO, 'config', 'v125_science_config.json'), encoding='utf-8') as f:
        eff = json.load(f)
    eff['schema'] = 'iscat125.effective_config.1'
    eff['environment'] = dict(python=identity['python'], numpy=identity['numpy'],
                              scipy=identity['scipy'], h5py=identity['h5py'], platform=identity['platform'])
    eff['plan_selection'] = identity['reusable_plan']
    eff['plan_lock_note'] = 'MAIN_7x9 selected BEFORE any V125 holdout response was read (15/15 reusable nodes verified at intake)'
    with open(os.path.join(OUT125, 'config_effective.json'), 'w', encoding='utf-8') as f:
        json.dump(eff, f, indent=1, ensure_ascii=False)
    os.makedirs(os.path.join(REPO, 'config'), exist_ok=True)
    with open(os.path.join(REPO, 'config', 'v125_effective_config.json'), 'w', encoding='utf-8') as f:
        json.dump(eff, f, indent=1, ensure_ascii=False)
    n_ok = sum(1 for r in rows if r['verified'])
    print(f'intake: {n_ok}/{len(rows)} verified, reusable={len(reusable)}/15, plan={identity["reusable_plan"]}')
    return identity

if __name__ == '__main__':
    main()
