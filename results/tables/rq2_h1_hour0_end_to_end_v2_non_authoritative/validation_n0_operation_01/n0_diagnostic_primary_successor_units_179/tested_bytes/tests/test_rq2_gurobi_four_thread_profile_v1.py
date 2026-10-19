from copy import deepcopy

from dataclasses import replace

from hashlib import sha256

import json

from types import SimpleNamespace

import pytest

from experiments import rq2_gurobi_four_thread_profile as api

from test_rq2_continuous_grid_normal_v1 import fixture, model_for

from test_rq2_normal_execution_gurobi_ordered_v1 import SPEC as OLD_SPEC, BUDGET as OLD_BUDGET
SPEC = replace(OLD_SPEC, threads=4)
BUDGET = replace(OLD_BUDGET, max_threads=4)

def arguments(inputs, callback):
    return dict(specification=SPEC, budget=BUDGET,
        expected_scale=api.kernel.model_scale(model_for(inputs)),
        expected_input_identity=api.kernel.normal_input_identity(inputs),
        expected_implementation_identity=api.implementation_identity(), before_solve=callback)

def test_tiny_same_outcome_single_reserved_call_and_no_loading(monkeypatch):
    inputs = fixture(2)
    events, retained = [], []
    factory = api.create_solver
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
    monkeypatch.setattr(api, 'create_solver', create)
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
    factory = api.create_solver
    def create(spec):
        solver, options = factory(spec)
        monkeypatch.setattr(solver, 'solve', lambda *a, **k: pytest.fail('solve reached'))
        return solver, options
    monkeypatch.setattr(api, 'create_solver', create)
    with pytest.raises(ValueError): api.observe_once(inputs, **kw)

@pytest.mark.parametrize('threads', [1, 2, 3, 5, True])
def test_only_four_threads_allowed(threads):
    with pytest.raises(ValueError): api.validate_spec(replace(SPEC, threads=threads))


def test_native_thread_parameter_drift_rejected(monkeypatch):
    factory = api.create_solver
    def create(spec):
        solver, options = factory(spec)
        solve = solver.solve
        def invoke(model, **kw):
            raw = solve(model, **kw)
            solver._solver_model.Params.Threads = 1
            return raw
        monkeypatch.setattr(solver, 'solve', invoke)
        return solver, options
    monkeypatch.setattr(api, 'create_solver', create)
    inputs = fixture(2)
    with pytest.raises(ValueError, match='native thread parameter'):
        api.observe_once(inputs, **arguments(inputs, lambda: None))
