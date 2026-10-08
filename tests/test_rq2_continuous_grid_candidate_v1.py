from dataclasses import asdict, replace
import json
from pathlib import Path
import subprocess
import sys

import pytest
from pyomo.environ import Var
from pyomo.opt import SolverResults, SolverStatus, TerminationCondition, SolutionStatus
from pyomo.opt.results.problem import ProblemSense

from test_rq2_continuous_grid_normal_v1 import fixture, assignment_for
from src.scenarios.rts_gmlc_n1_chronology import N1OutageEvent
from src.solvers.rq2_solver_adapter import Rq2SolverSpec, solver_options
from src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal import normal_input_identity, SOURCE_DEPENDENCIES
from src.rq2_joint_deliverability_boundary_v1.grid_carry import UnitPoint
from src.rq2_joint_deliverability_boundary_v1 import continuous_grid_candidate as runner

SPEC = Rq2SolverSpec('highs', '1.15.1', 1, 1e-8, 1e-9, 1e-9, 1e-9, 0, 1., False)
BUDGET = runner.GridDevelopmentBudget('synthetic normal/incident connection', 1., 1, 8, 1000, 2000, 10, 10.)
EVENT = N1OutageEvent(1, 'original_event', 'branch', 'AC1', 0, 2)


def run(inputs=None, *, events=(), spec=SPEC, budget=BUDGET):
    inputs = fixture(3) if inputs is None else inputs
    return runner.run_short_grid_candidate(inputs, expected_identity=normal_input_identity(inputs), events=events,
        event_evidence_role='mechanism_assumption', solver_specification=spec, budget=budget)


def test_real_normal_all_hours_without_events():
    result = run(fixture(2))
    assert result.normal.optimal, result.normal.errors
    assert result.normal_witness.errors == ()
    assert result.solver_calls == 1
    assert result.finite_grid_need_trace_available
    assert all(h.baseline_generation and h.baseline_commitment and h.grid_need_mw == 0 for h in result.hours)
    assert result.formal_result is result.security_certified is False
    assert result.corrective_cross_hour_feasibility is None
    assert len(result.result_id) == 64


def test_real_branch_event_keeps_original_interval():
    result = run(events=(EVENT,))
    assert result.normal.optimal, result.normal.errors
    assert result.solver_calls == 3
    assert result.finite_grid_need_trace_available, [(h.state, None if h.corrective is None else h.corrective.errors) for h in result.hours]
    assert tuple(h.event for h in result.hours) == (EVENT, EVENT, None)
    assert tuple(h.outage_source_index for h in result.hours) == (0, 1, 2)
    assert all(h.baseline_generation for h in result.hours)
    completion = result.hours[0].corrective.canonical_completed_values
    assert ('angle_degrees[1]', 0., 'canonical_fixed_constant') in completion
    assert ('angle_degrees[2]', 0., 'unused_unbounded_continuous_representative') in completion


def test_real_generator_outage_zero_dc_confirmation():
    event = replace(EVENT, component_type='generator', uid='G1', end_hour_exclusive=1)
    result = run(fixture(1), events=(event,))
    row = result.hours[0]
    assert row.state == 'solver_reported_exogenous_infeasibility', (row.corrective, row.zero_dc_confirmation)
    assert row.grid_need_mw is None and row.zero_dc_confirmation is not None
    assert not result.finite_grid_need_trace_available and result.solver_calls == 3


def install(monkeypatch, inputs, *, fault=None, affected_call=1):
    baseline = assignment_for(inputs)
    calls = {'create': 0, 'solve': 0}
    def create(spec):
        calls['create'] += 1
        class Fake:
            def solve(self, model, **kwargs):
                calls['solve'] += 1
                active = fault if calls['solve'] == affected_call else None
                assert kwargs['load_solutions'] is False
                assert kwargs['options'] == solver_options(spec)
                if active == 'exception':
                    raise RuntimeError('synthetic solve failure')
                native = SolverResults()
                native.solver.status = SolverStatus.ok
                native.solver.termination_condition = TerminationCondition.optimal
                native.problem.sense = ProblemSense.minimize
                native.problem.number_of_objectives = 1
                objective = 20. * len(inputs.source_hours) if hasattr(model, 'operating_cost') else 0.
                native.problem.lower_bound = native.problem.upper_bound = objective
                solution = native.solution.add()
                solution._cuid = False
                solution.status = SolutionStatus.optimal
                values = baseline if hasattr(model, 'operating_cost') else {
                    v.name: 20. if v.name == 'generation[G1]' else 0. for v in model.component_data_objects(Var)}
                solution.variable.update({name: {'Value': val} for name, val in values.items()})
                solution.objective['objective'] = {'Value': objective}
                if active == 'timeout':
                    native.solver.termination_condition = TerminationCondition.maxTimeLimit
                elif active == 'missing':
                    del solution.variable[next(iter(solution.variable))]
                elif active == 'unknown':
                    solution.variable['foreign'] = {'Value': 0.}
                elif active == 'nan':
                    solution.variable[next(iter(solution.variable))]['Value'] = float('nan')
                elif active == 'objective':
                    solution.objective['objective']['Value'] += 1.
                elif active == 'inverted_bounds':
                    native.problem.lower_bound = objective + 1.
                elif active == 'solution_status':
                    solution.status = SolutionStatus.infeasible
                elif active == 'multi_solution':
                    native.solution.add()
                elif active == 'multi_solver':
                    native.solver.add()
                elif active == 'multi_problem':
                    native.problem.add()
                elif active == 'options':
                    kwargs['options']['threads'] = 2
                elif active == 'structure':
                    next(model.component_data_objects(runner.Constraint)).deactivate()
                elif active == 'root_deactivation':
                    model.deactivate()
                elif active == 'preload':
                    next(model.component_data_objects(Var)).set_value(1.)
                elif active == 'load':
                    old = model.solutions.load_from
                    def changed(*args, **kw):
                        old(*args, **kw)
                        next(model.component_data_objects(Var)).set_value(.5)
                    model.solutions.load_from = changed
                elif active == 'none':
                    native.solution.clear()
                elif active == 'missing_objective_map':
                    solution.objective.clear()
                elif active == 'nonfinite_bound':
                    native.problem.upper_bound = float('nan')
                elif active == 'negative_corrective_upper':
                    native.problem.lower_bound = native.problem.upper_bound = -1e-10
                elif active == 'infeasible_error':
                    native.solution.clear()
                    native.solver.status = SolverStatus.error
                    native.solver.termination_condition = TerminationCondition.infeasible
                elif active == 'native_infeasible':
                    native.solution.clear()
                    native.solver.status = SolverStatus.warning
                    native.solver.termination_condition = TerminationCondition.infeasible
                return native
        return Fake(), solver_options(spec)
    monkeypatch.setattr(runner, 'create_solver', create)
    return calls


