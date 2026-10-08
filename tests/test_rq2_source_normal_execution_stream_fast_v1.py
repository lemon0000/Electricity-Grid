from copy import deepcopy
from dataclasses import fields, replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from test_rq2_continuous_grid_normal_v1 import fixture
from test_rq2_continuous_grid_candidate_v1 import install
from test_rq2_normal_execution_stream_fast_v1 import arguments
from test_rq2_source_pair_v1 import declaration
from src.rq2_joint_deliverability_boundary_v1 import source_normal_execution_stream_fast as api


@pytest.fixture
def supplied(monkeypatch):
    inputs = fixture(2)
    kw = arguments(inputs)
    assembly = api.StreamingSourceNormalAssembly(inputs, (0, 1), '1'*64, kw['expected_input_identity'],
        '2'*64, api.binding.source.implementation_identity(), '4'*64)
    d = replace(declaration(), hours=2)
    content = dict(normal_input_identity=assembly.normal_identity,
        normal_assembly_identity=assembly.legacy_content_assembly_identity,
        pair_identity='3'*64, dynamic_baseline_correspondence_verified=True,
        formal_result=False, observed_power_mapping=False)
    content['binding_identity'] = api.source_window._hash(content)
    wire=json.dumps(content,sort_keys=True,separators=(',', ':'))
    impl=api.binding.implementation_identity()
    report=dict(normal_identity=assembly.normal_identity,source_assembly_identity=assembly.assembly_identity,
        pair_identity='3'*64,legacy_content_json=wire,legacy_content_binding_identity=content['binding_identity'],
        implementation_identity=impl,binding_identity=api.kernel._digest(api.binding.CONTRACT,
        assembly.normal_identity,assembly.assembly_identity,'3'*64,wire,impl))
    count = [0]
    def binder(*args, **kwargs):
        count[0] += 1
        return api.binding.StreamingPairBinding(**deepcopy(report))
    monkeypatch.setattr(api.binding, 'bind_pair_normal', binder)
    return assembly, d, report, count


def options(assembly, d, report):
    kw = arguments(assembly.inputs)
    normal_pin = kw.pop('expected_execution_identity')
    implementations=dict(expected_source_implementation_identity=api.binding.source.implementation_identity(),
        expected_binding_implementation_identity=api.binding.implementation_identity())
    return dict(**kw, **implementations, expected_normal_execution_identity=normal_pin,
        expected_assembly_identity=assembly.assembly_identity, expected_pair_identity='3'*64,
        expected_binding_identity=report['binding_identity'],
        expected_source_execution_identity=api.source_execution_identity(report['binding_identity'], normal_pin, d,
            expected_assembly_identity=assembly.assembly_identity, expected_pair_identity='3'*64, **implementations))


def run(supplied, **changes):
    assembly, d, report, _ = supplied
    kw = options(assembly, d, report)
    kw.update(changes)
    return api.run_source_normal(assembly, 'unused', d, **kw)


def test_tiny_native_kernel_with_stubbed_source_boundary(supplied):
    result = run(supplied)
    assert result.source_bound_normal_accepted, (result.errors, result.normal_result.errors)
    assert result.source_correspondence_verified
    assert result.solver_calls == 1 and result.call_count_complete
    assert supplied[3][0] == 2
    assert result.binding_before_json == result.binding_after_json
    assert result.normal_result.public_source_binding_verified is False
    assert not any((result.hard_resource_limits_enforced, result.durable_invocation_tracking,
        result.registered_coupling, result.observed_power_mapping, result.formal_result, result.security_certified))
    assert len(result.identity) == 64
    with pytest.raises(TypeError):
        api.FastStreamingSourceNormalExecutionResult()
    with pytest.raises(TypeError):
        replace(result, source_bound_normal_accepted=False)


@pytest.mark.parametrize('field', ['expected_assembly_identity', 'expected_pair_identity',
    'expected_binding_identity', 'expected_input_identity',
    'expected_normal_execution_identity', 'expected_source_execution_identity',
    'expected_source_implementation_identity', 'expected_binding_implementation_identity'])
def test_wrong_external_pins_before_kernel(supplied, monkeypatch, field):
    count = [0]
    def forbidden(*args, **kwargs):
        count[0] += 1
        raise AssertionError('kernel must not be called')
    monkeypatch.setattr(api.kernel, 'run_normal_only', forbidden)
    with pytest.raises(ValueError):
        run(supplied, **{field: '0'*64})
    assert count == [0]


