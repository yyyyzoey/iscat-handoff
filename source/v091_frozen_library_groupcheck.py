# -*- coding: utf-8 -*-
"""v091 Phase B: leave-group nuisance examination of the frozen 24-state demo
simulation library (pure algebra on existing MATs; zero new physics).

Three pre-registered scenarios (query attribute excluded from the reference
pool; pool = 12 states, 4 per D):
  amplitude: query a in {5,20}, references = other amplitude's 12 states
  focus:     query zf in {450,550}, references = other zf's 12 states
  motion:    query type in {M200,M400}, references = other type's 12 states
Three fixed features (reported separately, no weight learning):
  ROI_L2_log_ratio          |log A_i - log A_j|
  magnitude_pattern_symmetric  2||v_i-v_j||/(A_i+A_j)
  unit_magnitude_shape      ||v_i/A_i - v_j/A_j||
216 query records + 9 summaries. Count-based reading only: NO accuracy,
RMSE, FPR, detectability or identifiability claims."""
import os, sys, csv, json, hashlib
import numpy as np
from scipy.io import loadmat

GH = os.path.join(r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff')
TAB = os.path.join(GH, 'tables')
NUM = os.path.join(GH, 'numeric')
ALL24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
         for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)]
CACHED = {'D30_zf450_M400_a5': 'v083_fullROI_double_C400_D30_zf450_M400_a5.mat',
          'D30_zf550_M400_a5': 'v083_fullROI_double_C400_D30_zf550_M400_a5.mat',
          'D60_zf450_M400_a5': 'v083_fullROI_double_C400_D60_zf450_M400_a5.mat',
          'D100_zf450_M200_a20': 'v083_fullROI_double_C400_D100_zf450_M200_a20.mat',
          'D30_zf550_M400_a20': 'v084_double_C400_D30_zf550_M400_a20.mat',
          'D60_zf450_M400_a20': 'v084_double_C400_D60_zf450_M400_a20.mat'}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def g17(x):
    return '%.17g' % x


def parse(key):
    p = key.split('_')
    return {'D': int(p[0][1:]), 'zf': int(p[1][2:]), 'type': p[2], 'a': int(p[3][1:])}


