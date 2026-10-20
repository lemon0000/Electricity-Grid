from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import pytest

from test_rq2_reference_grid_v1 import args
from test_rq2_reference_selector_v1 import run, install, SELECTOR, SHORT
from test_rq2_continuous_grid_candidate_v1 import SPEC
from src.rq2_joint_deliverability_boundary_v1 import reference_selector as selector
from src.rq2_joint_deliverability_boundary_v1 import grid_evidence_replay as replay
from src.rq2_joint_deliverability_boundary_v1 import continuous_grid_candidate as capture
from src.rq2_joint_deliverability_boundary_v1.prefix_handoff import _encoded


@pytest.fixture(scope='module')
def real():
    inputs = args()
    result = run(inputs)
    assert result.status == 'selected_numerical_reference'
    return inputs, result


def metadata(result, index):
    return dict(input_identity=result.input_identity, purpose=result.stages[index].raw_solve.purpose,
        specification=SPEC, budget=SHORT)


def export(result, index=0):
    return replay.export_grid_evidence(result.stages[index].raw_solve, **metadata(result, index))


def expectations(inputs, result, index=0):
    frozen = tuple(s.raw_solve.objective for s in result.stages[:index])
    return dict(expected_input_identity=result.input_identity, expected_purpose=result.stages[index].raw_solve.purpose,
        specification=SPEC, budget=SHORT, builder=lambda: selector._stage_model(
            *inputs, result.input_identity, index, frozen))


def check(data, inputs, result, index=0):
    return replay.replay_grid_evidence(data, expected_sha256=sha256(data).hexdigest(), **expectations(inputs, result, index))


def test_all_real_reference_stages_replay_without_solver(real, monkeypatch):
    inputs, result = real
    def forbidden(*a, **kw): raise AssertionError('native solver forbidden during replay')
    monkeypatch.setattr(capture, 'create_solver', forbidden)
    monkeypatch.setattr(capture, '_solve', forbidden)
    for index, stage in enumerate(result.stages):
        report = check(export(result, index), inputs, result, index)
        assert report.scope == 'complete_native_record'
        assert report.replay_consistent, report.replay_errors
        assert report.assignment_recomputed and report.canonical_assignment_valid
        assert report.optimal_flag_reproduced and not report.native_infeasible_flag_reproduced
        assert report.recomputed_objective == stage.raw_solve.objective
        assert report.solver_calls_by_replay_module == 0 and not report.external_builder_effects_verified
        assert not report.native_execution_authenticated
        assert report.model_relative_only and not report.source_input_binding_verified and not report.selector_chain_verified
        assert not report.formal_result and not report.security_certified
        assert report.optimality_certificate is report.infeasibility_certificate is None


@pytest.mark.parametrize('fault', ['timeout', 'infeasible', 'exception', 'missing_bound', 'missing_variable', 'options', 'objective'])
def test_failed_native_records_remain_unresolved(monkeypatch, fault):
    inputs = args()
    install(monkeypatch, fault, 0)
    result = run(inputs)
    report = check(export(result), inputs, result)
    assert not report.reported_optimal
    assert report.optimal_flag_reproduced in (False, None)
    assert report.optimality_certificate is report.infeasibility_certificate is None
    if fault in ('exception', 'missing_variable', 'options', 'objective'):
        assert report.scope == 'partial_execution_evidence'
        assert not report.replay_consistent
    else:
        assert report.replay_consistent, report.replay_errors


@pytest.mark.parametrize('field,new', [
    ('optimal', False), ('assignment_valid', False), ('native_infeasible', True),
    ('maximum_residual', .25), ('maximum_integrality_violation', .25),
    ('objective', 16.), ('lower', 14.), ('calls', 0), ('variables', 12345),
])
def test_rehashed_claim_changes_are_detected(real, field, new):
    inputs, result = real
    payload = json.loads(export(result))
    payload['raw'][field] = new
    report = check(_encoded(payload), inputs, result)
    assert not report.replay_consistent and report.replay_errors


@pytest.mark.parametrize('field', ['structures', 'options', 'versions', 'preload_values', 'initial_values'])
def test_rehashed_execution_identity_changes_are_detected(real, field):
    inputs, result = real
    payload = json.loads(export(result))
    payload['raw'][field] = []
    report = check(_encoded(payload), inputs, result)
    assert not report.replay_consistent


@pytest.mark.parametrize('field', ['native_values', 'loaded_values', 'native_objectives'])
def test_rehashed_assignment_changes_are_detected(real, field):
    inputs, result = real
    payload = json.loads(export(result))
    if payload['raw'][field]:
        payload['raw'][field][0][1] += .5
    else:
        payload['raw'][field] = [['foreign', .5]]
    report = check(_encoded(payload), inputs, result)
    assert not report.replay_consistent and report.replay_errors


