from dataclasses import replace

import pytest
from pyomo.environ import Constraint, Var
from pyomo.opt import SolverResults, SolverStatus, TerminationCondition, SolutionStatus
from pyomo.opt.results.problem import ProblemSense
from pyomo.core.expr.symbol_map import SymbolMap

from test_rq2_continuous_planner_v1 import inputs, scenario, build, assign
from src.rq2_joint_deliverability_boundary_v1.four_arm_replay import NETWORK, CFE, JOINT, B6
from src.rq2_joint_deliverability_boundary_v1 import planner_short_solve as runner
from src.rq2_joint_deliverability_v2.solver_adapter import Rq2SolverSpec, solver_options


SPEC = Rq2SolverSpec('highs', '1.15.1', 1, 1e-8, 1e-9, 1e-9, 1e-9, 0, 1., False)
BUDGET = runner.DevelopmentSolveBudget('tiny synthetic test', 1., 1, 1000, 2000, 2, 8)


def install(monkeypatch, contract, arm=JOINT, *, fault=None, count=1, status=SolverStatus.ok,
            termination=TerminationCondition.optimal, lower=.25, upper=.25,
            solution_status=SolutionStatus.optimal, assignment=None):
    calls = {'create': 0, 'solve': 0}
    def create(spec):
        calls['create'] += 1
        if fault == 'create_exception': raise RuntimeError('license unavailable')
        class FakeSolver:
            def solve(self, model, **kwargs):
                calls['solve'] += 1
                assert kwargs['load_solutions'] is False
                assert kwargs['options'] == solver_options(spec)
                if fault == 'solve_exception': raise RuntimeError('solver failed')
                if fault == 'foreign_result': return {'status': 'optimal'}
                if fault == 'preload_write': model.capacity.set_value(.25)
                if fault == 'constraint_change': model.service.deactivate()
                if fault == 'objective_change': model.minimum_capacity.set_value(2*model.capacity)
                if fault == 'option_change': kwargs['options']['threads'] = 2
                native = SolverResults()
                native.solver.status = status
                native.solver.termination_condition = termination
                native.problem.lower_bound = lower
                native.problem.upper_bound = upper
                native.problem.sense = ProblemSense.minimize
                source = build(contract, arm)
                assign(source, **(assignment or {}))
                for _ in range(count):
                    solution = native.solution.add()
                    solution._cuid = False
                    solution.status = solution_status
                    solution.variable.update({v.name: {'Value': v.value}
                        for v in source.component_data_objects(Var)})
                    if fault == 'missing_value': del solution.variable['capacity']
                    if fault == 'invalid_label': solution.variable['intruder'] = {'Value': 0.}
                    if fault == 'nan_value': solution.variable['capacity']['Value'] = float('nan')
                    if fault == 'wrong_objective_value': solution.objective['minimum_capacity'] = {'Value': .9}
                    elif fault == 'unknown_objective_label': solution.objective['other_objective'] = {'Value': .25}
                    if fault in ('mapped_unknown', 'mapped_duplicate', 'mapped_foreign'):
                        native._smap = SymbolMap()
                        for variable in model.component_data_objects(Var):
                            native._smap.addSymbol(variable, variable.name)
                        if fault == 'mapped_unknown': solution.variable['intruder'] = {'Value': 0.}
                        elif fault == 'mapped_duplicate':
                            native._smap.aliases['capacity_alias'] = model.capacity
                            solution.variable['capacity_alias'] = {'Value': .25}
                        else: native._smap.bySymbol['capacity'] = source.capacity
                if fault in ('load_exception', 'load_change'):
                    loader = model.solutions.load_from
                    def broken(*args, **kwargs):
                        loader(*args, **kwargs)
                        if fault == 'load_exception': raise RuntimeError('partial loading fault')
                        model.capacity.set_value(.5)
                    model.solutions.load_from = broken
                if fault == 'zero_solver': native.solver.clear()
                elif fault == 'two_solvers': native.solver.add()
                elif fault == 'zero_problem': native.problem.clear()
                elif fault == 'two_problems':
                    extra = native.problem.add()
                    extra.lower_bound, extra.upper_bound = .9, 1.
                elif fault == 'wrong_sense': native.problem.sense = ProblemSense.maximize
                elif fault == 'zero_objectives': native.problem.number_of_objectives = 0
                elif fault == 'two_objectives': native.problem.number_of_objectives = 2
                return native
        options = solver_options(spec)
        if fault == 'create_options': options['threads'] = 2
        return FakeSolver(), options
    monkeypatch.setattr(runner, 'create_solver', create)
    return calls


