from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys

import pytest

from test_rq2_continuous_grid_normal_v1 import fixture, model_for
from test_rq2_continuous_grid_candidate_v1 import SPEC as OLD_SPEC, install as old_install
from test_rq2_continuous_grid_candidate_v1 import runner as old_native
from src.solvers.rq2_solver_adapter import model_scale, Rq2ModelScale
from src.rq2_joint_deliverability_boundary_v1 import normal_execution_gurobi_ordered as api


SPEC = replace(OLD_SPEC, name='gurobi', expected_package_version='13.0.2', time_limit_seconds=15.)


def install(monkeypatch, inputs, **kwargs):
    calls = old_install(monkeypatch, inputs, **kwargs)
    monkeypatch.setattr(api.native, 'create_solver', old_native.create_solver)
    return calls


BUDGET = api.NormalExecutionBudget(15., 1, 25, 30000, 100000, 60., 8*1024**3, 16*1024**2)


def arguments(inputs, *, budget=BUDGET, spec=SPEC, scale=None):
    scale = model_scale(model_for(inputs)) if scale is None else scale
    pin = api.normal_input_identity(inputs)
    return dict(expected_input_identity=pin, expected_execution_identity=api.normal_execution_identity(
        pin, scale, spec, budget), expected_scale=scale, specification=spec, budget=budget)


def test_native_single_call_complete_normal():
    inputs = fixture(2)
    result = api.run_normal_only(inputs, **arguments(inputs))
    assert result.normal_accepted, result.errors
    assert result.solver_calls == 1 and result.call_count_complete
    assert result.normal.optimal and result.normal.assignment_valid
    assert result.witness.terminal_carry.source_hour == 2
    assert result.witness.errors == ()
    assert result.normal.lower == result.normal.upper == pytest.approx(40.)
    assert result.public_source_binding_verified is result.formal_result is result.security_certified is False
    assert result.hard_resource_limits_enforced is result.durable_invocation_tracking is False
    assert result.causal_certificate is result.infeasibility_certificate is None
    assert 0 < result.process_peak_working_set_bytes[0] <= result.process_peak_working_set_bytes[1]
    assert result.core_evidence_payload_bytes > 0
    assert all(x >= 0 for k, x in result.timings if k != 'builder_seconds_nested')
    assert len(dict(result.timings)['builder_seconds_nested']) == 3
    with pytest.raises(TypeError):
        api.GurobiOrderedNormalExecutionResult()
    with pytest.raises(TypeError):
        replace(result, normal_accepted=False)


@pytest.mark.parametrize('fault', ['exception', 'timeout', 'missing', 'unknown', 'nan', 'objective',
    'inverted_bounds', 'solution_status', 'multi_solution', 'multi_solver', 'multi_problem', 'options',
    'structure', 'root_deactivation', 'preload', 'load', 'none', 'nonfinite_bound', 'native_infeasible'])
def test_native_faults_preserve_evidence_without_acceptance(monkeypatch, fault):
    inputs = fixture(2)
    calls = install(monkeypatch, inputs, fault=fault)
    result = api.run_normal_only(inputs, **arguments(inputs))
    assert not result.normal_accepted
    assert result.status == 'unresolved_normal'
    assert result.solver_calls == calls['solve'] == 1
    assert result.call_count_complete
    if fault == 'timeout':
        assert result.normal.assignment_valid and result.witness is not None
        assert not result.normal.optimal


@pytest.mark.parametrize('field', ['expected_input_identity', 'expected_execution_identity'])
def test_external_identity_mismatch_before_native(monkeypatch, field):
    inputs = fixture(2)
    calls = install(monkeypatch, inputs)
    kw = arguments(inputs)
    kw[field] = '0'*64
    with pytest.raises(ValueError, match='identity drift'):
        api.run_normal_only(inputs, **kw)
    assert calls == {'create': 0, 'solve': 0}


def test_actual_scale_checked_not_just_budget(monkeypatch):
    inputs = fixture(2)
    calls = install(monkeypatch, inputs)
    with pytest.raises(ValueError, match='external scale'):
        api.run_normal_only(inputs, **arguments(inputs, scale=Rq2ModelScale(999, 1999)))
    assert calls['create'] == 0


