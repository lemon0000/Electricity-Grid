"""Read-only bounded P1 query provenance from independently replayed policy state."""
from dataclasses import asdict, replace
from pathlib import Path
import sys

from src import staged_rts24_saved_point_replay_v1 as point
from src import staged_rts24_causal_v2 as causal
from src import staged_rts24_causal_audit_v2 as policy_audit
from src.staged_rts24_reference_queries_v1 import reference_requests

core, codec, mechanical = point.core, point.codec, point.mechanical
require = codec.require
ROOT = point.ROOT
SOURCES = point.SOURCES + ('src/staged_rts24_saved_prefix_replay_v1.py',
    'tests/test_staged_rts24_saved_prefix_replay_v1.py',
    'docs/plan/staged_deliverability_c_saved_prefix_replay_contract_v1.md',
    'src/staged_rts24_causal_v2.py', 'src/staged_rts24_causal_audit_v2.py',
    'src/staged_rts24_reference_queries_v1.py')
PLAN, CLEAN, METHOD = 'on_time', 'early', 'full_temporal'


def source_pins():
    return {name: mechanical.pin(codec.read_bytes(ROOT/name)) for name in SOURCES}


def _sources(expected):
    require(type(expected) is dict and set(expected) == set(SOURCES), 'closed prefix source group required')
    for value in expected.values(): mechanical.checked_pin(value)
    actual = source_pins()
    require(actual == expected, 'prefix source bytes changed')
    for name in SOURCES:
        if not name.startswith('src/') or not name.endswith('.py'): continue
        module = sys.modules.get(name[:-3].replace('/', '.').removesuffix('.__init__'))
        require(module is not None and type(getattr(module, '__file__', None)) is str
            and Path(module.__file__).absolute() == (ROOT/name).absolute(), 'loaded prefix module path differs')
        require(mechanical.pin(codec.read_bytes(module.__file__)) == actual[name], 'loaded prefix source differs')
    return actual


def schedule_slot(request, ordinal, dynamic=False):
    return dict(ordinal=ordinal, hour=request.hour, role=request.role, objective=request.objective,
        outage=asdict(request.outages), request_sha=None if dynamic else request.identity,
        parent_request_sha=request.anchor_id, bound_query_sha=None,
        dynamic_reason='policy_power_and_parent_point' if dynamic else 'bound_parent_point' if request.anchor_id else None)


