from dataclasses import asdict, replace
import json

import pytest
from pyomo.opt import SolverResults, SolverStatus, SolutionStatus, TerminationCondition
from pyomo.opt.results.problem import ProblemSense

from test_rq2_business_grid_v1 import grid, network, business, contract, assigned
from test_rq2_continuous_grid_candidate_v1 import SPEC, BUDGET
from src.solvers.rq2_solver_adapter import solver_options
from src.rq2_joint_deliverability_boundary_v1 import business_grid_short_solve as runner
from src.rq2_joint_deliverability_boundary_v1 import continuous_grid_candidate as pipeline
from src.rq2_joint_deliverability_boundary_v1.business_grid import business_grid_identity


SHORT = replace(BUDGET, purpose='fixed_business_network_feasibility',
                max_solver_calls=1, max_total_solver_seconds=1.)


def run(inputs, spec=SPEC, budget=SHORT):
    return runner.run_short_business_grid(inputs, expected_identity=business_grid_identity(inputs),
        solver_specification=spec, budget=budget)


def install(monkeypatch, inputs, fault=None, values=None):
    values = assigned(inputs)[1] if values is None else values
    calls = {'create': 0, 'solve': 0}
    def create(spec):
        calls['create'] += 1
        class Fake:
            def solve(self, model, **kwargs):
                calls['solve'] += 1
                assert kwargs['load_solutions'] is False
                assert kwargs['options'] == solver_options(spec)
                if fault == 'exception':
                    raise RuntimeError('synthetic failure')
                native = SolverResults()
                native.solver.status = SolverStatus.ok
                native.solver.termination_condition = TerminationCondition.optimal
                native.problem.sense = ProblemSense.minimize
                native.problem.number_of_objectives = 1
                native.problem.lower_bound = native.problem.upper_bound = 0.
                solution = native.solution.add()
                solution._cuid = False
                solution.status = SolutionStatus.optimal
                solution.variable.update({name: {'Value': x} for name, x in values.items()})
                solution.objective['objective'] = {'Value': 0.}
                if fault == 'timeout':
                    native.solver.termination_condition = TerminationCondition.maxTimeLimit
                elif fault == 'warning_timeout':
                    native.solver.status = SolverStatus.warning
                    native.solver.termination_condition = TerminationCondition.maxTimeLimit
                    solution.status = SolutionStatus.feasible
                elif isinstance(fault, tuple):
                    native.solver.status, native.solver.termination_condition = fault
                elif fault == 'missing':
                    del solution.variable['generation[0,G1]']
                elif fault == 'nan':
                    solution.variable['generation[0,G1]']['Value'] = float('nan')
                elif fault == 'multiple':
                    native.solution.add()
                elif fault == 'status':
                    solution.status = SolutionStatus.infeasible
                elif fault in ('none', 'infeasible'):
                    native.solution.clear()
                    if fault == 'infeasible':
                        native.solver.termination_condition = TerminationCondition.infeasible
                elif fault == 'load':
                    old = model.solutions.load_from
                    def changed(*args, **kw):
                        old(*args, **kw)
                        model.generation[0, 'G1'].set_value(0.)
                    model.solutions.load_from = changed
                elif fault == 'objective':
                    solution.objective['objective']['Value'] = 1.
                elif fault == 'options':
                    kwargs['options']['threads'] = 2
                elif fault == 'balance':
                    solution.variable['generation[0,G1]']['Value'] = 0.
                return native
        return Fake(), solver_options(spec)
    monkeypatch.setattr(pipeline, 'create_solver', create)
    return calls


def assert_no_certificates(result):
    assert result.development_objective_interval is result.external_grid_need_trace is None
    assert result.capacity_certificate is result.causal_grid_dispatch_certificate is None
    assert result.infeasibility_certificate is None
    assert result.formal_result is result.security_certified is False


