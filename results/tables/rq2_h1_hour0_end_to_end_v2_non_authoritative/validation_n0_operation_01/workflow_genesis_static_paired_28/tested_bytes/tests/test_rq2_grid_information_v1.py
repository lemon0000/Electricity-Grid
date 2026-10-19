from dataclasses import asdict, replace
from math import degrees
import json

import pytest

from test_rq2_continuous_grid_normal_v1 import fixture, assignment_for
from src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal import normal_input_identity
from src.rq2_joint_deliverability_boundary_v1 import grid_information as info


def declaration(hour=0):
    return info.PlanInformationDeclaration(hour,
        'supplied_normal_profiles_declared_as_pre_episode_forecast',
        'fixed_normal_schedule_issued_before_first_action', 'mechanism_assumption')


def prepare(inputs, assignment=None, declared=None):
    return info.prepare_normal_information(inputs, assignment_for(inputs) if assignment is None else assignment,
        expected_input_identity=normal_input_identity(inputs), declaration=declaration() if declared is None else declared)


@pytest.fixture(scope='module')
def prepared():
    return prepare(fixture())


def current(t=1, demand=25.):
    return info.CurrentGridConditions(t, f'2020-01-01T0{t-1}:00:00+00:00',
        ((1, demand), (2, 0.)), (('G1', 10.),), (('G1', 90.),), (('G1', True),),
        5., 30., 25., 'mechanism_assumption')


def view(prepared, conditions):
    return info.current_grid_information(prepared, conditions, expected_audit_identity=prepared.audit_identity)


def test_current_conditions_are_distinct_from_declared_forecast(prepared):
    result = view(prepared, current())
    assert result.current.demand_by_bus_mw == ((1, 25.), (2, 0.))
    assert result.normal.generation_mw == (('G1', 20.),)
    assert result.current.generator_max_mw == (('G1', 90.),)
    assert result.network.units[0].maximum_power_mw == 100.
    assert result.current.dc_baseline_mw == 5.
    assert prepared.causal_certificate is None and prepared.formal_result is False
    assert result.normal.previous_commitment == (('G1', True),)
    assert result.normal.allowed_plan_identity == prepared.allowed_plan_identity


def test_raw_provenance_and_seed_do_not_enter_allowed_identity():
    inputs = fixture()
    first = prepare(inputs)
    changed = replace(inputs, carry=replace(inputs.carry, identity=replace(inputs.carry.identity,
        outage_seed=999, source_sha256='f'*64, trajectory_id='different-audit-label')))
    second = prepare(changed)
    assert first.audit_identity != second.audit_identity
    assert first.allowed_plan_identity == second.allowed_plan_identity
    assert first.hours == second.hours
    assert view(first, current()) == view(second, current())


@pytest.mark.parametrize('kind', ['reserve', 'flow'])
def test_unused_normal_assignment_details_change_only_audit_identity(kind):
    inputs = fixture()
    assignment = assignment_for(inputs)
    first = prepare(inputs, assignment)
    if kind == 'reserve':
        assignment['reserve_up[0,G1]'] = 1.
    else:
        assignment['branch_flow[normal,0,AC1]'] = 1.
        assignment['dc_flow[normal,0,DC1]'] = -1.
        assignment['angle_degrees[normal,0,2]'] = -degrees(.001)
    second = prepare(inputs, assignment)
    assert first.audit_identity != second.audit_identity
    assert first.allowed_plan_identity == second.allowed_plan_identity
    assert first.hours == second.hours


def test_future_declared_forecast_is_part_of_origin_information():
    inputs = fixture()
    first = prepare(inputs)
    points = inputs.data.hourly_points[:-1]+(replace(inputs.data.hourly_points[-1], demand_by_bus_mw={1: 30., 2: 0.}),)
    changed = replace(inputs, data=replace(inputs.data, hourly_points=points),
        request=replace(inputs.request, system_demand_by_bus_mw=tuple(p.demand_by_bus_mw for p in points)))
    second = prepare(changed)
    assert first.allowed_plan_identity != second.allowed_plan_identity
    assert first.hours[0].generation_mw == second.hours[0].generation_mw
    assert second.hours[2].generation_mw == (('G1', 30.),)


