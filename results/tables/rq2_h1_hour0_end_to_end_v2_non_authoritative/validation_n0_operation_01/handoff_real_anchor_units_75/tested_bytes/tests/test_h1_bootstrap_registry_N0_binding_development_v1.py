"""Bound declaration survives N0 protocol replay; fake numerical core, zero Job."""
from dataclasses import replace

from tests.test_h1_bootstrap_integration_development_v1 import m,example,setup,retained
from tests.test_h1_bootstrap_N0_registration_development_v1 import protocol


def test_bound_N0_terminal_reopen_and_foreign_replay(protocol,tmp_path):
    s,d=protocol
    source=m.registry_declaration.ROOT/'results/tables/rq2_h1_registry_declaration_v1_non_authoritative/training.declaration.json'
    raw=source.read_bytes();path=tmp_path/'registry.json';path.write_bytes(raw)
    d=replace(d,registry_binding=m.RegistryBinding(str(path),m.sha256(raw).hexdigest(),'training'))
    o=s.open(declaration=d)
    try:
        assert o.bootstrap()['state']=='pending_post_N'
        info=o.inspect()
        assert info['registry_declaration_bound'] and info['N0_numerical_evidence_audited']
        assert not info['paired_source_correspondence_verified'] and not info['retry_authorized']
        heads=retained(o,s)
    finally:o.close()
    reopened=s.open(create=False,create_study=False,declaration=d,**heads)
    try:assert reopened.inspect()['state']=='pending_post_N'
    finally:reopened.close()
    other=s.open(create=True,create_study=False,declaration=replace(d,ordinal=1),global_head=heads['global_head'])
    try:
        registry=other._registry()
        assert len(registry)==1 and next(iter(registry.values()))['terminal'] is not None
        assert other.inspect()['registry_declaration_bound']
    finally:other.close()