@pytest.mark.parametrize('field,value', [('max_seconds_per_solve', float('nan')),
    ('max_seconds_per_solve', 31), ('max_observed_wall_seconds', 61), ('max_observed_wall_seconds', 0),
    ('max_threads', 5), ('max_horizon', 169), ('max_variables', True), ('max_constraints', -1),
    ('max_process_peak_working_set_bytes', 0), ('max_core_evidence_payload_bytes', 1.5)])
def test_invalid_budget(field, value):
    with pytest.raises(ValueError):
        replace(BUDGET, **{field: value})


def test_short_budgets_remain_distinct():
    assert BUDGET.max_variables == 30000
    with pytest.raises(ValueError):
        api.native.GridDevelopmentBudget('unchanged', 1, 1, 25, 30000, 100000, 1, 1)


@pytest.mark.parametrize('spec', [replace(SPEC, time_limit_seconds=None), replace(SPEC, time_limit_seconds=2.),
    replace(SPEC, threads=2), replace(SPEC, feasibility_tolerance=1e-5)])
def test_solver_applicability(spec):
    with pytest.raises(ValueError):
        arguments(fixture(2), spec=spec)


def test_memory_precheck_before_native(monkeypatch):
    inputs = fixture(2)
    calls = install(monkeypatch, inputs)
    monkeypatch.setattr(api, '_peak_working_set_bytes', lambda: BUDGET.max_process_peak_working_set_bytes+1)
    with pytest.raises(ValueError, match='peak working set'):
        api.run_normal_only(inputs, **arguments(inputs))
    assert calls['create'] == 0


def test_post_return_memory_limit_keeps_raw(monkeypatch):
    inputs = fixture(2)
    calls = install(monkeypatch, inputs)
    original = api.streaming.audit_normal_assignment
    peak = [1000]
    monkeypatch.setattr(api, '_peak_working_set_bytes', lambda: peak[0])
    def audit(*args, **kwargs):
        witness = original(*args, **kwargs)
        peak[0] = BUDGET.max_process_peak_working_set_bytes+1
        return witness
    monkeypatch.setattr(api.streaming, 'audit_normal_assignment', audit)
    result = api.run_normal_only(inputs, **arguments(inputs))
    assert result.normal.optimal and result.witness is not None
    assert not result.normal_accepted
    assert 'process_lifetime_peak_exceeds_budget' in result.errors
    assert calls['solve'] == 1


def test_wall_time_post_return_is_not_hard_kill(monkeypatch):
    inputs = fixture(2)
    install(monkeypatch, inputs)
    clock = [0.]
    monkeypatch.setattr(api, 'perf_counter', lambda: clock[0])
    original = api.streaming.audit_normal_assignment
    def audit(*args, **kwargs):
        witness = original(*args, **kwargs)
        clock[0] = 61.
        return witness
    monkeypatch.setattr(api.streaming, 'audit_normal_assignment', audit)
    result = api.run_normal_only(inputs, **arguments(inputs))
    assert result.normal.optimal and not result.normal_accepted
    assert 'observed_wall_time_exceeds_budget' in result.errors
    assert result.hard_resource_limits_enforced is False


def test_payload_limit_keeps_full_raw(monkeypatch):
    inputs = fixture(2)
    install(monkeypatch, inputs)
    result = api.run_normal_only(inputs, **arguments(inputs, budget=replace(BUDGET, max_core_evidence_payload_bytes=1)))
    assert not result.normal_accepted and result.normal.optimal
    assert result.core_evidence_payload_bytes > 1
    assert 'core_evidence_payload_exceeds_budget' in result.errors


def test_create_exception_has_zero_known_calls(monkeypatch):
    inputs = fixture(2)
    def fail(*args):
        raise RuntimeError('create failure')
    monkeypatch.setattr(api.native, 'create_solver', fail)
    result = api.run_normal_only(inputs, **arguments(inputs))
    assert result.solver_calls == 0 and result.call_count_complete
    assert not result.normal_accepted
    assert any('create:RuntimeError' in x for x in result.errors)


def test_interrupt_missing_raw_keeps_call_count_unknown(monkeypatch):
    inputs = fixture(2)
    def fail(*args):
        raise KeyboardInterrupt('interrupted before complete return')
    monkeypatch.setattr(api.native, '_solve', fail)
    result = api.run_normal_only(inputs, **arguments(inputs))
    assert result.solver_calls is None and not result.call_count_complete
    assert result.status == 'interrupted_normal' and not result.normal_accepted
    assert result.normal is result.witness is None