@pytest.mark.parametrize('changes', [{'category': 'Gas CT'}, {'ramp_mw_per_minute': 2.}])
def test_normal_reserve_eligibility_parameters_are_bound(changes):
    inputs = fixture()
    first = prepare(inputs)
    changed = replace(inputs, data=replace(inputs.data,
        generators=(replace(inputs.data.generators[0], **changes),)))
    second = prepare(changed)
    assert first.allowed_plan_identity != second.allowed_plan_identity
    assert first.hours[0].generation_mw == second.hours[0].generation_mw


def test_inherited_unconstructible_reserve_case_produces_no_information():
    inputs = fixture()
    assignment = assignment_for(inputs)
    changed = replace(inputs, data=replace(inputs.data,
        generators=(replace(inputs.data.generators[0], category='Other'),)))
    # Existing normal backend has no symbolic reserve expression when an area
    # has no eligible unit. Preserve its explicit failure, never issue a view.
    with pytest.raises(ValueError, match='trivial Boolean'):
        info.prepare_normal_information(changed, assignment,
            expected_input_identity=normal_input_identity(changed), declaration=declaration())


def test_static_disabled_unit_cannot_be_enabled_by_current_report():
    inputs = fixture()
    disabled = replace(inputs.data.generators[0], uid='G2', dispatch_mode='disabled',
        enabled=False, disabled_reason='mechanism_disabled')
    points = tuple(replace(p, generator_min_mw={'G1': 10., 'G2': 0.},
        generator_max_mw={'G1': 100., 'G2': 0.}) for p in inputs.data.hourly_points)
    origin = replace(inputs.initial, commitment={'G1': True, 'G2': False},
        generation_mw={'G1': 20., 'G2': 0.}, time_in_state_hours={'G1': 1, 'G2': 0})
    inputs = replace(inputs, data=replace(inputs.data, generators=(*inputs.data.generators, disabled), hourly_points=points),
        initial=origin, request=replace(inputs.request, initial_commitment=origin.commitment,
            initial_generation_mw=origin.generation_mw, initial_time_in_state_hours=origin.time_in_state_hours,
            generator_availability=({'G1': True, 'G2': False},)*3))
    plan = prepare(inputs)
    conditions = replace(current(), generator_min_mw=(('G1', 10.), ('G2', 0.)),
        generator_max_mw=(('G1', 90.), ('G2', 0.)), generator_available=(('G1', True), ('G2', False)))
    assert view(plan, conditions).normal.commitment == (('G1', True), ('G2', False))
    with pytest.raises(ValueError, match='statically disabled'):
        view(plan, replace(conditions, generator_available=(('G1', True), ('G2', True))))


def test_current_input_projection_does_not_read_future_reports(prepared):
    reports = (current(1), current(2), current(3))
    altered = reports[:2]+(current(3, demand=70.),)
    left = tuple(view(prepared, c) for c in reports)
    right = tuple(view(prepared, c) for c in altered)
    assert left[:2] == right[:2]
    assert left[2] != right[2]
    assert left == tuple(view(prepared, c) for c in reports[:1])+tuple(view(prepared, c) for c in reports[1:])


def test_first_hour_prior_uses_initial_not_current_commitment():
    inputs = fixture(committed=False, age=3)
    result = prepare(inputs)
    assert result.hours[0].previous_commitment == (('G1', False),)
    assert result.hours[0].commitment == (('G1', True),)
    assert result.hours[1].previous_commitment == (('G1', True),)