def run(contract=None, arm=JOINT, **kwargs):
    return runner.run_short_continuous_solve(inputs() if contract is None else contract, arm,
        solver_specification=kwargs.get('spec', SPEC), budget=kwargs.get('budget', BUDGET))


def test_native_optimal_result_bound_to_owned_assignment(monkeypatch):
    calls = install(monkeypatch, inputs())
    result = run()
    assert calls == {'create': 1, 'solve': 1}
    assert result.lineage_checked and result.relaxed_prefix_assignment_audited
    assert result.relaxed_prefix_interval == (.25, .25)
    assert result.effective_prefix_witness_available
    assert result.native_values == result.assignment.snapshot
    assert result.initial_values == result.preload_values
    assert result.passed_options == tuple(sorted(solver_options(SPEC).items()))
    assert len(result.result_id) == 64
    assert result.evidence()['complete_capacity_upper_bound'] is None
    assert result.evidence()['formal_result'] is False
    with pytest.raises(TypeError, match='owned solver flow'):
        replace(result, termination=runner._enum(TerminationCondition.maxTimeLimit, TerminationCondition))


@pytest.mark.parametrize('status', [SolverStatus.ok, SolverStatus.warning, SolverStatus.aborted])
def test_timeout_incumbent_is_loaded_and_audited_but_interval_unresolved(monkeypatch, status):
    install(monkeypatch, inputs(), status=status, termination=TerminationCondition.maxTimeLimit,
            solution_status=SolutionStatus.feasible, lower=.2)
    result = run()
    assert result.loaded and result.relaxed_prefix_assignment_audited
    assert result.effective_prefix_witness_available
    assert result.relaxed_prefix_interval is None and result.evidence()['assessment'] == 'unresolved'
    assert result.lower.number == .2


@pytest.mark.parametrize('count', [0, 2])
@pytest.mark.parametrize('termination', [TerminationCondition.optimal, TerminationCondition.maxTimeLimit])
def test_no_or_multiple_solutions_are_not_selected(monkeypatch, count, termination):
    calls = install(monkeypatch, inputs(), count=count, termination=termination)
    result = run()
    assert calls['solve'] == 1 and not result.loaded and result.assignment is None
    assert result.relaxed_prefix_interval is None


@pytest.mark.parametrize('fault', ['preload_write', 'constraint_change', 'objective_change',
    'option_change', 'create_options', 'missing_value', 'invalid_label', 'nan_value',
    'load_exception', 'load_change', 'foreign_result', 'create_exception', 'solve_exception',
    'mapped_unknown', 'mapped_duplicate', 'mapped_foreign', 'wrong_objective_value', 'unknown_objective_label',
    'zero_objectives', 'two_objectives'])
def test_solver_and_loader_faults_cannot_promote_interval(monkeypatch, fault):
    calls = install(monkeypatch, inputs(), fault=fault)
    result = run()
    assert calls['create'] == 1 and calls['solve'] <= 1
    assert not result.lineage_checked and result.relaxed_prefix_interval is None
    if fault in ('load_exception', 'invalid_label', 'missing_value', 'nan_value',
                  'mapped_unknown', 'mapped_duplicate', 'mapped_foreign'):
        assert not result.loaded and result.assignment is None


