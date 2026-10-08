from dataclasses import fields, replace
from fractions import Fraction as Q

import pytest

from test_rq2_continuous_planner_v1 import inputs, scenario, assign, violations
from test_rq2_continuous_planner_short_solve_v1 import SPEC, BUDGET
from src.rq2_joint_deliverability_boundary_v1 import continuous_planner_bidirectional as p
from src.rq2_joint_deliverability_boundary_v1 import planner_bidirectional_witness as w
from src.rq2_joint_deliverability_boundary_v1 import planner_bidirectional_assignment as a
from src.rq2_joint_deliverability_boundary_v1 import planner_bidirectional_short_solve as r
from src.rq2_joint_deliverability_boundary_v1 import continuous_planner_open_activity as old
from src.rq2_joint_deliverability_boundary_v1 import planner_witness as actions
from src.rq2_joint_deliverability_boundary_v1.four_arm_replay import NETWORK, CFE, JOINT, B6


def contract(s=None, **changes):
    original = inputs(s)
    data = {f.name: getattr(original, f.name) for f in fields(original)}
    data.update(planner_scope=p.SCOPE, minimum_event_power=1e-6)
    return p.BidirectionalPlanningInputs(**dict(data, **changes))


@pytest.mark.parametrize('arm', [NETWORK, CFE, JOINT, B6])
@pytest.mark.parametrize('hours,capacity', [(2, .5), (3, .4)])
def test_analytic_deadline_changes_minimum_physical_capacity(arm, hours, capacity):
    # Independent lower bound: q=.4; total physical recovery=.4/.8=.5.
    # One idle hour needs .5, two idle hours admit .25+.25 at capacity .4.
    g = ((.4 if arm != CFE else 0.),)+(0.,)*(hours-1)
    c = ((.4 if arm == CFE else 0.),)+(0.,)*(hours-1)
    config = contract(scenario(g=g, c=c, due=(hours,)+(None,)*(hours-1)))
    model = p.build_continuous_planning_model(config, arm)
    track = 'grid' if arm == B6 else 'shared'
    recovery = {('s', track, t): .5/(hours-1) for t in range(1, hours)}
    allocation = {('s', track, 0, t): .4/(hours-1) for t in range(1, hours)}
    assign(model, recovery=recovery, allocations=allocation, capacity=capacity)
    assert not violations(model)
    witness = a.audit_planner_assignment(config, arm, model, SPEC).witness
    assert witness.accepted
    assert witness.scenarios[0].execution.tracks[0][1].ledger.debt == 0
    native = r.run_short_continuous_solve(config, arm, solver_specification=SPEC, budget=BUDGET)
    assert native.lineage_checked and native.assignment.numerical_assignment_accepted
    assert native.lower.number == pytest.approx(capacity, abs=1e-9)
    assert native.upper.number == pytest.approx(capacity, abs=1e-9)
    assert native.evidence()['complete_capacity_upper_bound'] is None
    # Strict native and exact witness gates are never repaired by this test.
    if native.relaxed_prefix_interval is None:
        assert native.interval_issues


@pytest.mark.parametrize('arm', [NETWORK, CFE, JOINT, B6])
def test_exact_recovery_over_capacity_rejects_before_state_progression(arm):
    config = contract(scenario(g=(0. if arm == CFE else .4, 0.),
                               c=(.4 if arm == CFE else 0., 0.), due=(2, None)))
    model = p.build_continuous_planning_model(config, arm)
    track = 'grid' if arm == B6 else 'shared'
    assign(model, recovery={('s', track, 1): .5}, allocations={('s', track, 0, 1): .4}, capacity=.4)
    result = a.audit_planner_assignment(config, arm, model, SPEC)
    assert not result.numerical_assignment_accepted
    witness = result.witness
    assert not witness.accepted
    rejected = witness.scenarios[0].records[-1]
    assert rejected.stage == 'exact_bidirectional_capacity_validation' and rejected.candidate_step is None
    assert witness.scenarios[0].execution == rejected.before
    assert dict(witness.scenarios[0].execution.tracks)[track].ledger.debt == Q('.4')


def test_sub_tolerance_capacity_excess_is_still_rejected_exactly():
    config = contract(scenario(g=(.4, 0.), due=(2, None)))
    model = p.build_continuous_planning_model(config, JOINT)
    assign(model, recovery={('s', 'shared', 1): .5}, allocations={('s', 'shared', 0, 1): .4}, capacity=.5-1e-10)
    result = a.audit_planner_assignment(config, JOINT, model, SPEC)
    assert result.numerical_assignment_accepted and not result.exact_witness_accepted


def test_b6_capacity_is_separate_in_planning():
    config = contract(scenario(g=(.4, 0.), c=(.4, 0.), due=(2, None)))
    model = p.build_continuous_planning_model(config, B6)
    assign(model, recovery={('s', k, 1): .5 for k in ('grid', 'cfe')},
           allocations={('s', k, 0, 1): .4 for k in ('grid', 'cfe')}, capacity=.5)
    result = a.audit_planner_assignment(config, B6, model, SPEC)
    assert result.numerical_assignment_accepted and result.exact_witness_accepted
    assert result.witness.evidence()['scope'] == 'b6_separate_planning'
    assert result.witness.evidence()['complete_capacity_upper_bound'] is None


def test_versioned_types_reject_cross_admission():
    config = contract()
    with pytest.raises(ValueError, match='typed'):
        old.build_continuous_planning_model(config, JOINT)
    from test_rq2_continuous_planner_open_activity_v1 import contract as old_contract
    with pytest.raises(ValueError, match='typed'):
        p.build_continuous_planning_model(old_contract(), JOINT)
    candidate = actions.PlannerWitnessCandidate(p.planner_identity(config, JOINT), Q(1), ())
    with pytest.raises(ValueError, match='typed'):
        w.audit_planner_witness(config, JOINT, candidate)


@pytest.mark.parametrize('limit', ['maximum_recovery_power', 'business_recovery_headroom', 'cfe_compatible_surplus'])
def test_other_recovery_limits_remain_independent(limit):
    source = scenario(g=(.4, 0.), due=(2, None))
    second = source.observations[1]
    source = replace(source, observations=(source.observations[0], replace(second,
        observation=replace(second.observation, limits=replace(second.observation.limits, **{limit: .25})))))
    config = contract(source)
    model = p.build_continuous_planning_model(config, JOINT)
    assign(model, recovery={('s', 'shared', 1): .5}, allocations={('s', 'shared', 0, 1): .4}, capacity=.5)
    result = a.audit_planner_assignment(config, JOINT, model, SPEC)
    assert not result.numerical_assignment_accepted and not result.exact_witness_accepted
    assert result.witness.scenarios[0].records[-1].error == 'track recovery exceeds applicable headroom'
