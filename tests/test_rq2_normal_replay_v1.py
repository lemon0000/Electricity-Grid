"""Solver-free normal replay after one explicitly synthetic-source invocation."""
from copy import deepcopy
from hashlib import sha256
import json
import sqlite3

import pytest

from test_rq2_normal_store_v1 import supplied, open_store, LIMIT
from test_rq2_source_normal_execution_v1 import options
from test_rq2_continuous_grid_candidate_v1 import install
from src.rq2_joint_deliverability_boundary_v1 import normal_replay as api


def saved(tmp_path, supplied):
    root = tmp_path/'replay_non_authoritative'
    with open_store(root, supplied) as store:
        _, observed = store.execute()
    with sqlite3.connect(root/'normal.sqlite3') as connection:
        data = connection.execute('SELECT payload FROM result').fetchone()[0]
    return root, data, observed


def arguments(supplied, observed):
    assembly, declaration, report, _ = supplied
    kw = options(assembly, declaration, report)
    return dict(**kw, expected_record_sha256=observed.archived_result_sha256,
        expected_result_identity=observed.result_identity, expected_store_identity=observed.store_identity,
        expected_replay_identity=api.replay_identity(kw['expected_source_execution_identity'], kw['specification'], kw['budget']),
        max_record_bytes=LIMIT)


def run(data, supplied, observed, **changes):
    kw = arguments(supplied, observed)
    kw.update(changes)
    return api.replay_normal_record(data, supplied[0], 'unused', supplied[1], **kw)


def no_solver(monkeypatch):
    def forbidden(*a, **k):
        raise AssertionError('normal replay may not execute a native solver')
    monkeypatch.setattr(api.kernel.native, 'create_solver', forbidden)
    monkeypatch.setattr(api.kernel, 'run_normal_only', forbidden)
    monkeypatch.setattr(api.source, 'run_source_normal', forbidden)


def test_owned_record_replays_source_raw_and_full_witness_without_solver(tmp_path, supplied, monkeypatch):
    root, data, observed = saved(tmp_path, supplied)
    no_solver(monkeypatch)
    result = run(data, supplied, observed)
    assert result.archive_consistent and result.accepted_record_reproduced, result.errors
    assert result.assignment_recomputed and result.normal_witness_reproduced
    assert result.source_input_binding_verified
    assert result.status == 'replayed_accepted_normal_record'
    assert result.native_record_scope == 'complete_native_record'
    assert result.solver_calls_by_replay == 0
    assert not result.native_execution_authenticated and not result.resource_measurements_authenticated
    assert not result.resume_authorized and not result.formal_result and not result.security_certified
    assert result.optimality_certificate is result.infeasibility_certificate is None
    kw = arguments(supplied, observed)
    kw.pop('expected_store_identity')
    assert api.replay_normal_store(root, supplied[0], 'unused', supplied[1],
        expected_head=observed.head, **kw) == result
    with pytest.raises(TypeError):
        api.NormalRecordReplay()


def test_current_head_required_instead_of_genesis(tmp_path, supplied):
    root, _, observed = saved(tmp_path, supplied)
    kw = arguments(supplied, observed)
    kw.pop('expected_store_identity')
    with pytest.raises(ValueError, match='current normal head'):
        api.replay_normal_store(root, supplied[0], 'unused', supplied[1], expected_head=observed.genesis, **kw)


def field(wire, name):
    return dict(wire[1])[name]


def put(wire, name, value):
    for row in wire[1]:
        if row[0] == name:
            row[1] = api.kernel._encode(value)
            return
    raise AssertionError(name)


def rewrite(data, mutate):
    record = api.journal._decoded(data)
    outer = record['encoded_result']
    inner = field(outer, 'normal_result')
    raw = field(inner, 'normal')
    mutate(outer, inner, raw)
    record['result_identity'] = api.journal._result_identity(outer)
    encoded = api.journal._bytes(record)
    return encoded, dict(expected_record_sha256=sha256(encoded).hexdigest(), expected_result_identity=record['result_identity'])


@pytest.mark.parametrize('fault', ['objective', 'bound', 'assignment', 'witness', 'normal_flag',
    'source_flag', 'calls', 'core_size', 'elapsed', 'memory', 'post_source', 'status'])