@pytest.mark.parametrize('lower,upper,issue', [(None, .25, 'lower_missing_value'),
    (float('inf'), .25, 'lower_nonfinite_value'), (.3, .25, 'inverted_bounds'),
    (.2, .3, 'upper_differs_from_assignment_objective'), (.2, .25, 'relative_gap_unaccepted'),
    (.251, .251, 'lower_exceeds_assignment_objective')])
def test_native_bounds_are_checked_without_abs_repair(monkeypatch, lower, upper, issue):
    install(monkeypatch, inputs(), lower=lower, upper=upper)
    result = run()
    assert result.relaxed_prefix_assignment_audited
    assert result.relaxed_prefix_interval is None and issue in result.interval_issues


@pytest.mark.parametrize('termination', [TerminationCondition.infeasible, TerminationCondition.infeasibleOrUnbounded,
    TerminationCondition.unbounded, TerminationCondition.solverFailure, TerminationCondition.locallyOptimal])
def test_other_native_termination_never_certifies_infeasibility_or_interval(monkeypatch, termination):
    install(monkeypatch, inputs(), termination=termination)
    result = run()
    assert result.relaxed_prefix_interval is None
    assert result.evidence()['infeasibility_certificate'] is None


def test_relaxed_interval_does_not_require_effective_micro_recovery_witness(monkeypatch):
    contract = inputs(scenario(g=(.25, 0.)))
    install(monkeypatch, contract, assignment={'recovery': {('s', 'shared', 1): 5e-7},
        'allocations': {('s', 'shared', 0, 1): 4e-7}})
    result = run(contract)
    assert result.relaxed_prefix_interval == (.25, .25)
    assert not result.effective_prefix_witness_available
    assert result.evidence()['prefix_capacity_interval'] is None


@pytest.mark.parametrize('solution_status', [SolutionStatus.feasible, SolutionStatus.bestSoFar, SolutionStatus.unknown])
def test_optimal_termination_requires_consistent_optimal_solution_metadata(monkeypatch, solution_status):
    install(monkeypatch, inputs(), solution_status=solution_status)
    result = run()
    assert result.loaded
    assert result.relaxed_prefix_interval is None
    assert 'solution_status_not_optimal' in result.interval_issues


def test_package_version_drift_during_solve_blocks_interval(monkeypatch):
    install(monkeypatch, inputs())
    calls = []
    def changing(package):
        calls.append(package)
        if package == 'pyomo': return '6.10.1'
        return '1.15.1' if calls.count(package) == 1 else '1.15.2'
    monkeypatch.setattr(runner, 'version', changing)
    result = run()
    assert result.loaded and result.assignment.numerical_assignment_accepted
    assert not result.lineage_checked and result.relaxed_prefix_interval is None


def test_result_identity_captures_runner_contract_version(monkeypatch):
    install(monkeypatch, inputs())
    monkeypatch.setattr(runner, 'perf_counter', lambda: 1.)
    first = run()
    original_contract = runner.CONTRACT
    monkeypatch.setattr(runner, 'CONTRACT', original_contract+'_test_changed')
    second = run()
    assert first.evidence()['contract'] == original_contract
    assert first.result_id != second.result_id


@pytest.mark.parametrize('fault,solver_count,problem_count', [('zero_solver', 0, 1), ('two_solvers', 2, 1),
    ('zero_problem', 1, 0), ('two_problems', 1, 2), ('wrong_sense', 1, 1)])
def test_complete_native_metadata_inventory_and_minimization(monkeypatch, fault, solver_count, problem_count):
    install(monkeypatch, inputs(), fault=fault)
    result = run()
    assert len(result.solver_records) == solver_count
    assert len(result.problem_records) == problem_count
    assert result.solution_count == 1 and len(result.solution_statuses) == 1
    assert not result.lineage_checked and result.relaxed_prefix_interval is None
    if fault == 'two_problems':
        assert result.problem_records[1].lower.number == .9
    assert len(result.result_id) == 64


