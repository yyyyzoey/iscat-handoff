"""V126 intake, budget reservation, and identity checks."""
import csv, hashlib, json, os, platform, subprocess, sys
import numpy as np
import h5py

REPO = r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff'
OUT = os.path.join(REPO, 'results', 'v126')
V125 = os.path.join(REPO, 'results', 'v125')
LIMITS = dict(bem_system_attempts=16, optical_render_attempts=128, synthetic_exposure_events=6000)

def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()

def counters_path():
    return os.path.join(OUT, 'logs', 'budget_counters.json')

def load_counters():
    if os.path.isfile(counters_path()):
        return json.load(open(counters_path()))
    return {k: 0 for k in LIMITS}

def reserve(kind, n=1):
    """Atomic pre-check + reservation BEFORE any budgeted computation."""
    c = load_counters()
    if c[kind] + n > LIMITS[kind]:
        raise RuntimeError(f'BUDGET_EXCEEDED: {kind} {c[kind]}+{n} > {LIMITS[kind]}')
    c[kind] += n
    json.dump(c, open(counters_path(), 'w'), indent=1)
    return c[kind]

def intake():
    os.makedirs(os.path.join(OUT, 'logs'), exist_ok=True)
    rows = []
    tr = os.path.join(V125, 'library', 'v125_Dh_train_fields.h5')
    ho = os.path.join(V125, 'library', 'v125_direct_holdouts.h5')
    ok_tr = os.path.isfile(tr)
    n_nodes = 0
    if ok_tr:
        with h5py.File(tr, 'r') as h:
            n_nodes = len(h.keys())
            for k in list(h.keys())[:3]:
                g = h[k]
                ok = (g['C'].shape == (17, 17) and np.isfinite(g['Eref'][()]).all()
                      and 'wide' in g)
                rows.append(dict(file='v125_Dh_train_fields.h5', node=k, verified=bool(ok), note=''))
    ok_ho = os.path.isfile(ho)
    if ok_ho:
        with h5py.File(ho, 'r') as h:
            for k in h.keys():
                ok = ('at_offset/C' in h[k] and 'wide/Eref' in h[k])
                rows.append(dict(file='v125_direct_holdouts.h5', node=k, verified=bool(ok), note=''))
    rows.append(dict(file='v125_Dh_train_fields.h5', node='FILE', verified=ok_tr,
                     note=f'{n_nodes} nodes; sha256={sha256(tr)[:16]}' if ok_tr else 'missing'))
    with open(os.path.join(OUT, 'validation', 'v125_intake.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['file', 'node', 'verified', 'note'])
        w.writeheader()
        for r in rows: w.writerow(r)
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=REPO, capture_output=True, text=True).stdout.strip()
    identity = dict(schema='iscat126.source_identity.1', fixed_v125_commit='36a231ec8319ae47906664bdc8b54c166727af5a',
                    current_head=head, platform=platform.platform(), python=sys.version.split()[0],
                    numpy=np.__version__,
                    train_h5_sha256=sha256(tr)[:16] if ok_tr else None,
                    n_train_nodes=n_nodes)
    json.dump(identity, open(os.path.join(OUT, 'logs', 'source_identity.json'), 'w'), indent=1)
    print(f'intake: train={n_nodes} nodes ok={ok_tr}, holdouts ok={ok_ho}')
    return identity

if __name__ == '__main__':
    intake()
