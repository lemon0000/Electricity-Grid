from dataclasses import replace
from hashlib import sha256
import json

import pytest

from tests.test_rq2_normal_bidirectional_episode_binding_v1 import (
    bound, supplied, legacy_request, declared_source, prepared_source, bound_source as original_bound_source, base_bound_source,
    source_supplied as original_source_supplied)
from src.rq2_joint_deliverability_boundary_v1 import normal_bidirectional_episode_transport as api


@pytest.fixture
def bound_source(original_bound_source, monkeypatch, tmp_path_factory):
    from tests.normal_episode_source_fixture import packages
    root = tmp_path_factory.mktemp('indirect_sources')
    config = packages(root)
    audit = api.binding.source_pair.source_window.audit
    monkeypatch.setattr(audit, 'ROOT', root.parent)
    monkeypatch.setattr(audit, '_load_config', lambda path: config)
    return original_bound_source


@pytest.fixture
def source_supplied(original_source_supplied, monkeypatch):
    from src.rq2_joint_deliverability_boundary_v1 import source_normal as source
    root, inputs = original_source_supplied
    data = root/'synthetic_source.bin'
    data.write_bytes(b'explicit synthetic source fixture')
    manifest = root/'SHA256SUMS'
    manifest.write_text(sha256(data.read_bytes()).hexdigest()+'  synthetic_source.bin\n', encoding='ascii')
    digest = sha256(manifest.read_bytes()).hexdigest()
    inputs = replace(inputs, carry=replace(inputs.carry,
        identity=replace(inputs.carry.identity, source_sha256=digest)))
    monkeypatch.setattr(source, 'RTS_GMLC_MANIFEST_SHA256', digest)
    monkeypatch.setattr(source, 'load_rts_gmlc_chronological_data', lambda root: inputs.data)
    return root, inputs


@pytest.fixture
def packet(bound):
    request, raw, episode, _ = bound
    epraw = api.legacy.export_inputs(episode)
    args = dict(normal_sha256=sha256(raw).hexdigest(), episode_sha256=sha256(epraw).hexdigest(),
        max_normal_bytes=api.LIMIT, max_episode_bytes=api.LIMIT)
    return api.BoundEpisodeInputs(request, raw, episode, args['normal_sha256'],
        api.binding.normal.request_identity(request), args['episode_sha256'],
        api.binding.binding_identity(request, **args), api.LIMIT)


def test_complete_packet_roundtrip_and_bound_replay(packet):
    raw = api.export_inputs(packet)
    decoded = api.decode_inputs(raw)
    assert api.export_inputs(decoded) == raw
    report = api.audit_inputs(decoded)
    assert report['binding_identity'] == packet.binding_identity
    assert report['business_pair_correspondence_verified'] and report['solver_calls_by_binding'] == 0
    with pytest.raises(ValueError): api.legacy.decode_inputs(raw)
    with pytest.raises(ValueError): api.decode_inputs(api.legacy.export_inputs(packet.episode_inputs))
    for key, value in [('normal_sha256','0'*64), ('normal_request_identity','0'*64),
            ('episode_sha256','0'*64), ('binding_identity','0'*64), ('normal_record',b'{}'),
            ('max_normal_bytes',True)]:
        with pytest.raises(ValueError): api.export_inputs(replace(packet, **{key:value}))
    wire = json.loads(raw)
    wire['extra'] = False
    with pytest.raises(ValueError): api.decode_inputs(api.selector.store._bytes(wire))


def test_source_snapshot_and_output_isolation(packet, tmp_path_factory):
    before = api.source_snapshot(packet)
    api.isolate_outputs(packet, tmp_path_factory.mktemp('isolated')/'episode_non_authoritative')
    with pytest.raises(ValueError): api.isolate_outputs(packet, packet.normal_request.source.upstream_root)
    from pathlib import Path
    path = Path(packet.normal_request.source.config_path)
    raw = path.read_bytes()
    path.write_bytes(raw+b'\n')
    with pytest.raises(ValueError): api.source_snapshot(packet)
    assert before


def test_manifest_member_drift_with_unchanged_manifest(packet):
    from pathlib import Path
    before = api.source_snapshot(packet)
    root = Path(packet.normal_request.source.upstream_root)
    manifest = (root/'SHA256SUMS').read_bytes()
    (root/'synthetic_source.bin').write_bytes(b'changed data, unchanged manifest')
    assert (root/'SHA256SUMS').read_bytes() == manifest
    with pytest.raises(ValueError, match='manifest-listed source file changed'):
        api.source_snapshot(packet)
    assert before


def test_indirect_member_drift_with_unchanged_config(packet):
    from pathlib import Path
    api.source_snapshot(packet)
    _, files = api._indirect_sources(packet)
    member = next(p for p in files if p.name == 'workload_blocks.csv.gz')
    config = Path(packet.normal_request.source.config_path).read_bytes()
    member.write_bytes(b'changed indirect workload source')
    assert Path(packet.normal_request.source.config_path).read_bytes() == config
    with pytest.raises(ValueError, match='indirect source file changed'):
        api.source_snapshot(packet)
