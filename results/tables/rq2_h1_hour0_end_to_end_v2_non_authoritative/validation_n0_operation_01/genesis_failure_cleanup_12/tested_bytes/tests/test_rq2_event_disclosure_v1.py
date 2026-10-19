from dataclasses import asdict, replace

import pytest

from src.rq2_joint_deliverability_boundary_v1.event_disclosure import (
    OutageComponent, DisclosureProtocol, CurrentOutageReport, DisclosureState, DisclosureStep,
    RevealedOutage, initialize_disclosure, disclose_current)
from src.scenarios.rts_gmlc_n1_chronology import N1OutageEvent


B = OutageComponent('branch', 'B1')
G = OutageComponent('generator', 'G1')
H = OutageComponent('generator', 'G2')


def protocol():
    return DisclosureProtocol((B, G, H), 'current_n1_outage_overlay_revealed_before_current_action',
        'complete_current_n1_outage_overlay__no_hidden_same_hour_replacement', 'mechanism_assumption')


def initial(active=None, hour=0):
    return initialize_disclosure(protocol(), source_hour=hour, active_component=active)


def step(state, active, cap=None):
    return disclose_current(state, CurrentOutageReport(state.source_hour+1, active, cap))


def test_trip_ongoing_repair_and_local_event_identity():
    origin = initial()
    trip = step(origin, G)
    assert trip.started.local_ordinal == 1
    assert trip.started.observed_start_hour == 1
    ongoing = step(trip.after, G)
    assert ongoing.started is ongoing.ended is None
    assert ongoing.after.active == trip.started
    repair = step(ongoing.after, None, 12.)
    assert repair.ended == trip.started and repair.started is None
    assert repair.after.active is None
    assert repair.repaired_generator_return_limit_mw == 12.
    next_trip = step(repair.after, B)
    assert next_trip.started.local_ordinal == 2
    assert origin == initial()


def test_stationary_down_origin_never_fabricates_trip_or_age():
    origin = initial(G, hour=24)
    assert origin.active.first_seen_hour == 24
    assert origin.active.observed_start_hour is None
    ongoing = step(origin, G)
    assert ongoing.started is ongoing.ended is None
    assert ongoing.after.active.observed_start_hour is None
    assert step(ongoing.after, None, 0.).ended == origin.active


def test_observation_end_does_not_repair():
    state = step(initial(), G).after
    state = step(state, G).after
    assert state.source_hour == 2 and state.active is not None
    with pytest.raises(ValueError, match='typed state and current report'):
        disclose_current(state, None)
    assert state.active.observed_start_hour == 1


def test_branch_repair_requires_no_generator_limit():
    origin = initial(B)
    repaired = step(origin, None)
    assert repaired.ended == origin.active
    assert repaired.repaired_generator_return_limit_mw is None
    with pytest.raises(ValueError, match='repair limit required exactly'):
        step(origin, None, 0.)


def test_boundary_switch_ends_previous_event_and_starts_new_one():
    origin = initial(G)
    switched = step(origin, H, 7.)
    assert switched.ended.component == G
    assert switched.started.component == H
    assert switched.after.active == switched.started
    assert switched.after.observed_event_count == 2
    assert switched.repaired_generator_return_limit_mw == 7.


@pytest.mark.parametrize('active,cap', [(None, None), (B, None), (H, None), (G, 2.)])
def test_missing_or_premature_repair_limits_rejected(active, cap):
    state = initial(G)
    with pytest.raises(ValueError, match='repair limit required exactly'):
        step(state, active, cap)
    assert state == initial(G)


@pytest.mark.parametrize('cap', [-1., float('nan'), float('inf'), True, '2'])
def test_invalid_repair_limits(cap):
    with pytest.raises(ValueError):
        CurrentOutageReport(1, None, cap)


@pytest.mark.parametrize('hour', [0, 2, -1, True, 1.5])
def test_gap_duplicate_and_invalid_hour(hour):
    with pytest.raises(ValueError):
        disclose_current(initial(), CurrentOutageReport(hour, None, None))


