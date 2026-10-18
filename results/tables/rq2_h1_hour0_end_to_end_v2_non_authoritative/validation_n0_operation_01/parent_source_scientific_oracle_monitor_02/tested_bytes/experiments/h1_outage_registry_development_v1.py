"""Approved origin/cap rules, implemented as fresh detached development inputs.

Only the selected split archive is decoded. Original mixed CSV/event members
are opaque integrity hashes. No N, physical owner, selector or run is invoked.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from fractions import Fraction as Q
from hashlib import sha256
import gzip
import json
from pathlib import Path

from experiments import audit_h1_outage_boundary_development_v1 as catalog
from experiments import audit_h1_outage_origin_replay_development_v1 as frozen
from experiments import build_h1_outage_split_archive_development_v1 as extractor
from experiments import h1_outage_source_development_v1 as old
from src.grid import rts_gmlc

ROOT = frozen.ROOT
OUTPUT = ROOT/'results/tables/rq2_h1_outage_registry_v1_non_authoritative'
AUTHORITY = OUTPUT/'scientific_development_authority.json'
AUTHORITY_SHA = '45710f18fcf98113d53c50cd74e0dfc311ad3e03cfb8ab8f75b01dc2720de0a8'
ARCHIVE = OUTPUT/'split_archive'
ARCHIVE_SHA = '2bd9a14f9e54f80e860975e26fc2b44fa527f1725cfb8ce7bec592ff5fdc5bd9'
SCHEMA = 'h1_approved_outage_origin_cap_registry_development_v1'
events = old.events


def _pin(path, expected):
    old.source._sha(expected)
    data = Path(path).read_bytes()
    if sha256(data).hexdigest() != expected:
        raise ValueError('pinned registry input drift: '+str(path))
    return data


def implementation_identity():
    return old.source._hash({m.__name__: frozen._hash(m.__file__)
        for m in (old, old.source, old.source.audit, events, frozen, frozen.chronology,
                  frozen.builder, rts_gmlc, extractor, catalog)} | {
            'self': frozen._hash(__file__)})


def _load(split):
    """Private owner of verified files; callers cannot provide a registry object."""
    if type(split) is not str or split not in ('training', 'holdout'):
        raise ValueError('explicit source split required')
    authority = json.loads(_pin(AUTHORITY, AUTHORITY_SHA))
    _pin(ROOT/authority['proposal_path'], authority['proposal_sha256'])
    table = json.loads(_pin(ROOT/authority['cap_table_path'], authority['cap_table_sha256']))
    config = frozen.yaml.safe_load(_pin(frozen.CONFIG, frozen.CONFIG_SHA))
    package = ROOT/config['output']['directory']
    # Complete member hashes only; never decode the mixed CSV or event table.
    frozen.builder._verify_package(package, frozen.PACKAGE_SHA)
    summary = json.loads((package/'summary.json').read_bytes())
    source = config['source']
    if (summary['config_sha256'] != frozen.CONFIG_SHA
            or summary['grid_source_manifest_sha256'] != source['grid_manifest_sha256']
            or summary['cfe_package_manifest_sha256'] != source['cfe_manifest_sha256']):
        raise ValueError('package/source cross-link drift')
    _pin(frozen.builder.__file__, summary['implementation_sha256'])
    _pin(frozen.chronology.__file__, summary['n1_chronology_module_sha256'])
    grid = ROOT/source['grid_root']
    _pin(grid/'SHA256SUMS', source['grid_manifest_sha256'])
    if not frozen.builder.verify_sha256_manifest(grid):
        raise ValueError('static upstream drift')
    frozen.builder._verify_package(ROOT/source['cfe_package'], source['cfe_manifest_sha256'])
    components, excluded_units, excluded_branches = frozen.builder._components(grid,
        excluded_generator_unit_types=frozenset(config['derivation']['excluded_generator_unit_types']))
    if (len(components) != summary['reliability_components']
            or list(excluded_units) != summary['excluded_disabled_generator_uids']
            or list(excluded_branches) != summary['excluded_islanding_branch_uids']):
        raise ValueError('eligible component inventory drift')
    protocol = events.DisclosureProtocol(tuple(sorted(
        (events.OutageComponent(c.component_type, c.uid) for c in components), key=lambda c:(c.kind,c.uid))),
        'current_n1_outage_overlay_revealed_before_current_action',
        'complete_current_n1_outage_overlay__no_hidden_same_hour_replacement', 'mechanism_assumption')
    _pin(ROOT/table['source_gen_path'], table['source_gen_sha256'])
    import csv
    with (ROOT/table['source_gen_path']).open(encoding='utf-8', newline='') as stream:
        units = {r['GEN UID']: r for r in csv.DictReader(stream)}
    caps = {}
    for row in table['rows']:
        uid = row['generator_uid']; raw = units[uid]
        if (row['raw_pmax_mw'], row['raw_pmin_mw'], row['raw_ramp_mw_per_minute']) != (
                raw['PMax MW'], raw['PMin MW'], raw['Ramp Rate MW/Min']):
            raise ValueError('repair source projection drift')
        pmax, pmin, ramp = Q(raw['PMax MW']), Q(raw['PMin MW']), Q(raw['Ramp Rate MW/Min'])
        cap = min(pmax, 60*ramp)
        if (not 0 <= pmin <= pmax or ramp < 0 or str(cap) != row['proposed_cap_mw_fraction']
                or Q(str(float(cap))) != cap or uid in caps):
            raise ValueError('invalid exact repair table')
        caps[uid] = cap
    if set(caps) != {c.uid for c in components if c.component_type == 'generator'}:
        raise ValueError('repair table inventory drift')
    manifest = json.loads(_pin(ARCHIVE/'manifest.json', ARCHIVE_SHA))
    if (manifest['source_package_manifest_sha256'] != frozen.PACKAGE_SHA
            or manifest['generator_config_sha256'] != frozen.CONFIG_SHA
            or manifest['split_hour'] != summary['split_hour']
            or manifest['source_horizon_hours'] != summary['hours']):
        raise ValueError('split archive source mismatch')
    _pin(extractor.__file__, manifest['builder_sha256'])
    _pin(ROOT/manifest['source_member_path'], manifest['source_member_sha256'])
    entry = manifest['members'][split]
    payload = gzip.decompress(_pin(ARCHIVE/entry['path'], entry['sha256']))
    if sha256(payload).hexdigest() != entry['content_sha256']:
        raise ValueError('split archive content drift')
    data = json.loads(payload); rows = data['rows']
    if data['split'] != split or len(rows) != entry['row_count'] or any(r['split'] != split for r in rows):
        raise ValueError('cross-split archive rejected')
    hashes = [sha256(extractor.encode(r)).hexdigest() for r in rows]
    if sha256(extractor.encode(hashes)).hexdigest() != entry['ordered_row_hashes_sha256']:
        raise ValueError('split row projection drift')
    grouped = {}
    for row in rows:
        seed, hour = int(row['outage_seed']), int(row['source_hour'])
        allowed = (0 <= hour < summary['split_hour'] if split == 'training'
                   else summary['split_hour'] <= hour < summary['hours'])
        if not allowed or seed not in config['derivation']['outage_seeds']:
            raise ValueError('source split/seed/hour mismatch')
        group = grouped.setdefault(seed, {})
        if hour in group:
            raise ValueError('duplicate source hour')
        group[hour] = row
    for group in grouped.values():
        _ordered(list(group.values()))
    axes = json.loads(_pin(ROOT/catalog.CATALOG, catalog.CATALOG_SHA))['obligation_catalog']['axes']
    gaps = json.loads(_pin(frozen.GAPS, frozen.GAPS_SHA))['unique_unresolved']
    catalog_entries = [e for axis in axes.values() for e in axis['power'] if e['split'] == split]
    identity = old.source._hash(dict(schema=SCHEMA, authority=AUTHORITY_SHA, archive=ARCHIVE_SHA,
        source_package=frozen.PACKAGE_SHA, cap_table=authority['cap_table_sha256'],
        catalog=catalog.CATALOG_SHA, implementation=implementation_identity()))
    return dict(split=split, protocol=protocol, caps=caps, components=components, rows=grouped,
        catalog_entries=catalog_entries, gaps=gaps, identity=identity, axes=axes,
        split_hour=summary['split_hour'], archive_member_sha256=entry['sha256'],
        cap_table_sha256=authority['cap_table_sha256'])


def _ordered(rows):
    hours = [int(r['source_hour']) for r in rows]
    times = [datetime.fromisoformat(r['timestamp']) for r in rows]
    if (hours != list(range(hours[0], hours[0]+len(rows)))
            or any(t.utcoffset() is None for t in times)
            or any(b-a != timedelta(hours=1) for a,b in zip(times,times[1:]))):
        raise ValueError('contiguous source hour and clock required')


@dataclass(frozen=True)
class FirstAction:
    relative_hour: int
    current_state: events.DisclosureState

    def __post_init__(self):
        if type(self.relative_hour) is not int or self.relative_hour != 0:
            raise ValueError('first action requires relative hour zero')
        if type(self.current_state) is not events.DisclosureState:
            raise ValueError('typed initial disclosure required')
        self.current_state.__post_init__()
        if self.current_state.origin_hour != 0 or self.current_state.source_hour != 0:
            raise ValueError('first action cannot consume a disclosure transition')


@dataclass(frozen=True)
class TransitionAction:
    relative_hour: int
    step: events.DisclosureStep


def decision_view(action):
    """Physical projection omits raw clocks, source labels and event IDs."""
    if type(action) is FirstAction:
        action.__post_init__()
        state, started, ended, cap = action.current_state, None, None, None
    elif type(action) is TransitionAction:
        if type(action.relative_hour) is not int or not 0 <= action.relative_hour < 192:
            raise ValueError('current relative action hour required')
        step = action.step
        if type(step) is not events.DisclosureStep or events.disclose_current(step.before,step.report) != step:
            raise ValueError('valid current transition required')
        state, started, ended = step.after, step.started, step.ended
        cap = None if step.repaired_generator_return_limit_mw is None else Q(str(step.repaired_generator_return_limit_mw))
    else:
        raise ValueError('explicit first or transition action required')
    component = lambda item: None if item is None else asdict(item.component)
    return dict(relative_hour=action.relative_hour, active=component(state.active),
        started=component(started), ended=component(ended),
        repair_cap_exact=None if cap is None else [str(cap.numerator),str(cap.denominator)])


@dataclass(frozen=True)
class Prefix:
    origin: events.DisclosureState
    actions: tuple
    decision_identity: str
    audit: dict


def _component(row):
    return old._component(row)


def _continuity(previous, current, seen):
    old_id, new_id = previous['active_event_id'], current['active_event_id']
    same = _component(previous) == _component(current)
    if old_id and old_id == new_id and not same:
        raise ValueError('event identity changed component')
    if old_id != new_id and same and _component(current) is not None:
        raise ValueError('hidden same-hour replacement')
    if new_id and new_id != old_id:
        if new_id in seen:
            raise ValueError('ended event identity reappeared')
        seen.add(new_id)


def _prepare(context, *, raw_start, hours, outage_seed):
    """Private deterministic seam, not a credential accepting user-built contexts."""
    if (type(raw_start) is not int or raw_start < 0 or type(hours) is not int
            or not 1 <= hours <= 192 or type(outage_seed) is not int or outage_seed < 0):
        raise ValueError('explicit source coordinates and one through 192 hours required')
    split = context['split']
    entries = [e for e in context['catalog_entries'] if e['source_start'] == raw_start
               and e['outage_seed'] == outage_seed]
    if not entries or any(raw_start+hours-1 > e['observed_end_inclusive'] for e in entries):
        raise ValueError('source request outside unchanged catalog support')
    if any(e['chain_id'] != f'power:{split}:outage_seed={outage_seed}' for e in entries):
        raise ValueError('catalog trajectory mismatch')
    group = context['rows'][outage_seed]
    try:
        rows = [group[h] for h in range(raw_start,raw_start+hours)]
    except KeyError:
        raise ValueError('current source prefix missing') from None
    _ordered(rows)
    gaps = {(g['split'],g['outage_seed'],g['raw_start']) for g in context['gaps']}
    key = (split,outage_seed,raw_start)
    first = raw_start == 0
    if first:
        if split != 'training' or key not in gaps:
            raise ValueError('chronology origin outside approved support')
        generated = frozen.prefix_overlay(context['components'],outage_seed,0)[0]
        if generated != tuple(rows[0][k] for k in ('active_event_id','active_component_type','active_component_uid')):
            raise ValueError('initial row differs from stationary generator draw')
        boundary = rows[0]; kind = 'chronology_origin'
    elif raw_start-1 in group:
        boundary = group[raw_start-1]; kind = 'existing_same_chain_boundary'
        _ordered([boundary]+rows)
    else:
        if split != 'holdout' or key not in gaps or raw_start-1 < context['split_hour']:
            raise ValueError('input unresolved: boundary outside approved generated support')
        eid, component_type, uid = frozen.prefix_overlay(context['components'],outage_seed,raw_start-1)[-1]
        boundary = dict(active_event_id=eid,active_component_type=component_type,active_component_uid=uid)
        kind = 'generated_same_split_boundary'
    origin = events.initialize_disclosure(context['protocol'],source_hour=0,active_component=_component(boundary))
    state, previous, actions = origin, boundary, []
    seen = {boundary['active_event_id']} - {''}
    for hour, row in enumerate(rows):
        if first and hour == 0:
            action = FirstAction(0,origin)
        else:
            _continuity(previous,row,seen)
            active = _component(row)
            ended = state.active if state.active is not None and state.active.component != active else None
            cap = (context['caps'][ended.component.uid] if ended is not None
                   and ended.component.kind == 'generator' else None)
            step = events.disclose_current(state,events.CurrentOutageReport(
                state.source_hour+1,active,None if cap is None else float(cap)))
            action = TransitionAction(hour,step);state = step.after
        actions.append(action);previous = row
    views = [decision_view(a) for a in actions]
    return Prefix(origin,tuple(actions),old.source._hash(views),dict(
        origin_kind=kind,split=split,outage_seed=outage_seed,raw_start=raw_start,hours=hours,
        raw_origin_hour=0 if first else raw_start-1,predecessor_source_hour=None if first else raw_start-1,
        raw_current_hours=list(range(raw_start,raw_start+hours)),
        last_revealed_raw_hour=raw_start+hours-1,completed_actions=hours,
        current_rows=rows,boundary_evidence=boundary,registry_identity=context['identity'],
        archive_member_sha256=context['archive_member_sha256'],cap_table_sha256=context['cap_table_sha256'],
        origin_onset_known=False,existing_same_chain_row=kind=='existing_same_chain_boundary',
        synthetic_mechanism_not_empirical=True,detached_consumer_authenticated=False,
        normal_source_correspondence_verified=False,physical_consumer_connected=False,
        persistent_lane_owner_implemented=False,full_192_hour_execution_verified=False,
        resource_admission=False,formal_execution_ready=False,formal_result=False,native_execution_authorized=False))


def inspect_registry_identity(split):
    """Discovery only; no operational authentication or authority."""
    return _load(split)['identity']


def prepare(*, split, raw_start, hours, outage_seed, expected_registry_identity):
    old.source._sha(expected_registry_identity)
    before = implementation_identity()
    context = _load(split)
    if context['identity'] != expected_registry_identity:
        raise ValueError('registry identity mismatch')
    result = _prepare(context,raw_start=raw_start,hours=hours,outage_seed=outage_seed)
    again = _load(split)
    if (_prepare(again,raw_start=raw_start,hours=hours,outage_seed=outage_seed) != result
            or implementation_identity() != before):
        raise ValueError('registry/source changed during preparation')
    return result


def audit_catalog():
    """Offline development coverage of every catalog prefix, preserving censoring."""
    families, unique, source_kinds = {}, {}, {}
    initial = implementation_identity()
    for split in ('training','holdout'):
        context = _load(split)
        for family, axis in context['axes'].items():
            selected = [e for e in axis['power'] if e['split'] == split]
            if not selected:
                continue
            records = []
            for entry in selected:
                start,seed = entry['source_start'],entry['outage_seed']
                hours = entry['observed_end_inclusive']-start+1
                key = (split,seed,start,hours)
                if key not in unique:
                    result = _prepare(context,raw_start=start,hours=hours,outage_seed=seed)
                    unique[key] = (result.audit['origin_kind'],result.decision_identity)
                    source_kinds[result.audit['origin_kind']] = source_kinds.get(result.audit['origin_kind'],0)+1
                kind,identity = unique[key]
                records.append(dict(entry=entry,origin_kind=kind,decision_identity=identity,actions=hours))
            families[family] = dict(power_entries=len(records),entries=records,obligations_removed=0)
        if _load(split)['identity'] != context['identity']:
            raise ValueError('registry changed during coverage audit')
    if implementation_identity() != initial:
        raise ValueError('implementation changed during coverage audit')
    return dict(schema=SCHEMA,status='DRAFT_NONAUTHORITATIVE',families=families,
        unique_entries=len(unique),origin_kinds=source_kinds,source_input_unresolved=0,obligations_removed=0,
        source_origin_cap_coverage_development_verified=True,full_boundary_coverage_verified=False,
        full_192_hour_execution_verified=False,physical_consumer_connected=False,
        persistent_lane_owner_implemented=False,formal_execution_ready=False,formal_result=False,
        resource_admission=False,native_execution_authorized=False,solver_calls=0,synthetic_jobs=0)
