from copy import deepcopy
from dataclasses import replace

import pytest

from experiments import diagnose_rq2_grid_structure_fast_v1 as api


def record():
    return dict(schema='rq2_h25_structure_comparison_v1', input_identity='a'*64,
        scale=dict(variables=22275, constraints=28004),
        observations=[dict(method=m, structure_identity=api.STRUCTURE, seconds=1.) for m in api.ORDER],
        solver_calls=0, formal_result=False, normal_accepted=False,
        preparation_seconds=1., build_seconds=1., execution_bindings={'task_identity': 'b'*64})


def test_exact_build_only_report():
    body = record(); before = deepcopy(body)
    api.validate(body, 'a'*64, {'task_identity': 'b'*64})
    assert body == before


@pytest.mark.parametrize('fault', ['extra', 'input', 'variables', 'count_type', 'calls', 'bool_calls',
    'authority', 'acceptance', 'order', 'structure', 'missing_row', 'nan', 'negative', 'bool_duration'])
def test_corrupt_report_cannot_support_equivalence(fault):
    body = record()
    if fault == 'extra': body['extra'] = 0
    elif fault == 'input': body['input_identity'] = 'b'*64
    elif fault == 'variables': body['scale']['variables'] = 22274
    elif fault == 'count_type': body['scale']['constraints'] = 28004.
    elif fault == 'calls': body['solver_calls'] = 1
    elif fault == 'bool_calls': body['solver_calls'] = False
    elif fault == 'authority': body['formal_result'] = True
    elif fault == 'acceptance': body['normal_accepted'] = True
    elif fault == 'order': body['observations'][0]['method'] = 'fast'
    elif fault == 'structure': body['observations'][1]['structure_identity'] = '0'*64
    elif fault == 'missing_row': body['observations'].pop()
    elif fault == 'nan': body['observations'][1]['seconds'] = float('nan')
    elif fault == 'negative': body['build_seconds'] = -1.
    elif fault == 'bool_duration': body['preparation_seconds'] = True
    with pytest.raises(ValueError): api.validate(body, 'a'*64, {'task_identity': 'b'*64})


def test_all_registered_solver_entries_are_forbidden(monkeypatch):
    for module, name in api.solver_entrypoints():
        monkeypatch.setattr(module, name, getattr(module, name))
    state = api.guard_solver_calls()
    for module, name in api.solver_entrypoints():
        with pytest.raises(AssertionError, match='solver forbidden'): getattr(module, name)()
    assert state['forbidden_calls'] == len(api.solver_entrypoints())


@pytest.mark.parametrize('field', ['task_identity', 'source_request_identity', 'model_implementation_identity',
    'preparation_sha256', 'normal_execution_identity'])
def test_execution_binding_drift_rejected(monkeypatch, field):
    _, request, _, _, _ = api.declaration.read_declaration(api.CONFIG, api.CONFIG_SHA)
    before = api.execution_bindings(request)
    after = dict(before); after[field] = '0'*64
    monkeypatch.setattr(api, 'execution_bindings', lambda _: after)
    with pytest.raises(ValueError, match='identity drift'): api.check_bindings(request, before)


def observation():
    return api.c.process.TaskProcessObservation('a'*64, 123, 456, 0, 'child_exited',
        1., 2, 1024, (('test-volume', 1024),), (), None, ('direct_child_exit_observed',),
        1024, 2048, True)


def test_valid_process_observation():
    api.validate_process(observation(), 'a'*64, dict(pid=123, creation_filetime=456))


@pytest.mark.parametrize('field,value', [('process_identity', 'b'*64), ('pid', 124),
    ('creation_filetime', 457), ('whole_job_quiescent', False), ('job_commit_limits_configured', False),
    ('reason', 'deadline'), ('exit_code', False), ('exit_code', 1),
    ('elapsed_seconds', float('nan')), ('elapsed_seconds', -1.), ('runtime_samples', 0),
    ('job_peak_process_commit_bytes', True), ('job_peak_process_commit_bytes', 4096),
    ('job_peak_total_commit_bytes', 2**30), ('minimum_runtime_commit_available_bytes', None),
    ('last_resource_errors', ('test',)), ('observation_error_type', 'ValueError'),
    ('formal_result', True), ('hard_disk_quota_enforced', True),
    ('whole_task_resources_verified', True), ('numerical_evidence_verified', True)])
def test_process_tampering_rejected(field, value):
    with pytest.raises(ValueError):
        api.validate_process(replace(observation(), **{field: value}), 'a'*64,
            dict(pid=123, creation_filetime=456))


def test_process_mapping_not_owned_observation():
    with pytest.raises(ValueError): api.validate_process({}, 'a'*64, dict(pid=123, creation_filetime=456))


@pytest.mark.parametrize('target', ['preparation', 'model', 'encoding'])
def test_real_dependency_byte_drift_is_detected(monkeypatch, target):
    from pathlib import Path
    _, request, _, _, _ = api.declaration.read_declaration(api.CONFIG, api.CONFIG_SHA)
    before = api.execution_bindings(request)
    module = {'preparation': api.c.worker.inputs, 'model': api.c.worker.kernel.streaming,
        'encoding': api.fast.encoding}[target]
    selected = Path(module.__file__).resolve()
    original = Path.read_bytes
    monkeypatch.setattr(Path, 'read_bytes', lambda p: original(p)+(b'\n# drift'
        if p.resolve() == selected else b''))
    with pytest.raises(ValueError): api.check_bindings(request, before)
