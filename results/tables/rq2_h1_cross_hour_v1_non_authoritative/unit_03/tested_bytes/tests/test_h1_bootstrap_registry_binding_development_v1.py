"""Pre-attempt declaration binding; no source production or Job."""
from dataclasses import replace
from pathlib import Path

import pytest
from tests.test_h1_bootstrap_integration_development_v1 import m,example,setup,retained


@pytest.fixture
def bound(setup,tmp_path):
    source=m.registry_declaration.ROOT/'results/tables/rq2_h1_registry_declaration_v1_non_authoritative/training.declaration.json'
    raw=source.read_bytes();path=tmp_path/'registry.json';path.write_bytes(raw)
    binding=m.RegistryBinding(str(path),m.sha256(raw).hexdigest(),'training')
    return setup,replace(setup.declaration,registry_binding=binding),path


def test_binding_retained_in_study_and_foreign_replay(bound):
    s,d,path=bound;o=s.open(declaration=d)
    try:
        assert o.inspect()['registry_declaration_bound']
        assert not o.inspect()['paired_source_correspondence_verified']
        with pytest.raises(ValueError,match='producer not implemented'):o.bootstrap()
        heads=retained(o,s)
        assert o._study_binding['registry_binding']==dict(path=str(path),sha256=d.registry_binding.sha256,split='training')
        assert o._study_binding['registry_declaration']['split']=='training'
    finally:o.close()
    other=s.open(create=True,create_study=False,declaration=replace(d,ordinal=1),global_head=heads['global_head'])
    try:assert len(other._registry())==1
    finally:other.close()
    reopened=s.open(create=False,create_study=False,declaration=d,**heads)
    try:assert reopened.inspect()['state']=='claimed_pre_source'
    finally:reopened.close()


def test_invalid_pin_before_study_creation(bound):
    s,d,path=bound
    with pytest.raises(ValueError,match='external declaration pin'):
        s.open(declaration=replace(d,registry_binding=m.RegistryBinding(str(path),'a'*64,'training')))
    assert not Path(d.study_root).exists()


def test_change_after_open_before_attempt_denied(bound):
    s,d,path=bound;o=s.open(declaration=d)
    try:
        path.write_bytes(path.read_bytes()+b' ')
        with pytest.raises(ValueError,match='registry declaration changed'):o.bootstrap()
        assert not list(o._bootstrap.root.glob('[0-9]*.json'))
        assert not list(o._global.root.glob('[0-9]*.json'))
    finally:o.close()


@pytest.mark.parametrize('which',['local','global'])
def test_retention_callback_change_denied(bound,which):
    s,d,path=bound
    def retain(root,before,after):
        result=s.retain(root,before,after)
        if Path(root)==(o._bootstrap.root if which=='local' else o._global.root):
            path.write_bytes(path.read_bytes()+b' ')
        return result
    o=m.BootstrapOwner(d,create=True,create_study=True,retain_global_head=retain,retain_bootstrap_head=retain)
    try:
        with pytest.raises(ValueError,match='registry declaration changed'):o.bootstrap()
        heads=retained(o,s)
        assert len(list(o._bootstrap.root.glob('[0-9]*.json')))==1
        assert len(list(o._global.root.glob('[0-9]*.json')))==(0 if which=='local' else 1)
    finally:o.close()
    with pytest.raises(ValueError,match='external declaration pin'):
        s.open(create=False,create_study=False,declaration=d,**heads)


def test_reopen_cannot_replace_binding_path(bound,tmp_path):
    s,d,path=bound;o=s.open(declaration=d)
    try:
        with pytest.raises(ValueError,match='producer not implemented'):o.bootstrap()
        heads=retained(o,s)
    finally:o.close()
    other=tmp_path/'other.json';other.write_bytes(path.read_bytes())
    changed=replace(d,registry_binding=m.RegistryBinding(str(other),d.registry_binding.sha256,'training'))
    with pytest.raises(ValueError,match='journal declaration changed'):
        s.open(create=False,create_study=False,declaration=changed,**heads)


def test_dependency_revalidation_before_attempt(bound,monkeypatch):
    s,d,path=bound;o=s.open(declaration=d)
    try:
        def reject(*a,**k):raise ValueError('injected registry dependency drift')
        monkeypatch.setattr(m.registry_declaration,'inspect',reject)
        with pytest.raises(ValueError,match='dependency drift'):o.bootstrap()
        assert not list(o._bootstrap.root.glob('[0-9]*.json'))
    finally:o.close()


def test_wrong_obligation_split_before_creation(bound):
    s,d,path=bound
    with pytest.raises(ValueError,match='obligation split'):
        s.open(declaration=replace(d,registry_binding=replace(d.registry_binding,split='holdout')))
    assert not Path(d.study_root).exists()


@pytest.mark.parametrize('which',['local','global'])
def test_dependency_change_after_claim_stops_before_continuation(bound,monkeypatch,which):
    s,d,path=bound;original=m.registry_declaration.inspect
    def retain(root,before,after):
        result=s.retain(root,before,after)
        if Path(root)==(o._bootstrap.root if which=='local' else o._global.root):
            def reject(*a,**k):raise ValueError('post-claim dependency drift')
            monkeypatch.setattr(m.registry_declaration,'inspect',reject)
        return result
    o=m.BootstrapOwner(d,create=True,create_study=True,retain_global_head=retain,retain_bootstrap_head=retain)
    try:
        with pytest.raises(ValueError,match='post-claim dependency drift'):o.bootstrap()
        heads=retained(o,s)
        assert len(list(o._global.root.glob('[0-9]*.json')))==1
        assert not Path(o.roots['controller']).exists()
    finally:o.close()
    monkeypatch.setattr(m.registry_declaration,'inspect',original)
    reopened=s.open(create=False,create_study=False,declaration=d,**heads)
    try:
        assert reopened.inspect()['state']=='claimed_pre_source'
        with pytest.raises(ValueError,match='no automatic retry'):reopened.bootstrap()
    finally:reopened.close()
