from dataclasses import replace
import json

import pytest

from tests.test_rq2_continuous_grid_normal_v1 import fixture
from tests.test_rq2_objective_provenance_run_v1 import spec
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_short_solve as api


def budget():
    return api.GridDevelopmentBudget(api.PURPOSE, 1., 1, 1, 100, 500, 3, 3.)


def run(inputs=None, bound=None):
    x = fixture(1) if inputs is None else inputs
    b = budget() if bound is None else bound
    return api.run_h1_chain(x, spec(), b, expected_identity=api.chain_identity(x, spec(), b))


@pytest.fixture(scope='module')
def native_chain():
    return run()


def test_real_three_stage_chain_preserves_native_values_and_canonical_locks(native_chain):
    result = native_chain
    assert result.numerical_chain_accepted, result.errors
    assert result.collector_attempts == result.solver_calls == 3
    assert [s.prior_locks for s in result.stages] == [(), (20.,), (20., 1.)]
    assert [s.lock_value for s in result.stages] == [20., 1., 20.]
    for stage in result.stages:
        raw = json.loads(stage.native_payload)
        assert raw['provenance']['native']['ObjBound']['available']
        assert raw['provenance']['native']['ObjVal']['available']
        assert json.loads(stage.numeric_predicate_payload)['candidate_numeric_predicate_passed']
        assert not stage.assignment_audit.errors
    assert not result.exact_mathematical_certificate
    assert not result.formal_result and not result.hard_process_resources_verified


@pytest.mark.parametrize('updates', [dict(max_solver_calls=2), dict(max_total_solver_seconds=2.),
                                    dict(max_variables=1), dict(max_constraints=1), dict(max_horizon=2)])
def test_all_stages_prebudgeted_without_native(monkeypatch, updates):
    def forbidden(*args, **kwargs):
        pytest.fail('inadmissible chain called native')
    monkeypatch.setattr(api.capture, 'solve_once', forbidden)
    with pytest.raises(ValueError):
        run(bound=replace(budget(), **updates))


def test_identity_and_public_construction_rejected(monkeypatch):
    monkeypatch.setattr(api.capture, 'solve_once', lambda *a, **k: pytest.fail('unexpected native'))
    with pytest.raises(ValueError, match='declaration mismatch'):
        api.run_h1_chain(fixture(1), spec(), budget(), expected_identity='0'*64)
    for cls in (api.H1StageEvidence, api.H1ChainEvidence):
        with pytest.raises(TypeError, match='owned execution'):
            cls()


def test_failure_stops_chain_and_does_not_use_unaccepted_lock(monkeypatch, native_chain):
    reports = [s.native_payload for s in native_chain.stages]
    seen = []
    def corrupted(*args, **kwargs):
        index = len(seen)
        seen.append(index)
        if index == 1:
            report = json.loads(reports[index])
            report['provenance'] = None
            return api.capture.encode(report)
        return reports[index]
    monkeypatch.setattr(api.capture, 'solve_once', corrupted)
    result = run()
    assert seen == [0, 1]
    assert not result.numerical_chain_accepted
    assert result.solver_calls == 2
    assert result.stages[-1].prior_locks == (20.,)
    assert result.stages[-1].lock_value is None


def test_collector_exception_unknown_calls_no_retry(monkeypatch):
    attempts = []
    def broken(*args, **kwargs):
        attempts.append(1)
        raise RuntimeError('failure after possible native call')
    monkeypatch.setattr(api.capture, 'solve_once', broken)
    result = run()
    assert len(attempts) == result.collector_attempts == 1
    assert result.solver_calls is None
    assert not result.numerical_chain_accepted


def test_native_bound_tamper_is_not_repaired(monkeypatch, native_chain):
    original = native_chain.stages[0].native_payload
    report = json.loads(original)
    report['provenance']['native']['ObjBound']['hex'] = 21.0.hex()
    altered = api.capture.encode(report)
    monkeypatch.setattr(api.capture, 'solve_once', lambda *args, **kw: altered)
    result = run()
    assert not result.numerical_chain_accepted and len(result.stages) == 1
    assert result.stages[0].native_payload == altered
    assert native_chain.stages[0].native_payload == original


