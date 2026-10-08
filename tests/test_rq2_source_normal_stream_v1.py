from dataclasses import replace

import pytest

from src.rq2_joint_deliverability_boundary_v1 import source_normal_stream as source
from tests.test_rq2_source_normal_v1 import supplied, assemble as old_assemble


def assemble(supplied, hours=(0, 1, 2), **changes):
    root, inputs = supplied
    return source.assemble_source_normal(root, hours,
        changes.get('request', inputs.request), changes.get('initial', inputs.initial),
        changes.get('carry', inputs.carry), source_time_basis=changes.get('basis', inputs.source_time_basis),
        expected_implementation_identity=changes.get('pin', source.implementation_identity()))


def test_content_equal_execution_distinct(supplied):
    old, new = old_assemble(supplied), assemble(supplied)
    assert new.inputs == old.inputs
    assert new.normal_identity == old.normal_identity
    assert new.legacy_content_assembly_identity == old.assembly_identity
    assert new.assembly_identity != old.assembly_identity
    assert source.validate_source_assembly(new, supplied[0],
        expected_implementation_identity=source.implementation_identity()) == new
    with pytest.raises(ValueError, match='typed source assembly'):
        source.legacy.validate_source_assembly(new, supplied[0])
    with pytest.raises(ValueError, match='typed streaming'):
        source.validate_source_assembly(old, supplied[0],
            expected_implementation_identity=source.implementation_identity())


def test_no_legacy_full_input_encoder(supplied, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('legacy full-tree input path reached')
    monkeypatch.setattr(source.legacy, 'normal_input_identity', forbidden)
    monkeypatch.setattr(source.legacy, '_digest', forbidden)
    monkeypatch.setattr(source.stream.legacy, 'normal_input_identity', forbidden)
    monkeypatch.setattr(source.stream.legacy, '_digest', forbidden)
    result = assemble(supplied)
    source.validate_source_assembly(result, supplied[0],
        expected_implementation_identity=source.implementation_identity())


@pytest.mark.parametrize('hours', [(), (True,), (-1,), (0, 2), (1, 0), (1, 2, 3), (0, 1, 2, 3)])
def test_invalid_window(supplied, hours):
    with pytest.raises(ValueError):
        assemble(supplied, hours)


@pytest.mark.parametrize('field', ['source_manifest_sha256', 'normal_identity',
    'legacy_content_assembly_identity', 'implementation_identity', 'assembly_identity'])
def test_tampered_digest(supplied, field):
    result = replace(assemble(supplied), **{field: '0'*64})
    with pytest.raises(ValueError, match='drift'):
        source.validate_source_assembly(result, supplied[0],
            expected_implementation_identity=source.implementation_identity())


def test_implementation_pin_before_load(supplied, monkeypatch):
    monkeypatch.setattr(source.legacy, 'load_rts_gmlc_chronological_data',
        lambda root: pytest.fail('load before pin rejection'))
    with pytest.raises(ValueError, match='implementation drift'):
        assemble(supplied, pin='0'*64)


def test_implementation_change_during_load(supplied, monkeypatch):
    _, inputs = supplied
    pin = source.implementation_identity()
    def changed(root):
        monkeypatch.setattr(source, 'implementation_identity', lambda: '0'*64)
        return inputs.data
    monkeypatch.setattr(source.legacy, 'load_rts_gmlc_chronological_data', changed)
    with pytest.raises(ValueError, match='implementation drift'):
        assemble(supplied, pin=pin)


def test_source_change_during_load(supplied, monkeypatch):
    root, inputs = supplied
    def changed(path):
        (root / 'SHA256SUMS').write_bytes(b'changed')
        return inputs.data
    monkeypatch.setattr(source.legacy, 'load_rts_gmlc_chronological_data', changed)
    with pytest.raises(ValueError, match='manifest'):
        assemble(supplied)


def test_mutable_content_drift(supplied):
    result = assemble(supplied)
    result.inputs.data.hourly_points[0].demand_by_bus_mw[1] = 99.
    with pytest.raises(ValueError):
        source.validate_source_assembly(result, supplied[0],
            expected_implementation_identity=source.implementation_identity())


def test_caller_snapshot(supplied):
    result = assemble(supplied)
    supplied[1].initial.generation_mw['G1'] = 99.
    supplied[1].request.system_demand_by_bus_mw[0][1] = 99.
    assert result.inputs.initial.generation_mw['G1'] == 20.
    assert result.inputs.request.system_demand_by_bus_mw[0][1] == 20.


def test_loader_object_released_before_hash(supplied, monkeypatch):
    from copy import deepcopy
    import weakref
    references = []
    def load(root):
        data = deepcopy(supplied[1].data)
        references.append(weakref.ref(data))
        return data
    original = source.stream.normal_input_identity
    def checked(inputs):
        assert references and references[-1]() is None
        return original(inputs)
    monkeypatch.setattr(source.legacy, 'load_rts_gmlc_chronological_data', load)
    monkeypatch.setattr(source.stream, 'normal_input_identity', checked)
    assemble(supplied)


@pytest.mark.parametrize('value', [None, True, 'A'*64, '0'*63])
def test_malformed_external_pin(supplied, value):
    with pytest.raises(ValueError, match='SHA256'):
        assemble(supplied, pin=value)


@pytest.mark.parametrize('module', [source, source.stream, source.legacy, source.stream.legacy])
def test_implementation_binds_source_bytes(supplied, monkeypatch, module):
    from pathlib import Path
    pin = source.implementation_identity()
    target = Path(module.__file__).resolve()
    original = Path.read_bytes
    monkeypatch.setattr(Path, 'read_bytes', lambda path:
        original(path) + (b'\n# changed\n' if path.resolve() == target else b''))
    assert source.implementation_identity() != pin
    with pytest.raises(ValueError, match='implementation drift'):
        assemble(supplied, pin=pin)


@pytest.mark.parametrize('change', ['timestamp', 'demand', 'initial', 'carry', 'clock'])
def test_no_mechanism_or_source_correction(supplied, change):
    _, inputs = supplied
    changes = {
        'timestamp': dict(request=replace(inputs.request,
            timestamps=tuple(reversed(inputs.request.timestamps)))),
        'demand': dict(request=replace(inputs.request,
            system_demand_by_bus_mw=({1: 21., 2: 0.},)*3)),
        'initial': dict(initial=replace(inputs.initial, generation_mw={'G1': 30.})),
        'carry': dict(carry=replace(inputs.carry,
            identity=replace(inputs.carry.identity, source_sha256='0'*64))),
        'clock': dict(basis='aware_source'),
    }
    with pytest.raises(ValueError):
        assemble(supplied, **changes[change])