def test_rehashed_bound_number_descriptor_cannot_lie(real):
    inputs, result = real
    payload = json.loads(export(result))
    payload['raw']['problem_records'][0][1][2] += 1.
    report = check(_encoded(payload), inputs, result)
    assert not report.replay_consistent and report.replay_errors


def test_native_termination_not_replaced_by_saved_optimal_flag(real):
    inputs, result = real
    payload = json.loads(export(result))
    from pyomo.opt import TerminationCondition
    payload['raw']['solver_records'][0][1] = capture._enum(TerminationCondition.maxTimeLimit)
    report = check(_encoded(payload), inputs, result)
    assert report.reported_optimal and report.optimal_flag_reproduced is False
    assert 'optimal_flag_mismatch' in report.replay_errors


def test_external_digest_and_input_pins_are_required(real):
    inputs, result = real
    data = export(result)
    values = expectations(inputs, result)
    with pytest.raises(ValueError, match='digest'):
        replay.replay_grid_evidence(data, expected_sha256='0'*64, **values)
    values['expected_input_identity'] = '1'*64
    with pytest.raises(ValueError, match='metadata'):
        replay.replay_grid_evidence(data, expected_sha256=sha256(data).hexdigest(), **values)


@pytest.mark.parametrize('mutation', ['duplicate', 'extra', 'nan', 'noncanonical'])
def test_json_contract_rejects_ambiguous_or_noncanonical_bytes(real, mutation):
    inputs, result = real
    data = export(result)
    if mutation == 'duplicate':
        data = data.replace(b'{', b'{"schema":"duplicate",', 1)
    elif mutation == 'extra':
        payload = json.loads(data)
        payload['foreign'] = False
        data = _encoded(payload)
    elif mutation == 'nan':
        data = data.replace(b'"objective":15.0', b'"objective":NaN', 1)
        assert b'NaN' in data
    else:
        data = data+b'\n'
    with pytest.raises(ValueError): check(data, inputs, result)


def test_create_only_persistence_and_truncated_file_detection(real, tmp_path):
    inputs, result = real
    path = tmp_path/'stage_non_authoritative.json'
    digest = replay.write_grid_evidence(result.stages[0].raw_solve, path, **metadata(result, 0))
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        replay.write_grid_evidence(result.stages[0].raw_solve, path, **metadata(result, 0))
    assert path.read_bytes() == before
    report = replay.read_grid_evidence(path, expected_sha256=digest, **expectations(inputs, result))
    assert report.replay_consistent
    partial = tmp_path/'partial_non_authoritative.json'
    partial.write_bytes(before[:100])
    with pytest.raises(ValueError):
        replay.read_grid_evidence(partial, expected_sha256=digest, **expectations(inputs, result))


def test_fresh_process_reads_and_recomputes_without_solver(real, tmp_path):
    _, result = real
    path = tmp_path/'fresh_non_authoritative.json'
    digest = replay.write_grid_evidence(result.stages[0].raw_solve, path, **metadata(result, 0))
    script = '''
import sys
from test_rq2_reference_grid_v1 import args
from test_rq2_reference_selector_v1 import SHORT
from test_rq2_continuous_grid_candidate_v1 import SPEC
from src.rq2_joint_deliverability_boundary_v1 import reference_selector as selector
from src.rq2_joint_deliverability_boundary_v1 import reference_grid as ref
from src.rq2_joint_deliverability_boundary_v1 import continuous_grid_candidate as capture
from src.rq2_joint_deliverability_boundary_v1.grid_evidence_replay import read_grid_evidence
inputs=args()
identity=ref.reference_input_identity(*inputs)
def forbidden(*a, **kw): raise AssertionError('solver forbidden')
capture.create_solver=capture._solve=forbidden
r=read_grid_evidence(sys.argv[1], expected_sha256=sys.argv[2], expected_input_identity=identity,
    expected_purpose=selector.PURPOSE+':0:grid_request', specification=SPEC, budget=SHORT,
    builder=lambda:selector._stage_model(*inputs, identity, 0, ()))
assert r.replay_consistent, r.replay_errors
assert r.solver_calls_by_replay_module == 0
print('fresh solver-free replay matched')
'''
    root = Path(__file__).resolve().parents[1]
    import os
    env = dict(os.environ, PYTHONPATH=str(root/'tests')+os.pathsep+str(root))
    completed = subprocess.run([sys.executable, '-B', '-c', script, str(path), digest],
        cwd=root, env=env, capture_output=True, text=True, timeout=30, check=True)
    assert 'fresh solver-free replay matched' in completed.stdout


