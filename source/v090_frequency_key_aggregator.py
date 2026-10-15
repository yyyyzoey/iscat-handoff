# -*- coding: utf-8 -*-
"""v090 shared frequency-key aggregator and contract validator.

v089 defect: the D2/D3 summary dict used keys (model, window) WITHOUT the
frequency, so 420 Hz overwrote 200/400 Hz in the published 12-row table.
The NPZ was saved with full keys and is the recovery source.

Contract: every multi-frequency result MUST be stored/retrieved with the full
key `model|window|<int(f)>Hz`. The aggregator below is the single production
entry; the fixtures exercise it (including the overwrite negative)."""
import numpy as np

FREQS = (200, 400, 420)
WINDOWS = ('W1', 'W2')
MODELS = ('D0_direct_local', 'D1_direct_common', 'D2_joint7', 'D3_joint8_trend')


class ContractError(Exception):
    pass


def full_key(model, window, freq_hz):
    if float(freq_hz) != int(freq_hz):
        raise ContractError('non-integer frequency alias %r rejected (frozen set 200/400/420)' % (freq_hz,))
    return '%s|%s|%dHz' % (model, window, int(freq_hz))


def aggregate(model, window, freq_hz, complex_map, store):
    """Production aggregation entry: REQUIRES the full frequency key.
    A plain (model, window) store is rejected - the v089 overwrite failure
    mode cannot recur through this entry."""
    k = full_key(model, window, freq_hz)
    if not isinstance(complex_map, np.ndarray) or complex_map.shape != (41, 41) \
            or not np.iscomplexobj(complex_map):
        raise ContractError('map %s must be a 41x41 complex array' % k)
    store[k] = complex_map
    return k


def validate_archive(store, expect_models=MODELS, expect_windows=WINDOWS,
                     expect_freqs=FREQS, n_mean_maps=3):
    """Validate an NPZ-loaded archive: exactly len(expect_models)*2*3 map keys
    with full frequency identity, plus mean maps and mask."""
    mapkeys = [k for k in store.files if '|' in k]
    expected = set(full_key(m, w, f) for m in expect_models for w in expect_windows for f in expect_freqs)
    if set(mapkeys) != expected:
        missing = sorted(expected - set(mapkeys))
        extra = sorted(set(mapkeys) - expected)
        raise ContractError('archive key mismatch: missing=%s extra=%s' % (missing[:4], extra[:4]))
    for k in mapkeys:
        a = store[k]
        if a.shape != (41, 41) or not np.iscomplexobj(a):
            raise ContractError('map %s wrong shape/dtype: %s %s' % (k, a.shape, a.dtype))
    for mk in ('Imean_full', 'Imean_W1', 'Imean_W2'):
        if mk not in store.files:
            raise ContractError('mean map %s missing from archive' % mk)
    if 'common_mask' not in store.files:
        raise ContractError('common_mask missing from archive')
    return sorted(mapkeys)
