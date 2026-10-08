from dataclasses import replace

import pytest
from pyomo.environ import Constraint
from pyomo.opt import SolverStatus, TerminationCondition, SolutionStatus

from test_rq2_bidirectional_capacity_v1 import contract
from test_rq2_continuous_planner_v1 import scenario, inputs, assign
import test_rq2_continuous_planner_short_solve_v1 as legacy_fixture
from src.rq2_joint_deliverability_boundary_v1 import continuous_planner_bidirectional as p
from src.rq2_joint_deliverability_boundary_v1 import planner_bidirectional_assignment as a
from src.rq2_joint_deliverability_boundary_v1 import planner_bidirectional_short_solve as r
from src.rq2_joint_deliverability_boundary_v1 import planner_assignment as old_a
from src.rq2_joint_deliverability_boundary_v1 import planner_short_solve as old_r
from src.rq2_joint_deliverability_boundary_v1.four_arm_replay import NETWORK, CFE, JOINT, B6

SPEC, BUDGET = legacy_fixture.SPEC, legacy_fixture.BUDGET


def fake(monkeypatch, config, arm=JOINT, **kwargs):
    # Reuse the independent native-result fault generator, with the versioned builder.
    monkeypatch.setattr(legacy_fixture, 'runner', r)
    monkeypatch.setattr(legacy_fixture, 'build', p.build_continuous_planning_model)
    return legacy_fixture.install(monkeypatch, config, arm, **kwargs)


def run(config, arm=JOINT, spec=SPEC, budget=BUDGET):
    return r.run_short_continuous_solve(config, arm, solver_specification=spec, budget=budget)


def test_boundary_numeric_assignment_cannot_become_effective_witness():
    config = contract(scenario(g=(0.,)), service_action_mode=p.GRID_EXCESS)
    model = p.build_continuous_planning_model(config, JOINT)
    assign(model, grid={('s', 0): 1e-6})
    audit = a.audit_planner_assignment(config, JOINT, model, SPEC)
    assert audit.numerical_assignment_accepted and audit.structure_matches
    assert not audit.exact_witness_accepted
    assert audit.witness.scenarios[0].records[0].error == 'positive track call violates minimum activity'
    assert audit.evidence()['complete_capacity_upper_bound'] is None
    raw = a.audit_raw_solver_outcome(audit, solver_status='ok', termination='optimal',
                                    lower_bound=0., upper_bound=1e-6)
    assert raw.evidence()['relaxed_prefix_capacity_interval'] is None


def test_canonical_rebuild_catches_hidden_invalid_assignment():
    config = contract()
    model = p.build_continuous_planning_model(config, JOINT)
    assign(model, capacity=.1)
    for c in model.component_objects(Constraint):
        c.deactivate()
    audit = a.audit_planner_assignment(config, JOINT, model, SPEC)
    assert not audit.structure_matches and not audit.numerical_assignment_accepted
    assert audit.maximum_constraint_violation > .14
    with pytest.raises(ValueError, match='canonical snapshot replay'):
        replace(audit, objective=.1+1e-9)


def test_versioned_assignment_and_solver_refuse_legacy_contracts(monkeypatch):
    config = contract()
    model = p.build_continuous_planning_model(config, JOINT)
    assign(model)
    with pytest.raises(ValueError, match='typed'):
        old_a.audit_planner_assignment(config, JOINT, model, SPEC)
    with pytest.raises(ValueError, match='typed'):
        a.audit_planner_assignment(inputs(), JOINT, model, SPEC)
    calls = fake(monkeypatch, config)
    with pytest.raises(ValueError, match='typed'):
        run(inputs())
    with pytest.raises(ValueError, match='typed'):
        old_r.run_short_continuous_solve(config, JOINT, solver_specification=SPEC, budget=BUDGET)
    assert calls == {'create': 0, 'solve': 0}


def test_owned_boundary_result_keeps_relaxation_and_physical_evidence_separate(monkeypatch):
    config = contract(scenario(g=(0.,)), service_action_mode=p.GRID_EXCESS)
    calls = fake(monkeypatch, config, lower=0., upper=1e-6, assignment={'grid': {('s', 0): 1e-6}})
    result = run(config)
    assert calls == {'create': 1, 'solve': 1}
    assert result.relaxed_prefix_assignment_audited
    assert not result.effective_prefix_witness_available
    assert result.relaxed_prefix_interval is None  # Native gap is not repaired.
    assert 'relative_gap_unaccepted' in result.interval_issues
    assert result.assignment.snapshot == result.native_values
    assert result.evidence()['activity_representation'] == p.ACTIVITY_RELAXATION
    assert result.evidence()['complete_capacity_upper_bound'] is None
    with pytest.raises(TypeError, match='owned solver flow'):
        replace(result, errors=())


