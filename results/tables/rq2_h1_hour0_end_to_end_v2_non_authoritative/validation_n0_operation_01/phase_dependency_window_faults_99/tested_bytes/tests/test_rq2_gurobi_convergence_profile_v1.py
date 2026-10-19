from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from types import SimpleNamespace

import pytest

from experiments import rq2_gurobi_convergence_profile as api
from test_rq2_continuous_grid_normal_v1 import fixture, model_for
from test_rq2_normal_execution_gurobi_ordered_v1 import SPEC, BUDGET


def arguments(inputs, callback):
    return dict(specification=SPEC, budget=BUDGET,
        expected_scale=api.kernel.model_scale(model_for(inputs)),
        expected_input_identity=api.kernel.normal_input_identity(inputs),
        expected_implementation_identity=api.implementation_identity(), before_solve=callback)


def test_tiny_same_outcome_single_reserved_call_and_no_loading(monkeypatch):
    inputs = fixture(2)
    events, retained = [], []
    factory = api.kernel.native.create_solver
    text = api.MessageCapture.text
    private = 'LICENSEID fake-secret; path C:/private/fake.lic; credential=fake-token\n'
    monkeypatch.setattr(api.MessageCapture, 'text', lambda self: private + text(self))
    def create(spec):
        events.append('create')
        solver, options = factory(spec)
        solve = solver.solve
        def invoke(model, **kw):
            events.append('solve')
            assert kw == dict(load_solutions=False, tee=False, options=options)
            before = api.kernel.native._snapshot(model)
            result = solve(model, **kw)
            assert api.kernel.native._snapshot(model) == before
            retained.append(result)
            return result
        monkeypatch.setattr(solver, 'solve', invoke)
        return solver, options
    monkeypatch.setattr(api.kernel.native, 'create_solver', create)
    result = api.observe_once(inputs, **arguments(inputs, lambda: events.append('reserved')))
    assert events == ['create', 'reserved', 'solve'] and len(retained) == 1
    p = result['profile']
    assert 'solver_log' not in p
    assert all(token not in json.dumps(result) for token in ('fake-secret', 'fake.lic', 'fake-token'))
    assert p['native_status'] == api.gp.GRB.OPTIMAL and p['legacy_termination'] == 'optimal'
    assert p['counters']['SolCount'] > 0 and p['solver_log_bytes'] > 0
    assert not any(p[k] for k in ('model_values_loaded', 'normal_accepted', 'formal_result'))
    solver, options = factory(SPEC)
    raw = solver.solve(model_for(inputs), load_solutions=False, tee=False, options=options)
    assert raw.solver[0].status == retained[0].solver[0].status
    assert raw.problem[0].lower_bound == retained[0].problem[0].lower_bound
    assert raw.problem[0].upper_bound == retained[0].problem[0].upper_bound


@pytest.mark.parametrize('fault', ['implementation', 'input', 'scale', 'scope', 'reservation'])
def test_rejected_before_solve(monkeypatch, fault):
    inputs = fixture(2)
    def reserve():
        if fault == 'reservation': raise ValueError('reservation rejected')
    kw = arguments(inputs, reserve)
    if fault == 'implementation': kw['expected_implementation_identity'] = '0'*64
    if fault == 'input': kw['expected_input_identity'] = '0'*64
    if fault == 'scale': kw['expected_scale'] = replace(kw['expected_scale'], variables=1)
    if fault == 'scope': kw['specification'] = replace(SPEC, time_limit_seconds=30.)
    factory = api.kernel.native.create_solver
    def create(spec):
        solver, options = factory(spec)
        monkeypatch.setattr(solver, 'solve', lambda *a, **k: pytest.fail('solve reached'))
        return solver, options
    monkeypatch.setattr(api.kernel.native, 'create_solver', create)
    with pytest.raises(ValueError): api.observe_once(inputs, **kw)


