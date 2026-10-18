"""Real project graph and Windows lease: static identity versus live membership."""
from pathlib import Path
import os
from types import SimpleNamespace

import pytest

from experiments import h1_historical_n0_verifier_development_v3 as m


pytestmark = pytest.mark.skipif(os.name != 'nt', reason='actual Windows store leases')


def test_real_owner_lease_membership_can_change_between_operations(tmp_path):
    store = m.lease_store
    before = set(store._REGISTRY)
    m._runtime_check(True)
    first = store._Lease(tmp_path / 'first_non_authoritative', True)
    second = None
    try:
        first.check()
        assert store._REGISTRY == before | {first.key}
        m._runtime_check(True)
        second = store._Lease(tmp_path / 'second_non_authoritative', True)
        second.check()
        assert store._REGISTRY == before | {first.key, second.key}
        m._runtime_check(True)
        with pytest.raises(ValueError, match='already held'):
            store._Lease(first.root, False)
    finally:
        if second is not None:
            second.close()
        first.close()
    assert store._REGISTRY == before
    m._runtime_check(True)
    for root in (first.root, second.root):
        lease = store._Lease(root, False)
        lease.check()
        lease.close()


@pytest.mark.parametrize('field', ['_REGISTRY', '_REGISTRY_LOCK'])
def test_definition_guard_rejects_store_object_rebinding(monkeypatch, field):
    before = getattr(m.lease_store, field)
    monkeypatch.setattr(m.lease_store, field, set(before) if field == '_REGISTRY' else object())
    with pytest.raises(ValueError, match='store registry object or lock'):
        m._runtime_check(True)


def test_unchanged_hour_context_still_rejects_membership_drift(tmp_path):
    scope = m.prior_witness._HourScope(tmp_path,
        tuple(SimpleNamespace(check=lambda: None) for _ in range(4)), caller=m)
    member = str(tmp_path / 'foreign_non_authoritative')
    try:
        with m.lease_store._REGISTRY_LOCK:
            m.lease_store._REGISTRY.add(member)
        # The static definition guard allows changing membership, but the
        # original numerical context rejects drift before any result is reused.
        m._runtime_check(True)
        with m.hour.prior.guard.solver_calls_forbidden():
            with pytest.raises(ValueError, match='dispatch or source changed'):
                scope._context(None, None, None, None, {})
    finally:
        with m.lease_store._REGISTRY_LOCK:
            m.lease_store._REGISTRY.discard(member)
        scope.close()


def test_original_lease_identity_failure_is_preserved(tmp_path):
    lease = m.lease_store._Lease(tmp_path / 'closed_non_authoritative', True)
    lease.close()
    with pytest.raises(ValueError, match='live same-process'):
        lease.check()