@pytest.mark.parametrize('mocked', [True, False])
def test_optimal_relaxed_interval_does_not_require_effective_witness(monkeypatch, mocked):
    # One event must bridge the empty middle hour. The closed model chooses tol;
    # peak .25 is an independent necessary lower bound from hours 1 and 3.
    config = contract(scenario(g=(.25, 0., .25), due=(10, None, 10)),
        service_action_mode=p.GRID_EXCESS, maximum_event_count=1)
    if mocked:
        fake(monkeypatch, config, lower=.25, upper=.25,
             assignment={'grid': {('s', 1): 1e-6}})
    result = run(config)
    assert result.relaxed_prefix_interval == (.25, .25)
    assert result.relaxed_prefix_assignment_audited
    assert not result.effective_prefix_witness_available
    assert result.assignment.witness.scenarios[0].records[1].error == 'positive track call violates minimum activity'
    assert result.evidence()['complete_capacity_upper_bound'] is None


@pytest.mark.parametrize('fault', ['preload_write', 'constraint_change', 'objective_change',
    'option_change', 'create_options', 'missing_value', 'invalid_label', 'nan_value',
    'load_exception', 'load_change', 'foreign_result', 'create_exception', 'solve_exception',
    'mapped_unknown', 'mapped_duplicate', 'mapped_foreign', 'wrong_objective_value', 'unknown_objective_label',
    'zero_objectives', 'two_objectives', 'zero_solver', 'two_solvers', 'zero_problem', 'two_problems', 'wrong_sense'])
def test_native_faults_do_not_publish_interval_or_retry(monkeypatch, fault):
    config = contract()
    calls = fake(monkeypatch, config, fault=fault)
    result = run(config)
    assert calls['create'] == 1 and calls['solve'] <= 1
    assert result.relaxed_prefix_interval is None and not result.lineage_checked
    assert result.evidence()['infeasibility_certificate'] is None


@pytest.mark.parametrize('termination,count', [(TerminationCondition.maxTimeLimit, 1),
    (TerminationCondition.maxTimeLimit, 0), (TerminationCondition.infeasible, 0),
    (TerminationCondition.optimal, 2)])
def test_unresolved_native_outcomes_keep_unknown_semantics(monkeypatch, termination, count):
    config = contract()
    calls = fake(monkeypatch, config, termination=termination, count=count,
        solution_status=SolutionStatus.feasible)
    result = run(config)
    assert calls['solve'] == 1 and result.relaxed_prefix_interval is None
    assert result.evidence()['infeasibility_certificate'] is None
    if count == 1:
        assert result.relaxed_prefix_assignment_audited and result.effective_prefix_witness_available


@pytest.mark.parametrize('lower,upper,issue', [(None, .25, 'lower_missing_value'),
    (float('inf'), .25, 'lower_nonfinite_value'), (.3, .25, 'inverted_bounds'),
    (.2, .3, 'upper_differs_from_assignment_objective'), (.2, .25, 'relative_gap_unaccepted'),
    (.25000000001, .25000000001, 'lower_exceeds_assignment_objective')])
def test_native_bounds_are_preserved_and_normal_repair_is_not_extended(monkeypatch, lower, upper, issue):
    config = contract()
    fake(monkeypatch, config, lower=lower, upper=upper)
    result = run(config)
    assert issue in result.interval_issues and result.relaxed_prefix_interval is None
    assert result.upper.raw_repr == repr(upper)


@pytest.mark.parametrize('change', [dict(time_limit_seconds=2.), dict(threads=2),
                                  dict(feasibility_tolerance=1e-5)])
def test_budget_and_tolerance_admission_precedes_solver(monkeypatch, change):
    config = contract()
    calls = fake(monkeypatch, config)
    with pytest.raises(ValueError):
        run(config, spec=replace(SPEC, **change))
    assert calls == {'create': 0, 'solve': 0}


@pytest.mark.parametrize('arm,expected', [(NETWORK, .3125), (CFE, .15625), (JOINT, .46875), (B6, .3125)])
def test_real_tiny_native_four_arm_solve(arm, expected):
    config = contract(scenario(g=(.25, 0.), c=(.125, 0.), due=(2, None)))
    result = run(config, arm)
    assert result.solve_calls == 1 and result.lineage_checked
    assert result.relaxed_prefix_interval == (expected, expected)
    assert result.effective_prefix_witness_available
    assert result.assignment.witness.accepted
    assert result.contract == 'continuous_bidirectional_planner_short_solve_v1'
    evidence = result.evidence()
    assert evidence['prefix_capacity_interval'] is None
    assert evidence['complete_capacity_lower_bound'] is None and evidence['complete_capacity_upper_bound'] is None
    assert not evidence['formal_result'] and evidence['causal_policy_certificate'] is None
