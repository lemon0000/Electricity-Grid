"""Successor persistence regression over explicit synthetic source/Parent seams.

Reuse predecessor fault schedules, but instantiate v2 genesis and handoff.
No N0, selector Job, native result, or full-chain success is claimed here.
"""
import pytest

from experiments import h1_common_owner_genesis_development_v2 as genesis
from experiments import h1_selector_input_snapshot_development_v2 as snapshot
from experiments import h1_selector_phase_handoff_development_v2 as handoff
from tests import test_h1_common_owner_genesis_development_v1 as genesis_cases
from tests import test_h1_selector_input_snapshot_development_v1 as snapshot_cases
from tests import test_h1_selector_phase_handoff_faults_development_v1 as fault_cases
from tests.test_h1_selector_phase_handoff_faults_development_v1 import (
    setup,legacy_setup,no_solver,
    test_durable_write_windows_keep_exact_prefix_and_release_leases,
    test_external_retention_failure_never_retries_or_fills_missing_bytes,
    test_outer_file_failure_preserves_live_predecessor,
    test_predecessor_close_failure_releases_original_leases,
    test_reopen_failure_keeps_empty_prefix_and_releases_owned_handles)
from tests.test_h1_selector_phase_handoff_integrity_development_v1 import (
    test_wrong_retention_acknowledgement_rejects_exact_stage,
    test_same_bytes_phase_replacement_between_close_and_reopen_rejected)

pytestmark=pytest.mark.parametrize('context',['business_unresolved'],indirect=True)


@pytest.fixture
def case(setup,tmp_path,monkeypatch):
    monkeypatch.setattr(genesis_cases,'m',genesis)
    return genesis_cases.case.__wrapped__(setup,tmp_path,monkeypatch)


@pytest.fixture
def context(case,setup,monkeypatch,no_solver,request):
    monkeypatch.setattr(snapshot_cases,'m',snapshot)
    yield from snapshot_cases.context.__wrapped__(case,setup,monkeypatch,no_solver,request)


@pytest.fixture
def fault_case(context,monkeypatch,tmp_path):
    monkeypatch.setattr(fault_cases,'canonical',handoff)
    original=fault_cases.load
    def routed(file,name,patch,dependencies=None):
        if dependencies:
            dependencies={key.replace('h1_selector_parent_controller_development_v1',
                'h1_selector_parent_controller_development_v2'):value for key,value in dependencies.items()}
        return original(file,name,patch,dependencies)
    monkeypatch.setattr(fault_cases,'load',routed)
    fixture=fault_cases.fault_case.__wrapped__(context,monkeypatch,tmp_path)
    item=next(fixture)
    try:
        assert item.m.common is genesis and item.m.snapshot is snapshot
        assert item.m.SCHEMA=='h1_selector_phase_handoff_development_v2'
        assert type(context.owner) is genesis.CommonOwnerGenesis
        yield item
    finally:fixture.close()
