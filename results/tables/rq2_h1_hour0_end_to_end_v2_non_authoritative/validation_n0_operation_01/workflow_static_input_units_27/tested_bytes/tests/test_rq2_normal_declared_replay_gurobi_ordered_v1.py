"""Solver-free normal replay after one explicitly synthetic-source invocation."""
from copy import deepcopy
from hashlib import sha256
import json
import sqlite3

import pytest

from test_rq2_normal_declared_store_gurobi_ordered_v1 import supplied, prepared_source, bound_source, source_supplied, open_store, LIMIT
from test_rq2_normal_execution_gurobi_ordered_v1 import install
from src.rq2_joint_deliverability_boundary_v1 import normal_declared_replay_gurobi_ordered as api


def saved(tmp_path, supplied):
    root = tmp_path/'replay_non_authoritative'
    with open_store(root, supplied) as store:
        _, observed = store.execute()
    with sqlite3.connect(root/'normal.sqlite3') as connection:
        data = connection.execute('SELECT payload FROM result').fetchone()[0]
    return root, data, observed


def arguments(supplied, observed):
    kw = supplied[1]
    return dict(**kw, expected_record_sha256=observed.archived_result_sha256,
        expected_result_identity=observed.result_identity, expected_store_identity=observed.store_identity,
        expected_replay_identity=api.replay_identity(kw['expected_declared_execution_identity'], kw['specification'], kw['budget']),
        max_record_bytes=LIMIT)



def run(data, supplied, observed, **changes):
    kw = arguments(supplied, observed)
    kw.update(changes)
    return api.replay_normal_record(data, supplied[0], **kw)


def no_solver(monkeypatch):
    def forbidden(*a, **k):
        raise AssertionError('normal replay may not execute a native solver')
    monkeypatch.setattr(api.kernel.native, 'create_solver', forbidden)
    monkeypatch.setattr(api.kernel, 'run_normal_only', forbidden)
    monkeypatch.setattr(api.source, 'run_source_normal', forbidden)
    monkeypatch.setattr(api.execution, 'run_declared_normal', forbidden)


def test_owned_record_replays_source_raw_and_full_witness_without_solver(tmp_path, supplied, monkeypatch):
    root, data, observed = saved(tmp_path, supplied)
    no_solver(monkeypatch)
    result = run(data, supplied, observed)
    assert result.archive_consistent and result.accepted_record_reproduced, result.errors
    assert result.assignment_recomputed and result.normal_witness_reproduced
    assert result.source_input_binding_verified
    assert result.status == 'replayed_accepted_declared_normal_record'
    assert json.loads(result.source_replay_json)['native_record_scope'] == 'complete_native_record'
    assert result.solver_calls_by_replay == 0
    assert not result.native_execution_authenticated and not result.resource_measurements_authenticated
    assert not result.resume_authorized and not result.formal_result and not result.security_certified
    assert result.optimality_certificate is result.infeasibility_certificate is None
    kw = arguments(supplied, observed)
    kw.pop('expected_store_identity')
    assert api.replay_normal_store(root, supplied[0],
        expected_head=observed.head, **kw) == result
    with pytest.raises(TypeError):
        api.DeclaredGurobiOrderedNormalRecordReplay()


def test_current_head_required_instead_of_genesis(tmp_path, supplied):
    root, _, observed = saved(tmp_path, supplied)
    kw = arguments(supplied, observed)
    kw.pop('expected_store_identity')
    with pytest.raises(ValueError, match='current normal head'):
        api.replay_normal_store(root, supplied[0], expected_head=observed.genesis, **kw)


def test_old_replay_pin_cannot_authorize_fast_replay(tmp_path, supplied, monkeypatch):
    from src.rq2_joint_deliverability_boundary_v1 import normal_declared_replay_stream as prior
    _, data, observed = saved(tmp_path, supplied)
    no_solver(monkeypatch)
    options = supplied[1]
    old_pin = prior.replay_identity(options['expected_declared_execution_identity'],
        options['specification'], options['budget'])
    with pytest.raises(ValueError):
        run(data, supplied, observed, expected_replay_identity=old_pin)


@pytest.mark.parametrize('layer,old_type', [('declared', 'DeclaredStreamingNormalResult'),
    ('source', 'StreamingSourceNormalExecutionResult'), ('kernel', 'StreamingNormalExecutionResult'),
    ('declared', 'DeclaredFastStreamingNormalResult'),
    ('source', 'FastStreamingSourceNormalExecutionResult'), ('kernel', 'FastStreamingNormalExecutionResult')])
