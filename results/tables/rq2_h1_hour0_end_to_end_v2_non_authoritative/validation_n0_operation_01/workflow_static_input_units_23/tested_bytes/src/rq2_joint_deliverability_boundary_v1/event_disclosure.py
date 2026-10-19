"""Explicit current-hour N-1 disclosure mechanism, without a future event table.

This advances the revealed N-1 outage overlay, not total unit availability,
dispatch or a business ledger.
Reports and origin are mechanism inputs; no empirical observation is certified.
"""
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class OutageComponent:
    kind: str
    uid: str

    def __post_init__(self):
        if type(self.kind) is not str or self.kind not in ('generator', 'branch'):
            raise ValueError('generator or branch component required')
        if type(self.uid) is not str or not self.uid.strip():
            raise ValueError('explicit component UID required')


def _hour(x):
    if type(x) is not int or x < 0:
        raise ValueError('nonnegative integer source hour required')


@dataclass(frozen=True)
class DisclosureProtocol:
    components: tuple[OutageComponent, ...]
    visibility_rule: str
    report_semantics: str
    evidence_role: str

    def __post_init__(self):
        if (type(self.components) is not tuple or not self.components
                or any(type(c) is not OutageComponent for c in self.components)):
            raise ValueError('immutable component inventory required')
        for c in self.components:
            c.__post_init__()
        keys = tuple((c.kind, c.uid) for c in self.components)
        if keys != tuple(sorted(set(keys))):
            raise ValueError('unique sorted component inventory required')
        for name, expected in (
            ('visibility_rule', 'current_n1_outage_overlay_revealed_before_current_action'),
            ('report_semantics', 'complete_current_n1_outage_overlay__no_hidden_same_hour_replacement'),
            ('evidence_role', 'mechanism_assumption')):
            if type(getattr(self, name)) is not str or getattr(self, name) != expected:
                raise ValueError('explicit disclosure mechanism required: '+name)


@dataclass(frozen=True)
class RevealedOutage:
    local_ordinal: int
    component: OutageComponent
    first_seen_hour: int
    observed_start_hour: int | None


@dataclass(frozen=True, init=False)
class DisclosureState:
    protocol: DisclosureProtocol
    origin_hour: int
    source_hour: int
    observed_event_count: int
    active: RevealedOutage | None

    def __init__(self, *args, **kwargs):
        raise TypeError('disclosure state requires initialization or current transition')

    def __post_init__(self):
        if type(self.protocol) is not DisclosureProtocol:
            raise ValueError('typed disclosure protocol required')
        self.protocol.__post_init__()
        for x in (self.origin_hour, self.source_hour, self.observed_event_count):
            _hour(x)
        if self.source_hour < self.origin_hour:
            raise ValueError('state precedes origin')
        if self.source_hour == self.origin_hour and self.observed_event_count != int(self.active is not None):
            raise ValueError('origin event count must match explicit incoming outage overlay')
        if self.observed_event_count > self.source_hour-self.origin_hour+1:
            raise ValueError('event count exceeds observed support')
        a = self.active
        if a is not None:
            if type(a) is not RevealedOutage or type(a.component) is not OutageComponent:
                raise ValueError('typed revealed outage required')
            a.component.__post_init__()
            if a.component not in self.protocol.components:
                raise ValueError('unknown active component')
            _hour(a.local_ordinal)
            _hour(a.first_seen_hour)
            if (a.local_ordinal == 0 or a.local_ordinal != self.observed_event_count
                    or not self.origin_hour <= a.first_seen_hour <= self.source_hour):
                raise ValueError('inconsistent revealed outage state')
            if a.observed_start_hour is None:
                if a.first_seen_hour != self.origin_hour or a.local_ordinal != 1:
                    raise ValueError('unknown onset only at explicit left boundary')
            else:
                _hour(a.observed_start_hour)
                if a.observed_start_hour != a.first_seen_hour or a.first_seen_hour <= self.origin_hour:
                    raise ValueError('observed onset requires a post-origin transition')


@dataclass(frozen=True)
class CurrentOutageReport:
    source_hour: int
    active_component: OutageComponent | None
    repaired_generator_return_limit_mw: float | None

    def __post_init__(self):
        _hour(self.source_hour)
        if self.active_component is not None:
            if type(self.active_component) is not OutageComponent:
                raise ValueError('current component only; future event objects forbidden')
            self.active_component.__post_init__()
        cap = self.repaired_generator_return_limit_mw
        if cap is not None and (type(cap) not in (int, float) or not isfinite(cap) or cap < 0):
            raise ValueError('finite nonnegative explicit repair limit required')


@dataclass(frozen=True, init=False)
class DisclosureStep:
    before: DisclosureState
    report: CurrentOutageReport
    after: DisclosureState
    started: RevealedOutage | None
    ended: RevealedOutage | None
    repaired_generator_return_limit_mw: float | None

    def __init__(self, *args, **kwargs):
        raise TypeError('disclosure step requires current transition')


def _owned(cls, **values):
    result = object.__new__(cls)
    for name, value in values.items():
        object.__setattr__(result, name, value)
    if cls is DisclosureState:
        result.__post_init__()
    return result


def initialize_disclosure(protocol, *, source_hour, active_component):
    """An incoming down state has unknown onset; initialization is not a trip."""
    if active_component is not None and type(active_component) is not OutageComponent:
        raise ValueError('typed initial current component required')
    active = None if active_component is None else RevealedOutage(1, active_component, source_hour, None)
    return _owned(DisclosureState, protocol=protocol, origin_hour=source_hour, source_hour=source_hour,
                  observed_event_count=int(active is not None), active=active)


def disclose_current(state, report):
    """One complete current report; missing hours or repair evidence stop here."""
    if type(state) is not DisclosureState or type(report) is not CurrentOutageReport:
        raise ValueError('typed state and current report required')
    state.__post_init__()
    report.__post_init__()
    if report.source_hour != state.source_hour+1:
        raise ValueError('contiguous current source hour required')
    current = report.active_component
    if current is not None and current not in state.protocol.components:
        raise ValueError('unknown reported component')
    old = state.active
    same = old is not None and old.component == current
    ended = old if old is not None and not same else None
    generator_return = ended is not None and ended.component.kind == 'generator'
    cap = report.repaired_generator_return_limit_mw
    if generator_return != (cap is not None):
        raise ValueError('repair limit required exactly when a generator return is observed')
    started = None
    active = old if same else None
    count = state.observed_event_count
    if current is not None and not same:
        count += 1
        started = RevealedOutage(count, current, report.source_hour, report.source_hour)
        active = started
    after = _owned(DisclosureState, protocol=state.protocol, origin_hour=state.origin_hour,
                   source_hour=report.source_hour, observed_event_count=count, active=active)
    return _owned(DisclosureStep, before=state, report=report, after=after,
                  started=started, ended=ended, repaired_generator_return_limit_mw=cap)
