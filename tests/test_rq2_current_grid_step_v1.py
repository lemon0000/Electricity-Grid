from dataclasses import replace
from fractions import Fraction

import pytest
from pyomo.environ import Var

from test_rq2_continuous_grid_normal_v1 import fixture, assignment_for
from test_rq2_grid_information_v1 import prepare, current, view
from src.rq2_joint_deliverability_boundary_v1 import current_grid_step as step
from src.rq2_joint_deliverability_boundary_v1.event_disclosure import (
    OutageComponent, DisclosureProtocol, CurrentOutageReport,
    initialize_disclosure, disclose_current)


G = OutageComponent('generator', 'G1')
B = OutageComponent('branch', 'AC1')


def protocol():
    return step.CurrentGridProtocol('fixed_normal_commitment__outage_as_availability',
        'committable_only_actual_ramp__explicit_generator_repair_cap',
        'fixed_base_availability_for_episode', 'realtime_reserve_unregistered_not_modeled',
        'current_report_only__declared_pre_episode_normal_plan', 'mechanism_assumption')


def prepared(ramp=60.):
    inputs = fixture()
    inputs = replace(inputs, data=replace(inputs.data, generators=(replace(inputs.data.generators[0],
        ramp_mw_per_hour=ramp, ramp_mw_per_minute=ramp/60.),)),
        carry=replace(inputs.carry, limits=(replace(inputs.carry.limits[0], ramp_mw_per_hour=ramp),)))
    return prepare(inputs)


def origin(info, active=None, generation=20., components=(B, G)):
    declared = DisclosureProtocol(components,
        'current_n1_outage_overlay_revealed_before_current_action',
        'complete_current_n1_outage_overlay__no_hidden_same_hour_replacement', 'mechanism_assumption')
    disclosure = initialize_disclosure(declared, source_hour=0, active_component=active)
    return step.initialize_actual_carry(info, disclosure, protocol=protocol(),
        generation_mw=(('G1', generation),), base_availability=(('G1', True),),
        evidence_role='mechanism_assumption')


def power(t=1, mw=0):
    q = Fraction(str(mw))
    return step.PrescribedDcPower(t, str(q.numerator), str(q.denominator), 'mechanism_assumption')


def audit(info, before, dc, generation, active=None, cap=None, changes=None):
    disclosure = disclose_current(before.disclosure, CurrentOutageReport(info.current.source_hour, active, cap))
    identity = step.current_step_identity(info, disclosure, before, dc)
    model = step.build_current_grid_model(info, disclosure, before, dc, expected_identity=identity)
    assignment = {v.name: 0. for v in model.component_data_objects(Var)}
    assignment['generation[G1]'] = generation
    assignment.update(changes or {})
    return step.audit_current_grid_assignment(info, disclosure, before, dc, assignment, expected_identity=identity)


@pytest.mark.parametrize('dc,generation,valid', [(20, 30., True), (21, 31., False)])
def test_analytic_ramp_boundary(dc, generation, valid):
    info = view(prepared(10.), current(demand=10.))
    before = origin(info)
    result = audit(info, before, power(mw=dc), generation)
    assert result.physical_assignment_valid is valid
    assert (result.next_carry is not None) is valid
    assert before.source_hour == 0
    assert result.causal_certificate is None and result.infeasibility_certificate is None
    assert not result.formal_result and not result.security_certified


@pytest.mark.parametrize('cap,valid', [(10., True), (9., False)])
def test_repair_return_limit_is_current_and_binding(cap, valid):
    info = view(prepared(), current(demand=10.))
    before = origin(info, active=G, generation=0.)
    result = audit(info, before, power(), 10., cap=cap)
    assert result.physical_assignment_valid is valid
    assert (result.next_carry is not None) is valid


def test_trip_exempts_only_forced_down_ramp():
    info = view(prepared(4.), current(demand=0.))
    before = origin(info)
    result = audit(info, before, power(), 0., active=G)
    assert result.physical_assignment_valid
    assert result.next_carry.effective_availability == (('G1', False),)
    assert result.next_carry.planned_commitment == (('G1', True),)
    assert not audit(info, before, power(), 0.).physical_assignment_valid


def test_actual_previous_generation_not_normal_plan_controls_next_ramp():
    plan = prepared(10.)
    first = view(plan, current(demand=30.))
    carry = audit(first, origin(first), power(), 30.).next_carry
    second = view(plan, current(2, demand=10.))
    result = audit(second, carry, power(2), 10.)
    assert not result.physical_assignment_valid
    assert result.maximum_exact_violation == 10.
    assert result.next_carry is None and carry.source_hour == 1