@pytest.mark.parametrize('field', ['feasibility_tolerance', 'optimality_tolerance', 'integer_feasibility_tolerance'])
def test_large_tolerances_reject_before_solver_creation(monkeypatch, field):
    calls = install(monkeypatch, inputs(), lower=-.5, upper=-.5)
    with pytest.raises(ValueError, match='short development applicability'):
        run(spec=replace(SPEC, **{field: 1.}))
    assert calls == {'create': 0, 'solve': 0}


def test_negative_upper_bound_is_not_a_capacity_interval_even_with_tiny_gap(monkeypatch):
    contract = inputs(scenario(g=(0.,)))
    install(monkeypatch, contract, lower=-1e-12, upper=-1e-12)
    result = run(contract)
    assert result.relaxed_prefix_assignment_audited
    assert result.relaxed_prefix_interval is None
    assert 'upper_outside_declared_capacity_domain' in result.interval_issues


def test_loose_negative_lower_bound_can_still_bound_zero_optimum(monkeypatch):
    contract = inputs(scenario(g=(0.,)))
    install(monkeypatch, contract, lower=-1e-24, upper=0.)
    result = run(contract)
    assert result.relaxed_prefix_interval == (-1e-24, 0.)


def test_upper_capacity_domain_and_objective_consistency_have_strict_gates(monkeypatch):
    contract = inputs(maximum_capacity=.25)
    install(monkeypatch, contract, lower=.25, upper=.250000000001)
    result = run(contract)
    assert result.relaxed_prefix_interval is None
    assert 'upper_outside_declared_capacity_domain' in result.interval_issues
    install(monkeypatch, inputs(), lower=.25, upper=.25000001)
    result = run(spec=replace(SPEC, feasibility_tolerance=1e-6, mip_relative_gap=1e-3))
    assert 'upper_differs_from_assignment_objective' in result.interval_issues


@pytest.mark.parametrize('kind', ['time_absent', 'time_large', 'threads', 'variables', 'constraints', 'horizon', 'scenarios', 'integer'])
def test_budget_and_invalid_spec_reject_before_solver_creation(monkeypatch, kind):
    contract, spec, budget = inputs(), SPEC, BUDGET
    if kind == 'time_absent': spec = replace(spec, time_limit_seconds=None)
    elif kind == 'time_large': spec = replace(spec, time_limit_seconds=2.)
    elif kind == 'threads': spec = replace(spec, threads=2)
    elif kind == 'variables': budget = replace(budget, max_variables=1)
    elif kind == 'constraints': budget = replace(budget, max_constraints=1)
    elif kind == 'horizon': contract = inputs(scenario(g=(.25,)*9))
    elif kind == 'scenarios': contract = inputs(scenarios=tuple(scenario(name=str(i)) for i in range(3)))
    else: spec = replace(spec, integer_feasibility_tolerance=.5)
    calls = install(monkeypatch, contract)
    with pytest.raises(ValueError): run(contract, spec=spec, budget=budget)
    assert calls == {'create': 0, 'solve': 0}


@pytest.mark.parametrize('change', [dict(max_time_limit_seconds=31), dict(max_variables=20001),
    dict(max_horizon_hours=True), dict(purpose='')])
def test_development_budget_itself_is_bounded(change):
    with pytest.raises(ValueError): replace(BUDGET, **change)


@pytest.mark.parametrize('arm,peak', [(NETWORK, .25), (CFE, .125), (JOINT, .375), (B6, .25)])
def test_real_highs_tiny_four_arm_recovery(arm, peak):
    pytest.importorskip('highspy')
    result = run(inputs(scenario(g=(.25, 0.), c=(.125, 0.), due=(2, None))), arm)
    assert result.relaxed_prefix_interval == (peak, peak), result.interval_issues
    assert result.effective_prefix_witness_available
    assert result.assignment.maximum_constraint_violation == 0
    assert all(status == 'recovered_by_deadline' for _, _, status in result.assignment.witness.scenarios[0].cohort_statuses)
    assert result.solve_calls == 1 and result.loaded
