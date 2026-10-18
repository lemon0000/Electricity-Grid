"""Complete negative disposition matrix with explicit fake Parents, no execution evidence."""
import json

import pytest

from tests.test_h1_selector_phase_handoff_negative_development_v1 import (
    setup, case, legacy_setup, context, no_solver, load, loaded)
from tests.test_h1_selector_phase_handoff_faults_development_v1 import fault_case
from tests.test_h1_selector_phase_handoff_bundle_development_v1 import actual


def rich_reference(f, monkeypatch):
    parent = f.m.parent
    reference = f.ref
    reference._state = 'complete'
    terminal = parent.io.encode(dict(explicit_synthetic_parent=True))
    object.__setattr__(f.receipt, 'terminal_sha256', parent.io.digest(terminal))
    reference._issued_bytes = parent._completion_bytes(f.receipt)
    reference._records = {'terminal.json': (len(terminal), terminal, (0,) * 5)}
    def shallow(owner):
        assert owner is reference and not owner.closed and owner._state == 'complete'
    monkeypatch.setattr(parent.Parent, '_check', shallow, raising=False)
    return loaded(parent, monkeypatch, 'negative_handoff_complete_matrix_unit_alias')


@pytest.mark.parametrize('missing', ['all', 'joint', 'second', 'third'])
def test_every_missing_disposition_rejects_without_common_or_persistence(fault_case, monkeypatch, missing):
    f = fault_case
    module = rich_reference(f, monkeypatch)
    lanes = tuple(lane.lane_id for lane in f.c.owner._manifest.lanes)
    assert lanes == ('joint', 'second', 'third')
    # The other lanes are structural fake pairs, not accepted execution. The
    # negative predicate cannot authenticate any of them or issue a credential.
    pairs = {lane: actual(f, lane) for lane in lanes}
    partial = {lane: None if missing in ('all', lane) else pairs[lane] for lane in lanes}
    before = len(f.c.case.common_prepare_calls)
    try:
        with module.Handoff(f.c.owner, (f.ref, f.receipt), partial, **f.options) as owner:
            with pytest.raises(ValueError, match='Actual execution missing or failed'):
                owner.consume()
            assert len(f.c.case.common_prepare_calls) == before
            assert owner._state == 'failed' and not owner.root.exists() and not f.retained
            assert not owner._guard.locked() and not f.ref._guard.locked()
            assert all(not pair[0]._guard.locked() and not pair[0]._reference_held for pair in pairs.values())
            assert not f.c.owner._original_operation.locked() and not f.c.case.guard.locked()
            with pytest.raises(ValueError):
                owner.consume()
    finally:
        for parent, _ in pairs.values():
            parent.close()


@pytest.mark.parametrize('context', ['business_input_unresolved', 'business_unresolved'], indirect=True)
def test_both_legitimate_none_dispositions_keep_original_complete_path(fault_case, monkeypatch):
    f = fault_case
    module = rich_reference(f, monkeypatch)
    with module.Handoff(f.c.owner, (f.ref, f.receipt), {'joint': None}, **f.options) as owner:
        before = len(f.c.case.common_prepare_calls)
        result = owner.consume()
        assert len(f.c.case.common_prepare_calls) > before
        assert result['completed_hours'] == 1
        lane, = json.loads(owner._plan.projection)['lanes']
        assert lane['status'] in ('business_input_unresolved', 'business_unresolved')
        assert all(result[key] is False for key in module.FLAGS)
