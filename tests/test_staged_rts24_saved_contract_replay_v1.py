"""Handwritten F/X orchestration points and a separate real saved 10-point C replay."""
from dataclasses import asdict, replace
from fractions import Fraction as Q
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments.staged_rts24_causal_examples_v1 import analytic_fixture, analytic_point
from src import staged_rts24_saved_contract_replay_v1 as d
from src.staged_rts24_causal_v1 import PointEvidence
from test_staged_rts24_p2_outer_observation_v2 import process as outer_process


@pytest.fixture(autouse=True)
def deny_execution_and_publication(monkeypatch):
    import subprocess
    import pyomo.environ as pyo
    from src import staged_rts24_journal_v2 as journal
    def denied(*a, **kw): pytest.fail('contract replay requested native/spawn/journal/publication')
    for module, name in ((pyo, 'SolverFactory'), (d.point.backend, 'call_highs'), (d.point.backend, 'make_model'),
            (d.codec, 'publish'), (d.codec.EvidenceStore, 'put'), (subprocess, 'Popen')):
        monkeypatch.setattr(module, name, denied)
    for name in ('create_session', 'begin_step', 'commit_step', 'finish', 'reopen'):
        monkeypatch.setattr(journal, name, denied)


def hand(query, raw_curtailment=None):
    q = query.request
    meter = q.meter_max
    curtail = meter-60 if q.role == 'fault_raw_need' and q.outages.branches else Q(0)
    if q.role == 'fault_raw_need' and raw_curtailment is not None:curtail = Q(raw_curtailment)
    witness = analytic_point(query, meter, curtail)
    net = float(meter-curtail)
    generation = ((0, 0.), (1, net)) if q.outages.generators else ((0, net/2), (1, net/2))
    witness = replace(witness, generation_mw=generation)
    economic = None
    if query.base_query is None:
        generator = q.data.generators[0]
        gradient = 2*(generator.cost_quadratic+1e-8)*net/2+generator.cost_linear
        economic = d.core.EconomicEvidence(query.identity, d.core.digest(witness), tuple((i, -gradient) for i in (1, 2, 3)),
            tuple((i, 0.) for i in (0, 1, 2)), ((0, 0.), (1, 0.)), ((0, 0.), (1, 0.)),
            tuple((i, 0.) for i in (0, 1, 2)), tuple((i, 0.) for i in (0, 1, 2)))
    # This C stand-in deliberately supplies no child LP certificate. It tests
    # orchestration and original primal predicates, never raw/KKT import.
    return PointEvidence(query, witness, economic=economic)


def oracle_slot(request, ordinal):
    return dict(ordinal=ordinal, hour=request.hour, role=request.role, objective=request.objective,
        outage=asdict(request.outages), request_sha=request.identity, parent_request_sha=request.anchor_id,
        bound_query_sha=None, dynamic_reason='bound_parent_point' if request.anchor_id else None)


def case(tmp_path, monkeypatch, firm=20):
    fixture = analytic_fixture();generator = replace(fixture.before.generators[0], p_min_mw=0.)
    data = replace(fixture.before, generators=(generator, replace(generator, index=1)))
    outages = (d.core.Outage('branch_2', (2,)), d.core.Outage('generator_0', (), (0,)))
    fixture = replace(fixture, before=data, after=data, selected=outages,
        rights_before=(Q(firm), Q(150-firm)), rights_after=(Q(firm), Q(150-firm)))
    points = tmp_path/'points';points.mkdir();rows_directory = tmp_path/'row_records';rows_directory.mkdir()
    rows_path = rows_directory/'contract_rows.json'
    rows = [];slots = [];expected_evidence = []
    for hour in (1, 2):
        group = d.core.hour_requests(fixture, d.PLAN, d.CLEAN, d.METHOD, hour)
        normal = hand(d.core.bind(group['requests'][0]))
        expected_evidence.append(normal);slots.append(oracle_slot(normal.query.request, 21+len(expected_evidence)))
        for outage in outages:
            requests = [r for r in group['requests'] if r.outages == outage and r.role in ('fault_firm_F', 'fault_raw_need')]
            a, b = [hand(d.core.bind(r, normal.query, normal.point, normal.economic)) for r in requests]
            for item in (a, b):
                expected_evidence.append(item);slots.append(oracle_slot(item.query.request, 21+len(expected_evidence)))
            rows.append(dict(hour=hour, outage=asdict(outage), normal_query=normal.query.identity,
                firm_query=a.query.identity, raw_query=b.query.identity, raw_curtailment_mw=b.point.curtailment_mw,
                firm_audit=d.point.audit.audit_point(a.query, a.point),
                legal_X=d.point.audit.audit_legal_x(b.query, b.point, *b.query.request.rights)))
    rows_path.write_bytes(d.codec.canonical(rows));files = {}
    for ordinal in d.ORDINALS:
        folder = points/f'point_{ordinal:04d}';folder.mkdir();(folder/'fixture.json').write_bytes(b'hand points; not numeric import')
        files[str(ordinal)] = d.mechanical.inventory(folder)['pins']
    observed = []
    def fake(point_root, expected_query, frame, expected_files, outer, sources):
        observed.append((expected_query, frame.copy()))
        evidence = hand(expected_query)
        family = 'economic_kkt' if expected_query.base_query is None else 'primal_point' if expected_query.request.objective == 'economic' else 'child_lp_kkt'
        return dict(evidence=evidence, evidence_ref=d.codec.pack(evidence)[0], evidence_family=family,
            replay_state='imported_replay_matches_saved')
    monkeypatch.setattr(d.point, 'replay_point', fake)
    expected = dict(fixture_sha=d.core.digest(fixture), pins_sha='a'*64, registration_sha='b'*64,
        slots=tuple(slots), point_files=files, rows_pin=d.mechanical.pin(rows_path.read_bytes()))
    return SimpleNamespace(points=points, row_path=rows_path, fixture=fixture, expected=expected,
        outer=outer_process(), sources=d.source_pins(), rows=rows, observed=observed, fake=fake, evidence=expected_evidence)


