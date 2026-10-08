from dataclasses import asdict, replace
import json

import pytest
from pyomo.environ import Var, value
from pyomo.opt import SolverResults, SolverStatus, SolutionStatus, TerminationCondition
from pyomo.opt.results.problem import ProblemSense

from test_rq2_current_grid_step_v1 import prepared, current, view, origin, power
from test_rq2_reference_selector_v1 import two_inputs
from test_rq2_continuous_grid_candidate_v1 import SPEC, BUDGET
from src.solvers.rq2_solver_adapter import solver_options
from src.rq2_joint_deliverability_boundary_v1 import actual_dispatch_selector as runner
from src.rq2_joint_deliverability_boundary_v1 import continuous_grid_candidate as pipeline
from src.rq2_joint_deliverability_boundary_v1.event_disclosure import CurrentOutageReport, disclose_current


SELECTOR = runner.ActualDispatchSpec('l1_normal_deviation_generation_uid_order', 1e-7, 1e-8, 1e-9, 'mechanism_assumption')
SHORT = replace(BUDGET, purpose=runner.PURPOSE, max_horizon=1, max_solver_calls=2, max_total_solver_seconds=2.)


def wrap(info, physical, selector=SELECTOR, spec=SPEC, budget=SHORT):
    return runner.initialize_dispatch_origin(info, physical.disclosure, grid_protocol=physical.protocol,
        generation_mw=physical.generation_mw, base_availability=physical.base_availability,
        selector=selector, solver_specification=spec, budget=budget)


def inputs(ramp=10., demand=20., dc=5, generation=20., spec=SPEC):
    info = view(prepared(ramp), current(demand=demand))
    physical = origin(info, generation=generation)
    before = wrap(info, physical, spec=spec)
    return info, disclose_current(physical.disclosure, CurrentOutageReport(1, None, None)), before, power(mw=dc)


def run(args, selector=SELECTOR, spec=SPEC, budget=SHORT):
    return runner.select_actual_dispatch(*args, expected_identity=runner.dispatch_input_identity(*args),
        selector=selector, solver_specification=spec, budget=budget)


def no_certificates(result):
    assert result.exact_lexicographic_certificate is result.causal_certificate is result.infeasibility_certificate is None
    assert result.capacity_certificate is None
    assert result.formal_result is result.security_certified is False


def install(monkeypatch, fault=None, stage=1, overrides=None):
    calls = {'create': 0, 'solve': 0}
    def create(spec):
        calls['create'] += 1
        class Fake:
            def solve(self, model, **kwargs):
                index = calls['solve']
                calls['solve'] += 1
                assert kwargs['load_solutions'] is False
                assert kwargs['options'] == solver_options(spec)
                active = fault if index == stage else None
                if active == 'exception':
                    raise RuntimeError('synthetic dispatch failure')
                values = {v.name: 0. for v in model.component_data_objects(Var)}
                values.update({'generation[G1]': 25., 'selector_deviation[G1]': 5.})
                values.update(overrides or {})
                if active == 'small_l1_slack':
                    values['selector_deviation[G1]'] += 5e-7
                if active == 'small_l1_drift':
                    values['generation[G1]'] += 5e-7
                    values['selector_deviation[G1]'] += 5e-7
                if active == 'small_uid_drift':
                    values['generation[G1]'] += 5e-7
                    values['generation[G2]'] -= 5e-7
                    values['selector_deviation[G1]'] += 5e-7
                    values['selector_deviation[G2]'] -= 5e-7
                if active == 'balance':
                    values['generation[G1]'] = 20.
                clone = model.clone()
                for name, number in values.items():
                    clone.find_component(name).set_value(number, skip_validation=True)
                objective = value(clone.objective)
                native = SolverResults()
                native.solver.status = SolverStatus.ok
                native.solver.termination_condition = TerminationCondition.optimal
                native.problem.sense = ProblemSense.minimize
                native.problem.number_of_objectives = 1
                native.problem.lower_bound = native.problem.upper_bound = objective
                solution = native.solution.add()
                solution._cuid = False
                solution.status = SolutionStatus.optimal
                solution.variable.update({name: {'Value': x} for name, x in values.items()})
                solution.objective['objective'] = {'Value': objective}
                if active == 'timeout':
                    native.solver.termination_condition = TerminationCondition.maxTimeLimit
                    solution.status = SolutionStatus.feasible
                elif active == 'missing_bound':
                    native.problem.lower_bound = None
                elif active == 'negative_bound':
                    native.problem.lower_bound = -1.
                elif active == 'gap':
                    native.problem.lower_bound = objective-1e-6
                elif active == 'objective':
                    solution.objective['objective']['Value'] = objective+1.
                elif active == 'missing_variable':
                    del solution.variable['selector_deviation[G1]']
                elif active == 'infeasible':
                    native.solver.termination_condition = TerminationCondition.infeasible
                    native.solution.clear()
                elif active == 'contradictory':
                    native.solver.termination_condition = TerminationCondition.infeasible
                elif active == 'options':
                    kwargs['options']['threads'] = 2
                return native
        return Fake(), solver_options(spec)
    monkeypatch.setattr(pipeline, 'create_solver', create)
    return calls


