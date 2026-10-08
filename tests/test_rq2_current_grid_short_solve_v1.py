from dataclasses import asdict, replace
import json

import pytest
from pyomo.environ import Var
from pyomo.opt import SolverResults, SolverStatus, SolutionStatus, TerminationCondition
from pyomo.opt.results.problem import ProblemSense

from test_rq2_current_grid_step_v1 import prepared, current, view, origin, power, G, B
from test_rq2_continuous_grid_candidate_v1 import SPEC, BUDGET
from src.solvers.rq2_solver_adapter import solver_options
from src.rq2_joint_deliverability_boundary_v1 import current_grid_short_solve as runner
from src.rq2_joint_deliverability_boundary_v1 import current_grid_step as step
from src.rq2_joint_deliverability_boundary_v1 import continuous_grid_candidate as pipeline
from src.rq2_joint_deliverability_boundary_v1.event_disclosure import CurrentOutageReport, disclose_current


SHORT = replace(BUDGET, purpose='current_hour_fixed_power_network_feasibility', max_horizon=1,
    max_solver_calls=1, max_total_solver_seconds=1.)


def inputs(ramp=60., demand=20., dc=5, initial_down=False, cap=None):
    info = view(prepared(ramp), current(demand=demand))
    before = origin(info, active=G if initial_down else None, generation=0. if initial_down else 20.)
    disclosure = disclose_current(before.disclosure, CurrentOutageReport(1, None, cap))
    return info, disclosure, before, power(mw=dc)


def run(args, spec=SPEC, budget=SHORT):
    return runner.run_short_current_grid(*args, expected_identity=step.current_step_identity(*args),
        solver_specification=spec, budget=budget)


def install(monkeypatch, args, fault=None):
    model = step.build_current_grid_model(*args, expected_identity=step.current_step_identity(*args))
    values = {v.name: 0. for v in model.component_data_objects(Var)}
    values['generation[G1]'] = dict(args[0].current.demand_by_bus_mw)[1]+float(args[3].exact_mw)
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
                    native.solver.status = SolverStatus.warning
                    native.solver.termination_condition = TerminationCondition.maxTimeLimit
                    solution.status = SolutionStatus.feasible
                elif fault == 'missing':
                    del solution.variable['generation[G1]']
                elif fault == 'nan':
                    solution.variable['generation[G1]']['Value'] = float('nan')
                elif fault == 'multiple':
                    native.solution.add()
                elif fault == 'status':
                    solution.status = SolutionStatus.infeasible
                elif fault in ('none', 'infeasible'):
                    native.solution.clear()
                    native.solver.termination_condition = (TerminationCondition.infeasible
                        if fault == 'infeasible' else TerminationCondition.maxTimeLimit)
                elif fault == 'load':
                    original = model.solutions.load_from
                    def changed(*a, **kw):
                        original(*a, **kw)
                        model.generation['G1'].set_value(0.)
                    model.solutions.load_from = changed
                elif fault == 'objective':
                    solution.objective['objective']['Value'] = 1.
                elif fault == 'options':
                    kwargs['options']['threads'] = 2
                elif fault == 'balance':
                    solution.variable['generation[G1]']['Value'] = 0.
                elif fault == 'exact':
                    solution.variable['generation[G1]']['Value'] = 37.799999
                elif isinstance(fault, tuple):
                    native.solver.status, native.solver.termination_condition = fault
                return native
        return Fake(), solver_options(spec)
    monkeypatch.setattr(pipeline, 'create_solver', create)
    return calls


def no_certificates(result):
    assert result.development_objective_interval is result.external_grid_need_trace is None
    assert result.capacity_certificate is result.causal_grid_dispatch_certificate is None
    assert result.infeasibility_certificate is None
    assert result.formal_result is result.security_certified is False


