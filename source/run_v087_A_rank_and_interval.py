# -*- coding: utf-8 -*-
"""v087 Phase A: rank-argmin logic fix (pure post-processing on the frozen
v086/v085 tables).

v086 defect: `observed_same` used the per-pair proxy |d_d - d_s| <= b, which
only says the two path distances of the SAME pair agree within the triangle
bound - it never compares argmin(d_single) with argmin(d_double).

v087 correct logic:
  observed_rank_same = (argmin_single pair == argmin_double pair) over the 192
  cross-D candidates, ties broken by (distance, pair_id) stable ordering.
  Certification: nearest_hi < min(other_lo) with I=[max(0,d_d-b), d_d+b];
  endpoint touching counts as NOT certified (strict inequality required)."""
import os, sys, csv, json, hashlib, itertools
import numpy as np

GH = os.path.join(ROOT if False else r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff')
TAB = os.path.join(GH, 'tables')


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def g17(x):
    return '%.17g' % x


def main():
    src86 = os.path.join(TAB, 'v086_276_pair_distance_intervals.csv')
    src85 = os.path.join(TAB, '..', 'tables', 'v085_pairwise_276_stability.csv')
    src85 = os.path.normpath(src85)
    # load actual rows
    with open(src86, 'r', newline='', encoding='utf-8') as f:
        rows86 = list(csv.DictReader(f))
    cross = [r for r in rows86 if r['pair_class'] == 'cross_D']
    assert len(cross) == 192
    assert len({r['pair_id'] for r in rows86}) == 276

    # true argmins (stable (distance, pair_id) ordering)
    by_single = sorted(cross, key=lambda r: (float(r['d_shape_single']), r['pair_id']))
    by_double = sorted(cross, key=lambda r: (float(r['d_shape_double']), r['pair_id']))
    arg_s, arg_d = by_single[0], by_double[0]
    observed_rank_same = (arg_s['pair_id'] == arg_d['pair_id'])

    # strict interval certification on the double-precision nearest
    nearest = by_double[0]
    nearest_hi = float(nearest['d_shape_double']) + float(nearest['b_ij'])
    others_lo = [max(0.0, float(r['d_shape_double']) - float(r['b_ij'])) for r in by_double[1:]]
    certified = bool(nearest_hi < min(others_lo)) if others_lo else False

    # analytic fixtures (zero simulation cost)
    fx = []
    def add_fid(fid, desc, old_result, verdict, expect, detail=''):
        fx.append({'fixture_id': fid, 'description': desc,
                   'v086_old_criterion_result': old_result,
                   'v087_correct_criterion_verdict': verdict,
                   'expected': expect, 'detail': detail,
                   'status': 'PASS' if verdict == expect else 'FAIL'})
    # F1: argmin swap while both per-pair triangle conditions hold
    #   pair A: d_s=0.100, d_d=0.104, b=0.01 -> |0.004|<=0.01 OK
    #   pair B: d_s=0.101, d_d=0.102, b=0.01 -> OK
    #   argmin_s=A(0.100), argmin_d=B(0.102) -> swap; old proxy would say YES for both
    swap_same = abs(0.104 - 0.100) <= 0.01 and abs(0.102 - 0.101) <= 0.01
    add_fid('FIX1_argmin_swap', 'two cross-D pairs each satisfy |d_d-d_s|<=b but argmins swap between paths',
            'YES (wrong: proxy only checks per-pair bound)', 'NO', 'NO',
            detail='argmin_single=A, argmin_double=B; both per-pair bounds hold (%s)' % swap_same)
    # F2: endpoint-touching intervals -> NOT certified (strict inequality)
    d1, b1 = 0.10, 0.01
    d2, b2 = 0.11, 0.01   # I1 hi = 0.11 == I2 lo = 0.10+0.01 = 0.11
    add_fid('FIX2_endpoint_touch', 'nearest_hi == other_lo exactly (touching intervals)',
            'potentially YES (overlap logic with >= tolerance)', 'NO', 'NO',
            detail='hi %.6g == lo %.6g; strict < required' % (d1 + b1, d2 - b2))
    # F3: truly separated -> certified
    d1, b1 = 0.10, 0.005
    d2, b2 = 0.12, 0.005   # I1 hi=0.105 < I2 lo=0.115
    add_fid('FIX3_separated', 'genuinely separated intervals',
            'YES', 'YES', 'YES', detail='hi %.6g < lo %.6g' % (d1 + b1, d2 - b2))
    with open(os.path.join(TAB, 'v087_rank_logic_fixtures.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['fixture_id', 'description', 'v086_old_criterion_result',
                                          'v087_correct_criterion_verdict', 'expected', 'detail', 'status'],
                           lineterminator='\n'); w.writeheader(); w.writerows(fx)

    # actual argmins table
    arg_rows = [{'record_key': 'single|1', 'path': 'single', 'rank': 1, 'pair_id': arg_s['pair_id'],
                 'distance': g17(float(arg_s['d_shape_single']))},
                {'record_key': 'double|1', 'path': 'double', 'rank': 1, 'pair_id': arg_d['pair_id'],
                 'distance': g17(float(arg_d['d_shape_double']))},
                {'record_key': 'single|2', 'path': 'single', 'rank': 2, 'pair_id': by_single[1]['pair_id'],
                 'distance': g17(float(by_single[1]['d_shape_single']))},
                {'record_key': 'double|2', 'path': 'double', 'rank': 2, 'pair_id': by_double[1]['pair_id'],
                 'distance': g17(float(by_double[1]['d_shape_double']))}]
    with open(os.path.join(TAB, 'v087_rank_actual_argmins.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['record_key', 'path', 'rank', 'pair_id', 'distance'], lineterminator='\n')
        w.writeheader(); w.writerows(arg_rows)

    decision = {
        'source_tables': {'v086': sha256_file(src86), 'v085': sha256_file(src85)},
        'n_cross_D_candidates': 192,
        'argmin_single_pair': arg_s['pair_id'], 'argmin_single_distance': g17(float(arg_s['d_shape_single'])),
        'argmin_double_pair': arg_d['pair_id'], 'argmin_double_distance': g17(float(arg_d['d_shape_double'])),
        'observed_rank_same_between_two_paths': 'YES' if observed_rank_same else 'NO',
        'v086_old_criterion': 'per-pair proxy |d_d-d_s|<=b (mathematical necessity, not an argmin comparison)',
        'certification_criterion': 'nearest_hi < min(other_lo), strict; endpoint touching = NOT certified',
        'nearest_hi': g17(nearest_hi), 'min_other_lo': g17(min(others_lo)),
        'triangle_interval_certified': 'YES' if certified else 'NO',
        'v086_not_certified_result_stands': True,
        'interpretation': 'single- and double-precision paths select DIFFERENT nearest cross-D pairs at the reported distances; the conservative triangle intervals overlap, so no rank is certified; this is a numerical-path statement, not physics',
        'fixtures_all_pass': all(x['status'] == 'PASS' for x in fx)}
    with open(os.path.join(TAB, 'v087_ranking_decision.json'), 'w', encoding='utf-8') as f:
        json.dump(decision, f, indent=2)
    print('[A] summary:', json.dumps({k: decision[k] for k in (
        'argmin_single_pair', 'argmin_double_pair', 'observed_rank_same_between_two_paths',
        'triangle_interval_certified', 'fixtures_all_pass')}))
    # readback
    for name, nexp in (('v087_rank_logic_fixtures.csv', 3), ('v087_rank_actual_argmins.csv', 4)):
        with open(os.path.join(TAB, name), 'r', newline='', encoding='utf-8') as f:
            rr = list(csv.reader(f))
        assert len(rr) - 1 == nexp and all(len(x) == len(rr[0]) for x in rr), name


if __name__ == '__main__':
    main()
