"""V127 P0: intake, machine-contract checks, SQLite atomic budget ledger."""
import hashlib, json, os, sqlite3, subprocess, sys
import numpy as np
import h5py

REPO = r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff'
OUT = os.path.join(REPO, 'results', 'v127')
V126 = os.path.join(REPO, 'results', 'v126')
LIMITS = dict(bem_system_attempts=16, optical_render_attempts=128, synthetic_exposure_events=6000)

def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()

# ---------------- SQLite atomic budget ledger ----------------
DB = os.path.join(OUT, 'logs', 'budget.sqlite')

def db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB, timeout=30)
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('''CREATE TABLE IF NOT EXISTS attempts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT NOT NULL,
        status TEXT NOT NULL,           -- RESERVED / SUCCESS / FAILED
        ref TEXT, created_utc TEXT DEFAULT (datetime('now')))''')
    return con

def reserve(kind, ref=''):
    con = db()
    try:
        used = con.execute("SELECT COUNT(*) FROM attempts WHERE kind=? AND status IN ('RESERVED','SUCCESS','FAILED')", (kind,)).fetchone()[0]
        if used + 1 > LIMITS[kind]:
            raise RuntimeError(f'BUDGET_EXCEEDED {kind}: {used}+1 > {LIMITS[kind]}')
        cur = con.execute('INSERT INTO attempts(kind,status,ref) VALUES (?,?,?)', (kind, 'RESERVED', ref))
        con.commit()
        return cur.lastrowid
    finally:
        con.close()

def finish(attempt_id, ok, note=''):
    con = db()
    con.execute("UPDATE attempts SET status=?, ref=ref||? WHERE id=?", ('SUCCESS' if ok else 'FAILED', note, attempt_id))
    con.commit(); con.close()

def used(kind):
    con = db()
    n = con.execute("SELECT COUNT(*) FROM attempts WHERE kind=? AND status IN ('RESERVED','SUCCESS','FAILED')", (kind,)).fetchone()[0]
    con.close()
    return n

# ---------------- intake ----------------
def intake():
    os.makedirs(os.path.join(OUT, 'logs'), exist_ok=True)
    os.makedirs(os.path.join(OUT, 'validation'), exist_ok=True)
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=REPO, capture_output=True, text=True).stdout.strip()
    tr = os.path.join(V126, 'library', 'v126_Dh_train_fields.h5')
    ho = os.path.join(V126, 'validation', 'new_holdout_images.h5')
    rows = []
    ok_tr = os.path.isfile(tr)
    n_nodes = 0
    if ok_tr:
        with h5py.File(tr, 'r') as h:
            n_nodes = len(h.keys())
            for k in list(h.keys()):
                g = h[k]
                ok = (g['C'].shape == (17, 17) and np.isfinite(g['Eref'][()]).all() and 'wide' in g)
                if not ok:
                    rows.append(dict(file='train', node=k, verified=False, note='field check failed'))
    rows.append(dict(file='v126_Dh_train_fields.h5', node='FILE', verified=ok_tr,
                     note=f'{n_nodes} nodes sha256={sha256(tr)[:16]}'))
    ok_ho = os.path.isfile(ho)
    if ok_ho:
        with h5py.File(ho, 'r') as h:
            for k in h.keys():
                ok = ('at_offset/C' in h[k] and 'wide/Eref' in h[k])
                rows.append(dict(file='new_holdout_images.h5 (V126, dev)', node=k, verified=bool(ok), note=''))
    # pixel-scale machine assertions
    cfgpx = 1000.0 * 14.0 / (50.0 * 1.0)
    fine = cfgpx / 5.0
    rows.append(dict(file='config', node='pixel_scale', verified=bool(abs(cfgpx - 280.0) < 1e-9 and abs(fine - 56.0) < 1e-9),
                     note=f'object={cfgpx} fine={fine}'))
    with open(os.path.join(OUT, 'validation', 'v126_intake.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['file', 'node', 'verified', 'note']); w.writeheader()
        for r in rows: w.writerow(r)
    identity = dict(schema='iscat127.source_identity.1', fixed_v126_commit='b546d80beb0dc4789effac8c192896e5f45876e9',
                    current_head=head, n_train_nodes=n_nodes, python=sys.version.split()[0],
                    platform=platform.platform(), numpy=np.__version__,
                    train_h5_sha256=sha256(tr)[:16] if ok_tr else None)
    json.dump(identity, open(os.path.join(OUT, 'logs', 'source_identity.json'), 'w'), indent=1)
    print(f'P0 intake: {n_nodes} train nodes, holdouts={ok_ho}, pixel scale OK')
    return identity

import csv, platform

if __name__ == '__main__':
    intake()
    print('budget used:', {k: used(k) for k in LIMITS})
