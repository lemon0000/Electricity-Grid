from dataclasses import asdict, replace
import json

import pytest
from pyomo.environ import Constraint, Var
from pyomo.opt import SolverResults, SolverStatus, SolutionStatus, TerminationCondition
from pyomo.opt.results.problem import ProblemSense

from test_rq2_outage_trajectory_v1 import normal_base, inputs
from test_rq2_outage_assignment_v1 import assignment
from test_rq2_continuous_grid_candidate_v1 import SPEC, BUDGET
from src.solvers.rq2_solver_adapter import solver_options
from src.rq2_joint_deliverability_boundary_v1.outage_trajectory import outage_trajectory_identity
from src.rq2_joint_deliverability_boundary_v1 import outage_short_solve as runner


SHORT = replace(BUDGET, purpose='one complete offline outage LP', max_solver_calls=1, max_total_solver_seconds=1.)


def run(contract, spec=SPEC, budget=SHORT):
    return runner.run_short_outage(contract, expected_identity=outage_trajectory_identity(contract),
        solver_specification=spec, budget=budget)


def install(monkeypatch, contract, fault=None):
    values = assignment(contract)
    calls = {'create': 0, 'solve': 0}
    def create(spec):
        calls['create'] += 1
        class Fake:
            def solve(self, model, **kwargs):
                calls['solve'] += 1
                assert kwargs['load_solutions'] is False
                assert kwargs['options'] == solver_options(spec)
                if fault == 'exception':
                    raise RuntimeError('synthetic outage solver failure')
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
                elif fault == 'missing':
                    del solution.variable['generation[1,G2]']
                elif fault == 'unknown':
                    solution.variable['foreign'] = {'Value': 0.}
                elif fault == 'nan':
                    solution.variable['generation[1,G2]']['Value'] = float('nan')
                elif fault == 'objective':
                    solution.objective['objective']['Value'] = 1.
                elif fault == 'inverted_bounds':
                    native.problem.lower_bound = 1.
                elif fault == 'negative_upper':
                    native.problem.lower_bound = native.problem.upper_bound = -1e-10
                elif fault == 'positive_upper':
                    native.problem.upper_bound = 1e-10
                elif fault == 'nonfinite_bound':
                    native.problem.upper_bound = float('inf')
                elif fault == 'solution_status':
                    solution.status = SolutionStatus.infeasible
                elif fault == 'multi_solution':
                    native.solution.add()
                elif fault == 'multi_solver':
                    native.solver.add()
                elif fault == 'multi_problem':
                    native.problem.add()
                elif fault == 'options':
                    kwargs['options']['threads'] = 2
                elif fault == 'structure':
                    next(model.component_data_objects(Constraint)).deactivate()
                elif fault == 'root_deactivation':
                    model.deactivate()
                elif fault == 'preload':
                    model.generation[0, 'G1'].set_value(21.)
                elif fault == 'load':
                    old = model.solutions.load_from
                    def changed(*args, **kw):
                        old(*args, **kw)
                        model.generation[0, 'G1'].set_value(21.)
                    model.solutions.load_from = changed
                elif fault in ('none', 'infeasible_error'):
                    native.solution.clear()
                    if fault == 'infeasible_error':
                        native.solver.status = SolverStatus.error
                        native.solver.termination_condition = TerminationCondition.infeasible
                elif fault == 'missing_objective':
                    solution.objective.clear()
                elif fault == 'canonical_failure':
                    solution.variable['generation[1,G2]']['Value'] = 39.
                elif fault == 'duplicate':
                    from pyomo.core.expr.symbol_map import SymbolMap
                    symbols = SymbolMap()
                    for variable in model.component_data_objects(Var):
                        symbols.addSymbol(variable, variable.name)
                    symbols.addSymbol(model.objective, 'objective')
                    symbols.alias(model.generation[0, 'G1'], 'alias_G1')
                    native._smap = symbols
                    solution.variable['alias_G1'] = {'Value': 20.}
                return native
        return Fake(), solver_options(spec)
    monkeypatch.setattr(runner, 'create_solver', create)
    return calls


