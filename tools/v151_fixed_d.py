"""V151: strict fixed-D profiles with atomic budget."""
from __future__ import annotations
import argparse, csv, hashlib, json, os, sqlite3, sys, time
from pathlib import Path
import numpy as np, h5py
sys.path.insert(0, str(Path(__file__).resolve().parent))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--cases', nargs='+', default=['ANON_01','ANON_02','ANON_03','ANON_04'])
    ap.add_argument('--max-total-calls', type=int, default=70000)
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(repo / 'tools'))
    from v142_model import construct
    from scipy.optimize import least_squares
    legacy, cand, _ = construct(repo)
    model_id = cand.model_id

    db_path = out / 'v151_budget.sqlite'
    if db_path.exists(): db_path.unlink()
    con = sqlite3.connect(str(db_path))
    con.execute('CREATE TABLE events(op TEXT PRIMARY KEY, reserved INT, actual INT, state TEXT, payload TEXT)')
    con.commit()
    total_used = [0]

    def reserve_and_finish(op, cap, actual_used):
        con.execute('INSERT INTO events VALUES(?,?,?,?,?)', (op, cap, actual_used, 'COMPLETED' if actual_used > 0 else 'FAILED', ''))
        con.commit()
        total_used[0] += actual_used

    camera = repo / 'results/v143/validation/camera_pilot/conditional_camera_arrays.h5'
    from v146_fit_saved_camera import camera_events
    events = camera_events(camera, repo / 'results/v143/validation/camera_pilot', [1000, 10000, 100000], 2.0)
    from collections import defaultdict
    groups = defaultdict(list)
    for ev in events:
        anon = ev['label'].rsplit('_', 1)[0]
        groups[(ev['B'], anon)].append(ev)

    all_fixed = []
    case_summary = {}
    eps = 0.0015811481066672155

    for case in a.cases:
        case_entries = []
        for (B, anon), evs in sorted(groups.items()):
            if anon != case: continue
            Ys = [e['Y'] for e in evs]; Vs = [e['V'] for e in evs]
            Yi = np.stack(Ys); Vi = np.stack(Vs)
            Vbar = 1.0 / np.sum(1.0 / Vi, axis=0)
            Ybar = Vbar * np.sum(Yi / Vi, axis=0)

            # candidate D from V150 joint
            v150_path = repo / 'results/v150/all_results.json'
            cand_D = 100.0
            if v150_path.is_file():
                v150j = json.loads(v150_path.read_text(encoding='utf-8'))
                for r in v150j.get('joint', []):
                    if r.get('anon') == anon and r.get('B') == B and r.get('joint_D'):
                        cand_D = r['joint_D']; break

            Ds = sorted(set([30., 50., 75., 100., 125., 150., 175., 200., round(float(cand_D), 3)]))

            for D in Ds:
                if total_used[0] >= a.max_total_calls:
                    case_entries.append(dict(B=B, fixed_D=D, status='BUDGET_EXHAUSTED'))
                    break
                op = f'V151FIX_{B}_{anon}_{D:.3f}'
                used = 0; results = []
                start_hs = [350., 400., 450., 500., 550.]
                for h0 in start_hs:
                    if used >= 400: break
                    x0 = [h0, 0., 0.]
                    def res(p):
                        nonlocal used
                        used += 1
                        th = (D, float(p[0]), float(p[1]), float(p[2]))
                        Cm = cand.forward(th).score_C
                        return (Cm - Ybar).ravel()
                    try:
                        r = least_squares(res, x0, bounds=([350., -500., -500.], [550., 500., 500.]),
                            max_nfev=90, x_scale=[50., 140., 140.], ftol=1e-10, xtol=1e-10, gtol=1e-10)
                        th_final = (D, float(r.x[0]), float(r.x[1]), float(r.x[2]))
                        assert abs(th_final[0] - D) <= 1e-10
                        Cm = cand.forward(th_final).score_C
                        Q = float(np.sum((Cm - Ybar) ** 2))
                        results.append(dict(target_D=D, h=float(r.x[0]), x=float(r.x[1]), y=float(r.x[2]),
                            Q=Q, success=bool(r.success), nfev=int(r.nfev), fixed_D_ok=True))
                    except Exception as exc:
                        results.append(dict(target_D=D, h=h0, status='EXCEPTION', error=repr(exc)[:120]))
                reserve_and_finish(op, 400, used)
                ok_results = [r for r in results if 'Q' in r]
                best = min(ok_results, key=lambda r: r['Q']) if ok_results else None
                entry = dict(B=B, anon=anon, fixed_D=D,
                    best_Q=best['Q'] if best else None,
                    best_theta=[D, best['h'], best['x'], best['y']] if best else None,
                    n_starts=len(results), n_success=sum(1 for r in results if r.get('success')),
                    used=used)
                case_entries.append(entry); all_fixed.append(entry)

            if total_used[0] >= a.max_total_calls: break

        losses = [e['best_Q'] for e in case_entries if e.get('best_Q') is not None]
        minQ = min(losses) if losses else None
        compat = [e['fixed_D'] for e in case_entries if e.get('best_Q') is not None and minQ is not None and e['best_Q'] <= minQ + eps]
        case_summary[case] = dict(n_points=len(case_entries), min_Q=minQ, epsilon_dev=eps,
            compatible_witnesses_D=compat, non_unique_under_dev_eps=len(compat) > 1,
            total_used_for_case=sum(e.get('used', 0) for e in case_entries))
        print(case, 'points=', len(case_entries), 'min_Q=', minQ, 'compat=', compat, flush=True)

    (out / 'fixed_D_summary.json').write_text(
        json.dumps(dict(cases=case_summary, total_calls=total_used[0], limit=a.max_total_calls),
                   indent=1, ensure_ascii=False), encoding='utf-8')
    with (out / 'fixed_D_witnesses.csv').open('w', newline='', encoding='utf-8') as f:
        if all_fixed:
            w = csv.DictWriter(f, fieldnames=list(all_fixed[0].keys()))
            w.writeheader()
            for r in all_fixed:
                w.writerow({k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in r.items()})
    con.close()
    print(f'V151_FIXED_D done total_calls={total_used[0]}/{a.max_total_calls}')

if __name__ == '__main__':
    main()