def test_repeat_native_chain_same_projection(native_chain):
    again = run()
    assert again.numerical_chain_accepted, again.errors
    assert [s.lock_value for s in again.stages] == [s.lock_value for s in native_chain.stages]
    assert dict(json.loads(again.stages[-1].native_payload)['assignment']) == dict(
        json.loads(native_chain.stages[-1].native_payload)['assignment'])


def test_real_double_zero_chain():
    result = run(fixture(1, committed=False, age=3, demand=0.))
    assert result.numerical_chain_accepted, result.errors
    assert [s.lock_value for s in result.stages] == [0., 0., 0.]
    for stage in result.stages:
        assert json.loads(stage.numeric_predicate_payload)['raw_relative_gap_exact'] == '0'


@pytest.mark.parametrize('mutation', ['bad_bytes', 'wrong_scale', 'wrong_status'])
def test_report_binding_failures_stop_without_publishing_locks(monkeypatch, native_chain, mutation):
    record = json.loads(native_chain.stages[0].native_payload)
    if mutation == 'wrong_scale':
        record['constraints'] += 1
    if mutation == 'wrong_status':
        record['native_status'] = 3
    payload = b'not json' if mutation == 'bad_bytes' else api.capture.encode(record)
    monkeypatch.setattr(api.capture, 'solve_once', lambda *args, **kw: payload)
    result = run()
    assert not result.numerical_chain_accepted and len(result.stages) == 1
    assert result.stages[0].lock_value is None
    assert result.solver_calls == (1 if mutation == 'wrong_status' else None)


def test_equal_cost_units_follow_uid_lex_chain():
    x = fixture(1, committed=False, age=3)
    g = x.data.generators[0]
    units = (replace(g, uid='Z'), replace(g, uid='A'))
    point = replace(x.data.hourly_points[0], generator_min_mw={'A': 10., 'Z': 10.},
                    generator_max_mw={'A': 100., 'Z': 100.})
    initial = api.model_api.declared_normal_initial(units, point)
    request = replace(x.request, initial_commitment=initial.commitment,
        initial_generation_mw=initial.generation_mw, initial_time_in_state_hours=initial.time_in_state_hours,
        generator_availability=({'A': True, 'Z': True},))
    carry = replace(x.carry,
        limits=tuple(replace(x.carry.limits[0], uid=uid) for uid in ('A','Z')),
        points=tuple(replace(x.carry.points[0], uid=uid) for uid in ('A','Z')),
        elapsed_state_hours=(3,3))
    inputs = replace(x, data=replace(x.data, generators=units, hourly_points=(point,)),
                     initial=initial, request=request, carry=carry)
    result = run(inputs, replace(budget(), max_solver_calls=5, max_total_solver_seconds=5.))
    assert result.numerical_chain_accepted, result.errors
    # Both generators have identical costs. UID minimization selects A off,
    # then Z on, rather than whichever stage-zero incumbent happened to win.
    assert [s.lock_value for s in result.stages] == [20., 0., 1., 0., 20.]
    assert [s.objective for s in result.stages][1:] == [
        ('commitment','A'), ('commitment','Z'), ('generation','A'), ('generation','Z')]


@pytest.mark.parametrize('bad', ['native json string', bytearray(b'wrong container')])
def test_nonbytes_collector_result_does_not_corrupt_evidence(monkeypatch, bad):
    monkeypatch.setattr(api.capture, 'solve_once', lambda *a, **kw: bad)
    result = run()
    assert not result.numerical_chain_accepted
    assert result.solver_calls is None and result.collector_attempts == 1
    assert result.stages[0].native_payload is None
    assert type(bad).__name__ in result.stages[0].errors[0]


def test_budget_implementation_file_is_identity_dependency(monkeypatch, tmp_path):
    changed = tmp_path/'budget.py'
    changed.write_text('changed budget semantics', encoding='utf-8')
    old = api.chain_identity(fixture(1), spec(), budget())
    monkeypatch.setattr(api.budget_api, '__file__', str(changed))
    assert api.chain_identity(fixture(1), spec(), budget()) != old