def run(c, **overrides):
    args = dict(points_root=c.points, rows_path=c.row_path, fixture=c.fixture, expectations=c.expected,
        outer_record=c.outer, expected_sources=c.sources)
    args.update(overrides)
    return d.replay_contracts(**args)


def test_hand_primal_oracle_binds_normal_full_C_firm_F_and_unclipped_raw(tmp_path, monkeypatch):
    c = case(tmp_path, monkeypatch);result = run(c)
    assert len(result['rows']) == 4 and len(c.observed) == 10
    assert [r['ordinal'] for r in result['visited_points']] == list(d.ORDINALS)
    for row in result['rows']:
        assert row['firm_audit']['point_constraints_satisfied'] is True
        assert row['legal_X'] == dict(point_legal_under_X=True, minimum_established=False,
            independent_firm_point_still_required=True, temporal_backing='not_established')
        assert row['raw_curtailment_mw'] == (90. if row['outage']['branches'] else 0.)
    for query, frame in c.observed:
        q = query.request
        assert frame['execution_binding'] is None
        if q.role == 'normal_contract_C': assert q.meter_min == q.meter_max == 150 and query.base_query is None
        else:
            assert query.base_query.request.role == 'normal_contract_C' and query.base_query.request.hour == q.hour
            assert q.meter_min == q.meter_max == (20 if q.role == 'fault_firm_F' else 150)
            assert q.curtailment_max == (0 if q.role == 'fault_firm_F' else 150)
    for name in ('scientific_evidence_adopted', 'expected_query_provenance_independently_verified',
            'full_fx_contract_verified', 'independent_139_verified', 'journal_replayed', 'resource_admission', 'formal_result'):
        assert result[name] is False


def test_original_negative_predicates_stay_false_under_C_standin(tmp_path, monkeypatch):
    # Firm remains primal-valid. The stand-in's deliberately nonoptimal raw
    # point supplies no KKT claim; this only checks the original legal-X predicate.
    c = case(tmp_path, monkeypatch)
    for row_index,item_index in ((0,2),(2,7)):
        raw = hand(c.evidence[item_index].query,141)
        assert d.point.audit.audit_point(raw.query,raw.point)['point_constraints_satisfied'] is True
        c.rows[row_index]['raw_curtailment_mw'] = 141.
        c.rows[row_index]['legal_X'] = d.point.audit.audit_legal_x(raw.query,raw.point,*raw.query.request.rights)
    c.row_path.write_bytes(d.codec.canonical(c.rows));c.expected['rows_pin'] = d.mechanical.pin(c.row_path.read_bytes())
    def fake(*args,**kw):
        result = c.fake(*args,**kw)
        if args[1].request.role == 'fault_raw_need' and args[1].request.outages.branches:
            raw = hand(args[1],141);result.update(evidence=raw,evidence_ref=d.codec.pack(raw)[0])
        return result
    monkeypatch.setattr(d.point,'replay_point',fake)
    result = run(c)
    for row in (result['rows'][0], result['rows'][2]):
        assert row['firm_audit']['point_constraints_satisfied'] is True
        assert row['legal_X']['point_legal_under_X'] is False
        assert row['raw_curtailment_mw'] == 141. and row['legal_X']['minimum_established'] is False
    assert result['full_fx_contract_verified'] is result['scientific_evidence_adopted'] is False


