# -*- coding: utf-8 -*-
"""v111 validate_decisions: strict comparison helper for computed decision
records. This is NOT a MATLAB distance solver: it judges already-computed rows
against independently computed expected records through the released validation
entry (same functions the injection tests use). Full-field: identity, query
metadata + SHA, reference pool members/size, first/second candidates and
distances/D, near_min members/D-set/size/tau, same/cross/margin, final decision."""
import os, sys, csv, json, math

DECISION_FIELDS = ['nearest_candidate', 'nearest_label_D',
                   'same_D_nearest_dist', 'cross_D_nearest_dist',
                   'min_cross_minus_min_same', 'model_label_consistent']
NUMERIC_FIELDS = ['nearest_dist', 'second_dist', 'same_D_nearest_dist',
                  'cross_D_nearest_dist', 'min_cross_minus_min_same', 'tie_threshold']
EXACT_FIELDS = ['nearest_candidate', 'nearest_label_D', 'second_candidate', 'second_label_D',
                'near_min_set', 'near_min_D_set', 'tied_set_size', 'tie_across_D', 'final_decision']

def rcsv(p):
    with open(p, 'r', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def finite_diff(a, b):
    try:
        fa, fb = float(a), float(b)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(fa) and math.isfinite(fb)):
        return None
    return abs(fa - fb)

def validate_row(rec, expected):
    issues = []
    required = DECISION_FIELDS + ['nearest_dist', 'second_dist', 'final_decision', 'tie_threshold',
                                  'near_min_set', 'near_min_D_set', 'tied_set_size', 'tie_across_D',
                                  'reference_pool', 'reference_pool_size', 'source_sha256', 'record_key']
    for f in required:
        if f not in rec or rec[f] in (None, ''):
            issues.append('missing field %s' % f)
    for f in NUMERIC_FIELDS:
        try:
            fv = float(rec.get(f, ''))
        except (TypeError, ValueError):
            issues.append('unparsable %s' % f)
            continue
        if not math.isfinite(fv):
            issues.append('non-finite %s' % f)
    if issues:
        return issues
    if rec['record_key'] != expected['record_key']:
        issues.append('key mismatch')
        return issues
    if sorted(str(rec['reference_pool']).split('|')) != sorted(str(expected['reference_pool']).split('|')):
        issues.append('reference pool mismatch')
    if str(rec['reference_pool_size']) != str(expected['reference_pool_size']):
        issues.append('reference pool size mismatch')
    if str(rec.get('source_sha256', '')) != str(expected.get('source_sha256', '')):
        issues.append('source_sha256 mismatch')
    for f in DECISION_FIELDS:
        a, b = rec.get(f, ''), expected.get(f, '')
        d = finite_diff(a, b)
        if d is None:
            if str(a) != str(b):
                issues.append('%s mismatch: %r vs %r' % (f, a, b))
        elif not d < 1e-12:
            issues.append('%s diff %g >= 1e-12' % (f, d))
    for f in ['nearest_dist', 'second_dist', 'tie_threshold']:
        a, b = rec.get(f, ''), expected.get(f, '')
        if b == '':
            continue
        d = finite_diff(a, b)
        if d is None or not d < 1e-12:
            issues.append('%s mismatch' % f)
    for f in EXACT_FIELDS:
        if str(rec.get(f, '')) != str(expected.get(f, '')):
            issues.append('%s mismatch' % f)
    return issues

def validate_table(recs, expected_by_key):
    """Order-insensitive; catches duplicate/extra/missing keys on the REAL table
    (no dict conversion of the production side that could mask key defects)."""
    issues = []
    seen = {}
    for r in recs:
        k = r.get('record_key')
        if k in seen:
            issues.append('duplicate record_key: %s' % k)
        seen[k] = r
    for k in expected_by_key:
        if k not in seen:
            issues.append('missing record_key: %s' % k)
    for k in seen:
        if k not in expected_by_key:
            issues.append('extra record_key: %s' % k)
    for k, r in seen.items():
        if k in expected_by_key:
            issues.extend('row %s: %s' % (k, m) for m in validate_row(r, expected_by_key[k]))
    return issues

def main():
    """CLI: validate_decisions.py --production PROD.csv --expected EXPECTED.json|CSV [--out report.json]"""
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--production', required=True)
    ap.add_argument('--expected', required=True)
    ap.add_argument('--out', default='')
    args = ap.parse_args()
    prod = rcsv(args.production)
    if args.expected.endswith('.json'):
        expected_rows = json.load(open(args.expected, encoding='utf-8'))
    else:
        expected_rows = rcsv(args.expected)
    expected_by_key = {r['record_key']: r for r in expected_rows}
    issues = validate_table(prod, expected_by_key)
    report = {'production': args.production, 'expected': args.expected,
              'production_rows': len(prod), 'expected_rows': len(expected_rows),
              'issue_count': len(issues), 'accepted': len(issues) == 0,
              'sample_issues': issues[:20]}
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2)[:600])
    return 0 if len(issues) == 0 else 2

if __name__ == '__main__':
    sys.exit(main())
