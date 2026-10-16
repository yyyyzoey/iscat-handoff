# -*- coding: utf-8 -*-
import os, sys, csv, json, itertools
import numpy as np
from scipy.io import loadmat
GH = os.getcwd()
AN = os.path.join(GH, chr(97)+chr(110)+chr(97)+chr(108)+chr(121)+chr(115)+chr(105)+chr(115))
TAB = os.path.join(GH, chr(116)+chr(97)+chr(98)+chr(108)+chr(101)+chr(115))
BANK = os.path.join(AN, chr(98)+chr(97)+chr(110)+chr(107))
ALL24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a) for D in (30,60,100) for zf in (450,550) for t in ('M200','M400') for a in (5,20)]
INTER24 = ['D%d_zf%d_%s_a%d' % (D, zf, t, a) for D in (30,60,100) for zf in (450,550) for t in ('M200','M400') for a in (10,15)]
ALL48 = ALL24 + INTER24
BIN_SUBSETS = [(80,),(160,),(320,),(80,160),(80,320),(160,320),(80,160,320)]
def g17(x): return '%.17g' % x
def parse(k):
    p = k.split('_')
    return {'D': int(p[0][1:]), 'zf': int(p[1][2:]), 'type': p[2], 'a': int(p[3][1:])}
def wcsv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader(); w.writerows(rows)
bank_C = {}
for key in ALL48:
    m = loadmat(os.path.join(BANK, 'v092_bank_%s.mat' % key))
    bank_C[key] = np.asarray(m['C'], dtype=np.complex128)
abs_C = {}
for key in ALL48:
    for ki, k0 in enumerate([80, 160, 320]):
        abs_C[(key, k0)] = np.abs(bank_C[key][ki]).reshape(-1)
def get_vector(key, bins):
    return np.concatenate([abs_C[(key, k0)] for k0 in sorted(bins)])
meta = {k: parse(k) for k in ALL48}
from itertools import combinations
FACTOR_SUBSETS = []
for r in (1, 2, 3):
    FACTOR_SUBSETS.extend(combinations(['a', 'zf', 'type'], r))
FEATS = [(1, 'ROI_L2_log_ratio'), (2, 'magnitude_pattern_symmetric'), (3, 'unit_magnitude_shape')]
POLICIES = [
    ('unknown_zf_motion', lambda q, r: True),
    ('known_motion', lambda q, r: meta[q]['type'] == meta[r]['type']),
    ('known_motion_zf', lambda q, r: meta[q]['type'] == meta[r]['type'] and meta[q]['zf'] == meta[r]['zf']),
]
eps64 = np.finfo(np.float64).eps
comp = []
summ = []
for bins in BIN_SUBSETS:
    bins_key = '+'.join(str(b) for b in bins)
    for S in FACTOR_SUBSETS:
        S = list(S)
        for qi in ALL24:
            refs = [r for r in ALL24 if r != qi and all(meta[r][f] != meta[qi][f] for f in S)]
            vq = get_vector(qi, bins)
            Aq = float(np.linalg.norm(vq))
            qD = meta[qi]['D']
            ds1 = {r: abs(np.log(Aq) - np.log(float(np.linalg.norm(get_vector(r, bins))))) for r in refs}
            ds2 = {r: 2.0 * float(np.linalg.norm(vq - get_vector(r, bins))) / (Aq + float(np.linalg.norm(get_vector(r, bins)))) for r in refs}
            ds3 = {r: float(np.linalg.norm(vq / Aq - get_vector(r, bins) / float(np.linalg.norm(get_vector(r, bins))))) for r in refs}
            all_ds = [ds1, ds2, ds3]
            for fi, fname in FEATS:
                ds = all_ds[fi - 1]
                ordered = sorted(refs, key=lambda r: (ds[r], r))
                dmin = ds[ordered[0]]
                tied = [r for r in ordered if ds[r] <= dmin + 64 * eps64 * max(1.0, abs(dmin))]
                tied_Ds = {meta[r]['D'] for r in tied}
                ambiguous = len(tied_Ds) > 1
                same_D = [r for r in refs if meta[r]['D'] == qD]
                cross_D = [r for r in refs if meta[r]['D'] != qD]
                min_same = min(ds[r] for r in same_D)
                min_cross = min(ds[r] for r in cross_D)
                label = meta[ordered[0]]['D']
                consistent = (label == qD) and not ambiguous
                comp.append({
                    'record_key': '%s|%s|q=%s|%s' % (bins_key, '+'.join(S), qi, fname),
                    'bins': bins_key, 'batch': 'endpoint_leavegroup',
                    'subset_S': '+'.join(S), 'query': qi, 'feature': fname,
                    'nearest_candidate': ordered[0], 'nearest_label_D': str(label),
                    'same_D_nearest_dist': g17(min_same), 'cross_D_nearest_dist': g17(min_cross),
                    'min_cross_minus_min_same': g17(min_cross - min_same),
                    'model_label_consistent': 'YES' if consistent else ('AMBIGUOUS_CROSS_D' if ambiguous else 'NO'),
                    'status': 'EVALUATED'})
    for pname, pol in POLICIES:
        for qi in INTER24:
            refs = [r for r in ALL24 if pol(qi, r)]
            vq = get_vector(qi, bins)
            Aq = float(np.linalg.norm(vq))
            qD = meta[qi]['D']
            ds1 = {r: abs(np.log(Aq) - np.log(float(np.linalg.norm(get_vector(r, bins))))) for r in refs}
            ds2 = {r: 2.0 * float(np.linalg.norm(vq - get_vector(r, bins))) / (Aq + float(np.linalg.norm(get_vector(r, bins)))) for r in refs}
            ds3 = {r: float(np.linalg.norm(vq / Aq - get_vector(r, bins) / float(np.linalg.norm(get_vector(r, bins))))) for r in refs}
            all_ds = [ds1, ds2, ds3]
            for fi, fname in FEATS:
                ds = all_ds[fi - 1]
                ordered = sorted(refs, key=lambda r: (ds[r], r))
                dmin = ds[ordered[0]]
                tied = [r for r in ordered if ds[r] <= dmin + 64 * eps64 * max(1.0, abs(dmin))]
                tied_Ds = {meta[r]['D'] for r in tied}
                ambiguous = len(tied_Ds) > 1
                same_D = [r for r in refs if meta[r]['D'] == qD]
                cross_D = [r for r in refs if meta[r]['D'] != qD]
                min_same = min(ds[r] for r in same_D)
                min_cross = min(ds[r] for r in cross_D)
                label = meta[ordered[0]]['D']
                consistent = (label == qD) and not ambiguous
                comp.append({
                    'record_key': '%s|%s|q=%s|%s' % (bins_key, pname, qi, fname),
                    'bins': bins_key, 'batch': 'intermediate_query',
                    'policy': pname, 'query': qi, 'feature': fname,
                    'nearest_candidate': ordered[0], 'nearest_label_D': str(label),
                    'same_D_nearest_dist': g17(min_same), 'cross_D_nearest_dist': g17(min_cross),
                    'min_cross_minus_min_same': g17(min_cross - min_same),
                    'model_label_consistent': 'YES' if consistent else ('AMBIGUOUS_CROSS_D' if ambiguous else 'NO'),
                    'status': 'EVALUATED'})
