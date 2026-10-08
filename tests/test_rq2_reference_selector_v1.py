from dataclasses import asdict, replace
import json

import pytest
from pyomo.environ import Var, value
from pyomo.opt import SolverResults, SolverStatus, SolutionStatus, TerminationCondition
from pyomo.opt.results.problem import ProblemSense

from test_rq2_reference_grid_v1 import args
from test_rq2_current_grid_step_v1 import prepared, current, view
from test_rq2_continuous_grid_candidate_v1 import SPEC, BUDGET
from src.solvers.rq2_solver_adapter import solver_options
from src.rq2_joint_deliverability_boundary_v1 import reference_grid as ref
from src.rq2_joint_deliverability_boundary_v1 import reference_selector as runner
from src.rq2_joint_deliverability_boundary_v1 import continuous_grid_candidate as pipeline
from src.rq2_joint_deliverability_boundary_v1.event_disclosure import CurrentOutageReport, disclose_current


SELECTOR = runner.ReferenceSelectorSpec('request_l1_normal_deviation_generation_uid_order', 1e-7, 1e-8, 1e-9, 'mechanism_assumption')
SHORT = replace(BUDGET, purpose='common_reference_numerical_lexicographic_selection',
    max_solver_calls=3, max_total_solver_seconds=3., max_horizon=1)


def run(inputs, selector=SELECTOR, spec=SPEC, budget=SHORT):
    return runner.select_reference_hour(*inputs, expected_identity=ref.reference_input_identity(*inputs),
        selector=selector, solver_specification=spec, budget=budget)


def no_certificates(result):
    assert result.exact_lexicographic_certificate is result.causal_certificate is result.infeasibility_certificate is None
    assert result.capacity_certificate is None
    assert result.formal_result is result.security_certified is False


def install(monkeypatch, fault=None, stage=1, values_override=None):
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
                    raise RuntimeError('synthetic selector failure')
                values = {v.name: 0. for v in model.component_data_objects(Var)}
                values.update({'reference_power': 10., 'generation[G1]': 30., 'selector_deviation[G1]': 10.})
                values.update(values_override or {})
                if active == 'prior_lock':
                    values.update({'reference_power': 9., 'generation[G1]': 29., 'selector_deviation[G1]': 9.})
                if active == 'deviation':
                    values['selector_deviation[G1]'] = 11.
                if active == 'small_lock_drift':
                    values.update({'reference_power': 9.9999995, 'generation[G1]': 29.9999995,
                        'selector_deviation[G1]': 9.9999995})
                if active == 'small_l1_slack':
                    values['selector_deviation[G1]'] = 10.0000005
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


def test_real_three_stage_reference_and_next_hour():
    inputs = args()
    result = run(inputs)
    assert result.status == 'selected_numerical_reference', result.errors
    assert result.selected_request_exact == ('15', '1')
    assert result.solver_calls == result.planned_solver_calls == 3
    assert tuple(s.raw_solve.objective for s in result.stages) == (15., 10., 30.)
    state = result.next_reference_state
    assert state.physical_carry.generation_mw == (('G1', 30.),)
    assert state.origin_identity == state.previous_state_identity == inputs[2].identity
    assert state.selector_policy_identity == result.selector_policy_identity
    second_info = view(prepared(10.), replace(current(2, demand=20.), dc_baseline_mw=25.))
    disclosure = disclose_current(state.physical_carry.disclosure, CurrentOutageReport(2, None, None))
    second = run((second_info, disclosure, state))
    assert second.status == 'selected_numerical_reference', second.errors
    assert second.selected_request_exact == ('15', '1')
    assert second.next_reference_state.origin_identity == inputs[2].identity
    assert second.next_reference_state.previous_state_identity == state.identity
    assert json.dumps(asdict(second), allow_nan=False)
    no_certificates(second)


def test_real_nonmonotone_domain_selects_baseline():
    result = run(args(demand=0., baseline=20., generation=25.))
    assert result.status == 'selected_numerical_reference', result.errors
    assert result.selected_request_exact == ('0', '1')
    assert result.next_reference_state.physical_carry.generation_mw == (('G1', 20.),)
    no_certificates(result)


def test_real_empty_domain_does_not_create_request_or_next_state():
    inputs = args(demand=0., baseline=0.)
    result = run(inputs)
    assert result.status == 'unresolved'
    assert result.solver_calls == 1 and len(result.stages) == 1
    assert result.selected_request_exact is result.next_reference_state is None
    assert inputs[2].physical_origin.source_hour == 0
    no_certificates(result)


