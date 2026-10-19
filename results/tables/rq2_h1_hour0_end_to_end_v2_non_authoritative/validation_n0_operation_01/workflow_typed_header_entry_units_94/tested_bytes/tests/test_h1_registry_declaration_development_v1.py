import json

import pytest
from experiments import h1_registry_declaration_development_v1 as m


@pytest.fixture(scope='module')
def training(): return m.build('training')


def test_metadata_only_and_split_binding(monkeypatch,training):
    def reject(*a,**kw):raise AssertionError('semantic source reader forbidden')
    monkeypatch.setattr(m.registry,'_load',reject)
    monkeypatch.setattr(m.registry.gzip,'decompress',reject)
    holdout=json.loads(m.build('holdout')); train=json.loads(training)
    assert holdout['expected_registry_identity']==train['expected_registry_identity']
    assert holdout['selected_archive_member']!=train['selected_archive_member']
    assert holdout['split']=='holdout' and train['split']=='training'
    assert not holdout['source_window_validated']
    assert not holdout['native_execution_authorized']


def test_correspondence_to_existing_registry(training):
    # Selected training only: compare static derivation with the established loader.
    context=m.registry._load('training')
    d=json.loads(training)
    assert d['expected_registry_identity']==context['identity']
    assert d['selected_archive_member']['sha256']==context['archive_member_sha256']
    assert d['registry_identity_basis']['cap_table']==context['cap_table_sha256']


def test_retained_roundtrip_and_wrong_split(tmp_path,training):
    path=tmp_path/'declaration.json';path.write_bytes(training)
    result=m.inspect(path,expected_sha256=m.io.digest(training),split='training')
    assert result==json.loads(training)
    with pytest.raises(ValueError,match='reconstruction'):
        m.inspect(path,expected_sha256=m.io.digest(training),split='holdout')


def test_forged_matching_external_pin_rejected(tmp_path,training):
    body=json.loads(training);body['expected_registry_identity']='a'*64
    raw=m.io.encode(body);path=tmp_path/'forged.json';path.write_bytes(raw)
    with pytest.raises(ValueError,match='reconstruction'):
        m.inspect(path,expected_sha256=m.io.digest(raw),split='training')
    with pytest.raises(ValueError,match='external declaration pin'):
        m.inspect(path,expected_sha256='b'*64,split='training')


@pytest.mark.parametrize('split',[None,True,'all','Training'])
def test_invalid_split(split):
    with pytest.raises(ValueError,match='split'):m.build(split)


def test_final_dependency_bookend(monkeypatch):
    original=m.io.read_stable; own=m.Path(m.__file__);count=0
    def change(path,cap):
        nonlocal count
        view=original(path,cap)
        if path==own:
            count+=1
            if count>1:return (view[0]+b' ',view[1])
        return view
    monkeypatch.setattr(m.io,'read_stable',change)
    with pytest.raises(ValueError,match='dependency changed'):m.build('training')


def test_declaration_mutation_during_inspect(tmp_path,training,monkeypatch):
    path=tmp_path/'declaration.json';path.write_bytes(training)
    original=m.build
    def changed(split):
        raw=original(split);path.write_bytes(raw+b' ');return raw
    monkeypatch.setattr(m,'build',changed)
    with pytest.raises(ValueError,match='changed during inspect'):
        m.inspect(path,expected_sha256=m.io.digest(training),split='training')