def test_prior_result_type_rejected_with_consistent_hashes(tmp_path, supplied, monkeypatch, layer, old_type):
    _, data, observed = saved(tmp_path, supplied)
    no_solver(monkeypatch)
    record = api.journal._decoded(data)
    declared = record['encoded_result']
    outer = field(declared, 'source_result')
    inner = field(outer, 'normal_result')
    {'declared': declared, 'source': outer, 'kernel': inner}[layer][0] = old_type
    record['result_identity'] = api.journal._result_identity(declared)
    data = api.journal._bytes(record)
    with pytest.raises(ValueError):
        run(data, supplied, observed, expected_record_sha256=sha256(data).hexdigest(),
            expected_result_identity=record['result_identity'])


def test_fast_replay_pin_cannot_authorize_numeric_replay(tmp_path, supplied, monkeypatch):
    from src.rq2_joint_deliverability_boundary_v1 import normal_declared_replay_stream_fast as prior
    _, data, observed = saved(tmp_path, supplied)
    no_solver(monkeypatch)
    options = supplied[1]
    pin = prior.replay_identity(options['expected_declared_execution_identity'],
        options['specification'], options['budget'])
    with pytest.raises(ValueError):
        run(data, supplied, observed, expected_replay_identity=pin)


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
    declared = record['encoded_result']
    outer = field(declared, 'source_result')
    inner = field(outer, 'normal_result')
    raw = field(inner, 'normal')
    mutate(outer, inner, raw)
    record['result_identity'] = api.journal._result_identity(declared)
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
    assert result.errors and result.status == 'inconsistent_declared_normal_record'


@pytest.mark.parametrize('fault', ['timeout', 'exception', 'load', 'none', 'native_infeasible'])
def test_partial_and_timeout_evidence_never_becomes_accepted(tmp_path, supplied, monkeypatch, fault):
    calls = install(monkeypatch, api.prepare.prepare_task_inputs(supplied[0],expected_request_identity=supplied[1]['expected_request_identity']).assembly.inputs, fault=fault)
    _, data, observed = saved(tmp_path, supplied)
    assert calls['solve'] == 1
    no_solver(monkeypatch)
    result = run(data, supplied, observed)
    assert not result.accepted_record_reproduced
    assert json.loads(result.source_replay_json)['recorded_normal_accepted'] is False
    assert not result.formal_result and result.solver_calls_by_replay == 0


def test_solver_creation_failure_remains_partial(tmp_path, supplied, monkeypatch):
    def fail(*a, **k): raise RuntimeError('create failure')
    monkeypatch.setattr(api.kernel.native, 'create_solver', fail)
    _, data, observed = saved(tmp_path, supplied)
    no_solver(monkeypatch)
    result = run(data, supplied, observed)
    assert json.loads(result.source_replay_json)['native_record_scope'] == 'partial_execution_evidence'
    assert not result.accepted_record_reproduced


def test_missing_inner_return_keeps_unknown_count(tmp_path, supplied, monkeypatch):
    def interrupted(*a, **k): raise KeyboardInterrupt('missing kernel return')
    monkeypatch.setattr(api.kernel, 'run_normal_only', interrupted)
    _, data, observed = saved(tmp_path, supplied)
    no_solver(monkeypatch)
    result = run(data, supplied, observed)
    assert result.archive_consistent and json.loads(result.source_replay_json)['recorded_normal_accepted'] is None
    assert json.loads(result.source_replay_json)['native_record_scope'] == 'no_native_record'
    assert not result.accepted_record_reproduced


@pytest.mark.parametrize('pin', ['expected_record_sha256', 'expected_result_identity', 'expected_store_identity',
    'expected_replay_identity', 'expected_assembly_identity', 'expected_request_identity', 'expected_binding_identity',
    'expected_declared_execution_identity', 'expected_source_implementation_identity', 'expected_binding_implementation_identity'])
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
    assert 'source:resource_error_projection_mismatch:'+error in result.errors


def test_recorded_post_memory_gate_rejection_replays_as_unresolved(tmp_path, supplied, monkeypatch):
    cap = supplied[1]['budget'].max_process_peak_working_set_bytes
    peak = [1000]
    original = api.kernel.streaming.audit_normal_assignment
    def audit(*args, **kwargs):
        result = original(*args, **kwargs)
        peak[0] = cap+1
        return result
    monkeypatch.setattr(api.kernel, '_peak_working_set_bytes', lambda: peak[0])
    monkeypatch.setattr(api.kernel.streaming, 'audit_normal_assignment', audit)
    _, data, observed = saved(tmp_path, supplied)
    no_solver(monkeypatch)
    result = run(data, supplied, observed)
    assert result.archive_consistent and not result.accepted_record_reproduced
    assert result.normal_witness_reproduced
    assert result.status == 'replayed_unresolved_declared_normal_record'


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
    assert json.loads(result.source_replay_json)['recorded_normal_accepted'] and json.loads(result.source_replay_json)['recorded_source_accepted']
    assert not result.archive_consistent and not result.accepted_record_reproduced


