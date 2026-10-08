from dataclasses import replace
from hashlib import sha256
import json

import pytest

from test_rq2_scale_normal_source_v1 import supplied, declared_source, prepared_source, bound_source, source_supplied
from src.rq2_joint_deliverability_boundary_v1 import scale_normal_transport as transport

b = transport.b


def plan():
    normal = b.workload.NormalWork('one', 'training', 'a'*64, ('G1',), (1, 2), 600)
    env = b.resources.TaskEnvelope('one', 1500, 900, 1000, 200, 40, 1, 30000, 100000)
    serial = b.resources.SerialResourceBudget(1520, 20, 100, 50, 1150, 10, 250, 1)
    return b.SingleNormalResourcePlan(normal, env, serial)


def budget(p):
    return b.budget_for_task(p, task_id=p.normal.task_id, max_observed_wall_seconds=720.,
        max_process_peak_working_set_bytes=1000, max_core_evidence_payload_bytes=100)


def single_request(request):
    old = request.resource_plan
    p = b.SingleNormalResourcePlan(old.normals[0], old.envelopes[0], old.serial_budget)
    allocation = b.budget_for_task(p, task_id=p.normal.task_id,
        max_observed_wall_seconds=request.budget.max_observed_wall_seconds,
        max_process_peak_working_set_bytes=request.budget.max_process_peak_working_set_bytes,
        max_core_evidence_payload_bytes=request.budget.max_core_evidence_payload_bytes)
    execution = transport.source.kernel.normal_execution_identity(request.source.expected_input_identity,
        request.source.expected_scale, request.specification, allocation)
    return replace(request, budget=allocation, resource_plan=p, expected_normal_execution_identity=execution)


def test_exact_single_task_arithmetic_and_no_episode_contract():
    p = plan()
    report = b.check_single_normal_plan(p)
    assert (report['normal_tasks'], report['episode_tasks'], report['solver_calls']) == (1, 0, 1)
    assert report['reserved_solver_seconds'] == 600
    assert report['reserved_total_wall_seconds'] == 1520
    assert report['required_additional_commit_bytes'] == 1150
    assert report['required_additional_disk_bytes'] == 250
    assert report['declaration_consistent'] and report['errors'] == ()
    assert report['whole_task_resources_verified'] is report['execution_authorized'] is report['formal_ready'] is False
    assert len(budget(p).resource_contract_identity) == 64
    with pytest.raises(ValueError, match='nonempty'):
        b.resources.check_resource_contract((p.normal,), (), (p.envelope,), p.serial_budget)


@pytest.mark.parametrize('where,change,error', [
    ('envelope', {'max_wall_seconds':1499}, 'task_wall_reservation_shortfall'),
    ('serial_budget', {'max_total_wall_seconds':1519}, 'total_wall_reservation_shortfall'),
    ('serial_budget', {'max_additional_commit_bytes':1149}, 'commit_reservation_shortfall'),
    ('serial_budget', {'max_additional_disk_bytes':249}, 'disk_reservation_shortfall'),
    ('envelope', {'max_threads':2}, 'thread_cap_exceeds_plan'),
])
def test_each_resource_shortfall_blocks_budget(where, change, error):
    p = plan()
    p = replace(p, **{where:replace(getattr(p, where), **change)})
    report = b.check_single_normal_plan(p)
    assert report['errors'] == (error,) and not report['declaration_consistent']
    with pytest.raises(ValueError, match='inconsistent'):
        budget(p)


@pytest.mark.parametrize('where,change', [
    ('normal', {'seconds_per_solve':True}), ('normal', {'source_hours':(1, 3)}),
    ('normal', {'generator_uids':('G1', 'G1')}), ('normal', {'split':'other'}),
    ('envelope', {'task_id':'other'}), ('serial_budget', {'controller_seconds':0}),
])
def test_malformed_inventory_is_rejected(where, change):
    p = plan()
    with pytest.raises(ValueError):
        b.check_single_normal_plan(replace(p, **{where:replace(getattr(p, where), **change)}))


def test_single_source_roundtrip_real_tiny_execution_and_zero_solver_replay(supplied, monkeypatch):
    old, old_pin = supplied
    request = single_request(old)
    pin = transport.source.request_identity(request)
    assert pin != old_pin and request.budget.resource_contract_identity != old.budget.resource_contract_identity
    assert transport.decode_request(transport.export_request(old)) == old
    assert transport.decode_request(transport.export_request(request)) == request
    result = transport.source.run_source(request, expected_request_identity=pin)
    assert result['accepted'] and result['solver_calls'] == 1
    def forbidden(*args, **kwargs): raise AssertionError('solver during replay')
    monkeypatch.setattr(transport.source.kernel, 'run_normal_only', forbidden)
    monkeypatch.setattr(transport.source.kernel.native, '_solve', forbidden)
    monkeypatch.setattr(transport.source.kernel.native, 'create_solver', forbidden)
    data = transport.source.replay._bytes(result)
    report = transport.source.audit_source(data, request, expected_sha256=sha256(data).hexdigest(),
        expected_request_identity=pin, max_record_bytes=32*1024**2)
    assert report['record_consistent'] and report['accepted_record_reproduced']
    assert report['solver_calls_by_replay'] == 0


@pytest.mark.parametrize('fault', ['tag', 'episode', 'missing'])
def test_transport_cannot_disguise_plan_or_add_episode(supplied, fault):
    request = single_request(supplied[0])
    packet = json.loads(transport.export_request(request))
    plan_wire = dict(packet['request'][1])['resource_plan']
    if fault == 'tag': plan_wire[0] = 'NormalResourcePlan'
    elif fault == 'episode': plan_wire[1].append(['episodes', ['tuple', []]])
    else: plan_wire[1].pop()
    with pytest.raises(ValueError, match='ordered normal request fields'):
        transport.decode_request(transport.source.replay._bytes(packet))
