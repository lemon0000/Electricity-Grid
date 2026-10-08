from dataclasses import replace
from fractions import Fraction as Q

import pytest
from pyomo.environ import Constraint, Var, value

from src.rq2_joint_deliverability_boundary_v1.boundary import BoundaryAnchor, ContinuationHour
from src.rq2_joint_deliverability_boundary_v1.causal_policy import CurrentObservation, HourlyLimits
from src.rq2_joint_deliverability_boundary_v1.capacity_policy import CapacityObservation
from src.rq2_joint_deliverability_boundary_v1.continuous_planner import (
    ContinuousPlanningScenario, ContinuousPlanningInputs, GRID_EXCESS, REQUEST_BOUNDED, OFFLINE,
    build_continuous_planning_model as build, planner_identity,
)
from src.rq2_joint_deliverability_boundary_v1.four_arm_replay import NETWORK, CFE, JOINT, B6


def scenario(g=(.25,), c=None, due=None, name='s', **changes):
    c = tuple(0. for _ in g) if c is None else c
    due = tuple(t+4 if g[t]+c[t] else None for t in range(len(g))) if due is None else due
    anchor = BoundaryAnchor(JOINT, 'shared', 'training', 0, 100, 'power-'+name, 'work-'+name,
                            '1'*64, 0, '2'*64, '3'*64)
    observations = []
    for t, (grid, cfe) in enumerate(zip(g, c, strict=True)):
        hour = ContinuationHour(**dict(anchor.__dict__, power_source_hour=t+1, workload_source_hour=101+t),
            grid_request=grid, cfe_request=cfe, workload_occupancy=changes.get('baseline', 1.))
        limits = HourlyLimits(changes.get('call_limit', 1.), changes.get('business', 1.),
                             changes.get('cfe_surplus', 1.), changes.get('recovery_cap', 1.))
        observations.append(CapacityObservation(CurrentObservation(hour, limits, due[t]), changes.get('available', 1.)))
    return ContinuousPlanningScenario(name, anchor, tuple(observations))


def inputs(s=None, **changes):
    data = dict(scenarios=(scenario() if s is None else s,), service_action_mode=REQUEST_BOUNDED,
        decision_information_mode=OFFLINE, accounting_period_id='synthetic-period', period_mode='single_nonrolling',
        initialization_mode='canonical_zero_period_start', terminal_mode='open_carry', maximum_capacity=1.,
        minimum_event_power=.01, response_time_hours=1., curtailment_ramp_per_hour=1., maximum_recovery_power=1.,
        recovery_efficiency=.8, maximum_event_duration_hours=3., maximum_event_count=3,
        minimum_recovery_hours=2., normalized_energy_budget=2., normalized_debt_limit=2.)
    return ContinuousPlanningInputs(**dict(data, **changes))


def assign(model, *, grid=None, cfe=None, recovery=None, allocations=None, capacity=None):
    """Install a hand-declared trajectory using an independent exact ledger.

    This is an assignment helper, not an optimizer or acceptance certificate.
    """
    grid, cfe, recovery, allocations = grid or {}, cfe or {}, recovery or {}, allocations or {}
    for var in model.component_data_objects(Var):
        var.set_value(0., skip_validation=True)
    peak = Q(0)
    for s in model._continuous_inputs.scenarios:
        g, c = [], []
        for t, obs in enumerate(s.observations):
            raw = obs.observation.hour
            default_g = raw.grid_request if model._continuous_arm != CFE and raw.grid_request > 1e-6 else 0.
            default_c = raw.cfe_request if model._continuous_arm != NETWORK and raw.cfe_request > 1e-6 else 0.
            g.append(Q(str(grid.get((s.name, t), default_g))))
            c.append(Q(str(cfe.get((s.name, t), default_c))))
            model.grid_service[s.name, t].set_value(float(g[-1]))
            model.cfe_service[s.name, t].set_value(float(c[-1]))
        for k in model._continuous_tracks:
            remaining, previous_on = {}, False
            for t in range(len(s.observations)):
                q = g[t] if k == 'grid' else c[t] if k == 'cfe' else g[t]+c[t]
                on = q > 0
                peak = max(peak, q)
                idx = (s.name, k, t)
                model.track_call[idx].set_value(float(q))
                model.on[idx].set_value(int(on))
                model.start[idx].set_value(int(on and not previous_on))
                model.stop[idx].set_value(int(previous_on and not on))
                model.recovery[idx].set_value(float(recovery.get(idx, 0.)))
                remaining[t] = q
                for b in range(t+1):
                    item = (s.name, k, b, t)
                    amount = Q(str(allocations.get(item, 0.)))
                    remaining[b] -= amount
                    model.allocation[item].set_value(float(amount), skip_validation=True)
                    model.remaining[item].set_value(float(remaining[b]), skip_validation=True)
                model.debt[idx].set_value(float(sum(remaining.values(), Q(0))), skip_validation=True)
                previous_on = on
    model.capacity.set_value(float(peak if capacity is None else capacity), skip_validation=True)


