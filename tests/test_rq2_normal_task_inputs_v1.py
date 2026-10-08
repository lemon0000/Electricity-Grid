from copy import deepcopy
from dataclasses import asdict, replace
from hashlib import sha256
import json
from pathlib import Path

import pytest
import yaml

from test_rq2_continuous_grid_normal_v1 import fixture
from test_rq2_source_pair_v1 import declaration
from src.rq2_joint_deliverability_boundary_v1 import normal_task_inputs as api


def encoded(record):
    return json.dumps(record, default=lambda x: x.isoformat() if hasattr(x, 'isoformat') else list(x),
                      allow_nan=False).encode()


@pytest.fixture
def supplied(tmp_path, monkeypatch):
    inputs = fixture(2)
    inputs = replace(inputs, carry=replace(inputs.carry, initial_history_role='mechanism_assumption'))
    normal_id = api.kernel.normal_input_identity(inputs)
    grid = inputs.carry.identity
    config = tmp_path/'audit.yaml'
    config.write_bytes(b'{}\n')
    config_sha = sha256(config.read_bytes()).hexdigest()
    d = replace(declaration(), hours=2, config_sha256=config_sha)
    pair = tmp_path/'pair.yaml'
    pair.write_text(yaml.safe_dump(asdict(d)), encoding='utf-8')
    pair_sha = sha256(pair.read_bytes()).hexdigest()
    binding = dict(normal_assembly_identity='1'*64, normal_input_identity=normal_id, pair_identity='3'*64,
        power_binding=dict(grid_source_manifest_sha256=grid.source_sha256, split=grid.split,
            outage_seed=grid.outage_seed, trajectory_id=grid.trajectory_id, raw_source_hours=[0, 1]))
    binding['binding_identity'] = api.source.source_window._hash(binding)
    record = dict(status='DRAFT_NONAUTHORITATIVE', mode='verify', external_assembly_identity_verified=True,
        formal_result=False, solver_calls=0, declaration_role='explicit_mechanism_input_not_executable_checkpoint',
        normal_assembly_identity='1'*64, expected_assembly_identity='1'*64, normal_input_identity=normal_id,
        pair_identity='3'*64, pair_declaration_sha256=pair_sha, binding=binding,
        request=asdict(inputs.request), initial=asdict(inputs.initial), carry=asdict(inputs.carry),
        source_time_basis=inputs.source_time_basis, dependencies=[], extra_implementation_sha256={},
        model_builds=1, model_scale=dict(variables=10, constraints=12), normal_assignment_verified=False,
        normal_declaration_sha256='4'*64, original_dc_requested_mw=[0., 0.], runner_sha256='5'*64)
    normal = tmp_path/'normal.json'
    normal.write_bytes(encoded(record))
    request = api.NormalTaskSourceRequest(str(normal), sha256(normal.read_bytes()).hexdigest(),
        str(pair), pair_sha, str(tmp_path), str(config), config_sha, '1'*64, normal_id, '3'*64,
        binding['binding_identity'], api.kernel.Rq2ModelScale(10, 12), 1024**2, 65536, 65536)
    calls = []
    def assemble(root, hours, req, initial, carry, *, source_time_basis):
        rebuilt = replace(inputs, request=req, initial=initial, carry=carry, source_time_basis=source_time_basis)
        calls.append(hours)
        return api.source.SourceNormalAssembly(rebuilt, hours, grid.source_sha256,
            api.kernel.normal_input_identity(rebuilt), '1'*64)
    monkeypatch.setattr(api.source_normal, 'assemble_source_normal', assemble)
    monkeypatch.setattr(api.source.binding, 'bind_pair_normal', lambda *a, **k: deepcopy(binding))
    def forbidden(*a, **k): raise AssertionError('task input preparation cannot solve')
    monkeypatch.setattr(api.kernel.native, 'create_solver', forbidden)
    return request, record, inputs, calls


def run(request):
    return api.prepare_task_inputs(request, expected_request_identity=api.task_source_identity(request))


def rewrite(request, record):
    raw = encoded(record)
    Path(request.normal_record_path).write_bytes(raw)
    return replace(request, expected_normal_record_sha256=sha256(raw).hexdigest())


def test_mechanism_inputs_reconstructed_not_executable_checkpoint(supplied):
    request, record, inputs, calls = supplied
    result = run(request)
    assert calls == [(0, 1)]
    assert api.kernel.normal_input_identity(result.assembly.inputs) == request.expected_input_identity
    assert result.binding_json == api.source._json(record['binding'])
    assert result.assembly.inputs.carry.initial_history_role == 'mechanism_assumption'
    assert result.solver_calls == 0 and result.mechanism_initial_state
    assert not any((result.observed_power_mapping, result.normal_assignment_verified, result.formal_result))
    times = dict(result.timings)
    assert times['observed_total_seconds'] == pytest.approx(sum(t for n, t in result.timings[:-1]))
    with pytest.raises(TypeError):
        api.PreparedNormalTaskInputs()
    with pytest.raises(TypeError):
        replace(result, formal_result=True)


@pytest.mark.parametrize('module', [api.local, api.source, api.source.kernel, api.declaration_reader])
def test_actual_dependency_bytes_are_bound(supplied, monkeypatch, module):
    before = api.task_source_identity(supplied[0])
    target = Path(module.__file__).resolve()
    original = Path.read_bytes
    def changed(path):
        raw = original(path)
        return raw+b'\n# changed dependency\n' if path.resolve() == target else raw
    monkeypatch.setattr(Path, 'read_bytes', changed)
    assert api.task_source_identity(supplied[0]) != before