def test_second_canonical_build_drift_is_detected(real):
    inputs, result = real
    data = export(result)
    values = expectations(inputs, result)
    build = values['builder']
    calls = []
    def changed():
        calls.append(1)
        model = build()
        if len(calls) == 2: model.reference_power.setub(24.)
        return model
    values['builder'] = changed
    report = replay.replay_grid_evidence(data, expected_sha256=sha256(data).hexdigest(), **values)
    assert len(calls) == 2
    assert not report.replay_consistent and not report.assignment_recomputed
    assert any('fresh canonical model changed' in e for e in report.replay_errors)


def test_recorded_invalid_assignment_is_recomputed_without_promoting_it(monkeypatch):
    inputs = args()
    install(monkeypatch, values_override={'generation[G1]': 0.})
    result = run(inputs)
    assert result.stages[0].raw_solve.errors == ('canonical_assignment_invalid',)
    report = check(export(result), inputs, result)
    assert report.replay_consistent, report.replay_errors
    assert report.assignment_recomputed and report.canonical_assignment_valid is False
    assert report.optimal_flag_reproduced is False


@pytest.mark.parametrize('fault', ['create_exception', 'multiple_solutions'])
def test_partial_native_capture_is_not_complete_evidence(monkeypatch, fault):
    inputs = args()
    install(monkeypatch)
    create = capture.create_solver
    def changed(spec):
        if fault == 'create_exception': raise RuntimeError('creation failed')
        solver, options = create(spec)
        solve = solver.solve
        def multi(*a, **kw):
            native = solve(*a, **kw)
            native.solution.add()
            return native
        solver.solve = multi
        return solver, options
    monkeypatch.setattr(capture, 'create_solver', changed)
    result = run(inputs)
    report = check(export(result), inputs, result)
    assert report.scope == 'partial_execution_evidence' and not report.replay_consistent
    assert report.optimal_flag_reproduced is None
    assert result.stages[0].raw_solve.calls == (0 if fault == 'create_exception' else 1)


def test_real_canonical_omissions_are_recomputed(monkeypatch):
    from pyomo.environ import ConcreteModel, Var, Constraint, Objective, NonNegativeReals
    from test_rq2_continuous_grid_candidate_v1 import BUDGET
    def build():
        m = ConcreteModel()
        m.x = Var(domain=NonNegativeReals)
        m.unused = Var()
        m.fixed = Var(initialize=3.)
        m.fixed.fix(3.)
        m.lower = Constraint(expr=m.x >= 1.)
        m.objective = Objective(expr=m.x)
        return m
    raw = capture._solve(build, SPEC, BUDGET, 'tiny_completion_replay')
    assert raw.optimal and len(raw.canonical_completed_values) == 2
    data = replay.export_grid_evidence(raw, input_identity='a'*64, purpose=raw.purpose, specification=SPEC, budget=BUDGET)
    def forbidden(*a, **kw): raise AssertionError('solver forbidden during replay')
    monkeypatch.setattr(capture, 'create_solver', forbidden)
    report = replay.replay_grid_evidence(data, expected_sha256=sha256(data).hexdigest(), expected_input_identity='a'*64,
        expected_purpose=raw.purpose, specification=SPEC, budget=BUDGET, builder=build)
    assert report.replay_consistent and report.canonical_assignment_valid
    changed = json.loads(data)
    changed['raw']['canonical_completed_values'][0][1] = int(changed['raw']['canonical_completed_values'][0][1])
    changed = _encoded(changed)
    report = replay.replay_grid_evidence(changed, expected_sha256=sha256(changed).hexdigest(), expected_input_identity='a'*64,
        expected_purpose=raw.purpose, specification=SPEC, budget=BUDGET, builder=build)
    assert not report.replay_consistent and 'canonical_completion_mismatch' in report.replay_errors


def test_fresh_import_source_closure():
    script = '''
import json,sys
from pathlib import Path
import src.rq2_joint_deliverability_boundary_v1.grid_evidence_replay
root=Path.cwd()
print(json.dumps(sorted(Path(m.__file__).resolve().relative_to(root).as_posix()
    for n,m in sys.modules.items() if n=='src' or n.startswith('src.'))))
'''
    completed = subprocess.run([sys.executable, '-B', '-c', script], capture_output=True, text=True,
        cwd=Path(__file__).resolve().parents[1], timeout=30, check=True)
    assert set(json.loads(completed.stdout)) == set(replay.DEPENDENCIES)