@pytest.mark.parametrize('stage', [0, 1, 2])
@pytest.mark.parametrize('fault', ['timeout', 'exception', 'missing_bound', 'missing_variable', 'infeasible'])
def test_any_stage_failure_stops_without_partial_commit(monkeypatch, stage, fault):
    inputs = args()
    calls = install(monkeypatch, fault, stage)
    result = run(inputs)
    assert result.status == 'unresolved'
    assert calls == {'create': stage+1, 'solve': stage+1}
    assert len(result.stages) == stage+1
    assert result.selected_request_exact is result.next_reference_state is None
    assert inputs[2].physical_origin.source_hour == 0
    no_certificates(result)


@pytest.mark.parametrize('fault', ['prior_lock', 'deviation', 'negative_bound', 'gap', 'objective', 'contradictory', 'options'])
def test_native_optimal_label_does_not_replace_stage_audits(monkeypatch, fault):
    install(monkeypatch, fault)
    result = run(args())
    assert result.status == 'unresolved'
    assert result.next_reference_state is None
    assert len(result.stages) == 2 and not result.stages[-1].accepted
    if fault == 'deviation':
        assert result.stages[-1].raw_solve.optimal
        assert 'selector_exact_lock_or_deviation_violation' in result.stages[-1].errors


@pytest.mark.parametrize('changes', [{'max_solver_calls': 2}, {'max_total_solver_seconds': 2.},
    {'max_variables': 1}, {'max_constraints': 1}, {'max_seconds_per_solve': .5}])
def test_complete_budget_checked_before_first_solver(monkeypatch, changes):
    calls = install(monkeypatch)
    with pytest.raises(ValueError):
        run(args(), budget=replace(SHORT, **changes))
    assert calls == {'create': 0, 'solve': 0}


def test_final_stage_scale_checked_before_first_call(monkeypatch):
    inputs = args()
    first = runner._stage_model(*inputs, ref.reference_input_identity(*inputs), 0, ())
    count = runner.model_scale(first).constraints
    calls = install(monkeypatch)
    with pytest.raises(ValueError, match='scale'):
        run(inputs, budget=replace(SHORT, max_constraints=count))
    assert calls == {'create': 0, 'solve': 0}


def test_policy_cannot_change_after_selected_state(monkeypatch):
    inputs = args()
    install(monkeypatch)
    state = run(inputs).next_reference_state
    info = view(prepared(10.), replace(current(2, demand=20.), dc_baseline_mw=25.))
    disclosure = disclose_current(state.physical_carry.disclosure, CurrentOutageReport(2, None, None))
    calls = install(monkeypatch)
    with pytest.raises(ValueError, match='policy changed'):
        run((info, disclosure, state), selector=replace(SELECTOR, absolute_gap_mw=1e-8))
    assert calls == {'create': 0, 'solve': 0}


def test_owned_state_and_raw_carry_separation(monkeypatch):
    inputs = args()
    install(monkeypatch)
    result = run(inputs)
    with pytest.raises(TypeError):
        replace(result.next_reference_state, selector_policy_identity='f'*64)
    with pytest.raises(TypeError):
        replace(result, formal_result=True)
    with pytest.raises(ValueError, match='arm actual carry'):
        run((inputs[0], inputs[1], inputs[2].physical_origin))


@pytest.mark.parametrize('where', ['input', 'policy'])
def test_post_solve_identity_drift_is_not_a_selected_result(monkeypatch, where):
    inputs = args()
    install(monkeypatch)
    solve = runner._solve
    def changed(*a, **kw):
        raw = solve(*a, **kw)
        if where == 'input':
            monkeypatch.setattr(runner, 'reference_input_identity', lambda *a: 'f'*64)
        else:
            monkeypatch.setattr(runner, '_policy_identity', lambda *a: 'f'*64)
        return raw
    monkeypatch.setattr(runner, '_solve', changed)
    with pytest.raises(ValueError, match='drifted'):
        run(inputs)


