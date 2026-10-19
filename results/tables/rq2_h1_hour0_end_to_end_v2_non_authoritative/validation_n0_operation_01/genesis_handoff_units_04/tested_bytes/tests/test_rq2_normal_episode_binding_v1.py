from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as Q
from hashlib import sha256

import pytest

from tests.test_rq2_normal_numerical_execution_v2 import (
    supplied, legacy_request, declared_source, prepared_source, bound_source as base_bound_source, source_supplied)
from test_rq2_episode_zero_face_v1 import inputs as episode_fixture
from src.rq2_joint_deliverability_boundary_v1 import normal_episode_binding as api


@pytest.fixture
def bound_source(base_bound_source):
    from dataclasses import asdict
    from test_rq2_common_request_adapter_v1 import mapping
    from test_rq2_continuous_recovery_controller_v1 import obs
    root, old, new, pair, window = base_bound_source
    pair['mapping'] = asdict(mapping('250'))
    pair['hours'] = [asdict(replace(obs(i+1, g=0., c=0., due=None).hour,
        split='training', power_outage_seed=1, workload_occupancy=x))
        for i,x in enumerate((.04,.08,.12))]
    return root, old, new, pair, window


@pytest.fixture
def bound(supplied, bound_source, tmp_path, request):
    start = getattr(request, 'param', 1)
    (tmp_path/'selector_fixture').mkdir()
    req, arms, hours, settings = episode_fixture(tmp_path/'selector_fixture', zero=True)
    normal = api.normal
    # One complete shared declaration: a three-hour normal and one-hour episode.
    old = supplied.resource_plan
    serial = replace(old.serial_budget, max_total_wall_seconds=3000,
        commit_reserve_bytes=settings['budget'].commit_reserve_bytes,
        disk_reserve_bytes=settings['budget'].disk_reserve_bytes, max_additional_disk_bytes=2*1024**3)
    task = replace(old.episodes[0], source_hours=(start,))
    plan = replace(old, episodes=(task,), envelopes=(old.envelopes[0], settings['budget'].envelope), serial_budget=serial)
    budget = normal.budgets.budget_for_task(plan, task_id='normal', max_observed_wall_seconds=121.,
        max_process_peak_working_set_bytes=8*1024**3, max_core_evidence_payload_bytes=16*1024**2)
    nr = replace(supplied.normal, resource_plan=plan, budget=budget,
        expected_normal_execution_identity=normal.kernel.normal_execution_identity(
            supplied.source.expected_input_identity, supplied.source.expected_scale,
            supplied.normal.specification, budget))
    request = replace(supplied, normal=nr)
    pin = normal.request_identity(request)
    record = normal.run_source(request, expected_request_identity=pin)
    raw = normal.replay._bytes(record)
    _, prepared = normal.replay_information(raw, request, expected_sha256=sha256(raw).hexdigest(),
        expected_request_identity=pin, max_record_bytes=32*1024**2)
    inputs, _ = normal._snapshot(request, pin)
    current = replace(req.info.current, source_hour=start, timestamp=prepared.hours[start-1].timestamp,
        dc_baseline_mw=10.*start)
    info = api.information.current_grid_information(prepared, current, expected_audit_identity=prepared.audit_identity)
    source_audit = api.mapping.bind_request_source(inputs, prepared, info,
        expected_normal_identity=request.source.expected_input_identity, expected_prepared_identity=prepared.audit_identity)
    scale = api.episode.tx.scale
    def role_budget(role):
        return scale.legacy.budget_for_hour(plan.normals, plan.episodes, plan.envelopes, plan.serial_budget,
            task_id=task.task_id, source_hour=start, role=role)
    physical = req.before.physical_origin
    origin_disclosure = api.disclosure.initialize_disclosure(physical.disclosure.protocol,
        source_hour=start-1, active_component=None)
    current_disclosure = api.disclosure.disclose_current(origin_disclosure,
        api.disclosure.CurrentOutageReport(start, None, None))
    # Existing scientific contract permits origins distinct from normal and reference.
    origin = api.reference_grid.initialize_reference_origin(info, origin_disclosure,
        reference_protocol=req.before.protocol, grid_protocol=physical.protocol,
        generation_mw=(('G1', 25.),), base_availability=physical.base_availability)
    b = role_budget('reference')
    req = replace(req, info=info, disclosure=current_disclosure, before=origin, budget=b,
        expected_identity=scale.reference.reference_input_identity(info, current_disclosure, origin),
        expected_policy_identity=scale.policy_identity(req.selection_spec, req.solver_specification, b))
    paired = api.transport.boundary.ContinuationHour(**bound_source[3]['hours'][start-1])
    paired_mapping = api.mapping.CommonRequestMapping(**bound_source[3]['mapping'])
    anchor = replace(api.episode.tx.legacy._anchor(paired), power_source_hour=paired.power_source_hour-1,
        workload_source_hour=paired.workload_source_hour-1)
    rebound = []
    for index, arm in enumerate(arms):
        b = role_budget('actual:'+str(index))
        grid = scale.initialize_actual_origin(info, origin_disclosure, grid_protocol=physical.protocol,
            generation_mw=(('G1', 35.),), base_availability=physical.base_availability,
            selector=arm.selector, solver_specification=arm.specification, budget=b,
            expected_policy_identity=scale.policy_identity(arm.selector, arm.specification, b))
        track = arm.business.initial.tracks[0][1]
        business = api.transport.capacity_policy.initialize_capacity_policy(arm.business.spec,
            anchor=anchor, envelope=dict(track.physical.envelope),
            accounting_period_id=track.ledger.accounting_period_id, zero_carry_in_assumption=True)
        rebound.append(replace(arm, business=business, grid=grid, budget=b))
    hour = replace(hours[0], info=info, disclosure=current_disclosure, source_audit=source_audit,
        source_hour=paired, mapping=paired_mapping)
    epplan = api.episode.resources.EpisodeResourcePlan(plan.normals, plan.episodes, plan.envelopes, plan.serial_budget)
    packet = api.transport.EpisodeInputs(req, tuple(rebound), (hour,), settings['budget'], epplan)
    return request, raw, packet, settings['environment']