def test_real_actual_dispatch_stages_have_solver_free_replay(monkeypatch):
    from test_rq2_actual_dispatch_selector_v1 import inputs, run as actual_run, SHORT as actual_budget
    from src.rq2_joint_deliverability_boundary_v1 import actual_dispatch_selector as actual
    current = inputs()
    result = actual_run(current)
    assert result.status == 'selected_numerical_dispatch'
    def forbidden(*a, **kw): raise AssertionError('no native solve in replay')
    monkeypatch.setattr(capture, 'create_solver', forbidden)
    monkeypatch.setattr(capture, '_solve', forbidden)
    for index, stage in enumerate(result.stages):
        data = replay.export_grid_evidence(stage.raw_solve, input_identity=result.input_identity,
            purpose=stage.raw_solve.purpose, specification=SPEC, budget=actual_budget)
        frozen = tuple(s.raw_solve.objective for s in result.stages[:index])
        report = replay.replay_grid_evidence(data, expected_sha256=sha256(data).hexdigest(),
            expected_input_identity=result.input_identity, expected_purpose=stage.raw_solve.purpose,
            specification=SPEC, budget=actual_budget, builder=lambda: actual._stage_model(*current, index, frozen))
        assert report.replay_consistent and report.optimal_flag_reproduced
        assert not report.selector_chain_verified


@pytest.mark.parametrize('field', ['optimal', 'assignment_valid', 'variables', 'calls', 'objective'])
def test_wrong_scalar_types_rejected(real, field):
    inputs, result = real
    payload = json.loads(export(result))
    payload['raw'][field] = 1 if field in ('optimal', 'assignment_valid') else True
    with pytest.raises(ValueError): check(_encoded(payload), inputs, result)


@pytest.mark.parametrize('field', ['objective', 'lower', 'upper', 'maximum_residual', 'maximum_integrality_violation'])
def test_equal_integer_metric_does_not_impersonate_float(real, field):
    inputs, result = real
    payload = json.loads(export(result))
    original = payload['raw'][field]
    assert type(original) is float and original == int(original)
    payload['raw'][field] = int(original)
    with pytest.raises(ValueError, match='float metric'): check(_encoded(payload), inputs, result)


def test_extra_native_solver_record_field_detected(real):
    inputs, result = real
    payload = json.loads(export(result))
    payload['raw']['solver_records'][0].append('ignored field')
    report = check(_encoded(payload), inputs, result)
    assert not report.replay_consistent
    assert any('exact status/termination pair' in e for e in report.replay_errors)


def test_external_builder_effects_are_not_claimed_verified(real):
    inputs, result = real
    data = export(result)
    values = expectations(inputs, result)
    original = values['builder']
    effects = []
    def opaque():
        effects.append('external effect not inspected by replay')
        return original()
    values['builder'] = opaque
    report = replay.replay_grid_evidence(data, expected_sha256=sha256(data).hexdigest(), **values)
    assert report.replay_consistent and len(effects) == 2
    assert report.solver_calls_by_replay_module == 0
    assert not report.external_builder_effects_verified
    assert not hasattr(report, 'solver_calls_during_replay')


def test_single_declared_call_must_fit_total_budget(real):
    _, result = real
    meta = metadata(result, 0)
    meta['budget'] = replace(SHORT, max_total_solver_seconds=.5)
    with pytest.raises(ValueError, match='development budget'):
        replay.export_grid_evidence(result.stages[0].raw_solve, **meta)


@pytest.mark.parametrize('mutation', [None, 'termination', 'count', 'flag'])
def test_zero_solution_native_infeasibility_remains_only_a_report(monkeypatch, mutation):
    from pyomo.opt import TerminationCondition
    inputs = args()
    install(monkeypatch, 'infeasible', 0)
    result = run(inputs)
    payload = json.loads(export(result))
    if mutation == 'termination':
        payload['raw']['solver_records'][0][1] = capture._enum(TerminationCondition.maxTimeLimit)
    elif mutation == 'count':
        payload['raw']['solution_count'] = 1
    elif mutation == 'flag':
        payload['raw']['native_infeasible'] = False
    report = check(_encoded(payload), inputs, result)
    assert not report.native_execution_authenticated
    assert report.infeasibility_certificate is None
    if mutation is None:
        assert report.replay_consistent and report.native_infeasible_flag_reproduced
        assert not report.assignment_recomputed and report.optimal_flag_reproduced is False
    else:
        assert not report.replay_consistent and report.replay_errors
