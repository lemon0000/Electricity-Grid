from dataclasses import replace
from hashlib import sha256

import pytest

from src.rq2_joint_deliverability_boundary_v1 import source_normal as source
from tests.test_rq2_continuous_grid_normal_v1 import fixture


@pytest.fixture
def supplied(tmp_path, monkeypatch):
    inputs = fixture(3)
    manifest = tmp_path / 'SHA256SUMS'
    manifest.write_bytes(b'synthetic-test-manifest\n')
    digest = sha256(manifest.read_bytes()).hexdigest()
    inputs = replace(inputs, carry=replace(inputs.carry,
        identity=replace(inputs.carry.identity, source_sha256=digest)))
    monkeypatch.setattr(source, 'RTS_GMLC_MANIFEST_SHA256', digest)
    monkeypatch.setattr(source, 'verify_sha256_manifest', lambda root: True)
    monkeypatch.setattr(source, 'load_rts_gmlc_chronological_data', lambda root: inputs.data)
    return tmp_path, inputs


def assemble(supplied, hours=(0, 1, 2), **changes):
    root, inputs = supplied
    return source.assemble_source_normal(root, hours,
        changes.get('request', inputs.request), changes.get('initial', inputs.initial),
        changes.get('carry', inputs.carry), source_time_basis=changes.get('basis', inputs.source_time_basis))


def test_first_hour_mapping_and_source_revalidation(supplied):
    result = assemble(supplied)
    assert result.raw_source_hours == (0, 1, 2)
    assert result.inputs.source_hours == (1, 2, 3)
    assert result.inputs.carry.source_hour == 0
    assert source.validate_source_assembly(result, supplied[0]) == result


@pytest.mark.parametrize('hours', [(), (True,), (-1,), (0, 2), (1, 0), (1, 2, 3), (0, 1, 2, 3)])
def test_invalid_or_shifted_hours_rejected(supplied, hours):
    with pytest.raises(ValueError):
        assemble(supplied, hours)


def test_manifest_pin_and_file_verification(supplied, monkeypatch):
    root, _ = supplied
    monkeypatch.setattr(source, 'verify_sha256_manifest', lambda root: False)
    with pytest.raises(ValueError, match='manifest'):
        assemble(supplied)
    monkeypatch.setattr(source, 'verify_sha256_manifest', lambda root: True)
    (root / 'SHA256SUMS').write_bytes(b'changed')
    with pytest.raises(ValueError, match='manifest'):
        assemble(supplied)


def test_source_change_during_load_rejected(supplied, monkeypatch):
    root, inputs = supplied
    def changed(root):
        (root / 'SHA256SUMS').write_bytes(b'changed')
        return inputs.data
    monkeypatch.setattr(source, 'load_rts_gmlc_chronological_data', changed)
    with pytest.raises(ValueError, match='manifest'):
        assemble(supplied)


def test_no_silent_timestamp_or_demand_correction(supplied):
    _, inputs = supplied
    request = replace(inputs.request, timestamps=tuple(reversed(inputs.request.timestamps)))
    with pytest.raises(ValueError):
        assemble(supplied, request=request)
    request = replace(inputs.request, system_demand_by_bus_mw=({1: 21., 2: 0.},)*3)
    with pytest.raises(ValueError, match='demand mismatch'):
        assemble(supplied, request=request)


def test_initial_is_not_inferred_or_corrected(supplied):
    _, inputs = supplied
    initial = replace(inputs.initial, generation_mw={'G1': 30.})
    with pytest.raises(ValueError, match='initial/request'):
        assemble(supplied, initial=initial)
    with pytest.raises(ValueError, match='source clock'):
        assemble(supplied, basis='aware_source')


def test_mutable_payload_drift_and_relabel_rejected(supplied):
    result = assemble(supplied)
    result.inputs.data.hourly_points[0].demand_by_bus_mw[1] = 99.
    with pytest.raises(ValueError):
        source.validate_source_assembly(result, supplied[0])


@pytest.mark.parametrize('field', ['normal_identity', 'assembly_identity', 'source_manifest_sha256'])
def test_bound_identity_drift(supplied, field):
    result = replace(assemble(supplied), **{field: '0'*64})
    with pytest.raises(ValueError, match='drift'):
        source.validate_source_assembly(result, supplied[0])


def test_cross_day_mapping(supplied, monkeypatch):
    root, _ = supplied
    original = fixture(26)
    monkeypatch.setattr(source, 'load_rts_gmlc_chronological_data', lambda root: original.data)
    request = original.request
    from dataclasses import fields
    request = replace(request, **{f.name: getattr(request, f.name)[23:26]
        for f in fields(request) if type(getattr(request, f.name)) is tuple
        and len(getattr(request, f.name)) == 26})
    carry = replace(original.carry, source_hour=23,
        identity=replace(original.carry.identity, source_sha256=source.RTS_GMLC_MANIFEST_SHA256))
    result = source.assemble_source_normal(root, (23, 24, 25), request, original.initial,
        carry, source_time_basis=original.source_time_basis)
    assert result.inputs.source_hours == (24, 25, 26)
    assert tuple(t.hour for t in result.inputs.request.timestamps) == (23, 0, 1)


def test_carry_source_mismatch(supplied):
    _, inputs = supplied
    carry = replace(inputs.carry, identity=replace(inputs.carry.identity, source_sha256='0'*64))
    with pytest.raises(ValueError, match='carry source identity'):
        assemble(supplied, carry=carry)


@pytest.mark.parametrize('field', ['normal_identity', 'assembly_identity', 'source_manifest_sha256'])
def test_custom_digest_comparison_rejected(supplied, field):
    class Equal:
        def __eq__(self, other):
            return True
        def __ne__(self, other):
            return False
    result = replace(assemble(supplied), **{field: Equal()})
    with pytest.raises(ValueError, match='SHA256 required'):
        source.validate_source_assembly(result, supplied[0])


def test_caller_dictionary_mutation_does_not_change_assembly(supplied):
    _, inputs = supplied
    result = assemble(supplied)
    inputs.initial.generation_mw['G1'] = 99.
    inputs.request.system_demand_by_bus_mw[0][1] = 99.
    assert result.inputs.initial.generation_mw['G1'] == 20.
    assert result.inputs.request.system_demand_by_bus_mw[0][1] == 20.


def test_source_drift_after_assembly(supplied):
    root, _ = supplied
    result = assemble(supplied)
    (root / 'SHA256SUMS').write_bytes(b'changed')
    with pytest.raises(ValueError, match='manifest'):
        source.validate_source_assembly(result, root)


def test_last_source_hour_and_first_out_of_range(supplied):
    from dataclasses import fields
    root, inputs = supplied
    request = replace(inputs.request, **{f.name: getattr(inputs.request, f.name)[-1:]
        for f in fields(inputs.request) if type(getattr(inputs.request, f.name)) is tuple
        and len(getattr(inputs.request, f.name)) == 3})
    result = source.assemble_source_normal(root, (2,), request, inputs.initial,
        replace(inputs.carry, source_hour=2), source_time_basis=inputs.source_time_basis)
    assert result.inputs.source_hours == (3,)
    with pytest.raises(ValueError, match='source indices'):
        source.assemble_source_normal(root, (3,), request, inputs.initial,
            replace(inputs.carry, source_hour=3), source_time_basis=inputs.source_time_basis)