def test_original_numeric_import_and_contract_replay_reject_invalid_firm(tmp_path,monkeypatch):
    from test_staged_rts24_numeric_interface_v1 import raw_snapshot
    c = case(tmp_path,monkeypatch,firm=120);firm = c.evidence[1]
    assert d.point.audit.audit_point(firm.query,firm.point)['point_constraints_satisfied'] is False
    problem,snapshot = raw_snapshot(firm)
    with pytest.raises(ValueError,match='numeric point audit failed'):
        d.point.numeric.import_snapshot(firm.query,problem,snapshot)
    with pytest.raises(ValueError,match='independent firm point audit failed'):run(c)
    assert len(c.observed) == 2


@pytest.mark.parametrize('ordinal', [22, 23, 24, 26, 31])
def test_numeric_unresolved_cannot_supply_success_rows_or_generate_later_points(tmp_path, monkeypatch, ordinal):
    c = case(tmp_path, monkeypatch)
    def unresolved(*args, **kw):
        result = c.fake(*args, **kw)
        if args[2]['ordinal'] == ordinal: result.update(evidence=None, evidence_ref=None, evidence_family=None, replay_state='numeric_unresolved_reproduced')
        return result
    monkeypatch.setattr(d.point, 'replay_point', unresolved)
    with pytest.raises(ValueError, match='unresolved contract point'): run(c)
    assert len(c.observed) == ordinal-21


@pytest.mark.parametrize('field', ['hour', 'outage', 'normal_query', 'raw_curtailment_mw', 'firm_residual', 'legal_X', 'minimum'])
def test_saved_audit_is_compared_to_independent_raw_derived_row(tmp_path, monkeypatch, field):
    c = case(tmp_path, monkeypatch)
    row = c.rows[0]
    if field == 'firm_residual': row['firm_audit']['residuals']['balance_mw'] = 1.
    elif field == 'legal_X': row['legal_X']['point_legal_under_X'] = False
    elif field == 'minimum': row['legal_X']['minimum_established'] = True
    elif field == 'outage': row['outage']['name'] = 'other'
    elif field == 'normal_query': row[field] = 'c'*64
    else: row[field] = 1000
    c.row_path.write_bytes(d.codec.canonical(c.rows));c.expected['rows_pin'] = d.mechanical.pin(c.row_path.read_bytes())
    with pytest.raises(ValueError, match='rebuilt contract row differs'): run(c)
    assert len(c.observed) == 3


@pytest.mark.parametrize('change', ['ordinal_bool', 'parent', 'role', 'outage'])
def test_schedule_is_generated_from_frozen_policy_not_same_CAS(tmp_path, monkeypatch, change):
    c = case(tmp_path, monkeypatch);index = 0 if change == 'ordinal_bool' else 1
    slot = c.expected['slots'][index]
    if change == 'ordinal_bool': slot['ordinal'] = True
    elif change == 'parent': slot['parent_request_sha'] = 'c'*64
    elif change == 'role': slot['role'] = 'actual_P'
    else: slot['outage']['generators'] = [0]
    with pytest.raises(ValueError, match='schedule differs'): run(c)
    assert len(c.observed) == index


@pytest.mark.parametrize('kind', ['fixture', 'rows_pin', 'bytes', 'files', 'missing_point', 'future_slot', 'outage_family'])
def test_closed_input_and_budget_rejection_before_point_reads(tmp_path, monkeypatch, kind):
    c = case(tmp_path, monkeypatch)
    if kind == 'fixture': c.expected['fixture_sha'] = 'c'*64
    elif kind == 'rows_pin': c.expected['rows_pin']['sha256'] = 'c'*64
    elif kind == 'missing_point': c.expected['point_files'].pop('31')
    elif kind == 'future_slot': c.expected['slots'] += (c.expected['slots'][-1],)
    elif kind == 'outage_family':
        c.fixture = replace(c.fixture, selected=(c.fixture.selected[0], c.fixture.selected[0]))
        c.expected['fixture_sha'] = d.core.digest(c.fixture)
    elif kind == 'bytes':
        p = dict(next(iter(c.expected['point_files']['22'].values())), bytes=8*1024*1024)
        c.expected['point_files']['22'] = {str(i): dict(p) for i in range(9)}
    else:
        p = next(iter(c.expected['point_files']['22'].values()))
        c.expected['point_files'] = {key: {str(i): dict(p) for i in range(820)} for key in c.expected['point_files']}
    with pytest.raises(ValueError): run(c)
    assert c.observed == []


