"""Analytic orchestration oracles and one original saved P1 five-hour raw replay."""
from dataclasses import asdict, replace
from hashlib import sha256
from fractions import Fraction as Q
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments.staged_rts24_causal_examples_v1 import (
    analytic_fixture, analytic_hour, analytic_actual, analytic_point, analytic_economic, analytic_child,
)
from src import staged_rts24_saved_prefix_replay_v1 as d
from src.staged_rts24_causal_v1 import PointEvidence
from test_staged_rts24_p2_outer_observation_v2 import process as outer_process


@pytest.fixture(autouse=True)
def deny_execution_and_publication(monkeypatch):
    import subprocess
    import pyomo.environ as pyo
    from src import staged_rts24_journal_v2 as journal
    def denied(*a, **kw): pytest.fail('saved prefix requested native/spawn/journal/publication')
    for module, name in ((pyo, 'SolverFactory'), (d.point.backend, 'call_highs'), (d.point.backend, 'make_model'),
            (d.codec, 'publish'), (d.codec.EvidenceStore, 'put'), (subprocess, 'Popen')):
        monkeypatch.setattr(module, name, denied)
    for name in ('create_session', 'begin_step', 'commit_step', 'finish', 'reopen'):
        monkeypatch.setattr(journal, name, denied)


def slot(request, ordinal, dynamic=False):
    # Independent rendering of the historical schedule's public representation.
    return dict(ordinal=ordinal, hour=request.hour, role=request.role, objective=request.objective,
        outage=asdict(request.outages), request_sha=None if dynamic else request.identity,
        parent_request_sha=request.anchor_id, bound_query_sha=None,
        dynamic_reason='policy_power_and_parent_point' if dynamic else 'bound_parent_point' if request.anchor_id else None)


def analytic_case(tmp_path, monkeypatch, length=2, reject=False):
    fixture = replace(analytic_fixture(), first_hour=-2)
    business = json.loads(fixture.business_json);business['equipment'][0]['start'] = -2
    if reject:
        business['clean_paths']['early'][1] = '0'
        fixture = replace(fixture, parameters=replace(fixture.parameters, capacity=Q(100), call_ramp=Q(100)))
    fixture = replace(fixture, business_json=json.dumps(business, sort_keys=True))
    hours = tuple(range(-2, -2+length));root = tmp_path/'points';root.mkdir()
    state = d.causal.initialize_execution(fixture, d.PLAN, d.CLEAN, d.METHOD)
    initial = d.core.digest(state);states = [];slots = [];inventories = {};observed = []
    for hour in hours:
        if state.stopped:
            states.append(None)
            continue
        evidence = analytic_hour(fixture, state)
        for item in (evidence.reference, evidence.raw, evidence.lower, evidence.upper):
            if item is not None: slots.append(slot(item.query.request, len(slots)+1))
        prepared = d.causal.prepare_hour(fixture, state, evidence)
        proposal = d.causal.propose_hour(state, prepared)
        request = replace(evidence.reference.query.request, role='actual_P', outages=prepared.actual_outage,
            anchor_id=evidence.reference.query.request.identity)
        slots.append(slot(request, len(slots)+1, True))
        excluded = any(code.startswith('network_projection_') or code == 'connection_capacity' for code in proposal.violations)
        state = d.causal.accept_hour(fixture, state, prepared, proposal, None if excluded else analytic_actual(prepared, proposal))
        states.append(None if state.stopped else d.core.digest(state))
    for ordinal in range(1, len(slots)+1):
        folder = root/f'point_{ordinal:04d}';folder.mkdir();(folder/'fixture.json').write_bytes(b'analytic plumbing fixture')
        inventories[str(ordinal)] = d.mechanical.inventory(folder)['pins']
    def fake_point(point_root, expected_query, expected_frame, expected_files, outer_record, expected_sources):
        observed.append((expected_query, expected_frame.copy()))
        q = expected_query.request
        if q.role == 'reference_base_P0':
            p = analytic_point(expected_query, q.meter_min)
            evidence = PointEvidence(expected_query, p, economic=analytic_economic(expected_query, p))
        elif q.role == 'actual_P': evidence = PointEvidence(expected_query, analytic_point(expected_query, q.meter_min))
        else: evidence = analytic_child(expected_query)
        return dict(evidence=evidence, evidence_ref=d.codec.pack(evidence)[0],
            evidence_family='economic_kkt' if evidence.economic else 'child_lp_kkt' if evidence.child_lp else 'primal_point',
            replay_state='imported_replay_matches_saved')
    monkeypatch.setattr(d.point, 'replay_point', fake_point)
    expected = dict(fixture_sha=d.core.digest(fixture), initial_state_sha=initial, after_state_shas=tuple(states),
        pins_sha='a'*64, registration_sha='b'*64, slots=tuple(slots), point_files=inventories)
    return SimpleNamespace(root=root, fixture=fixture, hours=hours, expected=expected, outer=outer_process(),
        sources=d.source_pins(), observed=observed, fake=fake_point, final_state=state)