def test_post_source_failure_not_promoted_when_source_becomes_readable(tmp_path, supplied, monkeypatch):
    original = api.source.binding.bind_pair_normal
    calls = [0]
    def binder(*a, **k):
        calls[0] += 1
        if calls[0] == 3:
            raise RuntimeError('source temporarily unreadable')
        return original(*a, **k)
    monkeypatch.setattr(api.source.binding, 'bind_pair_normal', binder)
    _, data, observed = saved(tmp_path, supplied)
    no_solver(monkeypatch)
    result = run(data, supplied, observed)
    assert result.archive_consistent and json.loads(result.source_replay_json)['recorded_normal_accepted']
    assert result.normal_witness_reproduced and not result.accepted_record_reproduced
    assert result.status == 'replayed_unresolved_declared_normal_record'


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
    assert 'source:resource_error_projection_mismatch:'+error in result.errors


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
    assert json.loads(result.source_replay_json)['recorded_normal_accepted'] and json.loads(result.source_replay_json)['recorded_source_accepted']
    assert not result.archive_consistent and not result.accepted_record_reproduced
    assert 'source:accepted_builder_inventory_mismatch' in result.errors


def rewrite_declared(data, mutate):
    record=api.journal._decoded(data)
    mutate(record['encoded_result'])
    record['result_identity']=api.journal._result_identity(record['encoded_result'])
    raw=api.journal._bytes(record)
    return raw,dict(expected_record_sha256=sha256(raw).hexdigest(),expected_result_identity=record['result_identity'])


@pytest.mark.parametrize('fault',['accepted','status','calls','complete','timing_sum','source_missing'])
def test_declared_coherent_rehash_tamper_rejected(tmp_path,supplied,monkeypatch,fault):
    _,data,observed=saved(tmp_path,supplied)
    no_solver(monkeypatch)
    def mutate(wire):
        if fault=='accepted':put(wire,'accepted',False)
        elif fault=='status':put(wire,'status','unresolved_declared_normal')
        elif fault=='calls':put(wire,'solver_calls',0)
        elif fault=='complete':put(wire,'call_count_complete',False)
        elif fault=='source_missing':put(wire,'source_result',None)
        else:
            times=api.codec._decode(field(wire,'preparation_timings'))
            put(wire,'preparation_timings',(*times[:-1],('observed_total_seconds',999.)))
    changed,pins=rewrite_declared(data,mutate)
    result=run(changed,supplied,observed,**pins)
    assert not result.archive_consistent and not result.accepted_record_reproduced


@pytest.mark.parametrize('name,value',[('request_identity','0'*64),('contract','foreign'),
    ('formal_result',True),('mechanism_initial_state',False),('accepted',1),('preparation_timings',())])
def test_declared_role_and_types_rejected(tmp_path,supplied,monkeypatch,name,value):
    _,data,observed=saved(tmp_path,supplied)
    no_solver(monkeypatch)
    changed,pins=rewrite_declared(data,lambda wire:put(wire,name,value))
    with pytest.raises(ValueError):run(changed,supplied,observed,**pins)


def test_missing_source_return_replays_unknown_without_solver(tmp_path,supplied,monkeypatch):
    def interrupted(*a,**k):raise KeyboardInterrupt('source return lost')
    monkeypatch.setattr(api.source,'run_source_normal',interrupted)
    _,data,observed=saved(tmp_path,supplied)
    no_solver(monkeypatch)
    result=run(data,supplied,observed)
    assert result.archive_consistent and not result.accepted_record_reproduced
    assert result.source_replay_json is None and not result.assignment_recomputed
    assert result.solver_calls_by_replay==0


def test_post_declaration_failure_not_promoted_after_file_restored(tmp_path,supplied,monkeypatch):
    from pathlib import Path
    path=Path(supplied[0].normal_record_path)
    original_bytes=path.read_bytes()
    original=api.source.run_source_normal
    def changed(*a,**k):
        result=original(*a,**k)
        path.write_bytes(b'changed after solve')
        return result
    monkeypatch.setattr(api.source,'run_source_normal',changed)
    _,data,observed=saved(tmp_path,supplied)
    path.write_bytes(original_bytes)
    no_solver(monkeypatch)
    result=run(data,supplied,observed)
    assert result.archive_consistent and not result.accepted_record_reproduced
    assert result.assignment_recomputed and result.normal_witness_reproduced
    assert json.loads(result.source_replay_json)['accepted_record_reproduced']