def test_real_fixed_business_recovery_network_solve(grid):
    inputs = contract(grid)
    before = business_grid_identity(inputs)
    result = run(inputs)
    assert result.raw_solve.optimal, result.errors
    assert result.owned_solver_assignment_available
    assert result.network_feasibility_status == 'witnessed'
    assert result.raw_solve.calls == 1
    generation = dict(result.raw_solve.loaded_values)
    assert tuple(generation[f'generation[{t},G1]'] for t in range(3)) == (37.5, 43.125, 40.)
    assert business_grid_identity(inputs) == before
    assert_no_certificates(result)
    assert json.dumps(asdict(result), allow_nan=False)


def test_real_ramp_failure_does_not_certify_infeasibility():
    inputs = contract(network(ramp=4.))
    result = run(inputs)
    assert result.raw_solve.calls == 1
    assert not result.physical_assignment_witness_available
    assert result.network_feasibility_status == 'unresolved'
    assert_no_certificates(result)


def test_real_network_witness_preserves_cfe_shortfall(grid):
    result = run(contract(grid, business(c=.5)))
    assert result.owned_solver_assignment_available
    assert not result.assignment_witness.effective_applicable_requests_fully_served
    assert result.assignment_witness.full_service_completion is None
    assert_no_certificates(result)


@pytest.mark.parametrize('fault', ['exception', 'missing', 'nan', 'multiple', 'status', 'none',
                                 'infeasible', 'load', 'balance'])
def test_bad_native_or_assignment_remains_unresolved(grid, monkeypatch, fault):
    inputs = contract(grid)
    calls = install(monkeypatch, inputs, fault)
    result = run(inputs)
    assert calls == {'create': 1, 'solve': 1}
    assert not result.owned_solver_assignment_available
    assert not result.physical_assignment_witness_available
    assert result.network_feasibility_status == 'unresolved'
    assert_no_certificates(result)


@pytest.mark.parametrize('fault', ['timeout', 'objective', 'options'])
def test_independent_assignment_is_separate_from_solver_claims(grid, monkeypatch, fault):
    inputs = contract(grid)
    install(monkeypatch, inputs, fault)
    result = run(inputs)
    assert result.physical_assignment_witness_available
    assert not result.raw_solve.optimal
    if fault != 'timeout':
        assert not result.solver_lineage_checked
        assert not result.owned_solver_assignment_available
    assert_no_certificates(result)


@pytest.mark.parametrize('status,termination', [
    (SolverStatus.ok, TerminationCondition.infeasible),
    (SolverStatus.warning, TerminationCondition.infeasible),
    (SolverStatus.ok, TerminationCondition.unbounded),
    (SolverStatus.warning, TerminationCondition.infeasibleOrUnbounded),
    (SolverStatus.ok, TerminationCondition.solverFailure),
    (SolverStatus.unknown, TerminationCondition.optimal),
    (SolverStatus.error, TerminationCondition.optimal),
])
def test_conflicting_solver_outcome_cannot_pass_lineage(grid, monkeypatch, status, termination):
    inputs = contract(grid)
    install(monkeypatch, inputs, (status, termination))
    result = run(inputs)
    if status in (SolverStatus.error, SolverStatus.unknown):
        assert not result.physical_assignment_witness_available
        assert any(error.startswith('load:') for error in result.errors)
    else:
        assert result.physical_assignment_witness_available
    assert not result.solver_lineage_checked
    assert not result.owned_solver_assignment_available
    assert 'native_solver_outcome_inconsistent_or_unsupported' in result.errors
    assert_no_certificates(result)


def test_warning_timeout_with_feasible_incumbent_has_assignment_lineage(grid, monkeypatch):
    inputs = contract(grid)
    install(monkeypatch, inputs, 'warning_timeout')
    result = run(inputs)
    assert result.owned_solver_assignment_available
    assert not result.raw_solve.optimal
    assert_no_certificates(result)


def test_exact_balance_can_reject_float_residual_accepted_assignment(grid, monkeypatch):
    inputs = contract(grid, business(c=.1099999999999999))
    values = assigned(inputs)[1]
    values['generation[0,G1]'] = 37.799999
    install(monkeypatch, inputs, values=values)
    result = run(inputs, spec=replace(SPEC, feasibility_tolerance=1e-6))
    assert result.raw_solve.assignment_valid, result.raw_solve.errors
    assert result.assignment_witness.maximum_exact_power_balance_violation > 1e-6
    assert not result.physical_assignment_witness_available
    assert result.network_feasibility_status == 'unresolved'