def test_post_solve_execution_drift_keeps_evidence(monkeypatch):
    inputs = fixture(2)
    install(monkeypatch, inputs)
    original = api.streaming.audit_normal_assignment
    def audit(*args, **kwargs):
        witness = original(*args, **kwargs)
        monkeypatch.setattr(api, 'normal_execution_identity', lambda *a: '0'*64)
        return witness
    monkeypatch.setattr(api.streaming, 'audit_normal_assignment', audit)
    result = api.run_normal_only(inputs, **arguments(inputs))
    assert result.normal.optimal and not result.normal_accepted
    assert any(x.startswith('post_identity:') for x in result.errors)


def test_caller_mutation_does_not_change_private_normal(monkeypatch):
    inputs = fixture(2)
    install(monkeypatch, inputs)
    original = api.native._solve
    def mutate(*args):
        inputs.request.system_demand_by_bus_mw[0][1] = 999.
        return original(*args)
    monkeypatch.setattr(api.native, '_solve', mutate)
    result = api.run_normal_only(inputs, **arguments(inputs))
    assert result.normal_accepted, result.errors
    assert result.normal.objective == pytest.approx(40.)


def test_fresh_import_source_closure_bound():
    script = '''
import json, sys
from pathlib import Path
import src.rq2_joint_deliverability_boundary_v1.normal_execution_gurobi_ordered
root=Path.cwd()
print(json.dumps(sorted(Path(m.__file__).resolve().relative_to(root).as_posix()
 for n,m in sys.modules.items() if n == 'src' or n.startswith('src.'))))
'''
    result = subprocess.run([sys.executable, '-B', '-c', script], check=True, capture_output=True,
        text=True, cwd=Path(__file__).resolve().parents[1], timeout=30)
    dependencies = {n for n, _ in api.native._dependencies()[0]} | set(api.native.EXTRA_DEPENDENCIES)
    dependencies.update('src/rq2_joint_deliverability_boundary_v1/'+name+'.py' for name in
        ('normal_execution','normal_execution_gurobi_ordered','continuous_grid_normal_stream_ordered',
         'identity_stream_ordered','identity_stream_fast'))
    assert set(json.loads(result.stdout)) == dependencies


@pytest.mark.parametrize('fault', ['gap', 'bad_assignment', 'missing_bound'])
def test_numeric_gate_failures(monkeypatch, fault):
    inputs = fixture(2)
    calls = install(monkeypatch, inputs)
    create = api.native.create_solver
    def altered(spec):
        engine, options = create(spec)
        solve = engine.solve
        def changed(*args, **kwargs):
            result = solve(*args, **kwargs)
            if fault == 'gap':
                result.problem.lower_bound = 0.
            elif fault == 'missing_bound':
                result.problem.lower_bound = None
            else:
                result.solution[0].variable['generation[normal,0,G1]']['Value'] += 5.
            return result
        engine.solve = changed
        return engine, options
    monkeypatch.setattr(api.native, 'create_solver', altered)
    result = api.run_normal_only(inputs, **arguments(inputs))
    assert not result.normal_accepted and not result.normal.optimal
    assert calls['solve'] == 1
    if fault == 'gap':
        assert result.witness is not None and result.witness.errors == ()


def test_audit_exception_preserves_returned_call_evidence(monkeypatch):
    inputs = fixture(2)
    install(monkeypatch, inputs)
    def fail(*args, **kwargs):
        raise RuntimeError('witness unavailable')
    monkeypatch.setattr(api.streaming, 'audit_normal_assignment', fail)
    result = api.run_normal_only(inputs, **arguments(inputs))
    assert result.normal.optimal and result.witness is None
    assert result.solver_calls == 1 and result.call_count_complete
    assert not result.normal_accepted


def test_normal_evidence_matches_unchanged_legacy_core(monkeypatch):
    inputs = fixture(2)
    install(monkeypatch, inputs)
    from src.rq2_joint_deliverability_boundary_v1 import normal_execution_stream_numeric as prior
    options = arguments(inputs)
    options['expected_execution_identity'] = prior.normal_execution_identity(
        options['expected_input_identity'], options['expected_scale'], SPEC, BUDGET)
    old = prior.run_normal_only(inputs, **options)
    new = api.run_normal_only(inputs, **arguments(inputs))
    assert new.normal == old.normal
    assert new.witness == old.witness
    assert new.normal_accepted == old.normal_accepted