def second_inputs(state, dc=5):
    info = view(prepared(10.), current(2, demand=20.))
    disclosure = disclose_current(state.physical_carry.disclosure, CurrentOutageReport(2, None, None))
    return info, disclosure, state, power(t=2, mw=dc)


def test_real_fixed_power_and_next_hour():
    args = inputs()
    result = run(args)
    assert result.status == 'selected_numerical_dispatch', result.errors
    assert result.solver_calls == result.planned_solver_calls == 2
    assert tuple(s.raw_solve.objective for s in result.stages) == (5., 25.)
    state = result.next_dispatch_state
    assert state.physical_carry.generation_mw == (('G1', 25.),)
    assert state.origin_identity == state.previous_state_identity == args[2].identity
    second = run(second_inputs(state))
    assert second.status == 'selected_numerical_dispatch', second.errors
    assert second.next_dispatch_state.previous_state_identity == state.identity
    assert second.next_dispatch_state.origin_identity == args[2].identity
    assert second.next_dispatch_state.selector_policy_identity == state.selector_policy_identity
    assert json.dumps(asdict(second), allow_nan=False)
    no_certificates(second)


@pytest.mark.parametrize('reverse', [False, True])
def test_real_two_generator_dispatch_tie_uses_uid(reverse):
    info, disclosure, reference = two_inputs(reverse)
    budget = replace(SHORT, max_solver_calls=3, max_total_solver_seconds=3.)
    before = wrap(info, reference.physical_origin, budget=budget)
    result = run((info, disclosure, before, power(mw=100)), budget=budget)
    assert result.status == 'selected_numerical_dispatch', result.errors
    assert tuple(s.objective_label for s in result.stages) == ('l1_normal_deviation', 'generation:G1', 'generation:G2')
    assert tuple(s.raw_solve.objective for s in result.stages) == (80., 10., 90.)
    assert result.next_dispatch_state.physical_carry.generation_mw == (('G1', 10.), ('G2', 90.))
    for s in result.stages:
        assert s.fixed_previous_objective_hex == tuple(float(x).hex() for x in s.fixed_previous_objectives)
        assert s.canonical_objective_hex == float(s.raw_solve.objective).hex()
    no_certificates(result)


def test_real_extra_cfe_reduction_can_violate_down_ramp():
    feasible = run(inputs(demand=0., dc=20, generation=25.))
    assert feasible.status == 'selected_numerical_dispatch', feasible.errors
    failed = run(inputs(demand=0., dc=10, generation=25.))
    assert failed.status == 'unresolved' and failed.solver_calls == 1
    assert failed.next_dispatch_state is None
    no_certificates(failed)


@pytest.mark.parametrize('stage', [0, 1])
@pytest.mark.parametrize('fault', ['timeout', 'exception', 'missing_bound', 'missing_variable', 'infeasible'])
def test_stage_failure_never_commits_partial_dispatch(monkeypatch, stage, fault):
    args = inputs()
    calls = install(monkeypatch, fault, stage)
    result = run(args)
    assert result.status == 'unresolved' and result.next_dispatch_state is None
    assert calls == {'create': stage+1, 'solve': stage+1}
    assert args[2].physical_origin.source_hour == 0
    no_certificates(result)


@pytest.mark.parametrize('fault', ['balance', 'negative_bound', 'gap', 'objective', 'contradictory', 'options'])
def test_native_optimal_does_not_bypass_audits(monkeypatch, fault):
    install(monkeypatch, fault)
    result = run(inputs())
    assert result.status == 'unresolved' and len(result.stages) == 2
    assert result.next_dispatch_state is None


@pytest.mark.parametrize('fault,stage', [('small_l1_slack', 0), ('small_l1_slack', 1), ('small_l1_drift', 1)])
def test_small_objective_drift_rejected_under_looser_physical_gate(monkeypatch, fault, stage):
    install(monkeypatch, fault, stage)
    spec = replace(SPEC, feasibility_tolerance=1e-6, optimality_tolerance=1e-6, integer_feasibility_tolerance=1e-6)
    result = run(inputs(spec=spec), spec=spec)
    last = result.stages[-1]
    assert last.raw_solve.optimal and last.assignment_witness.physical_assignment_valid
    assert last.maximum_objective_lock_violation == 5e-7
    assert 'dispatch_exact_lock_or_deviation_violation' in last.errors
    assert result.next_dispatch_state is None


