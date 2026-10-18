"""Selector declaration bound to real journals; no selector execution."""
from dataclasses import replace
from pathlib import Path

import pytest

from tests.test_h1_bootstrap_integration_development_v1 import (
    m, example, setup, retained, enable_post_claim,
)
from tests.test_h1_selector_configuration_development_v1 import configuration, no_execution
from tests.test_h1_bootstrap_N0_registration_development_v1 import protocol


def bound(d):
    n=d.run_configuration
    uids=tuple(uid for kind,uid in n.stage_order if kind=='generation')
    return replace(d,selector_configuration=configuration(uids,n.network_sha256))


def test_claim_and_foreign_reopen_bind_selector_configuration(setup):
    s=setup;d=bound(s.declaration);o=s.open(declaration=d)
    try:
        info=o.inspect()
        assert info['selector_configuration_bound'] and not info['selector_producer_connected']
        with pytest.raises(ValueError,match='producer not implemented'):o.bootstrap()
        heads=retained(o,s)
        assert o._study_binding['selector_configuration']==d.selector_configuration.binding()
    finally:o.close()
    other=s.open(create=True,create_study=False,declaration=replace(d,ordinal=1),global_head=heads['global_head'])
    try:assert len(other._registry())==1
    finally:other.close()
    reopened=s.open(create=False,create_study=False,declaration=d,**heads)
    try:assert reopened.inspect()['state']=='claimed_pre_source'
    finally:reopened.close()
    changed=replace(d,selector_configuration=replace(d.selector_configuration,reference_non_solver_seconds=1))
    with pytest.raises(ValueError,match='journal declaration changed'):
        s.open(create=False,create_study=False,declaration=changed,**heads)


@pytest.mark.parametrize('change',['network','uid','missing_N','type'])
def test_mismatch_before_study_creation(setup,change):
    s=setup;d=bound(s.declaration);c=d.selector_configuration
    with pytest.raises(ValueError):
        if change=='network':d=replace(d,selector_configuration=replace(c,network_sha256='b'*64))
        elif change=='uid':d=replace(d,selector_configuration=replace(c,generation_uids=('other',)))
        elif change=='missing_N':d=replace(d,run_configuration=None)
        else:d=replace(d,selector_configuration=vars(c))
        s.open(declaration=d)
    assert not Path(s.declaration.study_root).exists()


@pytest.mark.parametrize('where',['before_attempt','local_retention','global_retention'])
def test_mutation_stops_before_scientific_source_entry(setup,where):
    s=setup;d=bound(s.declaration)
    def mutate():object.__setattr__(d.selector_configuration,'reference_non_solver_seconds',1)
    def retain(root,before,after):
        result=s.retain(root,before,after)
        if Path(root)==(o._bootstrap.root if where=='local_retention' else o._global.root):mutate()
        return result
    o=m.BootstrapOwner(d,create=True,create_study=True,retain_global_head=retain,retain_bootstrap_head=retain)
    try:
        if where=='before_attempt':mutate()
        with pytest.raises(ValueError,match='configuration changed'):o.bootstrap()
        assert len(list(o._bootstrap.root.glob('[0-9]*.json')))==(0 if where=='before_attempt' else 1)
        assert len(list(o._global.root.glob('[0-9]*.json')))==(1 if where=='global_retention' else 0)
        assert not Path(o.roots['controller']).exists()
    finally:o.close()


def test_actual_static_inventory_revalidated_after_retained_claim(setup,monkeypatch):
    s=setup;d,events=enable_post_claim(s,monkeypatch);d=bound(d)
    original=m.selector_config.SelectorRunConfiguration.validate_normal;seen=[]
    def check(self,network,order):
        original(self,network,order)
        if events and events[-1]=='static_load' and order is not d.run_configuration.stage_order:
            seen.append(tuple(uid for k,uid in order if k=='generation'))
    monkeypatch.setattr(m.selector_config.SelectorRunConfiguration,'validate_normal',check)
    o=s.open(declaration=d)
    try:
        with pytest.raises(ValueError,match='release/capability entry not implemented'):o.bootstrap()
        assert seen and all(uids==d.selector_configuration.generation_uids for uids in seen)
        assert events==['manifest','static_load','manifest']
    finally:o.close()


def test_loaded_uid_mismatch_retains_attempt_before_controller(setup,monkeypatch):
    s=setup;n=s.declaration.run_configuration
    wrong=tuple((kind, None if uid is None else uid+'_other') for kind,uid in n.stage_order)
    d,events=enable_post_claim(s,monkeypatch,config=replace(n,stage_order=wrong));d=bound(d)
    controllers=[]
    def denied(*a,**k):
        controllers.append(True);raise AssertionError('mismatched inventory reached controller')
    monkeypatch.setattr(m._BootstrapController,'__init__',denied)
    o=s.open(declaration=d)
    try:
        with pytest.raises(ValueError,match='loaded network/DC/stage profile differs'):o.bootstrap()
        assert events==['manifest','static_load'] and controllers==[]
        assert not Path(o.roots['controller']).exists()
        assert len(list(o._global.root.glob('[0-9]*.json')))==1
        assert len(list(o._bootstrap.root.glob('[0-9]*.json')))==2
        heads=retained(o,s)
    finally:o.close()
    reopened=s.open(create=False,create_study=False,declaration=d,**heads)
    try:
        assert reopened.inspect()['state']=='pre_release_unresolved'
        with pytest.raises(ValueError,match='no automatic retry'):reopened.bootstrap()
    finally:reopened.close()


def test_bound_N0_protocol_compatibility(protocol):
    # Explicitly fake numerical core from the existing protocol fixture.
    # This tests journal reconstruction, not native/scientific acceptance.
    s,d=protocol;d=bound(d);o=s.open(declaration=d)
    try:
        assert o.bootstrap()['state']=='pending_post_N'
        heads=retained(o,s)
        assert o.inspect()['selector_configuration_bound']
        assert not o.inspect()['selector_producer_connected']
    finally:o.close()
    reopened=s.open(create=False,create_study=False,declaration=d,**heads)
    try:assert reopened.inspect()['state']=='pending_post_N'
    finally:reopened.close()
    other=s.open(create=True,create_study=False,declaration=replace(d,ordinal=1),global_head=heads['global_head'])
    try:assert next(iter(other._registry().values()))['terminal'] is not None
    finally:other.close()