@pytest.mark.parametrize('mode', ['weighted_total_curtailment', 'fixed_curtailment_vector'])
def test_real_short_outage_both_objective_modes(normal_base, mode):
    result = run(inputs(normal_base, mode=mode))
    assert result.solve.optimal, result.solve.errors
    assert result.offline_feasible_trajectory_witness_available
    assert result.solve.calls == 1
    assert result.fixed_vector_feasibility_witness_available == (mode == 'fixed_curtailment_vector')
    assert result.development_objective_interval == ((0., 0.) if mode == 'weighted_total_curtailment' else None)
    assert result.hourly_curtailment_mw == ((1, 0.), (2, 0.), (3, 0.))
    assert result.external_grid_need_trace is result.causal_policy_certificate is result.infeasibility_certificate is None
    assert result.formal_result is result.security_certified is False
    assert json.dumps(asdict(result), allow_nan=False)


def test_real_infeasible_return_cap_is_only_raw_report(normal_base):
    result = run(inputs(normal_base, cap=19.))
    assert result.solve.solution_count == 0
    assert result.assignment_witness is None
    assert not result.solve.native_infeasible
    assert result.infeasibility_certificate is result.development_objective_interval is None


@pytest.mark.parametrize('fault', ['exception', 'timeout', 'missing', 'unknown', 'nan', 'objective',
    'inverted_bounds', 'negative_upper', 'positive_upper', 'nonfinite_bound', 'solution_status',
    'multi_solution', 'multi_solver', 'multi_problem', 'options', 'structure', 'root_deactivation',
    'preload', 'load', 'none', 'infeasible_error', 'canonical_failure', 'duplicate'])
def test_faults_never_produce_optimal_interval(normal_base, monkeypatch, fault):
    contract = inputs(normal_base)
    calls = install(monkeypatch, contract, fault)
    result = run(contract)
    assert calls == {'create': 1, 'solve': 1}
    assert not result.solve.optimal
    assert result.development_objective_interval is result.infeasibility_certificate is None
    assert not result.solve.native_infeasible


@pytest.mark.parametrize('mode', ['weighted_total_curtailment', 'fixed_curtailment_vector'])
def test_timeout_keeps_independent_feasible_assignment(normal_base, monkeypatch, mode):
    contract = inputs(normal_base, mode=mode)
    install(monkeypatch, contract, 'timeout')
    result = run(contract)
    assert result.offline_feasible_trajectory_witness_available
    assert not result.assignment_witness.errors
    assert result.fixed_vector_feasibility_witness_available == (mode == 'fixed_curtailment_vector')
    assert result.development_objective_interval is None


def test_native_objective_absence_is_explicit(normal_base, monkeypatch):
    contract = inputs(normal_base)
    install(monkeypatch, contract, 'missing_objective')
    result = run(contract)
    assert result.solve.optimal
    assert result.solve.native_objectives == ()


def test_objective_mismatch_keeps_physical_witness_separate_from_lineage(normal_base, monkeypatch):
    contract = inputs(normal_base)
    install(monkeypatch, contract, 'objective')
    result = run(contract)
    assert result.offline_feasible_trajectory_witness_available
    assert not result.solver_lineage_checked
    assert result.development_objective_interval is None


@pytest.mark.parametrize('changes', [{'max_horizon': 2}, {'max_variables': 1}, {'max_constraints': 1},
    {'max_seconds_per_solve': .5}, {'max_total_solver_seconds': .5}])
def test_budget_refusal_before_solver_creation(normal_base, monkeypatch, changes):
    contract = inputs(normal_base)
    calls = install(monkeypatch, contract)
    with pytest.raises(ValueError):
        run(contract, budget=replace(SHORT, **changes))
    assert calls == {'create': 0, 'solve': 0}


def test_owned_result_and_runtime_contract(normal_base, monkeypatch):
    contract = inputs(normal_base)
    install(monkeypatch, contract)
    result = run(contract)
    identity = result.result_id
    with pytest.raises(TypeError):
        replace(result, formal_result=True)
    monkeypatch.setattr(runner, 'CONTRACT', 'changed')
    assert result.result_id == identity
    with pytest.raises(ValueError, match='contract drift'):
        run(contract)


