# -*- coding: utf-8 -*-
"""v111 audit_attribution: read the REAL v110 attribution source table, verify the
60 exact combination keys, integer count ranges and reproduction relations, then
decompose the 30 old three_bin count differences algebraically:
    H - S = (H - M) + (M - S)
H = historical old three-bin count (v092_summaries60, three_bin_magnitude)
M = current correct three-channel count (accepted full-3bin summaries)
S = current single-160 count (accepted bin160 summaries)
This is a count decomposition, NOT a physical causal contribution; total
differences may cancel. No new optics, no new reference pools/weights/masks."""
import os, sys, csv, json

def rcsv(p):
    with open(p, 'r', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(root, 'analysis')
    an = os.path.join(root, 'analysis')
    src_rows = rcsv(os.path.join(an, 'v110_s60_difference_attribution.csv'))
    issues = []
    if len(src_rows) != 60:
        issues.append('v110 attribution rows=%d != 60' % len(src_rows))
    seen = set()
    for r in src_rows:
        k = (r['representation'], r['group'], r['feature'])
        if k in seen:
            issues.append('duplicate combo key: %s' % (k,))
        seen.add(k)
        for f in ('historical_count', 'recomputed_v092_definition_count',
                  'current_bin160_count', 'current_full3bin_count'):
            v = r.get(f, '')
            if v == '':
                continue
            iv = int(v)
            if not 0 <= iv <= 24:
                issues.append('count out of range: %s %s=%d' % (k, f, iv))
        if r['historical_reproduced'] != 'YES':
            issues.append('reproduction broken: %s' % (k,))

    # accepted current summaries: from the frozen v110 210-table
    summ = rcsv(os.path.join(root, 'analysis', 'v110_summaries210.csv'))
    by = {(r['bins'], r['subset_or_policy'], r['feature']): int(r['consistent_count']) for r in summ}
    s60 = rcsv(os.path.join(an, 'v092_summaries60.csv'))
    hist3 = {(r['subset_or_policy'], r['feature']): int(r['consistent_count'])
             for r in s60 if r['representation'] == 'three_bin_magnitude'}
    if len(hist3) != 30:
        issues.append('historical three_bin rows=%d != 30' % len(hist3))

    decomp_rows = []
    n_identical = n_diff = 0
    for (g, f), H in sorted(hist3.items()):
        M = by.get(('80+160+320', g, f))
        S = by.get(('160', g, f))
        if M is None or S is None:
            issues.append('missing current summary for %s|%s' % (g, f))
            continue
        HS, HM, MS = H - S, H - M, M - S
        ident = (HS == 0)
        n_identical += int(ident)
        n_diff += int(not ident)
        decomposition_ok = (HS == HM + MS)
        if not decomposition_ok:
            issues.append('decomposition broken: %s|%s' % (g, f))
        decomp_rows.append({'record_key': 'three_bin|%s|%s' % (g, f),
                            'group': g, 'feature': f,
                            'H_historical_threebin': H, 'M_current_full3bin': M,
                            'S_current_bin160': S,
                            'H_minus_S': HS, 'H_minus_M': HM, 'M_minus_S': MS,
                            'decomposition_identity_ok': 'YES' if decomposition_ok else 'NO',
                            'total_diff_identical_to_bin160': 'YES' if ident else 'NO',
                            'interpretation': ('total count difference zero: component terms may cancel'
                                               if ident else
                                               'nonzero total: (H-M) = implementation-object difference of the '
                                               'two specified three-channel realizations; (M-S) = channel-count '
                                               'comparison under the fixed current definition'),
                            'causal_claim': 'NONE (count algebra, not causal contribution)'})
    w_fields = list(decomp_rows[0].keys())
    with open(os.path.join(out_dir, 'v111_threebin_decomposition30.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=w_fields, lineterminator='\n')
        w.writeheader()
        w.writerows(decomp_rows)
    summary = {'decomposition_rows': len(decomp_rows),
               'identity_ok_all': not any(r['decomposition_identity_ok'] == 'NO' for r in decomp_rows),
               'total_diff_zero_groups': n_identical,
               'total_diff_nonzero_groups': n_diff,
               'note': 'H-S = (H-M) + (M-S) count algebra; no causal or precision attribution; '
                       'H-M reflects the two specified three-channel implementations (including the '
                       'historical 6-cached-states C400 triple-copy defect, reproduced but NOT endorsed); '
                       'M-S is the fixed-definition channel comparison',
               'issues': issues}
    with open(os.path.join(out_dir, 'v111_threebin_decomposition_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print('AUDIT_ATTRIBUTION_OK decomposed=%d identical=%d nonzero=%d issues=%d'
          % (len(decomp_rows), n_identical, n_diff, len(issues)))
    return 0 if not issues and len(decomp_rows) == 30 else 2

if __name__ == '__main__':
    sys.exit(main())