@pytest.mark.parametrize('changes', [{'max_solver_calls': 1}, {'max_total_solver_seconds': 1.},
    {'max_variables': 1}, {'max_constraints': 1}, {'max_seconds_per_solve': .5}])
def test_complete_budget_precedes_any_solver(monkeypatch, changes):
    calls = install(monkeypatch)
    with pytest.raises(ValueError):
        run(inputs(), budget=replace(SHORT, **changes))
    assert calls == {'create': 0, 'solve': 0}


def test_final_stage_scale_checked_before_first_call(monkeypatch):
    args = inputs()
    first = runner._stage_model(*args, 0, ())
    calls = install(monkeypatch)
    budget = replace(SHORT, max_constraints=runner.model_scale(first).constraints)
    before = wrap(args[0], args[2].physical_origin, budget=budget)
    with pytest.raises(ValueError, match='scale'):
        run((args[0], args[1], before, args[3]), budget=budget)
    assert calls == {'create': 0, 'solve': 0}


def test_policy_change_and_later_failure_preserve_actual_state(monkeypatch):
    install(monkeypatch)
    state = run(inputs()).next_dispatch_state
    identity = state.identity
    calls = install(monkeypatch)
    with pytest.raises(ValueError, match='policy changed'):
        run(second_inputs(state), selector=replace(SELECTOR, absolute_gap_mw=1e-8))
    assert calls == {'create': 0, 'solve': 0}
    install(monkeypatch, 'timeout', 1)
    failed = run(second_inputs(state))
    assert failed.next_dispatch_state is None
    assert state.identity == identity and state.physical_carry.source_hour == 1


def test_reference_and_raw_state_are_not_actual_dispatch_state(monkeypatch):
    from test_rq2_reference_grid_v1 import args as reference_args
    args = inputs()
    calls = install(monkeypatch)
    for wrong in (args[2].physical_origin, reference_args()[2]):
        with pytest.raises(ValueError, match='owned actual dispatch'):
            run((args[0], args[1], wrong, args[3]))
    assert calls == {'create': 0, 'solve': 0}
    with pytest.raises(TypeError):
        replace(args[2], contract='changed')


@pytest.mark.parametrize('where', ['input', 'policy'])
def test_post_solve_identity_drift_rejected(monkeypatch, where):
    args = inputs()
    install(monkeypatch)
    solve = runner._solve
    def changed(*a, **kw):
        raw = solve(*a, **kw)
        monkeypatch.setattr(runner, 'dispatch_input_identity' if where == 'input' else '_policy_identity', lambda *a: 'f'*64)
        return raw
    monkeypatch.setattr(runner, '_solve', changed)
    with pytest.raises(ValueError, match='drifted'):
        run(args)


def test_independent_objective_check_rejects_corrupt_summary(monkeypatch):
    install(monkeypatch)
    solve = runner._solve
    def changed(*a, **kw):
        raw = solve(*a, **kw)
        return pipeline._make(pipeline.GridSolveEvidence, **dict(vars(raw),
            objective=raw.objective+2e-6, lower=raw.lower+2e-6, upper=raw.upper+2e-6))
    monkeypatch.setattr(runner, '_solve', changed)
    result = run(inputs())
    assert result.status == 'unresolved' and result.solver_calls == 1
    assert 'dispatch_exact_lock_or_deviation_violation' in result.stages[0].errors


def test_exact_rational_power_is_audited_without_request_optimization(monkeypatch):
    from src.rq2_joint_deliverability_boundary_v1.current_grid_step import PrescribedDcPower
    args = inputs(demand=20.)
    args = (*args[:3], PrescribedDcPower(1, '1', '3', 'mechanism_assumption'))
    install(monkeypatch, overrides={'generation[G1]': 20.+1/3, 'selector_deviation[G1]': 1/3})
    result = run(args)
    assert result.status == 'selected_numerical_dispatch', result.errors
    assert result.stages[-1].assignment_witness.maximum_exact_violation > 0
    assert result.prescribed_power == args[3]
    assert 'reference_power' not in dict(result.stages[-1].raw_solve.loaded_values)
    changed = (*args[:3], PrescribedDcPower(1, '2', '3', 'mechanism_assumption'))
    assert runner.dispatch_input_identity(*args) != runner.dispatch_input_identity(*changed)