def test_quiet_unknown_precedes_source_row_and_point_reads(tmp_path, monkeypatch):
    c = case(tmp_path, monkeypatch);c.outer['quiescence_witness']['status'] = 'unknown'
    monkeypatch.setattr(d, '_sources', lambda *a: pytest.fail('source read before quiet'))
    monkeypatch.setattr(d, '_row_file', lambda *a: pytest.fail('row read before quiet'))
    with pytest.raises(ValueError): run(c)
    assert c.observed == []


@pytest.mark.parametrize('kind', ['size_mismatch', 'over_8MiB'])
def test_actual_row_size_must_match_held_budget_before_any_content_read(tmp_path, monkeypatch, kind):
    c = case(tmp_path, monkeypatch)
    c.row_path.write_bytes(c.row_path.read_bytes()+b' ' if kind == 'size_mismatch' else b'x'*(8*1024*1024+1))
    original_read = d.codec.read_bytes
    def read(path,*a,**kw):
        assert Path(path) != c.row_path, 'row content helper called before budget rejection'
        return original_read(path,*a,**kw)
    monkeypatch.setattr(d.codec,'read_bytes',read)
    monkeypatch.setattr(d.mechanical,'bounded_file_bytes',lambda *a,**kw: pytest.fail('bounded reader called before row budget rejection'))
    with pytest.raises(ValueError,match='row size differs'):run(c)
    assert c.observed == []


@pytest.mark.parametrize('target', ['caller', 'fixture', 'source', 'early_bytes', 'row_bytes', 'root', 'point_directory', 'point_file', 'row_file', 'row_directory'])
def test_late_bookends_and_identical_byte_identity_replacement(tmp_path, monkeypatch, target):
    import shutil
    c = case(tmp_path, monkeypatch)
    def changed(*args, **kw):
        result = c.fake(*args, **kw)
        if args[2]['ordinal'] == 31:
            if target == 'caller': c.expected['registration_sha'] = 'c'*64
            elif target == 'fixture': object.__setattr__(c.fixture, 'source_identity', 'c'*64)
            elif target == 'source': c.sources['src/staged_rts24_saved_contract_replay_v1.py']['sha256'] = 'c'*64
            elif target == 'early_bytes': (c.points/'point_0022/fixture.json').write_bytes(b'changed')
            elif target == 'row_bytes': c.row_path.write_bytes(b'changed')
            else:
                path = c.points if target == 'root' else c.points/'point_0022' if target == 'point_directory' else c.row_path.parent if target == 'row_directory' else c.row_path if target == 'row_file' else c.points/'point_0022/fixture.json'
                saved = tmp_path/'preserved_original'
                assert path.absolute().is_relative_to(tmp_path.absolute()) and saved.absolute().is_relative_to(tmp_path.absolute())
                path.rename(saved)
                if target in ('root', 'point_directory', 'row_directory'): shutil.copytree(saved, path)
                else: path.write_bytes(saved.read_bytes())
                assert path.stat().st_ino != saved.stat().st_ino
        return result
    monkeypatch.setattr(d.point, 'replay_point', changed)
    with pytest.raises((ValueError, AssertionError)): run(c)


def test_loaded_contract_reader_path_is_bound(tmp_path, monkeypatch):
    c = case(tmp_path, monkeypatch)
    monkeypatch.setattr(d, '__file__', str(tmp_path/'foreign.py'))
    with pytest.raises(ValueError, match='loaded contract module path'): run(c)
    assert c.observed == []


