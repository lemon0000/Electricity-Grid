"""Read-only representative F/X rows rebuilt from independent normal/firm/raw queries."""
from dataclasses import asdict
from pathlib import Path
import sys

from src import staged_rts24_saved_point_replay_v1 as point

core, codec, mechanical = point.core, point.codec, point.mechanical
require = codec.require
ROOT = point.ROOT
SOURCES = point.SOURCES + ('src/staged_rts24_saved_contract_replay_v1.py',
    'tests/test_staged_rts24_saved_contract_replay_v1.py',
    'docs/plan/staged_deliverability_c_saved_contract_replay_contract_v1.md')
PLAN, CLEAN, METHOD = 'on_time', 'early', 'full_temporal'
ORDINALS = tuple(range(22, 32))


def source_pins():
    return {name: mechanical.pin(codec.read_bytes(ROOT/name)) for name in SOURCES}


def _sources(expected):
    require(type(expected) is dict and set(expected) == set(SOURCES), 'closed contract source group required')
    for value in expected.values(): mechanical.checked_pin(value)
    actual = source_pins()
    require(actual == expected, 'contract source bytes changed')
    for name in SOURCES:
        if not name.startswith('src/') or not name.endswith('.py'): continue
        module = sys.modules.get(name[:-3].replace('/', '.').removesuffix('.__init__'))
        require(module is not None and type(getattr(module, '__file__', None)) is str
            and Path(module.__file__).absolute() == (ROOT/name).absolute(), 'loaded contract module path differs')
        require(mechanical.pin(codec.read_bytes(module.__file__)) == actual[name], 'loaded contract source differs')
    return actual


def _row_file(path, expected_pin):
    directories = codec.directory_identity(path.parent)
    def identity():
        info = codec.ordinary(path)
        return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns
    before = identity()
    require(before[2] == expected_pin['bytes'] and before[2] <= 8*1024*1024, 'row size differs from held budget')
    raw = mechanical.bounded_file_bytes(path, before)
    require(before == identity() and directories == codec.directory_identity(path.parent), 'row file identity changed')
    require(mechanical.pin(raw) == expected_pin, 'held contract row bytes differ')
    return dict(raw=raw, identity=before, directories=directories)


def _slot(request, ordinal):
    return dict(ordinal=ordinal, hour=request.hour, role=request.role, objective=request.objective,
        outage=asdict(request.outages), request_sha=request.identity, parent_request_sha=request.anchor_id,
        bound_query_sha=None, dynamic_reason='bound_parent_point' if request.anchor_id else None)