def test_request_file_changed_during_replay_rejected(tmp_path,supplied,monkeypatch):
    from pathlib import Path
    _,data,observed=saved(tmp_path,supplied)
    no_solver(monkeypatch)
    original=api._replay_source
    def changed(*a,**k):
        result=original(*a,**k)
        Path(supplied[0].normal_record_path).write_bytes(b'changed during replay')
        return result
    monkeypatch.setattr(api,'_replay_source',changed)
    with pytest.raises(ValueError,match='size/hash mismatch'):run(data,supplied,observed)


@pytest.mark.parametrize('error',['fabricated_failure','source_result_binding_mismatch',
    'normal_result_binding_mismatch','source_result_acceptance_inconsistent','source_return:RuntimeError:invented'])
def test_fabricated_declared_rejection_cannot_be_consistent(tmp_path,supplied,monkeypatch,error):
    _,data,observed=saved(tmp_path,supplied)
    no_solver(monkeypatch)
    def mutate(wire):
        put(wire,'errors',(error,))
        put(wire,'accepted',False)
        put(wire,'status','unresolved_declared_normal')
    changed,pins=rewrite_declared(data,mutate)
    if error=='fabricated_failure':
        with pytest.raises(ValueError,match='vocabulary'):run(changed,supplied,observed,**pins)
    else:
        result=run(changed,supplied,observed,**pins)
        assert not result.archive_consistent and not result.accepted_record_reproduced


@pytest.mark.parametrize('field_name,value',[('solver_calls',False),('solver_calls',1),
    ('mechanism_initial_state',False),('observed_power_mapping',True),
    ('normal_assignment_verified',True),('formal_result',True)])
def test_prepared_role_rejected_before_source_replay(tmp_path,supplied,monkeypatch,field_name,value):
    from dataclasses import fields
    _,data,observed=saved(tmp_path,supplied)
    no_solver(monkeypatch)
    original=api.prepare.prepare_task_inputs
    def changed(*a,**k):
        result=original(*a,**k)
        values={f.name:getattr(result,f.name) for f in fields(result)}
        values[field_name]=value
        return api.kernel.native._make(api.prepare.PreparedStreamingNormalTaskInputs,**values)
    monkeypatch.setattr(api.prepare,'prepare_task_inputs',changed)
    monkeypatch.setattr(api,'_replay_source',lambda *a,**k:pytest.fail('source replay entered'))
    with pytest.raises(ValueError,match='prepared inputs differ'):run(data,supplied,observed)


@pytest.mark.parametrize('error',['invented','source_binding_changed','normal_result_binding_mismatch'])
def test_fabricated_source_rejection_cannot_be_consistent(tmp_path,supplied,monkeypatch,error):
    _,data,observed=saved(tmp_path,supplied)
    no_solver(monkeypatch)
    def mutate(wire):
        outer=field(wire,'source_result')
        put(outer,'errors',(error,))
        put(outer,'source_bound_normal_accepted',False)
        put(outer,'status','unresolved_source_bound_normal')
        put(wire,'accepted',False)
        put(wire,'status','unresolved_declared_normal')
    changed,pins=rewrite_declared(data,mutate)
    if error=='invented':
        with pytest.raises(ValueError,match='vocabulary'):run(changed,supplied,observed,**pins)
    else:
        result=run(changed,supplied,observed,**pins)
        assert not result.archive_consistent


@pytest.mark.parametrize('phase',['post_source_with_complete_binding','validation_without_inner'])
def test_source_exception_phase_must_match_archived_return(tmp_path,supplied,monkeypatch,phase):
    if phase=='validation_without_inner':
        def missing(*a,**k):raise RuntimeError('lost kernel return')
        monkeypatch.setattr(api.kernel,'run_normal_only',missing)
    _,data,observed=saved(tmp_path,supplied)
    no_solver(monkeypatch)
    def mutate(wire):
        outer=field(wire,'source_result')
        messages=('post_source:RuntimeError:invented',) if phase=='post_source_with_complete_binding' else (
            'normal_return_missing:RuntimeError:lost kernel return','normal_result_validation:RuntimeError:invented')
        put(outer,'errors',messages)
        put(outer,'source_bound_normal_accepted',False)
        put(outer,'status','unresolved_source_bound_normal')
        put(wire,'accepted',False)
        put(wire,'status','unresolved_declared_normal')
    changed,pins=rewrite_declared(data,mutate)
    result=run(changed,supplied,observed,**pins)
    assert not result.archive_consistent and not result.accepted_record_reproduced
