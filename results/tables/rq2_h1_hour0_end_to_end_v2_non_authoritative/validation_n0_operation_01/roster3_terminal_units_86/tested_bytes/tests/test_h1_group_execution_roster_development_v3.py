"""Bootstrap4 type and terminal correspondence; explicit data-only fixtures.

No fixture in this module is a live owner, N0 producer or numerical proof.
"""
from types import SimpleNamespace

import pytest

from experiments import h1_group_execution_roster_development_v3 as roster
from experiments import h1_bootstrap_integration_development_v2 as old_bootstrap


PIN = 'a' * 64
OTHER = 'b' * 64


@pytest.fixture
def local():
    return roster.bootstrap._N0_body('controller_non_authoritative',
        {name: PIN for name in roster.bootstrap.N0_PINS})


def test_exact_bootstrap4_terminal_shape(local):
    roster._retained_local(local, 'controller_non_authoritative', PIN)
    assert local['historical_verifier_schema'] == roster.bootstrap.historical_verifier.VERIFIER_SCHEMA
    assert 'full_numerical_hour_replays' not in local
    assert local['legacy_compatibility_execution_metadata']['scope'] == 'predecessor_scientific_projection_only'


@pytest.mark.parametrize('field', roster.bootstrap.N0_PINS)
def test_terminal_pin_must_be_exact_sha(local, field):
    local[field] = 1
    with pytest.raises((ValueError, TypeError)):
        roster._retained_local(local, 'controller_non_authoritative', PIN)


@pytest.mark.parametrize('field', ('kind', 'controller_root', 'completed_hours',
    'historical_verifier_schema', 'historical_validation_contract', 'outcome',
    'scratch_contents_audited', 'scratch_included_in_scientific_evidence',
    'filesystem_allocation_bound_proven', 'exact_n0_topology_verified', 'retry_authorized',
    *roster.bootstrap.FLAGS))
def test_terminal_literal_drift_is_rejected(local, field):
    local[field] = None
    with pytest.raises(ValueError):
        roster._retained_local(local, 'controller_non_authoritative', PIN)


@pytest.mark.parametrize('field', ('full_numerical_hour_replays', 'fresh_byte_context_revalidations',
    'recomputed_on_revalidation', 'scope'))
def test_nested_compatibility_metadata_is_exact(local, field):
    local['legacy_compatibility_execution_metadata'][field] = None
    with pytest.raises(ValueError):
        roster._retained_local(local, 'controller_non_authoritative', PIN)


@pytest.mark.parametrize('change', ('old_flat_counts', 'extra_receipt', 'missing_pin',
    'wrong_verifier', 'extra_nested_field'))
def test_retained_terminal_cannot_adopt_unbound_metadata(local, change):
    if change == 'old_flat_counts':
        local['full_numerical_hour_replays'] = 4
    elif change == 'extra_receipt':
        local['N0_validation_execution_receipt'] = {'complete': True}
    elif change == 'missing_pin':
        del local['audit_payload_sha256']
    elif change == 'wrong_verifier':
        local['historical_verifier_identity'] = OTHER
    else:
        local['legacy_compatibility_execution_metadata']['complete'] = True
    with pytest.raises(ValueError):
        roster._retained_local(local, 'controller_non_authoritative', PIN)


@pytest.mark.parametrize('kind', ('Bootstrap2', 'subclass', 'lookalike'))
def test_roster_rejects_nonexact_bootstrap_owner_before_resources(kind):
    if kind == 'Bootstrap2':
        owner = object.__new__(old_bootstrap.BootstrapOwner)
    elif kind == 'subclass':
        class Derived(roster.bootstrap.BootstrapOwner):
            pass
        owner = object.__new__(Derived)
    else:
        owner = SimpleNamespace()
    with pytest.raises(ValueError, match='exact live bootstrap owner'):
        roster.GroupRoster(owner, create=True, retain_head=lambda *args: None, max_record_bytes=65536)


@pytest.fixture
def reference_case(tmp_path):
    sibling = dict(ordinal=2, arm_id='test-arm', obligation_sha256=OTHER,
        obligation_node=dict(branch='synthetic'))
    study = dict(test='data-only')
    roots = {name: str(tmp_path / 'episodes' / OTHER / (name + '_non_authoritative'))
        for name in ('bootstrap', 'controller', 'owner', 'holder')}
    proposal = dict(ordinal=2, family='training_ub', slot_id=PIN, roots=roots, study=study)
    proposal_id = roster.bootstrap.digest(proposal)
    claim = dict(proposal=proposal, claim_proposal_id=proposal_id)
    pins = {name: PIN for name in roster.bootstrap.N0_PINS}
    pins['claim_proposal_id'] = proposal_id
    local = roster.bootstrap._N0_body(roots['controller'], pins)
    terminal = roster.bootstrap._global_N0_body(PIN, local)
    state = dict(claim=(PIN, claim), release=(PIN, {'kind': 'synthetic_release'}),
        local_terminal=(PIN, local), terminal=(PIN, terminal))
    owner = SimpleNamespace(study_root=tmp_path, declaration=SimpleNamespace(family='training_ub'),
        _study_binding_bytes=roster.encode(study),
        _manifest=SimpleNamespace(obligation=lambda *args: dict(obligation_node=sibling['obligation_node']),
            resolve=lambda *args: dict(kind='potential_N_slot', slot_id=PIN)))
    return owner, sibling, {PIN: state}


def test_reference_preserves_complete_retained_lineage(reference_case):
    owner, sibling, registry = reference_case
    value = roster._reference(owner, sibling, registry, PIN)
    assert value['arm_id'] == sibling['arm_id']
    assert value['local_terminal']['body'] == registry[PIN]['local_terminal'][1]
    assert value['global_terminal']['body'] == registry[PIN]['terminal'][1]
    assert value['reuse_edge'] is None


@pytest.mark.parametrize('field', ('bootstrap_terminal_head', 'bootstrap_terminal_body_sha256',
    'release_head', 'claim_head', 'slot_id', 'evidence_identity', 'outcome', 'retry_authorized'))
def test_global_terminal_binding_drift_is_rejected(reference_case, field):
    owner, sibling, registry = reference_case
    registry[PIN]['terminal'][1][field] = None
    with pytest.raises(ValueError):
        roster._reference(owner, sibling, registry, PIN)


@pytest.mark.parametrize('change', ('release_head', 'claim_proposal_id', 'foreign_ordinal',
    'foreign_roots', 'extra_global_key', 'wrong_retained_verifier'))
def test_cross_arm_and_body_correspondence_drift_is_rejected(reference_case, change):
    owner, sibling, registry = reference_case
    state = registry[PIN]
    if change == 'release_head':
        state['release'] = OTHER, state['release'][1]
    elif change == 'claim_proposal_id':
        state['claim'][1]['claim_proposal_id'] = OTHER
    elif change == 'foreign_ordinal':
        state['claim'][1]['proposal']['ordinal'] += 1
    elif change == 'foreign_roots':
        state['claim'][1]['proposal']['roots']['owner'] += '_foreign'
    elif change == 'extra_global_key':
        state['terminal'][1]['extra'] = False
    else:
        state['local_terminal'][1]['historical_verifier_identity'] = OTHER
    with pytest.raises(ValueError):
        roster._reference(owner, sibling, registry, PIN)