def test_saved_P1_four_contract_rows_use_original_C_and_explicit_call_accounting(monkeypatch):
    p1 = d.ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'
    anchor = p1.parent/'p1_execution_review_01/postcheck_03.stdout.json';raw = anchor.read_bytes()
    assert sha256(raw).hexdigest() == 'c6a25cd96c8a4a2cf293d41fe51bc7905db63fbc35253076f97e9239a4f22473'
    files = json.loads(raw)['p1_files'];assert len(files) == 683
    def preserve(): assert all(d.mechanical.pin((p1/n).read_bytes()) == v for n, v in files.items())
    preserve();fixture = d.core.load_fixture();start = json.loads((p1/'start.json').read_bytes())
    expected = dict(fixture_sha=d.core.digest(fixture), pins_sha=d.core.digest(start['pins']), registration_sha=start['registration_sha'],
        slots=tuple(json.loads((p1/'request_schedule.json').read_bytes())[21:]), rows_pin=files['contract_rows.json'],
        point_files={str(i): {n[len(f'points/point_{i:04d}/'):]: v for n, v in files.items()
            if n.startswith(f'points/point_{i:04d}/')} for i in d.ORDINALS})
    source = d.source_pins();counts = dict(compile=0,snapshot=0,import_snapshot=0,hour_requests=0,
        legal_x=0,explicit_firm_audit=0,source_reads=0,point_reads=0,row_reads=0,typed_pack=0)
    active = False
    original_C = d.point.replay_point
    def replay(*a, **kw):
        nonlocal active
        active = True
        try:return original_C(*a, **kw)
        finally:active = False
    monkeypatch.setattr(d.point, 'replay_point', replay)
    def counter(module, name, key):
        original = getattr(module, name)
        def wrapped(*a, **kw): counts[key] += 1;return original(*a, **kw)
        monkeypatch.setattr(module, name, wrapped)
    for module, name, key in ((d.point.numeric,'compile_problem','compile'),(d.point.backend,'snapshot_from_raw','snapshot'),
            (d.point.numeric,'import_snapshot','import_snapshot'),(d.core,'hour_requests','hour_requests'),
            (d.point.audit,'audit_legal_x','legal_x'),(d.codec,'pack','typed_pack')):counter(module,name,key)
    original_audit = d.point.audit.audit_point;in_legal = False
    original_legal = d.point.audit.audit_legal_x
    def legal(*a, **kw):
        nonlocal in_legal
        in_legal = True
        try:return original_legal(*a, **kw)
        finally:in_legal = False
    def audit(*a, **kw):
        if not active and not in_legal and a[0].request.role == 'fault_firm_F': counts['explicit_firm_audit'] += 1
        return original_audit(*a, **kw)
    monkeypatch.setattr(d.point.audit,'audit_legal_x',legal);monkeypatch.setattr(d.point.audit,'audit_point',audit)
    original_read = d.codec.read_bytes;original_bounded = d.mechanical.bounded_file_bytes
    def read(path,*a,**kw):
        key = 'row_reads' if Path(path) == p1/'contract_rows.json' else 'point_reads' if Path(path).is_relative_to(p1) else 'source_reads'
        counts[key] += 1;return original_read(path,*a,**kw)
    def bounded(path,*a,**kw):
        if Path(path) == p1/'contract_rows.json':counts['row_reads'] += 1
        else:
            assert Path(path).is_relative_to(p1/'points');counts['point_reads'] += 1
        return original_bounded(path,*a,**kw)
    monkeypatch.setattr(d.codec,'read_bytes',read);monkeypatch.setattr(d.mechanical,'bounded_file_bytes',bounded)
    result = d.replay_contracts(p1/'points',p1/'contract_rows.json',fixture,expected,
        json.loads((p1/'launcher.json').read_bytes()),source)
    objects = sum(n.startswith('cas/objects/') for inv in expected['point_files'].values() for n in inv)
    assert counts == dict(compile=20,snapshot=10,import_snapshot=10,hour_requests=2,legal_x=4,
        explicit_firm_audit=4,source_reads=954,point_reads=8*objects+32*10,row_reads=2,typed_pack=50)
    assert result['saved_representative_rows_match'] is True
    assert d.codec.canonical(list(result['rows'])) == (p1/'contract_rows.json').read_bytes()
    assert [r['evidence_family'] for r in result['visited_points']] == ['economic_kkt','primal_point','child_lp_kkt','primal_point','child_lp_kkt']*2
    assert all(r['legal_X']['point_legal_under_X'] and not r['legal_X']['minimum_established'] for r in result['rows'])
    preserve();assert anchor.read_bytes() == raw
    print(json.dumps(dict(oracle='saved_P1_four_representative_FX_rows',replayed_points=10,rows=list(result['rows']),
        queries=list(result['visited_points']),calls=counts,cas_objects=objects,P1_683_files_unchanged=True,new_native_calls=0,
        scientific_evidence_adopted=False,full_fx_contract_verified=False,independent_139_verified=False,
        journal_replayed=False,resource_admission=False,formal_result=False)))