def violations(model):
    failures = []
    for var in model.component_data_objects(Var):
        x = value(var)
        if ((var.lb is not None and x < value(var.lb)-1e-9)
            or (var.ub is not None and x > value(var.ub)+1e-9)
            or (var.is_integer() and abs(x-round(x)) > 1e-9)):
            failures.append(var.name)
    for constraint in model.component_data_objects(Constraint, active=True):
        body = value(constraint.body)
        if ((constraint.lower is not None and body < value(constraint.lower)-1e-9)
            or (constraint.upper is not None and body > value(constraint.upper)+1e-9)):
            failures.append(constraint.name)
    return failures


@pytest.mark.parametrize('arm,peak', [(NETWORK, .25), (CFE, .125), (JOINT, .375), (B6, .25)])
def test_analytic_four_arm_peak_and_open_terminal(arm, peak):
    model = build(inputs(scenario(g=(.25,), c=(.125,))), arm)
    assign(model)
    assert not violations(model)
    assert value(model.capacity) == peak
    assert all(value(model.debt['s', k, 0]) > 0 for k in model._continuous_tracks)
    model.capacity.set_value(peak-.01)
    assert violations(model)  # peak is also an analytic lower bound for this fixture.
    assert model._continuous_evidence['complete_capacity_upper_bound'] is None
    assert model._continuous_evidence['prefix_capacity_interval'] is None


@pytest.mark.parametrize('horizon', [1, 3, 48])
def test_last_hour_can_be_active_with_positive_debt_at_arbitrary_horizon(horizon):
    model = build(inputs(scenario(g=(0.,)*(horizon-1)+(.125,))), JOINT)
    assign(model)
    assert len(model.points) == horizon and not violations(model)
    assert value(model.on['s', 'shared', horizon-1]) == 1
    assert value(model.debt['s', 'shared', horizon-1]) == .125


def test_hour_24_has_no_reset_or_special_terminal_constraint():
    calls = tuple(.125 if t in (22, 23, 24) else 0. for t in range(25))
    model = build(inputs(scenario(g=calls)), JOINT)
    assign(model)
    assert not violations(model)
    assert value(model.debt['s', 'shared', 24]) == .375
    assert sum(value(model.start['s', 'shared', t]) for t in range(25)) == 1


def test_action_modes_distinguish_minimum_event_counterexample():
    s = scenario(g=(.05,))
    legacy = build(inputs(s, minimum_event_power=.1, service_action_mode=GRID_EXCESS), NETWORK)
    assign(legacy, grid={('s', 0): .1})
    assert not violations(legacy)
    assert value(legacy.debt['s', 'shared', 0]) == .1  # executed excess also creates debt.
    bounded = build(inputs(s, minimum_event_power=.1), NETWORK)
    assign(bounded)
    assert violations(bounded)
    assign(bounded, grid={('s', 0): .1})
    assert any(n.startswith('service[') for n in violations(bounded))
    assert legacy._continuous_planner_id != bounded._continuous_planner_id


@pytest.mark.parametrize('due,amount,accepted', [(2, .25, True), (2, .24, False), (3, .24, True), (None, .24, True)])
def test_exact_recovery_energy_and_due_hour_after_recovery(due, amount, accepted):
    model = build(inputs(scenario(g=(.25, 0.), due=(due, None))), JOINT)
    recovery = float(Q(str(amount))/Q('.8'))
    assign(model, recovery={('s', 'shared', 1): recovery}, allocations={('s', 'shared', 0, 1): amount})
    assert (not violations(model)) == accepted
    if accepted:
        assert abs(value(model.debt['s', 'shared', 1])-(.25-amount)) < 1e-12


def test_late_recovery_cannot_erase_missed_hard_deadline():
    model = build(inputs(scenario(g=(.25, 0., 0.), due=(2, None, None))), JOINT)
    assign(model, recovery={('s', 'shared', 2): .3125}, allocations={('s', 'shared', 0, 2): .25})
    assert value(model.debt['s', 'shared', 2]) == 0
    assert any(n.startswith('deadline[') for n in violations(model))


