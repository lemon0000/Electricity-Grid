"""Owned bootstrap execution gates; synthetic inputs only."""
from pathlib import Path
from copy import deepcopy
from threading import Lock
from types import SimpleNamespace

import pytest

from tests.test_h1_bootstrap_integration_development_v1 import (
    m, example, setup, enable_post_claim, retained,
)

owned = m.owned


def enable_owned(s, monkeypatch):
    declaration, events = enable_post_claim(s, monkeypatch)
    monkeypatch.setattr(m.BootstrapOwner, '_continue_bootstrap', m.BootstrapOwner._continue_owned_development)
    captured = []
    original = owned.OwnedController.__init__
    def capture(self, *args):
        original(self, *args)
        captured.append(self)
    monkeypatch.setattr(owned.OwnedController, '__init__', capture)
    def no_child(*a, **k):
        raise AssertionError('unexpected Job creation in zero-Job gate test')
    monkeypatch.setattr(owned.old.process, 'normal_task_child', no_child)
    return declaration, events, captured


def tree(root):
    return {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*')
        if p.is_file() and p.name != 'execution.lock'}


def assert_legacy_denied(controller):
    base, bridge, phase = owned.base, owned.bridge, owned.phase
    before = tree(controller._owned_lease.root)
    step_args = dict(expected_source_identity='0'*64, expected_head='0'*64)
    calls = [
        lambda:base.Controller.step(controller, **step_args),
        lambda:bridge.Controller.step(controller, **step_args),
        lambda:phase.Controller._step_development(controller, **step_args),
        lambda:phase.Controller.step(controller, **step_args),
        lambda:base.Controller._job(controller, 0, None, {}, '0'*64),
        lambda:bridge.Controller._job(controller, 0, None, {}, '0'*64),
        lambda:phase.Controller._job(controller, 0, None, {}, '0'*64),
        lambda:bridge.Controller._headroom(controller),
        lambda:phase.Controller._headroom(controller),
        lambda:base.Controller.inspect(controller),
        lambda:bridge.Controller.inspect(controller),
        lambda:phase.Controller.inspect(controller),
        lambda:base.Controller.close(controller),
        lambda:bridge.Controller.close(controller),
        lambda:phase.Controller.close(controller),
        lambda:controller.close(),
    ]
    for call in calls:
        with pytest.raises((ValueError, AttributeError)):
            call()
        assert controller._lease is None
        assert tree(controller._owned_lease.root) == before


def test_owned_release_headroom_source_order_and_legacy_bypass(setup, monkeypatch):
    s = setup
    declaration, _, captured = enable_owned(s, monkeypatch)
    order = []
    def retain(root, before, after):
        if captured:
            assert_legacy_denied(captured[0])
            order.append('global' if root.name == 'global_claims_non_authoritative' else
                'ready' if len(order) == 0 else 'local')
        return s.retain(root, before, after)
    def headroom(self):
        self._owned_check()
        assert_legacy_denied(self)
        assert len(self._owned_owner._global.rows()) == 2
        order.append('headroom')
    def source(*a, **k):
        order.append('current')
        raise ValueError('test-only first-current stop')
    monkeypatch.setattr(owned.OwnedController, '_owned_headroom', headroom)
    monkeypatch.setattr(owned.binding.source_binding, 'load_pinned_current', source)
    o = m.BootstrapOwner(declaration, create=True, create_study=True,
        retain_global_head=retain, retain_bootstrap_head=retain)
    try:
        with pytest.raises(ValueError, match='first-current stop'):
            o.bootstrap()
        heads = retained(o, s)
        assert order == ['ready', 'local', 'global', 'headroom', 'current']
        assert o._controller is None and o._original_controller is None
        assert captured[0]._owned_lease is None and captured[0]._owned_scope is None
        assert not list(Path(o.roots['controller']).glob('job_*'))
        with pytest.raises(ValueError):
            captured[0]._owned_run()
    finally:
        o.close()
    reopened = s.open(create=False, create_study=False, declaration=declaration, **heads)
    try:
        assert reopened.inspect()['state'] == 'execution_indeterminate'
        assert reopened.inspect()['execution_artifacts_audited'] is False
    finally:
        reopened.close()


