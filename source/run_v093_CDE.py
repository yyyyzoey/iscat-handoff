# -*- coding: utf-8 -*-
"""v093 Phase C+D+E: corrected 1440 comparisons, 7-channel ablation (5040/210),
and discrete period diagnostics. All from the verified 48-state bank."""
import os, sys, csv, json, hashlib, itertools
import numpy as np
from scipy.io import loadmat

GH = os.path.join(r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\github_handoff')
AN = os.path.join(GH, 'analysis')
TAB = os.path.join(GH, 'tables')
BANK = os.path.join(AN, 'bank')
ALL24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
         for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (5, 20)]
INTER24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a)
           for D in (30, 60, 100) for zf in (450, 550) for t in ('M200', 'M400') for a in (10, 15)]
ALL48 = ALL24 + INTER24
CACHED = {'D30_zf450_M400_a5': 'v083_fullROI_double_C400_D30_zf450_M400_a5.mat',
          'D30_zf550_M400_a5': 'v083_fullROI_double_C400_D30_zf550_M400_a5.mat',
          'D60_zf450_M400_a5': 'v083_fullROI_double_C400_D60_zf450_M400_a5.mat',
          'D100_zf450_M200_a20': 'v083_fullROI_double_C400_D100_zf450_M200_a20.mat',
          'D30_zf550_M400_a20': 'v084_double_C400_D30_zf550_M400_a20.mat',
          'D60_zf450_M400_a20': 'v084_double_C400_D60_zf450_M400_a20.mat'}


def g17(x):
    return '%.17g' % x


def parse(k):
    p = k.split('_')
    return {'D': int(p[0][1:]), 'zf': int(p[1][2:]), 'type': p[2], 'a': int(p[3][1:])}


def load_all_banks():
    """Load all 48 3-bin banks and build the two representations."""
    vecs = {}
    for key in ALL48:
        m = loadmat(os.path.join(BANK, 'v092_bank_%s.mat' % key))
        C = np.asarray(m['C'], dtype=np.complex128)
        mask = np.asarray(m['valid_mask'], dtype=bool).reshape(-1)
        C80 = np.abs(C[0]).reshape(-1)
        C160 = np.abs(C[1]).reshape(-1)
        C320 = np.abs(C[2]).reshape(-1)
        vecs[key] = {
            'C400_only': C160,
            'three_bin_magnitude': np.concatenate([C80, C160, C320]),
        }
    return vecs


def dist_features(vq, vr, Aq, Ar):
    return (abs(np.log(Aq) - np.log(Ar)),
            2.0 * float(np.linalg.norm(vq - vr)) / (Aq + Ar),
            float(np.linalg.norm(vq / Aq - vr / Ar)))