def test_due_hour_uses_absolute_source_clock_at_nonzero_zero_origin():
    s = scenario(g=(.25, 0.), due=(2, None))
    observations = tuple(replace(o, observation=replace(o.observation,
        hour=replace(o.observation.hour, power_source_hour=o.observation.hour.power_source_hour+48,
            workload_source_hour=o.observation.hour.workload_source_hour+48),
        due_hour=o.observation.due_hour+48 if o.observation.due_hour is not None else None)) for o in s.observations)
    s = replace(s, anchor=replace(s.anchor, power_source_hour=48, workload_source_hour=148), observations=observations)
    model = build(inputs(s), JOINT)
    assign(model, recovery={('s', 'shared', 1): .3125}, allocations={('s', 'shared', 0, 1): .25})
    assert len(model.deadline) == 1 and not violations(model)


def test_tiny_continuous_recovery_is_labelled_relaxation_not_physical_certificate():
    model = build(inputs(scenario(g=(.125, 0.), due=(4, None))), JOINT)
    assign(model, recovery={('s', 'shared', 1): .0000005}, allocations={('s', 'shared', 0, 1): .0000004})
    assert not violations(model)
    evidence = model._continuous_evidence
    assert evidence['recovery_representation'] == 'continuous_nonnegative_recovery_relaxation'
    assert evidence['relaxed_prefix_capacity_interval'] is None
    assert evidence['prefix_capacity_interval'] is None and evidence['complete_capacity_upper_bound'] is None


def test_no_future_borrowing_double_efficiency_or_same_hour_active_recovery():
    model = build(inputs(scenario(g=(.25, 0.), due=(2, None))), JOINT)
    assert ('s', 'shared', 1, 0) not in model.allocation
    assign(model, recovery={('s', 'shared', 1): .3125}, allocations={('s', 'shared', 0, 1): .3125})
    assert violations(model)  # effective energy is .25, not .3125.
    assign(model, recovery={('s', 'shared', 0): .3125}, allocations={('s', 'shared', 0, 0): .25})
    assert any(n.startswith('temporal[') for n in violations(model))


def test_two_cohorts_with_distinct_deadlines_cannot_be_swapped():
    model = build(inputs(scenario(g=(.125, .125, 0., 0.), due=(3, 4, None, None))), JOINT)
    recoveries = {('s', 'shared', 2): .15625, ('s', 'shared', 3): .15625}
    correct = {('s', 'shared', 0, 2): .125, ('s', 'shared', 1, 3): .125}
    assign(model, recovery=recoveries, allocations=correct)
    assert not violations(model)
    swapped = {('s', 'shared', 1, 2): .125, ('s', 'shared', 0, 3): .125}
    assign(model, recovery=recoveries, allocations=swapped)
    assert any(n.startswith('deadline[') for n in violations(model))


def test_b6_separate_recovery_is_not_shared_execution():
    s = scenario(g=(.25, 0.), c=(0., .125), due=(2, 4))
    b6 = build(inputs(s), B6)
    assign(b6, recovery={('s', 'grid', 1): .3125}, allocations={('s', 'grid', 0, 1): .25})
    assert not violations(b6)
    shared = build(inputs(s), JOINT)
    assign(shared, recovery={('s', 'shared', 1): .3125}, allocations={('s', 'shared', 0, 1): .25})
    assert any(n.startswith('temporal[') for n in violations(shared))


@pytest.mark.parametrize('change', [dict(available=.2), dict(call_limit=.2), dict(baseline=.2)])
def test_current_call_envelopes_bind(change):
    model = build(inputs(scenario(**change)), JOINT)
    assign(model)
    assert any(n.startswith('service[') for n in violations(model))


def test_b6_combined_connected_demand_is_still_shared():
    model = build(inputs(scenario(g=(.25,), c=(.25,), baseline=.4)), B6)
    assign(model)
    assert any(n.startswith('service[') for n in violations(model))


@pytest.mark.parametrize('change', [dict(business=.2), dict(cfe_surplus=.2), dict(recovery_cap=.2)])
def test_current_recovery_headrooms_bind(change):
    model = build(inputs(scenario(g=(.25, 0.), **change)), JOINT)
    assign(model, recovery={('s', 'shared', 1): .3125}, allocations={('s', 'shared', 0, 1): .25})
    assert any(n.startswith('temporal[') for n in violations(model))


def test_network_recovery_does_not_require_cfe_surplus():
    model = build(inputs(scenario(g=(.25, 0.), cfe_surplus=0.)), NETWORK)
    assign(model, recovery={('s', 'shared', 1): .3125}, allocations={('s', 'shared', 0, 1): .25})
    assert not violations(model)