def test_three_hour_actual_carry_and_repeated_audit_are_identical():
    plan = prepared()
    info = view(plan, current(demand=20.))
    before = origin(info)
    for t in (1, 2, 3):
        info = view(plan, current(t, demand=20.))
        result = audit(info, before, power(t, 5), 25.)
        repeated = audit(info, before, power(t, 5), 25.)
        assert result == repeated and result.physical_assignment_valid
        assert result.next_carry.predecessor_identity
        before = result.next_carry
    assert before.source_hour == 3


@pytest.mark.parametrize('changes', [{'angle_degrees[1]': 1.}, {'branch_flow[AC1]': 101.},
                                   {'dc_flow[DC1]': 101.}, {'generation[G1]': 19.}])
def test_invalid_complete_assignment_never_produces_carry(changes):
    info = view(prepared(), current(demand=20.))
    assert audit(info, origin(info), power(), 20., changes=changes).next_carry is None


def test_branch_outage_zero_flow_and_remote_balance():
    info = view(prepared(), replace(current(demand=10.), demand_by_bus_mw=((1, 10.), (2, 10.))))
    before = origin(info)
    # DC branch can supply the remote bus; the outaged AC branch cannot.
    good = audit(info, before, power(), 20., active=B, changes={'dc_flow[DC1]': 10.})
    bad = audit(info, before, power(), 20., active=B, changes={'branch_flow[AC1]': 10.})
    assert good.physical_assignment_valid and bad.next_carry is None


def test_base_availability_transition_is_not_silently_a_trip():
    plan = prepared()
    first = view(plan, current(demand=20.))
    before = origin(first)
    changed = view(plan, replace(current(demand=20.), generator_available=(('G1', False),)))
    with pytest.raises(ValueError, match='base availability transition'):
        audit(changed, before, power(), 0.)


@pytest.mark.parametrize('dc', [26, 31])
def test_power_above_connected_or_physical_limit_rejected(dc):
    info = view(prepared(), current(demand=20.))
    with pytest.raises(ValueError, match='physical or connected'):
        audit(info, origin(info), power(mw=dc), 20.+dc)


def test_wrong_hour_and_missing_current_repair_report_rejected():
    info = view(prepared(), current(demand=20.))
    with pytest.raises(ValueError, match='clock'):
        audit(info, origin(info), power(2), 20.)
    with pytest.raises(ValueError):
        audit(info, origin(info, active=G, generation=0.), power(), 20.)


def test_unknown_origin_component_rejected_before_carry():
    info = view(prepared(), current(demand=20.))
    other = OutageComponent('generator', 'unknown')
    with pytest.raises(ValueError, match='inventory'):
        origin(info, active=other, components=(other,))


@pytest.mark.parametrize('numerator,denominator', [('2', '2'), ('-1', '1'), ('1', '0'),
    ('1'+'0'*400, '1'), ('1', '1'+'0'*400)])
def test_invalid_or_unrepresentable_exact_power(numerator, denominator):
    with pytest.raises(ValueError):
        step.PrescribedDcPower(1, numerator, denominator, 'mechanism_assumption')


@pytest.mark.parametrize('name,new', [('TOLERANCE', 1e-5), ('CONTRACT', 'changed')])
def test_contract_drift_stops_audit(monkeypatch, name, new):
    info = view(prepared(), current(demand=20.))
    before = origin(info)
    monkeypatch.setattr(step, name, new)
    with pytest.raises(ValueError, match='drift'):
        audit(info, before, power(), 20.)


def test_exact_power_residual_survives_float_projection():
    info = view(prepared(), current(demand=20.))
    result = audit(info, origin(info), power(mw='17.800000000000002'), 37.799999)
    assert result.maximum_exact_violation > 1e-6
    assert 'current_grid_exact_violation' in result.errors and result.next_carry is None


def test_caller_cannot_construct_or_replace_actual_state():
    with pytest.raises(TypeError):
        step.ActualStepCarry()
    info = view(prepared(), current(demand=20.))
    with pytest.raises(TypeError):
        replace(origin(info), source_hour=7)


