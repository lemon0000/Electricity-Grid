from dataclasses import replace
from fractions import Fraction as Q

import pytest

from test_rq2_continuous_planner_v1 import inputs, scenario
from src.rq2_joint_deliverability_boundary_v1.continuous_planner import GRID_EXCESS, planner_identity
from src.rq2_joint_deliverability_boundary_v1.four_arm_replay import NETWORK, CFE, JOINT, B6
from src.rq2_joint_deliverability_boundary_v1 import planner_witness as w


def candidate(contract, arm=JOINT, capacity=Q(1), *, grid=None, cfe=None, recoveries=None, allocations=None):
    grid, cfe, recoveries, allocations = grid or {}, cfe or {}, recoveries or {}, allocations or {}
    result = []
    for s in contract.scenarios:
        hours = []
        for t, current in enumerate(s.observations):
            raw = current.observation.hour
            g = Q(str(raw.grid_request)) if raw.grid_request > 1e-6 and arm != CFE else Q(0)
            c = Q(str(raw.cfe_request)) if raw.cfe_request > 1e-6 and arm != NETWORK else Q(0)
            g, c = grid.get((s.name, t), g), cfe.get((s.name, t), c)
            tracks = []
            for k in ('grid', 'cfe') if arm == B6 else ('shared',):
                q = g if k == 'grid' else c if k == 'cfe' else g+c
                r = recoveries.get((s.name, k, t), Q(0))
                tracks.append((k, w.PlannerTrackAction(r, Q(str(raw.workload_occupancy))-q+r,
                    allocations.get((s.name, k, t), ()))))
            hours.append(w.PlannerHourAction(g, c, tuple(tracks)))
        result.append((s.name, tuple(hours)))
    return w.PlannerWitnessCandidate(planner_identity(contract, arm), capacity, tuple(result))


def audit(contract, arm=JOINT, **kwargs):
    return w.audit_planner_witness(contract, arm, candidate(contract, arm, **kwargs))


@pytest.mark.parametrize('arm,capacity', [(NETWORK, '.25'), (CFE, '.125'), (JOINT, '.375'), (B6, '.25')])
def test_four_arm_open_prefix_witness_preserves_source_and_exact_debt(arm, capacity):
    contract = inputs(scenario(g=(.25,), c=(.125,)))
    result = audit(contract, arm, capacity=Q(capacity))
    assert result.accepted and result.witness_capacity == Q(capacity)
    row = result.scenarios[0].records[0]
    assert row.original_current is contract.scenarios[0].observations[0]
    assert isinstance(row.executed_request_projection.grid_request, Q)
    if arm == B6:
        assert result.scenarios[0].execution.mode == 'separate_planning'
        assert dict((k, track.ledger.debt) for k, track in result.scenarios[0].execution.tracks) == {'grid': Q('.25'), 'cfe': Q('.125')}
    assert all(status == 'right_censored_before_deadline' for _, _, status in result.scenarios[0].cohort_statuses)
    evidence = result.evidence()
    assert evidence['prefix_upper_bound'] is None and evidence['complete_capacity_upper_bound'] is None
    assert evidence['solver_residual_audit_complete'] is False and evidence['security_certified'] is False


def test_excess_mode_preserves_original_and_executed_amounts():
    contract = inputs(scenario(g=(.05,)), minimum_event_power=.1, service_action_mode=GRID_EXCESS)
    result = audit(contract, grid={('s', 0): Q('.1')}, capacity=Q('.1'))
    assert result.accepted
    row = result.scenarios[0].records[0]
    assert row.original_current.observation.hour.grid_request == .05
    assert row.executed_request_projection.grid_request == Q('.1')
    assert row.candidate_step.cursor.tracks[0][1].ledger.debt == Q('.1')
    bounded = replace(contract, service_action_mode='request_bounded_exact_fulfillment')
    assert not audit(bounded, grid={('s', 0): Q('.1')}).accepted


def test_small_component_is_preserved_inside_active_shared_total():
    contract = inputs(scenario(g=(0.,), c=(.125,)), service_action_mode=GRID_EXCESS)
    result = audit(contract, grid={('s', 0): Q('.0000005')})
    assert result.accepted
    assert result.scenarios[0].execution.tracks[0][1].ledger.debt == Q('.1250005')


