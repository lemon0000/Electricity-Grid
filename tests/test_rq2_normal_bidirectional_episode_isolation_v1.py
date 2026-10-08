"""Version boundaries rejected before payload use, and transitive identity binding."""
from dataclasses import fields

import pytest

from src.rq2_joint_deliverability_boundary_v1 import normal_episode_transport as old
from src.rq2_joint_deliverability_boundary_v1 import normal_bidirectional_episode_transport as new
from src.rq2_joint_deliverability_boundary_v1 import normal_bidirectional_episode_worker as worker


@pytest.mark.parametrize('sender,receiver', [(old, new), (new, old)])
def test_foreign_outer_type_is_rejected_before_payload_use(sender, receiver):
    packet = sender.BoundEpisodeInputs(**{field.name: None for field in fields(sender.BoundEpisodeInputs)})
    with pytest.raises(ValueError, match='typed normal-bound episode inputs required'):
        receiver.validate(packet)


@pytest.mark.parametrize('sender,receiver', [(old, new), (new, old)])
def test_foreign_schema_is_rejected_before_payload_decode(sender, receiver):
    wire = dict(schema=sender.SCHEMA, normal_request='', normal_record_hex='', episode_inputs='',
        normal_sha256='', normal_request_identity='', episode_sha256='', binding_identity='', max_normal_bytes=1)
    with pytest.raises(ValueError, match='exact normal-bound episode wire inventory required'):
        receiver.decode_inputs(receiver.selector.store._bytes(wire))


def test_bidirectional_dependency_identity_propagates_through_bridge(monkeypatch):
    identities = (new.binding.implementation_identity, new.implementation_identity, worker.implementation_identity)
    before = tuple(identity() for identity in identities)
    monkeypatch.setattr(new.legacy, 'implementation_identity', lambda: 'f'*64)
    after = tuple(identity() for identity in identities)
    assert all(a != b for a, b in zip(before, after, strict=True))
