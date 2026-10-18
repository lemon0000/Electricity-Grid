from dataclasses import replace

import pytest

from test_rq2_reference_grid_v1 import args
from test_rq2_reference_selector_v1 import SELECTOR as REF, install as ref_install, run as old_ref_run, two_inputs
from test_rq2_actual_dispatch_selector_v1 import SELECTOR as ACT, install as act_install, inputs as old_actual_inputs
from test_rq2_continuous_grid_candidate_v1 import SPEC
from src.rq2_joint_deliverability_boundary_v1 import scale_selector as scale
from src.rq2_joint_deliverability_boundary_v1 import reference_selector as reference
from src.rq2_joint_deliverability_boundary_v1 import actual_dispatch_selector as actual
from src.rq2_joint_deliverability_boundary_v1.execution_workload import NormalWork, EpisodeWork
from src.rq2_joint_deliverability_boundary_v1.execution_resource_contract import TaskEnvelope, SerialResourceBudget


def budget(role='reference', uids=('G1',), hour=1):
    count = len(uids)+(2 if role == 'reference' else 1)
    return scale.ScaleSelectorBudget('a'*64, 'episode', hour, role, uids, 1, 1, 10000, 10000, count, count)


def run_ref(inputs=None, b=None):
    inputs = args() if inputs is None else inputs
    b = budget() if b is None else b
    return scale.select_hour(*inputs, expected_identity=reference.reference_input_identity(*inputs),
        selector=REF, solver_specification=SPEC, budget=b,
        expected_policy_identity=scale.policy_identity(REF, SPEC, b))


def actual_inputs(b):
    info, disclosure, old_origin, power = old_actual_inputs()
    physical = old_origin.physical_origin
    before = scale.initialize_actual_origin(info, physical.disclosure, grid_protocol=physical.protocol,
        generation_mw=physical.generation_mw, base_availability=physical.base_availability,
        selector=ACT, solver_specification=SPEC, budget=b,
        expected_policy_identity=scale.policy_identity(ACT, SPEC, b))
    return info, disclosure, before, power


def run_actual(b=None):
    b = budget('actual:0') if b is None else b
    inputs = actual_inputs(b)
    return scale.select_hour(*inputs[:3], power=inputs[3], expected_identity=actual.dispatch_input_identity(*inputs),
        selector=ACT, solver_specification=SPEC, budget=b,
        expected_policy_identity=scale.policy_identity(ACT, SPEC, b))


def test_real_reference_matches_old_numerical_stages():
    inputs = args()
    old = old_ref_run(inputs)
    new = run_ref(inputs)
    assert new.status == 'selected', new.errors
    assert new.stages == old.stages
    assert new.selected_request_exact == old.selected_request_exact
    assert new.next_state.physical_carry == old.next_reference_state.physical_carry
    assert new.policy_identity != old.selector_policy_identity
    assert type(new) is scale.ScaleSelectionResult
    assert not new.hard_resource_limits_enforced and not new.durable_invocation_tracking
    assert not new.formal_result and not new.security_certified


def test_real_actual_dispatch_keeps_all_stages_and_carry():
    result = run_actual()
    assert result.status == 'selected', result.errors
    assert result.solver_calls == result.completed_solver_calls == 2
    assert tuple(s.objective_label for s in result.stages) == ('l1_normal_deviation', 'generation:G1')
    assert tuple(s.raw_solve.objective for s in result.stages) == (5., 25.)
    assert result.next_state.physical_carry.generation_mw == (('G1', 25.),)


def test_two_uid_tie_keeps_registered_order():
    result = run_ref(two_inputs(), budget(uids=('G1', 'G2')))
    assert result.status == 'selected', result.errors
    assert tuple(s.raw_solve.objective for s in result.stages) == (0., 80., 10., 90.)
    assert result.next_state.physical_carry.generation_mw == (('G1', 10.), ('G2', 90.))


@pytest.mark.parametrize('role', ['reference', 'actual:0'])
@pytest.mark.parametrize('fault', ['timeout', 'exception', 'missing_bound', 'gap', 'missing_variable', 'options'])
def test_rejected_stage_stops_without_next_state(monkeypatch, role, fault):
    install = ref_install if role == 'reference' else act_install
    calls = install(monkeypatch, fault=fault, stage=1)
    result = run_ref() if role == 'reference' else run_actual()
    assert result.status == 'unresolved' and result.next_state is None
    assert calls['solve'] == result.solver_calls == 2
    assert len(result.stages) == 2 and not result.stages[-1].accepted