def replay_contracts(points_root, rows_path, fixture, expectations, outer_record, expected_sources):
    """No actual-policy/journal replay or complete F/X adoption is implied."""
    point._outer(outer_record)
    before_sources = _sources(expected_sources)
    mechanical.keys(expectations, 'fixture_sha pins_sha registration_sha slots point_files rows_pin')
    for key in ('fixture_sha', 'pins_sha', 'registration_sha'): mechanical.sha(expectations[key])
    require(type(fixture) is core.Fixture and core.digest(fixture) == expectations['fixture_sha'], 'independent contract fixture differs')
    for data in (fixture.before, fixture.after):
        require(1 <= len(data.buses) <= 24 and 1 <= len(data.generators) <= 33 and len(data.branches) <= 38,
            'contract fixture exceeds network budget')
    require(type(fixture.selected) is tuple and 2 <= len(fixture.selected) <= 71, 'bounded selected N-1 set required')
    branches = [o for o in fixture.selected if o.branches]
    generators = [o for o in fixture.selected if o.generators]
    require(branches and generators, 'both representative outage families required')
    outages = (min(branches, key=lambda o: o.branches), min(generators, key=lambda o: o.generators))
    slots, files = expectations['slots'], expectations['point_files']
    require(type(slots) is tuple and len(slots) == 10 and type(files) is dict
        and set(files) == {str(i) for i in ORDINALS}, 'closed ten-point contract prefix required')
    mechanical.checked_pin(expectations['rows_pin'])
    total_files, total_bytes = 1, expectations['rows_pin']['bytes']
    for inventory in files.values():
        require(type(inventory) is dict and 1 <= len(inventory) <= 8192, 'held contract point pins required')
        total_files += len(inventory)
        for name, value in inventory.items():
            mechanical.relative(name);mechanical.checked_pin(value);total_bytes += value['bytes']
    require(total_files <= 8192 and total_bytes <= 64*1024*1024, 'combined contract file budget exceeded')
    held = tuple(map(codec.canonical, (expectations, outer_record, expected_sources)))
    fixture_sha = core.digest(fixture)
    roots = codec.directory_chain(Path(points_root).absolute());root_identity = codec.directory_identity(roots)
    row_path = Path(rows_path).absolute();saved_rows = _row_file(row_path, expectations['rows_pin'])
    expected_rows = codec.parse(saved_rows['raw'])
    require(type(expected_rows) is list and len(expected_rows) == 4, 'four saved contract rows required')
    for row in expected_rows:
        mechanical.keys(row, 'hour outage normal_query firm_query raw_query raw_curtailment_mw firm_audit legal_X')
    reports, visited, rows = [], [], []
    c_sources = {name: before_sources[name] for name in point.SOURCES}

    def replay(query, family):
        ordinal = 22+len(reports)
        require(ordinal in ORDINALS and codec.canonical(slots[ordinal-22]) == codec.canonical(_slot(query.request, ordinal)),
            'independent contract schedule differs')
        require(codec.directory_identity(roots) == root_identity, 'contract point root identity changed')
        inventory = mechanical.inventory(roots/f'point_{ordinal:04d}')
        require(inventory['pins'] == files[str(ordinal)], 'held contract point inventory differs')
        visited.append({key: inventory[key] for key in ('pins', 'files', 'directories')})
        frame = dict(ordinal=ordinal, pins_sha=expectations['pins_sha'], registration_sha=expectations['registration_sha'], execution_binding=None)
        result = point.replay_point(roots/f'point_{ordinal:04d}', query, frame, files[str(ordinal)], outer_record, c_sources)
        require(result['evidence'] is not None and result['evidence_family'] == family
            and result['replay_state'] == 'imported_replay_matches_saved', 'unresolved contract point cannot supply saved successful row')
        reports.append(dict(ordinal=ordinal, hour=query.request.hour, role=query.request.role,
            request_sha=query.request.identity, query_sha=query.identity, evidence_ref=result['evidence_ref'], evidence_family=family,
            parent_query_sha=None if query.base_query is None else query.base_query.identity,
            parent_point_sha=None if query.base_point is None else core.digest(query.base_point),
            parent_economic_sha=None if query.base_economic is None else core.digest(query.base_economic)))
        return result['evidence']

    for hour in (1, 2):
        group = core.hour_requests(fixture, PLAN, CLEAN, METHOD, hour)
        normal_request = group['requests'][0]
        require(normal_request.role == 'normal_contract_C', 'full-C root role differs')
        normal = replay(core.bind(normal_request), 'economic_kkt')
        for outage in outages:
            requests = [q for q in group['requests'] if q.outages == outage and q.role in ('fault_firm_F', 'fault_raw_need')]
            require([q.role for q in requests] == ['fault_firm_F', 'fault_raw_need'], 'representative firm/raw requests differ')
            firm = replay(core.bind(requests[0], normal.query, normal.point, normal.economic), 'primal_point')
            firm_audit = point.audit.audit_point(firm.query, firm.point)
            require(firm_audit['point_constraints_satisfied'], 'independent firm point audit failed')
            raw = replay(core.bind(requests[1], normal.query, normal.point, normal.economic), 'child_lp_kkt')
            row = dict(hour=hour, outage=asdict(outage), normal_query=normal.query.identity,
                firm_query=firm.query.identity, raw_query=raw.query.identity, raw_curtailment_mw=raw.point.curtailment_mw,
                firm_audit=firm_audit,
                legal_X=point.audit.audit_legal_x(raw.query, raw.point, *raw.query.request.rights))
            require(codec.canonical(row) == codec.canonical(expected_rows[len(rows)]), 'independently rebuilt contract row differs')
            rows.append(row)
    require(len(reports) == 10 and len(rows) == 4, 'contract replay ended outside fixed scope')
    require(codec.directory_identity(roots) == root_identity, 'contract point root identity changed')
    for report, before in zip(reports, visited):
        after = mechanical.inventory(roots/f"point_{report['ordinal']:04d}")
        require({key: after[key] for key in before} == before, 'visited contract point changed')
    require(codec.directory_identity(roots) == root_identity and _row_file(row_path, expectations['rows_pin']) == saved_rows,
        'contract root or row bookend changed')
    require(_sources(expected_sources) == before_sources and core.digest(fixture) == fixture_sha
        and tuple(map(codec.canonical, (expectations, outer_record, expected_sources))) == held, 'contract source fixture or caller changed')
    return dict(authority='DRAFT_NONAUTHORITATIVE', scope='four_saved_static_DC_representative_FX_rows_numeric_consistency',
        rows=tuple(rows), visited_points=tuple(reports), saved_representative_rows_match=True,
        expected_query_provenance_independently_verified_for_visited_points=True,
        expected_query_provenance_independently_verified=False, scientific_evidence_adopted=False,
        full_fx_contract_verified=False, independent_139_verified=False, journal_replayed=False,
        resource_admission=False, formal_result=False)