@pytest.mark.parametrize('fault', ['nonce', 'global_head', 'lease', 'lock_bytes', 'cleanup', 'original_cleanup'])
def test_owned_fault_before_first_current_preserves_indeterminate(setup, monkeypatch, fault):
    s = setup
    declaration, _, captured = enable_owned(s, monkeypatch)
    reads = []
    def source(*a, **k):
        reads.append(1)
        raise AssertionError('source reached after owned binding fault')
    def headroom(self):
        self._owned_check()
        if fault == 'nonce': self._owned_owner._operation_nonce = object()
        elif fault == 'global_head': self._owned_owner._global.head = '0'*64
        elif fault == 'lease': self._clock_lease, self._obligation_lease = self._obligation_lease, self._clock_lease
        elif fault == 'cleanup': self._owned_cleanup_leases = ()
        elif fault == 'original_cleanup': self._owned_original_cleanup = self._owned_original_cleanup[1:]
        else:
            stream = self._owned_lease.stream
            stream.seek(0); stream.write(b'1'); stream.flush()
    monkeypatch.setattr(owned.OwnedController, '_owned_headroom', headroom)
    monkeypatch.setattr(owned.binding.source_binding, 'load_pinned_current', source)
    o = s.open(declaration=declaration)
    try:
        with pytest.raises(ValueError): o.bootstrap()
        assert reads == []
        assert captured[0]._owned_scope is None and captured[0]._owned_lease is None
        assert len(captured[0]._owned_leases) == 6
        assert all(x.stream is None and not x.locked for x in captured[0]._owned_leases)
        assert not list(Path(o.roots['controller']).glob('job_*'))
    finally:
        o.close()


def test_owned_rejects_hand_constructed_current_observation(setup, monkeypatch):
    declaration, _, _ = enable_owned(setup, monkeypatch)
    monkeypatch.setattr(owned.OwnedController, '_owned_headroom', lambda self:self._owned_check())
    monkeypatch.setattr(owned.binding.source_binding, 'load_pinned_current', lambda *a, **k:SimpleNamespace())
    o = setup.open(declaration=declaration)
    try:
        with pytest.raises(ValueError, match='pinned current'): o.bootstrap()
        assert not list(Path(o.roots['controller']).glob('job_*'))
    finally:
        o.close()


def test_owned_cursor_network_and_lease_metadata_bound_before_source(setup, monkeypatch):
    declaration, _, _ = enable_owned(setup, monkeypatch)
    def headroom(self):
        self._owned_check()
        changes = [
            (self, '_clock_index', 1), (self, '_clock_previous', '0'*64),
            (self, '_clock_index', False), (self, '_clock_hours', 192.),
            (self, '_clock_start', float(self._clock_start)),
            (self, '_obligation_previous', '0'*64), (self, 'binding_pin', '0'*64),
            (self, 'obligation_binding_pin', '0'*64), (self, '_clock_hours', 191),
            (self, '_clock_start', self._clock_start+1), (self, 'clock_root', self.clock_root.parent),
            (self, 'obligation_root', self.obligation_root.parent), (self, '_clock_guard', Lock()),
            (self._owned_owner, '_network', deepcopy(self._owned_network)),
        ]
        for lease in self._owned_leases:
            changes.extend([(lease, 'root', lease.root.parent), (lease, 'file_identity', (0,0)),
                (lease, 'root_identity', (0,0)), (lease, 'key', 'different')])
        for target, name, value in changes:
            before = getattr(target, name)
            setattr(target, name, value)
            try:
                with pytest.raises(ValueError, match='live binding'): self._owned_check()
            finally:
                setattr(target, name, before)
        self._owned_check()
        raise ValueError('test-only state mutation checks complete')
    monkeypatch.setattr(owned.OwnedController, '_owned_headroom', headroom)
    o = setup.open(declaration=declaration)
    try:
        with pytest.raises(ValueError, match='state mutation checks complete'): o.bootstrap()
        assert not list(Path(o.roots['controller']).glob('job_*'))
    finally:
        o.close()


def test_owned_constructor_tail_failure_closes_all_original_leases(setup, monkeypatch):
    declaration, _, _ = enable_owned(setup, monkeypatch)
    captured = []
    def fail(self):
        captured.extend(self._owned_cleanup_leases)
        raise ValueError('test-only constructor tail failure')
    monkeypatch.setattr(owned.OwnedController, '_leases', fail)
    o = setup.open(declaration=declaration)
    try:
        with pytest.raises(ValueError, match='constructor tail failure'): o.bootstrap()
        assert len(captured) == 6
        assert all(x.stream is None and not x.locked for x in captured)
        assert not list(Path(o.roots['controller']).glob('job_*'))
    finally:
        o.close()