def test_pipeline_interrupt_keeps_completed_and_unknown_call_counts(monkeypatch):
    ref_install(monkeypatch)
    original = scale.native._solve
    def interrupted(*args, **kwargs):
        if args[3].endswith('l1_normal_deviation'):
            raise KeyboardInterrupt()
        return original(*args, **kwargs)
    monkeypatch.setattr(scale.native, '_solve', interrupted)
    result = run_ref()
    assert result.solver_calls is None and result.completed_solver_calls == 1
    assert len(result.stages) == 1 and result.next_state is None
    assert 'KeyboardInterrupt' in result.errors[0]


def test_audit_failure_keeps_returned_raw_evidence_and_known_call(monkeypatch):
    ref_install(monkeypatch)
    def broken(*a, **kw):
        raise RuntimeError('synthetic audit failure')
    monkeypatch.setattr(reference, '_audit_stage', broken)
    result = run_ref()
    assert result.solver_calls == 1 and len(result.stages) == 1
    assert result.stages[0].raw_solve.assignment_valid
    assert not result.stages[0].accepted and result.next_state is None


@pytest.mark.parametrize('change', [
    {'source_hour': 2}, {'generator_uids': ('other',)}, {'max_solver_calls': 2},
    {'max_total_solver_seconds': 2}, {'max_seconds_per_solve': 2}, {'max_variables': 1},
])
def test_reservation_mismatch_rejected_before_solver(monkeypatch, change):
    def forbidden(*a, **kw):
        pytest.fail('solver reached after invalid reservation')
    monkeypatch.setattr(scale.native, '_solve', forbidden)
    with pytest.raises(ValueError):
        run_ref(b=replace(budget(), **change))


def test_158_uid_reservation_accepts_complete_stage_counts_without_solving():
    uids = tuple(f'g{x:03}' for x in range(158))
    for role, selector, count in [('reference', REF, 160), ('actual:0', ACT, 159)]:
        b = budget(role, uids)
        assert b.max_solver_calls == count
        scale._admit(selector, SPEC, b, count)


def test_hour_is_invocation_binding_not_a_new_policy():
    b = budget()
    assert scale.policy_identity(REF, SPEC, b) == scale.policy_identity(REF, SPEC, replace(b, source_hour=2))
    assert scale.policy_identity(REF, SPEC, b) != scale.policy_identity(REF, SPEC, replace(b, task_id='other'))


def test_budget_derives_from_complete_contract_with_actual_arm_limits():
    normal = NormalWork('n', 'training', 'a'*64, ('G1',), (1, 2), 1)
    episode = EpisodeWork('e', 'training', 'n', 'a'*64, ('G1',), (1, 2), 1, (1, 2, 3, 4))
    envelopes = tuple(TaskEnvelope(name, 100, 10, 100, 100, 100, 1, 1000, 1000) for name in ('n', 'e'))
    plan = SerialResourceBudget(210, 10, 100, 100, 300, 100, 500, 1)
    b = scale.budget_for_hour((normal,), (episode,), envelopes, plan, task_id='e', source_hour=2, role='actual:3')
    assert b.max_solver_calls == 2 and b.max_total_solver_seconds == 8
    assert b.max_seconds_per_solve == 4 and b.generator_uids == ('G1',)
    with pytest.raises(ValueError):
        scale.budget_for_hour((normal,), (episode,), envelopes, replace(plan, max_additional_disk_bytes=499),
                              task_id='e', source_hour=2, role='reference')


