from copy import deepcopy
from dataclasses import replace

import pytest

from tests.test_rq2_normal_numerical_execution_v2 import (
    api, worker, supplied, legacy_request, declared_source, prepared_source, bound_source,
    source_supplied, run, audit, setup)


@pytest.mark.parametrize('peak', [True, 0, -1, None, 2**63])
def test_invalid_or_excessive_peak_stops_before_solver(supplied, monkeypatch, peak):
    monkeypatch.setattr(api.kernel, '_peak_working_set_bytes', lambda: peak)
    monkeypatch.setattr(api.projection.capture, 'solve_once', lambda *a, **k: pytest.fail('native invoked'))
    with pytest.raises(ValueError, match='peak working set'): run(supplied)


@pytest.mark.parametrize('stage', ['after_native', 'after_serialization'])
def test_post_call_resource_failure_preserves_intent_and_blocks_receipt(supplied, tmp_path_factory, monkeypatch, stage):
    args = setup(supplied, tmp_path_factory)
    state = dict(failed=False, calls=0)
    solve = api.projection.capture.solve_once
    encode = api.replay._bytes
    def native(*a, **k):
        state['calls'] += 1
        result = solve(*a, **k)
        if stage == 'after_native': state['failed'] = True
        return result
    def serialize(value):
        result = encode(value)
        if stage == 'after_serialization' and type(value) is dict and value.get('schema') == api.SCHEMA:
            state['failed'] = True
        return result
    monkeypatch.setattr(api.projection.capture, 'solve_once', native)
    monkeypatch.setattr(api.replay, '_bytes', serialize)
    monkeypatch.setattr(api.kernel, '_peak_working_set_bytes',
        lambda: supplied.budget.max_process_peak_working_set_bytes+1 if state['failed'] else 100)
    with pytest.raises(ValueError, match='peak working set'): worker.run_worker(**args)
    assert state['calls'] == 1 and args['root'].exists() and not args['receipt_path'].exists()
    with pytest.raises((ValueError, FileExistsError)): worker.run_worker(**args)
    assert state['calls'] == 1


def with_core_cap(request, cap):
    budget = replace(request.budget, max_core_evidence_payload_bytes=cap)
    normal = replace(request.normal, budget=budget,
        expected_normal_execution_identity=api.kernel.normal_execution_identity(
            request.source.expected_input_identity, request.source.expected_scale,
            request.normal.specification, budget))
    return replace(request, normal=normal, numerical_byte_limit=min(cap, request.numerical_byte_limit))


def test_full_core_cap_includes_projection_and_prepared_plan(supplied, monkeypatch):
    record = run(supplied)
    raw = api.projection.capture.encode(record['numerical'])
    cap = len(raw)+256
    assert cap < len(api.replay._bytes(record))
    request = with_core_cap(supplied, cap)
    calls = []
    def retained(*a, **k): calls.append(1); return raw
    monkeypatch.setattr(api.projection.capture, 'solve_once', retained)
    with pytest.raises(ValueError, match='complete core evidence payload'): run(request)
    assert calls == [1]


def test_reencoded_resources_and_native_timing_are_checked_offline(supplied):
    record = run(supplied)
    variants = []
    for peaks in (None, {'before': True, 'after': 100}, {'before': 100, 'after': 99},
            {'before': 100, 'after': supplied.budget.max_process_peak_working_set_bytes+1}):
        variants.append(dict(record, process_peak_working_set_bytes=peaks))
    for altered in variants:
        with api.solver_free(), pytest.raises(ValueError): audit(supplied, altered)
    # Tiny native solves can report Runtime=0. Inject an explicit contradiction
    # rather than relying on machine speed or timer granularity.
    altered = deepcopy(record)
    altered['observed_wall_seconds'] = 0.0
    altered['numerical']['provenance']['native']['Runtime']['hex'] = (1.0).hex()
    with api.solver_free(), pytest.raises(ValueError, match='does not cover native Runtime'):
        audit(supplied, altered)
    report = audit(supplied, record)
    assert report['accepted_record_reproduced'] and not report['resource_measurements_authenticated']


def test_full_core_limit_is_reapplied_to_reencoded_archive(supplied, monkeypatch):
    record = run(supplied)
    request = with_core_cap(supplied, len(api.projection.capture.encode(record['numerical']))+256)
    # Give the forger consistent current request/projection pins; the payload gate still applies.
    with api.solver_free():
        projected, prepared = api._project(request, record['numerical'])
    record.update(request_identity=api.request_identity(request), projection=projected,
        prepared_information=api.kernel._encode(prepared))
    with api.solver_free(), pytest.raises(ValueError, match='complete core evidence payload'):
        audit(request, record)


def test_inconsistent_native_runtime_cannot_publish_execution_receipt(supplied, tmp_path_factory, monkeypatch):
    args = setup(supplied, tmp_path_factory)
    solve = api.projection.capture.solve_once
    calls = []
    def inconsistent(*a, **k):
        calls.append(1)
        import json
        numerical = json.loads(solve(*a, **k))
        numerical['provenance']['native']['Runtime']['hex'] = float(
            supplied.budget.max_observed_wall_seconds+1).hex()
        return api.projection.capture.encode(numerical)
    monkeypatch.setattr(api.projection.capture, 'solve_once', inconsistent)
    with pytest.raises(ValueError, match='does not cover native Runtime'): worker.run_worker(**args)
    assert calls == [1] and not args['receipt_path'].exists()
    with pytest.raises((ValueError, FileExistsError)): worker.run_worker(**args)
    assert calls == [1]