@pytest.mark.parametrize('field,value', [('formal_result', True), ('solver_calls', False),
    ('solver_calls', 1), ('mode', 'derive'), ('external_assembly_identity_verified', 1),
    ('declaration_role', 'checkpoint'), ('normal_assembly_identity', '0'*64),
    ('normal_input_identity', '0'*64), ('pair_identity', '0'*64), ('pair_declaration_sha256', '0'*64),
    ('normal_assignment_verified', True), ('model_builds', True),
    ('model_scale', dict(variables=10., constraints=12)), ('unknown', 'value')])
def test_coherently_rehashed_wrong_role_or_pin_rejected_before_source(supplied, field, value):
    request, record, _, calls = supplied
    record[field] = value
    with pytest.raises(ValueError):
        run(rewrite(request, record))
    assert not calls


@pytest.mark.parametrize('name', ['normal_record_path', 'pair_declaration_path', 'config_path'])
def test_source_declaration_drift_and_limits_before_rebuild(supplied, name):
    request, _, _, calls = supplied
    Path(getattr(request, name)).write_bytes(b'changed')
    with pytest.raises(ValueError, match='size/hash'):
        run(request)
    assert not calls


@pytest.mark.parametrize('name', ['max_normal_record_bytes', 'max_pair_declaration_bytes', 'max_config_bytes'])
def test_each_byte_limit_enforced(supplied, name):
    request, _, _, calls = supplied
    with pytest.raises(ValueError, match='size/hash'):
        run(replace(request, **{name: 1}))
    assert not calls


def test_wrong_request_pin_prevents_reads(supplied, monkeypatch):
    def forbidden(*a): raise AssertionError('read forbidden')
    monkeypatch.setattr(api, '_read_pinned', forbidden)
    with pytest.raises(ValueError, match='request drift'):
        api.prepare_task_inputs(supplied[0], expected_request_identity='0'*64)


def test_saved_binding_body_tamper_rejected_before_source(supplied):
    request, record, _, calls = supplied
    record['binding']['power_binding']['outage_seed'] += 1
    with pytest.raises(ValueError, match='binding body'):
        run(rewrite(request, record))
    assert not calls


def test_changed_initial_mechanism_does_not_inherit_normal_pin(supplied):
    request, record, _, _ = supplied
    record['initial']['generation_mw']['G1'] += 1
    with pytest.raises(ValueError):
        run(rewrite(request, record))


def test_fresh_binding_content_not_only_identity_checked(supplied, monkeypatch):
    request, record, _, _ = supplied
    bad = deepcopy(record['binding'])
    bad['unbound_field'] = True
    monkeypatch.setattr(api.source.binding, 'bind_pair_normal', lambda *a, **k: bad)
    with pytest.raises(ValueError, match='rebuilt normal task binding'):
        run(request)


def test_post_rebuild_file_drift_rejected(supplied, monkeypatch):
    request, record, _, _ = supplied
    def binder(*a, **k):
        Path(request.config_path).write_bytes(b'changed')
        return deepcopy(record['binding'])
    monkeypatch.setattr(api.source.binding, 'bind_pair_normal', binder)
    with pytest.raises(ValueError, match='size/hash'):
        run(request)


@pytest.mark.parametrize('raw', [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}'])
def test_noncanonical_json_values_rejected(raw):
    with pytest.raises(ValueError):
        api._json(raw)


def test_real_pinned_h25_preparation_without_solver(monkeypatch):
    path = Path('results/tables/rq2_source_pairs_v1_non_authoritative/normal_dynamic_verified_non_authoritative.json').resolve()
    raw = path.read_bytes()
    assert sha256(raw).hexdigest() == '8c9b58ff3de2f37fecddcc283a1950e91c917a0dd0fc3d4c9025c29af317707d'
    record = json.loads(raw)
    pair = Path('configs/rq2_source_pair_training_example_v1.DRAFT.yaml').resolve()
    config = Path(api.source.source_window.audit.DEFAULT_CONFIG).resolve()
    request = api.NormalTaskSourceRequest(str(path), sha256(raw).hexdigest(), str(pair),
        'e4d78a3c4e060f493a8d238e4122a649c7a610cde8c0b2cc882fa091831e5019',
        str(Path('data/raw/rts_gmlc/v0.2.3/upstream').resolve()), str(config),
        '0cca33dbfbd934881be3c4e375c76eb668c2ec41ff9bbc7392c2eb3947de18a5',
        record['normal_assembly_identity'], record['normal_input_identity'], record['pair_identity'],
        record['binding']['binding_identity'], api.kernel.Rq2ModelScale(22275, 28004), 1024**2, 65536, 65536)
    def forbidden(*a, **k): raise AssertionError('native solve forbidden')
    monkeypatch.setattr(api.kernel.native, 'create_solver', forbidden)
    result = run(request)
    assert result.assembly.assembly_identity == record['normal_assembly_identity']
    assert result.binding_json == api.source._json(record['binding'])
    assert len(result.assembly.inputs.source_hours) == 25 and result.solver_calls == 0
    print(json.dumps(dict(result.timings), sort_keys=True))
