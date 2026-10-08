from dataclasses import replace, fields
from fractions import Fraction
from hashlib import sha256

import pytest

from test_rq2_episode_bidirectional_v1 import inputs
from src.rq2_joint_deliverability_boundary_v1 import scale_episode_bidirectional_transport as transport


@pytest.fixture(scope='module')
def packet(tmp_path_factory):
    req, arms, hours, settings = inputs(tmp_path_factory.mktemp('episode_transport'))
    original = transport.EpisodeInputs(req, arms, hours, settings['budget'], settings['resource_plan'])
    return original, transport.export_inputs(original)


def test_complete_typed_roundtrip(packet):
    original, raw = packet
    reconstructed = transport.decode_inputs(raw)
    assert reconstructed == original
    assert transport.export_inputs(reconstructed) == raw
    assert reconstructed is not original
    assert type(reconstructed.arms[0].business.initial.tracks[0][1].ledger.debt) is Fraction


def test_old_request_tag_and_old_episode_class_are_rejected(packet):
    from src.rq2_joint_deliverability_boundary_v1 import scale_selector_store as old_store
    from src.rq2_joint_deliverability_boundary_v1 import scale_episode_transport as old_transport
    original, raw = packet
    old_request = old_store.SelectorRequest(**vars(original.reference_request))
    with pytest.raises(ValueError):
        transport.export_inputs(replace(original, reference_request=old_request))
    old_inputs = old_transport.EpisodeInputs(**vars(original))
    with pytest.raises(ValueError): transport.export_inputs(old_inputs)
    # Keep the new envelope and canonical bytes, but use the old request type tag.
    tampered = raw.replace(b'"MixedSelectorRequest"', b'"SelectorRequest"')
    assert tampered != raw
    with pytest.raises(ValueError, match='fixed inventory'): transport.decode_inputs(tampered)


@pytest.mark.parametrize('value', [Fraction(1, 3), Fraction(-2, 7), Fraction(0)])
def test_exact_rational_encoding(value):
    assert transport._transform(transport._transform(value, decoding=False), decoding=True) == value


@pytest.mark.parametrize('wire', [['fraction', [2, 6]], ['fraction', [0, 2]], ['fraction', [1, -2]],
    ['fraction', [True, 2]], ['float', 'nan'], ['float', '0.5'], ['ScaleSelectionResult', []],
    ['ActualDispatchState', []], ['ReferenceGridState', []], ['mapping', []]])
def test_noncanonical_or_noninput_types_rejected(wire):
    with pytest.raises(ValueError): transport._transform(wire, decoding=True)


@pytest.mark.parametrize('fault', ['extra', 'reorder', 'omit', 'schema', 'trailing'])
def test_closed_packet_and_fields(packet, fault):
    _, raw = packet
    body = transport.selector.store._decoded(raw)
    if fault == 'extra': body['extra'] = None
    elif fault == 'reorder': body['inputs'][1].reverse()
    elif fault == 'omit': body['inputs'][1].pop()
    elif fault == 'schema': body['schema'] = 'other'
    altered = transport.selector.store._bytes(body)+(b' ' if fault == 'trailing' else b'')
    with pytest.raises(ValueError): transport.decode_inputs(altered)


def test_request_file_bound_and_bounded(packet, tmp_path):
    original, raw = packet
    path = tmp_path/'inputs.json'
    path.write_bytes(raw)
    pin = sha256(raw).hexdigest()
    assert transport.read_inputs(path, expected_sha256=pin, max_request_bytes=len(raw)) == original
    for digest, limit in ((pin, len(raw)-1), ('0'*64, len(raw))):
        with pytest.raises(ValueError): transport.read_inputs(path, expected_sha256=digest, max_request_bytes=limit)