@pytest.mark.parametrize('fault', ['exception', 'timeout', 'missing', 'unknown', 'nan', 'objective',
    'inverted_bounds', 'solution_status', 'multi_solution', 'multi_solver', 'multi_problem', 'options',
    'structure', 'root_deactivation', 'preload', 'load', 'none', 'nonfinite_bound'])
def test_normal_fault_does_not_start_corrective(monkeypatch, fault):
    inputs = fixture(3)
    calls = install(monkeypatch, inputs, fault=fault)
    result = run(inputs, events=(EVENT,))
    assert calls['solve'] == result.solver_calls == 1
    assert not result.normal.optimal
    assert all(h.state == 'unresolved_grid_need' and h.grid_need_mw is None for h in result.hours)
    if fault == 'timeout':
        assert result.normal_witness is not None


def test_one_corrective_timeout_preserves_other_hours(monkeypatch):
    inputs = fixture(3)
    calls = install(monkeypatch, inputs, fault='timeout', affected_call=2)
    result = run(inputs, events=(EVENT,))
    assert calls['solve'] == 3
    assert tuple(h.state for h in result.hours) == ('unresolved_grid_need', 'finite_grid_need', 'finite_grid_need')
    assert not result.finite_grid_need_trace_available
    assert result.hours[0].corrective.assignment_valid


@pytest.mark.parametrize('events', [(replace(EVENT, seed=2),), (EVENT, EVENT),
    (EVENT, replace(EVENT, event_id='overlap')), (replace(EVENT, uid='unknown'),),
    (replace(EVENT, start_hour=True),), (replace(EVENT, end_hour_exclusive=4),)])
def test_invalid_event_before_solver_creation(monkeypatch, events):
    inputs = fixture(3)
    calls = install(monkeypatch, inputs)
    with pytest.raises(ValueError):
        run(inputs, events=events)
    assert calls == {'create': 0, 'solve': 0}


@pytest.mark.parametrize('changes', [{'max_solver_calls': 4}, {'max_total_solver_seconds': 4.},
    {'max_horizon': 2}, {'max_variables': 1}, {'max_constraints': 1}])
def test_budget_admission_before_solve(monkeypatch, changes):
    inputs = fixture(3)
    calls = install(monkeypatch, inputs)
    with pytest.raises(ValueError):
        run(inputs, events=(EVENT,), budget=replace(BUDGET, **changes))
    assert calls == {'create': 0, 'solve': 0}


def test_result_cannot_be_relabelled(monkeypatch):
    inputs = fixture(3)
    install(monkeypatch, inputs)
    result = run(inputs)
    with pytest.raises(TypeError):
        replace(result, formal_result=True)
    with pytest.raises(TypeError):
        replace(result.normal, optimal=False)
    assert json.dumps(asdict(result), allow_nan=False)


def test_event_schedule_does_not_change_normal_model(monkeypatch):
    inputs = fixture(3)
    install(monkeypatch, inputs)
    without = run(inputs)
    with_event = run(inputs, events=(EVENT,))
    assert without.normal.structures == with_event.normal.structures
    assert without.normal.loaded_values == with_event.normal.loaded_values
    assert without.event_identity != with_event.event_identity