def test_policy_view_has_no_audit_source_or_full_future_arrays(prepared):
    result = view(prepared, current())
    payload = json.dumps(asdict(result), allow_nan=False)
    for forbidden in ('source_input_identity', 'normal_assignment_identity', 'normal_witness',
                      'source_sha256', 'outage_seed', 'event_id', 'end_hour_exclusive', 'hourly_points'):
        assert forbidden not in payload
    assert prepared.source_input_identity not in payload
    assert prepared.audit_identity not in payload
    assert set(asdict(result)) == {'contract', 'network', 'normal', 'current'}


@pytest.mark.parametrize('fault', ['missing', 'balance', 'nan'])
def test_bad_complete_normal_assignment_produces_no_view(fault):
    inputs = fixture()
    assignment = assignment_for(inputs)
    if fault == 'missing':
        del assignment['reserve_up[0,G1]']
    else:
        assignment['generation[normal,0,G1]'] = float('nan') if fault == 'nan' else 21.
    with pytest.raises(ValueError):
        prepare(inputs, assignment)


def test_source_and_prepared_identities_fail_closed(prepared):
    inputs = fixture()
    with pytest.raises(ValueError, match='source identity'):
        info.prepare_normal_information(inputs, assignment_for(inputs), expected_input_identity='0'*64,
            declaration=declaration())
    with pytest.raises(ValueError, match='audit identity'):
        info.current_grid_information(prepared, current(), expected_audit_identity='0'*64)


@pytest.mark.parametrize('changes', [{'issued_at_source_hour': 1}, {'forecast_rule': 'observed_forecast'},
    {'plan_rule': 'future_outage_selected'}, {'evidence_role': 'observed'}, {'issued_at_source_hour': True}])
def test_information_declaration_is_explicit_and_before_episode(changes):
    with pytest.raises(ValueError):
        prepare(fixture(), declared=replace(declaration(), **changes))


@pytest.mark.parametrize('changes', [
    {'source_hour': 4}, {'timestamp': '2020-01-02T00:00:00+00:00'},
    {'demand_by_bus_mw': ((1, 20.),)},
    {'generator_min_mw': (('other', 10.),), 'generator_max_mw': (('other', 90.),), 'generator_available': (('other', True),)},
    {'generator_max_mw': (('G1', 101.),)}, {'generator_min_mw': (('G1', 9.),)},
    {'generator_available': (('G1', 1),)}, {'dc_baseline_mw': 26.},
    {'dc_baseline_mw': float('nan')}, {'demand_by_bus_mw': ((True, 20.), (2, 0.))},
    {'generator_min_mw': (('G1', 95.),)}, {'evidence_role': 'observed'},
])
def test_invalid_current_input_cannot_enter_kernel(prepared, changes):
    with pytest.raises(ValueError):
        view(prepared, replace(current(), **changes))


def test_unavailable_base_report_remains_separate_from_plan(prepared):
    result = view(prepared, replace(current(), generator_available=(('G1', False),)))
    assert result.current.generator_available == (('G1', False),)
    assert result.normal.commitment == (('G1', True),)
    assert result.network.units[0].enabled


def test_caller_mutation_after_preparation_cannot_change_output():
    inputs = fixture()
    assignment = assignment_for(inputs)
    result = prepare(inputs, assignment)
    identity = result.audit_identity
    inputs.data.hourly_points[0].demand_by_bus_mw[1] = 999.
    assignment['generation[normal,0,G1]'] = 999.
    assert result.audit_identity == identity
    assert result.hours[0].generation_mw == (('G1', 20.),)


def test_owned_outputs_and_runtime_contract(prepared, monkeypatch):
    result = view(prepared, current())
    identity = result.visible_identity
    with pytest.raises(TypeError):
        replace(prepared, formal_result=True)
    with pytest.raises(TypeError):
        replace(result.normal, generation_mw=(('G1', 1.),))
    monkeypatch.setattr(info, 'CONTRACT', 'changed')
    assert result.visible_identity == identity
    with pytest.raises(ValueError, match='contract drift'):
        view(prepared, current())