def test_coherent_hash_tampering_cannot_pass_numerical_replay(tmp_path, supplied, monkeypatch, fault):
    _, data, observed = saved(tmp_path, supplied)
    no_solver(monkeypatch)
    def mutate(outer, inner, raw):
        if fault == 'objective': put(raw, 'objective', 999.)
        elif fault == 'bound': put(raw, 'lower', -999.)
        elif fault == 'assignment':
            values = list(api.codec._decode(field(raw, 'loaded_values')))
            index = next(i for i, (n, _) in enumerate(values) if n.startswith('generation['))
            name, value = values[index]
            values[index] = (name, value+1.)
            put(raw, 'loaded_values', tuple(values))
        elif fault == 'witness': put(field(inner, 'witness'), 'input_identity', '0'*64)
        elif fault == 'normal_flag': put(inner, 'normal_accepted', False)
        elif fault == 'source_flag': put(outer, 'source_bound_normal_accepted', False)
        elif fault == 'calls': put(inner, 'solver_calls', 0)
        elif fault == 'core_size': put(inner, 'core_evidence_payload_bytes', 1)
        elif fault == 'elapsed':
            timings = api.codec._decode(field(inner, 'timings'))
            put(inner, 'timings', (*timings[:-1], ('observed_total_seconds', 999.)))
        elif fault == 'memory':
            before, _ = api.codec._decode(field(inner, 'process_peak_working_set_bytes'))
            put(inner, 'process_peak_working_set_bytes', (before, 10**14))
        elif fault == 'post_source': put(outer, 'binding_after_json', None)
        elif fault == 'status': put(inner, 'status', 'unresolved_normal')
    changed, pins = rewrite(data, mutate)
    result = run(changed, supplied, observed, **pins)
    assert not result.archive_consistent and not result.accepted_record_reproduced
    assert result.errors and result.status == 'inconsistent_normal_record'


@pytest.mark.parametrize('fault', ['timeout', 'exception', 'load', 'none', 'native_infeasible'])
def test_partial_and_timeout_evidence_never_becomes_accepted(tmp_path, supplied, monkeypatch, fault):
    calls = install(monkeypatch, supplied[0].inputs, fault=fault)
    _, data, observed = saved(tmp_path, supplied)
    assert calls['solve'] == 1
    no_solver(monkeypatch)
    result = run(data, supplied, observed)
    assert not result.accepted_record_reproduced
    assert result.recorded_normal_accepted is False
    assert not result.formal_result and result.solver_calls_by_replay == 0


def test_solver_creation_failure_remains_partial(tmp_path, supplied, monkeypatch):
    def fail(*a, **k): raise RuntimeError('create failure')
    monkeypatch.setattr(api.kernel.native, 'create_solver', fail)
    _, data, observed = saved(tmp_path, supplied)
    no_solver(monkeypatch)
    result = run(data, supplied, observed)
    assert result.native_record_scope == 'partial_execution_evidence'
    assert not result.accepted_record_reproduced


def test_missing_inner_return_keeps_unknown_count(tmp_path, supplied, monkeypatch):
    def interrupted(*a, **k): raise KeyboardInterrupt('missing kernel return')
    monkeypatch.setattr(api.kernel, 'run_normal_only', interrupted)
    _, data, observed = saved(tmp_path, supplied)
    no_solver(monkeypatch)
    result = run(data, supplied, observed)
    assert result.archive_consistent and result.recorded_normal_accepted is None
    assert result.native_record_scope == 'no_native_record'
    assert not result.accepted_record_reproduced


@pytest.mark.parametrize('pin', ['expected_record_sha256', 'expected_result_identity', 'expected_store_identity',
    'expected_replay_identity', 'expected_assembly_identity', 'expected_pair_identity', 'expected_input_identity'])
def test_independent_pins_are_required(tmp_path, supplied, pin):
    _, data, observed = saved(tmp_path, supplied)
    with pytest.raises(ValueError):
        run(data, supplied, observed, **{pin: '0'*64})


def test_certification_flag_in_archive_rejected(tmp_path, supplied):
    _, data, observed = saved(tmp_path, supplied)
    changed, pins = rewrite(data, lambda outer, inner, raw: put(inner, 'security_certified', True))
    with pytest.raises(ValueError, match='certification'):
        run(changed, supplied, observed, **pins)


@pytest.mark.parametrize('error', ['core_evidence_payload_exceeds_budget',
    'process_lifetime_peak_exceeds_budget', 'observed_wall_time_exceeds_budget'])
def test_fabricated_resource_rejection_not_consistent_even_if_flags_lowered(tmp_path, supplied, error):
    _, data, observed = saved(tmp_path, supplied)
    def mutate(outer, inner, raw):
        put(inner, 'errors', (error,))
        put(inner, 'normal_accepted', False)
        put(inner, 'status', 'unresolved_normal')
        put(outer, 'source_bound_normal_accepted', False)
        put(outer, 'status', 'unresolved_source_bound_normal')
    changed, pins = rewrite(data, mutate)
    result = run(changed, supplied, observed, **pins)
    assert not result.archive_consistent and not result.accepted_record_reproduced
    assert 'resource_error_projection_mismatch:'+error in result.errors


def test_recorded_post_memory_gate_rejection_replays_as_unresolved(tmp_path, supplied, monkeypatch):
    cap = options(supplied[0], supplied[1], supplied[2])['budget'].max_process_peak_working_set_bytes
    peak = [1000]
    original = api.kernel.audit_normal_assignment
    def audit(*args, **kwargs):
        result = original(*args, **kwargs)
        peak[0] = cap+1
        return result
    monkeypatch.setattr(api.kernel, '_peak_working_set_bytes', lambda: peak[0])
    monkeypatch.setattr(api.kernel, 'audit_normal_assignment', audit)
    _, data, observed = saved(tmp_path, supplied)
    no_solver(monkeypatch)
    result = run(data, supplied, observed)
    assert result.archive_consistent and not result.accepted_record_reproduced
    assert result.normal_witness_reproduced
    assert result.status == 'replayed_unresolved_normal_record'