@pytest.mark.parametrize('changes', [{'purpose': 'other'}, {'max_horizon': 2}, {'max_variables': 1},
    {'max_constraints': 1}, {'max_seconds_per_solve': .5}, {'max_total_solver_seconds': .5}])
def test_budget_refusal_before_solver(grid, monkeypatch, changes):
    inputs = contract(grid)
    calls = install(monkeypatch, inputs)
    with pytest.raises(ValueError):
        run(inputs, budget=replace(SHORT, **changes))
    assert calls == {'create': 0, 'solve': 0}


@pytest.mark.parametrize('name', ['CONTRACT', 'PURPOSE'])
def test_contract_identity_and_owned_result(grid, monkeypatch, name):
    inputs = contract(grid)
    install(monkeypatch, inputs)
    result = run(inputs)
    identity = result.result_id
    with pytest.raises(TypeError):
        replace(result, formal_result=True)
    monkeypatch.setattr(runner, name, 'changed')
    assert result.result_id == identity
    with pytest.raises(ValueError, match='contract drift'):
        run(inputs)


def test_stale_input_identity_stops_before_solver(grid, monkeypatch):
    inputs = contract(grid)
    calls = install(monkeypatch, inputs)
    with pytest.raises(ValueError, match='identity mismatch'):
        runner.run_short_business_grid(inputs, expected_identity='0'*64,
            solver_specification=SPEC, budget=SHORT)
    assert calls == {'create': 0, 'solve': 0}


@pytest.mark.parametrize('fault', ['execution', 'input'])
def test_post_solve_identity_drift_fails_closed(grid, monkeypatch, fault):
    inputs = contract(grid)
    calls = install(monkeypatch, inputs)
    original = runner._solve
    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        if fault == 'execution':
            monkeypatch.setattr(runner, 'CONTRACT', 'changed')
        else:
            object.__setattr__(inputs, 'expected_business_prefix_sha256', '0'*64)
        return result
    monkeypatch.setattr(runner, '_solve', changed)
    with pytest.raises(ValueError):
        run(inputs)
    assert calls == {'create': 1, 'solve': 1}


def test_real_unused_angle_completion(grid):
    from src.scenarios.rts_gmlc_n1_chronology import N1OutageEvent
    event = N1OutageEvent(1, 'branch_all', 'branch', 'AC1', 0, 3)
    result = run(contract(replace(grid, events=(event,))))
    assert result.owned_solver_assignment_available, result.errors
    assert ('angle_degrees[0,2]', 0., 'unused_unbounded_continuous_representative') in result.raw_solve.canonical_completed_values
    assert_no_certificates(result)


def test_dependency_closure_bound_in_execution():
    from pathlib import Path
    import subprocess
    import sys
    from src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal import SOURCE_DEPENDENCIES
    from src.rq2_joint_deliverability_boundary_v1.continuous_grid_candidate import EXTRA_DEPENDENCIES
    from src.rq2_joint_deliverability_boundary_v1.prefix_handoff import IMPLEMENTATION
    script = '''
import json, sys
from pathlib import Path
import src.rq2_joint_deliverability_boundary_v1.business_grid_short_solve
root = Path.cwd()
print(json.dumps(sorted(Path(module.__file__).resolve().relative_to(root).as_posix()
    for name, module in sys.modules.items() if name == 'src' or name.startswith('src.'))))
'''
    result = subprocess.run([sys.executable, '-B', '-c', script], check=True, capture_output=True,
        text=True, cwd=Path(__file__).resolve().parents[1], timeout=30)
    expected = set(SOURCE_DEPENDENCIES) | set(EXTRA_DEPENDENCIES) | set(IMPLEMENTATION) | {
        'src/rq2_joint_deliverability_boundary_v1/' + name + '.py' for name in
        ('business_grid', 'outage_trajectory', 'outage_assignment', 'outage_short_solve', 'business_grid_short_solve')}
    assert set(json.loads(result.stdout)) == expected
