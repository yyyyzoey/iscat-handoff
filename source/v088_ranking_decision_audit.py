# -*- coding: utf-8 -*-
"""v088 Phase B2: ranking decision audit with truly-executed fixtures.

Fixes two v087 defects: (i) the JSON interpretation text contradicted its own
argmin result (templated from booleans now); (ii) FIX2 endpoint-touching was
not actually touching in binary floating point - fixtures are now executed as
real function calls using Fraction arithmetic for exact endpoint equality."""
import os, sys, csv, json, hashlib
from fractions import Fraction

GH = os.path.join(r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff')
TAB = os.path.join(GH, 'tables')


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def rank_candidates(cands):
    """cands: list of dicts with d_single, d_double, b, pair_id.
    Returns (argmin_single, argmin_double, certified_double, nearest) using
    stable (distance, pair_id) ordering and strict interval certification."""
    by_s = sorted(cands, key=lambda r: (r['d_single'], r['pair_id']))
    by_d = sorted(cands, key=lambda r: (r['d_double'], r['pair_id']))
    nearest = by_d[0]
    nearest_hi = nearest['d_double'] + nearest['b']
    others_lo = [max(Fraction(0), r['d_double'] - r['b']) for r in by_d[1:]]
    certified = all(nearest_hi < lo for lo in others_lo) if others_lo else False
    return by_s[0], by_d[0], certified, nearest, by_d


def observed_rank_same(by_s, by_d):
    return by_s['pair_id'] == by_d['pair_id']


def main():
    # load the frozen v086 276 rows
    with open(os.path.join(TAB, 'v086_276_pair_distance_intervals.csv'), 'r', newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    cross = [r for r in rows if r['pair_class'] == 'cross_D']
    assert len(cross) == 192
    cands = [{'pair_id': r['pair_id'],
              'd_single': float(r['d_shape_single']),
              'd_double': float(r['d_shape_double']),
              'b': float(r['b_ij'])} for r in cross]
    arg_s, arg_d, certified, nearest, by_d = rank_candidates(cands)
    same = observed_rank_same(arg_s, arg_d)

    # ---- fixtures executed as real function calls ----
    fx = []
    def run_case(cands_):
        a_s, a_d, cert, near, _ = rank_candidates(cands_)
        return a_s, a_d, cert

    # F1: argmin swap, both per-pair triangle bounds hold
    f1 = [{'pair_id': 'A', 'd_single': Fraction(100, 1000), 'd_double': Fraction(104, 1000), 'b': Fraction(10, 1000)},
          {'pair_id': 'B', 'd_single': Fraction(101, 1000), 'd_double': Fraction(102, 1000), 'b': Fraction(10, 1000)}]
    a_s, a_d, _ = run_case(f1)
    swap = a_s['pair_id'] != a_d['pair_id']
    bounds_hold = all(abs(c['d_double'] - c['d_single']) <= c['b'] for c in f1)
    fx.append({'fixture_id': 'F1', 'description': 'argmin swap while both per-pair |d_d-d_s|<=b hold',
               'executed': 'YES', 'observed': 'argmin_single=%s argmin_double=%s bounds_hold=%s' % (
                   a_s['pair_id'], a_d['pair_id'], bounds_hold),
               'correct_verdict': 'OBSERVED_SAME=NO (swap)', 'status': 'PASS' if (swap and bounds_hold) else 'FAIL'})
    # F2: exact endpoint touching (Fraction arithmetic - no binary fp drift)
    f2 = [{'pair_id': 'N', 'd_single': Fraction(1, 10), 'd_double': Fraction(1, 10), 'b': Fraction(1, 100)},
          {'pair_id': 'M', 'd_single': Fraction(12, 100), 'd_double': Fraction(12, 100), 'b': Fraction(1, 100)}]
    a_s, a_d, cert2 = run_case(f2)
    touch = (a_d['d_double'] + a_d['b']) == max(Fraction(0), f2[1]['d_double'] - f2[1]['b'])
    fx.append({'fixture_id': 'F2', 'description': 'exact endpoint touching (nearest_hi == other_lo exactly)',
               'executed': 'YES', 'observed': 'touching=%s certified=%s' % (touch, cert2),
               'correct_verdict': 'RANK_CERTIFIED=NO (strict < required)', 'status': 'PASS' if (touch and not cert2) else 'FAIL'})
    # F3: genuinely separated
    f3 = [{'pair_id': 'N', 'd_single': Fraction(1, 10), 'd_double': Fraction(1, 10), 'b': Fraction(5, 1000)},
          {'pair_id': 'M', 'd_single': Fraction(12, 100), 'd_double': Fraction(12, 100), 'b': Fraction(5, 1000)}]
    a_s, a_d, cert3 = run_case(f3)
    fx.append({'fixture_id': 'F3', 'description': 'genuinely separated intervals',
               'executed': 'YES', 'observed': 'certified=%s' % cert3,
               'correct_verdict': 'RANK_CERTIFIED=YES', 'status': 'PASS' if cert3 else 'FAIL'})
    # F4: overlapping intervals (real-data-like)
    f4 = [{'pair_id': 'N', 'd_single': Fraction(13326434264817294, 10 ** 17), 'd_double': Fraction(13326434264817294, 10 ** 17), 'b': Fraction(29981976034319247, 10 ** 20)},
          {'pair_id': 'M', 'd_single': Fraction(13335327361218305, 10 ** 17), 'd_double': Fraction(13335327361218305, 10 ** 17), 'b': Fraction(10893800248403135, 10 ** 20)}]
    a_s, a_d, cert4 = run_case(f4)
    fx.append({'fixture_id': 'F4', 'description': 'overlapping intervals (real-data-like geometry)',
               'executed': 'YES', 'observed': 'certified=%s' % cert4,
               'correct_verdict': 'RANK_CERTIFIED=NO', 'status': 'PASS' if not cert4 else 'FAIL'})
    with open(os.path.join(TAB, 'v088_rank_fixtures_validated.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['fixture_id', 'description', 'executed', 'observed',
                                          'correct_verdict', 'status'], lineterminator='\n')
        w.writeheader(); w.writerows(fx)

    # ---- decision JSON templated from booleans ----
    decision = {
        'source_table': sha256_file(os.path.join(TAB, 'v086_276_pair_distance_intervals.csv')),
        'n_cross_D_candidates': 192,
        'argmin_single_pair': arg_s['pair_id'],
        'argmin_single_distance': '%.17g' % arg_s['d_single'],
        'argmin_double_pair': arg_d['pair_id'],
        'argmin_double_distance': '%.17g' % arg_d['d_double'],
        'observed_rank_same_between_two_paths': 'YES' if same else 'NO',
        'certification_criterion': 'nearest_hi < min(other_lo), strict (Fraction-exact fixture F2)',
        'triangle_interval_certified': 'YES' if certified else 'NO',
        'nearest_hi': '%.17g' % float(nearest['d_double'] + nearest['b']),
        'min_other_lo': '%.17g' % float(max(Fraction(0), by_d[1]['d_double'] - by_d[1]['b'])),
        'fixtures_all_pass': all(x['status'] == 'PASS' for x in fx),
    }
    # interpretation TEMPLATED from the actual booleans (v087 defect: hardcoded text)
    if same and not certified:
        decision['interpretation'] = ('Both numerical paths select the SAME nearest cross-D pair (%s), '
                                      'but the conservative triangle intervals overlap, so the ranking is NOT '
                                      'certified by the reported intervals; this is a numerical-path statement, not physics.') % arg_d['pair_id']
    elif same and certified:
        decision['interpretation'] = 'Both paths select the same nearest pair AND the intervals certify the ranking.'
    elif (not same) and not certified:
        decision['interpretation'] = ('The two paths select DIFFERENT nearest cross-D pairs (%s vs %s) and the '
                                      'intervals overlap - the ranking is neither observed-stable nor certified.') % (
            arg_s['pair_id'], arg_d['pair_id'])
    else:
        decision['interpretation'] = 'Paths differ but intervals certify; unexpected combination - inspect.'
    with open(os.path.join(TAB, 'v088_rank_decision_corrected.json'), 'w', encoding='utf-8') as f:
        json.dump(decision, f, indent=2)
    # readback
    for name, nexp in (('v088_rank_fixtures_validated.csv', 4),):
        with open(os.path.join(TAB, name), 'r', newline='', encoding='utf-8') as f:
            rr = list(csv.reader(f))
        assert len(rr) - 1 == nexp and all(len(x) == len(rr[0]) for x in rr), name
        assert len({x[0] for x in rr[1:]}) == nexp, name
    print('[B2] summary:', json.dumps({k: decision[k] for k in (
        'observed_rank_same_between_two_paths', 'triangle_interval_certified', 'fixtures_all_pass')}))
    assert decision['fixtures_all_pass']


if __name__ == '__main__':
    main()