@pytest.mark.parametrize('field,new', [('CONTRACT', 'changed'), ('PURPOSE', 'changed'), ('TOLERANCE', 1e-5)])
def test_contract_drift_precedes_solver(monkeypatch, field, new):
    calls = install(monkeypatch)
    monkeypatch.setattr(runner, field, new)
    with pytest.raises(ValueError, match='contract drift'):
        run(inputs())
    assert calls == {'create': 0, 'solve': 0}


@pytest.mark.parametrize('change', ['selector', 'solver', 'budget'])
def test_first_hour_retry_cannot_change_origin_policy(monkeypatch, change):
    args = inputs()
    install(monkeypatch, 'timeout', 0)
    assert run(args).next_dispatch_state is None
    calls = install(monkeypatch)
    options = dict(selector=SELECTOR, spec=SPEC, budget=SHORT)
    if change == 'selector':
        options['selector'] = replace(SELECTOR, lock_tolerance_mw=1e-8)
    elif change == 'solver':
        options['spec'] = replace(SPEC, feasibility_tolerance=1e-8)
    else:
        options['budget'] = replace(SHORT, max_total_solver_seconds=3.)
    with pytest.raises(ValueError, match='policy changed'):
        run(args, **options)
    assert calls == {'create': 0, 'solve': 0}


@pytest.mark.parametrize('fault', ['timeout', 'small_uid_drift'])
def test_last_uid_failure_never_publishes_a_partial_selection(monkeypatch, fault):
    info, disclosure, reference = two_inputs()
    budget = replace(SHORT, max_solver_calls=3, max_total_solver_seconds=3.)
    spec = replace(SPEC, feasibility_tolerance=1e-6, optimality_tolerance=1e-6, integer_feasibility_tolerance=1e-6)
    before = wrap(info, reference.physical_origin, spec=spec, budget=budget)
    install(monkeypatch, fault, 2, overrides={'generation[G1]': 10., 'generation[G2]': 90.,
        'selector_deviation[G1]': 0., 'selector_deviation[G2]': 80.})
    result = run((info, disclosure, before, power(mw=100)), spec=spec, budget=budget)
    assert result.status == 'unresolved' and result.solver_calls == 3
    assert all(s.accepted for s in result.stages[:2])
    assert result.next_dispatch_state is None and before.physical_origin.source_hour == 0
    if fault == 'small_uid_drift':
        assert result.stages[-1].raw_solve.optimal
        assert result.stages[-1].maximum_objective_lock_violation == 5e-7


def test_dispatch_replay_is_deterministic_and_cannot_reinitialize_derived_carry(monkeypatch):
    args = inputs()
    install(monkeypatch)
    first = run(args)
    install(monkeypatch)
    second = run(args)
    assert first.identity == second.identity
    assert first.next_dispatch_state == second.next_dispatch_state
    next_info = second_inputs(first.next_dispatch_state)[0]
    with pytest.raises(ValueError, match='origin disclosure'):
        wrap(next_info, first.next_dispatch_state.physical_carry)


def test_strict_expected_identity_rejects_custom_equality(monkeypatch):
    class EqualAnything:
        def __eq__(self, other):
            return True
    args = inputs()
    calls = install(monkeypatch)
    with pytest.raises(ValueError, match='SHA256'):
        runner.select_actual_dispatch(*args, expected_identity=EqualAnything(), selector=SELECTOR,
            solver_specification=SPEC, budget=SHORT)
    assert calls == {'create': 0, 'solve': 0}


def test_dispatch_fresh_import_dependency_closure():
    from pathlib import Path
    import subprocess
    import sys
    from src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal import SOURCE_DEPENDENCIES
    from src.rq2_joint_deliverability_boundary_v1.continuous_grid_candidate import EXTRA_DEPENDENCIES
    script = '''
import json, sys
from pathlib import Path
import src.rq2_joint_deliverability_boundary_v1.actual_dispatch_selector
root = Path.cwd()
print(json.dumps(sorted(Path(module.__file__).resolve().relative_to(root).as_posix()
    for name, module in sys.modules.items() if name == 'src' or name.startswith('src.'))))
'''
    result = subprocess.run([sys.executable, '-B', '-c', script], check=True, capture_output=True,
        text=True, cwd=Path(__file__).resolve().parents[1], timeout=30)
    expected = set(SOURCE_DEPENDENCIES) | set(EXTRA_DEPENDENCIES) | {
        'src/rq2_joint_deliverability_boundary_v1/'+name+'.py'
        for name in ('actual_dispatch_selector', 'current_grid_step', 'grid_information', 'event_disclosure')}
    assert set(json.loads(result.stdout)) == expected