def two_inputs(reverse=False):
    from test_rq2_continuous_grid_normal_v1 import fixture, assignment_for
    from test_rq2_grid_information_v1 import prepare
    from test_rq2_current_grid_step_v1 import protocol
    from src.rq2_joint_deliverability_boundary_v1.event_disclosure import (
        OutageComponent, DisclosureProtocol, initialize_disclosure)
    inputs = fixture()
    g1 = replace(inputs.data.generators[0], ramp_mw_per_hour=100., ramp_mw_per_minute=100./60.)
    g2 = replace(g1, uid='G2')
    initial = replace(inputs.initial, commitment={'G1': True, 'G2': True},
        generation_mw={'G1': 10., 'G2': 10.}, time_in_state_hours={'G1': 1, 'G2': 1})
    points = tuple(replace(p, generator_min_mw={'G1': 10., 'G2': 10.},
        generator_max_mw={'G1': 100., 'G2': 100.}) for p in inputs.data.hourly_points)
    limit = replace(inputs.carry.limits[0], ramp_mw_per_hour=100.)
    inputs = replace(inputs, data=replace(inputs.data, generators=(g2, g1) if reverse else (g1, g2), hourly_points=points),
        initial=initial, carry=replace(inputs.carry, limits=(limit, replace(limit, uid='G2')),
            points=(replace(inputs.carry.points[0], generation_mw=10.),
                replace(inputs.carry.points[0], uid='G2', generation_mw=10.)), elapsed_state_hours=(1, 1)),
        request=replace(inputs.request, initial_commitment=initial.commitment,
            initial_generation_mw=initial.generation_mw, initial_time_in_state_hours=initial.time_in_state_hours,
            generator_availability=({'G1': True, 'G2': True},)*3))
    assignment = assignment_for(inputs)
    for t in range(3):
        assignment[f'generation[normal,{t},G1]'] = 10.
        assignment[f'generation[normal,{t},G2]'] = 10.
        assignment[f'commitment[{t},G2]'] = 1.
        assignment[f'segment_power[{t},G1,0]'] = 0.
    info = view(prepare(inputs, assignment), replace(current(demand=0.),
        generator_min_mw=(('G1', 10.), ('G2', 10.)), generator_max_mw=(('G1', 100.), ('G2', 100.)),
        generator_available=(('G1', True), ('G2', True)),
        dc_baseline_mw=100., dc_physical_maximum_mw=100., dc_connected_capacity_mw=100.))
    declared = DisclosureProtocol((OutageComponent('generator', 'G1'), OutageComponent('generator', 'G2')),
        'current_n1_outage_overlay_revealed_before_current_action',
        'complete_current_n1_outage_overlay__no_hidden_same_hour_replacement', 'mechanism_assumption')
    incoming = initialize_disclosure(declared, source_hour=0, active_component=None)
    before = ref.initialize_reference_origin(info, incoming, reference_protocol=args()[2].protocol,
        grid_protocol=protocol(), generation_mw=(('G1', 10.), ('G2', 10.)), base_availability=info.current.generator_available)
    return info, disclose_current(incoming, CurrentOutageReport(1, None, None)), before


@pytest.mark.parametrize('reverse', [False, True])
def test_real_two_generator_l1_tie_uses_sorted_uid_order(reverse):
    result = run(two_inputs(reverse), budget=replace(SHORT, max_solver_calls=4, max_total_solver_seconds=4.))
    assert result.status == 'selected_numerical_reference', result.errors
    assert result.selected_request_exact == ('0', '1')
    assert tuple(s.objective_label for s in result.stages) == ('grid_request', 'l1_normal_deviation', 'generation:G1', 'generation:G2')
    assert tuple(s.raw_solve.objective for s in result.stages) == (0., 80., 10., 90.)
    assert result.next_reference_state.physical_carry.generation_mw == (('G1', 10.), ('G2', 90.))
    for s in result.stages:
        assert s.fixed_previous_objective_hex == tuple(float(x).hex() for x in s.fixed_previous_objectives)
        assert s.canonical_objective_hex == float(s.raw_solve.objective).hex()
    no_certificates(result)


def test_decimal_request_and_float_fixed_rhs_are_distinct(monkeypatch):
    inputs = args(demand=19.8, baseline=.3)
    install(monkeypatch, values_override={'reference_power': .2, 'generation[G1]': 20., 'selector_deviation[G1]': 0.})
    result = run(inputs)
    assert result.status == 'selected_numerical_reference', result.errors
    assert result.selected_request_exact == ('1', '10')
    assert result.stages[1].fixed_previous_objectives == (.3-.2,)
    assert result.stages[1].fixed_previous_objective_hex == ((.3-.2).hex(),)
    assert result.stages[1].fixed_previous_objectives[0] != .1


def test_reference_same_inputs_repeat_same_selected_state(monkeypatch):
    inputs = args()
    install(monkeypatch)
    first = run(inputs)
    install(monkeypatch)
    second = run(inputs)
    assert first.identity == second.identity
    assert first.next_reference_state == second.next_reference_state


