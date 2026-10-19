"""One-shot observation faults must stop v3, using an explicit fake Parent."""
import pytest

from tests.test_h1_selector_phase_handoff_faults_development_v1 import (
    fault_case, context, case, setup, legacy_setup, no_solver, load)
from tests.test_h1_selector_phase_handoff_negative_development_v1 import loaded, calls_to
from tests.test_h1_selector_phase_handoff_bundle_development_v1 import actual

pytestmark = pytest.mark.parametrize('context', ['business_unresolved'], indirect=True)


@pytest.mark.parametrize('point', ['snapshot', 'sequence', 'fresh', 'preview'])
def test_one_shot_observation_error_is_not_consumed_before_original_path(fault_case, monkeypatch, point):
    f = fault_case
    parent = f.m.parent
    reference = f.ref
    # Extend only this fixture's explicitly fake interface. It has no live
    # Parent authentication or execution authority and cannot establish M2.
    reference._state = 'complete'
    terminal = parent.io.encode(dict(explicit_synthetic_parent=True))
    object.__setattr__(f.receipt, 'terminal_sha256', parent.io.digest(terminal))
    reference._issued_bytes = parent._completion_bytes(f.receipt)
    reference._records = {'terminal.json': (len(terminal), terminal, (0,) * 5)}

    def shallow(owner):
        assert owner is reference and not owner.closed and owner._state == 'complete'

    monkeypatch.setattr(parent.Parent, '_check', shallow, raising=False)
    targets = dict(snapshot=(parent.worker.snapshot, 'rebuild'), sequence=(parent.worker.sequence, 'inspect'),
        fresh=(f.m.phase, '_fresh'), preview=(f.m.preview, '_planned_bootstrap'))
    owner, name = targets[point]
    original = getattr(owner, name)
    calls = []

    def one_shot(*args, **kwargs):
        calls.append(point)
        if len(calls) == 1:
            raise OSError('one-shot negative hint observation')
        return original(*args, **kwargs)

    monkeypatch.setattr(owner, name, one_shot)
    module = loaded(parent, monkeypatch, 'negative_handoff_one_shot_unit_alias')
    with module.Handoff(f.c.owner, (reference, f.receipt), {'joint': None}, **f.options) as handoff:
        with calls_to(module) as counts:
            with pytest.raises(OSError, match='one-shot negative hint observation'):
                handoff.consume()
        assert calls == [point]
        assert counts == dict(negative=1)
        assert handoff._state == 'failed' and not handoff.root.exists() and not f.retained
        assert not reference._guard.locked() and not handoff._guard.locked()
        assert not f.c.owner._original_operation.locked() and not f.c.case.guard.locked()
        with pytest.raises(ValueError):
            handoff.consume()


def test_no_none_never_calls_negative_probe(fault_case, monkeypatch):
    f = fault_case
    pair = actual(f, 'joint')
    module = loaded(f.m.parent, monkeypatch, 'negative_handoff_no_none_unit_alias')
    try:
        with module.Handoff(f.c.owner, (f.ref, f.receipt), {'joint': pair}, **f.options) as handoff:
            with calls_to(module) as counts:
                with pytest.raises(ValueError, match='unused Actual execution'):
                    handoff.consume()
            assert counts == dict(bundle=1, prepare=1)
            assert handoff._state == 'failed' and not handoff.root.exists() and not f.retained
            assert not f.ref._guard.locked() and not pair[0]._guard.locked()
    finally:
        pair[0].close()