for key in sorted({(r['bins'], r.get('subset_S', r.get('policy', '')), r['feature']) for r in comp}):
    bins, S, fname = key
    rs = [r for r in comp if r['bins'] == bins and r.get('subset_S', r.get('policy', '')) == S and r['feature'] == fname]
    summ.append({'record_key': '%s|%s|%s' % (bins, S, fname), 'bins': bins,
                 'subset_or_policy': S, 'feature': fname, 'n_queries': len(rs),
                 'consistent_count': sum(1 for r in rs if r['model_label_consistent'] == 'YES'),
                 'inconsistent_count': sum(1 for r in rs if r['model_label_consistent'] == 'NO'),
                 'ambiguous_count': sum(1 for r in rs if r['model_label_consistent'] == 'AMBIGUOUS_CROSS_D')})
all_f = ['record_key'] + sorted({k for r in comp for k in r if k != 'record_key'})
wcsv(os.path.join(AN, 'v099_comparisons5040.csv'), all_f, comp)
all_s = ['record_key'] + sorted({k for r in summ for k in r if k != 'record_key'})
wcsv(os.path.join(AN, 'v099_summaries210.csv'), all_s, summ)
print('  comparisons: %d, summaries: %d' % (len(comp), len(summ)))
# 852 decomposition
dec_rows = []
n_dec_pass = 0
pairs_ee = list(itertools.combinations(ALL24, 2))
pairs_ei = list(itertools.product(ALL24, INTER24))
for qi, rj in [(i, j) for i, j, _ in [(a, b, 'EE') for a, b in pairs_ee] + [(a, b, 'EI') for a, b in pairs_ei]]:
    vq_bins = [abs_C[(qi, k0)] for k0 in [80, 160, 320]]
    vr_bins = [abs_C[(rj, k0)] for k0 in [80, 160, 320]]
    aq = [float(np.linalg.norm(v)) for v in vq_bins]
    ar = [float(np.linalg.norm(v)) for v in vr_bins]
    Aq = float(np.sqrt(sum(a**2 for a in aq)))
    Ar = float(np.sqrt(sum(a**2 for a in ar)))
    if Aq == 0 or Ar == 0:
        continue
    rq = [a/Aq for a in aq]; rr = [a/Ar for a in ar]
    uq = [v/a if a > 0 else np.zeros_like(v) for v, a in zip(vq_bins, aq)]
    ur = [v/a if a > 0 else np.zeros_like(v) for v, a in zip(vr_bins, ar)]
    spec = sum((r1-r2)**2 for r1, r2 in zip(rq, rr))
    spat = sum(r1*r2*float(np.linalg.norm(u1-u2))**2 for r1, r2, u1, u2 in zip(rq, rr, uq, ur))
    shape_sq = spec + spat
    concat_q = np.concatenate(vq_bins)/Aq
    concat_r = np.concatenate(vr_bins)/Ar
    shape_check = float(np.linalg.norm(concat_q - concat_r))
    shape_resid = abs(shape_sq - shape_check**2)
    sym_term = 4*(Aq-Ar)**2/(Aq+Ar)**2
    sym_shape = 4*Aq*Ar/(Aq+Ar)**2 * shape_sq
    sym_sq = sym_term + sym_shape
    concat_vq = np.concatenate(vq_bins)
    concat_vr = np.concatenate(vr_bins)
    sym_check = 2.0*float(np.linalg.norm(concat_vq - concat_vr))/(Aq+Ar)
    sym_resid = abs(sym_sq - sym_check**2)
    ok = shape_resid < 1e-12 and sym_resid < 1e-12
    n_dec_pass += int(ok)
    dec_rows.append({'record_key': '%s__vs__%s' % (qi, rj),
                     'shape_residual': g17(shape_resid), 'sym_residual': g17(sym_resid),
                     'status': 'PASS' if ok else 'FAIL'})