def test_candidate_dependencies_cover_fresh_import_closure():
    script = '''
import json, sys
from pathlib import Path
import src.rq2_joint_deliverability_boundary_v1.continuous_grid_candidate
root=Path.cwd()
print(json.dumps(sorted(Path(m.__file__).resolve().relative_to(root).as_posix()
    for n,m in sys.modules.items() if n == 'src' or n.startswith('src.'))))
'''
    result = subprocess.run([sys.executable, '-B', '-c', script], check=True, capture_output=True, text=True,
                            cwd=Path(__file__).resolve().parents[1], timeout=30)
    assert set(json.loads(result.stdout)) == set(SOURCE_DEPENDENCIES) | set(runner.EXTRA_DEPENDENCIES)


def test_real_positive_grid_need_from_binding_dc_transfer():
    base = fixture(1)
    generator = replace(base.data.generators[0], p_max_mw=150.,
        cost_breakpoints_mw=(10., 60., 110., 150.), cost_values_usd_per_hour=(10., 60., 110., 150.))
    point = replace(base.data.hourly_points[0], demand_by_bus_mw={1: 0., 2: 100.},
                    generator_max_mw={'G1': 150.})
    initial = replace(base.initial, generation_mw={'G1': 120.})
    inputs = replace(base, data=replace(base.data, generators=(generator,), hourly_points=(point,)),
        initial=initial, carry=replace(base.carry, points=(UnitPoint('G1', True, 120.),),
            limits=(replace(base.carry.limits[0], maximum_power_mw=150.),)),
        request=replace(base.request, initial_generation_mw={'G1': 120.},
            system_demand_by_bus_mw=({1: 0., 2: 100.},), dc_bus=2, dc_requested_mw=(20.,),
            dc_physical_maximum_mw=(20.,), dc_connected_capacity_mw=(20.,)))
    result = run(inputs, events=(replace(EVENT, end_hour_exclusive=1),))
    row = result.hours[0]
    assert result.normal.optimal and row.state == 'finite_grid_need', (result.normal, row)
    assert row.grid_need_mw == pytest.approx(20.)
    assert row.corrective.lower == pytest.approx(20.)
    assert row.corrective.upper == pytest.approx(20.)


def test_window_starts_inside_original_event(monkeypatch):
    base = fixture(3)
    request = base.request
    hourly = ('timestamps', 'periods', 'system_demand_by_bus_mw', 'generator_availability',
        'dc_requested_mw', 'dc_flexible_demand_mw', 'dc_recoverable_flexible_mw',
        'dc_physical_maximum_mw', 'dc_connected_capacity_mw', 'dc_call_limit_mw', 'recovery_headroom_mw')
    request = replace(request, **{name: getattr(request, name)[1:] for name in hourly})
    inputs = replace(base, request=request, carry=replace(base.carry, source_hour=1), source_hours=(2, 3))
    install(monkeypatch, inputs)
    result = run(inputs, events=(EVENT,))
    assert result.hours[0].source_hour == 2 and result.hours[0].outage_source_index == 1
    assert result.hours[0].event.start_hour == 0
    assert result.hours[0].event.end_hour_exclusive == 2
    assert result.hours[1].event is None


def test_used_variable_missing_cannot_be_completed(monkeypatch):
    inputs = fixture(3)
    install(monkeypatch, inputs, fault='missing')
    result = run(inputs)
    assert not result.normal.optimal
    assert any('missing native decision variable' in error for error in result.normal.errors)


def test_raw_timeout_is_not_exogenous(monkeypatch):
    inputs = fixture(3)
    calls = install(monkeypatch, inputs, fault='timeout', affected_call=2)
    result = run(inputs, events=(EVENT,))
    assert not result.hours[0].corrective.native_infeasible
    assert result.hours[0].zero_dc_confirmation is None
    assert calls['solve'] == 3


def test_native_objective_absence_retained_and_ub_still_checked(monkeypatch):
    inputs = fixture(3)
    install(monkeypatch, inputs, fault='missing_objective_map')
    result = run(inputs)
    assert result.normal.optimal and result.normal.native_objectives == ()
    assert result.normal.objective == result.normal.upper == 60.


def test_corrective_negative_upper_does_not_certify_finite_need(monkeypatch):
    inputs = fixture(3)
    install(monkeypatch, inputs, fault='negative_corrective_upper', affected_call=2)
    result = run(inputs, events=(EVENT,))
    assert result.hours[0].state == 'unresolved_grid_need'
    assert result.hours[0].grid_need_mw is None


def test_error_infeasible_mapping_not_used_for_normal_mip(monkeypatch):
    inputs = fixture(3)
    install(monkeypatch, inputs, fault='infeasible_error')
    result = run(inputs, events=(EVENT,))
    assert not result.normal.native_infeasible
    assert result.solver_calls == 1


def test_zero_dc_feasible_does_not_turn_primary_report_into_exogenous(monkeypatch):
    inputs = fixture(3)
    calls = install(monkeypatch, inputs, fault='native_infeasible', affected_call=2)
    result = run(inputs, events=(EVENT,))
    assert result.hours[0].corrective.native_infeasible
    assert result.hours[0].zero_dc_confirmation.optimal
    assert result.hours[0].state == 'unresolved_grid_need'
    assert result.hours[0].grid_need_mw is None and calls['solve'] == 4