@pytest.mark.parametrize('fault', ['pipeline', 'builder', 'wrapper', 'peak_decrease'])
def test_resource_cross_field_tamper_cannot_preserve_acceptance(tmp_path, supplied, fault):
    _, data, observed = saved(tmp_path, supplied)
    def mutate(outer, inner, raw):
        if fault == 'peak_decrease':
            before, _ = api.codec._decode(field(inner, 'process_peak_working_set_bytes'))
            put(inner, 'process_peak_working_set_bytes', (before, before-1))
        elif fault == 'wrapper':
            put(outer, 'observed_wrapper_seconds', 0.)
        else:
            timings = list(api.codec._decode(field(inner, 'timings')))
            index = 1 if fault == 'pipeline' else 3
            timings[index] = (timings[index][0], 999. if fault == 'pipeline' else (999.,))
            put(inner, 'timings', tuple(timings))
    changed, pins = rewrite(data, mutate)
    result = run(changed, supplied, observed, **pins)
    assert result.recorded_normal_accepted and result.recorded_source_accepted
    assert not result.archive_consistent and not result.accepted_record_reproduced


def test_post_source_failure_not_promoted_when_source_becomes_readable(tmp_path, supplied, monkeypatch):
    report = supplied[2]
    calls = [0]
    def binder(*a, **k):
        calls[0] += 1
        if calls[0] == 2:
            raise RuntimeError('source temporarily unreadable')
        return deepcopy(report)
    monkeypatch.setattr(api.source.binding, 'bind_pair_normal', binder)
    _, data, observed = saved(tmp_path, supplied)
    no_solver(monkeypatch)
    result = run(data, supplied, observed)
    assert result.archive_consistent and result.recorded_normal_accepted
    assert result.normal_witness_reproduced and not result.accepted_record_reproduced
    assert result.status == 'replayed_unresolved_normal_record'


@pytest.mark.parametrize('fault', ['integer_time', 'budget_scalar', 'boolean_scalar'])
def test_equal_valued_scalar_type_tampering_rejected(tmp_path, supplied, monkeypatch, fault):
    _, data, observed = saved(tmp_path, supplied)
    no_solver(monkeypatch)
    def mutate(outer, inner, raw):
        if fault == 'integer_time':
            times = api.codec._decode(field(inner, 'timings'))
            put(inner, 'timings', tuple((name, (0,) if name == 'builder_seconds_nested' else 0)
                for name, value in times))
            put(outer, 'observed_wrapper_seconds', 0)
        elif fault == 'budget_scalar':
            put(field(inner, 'budget'), 'max_seconds_per_solve', 1)
        else:
            put(field(inner, 'specification'), 'tee', 0)
    changed, pins = rewrite(data, mutate)
    with pytest.raises(ValueError):
        run(changed, supplied, observed, **pins)


def test_duplicate_resource_rejection_marker_inconsistent(tmp_path, supplied, monkeypatch):
    _, data, observed = saved(tmp_path, supplied)
    no_solver(monkeypatch)
    error = 'process_lifetime_peak_exceeds_budget'
    def mutate(outer, inner, raw):
        before, _ = api.codec._decode(field(inner, 'process_peak_working_set_bytes'))
        put(inner, 'process_peak_working_set_bytes', (before, 10**14))
        put(inner, 'errors', (error, error))
        put(inner, 'normal_accepted', False)
        put(inner, 'status', 'unresolved_normal')
        put(outer, 'source_bound_normal_accepted', False)
        put(outer, 'status', 'unresolved_source_bound_normal')
    changed, pins = rewrite(data, mutate)
    result = run(changed, supplied, observed, **pins)
    assert not result.archive_consistent and not result.accepted_record_reproduced
    assert 'resource_error_projection_mismatch:'+error in result.errors


@pytest.mark.parametrize('count', [0, 1, 2, 4])
def test_builder_inventory_tamper_preserving_success_flags_rejected(tmp_path, supplied, monkeypatch, count):
    _, data, observed = saved(tmp_path, supplied)
    no_solver(monkeypatch)
    def mutate(outer, inner, raw):
        timings = api.codec._decode(field(inner, 'timings'))
        put(inner, 'timings', tuple((name, (0.,)*count if name == 'builder_seconds_nested' else value)
            for name, value in timings))
    changed, pins = rewrite(data, mutate)
    result = run(changed, supplied, observed, **pins)
    assert result.recorded_normal_accepted and result.recorded_source_accepted
    assert not result.archive_consistent and not result.accepted_record_reproduced
    assert 'accepted_builder_inventory_mismatch' in result.errors