def test_exact_result_identity_and_explicit_core_size(monkeypatch):
    inputs = fixture(2)
    install(monkeypatch, inputs)
    result = api.run_normal_only(inputs, **arguments(inputs))
    payload = (api.CONTRACT, result.input_identity, result.execution_identity, result.specification,
        result.budget, result.scale, result.normal, result.witness)
    core_size = len(json.dumps(api._encode(payload), ensure_ascii=True, allow_nan=False).encode('utf-8'))
    full_size = len(json.dumps(api._encode(result), ensure_ascii=True, allow_nan=False).encode('utf-8'))
    assert core_size == result.core_evidence_payload_bytes < full_size
    # Internal construction solely tests digest coverage, not a public restore API.
    from dataclasses import fields
    values = {f.name: getattr(result, f.name) for f in fields(result)}
    assert len(result.identity) == 64
    for field, changed in [('errors', ('diagnostic_changed',)), ('normal', None), ('witness', None),
                           ('solver_calls', None), ('process_peak_working_set_bytes', (1, 2)),
                           ('timings', (('changed', 0.),))]:
        modified = api.native._make(api.GurobiOrderedNormalExecutionResult, **{**values, field: changed})
        assert modified.identity != result.identity


def test_horizon_and_declared_model_budget_before_native(monkeypatch):
    inputs = fixture(2)
    calls = install(monkeypatch, inputs)
    with pytest.raises(ValueError, match='horizon exceeds'):
        api.run_normal_only(inputs, **arguments(inputs, budget=replace(BUDGET, max_horizon=1)))
    with pytest.raises(ValueError, match='declared scale exceeds'):
        arguments(inputs, budget=replace(BUDGET, max_variables=1))
    assert calls['create'] == calls['solve'] == 0


def test_legacy_execution_pin_cannot_authorize_successor(monkeypatch):
    inputs = fixture(2)
    calls = install(monkeypatch, inputs)
    kw = arguments(inputs)
    kw['expected_execution_identity'] = api.legacy.normal_execution_identity(
        kw['expected_input_identity'], kw['expected_scale'], SPEC, BUDGET)
    with pytest.raises(ValueError, match='execution identity drift'):
        api.run_normal_only(inputs, **kw)
    assert calls == {'create': 0, 'solve': 0}


def test_streaming_kernel_does_not_use_legacy_annual_encoding(monkeypatch):
    inputs = fixture(2)
    install(monkeypatch, inputs)
    kw = arguments(inputs)
    def forbidden(*args, **kwargs):
        raise AssertionError('legacy annual input path entered')
    for module in (api.legacy, api.streaming.legacy):
        for name in ('normal_input_identity', 'build_continuous_normal_model', 'audit_normal_assignment'):
            monkeypatch.setattr(module, name, forbidden)
    result = api.run_normal_only(inputs, **kw)
    assert result.normal_accepted, result.errors
    assert type(result) is api.GurobiOrderedNormalExecutionResult
    assert not isinstance(result, api.legacy.NormalExecutionResult)


def test_model_implementation_drift_rejected_before_native(monkeypatch):
    inputs = fixture(2)
    calls = install(monkeypatch, inputs)
    kw = arguments(inputs)
    monkeypatch.setattr(api.streaming, 'implementation_identity', lambda: '0'*64)
    with pytest.raises(ValueError, match='execution identity drift'):
        api.run_normal_only(inputs, **kw)
    assert calls == {'create': 0, 'solve': 0}


def test_prior_stream_execution_pin_cannot_authorize_fast_kernel(monkeypatch):
    from src.rq2_joint_deliverability_boundary_v1 import normal_execution_stream as prior
    inputs = fixture(2)
    calls = install(monkeypatch, inputs)
    kw = arguments(inputs)
    kw['expected_execution_identity'] = prior.normal_execution_identity(
        kw['expected_input_identity'], kw['expected_scale'], SPEC, BUDGET)
    with pytest.raises(ValueError, match='execution identity drift'):
        api.run_normal_only(inputs, **kw)
    assert calls == {'create': 0, 'solve': 0}