def run(case, **overrides):
    args = dict(points_root=case.root, fixture=case.fixture, hours=case.hours, expectations=case.expected,
        outer_record=case.outer, expected_sources=case.sources)
    args.update(overrides)
    return d.replay_prefix(**args)


def test_analytic_two_hour_actuals_alone_advance_independent_state(tmp_path, monkeypatch):
    case = analytic_case(tmp_path, monkeypatch)
    result = run(case)
    assert result['outcome'] == 'bounded_prefix_complete' and result['state'] == case.final_state
    assert [row['actual_slot'] for row in result['accepted_transitions']] == [4, 8]
    points = result['visited_points']
    assert all(row['state_after_actual_slot'] is None for row in points[:4])
    assert all(row['state_after_actual_slot'] == 4 for row in points[4:])
    assert all(row['accepted_state_sha'] == case.expected['after_state_shas'][0] for row in points[4:])
    for row, (query, frame) in zip(points, case.observed):
        assert row['query_sha'] == query.identity and frame['ordinal'] == row['ordinal']
        assert frame['execution_binding'] is None
        if query.request.role == 'actual_P':
            assert query.request.meter_min == query.request.meter_max == 100
            assert query.base_query.request.role == 'reference_base_P0'
    assert result['accepted_prefix_summary']['coverage_complete'] is False
    assert result['accepted_prefix_summary']['method_conditions_satisfied'] is result['accepted_prefix_summary']['full_replay_conditions_satisfied'] is None
    assert result['expected_query_provenance_independently_verified_for_visited_points'] is True
    for name in ('scientific_evidence_adopted', 'expected_query_provenance_independently_verified', 'journal_replayed',
            'full_fx_contract_verified', 'independent_139_verified', 'resource_admission', 'formal_result'):
        assert result[name] is False


@pytest.mark.parametrize('ordinal,stage', [(1, 'reference_numeric'), (2, 'reference_numeric'), (4, 'actual_numeric'),
    (5, 'reference_numeric'), (8, 'actual_numeric')])
def test_numeric_stops_without_filling_actual_or_future_state(tmp_path, monkeypatch, ordinal, stage):
    case = analytic_case(tmp_path, monkeypatch)
    case.expected['slots'] = case.expected['slots'][:ordinal]
    case.expected['point_files'] = {k: v for k, v in case.expected['point_files'].items() if int(k) <= ordinal}
    accepted = int(ordinal > 4)
    case.expected['after_state_shas'] = case.expected['after_state_shas'][:accepted]+(None,)*(2-accepted)
    def numeric(*args, **kwargs):
        if args[2]['ordinal'] == ordinal:
            case.observed.append((args[1], args[2]))
            return dict(evidence=None, evidence_ref=None, evidence_family=None, replay_state='numeric_unresolved_reproduced')
        return case.fake(*args, **kwargs)
    monkeypatch.setattr(d.point, 'replay_point', numeric)
    result = run(case)
    assert len(case.observed) == len(result['visited_points']) == ordinal
    assert result['outcome'] == 'numeric_unresolved_reproduced' and result['unresolved_stage'] == stage
    assert len(result['accepted_transitions']) == accepted and result['state'].next_hour == -2+accepted
    assert result['state_sha'] == (case.expected['after_state_shas'][0] if accepted else case.expected['initial_state_sha'])
    assert result['attempted_state'] is None
    assert result['attempted_state_sha'] is result['attempted_audit'] is result['attempted_summary'] is None