def test_future_event_object_not_admitted_as_current_report():
    future = N1OutageEvent(7, 'seed_7_event_0000', 'generator', 'G1', 1, 100)
    with pytest.raises(ValueError, match='future event objects forbidden'):
        CurrentOutageReport(1, future, None)
    with pytest.raises(ValueError):
        disclose_current(initial(), future)


def test_unknown_component_not_in_static_inventory():
    with pytest.raises(ValueError, match='unknown reported'):
        step(initial(), OutageComponent('generator', 'OTHER'))


@pytest.mark.parametrize('field,value', [('visibility_rule', 'after_action'),
    ('report_semantics', 'missing_means_up'), ('evidence_role', 'observed')])
def test_explicit_mechanism_has_no_silent_defaults(field, value):
    with pytest.raises(ValueError):
        replace(protocol(), **{field: value})


def replay(origin, reports):
    records = []
    for report in reports:
        record = disclose_current(origin, report)
        records.append(record)
        origin = record.after
    return tuple(records)


def test_changed_future_report_does_not_change_revealed_prefix():
    prefix = (CurrentOutageReport(1, G, None), CurrentOutageReport(2, G, None))
    left = replay(initial(), prefix+(CurrentOutageReport(3, None, 10.),))
    right = replay(initial(), prefix+(CurrentOutageReport(3, G, None),))
    assert left[:2] == right[:2]
    assert left[2] != right[2]
    changed_current = replay(initial(), (CurrentOutageReport(1, B, None),))
    assert changed_current[0] != left[0]


def test_chunk_partition_preserves_all_records():
    reports = (CurrentOutageReport(1, G, None), CurrentOutageReport(2, G, None),
        CurrentOutageReport(3, None, 10.), CurrentOutageReport(4, B, None))
    whole = replay(initial(), reports)
    first = replay(initial(), reports[:2])
    second = replay(first[-1].after, reports[2:])
    assert whole == first+second


def test_policy_visible_record_has_no_future_interval_or_random_seed():
    record = step(initial(), G)
    def keys(value):
        if isinstance(value, dict):
            for key, child in value.items():
                yield key
                yield from keys(child)
        elif isinstance(value, (tuple, list)):
            for child in value:
                yield from keys(child)
    assert not {'seed', 'outage_seed', 'event_id', 'end_hour_exclusive', 'horizon_hours'} & set(keys(asdict(record)))


def test_mutated_typed_inputs_are_revalidated():
    state = initial()
    report = CurrentOutageReport(1, G, None)
    object.__setattr__(report, 'source_hour', True)
    with pytest.raises(ValueError):
        disclose_current(state, report)


def test_origin_cannot_claim_unseen_event_history():
    with pytest.raises(TypeError, match='requires initialization'):
        replace(initial(), observed_event_count=1)


@pytest.mark.parametrize('changes', [{'local_ordinal': 2}, {'first_seen_hour': 2},
    {'observed_start_hour': 0}, {'observed_start_hour': True}])
def test_origin_outage_metadata_must_not_invent_onset(changes):
    state = initial(G)
    object.__setattr__(state, 'active', replace(state.active, **changes))
    with pytest.raises(ValueError):
        step(state, G)


@pytest.mark.parametrize('count,active', [(2, RevealedOutage(2, G, 1, 1)), (1, None)])
def test_unreachable_public_state_construction_is_rejected(count, active):
    with pytest.raises(TypeError, match='requires initialization'):
        DisclosureState(protocol(), 0, 1, count, active)
    with pytest.raises(TypeError, match='requires initialization'):
        replace(step(initial(), G).after, observed_event_count=count, active=active)


def test_step_cannot_be_constructed_or_relabelled():
    record = step(initial(), G)
    with pytest.raises(TypeError, match='requires current transition'):
        DisclosureStep(record.before, record.report, record.after, None, None, None)
    with pytest.raises(TypeError, match='requires current transition'):
        replace(record, started=None)