def test_depth_nodes_and_bytes_bounded():
    value = None
    for _ in range(66): value = ('nested', value)
    with pytest.raises(ValueError, match='structure'): transport._transform(value, decoding=False)
    with pytest.raises(ValueError, match='structure'): transport._transform((None,)*500001, decoding=False)
    with pytest.raises(ValueError, match='bytes'): transport.decode_inputs(b' '*(transport.LIMIT+1))


def test_resource_plan_revalidated_on_export(packet):
    original, _ = packet
    changed = replace(original.resource_plan, episodes=())
    with pytest.raises(ValueError): transport.export_inputs(replace(original, resource_plan=changed))


@pytest.mark.parametrize('fault', ['successor', 'contract'])
def test_successor_cannot_hide_inside_reference_origin(packet, fault):
    original, _ = packet
    origin = original.reference_request.before
    values = {f.name: getattr(origin, f.name) for f in fields(origin)}
    if fault == 'successor':
        physical = origin.physical_origin
        attributes = {f.name: getattr(physical, f.name) for f in fields(physical)}
        attributes.update(predecessor_identity='a'*64, evidence_role='derived_current_network_assignment')
        values['physical_origin'] = transport.selector.step._owned(type(physical), **attributes)
    else: values['contract'] = 'wrong'
    changed = replace(original, reference_request=replace(original.reference_request,
        before=transport.selector.step._owned(type(origin), **values)))
    with pytest.raises(ValueError, match='reference'):
        transport.export_inputs(changed)
    raw = transport.selector.store._bytes(dict(schema=transport.SCHEMA,
        inputs=transport._transform(changed, decoding=False)))
    with pytest.raises(ValueError, match='reference'): transport.decode_inputs(raw)


@pytest.mark.parametrize('filename', ['capacity_policy.py', 'capacity_policy_bidirectional.py', 'debt_cohorts.py', 'multiday.py',
                                    'scale_episode_resources.py', 'execution_resource_contract.py'])
def test_direct_and_transitive_input_sources_are_pinned(monkeypatch, filename):
    from pathlib import Path
    before = transport.implementation_identity()
    read = Path.read_bytes
    monkeypatch.setattr(Path, 'read_bytes', lambda path: read(path)+(b' ' if path.name == filename else b''))
    assert transport.implementation_identity() != before


def test_sealed_mixed_transport_rejects_bidirectional_input_and_schema(packet):
    from src.rq2_joint_deliverability_boundary_v1 import scale_episode_zero_face_transport as old
    original, raw = packet
    with pytest.raises(ValueError): old.decode_inputs(raw)
    with pytest.raises(ValueError): old.export_inputs(original)
    with pytest.raises(ValueError): transport.decode_inputs(raw.replace(transport.SCHEMA.encode(), old.SCHEMA.encode()))


def test_legacy_business_origin_rejected_before_episode_root(packet, tmp_path):
    from src.rq2_joint_deliverability_boundary_v1 import capacity_policy as old
    original, _ = packet
    current = original.arms[0].business
    spec = old.CapacityPolicy(**dict(vars(current.spec), rule=old.RULE))
    track = current.initial.tracks[0][1]
    prior = old.initialize_capacity_policy(spec, anchor=track.physical.anchor,
        envelope=dict(track.physical.envelope), accounting_period_id=track.ledger.accounting_period_id,
        zero_carry_in_assumption=True)
    arms = (replace(original.arms[0], business=prior),)+original.arms[1:]
    with pytest.raises(ValueError, match='bidirectional business origin'):
        transport.episode._fairness(arms)
    with pytest.raises(ValueError, match='fixed inventory'):
        transport.export_inputs(replace(original, arms=arms))
    root = tmp_path/'old_policy_non_authoritative'
    import os
    with pytest.raises(ValueError, match='bidirectional business origin'):
        transport.episode.DevelopmentBidirectionalEpisode(root, original.reference_request, arms,
            original.hours, budget=original.budget, environment=dict(os.environ), resource_plan=original.resource_plan)
    assert not root.exists()