@pytest.mark.parametrize('mutation', ['missing', 'extra', 'nan', 'wrong_identity'])
def test_assignment_and_identity_errors_are_not_physical_failures(mutation):
    info = view(prepared(), current(demand=20.))
    before = origin(info)
    dc = power()
    disclosure = disclose_current(before.disclosure, CurrentOutageReport(1, None, None))
    identity = step.current_step_identity(info, disclosure, before, dc)
    model = step.build_current_grid_model(info, disclosure, before, dc, expected_identity=identity)
    assignment = {v.name: 0. for v in model.component_data_objects(Var)}
    assignment['generation[G1]'] = 20.
    if mutation == 'missing':
        del assignment['dc_flow[DC1]']
    elif mutation == 'extra':
        assignment['unknown'] = 0.
    elif mutation == 'nan':
        assignment['generation[G1]'] = float('nan')
    else:
        identity = '0'*64
    with pytest.raises(ValueError):
        step.audit_current_grid_assignment(info, disclosure, before, dc, assignment, expected_identity=identity)
    assert before.source_hour == 0


def test_changed_plan_cannot_splice_actual_carry():
    first = view(prepared(), current(demand=20.))
    before = origin(first)
    other = view(prepared(10.), current(demand=20.))
    with pytest.raises(ValueError, match='network/plan/clock'):
        audit(other, before, power(), 20.)


def test_repair_cap_above_nameplate_is_input_error():
    info = view(prepared(), current(demand=20.))
    with pytest.raises(ValueError, match='nameplate'):
        audit(info, origin(info, active=G, generation=0.), power(), 20., cap=101.)


def test_mid_audit_contract_change_cannot_issue_carry(monkeypatch):
    info = view(prepared(), current(demand=20.))
    before = origin(info)
    original = step._exact_residual
    def changed(*args):
        result = original(*args)
        monkeypatch.setattr(step, 'TOLERANCE', 1e-5)
        return result
    monkeypatch.setattr(step, '_exact_residual', changed)
    with pytest.raises(ValueError, match='drift'):
        audit(info, before, power(), 20.)


def test_one_generator_returns_while_another_trips_same_hour():
    inputs = fixture()
    g1 = inputs.data.generators[0]
    initial = replace(inputs.initial, commitment={'G1': True, 'G2': True},
        generation_mw={'G1': 10., 'G2': 10.}, time_in_state_hours={'G1': 1, 'G2': 1})
    points = tuple(replace(p, generator_min_mw={'G1': 10., 'G2': 10.},
        generator_max_mw={'G1': 100., 'G2': 100.}) for p in inputs.data.hourly_points)
    inputs = replace(inputs, data=replace(inputs.data, generators=(g1, replace(g1, uid='G2')),
        hourly_points=points), initial=initial,
        carry=replace(inputs.carry, limits=(inputs.carry.limits[0], replace(inputs.carry.limits[0], uid='G2')),
            points=(replace(inputs.carry.points[0], generation_mw=10.),
                replace(inputs.carry.points[0], uid='G2', generation_mw=10.)), elapsed_state_hours=(1, 1)),
        request=replace(inputs.request, initial_commitment=initial.commitment,
            initial_generation_mw=initial.generation_mw, initial_time_in_state_hours=initial.time_in_state_hours,
            generator_availability=({'G1': True, 'G2': True},)*3))
    assignment = assignment_for(inputs)
    for t in range(3):
        assignment[f'generation[normal,{t},G1]'] = 10.
        assignment[f'generation[normal,{t},G2]'] = 10.
        assignment[f'commitment[{t},G2]'] = 1.
        assignment[f'segment_power[{t},G1,0]'] = 0.
    plan = prepare(inputs, assignment)
    conditions = replace(current(demand=10.), generator_min_mw=(('G1', 10.), ('G2', 10.)),
        generator_max_mw=(('G1', 100.), ('G2', 100.)), generator_available=(('G1', True), ('G2', True)))
    info = view(plan, conditions)
    g2 = OutageComponent('generator', 'G2')
    declared = DisclosureProtocol((G, g2), 'current_n1_outage_overlay_revealed_before_current_action',
        'complete_current_n1_outage_overlay__no_hidden_same_hour_replacement', 'mechanism_assumption')
    incoming = initialize_disclosure(declared, source_hour=0, active_component=G)
    before = step.initialize_actual_carry(info, incoming, protocol=protocol(),
        generation_mw=(('G1', 0.), ('G2', 20.)), base_availability=(('G1', True), ('G2', True)),
        evidence_role='mechanism_assumption')
    result = audit(info, before, power(), 10., active=g2, cap=10.)
    assert result.physical_assignment_valid
    assert result.next_carry.effective_availability == (('G1', True), ('G2', False))
    assert result.next_carry.generation_mw == (('G1', 10.), ('G2', 0.))


