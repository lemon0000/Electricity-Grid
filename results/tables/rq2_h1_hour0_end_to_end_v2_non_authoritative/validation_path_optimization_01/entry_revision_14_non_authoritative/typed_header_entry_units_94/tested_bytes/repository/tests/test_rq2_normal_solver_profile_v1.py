from dataclasses import replace
from types import SimpleNamespace
import json
from hashlib import sha256

import pytest

from experiments import rq2_normal_solver_profile as api
from test_rq2_continuous_grid_normal_v1 import fixture, model_for
from test_rq2_normal_execution_stream_numeric_v1 import BUDGET, SPEC


def arguments(inputs, callback):
    return dict(specification=SPEC, budget=BUDGET,
        expected_scale=api.kernel.model_scale(model_for(inputs)),
        expected_input_identity=api.kernel.normal_input_identity(inputs),
        expected_implementation_identity=api.implementation_identity(), before_solve=callback)


def test_tiny_one_call_without_loading_and_same_native_outcome(monkeypatch):
    inputs = fixture(2)
    events, retained = [], []
    original = api.kernel.native.create_solver
    def create(spec):
        events.append('create')
        solver, options = original(spec)
        solve = solver.solve
        def observed(model, **kwargs):
            events.append('solve')
            assert kwargs == dict(load_solutions=False, tee=False, options=options)
            raw = solve(model, **kwargs)
            retained.append((solver, raw))
            return raw
        monkeypatch.setattr(solver, 'solve', observed)
        return solver, options
    monkeypatch.setattr(api.kernel.native, 'create_solver', create)
    result = api.observe_once(inputs, **arguments(inputs, lambda: events.append('reserved')))
    assert events == ['create', 'reserved', 'solve']
    assert len(retained) == 1
    profile = result['profile']
    assert profile['solution_count'] == 1 and profile['legacy_termination'] == 'optimal'
    assert profile['internal_solution_status'] == 'optimal'
    assert profile['solver_calls'] == 1 and not profile['model_values_loaded']
    assert not profile['normal_accepted'] and not profile['formal_result']
    assert profile['optimality_certificate'] is profile['infeasibility_certificate'] is None
    model = model_for(inputs)
    solver, opts = original(SPEC)
    raw = solver.solve(model, load_solutions=False, tee=False, options=opts)
    assert raw.solver[0].status == retained[0][1].solver[0].status
    assert raw.solver[0].termination_condition == retained[0][1].solver[0].termination_condition
    assert len(raw.solution) == profile['solution_count']
    assert api.kernel.native._structure(model) == result['model_structure_identity']


@pytest.mark.parametrize('fault', ['implementation', 'input', 'scale', 'solver_scope', 'reservation'])
def test_rejection_cannot_start_solver(monkeypatch, fault):
    inputs = fixture(2)
    def reserve():
        if fault == 'reservation':
            raise ValueError('reservation rejected')
    kw = arguments(inputs, reserve)
    if fault == 'implementation': kw['expected_implementation_identity'] = '0'*64
    if fault == 'input': kw['expected_input_identity'] = '0'*64
    if fault == 'scale': kw['expected_scale'] = replace(kw['expected_scale'], variables=1)
    if fault == 'solver_scope': kw['specification'] = replace(SPEC, time_limit_seconds=2.)
    original = api.kernel.native.create_solver
    def create(spec):
        solver, options = original(spec)
        monkeypatch.setattr(solver, 'solve', lambda *a, **k: pytest.fail('solve reached'))
        return solver, options
    monkeypatch.setattr(api.kernel.native, 'create_solver', create)
    with pytest.raises(ValueError): api.observe_once(inputs, **kw)


@pytest.fixture
def extraction(monkeypatch):
    detail = api.results.Results()
    detail.termination_condition = api.results.TerminationCondition.maxTimeLimit
    detail.solution_status = api.results.SolutionStatus.noSolution
    detail.solver_log = 'Time limit reached\n'
    detail.incumbent_objective = None
    timer = api.timing.HierarchicalTimer()
    for name in ('set_instance', 'optimize', 'load solution'):
        timer.start(name); timer.stop(name)
    monkeypatch.setattr(timer, 'get_total_time', lambda name: 1.)
    detail.timing_info.timer = timer
    detail.timing_info.wall_time = 3.5
    detail.timing_info.highs_time = 1.
    raw = api.SolverResults()
    raw.solver.status = api.SolverStatus.aborted
    raw.solver.termination_condition = api.TerminationCondition.maxTimeLimit
    return SimpleNamespace(_last_results_object=detail), raw, 4.