def test_real_current_hour_solve_and_next_actual_hour():
    plan = prepared(10.)
    info = view(plan, current(demand=20.))
    before = origin(info)
    disclosure = disclose_current(before.disclosure, CurrentOutageReport(1, None, None))
    result = run((info, disclosure, before, power(mw=5)))
    assert result.owned_solver_assignment_available, result.errors
    assert result.next_carry.generation_mw == (('G1', 25.),)
    assert result.raw_solve.calls == 1
    no_certificates(result)
    assert json.dumps(asdict(result), allow_nan=False)
    next_info = view(plan, current(2, demand=10.))
    next_disclosure = disclose_current(result.next_carry.disclosure, CurrentOutageReport(2, None, None))
    # 10 is within normal-plan response, but 25 -> 10 violates actual ramp 10.
    stopped = run((next_info, next_disclosure, result.next_carry, power(2)))
    assert not stopped.physical_assignment_witness_available
    assert stopped.next_carry is None and result.next_carry.source_hour == 1
    assert stopped.network_feasibility_status == 'unresolved'
    no_certificates(stopped)


def test_real_generator_repair_and_return_cap():
    result = run(inputs(demand=10., dc=0, initial_down=True, cap=10.))
    assert result.owned_solver_assignment_available, result.errors
    assert result.next_carry.generation_mw == (('G1', 10.),)
    no_certificates(result)


@pytest.mark.parametrize('fault', ['exception', 'missing', 'nan', 'multiple', 'status',
    'none', 'infeasible', 'load', 'balance'])
def test_bad_native_or_assignment_does_not_advance_actual_state(monkeypatch, fault):
    args = inputs()
    calls = install(monkeypatch, args, fault)
    result = run(args)
    assert calls == {'create': 1, 'solve': 1}
    assert not result.physical_assignment_witness_available
    assert not result.owned_solver_assignment_available and result.next_carry is None
    assert result.network_feasibility_status == 'unresolved'
    assert args[2].source_hour == 0
    no_certificates(result)


@pytest.mark.parametrize('fault', ['objective', 'options'])
def test_physical_witness_does_not_override_broken_solver_lineage(monkeypatch, fault):
    args = inputs()
    install(monkeypatch, args, fault)
    result = run(args)
    assert result.physical_assignment_witness_available
    assert result.assignment_witness.next_carry is not None
    assert not result.solver_lineage_checked and not result.owned_solver_assignment_available
    assert result.next_carry is None
    no_certificates(result)


def test_timeout_feasible_incumbent_can_have_audited_carry(monkeypatch):
    args = inputs()
    install(monkeypatch, args, 'timeout')
    result = run(args)
    assert result.owned_solver_assignment_available and result.next_carry is not None
    assert not result.raw_solve.optimal
    no_certificates(result)


@pytest.mark.parametrize('status,termination', [
    (SolverStatus.ok, TerminationCondition.infeasible),
    (SolverStatus.warning, TerminationCondition.unbounded),
    (SolverStatus.ok, TerminationCondition.solverFailure),
    (SolverStatus.unknown, TerminationCondition.optimal),
    (SolverStatus.error, TerminationCondition.optimal)])
def test_contradictory_status_cannot_advance_owned_result(monkeypatch, status, termination):
    args = inputs()
    install(monkeypatch, args, (status, termination))
    result = run(args)
    assert not result.solver_lineage_checked
    assert result.next_carry is None and not result.owned_solver_assignment_available
    assert 'native_solver_outcome_inconsistent_or_unsupported' in result.errors
    no_certificates(result)


def test_exact_mw_audit_can_reject_solver_tolerance_assignment(monkeypatch):
    args = inputs(dc='17.800000000000002')
    install(monkeypatch, args, 'exact')
    result = run(args, spec=replace(SPEC, feasibility_tolerance=1e-6))
    assert result.raw_solve.assignment_valid, result.raw_solve.errors
    assert result.assignment_witness.maximum_exact_violation > 1e-6
    assert not result.physical_assignment_witness_available and result.next_carry is None


@pytest.mark.parametrize('changes', [{'purpose': 'other'}, {'max_variables': 1}, {'max_constraints': 1},
    {'max_seconds_per_solve': .5}, {'max_total_solver_seconds': .5}])
