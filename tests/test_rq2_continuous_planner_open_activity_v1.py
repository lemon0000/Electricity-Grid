from dataclasses import fields, replace
from fractions import Fraction as Q

import pytest
from pyomo.environ import Constraint, Objective, Var, value
from pyomo.repn import generate_standard_repn

from test_rq2_continuous_planner_v1 import inputs, scenario, assign, violations
from src.rq2_joint_deliverability_boundary_v1 import continuous_planner as old
from src.rq2_joint_deliverability_boundary_v1 import planner_witness as strict
from src.rq2_joint_deliverability_boundary_v1 import continuous_planner_open_activity as p
from src.rq2_joint_deliverability_boundary_v1 import planner_open_activity_witness as w
from src.rq2_joint_deliverability_boundary_v1.four_arm_replay import NETWORK, CFE, JOINT, B6


def contract(s=None, **changes):
    original = inputs(s)
    data = {f.name: getattr(original, f.name) for f in fields(original)}
    data.update(planner_scope=p.SCOPE, minimum_event_power=1e-6)
    return p.OpenActivityPlanningInputs(**dict(data, **changes))


def candidate(config, arm, *, grid=None, recoveries=None, allocations=None):
    grid, recoveries, allocations = grid or {}, recoveries or {}, allocations or {}
    sequences = []
    for s in config.scenarios:
        actions = []
        for t, current in enumerate(s.observations):
            raw = current.observation.hour
            g = Q(str(raw.grid_request)) if arm != CFE and raw.grid_request > 1e-6 else Q(0)
            c = Q(str(raw.cfe_request)) if arm != NETWORK and raw.cfe_request > 1e-6 else Q(0)
            g = grid.get((s.name, t), g)
            tracks = []
            for k in ('grid', 'cfe') if arm == B6 else ('shared',):
                q = g if k == 'grid' else c if k == 'cfe' else g+c
                r = recoveries.get((s.name, k, t), Q(0))
                tracks.append((k, strict.PlannerTrackAction(r, Q(str(raw.workload_occupancy))-q+r,
                    allocations.get((s.name, k, t), ()))))
            actions.append(strict.PlannerHourAction(g, c, tuple(tracks)))
        sequences.append((s.name, tuple(actions)))
    return strict.PlannerWitnessCandidate(p.planner_identity(config, arm), Q(1), tuple(sequences))


@pytest.mark.parametrize('arm', [NETWORK, CFE, JOINT, B6])
def test_above_boundary_physical_projection_and_four_arm_ledger(arm):
    config = contract(scenario(g=(.00000101,), c=(.00000102,)))
    model = p.build_continuous_planning_model(config, arm)
    assign(model)
    assert not violations(model)
    result = w.audit_planner_witness(config, arm, candidate(config, arm))
    assert result.accepted
    expected = {NETWORK: {'shared': Q('.00000101')}, CFE: {'shared': Q('.00000102')},
                JOINT: {'shared': Q('.00000203')}, B6: {'grid': Q('.00000101'), 'cfe': Q('.00000102')}}
    assert {k: track.ledger.debt for k, track in result.scenarios[0].execution.tracks} == expected[arm]
    assert all(status == 'right_censored_before_deadline'
               for _, _, status in result.scenarios[0].cohort_statuses)
    evidence = result.evidence()
    assert evidence['complete_capacity_upper_bound'] is None
    assert evidence['prefix_upper_bound'] is None and evidence['causal_policy_certificate'] is None
    assert not evidence['formal_result'] and not evidence['completion_claim_allowed']
    assert model._continuous_evidence['activity_representation'] == p.ACTIVITY_RELAXATION
    assert not model._continuous_evidence['relaxed_incumbent_is_physical_witness']


@pytest.mark.parametrize('arm', [NETWORK, JOINT, B6])
def test_exact_boundary_fake_activity_is_relaxed_only(arm):
    config = contract(scenario(g=(0.,)), service_action_mode=p.GRID_EXCESS)
    model = p.build_continuous_planning_model(config, arm)
    assign(model, grid={('s', 0): 1e-6})
    assert not violations(model)
    track = 'grid' if arm == B6 else 'shared'
    assert value(model.on['s', track, 0]) == 1
    result = w.audit_planner_witness(config, arm,
        candidate(config, arm, grid={('s', 0): Q('1e-6')}))
    assert not result.accepted and result.witness_capacity is None
    assert result.scenarios[0].records[0].error == 'positive track call violates minimum activity'
    assert result.scenarios[0].execution.tracks[0][1].ledger.debt == 0


@pytest.mark.parametrize('arm', [NETWORK, CFE, JOINT, B6])
def test_zero_is_inactive_and_not_forced_into_an_event(arm):
    config = contract(scenario(g=(0.,)))
    model = p.build_continuous_planning_model(config, arm)
    assign(model)
    assert not violations(model)
    assert all(value(model.on[idx]) == 0 for idx in model.tracked_points)
    assert w.audit_planner_witness(config, arm, candidate(config, arm)).accepted