@pytest.mark.parametrize('amount', ['0.0000005', '0.000001'])
def test_tiny_recovery_is_rejected_without_effective_rounding(amount):
    contract = inputs(scenario(g=(.25, 0.)))
    r = Q(amount)
    result = audit(contract, recoveries={('s', 'shared', 1): r},
        allocations={('s', 'shared', 1): ((1, Q('.8')*r),)})
    assert not result.accepted and result.witness_capacity is None
    assert 'effective physical threshold' in result.scenarios[0].records[-1].error
    assert result.scenarios[0].execution.tracks[0][1].ledger.debt == Q('.25')


def test_arbitrary_fraction_recovery_is_not_forced_to_decimal_lattice():
    contract = inputs(scenario(g=(.25, 0.)))
    result = audit(contract, recoveries={('s', 'shared', 1): Q(1, 7)},
        allocations={('s', 'shared', 1): ((1, Q(4, 35)),)})
    assert result.accepted
    assert result.scenarios[0].execution.tracks[0][1].ledger.debt == Q(1, 4)-Q(4, 35)


def test_ramp_binds_precomputed_planner_coefficient_without_tolerance():
    contract = inputs(scenario(g=(.029,)), curtailment_ramp_per_hour=.29, response_time_hours=.1)
    result = audit(contract)
    assert not result.accepted
    assert 'ramp/response' in result.scenarios[0].records[0].error
    coefficient = .29*.1
    assert coefficient < .029
    exact_boundary = replace(contract, scenarios=(scenario(g=(coefficient,)),))
    assert audit(exact_boundary).accepted


@pytest.mark.parametrize('due', [2, 3, None])
def test_due_hour_miss_cannot_be_hidden_by_later_recovery(due):
    contract = inputs(scenario(g=(.25, 0., 0.), due=(due, None, None)))
    result = audit(contract, recoveries={('s', 'shared', 1): Q('.30'), ('s', 'shared', 2): Q('.0125')},
        allocations={('s', 'shared', 1): ((1, Q('.24')),), ('s', 'shared', 2): ((1, Q('.01')),)})
    if due == 2:
        assert not result.accepted and len(result.scenarios[0].records) == 2
        failed = result.scenarios[0].records[-1]
        assert failed.stage == 'hard_deadline_validation'
        assert failed.candidate_step.cursor.tracks[0][1].ledger.cohorts[0].missed_at_deadline == Q('.01')
        assert result.scenarios[0].execution == failed.before
    else:
        assert result.accepted and result.scenarios[0].execution.tracks[0][1].ledger.debt == 0
        expected = 'deadline_unidentified' if due is None else 'recovered_by_deadline'
        assert result.scenarios[0].cohort_statuses == (('shared', 1, expected),)


def test_b6_independent_recovery_and_shared_connected_baseline():
    contract = inputs(scenario(g=(.25, 0.), c=(0., .125), due=(2, 4), cfe_surplus=0.))
    result = audit(contract, B6, recoveries={('s', 'grid', 1): Q('.3125')},
        allocations={('s', 'grid', 1): ((1, Q('.25')),)})
    assert result.accepted
    assert result.evidence()['scope'] == 'b6_separate_planning'
    shared = audit(contract, JOINT, recoveries={('s', 'shared', 1): Q('.3125')},
        allocations={('s', 'shared', 1): ((1, Q('.25')),)})
    assert not shared.accepted
    over = audit(inputs(scenario(g=(.25,), c=(.25,), baseline=.4)), B6)
    assert not over.accepted and 'connected baseline' in over.scenarios[0].records[0].error


@pytest.mark.parametrize('change', [dict(available=.1249999), dict(call_limit=.1249999)])
def test_static_limits_are_checked_exactly_not_with_replay_slack(change):
    result = audit(inputs(scenario(g=(.125,), **change)))
    assert not result.accepted and 'call limit' in result.scenarios[0].records[0].error


@pytest.mark.parametrize('kind', ['capacity', 'ramp', 'duration', 'rest', 'count', 'energy', 'debt', 'minimum'])
def test_exact_envelope_constraints_not_delegated_to_tolerant_replay(kind):
    calls, settings, options = (.125,), {}, {}
    if kind == 'capacity': options['capacity'] = Q('.1249999')
    elif kind == 'ramp': calls = (.0500000001,); settings.update(curtailment_ramp_per_hour=.1, response_time_hours=.5)
    elif kind == 'duration': calls = (.125,)*3; settings['maximum_event_duration_hours'] = 2.9999999
    elif kind == 'rest': calls = (.125, 0., 0., .125); settings['minimum_recovery_hours'] = 2.0000001
    elif kind == 'count': calls = (.125, 0., 0., .125); settings['maximum_event_count'] = 1
    elif kind == 'energy': calls = (.125,)*2; settings['normalized_energy_budget'] = .2499999
    elif kind == 'debt': settings['normalized_debt_limit'] = .1249999
    else: settings['minimum_event_power'] = .126
    contract = inputs(scenario(g=calls, due=tuple(10 if g else None for g in calls)), **settings)
    result = audit(contract, **options)
    assert not result.accepted and result.scenarios[0].records[-1].stage == 'exact_action_validation'