def test_budget_refusal_precedes_solver(monkeypatch, changes):
    args = inputs()
    calls = install(monkeypatch, args)
    with pytest.raises(ValueError):
        run(args, budget=replace(SHORT, **changes))
    assert calls == {'create': 0, 'solve': 0}


@pytest.mark.parametrize('changes', [{'threads': 2}, {'time_limit_seconds': None},
    {'feasibility_tolerance': 1e-5}, {'optimality_tolerance': 1e-5}, {'integer_feasibility_tolerance': 1e-5}])
def test_solver_applicability_refusal_precedes_solver(monkeypatch, changes):
    args = inputs()
    calls = install(monkeypatch, args)
    with pytest.raises(ValueError):
        run(args, spec=replace(SPEC, **changes))
    assert calls == {'create': 0, 'solve': 0}


def test_stale_input_identity_precedes_solver(monkeypatch):
    args = inputs()
    calls = install(monkeypatch, args)
    with pytest.raises(ValueError, match='identity mismatch'):
        runner.run_short_current_grid(*args, expected_identity='0'*64, solver_specification=SPEC, budget=SHORT)
    assert calls == {'create': 0, 'solve': 0}


@pytest.mark.parametrize('name', ['CONTRACT', 'PURPOSE'])
def test_result_owned_identity_and_contract_drift(monkeypatch, name):
    args = inputs()
    install(monkeypatch, args)
    result = run(args)
    identity = result.result_id
    with pytest.raises(TypeError):
        replace(result, formal_result=True)
    monkeypatch.setattr(runner, name, 'changed')
    assert result.result_id == identity
    with pytest.raises(ValueError):
        run(args)


@pytest.mark.parametrize('which', ['input', 'execution'])
def test_post_solve_identity_drift_fails_closed(monkeypatch, which):
    args = inputs()
    install(monkeypatch, args)
    solve = runner._solve
    def changed(*a, **kw):
        raw = solve(*a, **kw)
        if which == 'input':
            monkeypatch.setattr(runner, 'current_step_identity', lambda *a: 'f'*64)
        else:
            monkeypatch.setattr(runner, '_identity', lambda *a: 'f'*64)
        return raw
    monkeypatch.setattr(runner, '_solve', changed)
    with pytest.raises(ValueError, match='drifted'):
        run(args)


def test_real_branch_outage_canonical_completions():
    info, _, before, dc = inputs()
    disclosure = disclose_current(before.disclosure, CurrentOutageReport(1, B, None))
    result = run((info, disclosure, before, dc))
    assert result.owned_solver_assignment_available, result.errors
    completed = {name: (value, reason) for name, value, reason in result.raw_solve.canonical_completed_values}
    assert completed['angle_degrees[1]'][0] == 0.
    assert completed['angle_degrees[2]'] == (0., 'unused_unbounded_continuous_representative')
    assert dict(result.raw_solve.loaded_values)['branch_flow[AC1]'] == 0.
    assert result.next_carry.disclosure.active.component == B
    no_certificates(result)


def test_fresh_import_execution_dependency_closure():
    from pathlib import Path
    import subprocess
    import sys
    from src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal import SOURCE_DEPENDENCIES
    from src.rq2_joint_deliverability_boundary_v1.continuous_grid_candidate import EXTRA_DEPENDENCIES
    script = '''
import json, sys
from pathlib import Path
import src.rq2_joint_deliverability_boundary_v1.current_grid_short_solve
root = Path.cwd()
print(json.dumps(sorted(Path(module.__file__).resolve().relative_to(root).as_posix()
    for name, module in sys.modules.items() if name == 'src' or name.startswith('src.'))))
'''
    result = subprocess.run([sys.executable, '-B', '-c', script], check=True, capture_output=True,
        text=True, cwd=Path(__file__).resolve().parents[1], timeout=30)
    expected = set(SOURCE_DEPENDENCIES) | set(EXTRA_DEPENDENCIES) | {
        'src/rq2_joint_deliverability_boundary_v1/'+name+'.py'
        for name in ('current_grid_step', 'current_grid_short_solve', 'grid_information', 'event_disclosure')}
    assert set(json.loads(result.stdout)) == expected