def test_selector_fresh_import_dependency_closure():
    from pathlib import Path
    import subprocess
    import sys
    from src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal import SOURCE_DEPENDENCIES
    from src.rq2_joint_deliverability_boundary_v1.continuous_grid_candidate import EXTRA_DEPENDENCIES
    script = '''
import json, sys
from pathlib import Path
import src.rq2_joint_deliverability_boundary_v1.reference_selector
root = Path.cwd()
print(json.dumps(sorted(Path(module.__file__).resolve().relative_to(root).as_posix()
    for name, module in sys.modules.items() if name == 'src' or name.startswith('src.'))))
'''
    result = subprocess.run([sys.executable, '-B', '-c', script], check=True, capture_output=True,
        text=True, cwd=Path(__file__).resolve().parents[1], timeout=30)
    expected = set(SOURCE_DEPENDENCIES) | set(EXTRA_DEPENDENCIES) | {
        'src/rq2_joint_deliverability_boundary_v1/'+name+'.py'
        for name in ('reference_grid', 'reference_selector', 'current_grid_step', 'grid_information', 'event_disclosure')}
    assert set(json.loads(result.stdout)) == expected


def test_independent_current_objective_check_does_not_trust_summary(monkeypatch):
    inputs = args()
    install(monkeypatch)
    solve = runner._solve
    def changed(*a, **kw):
        raw = solve(*a, **kw)
        # Fault-inject a corrupted summary while retaining a complete feasible
        # assignment; this must not become a new fixed numerical objective.
        return pipeline._make(pipeline.GridSolveEvidence, **dict(vars(raw),
            objective=raw.objective+2e-6, lower=raw.lower+2e-6, upper=raw.upper+2e-6))
    monkeypatch.setattr(runner, '_solve', changed)
    result = run(inputs)
    assert result.status == 'unresolved' and result.solver_calls == 1
    assert 'selector_exact_lock_or_deviation_violation' in result.stages[0].errors
    assert result.selected_request_exact is result.next_reference_state is None


def test_failed_later_hour_retains_last_selected_state(monkeypatch):
    inputs = args()
    install(monkeypatch)
    state = run(inputs).next_reference_state
    identity = state.identity
    info = view(prepared(10.), replace(current(2, demand=20.), dc_baseline_mw=25.))
    disclosure = disclose_current(state.physical_carry.disclosure, CurrentOutageReport(2, None, None))
    install(monkeypatch, 'timeout', 2)
    result = run((info, disclosure, state))
    assert result.status == 'unresolved' and result.solver_calls == 3
    assert result.next_reference_state is None
    assert state.identity == identity and state.physical_carry.source_hour == 1


@pytest.mark.parametrize('field,new', [('CONTRACT', 'changed'), ('PURPOSE', 'changed'), ('TOLERANCE', 1e-5)])
def test_runtime_selector_contract_drift_precedes_solver(monkeypatch, field, new):
    calls = install(monkeypatch)
    monkeypatch.setattr(runner, field, new)
    with pytest.raises(ValueError, match='contract drift'):
        run(args())
    assert calls == {'create': 0, 'solve': 0}


@pytest.mark.parametrize('fault', ['small_lock_drift', 'small_l1_slack'])
def test_subphysical_tolerance_objective_drift_is_rejected(monkeypatch, fault):
    install(monkeypatch, fault, 1)
    spec = replace(SPEC, feasibility_tolerance=1e-6, optimality_tolerance=1e-6,
        integer_feasibility_tolerance=1e-6)
    result = run(args(), selector=replace(SELECTOR, absolute_gap_mw=1e-8), spec=spec)
    stage = result.stages[-1]
    assert stage.raw_solve.optimal and stage.assignment_witness.physical_assignment_valid
    assert stage.maximum_objective_lock_violation == 5e-7
    assert 'selector_exact_lock_or_deviation_violation' in stage.errors
    assert result.status == 'unresolved' and result.solver_calls == 2
    assert result.selected_request_exact is result.next_reference_state is None


@pytest.mark.parametrize('tolerance', [-1e-9, 1e-6, float('nan'), True])
def test_invalid_lock_tolerance_rejected(tolerance):
    with pytest.raises(ValueError):
        replace(SELECTOR, lock_tolerance_mw=tolerance)


def test_zero_lock_tolerance_does_not_round_decimal_objective(monkeypatch):
    install(monkeypatch, values_override={'reference_power': .2, 'generation[G1]': 20., 'selector_deviation[G1]': 0.})
    result = run(args(demand=19.8, baseline=.3), selector=replace(SELECTOR, lock_tolerance_mw=0.))
    assert result.status == 'unresolved' and result.solver_calls == 1
    assert result.stages[0].maximum_objective_lock_violation > 0
    assert result.selected_request_exact is result.next_reference_state is None