def many_inputs():
    from pyomo.environ import Var
    from test_rq2_continuous_grid_normal_v1 import fixture, model_for
    from test_rq2_grid_information_v1 import prepare, current, view
    from test_rq2_current_grid_step_v1 import protocol
    from src.rq2_joint_deliverability_boundary_v1 import reference_grid
    from src.rq2_joint_deliverability_boundary_v1.event_disclosure import (
        OutageComponent, DisclosureProtocol, initialize_disclosure, CurrentOutageReport, disclose_current)
    uids = tuple(sorted(('G1',)+tuple(f'G{i:02}' for i in range(2, 22))))
    original = fixture(demand=210.)
    generators = tuple(replace(original.data.generators[0], uid=uid) for uid in uids)
    initial = replace(original.initial, commitment={uid: True for uid in uids},
        generation_mw={uid: 10. for uid in uids}, time_in_state_hours={uid: 1 for uid in uids})
    points = tuple(replace(p, generator_min_mw={uid: 10. for uid in uids},
        generator_max_mw={uid: 100. for uid in uids}) for p in original.data.hourly_points)
    source = replace(original, data=replace(original.data, generators=generators, hourly_points=points),
        initial=initial, carry=replace(original.carry,
            limits=tuple(replace(original.carry.limits[0], uid=uid) for uid in uids),
            points=tuple(replace(original.carry.points[0], uid=uid, generation_mw=10.) for uid in uids),
            elapsed_state_hours=(1,)*len(uids)),
        request=replace(original.request, initial_commitment=initial.commitment,
            initial_generation_mw=initial.generation_mw, initial_time_in_state_hours=initial.time_in_state_hours,
            generator_availability=tuple({uid: True for uid in uids} for _ in points)))
    model = model_for(source)
    values = {v.name: 0. for v in model.component_data_objects(Var)}
    for t in range(3):
        for uid in uids:
            values[f'commitment[{t},{uid}]'] = 1.
            values[f'generation[normal,{t},{uid}]'] = 10.
    conditions = replace(current(demand=0.), generator_min_mw=tuple((uid, 10.) for uid in uids),
        generator_max_mw=tuple((uid, 100.) for uid in uids), generator_available=tuple((uid, True) for uid in uids),
        dc_baseline_mw=210., dc_physical_maximum_mw=210., dc_connected_capacity_mw=210.)
    info = view(prepare(source, values), conditions)
    declaration = DisclosureProtocol(tuple(OutageComponent('generator', uid) for uid in uids),
        'current_n1_outage_overlay_revealed_before_current_action',
        'complete_current_n1_outage_overlay__no_hidden_same_hour_replacement', 'mechanism_assumption')
    incoming = initialize_disclosure(declaration, source_hour=0, active_component=None)
    before = reference_grid.initialize_reference_origin(info, incoming, reference_protocol=args()[2].protocol,
        grid_protocol=protocol(), generation_mw=tuple((uid, 10.) for uid in uids),
        base_availability=conditions.generator_available)
    return info, disclose_current(incoming, CurrentOutageReport(1, None, None)), before


def test_real_21_uid_reference_crosses_old_20_call_cap():
    inputs = many_inputs()
    uids = tuple(g.uid for g in inputs[0].network.units)
    result = run_ref(inputs, budget(uids=uids))
    assert result.status == 'selected', result.errors
    assert result.solver_calls == result.planned_solver_calls == len(result.stages) == 23
    assert tuple(stage.objective_label for stage in result.stages[2:]) == tuple('generation:'+uid for uid in uids)
    assert result.selected_request_exact == ('0', '1')
    assert result.next_state.physical_carry.generation_mw == tuple((uid, 10.) for uid in uids)


@pytest.mark.parametrize('filename', ['execution_resource_contract.py', 'execution_workload.py'])
def test_resource_dependency_source_drift_changes_policy_and_rejects_old_pin(monkeypatch, filename):
    from pathlib import Path
    b, inputs = budget(), args()
    pin = scale.policy_identity(REF, SPEC, b)
    read = Path.read_bytes
    monkeypatch.setattr(Path, 'read_bytes', lambda path: read(path)+(b'\n# drift' if path.name == filename else b''))
    assert scale.policy_identity(REF, SPEC, b) != pin
    with pytest.raises(ValueError, match='policy identity'):
        scale.select_hour(*inputs, expected_identity=reference.reference_input_identity(*inputs),
            selector=REF, solver_specification=SPEC, budget=b, expected_policy_identity=pin)


@pytest.mark.parametrize('fault', ['carry', 'state'])
def test_finalization_failure_preserves_all_known_stages(monkeypatch, fault):
    from copy import copy
    ref_install(monkeypatch)
    if fault == 'state':
        owned = scale._owned
        def fail(cls, **values):
            if cls is reference.ReferenceGridState:
                raise RuntimeError('synthetic final state failure')
            return owned(cls, **values)
        monkeypatch.setattr(scale, '_owned', fail)
    else:
        audit = reference._audit_stage
        def drift(*args, **kwargs):
            witness, exact, lock, errors = audit(*args, **kwargs)
            witness = copy(witness)
            physical = copy(witness.physical_witness)
            carry = copy(physical.next_carry)
            object.__setattr__(carry, 'generation_mw', (('G1', 31.),))
            object.__setattr__(physical, 'next_carry', carry)
            object.__setattr__(witness, 'physical_witness', physical)
            return witness, exact, lock, errors
        monkeypatch.setattr(reference, '_audit_stage', drift)
    result = run_ref()
    assert result.next_state is result.selected_request_exact is None
    assert result.solver_calls == result.completed_solver_calls == len(result.stages) == 3
    assert all(stage.accepted for stage in result.stages)
    assert result.status == 'unresolved' and result.errors[0].startswith('finalization_unresolved:')