def test_pre_source_rejection_does_not_call_kernel(supplied, monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError('unresolved source pair')
    def forbidden(*args, **kwargs):
        raise AssertionError('kernel must not be called')
    monkeypatch.setattr(api.binding, 'bind_pair_normal', fail)
    monkeypatch.setattr(api.kernel, 'run_normal_only', forbidden)
    with pytest.raises(ValueError, match='unresolved source pair'):
        run(supplied)


@pytest.mark.parametrize('fault', ['pin', 'report', 'exception', 'interrupt'])
def test_post_source_failure_preserves_returned_normal(supplied, monkeypatch, fault):
    install(monkeypatch, supplied[0].inputs)
    report = deepcopy(supplied[2])
    count = [0]
    def binder(*args, **kwargs):
        count[0] += 1
        changed = deepcopy(report)
        if count[0] == 2:
            if fault == 'pin': changed['binding_identity'] = '0'*64
            elif fault == 'report': changed['legacy_content_json'] += ' '
            elif fault == 'exception': raise ValueError('source changed')
            else: raise KeyboardInterrupt('source audit interrupted')
        return api.binding.StreamingPairBinding(**changed)
    monkeypatch.setattr(api.binding, 'bind_pair_normal', binder)
    result = run(supplied)
    assert result.normal_result.normal_accepted
    assert not result.source_bound_normal_accepted and not result.source_correspondence_verified
    assert result.solver_calls == 1 and result.call_count_complete
    assert result.errors
    if fault == 'interrupt': assert result.status == 'interrupted_source_bound_normal'


def test_kernel_timeout_not_promoted_by_valid_sources(supplied, monkeypatch):
    install(monkeypatch, supplied[0].inputs, fault='timeout')
    result = run(supplied)
    assert result.source_correspondence_verified
    assert not result.source_bound_normal_accepted
    assert result.normal_result.witness is not None
    assert result.normal_result.normal.assignment_valid
    assert result.status == 'unresolved_source_bound_normal'


@pytest.mark.parametrize('kind', ['exception', 'interrupt', 'nonowned'])
def test_missing_owned_kernel_return_stays_unknown(supplied, monkeypatch, kind):
    def missing(*args, **kwargs):
        if kind == 'nonowned': return {'normal_accepted': True, 'solver_calls': 0}
        if kind == 'interrupt': raise KeyboardInterrupt('lost return')
        raise RuntimeError('lost return')
    monkeypatch.setattr(api.kernel, 'run_normal_only', missing)
    result = run(supplied)
    assert result.normal_result is None and result.solver_calls is None
    assert not result.call_count_complete and not result.source_bound_normal_accepted
    assert result.source_correspondence_verified


def test_wrong_returned_kernel_identity_not_accepted(supplied, monkeypatch):
    install(monkeypatch, supplied[0].inputs)
    original = api.kernel.run_normal_only
    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        payload = {f.name: getattr(result, f.name) for f in fields(result)}
        payload['execution_identity'] = '0'*64
        return api.kernel.native._make(api.kernel.FastStreamingNormalExecutionResult, **payload)
    monkeypatch.setattr(api.kernel, 'run_normal_only', changed)
    result = run(supplied)
    assert result.normal_result.normal_accepted and not result.source_bound_normal_accepted
    assert 'normal_result_binding_mismatch' in result.errors
    assert result.solver_calls == 1


def test_caller_mutation_isolated_before_kernel(supplied, monkeypatch):
    assembly = supplied[0]
    install(monkeypatch, assembly.inputs)
    original = api.kernel.run_normal_only
    def changed(inputs, **kwargs):
        assembly.inputs.request.system_demand_by_bus_mw[0][1] = 999.
        assert inputs.request.system_demand_by_bus_mw[0][1] == 20.
        return original(inputs, **kwargs)
    monkeypatch.setattr(api.kernel, 'run_normal_only', changed)
    result = run(supplied)
    assert result.source_bound_normal_accepted


def test_wrapper_source_drift_after_kernel(supplied, monkeypatch):
    install(monkeypatch, supplied[0].inputs)
    original = api.kernel.run_normal_only
    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        monkeypatch.setattr(api, 'source_execution_identity', lambda *args, **kwargs: '0'*64)
        return result
    monkeypatch.setattr(api.kernel, 'run_normal_only', changed)
    result = run(supplied)
    assert result.normal_result.normal_accepted and not result.source_bound_normal_accepted
    assert result.errors[0].startswith('post_source:')


def test_fresh_import_source_closure_bound():
    script = '''
import json, sys
from pathlib import Path
import src.rq2_joint_deliverability_boundary_v1.source_normal_execution_stream_fast
root=Path.cwd()
print(json.dumps(sorted(Path(m.__file__).resolve().relative_to(root).as_posix()
 for n,m in sys.modules.items() if n == 'src' or n.startswith('src.'))))
'''
    result = subprocess.run([sys.executable, '-B', '-c', script], check=True, capture_output=True,
        text=True, cwd=Path(__file__).resolve().parents[1], timeout=30)
    known = {n for n, _ in api.kernel.native._dependencies()[0]} | set(api.kernel.native.EXTRA_DEPENDENCIES)
    known |= set(api.ADAPTER_DEPENDENCIES) | {'src/rq2_joint_deliverability_boundary_v1/normal_execution.py'}
    assert set(json.loads(result.stdout)) == known


@pytest.mark.parametrize('field,value', [('normal', None), ('witness', None), ('solver_calls', 0),
    ('call_count_complete', False), ('status', 'unresolved_normal'), ('errors', ('failed',)),
    ('formal_result', True), ('normal_accepted', 1), ('contract', 'foreign')])
def test_inconsistent_typed_success_rejected(supplied, monkeypatch, field, value):
    install(monkeypatch, supplied[0].inputs)
    original = api.kernel.run_normal_only
    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        payload = {f.name: getattr(result, f.name) for f in fields(result)}
        payload[field] = value
        return api.kernel.native._make(api.kernel.FastStreamingNormalExecutionResult, **payload)
    monkeypatch.setattr(api.kernel, 'run_normal_only', changed)
    result = run(supplied)
    assert not result.source_bound_normal_accepted
    assert 'normal_result_acceptance_inconsistent' in result.errors


@pytest.mark.parametrize('field', ['source_assembly_identity', 'pair_identity'])
def test_binding_report_lineage_cannot_ignore_external_pins(supplied, monkeypatch, field):
    supplied[2][field] = '0'*64
    called = [False]
    def forbidden(*args, **kwargs):
        called[0] = True
        raise AssertionError('kernel forbidden')
    monkeypatch.setattr(api.kernel, 'run_normal_only', forbidden)
    with pytest.raises(ValueError, match='external binding'):
        run(supplied)
    assert called == [False]


def test_binding_content_must_match_pin_not_only_identity_field(supplied, monkeypatch):
    supplied[2]['legacy_content_json'] += ' '
    count = [0]
    def forbidden(*args, **kwargs):
        count[0] += 1
        raise AssertionError('kernel forbidden')
    monkeypatch.setattr(api.kernel, 'run_normal_only', forbidden)
    with pytest.raises(ValueError, match='binding content'):
        run(supplied)
    assert count == [0]


@pytest.mark.parametrize('field', ['legacy_content_binding_identity', 'implementation_identity'])
def test_binding_metadata_not_trusted(supplied, monkeypatch, field):
    supplied[2][field] = '0'*64
    monkeypatch.setattr(api.kernel, 'run_normal_only', lambda *a, **k: pytest.fail('kernel entered'))
    with pytest.raises(ValueError): run(supplied)


def test_legacy_binding_pin_cannot_authorize_streaming_source(supplied,monkeypatch):
    monkeypatch.setattr(api.kernel, 'run_normal_only', lambda *a, **k: pytest.fail('kernel entered'))
    with pytest.raises(ValueError):
        run(supplied,expected_binding_identity=supplied[2]['legacy_content_binding_identity'])


def test_prior_stream_source_pin_cannot_authorize_fast_source(supplied, monkeypatch):
    from src.rq2_joint_deliverability_boundary_v1 import source_normal_execution_stream as prior
    assembly, declaration, report, _ = supplied
    kw = options(assembly, declaration, report)
    old_pin = prior.source_execution_identity(kw['expected_binding_identity'],
        kw['expected_normal_execution_identity'], declaration, **{name: kw[name] for name in (
            'expected_assembly_identity', 'expected_pair_identity',
            'expected_source_implementation_identity', 'expected_binding_implementation_identity')})
    monkeypatch.setattr(api.kernel, 'run_normal_only', lambda *a, **k: pytest.fail('kernel entered'))
    with pytest.raises(ValueError):
        run(supplied, expected_source_execution_identity=old_pin)