def replay_prefix(points_root, fixture, hours, expectations, outer_record, expected_sources):
    """Only reconstructed accepted actuals can advance this five-hour policy prefix."""
    point._outer(outer_record)
    before_sources = _sources(expected_sources)
    require(type(fixture) is core.Fixture and fixture.first_hour == -2, 'P1 initial fixture required')
    require(type(hours) is tuple and 1 <= len(hours) <= 5
        and all(type(h) is int for h in hours) and hours == tuple(range(-2, -2+len(hours))), 'bounded contiguous P1 hours required')
    mechanical.keys(expectations, 'fixture_sha initial_state_sha after_state_shas pins_sha registration_sha slots point_files')
    for key in ('fixture_sha', 'initial_state_sha', 'pins_sha', 'registration_sha'): mechanical.sha(expectations[key])
    require(core.digest(fixture) == expectations['fixture_sha'], 'independent fixture differs')
    for data in (fixture.before, fixture.after):
        require(1 <= len(data.buses) <= 24 and 1 <= len(data.generators) <= 33 and len(data.branches) <= 38,
            'fixture network exceeds bounded prefix')
    states, slots, files = (expectations[key] for key in ('after_state_shas', 'slots', 'point_files'))
    require(type(states) is tuple and len(states) == len(hours), 'expected state prefix length differs')
    for value in states:
        if value is not None: mechanical.sha(value)
    require(type(slots) is tuple and 1 <= len(slots) <= 21 and type(files) is dict
        and set(files) == {str(i) for i in range(1, len(slots)+1)}, 'bounded closed prefix slots required')
    total_files = total_bytes = 0
    for inventory in files.values():
        require(type(inventory) is dict and 1 <= len(inventory) <= 8192, 'held point pins required')
        total_files += len(inventory)
        for name, value in inventory.items():
            mechanical.relative(name);mechanical.checked_pin(value);total_bytes += value['bytes']
    require(total_files <= 8192 and total_bytes <= 64*1024*1024, 'combined prefix file budget exceeded')
    held = tuple(map(codec.canonical, (expectations, outer_record, expected_sources)))
    fixture_sha = core.digest(fixture)
    state = causal.initialize_execution(fixture, PLAN, CLEAN, METHOD)
    require(core.digest(state) == expectations['initial_state_sha'], 'independent initial state differs')
    roots = codec.directory_chain(Path(points_root).absolute())
    root_identity = codec.directory_identity(roots)
    reports, transitions, visited_inventory = [], [], []
    stage, outcome, attempted_state = None, 'bounded_prefix_complete', None
    attempted_audit = attempted_summary = None
    c_sources = {name: before_sources[name] for name in point.SOURCES}

    def replay(query, slot_request=None):
        ordinal = len(reports)+1
        require(ordinal <= len(slots), 'unexpected prefix query after held slots')
        expected_slot = schedule_slot(query.request if slot_request is None else slot_request, ordinal, slot_request is not None)
        require(codec.canonical(slots[ordinal-1]) == codec.canonical(expected_slot), 'independent prefix schedule differs')
        require(codec.directory_identity(roots) == root_identity, 'prefix root identity changed')
        inventory = mechanical.inventory(roots/f'point_{ordinal:04d}')
        require(inventory['pins'] == files[str(ordinal)], 'held prefix point inventory differs')
        visited_inventory.append({key: inventory[key] for key in ('pins', 'files', 'directories')})
        frame = dict(ordinal=ordinal, pins_sha=expectations['pins_sha'],
            registration_sha=expectations['registration_sha'], execution_binding=None)
        result = point.replay_point(roots/f'point_{ordinal:04d}', query, frame, files[str(ordinal)], outer_record, c_sources)
        reports.append(dict(ordinal=ordinal, hour=query.request.hour, role=query.request.role, query_sha=query.identity,
            request_sha=query.request.identity, evidence_ref=result['evidence_ref'], evidence_family=result['evidence_family'],
            replay_state=result['replay_state'], accepted_state_sha=core.digest(state),
            state_after_actual_slot=transitions[-1]['actual_slot'] if transitions else None,
            parent_query_sha=None if query.base_query is None else query.base_query.identity,
            parent_point_sha=None if query.base_point is None else core.digest(query.base_point),
            parent_economic_sha=None if query.base_economic is None else core.digest(query.base_economic)))
        return result['evidence']

    for index, hour in enumerate(hours):
        require(not state.stopped and state.next_hour == hour, 'accepted prefix cannot reach next hour')
        group = reference_requests(fixture, PLAN, CLEAN, METHOD, hour)
        require(group['reference_connection_shortfall_mw'] == 0, 'reference_connection_shortfall')
        reference = None;children = {};unresolved = False
        for request in group['requests']:
            query = core.bind(request) if reference is None else core.bind(request, reference.query, reference.point, reference.economic)
            evidence = replay(query)
            if evidence is None:
                stage, outcome, unresolved = 'reference_numeric', 'numeric_unresolved_reproduced', True
                break
            if reference is None: reference = evidence
            else: children[request.role] = evidence
        if unresolved: break
        evidence = causal.HourEvidence(reference, children.get('reference_raw_need'),
            children.get('recovery_min_meter'), children.get('recovery_max_meter'))
        prepared = causal.prepare_hour(fixture, state, evidence)
        proposal = causal.propose_hour(state, prepared)
        excluded = any(code.startswith('network_projection_') or code == 'connection_capacity' for code in proposal.violations)
        actual = None
        if not excluded:
            static_request = replace(reference.query.request, role='actual_P', outages=prepared.actual_outage,
                anchor_id=reference.query.request.identity)
            request = replace(static_request, meter_min=proposal.power_mw, meter_max=proposal.power_mw)
            actual = replay(core.bind(request, reference.query, reference.point, reference.economic), static_request)
            if actual is None:
                stage, outcome = 'actual_numeric', 'numeric_unresolved_reproduced'
                break
        candidate = causal.accept_hour(fixture, state, prepared, proposal, actual)
        independent = policy_audit.audit_execution(fixture, candidate)
        row = candidate.records[-1]
        if not row['actual_accepted'] or not row['proposal_ledger_applied']:
            require(states[index] is None, 'expected accepted state contradicts rejection')
            stage, outcome, attempted_state = 'actual_policy', 'policy_rejected', candidate
            attempted_audit = independent
            attempted_summary = causal.execution_summary(fixture, candidate)
            break
        require(actual is not None and candidate.next_hour == hour+1 and not candidate.stopped,
            'accepted actual failed to advance state')
        after_sha = core.digest(candidate)
        require(states[index] == after_sha, 'independent accepted state differs')
        transitions.append(dict(hour=hour, before_state_sha=core.digest(state), after_state_sha=after_sha,
            actual_slot=len(reports), actual_accepted=True, proposal_ledger_applied=True,
            power_mw=proposal.power_mw, deferred=proposal.deferred, recovery=proposal.recovery,
            remaining_debt=candidate.ledger.debt, independent_audit=independent))
        state = candidate
    require(len(reports) == len(slots), 'held future slots exceed terminal prefix')
    if outcome != 'bounded_prefix_complete':
        require(all(value is None for value in states[index:]), 'terminal failure contradicts held accepted state')
    summary = causal.execution_summary(fixture, state)
    require(codec.directory_identity(roots) == root_identity, 'prefix root identity changed')
    for report, before_inventory in zip(reports, visited_inventory):
        ordinal = report['ordinal']
        after_inventory = mechanical.inventory(roots/f'point_{ordinal:04d}')
        require({key: after_inventory[key] for key in before_inventory} == before_inventory,
            'visited point changed before prefix return')
    require(codec.directory_identity(roots) == root_identity, 'prefix root identity changed')
    require(_sources(expected_sources) == before_sources and core.digest(fixture) == fixture_sha
        and tuple(map(codec.canonical, (expectations, outer_record, expected_sources))) == held, 'prefix source fixture or caller changed')
    return dict(authority='DRAFT_NONAUTHORITATIVE', scope='bounded_saved_P1_actual_path_query_and_state_consistency',
        outcome=outcome, unresolved_stage=stage, state=state, state_sha=core.digest(state), accepted_prefix_summary=summary,
        attempted_state=attempted_state, attempted_state_sha=None if attempted_state is None else core.digest(attempted_state),
        attempted_audit=attempted_audit, attempted_summary=attempted_summary,
        visited_points=tuple(reports), accepted_transitions=tuple(transitions),
        expected_query_provenance_independently_verified_for_visited_points=True,
        expected_query_provenance_independently_verified=False, scientific_evidence_adopted=False,
        journal_replayed=False, full_fx_contract_verified=False, independent_139_verified=False,
        resource_admission=False, formal_result=False)