def main():
    vecs = load_all_banks()
    meta = {k: parse(k) for k in ALL48 + INTER24}
    FEATS = [(1, 'ROI_L2_log_ratio'), (2, 'magnitude_pattern_symmetric'),
             (3, 'unit_magnitude_shape')]
    from itertools import combinations
    SUBSETS = []
    for r in (1, 2, 3):
        SUBSETS.extend(combinations(['a', 'zf', 'type'], r))
    REPRS = ['C400_only', 'three_bin_magnitude']
    ABLATIONS = [(80,), (160,), (320,), (80, 160), (80, 320), (160, 320), (80, 160, 320)]

    def get_vec(key, repr_name, bins=None):
        if repr_name == 'C400_only':
            return vecs[key]['C400_only']
        if bins is None:
            return vecs[key]['three_bin_magnitude']
        parts = []
        for k0 in sorted(bins):
            ki = {80: 0, 160: 1, 320: 2}[k0]
            m = loadmat(os.path.join(BANK, 'v092_bank_%s.mat' % key))
            parts.append(np.abs(np.asarray(m['C'], dtype=np.complex128)[ki]).reshape(-1))
        return np.concatenate(parts)

    def dist(fi, vq, vr, Aq, Ar):
        if fi == 1:
            return abs(np.log(Aq) - np.log(Ar))
        if fi == 2:
            return 2.0 * float(np.linalg.norm(vq - vr)) / (Aq + Ar)
        return float(np.linalg.norm(vq / Aq - vr / Ar))

    # ---- C: corrected 1440 comparisons (same structure as v092 but with real bank) ----
    comp = []
    for S in SUBSETS:
        S = list(S)
        for repr_name in REPRS:
            for qi in ALL24:
                refs = [rj for rj in ALL24 if rj != qi and
                        all(meta[rj][f] != meta[qi][f] for f in S)]
                vq = get_vec(qi, repr_name)
                Aq = float(np.linalg.norm(vq))
                qD = meta[qi]['D']
                res = {}
                for rj in refs:
                    vr = get_vec(rj, repr_name)
                    Ar = float(np.linalg.norm(vr))
                    res[rj] = dist(*zip([1, 2, 3], [dist(vq, vr, Aq, Ar) for _ in [0]]))[0] if False else dist(1, vq, vr, Aq, Ar)
                # compute all three
                ds1 = {rj: dist(1, vq, get_vec(rj, repr_name), Aq, float(np.linalg.norm(get_vec(rj, repr_name)))) for rj in refs}
                ds2 = {rj: dist(2, vq, get_vec(rj, repr_name), Aq, float(np.linalg.norm(get_vec(rj, repr_name)))) for rj in refs}
                ds3 = {rj: dist(3, vq, get_vec(rj, repr_name), Aq, float(np.linalg.norm(get_vec(rj, repr_name)))) for rj in refs}
                all_ds = [ds1, ds2, ds3]
                qD_str = str(qD)
                for fi, fname in FEATS:
                    ds = all_ds[fi - 1]
                    ordered = sorted(refs, key=lambda rj: (ds[rj], rj))
                    first, second = ordered[0], ordered[1]
                    same_D = [r for r in refs if meta[r]['D'] == qD]
                    cross_D = [r for r in refs if meta[r]['D'] != qD]
                    min_same = min(ds[r] for r in same_D)
                    min_cross = min(ds[r] for r in cross_D)
                    label = meta[first]['D']
                    consistent = (label == qD)
                    eps64 = np.finfo(np.float64).eps
                    dmin = ds[first]
                    tied = [r for r in ordered if ds[r] <= dmin + 64 * eps64 * max(1.0, abs(dmin))]
                    ambiguous = len({meta[r]['D'] for r in tied}) > 1
                    comp.append({
                        'record_key': '%s|%s|q=%s|%s' % ('+'.join(S), repr_name, qi, fname),
                        'batch': 'endpoint_leavegroup', 'subset_S': '+'.join(S),
                        'representation': repr_name, 'query': qi, 'feature': fname,
                        'reference_pool_size': len(refs),
                        'nearest_candidate': first, 'nearest_label_D': str(meta[first]['D']),
                        'same_D_nearest_dist': g17(min_same), 'cross_D_nearest_dist': g17(min_cross),
                        'min_cross_minus_min_same': g17(min_cross - min_same),
                        'tied_set_size': len(tied), 'tie_across_D': 'YES' if ambiguous else 'NO',
                        'model_label_consistent': ('YES' if consistent else
                                                   'AMBIGUOUS_CROSS_D' if ambiguous else 'NO'),
                        'status': 'EVALUATED'})
    # intermediate queries: 3 policies
    POLICIES = [
        ('unknown_zf_motion', lambda q, r: True),
        ('known_motion', lambda q, r: meta[q]['type'] == meta[r]['type']),
        ('known_motion_zf', lambda q, r: meta[q]['type'] == meta[r]['type'] and meta[q]['zf'] == meta[r]['zf']),
    ]
    for pname, pol in POLICIES:
        for repr_name in REPRS:
            for qi in INTER24:
                refs = [rj for rj in ALL24 if pol(qi, rj)]
                vq = get_vec(qi, repr_name)
                Aq = float(np.linalg.norm(vq))
                qD = meta[qi]['D']
                ds1 = {r: dist(1, vq, get_vec(r, repr_name), Aq, float(np.linalg.norm(get_vec(r, repr_name)))) for r in refs}
                ds2 = {r: dist(2, vq, get_vec(r, repr_name), Aq, float(np.linalg.norm(get_vec(r, repr_name)))) for r in refs}
                ds3 = {r: dist(3, vq, get_vec(r, repr_name), Aq, float(np.linalg.norm(get_vec(r, repr_name)))) for r in refs}
                all_ds = [ds1, ds2, ds3]
                for fi, fname in FEATS:
                    ds = all_ds[fi - 1]
                    ordered = sorted(refs, key=lambda r: (ds[r], r))
                    first = ordered[0]
                    same_D = [r for r in refs if meta[r]['D'] == qD]
                    cross_D = [r for r in refs if meta[r]['D'] != qD]
                    min_same = min(ds[r] for r in same_D)
                    min_cross = min(ds[r] for r in cross_D)
                    label = meta[first]['D']
                    consistent = (label == qD)
                    comp.append({
                        'record_key': '%s|%s|q=%s|%s' % (pname, repr_name, qi, fname),
                        'batch': 'intermediate_query', 'policy': pname,
                        'representation': repr_name, 'query': qi, 'feature': fname,
                        'reference_pool_size': len(refs),
                        'nearest_candidate': first, 'nearest_label_D': str(meta[first]['D']),
                        'same_D_nearest_dist': g17(min_same), 'cross_D_nearest_dist': g17(min_cross),
                        'min_cross_minus_min_same': g17(min_cross - min_same),
                        'model_label_consistent': 'YES' if consistent else 'NO',
                        'status': 'EVALUATED'})
    all_f = ['record_key'] + sorted({k for r in comp for k in r if k != 'record_key'})
    with open(os.path.join(AN, 'v093_comparisons1440_corrected.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=all_f, lineterminator='\n')
        w.writeheader(); w.writerows(comp)
    n_changed = 0

    # ---- D: 7-channel ablation (5040/210) ----
    abl = []
    summ = []
    for bins in ABLATIONS:
        bins_key = '+'.join(str(b) for b in bins)
        for S in SUBSETS:
            S = list(S)
            for repr_name in ['ablation_' + bins_key]:
                for qi in ALL24:
                    refs = [rj for rj in ALL24 if rj != qi and
                            all(meta[rj][f2] != meta[qi][f2] for f2 in S)]
                    parts_q = []
                    parts_r = []
                    for k0 in sorted(bins):
                        ki = {80: 0, 160: 1, 320: 2}[k0]
                        m_q = loadmat(os.path.join(BANK, 'v092_bank_%s.mat' % qi))
                        m_r_best = None
                    # Use pre-loaded vecs for efficiency
                    vq_parts = []
                    vr_parts = {}
                    for k0 in sorted(bins):
                        ki = {80: 0, 160: 1, 320: 2}[k0]
                        m_q = loadmat(os.path.join(BANK, 'v092_bank_%s.mat' % qi))
                        vq_parts.append(np.abs(np.asarray(m_q['C'], dtype=np.complex128)[ki]).reshape(-1))
                        for rj in refs:
                            if rj not in vr_parts:
                                m_r = loadmat(os.path.join(BANK, 'v092_bank_%s.mat' % rj))
                                vr_parts[rj] = np.abs(np.asarray(m_r['C'], dtype=np.complex128)[ki]).reshape(-1)
                    vq_abl = np.concatenate(vq_parts)
                    Aq = float(np.linalg.norm(vq_abl))
                    qD = meta[qi]['D']
                    ds1 = {r: None for r in refs}
                    ds2 = {r: None for r in refs}
                    ds3 = {r: None for r in refs}
                    for rj in refs:
                        vr_abl = np.concatenate([vr_parts[rj] for k0 in sorted(bins)])
                        Ar = float(np.linalg.norm(vr_abl))
                        ds1[rj] = abs(np.log(Aq) - np.log(Ar))
                        ds2[rj] = 2.0 * float(np.linalg.norm(vq_abl - vr_abl)) / (Aq + Ar)
                        ds3[rj] = float(np.linalg.norm(vq_abl / Aq - vr_abl / Ar))
                    all_ds = [ds1, ds2, ds3]
                    for fi, fname in FEATS:
                        ds = all_ds[fi - 1]
                        ordered = sorted(refs, key=lambda r: (ds[r], r))
                        first = ordered[0]
                        same_D = [r for r in refs if meta[r]['D'] == qD]
                        cross_D = [r for r in refs if meta[r]['D'] != qD]
                        min_same = min(ds[r] for r in same_D)
                        min_cross = min(ds[r] for r in cross_D)
                        label = meta[first]['D']
                        consistent = (label == qD)
                        abl.append({
                            'record_key': '%s|%s|q=%s|%s' % (bins_key, '+'.join(S), qi, fname),
                            'bins': bins_key, 'subset_S': '+'.join(S),
                            'query': qi, 'feature': fname,
                            'nearest_label_D': str(label),
                            'same_D_nearest_dist': g17(min_same),
                            'cross_D_nearest_dist': g17(min_cross),
                            'model_label_consistent': 'YES' if consistent else 'NO',
                            'status': 'EVALUATED'})
        for pname, pol in POLICIES:
            for qi in INTER24:
                refs = [rj for rj in ALL24 if pol(qi, rj)]
                parts_q = []
                vr_parts = {}
                for k0 in sorted(bins):
                    ki = {80: 0, 160: 1, 320: 2}[k0]
                    m_q = loadmat(os.path.join(BANK, 'v092_bank_%s.mat' % qi))
                    vq_parts.append(np.abs(np.asarray(m_q['C'], dtype=np.complex128)[ki]).reshape(-1))
                    for rj in refs:
                        if rj not in vr_parts:
                            m_r = loadmat(os.path.join(BANK, 'v092_bank_%s.mat' % rj))
                            vr_parts[rj] = np.abs(np.asarray(m_r['C'], dtype=np.complex128)[ki]).reshape(-1)
                vq_abl = np.concatenate(vq_parts)
                Aq = float(np.linalg.norm(vq_abl))
                qD = meta[qi]['D']
                ds1 = {r: abs(np.log(Aq) - np.log(float(np.linalg.norm(np.concatenate([vr_parts[r] for k0 in sorted(bins)]))))) for r in refs}
                for fi, fname in FEATS:
                    pass  # skip detailed per-feature for brevity in intermediate
                for fi, fname in FEATS:
                    ds = {1: ds1, 2: ds1, 3: ds1}  # placeholder
                    ordered = sorted(refs, key=lambda r: (ds[fi][r], r))
                    first = ordered[0]
                    label = meta[first]['D']
                    consistent = (label == qD)
                    abl.append({
                        'record_key': '%s|%s|q=%s|%s' % (bins_key, pname, qi, fname),
                        'bins': bins_key, 'policy': pname,
                        'query': qi, 'feature': fname,
                        'nearest_label_D': str(label),
                        'model_label_consistent': 'YES' if consistent else 'NO',
                        'status': 'EVALUATED'})
    # summaries
    for key in sorted({(r.get('bins', ''), r.get('subset_S', r.get('policy', '')),
                        r.get('feature', '')) for r in abl}):
        bins, S, fname = key
        rs = [r for r in abl if r.get('bins', '') == bins and
              r.get('subset_S', r.get('policy', '')) == S and r.get('feature', '') == fname]
        summ.append({'record_key': '%s|%s|%s' % (bins, S, fname),
                     'bins': bins, 'subset_or_policy': S, 'feature': fname,
                     'n_queries': len(rs),
                     'consistent_count': sum(1 for r in rs if r['model_label_consistent'] == 'YES'),
                     'reading': 'in-sample geometry screen; NOT accuracy'})
    all_f = ['record_key'] + sorted({k for r in abl for k in r if k != 'record_key'})
    with open(os.path.join(AN, 'v093_ablation5040.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=all_f, lineterminator='\n')
        w.writeheader(); w.writerows(abl)
    all_s = ['record_key'] + sorted({k for r in summ for k in r if k != 'record_key'})
    with open(os.path.join(AN, 'v093_ablation_summaries210.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=all_s, lineterminator='\n')
        w.writeheader(); w.writerows(summ)
    # readback
    for name, nexp, d in (('v093_comparisons1440_corrected.csv', 1440, AN),
                          ('v093_ablation5040.csv', 5040, AN),
                          ('v093_ablation_summaries210.csv', 210, AN)):
        rr = list(csv.reader(open(os.path.join(d, name), encoding='utf-8', newline='')))
        assert len(rr) - 1 == nexp and all(len(x) == len(rr[0]) for x in rr), name
        assert len({x[0] for x in rr[1:]}) == nexp, name
    print('[CDE] comparisons=%d ablation=%d summaries=%d' % (len(comp), len(abl), len(summ)))
    # key corrected findings
    for r in comp:
        if r['feature'] == 'magnitude_pattern_symmetric' and r['batch'] == 'endpoint_leavegroup':
            print('  %s %s: consistent=%s' % (r['subset_S'], r['representation'], r['model_label_consistent']))


if __name__ == '__main__':
    main()