@pytest.fixture(scope='module')
def positive_contract(normal_base):
    from test_rq2_continuous_grid_normal_v1 import fixture
    from src.scenarios.rts_gmlc_n1_chronology import N1OutageEvent
    from src.rq2_joint_deliverability_boundary_v1.grid_carry import UnitPoint
    from src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal import normal_input_identity
    from src.rq2_joint_deliverability_boundary_v1.continuous_grid_candidate import run_short_grid_candidate
    from src.rq2_joint_deliverability_boundary_v1.outage_trajectory import ActualGridOrigin
    base = fixture(2)
    generator = replace(base.data.generators[0], p_max_mw=150.,
        cost_breakpoints_mw=(10., 60., 110., 150.), cost_values_usd_per_hour=(10., 60., 110., 150.))
    points = tuple(replace(p, demand_by_bus_mw={1: 0., 2: 100.}, generator_max_mw={'G1': 150.})
        for p in base.data.hourly_points)
    initial = replace(base.initial, generation_mw={'G1': 120.})
    normal = replace(base, data=replace(base.data, generators=(generator,), hourly_points=points), initial=initial,
        carry=replace(base.carry, points=(UnitPoint('G1', True, 120.),),
            limits=(replace(base.carry.limits[0], maximum_power_mw=150.),)),
        request=replace(base.request, initial_generation_mw={'G1': 120.},
            system_demand_by_bus_mw=tuple(p.demand_by_bus_mw for p in points), dc_bus=2,
            dc_requested_mw=(20., 20.), dc_physical_maximum_mw=(20., 20.), dc_connected_capacity_mw=(20., 20.)))
    candidate = run_short_grid_candidate(normal, expected_identity=normal_input_identity(normal), events=(),
        event_evidence_role='mechanism_assumption', solver_specification=SPEC, budget=BUDGET)
    assert candidate.normal.optimal, candidate.normal.errors
    return replace(inputs(normal_base), normal_inputs=normal, normal_candidate=candidate,
        expected_normal_candidate_id=candidate.result_id,
        actual_origin=ActualGridOrigin(normal.carry.identity, 0, (('G1', 120.),), (('G1', True),), 'mechanism_assumption'),
        events=(N1OutageEvent(1, 'branch_all', 'branch', 'AC1', 0, 2),),
        repair_return_limits_mw=(), curtailment_weights=(2., 3.))


def test_real_positive_indexed_curtailment_and_weighted_scalar(positive_contract):
    result = run(positive_contract)
    assert result.solve.optimal, result.solve.errors
    assert result.hourly_curtailment_mw == ((1, 20.), (2, 20.))
    assert result.weighted_objective_contributions == ((1, 40.), (2, 60.))
    assert result.development_objective_interval == (100., 100.)
    assert ('angle_degrees[0,2]', 0., 'unused_unbounded_continuous_representative') in result.solve.canonical_completed_values
    assert result.external_grid_need_trace is None


def test_real_fixed_positive_vector_has_no_scalar_grid_need_bound(positive_contract):
    fixed = replace(positive_contract, objective_mode='fixed_curtailment_vector', curtailment_weights=(),
                    fixed_curtailment_mw=(20., 20.))
    result = run(fixed)
    assert result.solve.optimal, result.solve.errors
    assert result.fixed_vector_feasibility_witness_available
    assert result.hourly_curtailment_mw == ((1, 20.), (2, 20.))
    assert result.solve.objective == 0.
    assert result.development_objective_interval is None


def test_runtime_version_drift_prevents_solver_lineage(normal_base, monkeypatch):
    contract = inputs(normal_base)
    install(monkeypatch, contract)
    original = runner.version
    queries = []
    def changed(name):
        queries.append(name)
        return 'changed' if name == 'highspy' and len(queries) > 2 else original(name)
    monkeypatch.setattr(runner, 'version', changed)
    result = run(contract)
    assert not result.solver_lineage_checked and not result.solve.optimal
    assert 'structure_options_or_version_drift' in result.solve.errors


def test_dependency_closure_bound_in_execution():
    from pathlib import Path
    import subprocess
    import sys
    from src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal import SOURCE_DEPENDENCIES
    from src.rq2_joint_deliverability_boundary_v1.continuous_grid_candidate import EXTRA_DEPENDENCIES
    script = '''
import json, sys
from pathlib import Path
import src.rq2_joint_deliverability_boundary_v1.outage_short_solve
root = Path.cwd()
print(json.dumps(sorted(Path(module.__file__).resolve().relative_to(root).as_posix()
    for name, module in sys.modules.items() if name == 'src' or name.startswith('src.'))))
'''
    result = subprocess.run([sys.executable, '-B', '-c', script], check=True, capture_output=True,
        text=True, cwd=Path(__file__).resolve().parents[1], timeout=30)
    expected = set(SOURCE_DEPENDENCIES) | set(EXTRA_DEPENDENCIES) | {
        'src/rq2_joint_deliverability_boundary_v1/' + name + '.py'
        for name in ('outage_trajectory', 'outage_assignment', 'outage_short_solve')}
    assert set(json.loads(result.stdout)) == expected
