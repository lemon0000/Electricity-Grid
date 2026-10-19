from hashlib import sha256
import json
import sqlite3

import pytest

from test_rq2_scale_selector_worker_v1 import request, actual_request, LIMIT
from src.rq2_joint_deliverability_boundary_v1 import scale_selector_replay as replay


def record(tmp_path, factory):
    req = factory()
    root = tmp_path/'selector_non_authoritative'
    with replay.store.DevelopmentScaleSelectorStore(root, req, max_record_bytes=LIMIT) as owned:
        result = owned.execute()
    with sqlite3.connect(root/'selector.sqlite3') as db:
        data = db.execute('SELECT payload FROM result WHERE id=1').fetchone()[0]
    return req, result, data


def verify(data, req):
    return replay.replay_record(data, req, expected_sha256=sha256(data).hexdigest(),
        expected_implementation_identity=replay.implementation_identity(req), max_record_bytes=LIMIT)


@pytest.mark.parametrize('factory', [request, actual_request])
def test_persisted_complete_chain_replays_without_solver(tmp_path, monkeypatch, factory):
    req, result, data = record(tmp_path, factory)
    assert result.status == 'selected'
    def forbidden(*args, **kwargs): raise AssertionError('replay called solver')
    monkeypatch.setattr(replay.scale.native, '_solve', forbidden)
    report = verify(data, req)
    assert report['reproduced_result_identity'] == result.identity
    assert report['selected_state_identity'] == result.next_state.identity
    assert report['selection_accepted'] and report['archive_reproduced']
    assert report['solver_calls_by_replay_module'] == 0
    assert not report['formal_result'] and not report['executable_resume_available']


@pytest.mark.parametrize('field,value', [('solver_calls', 99), ('next_state', None), ('formal_result', True)])
def test_rehashed_corruption_is_rejected(tmp_path, field, value):
    req, _, data = record(tmp_path, request)
    body = json.loads(data)
    for pair in body['encoded_result'][1]:
        if pair[0] == field: pair[1] = value
    body['result_identity'] = sha256(json.dumps(['tuple', [body['encoded_result']]],
        ensure_ascii=True, allow_nan=False).encode()).hexdigest()
    with pytest.raises(ValueError):
        verify(replay.store._bytes(body), req)


@pytest.mark.parametrize('fault', ['stage_order', 'lock', 'assignment', 'bound', 'partial', 'prefix'])
def test_rehashed_stage_evidence_cannot_forge_selection(tmp_path, fault):
    req, _, data = record(tmp_path, request)
    body = json.loads(data)
    fields = dict(body['encoded_result'][1])
    stages = fields['stages'][1]
    stage = dict(stages[0][1])
    raw = dict(stage['raw_solve'][1])
    if fault == 'stage_order':
        stages.reverse()
    elif fault == 'prefix':
        stages.pop()
    elif fault == 'lock':
        stage['fixed_previous_objectives'][1].append(['float', float(1).hex()])
    elif fault == 'assignment':
        raw['loaded_values'][1][0][1][1] = ['float', float(999).hex()]
    elif fault == 'bound':
        for pair in stage['raw_solve'][1]:
            if pair[0] == 'lower': pair[1] = ['float', float(999).hex()]
    else:
        raw['errors'][1].append('load:injected')
    body['result_identity'] = sha256(json.dumps(['tuple', [body['encoded_result']]],
        ensure_ascii=True, allow_nan=False).encode()).hexdigest()
    with pytest.raises(ValueError): verify(replay.store._bytes(body), req)


def test_unresolved_record_never_produces_state(tmp_path, monkeypatch):
    def failed(*args, **kwargs): raise RuntimeError('interrupted pipeline')
    monkeypatch.setattr(replay.scale.native, '_solve', failed)
    req, result, data = record(tmp_path, request)
    assert result.status == 'unresolved' and result.solver_calls is None
    report = verify(data, req)
    assert report['status'] == 'unresolved_archive_not_replayed'
    assert not report['selection_accepted'] and not report['archive_reproduced']


def test_21_uid_complete_record_replay(tmp_path):
    from test_rq2_scale_selector_v1 import many_inputs, budget, REF, SPEC
    def factory():
        info, disclosure, before = many_inputs()
        b = budget(uids=tuple(g.uid for g in info.network.units))
        return replay.store.SelectorRequest(info, disclosure, before,
            replay.scale.reference.reference_input_identity(info, disclosure, before), REF, SPEC, b,
            replay.scale.policy_identity(REF, SPEC, b))
    req, result, data = record(tmp_path, factory)
    report = verify(data, req)
    assert report['verified_stage_count'] == 23
    assert report['reproduced_result_identity'] == result.identity
