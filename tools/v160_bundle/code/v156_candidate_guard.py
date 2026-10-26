"""V156 read-only preparation of the 12x6 V152 historical joint starts.

This module deliberately DOES NOT predict, fit, know physical truth, compute
Jacobian, silently clip, select the best using historical Q, or choose fallback
parameters. The workstation must couple it to the source-locked and persistently
counted F2c predictor. Historical Q is solely a diagnostic reference.
"""
from __future__ import annotations
import json
from collections import defaultdict
from typing import Any
import numpy as np

from v152_gls_core import check_theta

BS = (1000, 10000, 100000)
ANONS = ('ANON_01', 'ANON_02', 'ANON_03', 'ANON_04')
EXPECTED = {(b, a) for b in BS for a in ANONS}

class AnchorSourceError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AnchorSourceError(message)


def read_v152_pool(document: Any, source_commit: str) -> dict[tuple[int, str], list[dict]]:
    """Extract *all* 72 indexed historical records; NO fallback on malformed input.

    The source_commit is a provenance label; cryptographic source verification
    must happen in the workstation adapter before calling this function.
    """
    _require(source_commit == '6d2db46d52509bd6987726dea211781cfa1b4127',
             'V152_COMMIT_NOT_FROZEN')
    _require(isinstance(document, dict) and isinstance(document.get('joint'), list),
             'V152_JOINT_RECORDS_MISSING')
    grouped: dict[tuple[int, str], list[dict]] = defaultdict(list)
    seen: set[tuple[int, str]] = set()
    for row_index, row in enumerate(document['joint']):
        _require(isinstance(row, dict), 'BAD_JOINT_GROUP')
        b, anon = row.get('B'), row.get('anon')
        _require(type(b) is int and isinstance(anon, str) and (b, anon) in EXPECTED,
                 'UNEXPECTED_B_ANON')
        _require((b, anon) not in seen, 'DUPLICATE_B_ANON')
        seen.add((b, anon))
        starts = row.get('results')
        if isinstance(starts, str):
            try:
                starts = json.loads(starts)
            except (TypeError, json.JSONDecodeError) as exc:
                raise AnchorSourceError('INVALID_STARTS_JSON') from exc
        _require(isinstance(starts, list) and len(starts) == 6,
                 f'EXPECTED_SIX_FULL_STARTS_{b}_{anon}')
        for start_index, item in enumerate(starts):
            _require(isinstance(item, dict) and 'theta' in item, 'FULL_THETA_MISSING')
            try:
                theta = check_theta(item['theta'])
            except (ValueError, TypeError) as exc:
                raise AnchorSourceError(f'ILLEGAL_THETA_{b}_{anon}_{start_index}') from exc
            _require(theta.shape == (4,), 'BAD_THETA_SHAPE')
            # Original loss retained as non-authoritative published evidence only.
            historic_q = item.get('Q_total')
            _require(isinstance(historic_q, (float, int)) and np.isfinite(historic_q),
                     'OLD_Q_MISSING_OR_NONFINITE')
            grouped[(b, anon)].append(dict(
                source_commit=source_commit,
                source_path='results/v152/all_results.json',
                group_index=row_index, start_index=start_index,
                source_record_id=f'v152:{b}:{anon}:{row_index}:{start_index}',
                theta=theta.astype(float).tolist(),
                historical_Q_unverified=float(historic_q),
                historical_status=item.get('status'),
                historic_record=item.copy()))
    _require(seen == EXPECTED and len(grouped) == 12 and
             sum(map(len, grouped.values())) == 72, 'NOT_ALL_12_GROUPS_72_STARTS')
    return dict(grouped)


def select_rescored_complete(group: list[dict]) -> dict:
    """Choose the *whole* freshly scored record, never recombine D/h/x/y/Q.

    Requires the adapter to have independently computed the fixed observed
    GLS from each full theta against its correctly paired three-frame data.
    """
    _require(bool(group), 'EMPTY_RESCORED_POOL')
    ids: set[str] = set()
    for r in group:
        _require(isinstance(r, dict) and isinstance(r.get('source_record_id'), str)
                 and bool(r['source_record_id']), 'MISSING_RECORD_ID')
        _require(r['source_record_id'] not in ids, 'DUPLICATE_RECORD_ID')
        ids.add(r['source_record_id'])
        for key in ('theta', 'candidate_D', 'Q_joint', 'Q_model', 'K', 'Q_per_frame',
                    'C_sha256', 'observation_identity', 'variance_identity', 'model_id'):
            _require(key in r, f'RESCORE_FIELD_MISSING_{key}')
        try:
            t = check_theta(r['theta'])
            q = float(r['Q_joint']); qm = float(r['Q_model']); k = float(r['K'])
            frames = np.asarray(r['Q_per_frame'], dtype=float)
        except (ValueError, TypeError) as exc:
            raise AnchorSourceError('INVALID_RESCORING_NUMERICS') from exc
        _require(frames.shape == (3,) and np.isfinite(frames).all()
                 and (frames >= 0).all(), 'BAD_PER_FRAME_Q')
        _require(np.isfinite(q) and np.isfinite(qm) and np.isfinite(k) and
                 q >= 0 and qm >= 0 and k >= 0, 'NONFINITE_OR_NEGATIVE_Q')
        _require(float(r['candidate_D']) == float(t[0]), 'D_NOT_BOUND_TO_THETA')
        tol = max(1e-8, 1e-10*abs(q))
        _require(abs(q - qm - k) <= tol and abs(q-frames.sum()) <= tol,
                 'Q_MODEL_K_FRAMES_MISMATCH')
        _require(all(isinstance(r[key], str) and r[key] for key in
                     ('C_sha256','observation_identity','variance_identity','model_id')),
                 'INCOMPLETE_PROVENANCE')
    return min(group, key=lambda r:(r['Q_joint'], r['source_record_id'])).copy()


def enforce_non_fallback(selected: dict[tuple[int, str], dict], pool: dict) -> None:
    _require(set(selected) == EXPECTED, 'SELECTED_GROUP_SET_MISMATCH')
    for key, r in selected.items():
        _require(r.get('source_record_id') in
                 {x['source_record_id'] for x in pool[key]},
                 f'SELECTED_THETA_NOT_FROM_POOL_{key}')
        expected = next(x['theta'] for x in pool[key]
                        if x['source_record_id'] == r['source_record_id'])
        _require(np.array_equal(np.asarray(r['theta']), np.asarray(expected)),
                 f'SELECTED_THETA_NOT_EXACT_ORIGINAL_{key}')