@pytest.mark.parametrize('startup', [True, False])
def test_planned_startup_and_shutdown_allowance(startup):
    inputs = fixture(committed=not startup, age=3, demand=20. if startup else 0.)
    inputs = replace(inputs, data=replace(inputs.data, generators=(replace(inputs.data.generators[0],
        ramp_mw_per_hour=4., ramp_mw_per_minute=4./60.),)),
        carry=replace(inputs.carry, limits=(replace(inputs.carry.limits[0], ramp_mw_per_hour=4.),)))
    plan = prepare(inputs, assignment_for(inputs, states=(startup,)*3))
    info = view(plan, current(demand=20. if startup else 0.))
    before = origin(info, generation=0. if startup else 20.)
    result = audit(info, before, power(), 20. if startup else 0.)
    assert result.physical_assignment_valid
    assert result.next_carry.planned_commitment == (('G1', startup),)


@pytest.mark.parametrize('mode,lower,outage,reject', [
    ('fixed', 0., False, True), ('fixed', 5., False, False), ('fixed', 0., True, False),
    ('curtailable', 0., False, False), ('disabled', 0., False, False)])
def test_noncommittable_current_bounds_have_explicit_semantics(mode, lower, outage, reject):
    base = fixture(1)
    enabled = mode != 'disabled'
    initial_power = 5. if enabled else 0.
    g2 = replace(base.data.generators[0], uid='G2', dispatch_mode=mode, enabled=enabled,
        p_min_mw=0., p_max_mw=5., category='Solar PV')
    point = replace(base.data.hourly_points[0], generator_min_mw={'G1': 10., 'G2': initial_power},
        generator_max_mw={'G1': 100., 'G2': initial_power})
    initial = replace(base.initial, commitment={'G1': True, 'G2': enabled},
        generation_mw={'G1': 20.-initial_power, 'G2': initial_power}, time_in_state_hours={'G1': 1, 'G2': 0})
    inputs = replace(base, data=replace(base.data, generators=(*base.data.generators, g2), hourly_points=(point,)),
        initial=initial, carry=replace(base.carry, points=(replace(base.carry.points[0], generation_mw=20.-initial_power),)),
        request=replace(base.request, generator_availability=({'G1': True, 'G2': enabled},),
            initial_commitment=initial.commitment, initial_generation_mw=initial.generation_mw,
            initial_time_in_state_hours=initial.time_in_state_hours))
    assignment = assignment_for(inputs)
    assignment['generation[normal,0,G2]'] = initial_power
    assignment['generation[normal,0,G1]'] = 20.-initial_power
    assignment['segment_power[0,G1,0]'] = 10.-initial_power
    plan = prepare(inputs, assignment)
    conditions = replace(current(demand=20.), generator_min_mw=(('G1', 10.), ('G2', lower)),
        generator_max_mw=(('G1', 100.), ('G2', 5.)), generator_available=(('G1', True), ('G2', enabled)))
    info = view(plan, conditions)
    other = OutageComponent('generator', 'G2')
    declared = DisclosureProtocol((G, other) if enabled else (G,),
        'current_n1_outage_overlay_revealed_before_current_action',
        'complete_current_n1_outage_overlay__no_hidden_same_hour_replacement', 'mechanism_assumption')
    incoming = initialize_disclosure(declared, source_hour=0, active_component=None)
    before = step.initialize_actual_carry(info, incoming, protocol=protocol(),
        generation_mw=tuple(sorted(initial.generation_mw.items())), base_availability=conditions.generator_available,
        evidence_role='mechanism_assumption')
    if reject:
        with pytest.raises(ValueError, match='fixed generator requires equal current bounds'):
            audit(info, before, power(), 15., changes={'generation[G2]': 5.})
    else:
        actual = 0. if outage or not enabled else (5. if mode == 'fixed' else 3.)
        result = audit(info, before, power(), 20.-actual, active=other if outage else None,
            changes={'generation[G2]': actual})
        assert result.physical_assignment_valid
        assert dict(result.next_carry.generation_mw)['G2'] == actual