def test_timeout_is_diagnostic_not_infeasibility(extraction):
    result = api.extract(*extraction)
    assert result['solution_count'] == 0 and result['legacy_termination'] == 'maxTimeLimit'
    assert result['counters'] == dict.fromkeys(api.COUNTERS)
    assert result['infeasibility_certificate'] is None and not result['normal_accepted']


def test_log_content_is_not_exported(extraction):
    log = ('BestBound 987654321.123 / BestSol 876543219.123\n'
           'Primal bound 876543219.123\nDual bound 987654321.123\n'
           'Unrecognized future format: 765432198.123 (objective)\n')
    extraction[0]._last_results_object.solver_log = log
    profile = api.extract(*extraction)
    wire = json.dumps(profile)
    assert 'solver_log' not in profile
    assert all(value not in wire for value in ('987654321.123', '876543219.123', '765432198.123'))
    assert profile['solver_log_bytes'] == len(log.encode('utf-8'))
    assert profile['solver_log_sha256'] == sha256(log.encode('utf-8')).hexdigest()


@pytest.mark.parametrize('field,value', [
    ('highs_reported_seconds', 1.1), ('solver_log_bytes', True),
    ('solver_log_bytes', 0), ('solver_log_bytes', api.LOG_LIMIT+1),
    ('solver_log_sha256', 'g'*64), ('solver_log_sha256', 'a'*63),
    ('normal_accepted', True), ('solver_calls', True), ('solution_count', 1)])
def test_persisted_profile_tampering_rejected(extraction, field, value):
    profile = api.extract(*extraction)
    profile[field] = value
    with pytest.raises(ValueError):
        api.validate_profile(profile)


def test_native_runtime_must_fit_optimize_interval(extraction):
    extraction[0]._last_results_object.timing_info.highs_time = 1.1
    with pytest.raises(ValueError, match='native runtime'):
        api.extract(*extraction)


@pytest.mark.parametrize('fault', ['missing_detail', 'raw_type', 'long_log', 'empty_log',
    'running_timer', 'many_timers', 'duplicate_timer', 'missing_timer', 'update_timer',
    'negative_time', 'nan_time', 'integer_time', 'counter', 'calls', 'wall_sum',
    'elapsed', 'outcome', 'solution_count'])
def test_incomplete_or_inconsistent_private_evidence_rejected(extraction, monkeypatch, fault):
    solver, raw, elapsed = extraction
    d = solver._last_results_object; t = d.timing_info.timer
    if fault == 'missing_detail': solver._last_results_object = None
    if fault == 'raw_type': raw = object()
    if fault == 'long_log': d.solver_log = 'x' * (api.LOG_LIMIT+1)
    if fault == 'empty_log': d.solver_log = ''
    if fault == 'running_timer': t.start('pending')
    if fault == 'many_timers': monkeypatch.setattr(t, 'get_timers', lambda: ['x']*65)
    if fault == 'duplicate_timer': monkeypatch.setattr(t, 'get_timers', lambda: ['optimize']*2)
    if fault == 'missing_timer': monkeypatch.setattr(t, 'get_timers', lambda: ['optimize'])
    if fault == 'update_timer': t.start('update'); t.stop('update')
    if fault in ('negative_time', 'nan_time', 'integer_time'):
        value = {'negative_time': -1., 'nan_time': float('nan'), 'integer_time': 1}[fault]
        monkeypatch.setattr(t, 'get_total_time', lambda name: value)
    if fault == 'counter': d.extra_info.mip_node_count = True
    if fault == 'calls': monkeypatch.setattr(t, 'get_num_calls', lambda name: 2)
    if fault == 'wall_sum': d.timing_info.wall_time = 2.
    if fault == 'elapsed': elapsed = 3.
    if fault == 'outcome': raw.solver.termination_condition = api.TerminationCondition.optimal
    if fault == 'solution_count': raw.solution.add()
    with pytest.raises(ValueError): api.extract(solver, raw, elapsed)