@pytest.mark.parametrize('limit', ['business', 'cfe_surplus', 'recovery_cap', 'fixed_max'])
def test_recovery_headroom_caps_are_exact(limit):
    kwargs = {} if limit == 'fixed_max' else {limit: .3124999}
    settings = {'maximum_recovery_power': .3124999} if limit == 'fixed_max' else {}
    contract = inputs(scenario(g=(.25, 0.), **kwargs), **settings)
    result = audit(contract, recoveries={('s', 'shared', 1): Q('.3125')},
        allocations={('s', 'shared', 1): ((1, Q('.25')),)})
    assert not result.accepted and 'headroom' in result.scenarios[0].records[-1].error


@pytest.mark.parametrize('fault', ['power', 'alloc_sum', 'future_birth', 'active_recovery'])
def test_power_and_cohort_conservation_reject_bad_actions(fault):
    contract = inputs(scenario(g=(.25, 0.)))
    r = {('s', 'shared', 1): Q('.3125')}
    a = {('s', 'shared', 1): ((1, Q('.25')),)}
    if fault == 'alloc_sum': a[('s', 'shared', 1)] = ((1, Q('.2499999999')),)
    elif fault == 'future_birth': a[('s', 'shared', 1)] = ((3, Q('.25')),)
    elif fault == 'active_recovery': r = {('s', 'shared', 0): Q('.3125')}; a = {('s', 'shared', 0): ((1, Q('.25')),)}
    cand = candidate(contract, recoveries=r, allocations=a)
    if fault == 'power':
        hours = list(cand.scenarios[0][1])
        track = hours[1].tracks[0][1]
        hours[1] = replace(hours[1], tracks=(('shared', replace(track, actual_service_power=track.actual_service_power+Q('1e-10'))),))
        cand = replace(cand, scenarios=(('s', tuple(hours)),))
    assert not w.audit_planner_witness(contract, JOINT, cand).accepted


@pytest.mark.parametrize('fault', ['id', 'missing_scenario', 'missing_hour', 'wrong_tracks', 'capacity_domain'])
def test_identity_and_complete_inventory(fault):
    contract = inputs()
    cand = candidate(contract)
    if fault == 'id': cand = replace(cand, planner_id='other')
    elif fault == 'missing_scenario': cand = replace(cand, scenarios=())
    elif fault == 'missing_hour': cand = replace(cand, scenarios=(('s', ()),))
    elif fault == 'capacity_domain': cand = replace(cand, capacity=Q(2))
    else:
        action = cand.scenarios[0][1][0]
        cand = replace(cand, scenarios=(('s', (replace(action, tracks=(('grid', action.tracks[0][1]),)),)),))
        assert not w.audit_planner_witness(contract, JOINT, cand).accepted
        return
    with pytest.raises(ValueError):
        w.audit_planner_witness(contract, JOINT, cand)


def test_all_scenarios_must_pass_and_audit_cannot_be_relabelled():
    contract = inputs(scenarios=(scenario(name='a', g=(.125,)), scenario(name='b', g=(.375,))))
    result = audit(contract, capacity=Q('.25'))
    assert result.scenarios[0].accepted and not result.scenarios[1].accepted
    assert result.witness_capacity is None
    with pytest.raises(ValueError, match='independent replay'):
        replace(result, scenarios=result.scenarios[:1])
    valid = audit(contract, capacity=Q('.375'))
    assert valid.accepted and valid.witness_id != result.witness_id


def test_numeric_projection_failure_is_unassessed_not_infeasible(monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError('physical and cohort debt diverged')
    monkeypatch.setattr(w, 'advance_arm_replay', fail)
    result = audit(inputs())
    assert not result.accepted
    assert result.scenarios[0].records[0].status == 'unassessed_numeric_projection'
    assert result.witness_capacity is None


@pytest.mark.parametrize('field', ['recovery', 'actual_service_power'])
def test_action_quantities_require_exact_fraction(field):
    args = dict(recovery=Q(0), actual_service_power=Q(1))
    args[field] = .125
    with pytest.raises(ValueError, match='Fraction'):
        w.PlannerTrackAction(**args)