def test_real_reference_second_hour_keeps_policy_and_carry_chain():
    from test_rq2_current_grid_step_v1 import prepared, current, view
    from src.rq2_joint_deliverability_boundary_v1.event_disclosure import CurrentOutageReport, disclose_current
    first = run_ref()
    state = first.next_state
    info = view(prepared(10.), replace(current(2, demand=20.), dc_baseline_mw=25.))
    disclosure = disclose_current(state.physical_carry.disclosure, CurrentOutageReport(2, None, None))
    second = run_ref((info, disclosure, state), budget(hour=2))
    assert second.status == 'selected', second.errors
    assert second.policy_identity == first.policy_identity
    assert second.next_state.previous_state_identity == state.identity


def test_real_actual_second_hour_keeps_policy_and_carry_chain():
    from test_rq2_actual_dispatch_selector_v1 import second_inputs
    first = run_actual()
    inputs = second_inputs(first.next_state)
    b = budget('actual:0', hour=2)
    second = scale.select_hour(*inputs[:3], power=inputs[3], expected_identity=actual.dispatch_input_identity(*inputs),
        selector=ACT, solver_specification=SPEC, budget=b,
        expected_policy_identity=scale.policy_identity(ACT, SPEC, b))
    assert second.status == 'selected', second.errors
    assert second.policy_identity == first.policy_identity
    assert second.next_state.previous_state_identity == first.next_state.identity


def test_real_21_uid_actual_crosses_old_20_call_cap():
    from src.rq2_joint_deliverability_boundary_v1.current_grid_step import PrescribedDcPower
    info, disclosure, ref_origin = many_inputs()
    uids = tuple(g.uid for g in info.network.units)
    b = budget('actual:0', uids)
    pin = scale.policy_identity(ACT, SPEC, b)
    physical = ref_origin.physical_origin
    before = scale.initialize_actual_origin(info, physical.disclosure, grid_protocol=physical.protocol,
        generation_mw=physical.generation_mw, base_availability=physical.base_availability,
        selector=ACT, solver_specification=SPEC, budget=b, expected_policy_identity=pin)
    power = PrescribedDcPower(1, '210', '1', 'mechanism_assumption')
    result = scale.select_hour(info, disclosure, before, power=power,
        expected_identity=actual.dispatch_input_identity(info, disclosure, before, power),
        selector=ACT, solver_specification=SPEC, budget=b, expected_policy_identity=pin)
    assert result.status == 'selected', result.errors
    assert result.solver_calls == result.planned_solver_calls == len(result.stages) == 22
    assert tuple(s.objective_label for s in result.stages[1:]) == tuple('generation:'+uid for uid in uids)
    assert result.next_state.physical_carry.generation_mw == tuple((uid, 10.) for uid in uids)


def test_old_selector_admission_rejects_new_budget():
    with pytest.raises(ValueError, match='development budget'):
        reference._admit(REF, SPEC, budget(), 3)
    with pytest.raises(ValueError, match='development budget'):
        actual._admit(ACT, SPEC, budget('actual:0'), 2)


def test_drift_during_largest_build_stops_before_any_native_call(monkeypatch):
    build = reference._stage_model
    pin = scale.policy_identity
    def drift(*args, **kwargs):
        result = build(*args, **kwargs)
        monkeypatch.setattr(scale, 'policy_identity', lambda *a, **kw: 'b'*64)
        return result
    monkeypatch.setattr(reference, '_stage_model', drift)
    inputs, b = args(), budget()
    result = scale.select_hour(*inputs, expected_identity=reference.reference_input_identity(*inputs),
        selector=REF, solver_specification=SPEC, budget=b, expected_policy_identity=pin(REF, SPEC, b))
    assert result.solver_calls == 0 and not result.stages and result.next_state is None
    assert result.errors == ('0:pre_stage_input_or_policy_drift',)