def test_old_admission_identity_and_audit_remain_isolated():
    original = inputs()
    with pytest.raises(ValueError, match='above activity tolerance'):
        replace(original, minimum_event_power=1e-6)
    new = contract(minimum_event_power=original.minimum_event_power)
    assert not isinstance(new, old.ContinuousPlanningInputs)
    assert p.planner_identity(new, JOINT) != old.planner_identity(original, JOINT)
    with pytest.raises(ValueError, match='typed'):
        old.build_continuous_planning_model(new, JOINT)
    with pytest.raises(ValueError, match='typed'):
        p.build_continuous_planning_model(original, JOINT)
    cand = candidate(new, JOINT)
    with pytest.raises(ValueError, match='typed'):
        strict.audit_planner_witness(new, JOINT, cand)
    with pytest.raises(ValueError, match='identity'):
        w.audit_planner_witness(new, JOINT,
            replace(cand, planner_id=old.planner_identity(original, JOINT)))


@pytest.mark.parametrize('changes', [dict(minimum_event_power=.0000009),
    dict(activity_representation='physical_exact'), dict(planner_scope=old.SCOPE),
    dict(recovery_representation='physical_exact'), dict(decision_information_mode='causal'),
    dict(period_mode='rolling'), dict(terminal_mode='cleared'), dict(minimum_event_power=float('nan'))])
def test_unsupported_contract_is_refused(changes):
    with pytest.raises(ValueError):
        contract(**changes)


@pytest.mark.parametrize('arm', [NETWORK, CFE, JOINT, B6])
def test_known_deadline_after_recovery_is_preserved(arm):
    config = contract(scenario(g=(.000002, 0.), c=(.000004, 0.), due=(2, None)))
    quantities = {'grid': Q('.000002'), 'cfe': Q('.000004')} if arm == B6 else {
        'shared': Q('.000002') if arm == NETWORK else Q('.000004') if arm == CFE else Q('.000006')}
    recovery = {('s', k, 1): q/Q('.8') for k, q in quantities.items()}
    allocation = {('s', k, 1): ((1, q),) for k, q in quantities.items()}
    model = p.build_continuous_planning_model(config, arm)
    assign(model, recovery={idx: float(r) for idx, r in recovery.items()},
        allocations={('s', k, 0, 1): float(q) for k, q in quantities.items()})
    assert not violations(model)
    result = w.audit_planner_witness(config, arm,
        candidate(config, arm, recoveries=recovery, allocations=allocation))
    assert result.accepted
    assert all(track.ledger.debt == 0 for _, track in result.scenarios[0].execution.tracks)
    assert not w.audit_planner_witness(config, arm, candidate(config, arm)).accepted


def test_tiny_recovery_is_still_a_relaxation_not_an_effective_action():
    config = contract(scenario(g=(.125, 0.)))
    model = p.build_continuous_planning_model(config, JOINT)
    assign(model, recovery={('s', 'shared', 1): .0000005},
        allocations={('s', 'shared', 0, 1): .0000004})
    assert not violations(model)
    result = w.audit_planner_witness(config, JOINT, candidate(config, JOINT,
        recoveries={('s', 'shared', 1): Q('.0000005')},
        allocations={('s', 'shared', 1): ((1, Q('.0000004')),)}))
    assert not result.accepted
    assert 'physical threshold' in result.scenarios[0].records[-1].error


@pytest.mark.parametrize('arm', [NETWORK, CFE, JOINT, B6])
@pytest.mark.parametrize('mode', [p.REQUEST_BOUNDED, p.GRID_EXCESS])
def test_common_domain_has_identical_linear_model(arm, mode):
    s = scenario(g=(.125, 0., 0.), c=(0., .25, 0.), due=(3, 3, None))
    original = inputs(s, service_action_mode=mode)
    new = contract(s, service_action_mode=mode, minimum_event_power=original.minimum_event_power)

    def signature(model):
        def linear(expr):
            rep = generate_standard_repn(expr)
            assert rep.is_linear()
            return rep.constant, tuple(sorted((v.name, c) for v, c in zip(rep.linear_vars, rep.linear_coefs)))
        variables = [(v.name, v.lb, v.ub, str(v.domain)) for v in model.component_data_objects(Var)]
        constraints = [(c.name, value(c.lower) if c.has_lb() else None,
                        value(c.upper) if c.has_ub() else None, linear(c.body))
                       for c in model.component_data_objects(Constraint)]
        objectives = [(o.name, o.sense, linear(o.expr)) for o in model.component_data_objects(Objective)]
        return variables, constraints, objectives

    assert signature(old.build_continuous_planning_model(original, arm)) == signature(
        p.build_continuous_planning_model(new, arm))