def test_fast_kernel_does_not_call_prior_stream_input_paths(monkeypatch):
    from src.rq2_joint_deliverability_boundary_v1 import identity_stream, normal_execution_stream
    from src.rq2_joint_deliverability_boundary_v1 import continuous_grid_normal_stream
    inputs = fixture(2)
    install(monkeypatch, inputs)
    kw = arguments(inputs)
    def forbidden(*args, **kwargs):
        raise AssertionError('prior streaming encoding path entered')
    for module in (identity_stream, normal_execution_stream, continuous_grid_normal_stream):
        monkeypatch.setattr(module, 'normal_input_identity', forbidden)
    result = api.run_normal_only(inputs, **kw)
    assert result.normal_accepted, result.errors
    assert type(result) is api.GurobiOrderedNormalExecutionResult
    assert not isinstance(result, normal_execution_stream.StreamingNormalExecutionResult)


def test_fast_execution_pin_cannot_authorize_numeric_kernel(monkeypatch):
    from src.rq2_joint_deliverability_boundary_v1 import normal_execution_stream_fast as prior
    inputs = fixture(2)
    calls = install(monkeypatch, inputs)
    kw = arguments(inputs)
    kw['expected_execution_identity'] = prior.normal_execution_identity(
        kw['expected_input_identity'], kw['expected_scale'], SPEC, BUDGET)
    with pytest.raises(ValueError, match='execution identity drift'):
        api.run_normal_only(inputs, **kw)
    assert calls == {'create': 0, 'solve': 0}


def test_numeric_kernel_does_not_use_fast_full_identity(monkeypatch):
    from src.rq2_joint_deliverability_boundary_v1 import identity_stream_fast, normal_execution_stream_fast
    from src.rq2_joint_deliverability_boundary_v1 import continuous_grid_normal_stream_fast
    inputs = fixture(2)
    install(monkeypatch, inputs)
    kw = arguments(inputs)
    def forbidden(*args, **kwargs):
        raise AssertionError('fast full identity path entered')
    for module in (identity_stream_fast, normal_execution_stream_fast, continuous_grid_normal_stream_fast):
        monkeypatch.setattr(module, 'normal_input_identity', forbidden)
    result = api.run_normal_only(inputs, **kw)
    assert result.normal_accepted, result.errors
    assert type(result) is api.GurobiOrderedNormalExecutionResult
    assert not isinstance(result, normal_execution_stream_fast.FastStreamingNormalExecutionResult)


def test_native_audit_algorithm_matches_unchanged_core():
    import ast
    import inspect
    assert ast.dump(ast.parse(inspect.getsource(api.native._solve))) == ast.dump(
        ast.parse(inspect.getsource(old_native._solve)))
    names = {node.id for node in ast.walk(ast.parse(inspect.getsource(old_native._solve)))
        if isinstance(node, ast.Name)} & set(vars(old_native))
    for name in names - {'create_solver', '_structure'}:
        assert vars(api.native)[name] is vars(old_native)[name], name


def test_fresh_direct_module_and_function_provenance():
    script = '''
from src.rq2_joint_deliverability_boundary_v1 import continuous_grid_native_gurobi_ordered as n
assert n.__name__ == n.__spec__.name == 'src.rq2_joint_deliverability_boundary_v1.continuous_grid_native_gurobi_ordered'
assert n._solve.__module__ == n.__name__
assert n._execution_identity.__module__ == n.__name__
'''
    subprocess.run([sys.executable, '-B', '-c', script], check=True,
        cwd=Path(__file__).resolve().parents[1], timeout=30)


def test_direct_adapter_identity_drift_rejected_before_solver(monkeypatch):
    inputs = fixture(2)
    calls = install(monkeypatch, inputs)
    kw = arguments(inputs)
    monkeypatch.setattr(api.native.adapter, 'implementation_identity', lambda: '0'*64)
    with pytest.raises(ValueError, match='execution identity drift'):
        api.run_normal_only(inputs, **kw)
    assert calls == {'create': 0, 'solve': 0}


def test_numeric_predecessor_pin_does_not_authorize_direct(monkeypatch):
    from src.rq2_joint_deliverability_boundary_v1 import normal_execution_stream_numeric as prior
    inputs = fixture(2)
    calls = install(monkeypatch, inputs)
    kw = arguments(inputs)
    kw['expected_execution_identity'] = prior.normal_execution_identity(
        kw['expected_input_identity'], kw['expected_scale'], SPEC, BUDGET)
    with pytest.raises(ValueError, match='execution identity drift'):
        api.run_normal_only(inputs, **kw)
    assert calls == {'create': 0, 'solve': 0}