wcsv(os.path.join(AN, 'v099_decomposition852.csv'), list(dec_rows[0].keys()), dec_rows)
print('  decomposition: %d/%d PASS' % (n_dec_pass, len(dec_rows)))
# 1680 radius
radius_rows = []
for bins in BIN_SUBSETS:
    bins_key = '+'.join(str(b) for b in bins)
    all_policies = [(('+'.join(S)), None) for S in FACTOR_SUBSETS] + POLICIES
    for S_name, pol in all_policies:
        if pol is not None:
            queries = [k for k in ALL48 if k.endswith('_a10') or k.endswith('_a15')]
        else:
            queries = ALL24
        S_list = S_name.split('+') if not S_name.startswith('unknown') and not S_name.startswith('known') else []
        for qi in queries:
            if pol is not None:
                refs = [r for r in ALL24 if pol(qi, r)]
            else:
                refs = [r for r in ALL24 if r != qi and all(parse(r)[f] != parse(qi)[f] for f in S_list)]
            vq = get_vector(qi, bins)
            Aq = float(np.linalg.norm(vq))
            uq = vq/Aq if Aq > 0 else vq
            qD = meta[qi]['D']
            ds3 = {r: float(np.linalg.norm(uq - get_vector(r, bins)/float(np.linalg.norm(get_vector(r, bins))))) for r in refs}
            all_d = sorted(ds3.values())
            dmin = all_d[0]
            tol = 64*eps64*max(1.0, abs(dmin))
            tied = [r for r in refs if ds3[r] <= dmin + tol]
            tied_Ds = {meta[r]['D'] for r in tied}
            ambiguous = len(tied_Ds) > 1
            same_D = [r for r in refs if meta[r]['D'] == qD]
            cross_D = [r for r in refs if meta[r]['D'] != qD]
            d_same = min(ds3[r] for r in same_D) if same_D else float('inf')
            d_cross = min(ds3[r] for r in cross_D) if cross_D else float('inf')
            m = d_cross - d_same
            if m > 0 and not ambiguous:
                radius = m/2.0; label = 'POSITIVE'
            elif ambiguous:
                radius = 0.0; label = 'AMBIGUOUS_CROSS_D'
            else:
                radius = 0.0; label = 'NO_POSITIVE_TRUE_LABEL_RADIUS'
            radius_rows.append({
                'record_key': '%s|%s|q=%s' % (bins_key, S_name, qi),
                'bins': bins_key, 'subset_S': S_name, 'query': qi,
                'd_same': g17(d_same), 'd_cross': g17(d_cross),
                'margin_m': g17(m), 'sufficient_radius': g17(radius),
                'radius_label': label})
wcsv(os.path.join(TAB, 'v099_radius1680.csv'), list(radius_rows[0].keys()), radius_rows)
n_pos = sum(1 for r in radius_rows if r['radius_label'] == 'POSITIVE')
print('  radius: %d rows, %d POSITIVE' % (len(radius_rows), n_pos))
print('[v099 remaining] DONE')