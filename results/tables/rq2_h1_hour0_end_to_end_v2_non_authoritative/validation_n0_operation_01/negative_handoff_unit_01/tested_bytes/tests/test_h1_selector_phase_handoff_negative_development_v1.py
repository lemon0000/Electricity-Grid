"""v3 negative-only route; synthetic source/native/Job seams are explicit."""
from collections import Counter
from contextlib import ExitStack, contextmanager
from dataclasses import replace
from fractions import Fraction
import json
import sys

import pytest

from experiments import h1_selector_phase_handoff_development_v3 as candidate
from experiments import h1_selector_phase_handoff_development_v1 as prior
from tests.test_h1_selector_parent_controller_development_v1 import (
    harness, context, case, setup as base_setup, legacy_setup, sequence_factory, no_solver, load)
from tests.test_h1_selector_phase_handoff_development_v1 import options


@pytest.fixture
def setup(base_setup, request):
    s = base_setup
    kind = getattr(request.node, 'callspec', None)
    kind = None if kind is None else kind.params.get('context')
    lane = s.manifest.lanes[0]
    if kind == 'business_input_unresolved':
        lane = replace(lane, mechanism=replace(lane.mechanism, flexible_fraction=Fraction(1, 21)))
        s.manifest = replace(s.manifest, lanes=(lane,))
    elif kind != 'business_unresolved':
        s.manifest = replace(s.manifest, lanes=(lane, replace(lane, lane_id='second'), replace(lane, lane_id='third')))
    return s


def loaded(parent, monkeypatch, label):
    # Explicit unit aliases; canonical runtime v3 keeps all v2 dependencies.
    return load(candidate.__file__, label, monkeypatch, dict(
        h1_selector_parent_controller_development_v2=parent,
        h1_common_owner_genesis_development_v2=prior.common,
        h1_selector_phase_consumption_development_v2=prior.preview))


@contextmanager
def calls_to(module):
    codes = {module._negative_missing_actual.__code__: 'negative',
        module._Bundle.enter.__code__: 'bundle', module.Handoff._prepare.__code__: 'prepare'}
    counts = Counter()
    original = sys.getprofile()
    assert original is None

    def observe(frame, event, arg):
        if event == 'call' and frame.f_code in codes:
            counts[codes[frame.f_code]] += 1

    sys.setprofile(observe)
    try:
        yield counts
    finally:
        sys.setprofile(original)


def test_missing_all_and_each_actual_reject_early_then_same_v3_commits_and_reopens(harness, monkeypatch):
    h = harness
    p, c = h.module, h.context
    m = loaded(p, monkeypatch, 'negative_handoff_three_actual_unit_alias')
    retained = []
    with ExitStack() as stack:
        reference = stack.enter_context(p.Parent(h.root, h.raw, **h.options))
        ref = reference.run()
        actuals = {}
        for lane in ('joint', 'second', 'third'):
            raw = p.worker.snapshot.capture_actual(c.owner, c.config, max_archive_bytes=c.cap, lane_id=lane,
                reference_root=ref.scientific_root, reference_terminal_sha256=ref.scientific_terminal_sha256,
                reference_request_sha256=ref.scientific_request_sha256, reference_max_archive_bytes=ref.max_archive_bytes)
            actual = stack.enter_context(p.Parent(h.root.parent / (lane + '_actual_non_authoritative'), raw,
                **h.options, reference_owner=reference, reference_completion=ref))
            actuals[lane] = actual, actual.run()
        declarations = [dict.fromkeys(actuals)]
        for lane in actuals:
            partial = dict(actuals)
            partial[lane] = None
            declarations.append(partial)
        for partial in declarations:
            with m.Handoff(c.owner, (reference, ref), partial, **options(lambda *args: args[-1])) as owner:
                with calls_to(m) as counts:
                    with pytest.raises(ValueError, match='Actual execution missing or failed'):
                        owner.consume()
                assert counts == dict(negative=1)
                assert owner._state == 'failed' and not owner.root.exists()
                assert not owner._guard.locked() and not reference._guard.locked()
                assert all(not actual._guard.locked() and not actual._reference_held for actual, _ in actuals.values())
                assert not c.owner._original_operation.locked() and not c.case.guard.locked()
                with pytest.raises(ValueError):
                    owner.consume()
        def retain(root, before, after):
            assert reference._guard.locked() and c.case.guard.locked()
            assert all(actual._guard.locked() and actual._reference_held for actual, _ in actuals.values())
            retained.append((before, after))
            return after
        with m.Handoff(c.owner, (reference, ref), actuals, **options(retain)) as owner:
            with calls_to(m) as counts:
                result = owner.consume()
            assert counts['negative'] == 0 and counts['bundle'] == counts['prepare'] == 1
            assert result['completed_hours'] == 1 and len(retained) == 5
            assert all(result[key] is False for key in m.FLAGS)
            projection = json.loads(owner._plan.projection)
            assert [(row['lane_id'], row['status']) for row in projection['lanes']] == [
                ('joint', 'paired_committed'), ('second', 'paired_committed'), ('third', 'paired_committed')]
            assert json.loads(owner._packet)['schema'] == m.SCHEMA
            assert (owner.root / 'takeover_packet.json').read_bytes() == owner._packet
            saved = dict(manifest=c.owner._manifest, binding=c.owner._binding,
                holder_root=c.owner.holder_root, owner_root=c.owner.owner_root,
                holder_head=owner._holder.head, phase_heads=owner._phase.heads,
                tickets=owner._plan.tickets, projection=owner._plan.projection, after=owner._plan.after)
    def deny_retention(*args):
        raise AssertionError('read-only replay cannot retain')
    phase = m.phase
    manifest = saved['manifest']
    with phase.tickets.TicketHolder(saved['holder_root'], owner_root=saved['owner_root'],
            max_tickets=manifest.max_events, max_ticket_bytes=manifest.max_event_bytes,
            max_total_ticket_bytes=manifest.max_archive_bytes, create=False,
            expected_head=saved['holder_head'], retain_head=deny_retention) as holder:
        assert holder.inspect() == saved['tickets']
        with phase.DevelopmentOwner(saved['owner_root'], manifest, saved['binding'], holder=holder,
                create=False, expected_heads=saved['phase_heads']) as reopened:
            report = reopened.inspect(expected_heads=saved['phase_heads'])
            with phase.closing(reopened._connect()) as db:
                rows = reopened._rows(db)
            replay, state, _ = reopened._restore(rows)
            assert replay == report and report.completed_hours == 1
            assert phase.encode(state.scientific) == saved['after']
            assert phase.encode(json.loads(rows[-1][3])['projection']) == saved['projection']
            assert rows == [ticket.event for ticket in saved['tickets']]


@pytest.mark.parametrize('context', ['business_input_unresolved', 'business_unresolved'], indirect=True)
def test_legitimate_unresolved_none_retains_complete_consume_path(harness, monkeypatch):
    h = harness
    p, c = h.module, h.context
    m = loaded(p, monkeypatch, 'negative_handoff_unresolved_unit_alias')
    with p.Parent(h.root, h.raw, **h.options) as reference:
        receipt = reference.run()
        with m.Handoff(c.owner, (reference, receipt), {'joint': None}, **options(lambda *args: args[-1])) as owner:
            with calls_to(m) as counts:
                result = owner.consume()
            assert counts == dict(negative=1, bundle=1, prepare=1)
            assert result['completed_hours'] == 1
            lane, = json.loads(owner._plan.projection)['lanes']
            assert lane['status'] in ('business_input_unresolved', 'business_unresolved')