def test_policy_rejection_keeps_accepted_prefix_and_avoids_next_hour(tmp_path, monkeypatch):
    case = analytic_case(tmp_path, monkeypatch, length=5, reject=True)
    # At hour1 full deferral would fall below the generator's lower endpoint.
    assert case.final_state.stopped
    states = case.expected['after_state_shas']
    case.expected['slots'] = case.expected['slots'][:16]
    case.expected['point_files'] = {k: v for k, v in case.expected['point_files'].items() if int(k) <= 16}
    result = run(case)
    assert result['outcome'] == 'policy_rejected' and result['state'].next_hour == 1
    assert result['attempted_state'].stopped and result['attempted_state'].records[-1]['actual_accepted'] is False
    assert len(result['accepted_transitions']) == 3 and len(result['visited_points']) == 16
    assert result['state_sha'] == states[2]
    assert result['accepted_prefix_summary']['stopped'] is False
    assert result['attempted_state_sha'] == d.core.digest(result['attempted_state'])
    assert result['attempted_audit']['record_consistency_satisfied'] is True
    assert result['attempted_summary']['stopped'] is True
    assert 'network_projection_lower' in result['attempted_summary']['terminal_violations']
    assert len(result['attempted_summary']['unapplied_attempts']) == 1


@pytest.mark.parametrize('kind', ['current_state', 'future_state', 'future_slot'])
def test_terminal_numeric_cannot_contradict_held_success_or_future_slots(tmp_path, monkeypatch, kind):
    case = analytic_case(tmp_path, monkeypatch)
    if kind != 'future_slot':
        case.expected['slots'] = case.expected['slots'][:1]
        case.expected['point_files'] = {'1': case.expected['point_files']['1']}
    state = case.expected['after_state_shas']
    case.expected['after_state_shas'] = (state[0], None) if kind == 'current_state' else (None, state[1]) if kind == 'future_state' else (None, None)
    monkeypatch.setattr(d.point, 'replay_point', lambda *a, **kw: dict(evidence=None, evidence_ref=None,
        evidence_family=None, replay_state='numeric_unresolved_reproduced'))
    with pytest.raises(ValueError, match='(contradicts held accepted state|future slots)'): run(case)


@pytest.mark.parametrize('kind', ['future_state', 'future_slot'])
def test_policy_rejection_cannot_ignore_future_anchors(tmp_path, monkeypatch, kind):
    case = analytic_case(tmp_path, monkeypatch, length=5, reject=True)
    if kind == 'future_state':
        case.expected['slots'] = case.expected['slots'][:16]
        case.expected['point_files'].pop('17')
        case.expected['after_state_shas'] = case.expected['after_state_shas'][:-1]+('c'*64,)
    with pytest.raises(ValueError, match='(contradicts held accepted state|future slots)'): run(case)


@pytest.mark.parametrize('hours', [(), (-1,), (-2, 0), (-2, -1, 0, 1, 2, 3), (-2, True)])
def test_hour_budget_rejects_before_point_reads(tmp_path, monkeypatch, hours):
    case = analytic_case(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match='contiguous'): run(case, hours=hours)
    assert case.observed == []


@pytest.mark.parametrize('field', ['fixture_sha', 'initial_state_sha'])
def test_independent_fixture_and_initial_state_are_required(tmp_path, monkeypatch, field):
    case = analytic_case(tmp_path, monkeypatch);case.expected[field] = 'c'*64
    with pytest.raises(ValueError, match='(fixture|initial state)'): run(case)
    assert case.observed == []


def test_accepted_state_mismatch_stops_before_next_hour_query(tmp_path, monkeypatch):
    case = analytic_case(tmp_path, monkeypatch)
    case.expected['after_state_shas'] = ('c'*64, case.expected['after_state_shas'][1])
    with pytest.raises(ValueError, match='accepted state differs'): run(case)
    assert len(case.observed) == 4


@pytest.mark.parametrize('change', ['role', 'request_sha', 'ordinal_bool', 'dynamic_sha'])
def test_static_slots_are_independently_checked(tmp_path, monkeypatch, change):
    case = analytic_case(tmp_path, monkeypatch)
    index = 3 if change == 'dynamic_sha' else 0
    value = case.expected['slots'][index]
    if change == 'ordinal_bool': value['ordinal'] = True
    elif change == 'dynamic_sha': value['request_sha'] = 'c'*64
    else: value[change] = 'incorrect'
    with pytest.raises(ValueError, match='schedule differs'): run(case)
    assert len(case.observed) == index


def test_unknown_whole_job_quiet_blocks_all_source_and_point_reads(tmp_path, monkeypatch):
    case = analytic_case(tmp_path, monkeypatch);case.outer['quiescence_witness']['status'] = 'unknown'
    monkeypatch.setattr(d, '_sources', lambda *a: pytest.fail('source read before whole quiet'))
    with pytest.raises(ValueError): run(case)
    assert case.observed == []


