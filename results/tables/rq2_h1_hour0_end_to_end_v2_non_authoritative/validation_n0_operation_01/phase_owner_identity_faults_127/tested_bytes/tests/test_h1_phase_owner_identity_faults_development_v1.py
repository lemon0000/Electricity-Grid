"""Weak-key equality aliases cannot select another owner's private capsule."""
import json
import subprocess
import sys

import pytest

from tests.test_h1_phase_dependency_window_faults_development_v1 import tiny
from tests.test_h1_phase_manifest_segment_faults_development_v1 import shared
from tests.test_h1_bootstrap_phase_segments_development_v5 import coordinator


@pytest.mark.parametrize('layer', ['dependency', 'shared'])
@pytest.mark.parametrize('hash_drift', [False, True])
def test_alias_cannot_observe_or_close_an_original_actual_handle_window(shared, monkeypatch, layer, hash_drift):
    window = shared.tiny.operation() if layer == 'dependency' else shared.operation()
    window.__enter__()
    cls = type(window)
    original_hash = hash(window)
    alias = object.__new__(cls)
    opened = shared.tiny.state['opens']
    live = set(shared.tiny.state['live'])
    assert live
    with monkeypatch.context() as mutation:
        mutation.setattr(cls, '__hash__', lambda self: original_hash + int(hash_drift))
        mutation.setattr(cls, '__eq__', lambda self, other: True)
        for name in ('receipt', 'close', 'retry_cleanup', '__enter__'):
            with pytest.raises(ValueError, match='owner identity'):
                getattr(alias, name)()
        assert shared.tiny.state['opens'] == opened and shared.tiny.state['live'] == live
        # A real hash change cannot strand genuine cleanup behind a hash lookup.
        try:window.close()
        except ValueError as error:assert 'definition-time' in str(error)
        assert not shared.tiny.state['live']
    assert window.receipt()['closed'] and not shared.tiny.state['live']


def test_private_coordinator_refuses_equal_unregistered_owner(coordinator, monkeypatch):
    c = coordinator
    c.run(c.owner, lambda: None, declaration=c.declaration)
    cls = type(c.owner)
    alias = cls()
    original_hash = hash(c.owner)
    opened = c.shared.tiny.state['opens']
    with monkeypatch.context() as mutation:
        mutation.setattr(cls, '__hash__', lambda self: original_hash)
        mutation.setattr(cls, '__eq__', lambda self, other: True)
        with pytest.raises(ValueError, match='original exact Bootstrap5 phase owner'):
            c.receipt(alias)
        with pytest.raises(ValueError, match='original exact Bootstrap5 phase owner'):
            c.run(alias, lambda: pytest.fail('aliased body must not run'))
    assert c.shared.tiny.state['opens'] == opened
    assert c.receipt(c.owner)['lifecycle_complete']


def test_actual_bootstrap5_hash_equality_drift_is_refused_before_phase_handles(tmp_path):
    # Runtime definition drift is sticky. Isolate it so later tests exercise an
    # unpoisoned genuine module; this child never creates a public owner.
    program = '''
import json
from experiments import h1_bootstrap_integration_development_v5 as m
owner = object.__new__(m.BootstrapOwner)
m.BootstrapOwner.__hash__ = lambda self: 1
m.BootstrapOwner.__eq__ = lambda self, other: True
try:
    m._phase_run(owner, lambda: (_ for _ in ()).throw(AssertionError('body ran')))
except ValueError as error:
    assert 'definition-time' in str(error)
else:
    raise AssertionError('class identity drift accepted')
value = m.phase_manifest.observation._CLEANUP_DIAGNOSTICS()
assert value['active_operations'] == value['abandoned_pending_operations'] == 0
print(json.dumps(value))
'''
    result = subprocess.run([sys.executable, '-B', '-c', program], capture_output=True,
                            text=True, timeout=20, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    observation = json.loads(result.stdout)
    assert observation['active_operations'] == observation['abandoned_pending_operations'] == 0