@pytest.mark.parametrize('case', ['ramp', 'response', 'duration', 'rest', 'count', 'energy', 'debt', 'maximum_recovery'])
def test_remaining_temporal_limits_bind(case):
    calls, settings = (.125,), {}
    if case == 'ramp': settings['curtailment_ramp_per_hour'] = .1
    if case == 'response': settings['response_time_hours'] = .1
    if case == 'duration': calls = (.125,)*4
    if case == 'rest': calls = (.125, 0., .125)
    if case == 'count': calls = (.125, 0., 0., .125); settings['maximum_event_count'] = 1
    if case == 'energy': calls = (.125,)*3; settings['normalized_energy_budget'] = .25
    if case == 'debt': settings['normalized_debt_limit'] = .1
    if case == 'maximum_recovery': calls = (.25, 0.); settings['maximum_recovery_power'] = .2
    model = build(inputs(scenario(g=calls), **settings), JOINT)
    if case == 'maximum_recovery':
        assign(model, recovery={('s', 'shared', 1): .3125}, allocations={('s', 'shared', 0, 1): .25})
    else:
        assign(model)
    assert violations(model)


def test_scenarios_share_capacity_and_have_no_probability_claim():
    contract = inputs(scenarios=(scenario(g=(.125,), name='a'), scenario(g=(.375,), name='b')))
    model = build(contract, NETWORK)
    assign(model)
    assert not violations(model) and value(model.capacity) == .375
    model.capacity.set_value(.125)
    assert violations(model)
    assert model._continuous_evidence['causal_policy_capacity_certificate'] is None


@pytest.mark.parametrize('kind', ['duration', 'rest'])
def test_fractional_time_boundaries_use_exact_step_rule(kind):
    if kind == 'duration':
        s = scenario(g=(.125, .125, .125))
        exact, near = dict(maximum_event_duration_hours=3.), dict(maximum_event_duration_hours=2.9999999)
    else:
        s = scenario(g=(.125, 0., 0., .125), due=(10, None, None, 10))
        exact, near = dict(minimum_recovery_hours=2.), dict(minimum_recovery_hours=2.0000001)
    valid, invalid = build(inputs(s, **exact), JOINT), build(inputs(s, **near), JOINT)
    assign(valid); assign(invalid)
    assert not violations(valid) and violations(invalid)
    assert invalid._continuous_evidence['temporal_step_rule'] == 'exact_fraction_floor_duration_ceil_rest'


@pytest.mark.parametrize('change', [dict(service_action_mode=None), dict(decision_information_mode='registered_causal_policy'),
    dict(initialization_mode='nonzero_carry'), dict(period_mode='rolling_24h'), dict(terminal_mode='zero_debt'),
    dict(time_step_hours=.5), dict(maximum_event_count=True), dict(minimum_event_power=1e-6),
    dict(maximum_capacity=1.1), dict(recovery_efficiency=0.), dict(maximum_recovery_power=float('nan')),
    dict(recovery_representation='effective_threshold_recovery')])
def test_unsupported_or_invalid_scientific_contract_fails_closed(change):
    with pytest.raises(ValueError):
        inputs(**change)


@pytest.mark.parametrize('fault', ['holdout', 'clock', 'trace', 'duplicates', 'horizons', 'mutable'])
def test_source_and_scenario_inventory_validation(fault):
    s = scenario(g=(.125, .125))
    with pytest.raises(ValueError):
        if fault == 'holdout':
            replace(s, anchor=replace(s.anchor, split='holdout'))
        elif fault in ('clock', 'trace'):
            h = s.observations[1].observation.hour
            h = replace(h, **({'power_source_hour': 99} if fault == 'clock' else {'workload_trace_id': 'other'}))
            second = replace(s.observations[1], observation=replace(s.observations[1].observation, hour=h))
            replace(s, observations=(s.observations[0], second))
        elif fault == 'duplicates': inputs(scenarios=(s, s))
        elif fault == 'horizons': inputs(scenarios=(s, scenario(name='other')))
        else: replace(s, observations=list(s.observations))


def test_effective_decomposition_gate_is_not_silently_changed():
    s = scenario(g=(.0000005,), c=(.125,))
    with pytest.raises(ValueError, match='decomposition'):
        build(inputs(s), JOINT)
    build(inputs(s, service_action_mode=GRID_EXCESS), JOINT)


def test_identity_binds_modes_sources_period_and_parameters():
    original = inputs()
    variants = [original, replace(original, service_action_mode=GRID_EXCESS),
        replace(original, accounting_period_id='other'), replace(original, normalized_energy_budget=3.),
        replace(original, scenarios=(scenario(name='other'),))]
    identities = {planner_identity(x, JOINT) for x in variants}
    assert len(identities) == len(variants)