@pytest.mark.parametrize('kind', ['bytes', 'files'])
def test_combined_prefix_budget_precedes_point_reads(tmp_path, monkeypatch, kind):
    case = analytic_case(tmp_path, monkeypatch)
    if kind == 'bytes':
        value = dict(case.expected['point_files']['1']['fixture.json'], bytes=8*1024*1024)
        case.expected['point_files']['1'] = {str(i): dict(value) for i in range(9)}
    else:
        pin = case.expected['point_files']['1']['fixture.json']
        case.expected['point_files'] = {key: {str(i): dict(pin) for i in range(1025)} for key in case.expected['point_files']}
    with pytest.raises(ValueError, match='combined prefix'): run(case)
    assert case.observed == []


@pytest.mark.parametrize('target', ['caller', 'fixture', 'early_point', 'source'])
def test_prefix_return_bookends_detect_late_changes(tmp_path, monkeypatch, target):
    case = analytic_case(tmp_path, monkeypatch)
    def changed(*args, **kwargs):
        result = case.fake(*args, **kwargs)
        if args[2]['ordinal'] == 8:
            if target == 'caller': case.expected['registration_sha'] = 'c'*64
            elif target == 'fixture': object.__setattr__(case.fixture, 'source_identity', 'c'*64)
            elif target == 'early_point': (case.root/'point_0001/fixture.json').write_bytes(b'changed')
            else: case.sources['src/staged_rts24_saved_prefix_replay_v1.py']['sha256'] = 'c'*64
        return result
    monkeypatch.setattr(d.point, 'replay_point', changed)
    with pytest.raises((ValueError, AssertionError)): run(case)


@pytest.mark.parametrize('target', ['root', 'point_directory', 'point_file'])
def test_same_byte_identity_replacement_is_rejected(tmp_path, monkeypatch, target):
    import shutil
    case = analytic_case(tmp_path, monkeypatch)
    def replaced(*args, **kwargs):
        result = case.fake(*args, **kwargs)
        if args[2]['ordinal'] == 8:
            path = case.root if target == 'root' else case.root/'point_0001' if target == 'point_directory' else case.root/'point_0001/fixture.json'
            saved = tmp_path/'preserved_original'
            assert path.absolute().is_relative_to(tmp_path.absolute()) and saved.absolute().is_relative_to(tmp_path.absolute())
            path.rename(saved)
            if target == 'point_file': path.write_bytes(saved.read_bytes())
            else: shutil.copytree(saved, path)
            assert path.stat().st_ino != saved.stat().st_ino
        return result
    monkeypatch.setattr(d.point, 'replay_point', replaced)
    with pytest.raises(ValueError, match='(identity changed|visited point changed)'): run(case)


@pytest.mark.parametrize('module_name', ['src.staged_rts24_causal_v2', 'src.staged_rts24_causal_audit_v2',
    'src.staged_rts24_reference_queries_v1', 'src.staged_rts24_saved_prefix_replay_v1'])
def test_loaded_policy_sources_are_bound(tmp_path, monkeypatch, module_name):
    import sys
    case = analytic_case(tmp_path, monkeypatch)
    monkeypatch.setattr(sys.modules[module_name], '__file__', str(tmp_path/'foreign.py'))
    with pytest.raises(ValueError, match='loaded prefix module path'): run(case)
    assert case.observed == []


