"""Successor dependency parity, live type separation and drift refusal; no Jobs."""
import importlib
import json
import sys

import pytest

from experiments import h1_phase_manifest_binding_development_v2 as manifest
from experiments import h1_bootstrap_integration_development_v2 as bootstrap
from experiments import h1_selector_phase_handoff_development_v1 as old_handoff
from experiments import h1_selector_phase_handoff_development_v2 as new_handoff
from tests.test_h1_selector_configuration_development_v1 import configuration


@pytest.mark.parametrize('ordinal',[0,11832353])
def test_actual_coordinate_full_group_and_compact_evidence(ordinal):
    c=configuration();a=manifest.ArchiveCapacityDeclaration(576,2**20,576*2**20,0)
    calls=[];code=manifest.verifier.prepare_group.__code__
    def observe(frame,event,arg):
        if event=='call' and frame.f_code is code:
            calls.append((frame.f_locals['family'],frame.f_locals['ordinal']))
    sys.setprofile(observe)
    try:prepared=manifest.prepare('training_ub',ordinal,c,a)
    finally:sys.setprofile(None)
    assert calls==[('training_ub',ordinal)]*2
    audit=json.loads(prepared.audit_payload)
    fresh=manifest.verifier.prepare_group('training_ub',ordinal)
    assert audit['group']==fresh['predecessor_group']
    assert audit['dependency_verifier']==manifest._verifier_evidence(fresh)
    assert audit['group']==manifest.group.prepare('training_ub',ordinal)
    assert audit['schema']==manifest.SCHEMA and all(audit[k] is False for k in (
        'formal_result','formal_execution_ready','native_execution_authorized','resource_admission'))
    fp=bootstrap._phase_input_fingerprint(c)
    assert fp==(audit['group']['implementation_sha256'],audit['implementation_sha256'],
        audit['dependency_verifier']['verifier_implementation_sha256'],
        audit['dependency_verifier']['dependency_inventory_sha256'])


def test_fingerprint_rejects_changed_implementation_at_return(monkeypatch):
    original=manifest._implementation;calls=[]
    def changing(c):
        calls.append(True)
        return original(c) if len(calls)==1 else '0'*64
    monkeypatch.setattr(manifest,'_implementation',changing)
    with pytest.raises(ValueError,match='changed during fingerprint'):
        bootstrap._phase_input_fingerprint(configuration())


def test_fingerprint_rejects_replaced_verifier_before_call(monkeypatch):
    def forged(*args):raise AssertionError('forged verifier must not be called')
    monkeypatch.setattr(manifest.verifier,'prepare_group',forged)
    with pytest.raises(ValueError,match='helper identity changed'):
        bootstrap._phase_input_fingerprint(configuration())


@pytest.mark.parametrize('version,foreign',[(1,2),(2,1)])
def test_cross_generation_owners_rejected_before_use(tmp_path,version,foreign):
    def module(name,v):return importlib.import_module(f'experiments.h1_{name}_development_v{v}')
    other=module('bootstrap_integration',foreign).BootstrapOwner.__new__(module('bootstrap_integration',foreign).BootstrapOwner)
    with pytest.raises(ValueError,match='exact live bootstrap'):
        module('group_execution_roster',version).GroupRoster(other,create=True,retain_head=lambda *a:None,max_record_bytes=65536)
    with pytest.raises(ValueError,match='fresh owned'):
        module('owned_bootstrap_controller',version).OwnedController(other,None)
    foreign_genesis=module('common_owner_genesis',foreign).CommonOwnerGenesis
    empty=foreign_genesis.__new__(foreign_genesis)
    with pytest.raises(ValueError,match='exact live common owner'):
        module('selector_input_snapshot',version).capture_reference(empty,configuration(),max_archive_bytes=2**30)
    with pytest.raises(TypeError,match='exact live common genesis'):
        module('selector_phase_handoff',version).Handoff(empty,None,{},retain_head=lambda *a:None,
            max_packet_bytes=2**20,max_record_bytes=65536,max_archive_bytes=2**24)
    assert not list(tmp_path.iterdir())


def test_v2_worker_launch_and_runtime_closure():
    from experiments import h1_selector_parent_controller_development_v2 as parent
    from experiments import h1_selector_phase_handoff_development_v2 as handoff
    worker=parent.worker
    assert parent.lifecycle.worker is worker is parent.inspection.worker is parent.preparation.worker
    assert worker.snapshot.common is handoff.common
    assert handoff.common.bootstrap is bootstrap
    assert 'h1_selector_released_worker_development_v2' in parent.preparation._SCRIPT
    assert 'h1_selector_released_worker_development_v1' not in parent.preparation._SCRIPT


def test_N0_route_rejects_replaced_historical_verifier(tmp_path,monkeypatch):
    def forged(*a,**k):raise AssertionError('forged verifier must not be called')
    monkeypatch.setattr(bootstrap.historical_verifier,'prepare',forged)
    with pytest.raises(ValueError,match='verifier dispatch changed'):
        bootstrap._prepare_N0(tmp_path,expected_binding_sha256='a'*64,
            expected_terminal_sha256='b'*64,completed_hours=1)


def test_N0_terminal_binds_distinct_verifier_identity_and_work():
    pins={key:'a'*64 for key in bootstrap.N0_PINS}
    pins['historical_verifier_identity']='b'*64
    body=bootstrap._N0_body('test-only-root',pins)
    assert body['historical_implementation']=='a'*64
    assert body['historical_verifier_identity']=='b'*64
    assert body['historical_verifier_schema']==bootstrap.historical_verifier.VERIFIER_SCHEMA
    assert (body['full_numerical_hour_replays'],body['fresh_byte_context_revalidations'])==(4,4)
    assert body['recomputed_on_revalidation'] is False
    assert parent.lifecycle.INSPECTION_SCHEMA.endswith('_v2')