def bind(bound, packet=None, **changes):
    request, raw, original, _ = bound
    epraw = api.transport.export_inputs(original if packet is None else packet)
    args = dict(normal_sha256=sha256(raw).hexdigest(), episode_sha256=sha256(epraw).hexdigest(),
        max_normal_bytes=32*1024**2, max_episode_bytes=api.transport.LIMIT)
    args.update(changes)
    return api.bind_episode(raw, request, epraw, **args,
        expected_request_identity=api.normal.request_identity(request),
        expected_binding_identity=api.binding_identity(request, **args))


@pytest.mark.parametrize('bound', [1, 2], indirect=True)
def test_full_normal_source_binds_existing_four_arm_inputs_without_solver(bound, monkeypatch):
    def forbidden(*a, **k): pytest.fail('binding attempted solver')
    monkeypatch.setattr(api.normal.projection.capture, 'solve_once', forbidden)
    report, packet = bind(bound)
    assert report['solver_calls_by_binding'] == 0 and report['complete_resource_plan_equal']
    assert api.transport.export_inputs(packet) == api.transport.export_inputs(bound[2])
    assert packet.reference_request.before.physical_origin.generation_mw == (('G1', 25.),)
    assert packet.arms[0].grid.physical_origin.generation_mw == (('G1', 35.),)
    assert not report['formal_result'] and report['causal_certificate'] is None


def test_reencoded_forged_information_audit_and_policy_are_rejected(bound):
    original = bound[2]
    forged = []
    for field, value in [('allowed_plan_identity', '0'*64), ('prepared_audit_identity', '0'*64)]:
        packet = deepcopy(original)
        target = packet.hours[0].info.normal if field == 'allowed_plan_identity' else packet.hours[0].source_audit
        object.__setattr__(target, field, value)
        forged.append(packet)
    forged.append(replace(original, reference_request=replace(original.reference_request, expected_identity='0'*64)))
    forged.append(replace(original, reference_request=replace(original.reference_request, expected_policy_identity='0'*64)))
    req = original.reference_request
    spec = replace(req.solver_specification, feasibility_tolerance=1e-3)
    forged.append(replace(original, reference_request=replace(req, solver_specification=spec,
        expected_policy_identity=api.episode.tx.scale.policy_identity(req.selection_spec, spec, req.budget))))
    h = original.hours[0]
    forged.append(replace(original, hours=(replace(h, source_hour=replace(h.source_hour, workload_occupancy=Q(1))),)))
    for changes in ({'workload_source_hour':h.source_hour.workload_source_hour+1},
            {'cfe_request':0.125}, {'workload_provenance_sha256':'0'*64},
            {'power_provenance_sha256':'0'*64}, {'workload_trace_id':'changed_trace'}):
        forged.append(replace(original, hours=(replace(h, source_hour=replace(h.source_hour, **changes)),)))
    for packet in forged:
        with pytest.raises(ValueError): bind(bound, packet)
    with pytest.raises(ValueError): bind(bound, normal_sha256='0'*64)
    with pytest.raises(ValueError): bind(bound, episode_sha256='0'*64)


def test_complete_plan_mismatch_refused_even_when_episode_budget_rebinds(bound):
    packet = bound[2]
    plan = packet.resource_plan
    plan = replace(plan, serial_budget=replace(plan.serial_budget,
        max_total_wall_seconds=plan.serial_budget.max_total_wall_seconds+1))
    scale = api.episode.tx.scale
    def budget(role):
        return scale.legacy.budget_for_hour(plan.normals, plan.episodes, plan.envelopes, plan.serial_budget,
            task_id=packet.reference_request.budget.task_id, source_hour=1, role=role)
    req = packet.reference_request
    b = budget('reference')
    req = replace(req, budget=b, expected_policy_identity=scale.policy_identity(req.selection_spec, req.solver_specification, b))
    arms = []
    for i, arm in enumerate(packet.arms):
        b, physical = budget('actual:'+str(i)), arm.grid.physical_origin
        grid = scale.initialize_actual_origin(req.info, physical.disclosure, grid_protocol=physical.protocol,
            generation_mw=physical.generation_mw, base_availability=physical.base_availability,
            selector=arm.selector, solver_specification=arm.specification, budget=b,
            expected_policy_identity=scale.policy_identity(arm.selector, arm.specification, b))
        arms.append(replace(arm, grid=grid, budget=b))
    altered = replace(packet, reference_request=req, arms=tuple(arms), resource_plan=plan)
    api.transport.validate(altered)
    with pytest.raises(ValueError, match='complete resource plans differ'): bind(bound, altered)


def test_bound_inputs_execute_existing_mixed_episode(bound, tmp_path):
    _, packet = bind(bound)
    root = tmp_path/'bound_episode_non_authoritative'
    with api.episode.DevelopmentMixedSelectorEpisode(root, packet.reference_request, packet.arms, packet.hours,
            budget=packet.budget, resource_plan=packet.resource_plan, environment=bound[3]) as owned:
        result = owned.advance()
    assert result['status'] == 'observation_window_consumed'
    assert result['reserved_solver_calls'] == 11
    assert all(row['status'] == 'committed' for row in result['results'])
    assert not result['formal_result']