def test_original_saved_P1_five_hours_rebuild_queries_raw_and_state_with_counts(monkeypatch):
    p1 = d.ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'
    anchor = p1.parent/'p1_execution_review_01/postcheck_03.stdout.json'
    anchor_raw = anchor.read_bytes()
    assert sha256(anchor_raw).hexdigest() == 'c6a25cd96c8a4a2cf293d41fe51bc7905db63fbc35253076f97e9239a4f22473'
    files = json.loads(anchor_raw)['p1_files'];assert len(files) == 683
    def preserve(): assert all(d.mechanical.pin((p1/name).read_bytes()) == value for name, value in files.items())
    preserve()
    fixture = d.core.load_fixture();start = json.loads((p1/'start.json').read_bytes())
    bindings = [json.loads((p1/f'trusted_prefixes/prefix_{n:06d}.json').read_bytes()) for n in range(6)]
    expected = dict(fixture_sha=d.core.digest(fixture), initial_state_sha=bindings[0]['known_state_sha'],
        after_state_shas=tuple(b['known_state_sha'] for b in bindings[1:]), pins_sha=d.core.digest(start['pins']),
        registration_sha=start['registration_sha'], slots=tuple(json.loads((p1/'request_schedule.json').read_bytes())[:21]),
        point_files={str(i): {n[len(f'points/point_{i:04d}/'):]: v for n, v in files.items()
            if n.startswith(f'points/point_{i:04d}/')} for i in range(1, 22)})
    source = d.source_pins();counts = dict(compile=0, snapshot=0, import_snapshot=0, execution_audit=0,
        history_rows=0, prepare=0, propose=0, reference_requests=0, source_reads=0, point_reads=0)
    def counter(module, name, key):
        original = getattr(module, name)
        def wrapped(*a, **kw):
            counts[key] += 1
            if key == 'execution_audit': counts['history_rows'] += len(a[1].records)
            return original(*a, **kw)
        monkeypatch.setattr(module, name, wrapped)
    for module, name, key in ((d.point.numeric, 'compile_problem', 'compile'),
            (d.point.backend, 'snapshot_from_raw', 'snapshot'), (d.point.numeric, 'import_snapshot', 'import_snapshot'),
            (d.policy_audit, 'audit_execution', 'execution_audit'), (d.causal, 'prepare_hour', 'prepare'),
            (d.causal, 'propose_hour', 'propose')): counter(module, name, key)
    original_ref = d.reference_requests
    def reference(*a, **kw): counts['reference_requests'] += 1;return original_ref(*a, **kw)
    for module in (d, d.causal, d.policy_audit): monkeypatch.setattr(module, 'reference_requests', reference)
    original_read = d.codec.read_bytes;original_bounded = d.mechanical.bounded_file_bytes
    def read(path, *a, **kw):
        counts['point_reads' if Path(path).is_relative_to(p1) else 'source_reads'] += 1
        return original_read(path, *a, **kw)
    def bounded(path, *a, **kw):
        assert Path(path).is_relative_to(p1/'points');counts['point_reads'] += 1
        return original_bounded(path, *a, **kw)
    monkeypatch.setattr(d.codec, 'read_bytes', read);monkeypatch.setattr(d.mechanical, 'bounded_file_bytes', bounded)
    result = d.replay_prefix(p1/'points', fixture, (-2, -1, 0, 1, 2), expected,
        json.loads((p1/'launcher.json').read_bytes()), source)
    objects = sum(n.startswith('cas/objects/') for inventory in expected['point_files'].values() for n in inventory)
    assert counts == dict(compile=42, snapshot=21, import_snapshot=21, execution_audit=16, history_rows=40,
        prepare=10, propose=10, reference_requests=55, source_reads=1912, point_reads=8*objects+32*21)
    assert result['outcome'] == 'bounded_prefix_complete' and len(result['accepted_transitions']) == 5
    assert result['state_sha'] == bindings[-1]['known_state_sha'] and result['state'].next_hour == 3
    assert [r['actual_slot'] for r in result['accepted_transitions']] == [4, 8, 12, 17, 21]
    assert all(result['visited_points'][i-1]['role'] == 'actual_P' for i in (4, 8, 12, 17, 21))
    assert result['accepted_transitions'][3]['deferred'] > 0 and result['accepted_transitions'][4]['recovery'] > 0
    summary = result['accepted_prefix_summary']
    assert summary['coverage_complete'] is False and summary['method_conditions_satisfied'] is summary['full_replay_conditions_satisfied'] is None
    assert result['scientific_evidence_adopted'] is result['journal_replayed'] is result['formal_result'] is False
    preserve();assert anchor.read_bytes() == anchor_raw
    print(json.dumps(dict(oracle='saved_P1_independent_query_and_accepted_state', simulated_hours=5, replayed_points=21,
        accepted_state_shas=[row['after_state_sha'] for row in result['accepted_transitions']],
        actual_slots=[row['actual_slot'] for row in result['accepted_transitions']],
        accepted_transitions=d.core.plain(result['accepted_transitions']), accepted_prefix_summary=d.core.plain(summary),
        queries=[{k: v for k, v in row.items()} for row in result['visited_points']],
        calls=counts, cas_objects=objects, P1_683_files_unchanged=True, new_native_calls=0,
        scientific_evidence_adopted=False, journal_replayed=False, resource_admission=False, formal_result=False)))
