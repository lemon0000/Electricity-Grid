"""Current-prefix outage binding; detached development evidence, no run authority."""
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path

from src.rq2_joint_deliverability_boundary_v1 import event_disclosure as events
from src.rq2_joint_deliverability_boundary_v1 import source_window as source


def implementation_identity():
    return source._hash({str(Path(m.__file__).relative_to(source.audit.ROOT)).replace('\\', '/'):
        sha256(Path(m.__file__).read_bytes()).hexdigest()
        for m in (source, source.audit, events)} | {
        'adapter': sha256(Path(__file__).read_bytes()).hexdigest()})


@dataclass(frozen=True)
class Prefix:
    origin: events.DisclosureState
    steps: tuple[events.DisclosureStep, ...]
    decision_identity: str
    audit: dict
    detached_consumer_authenticated: bool = False
    normal_source_correspondence_verified: bool = False
    formal_result: bool = False


def _parameters(split, raw_start, hours, seed, protocol, caps):
    if type(split) is not str or split not in ('training', 'holdout'):
        raise ValueError('explicit source split required')
    if type(raw_start) is not int or raw_start < 1:
        raise ValueError('input unresolved: prior boundary row required')
    if type(hours) is not int or not 1 <= hours <= 192:
        raise ValueError('one through 192 current hours required')
    if type(seed) is not int or seed < 0:
        raise ValueError('explicit outage seed required')
    if type(protocol) is not events.DisclosureProtocol:
        raise ValueError('typed static disclosure protocol required')
    protocol.__post_init__()
    if type(caps) is not tuple or len(caps) != hours:
        raise ValueError('explicit repair limit slot for every current hour required')
    for h, cap in enumerate(caps):
        events.CurrentOutageReport(h+1, None, cap).__post_init__()


def _component(row):
    values = tuple(row[k] for k in ('active_event_id', 'active_component_type', 'active_component_uid'))
    if any(type(v) is not str for v in values):
        raise ValueError('raw outage fields must be strings')
    if values == ('', '', ''):
        return None
    if any(not v.strip() for v in values):
        raise ValueError('incomplete current outage observation')
    return events.OutageComponent(values[1], values[2])


def _rebuild(window, *, split, raw_start, hours, seed, protocol, repair_limits):
    """Pure test seam. Only prepare loads and checks the pinned marginal source."""
    _parameters(split, raw_start, hours, seed, protocol, repair_limits)
    if (window['kind'], window['split'], window['raw_start'], window['hours'], window['outage_seed']) != (
            'power', split, raw_start-1, hours+1, seed):
        raise ValueError('boundary/current source window mismatch')
    rows = window['rows']
    if type(rows) is not list or len(rows) != hours+1:
        raise ValueError('complete boundary and current prefix required')
    chain = window['chain']
    selected, _ = source._select(rows, [chain], 'power', split, raw_start-1, hours+1, seed)
    if rows != selected:
        raise ValueError('source prefix must be ordered and contiguous')
    times = [datetime.fromisoformat(r['timestamp']) for r in rows]
    if any(t.utcoffset() is None for t in times) or any(
            b-a != timedelta(hours=1) for a, b in zip(times, times[1:])):
        raise ValueError('contiguous timezone-aware source clock required')
    components = tuple(_component(r) for r in rows)
    origin = events.initialize_disclosure(protocol, source_hour=0, active_component=components[0])
    state, steps = origin, []
    seen = {rows[0]['active_event_id']} - {''}
    for i, (previous, current) in enumerate(zip(rows, rows[1:]), 1):
        old_id, new_id = previous['active_event_id'], current['active_event_id']
        same = components[i-1] == components[i]
        if bool(old_id) and old_id == new_id and not same:
            raise ValueError('one event identity cannot change component')
        if old_id != new_id and same and components[i] is not None:
            raise ValueError('hidden same-hour replacement is outside disclosure protocol')
        if new_id and new_id != old_id:
            if new_id in seen:
                raise ValueError('ended event identity reappeared')
            seen.add(new_id)
        step = events.disclose_current(state, events.CurrentOutageReport(
            i, components[i], repair_limits[i-1]))
        steps.append(step)
        state = step.after
    # Source IDs/clocks are audit-only; decisions reveal no event ending or duration.
    decision = source._hash({'origin': asdict(origin), 'steps': [asdict(s) for s in steps]})
    return Prefix(origin, tuple(steps), decision, {
        'window_identity': window['window_identity'], 'split': split, 'outage_seed': seed,
        'raw_boundary_hour': raw_start-1, 'raw_current_hours': list(range(raw_start, raw_start+hours)),
        'rows': selected, 'config_sha256': window['config_sha256'],
        'package_manifest_sha256': window['package_manifest_sha256'],
        'source_role': 'synthetic_registered_marginal_outage_not_empirical_observation',
        'repair_limits_role': 'explicit_mechanism_inputs_not_source_observations',
        'origin_onset_known': False, 'cross_split_boundary_supported': False})


def prepare(*, split, raw_start, hours, outage_seed, protocol, repair_limits,
            expected_window_identity, expected_config_sha256, config_path=source.audit.DEFAULT_CONFIG):
    """Fresh-at-return prefix; a later owned consumer must revalidate its pins."""
    _parameters(split, raw_start, hours, outage_seed, protocol, repair_limits)
    source._sha(expected_window_identity)
    source._sha(expected_config_sha256)
    before = implementation_identity()
    def load():
        value = source.load_source_window('power', split, raw_start-1, hours+1,
            outage_seed=outage_seed, config_path=config_path,
            expected_config_sha256=expected_config_sha256)
        body = dict(value)
        identity = body.pop('window_identity')
        if identity != expected_window_identity or source._hash(body) != identity:
            raise ValueError('pinned source window changed')
        return value
    window = load()
    result = _rebuild(window, split=split, raw_start=raw_start, hours=hours, seed=outage_seed,
        protocol=protocol, repair_limits=repair_limits)
    if load() != window or implementation_identity() != before:
        raise ValueError('source or implementation changed during disclosure binding')
    result.audit['implementation_identity'] = before
    return result