def test_callback_only_reads_messages_and_is_bounded():
    calls = []
    model = SimpleNamespace(cbGet=lambda key: calls.append(key) or 'test\n')
    capture = api.MessageCapture()
    capture(model, api.gp.GRB.Callback.MIP)
    assert not calls
    capture(model, api.gp.GRB.Callback.MESSAGE)
    assert calls == [api.gp.GRB.Callback.MSG_STRING] and capture.text() == 'test\n'
    capture(SimpleNamespace(cbGet=lambda key: 'x'*api.LOG_LIMIT), api.gp.GRB.Callback.MESSAGE)
    assert capture.overflow and capture.size == 5
    with pytest.raises(ValueError): capture.text()


def test_callback_failure_is_recorded_without_solver_mutation():
    capture = api.MessageCapture()
    capture(SimpleNamespace(cbGet=lambda key: None), api.gp.GRB.Callback.MESSAGE)
    assert capture.error == 'TypeError'
    with pytest.raises(ValueError): capture.text()


def valid_profile():
    log = 'Time limit reached\n'
    return dict(schema=api.SCHEMA, native_status=api.gp.GRB.TIME_LIMIT,
        legacy_status='aborted', legacy_termination='maxTimeLimit',
        native_runtime_seconds=15., solve_interface_seconds=16.,
        counters=dict(NodeCount=1., IterCount=10., BarIterCount=0, Work=.5, SolCount=1),
        convergence=api.convergence_rows(log), solver_log_bytes=len(log.encode()), solver_log_sha256=sha256(log.encode()).hexdigest(),
        solver_calls=1, model_values_loaded=False, normal_accepted=False,
        formal_result=False, security_certified=False)


def test_timeout_remains_nonaccepted():
    body = valid_profile()
    api.validate_profile(body)
    assert body['normal_accepted'] is False and body['legacy_termination'] == 'maxTimeLimit'


@pytest.mark.parametrize('field,value', [
    ('native_status', True), ('legacy_status', 'ok'), ('legacy_termination', 'optimal'),
    ('native_runtime_seconds', 17.), ('solve_interface_seconds', float('nan')),
    ('solver_log_bytes', 0), ('solver_log_sha256', 'bad'), ('convergence', {}),
    ('solver_calls', True), ('formal_result', True), ('normal_accepted', True),
    ('model_values_loaded', True), ('counters', {})])
def test_forged_profile_rejected(field, value):
    body = valid_profile(); body[field] = value
    with pytest.raises(ValueError): api.validate_profile(body)


@pytest.mark.parametrize('name,value', [('NodeCount', .5), ('IterCount', -1.),
    ('Work', float('inf')), ('SolCount', True)])
def test_bad_counter(name, value):
    body = deepcopy(valid_profile()); body['counters'][name] = value
    with pytest.raises(ValueError): api.validate_profile(body)


def test_numeric_log_rows_and_unknown_text_excluded():
    log = ('LICENSEID=private-token C:/private/license.lic\n'
        'Root relaxation: objective 1.20e+06, 123 iterations, 0.50 seconds (0.20 work units)\n'
        '     0     0 1.20e+06 0 10 1.30e+06 1.21e+06 6.92% - 1s\n'
        'H    3     2              1.25e+06 1.22e+06 2.40% 5.0 5s\n'
        'Best objective 1.250000e+06, best bound 1.220000e+06, gap 2.4000%\n')
    rows = api.convergence_rows(log)
    assert rows == dict(root_relaxations=[[1200000., 123, .5]],
        progress=[[0, 0, 1300000., 1210000., 6.92, None, 1.],
                  [3, 2, 1250000., 1220000., 2.4, 5., 5.]],
        final_bounds=[[1250000., 1220000., 2.4]])
    assert 'private' not in json.dumps(rows)


@pytest.mark.parametrize('rows', [
    {'root_relaxations': [[1., 2, float('nan')]], 'progress': [], 'final_bounds': []},
    {'root_relaxations': [], 'progress': [[0, 0, 'secret', 1., 1., None, 1.]], 'final_bounds': []},
    {'root_relaxations': [], 'progress': [], 'final_bounds': [[1., 2., -1.]]}])
def test_forged_numeric_rows(rows):
    body = valid_profile(); body['convergence'] = rows
    with pytest.raises(ValueError): api.validate_profile(body)