def main():
    # identity readback against the frozen v085 ledger
    ledger = {}
    with open(os.path.join(TAB, 'v085_double_maps24_status.csv'), 'r', newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            ledger[r['case_id']] = r['map_sha256']
    vmaps, sha_ok = {}, 0
    for key in ALL24:
        fn = CACHED.get(key, 'C400_double_%s.mat' % key)
        p = os.path.join(NUM, fn)
        m = loadmat(p)
        C = np.asarray(m['C400_double'], dtype=np.complex128)
        cid = str(m['case_id'].flatten()[0])
        assert cid == key and C.shape == (41, 41)
        if sha256_file(p) == ledger[key]:
            sha_ok += 1
        vmaps[key] = np.abs(C)          # v = |C400|
    assert sha_ok == 24, 'SHA identity failed'
    # common spatial set: all 1681 pixels (verified in v085/v090)
    M = np.ones((41, 41), dtype=bool)

    feats = {}
    for key in ALL24:
        v = vmaps[key][M]
        A = float(np.linalg.norm(v))
        if A == 0 or not np.isfinite(A):
            raise RuntimeError('zero/non-finite norm for %s' % key)
        feats[key] = {'A': A, 'v': v, 'unit': v / A,
                      'meta': parse(key)}
    scenarios = {
        'amplitude': lambda q, r: feats[q]['meta']['a'] != feats[r]['meta']['a'],
        'focus': lambda q, r: feats[q]['meta']['zf'] != feats[r]['meta']['zf'],
        'motion': lambda q, r: feats[q]['meta']['type'] != feats[r]['meta']['type'],
    }

    def distances(qi, rj):
        fq, fr = feats[qi], feats[rj]
        d1 = abs(np.log(fq['A']) - np.log(fr['A']))
        d2 = 2.0 * float(np.linalg.norm(fq['v'] - fr['v'])) / (fq['A'] + fr['A'])
        d3 = float(np.linalg.norm(fq['unit'] - fr['unit']))
        return d1, d2, d3

    qrows = []
    summaries = []
    for scenario, excl in scenarios.items():
        per_label = {'consistent': 0, 'inconsistent': 0, 'tied_across_D': 0}
        per_feat_ties = {1: 0, 2: 0, 3: 0}
        for qi in ALL24:
            refs = [rj for rj in ALL24 if rj != qi and excl(qi, rj)]
            assert len(refs) == 12, (scenario, qi, len(refs))
            dists = {rj: distances(qi, rj) for rj in refs}
            qD = feats[qi]['meta']['D']
            for fi, fname in ((1, 'ROI_L2_log_ratio'), (2, 'magnitude_pattern_symmetric'),
                              (3, 'unit_magnitude_shape')):
                ordered = sorted(refs, key=lambda rj: (dists[rj][fi - 1], rj))
                first, second = ordered[0], ordered[1]
                same_D = [rj for rj in refs if feats[rj]['meta']['D'] == qD]
                cross_D = [rj for rj in refs if feats[rj]['meta']['D'] != qD]
                min_same = min(dists[rj][fi - 1] for rj in same_D)
                min_cross = min(dists[rj][fi - 1] for rj in cross_D)
                label = first.split('_')[0][1:]
                tie = (dists[first][fi - 1] == dists[second][fi - 1])
                labelD1 = first.split('_')[0][1:]
                labelD2 = second.split('_')[0][1:]
                tied_across_D = tie and (labelD1 != labelD2)
                consistent = (label == str(qD))
                per_label['consistent' if consistent else
                          ('tied_across_D' if tied_across_D else 'inconsistent')] += \
                    1 if (consistent or not tied_across_D) else 0
                if tied_across_D:
                    per_label['tied_across_D'] += 0  # counted above
                qrows.append({
                    'record_key': '%s|%s|q=%s' % (scenario, fname, qi),
                    'scenario': scenario, 'feature': fname, 'query': qi,
                    'reference_pool': '|'.join(sorted(refs)),
                    'pool_size': 12,
                    'nearest_candidate': first, 'nearest_dist': g17(dists[first][fi - 1]),
                    'second_candidate': second, 'second_dist': g17(dists[second][fi - 1]),
                    'nearest_label_D': label,
                    'same_D_nearest_dist': g17(min_same), 'cross_D_nearest_dist': g17(min_cross),
                    'min_cross_minus_min_same': g17(min_cross - min_same),
                    'tie_with_second': 'YES' if tie else 'NO',
                    'tie_across_D': 'YES' if tied_across_D else 'NO',
                    'model_label_consistent': 'YES' if consistent else 'NO',
                    'status': 'EVALUATED'})
        # summary per scenario per feature
        for fi, fname in ((1, 'ROI_L2_log_ratio'), (2, 'magnitude_pattern_symmetric'),
                          (3, 'unit_magnitude_shape')):
            rows = [r for r in qrows if r['scenario'] == scenario and r['feature'] == fname]
            summaries.append({
                'record_key': '%s|%s' % (scenario, fname), 'scenario': scenario, 'feature': fname,
                'n_queries': 24,
                'label_consistent_count': sum(1 for r in rows if r['model_label_consistent'] == 'YES'),
                'label_inconsistent_count': sum(1 for r in rows if r['model_label_consistent'] == 'NO'
                                                and r['tie_across_D'] == 'NO'),
                'tie_across_D_count': sum(1 for r in rows if r['tie_across_D'] == 'YES'),
                'reading': 'in-sample geometry screen with leave-group references; NOT accuracy/detectability'})
    with open(os.path.join(TAB, 'v091_leavegroup_216.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(qrows[0].keys()), lineterminator='\n')
        w.writeheader(); w.writerows(qrows)
    with open(os.path.join(TAB, 'v091_leavegroup_summary9.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['record_key'] + [k for k in summaries[0].keys() if k != 'record_key'], lineterminator='\n')
        w.writeheader(); w.writerows(summaries)
    # readback
    for name, nexp in (('v091_leavegroup_216.csv', 216), ('v091_leavegroup_summary9.csv', 9)):
        with open(os.path.join(TAB, name), 'r', newline='', encoding='utf-8') as f:
            rr = list(csv.reader(f))
        assert len(rr) - 1 == nexp and all(len(x) == len(rr[0]) for x in rr), name
        assert len({x[0] for x in rr[1:]}) == nexp, name
    print('[B] summary:', json.dumps({'queries': len(qrows), 'summaries': len(summaries),
                                      'sha_ok': sha_ok}))
    for s in summaries:
        print('  %-9s %-28s consistent=%2d inconsistent=%2d tied=%d' % (
            s['scenario'], s['feature'], s['label_consistent_count'],
            s['label_inconsistent_count'], s['tie_across_D_count']))


if __name__ == '__main__':
    main()
